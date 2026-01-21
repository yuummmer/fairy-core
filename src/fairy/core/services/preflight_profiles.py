from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# --- Profile interface -------------------------------------------------------

RunnerFn = Callable[..., dict[str, Any]]


@dataclass(frozen=True)
class PreflightProfile:
    id: str
    description: str
    runner: RunnerFn


class ProfileNotFoundError(ValueError):
    pass


class ProfilesRegistry:
    def __init__(self) -> None:
        self._profiles: dict[str, PreflightProfile] = {}

    def register(self, profile: PreflightProfile) -> None:
        if profile.id in self._profiles:
            raise ValueError(f"Duplicate profile id: {profile.id}")
        self._profiles[profile.id] = profile

    def get(self, profile_id: str) -> PreflightProfile:
        try:
            return self._profiles[profile_id]
        except KeyError as e:
            raise ProfileNotFoundError(f"Unknown profile: {profile_id}") from e

    def list(self) -> list[dict[str, str]]:
        return [
            {"id": p.id, "description": p.description}
            for p in sorted(self._profiles.values(), key=lambda x: x.id)
        ]


# --- Built-in runners --------------------------------------------------------


def _run_geo(
    *,
    rulepack: Path,
    inputs: dict[str, Any],
    fairy_version: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    # geo expects samples + files
    samples = inputs.get("samples")
    files = inputs.get("files")
    if not isinstance(samples, Path) or not isinstance(files, Path):
        raise ValueError("geo profile requires inputs['samples'] and inputs['files'] as Paths")

    from .validator import run_rulepack  # existing GEO runner

    return run_rulepack(
        rulepack_path=rulepack,
        samples_path=samples,
        files_path=files,
        fairy_version=fairy_version,
        params=params,
    )


def _run_generic(
    *,
    rulepack: Path,
    inputs: dict[str, Any],
    fairy_version: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    # Starter implementation:
    # - For #121, either raise NotImplemented OR call existing generic runner if present.
    #
    # If you already have a generic engine runner (rulepack_runner.py), wire it here.
    #
    # Example shape: inputs may be {"inputs": [Path(...), Path(...)]}
    #
    # For now, keep it explicit so #113 can implement it cleanly.
    raise NotImplementedError("generic profile runner will be implemented in #113")


# --- Singleton registry + entrypoint ----------------------------------------

_REGISTRY: ProfilesRegistry | None = None


def get_registry() -> ProfilesRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        reg = ProfilesRegistry()
        reg.register(
            PreflightProfile(
                id="geo", description="GEO-style samples/files TSV preflight", runner=_run_geo
            )
        )
        reg.register(
            PreflightProfile(
                id="generic",
                description="Generic validate-style inputs preflight",
                runner=_run_generic,
            )
        )
        _REGISTRY = reg
    return _REGISTRY


def run_profile(
    profile_id: str,
    *,
    rulepack: Path,
    inputs: dict[str, Any],
    fairy_version: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reg = get_registry()
    profile = reg.get(profile_id)
    return profile.runner(
        rulepack=rulepack,
        inputs=inputs,
        fairy_version=fairy_version,
        params=params or {},
    )
