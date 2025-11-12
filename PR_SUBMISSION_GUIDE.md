# PR Submission Guide

## Current Status

All implementation tasks are complete. Ready to submit PR.

## Files to Commit

### Core Implementation
- `src/fairy/core/models/preflight_report_v1.py` - Dataclass models
- `src/fairy/core/services/provenance.py` - Provenance utilities
- `src/fairy/core/services/transform.py` - Transformation utilities
- `src/fairy/core/services/validator.py` - Updated report generation
- `schemas/preflight_report_v1.schema.json` - JSON Schema

### CLI & Output
- `src/fairy/cli/cmd_preflight.py` - Updated CLI
- `src/fairy/cli/output_md.py` - Updated markdown generation
- `src/fairy/cli/run.py` - Updated runner
- `src/fairy/core/services/export_adapter.py` - Updated adapter

### Tests
- `tests/test_preflight_report_schema.py` - Comprehensive schema tests
- `tests/test_schema_validation_edge_cases.py` - Edge case tests
- `tests/test_schema_drift_guard.py` - Contract tests
- `tests/test_dataset_id.py` - Updated dataset ID tests
- `tests/cli/test_cmd_preflight_unit.py` - Updated CLI tests
- `tests/cli/test_output_md_unit.py` - Updated output tests
- `tests/helpers.py` - Updated normalization
- `tests/golden/preflight.report.json` - Updated golden file
- `tests/golden/preflight.report.md` - Updated golden markdown
- `tests/README.md` - Test documentation

### Documentation
- `docs/reporting.md` - Report schema documentation
- `docs/prd/prd-stabilize-json-report-schema.md` - PRD
- `CHANGELOG.md` - Version 0.2.0 entry
- `README.md` - Updated reports section
- `CONTRIBUTING.md` - Added PRD section

### Configuration
- `pyproject.toml` - Version bumped to 0.2.0
- `src/fairy/__init__.py` - Version set to 0.2.0
- `scripts/update_goldens.py` - Updated for fixed timestamps
- `.gitignore` - Excludes development artifacts

## Files Excluded (via .gitignore)
- `.cursor/` - Cursor IDE files
- `PR_DESCRIPTION.md` - Generated PR description (use for PR body)
- `SHIP_CHECKLIST.md` - Development checklist
- `tasks/tasks-*.md` - Task lists

## Steps to Submit PR

### 1. Create Feature Branch
```bash
git checkout -b feat/stabilize-preflight-report-schema
```

### 2. Stage Files
```bash
# Stage all implementation files
git add src/ schemas/ tests/ docs/ scripts/ pyproject.toml CHANGELOG.md README.md CONTRIBUTING.md .gitignore

# Verify what will be committed
git status
```

### 3. Commit
```bash
git commit -m "feat: stabilize preflight JSON report schema (v1.0.0)

- Add stable v1.0.0 schema with deterministic ordering
- Include metadata.inputs and metadata.rulepack with full provenance
- Transform findings → results with rule, level, count, samples
- Add summary.by_level and summary.by_rule for quick status checks
- Compute dataset_id as aggregate SHA-256 across inputs
- Add comprehensive schema validation tests
- Update golden tests with fixed timestamps
- Add deprecation warning for _legacy field (removal in v1.2.0)
- Update CLI and markdown generation to use new structure
- Add PRD documentation in docs/prd/

BREAKING CHANGE: Preflight report structure changed from legacy format
(attestation + findings) to v1.0.0 schema (metadata, summary, results).
Legacy structure preserved in _legacy field for backward compatibility.

See docs/prd/prd-stabilize-json-report-schema.md for full specification."
```

### 4. Push Branch
```bash
git push -u origin feat/stabilize-preflight-report-schema
```

### 5. Create PR on GitHub
- Use the content from `PR_DESCRIPTION.md` as the PR body
- Title: "Stabilize preflight JSON report schema (v1.0.0)"
- Link to PRD: `docs/prd/prd-stabilize-json-report-schema.md`
- Request review from team

### 6. After PR Merge
- Create git tag: `git tag -a v0.2.0 -m "Release 0.2.0: Preflight report schema v1.0.0"`
- Push tag: `git push origin v0.2.0`
- Create GitHub Release with schema file as asset

## Pre-Submission Checklist

- [x] All tests pass (`pytest -q`)
- [x] Code formatted (`black .`)
- [x] Golden file regenerated with fixed timestamp
- [x] Schema validates all generated reports
- [x] Documentation updated (README, CHANGELOG, docs/)
- [x] PRD aligned with implementation
- [x] Deprecation warnings added
- [x] Version bumped to 0.2.0
- [ ] Branch created and pushed
- [ ] PR created on GitHub
- [ ] CI passes

## Notes

- The PRD is now in `docs/prd/` and linked from CONTRIBUTING.md
- Development artifacts (task lists, checklists) are excluded via .gitignore
- All implementation is complete and ready for review
