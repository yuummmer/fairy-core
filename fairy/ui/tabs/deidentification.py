from __future__ import annotations
import streamlit as st
from fairy.ui.shared.context import ProjectCtx
from fairy.core.storage import update_project_timestamp

def render_deidentification_tab(ctx: ProjectCtx) -> None:
    p = ctx.project
    st.subheader("De-identification")
    strategy = st.text_area("Strategy / approach", value=p.get("deid", {}).get("strategy", ""))
    notes = st.text_area("Notes", value=p.get("deid", {}).get("notes", ""))

    if st.button("Save de-identification"):
        p["deid"] = {"strategy": strategy.strip(), "notes": notes.strip()}
        update_project_timestamp(p)
        ctx.save_and_refresh(ctx.projects)
