from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

import pandas as pd
import streamlit as st

from fairy.ui.shared.context import ProjectCtx
from fairy.validation.process_csv import process_csv
from fairy.core.services.report_writer import write_report
from fairy.core.storage import update_project_timestamp


def _build_metadata(df: pd.DataFrame, filename: str) -> Dict[str, Any]:
    return {
        "dataset_id": {"filename": filename},
        "run_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "shape": {"n_rows": int(df.shape[0]), "n_cols": int(df.shape[1])},
        "columns": [str(c) for c in list(df.columns)[:10]],
    }

def render_export_validate_tab(ctx: ProjectCtx) -> None:
    st.subheader("Export & Validate")

    MAX_MB = 200
    dry_run = st.toggle(
        "Dry-run (no files written)",
        value=True,
        help="Preview/download only; no files saved, no history",
    )
    upload = st.file_uploader("Upload a CSV to validate", type=["csv", "tsv", "txt"])

    # --- Delimiter control state (per project) ---
    delim_key = f"delim_{ctx.id}"
    if delim_key not in st.session_state:
        st.session_state[delim_key] = "auto"

    upload_sig_key = f"upload_sig_{ctx.id}"
    new_sig = (getattr(upload, "name", None), getattr(upload, "size", None))
    old_sig = st.session_state.get(upload_sig_key)
    if upload is not None and new_sig != old_sig:
        st.session_state[upload_sig_key] = new_sig
        st.session_state[delim_key] = "auto"          # reset delimiter when a new file arrives
        st.session_state["min_meta_ok"] = False       # reset validation state
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
    export_btn = c2.button(
        "Export metadata.json",
        disabled=st.session_state.get("min_meta_ok") is not True,
    )

    status = st.container()

    # --- Validate (guardrails + friendly parse + preflight via process_csv) ---
    if validate_btn:
        if upload is None:
            st.warning("Please choose a file to validate.")
            st.stop()

        with status:
            st.info("Validating…")

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
        ctx.proj_root.mkdir(parents=True, exist_ok=True)
        tmp_path = ctx.proj_root / (upload.name or "uploaded.csv")
        tmp_path.write_bytes(upload.getbuffer())

        # FAIRy preflight
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
        st.session_state["min_meta_ok"] = True
        st.session_state["min_meta_tmp_path"] = str(tmp_path)
        st.session_state["min_meta_filename"] = tmp_path.name
        st.session_state["min_meta_sha256"] = meta_pre.get("sha256", "0" * 64)
        st.session_state["min_meta_payload"] = meta_payload

    # --- Export ---
    if export_btn:
        if st.session_state.get("min_meta_ok") is not True or not st.session_state.get("min_meta_payload"):
            st.warning("Validate a CSV successfully before exporting.")
            return

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
            return

        # 1) Write metadata.json
        ctx.out_dir.mkdir(parents=True, exist_ok=True)
        meta_path = ctx.out_dir / "metadata.json"
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

        # 2) Write schema-validated report.json (v0.1) to project_dir/out
        report_path: Optional[Path] = None
        try:
            report_path = write_report(
                ctx.proj_root / "out",
                filename=st.session_state.get("min_meta_filename", "uploaded.csv"),
                sha256=st.session_state.get("min_meta_sha256", "0" * 64),
                meta={
                    "n_rows": int(meta["shape"]["n_rows"]),
                    "n_cols": int(meta["shape"]["n_cols"]),
                    "fields_validated": meta.get("columns", []),
                    "warnings": [],  # can feed process_csv warnings later
                },
                rulepacks=[],
                provenance={"license": None, "source_url": None, "notes": None},
                input_path=st.session_state.get("min_meta_tmp_path"),
            )
            st.success(f"Report written: {report_path}")
        except Exception as e:
            st.warning(f"Report writer skipped due to error: {e}")

        # 3) Record export entry in project
        p = ctx.project
        export_record = {
            "id": f"exp_{int(datetime.now(timezone.utc).timestamp())}",
            "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "summary": f"metadata.json written to {meta_path}",
            "files": {
                "metadata": str(meta_path.resolve()),
                "report": str(report_path.resolve()) if report_path else None,
            },
        }
        p.setdefault("exports", []).append(export_record)
        update_project_timestamp(p)
        ctx.save_and_refresh(ctx.projects)

        st.success(f"Export complete: {meta_path}")
        st.code(json.dumps(meta, indent=2), language="json")

    # Existing exports table
    if ctx.project.get("exports"):
        st.write(pd.DataFrame(ctx.project["exports"])[["id", "created_at", "summary"]])
