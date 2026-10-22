"""Clean bca-bebr-data.xlsx into tidy CSVs under data/.

Outputs
  data/buildings.csv   one row per building, numeric columns cleaned, with flags
  data/benchmarks.csv  2025 EUI quartile cut-offs per building type
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "bca-bebr-data.xlsx"
YEARS = [2022, 2023, 2024, 2025]

BENCH_NAME_MAP = {
    "Office Buildings": "Office",
    "Hotel Buildings": "Hotel",
    "Retail Buildings": "Retail",
    "Hospitals or Specialist Clinics": "Hospital or Specialist Clinic",
    "Nursing Homes": "Nursing Home",
    "Polyclinics or Private Clinics": "Polyclinic or Private Clinic",
    "Autonomous Universities": "Autonomous University",
    "Civic Buildings": "Civic Institution",
    "Community Institutions": "Community Institution",
    "Cultural Institutions": "Cultural Institution",
    "Other Educational Institutions": "Other Educational Institution",
    "Recreation Clubs": "Recreation Club",
    "Sports Centres": "Sports Centre",
}

# Plausible ranges; values outside are treated as unknown.
MIN_EUI = 5  # below this is a partial first-year / commissioning reading (lowest real 2025 EUI is ~8)
CHILLER_KWRT = (0.3, 2.0)
CHILLER_YEAR = (1960, 2026)
AUDIT_YEAR = (2000, 2026)
TOP_YEAR = (1950, 2025)


def num(s):
    return pd.to_numeric(s, errors="coerce")


def in_range(s, lo, hi):
    return s.where((s >= lo) & (s <= hi))


def clean_buildings():
    raw = pd.read_excel(SRC, sheet_name="Dataset")
    raw = raw[raw["Building Type"].notna()].copy()  # drops footer rows

    out = pd.DataFrame(index=raw.index)
    out["address"] = raw["Building Address"].str.strip()
    out["name"] = raw["Building Name"].str.strip().fillna(out["address"])  # one source row has no name
    out["postal"] = raw["Building Postal Code"].astype("Int64").astype(str).str.zfill(6)
    out["type"] = raw["Building Type"]

    # 'Combined' = shares an electricity meter with other buildings; no own EUI.
    combined = raw["2025 EUI (kWh/m²/yr)"].astype(str).eq("Combined")
    eui = pd.DataFrame({y: num(raw[f"{y} EUI (kWh/m²/yr)"]) for y in YEARS})
    no_data = eui.isna().all(axis=1) & ~combined
    out["reporting"] = np.select(
        [combined, no_data], ["combined", "no_data"], default="reported"
    )

    for y in YEARS:
        v = eui[y]
        out[f"eui_{y}"] = v.where(v >= MIN_EUI)  # zero, negative or implausibly low -> missing
        q = raw[f"{y} EUI Quartile"].where(raw[f"{y} EUI Quartile"].str.contains("Quartile", na=False))
        out[f"quartile_{y}"] = q.str[0].astype("float").astype("Int64")
    for y in YEARS[1:]:
        g = num(raw[f"{y} GUI (kWh/m²/yr)"])
        out[f"gui_{y}"] = g.where(g >= 0)

    out["gfa"] = num(raw["Total GFA of Building/ Development (m2)"])
    ac_area = num(raw["Total Air-Conditioned Floor Area (m2)"])
    out["ac_area"] = ac_area
    out["ac_inconsistent"] = ac_area > out["gfa"]
    out["ac_pct"] = (ac_area / out["gfa"]).where(~out["ac_inconsistent"])
    out["hotel_rooms"] = num(raw["Number of Hotel Rooms"])
    out["ac_system"] = raw["Type of AC System"].replace(
        {"Water Cooled Central Chilled Water": "Water Cooled Chilled Water Plant"}
    )
    out["year_built"] = in_range(raw["TOP/CSC Year"], *TOP_YEAR)
    out["chiller_year"] = in_range(raw["Year of Installation for Newest Chiller"], *CHILLER_YEAR)
    out["chiller_kwrt"] = in_range(raw["Chilled Water System Efficiency (kW/RT)"], *CHILLER_KWRT)
    out["airside_kwrt"] = in_range(raw["Air-side Efficiency (kW/RT)"], *CHILLER_KWRT)
    out["audit_year"] = in_range(raw["Year of Last Audit"], *AUDIT_YEAR)

    for c in [c for c in raw.columns if c.startswith("Percentage of GFA for")]:
        key = re.sub(r"Percentage of GFA for | Function", "", c)
        out[f"mix_{key}"] = num(raw[c])

    # Data-quality flags (shown to users as cautions, not deleted)
    flags = pd.Series("", index=out.index)
    def add(mask, text):
        nonlocal flags
        flags = flags.where(~mask, flags + text + "; ")
    e = out[[f"eui_{y}" for y in YEARS]]
    add(out["reporting"].eq("reported") & e.isna().any(axis=1), "missing/invalid EUI in some years")
    add(out["eui_2025"] > 1000, "EUI above 1,000 - verify")
    ratios = pd.concat([out[f"eui_{b}"] / out[f"eui_{a}"] for a, b in zip(YEARS, YEARS[1:])], axis=1)
    add(((ratios > 2) | (ratios < 0.5)).any(axis=1), "EUI changed by more than 2x between years (possible partial-year data)")
    add(out["ac_inconsistent"], "AC area exceeds GFA")
    add(out["gfa"] < 5000, "GFA below 5,000 m2")
    out["flags"] = flags.str.rstrip("; ")
    return out.reset_index(drop=True)


def clean_benchmarks():
    raw = pd.read_excel(SRC, sheet_name="Building Energy Benchmarks", header=None)
    rows = []
    for _, r in raw.iloc[3:16].iterrows():
        name = BENCH_NAME_MAP[str(r[1]).strip()]
        q1 = float(re.sub(r"[^\d.]", "", str(r[3])))
        q2 = float(str(r[4]).split("-")[1])
        q3 = float(str(r[5]).split("-")[1])
        rows.append({"type": name, "n_buildings": int(r[2]), "q1_max": q1, "q2_max": q2, "q3_max": q3})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    b = clean_buildings()
    bm = clean_benchmarks()
    (ROOT / "data").mkdir(exist_ok=True)
    b.to_csv(ROOT / "data" / "buildings.csv", index=False)
    bm.to_csv(ROOT / "data" / "benchmarks.csv", index=False)
    print(f"buildings: {len(b)}  benchmarks: {len(bm)}")
    print(b["reporting"].value_counts().to_dict())
    print("flagged:", (b["flags"] != "").sum())
