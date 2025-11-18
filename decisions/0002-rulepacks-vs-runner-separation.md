# ADR-0002: Rulepacks vs runner separation

**Status**: Accepted
**Date**: 2025-09-XX
**Deciders**: Project maintainers
**Tags**: architecture, validation, extensibility

## Context

FAIRy-core needs to validate research datasets against repository-specific requirements (GEO, SRA, Zenodo, etc.). Each repository has different rules, and these rules evolve over time. We need an architecture that:

- Allows non-programmers (data stewards, curators) to define or modify validation rules
- Enables versioning and sharing of rule sets independently from the codebase
- Supports multiple repositories with different rule requirements
- Keeps the validation engine generic and reusable
- Makes it easy to add new validation rule types without changing existing rule definitions

## Decision

We separate validation logic into two distinct components:

1. **Rulepacks** (declarative data): YAML/JSON files that define what to validate
   - Contain metadata (id, version, description)
   - Define resources (file patterns) and associated rules
   - Specify rule types (enum, required, unique, foreign_key, range, etc.) with configuration
   - Are version-controlled, shareable, and editable by non-programmers

2. **Runner** (imperative code): The execution engine that interprets rulepacks
   - Loads and parses rulepack files
   - Matches resources to input files by pattern
   - Executes rule-specific check functions (e.g., `check_enum`, `check_required`)
   - Aggregates results into standardized reports
   - Is generic and works with any valid rulepack

The runner (`src/fairy/validation/rulepack_runner.py`) implements a fixed set of check types (enum, required, unique, foreign_key, range, url, etc.), while rulepacks declare which checks to apply to which files with what parameters.

## Rationale

This separation provides several key benefits:

1. **Extensibility**: New repositories can be supported by creating new rulepack files without modifying code
2. **Versioning**: Rulepacks can be versioned independently (e.g., `GEO-SEQ-BULK/v0_1_0.json`) and evolve as repository requirements change
3. **Accessibility**: Data stewards and curators can create or modify rulepacks without Python knowledge
4. **Reusability**: The same runner engine validates against any rulepack, reducing code duplication
5. **Testability**: Rulepacks can be tested independently, and the runner can be tested with fixture rulepacks
6. **Licensing flexibility**: Rulepacks are licensed CC0 (public domain) while the runner is AGPL, allowing rulepacks to be freely shared and modified

The alternative of hardcoding validation logic for each repository would require code changes for every rule update, making the system less flexible and harder to maintain.

## Consequences

### Positive

- **Repository-specific rulepacks**: Each repository (GEO, SRA, etc.) can have its own rulepack that evolves independently
- **Easy rule updates**: Repository requirements can be updated by modifying YAML/JSON files, not code
- **Community contributions**: Non-programmers can contribute rulepacks for new repositories or improved rules
- **Version control**: Rulepack versions are explicit and can be referenced in reports and attestations
- **Separation of concerns**: Validation logic (what to check) is separate from execution logic (how to check)
- **Multi-input support**: The runner can handle multiple tables and cross-table rules (e.g., foreign keys) because it loads all inputs before applying rules

### Negative

- **Limited expressiveness**: Rulepacks can only express checks that the runner supports. Adding new check types requires code changes to the runner
- **Schema evolution**: Changes to the rulepack schema require migration of existing rulepacks or backward compatibility handling
- **Validation overhead**: The runner must parse and validate rulepack structure before execution
- **Two code paths**: Currently there are two runners (`rulepack_runner.py` for generic validation and `validator.py` for GEO preflight), which creates some duplication

### Neutral

- **Rulepack format**: Currently supports both YAML and JSON, with YAML being more human-readable for rule authors
- **Backward compatibility**: The runner supports both old schema (rules with patterns) and new schema (resources with patterns) to ease migration
- **Rule execution**: Rules are executed sequentially per resource, which is deterministic but could be parallelized in the future

## Alternatives Considered

### Alternative 1: Hardcode validation logic per repository

**Pros:**
- Simpler initial implementation
- Type safety at compile time
- No need to parse/validate rulepack files

**Cons:**
- Code changes required for every rule update
- Difficult for non-programmers to contribute
- Code duplication across repositories
- Harder to version and share rule sets

**Why not chosen:** This approach doesn't scale to multiple repositories and makes it difficult for domain experts (curators, data stewards) to maintain rules without developer involvement.

### Alternative 2: Domain-specific language (DSL) for rules

**Pros:**
- More expressive than YAML/JSON
- Could support complex logic and conditionals
- Type checking and validation at rulepack level

**Cons:**
- Steeper learning curve for non-programmers
- Requires parser/interpreter implementation
- More complex tooling and debugging
- Overkill for current validation needs

**Why not chosen:** The current rule types (enum, required, unique, etc.) are sufficient for repository validation needs. A DSL would add complexity without clear benefit.

### Alternative 3: Plugin system for custom check types

**Pros:**
- Allows users to define custom check types in Python
- More flexible than fixed set of check types
- Could enable repository-specific check implementations

**Cons:**
- Security concerns (arbitrary code execution)
- Requires Python knowledge, defeating the goal of non-programmer accessibility
- Versioning and distribution complexity
- Harder to audit and verify rule behavior

**Why not chosen:** Security and accessibility concerns outweigh the flexibility benefits. The fixed set of check types covers repository validation needs, and new types can be added to the runner when needed.

## Notes

- The runner currently supports these check types: `enum`, `required`, `unique`, `foreign_key`, `range`, `url`, `non_empty_trimmed`, `no_duplicate_rows` (aliased as `dup`)
- Rulepacks are stored in `src/fairy/rulepacks/` and licensed CC0-1.0 for maximum reusability
- The runner is in `src/fairy/validation/rulepack_runner.py` and implements the core validation loop
- There is ongoing work to unify the two runner implementations (`rulepack_runner.py` and `validator.py`) to reduce duplication
- Example rulepacks: `demos/rulepacks/penguins.yml`, `tests/fixtures/art-collections/rulepack.yaml`
