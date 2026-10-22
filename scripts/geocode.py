"""Geocode building postal codes via the OneMap search API (no token needed).

Reads data/buildings.csv, writes data/postal_coords.csv (postal, lat, lon).
Existing results are kept, so it is safe to re-run.
"""
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
URL = "https://www.onemap.gov.sg/api/common/elastic/search"
OUT = ROOT / "data" / "postal_coords.csv"


def lookup(term):
    """Return (lat, lon), None if not found, or raise RuntimeError if still rate-limited."""
    for attempt in range(6):
        try:
            r = requests.get(
                URL,
                params={"searchVal": term, "returnGeom": "Y", "getAddrDetails": "N", "pageNum": 1},
                timeout=20,
            )
            if r.status_code == 429:
                time.sleep(30 * (attempt + 1))
                continue
            r.raise_for_status()
            res = r.json().get("results", [])
            return (float(res[0]["LATITUDE"]), float(res[0]["LONGITUDE"])) if res else None
        except requests.RequestException:
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("OneMap kept failing; re-run later to resume")


if __name__ == "__main__":
    b = pd.read_csv(ROOT / "data" / "buildings.csv", dtype={"postal": str})
    rows = pd.read_csv(OUT, dtype={"postal": str}).to_dict("records") if OUT.exists() else []
    seen = {r["postal"] for r in rows}  # includes not-found, so they aren't retried
    todo = [p for p in b["postal"].unique() if p not in seen]
    try:
        for i, p in enumerate(todo, 1):
            hit = lookup(p)
            rows.append({"postal": p, "lat": hit[0] if hit else None, "lon": hit[1] if hit else None})
            if i % 50 == 0:
                pd.DataFrame(rows).to_csv(OUT, index=False)
                print(f"{i}/{len(todo)}", flush=True)
            time.sleep(1.2)
    finally:
        pd.DataFrame(rows).to_csv(OUT, index=False)
    res = pd.DataFrame(rows)
    print("geocoded:", res["lat"].notna().sum(), "not found:", res["lat"].isna().sum())
