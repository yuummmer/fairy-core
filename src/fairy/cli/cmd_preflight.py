from __future__ import annotations

import json
from pathlib import Path

from ..core.services.manifest import build_manifest_v1
from ..core.services.provenance import sha256_file
from ..core.services.validator import run_rulepack
from .common import ParamsFileError, load_params_file
from .output_md import emit_preflight_markdown

# Pull FAIRy version text if you want to embed it later; keep simple for now
try:
    from fairy import __version__ as FAIRY_VERSION
except Exception:
    FAIRY_VERSION = "0.1.0"


def add_subparser(sub):
    pf = sub.add_parser(
        "preflight",
        help="Run FAIRy rulepack on GEO-style TSVs and emit attestation + findings.",
        description=("Pre-submission check for GEO bulk RNA-seq."),
    )
    pf.add_argument("--rulepack", type=Path, required=True)
    pf.add_argument("--samples", type=Path, required=True)
    pf.add_argument("--files", type=Path, required=True)

    out_group = pf.add_mutually_exclusive_group(required=True)
    out_group.add_argument(
        "--out", type=Path, help="(legacy) Path to write the preflight JSON report."
    )
    out_group.add_argument(
        "--out-dir",
        dest="out_dir",
        type=Path,
        help="Output directory for handoff-ready artifacts (report, manifest, markdown, etc.).",
    )

    pf.add_argument("--fairy-version", default=FAIRY_VERSION)
    pf.add_argument(
        "--param-file",
        dest="param_file",
        type=Path,
        metavar="PATH",
        help="Path to a YAML file with tunable parameters injected into ctx['params']",
    )
    pf.set_defaults(func=main)


def _load_last_codes(cache_path: Path) -> set[str] | None:
    if not cache_path.exists():
        return None
    try:
        raw = json.loads(cache_path.read_text(encoding="utf-8"))
        return set(str(c) for c in raw.get("codes", []))
    except Exception:
        return None


def _save_last_codes(cache_path: Path, codes: set[str]) -> None:
    payload = {"codes": sorted(codes)}
    cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _resolve_output_paths(args) -> tuple[Path, Path, Path, Path, Path]:
    """
    Returns (report_json_path, report_md_path, manifest_path, cache_path, inputs_manifest_path).
    - Legacy mode: args.out is JSON file path.
    - Out-dir mode: args.out_dir is a directory; fixed filenames are used.
    """
    out_dir = getattr(args, "out_dir", None)
    if out_dir:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        report_path = out_dir / "preflight_report.json"
        md_path = out_dir / "preflight_report.md"
        manifest_path = out_dir / "manifest.json"
        cache_path = out_dir / ".fairy_last_run.json"
        inputs_manifest_path = out_dir / "artifacts" / "inputs_manifest.json"
        return report_path, md_path, manifest_path, cache_path, inputs_manifest_path

    # legacy: args.out is a file path
    report_path = Path(args.out)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    md_path = report_path.with_suffix(".md")
    manifest_path = report_path.parent / "manifest.json"
    cache_path = report_path.parent / ".fairy_last_run.json"
    inputs_manifest_path = report_path.parent / "artifacts" / "inputs_manifest.json"
    return report_path, md_path, manifest_path, cache_path, inputs_manifest_path


def _emit_inputs_manifest(path: Path, report: dict) -> None:
    """
    Emits minimal inputs manifest derived from report ['metadata']['inputs']g,
    """
    md = report.get("metadata") or {}
    inputs = md.get("inputs") or {}
    samples = inputs.get("samples") or {}
    files_info = inputs.get("files") or {}

    payload = {
        "schema_version": "inputs-manifest/v0",
        "inputs": [
            {
                "name": "samples",
                "path": samples.get("path"),
                "sha256": samples.get("sha256"),
            },
            {
                "name": "files",
                "path": files_info.get("path"),
                "sha256": files_info.get("sha256"),
            },
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )


def main(args) -> int:
    # tolerate missing attributes from test dummy args
    param_file = getattr(args, "param_file", None)

    # load params file if provided
    try:
        params = load_params_file(str(param_file) if param_file else None)
    except ParamsFileError as e:
        print(str(e))
        return 2

    report = run_rulepack(
        rulepack_path=args.rulepack,
        samples_path=args.samples,
        files_path=args.files,
        fairy_version=args.fairy_version,
        params=params,
    )
    report_path, md_path, manifest_path, cache_path, inputs_manifest_path = _resolve_output_paths(
        args
    )

    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    # Extract data from new v1 structure
    metadata = report.get("metadata") or {}
    summary = report.get("summary") or {}
    results = report.get("results") or []

    # Rulepack meta
    rulepack_meta = metadata.get("rulepack") or {}
    rp_id = rulepack_meta.get("id") or "UNKNOWN_RULEPACK"
    rp_version = rulepack_meta.get("version") or "0.0.0"

    # For backward compatibility during migration, also check _legacy
    legacy_att = report.get("_legacy", {}).get("attestation")

    # Extract rule codes from results (rule field)
    curr_codes = {r["rule"] for r in results}
    prior_codes = _load_last_codes(cache_path)
    resolved_codes = sorted((prior_codes or set()) - curr_codes) if prior_codes else []
    _save_last_codes(cache_path, curr_codes)

    # Pass new structure to markdown emitter (it will handle the migration)
    emit_preflight_markdown(md_path, report, resolved_codes, prior_codes)

    _emit_inputs_manifest(inputs_manifest_path, report)

    files_list = [
        {
            "path": report_path.name,
            "sha256": sha256_file(report_path, newline_stable=True),
            # role inferred
        },
        {
            "path": md_path.name,
            "sha256": sha256_file(md_path, newline_stable=True),
            # role inferred
        },
        {
            "path": str(inputs_manifest_path.relative_to(manifest_path.parent)),
            "sha256": sha256_file(inputs_manifest_path, newline_stable=True),
            # role inferred
        },
    ]

    manifest = build_manifest_v1(
        dataset_id=report["dataset_id"],
        created_at_utc=report["generated_at"],
        fairy_version=report.get("engine", {}).get("fairy_core_version", args.fairy_version),
        rulepack_id=rp_id,
        rulepack_version=rp_version,
        source_report=report_path.name,
        files=files_list,
    )

    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    # Console summary (trimmed)
    print("")
    print("=== FAIRy Preflight ===")

    # FAIRy version from legacy attestation if available, otherwise use default
    fairy_version = (
        legacy_att.get("fairy_version", args.fairy_version) if legacy_att else args.fairy_version
    )

    print(f"Rulepack:         {rp_id}@{rp_version}")
    print(f"FAIRy version:    {fairy_version}")
    print(f"Generated at:     {report['generated_at']}")
    print(f"Dataset ID:       {report['dataset_id']}")

    # Extract fail/warn codes from results
    fail_codes = sorted({r["rule"] for r in results if r["level"] == "fail"})
    warn_codes = sorted({r["rule"] for r in results if r["level"] == "warn"})

    # Get counts from summary
    by_level = summary.get("by_level", {})
    fail_count = by_level.get("fail", 0)
    warn_count = by_level.get("warn", 0)
    submission_ready = fail_count == 0

    print(f"FAIL findings:    {fail_count} {fail_codes}")
    print(f"WARN findings:    {warn_count} {warn_codes}")
    print(f"submission_ready: {submission_ready}")
    print(f"Report JSON:      {report_path}")
    print("")

    # Extract inputs from metadata.inputs
    inputs = metadata.get("inputs", {})
    samples_info = inputs.get("samples", {})
    files_info = inputs.get("files", {})

    def _fmt_file_info(label: str, meta: dict) -> str:
        if not meta:
            return f"{label}: (no input metadata)"
        sha = meta.get("sha256", "?")
        rows = meta.get("n_rows", "?")
        cols = meta.get("n_cols", "?")
        path = meta.get("path", "?")
        return f"{label} sha256: {sha}\n  path: {path}\n  rows:{rows} cols:{cols}"

    print("Input provenance:")
    print(_fmt_file_info("samples.tsv", samples_info))
    print(_fmt_file_info("files.tsv", files_info))
    print("")

    print("Resolved since last run:")
    if prior_codes is None:
        print("  (no baseline from prior run)")
    elif not resolved_codes:
        print("  (no previously-reported issues resolved)")
    else:
        for code in resolved_codes:
            print(f"  ✔ {code}")
    print("")

    return 0 if submission_ready else 1
