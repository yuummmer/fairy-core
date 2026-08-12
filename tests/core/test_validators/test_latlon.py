# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025 Jennifer Slotnick

import pandas as pd
from pathlib import Path

from fairy.core.validators.latlon import LatLonPlausibilityValidator

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "dwc_small.csv"


def test_latlon_zero_pair_only_warning():
    validator = LatLonPlausibilityValidator()
    res = validator.validate(
        str(FIXTURE_PATH),
        {"lat_column": "decimalLatitude", "lon_column": "decimalLongitude"},
    )
    assert len(res.warnings) == 1
    assert "Row 68" in res.warnings[0]
    assert "placeholder" in res.warnings[0].lower()


def test_latlon_swap_heuristic(tmp_path):
    swap_csv = tmp_path / "swap_test.csv"
    swap_csv.write_text("decimalLatitude,decimalLongitude\n95.0,10.0\n", encoding="utf-8")

    validator = LatLonPlausibilityValidator()
    res = validator.validate(
        str(swap_csv),
        {"lat_column": "decimalLatitude", "lon_column": "decimalLongitude", "warn_on_swapped": True},
    )
    assert len(res.warnings) == 1
    assert "swapped" in res.warnings[0].lower()
    assert "lat=95.0" in res.warnings[0]


def test_latlon_no_false_positive_on_single_zero(tmp_path):
    single_zero_csv = tmp_path / "single_zero.csv"
    single_zero_csv.write_text("decimalLatitude,decimalLongitude\n0,12.5\n15.0,0\n", encoding="utf-8")

    validator = LatLonPlausibilityValidator()
    res = validator.validate(
        str(single_zero_csv),
        {"lat_column": "decimalLatitude", "lon_column": "decimalLongitude"},
    )
    assert res.warnings == []
