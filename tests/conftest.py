import subprocess
import textwrap
from pathlib import Path

import pytest
from freezegun import freeze_time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLI = ["python", "-m", "fairy"]


@pytest.fixture
def tmp_pkg(tmp_path: Path):
    """Create a minimal fake FAIRy package: profile, data, and rulepack."""
    pkg = tmp_path / "sample_pkg"
    (pkg / "data").mkdir(parents=True)
    # minimal CSV/TSV that your validators expect
    (pkg / "data" / "samples.csv").write_text("sample_id,organism\nS1,Homo sapiens\n")

    # example rulepack/profile; tweak to match your schema keys
    (pkg / "profile.yaml").write_text(
        textwrap.dedent(
            """
        name: ENA_draft
        version: 0.1.0
        rules:
          - id: GEO.META.REQUIRED
            field: organism
            type: required
          - id: GEO.FILENAME.CHARS
            field: samples.csv
            type: filename_allowed_chars
    """
        ).strip()
    )

    return pkg


@pytest.fixture
def run_cli():
    """Run the CLI in a subprocess to stay framework-agnostic (Click/Typer/Argparse)."""

    def _run(args, cwd: Path = PROJECT_ROOT):
        result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr

    return _run


@pytest.fixture
def freeze_2025():
    """Freeze time for deterministic timestamps in outputs."""
    with freeze_time("2025-01-01T12:00:00Z"):
        yield
