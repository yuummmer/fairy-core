from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from hashlib import sha256
from ..core.services.report_writer import write_report, _now_utc_iso
from ..core.services.validator import validate_csv
from ..core.validators import generic, rna
from typing import Optional


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
        help= "Print engine + rulepack version and exit.",
    )

    sub = p.add_subparsers(dest="command", metavar="<command>")

    #validate
    v = sub.add_parser(
        "validate",
        help="Validate a CSV and emit a report.",
        description="Validate a CSV and emit JSON/Markdown reports.",
    )
    v.add_argument("input", help="CSV file to validate (e.g., demos/PASS_minimal_rnaseq/metadata.csv)")
    v.add_argument(
        "--out", 
        default="project_dir/reports",
        help="Output directory if using legacy JSON writer (default: project_dir/reports).",
    )
    v.add_argument(
        "--report-json",
        type=Path,
        default=None,
        metavar="Path",
        help="Write machine-readable JSON report to PATH (bypass legacy out-dir writer).",
    )
    v.add_argument(
        "--report-md",
        type=Path,
        default=None,
        metavar="PATH",
        help="Write human-readable Markdown summary to PATH.",
    )
    v.add_argument(
        "--rulepack",
        type=Path,
        default=None,
        help="Optional rulepack file/folder (reserved for future use).",
    )
    v.add_argument(
        "--kind",
        default="rna",
        help="Schema kind: rna | generic | dna | ... (default:rna).",
    )

    return p

def _version_text(rulepack: Path | None) -> str:
    #Customize if/when you add metadata to rulepacks
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
                f"No CSV file found in directory {p}."
                "Expected something like metadata.csv."
            )
        names = ", ".join(c.name for c in csvs)
        raise FileNotFoundError(
            f"Multiple CSVs found in {p}: {names}."
            "Please specify which file you want."
        )
    raise FileNotFoundError(f"{p} is not a file or directory")

def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = _build_parser()
    args = parser.parse_args(argv)

    # top-level --version
    if args.version and (args.command is None): 
        print(_version_text(None))
        return 0

    if args.command == "validate":
        csv_path = _resolve_input_path(Path(args.input))
        payload, _ = _build_payload(csv_path, kind=getattr(args, "kind", "rna"))

        wrote_any = False

        # new path: explicit file targets
        if args.report_json:
            args.report_json.parent.mkdir(parents=True, exist_ok=True)
            # Use my JSON writer if it accepts a file path, otherwise dump payload directly
            # the existing write_report writes to a directory, so here we dump directly
            args.report_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
            wrote_any = True

        if args.report_md:
            _emit_markdown(args.report_md, payload)
            wrote_any = True

        #legacy path: existing directory-based writer
        if not wrote_any:
            path = write_report(
                out_dir=args.out,
                filename=csv_path.name,
                sha256=payload["dataset_id"]["sha256"],
                meta = {
                    "n_rows": payload["summary"]["n_rows"],
                    "n_cols": payload["summary"]["n_cols"],
                    "fields_validated": payload["summary"]["fields_validated"],
                    "warnings": payload["warnings"],
                },
                rulepacks=[],
                provenance={"license": None, "source_url": None, "notes": None},
            )
            print(f"Wrote {path}")
        
        # Exit code: 0 for pass/warn, 1 for fail(adjust if status is added later)
        # Currently payload has warnings but no overall status; treat warnings as non-fatal:
        return 0

    # no command -> help
    parser.print_help()
    return 2

def demo_alias_main() -> int:
    """Deprecated alias for 'fairy-demo' (old interface)."""
    print("⚠️  `fairy-demo` is deprecated. Use `fairy validate <csv>` instead.",
          file=sys.stderr,
    )
    # For backward compatibility, interupt old flags and forward:
    # old: --input, --out, --dry-run, --kind
    # We'll map to: fairy validate <input> [--report-json -] or legacy writer.
    p = argparse.ArgumentParser(add_help = False)
    p.add_argument("--input", required=True, help="CSV file to summarize")
    p.add_argument("--out", default="project_dir/reports", help="Output directory for report_v0.json")
    p.add_argument("--dry-run", action= "store_true", help="Print JSON to stdout instead of writing")
    p.add_argument("--kind", default ="rna", help="schema kind: rna | generic | dna | ...")
    old = p.parse_args(sys.argv[1:])

    #Resolve what the user gave us:
    # - if it's a file, use it
    # - if it's a folder with exactly one CSV, use the CSV
    csv_path = _resolve_input_path(Path(old.input))

    if old.dry_run:
        # Build in-memory payload and pretty-print instead of writing to disk
        payload, _ = _build_payload(csv_path, kind = old.kind)
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    
    #Legacy writer path
    return main([
        "validate",
        str(csv_path),
        "--out", old.out,
        "--kind", old.kind
    ])

if __name__ == "__main__":
    raise SystemExit(main())
