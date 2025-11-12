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
    report: dict,
    resolved_codes: list[str],
    prior_codes: set[str] | None,
) -> None:
    """
    Write a curator-facing one-pager in Markdown that mirrors the CLI output.

    Uses the new v1 report structure:
    - Top-level: schema_version, generated_at, dataset_id, metadata, summary, results
    - metadata.inputs: input name → InputMetadata
    - metadata.rulepack: rulepack provenance
    - results: array of rule results (replaces findings)
    - summary: by_level and by_rule counts
    """

    # Extract from new v1 structure
    metadata = report.get("metadata", {})
    summary = report.get("summary", {})
    results = report.get("results", [])

    # For backward compatibility, check _legacy if new structure is incomplete
    legacy_att = report.get("_legacy", {}).get("attestation")

    # Extract inputs from metadata.inputs
    inputs = metadata.get("inputs", {})
    samples_info = inputs.get("samples", {})
    files_info = inputs.get("files", {})

    # Extract rulepack info from metadata.rulepack
    rulepack_meta = metadata.get("rulepack", {})
    rulepack_id = rulepack_meta.get("id", "UNKNOWN_RULEPACK")
    rulepack_version = rulepack_meta.get("version", "0.0.0")

    # Get FAIRy version from legacy attestation if available
    fairy_version = legacy_att.get("fairy_version", "unknown") if legacy_att else "unknown"

    # Get counts from summary
    by_level = summary.get("by_level", {})
    fail_count = by_level.get("fail", 0)
    warn_count = by_level.get("warn", 0)
    submission_ready = fail_count == 0

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

    # Extract active codes from results
    fail_codes = sorted({r["rule"] for r in results if r["level"] == "fail"})
    warn_codes = sorted({r["rule"] for r in results if r["level"] == "warn"})

    # Build results table rows
    # One row per result, showing rule-level summary
    # For detailed findings, we'll show samples from each result
    table_lines = [
        "| Level | Rule | Count | Samples |",
        "|-------|------|-------|--------|",
    ]
    for r in results:
        level = r.get("level", "?")
        rule = r.get("rule", "?")
        count = r.get("count", 0)
        samples = r.get("samples", [])

        # Format samples summary (show first few)
        if samples:
            sample_summaries = []
            for s in samples[:3]:  # Show first 3 samples
                parts = []
                if s.get("row"):
                    parts.append(f"row {s['row']}")
                if s.get("column"):
                    parts.append(f"col {s['column']}")
                if parts:
                    sample_summaries.append(", ".join(parts))
            sample_text = "; ".join(sample_summaries)
            if len(samples) > 3:
                sample_text += f" (+{len(samples) - 3} more)"
        else:
            sample_text = "(none)"

        table_lines.append(f"| {level} | {rule} | {count} | {sample_text} |")

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
        f"- **Schema version:** {report.get('schema_version', '?')}",
        f"- **Rulepack:** {rulepack_id}@{rulepack_version}",
        f"- **FAIRy version:** {fairy_version}",
        f"- **Generated at (UTC):** {report.get('generated_at', '?')}",
        f"- **Dataset ID:** {report.get('dataset_id', '?')}",
        f"- **submission_ready:** `{submission_ready}`",
        "",
        "## Summary",
        "",
        f"- FAIL findings: {fail_count} {fail_codes}",
        f"- WARN findings: {warn_count} {warn_codes}",
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
        "## Results (all current issues)",
        "",
        "Level `fail` means “must fix before submission.”",
        "Level `warn` means “soft violation / likely curator feedback.”",
        "Level `pass` means the rule passed with no violations.",
        "",
    ]

    # only include table if there are results
    if results:
        lines += table_lines
        lines += [""]  # newline after table

        # Add detailed samples for each result with violations
        for r in results:
            if r.get("count", 0) > 0 and r.get("samples"):
                rule = r.get("rule", "?")
                level = r.get("level", "?")
                samples = r.get("samples", [])
                sample_text = f"{len(samples)} sample{'s' if len(samples) != 1 else ''}"
                lines += [
                    f"### {rule} ({level}, {sample_text})",
                    "",
                ]
                for s in samples:
                    sample_parts = []
                    if s.get("row"):
                        sample_parts.append(f"row {s['row']}")
                    if s.get("column"):
                        sample_parts.append(f"column '{s['column']}'")
                    if s.get("value") is not None:
                        sample_parts.append(f"value: {s['value']}")
                    if s.get("message"):
                        sample_parts.append(f"message: {s['message']}")
                    if s.get("hint"):
                        sample_parts.append(f"hint: {s['hint']}")
                    if sample_parts:
                        lines.append(f"- {', '.join(sample_parts)}")
                lines += [""]
    else:
        lines += [
            "_No results (all rules passed)._",
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
