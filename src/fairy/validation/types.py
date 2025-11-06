# fairy/validation/types.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Callable, Dict, List, Tuple
import pandas as pd

@dataclass
class Issue:
    kind: str                 # "missing_value" | "duplicate_value" | "missing_column" | "column_name_mismatch" | ...
    message: str
    severity: str = "warning" # "error" | "warning" | "info"
    row: Optional[int] = None # 0-based row index in df
    col: Optional[str] = None # column name
    hint: Optional[str] = None

# A Validator returns:
#  - mask: bool DataFrame (same shape as df) marking cells to highlight
#  - issues: list of Issue objects
Validator = Callable[[pd.DataFrame], Tuple[pd.DataFrame, List[Issue]]]

def blank_mask(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(False, index=df.index, columns=df.columns)

def combine_masks(masks: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    # precedence handled later via CSS, for now union is fine
    out = None
    for m in masks.values():
        out = m if out is None else (out | m.reindex_like(out, fill_value=False))
    if out is None:
        out = pd.DataFrame(False, index=[], columns=[])
    return out
