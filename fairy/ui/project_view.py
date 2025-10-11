from __future__ import annotations
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import pandas as pd
import hashlib, io, json, time
import streamlit as st

from pathlib import Path
from fairy.core.storage import update_project_timestamp
from fairy.utils.projects import project_dir, exports_dir, load_manifest, save_manifest
from fairy.utils.ui import status_chip, format_bytes, shape_badge
from fairy.validation.checks import (
    missing_required, duplicate_in_column, column_name_mismatch
)
from fairy.validation.process_csv import process_csv
from fairy.core.services.report_writer import write_report
from fairy.ui.preview_utils import run_validators, build_tooltip_matrix, styled_preview
from fairy.ui.export_validate import render_export_validate_section

def _build_metadata(df: pd.DataFrame, filename: str) -> dict:
    return {
        "dataset_id": {"filename": filename},
        "run_at": datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
        "shape": {"n_rows": int(df.shape[0]), "n_cols": int(df.shape[1])},
        "columns": [str(c) for c in list(df.columns)[:10]],
    }

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

    with tabs[6]:
        st.subheader("Export & Validate")

        #Read required project context
        project_id = p.get("id")
        if not project_id:
            st.warning("No project selected. Go back to Home and pick a project.")
            st.stop()

        MAX_MB = 200
        proj_root = Path(project_dir(project_id))

        #Controls
        dry_run = st.toggle("Dry-run (no files written)", value=True, help="Preview/download only; no files saved, no history")
        upload = st.file_uploader("Upload a CSV to validate", type=["csv", "tsv", "txt"])
       
        #Delimiter control only shows once a file is picked
        delim_key = f"delim_{p['id']}"
        if delim_key not in st.session_state:
            st.session_state[delim_key] = "auto"

        upload_sig_key = f"upload_sig_{p['id']}"
        new_sig = (getattr(upload, "name", None), getattr(upload, "size", None))
        old_sig = st.session_state.get(upload_sig_key)
        if upload is not None and new_sig != old_sig:
            st.session_state[upload_sig_key] = new_sig
            st.session_state[delim_key] = "auto"
            st.session_state["min_meta_ok"] = False
            st.session_state["min_meta_payload"] = None

        if upload is not None:
            st.selectbox(
                 "Delimiter",
                options=[",", "\\t", ";", "|", "auto"],
                index=4,
                key=delim_key,
                help="If auto sniffing fails, pick the delimiter explicitly.",
            )

        delim = st.session_state[delim_key]

        st.session_state.setdefault("min_meta_ok", False)

        c1, c2 = st.columns([1, 1])
        validate_btn = c1.button("Validate", type="primary", disabled=upload is None)
        export_btn = c2.button("Export metadata.json", disabled=st.session_state.get("min_meta_ok") is not True)

        # Status container
        status = st.container()
                
        # --- Validate (guardrails + friendly parse + preflight via process_csv) ---
        if validate_btn:
            if upload is None:
                st.warning("Please choose a file to validate.")
                st.stop()

            with status:
                st.info("Validating...")
        
        # Size guardrail
            size_mb = upload.size / (1024 * 1024)
            if size_mb > MAX_MB:
                st.session_state["min_meta_ok"] = False
                status.error(f"File too large ({size_mb:.1f} MB). Limit is {MAX_MB} MB.")
                st.stop()

        # Parse with optional delimiter override (friendly errors)
            try:
                if delim == "auto":
                    df = pd.read_csv(upload, low_memory=False)
                else:
                    real = "\t" if delim == "\\t" else delim
                    df = pd.read_csv(upload, sep=real, low_memory=False)
            except UnicodeDecodeError:
                st.session_state["min_meta_ok"] = False
                status.error("Couldn’t read the file (encoding). Try saving as UTF-8 (CSV UTF-8).")
                st.stop()
            except pd.errors.ParserError as e:
                st.session_state["min_meta_ok"] = False
                status.error("Couldn’t parse CSV. Check delimiter and row consistency.")
                status.code(str(e))
                st.stop()
            except Exception as e:
                st.session_state["min_meta_ok"] = False
                status.error("Unexpected error while reading the file.")
                status.code(str(e))
                st.stop()

            status.success(f"Parsed OK — {df.shape[0]} rows × {df.shape[1]} cols")
            with st.expander("Preview (first 20 rows)", expanded=False):
                st.dataframe(df.head(20), use_container_width=True)

        # Persist the upload to project so downstream code has a real path
            proj_root = Path(project_dir(p["id"]))
            proj_root.mkdir(parents=True, exist_ok=True)
            tmp_path = proj_root / (upload.name or "uploaded.csv")
            tmp_path.write_bytes(upload.getbuffer())

        # Run FAIRy preflight checks
            meta_pre, _ = process_csv(str(tmp_path))
            warns = meta_pre.get("warnings", [])
            if warns:
                st.warning(f"{len(warns)} warnings found.")
                with st.expander("Warnings", expanded=False):
                    st.json(warns)
            else:
                st.info("No warnings produced by preflight checks.")

        # Build minimal metadata.json (prototype)
            meta_payload = _build_metadata(df, tmp_path.name)

        # Stash state for Export step
            st.session_state["min_meta_ok"]        = True
            st.session_state["min_meta_tmp_path"]  = str(tmp_path)
            st.session_state["min_meta_filename"]  = tmp_path.name
            st.session_state["min_meta_sha256"]    = meta_pre.get("sha256", "0"*64)
            st.session_state["min_meta_payload"]   = _build_metadata(df, tmp_path.name)

        # Export
        if export_btn:
            if st.session_state.get("min_meta_ok") is not True or not st.session_state.get("min_meta_payload"):
                st.warning("Validate a CSV successfully before exporting.")
            else:
                out_dir = Path(exports_dir(p["id"]))
                out_path = out_dir / "metadata.json"
                meta = st.session_state["min_meta_payload"]

                if dry_run:
                    st.info("Dry-run enabled: no file written.")
                    st.download_button(
                    "Download preview (metadata.json)",
                    data=json.dumps(meta, indent=2).encode("utf-8"),
                    file_name="metadata.json",
                    mime="application/json",
                    )
                    with st.expander("Preview JSON"):
                     st.code(json.dumps(meta, indent=2), language="json")
                else:
                    # 1) Write metadata.json
                    out_dir.mkdir(parents=True, exist_ok=True)
                    out_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

                    # 2)Write schema-validated report.json (v0.1) to project_dir/out
                    try:
                        proj_root = Path(project_dir(p["id"]))
                        report_out_dir = proj_root / "out"
                        report_path = write_report(
                            report_out_dir,
                            filename=st.session_state.get("min_meta_filename", "uploaded.csv"),
                            sha256=st.session_state.get("min_meta_sha256", "0"*64),
                            meta={
                                "n_rows": int(meta["shape"]["n_rows"]),
                                "n_cols": int(meta["shape"]["n_cols"]),
                                "fields_validated": meta.get("columns", []),
                                "warnings": [], #can feed process_csv here later
                            },
                            rulepacks=[],
                            provenance={"license": None, "source_url": None, "notes": None},
                            input_path=st.session_state.get("min_meta_tmp_path"),
                        )
                        st.success(f"Report written: {report_path}")
                    except Exception as e:
                        st.warning(f"Report writer skipped due to error: {e}")

                    # 3) Record export entry in project
                    export_record = {
                        "id": f"exp_{int(datetime.now(timezone.utc).timestamp())}",
                        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                        "summary": f"metadata.json written to {out_path}",
                        "files": {
                            "metadata": str(out_path),
                            "report": str((Path(project_dir(p["id"])) / 'out' / 'report.json').resolve()),
                        },
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
