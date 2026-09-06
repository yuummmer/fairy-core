from pathlib import Path

import pytest

from fairy.validation.rulepack_runner import run_rulepack


def test_package_rules_require_package_root(tmp_path: Path):
    rulepack = {
        "id": "test-package",
        "version": "0.1.0",
        "package": {
            "rules": [
                {
                    "id": "readme_present",
                    "type": "files_present",
                    "severity": "fail",
                    "pattern": "README*",
                    "min_count": 1,
                }
            ]
        },
    }

    with pytest.raises(ValueError, match="requires a package directory"):
        run_rulepack(
            {},
            rulepack,
            tmp_path / "rulepack.yml",
            "2026-09-05T00:00:00Z",
        )
def test_files_present_passes_when_file_exists(tmp_path: Path):
    (tmp_path / "README.md").write_text("hello")

    rulepack = {
        "id": "test-package",
        "version": "0.1.0",
        "package": {
            "rules": [
                {
                    "id": "readme_present",
                    "type": "files_present",
                    "severity": "fail",
                    "pattern": "README*",
                    "min_count": 1,
                }
            ]
        },
    }

    report = run_rulepack(
        {},
        rulepack,
        tmp_path / "rulepack.yml",
        "2026-09-05T00:00:00Z",
        package_root=tmp_path,
    )

    assert report["summary"]["pass"] == 1
    assert report["summary"]["fail"] == 0

    rule = report["resources"][0]["rules"][0]
    assert rule["status"] == "PASS"
    assert rule["evidence"]["matches"] == ["README.md"]


def test_files_present_fails_when_file_missing(tmp_path: Path):
    rulepack = {
        "id": "test-package",
        "version": "0.1.0",
        "package": {
            "rules": [
                {
                    "id": "readme_present",
                    "type": "files_present",
                    "severity": "fail",
                    "pattern": "README*",
                    "min_count": 1,
                }
            ]
        },
    }

    report = run_rulepack(
        {},
        rulepack,
        tmp_path / "rulepack.yml",
        "2026-09-05T00:00:00Z",
        package_root=tmp_path,
    )

    assert report["summary"]["fail"] == 1

    rule = report["resources"][0]["rules"][0]
    assert rule["status"] == "FAIL"
    assert rule["evidence"]["match_count"] == 0

def test_files_present_warns_when_optional_file_missing(tmp_path: Path):
    rulepack = {
        "id": "test-package",
        "version": "0.1.0",
        "package": {
            "rules": [
                {
                    "id": "code_present",
                    "type": "files_present",
                    "severity": "warn",
                    "pattern": "*.py",
                    "min_count": 1,
                }
            ]
        },
    }

    report = run_rulepack(
        {},
        rulepack,
        tmp_path / "rulepack.yml",
        "2026-09-05T00:00:00Z",
        package_root=tmp_path,
    )

    assert report["summary"]["warn"] == 1
    assert report["summary"]["fail"] == 0

    rule = report["resources"][0]["rules"][0]
    assert rule["status"] == "WARN"
    assert rule["evidence"]["match_count"] == 0