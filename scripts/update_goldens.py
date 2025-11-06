#!/usr/bin/env python3
"""
Create/update golden snapshot files for FAIRy-core.

- Always creates validate goldens:
    tests/golden/validate.report.json
    tests/golden/validate.report.md

- Optionally creates preflight goldens if a rulepack + TSVs are present:
    tests/golden/preflight.report.json
    tests/golden/preflight.report.md

Adjust DEFAULT_RULEPACK / DEFAULT_SAMPLES / DEFAULT_FILES if your paths differ.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GOLDEN = REPO / "tests" / "golden"
GOLDEN.mkdir(parents=True, exist_ok=True)

# ---- If you already have a rulepack + sample tsvs, set them here ----
# Example guesses—change to your actual paths or leave as-is to skip preflight.
DEFAULT_RULEPACK = REPO / "fairy" / "rulepacks" / "GEO-SEQ-BULK" / "v0_1_0.json"
DEFAULT_SAMPLES = REPO / "demos" / "PASS_minimal_rnaseq" / "samples.tsv"
DEFAULT_FILES = REPO / "demos" / "PASS_minimal_rnaseq" / "files.tsv"


def run(cmd, cwd=REPO):
    print("$", " ".join(str(c) for c in cmd))
    proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    print("--- STDOUT ---\n" + proc.stdout)
    if proc.stderr:
        print("--- STDERR ---\n" + proc.stderr, file=sys.stderr)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def make_validate_goldens():
    tmp = Path(tempfile.mkdtemp(prefix="fairy_validate_"))
    csv = tmp / "metadata.csv"
    csv.write_text("sample_id,organism\nS1,Homo sapiens\n", encoding="utf-8")

    out_json = GOLDEN / "validate.report.json"
    out_md = GOLDEN / "validate.report.md"

    # Write straight to target files so we skip copying and OS path weirdness
    run(
        [
            sys.executable,
            "-m",
            "fairy",
            "validate",
            str(csv),
            "--report-json",
            str(out_json),
            "--report-md",
            str(out_md),
            "--kind",
            "rna",
        ]
    )
    print(f"✅ validate goldens written: {out_json.name}, {out_md.name}")


def make_preflight_goldens():
    # Only run if all inputs exist (keeps this script robust on fresh clones)
    if not (DEFAULT_RULEPACK.exists() and DEFAULT_SAMPLES.exists() and DEFAULT_FILES.exists()):
        print("ℹ️  Skipping preflight goldens (rulepack or TSVs not found).")
        print("    Set DEFAULT_RULEPACK/DEFAULT_SAMPLES/DEFAULT_FILES in this script to enable.")
        return

    out_json = GOLDEN / "preflight.report.json"
    out_md = GOLDEN / "preflight.report.md"  # will be produced alongside JSON

    run(
        [
            sys.executable,
            "-m",
            "fairy",
            "preflight",
            "--rulepack",
            str(DEFAULT_RULEPACK),
            "--samples",
            str(DEFAULT_SAMPLES),
            "--files",
            str(DEFAULT_FILES),
            "--out",
            str(out_json),
        ]
    )
    # The CLI writes the MD next to the JSON with the same stem
    generated_md = out_json.with_suffix(".md")
    if generated_md.exists():
        shutil.move(str(generated_md), str(out_md))
    print(f"✅ preflight goldens written: {out_json.name}, {out_md.name}")


def main():
    make_validate_goldens()
    make_preflight_goldens()


if __name__ == "__main__":
    main()
