# FAIRy Preflight Report

- **Rulepack:** GEO-SEQ-BULK@0.1.0
- **FAIRy version:** 0.1.0
- **Run at (UTC):** 2025-11-06T04:35:45.736817+00:00
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

## Findings (all current issues)

Severity `FAIL` means “must fix before submission.”
Severity `WARN` means “soft violation / likely curator feedback.”

| Severity | Code | Location | Why it matters | How to fix |
|----------|------|----------|----------------|------------|
| FAIL | CORE.ID.UNMATCHED_SAMPLE | row 2, column 'sample_id' | Every file must map to a described sample and vice versa. | Align sample_id sets across samples.tsv and files.tsv. |
| WARN | CORE.DATE.INVALID_ISO8601 | row 0, column 'collection_date' | Ambiguous dates hurt reuse; curators may ask for fixes. | Use ISO8601 (YYYY-MM-DD). |

---

## Resolved since last run

_No baseline from prior run (first run or cache missing)._
