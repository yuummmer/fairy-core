from pathlib import Path

import pytest

from fairy.rulepack.loader import RulepackError, load_rulepack


def test_missing_file_raises():
    with pytest.raises(RulepackError):
        load_rulepack("nope.yaml")


def test_bad_yaml_raises(tmp_path: Path):
    p = tmp_path / "bad.yaml"
    p.write_text("meta: [unterminated\n", encoding="utf-8")
    with pytest.raises(RulepackError):
        load_rulepack(p)


def test_non_mapping_top_level_raises(tmp_path: Path):
    p = tmp_path / "list.yaml"
    p.write_text("- not: mapping\n- at: top\n", encoding="utf-8")
    with pytest.raises(RulepackError):
        load_rulepack(p)
