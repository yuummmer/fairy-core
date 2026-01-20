# ADR-0007: Profiles as workflow composition over rulepacks

**Status**: Proposed
**Date**: 2026-01-05
**Deciders**: Project maintainers
**Tags**: architecture, workflow, rulepacks, composition, ux
**Related ADRs**: ADR-0002 (Rulepacks vs runner separation), ADR-0004 (Rulepack organization and composition)

## Context

FAIRy rulepacks capture validation rules for specific standards and workflows (e.g., ENA, GEO, DwC-A, institution pilots).
As rulepacks grow, users face two problems:

1. **Discoverability**: "Which rulepack should I use for my task?"
2. **Repeatability**: The same workflow often needs consistent defaults (input naming, params, outputs/bundling) across runs.

Partners/pilots also ask for outcome-oriented workflows ("make this submission-ready") rather than a set of individual checks.
We want to avoid creating a new bespoke rulepack for every partner when many needs differ only by configuration.

## Decision

Introduce **Profiles** as a thin orchestration layer that composes existing **Rulepacks** plus workflow defaults.

- **Rulepacks** remain the unit of reusable validation logic.
  - **Rulepacks must be runnable standalone** (no profile required).
- **Profiles** define:
  - which rulepacks to run (with pinned versions/refs for domain profiles; flexible for generic)
  - expected inputs (filenames/aliases)
  - default parameters
  - output configuration (reports and optional bundle/packaging)
  - stable out-dir layout (reports + handoff artifacts) required for future `--bundle bagit`
- **Profiles must not contain validation logic** (only references + defaults).

Profiles come in two types:

1. **Domain profiles** (e.g., `geo`, `dwc`, `insdc`) — **Pinned recipes**
   - Pin specific rulepack versions for reproducibility
   - Provide stable, tested workflows for specific domains
   - Users get consistent, repeatable results

2. **Generic profile** — **Operator chassis**
   - Flexible workflow that accepts user-provided rulepack(s) or uses defaults
   - Acts as the universal operator mode for custom workflows
   - Does not pin rulepack versions; runs whatever the user specifies
   - Generic is a built-in profile shipped with fairy-core and serves as the base operator workflow

Profiles do **not** change the rulepack format, and rulepacks remain registry-listed and independently versioned.

## Decision Drivers

- **Improves UX**: "one command" entrypoints for common workflows.
- **Prevents sprawl**: Partner workflows can often be expressed as a profile that composes shared rulepacks.
- **Supports packaging/report defaults cleanly** without embedding them into every rulepack.
- **Enables support tiers**: we can define "officially supported profiles" with pinned dependencies and tests.

## Consequences

### Positive

- Clearer mental model (ingredients vs recipes)
- Easier docs and onboarding
- More stable public interface (profiles) while rulepacks evolve
- Reduces need for bespoke rulepacks when configuration differences suffice
- Enables outcome-oriented workflows ("make submission-ready") without changing rulepack architecture

### Negative

- Additional artifact type to maintain (profiles registry + docs)
- Requires conventions for naming, version pinning, and ownership (official vs community profiles)
- Need to define profile format and loading mechanism
- Profiles introduce an additional versioned surface area; we need policies for pinning/upgrading referenced rulepack versions

### Neutral

- Profiles are a new abstraction layer but don't change existing rulepack behavior
- Can start with a small set of official profiles and expand based on community needs

## Alternatives Considered

### Alternative 1: Create bespoke rulepacks for each partner/workflow

**Pros:**
- No new abstraction layer
- Each workflow is self-contained

**Cons:**
- Rulepack proliferation and duplication
- Harder to maintain shared validation logic
- Doesn't solve discoverability problem
- Configuration differences require full rulepack duplication

**Why not chosen:** Leads to maintenance burden and doesn't address the core problem of configuration vs. validation logic separation.

### Alternative 2: Embed workflow defaults into rulepacks

**Pros:**
- Single artifact type
- Workflow defaults travel with validation rules

**Cons:**
- Mixes concerns (validation logic vs. workflow configuration)
- Harder to reuse rulepacks in different workflows
- Doesn't solve discoverability for "which rulepack for my task?"

**Why not chosen:** Violates separation of concerns and makes rulepacks less reusable.

### Alternative 3: Use CLI flags/scripts to compose workflows

**Pros:**
- No new artifact type
- Flexible composition

**Cons:**
- Doesn't solve repeatability (users must remember flag combinations)
- Harder to document and share workflows
- No clear "official" vs. "community" distinction

**Why not chosen:** Doesn't provide the discoverability and repeatability benefits that profiles offer.

## Implementation Notes (Initial)

- Roll out incrementally, starting with one profile that wraps an existing rulepack to validate the UX.
- Profile definition format (YAML/JSON) referencing rulepack IDs + versions
- Start by wrapping existing rulepacks into profiles (e.g., `geo-bulk-seq-starter`) to validate the approach
- Define a small set of "official" profiles and treat others as community/experimental
- Profile format should include:
  - Profile metadata (id, version, description)
  - Rulepack references (with version pinning for domain profiles; optional/flexible for generic)
  - Input expectations (filenames/aliases/patterns)
  - Default parameters
  - Output configuration (report format, bundling options)

### Profile Types

**Domain profiles** (e.g., `geo`, `dwc`, `insdc`):
- Pin specific rulepack versions for reproducibility and stability
- Provide tested, repeatable workflows for specific submission standards
- Example: `geo` profile pins `geo-bulk-seq@v0.1.0`

**Generic profile**:
- Acts as the universal operator chassis
- Accepts user-provided rulepack(s) via `--rulepack` flag or uses sensible defaults
- Does not pin rulepack versions; flexible for custom workflows
- Example: `fairy preflight generic --rulepack path/to/custom.yaml ...`

### CLI Design for Profile Selection

**Subcommands are canonical**
- `fairy preflight <profile-id> ...` — Preferred way to run profiles (e.g., `fairy preflight geo --samples ... --files ...`)
- Provides clear discoverability and outcome-oriented workflows

**`--profile` is an alias (optional / for scripting)**
- `fairy preflight --profile <profile-id> ...` — Supported for scripting and flexibility

**`--rulepack` is an escape hatch (dev / advanced use)**
- `fairy preflight --rulepack <path> ...` — For development/testing and advanced use cases

**Legacy compatibility**
- Legacy GEO flags (e.g., `fairy preflight --samples ... --files ...` without profile/rulepack) temporarily supported
- Internally redirects to `fairy preflight geo`, emits deprecation warning, and shows replacement command
- Will be removed in a future release

**`validate` command**
- `fairy validate` remains unchanged — no profile subcommands
- In future, we may allow `validate --profile` for parity, but `validate` remains rulepack-first

- See Appendix A for initial placement options (non-normative)

## Non-goals

- Profiles are not a second rules language.
- Profiles must not contain validation logic (only references + defaults).
- Profiles should not include bespoke code per institution.
- Profiles do not replace rulepacks; they compose them.
- Rulepacks must remain runnable standalone without profiles.

## Notes

- This ADR builds on ADR-0002 (rulepack/runner separation) and ADR-0004 (rulepack organization) by adding a workflow composition layer.
- **Domain profiles** (geo, dwc, insdc) pin rulepack versions explicitly for reproducibility. This allows stable workflow interfaces while rulepacks evolve independently.
- **Generic profile** serves as the operator chassis and does not pin versions; it accepts user-provided rulepacks or uses defaults, making it flexible for custom workflows.
- Profiles may be distributed with fairy-core, but have their own `profile.version`.
- Consider a profiles registry similar to the rulepack registry for discoverability.
- Future work may include profile templates or generators to help users create custom profiles.

## Appendix A: Initial placement options (non-normative)

Profiles can live in different locations depending on their purpose and support level. Three approaches are anticipated:

### 1. Best Default: Profiles in `fairy-core` (Recommended for Initial Implementation)

Profiles live in a top-level `profiles/` directory within `fairy-core`:

```
fairy-core/
  profiles/
    geo-bulk-seq-starter/
      profile.yaml
      params.yaml
      README.md
      fixtures/   (optional)
    ena-submission-ready/
      profile.yaml
      params.yaml
      README.md
    institution-pilot/
      profile.yaml
      params.yaml
      README.md
```

**Why this is great early:**
- One place to document "the supported workflows"
- Profiles can be treated as part of the product surface area
- Profiles may be distributed with fairy-core, but have their own `profile.version` and pin rulepack versions explicitly
- Rulepacks still live in their own repos/registries; profiles just reference rulepacks + pinned versions

**Use when:** You want to market profiles as "supported by FAIRy" (at least initially).

### 2. Slightly More Scalable: Profiles in Separate Repos

Once you have many profiles, move them to dedicated repositories:

- `fairy-profiles` (official)
- `fairy-profiles-community` (community/experimental)

The CLI can point to a profile registry (similar to rulepack registries). This keeps core lean and lets the ecosystem grow without bloating `fairy-core`.

**Use when:** You have many profiles and want to keep `fairy-core` lean, or profiles are experimental/community-grown.

### 3. Institution-Specific Profiles in Private Repos

For institution-specific profiles that contain internal rules, URLs, or fixtures:

- Keep institution-specific profiles in private repos (e.g., `institution-fairy-profile`)
- Profiles reference public rulepacks when possible, and private rulepacks only when necessary
- This maintains clear boundaries between public and private profile content

**Use when:** Profiles are institution-specific, contain internal rules/URLs/fixtures, or need to remain private.

### Quick Rule of Thumb

- **If you want it to be "officially supported by FAIRy"** → put it in `fairy-core/profiles/` (at least initially)
- **If it's experimental or community-grown** → separate profiles repo
- **If it's institution-specific or contains private content** → private repo
