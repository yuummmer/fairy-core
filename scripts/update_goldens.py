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

Uses FAIRY_FIXED_TIMESTAMP environment variable to set a fixed timestamp
(2025-11-11T12:00:00Z) for deterministic golden files.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GOLDEN = REPO / "tests" / "golden"
GOLDEN.mkdir(parents=True, exist_ok=True)

# ---- If you already have a rulepack + sample tsvs, set them here ----
# Example guesses—change to your actual paths or leave as-is to skip preflight.
DEFAULT_RULEPACK = REPO / "src" / "fairy" / "rulepacks" / "GEO-SEQ-BULK" / "v0_1_0.json"
DEFAULT_SAMPLES = REPO / "demos" / "scratchrun" / "samples.tsv"
DEFAULT_FILES = REPO / "demos" / "scratchrun" / "files.tsv"


def run(cmd, cwd=REPO, env=None):
    print("$", " ".join(str(c) for c in cmd))
    if env is None:
        env = os.environ.copy()
    else:
        # Merge with existing environment
        merged_env = os.environ.copy()
        merged_env.update(env)
        env = merged_env
    env["PYTHONPATH"] = str(REPO / "src")
    proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, env=env)
    print("--- STDOUT ---\n" + proc.stdout)
    if proc.stderr:
        print("--- STDERR ---\n" + proc.stderr, file=sys.stderr)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def make_validate_goldens():
    """Generate validate goldens - requires a rulepack."""
    # Skip validate goldens for now since it requires a rulepack
    # and we're focusing on preflight reports
    print("ℹ️  Skipping validate goldens (validate command requires --rulepack).")
    print("    Focus is on preflight reports for this PR.")
    return

    # If we want to generate validate goldens later, we'd need:
    # - A rulepack file (YAML or JSON)
    # - Update the command to include --rulepack
    # tmp = Path(tempfile.mkdtemp(prefix="fairy_validate_"))
    # csv = tmp / "metadata.csv"
    # csv.write_text("sample_id,organism\nS1,Homo sapiens\n", encoding="utf-8")
    #
    # out_json = GOLDEN / "validate.report.json"
    # out_md = GOLDEN / "validate.report.md"
    #
    # run(
    #     [
    #         sys.executable,
    #         "-m",
    #         "fairy.cli.run",
    #         "validate",
    #         str(csv),
    #         "--rulepack",
    #         str(DEFAULT_RULEPACK),  # Would need to convert JSON to YAML or use a YAML rulepack
    #         "--report-json",
    #         str(out_json),
    #         "--report-md",
    #         str(out_md),
    #     ]
    # )
    # print(f"✅ validate goldens written: {out_json.name}, {out_md.name}")


def make_preflight_goldens():
    # Only run if all inputs exist (keeps this script robust on fresh clones)
    if not (DEFAULT_RULEPACK.exists() and DEFAULT_SAMPLES.exists() and DEFAULT_FILES.exists()):
        print("ℹ️  Skipping preflight goldens (rulepack or TSVs not found).")
        print("    Set DEFAULT_RULEPACK/DEFAULT_SAMPLES/DEFAULT_FILES in this script to enable.")
        return

    out_json = GOLDEN / "preflight.report.json"
    out_md = GOLDEN / "preflight.report.md"  # will be produced alongside JSON

    # Use fixed timestamp for deterministic golden files: 2025-11-11 12:00:00 UTC
    # Format: ISO-8601 with Z suffix
    fixed_timestamp = "2025-11-11T12:00:00Z"

    # Set environment variable to override timestamp in validator
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO / "src")
    env["FAIRY_FIXED_TIMESTAMP"] = fixed_timestamp

    run(
        [
            sys.executable,
            "-m",
            "fairy.cli.run",
            "preflight",
            "--rulepack",
            str(DEFAULT_RULEPACK),
            "--samples",
            str(DEFAULT_SAMPLES),
            "--files",
            str(DEFAULT_FILES),
            "--out",
            str(out_json),
        ],
        env=env,
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
