from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml

try:
    from fairy import __version__ as FAIRY_VERSION
except Exception:
    FAIRY_VERSION = "0.1.0"


class ParamsFileError(RuntimeError):
    """Raised when --param-file cannot be read/parsed/validated."""


def load_params_file(path: str | None) -> dict[str, Any]:
    """Load YAML params as a dict. Return {} if path is None."""
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        raise ParamsFileError(f"Param file not found: {path}")
    try:
        with p.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        raise ParamsFileError(f"Failed to parse params YAML at {path}: {e}") from e
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ParamsFileError(
            f"Top-level YAML must be a mapping (dict). Got: {type(data).__name__}"
        )
    return data


def sha256_bytes(b: bytes) -> str:
    h = sha256()
    h.update(b)
    return h.hexdigest()


def parse_inputs_kv(pairs: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise SystemExit(f"--inputs must be name=path, got '{pair}'")
        k, v = pair.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def resolve_input_path(p: Path) -> Path:
    if p.is_file():
        return p
    if p.is_dir():
        csvs = list(p.glob("*.csv"))
        if len(csvs) == 1:
            return csvs[0]
        if not csvs:
            raise FileNotFoundError(f"No CSV file found in {p}. Expected e.g. metadata.csv.")
        raise FileNotFoundError(
            f"Multiple CSVs found in {p}: {', '.join(c.name for c in csvs)}. Specify one."
        )
    raise FileNotFoundError(f"{p} is not a file or directory")


def version_text(rulepack: Path | None) -> str:
    rp = "default" if not rulepack else rulepack.name
    return f"fairy {FAIRY_VERSION}\nrulepack: {rp}"
