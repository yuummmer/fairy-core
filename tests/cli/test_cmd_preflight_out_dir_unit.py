from __future__ import annotations

import json
from pathlib import Path

from fairy.cli import cmd_preflight


class DummyArgs:
    def __init__(self, out_dir: Path):
        self.rulepack = Path("fake_rulepack.json")
        self.samples = Path("samples.tsv")
        self.files = Path("files.tsv")
        self.out_dir = out_dir
        self.fairy_version = "0.1.0"
        self.param_file = None


def test_preflight_main_emits_out_dir_contract(tmp_path, monkeypatch):
    out_dir = tmp_path / "out"

    fake_report = {
        "dataset_id": "DS123",
        "generated_at": "2025-11-11T12:00:00Z",
        "engine": {"fairy_core_version": "0.1.0"},
        "metadata": {
            "rulepack": {"id": "RP", "version": "1.0.0"},
            "inputs": {
                "samples": {"path": "samples.tsv", "sha256": "aaa"},
                "files": {"path": "files.tsv", "sha256": "bbb"},
            },
        },
        "summary": {"by_level": {"fail": 0, "warn": 0}},
        "results": [],
        "_legacy": {"attestation": {"fairy_version": "0.1.0"}},
    }

    def fake_run_profile(
        profile_id: str, *, rulepack: Path, inputs: dict, fairy_version: str, params=None
    ):
        assert profile_id == "geo"  # optional
        assert "samples" in inputs and "files" in inputs
        return fake_report

    def fake_sha256_file(path: Path, newline_stable: bool = True) -> str:
        return "deadbeef"

    def fake_emit_md(md_path: Path, report: dict, resolved_codes, prior_codes):
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text("# md", encoding="utf-8")

    monkeypatch.setattr("fairy.cli.cmd_preflight.run_profile", fake_run_profile)
    monkeypatch.setattr("fairy.cli.cmd_preflight.sha256_file", fake_sha256_file)
    monkeypatch.setattr("fairy.cli.cmd_preflight.emit_preflight_markdown", fake_emit_md)

    rc = cmd_preflight.main(DummyArgs(out_dir))
    assert rc == 0

    rep = out_dir / "preflight_report.json"
    md = out_dir / "preflight_report.md"
    manifest = out_dir / "manifest.json"
    inputs_manifest = out_dir / "artifacts" / "inputs_manifest.json"

    assert rep.exists()
    assert md.exists()
    assert manifest.exists()
    assert inputs_manifest.exists()

    man = json.loads(manifest.read_text(encoding="utf-8"))
    assert man["source_report"] == "preflight_report.json"
