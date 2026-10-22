"""Shared colours and chart styling (validated ordinal blue ramp; see dataviz skill)."""
import plotly.graph_objects as go

# Quartile 1 = most efficient (lowest EUI) -> green; quartile 4 = least efficient -> red.
# Validated for lightness and colour-blind separation; gold is faint on the page background,
# so the quartile name is always shown as text too (badge, legends) and map dots grow toward Q4.
QUARTILE_COLORS = {1: "#1a9850", 2: "#cfae00", 3: "#e06a10", 4: "#cc1a1e"}
QUARTILE_TEXT = {1: "#ffffff", 2: "#0b0b0b", 3: "#0b0b0b", 4: "#ffffff"}
QUARTILE_MAP_SIZE = {1: 8, 2: 9, 3: 10, 4: 12}
QUARTILE_NAMES = {
    1: "1st quartile (top)",
    2: "2nd quartile",
    3: "3rd quartile",
    4: "4th quartile (bottom)",
}
ACCENT = "#1f5fbf"      # "this building" (blue, so it never clashes with the quartile colours)
BLUE = "#2a78d6"
CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a"]  # first 3 slots validate all-pairs
OTHER = "#8a8984"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e4e3df"


def quartile_badge(q) -> str:
    if q is None or q != q:
        return '<span style="background:#e4e3df;padding:4px 12px;border-radius:14px">No quartile</span>'
    q = int(q)
    return (
        f'<span style="background:{QUARTILE_COLORS[q]};color:{QUARTILE_TEXT[q]};'
        f'padding:4px 14px;border-radius:14px;font-weight:600">{QUARTILE_NAMES[q]}</span>'
    )


def type_pill(label: str) -> str:
    return (
        '<span style="background:#f1f0ed;border:1px solid #cfcdc7;color:#0b0b0b;padding:5px 16px;'
        f'border-radius:14px;font-weight:600;font-size:1.05rem">🏷️ {label}</span>'
    )


def style(fig: go.Figure, height: int = 420) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=13, color=INK),
        legend=dict(orientation="h", yanchor="top", y=-0.18, x=0),
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False, linecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=GRID)
    return fig


def quartile_map_traces(d, eui_col, q_col, name_col="name"):
    """One Scattermap trace per quartile so the legend doubles as the colour key."""
    traces = []
    for q in (1, 2, 3, 4):
        s = d[d[q_col] == q]
        if s.empty:
            continue
        traces.append(
            go.Scattermap(
                lat=s["lat"], lon=s["lon"], mode="markers", name=QUARTILE_NAMES[q],
                marker=dict(size=QUARTILE_MAP_SIZE[q], color=QUARTILE_COLORS[q], opacity=0.9),
                text=s[name_col] + "<br>" + s["type"] + "<br>EUI " + s[eui_col].round(0).astype(int).astype(str),
                hoverinfo="text",
            )
        )
    return traces


def style_map(fig, lat, lon, zoom, height=480):
    fig.update_layout(
        map=dict(style="open-street-map", center=dict(lat=lat, lon=lon), zoom=zoom),
        height=height, margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(orientation="h", yanchor="top", y=1, x=0, bgcolor="rgba(252,252,251,0.85)"),
    )
    return fig
