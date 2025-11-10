from __future__ import annotations

import sys
from pathlib import Path

from fairy.rulepack.loader import RulepackError, load_rulepack

from .common import parse_inputs_kv


def add_subparser(sub):
    rp = sub.add_parser(
        "rulepack",
        help="Load a YAML rulepack and validate its shape (no execution).",
        description="Validates YAML: meta, rules[], optional params.",
    )
    rp.add_argument("--rulepack", type=Path, required=True)
    rp.add_argument("--inputs", action="append", default=[], metavar="name=path")
    rp.add_argument("--param-file", type=Path)
    rp.set_defaults(func=main)


def main(args) -> int:
    try:
        rp = load_rulepack(args.rulepack)
    except RulepackError as e:
        print(str(e), file=sys.stderr)
        return 2

    inputs = parse_inputs_kv(args.inputs)
    print(f"Loaded rulepack '{rp.meta.name}' v{rp.meta.version} with {len(rp.rules)} rule(s).")
    if inputs:
        print(f"Inputs parsed: {', '.join(f'{k}={v}' for k, v in inputs.items())}")
    return 0
