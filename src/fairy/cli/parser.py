from __future__ import annotations

import argparse
from pathlib import Path

from . import validate as cmd_validate
from .cmd_preflight import add_subparser as add_preflight
from .cmd_rulepack import add_subparser as add_rulepack


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="fairy", description="FAIRy CLI")
    p.add_argument(
        "--version", action="store_true", help="Print engine + rulepack version and exit."
    )
    sub = p.add_subparsers(dest="command", metavar="<command>")

    # top-level commands
    cmd_validate.add_subparser(sub)
    add_preflight(sub)
    add_rulepack(sub)

    # --- Back-compat umbrella: `run ...`
    run = sub.add_parser(
        "run",
        help="(compat/deprecated) Legacy command group. Use: validate | preflight | rulepack.",
    )
    # Allow legacy style: `run --mode rulepack --rulepack ...` (no subcommand)
    run.add_argument("--mode", choices=["rulepack", "legacy"], default="rulepack")
    run.add_argument("--rulepack", type=Path)
    run.add_argument("--inputs", action="append", default=[], metavar="name=path")
    run.add_argument("--param-file", type=Path)

    # Also allow explicit subcommand style: `run rulepack ...`
    run_sub = run.add_subparsers(dest="run_command", metavar="<subcommand>")
    cmd_validate.add_subparser(run_sub)
    add_preflight(run_sub)
    add_rulepack(run_sub)
    # ---
    return p
