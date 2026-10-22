import pandas as pd
import streamlit as st

from lib.data import LATEST, building_options, footer, load_benchmarks, load_buildings, reported

df = load_buildings()
bm = load_benchmarks()
rep = reported(df)

st.title("🏢 BEBR Dashboard")
st.markdown(
    "**Building Energy Benchmarking Report** — see how Singapore's larger buildings "
    "(5,000 m² GFA and above) use energy, and where yours stands."
)

# ── Search ──────────────────────────────────────────────────────────────
ids = building_options(df)
sel = st.selectbox(
    "Find your building",
    ids,
    index=None,
    format_func=lambda i: df.at[i, "label"],
    placeholder="Type a building name…",
)
if sel is not None:
    st.session_state["building_id"] = sel
    st.switch_page("views/my_building.py")

# ── Headline numbers ────────────────────────────────────────────────────
st.subheader(f"Singapore in {LATEST}")
both = df[(df["reporting"] == "reported") & df["eui_2022"].notna() & df[f"eui_{LATEST}"].notna()]
change = both[f"eui_{LATEST}"].median() / both["eui_2022"].median() - 1
top_share = (rep[f"quartile_{LATEST}"] == 1).mean()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Buildings reporting", f"{len(rep):,}", help="Plus " f"{(df.reporting == 'combined').sum()} buildings reported together with others.")
c2.metric("Median EUI", f"{rep[f'eui_{LATEST}'].median():.0f}", help="kWh/m²/yr")
c3.metric("Change since 2022", f"{change:+.1%}", help="Change in median EUI, buildings with valid data in both years.")
c4.metric("Median GFA", f"{rep['gfa'].median():,.0f}", help="m²")

# ── Go to modes ─────────────────────────────────────────────────────────
b1, b2 = st.columns(2)
with b1:
    if st.button("🏢 My Building — rank, trend and what to improve", width="stretch"):
        st.switch_page("views/my_building.py")
with b2:
    if st.button("📊 Sector Insights — distributions, trends, drivers", width="stretch"):
        st.switch_page("views/sector_insights.py")

# ── Benchmark table ─────────────────────────────────────────────────────
st.subheader(f"{LATEST} EUI benchmarks by building type")
st.caption("EUI in kWh/m²/yr. To be in a quartile, a building's EUI must fall in that range. Lower is better.")
t = bm.reset_index()
tbl = pd.DataFrame(
    {
        "Building type": t["type"],
        "Buildings": t["n_buildings"],
        "1st (top)": "≤ " + t["q1_max"].astype(int).astype(str),
        "2nd": t["q1_max"].astype(int).astype(str) + " – " + t["q2_max"].astype(int).astype(str),
        "3rd": t["q2_max"].astype(int).astype(str) + " – " + t["q3_max"].astype(int).astype(str),
        "4th (bottom)": "> " + t["q3_max"].astype(int).astype(str),
    }
)
st.dataframe(tbl, hide_index=True, width="stretch")
st.caption(
    "Mixed Development buildings have no published cut-offs; they are ranked within their own peer group."
)

with st.expander("How to read this"):
    st.markdown(
        """
- **EUI (Energy Use Intensity)** — electricity used per square metre of floor area per year (kWh/m²/yr). Lower means more efficient.
- **GUI (Gas Use Intensity)** — gas used per square metre of floor area per year (kWh/m²/yr).
- **Quartile** — buildings of the same type are split into four equal groups. **1st quartile = most efficient 25%**, 4th = least efficient 25%. BCA assigns each building's quartile.
- **kW/RT** — chiller plant efficiency: electrical power (kW) per refrigeration ton of cooling. **Lower is better.**
- **Combined** — some buildings share one electricity meter. BCA reports them together, so they have no EUI of their own here.
- **Peers** — other buildings of the same type.

*Example:* an office with EUI 140 sits in the 3rd quartile (135 – 165). Cutting it to 135 would move it to the 2nd.
"""
    )
footer()
