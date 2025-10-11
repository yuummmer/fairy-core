from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path
from typing import List, Optional

from ..models.report_v0 import (
    DatasetId,
    InputFile,
    Inputs,
    Provenance,
    ReportV0,
    Rulepack,
    Summary,
    WarningItem,
)

ISO_UTC = "%Y-%m-%dT%H:%M:%SZ"


def _now_utc_iso() -> str:
    # timezone-aware, then render with trailing Z
    return datetime.now(UTC).strftime(ISO_UTC)


def _posix_rel(child: Path, root: Path) -> str:
    """Return POSIX-style path for child relative to root; absolute if outside."""
    try:
        rel = child.resolve(strict=False).relative_to(root.resolve(strict=False))
    except Exception:
        rel = child.resolve(strict=False)
    return rel.as_posix()


def write_report(
    out_dir: str | Path,
    *,
    filename: str,
    sha256: str,
    meta: dict,  # expects: n_rows, n_cols, fields_validated, warnings[]
    rulepacks: Optional[List[dict]] = None,
    provenance: Optional[dict] = None,
    input_path: str | Path | None = None,
) -> Path:
    """Create project_dir/reports/report_v0.json (pretty, deterministic key order)."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Determine project_dir and file info
    if input_path is not None:
        project_dir = Path(input_path).resolve().parent
        data_file = Path(input_path).resolve()
    else:
        project_dir = Path.cwd().resolve()
        data_file = (project_dir / filename).resolve()

    size_bytes = data_file.stat().st_size if data_file.exists() else 0
    files = []
    if data_file.exists():
        files = [InputFile(path=_posix_rel(data_file, project_dir), bytes=size_bytes)]

    # Determinism niceties
    warnings_list = [WarningItem(**w) for w in meta.get("warnings", [])]
    warnings_list.sort(key=lambda w: (w.column, w.index, w.check))
    rulepacks_list = [Rulepack(**rp) for rp in (rulepacks or [])]
    rulepacks_list.sort(key=lambda r: (r.name, r.version))

    report = ReportV0(
        version="0.1.0",
        run_at=_now_utc_iso(),
        dataset_id=DatasetId(filename=filename, sha256=sha256),
        summary=Summary(
            n_rows=int(meta.get("n_rows", 0)),
            n_cols=int(meta.get("n_cols", 0)),
            fields_validated=sorted(list(meta.get("fields_validated", []))),
        ),
        warnings=warnings_list,
        rulepacks=rulepacks_list,
        provenance=Provenance(**(provenance or {})),
        inputs=Inputs(project_dir=str(project_dir), files=files),
        checks=[],  # v0: present but empty
        scores={"preflight": 0.0},
    )

    path = out_path / "report_v0.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(
            report,
            f,
            default=lambda o: o.__dict__,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        f.write("\n")
    return path
