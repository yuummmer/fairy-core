# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025 Jennifer Slotnick

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_DIRNAME = ".fairy_data"
PROJECTS_BASENAME = "projects.json"


class Storage:
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or Path(APP_DIRNAME)
        self.data_dir.mkdir(exist_ok=True)
        self.projects_json = self.data_dir / PROJECTS_BASENAME

    def load_projects(self) -> list[dict[str, Any]]:
        if self.projects_json.exists():
            return json.loads(self.projects_json.read_text(encoding="utf-8"))
        return []

    def save_projects(self, projects: list[dict[str, Any]]) -> None:
        self.projects_json.write_text(json.dumps(projects, indent=2), encoding="utf-8")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def update_project_timestamp(p: dict[str, Any]) -> None:
    p["updated_at"] = now_iso()
