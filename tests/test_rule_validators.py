import tempfile
from pathlib import Path

# Import the RNA validator module so it registers itself with the API.
# (Your validate_csv() fails otherwise because no validators are registered.)
import fairy.core.validators.rna  # noqa: F401
from fairy.core.validation_api import validate_csv


def test_validate_csv_returns_findings_list():
    tmp = Path(tempfile.mkdtemp())
    csv = tmp / "metadata.csv"
    csv.write_text("sample_id,organism\nS1,Homo sapiens\n", encoding="utf-8")

    result = validate_csv(str(csv), kind="rna")
    assert hasattr(result, "warnings")
    assert isinstance(result.warnings, list)
    assert result.n_rows >= 1
    assert result.n_cols >= 2
