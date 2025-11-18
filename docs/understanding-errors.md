# Understanding FAIRy errors

This guide helps data stewards interpret FAIRy validation results and understand what needs to be fixed.

## What "PASS / WARN / FAIL" mean

FAIRy reports use three severity levels:

- **PASS**: The rule checked out correctly. No action needed.
- **WARN**: There's a potential issue that might cause problems during curation or reuse, but it won't block submission. Consider fixing these, but they're not urgent.
- **FAIL**: This will block submission or cause rejection. These must be fixed before the dataset can be submitted.

The `submission_ready` field in the report is `true` only when there are zero FAIL findings.

## Example errors and how to fix them

### Missing required field

**What you'll see:**
```
Rule: GEO.REQ.MISSING_FIELD
Level: FAIL
Where: samples.tsv: column 'library_strategy' is missing
```

**What it means:** A required metadata column is missing from your dataset.

**Why it matters:** Repository curators need this information to process your submission. Missing required fields will cause your submission to be rejected or delayed.

**How to fix:** Add the missing column to your `samples.tsv` file and fill in values for all rows. Check the repository's submission guidelines to see what values are allowed.

### Unmatched sample ID

**What you'll see:**
```
Rule: CORE.ID.UNMATCHED_SAMPLE
Level: FAIL
Where: files.tsv references sample_id 'S999' not found in samples.tsv
```

**What it means:** There's a mismatch between the sample IDs in your `samples.tsv` and `files.tsv` files. A file references a sample that doesn't exist in your metadata, or vice versa.

**Why it matters:** Every file in a submission must map to described metadata, and every described sample must have associated files. Mismatches stop curation because the curator can't tell which file belongs to which sample.

**How to fix:**
- If the sample ID in `files.tsv` is wrong, correct it to match an existing sample in `samples.tsv`
- If the sample is missing from `samples.tsv`, add a row with that sample's metadata
- If the file shouldn't be included, remove it from `files.tsv`

### Invalid date format

**What you'll see:**
```
Rule: CORE.DATE.INVALID_ISO8601
Level: WARN
Where: samples.tsv: row 5, column 'collection_date' contains '10/3/25'
```

**What it means:** A date field contains a value that's not in ISO 8601 format (YYYY-MM-DD).

**Why it matters:** Ambiguous dates like "10/3/25" (is that October 3rd or March 10th?) hurt data reuse and trigger curator follow-up, even if they don't hard-block the deposit.

**How to fix:** Convert the date to ISO 8601 format. For example:
- `10/3/25` → `2025-10-03` (if you're certain it's October 3rd, 2025)
- `Spring 2024` → `2024-03-21` (use a specific date, or leave blank if unknown)

### Paired-end file mismatch

**What you'll see:**
```
Rule: GEO.FILE.PAIRING_MISMATCH
Level: FAIL
Where: Sample 'S001' marked as PAIRED but missing R2 file
```

**What it means:** A sample is marked as paired-end sequencing, but one of the required read files (R1 or R2) is missing.

**Why it matters:** GEO explicitly requires both reads for paired-end libraries. Missing mates blocks acceptance.

**How to fix:**
- If the sample is actually single-end, change `layout` to `SINGLE` in `samples.tsv`
- If it's paired-end, ensure both R1 and R2 files are listed in `files.tsv` with matching `sample_id`

## Important note about dataset_id

**You'll never be asked to "fix the dataset_id"** — that's generated automatically by FAIRy based on your dataset's content. When FAIRy shows an error, it will always point to a file, column, or field you can actually change.

The `dataset_id` is a content-based fingerprint that uniquely identifies your dataset. It's useful for:
- Tracking which datasets you've already validated
- Detecting duplicate bundles
- Linking your dataset to submission forms or internal tracking systems

But you don't need to do anything with it unless you want to use it for tracking or deduplication.

## Getting help

If you encounter an error that's not covered here:
1. Check the [Error taxonomy](error_taxonomy.md) for a complete list of error codes
2. Review the `how_to_fix` field in the FAIRy report for specific guidance
3. Consult the repository's submission guidelines for field requirements
4. Open an issue in the FAIRy tracker if you believe the error is incorrect
