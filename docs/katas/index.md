# Kata gallery

Katas are small, focused examples that show FAIRy-core validating real-ish
datasets. They're great for:

- Learning how rulepacks are structured
- Demonstrating FAIRy to other people
- Regression testing common patterns

## Available katas

### Art collections (toy museum dataset)

A multi-table validation example demonstrating foreign key relationships between artists and artworks.

**Location:** `tests/fixtures/art-collections/`

**What it demonstrates:**
- Multi-input validation with named tables
- Cross-table foreign key validation
- Required fields, uniqueness, and non-empty checks
- Duplicate row detection

**How to run:**

```bash
# PASS example (FK satisfied)
fairy validate \
  --rulepack tests/fixtures/art-collections/rulepack.yaml \
  --inputs artworks=tests/fixtures/art-collections/artworks_pass.csv \
  --inputs artists=tests/fixtures/art-collections/artists.csv \
  --report-json out/art-collections-pass.json

# FAIL example (missing artistId)
fairy validate \
  --rulepack tests/fixtures/art-collections/rulepack.yaml \
  --inputs artworks=tests/fixtures/art-collections/artworks_fail_missing_artist.csv \
  --inputs artists=tests/fixtures/art-collections/artists.csv \
  --report-json out/art-collections-fail.json
```

Or use the provided script:

```bash
bash tests/fixtures/art-collections/run.sh
```

**Files included:**
- `rulepack.yaml` – Rulepack with foreign key and validation rules
- `artists.csv` – Artist reference table
- `artworks_pass.csv` – Valid artworks dataset
- `artworks_fail_missing_artist.csv` – Invalid dataset (missing foreign key reference)
- `run.sh` – Example run script

### ENA bulk (toy) – *coming soon*

Each kata includes:

- a small dataset
- a rulepack
- example run commands

This doc will be updated as we add more katas.
