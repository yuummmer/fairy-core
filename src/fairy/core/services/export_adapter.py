# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025 Jennifer Slotnick

# fairy/core/services/export_adapter.py
from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ...cli.output_md import emit_preflight_markdown  # reuse your MD emitter
from ...cli.run import FAIRY_VERSION
from ..services.validator import run_rulepack


@dataclass
class ExportResult:
    export_dir: Path
    zip_path: Path
    manifest_path: Path
    provenance_path: Path
    report_path: Path
    report_md_path: Path


def _sha256_of_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, obj: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def run_preflight_and_write(
    *,
    rulepack: Path,
    samples: Path,
    files: Path,
    out_stem: Path,
    fairy_version: str = FAIRY_VERSION,
) -> tuple[Path, Path, dict]:
    """
    Runs validator (attestation+findings), writes JSON to out_stem (no suffix),
    writes Markdown to out_stem.md, returns (json_path, md_path, attestation_dict).
    """
    report = run_rulepack(
        rulepack_path=rulepack.resolve(),
        samples_path=samples.resolve(),
        files_path=files.resolve(),
        fairy_version=fairy_version,
    )
    # JSON
    json_path = out_stem
    json_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(json_path, report)

    # Markdown (reuse your CLI emitter)
    md_path = out_stem.with_suffix(".md")
    emit_preflight_markdown(
        md_path=md_path,
        report=report,
        resolved_codes=[],  # resolved diff is optional for export demo
        prior_codes=set(),  # pass empty set so emitter renders the block
    )
    # Return attestation dict (canonical, already includes provenance/header fields)
    att = report.get("attestation") or report.get("_legacy", {}).get("attestation") or {}
    return json_path, md_path, att


def _shim_build_bundle(
    *,
    export_dir: Path,
    samples: Path,
    files: Path,
    report_json: Path,
    attestation: dict,
) -> tuple[Path, Path, Path]:
    """
    Temporary shim until fairy_core.export.build_bundle is available.
    - Writes manifest.json (sha256, size, relpath) for key files
    - Writes provenance.json (who/when/version/inputs)
    - Creates bundle.zip containing the export_dir contents
    """
    manifest_items = []

    def _add(p: Path):
        rel = p.relative_to(export_dir).as_posix()
        manifest_items.append(
            {
                "path": rel,
                "sha256": _sha256_of_file(p),
                "bytes": p.stat().st_size,
            }
        )

    # Write manifest.json
    manifest_path = export_dir / "manifest.json"
    # Include canonical files present in export_dir
    for candidate in ["samples.tsv", "files.tsv", "report", "report.md"]:
        pc = export_dir / candidate
        if pc.exists():
            _add(pc)
    _write_json(manifest_path, manifest_items)

    # Write provenance.json
    prov = {
        "created_at_utc": _now_utc_iso(),
        # old key for compatibility
        "fairy_version": (
            attestation.get("fairy_core_version")
            or attestation.get("fairy_version")
            or FAIRY_VERSION
        ),
        # NEW canonical fields
        "fairy_core_version": (
            attestation.get("fairy_core_version")
            or attestation.get("core_version")
            or FAIRY_VERSION
        ),
        "rulepack_name": (
            attestation.get("rulepack_name") or (attestation.get("rulepack") or {}).get("id")
        ),
        "rulepack_version": (
            attestation.get("rulepack_version")
            or (attestation.get("rulepack") or {}).get("version")
        ),
        "rulepack_source_path": (
            attestation.get("rulepack_source_path")
            or (attestation.get("rulepack") or {}).get("path")
        ),
        "inputs": [
            {
                "name": "samples",
                "path": samples.name,
                "sha256": _sha256_of_file(samples),
                "bytes": samples.stat().st_size,
            },
            {
                "name": "files",
                "path": files.name,
                "sha256": _sha256_of_file(files),
                "bytes": files.stat().st_size,
            },
        ],
        "environment": {"cwd": os.getcwd()},
        "report_json": report_json.name,
    }
    provenance_path = export_dir / "provenance.json"
    _write_json(provenance_path, prov)

    # Create bundle.zip
    # Make a temp folder name to avoid zipping the zip itself on re-runs
    zip_base = export_dir.parent / f"{export_dir.name}_bundle"
    zip_path_str = shutil.make_archive(str(zip_base), "zip", root_dir=export_dir)
    zip_path = Path(zip_path_str)

    return zip_path, manifest_path, provenance_path


def export_submission(
    *,
    project_dir: Path,
    rulepack: Path,
    samples: Path,
    files: Path,
    fairy_version: str = FAIRY_VERSION,
) -> ExportResult:
    """
    One-call export for the UI:
      - creates timestamped export dir
      - runs preflight and writes report + report.md
      - copies samples/files into export dir (so the ZIP is self-contained)
      - builds manifest/provenance and zip (shim)
    """
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    export_dir = (project_dir / "exports" / ts).resolve()
    export_dir.mkdir(parents=True, exist_ok=True)

    # 1) run preflight into export_dir/report (+ .md)
    report_path, report_md_path, att = run_preflight_and_write(
        rulepack=rulepack,
        samples=samples,
        files=files,
        out_stem=export_dir / "report",
        fairy_version=fairy_version,
    )
    # Check submission_ready from returned attestation dict
    if not att.get("submission_ready", False):
        raise RuntimeError("Export requested while submission_ready == False")

    # 2) ensure inputs are copied next to the report so bundle is complete
    # (If you prefer symlinks, adjust accordingly)
    dst_samples = export_dir / "samples.tsv"
    dst_files = export_dir / "files.tsv"
    shutil.copy2(samples, dst_samples)
    shutil.copy2(files, dst_files)

    # 3) build shim bundle: manifest.json, provenance.json, bundle.zip
    zip_path, manifest_path, provenance_path = _shim_build_bundle(
        export_dir=export_dir,
        samples=dst_samples,
        files=dst_files,
        report_json=report_path,
        attestation=att,
    )

    return ExportResult(
        export_dir=export_dir,
        zip_path=zip_path,
        manifest_path=manifest_path,
        provenance_path=provenance_path,
        report_path=report_path,
        report_md_path=report_md_path,
    )
