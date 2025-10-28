from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

import pandas as pd
import streamlit as st

from fairy.ui.shared.context import ProjectCtx
from fairy.core.storage import update_project_timestamp
from fairy.core.services.validator import run_rulepack

# this import is from your current code
from fairy.validation.process_csv import process_csv
from fairy.core.services.report_writer import write_report

FAIRY_VERSION = "0.1.0"

# ----------------------------
# Helpers
# ----------------------------

def _read_manifest(uploaded_file):
    """
    Try TSV first, then CSV fallback.
    Returns a DataFrame[str] ("" for blanks) or None if unreadable.
    """
    if uploaded_file is None:
        return None

    try:
        df = pd.read_csv(uploaded_file, sep="\t", dtype=str).fillna("")
        return df
    except Exception:
        pass

    try:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, sep=",", dtype=str).fillna("")
        return df
    except Exception:
        return None


def _build_metadata(df: pd.DataFrame, filename: str) -> Dict[str, Any]:
    # This is from your original code
    return {
        "dataset_id": {"filename": filename},
        "run_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "shape": {"n_rows": int(df.shape[0]), "n_cols": int(df.shape[1])},
        "columns": [str(c) for c in list(df.columns)[:10]],
    }


# ----------------------------
# Flow 1: RNA-seq GEO rulepack preflight
# (This is the new "serious" validator)
# ----------------------------

def _render_rnaseq_preflight(ctx: ProjectCtx) -> None:
    import streamlit as st  # make sure we have st in scope here

    st.markdown(
        """
        **GEO bulk RNA-seq preflight**

        Upload:
        - `samples.tsv` (one row per biological sample)
        - `files.tsv` (FASTQs / processed outputs for each sample_id)

        FAIRy will:
        - decide if you're submission_ready (✅ / ❌),
        - show FAIL (blocking) vs WARN (non-blocking),
        - tell you how to fix each problem,
        - produce an attestation JSON you can save.
        """
    )

    # lil badge instead of st.info so it doesn't collapse on rerun
    st.markdown(
        """
        <div style="
            background-color:#1d2f40;
            border:1px solid #2f445a;
            border-radius:4px;
            padding:0.5rem 0.75rem;
            color:#cfe9ff;
            font-size:0.9rem;
            display:inline-block;
            font-weight:500;
            margin-bottom:1rem;
        ">
        Rulepack: GEO-SEQ-BULK@0.1.0
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns(2)
    with col_left:
        samples_file = st.file_uploader(
            "samples.tsv",
            type=["tsv", "txt", "csv"],
            help="Sample metadata. Must include sample_id and biological context (tissue / cell_line / cell_type).",
            key="pre_samples",
        )
    with col_right:
        files_file = st.file_uploader(
            "files.tsv",
            type=["tsv", "txt", "csv"],
            help="File manifest linking FASTQs and processed outputs to each sample_id.",
            key="pre_files",
        )

    run_btn = st.button(
        "Run FAIRy Preflight ✅",
        type="primary",
        key="pre_run",
    )

    # We'll store the latest run's output in session_state so it survives rerun
    result_key = f"preflight_result_{ctx.id}"
    last_report = st.session_state.get(result_key)

    # If the user clicked the button this run, compute a fresh report
    if run_btn:
        if samples_file is None or files_file is None:
            st.error("Please upload both `samples.tsv` and `files.tsv` before running FAIRy.")
        else:
            with st.spinner("Validating…"):
                # parse manifests
                samples_df = _read_manifest(samples_file)
                files_df = _read_manifest(files_file)

                if samples_df is None:
                    st.error("Could not parse `samples.tsv` as TSV or CSV.")
                    samples_df = None
                if files_df is None:
                    st.error("Could not parse `files.tsv` as TSV or CSV.")
                    files_df = None

                if samples_df is not None and files_df is not None:
                    # write temp copies so run_rulepack() can read from disk
                    tmp_dir = ctx.proj_root / ".preflight_tmp"
                    tmp_dir.mkdir(parents=True, exist_ok=True)

                    tmp_samples_path = tmp_dir / "samples.tmp.tsv"
                    tmp_files_path = tmp_dir / "files.tmp.tsv"
                    samples_df.to_csv(tmp_samples_path, sep="\t", index=False)
                    files_df.to_csv(tmp_files_path, sep="\t", index=False)

                    rulepack_path = Path("fairy/rulepacks/GEO-SEQ-BULK/v0_1_0.json")

                    report = run_rulepack(
                        rulepack_path=rulepack_path,
                        samples_path=tmp_samples_path,
                        files_path=tmp_files_path,
                        fairy_version=FAIRY_VERSION,
                    )

                    # cache the report + the preview dfs so we can show after rerun
                    st.session_state[result_key] = {
                        "report": report,
                        "samples_preview": samples_df.head(20),
                        "files_preview": files_df.head(20),
                    }

                    # also append to project history right now
                    att = report["attestation"]
                    export_record = {
                        "id": f"preflight_{int(datetime.now(timezone.utc).timestamp())}",
                        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                        "summary": (
                            f"submission_ready={att['submission_ready']}, "
                            f"FAIL={att['fail_count']}, WARN={att['warn_count']}"
                        ),
                        "files": {
                            "report_json": report,
                        },
                    }
                    ctx.project.setdefault("exports", []).append(export_record)
                    update_project_timestamp(ctx.project)
                    ctx.save_and_refresh(ctx.projects)
                    # ctx.save_and_refresh triggers st.rerun()
                    # After rerun, run_btn will be False but session_state[result_key] will exist.

        # After clicking, we don't render below in THIS run because st.rerun() will happen.
        # Just return now.
        return

    # If we reach here, either:
    # - user hasn't run yet this session, OR
    # - we've rerun after a successful run, so result is in session_state
    latest = st.session_state.get(result_key)
    if not latest:
        # nothing run yet -> show previous exports table (history) and bail
        if ctx.project.get("exports"):
            st.markdown("---")
            st.markdown("Previous validations / attestations")
            st.write(
                pd.DataFrame(ctx.project["exports"])[
                    ["id", "created_at", "summary"]
                ]
            )
        return

    # ----- We have a cached result: show full rich output -----

    report = latest["report"]
    att = report["attestation"]
    findings = report["findings"]

    # 1. Submission readiness banner
    ready_str = "✅ Submission READY" if att["submission_ready"] else "❌ Submission NOT READY"

    st.markdown(
        f"""
        <div style="
            background-color:#24384a;
            border:1px solid #3a5068;
            border-radius:4px;
            padding:0.75rem 1rem;
            color:#ffffff;
            font-weight:600;
            margin-top:1.5rem;
            margin-bottom:0.5rem;
        ">
        {ready_str}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div style="
            background-color:#1f3a1f;
            border:1px solid #395239;
            border-radius:4px;
            padding:0.5rem 1rem;
            color:#d8ffd8;
            font-size:0.9rem;
            margin-bottom:1rem;
        ">
        FAIL findings: <b>{att['fail_count']}</b> &nbsp;|&nbsp;
        WARN findings: <b>{att['warn_count']}</b><br/>
        Rulepack: <code>{att['rulepack_id']}@{att['rulepack_version']}</code><br/>
        FAIRy: <code>{att['fairy_version']}</code><br/>
        Run at (UTC): {att['run_at_utc']}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2. Preview inputs
    st.markdown("#### Preview (first 20 rows)")
    with st.expander("samples.tsv preview", expanded=False):
        st.dataframe(latest["samples_preview"], use_container_width=True)
    with st.expander("files.tsv preview", expanded=False):
        st.dataframe(latest["files_preview"], use_container_width=True)

    # 3. Summary banners for FAIL / WARN
    fail_count = att["fail_count"]
    warn_count = att["warn_count"]

    if fail_count > 0:
        st.markdown(
            f"""
            <div style="
                background-color:#553333;
                border:1px solid #aa5555;
                border-radius:4px;
                padding:0.75rem 1rem;
                color:#ffdada;
                font-weight:500;
                margin-top:1rem;
            ">
            {fail_count} blocking FAIL finding(s). You must fix these before submission.
            </div>
            """,
            unsafe_allow_html=True,
        )

    if warn_count > 0:
        st.markdown(
            f"""
            <div style="
                background-color:#555533;
                border:1px solid #aaaa55;
                border-radius:4px;
                padding:0.75rem 1rem;
                color:#fff8c0;
                font-weight:500;
                margin-top:0.5rem;
            ">
            {warn_count} WARN finding(s). These may pass submission, but should be cleaned up.
            </div>
            """,
            unsafe_allow_html=True,
        )

    if fail_count == 0 and warn_count == 0:
        st.markdown(
            """
            <div style="
                background-color:#1f3a1f;
                border:1px solid #395239;
                border-radius:4px;
                padding:0.75rem 1rem;
                color:#d8ffd8;
                font-weight:500;
                margin-top:1rem;
            ">
            No FAIL or WARN findings. Looks good for submission 🎉
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 4. Findings table + detail expanders
    st.markdown("#### Findings")
    if len(findings) == 0:
        st.success("No issues to report.")
    else:
        flat_rows: List[Dict[str, Any]] = []
        for f in findings:
            flat_rows.append({
                "Severity": f["severity"],
                "Code": f["code"],
                "Where": f["where"],
                "Why this matters": f["why"],
                "How to fix": f["how_to_fix"],
            })
        st.dataframe(pd.DataFrame(flat_rows), use_container_width=True)

        st.markdown("#### Details per finding")
        for f in findings:
            header = f"[{f['severity']}] {f['code']} @ {f['where']}"
            with st.expander(header, expanded=False):
                st.markdown(f"**Why this matters:** {f['why']}")
                st.markdown(f"**How to fix:** {f['how_to_fix']}")
                st.markdown("**Debug details:**")
                st.json(f["details"])

    # 5. FAIRy report JSON + download
    st.markdown("#### FAIRy report JSON")
    st.json(report)

    st.download_button(
        "Download FAIRy report.json",
        data=json.dumps(report, indent=2).encode("utf-8"),
        file_name="fairy_report.json",
        mime="application/json",
        key="pre_download",
    )

    # 6. History table (exports)
    if ctx.project.get("exports"):
        st.markdown("---")
        st.markdown("Previous validations / attestations")
        st.write(
            pd.DataFrame(ctx.project["exports"])[
                ["id", "created_at", "summary"]
            ]
        )

# ----------------------------
# Flow 2: Generic CSV checker
# (This is your original code, mostly intact)
# ----------------------------

def _render_generic_csv_checker(ctx: ProjectCtx) -> None:
    MAX_MB = 200

    st.markdown(
        """
        **Generic spreadsheet check (prototype)**

        Upload any CSV/TSV. FAIRy will:
        - parse it safely,
        - show you the first rows,
        - run lightweight checks,
        - generate a minimal metadata.json you can download or save.

        This is great for quick sanity checking before you commit to a repository.
        """
    )

    dry_run = st.toggle(
        "Dry-run (no files written)",
        value=True,
        help="Preview/download only; no files saved to the project history.",
    )

    upload = st.file_uploader(
        "Upload a CSV/TSV to validate",
        type=["csv", "tsv", "txt"]
    )

    # delimiter state per project
    delim_key = f"delim_{ctx.id}"
    if delim_key not in st.session_state:
        st.session_state[delim_key] = "auto"

    upload_sig_key = f"upload_sig_{ctx.id}"
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
    validate_btn = c1.button(
        "Validate",
        type="primary",
        disabled=upload is None,
        key="generic_validate_btn",
    )
    export_btn = c2.button(
        "Export metadata.json",
        disabled=st.session_state.get("min_meta_ok") is not True,
        key="generic_export_btn",
    )

    status = st.container()

    # --- VALIDATE step (parse + process_csv) ---
    if validate_btn:
        if upload is None:
            st.warning("Please choose a file to validate.")
            st.stop()

        with status:
            st.info("Validating…")

        # size guardrail
        size_mb = upload.size / (1024 * 1024)
        if size_mb > MAX_MB:
            st.session_state["min_meta_ok"] = False
            status.error(f"File too large ({size_mb:.1f} MB). Limit is {MAX_MB} MB.")
            st.stop()

        # parse CSV/TSV with delimiter override
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

        # Persist upload to disk for downstream uses (e.g. report_writer)
        ctx.proj_root.mkdir(parents=True, exist_ok=True)
        tmp_path = ctx.proj_root / (upload.name or "uploaded.csv")
        tmp_path.write_bytes(upload.getbuffer())

        # FAIRy lightweight preflight
        meta_pre, _ = process_csv(str(tmp_path))
        warns = meta_pre.get("warnings", [])
        if warns:
            st.warning(f"{len(warns)} warnings found.")
            with st.expander("Warnings", expanded=False):
                st.json(warns)
        else:
            st.info("No warnings produced by preflight checks.")

        # Build minimal metadata.json
        meta_payload = _build_metadata(df, tmp_path.name)

        # Store state for Export step
        st.session_state["min_meta_ok"] = True
        st.session_state["min_meta_tmp_path"] = str(tmp_path)
        st.session_state["min_meta_filename"] = tmp_path.name
        st.session_state["min_meta_sha256"] = meta_pre.get("sha256", "0" * 64)
        st.session_state["min_meta_payload"] = meta_payload

    # --- EXPORT step (write metadata.json + report) ---
    if export_btn:
        if st.session_state.get("min_meta_ok") is not True or not st.session_state.get("min_meta_payload"):
            st.warning("Validate a CSV successfully before exporting.")
            return

        meta = st.session_state["min_meta_payload"]

        if dry_run:
            st.info("Dry-run enabled: no file written to project.")
            st.download_button(
                "Download preview (metadata.json)",
                data=json.dumps(meta, indent=2).encode("utf-8"),
                file_name="metadata.json",
                mime="application/json",
                key="generic_download_btn",
            )
            with st.expander("Preview JSON"):
                st.code(json.dumps(meta, indent=2), language="json")
            return

        # Actually write metadata + report into the project
        ctx.out_dir.mkdir(parents=True, exist_ok=True)
        meta_path = ctx.out_dir / "metadata.json"
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

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
                    "warnings": [],  # you could plumb in warns later
                },
                rulepacks=[],
                provenance={"license": None, "source_url": None, "notes": None},
                input_path=st.session_state.get("min_meta_tmp_path"),
            )
            st.success(f"Report written: {report_path}")
        except Exception as e:
            st.warning(f"Report writer skipped due to error: {e}")

        # Log this export in the project
        export_record = {
            "id": f"exp_{int(datetime.now(timezone.utc).timestamp())}",
            "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "summary": f"metadata.json written to {meta_path}",
            "files": {
                "metadata": str(meta_path.resolve()),
                "report": str(report_path.resolve()) if report_path else None,
            },
        }
        ctx.project.setdefault("exports", []).append(export_record)
        update_project_timestamp(ctx.project)
        ctx.save_and_refresh(ctx.projects)

    # show previous exports table (history)
    if ctx.project.get("exports"):
        st.markdown("---")
        st.write(pd.DataFrame(ctx.project["exports"])[["id", "created_at", "summary"]])


# ----------------------------
# Router: decide which flow to show
# ----------------------------

def render_export_validate_tab(ctx: ProjectCtx) -> None:
    project_type = ctx.project.get("type", "RNA-seq")

    st.subheader("Export & Validate")
    st.caption(f"Project type: {project_type}")

    if project_type == "RNA-seq":
        _render_rnaseq_preflight(ctx)
    else:
        _render_generic_csv_checker(ctx)
