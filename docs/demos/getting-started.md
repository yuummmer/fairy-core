# Getting Started with FAIRy

**This is a demo recipe for running a GEO preflight check.**

**Works with:** fairy-core >= v0.2.2

This guide demonstrates the core FAIRy workflow: installing FAIRy, running a preflight check, and reviewing the results.

---

## Setup

### Install FAIRy

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install "git+https://github.com/yuummmer/fairy-core.git@<FAIRY_CORE_VERSION>"
fairy --version
```

**Note:** Replace `<FAIRY_CORE_VERSION>` with an actual tag (e.g., `v0.2.2`) or commit SHA. Never use `@main` for reproducible demos.

### Get Demo Data

```bash
rm -rf fairy-rulepacks-geo
git clone --branch <RULEPACKS_TAG> --depth 1 https://github.com/yuummmer/fairy-rulepacks-geo.git
cd fairy-rulepacks-geo
```

**Note:** Replace `<RULEPACKS_TAG>` with an actual tag (e.g., `v0.2.0`) or commit SHA.

---

## Run

Run FAIRy's preflight check:

```bash
mkdir -p .tmp
fairy preflight \
  --rulepack rulepacks/geo_bulk_seq/v0_2_0.json \
  --samples  rulepacks/geo_bulk_seq/fixtures/samples_bad.tsv \
  --files    rulepacks/geo_bulk_seq/fixtures/files.tsv \
  --out      .tmp/geo_bulk_seq_report.json
```

FAIRy generates a JSON report at the path specified with `--out`:
- **JSON** (`geo_bulk_seq_report.json`) - For programmatic use

Depending on version, FAIRy may also write a Markdown report (e.g., `geo_bulk_seq_report.md`); otherwise pass an explicit flag or use `--report-md` where supported.

---

## Review

Open the Markdown report:

```bash
less .tmp/geo_bulk_seq_report.md
```

Or open it in any text editor or browser.

### What to Look For

1. **Summary:** Check `submission_ready` status at the top
2. **Findings:** Review FAIL and WARN items with specific locations and fix instructions
3. **Input Provenance:** SHA-256 hashes of validated files for evidence/audit trails

<!-- ============================================ -->
<!-- MANIFEST V1 SPOTLIGHT - TOGGLE ON/OFF       -->
<!-- When Manifest v1 ships, uncomment below:   -->
<!-- ============================================ -->
<!--
**Manifest v1:** In Manifest v1, the provenance section becomes a stable contract via `manifest.json`, which records `dataset_id`, rulepack version, `created_at`, source report, and a typed list of files with roles + hashes.
-->

---

## Next Steps

- **Try with your data:** Replace the fixture files with your own dataset
- **Explore other rulepacks:** Check available rulepacks for GEO, Zenodo, ENA, and more
- **Learn more:** Visit the [FAIRy documentation](/) or [GitHub repository](https://github.com/yuummmer/fairy-core)

---

## Version Management

**IMPORTANT:** Always use pinned versions to prevent demo rot:

```bash
FAIRY_CORE_VERSION="<tag-or-sha>"  # e.g., "v0.2.2"
RULEPACKS_TAG="<tag-or-sha>"       # e.g., "v0.2.0"
```

**How to find versions:**
- Check release tags: `https://github.com/yuummmer/fairy-core/releases`
- Rulepacks: `https://github.com/yuummmer/fairy-rulepacks-geo/tags`
- Or use a specific commit SHA for exact reproducibility

**Never use `@main` or clone without a tag**—this will cause demos to break when repositories are updated.
