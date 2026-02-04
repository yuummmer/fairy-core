# FAIRy Preflight Report

- **Schema version:** 1.0.0
- **Rulepack:** geo_bulk_seq@0.2.0
- **FAIRy version:** 0.2.3
- **Generated at (UTC):** 2026-01-31T22:46:00Z
- **Dataset ID:** sha256:4cecfae2153f0b219230f3e88eb392be580066e98e6fc0949ac092676d80f1e1
- **submission_ready:** `True`

## Summary

- FAIL findings: 0 []
- WARN findings: 0 []

If `submission_ready` is `True`, FAIRy believes this dataset is ready to submit.

---

## Input provenance

These hashes and dimensions identify the exact files that FAIRy validated.
You can hand this block to a curator or PI as evidence of what was checked.

### samples.tsv

- path: 'tests/fixtures/preflight/samples.tsv'
- sha256: 'f965407ccaac8ee80953c634b7ad47a4c7441945dfebb8b5dabdb6657ed37165'
- rows: '2'
- cols: '10'

### files.tsv

- path: 'tests/fixtures/preflight/files.tsv'
- sha256: '8ec6eaeb72ce5d853b76876da578dc251d392176a9384544a8eaf6433964d9fe'
- rows: '3'
- cols: '3'

---

## Results (all current issues)

Level `fail` means “must fix before submission.”
Level `warn` means “soft violation / likely curator feedback.”
Level `pass` means the rule passed with no violations.

| Level | Rule | Count | Samples |
|-------|------|-------|--------|
| pass | GEO.REQ.MISSING_FIELD | 0 | (none) |

---

## Resolved since last run

_No baseline from prior run (first run or cache missing)._
