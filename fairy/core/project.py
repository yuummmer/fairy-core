from __future__ import annotations
from typing import Dict, Any
from datetime import datetime, timezone

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")

def new_project(title: str, description: str) -> Dict[str, Any]:
    now = _now_iso()
    return {
        "id": f"prj_{int(datetime.now(timezone.utc).timestamp())}",
        "title": title,
        "description": description,
        "status": "In Progress",
        "created_at": now,
        "updated_at": now,
        "type": "RNA-seq",          # starter default; extensible later
        "tags": [],                 # e.g., ["bulk", "human"]
        "data_inventory": [],
        "permissions": {"contains_human_data": None, "irb_required": None, "notes": ""},
        "deid": {"strategy": "", "notes": ""},
        "metadata": {"project": {}, "samples": []},
        "repository": {"choice": None, "notes": ""},
        "exports": []
    }
