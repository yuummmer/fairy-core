from pathlib import Path

import pytest

from fairy.validation.rulepack_runner import (
    MAX_PACKAGE_MATCHES,
    check_files_present,
    run_rulepack,
)


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


def test_files_present_glob_semantics(tmp_path: Path):
    (tmp_path / "README.md").write_text("root readme")

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "results.csv").write_text("a,b\n1,2\n")

    nested_data = data_dir / "nested"
    nested_data.mkdir()
    (nested_data / "more.csv").write_text("a,b\n3,4\n")

    nested_docs = tmp_path / "docs"
    nested_docs.mkdir()
    (nested_docs / "README-extra.md").write_text("nested readme")

    rulepack = {
        "id": "test-package-globs",
        "version": "0.1.0",
        "package": {
            "rules": [
                {
                    "id": "root_readme",
                    "type": "files_present",
                    "severity": "fail",
                    "pattern": "README*",
                },
                {
                    "id": "one_level_csv",
                    "type": "files_present",
                    "severity": "fail",
                    "pattern": "data/*.csv",
                },
                {
                    "id": "recursive_data",
                    "type": "files_present",
                    "severity": "fail",
                    "pattern": "data/**",
                    "min_count": 2,
                },
                {
                    "id": "readme_any_depth",
                    "type": "files_present",
                    "severity": "fail",
                    "pattern": "**/README*",
                    "min_count": 2,
                },
            ]
        },
    }

    report = run_rulepack(
        {},
        rulepack,
        tmp_path / "rulepack.yml",
        "2026-09-06T00:00:00Z",
        package_root=tmp_path,
    )

    rules = {rule["id"]: rule for rule in report["resources"][0]["rules"]}

    assert rules["root_readme"]["evidence"]["matches"] == ["README.md"]

    assert rules["one_level_csv"]["evidence"]["matches"] == ["data/results.csv"]

    assert rules["recursive_data"]["evidence"]["matches"] == [
        "data/nested/more.csv",
        "data/results.csv",
    ]

    assert rules["readme_any_depth"]["evidence"]["matches"] == [
        "README.md",
        "docs/README-extra.md",
    ]

    assert report["summary"]["pass"] == 4
    assert report["summary"]["fail"] == 0


def test_files_present_supports_multiple_patterns(tmp_path: Path):
    (tmp_path / "analysis.py").write_text("print('hello')")
    (tmp_path / "notes.txt").write_text("notes")

    rulepack = {
        "id": "test-package-patterns",
        "version": "0.1.0",
        "package": {
            "rules": [
                {
                    "id": "code_present",
                    "type": "files_present",
                    "severity": "fail",
                    "patterns": [
                        "*.R",
                        "*.py",
                        "*.ipynb",
                    ],
                    "min_count": 1,
                }
            ]
        },
    }

    report = run_rulepack(
        {},
        rulepack,
        tmp_path / "rulepack.yml",
        "2026-09-06T00:00:00Z",
        package_root=tmp_path,
    )

    rule = report["resources"][0]["rules"][0]

    assert rule["status"] == "PASS"
    assert rule["evidence"]["patterns"] == [
        "*.R",
        "*.py",
        "*.ipynb",
    ]
    assert rule["evidence"]["matches"] == ["analysis.py"]

def test_files_present_caps_match_evidence(tmp_path: Path):
    for i in range(MAX_PACKAGE_MATCHES + 5):
        (tmp_path / f"file-{i:02d}.txt").write_text("x", encoding="utf-8")

    status, evidence = check_files_present(
        tmp_path,
        pattern="*.txt",
        min_count=1,
        severity="fail",
    )

    assert status == "PASS"
    assert evidence["match_count"] == MAX_PACKAGE_MATCHES + 5
    assert len(evidence["matches"]) == MAX_PACKAGE_MATCHES
    assert evidence["matches_truncated"] is True