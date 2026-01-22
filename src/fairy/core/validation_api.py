# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025 Jennifer Slotnick

# fairy/core/validation_api.py

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

# --- Basic types you already use ---


@dataclass
class WarningItem:
    # what column/field the problem is about (if any)
    column: str | None
    # machine-ish category of check, like "missing_column"
    kind: str
    # human summary of what failed ("Required column 'sample_id' is missing")
    message: str
    # "error" or "warning"
    severity: str
    # row index in the table if applicable (or -1 / None for header-level problems)
    row: int | None = None
    # optional hint for how to fix
    hint: str | None = None


@dataclass
class Meta:
    n_rows: int
    n_cols: int
    fields_validated: list[str]
    warnings: list[WarningItem]


# --- Validator interface + registry ---


class Validator(Protocol):
    name: str
    version: str

    def validate(self, path: str) -> Meta: ...


_VALIDATORS: dict[str, Validator] = {}


def register(name: str, validator: Validator):
    _VALIDATORS[name] = validator


def get_validator(kind: str) -> Validator | None:
    return _VALIDATORS.get(kind)


def validate_csv(path: str, kind: str = "rna") -> Meta:
    v = _VALIDATORS.get(kind) or _VALIDATORS.get("generic")
    if v is None:
        raise RuntimeError(f"No validator registered for kind='{kind}' or 'generic'")
    return v.validate(path)


# --- Richer FAIRy finding types we'll add soon ---


@dataclass
class Finding:
    code: str  # e.g. "GEO.REQ.MISSING_FIELD"
    severity: str  # "FAIL" | "WARN"
    where: str
    why: str
    how_to_fix: str
    details: dict[str, Any]


@dataclass
class Attestation:
    rulepack_id: str
    rulepack_version: str
    fairy_version: str
    run_at_utc: str
    submission_ready: bool
    fail_count: int
    warn_count: int


@dataclass
class Report:
    attestation: Attestation
    findings: list[Finding]


def now_utc_iso() -> str:
    fixed = os.getenv("FAIRY_FIXED_TIMESTAMP")
    if fixed:
        return fixed
    return datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
