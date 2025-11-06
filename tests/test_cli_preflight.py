from pathlib import Path

from .helpers import normalize_json


def test_preflight_generates_expected_report(
    run_cli, rulepack_path, samples_path, files_path, tmp_path
):
    out_json = tmp_path / "report.json"

    # Use your argparse entrypoint module (no __main__ needed)
    code, out, err = run_cli(
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
            str(out_json),
        ]
    )

    # Your CLI exits 1 when submission_ready == False; that's OK for this test.
    # Assert the artifact exists instead:
    assert out_json.exists(), f"report.json not created.\nSTDOUT:\n{out}\nSTDERR:\n{err}"

    got = normalize_json(out_json)
    golden = Path(__file__).parents[0] / "golden" / "preflight.report.json"
    assert golden.exists(), "Missing golden: tests/golden/preflight.report.json"
    want = normalize_json(golden)

    assert got == want, "preflight report differs from golden (ignoring volatile fields)"
