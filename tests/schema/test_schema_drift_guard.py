# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025 Jennifer Slotnick

"""
Schema drift guard: Contract test to prevent accidental schema changes.

This test ensures the schema version and required keys remain stable.
If this test fails, it indicates an accidental schema edit that breaks the contract.
"""

import json
from pathlib import Path


def _get_schema_path() -> Path:
    """Get path to preflight_report_v1.schema.json relative to repo root."""
    repo_root = Path(__file__).resolve().parents[2]
    schema_path = repo_root / "schemas" / "preflight_report_v1.schema.json"
    return schema_path


def test_schema_version_is_locked():
    """Ensure schema_version constant is locked to 1.0.0."""
    schema_path = _get_schema_path()
    assert schema_path.exists(), f"Schema file not found: {schema_path}"

    schema = json.loads(schema_path.read_text())

    # Check that schema_version is locked to "1.0.0"
    schema_version_prop = schema["properties"]["schema_version"]
    assert schema_version_prop["type"] == "string", "schema_version must be a string"
    assert schema_version_prop["const"] == "1.0.0", "schema_version must be locked to '1.0.0'"


def test_required_top_level_keys_exist():
    """Ensure all required top-level keys are present in the schema."""
    schema_path = _get_schema_path()
    assert schema_path.exists(), f"Schema file not found: {schema_path}"

    schema = json.loads(schema_path.read_text())

    required_keys = {
        "schema_version",
        "generated_at",
        "dataset_id",
        "metadata",
        "summary",
        "results",
    }

    schema_properties = set(schema["properties"].keys())
    schema_required = set(schema.get("required", []))

    # All required keys must be in properties
    missing_props = required_keys - schema_properties
    assert not missing_props, f"Missing required properties: {missing_props}"

    # All required keys must be in required list
    missing_required = required_keys - schema_required
    assert not missing_required, f"Missing from required list: {missing_required}"


def test_summary_structure_is_locked():
    """Ensure summary structure (by_level, by_rule) is locked."""
    schema_path = _get_schema_path()
    assert schema_path.exists(), f"Schema file not found: {schema_path}"

    schema = json.loads(schema_path.read_text())

    summary_props = schema["properties"]["summary"]["properties"]
    summary_required = schema["properties"]["summary"]["required"]

    # by_level and by_rule must exist and be required
    assert "by_level" in summary_props, "summary.by_level must exist"
    assert "by_rule" in summary_props, "summary.by_rule must exist"
    assert "by_level" in summary_required, "summary.by_level must be required"
    assert "by_rule" in summary_required, "summary.by_rule must be required"

    # by_level must have pass, warn, fail
    by_level_props = summary_props["by_level"]["properties"]
    by_level_required = summary_props["by_level"]["required"]
    assert "pass" in by_level_props, "summary.by_level.pass must exist"
    assert "warn" in by_level_props, "summary.by_level.warn must exist"
    assert "fail" in by_level_props, "summary.by_level.fail must exist"
    assert "pass" in by_level_required, "summary.by_level.pass must be required"
    assert "warn" in by_level_required, "summary.by_level.warn must be required"
    assert "fail" in by_level_required, "summary.by_level.fail must be required"


def test_results_structure_is_locked():
    """Ensure results array structure is locked."""
    schema_path = _get_schema_path()
    assert schema_path.exists(), f"Schema file not found: {schema_path}"

    schema = json.loads(schema_path.read_text())

    results_items = schema["properties"]["results"]["items"]
    results_required = results_items["required"]

    # rule, level, count, samples must be required
    required_result_fields = {"rule", "level", "count", "samples"}
    missing_fields = required_result_fields - set(results_required)
    assert not missing_fields, f"Missing required result fields: {missing_fields}"

    # level must be enum with pass, warn, fail
    level_prop = results_items["properties"]["level"]
    assert level_prop["type"] == "string", "level must be a string"
    assert "enum" in level_prop, "level must have enum constraint"
    assert set(level_prop["enum"]) == {
        "pass",
        "warn",
        "fail",
    }, "level enum must be pass, warn, fail"
