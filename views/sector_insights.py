import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib.data import LATEST, YEARS, footer, load_buildings
from lib.theme import BLUE, CATEGORICAL, OTHER, QUARTILE_COLORS, quartile_map_traces, style, style_map

df = load_buildings()
st.title("📊 Sector Insights")

# ── Filters ─────────────────────────────────────────────────────────────
GFA_BANDS = {
    "Under 10,000 m²": (0, 10_000),
    "10,000 – 30,000 m²": (10_000, 30_000),
    "30,000 – 100,000 m²": (30_000, 100_000),
    "Over 100,000 m²": (100_000, np.inf),
}
with st.sidebar:
    st.header("Filters")
    year = st.selectbox("Year", YEARS[::-1], index=0)
    types = st.multiselect("Building type", sorted(df["type"].unique()), placeholder="All types")
    bands = st.multiselect("Floor area (GFA)", list(GFA_BANDS), placeholder="All sizes")
    systems = st.multiselect("AC system", sorted(df["ac_system"].dropna().unique()), placeholder="All systems")

def apply_filters(d):
    if types:
        d = d[d["type"].isin(types)]
    if systems:
        d = d[d["ac_system"].isin(systems)]
    if bands:
        mask = pd.Series(False, index=d.index)
        for k in bands:
            lo, hi = GFA_BANDS[k]
            mask |= (d["gfa"] >= lo) & (d["gfa"] < hi)
        d = d[mask]
    return d


f = apply_filters(df[df["reporting"] == "reported"])

eui_col = f"eui_{year}"
fy = f[f[eui_col].notna()]
st.caption(f"{len(fy):,} buildings match the filters with a valid {year} EUI. Combined buildings are not included.")
if fy.empty:
    st.info("No buildings match these filters.")
    footer()
    st.stop()

tab_dist, tab_trend, tab_driver, tab_map, tab_data = st.tabs(["Distribution", "Trends", "Drivers", "Map", "Data"])

# ── Distribution ────────────────────────────────────────────────────────
with tab_dist:
    st.subheader(f"EUI by building type, {year}")
    st.caption("Each box spans the middle 50% of buildings; the line is the median. Log scale. Lower is better.")
    order = fy.groupby("type")[eui_col].median().sort_values(ascending=False).index.tolist()
    fig = go.Figure()
    for t in order:
        s = fy[fy["type"] == t]
        fig.add_trace(
            go.Box(
                x=s[eui_col], y=[t] * len(s), name=t, orientation="h", boxpoints="outliers",
                marker=dict(color=BLUE, size=4), line=dict(color=BLUE, width=1.5),
                fillcolor="rgba(42,120,214,0.25)", text=s["name"],
                hovertemplate="%{text}<br>%{x:,.0f} kWh/m²/yr<extra>" + t + "</extra>", showlegend=False,
            )
        )
    fig.update_xaxes(type="log", title="EUI (kWh/m²/yr)", tickvals=[10, 20, 50, 100, 200, 500, 1000, 5000, 10000], ticktext=["10", "20", "50", "100", "200", "500", "1,000", "5,000", "10,000"])
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(style(fig, max(320, 55 * len(order) + 90)), width="stretch")

    summary = (
        fy.groupby("type")[eui_col]
        .agg(Buildings="count", Median="median", P25=lambda s: s.quantile(0.25), P75=lambda s: s.quantile(0.75))
        .round(0).astype(int).sort_values("Median").reset_index().rename(columns={"type": "Building type", "P25": "25th pct", "P75": "75th pct"})
    )
    st.dataframe(summary, hide_index=True, width="stretch")

# ── Trends ──────────────────────────────────────────────────────────────
with tab_trend:
    both = f[f["eui_2022"].notna() & f[f"eui_{LATEST}"].notna()].copy()
    st.subheader(f"Change in median EUI, 2022 → {LATEST}")
    st.caption("Only buildings with valid EUI in both years. Negative = more efficient.")
    if both.empty:
        st.info("Not enough buildings with both years.")
    else:
        chg = both.groupby("type").apply(
            lambda g: pd.Series({"n": len(g), "chg": g[f"eui_{LATEST}"].median() / g["eui_2022"].median() - 1}),
            include_groups=False,
        )
        chg = chg[chg["n"] >= 5].sort_values("chg")
        if chg.empty:
            st.info("Each building type has fewer than 5 buildings under these filters.")
        else:
            fig = go.Figure(
                go.Bar(
                    x=chg["chg"], y=chg.index, orientation="h", marker=dict(color=BLUE),
                    text=[f"{v:+.1%}  (n={int(n)})" for v, n in zip(chg["chg"], chg["n"])], textposition="outside",
                    hovertemplate="%{y}: %{x:+.1%}<extra></extra>", cliponaxis=False,
                )
            )
            pad = 0.12 * max(0.1, chg["chg"].abs().max())
            fig.update_xaxes(tickformat="+.0%", title="Change in median EUI", range=[min(0, chg["chg"].min()) - 6 * pad, max(0, chg["chg"].max()) + 6 * pad])
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(style(fig, max(300, 42 * len(chg) + 80)), width="stretch")
            st.caption("Types with fewer than 5 buildings are hidden.")

    st.subheader(f"Did buildings move quartile? 2022 → {LATEST}")
    st.caption("BCA re-computes quartiles each year, so this shows relative movement against peers. Buildings with a quartile label in both years.")
    qm = f[f["quartile_2022"].notna() & f[f"quartile_{LATEST}"].notna()].copy()
    qm["move"] = np.sign(qm["quartile_2022"].astype(int) - qm[f"quartile_{LATEST}"].astype(int)).map(
        {1: "Moved up", 0: "Same quartile", -1: "Moved down"}
    )
    mv_counts = qm.groupby(["type", "move"]).size().unstack(fill_value=0).reindex(columns=["Moved up", "Same quartile", "Moved down"], fill_value=0)
    mv_counts = mv_counts[mv_counts.sum(axis=1) >= 5]
    if mv_counts.empty:
        st.info("Not enough buildings under these filters.")
    else:
        mv_counts["Total"] = mv_counts.sum(axis=1)
        share = mv_counts[["Moved up", "Same quartile", "Moved down"]].div(mv_counts["Total"], axis=0).sort_values("Moved up")
        fig = go.Figure()
        for col, color in (("Moved up", QUARTILE_COLORS[1]), ("Same quartile", "#d4d3cf"), ("Moved down", QUARTILE_COLORS[4])):
            fig.add_trace(
                go.Bar(
                    y=share.index, x=share[col], name=col, orientation="h",
                    marker=dict(color=color, line=dict(color="#fcfcfb", width=2)),
                    text=[f"{v:.0%}" if v >= 0.08 else "" for v in share[col]], textposition="inside",
                    hovertemplate="%{y}: %{x:.0%}<extra>" + col + "</extra>",
                )
            )
        fig.update_layout(barmode="stack")
        fig.update_xaxes(tickformat=".0%", title="Share of buildings", range=[0, 1])
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(style(fig, max(320, 42 * len(share) + 110)), width="stretch")
        st.caption("Types with fewer than 5 buildings are hidden. 'Moved up' = a better (lower-numbered) quartile.")

    st.subheader("Biggest movers, 2022 → " + str(LATEST))
    inc = st.checkbox("Include buildings flagged for data caution", value=False)
    mv = both if inc else both[both["flags"] == ""]
    mv = mv.assign(change=mv[f"eui_{LATEST}"] / mv["eui_2022"] - 1)
    cols = {"name": "Building", "type": "Type", "eui_2022": "2022", f"eui_{LATEST}": str(LATEST), "change": "Change"}
    cfg = {
        "Building": st.column_config.TextColumn(width=190),
        "Type": st.column_config.TextColumn(width=125),
        "2022": st.column_config.NumberColumn(width=58),
        str(LATEST): st.column_config.NumberColumn(width=58),
        "Change": st.column_config.NumberColumn(width=70, format="%+.0f%%"),
    }
    st.caption("EUI in kWh/m²/yr; change is 2022 → " + str(LATEST) + ".")
    for head, d in (("Most improved (largest drop in EUI)", mv.nsmallest(10, "change")), ("Largest increase in EUI", mv.nlargest(10, "change"))):
        st.markdown(f"**{head}**")
        show = d[list(cols)].rename(columns=cols).copy()
        show["Change"] = show["Change"] * 100
        show[["2022", str(LATEST)]] = show[["2022", str(LATEST)]].round(0)
        st.dataframe(show, hide_index=True, width="stretch", column_config=cfg)

# ── Drivers ─────────────────────────────────────────────────────────────
with tab_driver:
    st.subheader("What goes with higher EUI?")
    xvars = {
        "Chiller efficiency (kW/RT, lower = more efficient)": "chiller_kwrt",
        "Newest chiller age (years)": "chiller_age",
        "Building age (years since TOP/CSC)": "building_age",
        "Air-conditioned share of floor area": "ac_pct",
        "Years since last energy audit": "years_since_audit",
    }
    xl = st.selectbox("Compare EUI against", list(xvars))
    rel = st.toggle("Relative to building-type median", value=True, help="1.0 = typical for that type. Removes the effect of building type, so mixed filters stay comparable.")
    xcol = xvars[xl]
    d = fy.dropna(subset=[xcol]).copy()
    if rel:
        d["y"] = d[eui_col] / d.groupby("type")[eui_col].transform("median")
        ytitle = "EUI vs type median (1 = typical)"
    else:
        d["y"] = d[eui_col]
        ytitle = "EUI (kWh/m²/yr)"
    if len(d) < 10:
        st.info(f"Only {len(d)} buildings have valid {xl.lower()} data under these filters — too few to chart.")
    else:
        top = d["ac_system"].value_counts().index[:3].tolist()
        d["grp"] = d["ac_system"].where(d["ac_system"].isin(top), "Other / unknown")
        colors = dict(zip(top, CATEGORICAL)) | {"Other / unknown": OTHER}
        fig = go.Figure()
        for g in top + ["Other / unknown"]:
            s = d[d["grp"] == g]
            if s.empty:
                continue
            fig.add_trace(
                go.Scatter(
                    x=s[xcol], y=s["y"], mode="markers", name=g, text=s["name"],
                    marker=dict(color=colors[g], size=8, opacity=0.8, line=dict(color="#fcfcfb", width=1)),
                    hovertemplate="%{text}<br>" + xl + ": %{x:.2f}<br>" + ("Relative EUI: %{y:.2f}" if rel else "EUI: %{y:,.0f}") + "<extra>" + g + "</extra>",
                )
            )
        fig.update_xaxes(title=xl)
        fig.update_yaxes(type="log", title=ytitle)
        if rel:
            fig.update_yaxes(tickvals=[0.1, 0.2, 0.5, 1, 2, 5, 10], ticktext=["0.1", "0.2", "0.5", "1", "2", "5", "10"])
        st.plotly_chart(style(fig, 460), width="stretch")
        r = d[xcol].corr(d["y"], method="spearman")
        strength = "no clear" if abs(r) < 0.1 else "a weak" if abs(r) < 0.3 else "a moderate" if abs(r) < 0.5 else "a strong"
        direction = "higher" if r > 0 else "lower"
        trend = (
            "There is no clear relationship between the two."
            if abs(r) < 0.1
            else f"Buildings with a higher value tend to have {direction} EUI."
        )
        st.markdown(
            f"**{len(d):,} buildings** have valid data. Rank correlation: **{r:+.2f}** ({strength} relationship). {trend}"
        )
        st.caption("Correlation is not causation, and many buildings have missing or implausible values for these fields (shown blank in the source data and excluded here).")

# ── Map ─────────────────────────────────────────────────────────────────
with tab_map:
    st.subheader(f"Where are the buildings? ({year})")
    qcol = f"quartile_{year}"
    m = fy[fy["lat"].notna() & fy[qcol].notna()]
    # A map created inside a hidden tab renders blank, so only draw it once the viewer asks for it.
    if not st.toggle("Show map", value=False):
        st.caption("Switch on to draw the map of the filtered buildings.")
    elif m.empty:
        st.info("No mappable buildings under these filters.")
    else:
        fig = go.Figure(quartile_map_traces(m, eui_col, qcol))
        st.plotly_chart(style_map(fig, 1.3521, 103.8198, 10.3, 560), width="stretch")
        st.caption(f"{len(m):,} buildings. Colours show BCA's {year} quartile within each building type; darker = higher EUI.")

# ── Data ────────────────────────────────────────────────────────────────
with tab_data:
    st.subheader("Data")
    allf = apply_filters(df[df["reporting"] != "no_data"])
    show_comb = st.checkbox("Include buildings reported with others (no EUI)", value=False)
    dd = allf if show_comb else allf[allf["reporting"] == "reported"]
    cols = {
        "name": "Building", "address": "Address", "postal": "Postal code", "type": "Type", "reporting": "Reporting",
        "eui_2022": "EUI 2022", "eui_2023": "EUI 2023", "eui_2024": "EUI 2024", "eui_2025": "EUI 2025",
        "quartile_2022": "Quartile 2022", "quartile_2023": "Quartile 2023", "quartile_2024": "Quartile 2024", "quartile_2025": "Quartile 2025",
        "gui_2023": "GUI 2023", "gui_2024": "GUI 2024", "gui_2025": "GUI 2025",
        "gfa": "GFA (m2)", "ac_pct": "AC share of GFA", "ac_system": "AC system", "chiller_kwrt": "Chiller kW/RT",
        "chiller_year": "Chiller year", "audit_year": "Last audit year", "year_built": "Year built", "flags": "Data caution",
    }
    out = dd[list(cols)].rename(columns=cols).replace({"Reporting": {"reported": "Own EUI", "combined": "Reported with others"}})
    out["Reporting"] = dd["reporting"].map({"reported": "Own EUI", "combined": "Reported with others"}).values
    st.caption(f"{len(out):,} buildings. EUI and GUI in kWh/m²/yr; blank = missing or invalid in the source data.")
    first = ["Building", "Type", "EUI 2025", "Quartile 2025", "Reporting"]
    out = out[first + [c for c in out.columns if c not in first]]
    st.caption("Scroll right for more columns. The CSV download has all of them.")
    st.dataframe(
        out, hide_index=True, width="stretch", height=480,
        column_config={"Building": st.column_config.TextColumn(width="large", pinned=True)},
    )
    st.download_button("Download CSV", out.to_csv(index=False).encode("utf-8"), "bebr_filtered.csv", "text/csv")
footer()
