import json
import subprocess


def _run(*args):
    return subprocess.run(args, text=True, capture_output=True)


def test_fk_pass(tmp_path):
    out = tmp_path / "out.json"
    r = _run(
        "fairy",
        "validate",
        "--rulepack",
        "tests/fixtures/art-collections/rulepack.yaml",
        "--inputs",
        "artworks=tests/fixtures/art-collections/artworks_pass.csv",
        "--inputs",
        "artists=tests/fixtures/art-collections/artists.csv",
        "--report-json",
        str(out),
    )
    assert r.returncode == 0
    data = json.loads(out.read_text())
    assert data["summary"]["fail"] == 0


def test_fk_fail(tmp_path):
    out = tmp_path / "out.json"
    r = _run(
        "fairy",
        "validate",
        "--rulepack",
        "tests/fixtures/art-collections/rulepack.yaml",
        "--inputs",
        "artworks=tests/fixtures/art-collections/artworks_fail_missing_artist.csv",
        "--inputs",
        "artists=tests/fixtures/art-collections/artists.csv",
        "--report-json",
        str(out),
    )
    assert r.returncode == 1
