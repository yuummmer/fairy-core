# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025 Jennifer Slotnick

"""
Test JSON Schema validation edge cases for preflight reports.

This module tests that the schema correctly validates and rejects invalid reports.
"""

import json
from pathlib import Path

import jsonschema
import pytest

from fairy.core.services.validator import run_rulepack


def _get_schema_path() -> Path:
    """Get path to preflight_report_v1.schema.json relative to repo root."""
    repo_root = Path(__file__).resolve().parent.parent
    schema_path = repo_root / "schemas" / "preflight_report_v1.schema.json"
    return schema_path


def _load_schema() -> dict:
    """Load and return the JSON schema."""
    schema_path = _get_schema_path()
    if not schema_path.exists():
        pytest.skip(f"Schema file not found: {schema_path}")
    return json.loads(schema_path.read_text())


def test_invalid_report_missing_required_field():
    """Test that a report missing a required field is rejected."""
    schema = _load_schema()

    # Missing schema_version
    invalid_report = {
        "generated_at": "2025-01-01T12:00:00Z",
        "dataset_id": "sha256:" + "0" * 64,
        "metadata": {"inputs": {}, "rulepack": {"path": "/test", "sha256": "0" * 64}},
        "summary": {"by_level": {"pass": 0, "warn": 0, "fail": 0}, "by_rule": {}},
        "results": [],
    }

    with pytest.raises(jsonschema.ValidationError) as exc_info:
        jsonschema.validate(instance=invalid_report, schema=schema)
    assert "schema_version" in str(exc_info.value.message).lower()


def test_invalid_report_wrong_schema_version():
    """Test that a report with wrong schema_version is rejected."""
    schema = _load_schema()

    invalid_report = {
        "schema_version": "2.0.0",  # Wrong version
        "generated_at": "2025-01-01T12:00:00Z",
        "dataset_id": "sha256:" + "0" * 64,
        "metadata": {"inputs": {}, "rulepack": {"path": "/test", "sha256": "0" * 64}},
        "summary": {"by_level": {"pass": 0, "warn": 0, "fail": 0}, "by_rule": {}},
        "results": [],
    }

    with pytest.raises(jsonschema.ValidationError) as exc_info:
        jsonschema.validate(instance=invalid_report, schema=schema)
    assert "1.0.0" in str(exc_info.value.message)


def test_invalid_report_invalid_generated_at_format():
    """Test that a report with invalid generated_at format is rejected."""
    schema = _load_schema()

    invalid_report = {
        "schema_version": "1.0.0",
        "generated_at": "2025-01-01 12:00:00",  # Missing T and Z
        "dataset_id": "sha256:" + "0" * 64,
        "metadata": {"inputs": {}, "rulepack": {"path": "/test", "sha256": "0" * 64}},
        "summary": {"by_level": {"pass": 0, "warn": 0, "fail": 0}, "by_rule": {}},
        "results": [],
    }

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=invalid_report, schema=schema)


def test_invalid_report_invalid_dataset_id_format():
    """Test that a report with invalid dataset_id format is rejected."""
    schema = _load_schema()

    invalid_report = {
        "schema_version": "1.0.0",
        "generated_at": "2025-01-01T12:00:00Z",
        "dataset_id": "invalid-format",  # Not sha256: format
        "metadata": {"inputs": {}, "rulepack": {"path": "/test", "sha256": "0" * 64}},
        "summary": {"by_level": {"pass": 0, "warn": 0, "fail": 0}, "by_rule": {}},
        "results": [],
    }

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=invalid_report, schema=schema)


def test_invalid_report_invalid_level():
    """Test that a result with invalid level is rejected."""
    schema = _load_schema()

    invalid_report = {
        "schema_version": "1.0.0",
        "generated_at": "2025-01-01T12:00:00Z",
        "dataset_id": "sha256:" + "0" * 64,
        "metadata": {"inputs": {}, "rulepack": {"path": "/test", "sha256": "0" * 64}},
        "summary": {"by_level": {"pass": 0, "warn": 0, "fail": 0}, "by_rule": {}},
        "results": [
            {
                "rule": "test.rule",
                "level": "invalid",  # Invalid level
                "count": 0,
                "samples": [],
            }
        ],
    }

    with pytest.raises(jsonschema.ValidationError) as exc_info:
        jsonschema.validate(instance=invalid_report, schema=schema)
    # Error message should indicate invalid enum value
    error_msg = str(exc_info.value.message).lower()
    assert (
        "level" in error_msg
        or "invalid" in error_msg
        or "not one of" in error_msg
        or "pass" in error_msg
    )


def test_invalid_report_negative_row():
    """Test that a sample with negative row is rejected."""
    schema = _load_schema()

    invalid_report = {
        "schema_version": "1.0.0",
        "generated_at": "2025-01-01T12:00:00Z",
        "dataset_id": "sha256:" + "0" * 64,
        "metadata": {"inputs": {}, "rulepack": {"path": "/test", "sha256": "0" * 64}},
        "summary": {"by_level": {"pass": 0, "warn": 0, "fail": 0}, "by_rule": {}},
        "results": [
            {
                "rule": "test.rule",
                "level": "fail",
                "count": 1,
                "samples": [{"row": 0}],  # Row 0 is invalid (must be >= 1)
            }
        ],
    }

    with pytest.raises(jsonschema.ValidationError) as exc_info:
        jsonschema.validate(instance=invalid_report, schema=schema)
    assert (
        "row" in str(exc_info.value.message).lower()
        or "minimum" in str(exc_info.value.message).lower()
    )


def test_valid_report_empty_results():
    """Test that a report with empty results array is valid."""
    schema = _load_schema()

    valid_report = {
        "schema_version": "1.0.0",
        "generated_at": "2025-01-01T12:00:00Z",
        "dataset_id": "sha256:" + "0" * 64,
        "metadata": {
            "inputs": {
                "samples": {
                    "path": "/test/samples.tsv",
                    "sha256": "0" * 64,
                    "n_rows": 0,
                    "n_cols": 0,
                    "header": [],
                }
            },
            "rulepack": {"path": "/test/rulepack.json", "sha256": "0" * 64},
        },
        "summary": {"by_level": {"pass": 0, "warn": 0, "fail": 0}, "by_rule": {}},
        "results": [],  # Empty results
    }

    # Should not raise
    jsonschema.validate(instance=valid_report, schema=schema)


def test_valid_report_missing_optional_fields():
    """Test that a report with missing optional fields is valid."""
    schema = _load_schema()

    valid_report = {
        "schema_version": "1.0.0",
        "generated_at": "2025-01-01T12:00:00Z",
        "dataset_id": "sha256:" + "0" * 64,
        "metadata": {
            "inputs": {
                "samples": {
                    "path": "/test/samples.tsv",
                    "sha256": "0" * 64,
                    "n_rows": 0,
                    "n_cols": 0,
                    "header": [],
                }
            },
            "rulepack": {"path": "/test/rulepack.json", "sha256": "0" * 64},
            # Missing optional fields: id, version, params_sha256
        },
        "summary": {"by_level": {"pass": 0, "warn": 0, "fail": 0}, "by_rule": {}},
        "results": [],
        # Missing optional fields: engine, attestation
    }

    # Should not raise
    jsonschema.validate(instance=valid_report, schema=schema)


def test_valid_report_with_optional_fields():
    """Test that a report with all optional fields is valid."""
    schema = _load_schema()

    valid_report = {
        "schema_version": "1.0.0",
        "generated_at": "2025-01-01T12:00:00Z",
        "dataset_id": "sha256:" + "0" * 64,
        "metadata": {
            "inputs": {
                "samples": {
                    "path": "/test/samples.tsv",
                    "sha256": "0" * 64,
                    "n_rows": 0,
                    "n_cols": 0,
                    "header": [],
                }
            },
            "rulepack": {
                "path": "/test/rulepack.json",
                "sha256": "0" * 64,
                "id": "test-rulepack",
                "version": "1.0.0",
                "params_sha256": "0" * 64,
            },
        },
        "summary": {"by_level": {"pass": 0, "warn": 0, "fail": 0}, "by_rule": {}},
        "results": [],
        "engine": {"name": "fairy", "version": "0.2.0"},
        "attestation": {"some": "data"},
    }

    # Should not raise
    jsonschema.validate(instance=valid_report, schema=schema)


def test_error_messages_are_clear(rulepack_path: Path, samples_path: Path, files_path: Path):
    """Test that validation error messages are clear and helpful."""
    schema = _load_schema()

    # Create a report with an error
    report = run_rulepack(
        rulepack_path=rulepack_path,
        samples_path=samples_path,
        files_path=files_path,
    )

    # Corrupt the report
    report["schema_version"] = "2.0.0"

    with pytest.raises(jsonschema.ValidationError) as exc_info:
        jsonschema.validate(instance=report, schema=schema)

    error = exc_info.value
    # Error should mention the field and expected value
    assert "schema_version" in str(error.message).lower() or "schema_version" in str(
        error.absolute_path
    )
    # Error should be accessible via .message attribute
    assert hasattr(error, "message")
    assert hasattr(error, "absolute_path")
