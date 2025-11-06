<!-- Project badges -->
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)
[![Rulepacks: CC0-1.0](https://img.shields.io/badge/Rulepacks-CC0%E2%80%911.0-lightgrey.svg)](src/fairy/rulepacks/LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-informational.svg)](#)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen.svg)](.pre-commit-config.yaml)

# ✨ FAIRy Core ✨

Local-first validator and packager for FAIR-compliant research datasets.
This repo contains the **core CLI** and rulepack support (e.g., GEO bulk RNA-seq).

- ✅ Validates tabular metadata against repository-specific **rulepacks**
- ✅ Emits **machine-readable** (JSON) and **human-readable** (Markdown) reports
- ✅ Writes **attestation & provenance**, with optional export bundle (zip)
- 🧪 Includes intentionally “failing” fixtures for smoketests
- 🚧 Early alpha; interfaces may change prior to v1.0

---

## Quickstart (90 seconds)

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
## What you get

out/report.json — structured findings + attestation (includes dataset hashes, timing, FAIRy version)

(optional) report.md — friendly summary (see “Export bundle” below to generate it)
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
  rulepacks/            # repository-specific rulepacks (CC0-1.0)
schemas/                # JSON Schemas for reports, etc.
```
---

## Licensing
- Core code (src/fairy/**, excluding rulepacks): AGPL-3.0-only. See LICENSE
- Rulepacks (src/fairy/rulepacks/**): CC0-1.0 (public domain dedication). See src/fairy/rulepacks/LICENSE
- Samples/fixtures (if present): CC BY-4.0 (documented per folder).

Third-party attributions: see THIRD_PARTY_LICENSES.md

*Commercial licensing is available. See COMMERCIAL.md or contact hello@datadabra.com*

---

## Developer notes
- Source files use SPDX headers (pre-commit will add them if missing):
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025 Jennifer Slotnick
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
