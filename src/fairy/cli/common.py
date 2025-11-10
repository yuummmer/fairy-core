from __future__ import annotations

from hashlib import sha256
from pathlib import Path

try:
    from fairy import __version__ as FAIRY_VERSION
except Exception:
    FAIRY_VERSION = "0.1.0"


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


def sha256_bytes(b: bytes) -> str:
    h = sha256()
    h.update(b)
    return h.hexdigest()


def version_text(rulepack: Path | None) -> str:
    rp = "default" if not rulepack else rulepack.name
    return f"fairy {FAIRY_VERSION}\nrulepack: {rp}"
