import tempfile
from pathlib import Path

import pandas as pd

# Import the RNA validator module so it registers itself with the API.
# (Your validate_csv() fails otherwise because no validators are registered.)
import fairy.core.validators.rna  # noqa: F401
from fairy.core.validation_api import validate_csv
from fairy.validation.checks import (
    column_enum,
    column_non_empty_trimmed,
    column_numeric_range,
    column_url,
    row_unique,
    schema_required,
    table_foreign_key,
)


def _count(res):
    return 0 if res is None else res.count


def _ids(res):
    return [] if res is None else [s.row for s in res.samples]


def test_schema_required_missing_and_present():
    df = pd.DataFrame({"a": [1], "b": [2]})
    res = schema_required(df, required=["a", "b"])
    assert res is None
    res2 = schema_required(df, required=["a", "b", "c"])
    assert res2 is not None
    assert res2.id == "schema.required"
    assert res2.level == "fail"
    assert res2.count == 1
    assert res2.samples[0].value == "c"


def test_row_unique_flags_duplicates_1_based_rows():
    df = pd.DataFrame({"id": [1, 1, 2, 3, 3, 3]})
    res = row_unique(df, column="id")
    assert res is not None
    assert res.id == "row.unique"
    assert res.count == 5  # all members of duplicate groups counted
    assert _ids(res)[:3] == [1, 2, 5]  # 1-based rows (indexes 0,1,4)


def test_table_foreign_key_misses_and_schema():
    from_df = pd.DataFrame({"artist_id": [10, 11, 12, None]})
    to_df = pd.DataFrame({"id": [11, 12, 13]})
    res = table_foreign_key(from_df, to_df, from_column="artist_id", to_column="id")
    # 10 not in {11,12,13}; None ignored
    assert res is not None and res.count == 1 and res.samples[0].value == 10
    # missing column surfaces as schema problem
    res2 = table_foreign_key(from_df, to_df, from_column="bogus", to_column="id")
    assert res2 is not None and res2.count == 1


def test_column_numeric_range_oob_and_non_numeric():
    df = pd.DataFrame({"x": [-1, "oops", 0, 5, 10]})
    res = column_numeric_range(df, column="x", min_value=0, max_value=9)
    assert res is not None
    # violations: -1 (oob), "oops" (non-numeric), 10 (oob) => 3
    assert res.count == 3
    rows = [s.row for s in res.samples]
    assert rows == [1, 2, 5]  # 1-based
    assert res.meta["non_numeric_count"] == 1


def test_column_url_schemes_and_syntax_only():
    df = pd.DataFrame({"u": ["http://ok", "https://ok", "ftp://nope", "not a url", None]})
    res = column_url(df, column="u", schemes=("http", "https"))
    assert res is not None
    # ftp and "not a url" are violations; None passes
    assert res.count == 2
    assert [s.row for s in res.samples] == [3, 4]


def test_column_url_accepts_www_without_scheme_by_normalizing():
    df = pd.DataFrame({"u": ["www.example.org/path", "www.example.org", None]})
    res = column_url(df, column="u", schemes=("http", "https"))
    # After normalization, www.* should be treated as https://www.*
    assert res is None


def test_column_url_trims_whitespace_before_validation():
    df = pd.DataFrame({"u": [" https://example.org/x ", "  http://example.org/y  ", None]})
    res = column_url(df, column="u", schemes=("http", "https"))
    assert res is None


def test_column_non_empty_trimmed_warns_on_blank_and_na():
    df = pd.DataFrame({"t": ["  ", "x", None, " y "]})
    res = column_non_empty_trimmed(df, column="t", level="warn")
    assert res is not None and res.level == "warn"
    assert res.count == 2
    assert [s.row for s in res.samples] == [1, 3]
    # detail shows NA vs length
    assert res.samples[0].detail.startswith("len")
    assert res.samples[1].detail == "NA"


def test_column_enum_case_insensitive():
    df = pd.DataFrame({"c": ["USD", "eur", "JPY", None]})
    res = column_enum(df, column="c", allowed=["USD", "EUR"], case_insensitive=True)
    # JPY is the only violation; None ignored
    assert res is not None and res.count == 1
    assert [s.row for s in res.samples] == [3]


def test_validate_csv_returns_findings_list():
    tmp = Path(tempfile.mkdtemp())
    csv = tmp / "metadata.csv"
    csv.write_text("sample_id,organism\nS1,Homo sapiens\n", encoding="utf-8")

    result = validate_csv(str(csv), kind="rna")
    assert hasattr(result, "warnings")
    assert isinstance(result.warnings, list)
    assert result.n_rows >= 1
    assert result.n_cols >= 2
