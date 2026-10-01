"""One city's Open-Meteo timeout must not sink the hourly refresh for every city."""
import json
import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ml"))
import common as C  # noqa: E402
import forecast as F  # noqa: E402


def run(monkeypatch, tmp_path, bad_ids):
    (tmp_path / "forecasts.json").write_text(json.dumps({
        "cities": [{"id": c["id"], "old": True} for c in C.ALL_CITIES], "grid": ["old"]}))

    def payload(city, *a):
        if city["id"] in bad_ids:
            raise requests.ReadTimeout("read timed out")
        return {"id": city["id"], "old": False}

    monkeypatch.setattr(C, "WEB_PUBLIC", tmp_path)
    monkeypatch.setattr(F, "load_models", lambda: ({}, {}))
    monkeypatch.setattr(F, "city_payload", payload)
    monkeypatch.setattr(F, "fetch_grid", lambda: (_ for _ in ()).throw(requests.ConnectionError()))
    monkeypatch.setattr(F, "update_log", lambda rows, actuals: None)
    monkeypatch.setattr(F, "live_score", lambda log: {})
    F.main()
    return json.loads((tmp_path / "forecasts.json").read_text())


def test_one_city_failing_keeps_its_last_forecast(monkeypatch, tmp_path):
    bad = C.ALL_CITIES[3]["id"]
    out = run(monkeypatch, tmp_path, {bad})
    assert len(out["cities"]) == len(C.ALL_CITIES)
    assert [c["id"] for c in out["cities"] if c["old"]] == [bad]
    assert out["grid"] == ["old"]


def test_most_cities_failing_still_stops_the_run(monkeypatch, tmp_path):
    with pytest.raises(RuntimeError, match="Open-Meteo looks down"):
        run(monkeypatch, tmp_path, {c["id"] for c in C.ALL_CITIES})
