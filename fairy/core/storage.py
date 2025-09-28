from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List

APP_DIRNAME = ".fairy_data"
PROJECTS_BASENAME = "projects.json"

class Storage:
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or Path(APP_DIRNAME)
        self.data_dir.mkdir(exist_ok=True)
        self.projects_json = self.data_dir / PROJECTS_BASENAME

    def load_projects(self) -> List[Dict[str, Any]]:
        if self.projects_json.exists():
            return json.loads(self.projects_json.read_text(encoding="utf-8"))
        return []

    def save_projects(self, projects: List[Dict[str, Any]]) -> None:
        self.projects_json.write_text(json.dumps(projects, indent=2), encoding="utf-8")

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def update_project_timestamp(p: Dict[str, Any]) -> None:
    p["updated_at"] = now_iso()
