from fairy.cli.parser import build_parser


def test_parser_has_subcommands_and_run():
    p = build_parser()
    # legacy: run --mode rulepack
    args = p.parse_args(["run", "--mode", "rulepack", "--rulepack", "x.yaml"])
    assert args.command == "run"
    assert args.mode == "rulepack"
    # direct subcommand exists
    args2 = p.parse_args(["rulepack", "--rulepack", "x.yaml"])
    assert args2.command is None or hasattr(args2, "func")
