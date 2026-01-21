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
        self.profile = None


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

    def fake_run_profile(
        profile_id: str, *, rulepack: Path, inputs: dict, fairy_version: str, params=None
    ):
        return fake

    monkeypatch.setattr("fairy.cli.cmd_preflight.run_profile", fake_run_profile)
    out_json = tmp_path / "report.json"
    rc = cmd_preflight.main(DummyArgs(out_json))
    assert rc == 0
    assert out_json.exists()
    assert out_json.with_suffix(".md").exists()


def test_preflight_geo_does_not_emit_legacy_guidance(tmp_path, monkeypatch, capsys):
    out_json = tmp_path / "report.json"

    fake_report = {
        "dataset_id": "DS123",
        "generated_at": "2025-11-11T12:00:00Z",
        "engine": {"fairy_core_version": "0.1.0"},
        "metadata": {"rulepack": {"id": "RP", "version": "1.0.0"}, "inputs": {}},
        "summary": {"by_level": {"fail": 0, "warn": 0}},
        "results": [],
        "_legacy": {"attestation": {"fairy_version": "0.1.0"}},
    }

    def fake_run_profile(profile_id: str, *, rulepack, inputs, fairy_version, params=None):
        assert profile_id == "geo"
        return fake_report

    def fake_sha256_file(path: Path, newline_stable: bool = True) -> str:
        return "deadbeef"

    def fake_emit_md(md_path: Path, report: dict, resolved_codes, prior_codes):
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text("# md", encoding="utf-8")

    monkeypatch.setattr("fairy.cli.cmd_preflight.run_profile", fake_run_profile)
    monkeypatch.setattr("fairy.cli.cmd_preflight.sha256_file", fake_sha256_file)
    monkeypatch.setattr("fairy.cli.cmd_preflight.emit_preflight_markdown", fake_emit_md)

    args = DummyArgs(out_json)
    args.profile = "geo"  # NEW: explicit geo path
    rc = cmd_preflight.main(args)
    assert rc == 0

    out = capsys.readouterr().out
    assert "This invocation uses the GEO preflight profile" not in out


def test_preflight_legacy_emits_guidance(tmp_path, monkeypatch, capsys):
    out_json = tmp_path / "report.json"

    fake_report = {
        "dataset_id": "DS123",
        "generated_at": "2025-11-11T12:00:00Z",
        "engine": {"fairy_core_version": "0.1.0"},
        "metadata": {"rulepack": {"id": "RP", "version": "1.0.0"}, "inputs": {}},
        "summary": {"by_level": {"fail": 0, "warn": 0}},
        "results": [],
        "_legacy": {"attestation": {"fairy_version": "0.1.0"}},
    }

    def fake_run_profile(profile_id: str, *, rulepack, inputs, fairy_version, params=None):
        assert profile_id == "geo"
        return fake_report

    def fake_sha256_file(path: Path, newline_stable: bool = True) -> str:
        return "deadbeef"

    def fake_emit_md(md_path: Path, report: dict, resolved_codes, prior_codes):
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text("# md", encoding="utf-8")

    monkeypatch.setattr("fairy.cli.cmd_preflight.run_profile", fake_run_profile)
    monkeypatch.setattr("fairy.cli.cmd_preflight.sha256_file", fake_sha256_file)
    monkeypatch.setattr("fairy.cli.cmd_preflight.emit_preflight_markdown", fake_emit_md)

    args = DummyArgs(out_json)
    args.profile = None  # legacy form
    rc = cmd_preflight.main(args)
    assert rc == 0

    out = capsys.readouterr().out
    assert "This invocation uses the GEO preflight profile" in out
    assert "Prefer: fairy preflight geo" in out
