# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025 Jennifer Slotnick

# fairy/validation/types.py
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd


@dataclass
class Issue:
    kind: str  # e.g.: "missing_value" | "duplicate_value" | "missing_column" |
    #       "column_name_mismatch" | ...
    message: str
    severity: str = "warning"  # "error" | "warning" | "info"
    row: int | None = None  # 0-based row index in df
    col: str | None = None  # column name
    hint: str | None = None


# A Validator returns:
#  - mask: bool DataFrame (same shape as df) marking cells to highlight
#  - issues: list of Issue objects
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
