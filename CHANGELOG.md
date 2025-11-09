# Changelog
All notable changes to this project will be documented in this file.

This format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `feat(validate)`: add `--rulepack` runner supporting `dup` (alias `no_duplicate_rows`), `unique`, `enum`, and `range` checks; JSON/MD writers; 1-based indices; exit code `1` on any FAIL. Demo rulepack: Penguins.
- `feat(validate)`: **multi-input** support via repeatable `--inputs name=path` pairs (e.g., `--inputs artworks=artworks.csv --inputs artists=artists.csv`).
- `feat(validate)`: **cross-table foreign key** rule (`type: foreign_key`) with `from.table/field` → `to.table/field` addressing.
- Reports: add **`metadata.inputs`** echo `{name → path}` for provenance (non-breaking).
- Tests/fixtures: CLI tests for multi-input pass/fail; art-collections fixtures (`artworks.csv`, `artists.csv`).

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
