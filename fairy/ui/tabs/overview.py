# fairy/ui/tabs/overview.py
from __future__ import annotations
from typing import Any, Dict, TYPE_CHECKING
if TYPE_CHECKING:
    from fairy.ui.shared.context import ProjectCtx
import streamlit as st
from fairy.core.storage import update_project_timestamp


def render_overview_tab(ctx: "ProjectCtx") -> None:
    project = ctx.project
    projects = ctx.projects
    save_and_refresh = ctx.save_and_refresh

    st.subheader("Overview")
    col1, col2 = st.columns(2)

    with col1:
        new_title = st.text_input("Title", value=project["title"], key=f"proj_title_{project['id']}")
        new_desc  = st.text_area("Description", value=project["description"], key=f"proj_desc_{project['id']}")

        colt, colg = st.columns(2)
        with colt:
            type_opts = ["RNA-seq", "ATAC-seq", "Proteomics", "Metabolomics"]
            idx = type_opts.index(project.get("type")) if project.get("type") in type_opts else 0
            p_type = st.selectbox("Project type", type_opts, index=idx, key=f"proj_type_{project['id']}")
        with colg:
            tags_str = st.text_input(
                "Tags (comma-separated)",
                value=",".join(project.get("tags", [])),
                key=f"proj_tags_{project['id']}",
            )

        if st.button("Save overview", key=f"save_overview_{project['id']}"):
            project["title"] = new_title.strip()
            project["description"] = new_desc.strip()
            project["type"] = p_type
            project["tags"] = [t.strip() for t in tags_str.split(",") if t.strip()]
            update_project_timestamp(project)
            ctx.save()  # calls the save_and_refresh you pass in

    with col2:
        st.markdown(f"**Status:** {project.get('status', '—')}")
        st.markdown(f"**Created:** {project.get('created_at', '—')}")
        st.markdown(f"**Updated:** {project.get('updated_at', '—')}")
