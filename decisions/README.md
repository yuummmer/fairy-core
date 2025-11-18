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

| ID   | Title                                      | Status   | Date       |
|------|--------------------------------------------|----------|------------|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted | 2025-11-17 |
| [0002](0002-rulepacks-vs-runner-separation.md) | Rulepacks vs runner separation | Accepted | 2025-09-XX |
| [0003](0003-dataset-bundle-manifest.md) | Dataset bundle manifest with hash-based dataset_id | Proposed | 2025-11-17 |

## Creating a new ADR

1. Copy `template.md` to create a new numbered ADR file (e.g., `0002-decision-name.md`)
2. Fill in the template with your decision details
3. Update this README to include the new ADR in the index
4. Set the status to "Proposed" initially, then update to "Accepted" after review
5. Optionally link to related issues or PRs in the "Notes" section

## References

- [ADR GitHub organization](https://adr.github.io/)
- [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
