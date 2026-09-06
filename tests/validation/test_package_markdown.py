from fairy.validation.rulepack_runner import write_markdown


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
