# Changelog
All notable changes to this project will be documented in this file.

This format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `feat(validate)`: add `--rulepack` runner supporting `dup` (alias `no_duplicate_rows`), `unique`, `enum`, and `range` checks; JSON/MD writers; 1-based indices; exit code `1` on any FAIL. Demo rulepack: Penguins.
