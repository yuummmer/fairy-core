from pathlib import Path

from fairy.cli.output_md import emit_markdown, emit_preflight_markdown


def test_emit_markdown_creates_file(tmp_path: Path):
    md = tmp_path / "report.md"
    payload = {
        "run_at": "2025-01-01T00:00:00Z",
        "dataset_id": {"filename": "x.csv", "sha256": "0" * 64},
        "summary": {"n_rows": 1, "n_cols": 1, "fields_validated": ["a"]},
        "warnings": [],
    }
    emit_markdown(md, payload)
    assert md.exists()
    assert "FAIRy Validation Report" in md.read_text()


def test_emit_preflight_markdown_creates_file(tmp_path: Path):
    md = tmp_path / "preflight.md"
    att = {
        "rulepack_id": "demo",
        "rulepack_version": "0.0.1",
        "fairy_version": "0.0.0",
        "run_at_utc": "2025-01-01T00:00:00Z",
        "submission_ready": True,
        "fail_count": 0,
        "warn_count": 0,
        "inputs": {"samples": {}, "files": {}},
    }
    report = {"findings": []}
    emit_preflight_markdown(md, att, report, resolved_codes=[], prior_codes=None)
    assert md.exists()
    txt = md.read_text()
    assert "FAIRy Preflight Report" in txt
    assert "submission_ready" in txt
