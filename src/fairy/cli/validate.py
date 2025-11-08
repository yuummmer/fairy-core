# src/fairy/cli/validate.py
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml  # pip install pyyaml
except Exception:
    yaml = None

from fairy.validation.rulepack_runner import run_rulepack, write_markdown


def main(argv=None) -> int:
    p = argparse.ArgumentParser("fairy validate")
    p.add_argument("input", help="CSV file or folder containing CSVs")
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
    if rp_path.suffix.lower() in (".yml", ".yaml"):
        rulepack = yaml.safe_load(text)
    else:
        rulepack = json.loads(text)

    inp = Path(args.input)
    if inp.is_dir():
        inputs = sorted([p for p in inp.glob("*.csv") if p.is_file()], key=lambda x: x.name)
    elif inp.is_file():
        inputs = [inp]
    else:
        print(f"ERROR: input not found: {inp}", file=sys.stderr)
        return 2

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    report = run_rulepack(inputs, rulepack, rp_path, now)

    if args.report_json:
        out = Path(args.report_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    if args.report_md:
        outm = Path(args.report_md)
        outm.parent.mkdir(parents=True, exist_ok=True)
        outm.write_text(write_markdown(report), encoding="utf-8")

    return 1 if report.get("summary", {}).get("fail", 0) > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
