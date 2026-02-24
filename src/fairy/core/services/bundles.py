from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

# -----------------------------
# Errors
# -----------------------------


class BundleError(RuntimeError):
    """User-facing bundling errors (unknown format, invalid opts, IO, packager failure)."""


# -----------------------------
# Core types
# -----------------------------


@dataclass(frozen=True)
class BundleRequest:
    payload_path: Path
    artifacts_dir: Path
    out_dir: Path
    dataset_id: str | None = None


@dataclass(frozen=True)
class BundleResult:
    bundle_path: Path
    format_id: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


class Packager(Protocol):
    format_id: str
    description: str | None

    def create_bundle(self, req: BundleRequest, options: Mapping[str, Any]) -> BundleResult: ...


@dataclass(frozen=True)
class BundleFormatSpec:
    packager: Packager
    default_options: dict[str, Any] = field(default_factory=dict)
    description: str | None = None


# -----------------------------
# Registry
# -----------------------------


class BundleRegistry:
    def __init__(self) -> None:
        self.__formats: dict[str, BundleFormatSpec] = {}

    def register(self, spec: BundleFormatSpec) -> None:
        fmt = spec.packager.format_id
        if not fmt:
            raise BundleError("Packager format_id must be a non-empty string.")
        if fmt in self.__formats:
            raise BundleError(f"Duplicate bundle format: {fmt}")
        self.__formats[fmt] = spec

    def get(self, format_id: str) -> BundleFormatSpec:
        try:
            return self.__formats[format_id]
        except KeyError as err:
            available = ", ".join(self.list_format_ids())
            raise BundleError(
                f"Unknown bundle format: {format_id}. Available: {available or '(none)'}"
            ) from err

    def list_format_ids(self) -> list[str]:
        return sorted(self.__formats.keys())

    def list_formats(self) -> list[tuple[str, str]]:
        """
        Returns [(format_id, description)] in stable order for CLI help.
        """
        rows: list[tuple[str, str]] = []
        for fmt in self.list_format_ids():
            spec = self.__formats[fmt]
            desc = spec.description or getattr(spec.packager, "description", None) or ""
            rows.append((fmt, desc))
        return rows


# -----------------------------
# Singleton registry
# -----------------------------

BUNDLE_REGISTRY = BundleRegistry()

# -----------------------------
# Helpers (core invocation logic)
# -----------------------------


def merge_bundle_options(
    *,
    defaults: Mapping[str, Any] | None = None,
    config: Mapping[str, Any] | None = None,
    cli: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Merge options with precedence:
        defaults < config < cli
    """
    merged: dict[str, Any] = {}
    if defaults:
        merged.update(dict(defaults))
    if config:
        merged.update(dict(config))
    if cli:
        merged.update(dict(cli))
    return merged


def create_bundle(
    *,
    format_id: str,
    payload_path: Path,
    artifacts_dir: Path,
    out_dir: Path,
    dataset_id: str | None = None,
    config_options: Mapping[str, Any] | None = None,
    cli_options: Mapping[str, Any] | None = None,
) -> BundleResult:
    """
    Core entry point: resolve packager, merge options, invoke packager.
    """
    spec = BUNDLE_REGISTRY.get(format_id)

    req = BundleRequest(
        payload_path=payload_path,
        artifacts_dir=artifacts_dir,
        out_dir=out_dir,
        dataset_id=dataset_id,
    )

    options = merge_bundle_options(
        defaults=spec.default_options,
        config=config_options,
        cli=cli_options,
    )

    try:
        return spec.packager.create_bundle(req, options)
    except BundleError:
        # Already user-facing. re-raise
        raise
    except Exception as e:
        # Wrap unexpected errors so CLI surfaces cleanly
        raise BundleError(f"Bundle creation failed for format '{format_id}': {e}") from e
