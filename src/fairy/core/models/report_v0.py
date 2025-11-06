# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025 Jennifer Slotnick

from dataclasses import dataclass, field
from typing import Any


@dataclass
class InputFile:
    path: str
    bytes: int


@dataclass
class Inputs:
    project_dir: str
    files: list[InputFile]


@dataclass
class DatasetId:
    filename: str
    sha256: str


@dataclass
class Rulepack:
    name: str
    version: str


@dataclass
class Provenance:
    license: str | None = None
    source_url: str | None = None
    notes: str | None = None


@dataclass
class Summary:
    n_rows: int
    n_cols: int
    fields_validated: list[str]


@dataclass
class WarningItem:
    column: str
    check: str
    failure: str
    index: int


@dataclass
class ReportV0:
    version: str
    run_at: str
    dataset_id: DatasetId
    summary: Summary
    warnings: list[WarningItem] = field(default_factory=list)
    rulepacks: list[Rulepack] = field(default_factory=list)
    provenance: Provenance = field(default_factory=Provenance)
    inputs: Inputs = field(default_factory=lambda: Inputs(project_dir=".", files=[]))
    checks: list[dict[str, Any]] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=lambda: {"preflight": 0.0})
