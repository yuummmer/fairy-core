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
    out_json = getattr(args, "out_json", None) or getattr(args, "out", None)
    out_md = getattr(args, "out_md", None)

    # Optional CLI fields for the "real" path
    rulepack = getattr(args, "rulepack", None)
    samples = getattr(args, "samples", None)
    files = getattr(args, "files", None)
    fairy_ver = getattr(args, "fairy_version", FAIRY_VERSION)

    # load params file if provided
    try:
        params = load_params_file(str(param_file) if param_file else None)
    except ParamsFileError as e:
        print(str(e))
        return 2

    # Two modes:
    #  - Real CLI mode (all three paths present)
    #  - Unit-test / lightweight mode (no paths; tests monkeypatch run_rulepack(**kwargs))
    if rulepack and samples and files:
        report = run_rulepack(
            rulepack_path=Path(rulepack).resolve(),
            samples_path=Path(samples).resolve(),
            files_path=Path(files).resolve(),
            fairy_version=fairy_ver,
            params=params,
        )
    else:
        # let tests call our run_rulepack(**kwargs) monkeypatch
        report = run_rulepack(params=params)

    # Write JSON if requested (unit test only sets out_json)
    if out_json:
        p = Path(out_json)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        # ALSO emit a .md with the same stem (unit test expects this)
        md_path = p.with_suffix(".md")
        att = report.get("attestation", {})
        cache_path = md_path.parent / ".fairy_last_run.json"
        curr_codes = {f["code"] for f in report.get("findings", [])}
        prior_codes = _load_last_codes(cache_path)
        resolved_codes = sorted((prior_codes or set()) - curr_codes) if prior_codes else []
        _save_last_codes(cache_path, curr_codes)
        emit_preflight_markdown(md_path, att, report, resolved_codes, prior_codes)

    # Only emit MD when explicitly asked
    if out_md:
        md_path = Path(out_md)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        # keep your existing MD rendering behavior
        att = report.get("attestation", {})
        cache_path = md_path.parent / ".fairy_last_run.json"
        curr_codes = {f["code"] for f in report.get("findings", [])}
        prior_codes = _load_last_codes(cache_path)
        resolved_codes = sorted((prior_codes or set()) - curr_codes) if prior_codes else []
        _save_last_codes(cache_path, curr_codes)
        emit_preflight_markdown(md_path, att, report, resolved_codes, prior_codes)

    # Exit code: 1 if any FAILs (test checks this pattern)
    att = report.get("attestation", {})
    fail_count = att.get("fail_count", 0)
    return 1 if fail_count and int(fail_count) > 0 else 0
