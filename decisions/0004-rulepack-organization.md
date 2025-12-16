# ADR-0004: Rulepack organization and composition

**Status**: Accepted
**Date**: 2025-12-15
**Deciders**: Project maintainers
**Tags**: rulepacks, versioning, composition, community

## Context

As FAIRy-core moves toward supporting community rulepacks, we need to establish clear patterns for:

- **Repository organization**: How to structure public rulepacks vs. private client overlays
- **Versioning**: How to version rulepacks independently from the FAIRy engine
- **Composition**: How multiple rulepacks can be combined and overridden
- **Rule ID management**: Preventing collisions when composing rulepacks from multiple sources

Without clear organization, we risk:
- Licensing confusion between public baselines and private client data
- Versioning conflicts when rulepacks evolve independently
- Silent rule overrides that break validation expectations
- Rule ID collisions that cause unpredictable behavior

## Decision

We will organize rulepacks using a clear repository structure, semantic versioning, prefixed rule IDs, and explicit composition semantics.

### Repository organization

**Core repositories:**
- `fairy-core`: Engine + CLI
- `fairy-lab`: UI/demo app

**Public rulepacks** (separate repositories, recommended):
- `fairy-rulepack-darwin-core`: Generic baseline for Darwin Core data
- `fairy-rulepack-obis`: OBIS-specific checks (if needed)

**Private client overlays** (private repositories):
- `fairy-client-pilot`: Example client pilot overlay
- `fairy-rulepack-client-private`: Future separation of data from rules (if needed)

This structure keeps licensing and sharing clean: public baselines remain reusable, while client overlays stay private.

### Versioning

**Rulepack versions:**

- Version the rulepack independently from FAIRy engine version
- Bump rulepack version when:
  - Adding new rules
  - Making rules stricter
  - Changing rule semantics
- Use semantic versioning meaningfully:
  - `0.x`: Can treat "minor" as "breaking" if desired (common for early projects)
  - `1.0+`: Normal semver rules apply once stable

**Rule IDs:**

- Always prefix rule IDs to prevent collisions across composed packs
- Examples:
  - `dwc_required_occurrenceID` (Darwin Core baseline)
  - `client_objectID_required` (Client overlay)
  - `obis_eventDate_parseable` (OBIS-specific)
- Prefixes are critical once multiple packs are composed together

### Rulepack composition

**Recommended rulepack format:**

Overlay rulepacks use an `includes` field to reference baseline packs:

```yaml
id: client-herbarium
version: 0.2.0
description: Client overlay on Darwin Core-ish baseline

includes:
  - id: darwin-core
    ref: "github:yuummmer/fairy-rulepack-darwin-core@v0.2.0"
    # Future: support semver ranges if desired

rules:
  - id: client_objectID_required
    type: required
    severity: fail
    config:
      pattern: "*.csv"
      columns: ["objectID"]
      remediation_link_column: resourceUrl
      remediation_link_label: "Open record in Portal"
```

**Merge semantics:**

1. Load includes in order (first → last)
2. Load local rules last
3. **Collision policy**: Rule ID collisions are an error by default
4. **Override mechanism**: Allow intentional overrides only if explicitly marked with `override: true`:

```yaml
rules:
  - id: dwc_required_occurrenceID
    override: true
    severity: fail
    ...
```

This policy provides:
- **Safety**: No silent overrides that could break validation
- **Flexibility**: Intentional override capability when needed (e.g., client needs stricter rules than baseline)
- **Explicitness**: Overrides are visible in rulepack definitions, making intent clear

**Decision rationale**: We chose this approach (collisions error unless `override: true`) over always-erroring on collisions because it allows legitimate use cases where clients need to override baseline rules (e.g., making a rule stricter or changing severity) while maintaining safety through explicit marking.

### Repository layout

**Public rulepack repository structure** (e.g., `fairy-rulepack-darwin-core`):

```
rulepacks/
  darwin-core/
    v0.1.0.yaml
    v0.2.0.yaml
data/
  minimal.csv
golden/
  report.pass.json
  report.fail.json
README.md
CHANGELOG.md
```

**Private overlay repositories** (e.g., client-specific overlays):

Same structure, but data can be minimal or redacted to protect client information.

## Rationale

**Repository separation:**
- Keeps public baselines reusable and shareable
- Maintains clear boundaries for licensing and privacy
- Allows independent evolution of baseline vs. client-specific rules

**Semantic versioning:**
- Enables rulepack consumers to understand compatibility
- Allows rulepacks to evolve independently from the FAIRy engine
- Provides clear signals about breaking changes

**Prefixed rule IDs:**
- Prevents collisions when composing multiple rulepacks
- Makes rule origin clear in validation reports
- Enables safe composition without namespace conflicts

**Explicit composition with collision detection:**
- Prevents silent overrides that could mask validation issues
- Makes composition behavior predictable and debuggable
- Allows intentional overrides when truly needed (e.g., stricter client requirements)

**Standard repository layout:**
- Makes rulepack structure predictable and discoverable
- Supports versioned rulepack files alongside test data
- Enables automated tooling and CI/CD workflows

## Consequences

### Positive

- Clear separation between public baselines and private overlays
- Independent versioning allows rulepacks to evolve at their own pace
- Prefixed rule IDs prevent collisions and make composition safe
- Explicit override mechanism provides safety while maintaining flexibility
- Standard layout makes rulepacks easier to discover and use
- Supports community contributions to public rulepacks

### Negative

- Requires discipline to use prefixes consistently
- Need to implement collision detection and override mechanism
- Repository proliferation (many small repos vs. monorepo)
- Version reference syntax needs to be implemented and maintained

### Neutral

- Can evolve override mechanism over time (start with "no collisions", add `override: true` later)
- Repository structure can be adapted if needed, but consistency is important

## Alternatives Considered

### Alternative 1: Monorepo for all rulepacks

**Pros:**
- Single repository to manage
- Easier to share code and utilities between rulepacks
- Simpler CI/CD setup

**Cons:**
- Mixes public and private code, complicating licensing
- Harder to version rulepacks independently
- Less clear boundaries for community contributions

**Why not chosen:** Repository separation provides cleaner licensing boundaries and allows independent versioning.

### Alternative 2: No prefix requirement for rule IDs

**Pros:**
- Simpler rule definitions
- Less verbose rule IDs

**Cons:**
- High risk of collisions when composing rulepacks
- Hard to debug which rulepack a rule came from
- Silent overrides become likely

**Why not chosen:** Prefixes are essential for safe composition and clear traceability.

### Alternative 3: Silent override by default (last wins)

**Pros:**
- Simpler merge semantics
- No need for collision detection

**Cons:**
- Silent overrides can mask validation issues
- Unpredictable behavior when order matters
- Hard to debug why a rule behaves differently than expected

**Why not chosen:** Explicit collision detection prevents bugs and makes composition behavior predictable.

### Alternative 4: Collisions always error (no override mechanism)

**Pros:**
- Simplest implementation
- Forces clear separation of concerns
- No ambiguity about override behavior
- Forces unique IDs forever, preventing any collision complexity

**Cons:**
- Cannot handle legitimate cases where client needs stricter rules
- Requires duplicating entire rule definitions to change severity
- Less flexible for real-world use cases
- May require workarounds when clients legitimately need to override baseline rules

**Why not chosen:** While simpler, this approach lacks flexibility for real-world scenarios where clients may need to override baseline rules (e.g., making a rule stricter or changing severity). The `override: true` mechanism provides safety through explicit marking while maintaining needed flexibility.

## Notes

- This ADR establishes the foundation for community rulepack support
- **Collision policy decision**: Collisions error unless `override: true` (chosen over always-erroring on collisions)
- Implementation should include both collision detection and the `override: true` mechanism
- Consider adding semver range support for `includes` refs in the future (e.g., `@^0.2.0`)
- Repository layout may evolve based on community feedback
- Consider creating a rulepack template repository to help contributors get started
