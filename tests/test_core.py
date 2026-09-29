"""Checks for the two things every number on the site rests on.
Run: python -m pytest -q
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ml"))
import common as C  # noqa: E402


@pytest.mark.parametrize("pm, aqi, cat", [
    # 2024 EPA table: https://aqs.epa.gov/aqsweb/documents/codetables/aqi_breakpoints.html
    (0.0, 0, "Good"),
    (9.0, 50, "Good"),
    (9.1, 51, "Moderate"),
    (35.4, 100, "Moderate"),
    (35.5, 101, "Unhealthy for Sensitive Groups"),
    (55.5, 151, "Unhealthy"),
    (125.4, 200, "Unhealthy"),
    (125.5, 201, "Very Unhealthy"),
    (225.5, 301, "Hazardous"),
])
def test_aqi_matches_epa_2024_breakpoints(pm, aqi, cat):
    r = C.pm25_to_aqi(pm)
    assert (r["aqi"], r["category"]) == (aqi, cat)


def test_aqi_handles_missing_and_negative():
    assert C.pm25_to_aqi(None) is None
    assert C.pm25_to_aqi(float("nan")) is None
    assert C.pm25_to_aqi(-3)["aqi"] == 0


def _toy(city="manila", hours=100):
    t = pd.date_range("2025-01-01", periods=hours, freq="h")
    df = pd.DataFrame({"time": t, "city": city, "lat": 14.6, "lon": 121.0,
                       "pm2_5": np.arange(hours, dtype=float)})
    for col in C.BASE_COLS:
        if col not in df:
            df[col] = 1.0
    df["wind_direction_10m"] = 90.0
    return df


@pytest.mark.parametrize("h", C.HORIZONS)
def test_target_is_exactly_h_hours_ahead_and_lags_look_back(h):
    f = C.make_features(_toy(), horizon=h).set_index("time")
    row = f.iloc[60]
    # pm2_5 equals the hour index, so every shift is directly readable
    assert row["target"] == row["pm2_5"] + h
    assert row["pm2_5_lag1"] == row["pm2_5"] - 1
    assert row["pm2_5_lag24"] == row["pm2_5"] - 24
    # no feature may know the future: every lag is at or below the current value
    lags = [c for c in C.FEATURES if "lag" in c and c.startswith("pm2_5")]
    assert (f[lags].max(axis=1).dropna() <= f.loc[f[lags].max(axis=1).notna(), "pm2_5"]).all()


def test_lags_never_cross_cities():
    df = pd.concat([_toy("manila"), _toy("cebu").assign(pm2_5=1000.0)])
    f = C.make_features(df, horizon=1)
    m = f[f["city"] == "manila"]
    assert m["pm2_5_lag1"].max() < 1000  # no Cebu value leaked into Manila's history
