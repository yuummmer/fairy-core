from __future__ import annotations
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import pandas as pd
import streamlit as st
from fairy.core.storage import update_project_timestamp

def _get_selected_project(projects: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    pid = st.session_state.get("selected_project_id")
    if not pid: return None
    for p in projects:
        if p["id"] == pid:
            return p
    return None

def render_project(projects: List[Dict[str, Any]], save_and_refresh) -> None:
    p = _get_selected_project(projects)
    if not p:
        st.warning("No project selected. Go to Home and choose a project, or create a new one.")
        return

    st.title(f"📁 {p['title']}")
    st.caption(p["description"])

    tabs = st.tabs(["Overview","Data Inventory","Permissions & Ethics","De-identification","Metadata","Repository","Export & Validate"])

    with tabs[0]:
        st.subheader("Overview")
        col1, col2 = st.columns(2)
        with col1:
            new_title = st.text_input("Title", value=p["title"], key=f"proj_title_{p['id']}")
            new_desc  = st.text_area("Description", value=p["description"], key=f"proj_desc_{p['id']}")
            # simple type/tags since you asked for them
            colt, colg = st.columns(2)
            with colt:
                p_type = st.selectbox("Project type", ["RNA-seq","ATAC-seq","Proteomics","Metabolomics"], index=0 if p.get("type") not in ["ATAC-seq","Proteomics","Metabolomics"] else ["RNA-seq","ATAC-seq","Proteomics","Metabolomics"].index(p.get("type")))
            with colg:
                tags_str = st.text_input("Tags (comma-separated)", value=",".join(p.get("tags", [])), key=f"proj_tags_{p['id']}")
            if st.button("Save overview"):
                p["title"], p["description"] = new_title.strip(), new_desc.strip()
                p["type"] = p_type
                p["tags"] = [t.strip() for t in tags_str.split(",") if t.strip()]
                update_project_timestamp(p)
                save_and_refresh(projects)
        with col2:
            st.markdown(f"**Status:** {p['status']}")
            st.markdown(f"**Created:** {p['created_at']}")
            st.markdown(f"**Updated:** {p['updated_at']}")

    with tabs[1]:
        st.subheader("Data Inventory")
        st.caption("Link to where your raw data lives (S3/GS/Box/Drive or local path). FAIRy doesn't upload your data; it records locations.")
        name = st.text_input("Item name", placeholder="e.g., FASTQ files (batch A)")
        path = st.text_input("Path or URL", placeholder="e.g., s3://bucket/run1/*.fastq.gz")
        notes = st.text_input("Notes (optional)")
        if st.button("Add to inventory") and name.strip() and path.strip():
            p["data_inventory"].append({"name": name.strip(), "path": path.strip(), "notes": notes.strip()})
            update_project_timestamp(p)
            save_and_refresh(projects)
        if p["data_inventory"]:
            st.table(pd.DataFrame(p["data_inventory"]))

    with tabs[2]:
        st.subheader("Permissions & Ethics (placeholder)")
        contains_human = st.radio("Does your dataset include human subjects data?", options=["Unknown","No","Yes"], index=0, key=f"perm_contains_human_{p['id']}")
        irb = st.radio("IRB/ethics approval required?", options=["Unknown","No","Yes"], index=0, key=f"perm_irb_{p['id']}")
        perm_notes = st.text_area("Notes", key=f"perm_notes_{p['id']}")
        if st.button("Save permissions"):
            p["permissions"] = {
                "contains_human_data": None if contains_human=="Unknown" else (contains_human=="Yes"),
                "irb_required": None if irb=="Unknown" else (irb=="Yes"),
                "notes": perm_notes.strip()
            }
            update_project_timestamp(p)
            save_and_refresh(projects)

    with tabs[3]:
        st.subheader("De-identification (placeholder)")
        strategy = st.text_area("Strategy / approach", value=p["deid"].get("strategy",""), key=f"deid_strategy_{p['id']}")
        deid_notes = st.text_area("Notes", value=p["deid"].get("notes",""), key=f"deid_notes_{p['id']}")
        if st.button("Save de-identification"):
            p["deid"] = {"strategy": strategy.strip(), "notes": deid_notes.strip()}
            update_project_timestamp(p)
            save_and_refresh(projects)

    with tabs[4]:
        st.subheader("Metadata (prototype)")
        uploaded = st.file_uploader("Upload samples CSV", type=["csv"])
        if uploaded:
            import pandas as pd
            try:
                df = pd.read_csv(uploaded)
                p["metadata"]["samples"] = df.to_dict(orient="records")
                update_project_timestamp(p)
                save_and_refresh(projects)
            except Exception as e:
                st.error(f"Failed to read CSV: {e}")
        if p["metadata"]["samples"]:
            st.dataframe(pd.DataFrame(p["metadata"]["samples"]), use_container_width=True)

    with tabs[5]:
        st.subheader("Repository (placeholder)")
        repo = st.selectbox("Choose a repository", ["— select —","GEO","SRA","ENA","Zenodo","dbGaP"], index=0, key=f"repo_choice_{p['id']}")
        repo_notes = st.text_area("Notes", value=p["repository"].get("notes",""), key=f"repo_notes_{p['id']}")
        if st.button("Save repository choice", key=f"repo_save_{p['id']}"):
            p["repository"] = {"choice": None if repo=="— select —" else repo, "notes": repo_notes.strip()}
            update_project_timestamp(p)
            save_and_refresh(projects)

    with tabs[6]:
        st.subheader("Export & Validate (prototype)")
        if st.button("Generate placeholder export"):
            export_record = {
                "id": f"exp_{int(datetime.now(timezone.utc).timestamp())}",
                "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
                "summary": "Placeholder export generated (implement real exporters next)."
            }
            p["exports"].append(export_record)
            update_project_timestamp(p)
            save_and_refresh(projects)
        if p["exports"]:
            st.write(pd.DataFrame(p["exports"])[["id","created_at","summary"]])

    if st.sidebar.button("← Back to Home"):
        st.session_state.selected_project_id = None
        st.rerun()
