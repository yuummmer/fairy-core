# Preflight Report Schema (v1.0.0)

This document describes the JSON report schema for `fairy preflight` command outputs.

## Schema Reference

- **Schema file**: [`schemas/preflight_report_v1.schema.json`](../schemas/preflight_report_v1.schema.json)
- **Schema ID**: See `$id` field in the schema file
- **Schema version**: `1.0.0`

## Report Structure

The preflight report follows a stable v1.0.0 schema with the following top-level structure:

```json
{
  "schema_version": "1.0.0",
  "generated_at": "2025-11-11T12:00:00Z",
  "dataset_id": "sha256:...",
  "metadata": {
    "inputs": { ... },
    "rulepack": { ... }
  },
  "summary": {
    "by_level": { "pass": 0, "warn": 1, "fail": 1 },
    "by_rule": { "CORE.ID.UNMATCHED_SAMPLE": "fail", ... }
  },
  "results": [ ... ],
  "_legacy": { ... }
}
```

### Top-Level Fields

- **`schema_version`** (string, required): Schema version identifier, currently `"1.0.0"`
- **`generated_at`** (string, required): ISO-8601 UTC timestamp with 'Z' suffix (e.g., `"2025-11-11T12:00:00Z"`)
- **`dataset_id`** (string, required): Aggregate SHA-256 hash of all inputs in format `"sha256:<64-hex-chars>"`
- **`metadata`** (object, required): Contains input and rulepack provenance
- **`summary`** (object, required): Aggregated statistics
- **`results`** (array, required): Rule-level validation results
- **`_legacy`** (object, optional): Legacy report structure for backward compatibility (deprecated)

### Metadata

#### `metadata.inputs`

Maps input names to full metadata objects:

```json
{
  "samples": {
    "path": "/path/to/samples.tsv",
    "sha256": "f965407ccaac8ee80953c634b7ad47a4c7441945dfebb8b5dabdb6657ed37165",
    "n_rows": 2,
    "n_cols": 10,
    "header": ["sample_id", "sample_title", "organism", ...]
  },
  "files": {
    "path": "/path/to/files.tsv",
    "sha256": "8ec6eaeb72ce5d853b76876da578dc251d392176a9384544a8eaf6433964d9fe",
    "n_rows": 3,
    "n_cols": 3,
    "header": ["sample_id", "layout", "filename"]
  }
}
```

#### `metadata.rulepack`

Rulepack provenance:

```json
{
  "path": "/path/to/rulepack.json",
  "sha256": "56187ff593c6a3fb23fda71de2707d52684cee3e972acf474c3aec985e2317ee",
  "id": "GEO-SEQ-BULK",
  "version": "0.1.0",
  "params_sha256": "..."  // optional, SHA-256 of canonical JSON params
}
```

### Summary

#### `summary.by_level`

Counts of rules by level:

```json
{
  "pass": 4,
  "warn": 1,
  "fail": 1
}
```

#### `summary.by_rule`

Mapping of rule ID to level (with fail > warn > pass precedence):

```json
{
  "CORE.ID.UNMATCHED_SAMPLE": "fail",
  "CORE.DATE.INVALID_ISO8601": "warn",
  "GEO.BIO.CONTEXT_MISSING": "pass",
  ...
}
```

### Results

Array of rule results, each containing:

```json
{
  "rule": "CORE.ID.UNMATCHED_SAMPLE",
  "level": "fail",
  "count": 1,
  "samples": [
    {
      "row": 2,
      "column": "sample_id",
      "message": "File references sample_id 'S999' not found in samples.tsv.",
      "hint": "Fix sample_id or add that sample to samples.tsv."
    }
  ]
}
```

- **`rule`** (string): Rule identifier
- **`level`** (string): One of `"pass"`, `"warn"`, `"fail"`
- **`count`** (integer): Number of violations (0 if level is "pass")
- **`samples`** (array): Up to 10 sample violations, sorted deterministically

#### Remediation links

When a rule is configured with `remediation_link_column`, the evidence includes remediation information:

```json
{
  "evidence": {
    "nullish": {
      "columns": ["primary_id"],
      "rows_by_column": {"primary_id": [1, 3]}
    },
    "remediation": {
      "column": "external_url",
      "label": "Open record in portal",
      "links": [
        {"row": 1, "url": "https://portal.example.com/record/1"},
        {"row": 3, "url": "https://portal.example.com/record/3"}
      ]
    }
  }
}
```

- **`remediation.column`** (string): The column name containing remediation URLs
- **`remediation.label`** (string): Human-readable label for the link
- **`remediation.links`** (array): List of remediation links, one per failing row
  - **`row`** (integer): 1-based row number
  - **`url`** (string): URL value from the remediation column (preserved as-is, may need `https://` prefix added for markdown rendering)

**Note**: While JSON reports include all remediation links, markdown reports are limited to the first 20 links per rule to keep report file sizes manageable. When more than 20 links exist, the markdown report shows a message indicating how many total links are available.

## Migration from Legacy Format

The legacy report structure (`attestation` + `findings`) has been replaced with the v1.0.0 schema. Use this mapping:

| Old Field | New Field |
|-----------|-----------|
| `attestation.run_at_utc` | `generated_at` |
| `attestation.inputs` | `metadata.inputs` |
| `attestation.rulepack_id` | `metadata.rulepack.id` |
| `attestation.rulepack_version` | `metadata.rulepack.version` |
| `attestation.fail_count` | `summary.by_level.fail` |
| `attestation.warn_count` | `summary.by_level.warn` |
| `attestation.submission_ready` | `summary.by_level.fail == 0` |
| `findings` | `results` |
| `findings[].code` | `results[].rule` |
| `findings[].severity` | `results[].level` (FAIL→fail, WARN→warn) |
| `findings[].details` | `results[].samples` |

### Backward Compatibility

The legacy structure is preserved in the `_legacy` field for temporary backward compatibility:

```json
{
  "_legacy": {
    "attestation": { ... },
    "findings": [ ... ]
  }
}
```

**⚠️ Deprecation Notice**: The `_legacy` field will be removed in v1.2.0 (or after 2 releases). Please migrate to the v1.0.0 structure.

## Deterministic Ordering

All arrays and object keys are sorted deterministically for reproducible reports:

- `results`: Sorted by `(meta.input, meta.column, rule, level)`
- `samples`: Sorted by `(row, column, stringify(value))`
- `metadata.inputs`: Keys sorted alphabetically
- `summary.by_rule`: Keys sorted alphabetically

## Example Report

See [`tests/golden/preflight.report.json`](../tests/golden/preflight.report.json) for a complete example.

## Validation

Reports can be validated against the JSON Schema:

```python
import json
import jsonschema
from pathlib import Path

schema = json.loads(Path("schemas/preflight_report_v1.schema.json").read_text())
report = json.loads(Path("report.json").read_text())

jsonschema.validate(instance=report, schema=schema)
```

## Markdown Reports

The CLI also generates human-readable Markdown reports alongside JSON. See the `--out` option in `fairy preflight --help`.

### Remediation links in markdown

When rules include remediation links, markdown reports render them as clickable links:

```markdown
- row 1, column 'primary_id', message: Missing value in required field 'primary_id.'
  [Open record in portal](https://portal.example.com/record/1)
```

URLs starting with `www.` automatically get an `https://` prefix for proper markdown link rendering. Empty or missing remediation link values are skipped.

**Link limit**: To keep markdown report files manageable, remediation links are limited to the first 20 links per rule. When a rule has more than 20 remediation links, only the first 20 are shown in the markdown report, with a message indicating the total count (e.g., "_Showing first 20 remediation links (of 45)._"). All links remain available in the JSON report.
