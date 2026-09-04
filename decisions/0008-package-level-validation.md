# ADR-0008: Package-level validation for incoming submission artifacts

**Status**: Proposed
**Date**: 2026-09-03
**Deciders**: Project maintainers
**Tags**: architecture, validation, rulepacks, packages
**Related ADRs**: ADR-0002 (Rulepacks vs runner separation), ADR-0005 (Bundles as first-class output), ADR-0007 (Profiles as workflow composition)

## Context

FAIRy today validates **tables**: named CSV/TSV inputs, filename globs that select which table a rule applies to, and check types that inspect columns and cells (`required`, `unique`, `enum`, and so on). That model fits metadata sheets and kata CSVs. It does not cover **incoming packages**: directories whose acceptance depends on which files and folders exist, not only on cell values in loaded tables.

Partners, journals, and repositories routinely require a submission tree to contain certain artifacts (documentation, data, code, manifests, and so on), including optional or stricter path patterns. The SORTEE proof of concept is the first consumer that made this gap concrete (for example README, data files, and scripts), but the missing capability is domain-generic.

Three current behaviors make this unsafe to bolt on without a decision:

1. **Silent skip.** `run_rulepack` in `src/fairy/validation/rulepack_runner.py` only evaluates rules whose `pattern` matches an input already in the inputs map. A required file that was never passed is not a FAIL; the rule never runs.
2. **CLI errors vs findings.** Missing `--samples`/`--files` or a missing path is typically exit code 2 (`FileNotFoundError` / `ValueError`), not a PASS/WARN/FAIL finding that can set `submission_ready`.
3. **Near-misses that are the wrong layer.** GEO `check_processed_data_present` / `check_paired_end_complete` look at **filenames listed in `files.tsv`**, not the filesystem. ADR-0005 packagers build **outgoing** BagIt (or similar) bundles. ADR-0007 profiles may name expected CLI inputs but must not contain validation logic.

We need a first-class way to declare and evaluate presence or absence of artifacts in an **incoming** package, without turning rulepacks into Python, without using packagers as validators, and without teaching profiles a second rules language.

## Decision drivers

- **Steward-authored rules.** Package requirements must live in declarative rulepacks (ADR-0002), not in profile code or CLI scripts.
- **Findings describe an inspected subject.** Missing artifacts (after FAIRy has a package root it can open) must be report findings (PASS/WARN/FAIL from rule `severity`), not silent skips. Missing *subject* (no directory to inspect, or the path is not an openable directory) is a usage/engine error (exit 2), not a finding. A report must not claim results about a package FAIRy never saw.
- **A directory is the natural subject.** Long-term FAIRy is “is this dataset/package ready for this handoff?” A folder on disk should be passable as that subject. We must not ossify a CLI whose only package UX is `--package-root` merely to protect today’s “positional dir = glob `*.csv`” shortcut.
- **Separation from packaging.** Incoming package checks are validation. Outgoing BagIt/RO-Crate creation stays with packagers (ADR-0005).
- **Separation from profiles.** A profile may pass the validation subject (a directory). Patterns, counts, and severities stay in the rulepack (ADR-0007).
- **Minimal v0.** Cover glob presence and minimum counts on a directory tree. No plugin check types, no full BagIt Profile engine, no content-type sniffing beyond path globs.
- **One runner for v0.** First implementation belongs on the generic rulepack runner, not a third engine and not the GEO `validator.py` dispatch table.

## Decision

Introduce **package-scoped rules** as a first-class rulepack section, evaluated once against an explicit **package root directory**. Presence checks are a new runner check type (`files_present`), implemented in the generic runner (`src/fairy/validation/rulepack_runner.py`).

### What is a package root

The package root is the directory treated as the incoming package (the tree whose layout the rulepack constrains). It is the **validation subject** for `package.rules`.

- The runner does **not** infer a package root from a bag of unrelated `--inputs` table paths.
- Table validation (existing `resources` / per-file rules) remains unchanged for table-only rulepacks.
- How the CLI *names* that directory is specified in [CLI: validation subject](#cli-validation-subject). Canonical form is a positional directory, not a required flag.

### CLI: validation subject

Today `fairy validate ./folder` means “load top-level `*.csv` as tables.” That is a table-centric shortcut, not a product definition of “subject.” If package validation could *only* be invoked via `--package-root`, we would keep the engine honest and the old shortcut intact, at the cost of a long-term CLI that hides the natural object (a package directory) behind a flag.

**Decision:** the rulepack declares *what to evaluate*; the positional path (when present) is the *subject*. Interpretation of a directory depends on whether the loaded rulepack has `package.rules`.

Canonical forms:

```bash
# Package-capable rulepack: the directory is the package
fairy validate ./submission --rulepack package-layout.yml --report-json out.json

# Table-only rulepack: unchanged — directory still means glob top-level *.csv
fairy validate ./csv_folder --rulepack penguins.yml --report-json out.json

# Single table file: unchanged
fairy validate data.csv --rulepack penguins.yml
```

Resolution when the rulepack has a non-empty `package.rules` list:

1. If `--package-root DIR` and a positional directory are both set and resolve to different paths, exit `2` (ambiguous subject).
2. If `--package-root DIR` is set, that directory is the package root (positional may be omitted).
3. Else if the positional INPUT is an existing directory, that directory is the package root.
4. Else exit `2` (no package subject). A positional CSV file is not a package root.

`--package-root` is an **escape hatch** for mixed or scripted runs (package tree here, tables from `--inputs` elsewhere). It is not the primary UX and must not be the only documented way to name a package directory.

Resolution when the rulepack has **no** `package` section:

- Positional directory keeps today’s meaning: load `*.csv` as tables (not recursive; not a package walk).
- `--package-root`, if passed, is a usage error (exit `2`) so we do not silently ignore a flag the rulepack cannot use. (Optional later: warn and ignore; v0 fail closed.)

Mixed rulepacks (`package.rules` plus table `resources`) in v0: the positional directory is the package root. Table files still come from `--inputs` unless a later change loads tables from the same tree using resource patterns. Do not silently treat “any CSV anywhere in the package” as today’s top-level glob; that glob is table-only-rulepack behavior.

This is **not** a silent skip of `package.rules`: if those rules exist and no directory subject is resolved, the process exits 2 before reporting.

### Rulepack shape (v0)

Package rules are **siblings** of table `resources`, not nested under a table glob. That is the mechanism that prevents silent skip: once a package root is supplied, these rules always run, independent of which CSVs were passed. They must not run—and must not be reported as PASS/WARN/FAIL—if there is no package root.

Illustrative rulepack (documentation, data, and code presence are examples of patterns a pack might require, not a built-in FAIRy policy):

```yaml
id: example-package-layout
version: 0.1.0
description: Example package presence checks

package:
  rules:
    - id: pkg_readme_present
      type: files_present
      severity: fail
      pattern: "README*"
      min_count: 1

    - id: pkg_data_present
      type: files_present
      severity: fail
      patterns:
        - "data/**"
        - "*.csv"
        - "*.tsv"
      min_count: 1

    - id: pkg_code_present
      type: files_present
      severity: fail
      patterns:
        - "code/**"
        - "*.R"
        - "*.py"
        - "*.ipynb"
      min_count: 1

    - id: pkg_data_csv_layout
      type: files_present
      severity: warn
      pattern: "data/*.csv"
      min_count: 1
```

Field notes (v0):

- `type`: only `files_present` in this ADR.
- `severity`: `fail` or `warn` (same contract as table rules). `fail` → report status FAIL; `warn` → WARN; otherwise PASS.
- `pattern` or `patterns`: glob(s) against each file’s path **relative to the package root**, with `/` separators. `*` does not cross `/`. `**` matches across directories. So `README.md` / `README*` are root-only; `**/README*` is any depth; `data/*.csv` and `code/*.R` are one level under those folders; `data/**` is any file under `data/`. Document this in `docs/rule-types.md` when implementing.
- `min_count`: minimum matching **files** (not directories). Default `1`. `min_count: 0` is allowed for inventory-only rules.
- Optional later (not v0): `max_count`, `exclude`, `match: files|dirs`.

A package-only rulepack may omit `resources` / table `rules`. Mixed rulepacks (package + tables) are allowed; v0 still expects named `--inputs` for the table half.

### Evaluation and findings

Package rules execute **once per run**, before or after table rules, as their own report resource block:

```json
{
  "name": "package",
  "path": "/abs/path/to/submission",
  "rules": [
    {
      "id": "pkg_readme_present",
      "type": "files_present",
      "severity": "fail",
      "status": "FAIL",
      "evidence": {
        "patterns": ["README*"],
        "min_count": 1,
        "match_count": 0,
        "matches": []
      }
    }
  ]
}
```

On PASS, `matches` lists relative paths (capped, deterministic sort) so reports stay useful.

**Subject vs content:** “You did not say which package to inspect” is not a validation finding. Findings are statements about a package FAIRy opened. Usage/engine errors (exit 2) mean the run did not inspect that subject; do not write a package resource block or `submission_ready` claim for it.

| Situation | v0 behavior |
| --- | --- |
| Package root provided; pattern matches `min_count` | PASS finding |
| Package root provided; too few matches; `severity: fail` | FAIL finding; contributes to `summary.fail` / `submission_ready: false` |
| Package root provided; too few matches; `severity: warn` | WARN finding; does not by itself block submission-ready |
| Rulepack has `package.rules` but no directory subject (no positional dir, no `--package-root`) | CLI/usage error, exit `2`. Message should say this rulepack needs a package directory (`fairy validate ./submission --rulepack …` or `--package-root`). Do **not** emit package FAIL findings, do **not** silent-skip `package.rules`, and do **not** write a report that implies the package was inspected. |
| Package path does not exist or is not a directory | CLI exit `2` (engine cannot open the subject). Same class as “input CSV not found.” |
| Rulepack has no `package` section | No package evaluation; positional directory keeps CSV-glob behavior; `--package-root` is exit `2` |
| `files_present` used but fairy-core too old | Existing `unknown_rule_type` FAIL (ADR-0002) **only if** the run actually reached package evaluation with a root. An old core that ignores the `package` key is a compatibility hazard (see below), not a substitute for exit 2. |

The runner must not convert “zero files matched this glob” into a Python exception or a silent empty `resources` entry. Zero matches on an **opened** tree are findings.

### Which runner and schema own v0

- **Runner:** generic `src/fairy/validation/rulepack_runner.py` and `fairy validate`. Add `files_present` to `CHECK_TYPES` (or a dedicated package dispatch that does not require a DataFrame).
- **Schema:** extend the **dict** rulepack the generic runner already understands (`resources` + top-level `id`/`version`). Add optional top-level `package.rules`.
- **Not v0:** GEO `src/fairy/core/services/validator.py` / `rna.py` check table; Pydantic `src/fairy/rulepack/schema.py` `load_rulepack` used by preflight (still `meta` + `rules`). Preflight/profiles may later take a directory subject and forward it as package root without duplicating check logic.
- **Not v0:** packagers (`src/fairy/core/services/bundles.py`).

Canonical CLI:

```bash
fairy validate ./submission --rulepack package-layout.yml --report-json out.json
```

Equivalent explicit form (scripts, mixed inputs):

```bash
fairy validate --package-root ./submission --rulepack package-layout.yml --report-json out.json
```

Profiles (later): a profile may pass the package directory as the validation subject. The profile YAML must not list artifact globs.

## Rationale

Package presence is a **validation** question (“does this incoming tree satisfy the rulepack?”). ADR-0002 already says new expressiveness is a new runner check type, not plugins and not hardcoded per-repository Python. A `package` section avoids overloading table `resources` patterns, which today mean “apply these cell checks to matching CSVs.”

Keeping evaluation on the generic runner keeps layout checks reusable across domains and avoids growing the GEO-specific dispatch list that ADR-0002 already wants to unify away.

The CLI treats a directory as the package subject when the rulepack has `package.rules` (`fairy validate ./submission --rulepack …`). That matches the product question “is this package ready?” without forcing `--package-root` as the only door. Table-only rulepacks keep the old positional meaning (top-level `*.csv`) so we do not break katas and CI. `--package-root` remains for disambiguation, not as the conceptual model.

If no directory subject can be resolved, that is “you asked for package validation but did not name a package,” not “this package is missing a required artifact.” Exit 2; do not put that case in the report.

## Alternatives considered

### Alternative 1: Encode presence as table `resources` patterns

Reuse `pattern: "README.md"` on a resource and `type: required`.

**Pros:** No new rulepack section; looks like existing globs.

**Cons:** Today a resource pattern only selects among **already-loaded tables**. Documentation and other non-table files are not tables; unmatched patterns skip. Folder `validate dir/` only loads `*.csv`. This reproduces the silent-skip bug.

**Why not chosen:** The execution model is table-scoped. Package presence is directory-scoped.

### Alternative 2: Put required files on the profile (expected inputs)

ADR-0007 already allows profiles to declare expected filenames/aliases.

**Pros:** No runner schema change; GEO-like UX (`--samples` / `--files`).

**Cons:** Patterns, `min_count`, and warn-vs-fail would live in profile YAML or Python. That is a second rules language and violates “profiles must not contain validation logic.” Rulepacks would no longer be runnable standalone.

**Why not chosen:** Conflicts with ADR-0007. Profiles may only wire the package root.

### Alternative 3: Treat this as packaging / BagIt verification (ADR-0005)

Validate incoming trees with `bagit.validate()` or a packager “verify” command.

**Pros:** Reuses the packager axis; BagIt has checksums and required tag files.

**Cons:** Incoming packages are not necessarily BagIt. ADR-0005 packagers consume **preflight output** to build **outgoing** bundles. Mixing incoming layout policy into packagers conflates validation and delivery and still would not give stewards YAML globs for arbitrary artifacts.

**Why not chosen:** Wrong axis. Optional later: after a FAIRy run, BagIt verify remains a packager concern.

### Alternative 4: Plugin or inline Python checks

Allow rulepacks to call custom functions for “is this a code file?”

**Pros:** Maximum flexibility.

**Cons:** Rejected in ADR-0002 (security, steward accessibility, distribution).

**Why not chosen:** Out of bounds. New types belong in the runner.

### Alternative 5: CLI-only conventions without rulepack types

Hardcode a fixed layout (for example “must have README”) in `fairy validate` when a directory is passed.

**Pros:** Fast for a single partner.

**Cons:** Not reusable across communities; not versioned with rulepacks; not CC0-shareable as rules.

**Why not chosen:** Fights ADR-0002 and ADR-0004 (rules as data).

### Alternative 6: Missing package subject as a FAIL finding

Emit `package_root_missing` FAIL (exit 1) so the case cannot be silent-skipped.

**Pros:** Fail-closed in the same report channel; easy to miss in CI that only checks exit 1 vs 0.

**Cons:** The report would state a validation outcome about a package that was never opened. That confuses “content of the package” with “invocation was incomplete,” and it does not match existing CLI contract (missing table path → exit 2).

**Why not chosen:** Incomplete invocation is usage/engine error (exit 2). Findings require an inspected package root.

### Alternative 7: Require `--package-root` forever (positional dir stays CSV-only)

Preserve `fairy validate ./folder` = glob `*.csv` for all rulepacks; package checks only via `--package-root`.

**Pros:** Zero ambiguity; smallest change to `docs/cli.md` and existing tests.

**Cons:** The natural subject of a growing share of FAIRy work (a package directory) is never the default argument. We would teach `--package-root` as the product CLI and later have to migrate everyone off it. That is compatibility theater: it protects a table-centric shortcut at the expense of the handoff-oriented UX.

**Why not chosen as the long-term model.** The flag may exist as an escape hatch; it must not be the canonical way to name a package directory.

### Alternative 8: Positional directory always means package; move CSV glob behind a flag

`fairy validate ./dir` always walks a package; table-only users pass `--tables-from-dir` or `--inputs`.

**Pros:** One meaning for a directory.

**Cons:** Breaks current validate katas/CI immediately, including rulepacks with no `package` section.

**Why not chosen for v0.** Table-only packs keep the glob. Package-capable packs reinterpret the same positional directory; that change is keyed off the rulepack the user already selected.

## Non-goals (v0)

- BagIt, RO-Crate, or OCFL **creation** or profile enforcement (ADR-0005).
- Validating file **contents** (documentation quality, CSV schema inside a data folder, script syntax). Pair with existing table rules when a matched path is a table.
- MIME sniffing, executable detection, or inferring file role from content.
- Recursively treating every positional folder as a package regardless of rulepack (see Alternative 8).
- Making `--package-root` the only supported way to name a package directory (see Alternative 7).
- GEO preflight / `files.tsv` filename heuristics as a substitute for filesystem presence.
- Profile-authored glob lists.
- Plugin check types.
- Unifying `rulepack_runner.py` and GEO `validator.py` (still desirable; not blocking this ADR).
- Changing dataset fingerprint / attestation ID formulas (ADR-0006) beyond hashing whatever inputs the run already attests.

## Compatibility and migration

- **Backward compatible** for rulepacks with no `package` key: behavior unchanged.
- **Additive schema:** unknown top-level keys should be ignored only if we document that `package` is reserved; older fairy-core that does not implement `files_present` should FAIL those rules with `unknown_rule_type` if they were placed under table `resources`. If an old runner **ignores** the entire `package` key, package rules would silently not run — **v0 must not ignore `package` once this ADR is implemented.** Until implementation ships, authors should not rely on `package` in production rulepacks.
- **Pydantic loader** (`fairy.rulepack.schema.Rulepack`) currently requires `meta` + `rules` and does not know `package` or `resources`. Preflight will not load package-capable packs until the loader is extended or `fairy validate` remains the first entrypoint. That extension is follow-up, not a silent change to GEO JSON packs.
- **Composition (ADR-0004):** `package.rules` IDs must be prefixed like other rules; collisions error unless `override: true` when `includes` lands. v0 can ship without `includes`.
- **Reports:** add a `package` resource block; JSON consumers should tolerate a resource that is not a table (no `rows`). Markdown writer should render package evidence (patterns, counts, sample paths).
- **CLI:** For rulepacks **without** `package.rules`, positional folder meaning stays “load top-level `*.csv`.” For rulepacks **with** `package.rules`, a positional directory is the package subject (`fairy validate ./submission --rulepack …`). `--package-root` is optional when the positional directory already names the package; required only when there is no such positional directory. Mixed packs: package root from the directory subject; tables from `--inputs` in v0.

## Consequences

### Positive

- Layout requirements are expressible in CC0 rulepacks without Python, for any domain that needs them.
- Missing artifacts show up as the same PASS/WARN/FAIL model as table rules. Incomplete invocation (no package to inspect) stays exit 2, so reports only describe packages that were opened.
- Clear boundary: profiles pass a directory; packagers still only export; runner owns globs. Canonical CLI is `fairy validate ./submission --rulepack …` for package-capable packs, so we do not freeze a flag-only UX.
- Path to mixed packs (package layout + table checks) without a third engine.

### Negative

- Directory meaning is now rulepack-dependent (CSV glob vs package root). Docs and `--help` must state that explicitly to avoid surprise.
- Second matching model (directory globs vs table filename globs) must be documented so authors do not put `files_present` under `resources`.
- Until the Pydantic loader learns `package`, preflight cannot load these rulepacks.
- Glob semantics (root vs recursive patterns, `**`, Windows paths) need tests and a short rule-types section.

### Neutral

- `CHECK_TYPES` grows by one.
- Unknown `files_present` on old cores fails closed (once rules are visible to that runner).
- **Artifact identity.** `files_present` evaluates package state at execution time. A PASS establishes presence for that run only. Package and file identity across runs is an attestation and fingerprinting concern (ADR-0006). Package-level validation must not imply that an artifact is unchanged since a previous run merely because its path is unchanged.

## Follow-up work

1. Implement `package.rules` + `files_present` in `rulepack_runner.py`; tests for PASS/WARN/FAIL on an opened tree, glob fixtures, and **no** package findings when the root is missing.
2. Document in `docs/rule-types.md` and a small kata/demo package-layout rulepack.
3. CLI: positional directory as package subject when `package.rules` exist; `--package-root` as escape hatch; exit `2` if neither yields an openable directory; table-only packs keep CSV glob. Tests for both interpretations of `./folder`.
4. Markdown/JSON report rendering for the `package` resource.
5. Later: `fairy preflight` takes the same directory subject; extend `rulepack/schema.py` when preflight should load these packs. Later still: mixed packs loading tables from the package tree via resource patterns (so one directory is enough for “handoff-ready”).
6. Later (not v0-blocking): `max_count`, excludes, and an explicit `match: root` flag if glob docs prove ambiguous.
7. Do not implement incoming layout checks inside `bundles.py`.

## Notes

- Inventory that motivated this ADR: package-level validation is not covered fully by ADR-0002, 0005, or 0007; GEO processed-file checks are table-listed names; table `required` means columns.
- First consumer / example: SORTEE proof of concept (documentation, data, and code presence). The engine and schema in this ADR are not SORTEE-specific.
