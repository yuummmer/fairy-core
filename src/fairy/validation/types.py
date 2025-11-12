# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025 Jennifer Slotnick

# fairy/validation/types.py
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

import pandas as pd


# --- UI-oriented types ---#
@dataclass
class Issue:
    kind: str  # e.g.: "missing_value" | "duplicate_value" | "missing_column" |
    #       "column_name_mismatch" | ...
    message: str
    severity: str = "warning"  # "error" | "warning" | "info"
    row: int | None = None  # 0-based row index in df
    col: str | None = None  # column name
    hint: str | None = None


# mask + issues for the Streamlit table highlighter
Validator = Callable[[pd.DataFrame], tuple[pd.DataFrame, list[Issue]]]


def blank_mask(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(False, index=df.index, columns=df.columns)


def combine_masks(masks: dict[str, pd.DataFrame]) -> pd.DataFrame:
    # precedence handled later via CSS, for now union is fine
    out = None
    for m in masks.values():
        out = m if out is None else (out | m.reindex_like(out, fill_value=False))
    if out is None:
        out = pd.DataFrame(False, index=[], columns=[])
    return out


# --- Report-oriented types ---#

Level = Literal["fail", "warn", "info"]


@dataclass(frozen=True)
class Sample:
    # 1-based row number for reports (per AC). Use 0-based only inside UI adapters
    row: int
    value: Any
    detail: str | None = None


@dataclass
class RuleResult:
    id: str  # e.g., "row.unique"
    level: Level  # "fail" | "warn" | "info"
    count: int  # number of violations
    samples: list[Sample]  # up to 10, deterministic order
    meta: dict[str, Any]  # free-form context (e.g., {"column:"price"})


# --- Adapters: RuleResult -> UI (mask + issues) ---


def rule_result_to_issues(rr: RuleResult, *, kind: str | None = None) -> list[Issue]:
    """
    Convert a RuleResult to Issue[] for the UI. Uses 0-based row in Issue.row.
    We prefer metadata to locate the column to highlight when possible.
    """
    sev = {"fail": "error", "warn": "warning", "info": "info"}[rr.level]
    col = rr.meta.get("column") or rr.meta.get("from_column")  # FK shows 'from' side
    issues: list[Issue] = []
    for s in rr.samples:
        issues.append(
            Issue(
                kind=kind or rr.id,
                message=f"{rr.id}: offending value {s.value!r}",
                severity=sev,
                row=(s.row - 1 if s.row and s.row > 0 else None),  # convert to 0-based for UI
                col=col,
                hint=s.detail,
            )
        )
    # If count > #samples, we still communicate via a summary Issue without row context.
    if rr.count > len(rr.samples):
        issues.append(
            Issue(
                kind=(kind or rr.id) + ".summary",
                message=f"{rr.id}: {rr.count} total violations; showing {len(rr.samples)} samples",
                severity=sev,
                row=None,
                col=col,
            )
        )
    return issues


def rule_result_to_mask(df: pd.DataFrame, rr: RuleResult) -> pd.DataFrame:
    """
    Build a boolean mask to highlight cells/rows in the UI table for this rule.
    Heuristic: if rr.meta has a single 'column' (or 'from_column' for FK), mark that column
    at offending rows; otherwise, mark entire offending rows.
    """
    mask = blank_mask(df)
    col = rr.meta.get("column") or rr.meta.get("from_column")
    rows0 = [s.row - 1 for s in rr.samples if s.row and s.row > 0]
    if len(rows0) == 0:
        return mask

    if col and col in df.columns:
        mask.loc[df.index[rows0], col] = True
    else:
        mask.loc[df.index[rows0], :] = True
    return mask
