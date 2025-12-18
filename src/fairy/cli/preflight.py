# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025 Jennifer Slotnick

# fairy/cli/preflight.py

from __future__ import annotations

import json
from pathlib import Path

import typer

from fairy.core.services.validator import run_rulepack

app = typer.Typer(help="FAIRy CLI commands")


@app.command("preflight")
def preflight(
    rulepack: str = typer.Option(
        ...,
        "--rulepack",
        help="Path to rulepack JSON (e.g. "
        "/path/to/fairy-rulepacks-geo/rulepacks/geo_bulk_seq/v0_1_0.json)",
    ),
    samples: str = typer.Option(..., "--samples", help="Path to samples.tsv"),
    files: str = typer.Option(..., "--files", help="Path to files.tsv / file manifest"),
    out: str = typer.Option(..., "--out", help="Where to write FAIRy report JSON"),
    fairy_version: str = typer.Option(
        "0.2.0", "--fairy-version", help="Version string to embed in attestation"
    ),
):
    """
    Run FAIRy rulepack validation and emit a machine-readable report
containing the attestation block and all findings.

    Example:
        python -m fairy.cli.preflight preflight \
            --rulepack /path/to/fairy-rulepacks-geo/rulepacks/geo_bulk_seq/v0_1_0.json \
            --samples demos/bulk_demo/samples.tsv \
            --files demos/bulk_demo/files.tsv \
            --out out/report.json
    """

    rulepack_path = Path(rulepack).resolve()
    samples_path = Path(samples).resolve()
    files_path = Path(files).resolve()
    out_path = Path(out).resolve()

    report = run_rulepack(
        rulepack_path=rulepack_path,
        samples_path=samples_path,
        files_path=files_path,
        fairy_version=fairy_version,
    )

    # ensure output dir exists
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)

    # friendly terminal summary
    att = report["attestation"]
    print("")
    print(
        "FAIRy preflight complete ✅"
        if att["submission_ready"]
        else "FAIRy preflight complete ❌ (not submission-ready)"
    )
    print(f"Rulepack: {att['rulepack_id']}@{att['rulepack_version']}")
    print(f"FAIL: {att['fail_count']} WARN: {att['warn_count']}")
    print(f"submission-ready: {att['submission_ready']}")
    print(f"Report written to: {out_path}")
    print("")
    print("First few findings:")
    for finding in report["findings"][:5]:
        print(f" - [{finding['severity']}] {finding['code']} @ {finding['where']}")
        print(f"   why: {finding['why']}")
        print(f"   fix: {finding['how_to_fix']}")
    print("")


def main():
    app()


if __name__ == "__main__":
    main()
