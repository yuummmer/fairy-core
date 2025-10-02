# fairy/validation/checks.py
from __future__ import annotations
import re
from typing import List, Tuple
import pandas as pd
from .types import Issue, Validator, blank_mask

def missing_required(required_cols: List[str]) -> Validator:
    def _validate(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[Issue]]:
        mask = blank_mask(df)
        issues: List[Issue] = []
        for col in required_cols:
            if col not in df.columns:
                issues.append(Issue(
                    kind="missing_column",
                    message=f"Required column '{col}' is missing.",
                    severity="error",
                    col=col,
                    hint="Add this column before export."
                ))
                continue
            nullish = df[col].isna() | df[col].astype(str).str.strip().eq("")
            if nullish.any():
                mask.loc[nullish, col] = True
                for r in df.index[nullish]:
                    issues.append(Issue(
                        kind="missing_value",
                        message=f"Missing value in required field '{col}'.",
                        severity="error",
                        row=int(r),
                        col=col,
                        hint="Fill this cell."
                    ))
        return mask, issues
    _validate.__name__ = "missing required"
    return _validate

def duplicate_in_column(col: str) -> Validator:
    def _validate(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[Issue]]:
        mask = blank_mask(df)
        issues: List[Issue] = []
        if col in df.columns:
            dupe = df[col].astype(str).str.lower().duplicated(keep=False)
            if dupe.any():
                mask.loc[dupe, col] = True
                for r, v in df.loc[dupe, col].items():
                    issues.append(Issue(
                        kind="duplicate_value",
                        message=f"Duplicate {col} value '{v}'.",
                        severity="warning",
                        row=int(r),
                        col=col,
                        hint="Ensure IDs are unique."
                    ))
        return mask, issues
    _validate.__name__ = f"duplicate_in_column[{col}]"
    return _validate

def column_name_mismatch() -> Validator:
    """Warn if columns differ only by case/underscores, e.g., SampleID vs sample_id."""
    def _validate(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[Issue]]:
        mask = blank_mask(df)  # no cell highlights; header warning instead
        issues: List[Issue] = []
        norm = {}
        for c in df.columns:
            key = re.sub(r"[^a-z0-9]+", "_", c.strip().lower()).strip("_")
            norm.setdefault(key, []).append(c)
        for key, cols in norm.items():
            if len(cols) > 1:
                issues.append(Issue(
                    kind="column_name_mismatch",
                    message=f"Columns {cols} appear to represent the same field (normalized '{key}').",
                    severity="warning",
                    hint=f"Keep one canonical name (e.g., '{key}') and remove/merge the others."
                ))
        return mask, issues
    _validate.__name__ = "column_name_mismatch"
    return _validate
