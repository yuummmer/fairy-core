# ADR-0005: Bundles as first-class output (BagIt first)

**Date:** 2025-12-30
**Status:** Proposed
**Deciders:** Jennifer Slotnick
**Tags:** architecture, packaging, handoff, bagit

## Update (2026-01-05)

Clarifications to the original proposal:
- Preflight is intended to be universal operator mode by design; the current GEO TSV-specific implementation will move under `preflight geo` / profiles.
- Bundling remains invoked from preflight (unchanged).
- This ADR accepts the architecture decision (packagers/bundles as first-class) while keeping BagIt implementation details as "next steps" since implementation has not yet started.

## Context

### How FAIRy operates today

FAIRy has three commands with distinct purposes:

- **`fairy validate`** — The engine command: runs checks and produces validation reports
- **`fairy preflight`** — The human-friendly entrypoint by design, but today it's GEO TSV-specific; it will become profile-based + output-dir oriented
- **`--bundle bagit`** (planned) — Optional delivery format: packages inputs + outputs for transfer

**Mental model:** `validate` = checks; `preflight` = checks + outputs + guidance; `bundle` = delivery format (optional)

**Note:** Preflight is intended to be universal operator mode. The current GEO-specific implementation will move under `preflight geo` / profiles as the command evolves to be profile-based.

For detailed command documentation, see [CLI usage](../docs/cli.md).

### The packaging need

Some partners require a *handoff package* with integrity guarantees (checksums, standardized folder structure) independent of the repository-specific validation rules. BagIt (RFC 8493) is a widely used packaging format in digital preservation / collections workflows and is a likely requirement for museum/archival users and other partners in digital preservation contexts.

We want to support packaging without conflating it with validation rulepacks, and integrate it naturally into the existing `fairy preflight` workflow.

## Decision

Introduce a new concept in FAIRy-core: **Packagers (aka Exporters)**.

**Naming:**
- **User-facing term**: Bundle
- **Internal term**: Packager interface

- **Rulepacks** define validation rules and may optionally *recommend or require* one or more packagers.
- **Packagers** are responsible for producing a handoff-ready bundle from:
  - user inputs (datasets/files),
  - FAIRy-generated outputs (reports/manifest/etc),
  - packager configuration (algorithm/options).

**Workflow integration:**
- `fairy preflight` remains the primary user entrypoint (the human-friendly default, universal operator mode).
- Bundling is an output/export capability that can be invoked from preflight via `--bundle bagit` flag.
  - `fairy preflight ...` → creates the handoff-ready artifacts
  - `fairy preflight ... --bundle bagit` → additionally creates a handoff-ready container
- `fairy bundle` as a standalone command is a power-user convenience (optional for later implementation).
- Preflight produces the things you want to hand off; bundling produces the container you hand off in.

**Architecture decision (accepted):**
- Packagers/bundles are first-class concepts in FAIRy-core.
- Bundling remains invoked from preflight.
- Preflight is universal operator mode; current GEO-specific implementation will move under `preflight geo` / profiles.

**Next steps (implementation not yet started):**
- Ship **BagIt** as the first official packager implementation.
- Single CLI flag `--bundle bagit` on `fairy preflight` command.
- BagIt bundle validates with the chosen library's validation (e.g., `bagit.validate()`).
- Deterministic output paths (as specified in directory layout convention).

## Rationale

This separation provides several key benefits:

1. **Separation of concerns**: Validation (rulepacks) and packaging (packagers) are distinct operations with different requirements
2. **Workflow clarity**: Preflight (analysis) and bundling (packaging) are clearly separated, with preflight as the primary entrypoint
3. **Reusability**: One BagIt packager can serve multiple rulepacks/partners without duplication
4. **Extensibility**: New packaging formats (ZIP, RO-Crate, OCFL, repo-specific layouts) can be added without modifying rulepacks
5. **Clarity**: Rulepacks remain focused on validation logic, not packaging details
6. **Flexibility**: CLI-first design allows UI wrappers (FAIRy Lab) to call the same core/CLI later

## Goals

- Provide a reliable way to generate integrity-checked handoff bundles.
- Keep rulepacks focused on validation; avoid embedding packaging logic in domain rulepacks.
- Maintain a small, stable "packager" surface area that can expand later (ZIP, RO-Crate, OCFL, repo-specific layouts).
- Allow CLI-first usage; UI wrappers (FAIRy Lab) may call the same core/CLI later.

## Non-goals (v0)

- No "Teams" / multi-user collaboration features.
- No full BagIt Profile enforcement engine in v0.
- No repository-specific submission exporters beyond BagIt (ENA submission layout remains rulepack-specific guidance for now unless explicitly needed).

## Design Sketch

### Packager interface (conceptual)
A packager:
- receives `inputs`, `fairy_outputs`, and `config`
- writes to an output directory (or archive)
- returns a structured summary (paths written, algorithm used, validation status)

### BagIt structure convention

For BagIt (and similar formats), we adopt this convention:

- **Payload (data/)**: User-provided dataset files (inputs)
- **Tag files (bag metadata)**: FAIRy artifacts (report.json, report.md, manifest, provenance, etc.)

This separation keeps user data distinct from FAIRy-generated metadata and aligns with BagIt's intended use: payload contains the data being preserved, while tag files contain metadata about the bag itself.

### Directory layout convention

Output directory structure (provisional):

- **Preflight outputs**: `<out>/` (report.json, report.md, manifest, etc.)
- **Bundle outputs**: `<out>/bundles/<name>/` (e.g., `<out>/bundles/bag/` for BagIt)

Alternative considered: `<out>/<name>.bag/` (flatter structure). The `bundles/` subdirectory approach groups all bundles together and allows multiple bundles per preflight run if needed in the future.

### CLI

**Primary integration (v0):**
- Add `--bundle <packager>` flag to `fairy preflight` command
  - Example: `fairy preflight --rulepack ... --samples ... --files ... --out ... --bundle bagit`
  - After preflight completes, automatically packages inputs + outputs using the specified packager
  - Preflight remains the main user entrypoint; bundling is an optional output step
  - Aligns with FAIRy's command structure: `preflight` is the human-friendly default

**Power-user convenience (optional, later):**
- `fairy bundle --packager bagit --inputs ... --fairy-outputs ... --out ... [options]`
  - Standalone command for users who want to bundle without running preflight
  - Useful for re-packaging or bundling pre-existing FAIRy outputs
  - Keeps `validate` as the engine command, `preflight` as the human-friendly default

**Verification (optional, later):**
- `fairy verify-bundle --packager bagit --path ...`
  - Verify integrity of an existing bundle

### Rulepack interaction (optional)
Rulepacks may declare:
- `recommended_packagers: [bagit]`
or
- `required_packagers: [bagit]`
This is advisory/enforcement for UX and future automation; v0 may only surface it in messaging.

## Consequences

### Positive

- Adds a third axis to FAIRy's ecosystem: Core engine, Rulepacks, Packagers.
- Improves reusability: one BagIt packager can serve multiple rulepacks/partners.
- Clear separation between validation and packaging concerns.
- Enables integrity-checked handoff bundles for partners requiring them.
- Foundation for future packaging formats (RO-Crate, OCFL, etc.).

### Negative

- Adds complexity to the codebase with a new module and concepts.
- Requires careful scoping to prevent "packagers" from turning into a large plugin system too early.
- Additional dependency (bagit library) for BagIt support.
- Need to maintain packager interface stability as new formats are added.

### Neutral

- Rulepacks become slightly more complex with optional packager declarations.
- CLI gains a new optional flag (`--bundle`) on the existing `preflight` command (no new top-level command in v0).
- Packaging is optional; existing workflows continue to work without it.
- Maintains FAIRy's command structure: `validate` as engine, `preflight` as human-friendly default.

## Alternatives Considered

### Alternative 1: Embed BagIt inside a specific rulepack

**Pros:**
- Fast for a single partner/use case
- No new concepts needed

**Cons:**
- Duplicates effort if multiple rulepacks need BagIt
- Confuses "validation vs packaging"
- Harder to reuse across rulepacks
- Mixes validation logic with packaging logic

**Why not chosen:** This approach doesn't scale and violates separation of concerns. Multiple partners will need BagIt, and packaging logic should be reusable.

### Alternative 2: Make packaging a separate "packaging rulepack"

**Pros:**
- Fits existing mental model
- Uses existing rulepack infrastructure

**Cons:**
- Rulepacks become overloaded; packaging is not validation
- Confusing to have "validation rulepacks" and "packaging rulepacks"
- Packaging requires different operations (file copying, checksumming, manifest generation) than validation

**Why not chosen:** Rulepacks are designed for validation logic. Packaging is a fundamentally different operation that doesn't fit the rulepack model.

### Alternative 3: UI-first (Streamlit) packaging

**Pros:**
- Non-technical friendly
- Can provide rich UI for packaging options

**Cons:**
- Increases maintenance + scope
- Risks diverging logic from core
- CLI-first approach is more flexible and testable
- UI can be built on top of CLI later

**Why not chosen:** CLI-first design is more maintainable and allows UI to be built as a wrapper. This keeps core logic separate and testable.

## Notes

**Architecture (accepted):**
- Packagers/bundles as first-class concepts in FAIRy-core.
- Implementation will be in `src/fairy/packaging/` module (internal term: "Packager"; user-facing term: "Bundle").
- Primary CLI integration: `--bundle` flag on `fairy preflight` command.
- Rulepack schema will be extended to support optional `recommended_packagers` and `required_packagers` fields.

**Next steps (implementation not yet started):**
- BagIt packager will use the `bagit` Python library (RFC 8493 compliant).
- Optional later: standalone `fairy bundle` command for power users.
- Optional later: `fairy verify-bundle` command for bundle verification.
- Follow-up: Consider BagIt Profiles if/when a partner requires strict profile enforcement.
- Follow-up: Consider minimal FAIRy Lab wrapper only after at least one partner requests non-CLI operation.
