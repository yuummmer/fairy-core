# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025 Jennifer Slotnick

# fairy/validation/checks.py
from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any
from urllib.parse import urlsplit

import pandas as pd

from .types import (
    Issue,
    Level,
    RuleResult,
    Sample,
    Validator,
    blank_mask,
    rule_result_to_issues,
    rule_result_to_mask,
)


def missing_required(required_cols: list[str]) -> Validator:
    def _validate(df: pd.DataFrame) -> tuple[pd.DataFrame, list[Issue]]:
        mask = blank_mask(df)
        issues: list[Issue] = []
        for col in required_cols:
            if col not in df.columns:
                issues.append(
                    Issue(
                        kind="missing_column",
                        message=f"Required column '{col}' is missing.",
                        severity="error",
                        col=col,
                        hint="Add this column before export.",
                    )
                )
                continue
            nullish = df[col].isna() | df[col].astype(str).str.strip().eq("")
            if nullish.any():
                mask.loc[nullish, col] = True
                for r in df.index[nullish]:
                    issues.append(
                        Issue(
                            kind="missing_value",
                            message=f"Missing value in required field '{col}'.",
                            severity="error",
                            row=int(r),
                            col=col,
                            hint="Fill this cell.",
                        )
                    )
        return mask, issues

    _validate.__name__ = "missing required"
    return _validate


def duplicate_in_column(col: str) -> Validator:
    def _validate(df: pd.DataFrame) -> tuple[pd.DataFrame, list[Issue]]:
        mask = blank_mask(df)
        issues: list[Issue] = []
        if col in df.columns:
            dupe = df[col].astype(str).str.lower().duplicated(keep=False)
            if dupe.any():
                mask.loc[dupe, col] = True
                for r, v in df.loc[dupe, col].items():
                    issues.append(
                        Issue(
                            kind="duplicate_value",
                            message=f"Duplicate {col} value '{v}'.",
                            severity="warning",
                            row=int(r),
                            col=col,
                            hint="Ensure IDs are unique.",
                        )
                    )
        return mask, issues

    _validate.__name__ = f"duplicate_in_column[{col}]"
    return _validate


def column_name_mismatch() -> Validator:
    """Warn if columns differ only by case/underscores, e.g., SampleID vs sample_id."""

    def _validate(df: pd.DataFrame) -> tuple[pd.DataFrame, list[Issue]]:
        mask = blank_mask(df)  # no cell highlights; header warning instead
        issues: list[Issue] = []
        norm = {}
        for c in df.columns:
            key = re.sub(r"[^a-z0-9]+", "_", c.strip().lower()).strip("_")
            norm.setdefault(key, []).append(c)
        for key, cols in norm.items():
            if len(cols) > 1:
                issues.append(
                    Issue(
                        kind="column_name_mismatch",
                        message=f"Columns {cols} look like the same field (normalized '{key}').",
                        severity="warning",
                        hint=f"Keep one canonical name (e.g., '{key}'); merge or drop others.",
                    )
                )
        return mask, issues

    _validate.__name__ = "column_name_mismatch"
    return _validate


# ===== RuleResult-based core rules (for rulepack runner) ===================


# Helpers
def _samples_from_index_values(idxs, vals, limit=10):
    sams = []
    for i, (idx, v) in enumerate(zip(list(idxs), list(vals), strict=False)):
        if i >= limit:
            break
        sams.append(Sample(row=int(idx) + 1, value=v))  # 1-based rows in reports
    return sams


def _result(
    rule_id: str, level: Level, count: int, samples: list[Sample], meta: dict[str, Any]
) -> RuleResult:
    return RuleResult(id=rule_id, level=level, count=count, samples=samples, meta=meta)


# 1) schema.required
def rr_schema_required(
    df: pd.DataFrame, *, required: Sequence[str], level: Level = "fail"
) -> RuleResult | None:
    missing = [c for c in required if c not in df.columns]
    if not missing:
        return None
    samples = [Sample(row=0, value=c, detail="missing column") for c in sorted(missing)[:10]]
    return _result(
        "schema.required",
        level,
        len(missing),
        samples,
        {"required": list(required), "missing": missing},
    )


# 2) row.unique
def rr_row_unique(
    df: pd.DataFrame,
    *,
    column: str,
    level: Level = "fail",
    case_insensitive: bool = False,
) -> RuleResult | None:
    if column not in df.columns:
        return rr_schema_required(df, required=[column], level=level)

    s = df[column]
    if case_insensitive:
        s = s.astype("string").str.lower()

    dup_mask = s.duplicated(keep=False)  # marks all members of duplicate groups
    if not dup_mask.any():
        return None

    total_count = int(dup_mask.sum())

    # Sample policy: for each duplicate value, take the LAST TWO indices
    groups: dict[Any, list[int]] = {}
    for idx, val in s.items():
        groups.setdefault(val, []).append(int(idx))

    sample_idxs: list[int] = []
    for _val, idxs in groups.items():
        if len(idxs) >= 2:
            sample_idxs.extend(idxs[-2:])  # last two of the run

    sample_idxs = sorted(sample_idxs)[:10]
    sams = [Sample(row=i + 1, value=df.loc[i, column]) for i in sample_idxs]

    return _result(
        "row.unique",
        level,
        total_count,
        sams,
        {"column": column, "case_insensitive": case_insensitive},
    )


# 3) table.foreign_key
def rr_table_foreign_key(
    df_from: pd.DataFrame,
    df_to: pd.DataFrame,
    *,
    from_column: str,
    to_column: str,
    level: Level = "fail",
) -> RuleResult | None:
    errs = []
    if from_column not in df_from.columns:
        errs.append(("from", from_column))
    if to_column not in df_to.columns:
        errs.append(("to", to_column))
    if errs:
        sams = [Sample(row=0, value=f"{side}.{col}", detail="missing column") for side, col in errs]
        return _result(
            "table.foreign_key",
            level,
            len(errs),
            sams,
            {"from_column": from_column, "to_column": to_column, "error": "missing columns"},
        )

    ref = set(pd.unique(df_to[to_column].dropna()).tolist())
    src = df_from[from_column]
    bad = ~src.isna() & (~src.isin(ref))
    if not bad.any():
        return None

    off = src[bad].sort_index(kind="mergesort")
    sams = _samples_from_index_values(off.index, off.values)
    return _result(
        "table.foreign_key",
        level,
        len(off),
        sams,
        {"from_column": from_column, "to_column": to_column},
    )


# 4) column.numeric_range
def rr_column_numeric_range(
    df: pd.DataFrame,
    *,
    column: str,
    min_value: float | None = None,
    max_value: float | None = None,
    level: Level = "fail",
) -> RuleResult | None:
    if column not in df.columns:
        return rr_schema_required(df, required=[column], level=level)

    # Coerce for mask calc (we need NaN for non-numeric)
    s_coerced = pd.to_numeric(df[column], errors="coerce")

    oob = pd.Series(False, index=df.index)
    if min_value is not None:
        oob |= s_coerced < min_value
    if max_value is not None:
        oob |= s_coerced > max_value
    nonnum = s_coerced.isna() & df[column].notna()
    bad = oob | nonnum
    if not bad.any():
        return None

    vals = df[column][bad].sort_index(kind="mergesort")
    sams = _samples_from_index_values(vals.index, vals.values)
    meta = {
        "column": column,
        "min": min_value,
        "max": max_value,
        "non_numeric_count": int(nonnum.sum()),
    }
    return _result("column.numeric_range", level, int(bad.sum()), sams, meta)


# 5) column.url (syntax + allowed schemes)
_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*$")


def _url_ok(v: Any, schemes: set[str]) -> bool:
    if pd.isna(v):
        return True
    try:
        s = str(v).strip()
    except Exception:
        return False

    if s.lower().startswith("www."):
        s = "https://" + s

    parts = urlsplit(s)
    scheme = (parts.scheme or "").lower()

    if not scheme or not _SCHEME_RE.match(scheme):
        return False

    if schemes and scheme not in {x.lower() for x in schemes}:
        return False

    return bool(parts.netloc or parts.path)


def rr_column_url(
    df: pd.DataFrame,
    *,
    column: str,
    schemes: Sequence[str] = ("http", "https"),
    level: Level = "fail",
) -> RuleResult | None:
    if column not in df.columns:
        return rr_schema_required(df, required=[column], level=level)

    allow = set(schemes or [])
    s = df[column]
    bad = ~s.apply(lambda v: _url_ok(v, allow))
    if not bad.any():
        return None

    vals = s[bad].sort_index(kind="mergesort")
    sams = _samples_from_index_values(vals.index, vals.values)
    return _result(
        "column.url", level, len(vals), sams, {"column": column, "schemes": sorted(allow)}
    )


# 6) column.non_empty_trimmed
def rr_column_non_empty_trimmed(
    df: pd.DataFrame,
    *,
    column: str,
    level: Level = "warn",
) -> RuleResult | None:
    if column not in df.columns:
        return rr_schema_required(df, required=[column], level=level)

    s = df[column].astype("string")
    bad = s.isna() | (s.str.strip().str.len() == 0)
    if not bad.any():
        return None
    vals = df[column][bad].sort_index(kind="mergesort")
    sams: list[Sample] = []
    for idx, val in vals.items():
        detail = "NA" if pd.isna(val) else f"len(stripped)={len(str(val).strip())}"
        sams.append(Sample(row=int(idx) + 1, value=val, detail=detail))
        if len(sams) >= 10:
            break
    return _result("column.non_empty_trimmed", level, len(vals), sams, {"column": column})


# 7) column.enum
def rr_column_enum(
    df: pd.DataFrame,
    *,
    column: str,
    allowed: Sequence[Any],
    level: Level = "warn",
    case_insensitive: bool = False,
) -> RuleResult | None:
    if column not in df.columns:
        return rr_schema_required(df, required=[column], level=level)

    if case_insensitive:
        allowed_set = {str(a).lower() for a in allowed}
        mask = df[column].notna() & (~df[column].astype(str).str.lower().isin(allowed_set))
    else:
        allowed_set = set(allowed)
        mask = df[column].notna() & (~df[column].isin(allowed_set))

    if not mask.any():
        return None

    vals = df[column][mask].sort_index(kind="mergesort")
    sams = _samples_from_index_values(vals.index, vals.values)
    return _result(
        "column.enum", level, len(vals), sams, {"column": column, "allowed_count": len(allowed_set)}
    )


# ===== UI wrappers so existing callers can still use (mask, issues) =========


def wrap_rr_as_validator(rr_fn, *, kind: str | None = None, **fixed_kwargs) -> Validator:
    """
    Wrap any RuleResult-producing function into your legacy Validator signature.
    Usage:
        unique_validator = wrap_rr_as_validator(rr_row_unique, column="id")
    """

    def _validate(df: pd.DataFrame):
        rr = rr_fn(df, **fixed_kwargs)
        if rr is None:
            return blank_mask(df), []
        return rule_result_to_mask(df, rr), rule_result_to_issues(rr, kind=kind)

    _validate.__name__ = getattr(rr_fn, "__name__", "rr_rule_wrapper")
    return _validate


# ---------- Back-compat exports expected by tests ----------
# Map legacy names used in tests to the new RuleResult-based implementations.

schema_required = rr_schema_required
row_unique = rr_row_unique
table_foreign_key = rr_table_foreign_key
column_numeric_range = rr_column_numeric_range
column_url = rr_column_url
column_non_empty_trimmed = rr_column_non_empty_trimmed
column_enum = rr_column_enum

__all__ = [
    # UI-style validators you already had:
    "missing_required",
    "duplicate_in_column",
    "column_name_mismatch",
    # RuleResult-based rules (new API):
    "rr_schema_required",
    "rr_row_unique",
    "rr_table_foreign_key",
    "rr_column_numeric_range",
    "rr_column_url",
    "rr_column_non_empty_trimmed",
    "rr_column_enum",
    # Back-compat names used by tests:
    "schema_required",
    "row_unique",
    "table_foreign_key",
    "column_numeric_range",
    "column_url",
    "column_non_empty_trimmed",
    "column_enum",
]
