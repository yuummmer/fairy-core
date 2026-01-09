# Roadmap

This roadmap reflects current pilot-driven priorities. It is not a promise; priorities may shift based on what partners need next.

**Give feedback / request features:** please comment in [GitHub Discussions → Roadmap & Feedback](https://github.com/yuummmer/fairy-core/discussions) (pinned thread).

_Last updated: 2026-01-08_

## Recently shipped

- **Regex / pattern rule type** — Validates string formats or detects forbidden patterns using regular expressions. Documented in [rule types reference](docs/rule-types.md).
- **Remediation links** — Rules can include `remediation_link_column` and `remediation_link_label` to provide clickable links for fixing validation failures. Links appear in both JSON and markdown reports (with capping in markdown). Documented in [reporting guide](docs/reporting.md).
- **URL normalization + validation** — URL rule type handles scheme-less URLs (e.g., `www.example.org` automatically normalized to `https://www.example.org`). Documented in [rule types reference](docs/rule-types.md).

## Now (next 2–4 weeks)

### Pilot-critical reliability

- **Preflight evolution to universal operator mode** (see [ADR-0007](decisions/0007-profiles-as-workflow-composition.md); bundling integration: [ADR-0005](decisions/0005-packaging-as-first-class-packagers.md))
  - Preflight is intended to be universal operator mode by design; current GEO TSV-specific implementation will move under `preflight geo` / profiles
  - Profiles as workflow composition over rulepacks
  - Preflight becoming profile-based + output-dir oriented
- **Manifest v1 (ADR-0003)**
  - Preflight emits `manifest.json` in standard outputs with dataset identity + provenance + file roles
  - Includes determinism tests
- **Cross-platform deterministic outputs**
  - Make dataset hashing newline-stable (`\r\n` → `\n`) before sha256
  - Keep "volatile fields" normalization consistent in golden tests
- **Report stability**
  - Finalize JSON report schema v1 (and document backwards compatibility story)
  - Ensure markdown output stays readable (caps + clear "showing first N" messaging)

### Rulepack authoring + community readiness

- Document rule config keys that have real UX impact:
  - `remediation_link_column`
  - `remediation_link_label`
  - link rendering rules + cap behavior
- Improve CLI error handling for common rulepack mistakes (bad paths, missing inputs, missing rulepack, etc.)

**Definition of done for "Now":**

- `fairy preflight` supports profiles (at least geo + generic) and writes to an output directory for handoff artifacts.
- Cross-platform deterministic outputs are stable (newline normalization + golden normalization locked by tests).
- JSON report schema v1 is finalized and documented (including backwards compatibility expectations).

## Next (after Now)

### Rulepack structure and composition

- Rulepack composition (`includes`) with collision detection
- Override mechanism (`override: true`) with clear precedence rules
- Support multiple rulepacks via CLI (either repeated `--rulepack` or composition-first approach)
- Semver range support for `includes` (e.g., `@^0.2.0`) if it materially helps use cases

### Testing + quality guardrails

- CI rulepack schema validation
- Rulepack "golden outputs" testing harness (esp. for community rulepacks)
- Expand remediation link support across additional rule types (unique/enum/range) as needed

### UX improvements (nice-to-have but high leverage)

- Better markdown formatting hierarchy (group by file, fold/limit long sections, clearer summaries)
- More actionable CLI guidance (e.g., "missing columns: X, Y; check your export mapping")

## Later / Ideas

- Conditional rules ("if one relation field is set, require all three") as a first-class rule type
- Plugin system for custom rule types (with security constraints)
- Registry/marketplace for rulepacks (discovery + trust tiers)
- CI/CD integrations (preflight in pipelines, webhook/report upload)
- Diff/migration tools for rulepacks and schema versions
- Non-tabular validation (JSON/XML schemas) when use cases demand it

## Rulepacks

### Bundled verified (ship with fairy-core)

These ship with fairy-core and are maintained as verified snapshots:

- **GEO-SEQ-BULK** (v0.1.0) — Bulk sequencing submissions to GEO
- (planned) Darwin Core baseline snapshot once example implementations stabilize

### Community (developed externally)

Community rulepacks live in their own repos (CC0 recommended) and can later be imported as verified snapshots.

Suggested repo naming:

- `fairy-rulepack-darwin-core`
- `fairy-rulepack-obis`

See [ADR-0004](decisions/0004-rulepack-organization.md) for the distribution model. If you decide to revise ADR-0004 based on community contribution goals, capture that as a new ADR ("ADR-000X: Rulepack contribution workflow v2") rather than editing history silently.

## How people can comment

- Use [GitHub Discussions](https://github.com/yuummmer/fairy-core/discussions) for roadmap commentary + feature requests.
- Convert agreed items into Issues (link back to the discussion comment).
- Keep ROADMAP.md as the curated "current plan," not a comment thread.
