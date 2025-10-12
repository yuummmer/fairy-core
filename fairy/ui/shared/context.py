from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Any, List
from fairy.utils.projects import project_dir, exports_dir

@dataclass
class ProjectCtx:
    project: Dict[str, Any]
    projects: List[Dict[str, Any]]
    save_and_refresh: Callable[[List[Dict[str, Any]]], None]

    @property
    def id(self) -> str: return self.project["id"]
    @property
    def proj_root(self) -> Path: return Path(project_dir(self.id))
    @property
    def out_dir(self) -> Path: return Path(exports_dir(self.id))
    @property
    def save(self) -> None:
             self.save_and_refresh(self.projects)