# UNICEF indicator export demo

This demo shows FAIRy validating a simple UNICEF indicator time-series export (CSV) and generating a report bundle.

## Files

- `unicef_pull.csv` — small example export (public/demo data)
- `unicef-export@0.1.0.yaml` — demo rulepack for expected columns + basic checks
- `out/` — local outputs (not committed)

## Run

From the repo root:

```bash
fairy validate \
  --rulepack demos/unicef/unicef-export@0.1.0.yaml \
  --inputs default=demos/unicef/unicef_pull.csv \
  --report-md demos/unicef/out/report.md \
  --report-json demos/unicef/out/report.json
rm demos/unicef/README.md
cat > demos/unicef/README.md <<'MD'
# UNICEF indicator export demo

This demo shows FAIRy validating a simple UNICEF indicator time-series export (CSV) and generating a report bundle.

## Files

- `unicef_pull.csv` — small example export (public/demo data)
- `unicef-export@0.1.0.yaml` — demo rulepack for expected columns + basic checks
- `out/` — local outputs (not committed)

## Run

From the repo root:

```bash
fairy validate \
  --rulepack demos/unicef/unicef-export@0.1.0.yaml \
  --inputs default=demos/unicef/unicef_pull.csv \
  --report-md demos/unicef/out/report.md \
  --report-json demos/unicef/out/report.json
