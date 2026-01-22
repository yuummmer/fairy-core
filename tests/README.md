# Test Suite

This directory contains the test suite for FAIRy-core.

## Golden Tests

Golden tests use snapshot testing to ensure report schema stability. The golden files are located in `tests/golden/`.

### Regenerating Golden Files

Golden files are generated with fixed timestamps and deterministic hashes for reproducibility. To regenerate:

```bash
# Using the update script (recommended)
python3 scripts/update_goldens.py

# Or manually with fixed timestamp
FAIRY_FIXED_TIMESTAMP=2025-11-11T12:00:00Z python3 -m fairy.cli.run preflight \
  --rulepack src/fairy/rulepacks/GEO-SEQ-BULK/v0_1_0.json \
  --samples demos/scratchrun/samples.tsv \
  --files demos/scratchrun/files.tsv \
  --out tests/golden/preflight.report.json
```

### Deterministic Generation

The `FAIRY_FIXED_TIMESTAMP` environment variable ensures golden files have consistent timestamps:

- **Format**: ISO-8601 UTC with 'Z' suffix (e.g., `2025-11-11T12:00:00Z`)
- **Usage**: Set before running preflight to generate deterministic reports
- **Default**: If not set, uses current system time (not suitable for golden tests)

### Hash Determinism

Report hashes (SHA-256) are deterministic when:
- Input files are identical
- Rulepack is identical
- Timestamp is fixed (via `FAIRY_FIXED_TIMESTAMP`)
- All arrays and object keys are sorted (enforced by the code)

### Normalization

Test helpers normalize volatile fields before comparing reports:

- `generated_at`: Timestamp is normalized to a fixed value
- Other volatile fields can be added to `VOLATILE_KEYS` in `tests/helpers.py`

See `tests/helpers.py` for the normalization implementation.

## Test Organization

Tests are organized to mirror the source code structure:

- **`cli/`**: CLI command tests (preflight, rulepack, etc.)
- **`core/`**: Core module tests
  - **`test_models/`**: Manifest and model tests
  - **`test_services/`**: Service layer tests (preflight profiles, provenance, etc.)
- **`rulepack/`**: Rulepack loader and validation tests
- **`validation/`**: Validation engine tests (rule validators, rulepack runner, etc.)
- **`schema/`**: Schema validation tests
  - `test_preflight_report_schema.py`: Comprehensive tests for report generation and schema validation
  - `test_schema_validation_edge_cases.py`: Edge cases and invalid report handling
  - `test_schema_drift_guard.py`: Contract tests to prevent accidental schema changes
- **`integration/`**: End-to-end integration tests

## Running Tests

```bash
# Run all tests
pytest -q

# Run specific test file
pytest -q tests/schema/test_preflight_report_schema.py

# Run tests for a specific module
pytest -q tests/core/
pytest -q tests/validation/
pytest -q tests/integration/

# Run with coverage
pytest --cov=src/fairy --cov-report=term-missing
```

## Test Dependencies

Required test dependencies (install with `pip install -e ".[dev]"`):

- `pytest`: Test framework
- `pytest-cov`: Coverage reporting
- `freezegun`: Time freezing for deterministic tests
- `jsonschema`: Schema validation (also a runtime dependency)
