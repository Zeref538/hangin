"""
Hangin: how well does CAMS (our training data) match real ground sensors?

Pulls hourly PM2.5 from OpenAQ low-cost sensors within 25 km of Manila for the
walk-forward test year, takes the median across sensors each hour, and compares
it with Open-Meteo's CAMS values for Manila over the same hours.

Needs OPENAQ_API_KEY in the environment (free: explore.openaq.org).
Caches data/openaq_manila.parquet. Writes data/ground_truth.json.
Run: python ml/ground_truth.py
"""
import json
import os
import time

import numpy as np
import pandas as pd
import requests

import common as C

API = "https://api.openaq.org/v3"
CACHE = C.DATA / "openaq_manila.parquet"
PARTS = C.DATA / "openaq_parts"  # one file per sensor, so a crash keeps finished work
MANILA = next(c for c in C.CITIES if c["id"] == "manila")


def get(path, **params):
    for attempt in range(5):
        r = requests.get(f"{API}{path}", params=params, timeout=60,
                         headers={"X-API-Key": os.environ["OPENAQ_API_KEY"]})
        if r.status_code == 200:
            return r.json()
        # 429 = free tier's 60 requests/minute; 408/5xx = their server timed out
        if r.status_code in (408, 429) or r.status_code >= 500:
            time.sleep(15 * (attempt + 1))
            continue
        r.raise_for_status()
    raise RuntimeError(f"OpenAQ kept failing on {path}")


def fetch(start, end):
    locs = get("/locations", coordinates=f"{MANILA['lat']},{MANILA['lon']}",
               radius=25000, parameters_id=2, limit=100)["results"]
    frames = []
    for loc in locs:
        if loc.get("isMobile") or "indoor" in loc["name"].lower():
            continue  # indoor air isn't city air
        for s in loc["sensors"]:
            if s["parameter"]["name"] != "pm25":
                continue
            part = PARTS / f"{s['id']}_{start}_{end}.parquet"  # keyed by range: one sensor, many windows
            if part.exists():
                frames.append(pd.read_parquet(part))
                continue
            rows = []
            # 60-day chunks: a whole year in one request times out on busy sensors
            edges = pd.date_range(start, end, freq="60D").append(pd.DatetimeIndex([end]))
            try:
                for lo, hi in zip(edges[:-1], edges[1:]):
                    page = 1
                    while True:
                        res = get(f"/sensors/{s['id']}/hours", datetime_from=f"{lo:%Y-%m-%d}",
                                  datetime_to=f"{hi:%Y-%m-%d}", limit=1000, page=page)["results"]
                        rows += [(r["period"]["datetimeFrom"]["utc"], r["value"]) for r in res]
                        if len(res) < 1000:
                            break
                        page += 1
            except RuntimeError as e:
                print(f"  skipping sensor {s['id']}: {e}")
                continue
            print(f"  {loc['name'][:35]:35} {len(rows)} hours")
            df = pd.DataFrame(rows, columns=["utc", "pm2_5"]).assign(sensor=s["id"])
            PARTS.mkdir(exist_ok=True)
            df.to_parquet(part)  # saved even when empty, so a rerun skips it
            if rows:
                frames.append(df)
    df = pd.concat(frames)
    df.to_parquet(CACHE)
    return df


def main():
    wf = json.load(open(C.DATA / "walkforward.json"))
    start, end = wf["test_period"].split("..")
    raw = fetch(start, end)  # per-sensor parts make re-runs fast
    raw = raw[(raw["pm2_5"] >= 0) & (raw["pm2_5"] < 500)]
    # UTC -> Manila local (naive), to line up with Open-Meteo's Asia/Manila times
    raw["time"] = pd.to_datetime(raw["utc"]).dt.tz_convert("Asia/Manila").dt.tz_localize(None)
    per_hour = raw.groupby("time").agg(ground=("pm2_5", "median"), n_sensors=("sensor", "nunique"))
    ground = per_hour[per_hour["n_sensors"] >= 3]["ground"]

    cams = pd.read_parquet(C.DATA / "unseen.parquet")
    cams = cams[cams["city"] == "manila"].set_index("time")["pm2_5"]
    both = pd.concat({"ground": ground, "cams": cams}, axis=1).dropna()

    g, c = both["ground"], both["cams"]
    naive24 = g.shift(24, freq="h").reindex(g.index)  # yesterday's sensor value, same hour
    ok = naive24.notna()
    out = {
        "period": f"{both.index.min():%Y-%m-%d}..{both.index.max():%Y-%m-%d}",
        "hours": len(both),
        "sensors": int(raw["sensor"].nunique()),
        "ground_mean": round(float(g.mean()), 2), "cams_mean": round(float(c.mean()), 2),
        "correlation_hourly": round(float(g.corr(c)), 3),
        "correlation_daily": round(float(g.resample("D").mean().corr(c.resample("D").mean())), 3),
        "cams_mae_vs_ground": round(float((c - g).abs().mean()), 2),
        "naive24_mae_vs_ground": round(float((naive24[ok] - g[ok]).abs().mean()), 2),
    }
    for k, v in out.items():
        print(f"  {k}: {v}")
    json.dump(out, open(C.DATA / "ground_truth.json", "w"), indent=1)


if __name__ == "__main__":
    main()
