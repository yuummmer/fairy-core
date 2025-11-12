# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025 Jennifer Slotnick

"""
Provenance utilities for file hashing and metadata collection.

This module provides functions for computing file hashes and summarizing
tabular file metadata (path, sha256, dimensions, headers).
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any


def sha256_file(p: Path) -> str:
    """
    Return sha256 hex digest of file at path p.
    Chunked so we don't load huge files fully into memory.
    """
    h = sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
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
    file_hash = sha256_file(p)

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


def compute_dataset_id(inputs_meta: dict[str, dict[str, Any]]) -> str:
    """
    Compute aggregate SHA-256 hash from all inputs for dataset identification.

    Creates a canonical representation of all inputs by:
    1. Sorting input names alphabetically
    2. For each input, building a canonical line: {name}\t{sha256}\t{n_rows}\t{n_cols}
    3. Joining lines with newline
    4. Computing SHA-256 hash of the resulting string
    5. Returning format: "sha256:<hex>"

    Args:
        inputs_meta: Dictionary mapping input name → metadata dict with keys:
            - sha256: str (64 hex chars) - required, but will be computed from path if missing
            - path: str - optional, used to compute sha256 if sha256 is missing
            - n_rows: int - required
            - n_cols: int - required

    Returns:
        String in format "sha256:<hex>" (64 hex chars)

    Raises:
        ValueError: If any input lacks required metadata fields:
            - sha256 (and no path available to compute it)
            - n_rows or n_cols
        FileNotFoundError: If path is provided but file doesn't exist
    """
    lines: list[str] = []

    # Sort input names alphabetically for deterministic ordering
    sorted_names = sorted(inputs_meta.keys())

    for name in sorted_names:
        meta = inputs_meta[name]

        # Get required fields
        sha256_val = meta.get("sha256")
        n_rows = meta.get("n_rows")
        n_cols = meta.get("n_cols")

        # If sha256 is missing, try to compute it from path
        if sha256_val is None:
            path_str = meta.get("path")
            if path_str:
                try:
                    path_obj = Path(path_str)
                    if not path_obj.exists():
                        raise FileNotFoundError(
                            f"Input '{name}': path '{path_str}' does not exist. "
                            "Cannot compute sha256."
                        )
                    sha256_val = sha256_file(path_obj)
                except Exception as e:
                    raise ValueError(
                        f"Input '{name}' lacks sha256 and cannot compute from path "
                        f"'{path_str}': {e}"
                    ) from e
            else:
                raise ValueError(
                    f"Input '{name}' lacks sha256 and no path available. "
                    "Compute file hash during load or omit dataset_id."
                )

        # Validate other required fields
        if n_rows is None or n_cols is None:
            raise ValueError(
                f"Input '{name}' lacks n_rows or n_cols. Required for dataset_id computation."
            )

        # Build canonical line: {name}\t{sha256}\t{n_rows}\t{n_cols}
        line = f"{name}\t{sha256_val}\t{n_rows}\t{n_cols}"
        lines.append(line)

    # Join lines with newline and compute SHA-256 hash
    canonical_string = "\n".join(lines)
    # Encode to UTF-8 bytes for hashing
    canonical_bytes = canonical_string.encode("utf-8")
    hash_obj = sha256(canonical_bytes)
    hex_digest = hash_obj.hexdigest()

    # Return format: "sha256:<hex>"
    return f"sha256:{hex_digest}"
