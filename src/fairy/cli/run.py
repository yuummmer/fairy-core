from __future__ import annotations

import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path

from ..core.services.report_writer import _now_utc_iso
from ..core.services.validator import run_rulepack
from ..core.validation_api import validate_csv

try:
    from fairy import __version__ as FAIRY_VERSION
except Exception:
    FAIRY_VERSION = "0.1.0"


def sha256_bytes(b: bytes) -> str:
    h = sha256()
    h.update(b)
    return h.hexdigest()


def _emit_markdown(md_path: Path, payload: dict) -> None:
    """Very small markdown summary until template improves."""
    checks = payload.get("warnings", [])
    lines = [
        "# FAIRy Validation Report",
        "",
        f"**Run at:** {payload.get('run_at', '')}",
        f"**File:** {payload.get('dataset_id', {}).get('filename', '')}",
        f"**SHA256:** {payload.get('dataset_id', {}).get('sha256', '')}",
        "",
        "## Summary",
        f"- Rows: {payload.get('summary', {}).get('n_rows', '?')}",
        f"- Cols: {payload.get('summary', {}).get('n_cols', '?')}",
        f"- Fields validated: {len(payload.get('summary', {}).get('fields_validated', []))}",
        "",
        "## Warnings",
    ]
    if not checks:
        lines.append("- None")
    else:
        for w in checks:
            lines.append(f"- {w.get('code', 'warn')} - {w.get('message', '')}")
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines), encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="fairy",
        description="FAIRy - validate a CSV/dataset locally and write a report.",
    )
    p.add_argument(
        "--version",
        action="store_true",
        help="Print engine + rulepack version and exit.",
    )

    sub = p.add_subparsers(dest="command", metavar="<command>")

    # validate (delegate to the new multi-input CLI)
    from . import validate as validate_cmd

    validate_cmd.add_subparser(sub)  # exposes --inputs etc.

    # preflight
    pf = sub.add_parser(
        "preflight",
        help="Run FAIRy rulepack on GEO-style TSVs and emit attestation + findings.",
        description=(
            "Pre-submission check for GEO bulk RNA-seq. "
            "Reads samples.tsv and files.tsv, applies the rulepack, "
            "and emits a FAIRy report with submission_ready."
        ),
    )
    pf.add_argument(
        "--rulepack",
        type=Path,
        required=True,
        help="Path to rulepack JSON (e.g. fairy/rulepacks/GEO-SEQ-BULK/v0_1_0.json)",
    )
    pf.add_argument(
        "--samples",
        type=Path,
        required=True,
        help="Path to samples.tsv (tab-delimited sample metadata)",
    )
    pf.add_argument(
        "--files",
        type=Path,
        required=True,
        help="Path to files.tsv (tab-delimited file manifest)",
    )
    pf.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Write FAIRy attestation+findings JSON to this path (e.g. out/report.json)",
    )
    pf.add_argument(
        "--fairy-version",
        default=FAIRY_VERSION,
        help=(
            "Version string to embed in attestation.fairy_version "
            "(default: current FAIRy version)"
        ),
    )

    return p


def _version_text(rulepack: Path | None) -> str:
    # Customize if/when you add metadata to rulepacks
    rp = "default" if not rulepack else rulepack.name
    return f"fairy {FAIRY_VERSION}\nrulepack: {rp}"


def _build_payload(csv_path: Path, kind: str) -> tuple[dict, bytes]:
    data_bytes = csv_path.read_bytes()
    meta_obj = validate_csv(str(csv_path), kind=kind)
    meta = {
        "n_rows": meta_obj.n_rows,
        "n_cols": meta_obj.n_cols,
        "fields_validated": meta_obj.fields_validated,
        "warnings": [w.__dict__ for w in meta_obj.warnings],
    }
    payload = {
        "version": FAIRY_VERSION,
        "run_at": _now_utc_iso(),
        "dataset_id": {"filename": csv_path.name, "sha256": sha256_bytes(data_bytes)},
        "summary": {
            "n_rows": meta["n_rows"],
            "n_cols": meta["n_cols"],
            "fields_validated": sorted(meta["fields_validated"]),
        },
        "warnings": meta["warnings"],
        "rulepacks": [],
        "provenance": {"license": None, "source_url": None, "notes": None},
        "scores": {"preflight": 0.0},
    }
    return payload, data_bytes


def _resolve_input_path(p: Path) -> Path:
    """
    Accept either:
    - a direct CSV file, OR
    - a dataset directory that contains exactly one CSV.
    """
    if p.is_file():
        return p

    if p.is_dir():
        csvs = list(p.glob("*.csv"))
        if len(csvs) == 1:
            return csvs[0]
        if len(csvs) == 0:
            raise FileNotFoundError(
                f"No CSV file found in directory {p}." "Expected something like metadata.csv."
            )
        names = ", ".join(c.name for c in csvs)
        raise FileNotFoundError(
            f"Multiple CSVs found in {p}: {names}." "Please specify which file you want."
        )
    raise FileNotFoundError(f"{p} is not a file or directory")


def _load_last_codes(cache_path: Path) -> set[str] | None:
    """
    Read previously saved finding codes from last run.
    Returns a set of codes (e.g. {"CORE.ID.UNMATCHED_SAMPLE", ...})
    or None if no cache yet.
    """

    if not cache_path.exists():
        return None
    try:
        raw = json.loads(cache_path.read_text(encoding="utf-8"))
        # Expecting {"codes": ["AAA", "BBB", ...]}
        codes_list = raw.get("codes", [])
        # Defensive cast to set[str]
        return set(str(c) for c in codes_list)
    except Exception:
        # If cache is corrupt, just ignore it this run
        return None


def _save_last_codes(cache_path: Path, codes: set[str]) -> None:
    """
    Persist finding codes for next run's diff.
    Overwrites each run
    """
    payload = {"codes": sorted(codes)}
    cache_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# _emit_preflight_markdown is now in output_md.py - import it if needed
# Keeping this comment for reference, but we use output_md.emit_preflight_markdown now


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = _build_parser()
    args = parser.parse_args(argv)
    # each subparser sets func
    if hasattr(args, "func"):
        return args.func(args)

    # top-level --version (no subcommand)
    if args.version and (args.command is None):
        print(_version_text(None))
        return 0

    # 'preflight' subcommand (NEW: GEO-style submission check)
    if args.command == "preflight":
        # Run the high-level rulepack runner on samples.tsv/files.tsv
        report = run_rulepack(
            rulepack_path=args.rulepack.resolve(),
            samples_path=args.samples.resolve(),
            files_path=args.files.resolve(),
            fairy_version=args.fairy_version,
        )

        # Write machine-readable FAIRy report (v1 structure)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        # Use sort_keys=True for deterministic JSON output
        args.out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        # Extract data from new v1 structure
        metadata = report["metadata"]
        summary = report["summary"]
        results = report["results"]

        # For backward compatibility during migration, also check _legacy
        legacy_att = report.get("_legacy", {}).get("attestation")

        # where we cache last-run codes
        cache_path = args.out.parent / ".fairy_last_run.json"

        # Extract rule codes from results (rule field)
        curr_codes = {r["rule"] for r in results}

        # Load previous run's codes (if any)
        prior_codes = _load_last_codes(cache_path)

        # Compute "resolved" = codes that used to exist but are gone now
        resolved_codes: list[str] = []
        if prior_codes is not None:
            resolved_codes = sorted(prior_codes - curr_codes)

        # Save current codes for next run
        _save_last_codes(cache_path, curr_codes)

        # Emit curator-facing Markdown one-pager
        # Use the updated function from output_md.py
        from .output_md import emit_preflight_markdown

        md_path = args.out.with_suffix(".md")
        emit_preflight_markdown(
            md_path=md_path,
            report=report,
            resolved_codes=resolved_codes,
            prior_codes=prior_codes,
        )

        # === Pretty console summary for humans / screenshots / CI logs
        print("")
        print("=== FAIRy Preflight ===")

        # Extract rulepack info from metadata.rulepack
        rulepack_meta = metadata.get("rulepack", {})
        rulepack_id = rulepack_meta.get("id", "UNKNOWN_RULEPACK")
        rulepack_version = rulepack_meta.get("version", "0.0.0")

        # FAIRy version from legacy attestation if available, otherwise use default
        fairy_version = (
            legacy_att.get("fairy_version", args.fairy_version)
            if legacy_att
            else args.fairy_version
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
            return f"{label} sha256: {sha}\n" f"  path: {path}\n" f"  rows:{rows} cols:{cols}"

        print("Input provenance:")
        print(_fmt_file_info("samples.tsv", samples_info))
        print(_fmt_file_info("files.tsv", files_info))
        print("")

        # Show example result if available
        fail_results = [r for r in results if r["level"] == "fail"]
        if fail_results:
            r0 = fail_results[0]
            print("Example result:")
            print(f"  [{r0['level']}] {r0['rule']} (count: {r0['count']})")
            if r0.get("samples"):
                s0 = r0["samples"][0]
                location_parts = []
                if s0.get("row"):
                    location_parts.append(f"row {s0['row']}")
                if s0.get("column"):
                    location_parts.append(f"column '{s0['column']}'")
                if location_parts:
                    print(f"    location: {', '.join(location_parts)}")
                if s0.get("message"):
                    print(f"    message: {s0['message']}")
            print("")

        # Print resolved diff block
        print("Resolved since last run:")
        if prior_codes is None:
            # first run or cache missing/corrupt
            print("  (no baseline from prior run)")
        elif not resolved_codes:
            print("  (no previously-reported issues resolved)")
        else:
            for code in resolved_codes:
                print(f"  ✔ {code}")
        print("")

        # Exit code for automation / CI:
        # - submission_ready == False (at least one FAIL) -> exit 1
        # - otherwise 0
        exit_code = 0 if submission_ready else 1
        return exit_code

    # no command -> help
    parser.print_help()
    return 2


def demo_alias_main() -> int:
    """Deprecated alias for 'fairy-demo' (old interface)."""
    print(
        "⚠️  `fairy-demo` is deprecated. Use `fairy validate <csv>` instead.",
        file=sys.stderr,
    )
    # For backward compatibility, interupt old flags and forward:
    # old: --input, --out, --dry-run, --kind
    # We'll map to: fairy validate <input> [--report-json -] or legacy writer.
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--input", required=True, help="CSV file to summarize")
    p.add_argument(
        "--out",
        default="project_dir/reports",
        help="Output directory for report_v0.json",
    )
    p.add_argument("--dry-run", action="store_true", help="Print JSON to stdout instead of writing")
    p.add_argument("--kind", default="rna", help="schema kind: rna | generic | dna | ...")
    old = p.parse_args(sys.argv[1:])

    # Resolve what the user gave us:
    # - if it's a file, use it
    # - if it's a folder with exactly one CSV, use the CSV
    csv_path = _resolve_input_path(Path(old.input))

    if old.dry_run:
        # Build in-memory payload and pretty-print instead of writing to disk
        payload, _ = _build_payload(csv_path, kind=old.kind)
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    # Legacy writer path
    return main(["validate", str(csv_path), "--out", old.out, "--kind", old.kind])


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
