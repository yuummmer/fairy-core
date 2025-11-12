# FAIRy Preflight Report

- **Schema version:** 1.0.0
- **Rulepack:** GEO-SEQ-BULK@0.1.0
- **FAIRy version:** 0.1.0
- **Generated at (UTC):** 2025-11-11T12:00:00Z
- **Dataset ID:** sha256:def328d544e5b5a6a0b9617438c5673432d5b57040c0b143eef99ef774c77ca9
- **submission_ready:** `False`

## Summary

- FAIL findings: 1 ['CORE.ID.UNMATCHED_SAMPLE']
- WARN findings: 1 ['CORE.DATE.INVALID_ISO8601']

If `submission_ready` is `True`, FAIRy believes this dataset is ready to submit.

---

## Input provenance

These hashes and dimensions identify the exact files that FAIRy validated.
You can hand this block to a curator or PI as evidence of what was checked.

### samples.tsv

- path: '/home/jenni/projects/fairy-core/demos/scratchrun/samples.tsv'
- sha256: 'f965407ccaac8ee80953c634b7ad47a4c7441945dfebb8b5dabdb6657ed37165'
- rows: '2'
- cols: '10'

### files.tsv

- path: '/home/jenni/projects/fairy-core/demos/scratchrun/files.tsv'
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
| warn | CORE.DATE.INVALID_ISO8601 | 1 | row 1, col collection_date |
| fail | CORE.ID.UNMATCHED_SAMPLE | 1 | row 2, col sample_id |
| pass | GEO.BIO.CONTEXT_MISSING | 0 | (none) |
| pass | GEO.FILE.PAIRING_MISMATCH | 0 | (none) |
| pass | GEO.REQ.MISSING_FIELD | 0 | (none) |
| pass | GEO.REQ.MISSING_PROCESSED_DATA | 0 | (none) |

### CORE.DATE.INVALID_ISO8601 (warn, 1 sample)

- row 1, column 'collection_date', message: Value '10/3/25' in collection_date is not ISO8601 (YYYY-MM-DD)., hint: Use format YYYY-MM-DD, e.g. 2025-10-02.

### CORE.ID.UNMATCHED_SAMPLE (fail, 1 sample)

- row 2, column 'sample_id', message: File references sample_id 'S999' not found in samples.tsv., hint: Fix sample_id or add that sample to samples.tsv.

---

## Resolved since last run

_No previously-reported issues resolved._
