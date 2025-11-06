from __future__ import annotations
from typing import Dict, Any, List, Optional
import pandas as pd
import streamlit as st
from fairy.core.project import new_project

def render_home(projects: List[Dict[str, Any]], save_and_refresh) -> None:
    st.title("✨ FAIRy: Make Your Research Data FAIR—No Stress, No Surprises")
    st.markdown(
        "FAIRy helps you turn messy spreadsheets into fundable, repository-ready datasets. "
        "Upload any file, get an instant FAIR compliance audit, and see exactly what to fix—"
        "**no jargon, no frustration.**"
    )
    st.markdown("---")
    st.markdown(
        "🌟 **FAIRy is the free, intuitive tool for researchers to check, fix, and prepare data for submission—"
        "so your science gets recognized, not rejected.**"
    )

    with st.expander("➕ Create a new project", expanded=True):
        col1, col2 = st.columns([2,1])
        with col1:
            title = st.text_input("Project title*", placeholder="e.g., RNA-seq study on XYZ", key="new_project_title")
            desc = st.text_area("Short description*", placeholder="One or two lines about the dataset and study.", key="new_project_desc")
        with col2:
            if st.button("Create project", type="primary", disabled=not (title.strip() and desc.strip()), key="new_project_button"):
                p = new_project(title.strip(), desc.strip())
                projects.insert(0, p)
                save_and_refresh(projects)

    if not projects:
        st.info("No projects yet. Create your first one above!")
        return

    st.subheader("Your projects")
    df = pd.DataFrame([{
        "Title": p["title"], "Status": p["status"], "Updated": p["updated_at"], "ID": p["id"]
    } for p in projects])
    st.dataframe(df, use_container_width=True, hide_index=True)

    select_id = st.selectbox("Open a project", options=["— select —"] + [p["id"] for p in projects])
    if select_id != "— select —":
        st.session_state.selected_project_id = select_id
        st.rerun()
