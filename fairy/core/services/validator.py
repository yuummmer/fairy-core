# fairy/core/services/validator.py
from dataclasses import dataclass
from typing import List, Dict, Protocol

@dataclass
class WarningItem:
    column: str
    check: str
    failure: str
    index: int

@dataclass
class Meta:
    n_rows: int
    n_cols: int
    fields_validated: List[str]
    warnings: List[WarningItem]

class Validator(Protocol):
    name: str
    version: str
    def validate(self, path: str) -> Meta: ...

# registry
_REGISTRY: Dict[str, Validator] = {}

def register(kind: str, validator: Validator):
    _REGISTRY[kind] = validator

def validate_csv(path: str, kind: str = "rna") -> Meta:
    # fallback to generic if kind not found
    v = _REGISTRY.get(kind) or _REGISTRY["generic"]
    return v.validate(path)
