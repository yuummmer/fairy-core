from pathlib import Path

import pytest

from fairy.validation.rulepack_runner import (
    MAX_PACKAGE_MATCHES,
    check_files_present,
    run_rulepack,
    write_markdown,
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


def test_referenced_artifacts_passes_when_all_references_exist(tmp_path: Path):
    reads = tmp_path / "reads"
    reads.mkdir()

    for filename in [
        "s1-r1.fastq.gz",
        "s1-r2.fastq.gz",
        "s2-r1.fastq.gz",
        "s2-r2.fastq.gz",
    ]:
        (reads / filename).write_bytes(b"")

    manifest = tmp_path / "manifest.tsv"
    manifest.write_text(
        "sample-id\tforward-path\treverse-path\n"
        "sample1\treads/s1-r1.fastq.gz\treads/s1-r2.fastq.gz\n"
        "sample2\treads/s2-r1.fastq.gz\treads/s2-r2.fastq.gz\n",
        encoding="utf-8",
    )

    rulepack = {
        "id": "test-referenced-artifacts",
        "version": "0.1.0",
        "package": {
            "rules": [
                {
                    "id": "reads_exist",
                    "type": "referenced_artifacts",
                    "severity": "fail",
                    "resource": "manifest",
                    "columns": ["forward-path", "reverse-path"],
                }
            ]
        },
    }

    report = run_rulepack(
        {"manifest": manifest},
        rulepack,
        tmp_path / "rulepack.yml",
        "2026-09-07T00:00:00Z",
        package_root=tmp_path,
    )

    rule = report["resources"][-1]["rules"][0]

    assert rule["status"] == "PASS"
    assert rule["evidence"]["reference_count"] == 4
    assert rule["evidence"]["missing_count"] == 0


def test_referenced_artifacts_fails_when_reference_is_missing(tmp_path: Path):
    reads = tmp_path / "reads"
    reads.mkdir()

    for filename in [
        "s1-r1.fastq.gz",
        "s1-r2.fastq.gz",
        "s2-r1.fastq.gz",
    ]:
        (reads / filename).write_bytes(b"")

    manifest = tmp_path / "manifest.tsv"
    manifest.write_text(
        "sample-id\tforward-path\treverse-path\n"
        "sample1\treads/s1-r1.fastq.gz\treads/s1-r2.fastq.gz\n"
        "sample2\treads/s2-r1.fastq.gz\treads/s2-r2.fastq.gz\n",
        encoding="utf-8",
    )

    rulepack = {
        "id": "test-referenced-artifacts",
        "version": "0.1.0",
        "package": {
            "rules": [
                {
                    "id": "reads_exist",
                    "type": "referenced_artifacts",
                    "severity": "fail",
                    "resource": "manifest",
                    "columns": ["forward-path", "reverse-path"],
                }
            ]
        },
    }

    report = run_rulepack(
        {"manifest": manifest},
        rulepack,
        tmp_path / "rulepack.yml",
        "2026-09-07T00:00:00Z",
        package_root=tmp_path,
    )

    rule = report["resources"][-1]["rules"][0]

    assert rule["status"] == "FAIL"
    assert rule["evidence"]["reference_count"] == 4
    assert rule["evidence"]["missing_count"] == 1
    assert rule["evidence"]["missing"] == [
        {
            "row": 2,
            "column": "reverse-path",
            "reference": "reads/s2-r2.fastq.gz",
            "resolved": "reads/s2-r2.fastq.gz",
        }
    ]


def test_referenced_artifacts_resolves_pwd_against_package_root(tmp_path: Path):
    reads = tmp_path / "pe-64"
    reads.mkdir()

    (reads / "s1-r1.fastq.gz").write_bytes(b"")

    manifest = tmp_path / "manifest.tsv"
    manifest.write_text(
        "sample-id\tforward-path\n" "sample1\t$PWD/pe-64/s1-r1.fastq.gz\n",
        encoding="utf-8",
    )

    rulepack = {
        "id": "test-referenced-artifacts-pwd",
        "version": "0.1.0",
        "package": {
            "rules": [
                {
                    "id": "reads_exist",
                    "type": "referenced_artifacts",
                    "severity": "fail",
                    "resource": "manifest",
                    "columns": ["forward-path"],
                }
            ]
        },
    }

    report = run_rulepack(
        {"manifest": manifest},
        rulepack,
        tmp_path / "rulepack.yml",
        "2026-09-07T00:00:00Z",
        package_root=tmp_path,
    )

    rule = report["resources"][-1]["rules"][0]

    assert rule["status"] == "PASS"
    assert rule["evidence"]["reference_count"] == 1
    assert rule["evidence"]["missing_count"] == 0


def test_referenced_artifacts_reports_missing_pwd_reference(tmp_path: Path):
    reads = tmp_path / "pe-64"
    reads.mkdir()

    manifest = tmp_path / "manifest.tsv"
    manifest.write_text(
        "sample-id\tforward-path\n" "sample2\t$PWD/pe-64/s2-r2.fastq.gz\n",
        encoding="utf-8",
    )

    rulepack = {
        "id": "test-referenced-artifacts-pwd-missing",
        "version": "0.1.0",
        "package": {
            "rules": [
                {
                    "id": "reads_exist",
                    "type": "referenced_artifacts",
                    "severity": "fail",
                    "resource": "manifest",
                    "columns": ["forward-path"],
                }
            ]
        },
    }

    report = run_rulepack(
        {"manifest": manifest},
        rulepack,
        tmp_path / "rulepack.yml",
        "2026-09-07T00:00:00Z",
        package_root=tmp_path,
    )

    rule = report["resources"][-1]["rules"][0]

    assert rule["status"] == "FAIL"
    assert rule["evidence"]["reference_count"] == 1
    assert rule["evidence"]["missing_count"] == 1
    assert rule["evidence"]["missing"] == [
        {
            "row": 1,
            "column": "forward-path",
            "reference": "$PWD/pe-64/s2-r2.fastq.gz",
            "resolved": "pe-64/s2-r2.fastq.gz",
        }
    ]

def test_referenced_artifacts_markdown_includes_missing_reference_details(tmp_path: Path):
    reads = tmp_path / "pe-64"
    reads.mkdir()

    manifest = tmp_path / "manifest.tsv"
    manifest.write_text(
        "sample-id\tforward-path\n"
        "sample2\t$PWD/pe-64/s2-r2.fastq.gz\n",
        encoding="utf-8",
    )

    rulepack = {
        "id": "test-referenced-artifacts-markdown",
        "version": "0.1.0",
        "package": {
            "rules": [
                {
                    "id": "reads_exist",
                    "type": "referenced_artifacts",
                    "severity": "fail",
                    "resource": "manifest",
                    "columns": ["forward-path"],
                }
            ]
        },
    }

    report = run_rulepack(
        {"manifest": manifest},
        rulepack,
        tmp_path / "rulepack.yml",
        "2026-09-07T00:00:00Z",
        package_root=tmp_path,
    )

    markdown = write_markdown(report)

    assert "References checked: 1" in markdown
    assert "Missing references: 1" in markdown
    assert "Row 1, `forward-path`" in markdown
    assert "Reference: `$PWD/pe-64/s2-r2.fastq.gz`" in markdown
    assert "Resolved: `pe-64/s2-r2.fastq.gz`" in markdown