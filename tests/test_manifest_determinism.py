import hashlib
from pathlib import Path


def sha256(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_manifest_is_stable(tmp_pkg, run_cli, freeze_2025, tmp_path):
    out1 = tmp_path / "out1"
    out1.mkdir()
    out2 = tmp_path / "out2"
    out2.mkdir()

    run_cli(
        ["python", "-m", "fairy", "preflight", str(tmp_pkg), "--out", str(out1), "--format", "json"]
    )
    run_cli(
        ["python", "-m", "fairy", "preflight", str(tmp_pkg), "--out", str(out2), "--format", "json"]
    )

    m1 = (out1 / "manifest.json").read_text()
    m2 = (out2 / "manifest.json").read_text()
    assert m1 == m2, "manifest.json should be identical for identical inputs when time is frozen"
