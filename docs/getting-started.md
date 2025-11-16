# Getting started with FAIRy-core

This guide walks through installing FAIRy-core and running your first validation
check on a small dataset.

## FAIRy for data stewards

If you're a data steward, research coordinator, or lab manager responsible for preparing datasets for submission to repositories like GEO, SRA, or Zenodo, FAIRy can help you ensure your data meets repository requirements before submission.

### What is FAIRy?

FAIRy is a validation tool that checks your research datasets against repository-specific rules and standards. Think of it as a quality control checker that runs on your computer—it reviews your data files and tells you what needs to be fixed before you submit to a repository.

### Why use FAIRy?

- **Avoid rejection cycles**: Catch errors before submission, so you don't have to fix and resubmit multiple times
- **Clear, actionable feedback**: FAIRy tells you exactly what's wrong and how to fix it, not just that something failed
- **Works on your computer**: All validation happens locally—your data never leaves your machine unless you choose to share it
- **Repository-specific rules**: FAIRy uses rulepacks tailored to specific repositories (GEO, SRA, etc.), so you know your data will meet their exact requirements
- **Human-readable reports**: Get both detailed technical reports and easy-to-read summaries that you can share with researchers

### What you'll learn in this guide

This guide will walk you through:
1. Installing FAIRy on your computer
2. Running your first validation check
3. Understanding the validation reports
4. Using FAIRy with different types of datasets

You don't need to be a programmer to use FAIRy—if you can use a command line (terminal) and follow step-by-step instructions, you can use FAIRy to validate your datasets.

---

## Prerequisites

- Python 3.10 or higher
- pip (Python package installer)
- Git (to clone the repository)

---

## 1. Install FAIRy-core

### Step 1: Clone the repository

```bash
git clone https://github.com/yuummmer/fairy-core.git
cd fairy-core
```

### Step 2: Create a virtual environment

A virtual environment isolates FAIRy-core's dependencies from your system Python. Choose the method that works for your system:

#### Option A: Using Python's built-in venv (Linux, macOS, Windows)

**Linux and macOS:**
```bash
python -m venv .venv
source .venv/bin/activate
```

**Windows (Command Prompt):**
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Windows with WSL (Windows Subsystem for Linux):**
Use the Linux instructions above. Note: use Linux paths (e.g., `/home/…`), not `\\wsl.localhost\…`.

#### Option B: Using Conda

If you prefer using Conda:

```bash
conda create -n fairy-core python=3.10
conda activate fairy-core
```

### Step 3: Install FAIRy-core

Once your virtual environment is activated (you should see `(.venv)` or `(fairy-core)` in your prompt), install FAIRy-core:

```bash
pip install -U pip
pip install -e ".[dev]"
```

**Optional:** Install pre-commit hooks for code quality checks:
```bash
pre-commit install
```

### Step 4: Verify installation

Check that FAIRy-core is installed correctly:

```bash
fairy --version
fairy --help
```

---

## 2. Run your first validation check

Let's run a simple validation using the included penguins example dataset.

### Step 1: Create an output directory

```bash
mkdir -p out
```

**Windows (Command Prompt):**
```cmd
mkdir out
```

**Windows (PowerShell):**
```powershell
New-Item -ItemType Directory -Path out -Force
```

### Step 2: Run validation

Use the `fairy validate` command with the example penguins dataset:

```bash
fairy validate \
  --rulepack demos/rulepacks/penguins.yml \
  --inputs default=tests/fixtures/penguins_small.csv \
  --report-json out/penguins-report.json \
  --report-md out/penguins-report.md
```

**Windows (Command Prompt):**
```cmd
fairy validate --rulepack demos/rulepacks/penguins.yml --inputs default=tests/fixtures/penguins_small.csv --report-json out/penguins-report.json --report-md out/penguins-report.md
```

**Windows (PowerShell):**
```powershell
fairy validate `
  --rulepack demos/rulepacks/penguins.yml `
  --inputs default=tests/fixtures/penguins_small.csv `
  --report-json out/penguins-report.json `
  --report-md out/penguins-report.md
```

### Step 3: View the report output

FAIRy-core generates two report files:

1. **JSON report** (`out/penguins-report.json`): Machine-readable structured report
2. **Markdown report** (`out/penguins-report.md`): Human-readable summary

**View the JSON report:**
```bash
cat out/penguins-report.json
```

**Windows (Command Prompt):**
```cmd
type out\penguins-report.json
```

**Windows (PowerShell):**
```powershell
Get-Content out/penguins-report.json
```

**View the Markdown report:**
```bash
cat out/penguins-report.md
```

The Markdown report is easier to read and provides a summary of validation results, including any failures or warnings.

### Understanding the report output

The report files are written to the directory you specify with `--report-json` and `--report-md`. In this example:
- **Location**: `out/` directory (relative to your current working directory)
- **JSON file**: `out/penguins-report.json` - Contains structured validation results
- **Markdown file**: `out/penguins-report.md` - Contains a human-readable summary

The JSON report includes:
- `summary.by_level`: Counts of pass/warn/fail results
- `results`: Detailed validation results for each rule
- `metadata`: Information about the input files and rulepack used

For a deeper explanation of the report structure, see [Reporting](./reporting.md).

---

## 3. Run a preflight check (GEO-style datasets)

The `fairy preflight` command is designed for GEO-style bulk RNA-seq datasets that use separate `samples.tsv` and `files.tsv` files.

### Step 1: Run preflight

```bash
fairy preflight \
  --rulepack src/fairy/rulepacks/GEO-SEQ-BULK/v0_1_0.json \
  --samples demos/scratchrun/samples.tsv \
  --files demos/scratchrun/files.tsv \
  --out out/geo-report.json
```

**Windows (Command Prompt):**
```cmd
fairy preflight --rulepack src/fairy/rulepacks/GEO-SEQ-BULK/v0_1_0.json --samples demos/scratchrun/samples.tsv --files demos/scratchrun/files.tsv --out out/geo-report.json
```

**Windows (PowerShell):**
```powershell
fairy preflight `
  --rulepack src/fairy/rulepacks/GEO-SEQ-BULK/v0_1_0.json `
  --samples demos/scratchrun/samples.tsv `
  --files demos/scratchrun/files.tsv `
  --out out/geo-report.json
```

### Step 2: View the preflight report

The preflight command generates both JSON and Markdown reports:
- **JSON report**: `out/geo-report.json` (specified with `--out`)
- **Markdown report**: `out/geo-report.md` (automatically generated with `.md` extension)

View the reports using the same commands as shown in section 2.

---

## 4. Multi-input (multiple tables)

FAIRy-core supports validating multiple tables in a single run. Use repeatable `--inputs name=path` flags to specify each table with a name:

```bash
fairy validate \
  --rulepack path/to/rulepack.yaml \
  --inputs artworks=artworks.csv \
  --inputs artists=artists.csv \
  --report-json out/multi-table-report.json
```

Each `--inputs` flag maps a table name to a CSV file path. These names are used in rulepacks to reference specific tables, especially for cross-table rules.

### Cross-table rules

Multi-input enables cross-table validation rules, such as foreign key checks. In your rulepack, you can define rules that reference multiple tables:

```yaml
resources:
  - pattern: "artworks_*.csv"
    rules:
      - id: artworks_artist_fk
        type: foreign_key
        severity: fail
        from: { table: artworks, field: artistId }
        to:   { table: artists,  field: artistId }
```

This rule ensures that every `artistId` in the `artworks` table exists in the `artists` table.

### Legacy single-input mode

For backward compatibility, you can still use a single positional input:

```bash
fairy validate path/to/data.csv --rulepack path/to/rulepack.yaml --report-json out/report.json
```

Or provide a folder containing CSV files (each CSV becomes a table named by its filename stem):

```bash
fairy validate path/to/folder --rulepack path/to/rulepack.yaml --report-json out/report.json
```

---
## 5. Params/config files (--param-file)

TODO: Add detailed guide (see issue Doc: Params file guide (--param-file)).

Planned content:

- What a params file looks like (YAML/JSON).
- Which settings can be moved into it (inputs, rulepacks, params, output).
- Example:

```bash
fairy-preflight --param-file configs/example-params.yaml
```

For now, see the CLI --help output for the most up-to-date flags.

Later, when you or a contributor do #27 and #10, they'll flesh this out.

---
## 6. Next steps
- Explore additional rule types and rulepacks
- Try a multi-input run (multiple tables) once you're comfortable.
- If you run into rough edges, please open an issue in the tracker.

---

## 7. Learn more

- **Kata gallery**: See the [Kata gallery](katas/index.md) for small, focused examples that show FAIRy-core validating real-ish datasets
- **CLI reference**: See [CLI usage](./cli.md) for detailed command documentation
- **Report structure**: See [Reporting](./reporting.md) for detailed information about report formats
