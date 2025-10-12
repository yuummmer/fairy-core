# ✨ FAIRy Skeleton

🚧 **Prototype / Smoketest** 🚧  
This is an experimental [Streamlit](https://streamlit.io/) prototype for FAIRy —  
a local-first validator and packager for FAIR-compliant data submissions.  

- ✅ Shows basic flows: create project, upload CSV, validate, export placeholder  
- ⚠️ Not production-ready — meant for demos, testing, and early feedback  
- 🔓 The clean, open-source FAIRy Core engine (validator, templates, CLI) will live in a separate repo soon

---

## 📸 Screenshot

### Dashboard view
![FAIRy Dashboard](FAIRy_Dash.png)

---

## 🚀 Getting Started

Clone the repo and set up a virtual environment:

```bash
git clone https://github.com/yuummmer/metadata-wizard.git
cd metadata-wizard   # or fairy-skeleton if you renamed it
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```
## Quickstart (v0.1)
```bash
Prereqs: Python 3.11+, `pip install -e .`
```
Produce a schema-validated report at project_dir/out/report.json:
```bash
python - <<'PY'
from fairy.core.services.report_writer import write_report
write_report("project_dir/out",
    filename="samples_toy.csv",
    sha256="0"*64,
    meta={"n_rows":1,"n_cols":2,"fields_validated":["a","b"],"warnings":[]},
    rulepacks=[],
    provenance={"license":None,"source_url":None,"notes":None},
    input_path="samples_toy.csv")
PY
# → [FAIRy] Wrote /abs/path/project_dir/out/report.json
```
Optional: validate the output against the JSON Schema
```bash
python - <<'PY'
import json, jsonschema
from pathlib import Path
schema = json.loads(Path("schemas/report_v0.schema.json").read_text())
data = json.loads(Path("project_dir/out/report.json").read_text())
jsonschema.validate(data, schema)
print("✅ report.json validates")
PY
```
## 🧪 Tests
```bash
pytest -q
```
## 🗺️ Roadmap (v0.1 scope)
Streamlit Export & Validate tab wired to backend (warn-mode).

Deterministic report.json writer validated by JSON Schema.

Golden fixture test for bad.csv.

(See GitHub issues for v0.2 items like bundles, manifests, ZIP export, and provenance.)

## Attribution / Citation

If you use FAIRy, please cite:
FAIRy (v0.1, prototype). URL: https://github.com/yuummmer/metadata-wizard
This project reuses open-source components credited in the repository’s LICENSE and NOTICE sections.
