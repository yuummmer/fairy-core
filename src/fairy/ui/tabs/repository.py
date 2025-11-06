from __future__ import annotations
import streamlit as st
from fairy.ui.shared.context import ProjectCtx
from fairy.core.storage import update_project_timestamp

def render_repository_tab(ctx: ProjectCtx) -> None:
    p = ctx.project
    st.subheader("Repository (placeholder)")
    repo = st.selectbox("Choose a repository",
                        ["— select —","GEO","SRA","ENA","Zenodo","dbGaP"],
                        index=0, key=f"repo_choice_{p['id']}")
    repo_notes = st.text_area("Notes", value=p["repository"].get("notes",""),
                                key=f"repo_notes_{p['id']}")
    if st.button("Save repository choice", key=f"repo_save_{p['id']}"):
        p["repository"] = {"choice": None if repo=="— select —" else repo, "notes": repo_notes.strip()}
        update_project_timestamp(p)
        save_and_refresh(projects)