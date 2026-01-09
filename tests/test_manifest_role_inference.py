import pytest

from fairy.core.services.manifest import infer_role


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("manifest.json", "metadata"),
        ("samples.tsv", "metadata"),
        ("files.tsv", "metadata"),
        ("geo_bulk_seq_report.json", "report"),
        ("geo_bulk_seq_report.md", "report"),
        ("run.log", "log"),
        ("data.csv", "data"),
        ("weird.bin", "other"),
    ],
)
def test_infer_role(path: str, expected: str) -> None:
    assert infer_role(path) == expected
