import json
from pathlib import Path

import jsonschema
from jsonschema import Draft202012Validator


def test_manifest_v1_schema_validates_example():
    repo_root = Path(__file__).resolve().parents[1]

    schema_path = repo_root / "schemas" / "manifest_v1.schema.json"
    example_path = repo_root / "fixtures" / "manifest_v1" / "example.json"

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    example = json.loads(example_path.read_text(encoding="utf-8"))

    # Ensure the schema itself is valid (draft 2020-12)
    Draft202012Validator.check_schema(schema)

    # Validate example with format checks (date-time, etc.)
    validator = Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    errors = sorted(validator.iter_errors(example), key=lambda e: e.path)

    assert errors == [], "Schema validation failed:\n" + "\n".join(
        f"- {list(e.path)}: {e.message}" for e in errors
    )
