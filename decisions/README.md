# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) that document major design choices and their rationale for the FAIRy-core project.

## What are ADRs?

Architecture Decision Records are a way to capture important architectural decisions along with their context and consequences. They help:

- **Contributors**: Understand why certain design choices were made
- **Grant writing**: Provide evidence of thoughtful design and planning
- **Long-term memory**: Preserve institutional knowledge about why we did X instead of Y

## When to create an ADR

Create an ADR when making decisions that:

- **Affect the architecture**: Changes to major components, data models, or system boundaries
- **Have long-term impact**: Decisions that will be difficult or costly to reverse
- **Involve trade-offs**: Choices where multiple valid alternatives exist
- **Set precedents**: Patterns or approaches that will influence future decisions
- **Require explanation**: Decisions that might seem surprising without context

Examples:
- ✅ Choosing a validation architecture (rulepacks vs runner)
- ✅ Selecting a data format or schema design
- ✅ Deciding on licensing strategy
- ✅ Major API changes or deprecations
- ❌ Routine bug fixes or small refactorings
- ❌ Choosing between similar libraries for a single use case

## Format

Each ADR follows a standard template with the following sections:

- **Status**: Proposed, Accepted, Deprecated, or Superseded
- **Context**: The issue motivating this decision
- **Decision**: The change we're proposing or have made
- **Consequences**: What becomes easier, harder, or different because of this decision

## Index

| ID   | Title                                      | Status   | Date       | Evidence |
|------|--------------------------------------------|----------|------------|----------|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted | 2025-11-17 | (process established) |
| [0002](0002-rulepacks-vs-runner-separation.md) | Rulepacks vs runner separation | Accepted | 2025-09-XX | (core implementation) |
| [0003](0003-dataset-bundle-manifest.md) | Dataset bundle manifest with hash-based dataset_id | Proposed | 2025-11-17 | (partial: dataset_id in reports) |
| [0004](0004-rulepack-organization.md) | Rulepack organization and composition | Accepted | 2025-12-15 | (schema + loader) |
| [0005](0005-packaging-as-first-class-packagers.md) | Bundles as first-class output (BagIt first) | Proposed | 2025-12-30 | |

## Creating a new ADR

1. Copy `template.md` to create a new numbered ADR file (e.g., `0002-decision-name.md`)
2. Fill in the template with your decision details
3. Update this README to include the new ADR in the index
4. Set the status to "Proposed" initially, then update to "Accepted" after review
5. Optionally link to related issues or PRs in the "Notes" section

## When to update ADR status

### Proposed → Accepted

Update to Accepted when implementation work starts in a way that commits you:

- You create the milestone + issues and begin the first PR, or
- You merge the first scaffolding PR that embodies the decision (e.g., `--bundle` flag stub / interface), or
- You've explicitly decided "we will do it this way" and you're executing against it.

For example, ADR-0005 would be marked Accepted when you start or merge the first PR implementing bundling via `--bundle bagit` on preflight.

### Accepted → Superseded

Change to Superseded when a later ADR replaces it (and link to the new ADR in a short note).

### Accepted → Deprecated

Use Deprecated if the decision is no longer relevant, but not exactly replaced.

## How often to review ADRs

### 1) Review on release / milestone close (best)

Every time you cut a release or close a milestone, do a 5-minute pass:

- Any ADRs referenced by merged PRs in that milestone → mark Accepted
- Any ADRs contradicted by what shipped → mark Superseded (and write a new ADR)

### 2) Monthly "status sweep" (backup)

Once a month (or at the end of the month) skim the ADR index table:

- If something has been "Proposed" for >30–60 days with no work → either close it (Deprecated) or keep it Proposed but add a "revisit by" note.

## Evidence column

In the ADR index table, the "Evidence" column tracks what demonstrates the status:

- `Accepted (PR #123)` or `Accepted (Milestone Bundles v0)` — links to implementation
- `Superseded by ADR-0007` — links to replacement ADR
- `(partial: dataset_id in reports)` — indicates partial implementation
- Leave empty for Proposed ADRs with no work started yet

## References

- [ADR GitHub organization](https://adr.github.io/)
- [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
