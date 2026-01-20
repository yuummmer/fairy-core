# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025 Jennifer Slotnick

"""
Provenance utilities for file hashing and metadata collection.

This module provides functions for computing file hashes and summarizing
tabular file metadata (path, sha256, dimensions, headers).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path
from typing import Any, TypedDict

CANON_VERSION_V1 = "fairy-canon@1"


class RulepackIdentity(TypedDict):
    id: str
    version: str
    sha256: str


def _canonical_json(obj: Any) -> str:
    # Stable JSON for hashing: sorted keys, no whitespace
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_params_sha256(params: dict | None) -> str:
    # Always hash canonical empty object {} when missing
    canon = _canonical_json(params or {})
    return sha256(canon.encode("utf-8")).hexdigest()


def sha256_file(p: Path, *, newline_stable: bool = False) -> str:
    """
    Return sha256 hex digest of file at path p.
    If newline_stable=True, normalize CRLF/CR to LF before hashing..
    """
    h = sha256()

    if not newline_stable:
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    pending_cr = False
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            if pending_cr:
                chunk = b"\r" + chunk
                pending_cr = False

            if chunk.endswith(b"\r"):
                chunk = chunk[:-1]
                pending_cr = True

            chunk = chunk.replace(b"\r\n", b"\n")
            chunk = chunk.replace(b"\r", b"\n")
            h.update(chunk)

    if pending_cr:
        h.update(b"\n")

    return h.hexdigest()


def summarize_tabular(p: Path) -> dict[str, Any]:
    """
    Collect provenance for a TSV/CSV-like metadata file:
    -path (as string)
    -sha256
    -n_rows (data rows, not counting header)
    -n_cols
    -header (list[str])

    Will *try* to use Frictionless if available for more robust parsing.
    If that fails or isn't installed, we fall back to simple TSV splitter.
    """
    path_str = str(p)
    file_hash = sha256_file(p, newline_stable=True)

    header: list[str] = []
    n_cols = 0
    n_rows = 0

    # Try Frictionless first
    try:
        from frictionless import Resource  # type: ignore

        resource = Resource(path_str)

        # header list
        header = list(resource.header or [])
        n_cols = len(header)

        # Count rows via frictionless read_rows() (each is a dict-like row of data)
        data_rows = resource.read_rows()
        n_rows = len(data_rows)

    except Exception:
        # Fallback: naive TSV parse
        with p.open("r", encoding="utf-8") as f:
            lines = f.read().splitlines()

        if lines:
            header_line = lines[0]
            header = header_line.split("\t")
            n_cols = len(header)
            # everything after header is data rows
            n_rows = max(len(lines) - 1, 0)
        else:
            header = []
            n_cols = 0
            n_rows = 0

    return {
        "path": path_str,
        "sha256": file_hash,
        "n_rows": n_rows,
        "n_cols": n_cols,
        "header": header,
    }


def compute_dataset_id(
    *,
    inputs_sha256: Mapping[str, str],
    rulepack: RulepackIdentity,
    params_sha256: str,
    canon_version: str = CANON_VERSION_V1,
) -> str:
    """
    Versioned dataset identity.
    Depends ONLY on:
      - input file sha256s
      - rulepack id/version/sha256
      - params sha256 (hash of {} if none)
      - canon_version
    """
    payload = {
        "canon_version": canon_version,
        "algorithm": "sha256",
        "includes": ["inputs.sha256", "rulepack.sha256", "params.sha256"],
        "inputs": {k: {"sha256": v} for k, v in sorted(inputs_sha256.items())},
        "rulepack": {
            "id": rulepack["id"],
            "version": rulepack["version"],
            "sha256": rulepack["sha256"],
        },
        "params": {"sha256": params_sha256},
    }
    h = sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return f"sha256:{h}"
