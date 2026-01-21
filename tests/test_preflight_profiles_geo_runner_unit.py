from __future__ import annotations

import pytest

from fairy.core.services.preflight_profiles import _run_geo


def test_geo_runner_calls_validator_run_rulepack_with_expected_args(tmp_path, monkeypatch):
    # Arrange
    rulepack = tmp_path / "rulepack.json"
    samples = tmp_path / "samples.tsv"
    files = tmp_path / "files.tsv"

    # touch files so Paths look realistic (not strictly required)
    rulepack.write_text("{}", encoding="utf-8")
    samples.write_text("x\n", encoding="utf-8")
    files.write_text("y\n", encoding="utf-8")

    captured = {}

    def fake_run_rulepack(*, rulepack_path, samples_path, files_path, fairy_version, params):
        captured["rulepack_path"] = rulepack_path
        captured["samples_path"] = samples_path
        captured["files_path"] = files_path
        captured["fairy_version"] = fairy_version
        captured["params"] = params
        return {"ok": True}

    # IMPORTANT: _run_geo imports validator.run_rulepack inside the function.
    # Monkeypatch the validator module function so the import picks up the patched version.
    monkeypatch.setattr("fairy.core.services.validator.run_rulepack", fake_run_rulepack)

    params = {"alpha": 1, "beta": "two"}

    # Act
    out = _run_geo(
        rulepack=rulepack,
        inputs={"samples": samples, "files": files},
        fairy_version="9.9.9",
        params=params,
    )

    # Assert
    assert out == {"ok": True}
    assert captured["rulepack_path"] == rulepack
    assert captured["samples_path"] == samples
    assert captured["files_path"] == files
    assert captured["fairy_version"] == "9.9.9"
    assert captured["params"] == params


def test_geo_runner_requires_samples_and_files_paths(tmp_path):
    rulepack = tmp_path / "rulepack.json"
    rulepack.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError):
        _run_geo(
            rulepack=rulepack,
            inputs={"samples": tmp_path / "samples.tsv"},  # missing files
            fairy_version="0.1.0",
            params={},
        )
