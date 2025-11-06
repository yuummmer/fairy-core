from pathlib import Path

from .helpers import normalize_json


def test_preflight_generates_expected_report(tmp_pkg, run_cli, freeze_2025, tmp_path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    # Adjust arguments to your CLI; example:
    # fairy preflight <pkg> --out <out_dir> --format json
    code, out, err = run_cli(
        [
            "python",
            "-m",
            "fairy",
            "preflight",
            str(tmp_pkg),
            "--out",
            str(out_dir),
            "--format",
            "json",
        ]
    )

    assert code == 0, f"CLI failed:\nSTDOUT:\n{out}\nSTDERR:\n{err}"

    report = out_dir / "report.json"
    changelog = out_dir / "changelog.json"
    assert report.exists(), "report.json not created"
    assert changelog.exists(), "changelog.json not created"

    # compare normalized outputs to goldens
    golden_dir = Path(__file__).parent / "golden"
    got = normalize_json(report)
    want = normalize_json(golden_dir / "report.preflight.json")

    assert got == want, "report.json does not match golden (ignoring volatile fields)"

    got_ch = normalize_json(changelog)
    want_ch = normalize_json(golden_dir / "changelog.json")
    assert got_ch == want_ch, "changelog.json does not match golden"
