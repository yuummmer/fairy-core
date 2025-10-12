# fairy/ui/tabs/data_inventory.py
from __future__ import annotations
import pandas as pd
import streamlit as st
from fairy.ui.shared.context import ProjectCtx

def render_data_inventory_tab(ctx: ProjectCtx) -> None:
    p = ctx.project
    st.subheader("Data Inventory")
    st.caption(
        "Link where your raw data lives (S3/GS/Box/Drive or local path). "
        "FAIRy records locations; it does not upload raw data."
    )

    name = st.text_input("Item name", placeholder="e.g., FASTQ files (batch A)")
    path = st.text_input("Path or URL", placeholder="e.g., s3://bucket/run1/*.fastq.gz")
    notes = st.text_input("Notes (optional)")

    if st.button("Add to inventory"):
        if name.strip() and path.strip():
            p.setdefault("data_inventory", [])
            p["data_inventory"].append(
                {"name": name.strip(), "path": path.strip(), "notes": notes.strip()}
            )
            ctx.save_and_refresh(ctx.projects)
        else:
            st.warning("Please provide both a name and a path/URL.")

    items = p.get("data_inventory", [])
    if items:
        st.table(pd.DataFrame(items))
    else:
        st.caption("No items yet.")
