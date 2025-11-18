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
This repo contains the **core validation engine** and **CLI** (e.g., `fairy preflight`, `fairy validate`).

- ✅ Validates tabular metadata against repository-specific **rulepacks**
- ✅ Emits **machine-readable** (JSON) and **human-readable** (Markdown) reports
- ✅ Writes **attestation & provenance**, with optional export bundle (zip)
- 🧪 Includes intentionally "failing" fixtures for smoketests
- 🚧 Early alpha; interfaces may change prior to v1.0

> 💡 **Want the full UI experience?** For project workspaces, guided fixes, visual workflows, and demo examples, see [**fairy-lab**](https://github.com/yuummmer/fairy-lab) — a Streamlit-based demo tenant that uses this core engine.

---
## 🌱 What is FAIRy?

- **Local-first**: All processing is on your machine. Your raw and fixed data never leave without your consent.
- **Flexible & Open**: Core validation engine, repository rule templates, and CLI are 100% open and community-driven.
- **Extensible**: Easily add new repository templates or contribute improved schemas/rules — keep up with the latest standards.
- **Practical**: Audit and fix real researcher pain points (dates, IDs, vocab, file names), export clean packages, avoid resubmission headaches.

---

## ⚙️ How Does It Work?

### Using the UI (fairy-lab)

The full visual workflow with project management, guided fixes, and export bundles is available in [**fairy-lab**](https://github.com/yuummmer/fairy-lab):

1. Create a new project workspace (all local).
2. Upload your dataset (CSV, TSV, FASTQ, Excel, JSON, etc.).
3. Choose your submission target(s): GEO, SRA, Zenodo, etc.
4. Validate & audit: FAIRy shows you errors, warnings, and actionable fixes.
5. Apply guided fixes on a working copy, or review/patch manually if preferred.
6. Export a submission-ready package for your target repository — no surprises, no guessing.
7. All fix history, audit logs, and provenance are saved in your local project.

### Using the CLI (fairy-core)

This repo provides the command-line interface:

1. Point the CLI at your data files (TSV/CSV) and a rulepack.
2. Run validation: `fairy preflight` or `fairy validate`.
3. Review the JSON/Markdown reports with findings and `how_to_fix` guidance.
4. Manually fix your data based on the reports.
5. Re-run validation until `submission_ready: true`.
6. Use the Python API (`export_submission()`) to create export bundles (or use fairy-lab UI).

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

> Requires Python **3.10+**. On Windows with WSL: use **Linux paths** (e.g., `/home/…`), not `\\wsl.localhost\…`.

```bash
# 0) Python 3.10+
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 1) Check CLI (after install, use: fairy --help)
python -m fairy.cli --help
python -m fairy.cli --version

# 2) Preflight (GEO bulk RNA-seq; expects JSON rulepack)
python -m fairy.cli preflight \
  --rulepack src/fairy/rulepacks/GEO-SEQ-BULK/v0_1_0.json \
  --samples demos/scratchrun/samples.tsv \
  --files   demos/scratchrun/files.tsv \
  --out     .tmp/report.json
cat .tmp/report.md   # human summary

# 3) Validate with custom rulepack (YAML or JSON)
python -m fairy.cli validate \
  --rulepack demos/rulepacks/penguins.yml \
  --inputs default=tests/fixtures/penguins_small.csv \
  --report-json .tmp/penguins_report.json

# 4) Rulepack schema validation only
python -m fairy.cli rulepack --rulepack demos/rulepacks/penguins.yml
```

---
## Documentation

For full documentation, see the [`docs/`](./docs) folder:

- [Getting started](./docs/getting-started.md)
- [CLI usage](./docs/cli.md)
- [Reporting](./docs/reporting.md)
- [Kata gallery](./docs/katas/index.md)

---
## Documentation

For full documentation, see the [`docs/`](./docs) folder:

- [Getting started](./docs/getting-started.md)
- [CLI usage](./docs/cli.md)
- [Reporting](./docs/reporting.md)
- [Kata gallery](./docs/katas/index.md)

---
## 🐧 Rulepacks (YAML)

Example rulepack (minimal shape):

```yaml
meta: { name: penguins-kata, version: "0.1.0", description: "Palmer Penguins checks" }
rules:
  - id: species_enum
    type: enum
    severity: fail
    config: { column: species, allow: ["Adelie","Chinstrap","Gentoo"] }

  - id: no_dups
    type: no_duplicate_rows
    severity: fail
    config:
      pattern: "penguins*.csv"
      keys: [species, island, bill_length_mm, bill_depth_mm, flipper_length_mm, body_mass_g, sex, year]

params: {}   # optional

```

## Reports

- **JSON**: Structured v1.0.0 schema reports with deterministic ordering (see [`schemas/preflight_report_v1.schema.json`](schemas/preflight_report_v1.schema.json) and [`docs/reporting.md`](docs/reporting.md))
- **Markdown**: Curator-friendly one-pager (generated alongside JSON)
- **Exit code**: 0 if no FAIL, else 1

---

## Development
```bash
# Tests (coverage scoped to cli + rulepack)
pytest -q

# Lint/format
ruff check . --fix
ruff format .

```
- Coverage config: .coveragerc, pytest.ini
- Demo fixtures: tests/fixtures/*, demos/
---

## Repo layout
```bash
src/fairy/
  cli/         # CLI entrypoints (validate, preflight, rulepack)
  core/        # services/models/validators (evolving)
  rulepack/    # loader + schema (YAML)
  rulepacks/   # packaged rulepacks (CC0)
demos/         # demo rulepacks / scratch data (not shipped)
tests/         # unit + smoke tests
decisions/     # Architecture Decision Records (ADRs)

```

See [Architecture Decision Records](decisions/README.md) for major design decisions and rationale.
---
## Want a longer guide?

See the [Documentation](#documentation) section above for detailed guides. For project management, guided fixes, and visual demos, see [fairy-lab](https://github.com/yuummmer/fairy-lab).

---

## License

FAIRy-core uses a mixed licensing model:

- **Core engine code** (`src/fairy/**`, excluding `src/fairy/rulepacks/**`):
  Licensed under **AGPL-3.0-only**. See [`LICENSE`](./LICENSE).

- **Built-in rulepacks** (`src/fairy/rulepacks/**`):
  Licensed under **CC0-1.0** (public domain dedication). See
  [`src/fairy/rulepacks/LICENSE`](./src/fairy/rulepacks/LICENSE).

- **Samples and fixtures** (e.g. `samples/**`, `tests/fixtures/**`):
  Licensed under **CC BY-4.0** (documented per folder).

- **Third-party components**:
  See [`THIRD_PARTY_LICENSES.md`](./THIRD_PARTY_LICENSES.md).

Commercial licensing for FAIRy-core is available for organizations that
cannot adopt AGPL. See [`COMMERCIAL.md`](./COMMERCIAL.md) or contact
**hello@datadabra.com**.

---

## Developer notes
- Source files use SPDX headers:
```python
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025 Jennifer Slotnick
```
- We package rulepacks as package data:
```toml
[tool.setuptools.package-data]
fairy = ["rulepacks/**/*.json","rulepacks/**/*.yaml","rulepacks/**/*.yml"]

```
- Local artifacts to ignore are preconfigured (.tmp/, .venv/, __pycache__/).

---

## Contributing
We welcome contributions! See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for guidelines on:
- How to get started (forking, setup, making changes)
- Ways to contribute (rulepacks, tests, documentation, engine improvements)
- Specs and PRDs for major features
- Licensing of contributions

For information about maintainer roles and module stewards, see [`MAINTAINERS.md`](./MAINTAINERS.md).

---

## Citation

If you use FAIRy in a project, demo, or talk, please cite:

FAIRy (v0.2). Local-first validator for FAIR research data.
FAIRy-core (engine): https://github.com/yuummmer/fairy-core
FAIRy Lab (UI & labs): https://github.com/yuummmer/fairy-lab

## Roadmap
- Rulepack adapters (aliases, NA sentinels, regex/type coercions, unit enums)
- Multi-input CLI UX (auto-detect TSV/CSV, merge on sample_id)
- Richer provenance + determinism tests (goldens)
- Export bundle CLI command (currently available via Python API)
