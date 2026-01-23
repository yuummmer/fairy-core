# Changelog
All notable changes to this project will be documented in this file.

This format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.3] - 2026-01-22

### Changed
- Clarify CLI roles: `validate` = engine/CI mode, `preflight` = operator mode, `run` = compat/deprecated
- `fairy preflight --help` now lists available profiles (geo, generic, spellbook) with examples
- Updated CLI help text and documentation to reflect mental model (validate = checks; preflight = checks + outputs + guidance)
- ADR-0005 marked as Accepted; preflight profiles + handoff output directory implementation complete

## [0.2.2] - 2025-12-26

### Added
- Auto-detect TSV delimiter when loading inputs

### Changed
- Updated `.gitignore` to ignore local scratch outputs

## [0.2.1] - 2025-12-22

### Added
- `validate` command: add `--rulepack` runner supporting `dup` (alias `no_duplicate_rows`), `unique`, `enum`, `range`, `url`, and `non_empty_trimmed` checks; JSON/MD writers; 1-based indices; exit code `1` on any FAIL. Demo rulepack: Penguins.
- `validate` command: **multi-input** support via repeatable `--inputs name=path` pairs (e.g., `--inputs artworks=artworks.csv --inputs artists=artists.csv`).
- `validate` command: **cross-table foreign key** rule (`type: foreign_key`) with `from.table/field` → `to.table/field` addressing.
- `validate` command: add `regex` rule type for string format validation / forbidden pattern detection (`mode: not_matches|matches`, `ignore_empty`).
- Reports: include `attestation.core_version` and keep `metadata.inputs` echo `{name → path}` for provenance (non-breaking).
- Docs: document `regex` in `docs/rule-types.md` and list it in the README.

### Changed
- `fairy validate -h` now documents both usage patterns (legacy positional input and `--inputs` multi-input).
- Dispatcher (`fairy` top-level CLI) delegates `validate` to the new subcommand implementation.

### Backward Compatibility
- Positional single-input is **kept forever**:
  - file → table name `default`
  - folder → each `*.csv` becomes a table named by its stem
- No breaking changes to the JSON schema; `metadata.inputs` is additive.

### Known / Notes
- Duplicate `--inputs` names: last one wins (warning emitted).
- If a rulepack references an unknown table, the CLI raises a clear error listing provided table names.

## [0.2.0] - 2025-11-11

### Added
- **Preflight report schema v1.0.0**: Stable JSON schema for `fairy preflight` reports with deterministic ordering
  - New top-level fields: `schema_version`, `generated_at`, `dataset_id`, `metadata`, `summary`, `results`
  - `metadata.inputs`: Full provenance for all input files (path, sha256, n_rows, n_cols, header)
  - `metadata.rulepack`: Rulepack provenance (path, sha256, id, version, params_sha256)
  - `summary.by_level`: Counts by level (pass, warn, fail)
  - `summary.by_rule`: Rule ID → level mapping with fail > warn > pass precedence
  - `results`: Array of rule results with `rule`, `level`, `count`, and `samples` (up to 10 per rule)
  - JSON Schema validation: `schemas/preflight_report_v1.schema.json`
  - Golden test support with fixed timestamps for reproducible snapshots
- Documentation: `docs/reporting.md` with schema reference, examples, and migration guide

### Changed
- **BREAKING**: Preflight report structure changed from legacy format to v1.0.0 schema
  - Old → New field mapping:
    - `attestation.run_at_utc` → `generated_at` (ISO-8601 UTC with 'Z' suffix)
    - `attestation.inputs` → `metadata.inputs` (full metadata objects)
    - `findings` → `results` (rule-level results with samples)
    - `attestation.fail_count` → `summary.by_level.fail`
    - `attestation.warn_count` → `summary.by_level.warn`
  - Legacy structure preserved in `_legacy` field for backward compatibility (deprecated, will be removed in v1.2.0)
- Deterministic report ordering: All arrays and object keys are sorted for reproducibility
- `dataset_id`: Now computed as aggregate SHA-256 hash across all inputs

### Backward Compatibility
- Legacy report structure (`attestation` + `findings`) available in `_legacy` field
- `_legacy` field will be removed in v1.2.0 (or after 2 releases)
- CLI and markdown generation updated to use new v1 structure
