import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib.data import LATEST, YEARS, building_options, footer, haversine_km, load_benchmarks, load_buildings, official_quartile
from lib.theme import ACCENT, INK_2, OTHER, QUARTILE_NAMES, quartile_badge, quartile_map_traces, style, style_map, type_pill

df = load_buildings()
bm = load_benchmarks()

st.title("🏢 My Building")

ids = building_options(df)
current = st.session_state.get("building_id")
sel = st.selectbox(
    "Find your building",
    ids,
    index=ids.index(current) if current in ids else None,
    format_func=lambda i: df.at[i, "label"],
    placeholder="Type a building name…",
)
if sel is None:
    st.info("Choose a building to see its energy scorecard.")
    footer()
    st.stop()
st.session_state["building_id"] = sel
b = df.loc[sel]

st.header(b["name"])
st.markdown(type_pill(b["type"]), unsafe_allow_html=True)
st.caption(f"{b['address']} · Singapore {b['postal']}")

if b["reporting"] == "combined":
    st.warning(
        "This building is **reported with other buildings** under a shared electricity meter, "
        "so BCA does not publish an EUI for it on its own."
    )
    footer()
    st.stop()
if b["reporting"] == "no_data":
    st.warning("No usable energy data is available for this building.")
    footer()
    st.stop()

yr = next((y for y in reversed(YEARS) if pd.notna(b[f"eui_{y}"])), None)
if yr is None:
    st.warning("No valid EUI figure for this building (values were zero or missing).")
    footer()
    st.stop()

eui = b[f"eui_{yr}"]
peers = df[(df["type"] == b["type"]) & (df["reporting"] == "reported") & df[f"eui_{yr}"].notna()]
others = peers[peers["id"] != b["id"]]
rank = int(1 + (peers[f"eui_{yr}"] < eui).sum())
better_than = (others[f"eui_{yr}"] > eui).mean() if len(others) else np.nan
quartile = b[f"quartile_{yr}"]
mismatch = (
    b["type"] in bm.index
    and pd.notna(quartile)
    and official_quartile(eui, bm.loc[b["type"]]) != int(quartile)
)

if b["flags"]:
    st.warning("⚠️ Data caution: " + b["flags"] + ". Figures are shown as reported.")

# ── Scorecard ───────────────────────────────────────────────────────────
st.markdown(quartile_badge(quartile) + f" &nbsp;<span style='color:#52514e'>among {b['type']} buildings</span>", unsafe_allow_html=True)
if mismatch:
    st.caption(
        "BCA's quartile label uses its own adjustments, so it can differ from a simple ranking by EUI "
        "(see rank below)."
    )
c1, c2, c3, c4 = st.columns(4)
c1.metric(f"{yr} EUI", f"{eui:,.0f}", help="kWh/m²/yr")
c2.metric(f"Rank (of {len(peers)})", f"{rank}", help=f"Among {b['type']} buildings with a valid EUI. 1 = lowest EUI (most efficient).")
c3.metric("Better than", f"{better_than:.0%}" if pd.notna(better_than) else "–", help="Share of other buildings of the same type with a higher EUI.")
c4.metric("GFA", f"{b['gfa']:,.0f}", help="m²")
if yr != LATEST:
    st.caption(f"Latest valid year for this building is {yr}.")

# ── Gap to next quartile ────────────────────────────────────────────────
st.subheader("How far to the next quartile?")
if b["type"] not in bm.index:
    st.info(
        f"BCA publishes no quartile cut-offs for {b['type']} buildings, so a target can't be calculated. "
        f"Its quartile label is shown above, and it ranks {rank} of {len(peers)} among peers."
    )
elif pd.isna(quartile):
    st.info("BCA has not assigned a quartile for this year.")
elif mismatch:
    st.info(
        "A gap to the next quartile isn't shown: BCA's label for this building uses adjustments that aren't in the "
        "public data, so the published EUI ranges don't line up with it and a gap could mislead."
    )
elif int(quartile) == 1:
    st.success("Already in the top quartile for its building type. 🎉")
else:
    cut = bm.loc[b["type"]]
    q = int(quartile)
    target = {2: cut.q1_max, 3: cut.q2_max, 4: cut.q3_max}[q]
    gap = eui - target
    a, bcol, ccol = st.columns(3)
    a.metric("Target EUI", f"≤ {target:,.0f}", help=f"To reach the {QUARTILE_NAMES[q - 1]}. kWh/m²/yr")
    bcol.metric("Reduction needed", f"{gap:,.1f}", f"-{gap / eui:.0%}", delta_color="off", help="kWh/m²/yr")
    ccol.metric("≈ MWh per year", f"{gap * b['gfa'] / 1000:,.0f}", help="Gap × GFA. Indicative only.")

# ── Trend ───────────────────────────────────────────────────────────────
st.subheader("Is it getting better or worse?")
rows = []
for y in YEARS:
    p = peers_y = df[(df["type"] == b["type"]) & (df["reporting"] == "reported") & df[f"eui_{y}"].notna()][f"eui_{y}"]
    rows.append((y, b[f"eui_{y}"], p.median(), p.quantile(0.25), p.quantile(0.75)))
t = pd.DataFrame(rows, columns=["year", "own", "median", "p25", "p75"])
fig = go.Figure()
fig.add_trace(go.Scatter(x=t.year, y=t.p75, mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"))
fig.add_trace(
    go.Scatter(
        x=t.year, y=t.p25, mode="lines", line=dict(width=0), fill="tonexty",
        fillcolor="rgba(138,137,132,0.18)", name="Middle 50% of peers", hoverinfo="skip",
    )
)
fig.add_trace(go.Scatter(x=t.year, y=t["median"], mode="lines", line=dict(color=OTHER, dash="dash", width=2), name="Peer median"))
fig.add_trace(
    go.Scatter(
        x=t.year, y=t.own, mode="lines+markers", connectgaps=False,
        line=dict(color=ACCENT, width=2), marker=dict(size=9, line=dict(color="#fcfcfb", width=2)),
        name="This building",
    )
)
fig.update_xaxes(tickvals=YEARS)
fig.update_yaxes(title="EUI (kWh/m²/yr)")
fig.update_layout(hovermode="x unified")
st.plotly_chart(style(fig, 380), width="stretch")

valid = t.dropna(subset=["own"])
if len(valid) >= 2:
    first, last = valid.iloc[0], valid.iloc[-1]
    ch = last.own / first.own - 1
    peer_ch = last["median"] / first["median"] - 1
    verdict = "✅ Improving" if ch < -0.03 else "⚠️ Rising" if ch > 0.03 else "➖ Stable"
    st.markdown(
        f"**{verdict}:** EUI went from {first.own:,.0f} in {int(first.year)} to {last.own:,.0f} in {int(last.year)} "
        f"({ch:+.0%}); the peer median moved {peer_ch:+.0%} over the same period."
    )
    if len(valid) < 4:
        st.caption("Some years are missing or invalid, so the line has gaps.")

# ── Improve ─────────────────────────────────────────────────────────────
st.subheader("What could help?")
st.caption("Compared with same-type peers. These are patterns in the data, not guaranteed savings.")


def row(name, own, peer_vals, fmt, lower_better=True):
    pv = peer_vals.dropna()
    if pd.isna(own) or len(pv) < 5:
        return {"Factor": name, "This building": "no data" if pd.isna(own) else fmt(own),
                "Peer median": fmt(pv.median()) if len(pv) >= 5 else "–", "Status": "— Not enough data"}
    med = pv.median()
    better = own < med if lower_better else own > med
    same = np.isclose(own, med, rtol=0.03)
    status = "➖ Similar to peers" if same else ("✅ Better than peers" if better else "⚠️ Worse than peers")
    return {"Factor": name, "This building": fmt(own), "Peer median": fmt(med), "Status": status}


pool = df[(df["type"] == b["type"]) & (df["reporting"] == "reported")]
items = [
    row("Chiller efficiency (kW/RT, lower is better)", b["chiller_kwrt"], pool["chiller_kwrt"], lambda v: f"{v:.2f}"),
    row("Newest chiller age (years)", b["chiller_age"], pool["chiller_age"], lambda v: f"{v:.0f}"),
    row("Years since last energy audit", b["years_since_audit"], pool["years_since_audit"], lambda v: f"{v:.0f}"),
]
if b[f"gui_{LATEST}"] > 0:  # most buildings report no gas use; a 0 vs 0 row says nothing
    items.append(row(f"Gas use intensity, {LATEST} (kWh/m²/yr)", b[f"gui_{LATEST}"], pool[f"gui_{LATEST}"], lambda v: f"{v:.1f}"))
st.dataframe(pd.DataFrame(items), hide_index=True, width="stretch")

if pd.notna(b["ac_system"]):
    same_sys = pool[pool["ac_system"] == b["ac_system"]][f"eui_{LATEST}"].dropna()
    all_med = pool[f"eui_{LATEST}"].median()
    if len(same_sys) >= 5:
        st.markdown(
            f"**Air-conditioning system:** {b['ac_system']}. {b['type']} buildings with this system have a median EUI of "
            f"**{same_sys.median():,.0f}** (n={len(same_sys)}), against **{all_med:,.0f}** for all {b['type']} buildings."
        )
    else:
        st.markdown(f"**Air-conditioning system:** {b['ac_system']} (too few peers to compare).")

# ── Near me ─────────────────────────────────────────────────────────────
st.subheader(f"{b['type']} buildings near me")
if pd.isna(b["lat"]):
    st.info("This building's location couldn't be found, so the map isn't available.")
else:
    km = st.slider("Radius (km)", 0.25, 5.0, 1.0, 0.25)
    cand = df[
        (df["reporting"] == "reported") & (df["type"] == b["type"]) & df["lat"].notna()
        & df[f"eui_{yr}"].notna() & (df["id"] != b["id"])
    ].copy()
    cand["km"] = haversine_km(b["lat"], b["lon"], cand["lat"], cand["lon"])
    nb = cand[cand["km"] <= km].sort_values("km")
    fig = go.Figure(quartile_map_traces(nb, f"eui_{yr}", f"quartile_{yr}"))
    fig.add_trace(  # white halo under the marker keeps it visible on any map tile
        go.Scattermap(lat=[b["lat"]], lon=[b["lon"]], mode="markers", marker=dict(size=25, color="#ffffff"), hoverinfo="skip", showlegend=False)
    )
    fig.add_trace(
        go.Scattermap(
            lat=[b["lat"]], lon=[b["lon"]], mode="markers", name="This building",
            marker=dict(size=18, color=ACCENT), text=[b["name"]], hoverinfo="text",
        )
    )
    zoom = 15 if km <= 0.5 else 14 if km <= 1 else 13 if km <= 2 else 12
    st.plotly_chart(style_map(fig, b["lat"], b["lon"], zoom), width="stretch")
    st.caption(f"{len(nb)} other {b['type']} buildings within {km:g} km. Colours show BCA's {yr} quartile.")
    if nb.empty:
        st.info(f"No other {b['type']} buildings within {km:g} km. Try a larger radius.")
    else:
        tbl = nb.head(15)[["name", "type", "km", f"eui_{yr}", f"quartile_{yr}"]].copy()
        tbl["km"] = tbl["km"].round(2)
        tbl[f"eui_{yr}"] = tbl[f"eui_{yr}"].round(0)
        tbl[f"quartile_{yr}"] = tbl[f"quartile_{yr}"].map(lambda q: {1: "1st (top)", 2: "2nd", 3: "3rd", 4: "4th (bottom)"}[int(q)] if pd.notna(q) else "–")
        tbl.columns = ["Building", "Type", "Distance (km)", f"EUI {yr}", "Quartile"]
        st.dataframe(tbl, hide_index=True, width="stretch")
footer()
