from __future__ import annotations

import json
from pathlib import Path

from ..core.services.validator import run_rulepack
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
    report = run_rulepack(
        rulepack_path=args.rulepack.resolve(),
        samples_path=args.samples.resolve(),
        files_path=args.files.resolve(),
        fairy_version=args.fairy_version,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    att = report["attestation"]

    cache_path = args.out.parent / ".fairy_last_run.json"
    curr_codes = {f["code"] for f in report["findings"]}
    prior_codes = _load_last_codes(cache_path)
    resolved_codes = sorted((prior_codes or set()) - curr_codes) if prior_codes else []
    _save_last_codes(cache_path, curr_codes)

    md_path = args.out.with_suffix(".md")
    emit_preflight_markdown(md_path, att, report, resolved_codes, prior_codes)

    # Console summary (trimmed)
    print("")
    print("=== FAIRy Preflight ===")
    print(f"Rulepack:         {att['rulepack_id']}@{att['rulepack_version']}")
    print(f"FAIRy version:    {att['fairy_version']}")
    print(f"Run at (UTC):     {att['run_at_utc']}")

    fail_codes = sorted({f["code"] for f in report["findings"] if f["severity"] == "FAIL"})
    warn_codes = sorted({f["code"] for f in report["findings"] if f["severity"] == "WARN"})

    print(f"FAIL findings:    {att['fail_count']} {fail_codes}")
    print(f"WARN findings:    {att['warn_count']} {warn_codes}")
    print(f"submission_ready: {att['submission_ready']}")
    print(f"Report JSON:      {args.out}")
    print("")

    inputs = att.get("inputs", {})
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

    return 0 if att["submission_ready"] else 1
