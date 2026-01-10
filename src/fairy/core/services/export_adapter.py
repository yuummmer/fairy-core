# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025 Jennifer Slotnick

# fairy/core/services/export_adapter.py
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from ...cli.output_md import emit_preflight_markdown  # reuse your MD emitter
from ...cli.run import FAIRY_VERSION
from ..services.manifest import build_manifest_v1
from ..services.provenance import sha256_file
from ..services.validator import run_rulepack


@dataclass
class ExportResult:
    export_dir: Path
    zip_path: Path
    manifest_path: Path
    report_path: Path
    report_md_path: Path


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
) -> tuple[Path, Path, dict[str, Any]]:
    """
    Runs validator, writes JSON and Markdown, returns (json_path, md_path, report_dict).
    """
    report = run_rulepack(
        rulepack_path=rulepack.resolve(),
        samples_path=samples.resolve(),
        files_path=files.resolve(),
        fairy_version=fairy_version,
        params={},
    )

    # JSON
    json_path = out_stem
    _write_json(json_path, report)

    # Markdown
    md_path = out_stem.with_suffix(".md")
    emit_preflight_markdown(
        md_path=md_path,
        report=report,
        resolved_codes=[],  # resolved diff is optional for export demo
        prior_codes=set(),  # pass empty set so emitter renders the block
    )

    return json_path, md_path, report


def _shim_build_bundle(
    *,
    export_dir: Path,
    samples: Path,
    files: Path,
    report_json: Path,
    report_md: Path,
    report: dict[str, Any],
) -> tuple[Path, Path]:
    """
    Temporary shim until fairy_core.export.build_bundle is available.
    - Writes manifest.json (sha256, size, relpath) for key files
    - Creates bundle.zip containing the export_dir contents
    """

    manifest_path = export_dir / "manifest.json"
    files_list: list[dict[str, object]] = []

    def _add(rel_name: str, abs_path: Path) -> None:
        files_list.append(
            {
                "path": rel_name,
                "sha256": sha256_file(abs_path, newline_stable=True),
                "bytes": abs_path.stat().st_size,
                # role inferred
            }
        )

    # Canonical artifacts in the bundle
    if samples.exists():
        _add(samples.name, samples)
    if files.exists():
        _add(files.name, files)
    if report_json.exists():
        _add(report_json.name, report_json)
    if report_md.exists():
        _add(report_md.name, report_md)

    # Rulepack info from report V1
    rulepack_meta = (report.get("metadata") or {}).get("rulepack") or {}
    rp_id = rulepack_meta.get("id") or "UNKNOWN_RULEPACK"
    rp_version = rulepack_meta.get("version") or "0.0.0"
    rp_sha256 = rulepack_meta.get("sha256")

    fairy_core_version = (report.get("engine") or {}).get("fairy_core_version") or FAIRY_VERSION

    manifest = build_manifest_v1(
        dataset_id=report["dataset_id"],
        created_at_utc=report["generated_at"],
        fairy_version=fairy_core_version,
        rulepack_id=rp_id,
        rulepack_version=rp_version,
        source_report=report_json.name,
        files=files_list,
    )

    # Optional: include rulepack sha256 if present
    if rp_sha256:
        manifest["rulepack"]["sha256"] = rp_sha256

    # Optional: provenance block that replaces provenance.json
    manifest["provenance"] = {
        "fairy_core_version": fairy_core_version,
        "inputs": [
            {
                "name": "samples",
                "path": samples.name,
                "sha256": sha256_file(samples, newline_stable=True),
                "bytes": samples.stat().st_size,
            },
            {
                "name": "files",
                "path": files.name,
                "sha256": sha256_file(files, newline_stable=True),
                "bytes": files.stat().st_size,
            },
        ],
    }

    _write_json(manifest_path, manifest)

    # Create bundle.zip
    # Make a temp folder name to avoid zipping the zip itself on re-runs
    zip_base = export_dir.parent / f"{export_dir.name}_bundle"
    zip_path_str = shutil.make_archive(str(zip_base), "zip", root_dir=export_dir)
    zip_path = Path(zip_path_str)

    return (
        zip_path,
        manifest_path,
    )


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
      - builds manifest(inclu provenance block) and zip
    """
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    export_dir = (project_dir / "exports" / ts).resolve()
    export_dir.mkdir(parents=True, exist_ok=True)

    # 1) run preflight into export_dir/report (+ .md)
    report_path, report_md_path, report = run_preflight_and_write(
        rulepack=rulepack,
        samples=samples,
        files=files,
        out_stem=export_dir / "report.json",
        fairy_version=fairy_version,
    )
    # submission_ready derived from v1 summary
    by_level = (report.get("summary") or {}).get("by_level") or {}
    submission_ready = (by_level.get("fail", 0) or 0) == 0
    if not submission_ready:
        raise RuntimeError(
            "Export requested while submission_ready == False (fail findings present)"
        )

    # 2) copy inputs next to report so bundle is complete
    dst_samples = export_dir / "samples.tsv"
    dst_files = export_dir / "files.tsv"
    shutil.copy2(samples, dst_samples)
    shutil.copy2(files, dst_files)

    zip_path, manifest_path = _shim_build_bundle(
        export_dir=export_dir,
        samples=dst_samples,
        files=dst_files,
        report_json=report_path,
        report_md=report_md_path,
        report=report,
    )

    return ExportResult(
        export_dir=export_dir,
        zip_path=zip_path,
        manifest_path=manifest_path,
        report_path=report_path,
        report_md_path=report_md_path,
    )
