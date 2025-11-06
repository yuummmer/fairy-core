# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025 Jennifer Slotnick

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

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

import pandas as pd

# pull shared types/utilities
from ..validation_api import (
    WarningItem,
    now_utc_iso,
)
from ..validation_api import (
    validate_csv as _core_validate_csv,  # <-- NEW: import the canonical validate_csv
)
from ..validators import rna  # to call check_* helpers


# ---  bridge function so legacy code (process_csv) still works ---
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
    bits: list[str] = []
    if issue.row is not None and issue.row >= 0:
        bits.append(f"row {issue.row}")
    if issue.column:
        bits.append(f"column '{issue.column}'")
    if bits:
        return ", ".join(bits)
    return fallback_where


# === provenance helpers


def _sha256_file(p: Path) -> str:
    """
    Return sha256 hex digest of file at path p.
    Chunked so we don't load huge files fully into memory.
    """

    h = sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _summarize_tabular(p: Path) -> dict[str, Any]:
    """
    Collect provenance for a TSV/CSV-like metadata file:
    -path (as string)
    -sha256
    -n_rows (data rows, not counting header)
    -n_cols
    -header (list[str])

    Will *try* to use Frictionless if available for more robust parsing.
    If that fails or isn't installed, we fall back to simple TSV splitter.
    """
    path_str = str(p)
    file_hash = _sha256_file(p)

    header: list[str] = []
    n_cols = 0
    n_rows = 0

    # Try Frictionless first
    try:
        from frictionless import Resource  # type: ignore

        resource = Resource(path_str)

        # header list
        header = list(resource.header or [])
        n_cols = len(header)

        # Count rows via frictionless read_rows() (each is a dict-like row of data)
        data_rows = resource.read_rows()
        n_rows = len(data_rows)

    except Exception:
        # Fallback: naive TSV parse
        with p.open("r", encoding="utf-8") as f:
            lines = f.read().splitlines()

        if lines:
            header_line = lines[0]
            header = header_line.split("\t")
            n_cols = len(header)
            # everything after header is data rows
            n_rows = max(len(lines) - 1, 0)
        else:
            header = []
            n_cols = 0
            n_rows = 0

    return {
        "path": path_str,
        "sha256": file_hash,
        "n_rows": n_rows,
        "n_cols": n_cols,
        "header": header,
    }


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

    all_findings: list[dict] = []

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

    # Capture provenance / trust info for each input sheet
    samples_meta = _summarize_tabular(Path(samples_path))
    files_meta = _summarize_tabular(Path(files_path))

    attestation = {
        "rulepack_id": pack.get("rulepack_id", "UNKNOWN_RULEPACK"),
        "rulepack_version": pack.get("rulepack_version", "0.0.0"),
        "fairy_version": fairy_version,
        "run_at_utc": now_utc_iso(),
        "submission_ready": (fail_count == 0),
        "fail_count": fail_count,
        "warn_count": warn_count,
        "inputs": {
            "samples": samples_meta,
            "files": files_meta,
        },
    }

    report = {
        "attestation": attestation,
        "findings": all_findings,
    }

    return report
