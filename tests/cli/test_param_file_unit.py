import pytest

from fairy.cli.common import ParamsFileError, load_params_file


def test_returns_empty_when_flag_absent():
    assert load_params_file(None) == {}


def test_loads_valid_yaml(tmp_path):
    p = tmp_path / "params.yml"
    p.write_text("min_year: 2007\nstrict: true\n", encoding="utf-8")
    out = load_params_file(str(p))
    assert out == {"min_year": 2007, "strict": True}


def test_missing_file_raises(tmp_path):
    with pytest.raises(ParamsFileError) as e:
        load_params_file(str(tmp_path / "nope.yml"))
    assert "Param file not found" in str(e.value)


def test_parse_error_raises(tmp_path):
    p = tmp_path / "bad.yml"
    p.write_text("min_year: [2007", encoding="utf-8")  # broken YAML
    with pytest.raises(ParamsFileError) as e:
        load_params_file(str(p))
    assert "Failed to parse params YAML" in str(e.value)


def test_non_mapping_top_level_raises(tmp_path):
    p = tmp_path / "list.yml"
    p.write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(ParamsFileError) as e:
        load_params_file(str(p))
    assert "Top-level YAML must be a mapping" in str(e.value)
