# Bundle Manifest Schema (v1.0.0)

This document describes the `manifest.json` file that FAIRy generates alongside preflight reports. The manifest provides a structured record of the bundle contents, dataset identity, and provenance information.

## Schema Reference

- **Schema file**: [`schemas/manifest_v1.schema.json`](../schemas/manifest_v1.schema.json)
- **Schema ID**: See `$id` field in the schema file
- **Schema version**: `1.0.0`

## Where to Find the Manifest

The `manifest.json` file is automatically generated in the same directory as your preflight report:

- **CLI usage**: When you run `fairy preflight`, the manifest is written to the same output directory as your report JSON file
  ```bash
  fairy preflight --rulepack rulepack.json --samples samples.tsv --files files.tsv --out report.json
  # Creates: report.json, report.md, and manifest.json in the same directory
  ```

- **Export/UI usage**: When exporting bundles, the manifest is included in the bundle root directory

The manifest file is always named `manifest.json` and is located at the bundle root (same directory as the preflight report).

## Manifest Structure

The manifest follows a stable v1.0.0 schema with the following top-level structure:

```json
{
  "schema_version": "1.0.0",
  "dataset_id": "sha256:8d65bb798164160994a781b6882514260f0d9dae155ffe0365029212dd884167",
  "created_at_utc": "2026-01-01T12:34:56Z",
  "fairy_version": "0.2.0",
  "hash_algorithm": "sha256",
  "rulepack": {
    "id": "GEO-SEQ-BULK",
    "version": "0.1.0"
  },
  "source_report": "preflight_report.json",
  "files": [
    {
      "path": "preflight_report.json",
      "sha256": "abc123...",
      "bytes": 12345,
      "role": "report"
    }
  ]
}
```

## Required Fields

### `schema_version`

- **Type**: string
- **Value**: `"1.0.0"` (constant)
- **Description**: Schema version identifier for the manifest format

### `dataset_id`

- **Type**: string
- **Format**: `"sha256:<64-hex-chars>"`
- **Description**: Snapshot identity for the validated dataset. This represents the identity of the dataset snapshot (inputs + rulepack + params), not the bundle itself. The `dataset_id` matches the `dataset_id` field in the preflight report JSON.

**Example**: `"sha256:8d65bb798164160994a781b6882514260f0d9dae155ffe0365029212dd884167"`

**Use cases**:
- Deduplicating bundles containing the same logical dataset
- Linking datasets to submission forms or institutional systems
- Referencing a specific dataset version in documentation or README files

### `created_at_utc`

- **Type**: string
- **Format**: ISO 8601 UTC timestamp with 'Z' suffix
- **Description**: When the bundle was created/assembled

**Example**: `"2026-01-01T12:34:56Z"`

### `fairy_version`

- **Type**: string
- **Format**: Semantic version (e.g., `"0.2.0"`, `"0.2.0-rc1"`, `"0.2.0+abc123"`)
- **Description**: The version of FAIRy that created this bundle

**Example**: `"0.2.0"`

### `hash_algorithm`

- **Type**: string
- **Value**: `"sha256"` (constant)
- **Description**: Hash algorithm used for file integrity verification

### `rulepack`

- **Type**: object
- **Required fields**: `id`, `version`
- **Optional fields**: `sha256`
- **Description**: Information about the rulepack used for validation

```json
{
  "id": "GEO-SEQ-BULK",
  "version": "0.1.0",
  "sha256": "56187ff593c6a3fb23fda71de2707d52684cee3e972acf474c3aec985e2317ee"
}
```

### `source_report`

- **Type**: string
- **Description**: Relative path to the preflight report JSON within the bundle
- **Constraints**: Must be a relative path (not absolute), cannot contain `..` or backslashes

**Example**: `"preflight_report.json"` or `"report.json"`

### `files`

- **Type**: array of objects
- **Description**: List of files included in the bundle, each with metadata

Each file entry contains:

```json
{
  "path": "relative/path/from/bundle/root.ext",
  "sha256": "f965407ccaac8ee80953c634b7ad47a4c7441945dfebb8b5dabdb6657ed37165",
  "bytes": 12345,
  "role": "report"
}
```

#### File Entry Fields

- **`path`** (string, required): Relative path from bundle root. Must not be absolute, contain `..`, or contain backslashes.
- **`sha256`** (string, required): SHA-256 hash of file contents (64 hex characters). Used for integrity verification of bundle files.
- **`bytes`** (integer, optional): File size in bytes. May be omitted if expensive to compute.
- **`role`** (string, required): File role in the bundle. One of:
  - `"data"`: Data payload files (e.g., `.csv`, `.tsv`, `.fasta`, `.fastq`)
  - `"metadata"`: Metadata files (e.g., `manifest.json`, `samples.tsv`, `files.tsv`)
  - `"report"`: Validation reports (e.g., `preflight_report.json`, `report.md`)
  - `"log"`: Log files (e.g., `*.log`)
  - `"other"`: Other files that don't fit the above categories

## Optional Fields

### `attestation_id`

- **Type**: string
- **Format**: `"fairy:attest:<8-64-hex-chars>"`
- **Description**: Link to PASS attestation stamp. Only present when validation passed (no fail-level findings). This provides a verifiable attestation that the dataset passed validation.

**Example**: `"fairy:attest:abc123def456"`

### `provenance`

- **Type**: object
- **Description**: Additional provenance information about the bundle creation

```json
{
  "fairy_core_version": "0.2.0",
  "rulepack_source_path": "rulepack.json",
  "inputs": [
    {
      "name": "samples",
      "path": "samples.tsv",
      "sha256": "f965407ccaac8ee80953c634b7ad47a4c7441945dfebb8b5dabdb6657ed37165",
      "bytes": 12345
    },
    {
      "name": "files",
      "path": "files.tsv",
      "sha256": "8ec6eaeb72ce5d853b76876da578dc251d392176a9384544a8eaf6433964d9fe",
      "bytes": 6789
    }
  ]
}
```

#### Provenance Fields

- **`fairy_core_version`** (string, optional): Explicit FAIRy core engine version (same as `report.engine.fairy_core_version`)
- **`rulepack_source_path`** (string, optional): Relative path to the rulepack source file
- **`inputs`** (array, optional): List of input files with metadata
  - **`name`** (string, required): Input name (e.g., `"samples"`, `"files"`)
  - **`path`** (string, required): Relative path to the input file
  - **`sha256`** (string, required): SHA-256 hash of the input file (for integrity verification)
  - **`bytes`** (integer, optional): File size in bytes

## Relationship to Preflight Report

The manifest is closely related to the preflight report:

- **`dataset_id`**: Matches `report.dataset_id` exactly
- **`created_at_utc`**: Matches `report.generated_at` (same timestamp)
- **`fairy_version`**: Derived from `report.engine.fairy_core_version` or the CLI version
- **`source_report`**: Points to the preflight report JSON file in the bundle

This ensures consistency between the manifest and the report it describes.

## Example Manifest

See [`fixtures/manifest_v1/example.json`](../fixtures/manifest_v1/example.json) for a complete example.

## Validation

Manifests can be validated against the JSON Schema:

```python
import json
import jsonschema
from pathlib import Path

schema = json.loads(Path("schemas/manifest_v1.schema.json").read_text())
manifest = json.loads(Path("manifest.json").read_text())

jsonschema.validate(instance=manifest, schema=schema)
```

## Use Cases

### Dataset Deduplication

The `dataset_id` provides a stable snapshot identity for the logical dataset (inputs + rulepack + params). Downstream systems can use this to:
- Detect duplicate bundles
- Skip re-validation of identical datasets
- Link multiple bundles that represent the same dataset

### Bundle Integrity Verification

The `files` array with SHA-256 hashes (used for integrity verification) enables verification that:
- All expected files are present
- Files haven't been modified since bundle creation
- Bundle contents match the manifest

### Provenance Tracking

The manifest captures:
- Which rulepack version was used
- When the bundle was created
- Which FAIRy version generated it
- What files are included and their roles

This information is useful for:
- Reproducibility
- Debugging validation issues
- Compliance and audit trails
- Linking bundles to submission systems

## CLI Integration

When you run `fairy preflight`, the `dataset_id` is also displayed in the console output:

```
=== FAIRy Preflight ===
Rulepack:         GEO-SEQ-BULK@0.1.0
FAIRy version:    0.2.0
Generated at:     2026-01-01T12:34:56Z
Dataset ID:       sha256:8d65bb798164160994a781b6882514260f0d9dae155ffe0365029212dd884167
...
```

This makes it easy to reference the `dataset_id` without opening the manifest file.

## Related Documentation

- [Preflight Report Schema](reporting.md) - Details about the preflight report JSON structure
- [ADR-0003: Dataset bundle manifest](../decisions/0003-dataset-bundle-manifest.md) - Architecture decision record for the manifest design

