from __future__ import annotations

import subprocess
from pathlib import Path


def run_cli(args: list[str]) -> subprocess.CompletedProcess:
    """Run the fairy CLI command and return the CompletedProcess."""
    return subprocess.run(args, capture_output=True, text=True)


def test_preflight_geo_success_creates_required_artifacts(tmp_path: Path):
    """Test that successful preflight creates required artifacts in output directory."""
    out_dir = tmp_path / "fairy-out"

    args = [
        "fairy",
        "preflight",
        "--rulepack",
        "tests/fixtures/rulepacks/geo_bulk_seq_min_v0_2_0.json",
        "--samples",
        "tests/fixtures/preflight/samples.tsv",
        "--files",
        "tests/fixtures/preflight/files.tsv",
        "--out-dir",
        str(out_dir),
        "geo",
    ]
    cp = run_cli(args)

    assert (
        out_dir.exists()
    ), f"Output directory should be created.\nSTDOUT:\n{cp.stdout}\nSTDERR:\n{cp.stderr}"

    # Verify all required artifacts exist
    expected_files = {
        "preflight_report.json": "JSON report file",
        "preflight_report.md": "Markdown report file",
        "manifest.json": "Manifest file",
        "artifacts/inputs_manifest.json": "Inputs manifest file",
    }

    missing_files = []
    for file_path, description in expected_files.items():
        full_path = out_dir / file_path
        if not full_path.exists():
            missing_files.append(f"{file_path} ({description})")

    assert not missing_files, (
        f"Expected files are missing from output directory:\n"
        f"{chr(10).join(f'  - {f}' for f in missing_files)}\n"
        f"STDOUT:\n{cp.stdout}\nSTDERR:\n{cp.stderr}"
    )


def test_preflight_geo_missing_files_path_hard_fails_no_out_dir(tmp_path: Path):
    """Test that missing --files path hard-fails and does not create output directory."""
    out_dir = tmp_path / "fairy-out"
    missing_files = tmp_path / "MISSING_files.tsv"  # does not exist

    args = [
        "fairy",
        "preflight",
        "--rulepack",
        "tests/fixtures/rulepacks/geo_bulk_seq_min_v0_2_0.json",
        "--samples",
        "tests/fixtures/preflight/samples.tsv",
        "--files",
        str(missing_files),
        "--out-dir",
        str(out_dir),
        "geo",
    ]
    cp = run_cli(args)

    assert (
        cp.returncode != 0
    ), f"Expected non-zero exit.\nSTDOUT:\n{cp.stdout}\nSTDERR:\n{cp.stderr}"
    assert (
        not out_dir.exists()
    ), f"Out dir should not be created on hard failure.\nSTDOUT:\n{cp.stdout}\nSTDERR:\n{cp.stderr}"
