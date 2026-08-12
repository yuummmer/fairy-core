# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025 Jennifer Slotnick

import pandas as pd

from ..validation_api import Meta, register


class LatLonPlausibilityValidator:
    name = "latlon_plausibility"
    version = "0.1.0"

    def validate(self, path: str, config: dict = None) -> Meta:
        if config is None:
            config = {}

        df = pd.read_csv(path)

        lat_col = config.get("lat_column")
        lon_col = config.get("lon_column")
        if not lat_col or not lon_col:
            return Meta(warnings=["lat_column and lon_column are required"], n_rows=int(df.shape[0]))

        if lat_col not in df.columns or lon_col not in df.columns:
            return Meta(warnings=[f"Columns {lat_col} or {lon_col} not found"], n_rows=int(df.shape[0]))

        eps = float(config.get("epsilon", 0.0))
        warn_zero = config.get("warn_on_zero_pair", True)
        warn_swap = config.get("warn_on_swapped", True)

        warnings = []
        for idx, row in df.iterrows():
            lat = pd.to_numeric(row[lat_col], errors='coerce')
            lon = pd.to_numeric(row[lon_col], errors='coerce')

            if pd.isna(lat) or pd.isna(lon):
                continue

            if warn_zero and abs(lat) <= eps and abs(lon) <= eps:
                warnings.append(f"Row {idx+1}: Potential (0,0) placeholder coordinates.")

            if warn_swap and abs(lat) > 90 and abs(lon) <= 90:
                warnings.append(f"Row {idx+1}: Likely swapped coordinates (lat={lat}, lon={lon}).")

        return Meta(warnings=warnings, n_rows=int(df.shape[0]))


register("latlon_plausibility", LatLonPlausibilityValidator())
