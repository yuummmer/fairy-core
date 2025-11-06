# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025 Jennifer Slotnick

import json
import time
from pathlib import Path

ROOT = Path(".fairy_data")


def project_dir(project_id: str) -> Path:
    """Ensure project dirs exist and return the project path."""
    p = ROOT / "projects" / project_id
    (p / "files").mkdir(parents=True, exist_ok=True)
    return p


def exports_dir(project_id: str) -> Path:
    d = project_dir(project_id) / "exports"
    d.mkdir(parents=True, exist_ok=True)
    return d


def manifest_path(project_id: str) -> Path:
    return project_dir(project_id) / "manifest.json"


def load_manifest(project_id: str) -> dict:
    mp = manifest_path(project_id)
    if mp.exists():
        return json.loads(mp.read_text(encoding="utf-8"))
    return {"project_id": project_id, "created_at": time.time(), "files": []}


def save_manifest(project_id: str, manifest: dict) -> None:
    manifest_path(project_id).write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def load_manifests(project_ids: list[str]) -> dict[str, dict]:
    """Convenience: load manifests for a list of projects."""
    return {pid: load_manifest(pid) for pid in project_ids}
