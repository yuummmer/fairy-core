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
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from typing import Any

import pandas as pd

from fairy import __version__ as FAIRY_CORE_VERSION
from fairy.rulepack.loader import load_rulepack

# pull shared types/utilities
from ..models.preflight_report_v1 import (
    InputMetadata,
    RulepackMetadata,
)
from ..validation_api import (
    WarningItem,
    now_utc_iso,
)
from ..validation_api import (
    validate_csv as _core_validate_csv,  # <-- NEW: import the canonical validate_csv
)
from ..validators import rna  # to call check_* helpers
from .provenance import compute_dataset_id, sha256_file, summarize_tabular
from .transform import transform_findings_to_results


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


def run_rulepack(
    rulepack_path: str | Path,
    samples_path: Path,
    files_path: Path,
    fairy_version: str,
    params: dict,
) -> dict:

    # ---NEW: context injected for rule functions
    ctx: dict[str, Any] = {"params": params or {}}

    # 1. load rulepack (YAML/JSON) -> Pydantic model
    rp = load_rulepack(rulepack_path)
    # convert to plain dict for existing logic (pack["rules"], pack.get)
    pack = rp.model_dump()

    # Build metadata.rulepack with provenance
    rulepack_sha256 = sha256_file(rulepack_path)
    meta = pack.get("meta") or {}

    rulepack_name = meta.get("name") or pack.get("rulepack_name") or "UNKNOWN_RULEPACK"
    rulepack_id = meta.get("id") or pack.get("rulepack_id") or rulepack_name
    rulepack_version = meta.get("version") or pack.get("rulepack_version") or "0.0.0"

    # 2. load dataframes
    samples_df = pd.read_csv(samples_path, sep="\t", dtype=str).fillna("")
    files_df = pd.read_csv(files_path, sep="\t", dtype=str).fillna("")

    all_findings: list[dict] = []
    all_rules: list[dict] = []  # Track all rules for transformation

    for rule in pack["rules"]:
        all_rules.append(rule)  # Track rule for later transformation
        spec = rule["check"]
        ctype = spec["type"]

        # dispatch to the right helper in rna.py
        if ctype == "require_columns":
            required_cols = spec.get("required_columns", [])
            warning_items = rna.check_required_columns(samples_df, required_cols, ctx=ctx)

        elif ctype == "at_least_one_nonempty_per_row":
            # spec["column_groups"] is like [["tissue","cell_line","cell_type"]]
            column_groups = spec.get("column_groups", [])
            group0 = column_groups[0] if column_groups else []
            warning_items = rna.check_bio_context(samples_df, group0, ctx=ctx)

        elif ctype == "id_crosscheck":
            # left_key is the sample ID key in samples.tsv
            left_key = spec.get("left_key", "sample_id")
            warning_items = rna.check_id_crossmatch(
                samples_df,
                files_df,
                samples_key=left_key,
                ctx=ctx,
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
                ctx=ctx,
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
                ctx=ctx,
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

    # Transform findings to results structure
    results = transform_findings_to_results(all_findings, all_rules)

    # Compute summary statistics
    by_level: dict[str, int] = {"pass": 0, "warn": 0, "fail": 0}
    by_rule: dict[str, str] = {}

    for result in results:
        level = result["level"]
        rule_id = result["rule"]
        by_level[level] = by_level.get(level, 0) + 1

        # Precedence: fail > warn > pass (if rule appears multiple times, take highest severity)
        if rule_id not in by_rule:
            by_rule[rule_id] = level
        else:
            current_level = by_rule[rule_id]
            # fail > warn > pass
            if level == "fail" or (level == "warn" and current_level == "pass"):
                by_rule[rule_id] = level

    # Sort by_rule keys for deterministic ordering
    by_rule = dict(sorted(by_rule.items()))

    # Build metadata.inputs with full metadata objects
    # Map input name → InputMetadata
    inputs_metadata: dict[str, InputMetadata] = {}

    # Current implementation uses hardcoded "samples" and "files"
    # TODO: Extract from rulepack inputs definition when available
    input_paths = {
        "samples": samples_path,
        "files": files_path,
    }

    # Build InputMetadata for each input
    for input_name, input_path in sorted(input_paths.items()):  # Sort for deterministic ordering
        meta_dict = summarize_tabular(Path(input_path))
        inputs_metadata[input_name] = InputMetadata(
            path=meta_dict["path"],
            sha256=meta_dict["sha256"],
            n_rows=meta_dict["n_rows"],
            n_cols=meta_dict["n_cols"],
            header=meta_dict["header"],
        )

    # For now, keep the old structure for backward compatibility
    # TODO: Replace with new PreflightReportV1 structure in next subtasks
    fail_count = sum(1 for f in all_findings if f["severity"] == "FAIL")
    warn_count = sum(1 for f in all_findings if f["severity"] == "WARN")

    # Build attestation (without inputs - metadata.inputs is canonical)
    attestation = {
        "rulepack_id": rulepack_id,
        "rulepack_version": rulepack_version,
        "rulepack_name": rulepack_name,
        "fairy_version": fairy_version,
        "run_at_utc": now_utc_iso(),
        "submission_ready": (fail_count == 0),
        "fail_count": fail_count,
        "warn_count": warn_count,
    }

    # Compute params_sha256 if params provided
    params_sha256: str | None = None
    if params:
        # Canonical JSON serialization: sorted keys, no whitespace
        canonical_params_json = json.dumps(params, sort_keys=True, separators=(",", ":"))
        params_bytes = canonical_params_json.encode("utf-8")
        params_hash_obj = sha256(params_bytes)
        params_sha256 = params_hash_obj.hexdigest()

    rulepack_metadata = RulepackMetadata(
        path=str(rulepack_path),
        sha256=rulepack_sha256,
        id=rulepack_id,
        version=rulepack_version,
        params_sha256=params_sha256,
    )

    # New canonical provenance fields
    rulepack_id = meta.get("id") or pack.get("rulepack_id", "UNKNOWN_RULEPACK")
    rulepack_ver = meta.get("version") or pack.get("rulepack_version", "0.0.0")
    rulepack_name = meta.get("name") or pack.get("rulepack", rulepack_id)
    rulepack_source_path = rulepack_metadata.path

    attestation.update(
        {
            "fairy_core_version": FAIRY_CORE_VERSION,
            "rulepack_name": rulepack_name,
            "rulepack_version": rulepack_ver,
            "rulepack_source_path": str(rulepack_source_path),
        }
    )

    # Convert InputMetadata dataclasses to dicts for JSON serialization
    inputs_metadata_dict: dict[str, dict[str, Any]] = {}
    for name, input_meta in sorted(inputs_metadata.items()):  # Sort keys alphabetically
        inputs_metadata_dict[name] = asdict(input_meta)

    # Convert RulepackMetadata to dict for JSON serialization
    # Filter out None values to match schema (optional fields should be omitted, not null)
    rulepack_metadata_dict = {k: v for k, v in asdict(rulepack_metadata).items() if v is not None}

    # Compute dataset_id from all inputs
    inputs_meta_for_dataset_id = {
        name: {
            "sha256": meta.sha256,
            "n_rows": meta.n_rows,
            "n_cols": meta.n_cols,
        }
        for name, meta in inputs_metadata.items()
    }
    dataset_id = compute_dataset_id(inputs_meta_for_dataset_id)

    # Format timestamp to ISO-8601 UTC with Z suffix
    # Allow override via environment variable for deterministic golden tests
    import os

    fixed_timestamp = os.environ.get("FAIRY_FIXED_TIMESTAMP")
    if fixed_timestamp:
        timestamp = fixed_timestamp
    else:
        timestamp = now_utc_iso()
    if timestamp.endswith("+00:00"):
        timestamp = timestamp.replace("+00:00", "Z")
    elif not timestamp.endswith("Z"):
        # If it's in ISO format without Z, add Z
        timestamp = timestamp + "Z" if "T" in timestamp else timestamp

    # Build new v1 report structure
    report = {
        "schema_version": "1.0.0",
        "generated_at": timestamp,
        "dataset_id": dataset_id,
        "metadata": {
            "inputs": inputs_metadata_dict,
            "rulepack": rulepack_metadata_dict,
        },
        "summary": {
            "by_level": by_level,
            "by_rule": by_rule,
        },
        "results": results,
        # Optional fields for future extensibility
        "engine": {"fairy_core_version": FAIRY_CORE_VERSION},
        "attestation": {
            "rulepack_name": rulepack_name,
            "rulepack_version": rulepack_ver,
            "rulepack_source_path": str(rulepack_path),
        },
        # Keep old structure temporarily for backward compatibility during migration
        "_legacy": {
            "attestation": attestation,
            "findings": all_findings,
        },
    }

    # Deprecation warning for _legacy field
    import warnings

    warnings.warn(
        "The '_legacy' field in preflight reports is deprecated and will be removed in v1.2.0. "
        "Please migrate to the v1.0.0 structure (metadata, summary, results).",
        DeprecationWarning,
        stacklevel=2,
    )

    return report
