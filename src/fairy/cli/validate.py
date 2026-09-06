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


# Resolve paths that tests pass relative to the repo root (pytest runs from a tmp dir)
def _repo_root() -> Path:
    # src/fairy/cli/validate.py -> .../src/fairy/cli -> repo root is parents[3]
    here = Path(__file__).resolve()
    candidate = here.parents[3]
    # extra safety: if someone moves files, walk up until we find a .git or pyproject
    for p in [candidate, *candidate.parents]:
        if (p / ".git").exists() or (p / "pyproject.toml").exists():
            return p
    return candidate  # fallback


def _resolve_path_like(p: Path) -> Path:
    if p.exists():
        return p
    alt = (_repo_root() / p).resolve()
    return alt if alt.exists() else p


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
        inputs[name] = _resolve_path_like(p)
    return inputs


def main(argv=None) -> int:
    p = argparse.ArgumentParser("fairy validate")
    # Legacy positional input retained (file OR folder)
    p.add_argument("input", nargs="?", help="CSV file or folder containing CSVs (legacy)")
    p.add_argument(
        "--package-root",
        help="Explicit package directory for rulepacks with package.rules.",
    )
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

    rp_path = _resolve_path_like(Path(args.rulepack))
    if not rp_path.exists():
        print(f"ERROR: rulepack not found: {rp_path}", file=sys.stderr)
        return 2

    text = rp_path.read_text(encoding="utf-8")
    rulepack = (
        yaml.safe_load(text) if rp_path.suffix.lower() in (".yml", ".yaml") else json.loads(text)
    )

    # Build inputs mapping and resolve optional package subject
    named_inputs = _parse_inputs(args.inputs)
    inputs_map: dict[str, Path]
    package_root: Path | None = None

    package_cfg = (rulepack.get("package") or {}) if isinstance(rulepack, dict) else {}
    package_rules = package_cfg.get("rules", []) or []
    has_package_rules = bool(package_rules)
    
    if has_package_rules:
        # Package-aware rulepacks require an explicit directory subject.
        positional = _resolve_path_like(Path(args.input)) if args.input else None
        explicit_package_root = (
            _resolve_path_like(Path(args.package_root).expanduser())
            if args.package_root
            else None
        )

        if explicit_package_root is not None:
            if not explicit_package_root.exists():
                print(
                    f"ERROR: package directory not found: {explicit_package_root}",
                    file=sys.stderr,
                )
                return 2

            if not explicit_package_root.is_dir():
                print(
                    f"ERROR: package subject is not a directory: {explicit_package_root}",
                    file=sys.stderr,
                )
                return 2

            if positional is not None and positional.is_dir():
                if positional.resolve() != explicit_package_root.resolve():
                    print(
                        "ERROR: positional package directory and --package-root "
                        "refer to different directories",
                        file=sys.stderr,
                    )
                    return 2

            package_root = explicit_package_root

        elif positional is not None and positional.is_dir():
            package_root = positional

        else:
            print(
                "ERROR: this rulepack requires a package directory. "
                "Provide a positional directory or --package-root DIR.",
                file=sys.stderr,
            )
            return 2

        # In package mode, tables are explicit.
        inputs_map = named_inputs

    else:
        if args.package_root:
            print(
                "ERROR: --package-root can only be used with rulepacks containing package.rules",
                file=sys.stderr,
            )
            return 2

        if named_inputs:
            inputs_map = named_inputs
        else:
            # Legacy positional mode
            if not args.input:
                print(
                    "ERROR: provide INPUT or at least one --inputs name=path",
                    file=sys.stderr,
                )
                return 2

            inp = _resolve_path_like(Path(args.input))

            if inp.is_dir():
                csvs = sorted(
                    [p for p in inp.glob("*.csv") if p.is_file()],
                    key=lambda x: x.name,
                )

                if not csvs:
                    print(
                        f"ERROR: no CSV files found in folder: {inp}",
                        file=sys.stderr,
                    )
                    return 2

                inputs_map = OrderedDict((p.stem, p) for p in csvs)

            elif inp.is_file():
                inputs_map = {"default": inp}

            else:
                print(f"ERROR: input not found: {inp}", file=sys.stderr)
                return 2

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    report = run_rulepack(
        inputs_map,
        rulepack,
        rp_path,
        now,
        package_root=package_root,
    )

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
        help="Engine / CI mode. Run checks and write reports (PASS/WARN/FAIL).",
        description=(
            "Use a single positional INPUT (legacy) or repeat\n--inputs name=path for multi-input."
        ),
    )
    p.add_argument("input", nargs="?", help="CSV file or folder containing CSVs (legacy)")
    p.add_argument(
        "--package-root",
        help="Explicit package directory for rulepacks with package.rules",
    )
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
