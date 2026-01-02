# ADR-0006: Dataset Fingerprint and PASS Attestation IDs

**Status:** Proposed
**Date:** 2026-01-01
**Deciders:** Jennifer Slotnick
**Tags:** architecture, validation, provenance, identity
**Related ADRs:** ADR-0003 (Dataset bundle manifest), ADR-0005 (Bundles as first-class output)

## Context

FAIRy needs a stable way to identify the exact dataset snapshot that was validated (inputs + configuration) and a clear, user-facing indicator when a dataset is "submission-ready" (i.e., passes validation against a specific rulepack and parameters).

External repositories and preprint servers often mint persistent identifiers (e.g., DOIs) only after a submission is approved/posted. FAIRy is not a PID authority, but should provide a comparable *internal* identity and an optional "stamp" when validation passes.

Users may validate data without bundling (e.g., single dataset uploaded directly into a repository UI). Therefore, tying identity or "submission-ready" signals exclusively to bundling would exclude common workflows.

Currently, FAIRy reports include:
- `dataset_id` (top-level, sha256 format) - content-addressed identifier based on inputs
- `summary.by_level` - counts of pass/warn/fail
- `attestation` (nullable, undefined structure) - exists in schema but not well-defined

The CLI already computes `submission_ready = (fail_count == 0)` for display, but this is not persisted in the report JSON.

## Decision

FAIRy will implement two core identity concepts, plus an optional bundle identity when bundling is used:

1. **Dataset Fingerprint (always generated):**
   The existing `dataset_id` field serves as the dataset fingerprint. It is a deterministic, content-addressed identifier representing the validated snapshot:
   - per-input file hashes (sha256 of bytes)
   - canonicalization algorithm version

   The dataset fingerprint (`dataset_id`) MUST be generated for every run (PASS or FAIL) and MUST change when any of the above inputs change.

   **Note:** Row/column counts (`n_rows`, `n_cols`) are NOT included in the fingerprint computation. These are derived statistics that may vary with parsing differences (delimiters, quoting, etc.) even when file bytes are identical. Row/column counts remain in `metadata.inputs.*` for UX/debugging purposes, but do not affect dataset identity.

   Computation details are documented in `metadata.dataset_id_method` (object with algorithm, canon_version, and includes fields) and `metadata.params` (parameterization hash, if applicable).

2. **PASS Attestation (generated only when validation passes):**
   When `summary.submission_ready == true` (i.e., `summary.by_level.fail == 0`), FAIRy will populate the `attestation` object with an **Attestation ID** that asserts:
   - this dataset fingerprint (`dataset_id`)
   - passes rulepack X (versioned) under params Y (or an explicit empty params hash)
   - issued at time T by FAIRy version V

   This attestation is scoped to the dataset snapshot and does not require bundling.

Additionally, when bundling is used (per ADR-0005):

3. **Bundle Identity (optional, only when bundling):**
   When users run `fairy preflight --bundle bagit`, FAIRy may generate a **Bundle ID** plus a file manifest for the packaged artifact (e.g., BagIt). This is separate from, and references, the PASS Attestation / Dataset Fingerprint.

## Implementation Sketch

### Report JSON Structure

**Always present:**
- `dataset_id` = `sha256:<hex>` (the dataset fingerprint)
- `summary.submission_ready` = boolean (`true` when `summary.by_level.fail == 0`)
- `metadata.dataset_id_method` = object (required) with:
  - `algorithm` = string (e.g., `"sha256"`)
  - `canon_version` = string (e.g., `"fairy-canon@1"` - canonicalization algorithm version)
  - `includes` = array of strings (e.g., `["inputs.*.sha256"]` - what fields are included in fingerprint)
- `metadata.params` = object (optional, includes `sha256` if parameters were used)

**When `summary.submission_ready == true`:**
- `attestation` = object with:
  - `attestation.id` = `fairy:attest:<short-hash>`
  - `attestation.issued_at` = ISO-8601 UTC timestamp
  - `attestation.scope` = `"dataset"`
  - `attestation.dataset_id` = reference to top-level `dataset_id`
  - `attestation.rulepack` = object (matches `metadata.rulepack` shape):
    - `id` = rulepack identifier
    - `version` = rulepack version
    - `sha256` = rulepack file hash (optional)
  - `attestation.params_sha256` = parameterization hash (if applicable)
  - `attestation.fairy_version` = FAIRy core version
  - `attestation.schema_version` = `"1.0.0"` (attestation schema version)

**When `summary.submission_ready == false`:**
- `attestation` = `null` (for backward compatibility with existing schema v1.0.x)

**Present only when bundling (per ADR-0005):**
- `bundle.id` = `fairy:bundle:<short-hash>`
- `bundle.format` = `"bagit"` (initially)
- `bundle.files[]` = array of file entries (relpath + sha256 + bytes)
- `bundle.attestation_id` = reference to `attestation.id`

### Schema Updates

1. Add `summary.submission_ready` (boolean, required)
2. Add `metadata.dataset_id_method` (object, required) with:
   - `algorithm` (string, required) - e.g., `"sha256"`
   - `canon_version` (string, required) - e.g., `"fairy-canon@1"`
   - `includes` (array of strings, required) - e.g., `["inputs.*.sha256"]`
3. Add `metadata.params` (object, optional) with `sha256` field
4. Define `attestation` object structure (currently nullable in schema; will remain nullable in v1.0.x, populated when `summary.submission_ready == true`, `null` otherwise):
   - `id` (string, required when present) - e.g., `"fairy:attest:<short-hash>"`
   - `issued_at` (string, required when present) - ISO-8601 UTC timestamp
   - `scope` (string, required when present) - e.g., `"dataset"`
   - `dataset_id` (string, required when present) - reference to top-level `dataset_id`
   - `rulepack` (object, required when present) - matches `metadata.rulepack` shape with `id`, `version`, and optional `sha256`
   - `params_sha256` (string, optional) - parameterization hash
   - `fairy_version` (string, required when present) - FAIRy core version
   - `schema_version` (string, required when present) - attestation schema version, e.g., `"1.0.0"`
5. Add `bundle` object structure (optional, for future bundling support):
   - `id` (string, required when present) - e.g., `"fairy:bundle:<short-hash>"`
   - `format` (string, required when present) - e.g., `"bagit"`
   - `files` (array, required when present) - array of file entries (relpath + sha256 + bytes)
   - `attestation_id` (string, required when present) - reference to `attestation.id`

### CLI Behavior

- `fairy validate` / `fairy preflight`:
  - always emit `dataset_id` (dataset fingerprint)
  - always emit `summary.submission_ready`
  - always emit `metadata.dataset_id_method` and `metadata.params` (if params used)
  - emit `attestation` as populated object when `summary.submission_ready == true`, or `null` otherwise

- `fairy preflight --bundle bagit`:
  - requires `summary.submission_ready == true` (either prior report or runs validate internally)
  - emits `bundle.*` and includes report(s) in bundle metadata

## Rationale

**Stable identity for "what was validated"**

Using `dataset_id` as the fingerprint provides a stable, content-addressed identifier that enables comparisons across iterations and environments. Computation details in `metadata` ensure reproducibility.

**Clear "submission-ready" signaling**

The `summary.submission_ready` boolean provides an explicit, machine-readable indicator that can be used by downstream tools, CI/CD pipelines, and UI workflows without parsing rule counts.

**PASS attestation without bundling**

Minting an attestation ID only when validation passes enables "submission-ready" messaging and provenance tracking without forcing users to create bundles. This supports workflows where users upload datasets directly to repository UIs.

**Separation of concerns**

Dataset fingerprint (always), attestation (on PASS), and bundle identity (on bundling) are distinct concepts that can evolve independently.

## Consequences

### Positive

- Provides stable identity for "what was validated," enabling comparisons across iterations.
- Enables "submission-ready" messaging without forcing bundling.
- Creates a foundation for future enhancements:
  - signed attestations
  - RO-Crate metadata mapping
  - associating external IDs (DOI/accession) with a fingerprint/attestation
- Clear separation between dataset identity, validation status, and packaging.

### Negative / Risks

- Requires defining canonicalization rules and versioning them (`metadata.dataset_id_method`).
- Schema changes to add `summary.submission_ready` and define `attestation` structure.
- Need to ensure `attestation` is either a populated object when `summary.submission_ready == true`, or `null` when not ready (schema validation or runtime checks).
- **Breaking change:** `dataset_id` computation will change to exclude `n_rows`/`n_cols` (currently included in implementation). This means existing `dataset_id` values will not match new computations. The `metadata.dataset_id_method` field will indicate which algorithm version was used. **Mitigation:** Increment `metadata.dataset_id_method.canon_version` (e.g., from `"fairy-canon@1"` to `"fairy-canon@2"`) when changing the computation, so consumers can distinguish old vs new fingerprints.

### Neutral

- `dataset_id` field name and format (`sha256:<hex>`) remain unchanged.
- `n_rows`/`n_cols` remain in `metadata.inputs.*` for UX/debugging (not part of fingerprint).
- `attestation` field already exists in schema but becomes well-defined.
- Bundle identity is deferred to ADR-0005 implementation.

## Alternatives Considered

1. **Mint IDs only on bundling**
   - Rejected: excludes "validate only" workflows; users often upload a single dataset directly.

2. **Mint only a run_id**
   - Rejected: non-deterministic; does not provide stable identity across runs or environments.

3. **Mint a DOI-like identifier**
   - Rejected: FAIRy is not a PID authority; may mislead users about global resolvability.

4. **Separate `dataset_fingerprint` field from `dataset_id`**
   - Rejected: adds confusion; `dataset_id` already serves as the fingerprint. Computation details live in `metadata`.

5. **Omit `attestation` field when not ready (vs `attestation: null`)**
   - **Pragmatic choice:** Keep `attestation: null` in schema v1.0.x for backward compatibility. Current reports already emit `attestation: null`, and the schema already allows nullability. Changing to omission would be a breaking change. Optionally move to omission in a future schema version bump (v2.0.0) if desired.

## Open Questions

- Exact attestation ID format (short hash vs structured string). Proposed: `fairy:attest:<first-16-hex-of-sha256(attestation_canonical_json)>`
- Which parameters are included in `metadata.params.sha256` (all vs allowlist). Proposed: all parameters used in validation.
- Where to store attestation/report within bundles for BagIt/RO-Crate (deferred to ADR-0005 implementation).
- Whether `metadata.dataset_id_method.canon_version` should include FAIRy version or be separate. Proposed: separate canonicalization version (e.g., `"fairy-canon@1"`) from `attestation.fairy_version`. The object structure allows adding new fields (e.g., `fairy_version`) without schema breaks.

## Notes

- This ADR extends ADR-0003 (which focuses on bundle manifests) by defining the report-level identity and attestation structure.
- Implementation should ensure `attestation` is a populated object when `summary.submission_ready == true`, or `null` otherwise (schema validation or runtime assertion). This maintains backward compatibility with existing schema v1.0.x which already allows `attestation: null`.
- The `attestation.rulepack` object structure matches `metadata.rulepack` for consistency (both use nested `id`, `version`, and optional `sha256` fields rather than flat `rulepack_id`/`rulepack_version` fields).
- **Implementation change required:** The `compute_dataset_id()` function in `src/fairy/core/services/provenance.py` currently includes `n_rows` and `n_cols` in the fingerprint computation. This must be updated to compute `dataset_id` from byte hashes only (plus canonicalization version). Row/column counts should remain in `metadata.inputs.*` for UX/debugging but not affect the fingerprint. **Important:** When making this change, increment `metadata.dataset_id_method.canon_version` (e.g., to `"fairy-canon@2"`) to distinguish the new computation from the old one.
- The `bundle` object structure is defined here but implementation is deferred to ADR-0005.
- Future work may include signed attestations using cryptographic signatures.
