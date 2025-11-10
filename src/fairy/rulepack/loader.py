from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from .schema import Rulepack


class RulepackError(Exception):
    """User-facing error for rulepack loading/validation."""


def _load_yaml_text(text: str):
    try:
        from ruamel.yaml import YAML  # optional but nicer errors

        y = YAML(typ="safe")
        return y.load(text)
    except Exception:
        import yaml  # type: ignore

        return yaml.safe_load(text)


def load_rulepack(path: str | Path) -> Rulepack:
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise RulepackError(f"Rulepack file not found: {p}")
    try:
        text = p.read_text(encoding="utf-8")
    except Exception as e:
        raise RulepackError(f"Could not read rulepack '{p}': {e}") from e
    try:
        data = _load_yaml_text(text)
    except Exception as e:
        raise RulepackError(f"YAML parse error in '{p}': {e}") from e
    if not isinstance(data, dict):
        raise RulepackError(f"Expected a YAML mapping at top-level in '{p}'.")
    try:
        return Rulepack.model_validate(data)
    except ValidationError as e:
        bullets = "; ".join(f"{err['loc']}: {err['msg']}" for err in e.errors())
        raise RulepackError(f"Rulepack schema validation failed for '{p}': {bullets}") from e
