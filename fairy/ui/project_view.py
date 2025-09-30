from __future__ import annotations
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import pandas as pd
import hashlib, io, json, time
import streamlit as st

from fairy.core.storage import update_project_timestamp
from fairy.utils.projects import project_dir, load_manifest, save_manifest
from fairy.utils.ui import status_chip, format_bytes, shape_badge


def _get_selected_project(projects: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    pid = st.session_state.get("selected_project_id")
    if not pid:
        return None
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

    tabs = st.tabs([
        "Overview",
        "Data Inventory",
        "Permissions & Ethics",
        "De-identification",
        "Metadata",
        "Repository",
        "Export & Validate"
    ])

    # ---- Overview -----------------------------------------------------------
    with tabs[0]:
        st.subheader("Overview")
        col1, col2 = st.columns(2)
        with col1:
            new_title = st.text_input("Title", value=p["title"], key=f"proj_title_{p['id']}")
            new_desc  = st.text_area("Description", value=p["description"], key=f"proj_desc_{p['id']}")
            colt, colg = st.columns(2)
            with colt:
                type_opts = ["RNA-seq","ATAC-seq","Proteomics","Metabolomics"]
                idx = type_opts.index(p.get("type")) if p.get("type") in type_opts else 0
                p_type = st.selectbox("Project type", type_opts, index=idx)
            with colg:
                tags_str = st.text_input("Tags (comma-separated)", value=",".join(p.get("tags", [])),
                                         key=f"proj_tags_{p['id']}")
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

    # ---- Data Inventory -----------------------------------------------------
    with tabs[1]:
        st.subheader("Data Inventory")
        st.caption("Link to where your raw data lives (S3/GS/Box/Drive or local path). FAIRy records locations; it does not upload raw data.")
        name = st.text_input("Item name", placeholder="e.g., FASTQ files (batch A)")
        path = st.text_input("Path or URL", placeholder="e.g., s3://bucket/run1/*.fastq.gz")
        notes = st.text_input("Notes (optional)")
        if st.button("Add to inventory") and name.strip() and path.strip():
            p["data_inventory"].append({"name": name.strip(), "path": path.strip(), "notes": notes.strip()})
            update_project_timestamp(p)
            save_and_refresh(projects)
        if p["data_inventory"]:
            st.table(pd.DataFrame(p["data_inventory"]))

    # ---- Permissions & Ethics ----------------------------------------------
    with tabs[2]:
        st.subheader("Permissions & Ethics (placeholder)")
        contains_human = st.radio("Does your dataset include human subjects data?",
                                  options=["Unknown","No","Yes"], index=0, key=f"perm_contains_human_{p['id']}")
        irb = st.radio("IRB/ethics approval required?",
                       options=["Unknown","No","Yes"], index=0, key=f"perm_irb_{p['id']}")
        perm_notes = st.text_area("Notes", key=f"perm_notes_{p['id']}")
        if st.button("Save permissions"):
            p["permissions"] = {
                "contains_human_data": None if contains_human=="Unknown" else (contains_human=="Yes"),
                "irb_required": None if irb=="Unknown" else (irb=="Yes"),
                "notes": perm_notes.strip()
            }
            update_project_timestamp(p)
            save_and_refresh(projects)

    # ---- De-identification --------------------------------------------------
    with tabs[3]:
        st.subheader("De-identification (placeholder)")
        strategy = st.text_area("Strategy / approach", value=p["deid"].get("strategy",""), key=f"deid_strategy_{p['id']}")
        deid_notes = st.text_area("Notes", value=p["deid"].get("notes",""), key=f"deid_notes_{p['id']}")
        if st.button("Save de-identification"):
            p["deid"] = {"strategy": strategy.strip(), "notes": deid_notes.strip()}
            update_project_timestamp(p)
            save_and_refresh(projects)

    # ---- Metadata (UPDATED) -------------------------------------------------
    with tabs[4]:
        st.subheader("Metadata (prototype)")
        if msg := st.session_state.get("last_save_notice"):
            st.success(msg)
        st.caption("Upload metadata tables and associate them with one or more repository templates (e.g., GEO, SRA).")

        # project storage + manifest
        pdir = project_dir(p["id"])
        manifest = load_manifest(p["id"])

        uploaded = st.file_uploader("Upload samples metadata",
                                    type=["csv","tsv","json","jsonl","parquet"])
        df = None
        raw = None

        if uploaded:
            raw = uploaded.read()
            lname = uploaded.name.lower()
            try:
                if lname.endswith((".json",".jsonl")):
                    text = raw.decode("utf-8", errors="replace")
                    if lname.endswith(".jsonl"):
                        recs = [json.loads(line) for line in text.splitlines() if line.strip()]
                    else:
                        obj = json.loads(text); recs = obj if isinstance(obj, list) else [obj]
                    df = pd.DataFrame(recs)
                elif lname.endswith(".parquet"):
                    df = pd.read_parquet(io.BytesIO(raw))
                else:
                    sniff = raw[:2048].decode("utf-8", errors="ignore")
                    sep = "\t" if sniff.count("\t") > sniff.count(",") or lname.endswith(".tsv") else ","
                    df = pd.read_csv(io.BytesIO(raw), sep=sep, encoding="utf-8-sig")
            except Exception as e:
                st.error(f"Failed to read file: {e}")

            if df is not None:
                st.write(f"Loaded **{len(df):,}** rows × **{len(df.columns):,}** columns")
                st.dataframe(df.head(25), use_container_width=True)

                save_as = st.text_input("Save as", value=uploaded.name)
                template_options = ["GEO RNA-seq minimal", "SRA RNA-seq minimal"]
                chosen_templates = st.multiselect("Associate templates", template_options,
                                                  default=["GEO RNA-seq minimal"])

                if st.button("Save to Project & Manifest"):
                    # 1) persist file bytes
                    (pdir / "files" / save_as).write_bytes(raw)
                    # 2) build/merge manifest entry
                    h = hashlib.sha256(); h.update(raw)
                    entry = {
                        "name": save_as,
                        "original_name": uploaded.name,
                        "bytes": len(raw),
                        "hash": h.hexdigest(),
                        "saved_at": time.time(),
                        "columns": list(df.columns),
                        "templates": [{"name": t, "status": "pending"} for t in chosen_templates]
                    }

                    files = manifest.get("files", [])
                    existing = next((f for f in files
                                     if f.get("name")==save_as or f.get("hash")==entry["hash"]), None)
                    merged = False
                    if existing:
                        merged = True
                        # merge columns + templates
                        existing_cols = set(existing.get("columns", []))
                        existing["columns"] = sorted(existing_cols.union(entry["columns"]))
                        existing["rows"] = max(existing.get("rows, 0") or 0, entry["rows"])
                        # merge templates by name
                        existing_templates = {t["name"]: t for t in existing.get("templates", [])}
                        for t in entry["templates"]:
                            if t["name"] not in existing_templates:
                                existing["templates"].append(t)
                    else:
                        files.append(entry)

                    manifest["files"] = files
                    save_manifest(p["id"], manifest)

                    # keep your in-memory project copy if you want it
                    p["metadata"]["samples"] = df.to_dict(orient="records")
                    update_project_timestamp(p)

                    # persisted toast
                    templ_list = ", ".join(chosen_templates) if chosen_templates else "—"
                    st.session_state["last_save_notice"] = (
                        f"{'Updated' if merged else 'Saved'} **{save_as}** → {templ_list}"
                        + (" (merged templates; no duplicate created)" if merged else "")
                    )
                    save_and_refresh(projects)

        # show manifest files + their templates
        if manifest.get("files"):
            st.markdown("### Files × Templates")
            rows_ft = []
            for f in manifest["files"]:
                tlist = f.get("templates", [])
                # if no templates yet, show a '-' template row
                if not tlist:
                    tlist = [{"name": "—", "status": "pending"}]
                for t in tlist:
                    rows_ft.append({
                    "file": f["name"],
                    "template": t["name"],
                    "status": status_chip(t.get("status")),
                    "size": format_bytes(f.get("bytes")),
                    "shape": shape_badge(f.get("rows"), len(f.get("columns", []))),
                    "hash": (f.get("hash","")[:10] + "…") if f.get("hash") else ""
                    })
            st.dataframe(pd.DataFrame(rows_ft), use_container_width=True)
        else:
            st.caption("No files saved to this project manifest yet.")

    # ---- Repository ---------------------------------------------------------
    with tabs[5]:
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

    # ---- Export & Validate --------------------------------------------------
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
