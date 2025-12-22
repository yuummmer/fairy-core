# tests/test_regex_rule_type.py
import datetime
from pathlib import Path

import yaml

from fairy.validation.rulepack_runner import run_rulepack


def _run(rp_path_str, inputs_map):
    rp_path = Path(rp_path_str)
    rp = yaml.safe_load(rp_path.read_text())
    now = datetime.datetime(2025, 1, 1).isoformat()
    return run_rulepack(inputs_map, rp, rp_path, now)


def test_regex_rule_type_enforces_format_and_detects_forbidden_chars():
    report = _run(
        "tests/fixtures/rulepacks/regex_demo.yaml",
        {"default": Path("tests/fixtures/regex_demo.csv")},
    )

    # After implementation:
    # - sample_id_format should FAIL due to AB-12345-001 (empty ignored)
    # - product_name_no_control_chars should WARN due to tab in product_name
    rules = report["resources"][0]["rules"]
    by_id = {r["id"]: r for r in rules}

    assert by_id["sample_id_format"]["status"] == "FAIL"
    assert by_id["product_name_no_control_chars"]["status"] == "WARN"
