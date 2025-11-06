# tests/test_rule_validators.py
import tempfile
from pathlib import Path

from fairy.core.validation_api import validate_csv


def test_validate_csv_returns_findings_list():
    # build a tiny CSV on the fly
    tmp = Path(tempfile.mkdtemp())
    csv = tmp / "metadata.csv"
    csv.write_text("sample_id,organism\nS1,Homo sapiens\n", encoding="utf-8")

    result = validate_csv(str(csv), kind="rna")
    # sanity: structure should match your ValidationResult model
    assert isinstance(result.warnings, list)
    assert result.n_rows >= 1
    assert result.n_cols >= 2
