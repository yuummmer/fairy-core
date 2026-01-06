# src/fairy/core/services/manifest.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .provenance import compute_dataset_id


def now_utc_iso_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_manifest_v1(
    *,
    inputs_meta: dict[str, dict[str, Any]],
    fairy_version: str,
    source_report: str,
    rulepack_id: str,
    rulepack_version: str,
    files: list[dict[str, Any]],
    created_at_utc: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "dataset_id": compute_dataset_id(inputs_meta),
        "created_at_utc": created_at_utc or now_utc_iso_z(),
        "fairy_version": fairy_version,
        "hash_algorithm": "sha256",
        "rulepack": {"id": rulepack_id, "version": rulepack_version},
        "source_report": source_report,
        "files": files,
    }
