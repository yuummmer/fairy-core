from pathlib import Path

from fairy.cli import cmd_rulepack


class Args:
    def __init__(self, rulepack, inputs=None, param_file=None):
        self.rulepack = Path(rulepack)
        self.inputs = inputs or []
        self.param_file = param_file


def test_cmd_rulepack_main_minimal(tmp_path: Path):
    rp = tmp_path / "rp.yaml"
    rp.write_text(
        "meta:\n  name: a\n  version: '0.0.1'\nrules:\n- id: r\n  type: always_pass\n",
        encoding="utf-8",
    )
    code = cmd_rulepack.main(Args(rulepack=rp))
    assert code == 0


def test_cmd_rulepack_main_with_inputs(tmp_path: Path, capsys):
    rp = tmp_path / "rp.yaml"
    rp.write_text(
        "meta:\n  name: a\n  version: '0.0.1'\nrules:\n- id: r\n  type: always_pass\n",
        encoding="utf-8",
    )
    rc = cmd_rulepack.main(Args(rulepack=rp, inputs=["t=./x.csv"]))
    out = capsys.readouterr().out
    assert rc == 0
    assert "Loaded rulepack 'a' v0.0.1" in out
    assert "Inputs parsed: t=./x.csv" in out
