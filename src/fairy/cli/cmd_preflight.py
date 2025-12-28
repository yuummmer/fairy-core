from __future__ import annotations

import json
from pathlib import Path

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
    pf.add_argument("--out", type=Path, required=True)
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
    args.out.parent.mkdir(parents=True, exist_ok=True)
    # Use sort_keys=True for deterministic JSON output
    args.out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    # Extract data from new v1 structure
    metadata = report["metadata"]
    summary = report["summary"]
    results = report["results"]

    # For backward compatibility during migration, also check _legacy
    legacy_att = report.get("_legacy", {}).get("attestation")

    cache_path = args.out.parent / ".fairy_last_run.json"
    # Extract rule codes from results (rule field)
    curr_codes = {r["rule"] for r in results}
    prior_codes = _load_last_codes(cache_path)
    resolved_codes = sorted((prior_codes or set()) - curr_codes) if prior_codes else []
    _save_last_codes(cache_path, curr_codes)

    md_path = args.out.with_suffix(".md")
    # Pass new structure to markdown emitter (it will handle the migration)
    emit_preflight_markdown(md_path, report, resolved_codes, prior_codes)

    # Console summary (trimmed)
    print("")
    print("=== FAIRy Preflight ===")

    # Extract rulepack info from metadata.rulepack
    rulepack_meta = metadata.get("rulepack", {})
    rulepack_id = rulepack_meta.get("id") or rulepack_meta.get("name") or "UNKNOWN_RULEPACK"
    rulepack_version = rulepack_meta.get("version") or "0.0.0"

    # FAIRy version from legacy attestation if available, otherwise use default
    fairy_version = (
        legacy_att.get("fairy_version", args.fairy_version) if legacy_att else args.fairy_version
    )

    print(f"Rulepack:         {rulepack_id}@{rulepack_version}")
    print(f"FAIRy version:    {fairy_version}")
    print(f"Generated at:     {report['generated_at']}")

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
    print(f"Report JSON:      {args.out}")
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
