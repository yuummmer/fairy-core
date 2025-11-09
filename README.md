<!-- Project badges -->
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)
[![Rulepacks: CC0-1.0](https://img.shields.io/badge/Rulepacks-CC0%E2%80%911.0-lightgrey.svg)](src/fairy/rulepacks/LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-informational.svg)](#)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen.svg)](.pre-commit-config.yaml)

## 📸 Quick look

**Preflight (CLI)**
![FAIRy CLI preflight showing FAIL finding and submission_ready False](docs/assets/preflight_cli_before.png)

# ✨ FAIRy Core ✨

Local-first validator and packager for FAIR-compliant research datasets.
This repo contains the **core CLI** and rulepack support (e.g., GEO bulk RNA-seq).

- ✅ Validates tabular metadata against repository-specific **rulepacks**
- ✅ Emits **machine-readable** (JSON) and **human-readable** (Markdown) reports
- ✅ Writes **attestation & provenance**, with optional export bundle (zip)
- 🧪 Includes intentionally “failing” fixtures for smoketests
- 🚧 Early alpha; interfaces may change prior to v1.0

---
## 🌱 What is FAIRy?

- **Local-first**: All processing is on your machine. Your raw and fixed data never leave without your consent.
- **Flexible & Open**: Core validation engine, repository rule templates, and CLI are 100% open and community-driven.
- **Extensible**: Easily add new repository templates or contribute improved schemas/rules — keep up with the latest standards.
- **Practical**: Audit and fix real researcher pain points (dates, IDs, vocab, file names), export clean packages, avoid resubmission headaches.

---

## ⚙️ How Does It Work?

1. Create a new project workspace (all local).
2. Upload your dataset (CSV, TSV, FASTQ, Excel, JSON, etc.).
3. Choose your submission target(s): GEO, SRA, Zenodo, etc.
4. Validate & audit: FAIRy shows you errors, warnings, and actionable fixes.
5. Apply guided fixes on a working copy, or review/patch manually if preferred.
6. Export a submission-ready package for your target repository — no surprises, no guessing.
7. All fix history, audit logs, and provenance are saved in your local project.

---

## 🚀 Why Use FAIRy?

- No more “submission rejected, fix and resubmit” cycles.
- Safe for sensitive data: nothing sent to the cloud unless you choose.
- No lock-in: Integrate with your existing analysis notebooks/lab systems.
- Community-driven templates: transparent, up-to-date, and user-hackable.
- **For researchers**: Grad students, postdocs, and lab managers can save hours per submission.

> 👉 **Institutions and labs interested in pilots or dashboards — we’d love to hear from you.**
> Email **hello@datadabra.com** or open an issue with the label `pilot-inquiry`.
---

## Quickstart (90 seconds)
New: validate is now available alongside preflight — run custom rulepacks with --rulepack and get JSON/Markdown reports (see Penguins demo below).
> Requires Python **3.10+**. On Windows with WSL: use **Linux paths** (e.g., `/home/…`), not `\\wsl.localhost\…`.

```bash
# 1) Install (editable)
pip install -e .

# 2) Check the CLI
fairy --version

# 3) Run a preflight check (GEO bulk RNA-seq rulepack)
fairy preflight \
  --rulepack src/fairy/rulepacks/GEO-SEQ-BULK/v0_1_0.json \
  --samples  /path/to/samples.tsv \
  --files    /path/to/files.tsv \
  --out      out/report.json

# 4) Inspect the results
jq '.attestation.submission_ready, (.findings | length)' out/report.json
```
---
## 🐧 Rulepacks Quickstart (Penguins demo)
Try --rulepack on a tiny Palmer Penguins CSV and see JSON + Markdown reports.
```bash
# Create temp outputs
mkdir -p .tmp

# Run FAIRy with a demo rulepack (numeric ranges, enums, unique, dup)
python -m fairy.cli.validate tests/fixtures/penguins_small.csv \
  --rulepack demos/rulepacks/penguins.yml \
  --report-json .tmp/report.json \
  --report-md   .tmp/report.md || true

# Inspect results
cat .tmp/report.md

```
What this checks

- dup (alias no_duplicate_rows): duplicate rows by composite keys
- unique: uniqueness across one or more columns
- enum: values must be in an allow-list (supports normalize: {trim, casefold})
- range: numeric min/max (inclusive by default)

What you'll see (excerpt)

# FAIRy Validate Report

**Timestamp:** 2025-11-07T20:12:34Z
**Rulepack:** penguins-kata@0.1.0 (demos/rulepacks/penguins.yml)

## Summary
- PASS: 6
- WARN: 3
- FAIL: 1

## Findings for `tests/fixtures/penguins_small.csv`
### [FAIL] no_dups — no_duplicate_rows
Duplicates at rows [7]

### [WARN] bill_len_range — range
Out of bounds rows [8,10] (count=2)


YAML (excerpt)
```yaml
# demos/rulepacks/penguins.yml
id: penguins-kata
version: 0.1.0
resources:
  - pattern: "penguins*.csv"
    rules:
      - id: no_dups
        type: no_duplicate_rows
        keys: [species, island, bill_length_mm, bill_depth_mm, flipper_length_mm, body_mass_g, sex, year]
        severity: fail
      - id: species_enum
        type: enum
        column: species
        allow: ["Adelie", "Chinstrap", "Gentoo"]
        severity: fail
      - id: bill_len_range
        type: range
        column: bill_length_mm
        min: 30
        max: 60
        inclusive: true
        severity: warn

```
Outputs
- .tmp/report.json — deterministic JSON (sorted keys)

- .tmp/report.md — human-readable summary
- Exit code: 1 if any rule FAILs; otherwise 0
 Dataset credit: tiny fixture derived from Palmer Penguins (CC0). Attribution appreciated: Horst, Hill & Gorman / Palmer Station LTER.
---
## What you get

- out/report.json — structured findings + attestation (includes dataset hashes, timing, FAIRy version)

- (optional) report.md — friendly summary (see “Export bundle” below to generate it)
---

## Export bundle (optional, one call)

Generates report.json, report.md, copies your inputs, writes manifest.json and provenance.json, and zips the folder.
```bash
python - <<'PY'
from pathlib import Path
from fairy.core.services.export_adapter import export_submission
res = export_submission(
    project_dir=Path("."),  # outputs under ./exports/<timestamp>/
    rulepack=Path("src/fairy/rulepacks/GEO-SEQ-BULK/v0_1_0.json"),
    samples=Path("/path/to/samples.tsv"),
    files=Path("/path/to/files.tsv"),
)
print("Export dir:", res.export_dir)
print("Bundle zip:", res.zip_path)
print("Report JSON:", res.report_path)
print("Report MD:", res.report_md_path)
PY

```
## Multi-input validation (--inputs name=path)
Some datasets are split across multiple tables (e.g., artworks.csv + artists.csv). FAIRy can validate them in one run, enabling cross-table checks like foreign keys and lookups.

#### Usage
Option A - Single input
```bash
# single file (kept forever; maps to table name "default")
fairy validate metadata.csv --rulepack rules.yaml --report-json out.json

# folder containing CSVs (stems become table names)
fairy validate data/ --rulepack rules.yaml --report-json out.json
# e.g., data/artworks.csv → table "artworks", data/artists.csv → table "artists"

```
Option B - explicit multi-input
```bash
fairy validate \
  --rulepack rules.yaml \
  --inputs artworks=artworks.csv \
  --inputs artists=artists.csv \
  --report-json out.json

```
- repeat --inputs for each table you want to pass
- table names are the keys (left side), file paths on the right.

Rulepack example (cross-table FK)
```yaml
id: tate-art-collections
version: 0.1.0

resources:
  - pattern: artworks.csv
    rules:
      - id: fk_artworks_artistId
        type: foreign_key
        severity: fail
        from: { table: artworks, field: artistId }
        to:   { table: artists,  field: artistId }

```
- from.table and to.table must match the names provided via --inputs (or folder systems).
- if a rulepack refers to an unknown table, FAIRy raises a clear error and lists the provided tables.

### Reports
- JSON/Markdown formats are unchanged
- We append metadata.inputs (name to path) for provenance:
```json
{
  "summary": { "pass": 1, "warn": 0, "fail": 0 },
  "metadata": {
    "inputs": {
      "artworks": "tests/fixtures/art-collections/artworks_pass.csv",
      "artists": "tests/fixtures/art-collections/artists.csv"
    }
  }
}

```
Exit Codes
- 0 when there are no FAIL findings
- 1 when any rule emits FAIL (useful for CLI)

### Examples
Passing FK
```bash
fairy validate \
  --rulepack tests/fixtures/art-collections/rulepack.yaml \
  --inputs artworks=tests/fixtures/art-collections/artworks_pass.csv \
  --inputs artists=tests/fixtures/art-collections/artists.csv \
  --report-json out_pass.json
# exit 0
```
Failing FK
```bash
fairy validate \
  --rulepack tests/fixtures/art-collections/rulepack.yaml \
  --inputs artworks=tests/fixtures/art-collections/artworks_fail_missing_artist.csv \
  --inputs artists=tests/fixtures/art-collections/artists.csv \
  --report-json out_fail.json
# exit 1

```
### Notes and back compatibility
- Positional single-input is kept forever
    - File → table name default.
    - Folder → each *.csv becomes a table named by its stem
- Duplicate --inputs name: last one wins (a warning is logged)
- Large datasets: FAIRy caches loaded tables by name during a run.
---

## Tests
```bash
pytest -q
```
---

## Repo layout
```bash
src/fairy/
  cli/                  # CLI entrypoints (e.g., validate, preflight)
  core/                 # services, models, validators, exporters
  validation/           # rulepack runner + checks (MVP lives here)
  rulepacks/            # repository-specific rulepacks (CC0-1.0)
schemas/                # JSON Schemas for reports, etc.
demos/
  rulepacks/            # demo rulepacks (not shipped in wheels)
tests/
  fixtures/             # tiny CSVs & local rulepacks for tests
  golden/               # deterministic expected reports (optional)

```
---

## Licensing
- Core code (src/fairy/**, excluding rulepacks): AGPL-3.0-only. See LICENSE
- Rulepacks (src/fairy/rulepacks/**): CC0-1.0 (public domain dedication). See src/fairy/rulepacks/LICENSE
- Samples/fixtures (if present): CC BY-4.0 (documented per folder).

Third-party attributions: see THIRD_PARTY_LICENSES.md

>Commercial licensing is available. See COMMERCIAL.md or contact hello@datadabra.com

---

## Developer notes
- Source files use SPDX headers (pre-commit will add them if missing):
### SPDX-License-Identifier: AGPL-3.0-only
### Copyright (c) 2025 Jennifer Slotnick
- We package rulepacks as package data:
```toml
[tool.setuptools.package-data]
fairy = ["rulepacks/**/*.json","rulepacks/**/*.yaml","rulepacks/**/*.yml"]

```
- Local artifacts to ignore are preconfigured (.out/, exports/, .tmp/, .venv/, __pycache__/).

---

## Contributing
Until v1.0, we’re not accepting external code contributions. Please open issues for bugs/ideas.
(We may introduce a CLA later to enable dual/commercial licensing while keeping the project open.)

---

## Citation
If you use FAIRy in a project or talk:

FAIRy Core (v0.1, alpha). Datadabra.
Repository: https://github.com/yuummmer/fairy-core

## Roadmap
- Rulepack adapters (aliases, NA sentinels, regex/type coercions, unit enums)
- Multi-input CLI UX(auto-detect TSV/CSV, merge on sample_id)
- Richer provenance + determinism tests (goldens)
- Hosted UI orchestrator (separate repo)
