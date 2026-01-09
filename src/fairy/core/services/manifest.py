# src/fairy/core/services/manifest.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

Role = Literal["data", "metadata", "report", "log", "other"]


def now_utc_iso_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def infer_role(relpath: str) -> Role:
    # Normalize (schema disallows backslashes, but be defensive)
    p = relpath.replace("\\", "/")
    name = p.rsplit("/", 1)[-1].lower()

    # Metadata artifacts
    if name == "manifest.json":
        return "metadata"
    if name in {"samples.tsv", "files.tsv"}:
        return "metadata"

    # Logs
    if name.endswith(".log"):
        return "log"

    # Reports (FAIRy outputs)
    # (Matches your current convention: *report*.json / *report*.md)
    if ("report" in name) and name.endswith((".json", ".md")):
        return "report"

    # Data payloads (future-proof; ok to be broad)
    if name.endswith((".csv", ".tsv", ".txt", ".fasta", ".fa", ".fastq", ".fq", ".bam", ".cram")):
        return "data"

    return "other"


def _ensure_roles(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for f in files:
        ff = dict(f)
        if not ff.get("role"):
            ff["role"] = infer_role(str(ff.get("path", "")))
        out.append(ff)
    return out


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
    files = _ensure_roles(files)

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
