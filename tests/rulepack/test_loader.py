from pathlib import Path

import pytest

from fairy.rulepack.loader import RulepackError, load_rulepack


def test_loads_minimal_rulepack(tmp_path: Path):
    p = tmp_path / "rp.yaml"
    p.write_text(
        "meta:\n  name: a\n  version: '1.0.0'\nrules:\n  - id: r1\n    type: always_pass\n",
        encoding="utf-8",
    )
    rp = load_rulepack(p)
    assert rp.meta.name == "a"
    assert len(rp.rules) == 1
    assert rp.rules[0].type == "always_pass"


def test_missing_keys_errors(tmp_path: Path):
    p = tmp_path / "rp.yaml"
    p.write_text("rules: []\n", encoding="utf-8")
    with pytest.raises(RulepackError):
        load_rulepack(p)


def test_bad_yaml_errors(tmp_path: Path):
    p = tmp_path / "rp.yaml"
    p.write_text("meta: [unterminated\n", encoding="utf-8")
    with pytest.raises(RulepackError):
        load_rulepack(p)


def test_top_level_not_mapping(tmp_path: Path):
    p = tmp_path / "rp.yaml"
    p.write_text("- not: a mapping\n- at: top\n", encoding="utf-8")
    with pytest.raises(RulepackError):
        load_rulepack(p)
