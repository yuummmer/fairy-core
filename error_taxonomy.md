# Error / Warning Taxonomy (v0.1)

FAIRy findings are expressed at two layers:

1. Engine diagnostics (low-level data quality checks)
   - IDs like `column.missing_required`
   - Severity values: `info | warn | error`
   - These are emitted by validators that look at tables / columns / rows.

2. Attestation findings (policy-level / repository-level)
   - Codes like `GEO.REQ.MISSING_FIELD`
   - Severity values: `WARN | FAIL`
   - These appear in the final FAIRy report/attestation and are what users,
     librarians, and compliance care about.

The attestation block in the FAIRy report summarizes FAIL vs WARN
and drives `submission_ready`.

## Attestation contract

Each FAIRy run produces an attestation header:

- `rulepack_id`
- `rulepack_version`
- `fairy_version`
- `run_at_utc`
- `submission_ready`   (true if there are 0 FAIL findings, else false)
- `fail_count`
- `warn_count`

Each finding in the final report MUST include:
- `code`         (stable ID like `GEO.REQ.MISSING_FIELD`)
- `severity`     (`FAIL` or `WARN`)
- `where`        (human locator, e.g. "samples.tsv: row 12, column 'library_strategy'")
- `why`          (why this matters to curation/reuse/repository acceptance)
- `how_to_fix`   (actionable guidance for the submitter)
- `details`      (machine-readable context like row index, column name, etc.)

---

## Layer 1. Engine diagnostics (internal / reusable primitives)

These are low-level table checks the validator engine can emit while inspecting files.
They are NOT necessarily what end users will see in the attestation, but rulepacks may map them into higher-level policy findings.

Severity here uses `info | warn | error`.

Deterministic ordering of raw diagnostics:
sort by `(path, id, severity)`.

| id                       | severity | message                                  | path/loc example                    |
|-------------------------|----------|------------------------------------------|-------------------------------------|
| column.missing_required | error    | Required column is missing               | `columns/library_strategy`          |
| cell.empty_required     | error    | Empty cell in required column            | `rows/45/columns/library_strategy`  |
| column.name_mismatch    | warn     | Column name differs from expected regex  | `columns/SampleID`                  |
| row.duplicate_key       | warn     | Duplicate value in key column            | `rows/123` (col: sample_id)         |

Notes:
- `column.missing_required` = the header itself is missing.
- `cell.empty_required` = header exists, but a row has blank where it's not allowed.
- `row.duplicate_key` = non-unique `sample_id`, etc.

Rulepacks consume these diagnostics and decide how serious they are in context.

---

## Layer 2. Attestation findings (surface / policy-level codes)

These are the stable `code` values that appear in FAIRy's final report/attestation.
Tests assert on these codes.
Severity here is `FAIL` or `WARN`.

### `GEO.REQ.MISSING_FIELD`
- Severity: `FAIL`
- Summary: Required metadata column is missing or blank.
- Emit when:
  - A required GEO field (e.g. `library_strategy`, `molecule`, `instrument_model`, `sample_title`, `organism`) is not present in `samples.tsv`, OR
  - It exists but at least one row is empty.
- Why it matters:
  GEO requires these fields and will stall/reject submissions missing them.
- Maps from engine diagnostics like:
  - `column.missing_required`
  - `cell.empty_required`

### `GEO.BIO.CONTEXT_MISSING`
- Severity: `FAIL`
- Summary: Sample has no biological source info.
- Emit when:
  - For a given row in `samples.tsv`, all of `tissue`, `cell_line`, and `cell_type` are blank.
- Why it matters:
  GEO curators consider biological source info required; missing it gets flagged as "missing required biological information."
- Engine support:
  - row-level check over those three columns.

### `CORE.ID.UNMATCHED_SAMPLE`
- Severity: `FAIL`
- Summary: sample_id mismatch between `samples.tsv` and `files.tsv`.
- Emit when:
  - A `sample_id` is present in one file but not the other.
- Why it matters:
  Every file in a submission must map to described metadata, and every described sample must have associated files.
  Mismatches stop curation because the curator can't tell which file belongs to which sample.
- Engine support:
  - cross-file set difference check.

### `GEO.FILE.PAIRING_MISMATCH`
- Severity: `FAIL`
- Summary: Paired-end read files are incomplete or mismatched.
- Emit when:
  - A sample marked as paired-end (e.g. `layout == PAIRED`) is missing R1 or R2,
    OR R1/R2 don't correspond to the same `sample_id`.
- Why it matters:
  GEO explicitly requires both reads for paired-end libraries ("Two fastq files are required (R1 and R2)...").
  Missing mates blocks acceptance.
- Engine support:
  - filename pattern / layout check.

### `CORE.DATE.INVALID_ISO8601`
- Severity: `WARN`
- Summary: Date/time is not valid ISO8601.
- Emit when:
  - Date-like columns (e.g. `collection_date`, `isolation_date`) contain values that don't parse as `YYYY-MM-DD` or full ISO8601.
- Why it matters:
  Ambiguous dates ("10/3/25", "Spring 2024") hurt reuse and trigger curator follow-up, even if they don't hard-block the deposit.
- Engine support:
  - attempt parse; if fail, emit.

### `GEO.REQ.MISSING_PROCESSED_DATA`
- Severity: `WARN`
- Summary: Processed/quantitative data not found.
- Emit when:
  - You have raw sequencing files but cannot find per-sample processed data
    (counts tables, peaks, coverage tracks, etc.).
- Why it matters:
  GEO expects processed, quantitative output, not just raw reads or "top 50 genes."
  Curators will ask for it, which delays release.
- Engine support:
  - heuristic: raw fastqs exist, but no processed outputs for those same sample_ids.

---
