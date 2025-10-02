# fairy/ui/metadata_preview.py
from __future__ import annotations
import io
import pandas as pd
import streamlit as st

from fairy.validation.checks import (
    missing_required, duplicate_in_column, column_name_mismatch
)
from fairy.ui.preview_utils import run_validators, build_tooltip_matrix, styled_preview

SUPPORTED_EXTS = (".csv", ".tsv", ".json", ".parquet")

def _read_any(f, name: str) -> pd.DataFrame:
    n = name.lower()
    if n.endswith(".csv"):
        return pd.read_csv(f)
    if n.endswith(".tsv") or n.endswith(".txt"):
        return pd.read_csv(f, sep="\t")
    if n.endswith(".json"):
        return pd.read_json(f, lines=False)
    if n.endswith(".parquet"):
        return pd.read_parquet(f)
    # fallback: try csv
    return pd.read_csv(f)

def render_metadata_preview():
    st.subheader("Metadata preview")
    st.caption("We only save after you confirm. This preview highlights obvious issues early.")

    uploaded = st.session_state.get("uploaded_metadata_file")
    # If your uploader lives elsewhere, set st.session_state["uploaded_metadata_file"] after upload.

    file = uploaded or st.file_uploader(
        "Upload samples metadata", type=[e.replace(".", "") for e in SUPPORTED_EXTS], accept_multiple_files=False
    )
    if file is None:
        st.info("Drop a CSV/TSV/JSON/Parquet file to preview.")
        return
    # Persist in session so we keep the preview while navigating
    st.session_state["uploaded_metadata_file"] = file

    df = _read_any(file, file.name)
    total_rows, total_cols = df.shape

    # Required fields (user can tweak)
    options = list(df.columns)
    expected = ["sample_id", "organism", "condition"]
    default_required = [c for c in expected if c in options]

    req = st.multiselect(
        "Required fields (highlight empties):",
        options=options,
        default=default_required,
        help="Cells missing in these columns are marked as errors."
    )

    # Preview size: 25–100 rows (or fewer if small file)
    # Pick safe slider bounds (works for tiny files too)
    if total_rows >= 25:
        min_rows = 25
        max_rows = min(100, total_rows)
        default_rows = min_rows
    else:
    # tiny dataset: let user preview everything
        min_rows = 1
        max_rows = max(1, total_rows)
        default_rows = max_rows
    
    n = st.slider("Rows to preview", min_rows, max_rows, default_rows, key = "preview_rows")

    # Validators (modular hooks)
    validators = [
        missing_required(req),
        duplicate_in_column("sample_id"),
        column_name_mismatch(),
        # ⤵️ you can append schema-specific checks later, e.g., from a rules pack
        # *rules_pack_validators
    ]

    masks, issues = run_validators(df, validators)
    tips = build_tooltip_matrix(df, issues)

    #Slice before styling
    preview_df = df.head(int(n))
    masks_slice = {name: m.loc[preview_df.index, preview_df.columns] for name, m in masks.items()}
    tips_slice = tips.loc[preview_df.index, preview_df.columns]
    
    #Build styler on sliced data
    styler = styled_preview(preview_df, masks_slice, tips_slice)

    # Header metrics
    mcol1, mcol2, mcol3 = st.columns(3)
    mcol1.metric("Rows", f"{total_rows:,}")
    mcol2.metric("Columns", f"{total_cols:,}")
    mcol3.metric("File", file.name)

    # Column-name mismatch warnings (header-level)
    for iss in [i for i in issues if i.kind == "column_name_mismatch"]:
        st.warning(iss.message + (f" Hint: {iss.hint}" if iss.hint else ""))

    # Scrollable raw grid (fast) + styled preview (with highlights & tooltips)
    st.markdown("#### Data (scrollable)")
    st.dataframe(df.head(n), use_container_width=True, hide_index=True, height=400)

    st.markdown("#### Validation highlights (first rows)")
    st.caption("Hover for reasons. Colors: **red = error**, **gold = warning**.")
    st.table(styler)

    # Issues summary panel
    if issues:
        with st.expander(f"Show {len(issues)} validation notes"):
            iss_df = pd.DataFrame([{
                "severity": i.severity,
                "kind": i.kind,
                "row": (i.row + 1) if i.row is not None else None,  # 1-based for humans
                "column": i.col,
                "message": i.message,
                "hint": i.hint
            } for i in issues])
            st.dataframe(iss_df, use_container_width=True, hide_index=True)
    else:
        st.success("No issues detected in the previewed rows.")

    # Optional: a light "OK to proceed" gate
    st.divider()
    st.checkbox("Looks good — proceed to repository mapping & export", key="metadata_preview_ok", value=False)
