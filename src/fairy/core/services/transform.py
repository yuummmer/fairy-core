# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025 Jennifer Slotnick

"""
Transformation utilities for converting findings to results and deterministic ordering.

This module provides functions for:
- Transforming findings lists into structured results arrays
- Sorting and limiting samples
- Ensuring deterministic ordering of report components
"""

from __future__ import annotations

from typing import Any


def sort_rules(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Sort rules array by (meta.input, meta.column, rule, level) for deterministic ordering.
    """
    return sorted(
        rules,
        key=lambda r: (
            r.get("meta", {}).get("input", "") if r.get("meta") else "",
            r.get("meta", {}).get("column", "") if r.get("meta") else "",
            r.get("rule", ""),
            r.get("level", ""),
        ),
    )


def sort_samples(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Sort samples array by (row, column, stringify(value)) for deterministic ordering.
    Handles None values gracefully.
    """
    return sorted(
        samples,
        key=lambda s: (
            s.get("row") if s.get("row") is not None else 0,
            s.get("column") if s.get("column") is not None else "",
            str(s.get("value")) if s.get("value") is not None else "",
        ),
    )


def limit_samples(samples: list[dict[str, Any]], max_count: int = 10) -> list[dict[str, Any]]:
    """
    Take first N samples after sorting. Used to limit sample violations per rule.
    """
    return samples[:max_count]


def sort_inputs_keys(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Return a new dict with keys sorted lexicographically.
    Note: When serializing to JSON, use sort_keys=True in json.dumps() for object key ordering.
    This function is useful if you need sorted keys before serialization.
    """
    return dict(sorted(inputs.items()))


def transform_findings_to_results(
    all_findings: list[dict[str, Any]], all_rules: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Transform findings list into results array grouped by rule code.

    Args:
        all_findings: List of finding dicts with "code", "severity", "details"
        all_rules: List of rule dicts with "code" and other metadata

    Returns:
        List of result dicts with rule, level, count, samples, meta
    """
    # Group findings by rule code
    findings_by_code: dict[str, list[dict[str, Any]]] = {}
    for finding in all_findings:
        code = finding["code"]
        if code not in findings_by_code:
            findings_by_code[code] = []
        findings_by_code[code].append(finding)

    results: list[dict[str, Any]] = []

    # Process each rule (including rules with no findings - those are "pass")
    for rule in all_rules:
        code = rule["code"]
        findings = findings_by_code.get(code, [])

        # Determine level: if no findings, it's "pass"
        if not findings:
            level = "pass"
            count = 0
        else:
            # Level is determined by the highest severity found
            severities = [f["severity"] for f in findings]
            if "FAIL" in severities:
                level = "fail"
            elif "WARN" in severities:
                level = "warn"
            else:
                level = "pass"
            count = len(findings)

        # Extract samples from findings
        samples: list[dict[str, Any]] = []
        for finding in findings:
            details = finding.get("details", {})
            sample: dict[str, Any] = {}

            # Convert row to 1-based if present (WarningItem may use 0-based)
            # Schema requires row >= 1, so omit if None or invalid
            row = details.get("row")
            if row is not None and isinstance(row, int):
                if row >= 1:
                    # Already 1-based, use as-is
                    sample["row"] = row
                elif row >= 0:
                    # Convert 0-based to 1-based (row 0 -> row 1, row 1 -> row 2, etc.)
                    sample["row"] = row + 1
                # If row < 0, omit it (invalid)

            # Add optional fields
            if details.get("column"):
                sample["column"] = details["column"]
            if "value" in details:
                # Value can be string, number, boolean, or null
                sample["value"] = details["value"]
            if details.get("message"):
                sample["message"] = details["message"]
            if details.get("hint"):
                sample["hint"] = details["hint"]

            if sample:  # Only add if sample has at least one field
                samples.append(sample)

        # Sort and limit samples
        samples = sort_samples(samples)
        samples = limit_samples(samples, max_count=10)

        # Build meta from rule context
        meta: dict[str, Any] | None = None
        # Try to extract input/column from rule spec if available
        # This is rulepack-specific, so we'll keep it simple for now
        # Meta can be extended later based on rulepack structure

        result: dict[str, Any] = {
            "rule": code,
            "level": level,
            "count": count,
            "samples": samples,
        }
        if meta:
            result["meta"] = meta

        results.append(result)

    # Sort results
    results = sort_rules(results)

    return results
