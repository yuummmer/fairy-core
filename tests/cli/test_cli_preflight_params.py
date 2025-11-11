import subprocess
import sys
from pathlib import Path

PY = sys.executable


def run_cli(rulepack, table_csv, params=None):
    cmd = [
        PY,
        "-m",
        "fairy.cli",
        "preflight",
        "--rulepack",
        str(rulepack),
        "--samples",
        "tests/fixtures/art-collections/artworks_pass.csv",  # adjust if needed
        "--files",
        "tests/fixtures/art-collections/artworks_pass.csv",  # adjust if needed
        "--out",
        "tests/golden/preflight.report.json",
    ]
    # If your preflight expects penguins TSVs, swap the inputs accordingly.
    if params:
        cmd += ["--param-file", str(params)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.returncode, res.stdout + res.stderr


def test_param_file_happy(tmp_path):
    # Just verifies the flag is accepted and the run succeeds
    params = tmp_path / "params.yml"
    params.write_text("min_year: 2007\n", encoding="utf-8")
    rulepack = Path("tests/fixtures/rulepacks/penguins.yml")  # or your GEO JSON rulepack path
    code, out = run_cli(rulepack, Path("tests/fixtures/penguins_small.csv"), params)
    assert code in (0, 1)  # 0 if submission_ready, 1 if not; either way CLI runs with params
    assert "--param-file" not in out  # placeholder assertion to ensure run completed
