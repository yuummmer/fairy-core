from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Meta(BaseModel):
    name: str
    version: str
    description: str | None = None


class Rule(BaseModel):
    id: str
    type: str
    message: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)

    model_config = dict(extra="allow")


class Rulepack(BaseModel):
    meta: Meta
    rules: list[Rule] = Field(min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)
