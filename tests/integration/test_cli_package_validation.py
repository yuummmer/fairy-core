import json
import subprocess
import sys
from pathlib import Path


def _run(*args):
    return subprocess.run(
        [sys.executable, "-m", "fairy.cli.validate", *args],
        text=True,
        capture_output=True,
    )


def _write_package_rulepack(path: Path) -> None:
    path.write_text(
        """
id: test-package-cli
version: 0.1.0
package:
  rules:
    - id: readme_present
      type: files_present
      severity: fail
      pattern: README*
      min_count: 1
""".lstrip(),
        encoding="utf-8",
    )


def test_package_directory_positional_passes(tmp_path: Path):
    package_dir = tmp_path / "submission"
    package_dir.mkdir()
    (package_dir / "README.md").write_text("hello", encoding="utf-8")

    rulepack = tmp_path / "rulepack.yaml"
    _write_package_rulepack(rulepack)

    out = tmp_path / "report.json"

    r = _run(
        str(package_dir),
        "--rulepack",
        str(rulepack),
        "--report-json",
        str(out),
    )

    assert r.returncode == 0, r.stderr

    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["summary"]["pass"] == 1
    assert data["summary"]["fail"] == 0

    package_resource = data["resources"][0]
    assert package_resource["name"] == "package"
    assert package_resource["path"] == str(package_dir.resolve())
    assert package_resource["rules"][0]["status"] == "PASS"


def test_package_rulepack_without_package_subject_exits_2(tmp_path: Path):
    rulepack = tmp_path / "rulepack.yaml"
    _write_package_rulepack(rulepack)

    r = _run(
        "--rulepack",
        str(rulepack),
    )

    assert r.returncode == 2
    assert "requires a package directory" in r.stderr


def test_package_root_flag_passes(tmp_path: Path):
    package_dir = tmp_path / "submission"
    package_dir.mkdir()
    (package_dir / "README.md").write_text("hello", encoding="utf-8")

    rulepack = tmp_path / "rulepack.yaml"
    _write_package_rulepack(rulepack)

    r = _run(
        "--rulepack",
        str(rulepack),
        "--package-root",
        str(package_dir),
    )

    assert r.returncode == 0, r.stderr


def test_package_root_rejected_for_non_package_rulepack(tmp_path: Path):
    package_dir = tmp_path / "submission"
    package_dir.mkdir()

    csv_path = tmp_path / "data.csv"
    csv_path.write_text("name\nalice\n", encoding="utf-8")

    rulepack = tmp_path / "rulepack.yaml"
    rulepack.write_text(
        """
id: table-only
version: 0.1.0
rules: []
""".lstrip(),
        encoding="utf-8",
    )

    r = _run(
        str(csv_path),
        "--rulepack",
        str(rulepack),
        "--package-root",
        str(package_dir),
    )

    assert r.returncode == 2
    assert "--package-root can only be used" in r.stderr


def test_conflicting_package_directories_exit_2(tmp_path: Path):
    positional_dir = tmp_path / "submission-a"
    positional_dir.mkdir()

    explicit_dir = tmp_path / "submission-b"
    explicit_dir.mkdir()

    rulepack = tmp_path / "rulepack.yaml"
    _write_package_rulepack(rulepack)

    r = _run(
        str(positional_dir),
        "--rulepack",
        str(rulepack),
        "--package-root",
        str(explicit_dir),
    )

    assert r.returncode == 2
    assert "different directories" in r.stderr