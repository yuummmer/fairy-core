# ADR-0003: Dataset bundle manifest with hash-based `dataset_id`

**Status**: Accepted
**Date**: 2025-11-17
**Deciders**: Project maintainers
**Tags**: architecture, storage, validation, export
**Related ADRs**: ADR-0001 (Preflight report schema), ADR-0002 (Bundle layout)  <!-- adjust as needed -->

## Context

Current FAIRy bundles include:
- A preflight report JSON
- A loose file list / manifest

However, they **lack a stable, explicit identifier for the dataset bundle itself** and a clear, structured manifest format. This creates several problems:

- No single, canonical `dataset_id` to reference in downstream systems
- Harder to verify bundle integrity beyond per-file checks
- Harder to deduplicate bundles that contain the same logical dataset
- Slight mismatch with the preflight report schema, which is already evolving toward more explicit provenance metadata

We already have a `compute_dataset_id()` function that can derive a content-based identifier from preflight contents.

## Decision

We will:

1. **Introduce a structured bundle manifest** (e.g., `manifest.json`) with:
   - `dataset_id` (string, format: `"sha256:<64-hex-chars>"`)
   - `created_at_utc` (ISO 8601 string)
   - `fairy_version` (semantic version string, e.g. `"0.2.0"`)
   - `files` (array of objects, one per file in the bundle)

2. **Define the `files` entries as:**

   ```jsonc
   {
     "path": "relative/path/from/bundle/root.ext",
     "sha256": "…",         // optional at first, can be added later
     "bytes": 123456,       // optional, if cheap to compute
     "role": "data|metadata|report|log|other"
   }
   ```

Populate `dataset_id` by reusing the existing `compute_dataset_id()` function, based on the preflight report JSON that is already included in the bundle. The manifest will not invent a new hash mechanism; it will expose the same dataset identifier in a canonical top-level field.

Include the manifest as a first-class artifact in all standard FAIRy bundles (CLI and UI flows).

## Rationale

**Content-addressable identification**

A hash-based `dataset_id` provides a stable, content-derived identifier for the dataset bundle, aligning with FAIRer data practices and reproducibility goals.

**Bundle integrity verification**

A structured manifest makes it easier to verify that a bundle is complete and unmodified (especially once per-file sha256 fields are fully populated).

**Deduplication support**

Downstream tools (HPC caches, institutional storage, registries) can use `dataset_id` to detect duplicate bundles and avoid unnecessary re-runs or re-uploads.

**Consistency with preflight report schema**

Surfacing the same `dataset_id` in both the preflight report and the bundle manifest keeps the model consistent and reduces confusion for users.

**Future extensibility**

A structured manifest gives us a natural place to hang additional provenance fields later (e.g., `source_repository`, `submission_target`, `rulepack_id`, `run_started_at`, etc.).

## Implementation Notes

The manifest schema is defined in [`schemas/manifest_v1.schema.json`](../../schemas/manifest_v1.schema.json). The manifest file (`manifest.json`) is written to the bundle root directory.

The manifest will be generated as part of the existing bundle creation step in FAIRy:

- Use `compute_dataset_id()` on the preflight report JSON to populate `dataset_id`.
- Capture `created_at_utc` at bundle assembly time.
- Read `fairy_version` from the core package version.
- Walk the bundle directory tree to build the `files` array.

In the initial implementation:

- `sha256` and `bytes` may be optional per file if this would be too expensive; we can add a config flag or later ADR for "full integrity manifest."
- `role` can be a small enum inferred from file paths:
  - `preflight_report.json` → `report`
  - `manifest.json` → `metadata`
  - `rulepack`, `logs`, etc. as needed

CLI:

- Consider adding `dataset_id` to the human-readable summary output.
- Optionally expose a `fairy bundle show <path>` command to print key manifest fields.

## Consequences

### Positive

- Users and integrators have a single, explicit `dataset_id` they can reference in README files, submission forms, or institutional systems.
- Easier to build higher-level registries or catalog views over FAIRy runs (e.g., "all bundles with dataset_id XYZ").
- Clearer story in docs, demos, and grants: FAIRy produces attested bundles with a canonical identifier and manifest.

### Negative / Risks

- We are committing to a `dataset_id` format and manifest shape that we may need to version later.
- Computing hashes for all files (if/when we enable that) could have performance implications on very large bundles.
- Any mismatch between the `dataset_id` in the preflight report and the manifest would be confusing; tests and tooling must ensure these stay in sync.

## Alternatives Considered

### Do nothing

Keep the existing loose manifest and no explicit `dataset_id`.

**Rejected:** makes deduplication and attestation harder and undermines future provenance stories.

### Introduce a non-hash, human-chosen ID

**Rejected:** more fragile, easier to collide, and undermines the "content-addressable" story.

### Compute a separate hash just for the manifest

**Rejected for now:** adds complexity without clear benefit; reusing the existing `compute_dataset_id()` keeps semantics aligned between preflight and bundle.
