from pathlib import Path

from fairy.cli import cmd_preflight


class DummyArgs:
    def __init__(self, out):
        self.rulepack = Path("ignored.json")
        self.samples = Path("ignored.tsv")
        self.files = Path("ignored.tsv")
        self.out = out
        self.fairy_version = "0.0.0"
        self.param_file = None


def test_preflight_main_emits_files(tmp_path, monkeypatch):
    # minimal fake report structure expected by cmd_preflight (new v1 structure)
    fake = {
        "schema_version": "1.0.0",
        "generated_at": "2025-01-01T00:00:00Z",
        "dataset_id": "sha256:" + "0" * 64,
        "metadata": {
            "inputs": {
                "samples": {
                    "path": "/test/samples.tsv",
                    "sha256": "0" * 64,
                    "n_rows": 0,
                    "n_cols": 0,
                    "header": [],
                },
                "files": {
                    "path": "/test/files.tsv",
                    "sha256": "0" * 64,
                    "n_rows": 0,
                    "n_cols": 0,
                    "header": [],
                },
            },
            "rulepack": {"path": "/test/rulepack.json", "sha256": "0" * 64},
        },
        "summary": {"by_level": {"pass": 0, "warn": 0, "fail": 0}, "by_rule": {}},
        "results": [],
        "_legacy": {
            "attestation": {
                "rulepack_id": "demo",
                "rulepack_version": "0.0.1",
                "fairy_version": "0.0.0",
                "run_at_utc": "2025-01-01T00:00:00Z",
                "submission_ready": True,
                "fail_count": 0,
                "warn_count": 0,
            },
            "findings": [],
        },
    }

    def fake_run_rulepack(**kwargs):
        return fake

    monkeypatch.setattr("fairy.cli.cmd_preflight.run_rulepack", fake_run_rulepack)
    out_json = tmp_path / "report.json"
    rc = cmd_preflight.main(DummyArgs(out_json))
    assert rc == 0
    assert out_json.exists()
    assert out_json.with_suffix(".md").exists()
