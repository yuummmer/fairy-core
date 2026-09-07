from pathlib import Path

from fairy.validation.rulepack_runner import run_rulepack, write_markdown


def test_files_present_markdown_includes_package_evidence():
    report = {
        "engine": {
            "fairy_core_version": "0.2.3",
        },
        "attestation": {
            "timestamp": "2026-09-06T00:00:00+00:00",
            "rulepack": {
                "id": "package-demo",
                "version": "0.1.0",
                "path": "/tmp/rulepack.yaml",
            },
            "inputs": [],
        },
        "summary": {
            "pass": 1,
            "warn": 0,
            "fail": 0,
        },
        "resources": [
            {
                "name": "package",
                "path": "/tmp/submission",
                "rules": [
                    {
                        "id": "readme_present",
                        "type": "files_present",
                        "severity": "fail",
                        "status": "PASS",
                        "evidence": {
                            "patterns": ["README*", "docs/*.md"],
                            "min_count": 1,
                            "match_count": 2,
                            "matches": [
                                "README.md",
                                "docs/methods.md",
                            ],
                        },
                    }
                ],
            }
        ],
    }

    markdown = write_markdown(report)

    assert "## Findings for `/tmp/submission`" in markdown
    assert "### [PASS] readme_present — files_present" in markdown

    assert "Patterns:" in markdown
    assert "- `README*`" in markdown
    assert "- `docs/*.md`" in markdown

    assert "Matched files: 2 (minimum required: 1)" in markdown

    assert "Matches:" in markdown
    assert "- `README.md`" in markdown
    assert "- `docs/methods.md`" in markdown


def _package_rulepack() -> dict:
    return {
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


def _table_rulepack() -> dict:
    return {
        "id": "test-table",
        "version": "0.1.0",
        "rules": [
            {
                "id": "species_required",
                "type": "required",
                "severity": "fail",
                "config": {
                    "pattern": "penguins_small.csv",
                    "columns": ["species"],
                },
            }
        ],
    }


def _fixture_csv() -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures" / "penguins_small.csv"


def test_package_only_markdown_omits_inputs(tmp_path: Path):
    (tmp_path / "README.md").write_text("hello")

    report = run_rulepack(
        {},
        _package_rulepack(),
        tmp_path / "rulepack.yml",
        "2026-09-06T00:00:00Z",
        package_root=tmp_path,
    )

    assert report["attestation"]["inputs"] == []

    markdown = write_markdown(report)

    assert "## Inputs" not in markdown
    assert "## Findings for" in markdown
    assert "### [PASS] readme_present — files_present" in markdown


def test_table_only_markdown_keeps_inputs():
    csv_path = _fixture_csv()

    report = run_rulepack(
        {"default": csv_path},
        _table_rulepack(),
        csv_path.parent / "rulepack.yml",
        "2026-09-06T00:00:00Z",
    )

    markdown = write_markdown(report)

    assert "## Inputs" in markdown
    assert "penguins_small.csv" in markdown


def test_mixed_package_and_table_markdown_keeps_inputs(tmp_path: Path):
    (tmp_path / "README.md").write_text("hello")
    csv_path = _fixture_csv()

    rulepack = _table_rulepack()
    rulepack["package"] = _package_rulepack()["package"]

    report = run_rulepack(
        {"default": csv_path},
        rulepack,
        tmp_path / "rulepack.yml",
        "2026-09-06T00:00:00Z",
        package_root=tmp_path,
    )

    markdown = write_markdown(report)

    assert "## Inputs" in markdown
    assert "penguins_small.csv" in markdown
    assert "readme_present" in markdown
