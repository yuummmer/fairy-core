from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fairy.core.services import validator

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

    def list_profile_ids(self) -> list[str]:
        return sorted(self._profiles.keys())

    def list_profiles(self) -> list[PreflightProfile]:
        return [self._profiles[k] for k in sorted(self._profiles.keys())]


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

    return validator.run_rulepack(
        rulepack_path=rulepack,
        samples_path=samples,
        files_path=files,
        fairy_version=fairy_version,
        params=params or {},
    )


def _run_generic(
    *,
    rulepack: Path,
    inputs: dict[str, Path],
    fairy_version: str,
    params: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Spellbook/generic = 2-input preflight.
    input_01 -> samples table
    input_02 -> files table
    Returns preflight report v1 (same shape as geo), so CLI can write
    manifest/report/md consistently.
    """
    a = inputs.get("input_01")
    b = inputs.get("input_02")
    if not a or not b:
        raise ValueError("spellbook/generic requires inputs {'input_01': A, 'input_02': B}")

    return validator.run_rulepack(
        rulepack_path=rulepack,
        samples_path=a,
        files_path=b,
        fairy_version=fairy_version,
        params=params,
    )


# --- Singleton registry + entrypoint ----------------------------------------

_REGISTRY: ProfilesRegistry | None = None


def get_registry() -> ProfilesRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        reg = ProfilesRegistry()

        reg.register(
            PreflightProfile(
                id="geo",
                description="GEO-style samples/files TSV preflight",
                runner=_run_geo,
            )
        )

        # v0: two-input wrapper over the existing 2-table engine
        reg.register(
            PreflightProfile(
                id="spellbook",
                description="Validate-style preflight for exactly 2 inputs (--inputs A B)",
                runner=_run_generic,
            )
        )

        reg.register(
            PreflightProfile(
                id="generic",
                description="Alias of spellbook (2-input validate-style preflight)",
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
