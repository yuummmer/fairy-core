# src/fairy/core/services/manifest.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def now_utc_iso_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_manifest_v1(
    *,
    dataset_id: str,
    fairy_version: str,
    source_report: str,
    rulepack_id: str,
    rulepack_version: str,
    files: list[dict[str, Any]],
    created_at_utc: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "dataset_id": dataset_id,
        "created_at_utc": created_at_utc or now_utc_iso_z(),
        "fairy_version": fairy_version,
        "hash_algorithm": "sha256",
        "rulepack": {"id": rulepack_id, "version": rulepack_version},
        "source_report": source_report,
        "files": files,
    }
