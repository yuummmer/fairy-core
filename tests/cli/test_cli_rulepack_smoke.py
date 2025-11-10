import subprocess
import sys
from pathlib import Path


def test_cli_smoke_rulepack(tmp_path: Path):
    rp = tmp_path / "rp.yaml"
    rp.write_text(
        "meta:\n  name: smoke\n  version: '0.0.1'\nrules:\n  - id: ping\n    type: always_pass\n",
        encoding="utf-8",
    )
    cmd = [
        sys.executable,
        "-m",
        "fairy.cli",
        "run",
        "--mode",
        "rulepack",
        "--rulepack",
        str(rp),
        "--inputs",
        "table=./x.csv",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert "Loaded rulepack 'smoke' v0.0.1 with 1 rule(s)." in proc.stdout
