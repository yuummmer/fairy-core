# Getting started with FAIRy-core

This guide walks through installing FAIRy-core and running your first preflight
check on a small dataset.

## 1. Install FAIRy-core (dev/editable)

```bash
git clone https://github.com/yuummmer/fairy-core.git
cd fairy-core

python -m venv .venv
source .venv/bin/activate   # or use your shell equivalent
pip install -U pip
pip install -e ".[dev]"
pre-commit install          # optional but recommended
```
---
## 2. Run a simple preflight check
Assuming you have a small CSV (e.g. samples/example.csv) and a rulepack (e.g. samples/example-rulepack.yaml):
```bash
fairy-preflight \
  --input samples/example.csv \
  --rules samples/example-rulepack.yaml \
  --output out/example-report.json

```
Check the generated report:
```bash
cat out/example-report.json
```
For a deeper explanation of the report structure, see
Reporting
---
## 3. Multi-input (multiple tables)

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
## 4. Params/config files (--param-file)

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
## 5. Next steps
- Explore additional rule types and rulepacks
- Try a multi-input run (multiple tables) once you're comfortable.
- If you run into rough edges, please open an issue in the tracker.

---
## 6. Give katas a home: `docs/katas/index.md`

See the [Kata gallery](katas/index.md) for small, focused examples that show FAIRy-core validating real-ish datasets.
---
