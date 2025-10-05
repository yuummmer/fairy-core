from __future__ import annotations
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import pandas as pd
import hashlib, io, json, time
import streamlit as st
import pandera as pa

from pandera import Column, DataFrameSchema
from pathlib import Path
from fairy.core.storage import update_project_timestamp
from fairy.utils.projects import project_dir, exports_dir, load_manifest, save_manifest
from fairy.utils.ui import status_chip, format_bytes, shape_badge
from fairy.validation.checks import (
    missing_required, duplicate_in_column, column_name_mismatch
)
from fairy.ui.preview_utils import run_validators, build_tooltip_matrix, styled_preview

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

    # ---- Metadata -------------------------------------------------
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

            if df is None:
                st.error("Could not read a tabular dataset from this file. Try CSV/TSV/JSONL")
                st.stop()

            # force string column names
            df.columns = [str(c) for c in df.columns]

            if df.empty:
                st.warning("The file loaded, but it has 0 rows.")
                st.stop()

            if len(df.columns) == 0:
               st.error("The file has no columns. Ensure there is a header row (CSV/TSV)")
               st.stop()

            if df is not None:
                total_rows, total_cols = df.shape

                # Header metrics
                m1, m2, m3 = st.columns(3)
                m1.metric("Rows", f"{total_rows:,}")
                m2.metric("Columns", f"{total_cols:,}")
                m3.metric("File", uploaded.name)

                # Choose required fields (defaults to common ones if present)
                options = list(df.columns)
                expected = ["sample_id", "organism", "condition"]
                default_required = [c for c in expected if c in options]
                
                req = st.multiselect(
                    "Required fields (highlight empties)",
                    options = options,
                    default = default_required,
                    help = "Empty cells in these columns are marked as errors"
                )
                
                if total_rows < 25:
                    n = st.number_input(
                        "Rows to preview",
                        min_value=1,
                        max_value=total_rows,
                        value=total_rows,
                        step=1,
                        key="preview_rows",
                    )
                else:
                    n = st.slider(
                        "Rows to preview",
                        min_value=25,
                        max_value=min(100, total_rows),
                        value=25,
                        key="preview_rows",
                    )
                
                # Run validators (modular hooks)
                validators = [
                missing_required(req),
                duplicate_in_column("sample_id"),
                column_name_mismatch(),
                ]
                masks, issues = run_validators(df, validators)
                tips = build_tooltip_matrix(df, issues)

                # Slice BEFORE styling
                preview_df  = df.head(int(n))
                masks_slice = {name: m.loc[preview_df.index, preview_df.columns] for name, m in masks.items()}
                tips_slice  = tips.loc[preview_df.index, preview_df.columns]

                styler = styled_preview(preview_df, masks_slice, tips_slice)

                # Column-name mismatch warnings(header-level)
                for iss in [i for i in issues if i.kind == "column_name_mismatch"]:
                    st.warning(iss.message + (f" Hint: {iss.hint}" if iss.hint else ""))
                # Raw grid
                st.markdown("#### Data (scrollable)")
                st.dataframe(df.head(n), use_container_width=True, hide_index=True, height=400)

                # Highlights view with tooltips
                st.markdown("#### Validation highlights (first rows)")
                st.caption("Hover for reasons. Colors: **red = error**, **gold = warning**.")
                st.table(styler)

                # Issue summary
                if issues:
                    with st.expander(f"Show {len(issues)} validation notes"):
                        iss_dif= pd.DataFrame([{
                            "severity": i.severity,
                            "kind": i.kind,
                            "row": (i.row +1) if i.row is not None else None,
                            "column": i.col,
                            "message": i.message,
                            "hint": i.hint
                        } for i in issues])
                        st.dataframe(iss_dif, use_container_width=True, hide_index=True)
                else:
                    st.success("No issues detected in the previewed rows.")

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
                        "rows": len(df),
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
                        existing["rows"] = max(existing.get("rows", 0) or 0, entry["rows"])
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
    def _minimal_schema_for(df: pd.DataFrame, max_cols: int = 3) -> DataFrameSchema:
        """Create a tiny schema from the first 2-3 columns"""
        cols = [str(c) for c in list(df.columns)[:max_cols]]
        if not cols:
            raise ValueError("CSV has no columns to validate.")
        schema_dict = {}
        for i, c in enumerate(cols):
            schema_dict[c] = Column(pa.String, coerce=True, nullable=(i != 0))
        return DataFrameSchema(schema_dict)
    
    def _build_metadata(df: pd.DataFrame, filename: str) -> dict:
        return {
            "dataset_id": {"filename": filename},
            "run_at": datetime.now(timezone.utc).isoformat().replace("+00.00","Z"),
            "shape": {"n_rows": int(df.shape[0]), "n_cols": int(df.shape[1])},
            "columns": [str(c) for c in list(df.columns)[:10]],
        }
    
    with tabs[6]:
        st.subheader("Export & Validate (prototype)")

        #Read required project context
        project_id = p.get("id")
        if not project_id:
            st.warning("No project selected. Go back to Home and pick a project.")
            st.stop()

        #Controls
        dry_run = st.toggle("Dry-run (no files written)", value=True)
        upload = st.file_uploader("Upload a CSV to validate", type=["csv"])

        c1, c2 = st.columns([1, 1])
        validate_btn = c1.button("Validate", type="primary", disabled=upload is None)
        export_btn = c2.button("Export metadata.json", disabled=st.session_state.get("min_meta_ok") is not True)

        # Status container
        status = st.container()

        # Validate
        if validate_btn and upload is not None:
            with status:
                st.info("Validating...")
            try:
                df = pd.read_csv(upload)
                schema = _minimal_schema_for(df)
                schema.validate(df, lazy=True)
                st.session_state["min_meta_ok"] = True
                st.session_state["min_meta_df_cols"] = list(df.columns)
                st.session_state["min_meta_filename"] = getattr(upload, "name", "uploaded.csv")
                st.session_state["min_meta_payload"] = _build_metadata(df, st.session_state["min_meta_filename"])
                status.success("Validation passed.")
            except Exception as e:
                msg = str(e)
                if len(msg) > 600:
                    msg = msg[:600] + "\n...(truncated)"
                st.session_state["min_meta_ok"] = False
                st.session_state["min_meta_payload"] = None
                status.error(msg)
                
        # Export
        if export_btn:
            if st.session_state.get("min_meta_ok") is not True or not st.session_state.get("min_meta_payload"):
                st.warning("Validate a CSV successfully before exporting.")
            else:
                out_dir = exports_dir(project_id)
                out_path = Path(out_dir) / "metadata.json"
                meta = st.session_state["min_meta_payload"]

                if dry_run:
                    st.info("Dry-run enabled: no file written.")
                    with st.expander("Preview metadata.json (dry-run)"):
                        st.code(json.dumps(meta, indent=2), language = "json")
                else:
                    out_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
                    export_record = {
                        "id": f"exp_{int(datetime.now(timezone.utc).timestamp())}",
                        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                        "summary": f"metadata.json written to {out_path}",
                    }
                    p.setdefault("exports", []).append(export_record)
                    update_project_timestamp(p)
                    save_and_refresh(projects)

                    st.success(f"Export complete: {out_path}")
                    st.code(json.dumps(meta, indent=2), language="json")
                
        if p.get("exports"):
            st.write(pd.DataFrame(p["exports"])[["id", "created_at", "summary"]])

    if st.sidebar.button("← Back to Home"):
        st.session_state.selected_project_id = None
        st.rerun()
