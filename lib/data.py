"""Data loading and shared helpers."""
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

DATA = Path(__file__).resolve().parent.parent / "data"
YEARS = [2022, 2023, 2024, 2025]
LATEST = 2025
# Year BCA published this edition of the report. Set it here (e.g. 2025); leave None to omit.
REPORT_PUBLISHED = 2026
DISCLAIMER = (
    "Source: BCA Building Energy Benchmarking Report"
    + (f" (published {REPORT_PUBLISHED})" if REPORT_PUBLISHED else "")
    + f", public data covering {YEARS[0]}–{YEARS[-1]}. "
    "This dashboard is for information only and is not official BCA advice."
)


def setup(title: str = "BEBR Dashboard"):
    st.set_page_config(page_title=title, page_icon="🏢", layout="wide")


def footer():
    st.divider()
    st.caption(DISCLAIMER)


def _stamp() -> tuple:
    """Changes whenever a data file is rewritten, so cached loads refresh."""
    return tuple((DATA / f).stat().st_mtime for f in ("buildings.csv", "benchmarks.csv", "postal_coords.csv"))


@st.cache_data
def _load_buildings(stamp: tuple) -> pd.DataFrame:
    df = pd.read_csv(DATA / "buildings.csv", dtype={"postal": str})
    coords = pd.read_csv(DATA / "postal_coords.csv", dtype={"postal": str})
    df = df.merge(coords, on="postal", how="left")
    df["id"] = df.index
    addr = df["address"].fillna("")
    same = [a.casefold().startswith(n.casefold()) or n.casefold().startswith(a.casefold()) for n, a in zip(df["name"], addr)]
    df["label"] = df["name"].where(same, df["name"] + " — " + addr)  # skip a repeated address
    df["flags"] = df["flags"].fillna("")
    df["building_age"] = (LATEST - df["year_built"]).clip(lower=0)
    df["chiller_age"] = (LATEST - df["chiller_year"]).clip(lower=0)
    df["years_since_audit"] = (LATEST - df["audit_year"]).clip(lower=0)
    return df


@st.cache_data
def _load_benchmarks(stamp: tuple) -> pd.DataFrame:
    return pd.read_csv(DATA / "benchmarks.csv").set_index("type")


def load_buildings() -> pd.DataFrame:
    return _load_buildings(_stamp())


def load_benchmarks() -> pd.DataFrame:
    return _load_benchmarks(_stamp())


def official_quartile(eui: float, cut: pd.Series):
    """Quartile implied by BCA's published cut-offs (1 = best)."""
    if pd.isna(eui):
        return None
    if eui <= cut.q1_max:
        return 1
    if eui <= cut.q2_max:
        return 2
    if eui <= cut.q3_max:
        return 3
    return 4


def reported(df: pd.DataFrame, year: int = LATEST) -> pd.DataFrame:
    return df[(df["reporting"] == "reported") & df[f"eui_{year}"].notna()]


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def building_options(df: pd.DataFrame) -> list[int]:
    """Building ids ordered A-Z by name (then address), for the search dropdowns."""
    order = df.assign(_k=df["name"].str.casefold()).sort_values(["_k", "address"])
    return [int(i) for i in order["id"]]
