from __future__ import annotations
import streamlit as st
from fairy.ui.shared.context import ProjectCtx
from fairy.core.storage import update_project_timestamp

TAB_PREFIX = "perm"  # namescope for this tab

def _k(pid: str, name: str) -> str:
    # e.g., "perm.contains_human_prj_123"
    return f"{TAB_PREFIX}.{name}_prj_{pid}"

def render_permissions_tab(ctx: ProjectCtx) -> None:
    p = ctx.project
    pid = p["id"]

    st.subheader("Permissions & Ethics")

    contains_human = st.radio(
        "Does your dataset include human subjects data?",
        options=["Unknown", "No", "Yes"],
        index=0,
        key=_k(pid, "contains_human"),
    )

    irb = st.radio(
        "IRB/ethics approval required?",
        options=["Unknown", "No", "Yes"],
        index=0,
        key=_k(pid, "irb_required"),
    )

    notes = st.text_area("Notes", key=_k(pid, "notes"))

    if st.button("Save permissions", key=_k(pid, "save")):
        p["permissions"] = {
            "contains_human_data": None if contains_human == "Unknown" else (contains_human == "Yes"),
            "irb_required": None if irb == "Unknown" else (irb == "Yes"),
            "notes": notes.strip(),
        }
        update_project_timestamp(p)
        ctx.save_and_refresh(ctx.projects)
