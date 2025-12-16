# Roadmap

This roadmap reflects current pilot-driven priorities. It is not a promise; priorities may shift based on what partners need next.

**Give feedback / request features:** please comment in [GitHub Discussions → Roadmap & Feedback](https://github.com/yuummmer/fairy-core/discussions) (pinned thread).

## Now (next 2–4 weeks)

### Pilot-critical reliability

- **Cross-platform deterministic outputs**
  - Make dataset hashing newline-stable (`\r\n` → `\n`) before sha256
  - Keep "volatile fields" normalization consistent in golden tests
- **Report stability**
  - Finalize JSON report schema v1 (and document backwards compatibility story)
  - Ensure markdown output stays readable (caps + clear "showing first N" messaging)

### High-value validation features (pilot-driven)

- **Regex / pattern rule type** (for ID validation and other pattern matching needs)
- **URL normalization + validation** (scheme-less URLs like `www.` and safe normalization)
- **Remediation links**
  - Keep JSON as the full fidelity source of truth
  - Markdown shows capped list + clear note that full list is in JSON
  - Apply remediation links for "row-level failures only" (nullish rows); do not attach remediation to missing-columns failures

### Rulepack authoring + community readiness

- Document rule config keys that have real UX impact:
  - `remediation_link_column`
  - `remediation_link_label`
  - link rendering rules + cap behavior
- Improve CLI error handling for common rulepack mistakes (bad paths, missing inputs, missing rulepack, etc.)

**Definition of done for "Now":**

- Example rulepack uses regex + remediation links and produces clean JSON + readable markdown output.
- Darwin Core example repo exists and is runnable with sample outputs.

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
