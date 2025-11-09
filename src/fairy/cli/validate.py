# src/fairy/cli/validate.py
from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml  # pip install pyyaml
except Exception:
    yaml = None

from fairy.validation.rulepack_runner import run_rulepack, write_markdown


def _parse_inputs(pairs: list[str]) -> dict[str, Path]:
    """Parse repeated --inputs name=path arguments into an ordered dict."""
    inputs: dict[str, Path] = OrderedDict()
    for raw in pairs:
        if "=" not in raw:
            print(f"ERROR: --inputs expects name=path, got: {raw}", file=sys.stderr)
            raise SystemExit(2)
        name, path = raw.split("=", 1)
        name = name.strip()
        p = Path(path).expanduser()
        if not name:
            print("ERROR: --inputs name cannot be empty", file=sys.stderr)
            raise SystemExit(2)
        inputs[name] = p
    return inputs


def main(argv=None) -> int:
    p = argparse.ArgumentParser("fairy validate")
    # Legacy positional input retained (file OR folder)
    p.add_argument("input", nargs="?", help="CSV file or folder containing CSVs (legacy)")
    # New: repeatable named inputs
    p.add_argument(
        "--inputs",
        action="append",
        default=[],
        metavar="name=path",
        help="Repeatable name=path pairs for multi-input "
        "(e.g., --inputs default=artworks.csv --inputs artists=artists.csv)",
    )
    p.add_argument("--rulepack", required=True, help="Path to YAML/JSON rulepack")
    p.add_argument("--report-json", help="Write JSON report to this path")
    p.add_argument("--report-md", help="Write Markdown report to this path")
    args = p.parse_args(argv)

    if yaml is None:
        print("ERROR: PyYAML is required (pip install pyyaml)", file=sys.stderr)
        return 2

    rp_path = Path(args.rulepack)
    if not rp_path.exists():
        print(f"ERROR: rulepack not found: {rp_path}", file=sys.stderr)
        return 2

    text = rp_path.read_text(encoding="utf-8")
    rulepack = (
        yaml.safe_load(text) if rp_path.suffix.lower() in (".yml", ".yaml") else json.loads(text)
    )

    # Build inputs mapping
    named_inputs = _parse_inputs(args.inputs)
    inputs_map: dict[str, Path]

    if named_inputs:
        # Multi-input mode (explicit)
        inputs_map = named_inputs
    else:
        # Legacy positional mode
        if not args.input:
            print("ERROR: provide INPUT or at least one --inputs name=path", file=sys.stderr)
            return 2
        inp = Path(args.input)
        if inp.is_dir():
            csvs = sorted([p for p in inp.glob("*.csv") if p.is_file()], key=lambda x: x.name)
            if not csvs:
                print(f"ERROR: no CSV files found in folder: {inp}", file=sys.stderr)
                return 2
            # name tables by stem: artist.csv -> 'artists'
            inputs_map = OrderedDict((p.stem, p) for p in csvs)
        elif inp.is_file():
            inputs_map = {"default": inp}
        else:
            print(f"ERROR: input not found: {inp}", file=sys.stderr)
            return 2

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    # NOTE: run_rulepack now expects a dict[str, Path] (name -> path)
    report = run_rulepack(inputs_map, rulepack, rp_path, now)

    if args.report_json:
        out = Path(args.report_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    if args.report_md:
        outm = Path(args.report_md)
        outm.parent.mkdir(parents=True, exist_ok=True)
        outm.write_text(write_markdown(report), encoding="utf-8")

    return 1 if report.get("summary", {}).get("fail", 0) > 0 else 0


def add_subparser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "validate",
        help="Validate dataset(s) against a rulepack",
        description=(
            "Use a single positional INPUT (legacy) or repeat\n"
            "--inputs name=path for multi-input."
        ),
    )
    p.add_argument("input", nargs="?", help="CSV file or folder containing CSVs (legacy)")
    p.add_argument(
        "--inputs",
        action="append",
        default=[],
        metavar="name=path",
        help=(
            "Repeatable name=path pairs (e.g., --inputs default=artworks.csv\n"
            "--inputs artists=artists.csv)"
        ),
    )
    p.add_argument("--rulepack", required=True, help="Path to YAML/JSON rulepack")
    p.add_argument("--report-json", help="Write JSON report to this path")
    p.add_argument("--report-md", help="Write Markdown report to this path")
    p.set_defaults(func=lambda _ns: main(None))


if __name__ == "__main__":
    raise SystemExit(main())
