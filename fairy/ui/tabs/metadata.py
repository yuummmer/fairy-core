# fairy/ui/tabs/metadata.py
from __future__ import annotations

import io, json, hashlib, time
from typing import List
from pathlib import Path

import pandas as pd
import streamlit as st

from fairy.ui.shared.context import ProjectCtx
from fairy.core.storage import update_project_timestamp
from fairy.utils.projects import project_dir, load_manifest, save_manifest
from fairy.utils.ui import status_chip, format_bytes, shape_badge
from fairy.validation.checks import (
    missing_required, duplicate_in_column, column_name_mismatch
)
from fairy.ui.preview_utils import run_validators, build_tooltip_matrix, styled_preview

TAB_PREFIX = "meta"  # namescope for this tab

def _k(pid: str, name: str) -> str:
    # e.g., "meta.preview_rows_prj_123"
    return f"{TAB_PREFIX}.{name}_prj_{pid}"

def render_metadata_tab(ctx: ProjectCtx) -> None:
    p = ctx.project
    pid = p["id"]

    st.subheader("Metadata (prototype)")

    # flash any save toast from earlier runs
    if msg := st.session_state.get("last_save_notice"):
        st.success(msg)

    st.caption("Upload metadata tables and associate them with one or more repository templates (e.g., GEO, SRA).")

    # project storage + manifest
    pdir = Path(project_dir(pid))
    manifest = load_manifest(pid)

    uploaded = st.file_uploader(
        "Upload samples metadata",
        type=["csv", "tsv", "json", "jsonl", "parquet"],
        key=_k(pid, "upload"),
    )

    df = None
    raw = None

    if uploaded:
        raw = uploaded.read()
        lname = uploaded.name.lower()
        try:
            if lname.endswith((".json", ".jsonl")):
                text = raw.decode("utf-8", errors="replace")
                if lname.endswith(".jsonl"):
                    recs = [json.loads(line) for line in text.splitlines() if line.strip()]
                else:
                    obj = json.loads(text)
                    recs = obj if isinstance(obj, list) else [obj]
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

        total_rows, total_cols = df.shape

        # Header metrics
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Rows", f"{total_rows:,}")
        with m2:
            st.metric("Columns", f"{total_cols:,}")
        with m3:
            st.metric("File", uploaded.name)

        # Choose required fields (defaults to common ones if present)
        options: List[str] = list(df.columns)
        expected = ["sample_id", "organism", "condition"]
        default_required = [c for c in expected if c in options]
        req = st.multiselect(
            "Required fields (highlight empties)",
            options=options,
            default=default_required,
            help="Empty cells in these columns are marked as errors",
            key=_k(pid, "required_fields"),
        )

        # Row count for preview
        if total_rows < 25:
            n = st.number_input(
                "Rows to preview",
                min_value=1,
                max_value=total_rows,
                value=total_rows,
                step=1,
                key=_k(pid, "preview_rows"),
            )
        else:
            n = st.slider(
                "Rows to preview",
                min_value=25,
                max_value=min(100, total_rows),
                value=25,
                key=_k(pid, "preview_rows"),
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
        preview_df = df.head(int(n))
        masks_slice = {name: m.loc[preview_df.index, preview_df.columns] for name, m in masks.items()}
        tips_slice = tips.loc[preview_df.index, preview_df.columns]

        styler = styled_preview(preview_df, masks_slice, tips_slice)

        # Column-name mismatch warnings (header-level)
        for iss in [i for i in issues if i.kind == "column_name_mismatch"]:
            st.warning(iss.message + (f" Hint: {iss.hint}" if iss.hint else ""))

        # Raw grid
        st.markdown("#### Data (scrollable)")
        st.dataframe(df.head(int(n)), use_container_width=True, hide_index=True, height=400)

        # Highlights view with tooltips
        st.markdown("#### Validation highlights (first rows)")
        st.caption("Hover for reasons. Colors: **red = error**, **gold = warning**.")
        st.table(styler)

        # Issue summary
        if issues:
            with st.expander(f"Show {len(issues)} validation notes"):
                iss_df = pd.DataFrame(
                    [
                        {
                            "severity": i.severity,
                            "kind": i.kind,
                            "row": (i.row + 1) if i.row is not None else None,
                            "column": i.col,
                            "message": i.message,
                            "hint": i.hint,
                        }
                        for i in issues
                    ]
                )
                st.dataframe(iss_df, use_container_width=True, hide_index=True)
        else:
            st.success("No issues detected in the previewed rows.")

        save_as = st.text_input("Save as", value=uploaded.name, key=_k(pid, "save_as"))
        template_options = ["GEO RNA-seq minimal", "SRA RNA-seq minimal"]
        chosen_templates = st.multiselect(
            "Associate templates",
            template_options,
            default=["GEO RNA-seq minimal"],
            key=_k(pid, "templates"),
        )

        if st.button("Save to Project & Manifest", key=_k(pid, "save_to_manifest")):
            # 1) persist file bytes
            (pdir / "files").mkdir(parents=True, exist_ok=True)
            (pdir / "files" / save_as).write_bytes(raw)

            # 2) build/merge manifest entry
            h = hashlib.sha256()
            h.update(raw)
            entry = {
                "name": save_as,
                "original_name": uploaded.name,
                "bytes": len(raw),
                "hash": h.hexdigest(),
                "saved_at": time.time(),
                "rows": int(df.shape[0]),
                "columns": list(df.columns),
                "templates": [{"name": t, "status": "pending"} for t in chosen_templates],
            }

            files = manifest.get("files", [])
            existing = next(
                (f for f in files if f.get("name") == save_as or f.get("hash") == entry["hash"]),
                None,
            )
            merged = False
            if existing:
                merged = True
                # merge columns + templates
                existing_cols = set(existing.get("columns", []))
                existing["columns"] = sorted(existing_cols.union(entry["columns"]))
                existing["rows"] = max(int(existing.get("rows", 0) or 0), entry["rows"])
                # merge templates by name
                existing_templates = {t["name"]: t for t in existing.get("templates", [])}
                for t in entry["templates"]:
                    if t["name"] not in existing_templates:
                        existing["templates"].append(t)
            else:
                files.append(entry)

            manifest["files"] = files
            save_manifest(pid, manifest)

            # keep your in-memory project copy if you want it
            p.setdefault("metadata", {}).setdefault("samples", [])
            p["metadata"]["samples"] = df.to_dict(orient="records")
            update_project_timestamp(p)

            # persisted toast
            templ_list = ", ".join(chosen_templates) if chosen_templates else "—"
            st.session_state["last_save_notice"] = (
                f"{'Updated' if merged else 'Saved'} **{save_as}** → {templ_list}"
                + (" (merged templates; no duplicate created)" if merged else "")
            )
            ctx.save_and_refresh(ctx.projects)

    # Files × Templates summary
    if manifest.get("files"):
        st.markdown("### Files × Templates")
        rows_ft = []
        for f in manifest["files"]:
            tlist = f.get("templates", [])
            # if no templates yet, show a '-' template row
            if not tlist:
                tlist = [{"name": "—", "status": "pending"}]
            for t in tlist:
                rows_ft.append(
                    {
                        "file": f["name"],
                        "template": t["name"],
                        "status": status_chip(t.get("status")),
                        "size": format_bytes(f.get("bytes")),
                        "shape": shape_badge(f.get("rows"), len(f.get("columns", []))),
                        "hash": (f.get("hash", "")[:10] + "…") if f.get("hash") else "",
                    }
                )
        st.dataframe(pd.DataFrame(rows_ft), use_container_width=True)
    else:
        st.caption("No files saved to this project manifest yet.")
