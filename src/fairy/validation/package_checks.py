from __future__ import annotations

import glob
from pathlib import Path
from typing import Any

MAX_PACKAGE_MATCHES = 20


def _status_from_severity(severity: str) -> str:
    return "WARN" if severity == "warn" else "FAIL"


def check_files_present(
    package_root: Path,
    *,
    pattern: str | None = None,
    patterns: list[str] | None = None,
    min_count: int = 1,
    severity: str = "fail",
) -> tuple[str, dict[str, Any]]:
    wanted_patterns: list[str] = []

    if pattern:
        wanted_patterns.append(pattern)

    if patterns:
        wanted_patterns.extend(patterns)

    if not wanted_patterns:
        return "FAIL", {"error": "config_missing_pattern"}

    if not isinstance(min_count, int) or min_count < 0:
        return "FAIL", {
            "error": "config_invalid_min_count",
            "min_count": min_count,
        }

    matched: set[str] = set()

    for pat in wanted_patterns:
        for match in glob.iglob(
            pat,
            root_dir=package_root,
            recursive=True,
        ):
            path = package_root / match
            if path.is_file():
                matched.add(Path(match).as_posix())

    all_matches = sorted(matched)

    evidence = {
        "patterns": wanted_patterns,
        "min_count": min_count,
        "match_count": len(all_matches),
        "matches": all_matches[:MAX_PACKAGE_MATCHES],
        "matches_truncated": len(all_matches) > MAX_PACKAGE_MATCHES,
    }

    if len(all_matches) < min_count:
        return _status_from_severity(severity), evidence

    return "PASS", evidence


def check_referenced_artifacts(
    package_root: Path,
    frame: Any,
    *,
    columns: list[str] | None = None,
    severity: str = "fail",
) -> tuple[str, dict[str, Any]]:
    if not columns:
        return "FAIL", {"error": "config_missing_columns"}

    missing_columns = [column for column in columns if column not in frame.columns]
    if missing_columns:
        return "FAIL", {
            "error": "config_missing_columns",
            "columns": missing_columns,
        }

    reference_count = 0
    missing: list[dict[str, Any]] = []

    for row_number, (_, row) in enumerate(frame.iterrows(), start=1):
        for column in columns:
            reference = str(row[column]).strip()

            if not reference:
                continue

            reference_count += 1

            if reference.startswith("$PWD/"):
                resolved = reference[len("$PWD/") :]
            else:
                resolved = Path(reference).as_posix()

            artifact_path = package_root / resolved

            if not artifact_path.is_file():
                missing.append(
                    {
                        "row": row_number,
                        "column": column,
                        "reference": reference,
                        "resolved": resolved,
                    }
                )

    evidence = {
        "reference_count": reference_count,
        "missing_count": len(missing),
        "missing": missing,
    }

    if missing:
        return _status_from_severity(severity), evidence

    return "PASS", evidence
