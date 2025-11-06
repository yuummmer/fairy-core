import json
import re
from pathlib import Path

VOLATILE_KEYS = {"timestamp", "duration_ms", "run_id", "abs_path"}


def _strip_volatile(obj):
    if isinstance(obj, dict):
        return {k: _strip_volatile(v) for k, v in obj.items() if k not in VOLATILE_KEYS}
    if isinstance(obj, list):
        return [_strip_volatile(x) for x in obj]
    if isinstance(obj, str):
        # normalize OS paths and temp dirs if needed
        obj = obj.replace("\\", "/")
        obj = re.sub(r"/tmp/[^/]+", "/tmp/XXX", obj)
    return obj


def load_json(path: Path):
    return json.loads(Path(path).read_text())


def normalize_json(path: Path):
    return _strip_volatile(load_json(path))
