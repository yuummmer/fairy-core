import subprocess
from pathlib import Path

import pytest

try:
    from freezegun import freeze_time
except ImportError:
    freeze_time = None  # freezegun not installed

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _find_rulepack() -> Path:
    # pick the first JSON rulepack under GEO-SEQ-BULK
    candidates = list(
        (PROJECT_ROOT / "src" / "fairy" / "rulepacks" / "GEO-SEQ-BULK").rglob("*.json")
    )
    if not candidates:
        pytest.skip("No rulepack JSON found under src/fairy/rulepacks/GEO-SEQ-BULK")
    return candidates[0]


@pytest.fixture(scope="session")
def rulepack_path() -> Path:
    return _find_rulepack()


@pytest.fixture(scope="session")
def samples_path() -> Path:
    # default demo location you created earlier
    p = PROJECT_ROOT / "tests" / "fixtures" / "preflight" / "samples.tsv"
    if not p.exists():
        pytest.skip("tests/fixtures/preflight/samples.tsv not found")
    return p


@pytest.fixture(scope="session")
def files_path() -> Path:
    p = PROJECT_ROOT / "tests" / "fixtures" / "preflight" / "files.tsv"
    if not p.exists():
        pytest.skip("tests/fixtures/preflight/files.tsv not found")
    return p


@pytest.fixture
def run_cli():
    """Run the argparse CLI (module = fairy.cli.run). Returns (code, stdout, stderr)."""

    def _run(args, cwd: Path = PROJECT_ROOT):
        proc = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
        return proc.returncode, proc.stdout, proc.stderr

    return _run


@pytest.fixture
def freeze_2025():
    """Freeze time for deterministic timestamps in outputs."""
    if freeze_time is None:
        pytest.skip("freezegun is not installed")
    with freeze_time("2025-01-01T12:00:00Z"):
        yield
