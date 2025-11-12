import json
import re
from pathlib import Path

# include keys that vary run-to-run in your current CLI output
VOLATILE_KEYS = {
    "run_at_utc",
    "generated_at",  # New v1 field (replaces run_at_utc)
    "sha256",
    "timestamp",
    "duration_ms",
    "run_id",
    "path",
}


def _strip_volatile(obj):
    if isinstance(obj, dict):
        return {k: _strip_volatile(v) for k, v in obj.items() if k not in VOLATILE_KEYS}
    if isinstance(obj, list):
        return [_strip_volatile(x) for x in obj]
    if isinstance(obj, str):
        # normalize path separators
        obj = obj.replace("\\", "/")
        # normalize tmp dirs
        obj = re.sub(r"/tmp/[^/]+", "/tmp/XXX", obj)
    return obj


def load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def normalize_json(path: Path):
    return _strip_volatile(load_json(path))
