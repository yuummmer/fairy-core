from __future__ import annotations

from pathlib import Path


def emit_markdown(md_path: Path, payload: dict) -> None:
    """Very small markdown summary until template improves."""
    checks = payload.get("warnings", [])
    lines = [
        "# FAIRy Validation Report",
        "",
        f"**Run at:** {payload.get('run_at', '')}",
        f"**File:** {payload.get('dataset_id', {}).get('filename', '')}",
        f"**SHA256:** {payload.get('dataset_id', {}).get('sha256', '')}",
        "",
        "## Summary",
        f"- Rows: {payload.get('summary', {}).get('n_rows', '?')}",
        f"- Cols: {payload.get('summary', {}).get('n_cols', '?')}",
        f"- Fields validated: {len(payload.get('summary', {}).get('fields_validated', []))}",
        "",
        "## Warnings",
    ]
    if not checks:
        lines.append("- None")
    else:
        for w in checks:
            lines.append(f"- {w.get('code', 'warn')} - {w.get('message', '')}")
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines), encoding="utf-8")


def emit_preflight_markdown(
    md_path: Path,
    att: dict,
    report: dict,
    resolved_codes: list[str],
    prior_codes: set[str] | None,
) -> None:
    """
    Write a curator-facing one-pager in Markdown that mirrors the CLI output.
    """

    inputs = att.get("inputs", {})
    samples_info = inputs.get("samples", {})
    files_info = inputs.get("files", {})

    def _fmt_input_block(label: str, meta: dict) -> list[str]:
        if not meta:
            return [f"### {label}", "", "_no input metadata_", ""]
        return [
            f"### {label}",
            "",
            f"- path: '{meta.get('path', '?')}'",
            f"- sha256: '{meta.get('sha256', '?')}'",
            f"- rows: '{meta.get('n_rows', '?')}'",
            f"- cols: '{meta.get('n_cols', '?')}'",
            "",
        ]

    # summarize active codes
    fail_codes = sorted({f["code"] for f in report["findings"] if f["severity"] == "FAIL"})
    warn_codes = sorted({f["code"] for f in report["findings"] if f["severity"] == "WARN"})

    # Build findings table rows
    # One row per finding, so curator can see all issues
    table_lines = [
        "| Severity | Code | Location | Why it matters | How to fix |",
        "|----------|------|----------|----------------|------------|",
    ]
    for f in report["findings"]:
        sev = f.get("severity", "?")
        code = f.get("code", "?")
        where = f.get("where", "").replace("|", r"\|")
        why = f.get("why", "").replace("|", r"\|")
        fix = f.get("how_to_fix", "").replace("|", r"\|")
        table_lines.append(f"| {sev} | {code} | {where} | {why} | {fix} |")

    # Resolved since last run block
    if prior_codes is None:
        resolved_block = ["_No baseline from prior run (first run or cache missing)._"]
    elif not resolved_codes:
        resolved_block = ["_No previously-reported issues resolved._"]
    else:
        resolved_block = [f" -✅ {code}" for code in resolved_codes]

    # Compose markdown doc
    lines: list[str] = []

    # Title / high-level summary
    lines += [
        "# FAIRy Preflight Report",
        "",
        f"- **Rulepack:** {att['rulepack_id']}@{att['rulepack_version']}",
        f"- **FAIRy version:** {att['fairy_version']}",
        f"- **Run at (UTC):** {att['run_at_utc']}",
        f"- **submission_ready:** `{att['submission_ready']}`",
        "",
        "## Summary",
        "",
        f"- FAIL findings: {att['fail_count']} {fail_codes}",
        f"- WARN findings: {att['warn_count']} {warn_codes}",
        "",
        "If `submission_ready` is `True`, FAIRy believes this dataset is ready to submit.",
        "",
        "---",
        "",
        "## Input provenance",
        "",
        "These hashes and dimensions identify the exact files that FAIRy validated.",
        "You can hand this block to a curator or PI as evidence of what was checked.",
        "",
    ]

    lines += _fmt_input_block("samples.tsv", samples_info)
    lines += _fmt_input_block("files.tsv", files_info)

    lines += [
        "---",
        "",
        "## Findings (all current issues)",
        "",
        "Severity `FAIL` means “must fix before submission.”",
        "Severity `WARN` means “soft violation / likely curator feedback.”",
        "",
    ]

    # only include table if there are findings
    if report["findings"]:
        lines += table_lines
        lines += [""]  # newline after table
    else:
        lines += [
            "_No findings._",
            "",
        ]

    lines += [
        "---",
        "",
        "## Resolved since last run",
        "",
    ]
    if resolved_block:
        lines += resolved_block
    lines += [""]

    # Write file
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines), encoding="utf-8")
