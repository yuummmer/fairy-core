# fairy/core/services/validator.py
# Responsibilities:
# - Expose validate_csv(...) for the generic CSV workflow (older path)
# - Expose run_rulepack(...) for GEO RNA-seq preflight
#   (rulepack: fairy/rulepacks/GEO-SEQ-BULK/v0_1_0.json)
#
# run_rulepack:
#   - loads rulepack
#   - loads samples.tsv and files.tsv
#   - calls helper checks in validators/rna.py
#   - maps WarningItem -> FAIRy Findings with code / severity / where / why / how_to_fix
#   - builds Attestation
#   - returns {attestation, findings}

from __future__ import annotations

from pathlib import Path
import json
from typing import List, Dict, Any
import pandas as pd

# pull shared types/utilities
from ..validation_api import (
    WarningItem,
    Finding,
    Attestation,
    Report,
    now_utc_iso,
    validate_csv as _core_validate_csv,  # <-- NEW: import the canonical validate_csv
)

from ..validators import rna  # to call check_* helpers


# --- NEW: bridge function so legacy code (process_csv) still works ---
def validate_csv(path: str, kind: str = "rna"):
    """
    Thin wrapper that delegates to core.validation_api.validate_csv.

    We keep this here because process_csv.py imports
    `from fairy.core.services.validator import validate_csv`.

    Returning whatever validation_api.validate_csv returns
    (a Meta object).
    """
    return _core_validate_csv(path, kind=kind)


def _map_severity(internal: str) -> str:
    # "error" -> "FAIL", "warning" -> "WARN"
    return "FAIL" if internal.lower() == "error" else "WARN"


def _where_from_issue(issue: WarningItem, fallback_where: str) -> str:
    bits: List[str] = []
    if issue.row is not None and issue.row >= 0:
        bits.append(f"row {issue.row}")
    if issue.column:
        bits.append(f"column '{issue.column}'")
    if bits:
        return ", ".join(bits)
    return fallback_where


def run_rulepack(
    rulepack_path: Path,
    samples_path: Path,
    files_path: Path,
    fairy_version: str = "0.2.0",
) -> dict:
    # 1. load rulepack JSON
    pack = json.loads(Path(rulepack_path).read_text())

    # 2. load dataframes
    samples_df = pd.read_csv(samples_path, sep="\t", dtype=str).fillna("")
    files_df = pd.read_csv(files_path, sep="\t", dtype=str).fillna("")

    all_findings: List[dict] = []

    for rule in pack["rules"]:
        spec = rule["check"]
        ctype = spec["type"]

        # dispatch to the right helper in rna.py
        if ctype == "require_columns":
            required_cols = spec.get("required_columns", [])
            warning_items = rna.check_required_columns(samples_df, required_cols)

        elif ctype == "at_least_one_nonempty_per_row":
            # spec["column_groups"] is like [["tissue","cell_line","cell_type"]]
            column_groups = spec.get("column_groups", [])
            group0 = column_groups[0] if column_groups else []
            warning_items = rna.check_bio_context(samples_df, group0)

        elif ctype == "id_crosscheck":
            # left_key is the sample ID key in samples.tsv
            left_key = spec.get("left_key", "sample_id")
            warning_items = rna.check_id_crossmatch(
                samples_df,
                files_df,
                samples_key=left_key,
            )

        elif ctype == "paired_end_complete":
            # be defensive and default sanely
            warning_items = rna.check_paired_end_complete(
                files_df,
                samples_key=spec.get("samples_key", "sample_id"),
                layout_col=spec.get("layout_column", "layout"),
                paired_value=spec.get("layout_value_for_paired", "PAIRED"),
                file_col=spec.get("file_column", "filename"),
                r1_pattern=spec.get("r1_pattern", r"_R1"),
                r2_pattern=spec.get("r2_pattern", r"_R2"),
            )

        elif ctype == "dates_are_iso8601":
            date_cols = spec.get("columns", [])
            warning_items = rna.check_dates_iso8601(samples_df, date_cols)

        elif ctype == "processed_data_present":
            warning_items = rna.check_processed_data_present(
                files_df,
                samples_key=spec.get("samples_key", "sample_id"),
                raw_file_glob=spec.get("raw_file_glob", ".fastq"),
                processed_globs=spec.get(
                    "processed_glob_candidates",
                    [".counts", ".quant", ".gene_counts"],
                ),
            )

        else:
            warning_items = []

        # convert WarningItem -> final FAIRy "finding"
        for w in warning_items:
            mapped_sev = _map_severity(w.severity)
            finding = {
                "code": rule["code"],
                "severity": mapped_sev,
                "where": _where_from_issue(w, rule["where"]),
                "why": rule["why"],
                "how_to_fix": rule["how_to_fix"],
                "details": {
                    "kind": w.kind,
                    "message": w.message,
                    "hint": w.hint,
                    "row": w.row,
                    "column": w.column,
                },
            }
            all_findings.append(finding)

    fail_count = sum(1 for f in all_findings if f["severity"] == "FAIL")
    warn_count = sum(1 for f in all_findings if f["severity"] == "WARN")

    attestation = {
        "rulepack_id": pack.get("rulepack_id", "UNKNOWN_RULEPACK"),
        "rulepack_version": pack.get("rulepack_version", "0.0.0"),
        "fairy_version": fairy_version,
        "run_at_utc": now_utc_iso(),
        "submission_ready": (fail_count == 0),
        "fail_count": fail_count,
        "warn_count": warn_count,
    }

    report = {
        "attestation": attestation,
        "findings": all_findings,
    }

    return report
