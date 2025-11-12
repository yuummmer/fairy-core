# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025 Jennifer Slotnick

from dataclasses import dataclass, field
from typing import Any


@dataclass
class InputMetadata:
    """Metadata for a single input file."""

    path: str
    sha256: str
    n_rows: int
    n_cols: int
    header: list[str]


@dataclass
class RulepackMetadata:
    """Metadata for the rulepack used in validation."""

    path: str
    sha256: str
    id: str | None = None
    version: str | None = None
    params_sha256: str | None = None


@dataclass
class RuleSample:
    """A single sample violation for a rule."""

    row: int | None = None  # 1-based row number (≥1), omit field when unknown (don't use None)
    column: str | None = None
    value: str | int | float | bool | None = None  # Can be string, number, boolean, or null
    message: str | None = None
    hint: str | None = None


@dataclass
class RuleResult:
    """Result for a single rule execution."""

    rule: str  # Rule identifier (e.g., "schema.required", "row.unique")
    level: str  # "pass", "warn", or "fail"
    count: int  # Number of violations (0 if level is "pass")
    samples: list[RuleSample] = field(default_factory=list)  # Up to 10 samples
    meta: dict[str, Any] | None = None  # Optional metadata (input, column, etc.)


@dataclass
class Metadata:
    """Metadata container for inputs and rulepack."""

    inputs: dict[str, InputMetadata]  # Map input name → InputMetadata
    rulepack: RulepackMetadata | None = None  # Optional rulepack metadata


@dataclass
class Summary:
    """Summary statistics for the validation run."""

    by_level: dict[str, int]  # {"pass": 5, "warn": 2, "fail": 1}
    by_rule: dict[str, str]  # {"schema.required": "pass", "row.unique": "fail", ...}


@dataclass
class PreflightReportV1:
    """Preflight report schema v1.0.0 - stable JSON structure for golden tests."""

    schema_version: str  # Schema version (e.g., "1.0.0")
    generated_at: str  # ISO-8601 UTC timestamp with 'Z' suffix
    dataset_id: str  # Aggregate SHA-256 hash format: "sha256:<hex>"
    metadata: Metadata
    summary: Summary
    results: list[RuleResult] = field(default_factory=list)  # Array of rule results
    engine: dict[str, Any] | None = None  # Optional engine metadata
    attestation: dict[str, Any] | None = None  # Optional attestation data
