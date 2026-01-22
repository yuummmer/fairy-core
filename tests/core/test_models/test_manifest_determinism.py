from ...helpers import normalize_json


def test_preflight_output_is_deterministic(
    run_cli, rulepack_path, samples_path, files_path, freeze_2025, tmp_path
):
    out1 = tmp_path / "out1"
    out1.mkdir()
    out2 = tmp_path / "out2"
    out2.mkdir()

    rep1 = out1 / "report.json"
    rep2 = out2 / "report.json"

    run_cli(
        [
            "python",
            "-m",
            "fairy.cli.run",
            "preflight",
            "--rulepack",
            str(rulepack_path),
            "--samples",
            str(samples_path),
            "--files",
            str(files_path),
            "--out",
            str(rep1),
        ]
    )
    run_cli(
        [
            "python",
            "-m",
            "fairy.cli.run",
            "preflight",
            "--rulepack",
            str(rulepack_path),
            "--samples",
            str(samples_path),
            "--files",
            str(files_path),
            "--out",
            str(rep2),
        ]
    )

    assert rep1.exists() and rep2.exists(), "preflight outputs missing"

    got1 = normalize_json(rep1)
    got2 = normalize_json(rep2)
    assert (
        got1 == got2
    ), "preflight outputs should be identical for identical inputs (with time frozen)"
