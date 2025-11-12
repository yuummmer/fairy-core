# PRD: Stabilize JSON Report Schema for Preflight

**Status**: Accepted
**Last updated**: 2025-11-11
**Owner**: @yuummmer

**Cross-references**:
- Schema: [`schemas/preflight_report_v1.schema.json`](../../schemas/preflight_report_v1.schema.json)
- Golden test: [`tests/golden/preflight.report.json`](../../tests/golden/preflight.report.json)
- Implementation PR: See PR description for full change log

---

## Introduction / Overview

This PRD defines a minimal, stable JSON report schema for FAIRy-core's `preflight` command. The current preflight report structure (`attestation` + `findings`) lacks a formal schema and clear separation between rule-level results and policy-level findings. By locking a minimal schema that includes top-level metadata (dataset_id, metadata.inputs, generated_at, schema_version), rule-based results (rule, level, count, samples), and summary statistics (by level and by rule), we enable reliable golden tests and predictable report consumption by downstream tools and curators.

---

## Goals

- Define and implement a minimal, stable JSON schema for preflight reports that supports golden test snapshots.
- Include top-level metadata: `dataset_id` (aggregate SHA-256 hash), `metadata.inputs` (name→full metadata object), `metadata.rulepack` (rulepack provenance), `generated_at`, and `schema_version`.
- Structure rule results with `rule`, `level` (pass/warn/fail), `count`, and `samples` (list of small dicts with row when applicable).
- Provide summary statistics aggregated by level (pass/warn/fail counts) and by rule (rule→level mapping via `summary.by_rule`).
- Update existing golden tests to match the new schema.
- Ensure deterministic ordering of all arrays and objects for reproducible reports.

---

## User Stories

- As a data steward, I can run `fairy preflight` and receive a stable JSON report that I can snapshot-test against golden files.
- As a curator, I can parse the report's `metadata.inputs` to verify which files were validated and their provenance (sha256, dimensions).
- As a developer, I can rely on the `summary.by_level` and `summary.by_rule` fields to quickly assess overall validation status without parsing individual rules.
- As a CI/CD system, I can compare report JSON against golden snapshots to detect schema drift or unexpected changes.

---

## Functional Requirements

**FR-1**: The preflight report **must** include the following top-level fields:
- `schema_version` (string, e.g., "1.0.0") — schema version for the report structure.
- `generated_at` (string, ISO 8601 UTC timestamp with 'Z' suffix, e.g., "2025-11-11T20:00:00Z") — when the validation run completed (RFC-3339/ISO-8601 compliant, always UTC).
- `dataset_id` (string) — SHA-256 hash of the aggregate dataset, computed from all inputs in canonical form (format: "sha256:<hex>", 64 hex chars).
- `metadata` (object) — contains `inputs` (object mapping input name→metadata object) and `rulepack` (object with rulepack provenance).

**FR-2**: The `metadata.inputs` object **must** map each input name (string) to a metadata object containing:
- `path` (string) — absolute or relative path to the input file.
- `sha256` (string, 64 hex chars) — SHA-256 hash of the file.
- `n_rows` (integer, ≥0) — number of data rows (excluding header).
- `n_cols` (integer, ≥0) — number of columns.
- `header` (array of strings) — column names in order.

**FR-2a**: The `metadata.rulepack` object **must** include rulepack provenance:
- `path` (string) — path to the rulepack file (repo-relative or absolute).
- `sha256` (string, 64 hex chars) — SHA-256 hash of the rulepack file.
- `id` (string, optional) — human-readable rulepack identifier (e.g., "penguins@local").
- `version` (string, optional) — semantic version of the rulepack (e.g., "1.0.0").
- `params_sha256` (string, optional, 64 hex chars) — SHA-256 hash of canonical JSON serialization of params map (sorted keys, no whitespace) to detect param changes.

**FR-3**: The report **must** include a `results` array, where each rule result object contains:
- `rule` (string) — rule identifier (e.g., "schema.required", "row.unique").
- `level` (string, one of "pass", "warn", "fail") — result level for this rule.
- `count` (integer, ≥0) — number of violations found (0 if level is "pass").
- `samples` (array) — up to 10 sample violations, each a small dict with:
  - `row` (integer, 1-based) — row number where applicable (may be omitted for schema-level issues).
  - `column` (string, optional) — column name if applicable.
  - `value` (string, optional) — the problematic value if applicable.
  - Additional context fields as needed (e.g., `message`, `hint`).
- `meta` (object, optional) — rule-specific metadata. When present, SHOULD include `input` (string, input name) and `column` (string, for column-scoped rules). Additional properties allowed for extensibility.

**FR-4**: The report **must** include a `summary` object with:
- `by_level` (object) — counts by level: `{"pass": 5, "warn": 2, "fail": 1}`.
- `by_rule` (object) — level per rule: `{"schema.required": "pass", "row.unique": "fail", ...}`. If a rule appears multiple times, precedence is fail > warn > pass.

**FR-5**: All arrays in the report **must** be deterministically ordered:
- `results` array sorted by `(meta.input, meta.column, rule, level)`.
- `samples` within each rule sorted by `(row, column, stringify(value))`.
- `metadata.inputs` object keys sorted lexicographically.
- `summary.by_rule` object keys sorted lexicographically.

**FR-6**: Row numbers in `samples` **must** be 1-based (first data row is 1, not 0).

**FR-7**: The report **must** be validatable against a JSON Schema file (e.g., `schemas/preflight_report_v1.schema.json`) in tests/CI.

**FR-8**: Existing golden test files (`tests/golden/preflight.report.json`) **must** be updated to match the new schema.

**FR-9**: The test suite **must** validate the generated JSON against the Schema (no runtime validation).

**FR-10**: CLI help and documentation **must** remain discoverable (no breaking changes to CLI flags).

---

## Non-Goals (Out of Scope)

- Changes to the `validate` command report structure (ReportV0 remains unchanged).
- Changes to rulepack YAML schema or rule implementations.
- Performance optimizations for report generation.
- Network I/O or remote validation features.
- Backwards compatibility with old report formats (this is a breaking change for preflight reports).
- Markdown report generation (only JSON schema is stabilized in this PRD).

---

## Design Considerations

### Example Report Structure

```json
{
  "schema_version": "1.0.0",
  "generated_at": "2025-01-15T10:30:00Z",
  "dataset_id": "sha256:f965407ccaac8ee80953c634b7ad47a4c7441945dfebb8b5dabdb6657ed37165",
  "metadata": {
    "inputs": {
      "files": {
        "path": "/path/to/files.tsv",
        "sha256": "8ec6eaeb72ce5d853b76876da578dc251d392176a9384544a8eaf6433964d9fe",
        "n_rows": 3,
        "n_cols": 3,
        "header": ["sample_id", "layout", "filename"]
      },
      "samples": {
        "path": "/path/to/samples.tsv",
        "sha256": "f965407ccaac8ee80953c634b7ad47a4c7441945dfebb8b5dabdb6657ed37165",
        "n_rows": 2,
        "n_cols": 10,
        "header": ["sample_id", "sample_title", "organism", ...]
      }
    },
    "rulepack": {
      "path": "demos/rulepacks/penguins.yml",
      "sha256": "3f7e8a9b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a",
      "id": "penguins@local",  // rulepack id (not to be confused with results[].rule)
      "version": "1.0.0",
      "params_sha256": "a91b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b"
    }
  },
  "summary": {
    "by_level": {
      "pass": 5,
      "warn": 1,
      "fail": 1
    },
    "by_rule": {
      "row.unique": "fail",
      "schema.required": "pass",
      "table.foreign_key": "pass"
    }
  },
  "results": [
    {
      "rule": "row.unique",
      "level": "fail",
      "count": 1,
      "samples": [
        {
          "row": 2,
          "column": "sample_id",
          "value": "S001",
          "message": "Duplicate value 'S001' found in column 'sample_id'"
        }
      ],
      "meta": {
        "input": "samples",
        "column": "sample_id"
      }
    },
    {
      "rule": "schema.required",
      "level": "pass",
      "count": 0,
      "samples": [],
      "meta": {
        "input": "samples",
        "column": "id"
      }
    }
  ]
}
```

### Migration from Current Structure

The current preflight report uses `attestation` (with `inputs` nested inside) and `findings` (policy-level codes). The new structure:
- Moves `inputs` to `metadata.inputs` with full metadata objects.
- Adds `metadata.rulepack` for rulepack provenance (path, sha256, id, version, params_sha256).
- Replaces `findings` with `results` (rule-level results).
- Adds `dataset_id` at top level as aggregate SHA-256 hash of all inputs (computed from canonical form).
- Adds `summary` for quick status checks.
- Adds `schema_version` for schema evolution.
- Renames `run_at_utc` to `generated_at` with ISO-8601 UTC format (trailing 'Z').
- Adds `dataset_id` as aggregate SHA-256 hash.
- Adds optional top-level `engine` and `attestation` fields for future extensibility.

### Edge Cases

- **Multiple inputs**: `metadata.inputs` includes all inputs used in the rulepack, keyed by input name.
- **No violations**: Rules with `level: "pass"` have `count: 0` and empty `samples` array.
- **Schema-level issues**: Samples may omit `row` if the issue is at the table/column level (e.g., missing column).
- **More than 10 violations**: Only the first 10 samples are included (sorted deterministically).
- **Empty rulepack**: Report still includes `metadata.inputs`, `summary` (all zeros), and empty `rules` array.

---

## Technical Considerations

### Implementation Locations

- **Report model**: Create or update dataclass in `src/fairy/core/models/` (e.g., `preflight_report_v1.py`).
- **Report writer**: Update `src/fairy/core/services/validator.py` (or create new writer module) to generate the new structure.
- **JSON Schema**: Create `schemas/preflight_report_v1.schema.json` with full validation rules.
- **Golden tests**: Update `tests/golden/preflight.report.json` to match new schema.
- **Test helpers**: Update `tests/helpers.py` (or equivalent) if normalization functions need changes.

### Dependencies

- No new runtime dependencies required (use existing `jsonschema` for validation).
- Ensure `jsonschema` is available in test environment.

### Deterministic Ordering Implementation

- Use `sort_keys=True` in `json.dumps()` for object key ordering.
- Manually sort arrays before serialization:
  - `results`: `sorted(results, key=lambda r: r["rule"])`
  - `samples`: `sorted(samples, key=lambda s: (s.get("row", 0), s.get("column", "")))`
  - `metadata.inputs`: Use `collections.OrderedDict` or rely on `sort_keys=True`.

### Dataset ID Computation

The `dataset_id` field is computed as an aggregate SHA-256 hash across all inputs to represent the entire dataset being validated. This provides:
- **Provenance/tamper detection**: Represents the complete dataset state.
- **Stability**: Reproducible as long as per-input hashes are stable.
- **No arbitrary semantics**: Avoids "primary" input assumptions.

**Implementation**:
1. For each input (sorted by input name ascending), build a canonical line: `{name}\t{sha256}\t{n_rows}\t{n_cols}` (UTF-8, tab-separated).
2. Sort all lines by input name (ascending).
3. Join lines with newline (`\n`).
4. Compute SHA-256 hash of the resulting string.
5. Emit as `dataset_id: "sha256:<hex>"` (64 hex chars).

**Edge cases**:
- If any input lacks sha256: compute file hash during load (preferred), or omit `dataset_id` and document as optional in schema.

### Error Handling

- If JSON Schema validation fails during report generation, raise a clear error with schema violation details.
- If input file metadata cannot be computed (e.g., file missing), include placeholder values or omit the input from `metadata.inputs` with appropriate logging.
- If rulepack metadata cannot be computed, `metadata.rulepack` may be omitted (document as optional in schema).

### Versioning Strategy

- Start with `schema_version: "1.0.0"` for the stabilized schema.
- Future schema changes should increment version (semantic versioning: major.minor.patch).
- The schema file includes a `$id` field for schema identification.

---

## Success Metrics

- All existing tests pass (CI Python 3.10–3.12).
- New JSON Schema file validates all generated reports.
- Golden test (`tests/golden/preflight.report.json`) matches the new schema and passes snapshot comparison.
- Report generation code includes schema validation before writing.
- CLI `--help` output remains accurate (no breaking flag changes).
- Documentation (if any) reflects the new report structure.

---

## Open Questions (Resolved)

### 1. Dataset ID: Primary vs Aggregate → **Decision: Aggregate**

**Rationale**: Represents the entire dataset being validated (safer for provenance/tamper checks). Stable and reproducible as long as per-input hashes are stable. Avoids arbitrary "primary" semantics that may not exist across rulepacks.

**Specification**:
- Compute `dataset_id` as a SHA-256 over a canonical, deterministic string built from all inputs (sorted by input name).
- For each input name, include name and its file hash (sha256) plus row/col counts to detect structural drift.
- Canonical form (UTF-8), newline-separated: `{name}\t{sha256}\t{n_rows}\t{n_cols}` per line.
- Sort lines by `{name}` ascending before hashing.
- Emit as `dataset_id: "sha256:<hex>"`.

**Edge cases**: If any input lacks sha256, either compute file hash during load (preferred), or omit `dataset_id` and still produce a valid report (documented as optional).

### 2. Timestamp Format → **Decision: ISO-8601 UTC with Z**

**Rationale**: Unambiguous, matches common tooling and current `run_at_utc` pattern. Simpler to diff and validate.

**Specification**:
- Field name: `generated_at` (replaces `run_at_utc`).
- Value format: `"2025-11-11T20:00:00Z"` (RFC-3339/ISO-8601 compliant, always UTC with trailing 'Z').
- Optional: May include local time field later, but not needed for v1.0.0.

### 3. Meta in Rule Results → **Decision: Optional**

**Rationale**: Some rules aren't tied to a single input/column (e.g., cross-input summaries). Keeps payload compact; only include when it adds signal.

**Specification**:
- `meta` MAY appear; when present and applicable:
  - SHOULD include `"input": "<name>"`.
  - SHOULD include `"column": "<col>"` for column-scoped rules.
- JSON Schema: `meta` is not required; when present, validate known keys but allow extension (`additionalProperties: true`).

**Example**:
```json
{
  "rule": "schema.required",
  "level": "fail",
  "count": 2,
  "samples": [{"row": 1, "column": "taxon", "value": null}],
  "meta": { "input": "specimens" }
}
```

### 4. Rulepack-Level Provenance → **Decision: Include under metadata.rulepack**

**Rationale**: Downstream reproducibility: lets integrators trace which rulepack/version produced the report. Keeps all non-input provenance together under `metadata` (inputs + rulepack). Engine (name/version) already covers the FAIRy binary version; rulepack info complements it.

**Specification**:
- Add an object at `metadata.rulepack`:
  - `path` (string) — repo-relative or absolute path to rulepack file.
  - `sha256` (string, 64 hex chars) — SHA-256 hash of rulepack file.
  - `id` (string, optional) — human-readable ID (e.g., "penguins@local").
  - `version` (string, optional) — semantic version (e.g., "1.0.0").
  - `params_sha256` (string, optional, 64 hex chars) — SHA-256 of canonical JSON serialization of params map (sorted keys, no whitespace) to detect param changes.

**Notes**:
- Prefer `sha256` over `version` if the rulepack is not semantically versioned yet.
- `params_sha256` = SHA-256 of a canonical JSON serialization of params (sorted keys, no whitespace). This lets you tell when the same rulepack was run with different params.
