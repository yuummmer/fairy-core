# fairy/ui/preview_utils.py
from __future__ import annotations
from typing import Dict, List, Tuple
import pandas as pd
from fairy.validation.types import Issue, Validator, combine_masks

def run_validators(df: pd.DataFrame, validators: List[Validator]) -> Tuple[Dict[str, pd.DataFrame], List[Issue]]:
    masks: Dict[str, pd.DataFrame] = {}
    issues: List[Issue] = []
    for v in validators:
        m, iss = v(df)
        name = getattr(v, "__name__", v.__class__.__name__)
        masks[name] = m
        issues.extend(iss)
    return masks, issues

def build_tooltip_matrix(df: pd.DataFrame, issues: List[Issue]) -> pd.DataFrame:
    tips = pd.DataFrame("", index=df.index, columns=df.columns)
    for iss in issues:
        if iss.row is not None and iss.col is not None and iss.col in tips.columns and iss.row in tips.index:
            msg = f"{iss.severity.upper()}: {iss.message}"
            if iss.hint:
                msg += f" — {iss.hint}"
            tips.at[iss.row, iss.col] = (tips.at[iss.row, iss.col] + " | " if tips.at[iss.row, iss.col] else "") + msg
    return tips

def styled_preview(df: pd.DataFrame, masks: Dict[str, pd.DataFrame], tips: pd.DataFrame) -> pd.io.formats.style.Styler:
    # precedence: errors > warnings
    css_error   = "background-color:#5b1a1a;color:#fff;"
    css_warn    = "background-color:#4a3d00;color:#fff;"
    # Build a CSS matrix
    style = pd.DataFrame("", index=df.index, columns=df.columns)
    # any 'missing_required' or 'missing_value' set -> error
    for name, m in masks.items():
        if "missing" in name:
            style = style.where(~m, other=(style + css_error))
    # duplicate warnings, etc.
    for name, m in masks.items():
        if "duplicate" in name:
            style = style.where(~m, other=(style + css_warn))
    st = (df.style
            .apply(lambda _df: style, axis=None)
            .set_tooltips(tips)
            .set_properties(**{"border": "1px solid #222"}))
    return st
