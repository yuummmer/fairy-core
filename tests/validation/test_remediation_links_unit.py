from fairy.validation.rulepack_runner import run_rulepack, write_markdown


def test_remediation_links_appear_in_json_and_markdown(tmp_path):
    # Arrange: write a tiny CSV
    csv_path = tmp_path / "data.csv"
    csv_path.write_text(
        "primary_id,external_url\n"
        ",https://example.org/1\n"
        "ABC,https://example.org/2\n"
        ",www.example.org/3\n"
    )

    # Rulepack dict (no YAML dependency needed)
    rulepack = {
        "id": "remediation-demo",
        "version": "0.0.0",
        "resources": [
            {
                "pattern": "data.csv",
                "rules": [
                    {
                        "id": "primary_id_required",
                        "type": "required",
                        "severity": "fail",
                        "columns": ["primary_id"],
                        "remediation_link_column": "external_url",
                        "remediation_link_label": "Open record",
                    }
                ],
            }
        ],
    }

    # Act
    report = run_rulepack(
        inputs_map={"default": csv_path},
        rulepack=rulepack,
        rp_path=tmp_path / "rulepack.yml",
        now_iso="2025-01-01T00:00:00+00:00",
    )

    # Assert: JSON evidence contains remediation links (raw URL preserved)
    evidence = report["resources"][0]["rules"][0]["evidence"]
    assert evidence["nullish"]["rows_by_column"]["primary_id"] == [1, 3]
    assert evidence["remediation"]["column"] == "external_url"
    assert evidence["remediation"]["label"] == "Open record"
    assert evidence["remediation"]["links"] == [
        {"row": 1, "url": "https://example.org/1"},
        {"row": 3, "url": "www.example.org/3"},
    ]

    # Assert: Markdown renders clickable link (adds https:// for www.*)
    md = write_markdown(report)
    assert "[Open record](https://example.org/1)" in md
    assert "[Open record](https://www.example.org/3)" in md


def test_no_remediation_block_when_not_configured(tmp_path):
    csv_path = tmp_path / "data.csv"
    csv_path.write_text("primary_id,external_url\n" ",https://example.org/1\n")

    rulepack = {
        "id": "no-remediation",
        "version": "0.0.0",
        "resources": [
            {
                "pattern": "data.csv",
                "rules": [
                    {
                        "id": "primary_id_required",
                        "type": "required",
                        "severity": "fail",
                        "columns": ["primary_id"],
                        # no remediation_link_column / label
                    }
                ],
            }
        ],
    }

    report = run_rulepack(
        inputs_map={"default": csv_path},
        rulepack=rulepack,
        rp_path=tmp_path / "rulepack.yml",
        now_iso="2025-01-01T00:00:00+00:00",
    )

    evidence = report["resources"][0]["rules"][0]["evidence"]
    assert "nullish" in evidence
    assert "remediation" not in evidence
