# CLI usage

FAIRy-core exposes a CLI for running validation checks on datasets.

## Basic usage

The main entry point is the `fairy` command:

```bash
fairy <command> [options]
```

To see all available commands:

```bash
fairy --help
```

To check the version:

```bash
fairy --version
```

## Command overview

FAIRy has three main commands, each with a distinct purpose:

### `fairy validate` — The engine command

**Purpose**: Evaluate rules against inputs and produce a validation result. Think: "run the checks."

- **Inputs**: Dataset files + rulepack
- **Output**: Validation report object / report files (minimal opinions about "handoff" or "where to put outputs")
- **Use when**: Iterating on a rulepack, fast checks in CI, or when you don't need the full "preflight" workflow

### `fairy preflight` — The human-friendly default

**Purpose**: A guided workflow on top of validate. Think: "prepare this dataset for submission/handoff."

- **Includes**: Running validate, writing standard FAIRy artifacts (report.json/md, manifest, provenance, etc.), nicer summaries, next steps, warnings about common gotchas
- **Use when**: This is the main user-facing command for humans preparing datasets for handoff
- **Future**: Will support `--bundle bagit` flag to create handoff-ready containers (see [ADR-0005](../decisions/0005-packaging-as-first-class-packagers.md))

### `--bundle bagit` (optional, on preflight) — The delivery format

**Purpose**: Package inputs + FAIRy artifacts for transfer. Think: "wrap it so I can ship it."

- **Use when**: You need a handoff-ready container with integrity guarantees
- **Status**: Planned feature (see [ADR-0005](../decisions/0005-packaging-as-first-class-packagers.md))

**Mental model:**
- `validate` = checks
- `preflight` = checks + outputs + guidance
- `bundle` = delivery format (optional)

**Positioning:**
- Most users should run `preflight`
- Use `validate` for automation, rulepack development, or CI
- This keeps UX coherent and avoids command sprawl

## Commands

### `fairy validate`

Validate one or more datasets against a rulepack. This is the primary command for custom rulepack validation.

#### Basic usage (single input)

```bash
fairy validate path/to/data.csv \
  --rulepack path/to/rulepack.yaml \
  --report-json out/report.json
```

#### Multi-input usage

Validate multiple tables with named inputs:

```bash
fairy validate \
  --rulepack path/to/rulepack.yaml \
  --inputs artworks=artworks.csv \
  --inputs artists=artists.csv \
  --report-json out/report.json
```

#### Options

- `--rulepack` (required): Path to YAML or JSON rulepack file
- `--inputs name=path` (repeatable): Named input tables for multi-input validation
- `--report-json`: Path to write JSON report
- `--report-md`: Path to write Markdown report

**Legacy mode:** You can also provide a single positional input (file or folder):

```bash
# Single file (becomes table named "default")
fairy validate data.csv --rulepack rulepack.yaml --report-json out.json

# Folder (each CSV becomes a table named by its filename stem)
fairy validate data_folder/ --rulepack rulepack.yaml --report-json out.json
```

#### Exit codes

- `0`: Validation passed (no FAIL findings)
- `1`: Validation failed (one or more FAIL findings)
- `2`: Error (invalid arguments, missing files, etc.)

### `fairy preflight`

Run pre-submission validation for GEO-style bulk RNA-seq datasets. This command expects specific TSV files (samples.tsv and files.tsv).

#### Usage

```bash
fairy preflight geo \
  --rulepack path/to/rulepack.json \
  --samples path/to/samples.tsv \
  --files path/to/files.tsv \
  --out-dir out/
```

#### Options

- `--rulepack` (required): Path to JSON rulepack file
- `--samples` (required for geo profile): Path to samples.tsv (tab-delimited sample metadata)
- `--files` (required for geo profile): Path to files.tsv (tab-delimited file manifest)
- `--inputs` (required for generic/spellbook profiles): Two input paths (e.g., `--inputs A.csv B.csv`)
- `--out-dir` (required): Output directory for handoff-ready artifacts (report, manifest, markdown, etc.)
- `--fairy-version`: Version string to embed in attestation (default: current FAIRy version)
- `--param-file`: Path to YAML file with tunable parameters (see [Parameter files](./params.md) for details)

The command generates multiple artifacts in the output directory:
- `preflight_report.json`: The main validation report
- `preflight_report.md`: Human-readable Markdown summary
- `manifest.json`: Manifest with file provenance
- `artifacts/inputs_manifest.json`: Input file metadata

#### Legacy

The `--out` option provides backward compatibility with older invocation patterns. It writes a single JSON report file (and a corresponding `.md` file) instead of the full handoff-ready artifact set.

**Old invocation pattern:**

```bash
fairy preflight \
  --rulepack path/to/rulepack.json \
  --samples path/to/samples.tsv \
  --files path/to/files.tsv \
  --out path/to/report.json
```

**What `--out` does:**
- Writes the JSON report to the specified file path
- Writes a Markdown report to the same location with `.md` extension
- Creates a `manifest.json` in the same directory as the report file
- Does not create the full `artifacts/` directory structure

**Note:** Prefer `--out-dir` for new workflows as it produces the complete set of handoff-ready artifacts.

### `fairy rulepack`

Validate a rulepack's YAML schema without executing validation. Useful for checking rulepack syntax.

#### Usage

```bash
fairy rulepack --rulepack path/to/rulepack.yaml
```

#### Options

- `--rulepack` (required): Path to YAML rulepack file
- `--inputs name=path` (optional, repeatable): Parse and display input mappings
- `--param-file` (optional): Path to params file

This command only validates the rulepack structure; it does not run validation on data.

## Examples

### Single table validation

```bash
fairy validate \
  --rulepack demos/rulepacks/penguins.yml \
  --inputs default=tests/fixtures/penguins_small.csv \
  --report-json out/penguins-report.json \
  --report-md out/penguins-report.md
```

### Multi-table validation with foreign keys

```bash
fairy validate \
  --rulepack tests/fixtures/art-collections/rulepack.yaml \
  --inputs artworks=tests/fixtures/art-collections/artworks_pass.csv \
  --inputs artists=tests/fixtures/art-collections/artists.csv \
  --report-json out/art-collections-report.json
```

### GEO preflight check

```bash
fairy preflight geo \
  --rulepack src/fairy/rulepacks/GEO-SEQ-BULK/v0_1_0.json \
  --samples demos/scratchrun/samples.tsv \
  --files demos/scratchrun/files.tsv \
  --out-dir out/
```

## Getting help

For command-specific help:

```bash
fairy validate --help
fairy preflight --help
fairy rulepack --help
```

## See also

- [Getting started](./getting-started.md) for installation and first steps
- [Parameter files](./params.md) for using `--param-file` to pass tunable parameters
- [Rule types reference](./rule-types.md) for complete documentation on all available rule types
- [Reporting](./reporting.md) for report structure details
- [Kata gallery](./katas/index.md) for example workflows
