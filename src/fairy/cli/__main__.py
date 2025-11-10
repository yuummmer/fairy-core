from __future__ import annotations

import sys

from .cmd_rulepack import main as rulepack_main
from .common import version_text
from .parser import build_parser

# (optional) if you want to support `--mode legacy` later, import validate main:
# from . import validate as cmd_validate


def main(argv=None) -> int:
    argv = sys.argv[1:] if not argv else argv

    parser = build_parser()
    args = parser.parse_args(argv)

    # direct subcommand
    if getattr(args, "func", None):
        return args.func(args)

    # top-level version
    if getattr(args, "version", False) and getattr(args, "command", None) is None:
        print(version_text(None))
        return 0

    # --- compat: `run --mode rulepack ...` with no subcommand
    if args.command == "run" and getattr(args, "run_command", None) is None:
        if getattr(args, "mode", None) == "rulepack":
            return rulepack_main(args)
        # elif args.mode == "legacy":
        #     return cmd_validate.main(args)  # wire if/when you support it
        parser.error("Unsupported --mode; try: fairy rulepack --help")

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
