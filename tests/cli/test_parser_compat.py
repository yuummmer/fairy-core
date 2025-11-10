from fairy.cli.parser import build_parser


def test_parser_has_run_compat():
    p = build_parser()
    # should parse legacy style without error; we won’t execute here
    args = p.parse_args(["run", "--mode", "rulepack", "--rulepack", "x.yaml"])
    assert args.command == "run"
    assert args.mode == "rulepack"
    # legacy fields present
    assert hasattr(args, "rulepack")
