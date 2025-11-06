# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025 Jennifer Slotnick

from hashlib import sha256
from pathlib import Path

import pandas as pd

from fairy.core.services.validator import validate_csv

# Ensure validators self-register on import (side effects)
from fairy.core.validators import generic as _generic  # noqa: F401


def _sha256_file(path: str) -> str:
    h = sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def process_csv(path: str):
    """Shim for legacy tests: returns (meta, df)."""
    df = pd.read_csv(path)
    m = validate_csv(path, kind="rna")
    p = Path(path)
    meta = {
        "filename": p.name,
        "sha256": _sha256_file(path),
        "n_rows": m.n_rows,
        "n_cols": m.n_cols,
        "fields_validated": m.fields_validated,
        "warnings": [w.__dict__ for w in m.warnings],
    }
    return meta, df
