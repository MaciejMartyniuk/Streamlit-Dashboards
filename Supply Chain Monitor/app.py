"""
Global Supply Chain Monitor
============================
Interactive Streamlit dashboard showing daily worldwide port activity and
shipping chokepoint transit data on a world map, fetched directly from the
public IMF PortWatch API (https://portwatch.imf.org) - a project by the IMF
and the University of Oxford.

Run:
    pip install -r requirements.txt
    streamlit run app.py

Data is cached (6h by default), so page refreshes don't re-download
everything - while the underlying source itself updates daily (the IMF
publishes a new batch weekly, on Tuesdays, with daily granularity going
back in time).
"""

import datetime as dt

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

import portwatch_data as pw

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Global Supply Chain Monitor",
    page_icon="🚢",
    layout="wide",
)

CACHE_TTL = 6 * 60 * 60  # 6 hours


# ---------------------------------------------------------------------------
# Cached data-fetching wrappers
# ---------------------------------------------------------------------------

@st.cache_data(ttl=CACHE_TTL, show_spinner="Loading port locations...")
def get_port_locations() -> pd.DataFrame:
    return pw.load_port_locations()


@st.cache_data(ttl=CACHE_TTL, show_spinner="Loading chokepoint locations...")
def get_chokepoint_locations() -> pd.DataFrame:
    return pw.load_chokepoint_locations()


@st.cache_data(ttl=CACHE_TTL, show_spinner="Loading recent port data...")
def get_port_recent_window(days: int = 8) -> pd.DataFrame:
    return pw.load_port_recent_window(days=days)


@st.cache_data(ttl=CACHE_TTL, show_spinner="Loading chokepoint history...")
def get_chokepoint_history(days: int = 120) -> pd.DataFrame:
    return pw.load_chokepoint_history(days=days)


@st.cache_data(ttl=CACHE_TTL, show_spinner="Loading global trend...")
def get_global_trend(days: int = 90) -> pd.DataFrame:
    return pw.load_global_port_trend(days=days)


@st.cache_data(ttl=CACHE_TTL, show_spinner="Loading port history...")
def get_port_history(portid: str, days: int = 180) -> pd.DataFrame:
    return pw.load_port_history(portid, days=days)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

st.sidebar.title("🚢 Global Supply Chain Monitor")
st.sidebar.caption("Data source: [IMF PortWatch](https://portwatch.imf.org) (IMF + University of Oxford)")

if st.sidebar.button("🔄 Refresh data now", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")

metric_options = {
    "Vessel port calls": "portcalls",
    "Import": "import",
    "Export": "export",
}
metric_label = st.sidebar.selectbox(
    "Port map metric",
    list(metric_options.keys()),
    help="Import and export are IMF PortWatch estimates based on satellite vessel-tracking data.",
)
metric_col = metric_options[metric_label]

trend_days = st.sidebar.slider("Global trend window (days)", 30, 180, 90, step=10)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Port and chokepoint data has daily granularity, but the IMF publishes "
    "a new batch once a week (Tuesdays, 9:00 ET). The dashboard caches data "
    "for 6h - use the refresh button to force a new fetch."
)

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

try:
    port_locations = get_port_locations()
    chokepoint_locations = get_chokepoint_locations()
    port_window = get_port_recent_window(days=8)
    chokepoint_hist = get_chokepoint_history(days=120)
except Exception as exc:  # noqa: BLE001
    st.error(
        "Could not fetch data from the IMF PortWatch API. "
        "Check your internet connection and try again.\n\n"
        f"Error details: {exc}"
    )
    st.stop()

if port_window.empty or port_locations.empty:
    st.warning("The PortWatch API returned no data. Try refreshing in a moment.")
    st.stop()

latest_date = port_window["date"].max()
earliest_date = port_window["date"].min()

latest_snap = port_window[port_window["date"] == latest_date].copy()
baseline_snap = port_window[port_window["date"] == earliest_date].copy()

# Join with metadata (lat/lon, country, continent)
port_map_df = latest_snap.merge(
    port_locations[["portid", "lat", "lon", "continent", "fullname"]],
    on="portid",
    how="left",
)

# % change vs the earliest day in the window (~one week earlier)
baseline_small = baseline_snap[["portid", metric_col]].rename(columns={metric_col: "baseline_val"})
port_map_df = port_map_df.merge(baseline_small, on="portid", how="left")
port_map_df["pct_change"] = (
    (port_map_df[metric_col] - port_map_df["baseline_val"]) / port_map_df["baseline_val"].replace(0, pd.NA) * 100
)
port_map_df["pct_change"] = port_map_df["pct_change"].fillna(0)
port_map_df = port_map_df.dropna(subset=["lat", "lon"])

# Ports where the selected metric is 0 usually mean no vessel activity was
# recorded that day (rather than a meaningful "zero"), and they'd otherwise
# show up as misleading -100% drops. Drop them from the map/table views.
port_map_df = port_map_df[port_map_df[metric_col] > 0]

# ---------------------------------------------------------------------------
# Header + KPIs
# ---------------------------------------------------------------------------

st.title("🚢 Global Supply Chain Monitor")
st.caption(
    f"Latest available port data: **{latest_date.date()}** • "
    f"Chokepoint data: **{chokepoint_hist['date'].max().date() if not chokepoint_hist.empty else '—'}** • "
    "Source: IMF PortWatch API (satellite AIS data, ~90k vessels, 2,065 ports, 28 chokepoints)"
)

total_portcalls = int(latest_snap["portcalls"].sum())
total_import = int(latest_snap["import"].sum())
total_export = int(latest_snap["export"].sum())

baseline_total_portcalls = int(baseline_snap["portcalls"].sum()) or 1
pct_portcalls = (total_portcalls - baseline_total_portcalls) / baseline_total_portcalls * 100

col1, col2, col3, col4 = st.columns(4)
col1.metric("Vessel port calls (world, day)", f"{total_portcalls:,}".replace(",", " "), f"{pct_portcalls:+.1f}% vs {earliest_date.date()}")
col2.metric("Import (world, day)", f"{total_import:,.0f}".replace(",", " "))
col3.metric("Export (world, day)", f"{total_export:,.0f}".replace(",", " "))
col4.metric("Active ports in database", f"{port_map_df['portid'].nunique():,}".replace(",", " "))

st.markdown("---")

# ---------------------------------------------------------------------------
# World map
# ---------------------------------------------------------------------------

st.subheader("🗺️ World map: port activity and chokepoints")

show_chokepoints = st.checkbox(
    "Show shipping chokepoints",
    value=True,
    help="Key straits and canals (Suez Canal, Panama Canal, Strait of Hormuz, etc.).",
)

# Compute chokepoint "load" (independent of the checkbox - also needed for the table below)
ck_df = pd.DataFrame()
if not chokepoint_hist.empty:
    latest_ck_date = chokepoint_hist["date"].max()
    last7_cutoff = latest_ck_date - pd.Timedelta(days=7)
    baseline_cutoff = latest_ck_date - pd.Timedelta(days=97)

    recent = chokepoint_hist[chokepoint_hist["date"] > last7_cutoff].groupby("portid")["n_total"].mean()
    baseline = chokepoint_hist[
        (chokepoint_hist["date"] > baseline_cutoff) & (chokepoint_hist["date"] <= last7_cutoff)
    ].groupby("portid")["n_total"].mean()

    stress = (recent / baseline).rename("stress_ratio").reset_index()
    ck_df = chokepoint_locations.merge(stress, on="portid", how="left")
    ck_df["stress_ratio"] = ck_df["stress_ratio"].fillna(1.0)
    latest_ck_vals = chokepoint_hist[chokepoint_hist["date"] == latest_ck_date][["portid", "n_total"]]
    ck_df = ck_df.merge(latest_ck_vals, on="portid", how="left")
    ck_df["n_total"] = ck_df["n_total"].fillna(0)
    ck_df = ck_df[ck_df["n_total"] > 0]

fig_map = go.Figure()

fig_map.add_trace(
    go.Scattergeo(
        lat=port_map_df["lat"],
        lon=port_map_df["lon"],
        text=port_map_df.apply(
            lambda r: f"{r['fullname']}<br>{metric_label}: {r[metric_col]:,.0f}<br>change vs {earliest_date.date()}: {r['pct_change']:+.1f}%",
            axis=1,
        ),
        mode="markers",
        marker=dict(
            size=port_map_df[metric_col].clip(lower=0).pow(0.5),
            sizemode="area",
            sizeref=2.0 * port_map_df[metric_col].pow(0.5).max() / (40.0 ** 2) if port_map_df[metric_col].max() else 1,
            sizemin=2,
            color=port_map_df["pct_change"],
            colorscale="RdYlGn_r",
            cmin=-50,
            cmax=50,
            colorbar=dict(title="Change % (week)", x=1.02),
            line=dict(width=0.3, color="rgba(40,40,40,0.4)"),
            opacity=0.85,
        ),
        name="Ports",
        hoverinfo="text",
    )
)

if show_chokepoints and not ck_df.empty:
    fig_map.add_trace(
        go.Scattergeo(
            lat=ck_df["lat"],
            lon=ck_df["lon"],
            text=ck_df.apply(
                lambda r: f"⚠️ {r['fullname']}<br>Transits (latest day): {r['n_total']:.0f}<br>Load vs 90d avg: {((r['stress_ratio'] - 1) * 100):+.0f}%",
                axis=1,
            ),
            mode="markers",
            marker=dict(
                size=16,
                symbol="diamond",
                color=ck_df["stress_ratio"],
                colorscale="Oranges",
                cmin=0.7,
                cmax=1.5,
                line=dict(width=1.2, color="black"),
            ),
            name="Chokepoints",
            hoverinfo="text",
        )
    )

fig_map.update_geos(
    projection_type="natural earth",
    showcountries=True,
    countrycolor="rgba(120,120,120,0.4)",
    showland=True,
    landcolor="rgb(235,235,230)",
    showocean=True,
    oceancolor="rgb(220,235,245)",
    showcoastlines=False,
)
fig_map.update_layout(
    height=620,
    margin=dict(l=0, r=0, t=10, b=0),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
)

st.plotly_chart(fig_map, use_container_width=True)
st.caption(
    "Port point color = % change in the selected metric vs "
    f"{earliest_date.date()} (red = decrease, green = increase). "
    "Point size = current metric level. Diamonds = shipping chokepoints; "
    "color = load relative to the 90-day average."
)

st.markdown("---")

# ---------------------------------------------------------------------------
# Historical map
# ---------------------------------------------------------------------------

st.subheader("🕰️ Historical map")

hist_layer = st.radio(
    "Data layer",
    ["Chokepoints", "Ports"],
    horizontal=True,
    help=(
        "Chokepoints: 28 locations, load instantly. "
        "Ports: about 2,065 locations - the first load for a given date "
        "range can take a moment, then it's cached."
    ),
)

if hist_layer == "Ports":
    hist_days = st.slider("History range (days)", 7, 60, 14, step=7)
    hist_df = get_port_recent_window(days=hist_days).merge(
        port_locations[["portid", "lat", "lon", "fullname"]], on="portid", how="left"
    ).dropna(subset=["lat", "lon"])
    hist_metric = metric_col
    hist_metric_label = metric_label
else:
    hist_df = chokepoint_hist.merge(
        chokepoint_locations[["portid", "lat", "lon", "fullname"]],
        on="portid",
        how="left",
        suffixes=("", "_meta"),
    ).dropna(subset=["lat", "lon"])
    hist_metric = "n_total"
    hist_metric_label = "Transit count"

if not hist_df.empty:
    hist_df = hist_df.copy()
    hist_df["date_only"] = hist_df["date"].dt.date
    available_dates = sorted(hist_df["date_only"].unique())

    selected_date = st.select_slider(
        "Date",
        options=available_dates,
        value=available_dates[-1],
        format_func=lambda d: d.strftime("%Y-%m-%d"),
    )
    # Drop zero-value points: for the selected metric, 0 almost always means
    # no activity was recorded that day rather than a meaningful data point,
    # and including them just clutters the map.
    day_df = hist_df[(hist_df["date_only"] == selected_date) & (hist_df[hist_metric] > 0)]

    metric_max = hist_df[hist_metric].max()
    fig_hist = go.Figure(
        go.Scattergeo(
            lat=day_df["lat"],
            lon=day_df["lon"],
            text=day_df.apply(
                lambda r: f"{r['fullname']}<br>{hist_metric_label}: {r[hist_metric]:,.0f}",
                axis=1,
            ),
            mode="markers",
            marker=dict(
                size=day_df[hist_metric].clip(lower=0).pow(0.5),
                sizemode="area",
                sizeref=2.0 * (metric_max ** 0.5) / (40.0 ** 2) if metric_max else 1,
                sizemin=2,
                color=day_df[hist_metric],
                colorscale="YlOrRd",
                cmin=0,
                cmax=metric_max,
                colorbar=dict(title=hist_metric_label, x=1.02),
                line=dict(width=0.3, color="rgba(40,40,40,0.4)"),
                opacity=0.85,
            ),
            hoverinfo="text",
        )
    )
    fig_hist.update_geos(
        projection_type="natural earth",
        showcountries=True,
        countrycolor="rgba(120,120,120,0.4)",
        showland=True,
        landcolor="rgb(235,235,230)",
        showocean=True,
        oceancolor="rgb(220,235,245)",
        showcoastlines=False,
    )
    fig_hist.update_layout(height=620, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig_hist, use_container_width=True)
    st.caption(
        f"Data for: {selected_date.strftime('%Y-%m-%d')}. "
        "Point size and color = metric level for that day "
        "(color/size scale is fixed across the whole range, for comparability between days)."
    )
else:
    st.info("No data available for the historical map.")

st.markdown("---")

# ---------------------------------------------------------------------------
# Trends
# ---------------------------------------------------------------------------

col_a, col_b = st.columns(2)

with col_a:
    st.subheader("📈 Global daily trend")
    trend_df = get_global_trend(days=trend_days)
    if not trend_df.empty:
        # Vessel port calls (count) and import/export (volume) are on very
        # different scales, so they're plotted on two separate Y axes.
        fig_trend = make_subplots(specs=[[{"secondary_y": True}]])
        fig_trend.add_trace(
            go.Scatter(
                x=trend_df["date"], y=trend_df["portcalls_sum"],
                name="Vessel port calls", line=dict(color="#636EFA"),
            ),
            secondary_y=False,
        )
        fig_trend.add_trace(
            go.Scatter(
                x=trend_df["date"], y=trend_df["import_sum"],
                name="Import", line=dict(color="#EF553B"),
            ),
            secondary_y=True,
        )
        fig_trend.add_trace(
            go.Scatter(
                x=trend_df["date"], y=trend_df["export_sum"],
                name="Export", line=dict(color="#00CC96"),
            ),
            secondary_y=True,
        )
        fig_trend.update_yaxes(title_text="Vessel port calls / day", secondary_y=False)
        fig_trend.update_yaxes(title_text="Import / Export (volume)", secondary_y=True)
        fig_trend.update_layout(
            height=400,
            legend=dict(orientation="h", y=1.15),
            margin=dict(t=40),
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("No trend data available for the selected period.")

with col_b:
    st.subheader("⚓ Chokepoint trend")
    if not chokepoint_hist.empty:
        ck_names = sorted(chokepoint_hist["portname"].dropna().unique())
        default_idx = ck_names.index("Suez Canal") if "Suez Canal" in ck_names else 0
        chosen_ck = st.selectbox("Select a chokepoint", ck_names, index=default_idx)
        ck_series = chokepoint_hist[chokepoint_hist["portname"] == chosen_ck].sort_values("date")
        fig_ck = px.line(
            ck_series,
            x="date",
            y=["n_total", "n_container", "n_tanker"],
            labels={"value": "Transits / day", "date": "Date", "variable": "Vessel type"},
        )
        fig_ck.update_layout(height=400, legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig_ck, use_container_width=True)
    else:
        st.info("No chokepoint data available.")

st.markdown("---")

# ---------------------------------------------------------------------------
# Tables: top ports and top chokepoints
# ---------------------------------------------------------------------------

col_c, col_d = st.columns(2)

with col_c:
    st.subheader(f"🏆 Top 15 ports by: {metric_label}")
    top_ports = (
        port_map_df.sort_values(metric_col, ascending=False)
        .head(15)[["fullname", "continent", metric_col, "pct_change"]]
        .rename(columns={"fullname": "Port", "continent": "Continent", metric_col: metric_label, "pct_change": "Change % (week)"})
    )
    st.dataframe(top_ports, use_container_width=True, hide_index=True)

with col_d:
    st.subheader("🔥 Chokepoints under highest strain")
    if not ck_df.empty:
        stress_table = ck_df.sort_values("stress_ratio", ascending=False).head(15)[
            ["fullname", "n_total", "stress_ratio"]
        ].rename(columns={"fullname": "Chokepoint", "n_total": "Transits (latest day)", "stress_ratio": "Load vs 90d avg"})
        stress_table["Load vs 90d avg"] = (stress_table["Load vs 90d avg"] - 1) * 100
        st.dataframe(
            stress_table.style.format({"Load vs 90d avg": "{:+.0f}%"}),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No data available.")

st.markdown("---")

# ---------------------------------------------------------------------------
# Drill-down: single port
# ---------------------------------------------------------------------------

st.subheader("🔍 Port details")
port_names_sorted = port_locations.sort_values("fullname")["fullname"].dropna().unique()
chosen_port_fullname = st.selectbox("Select a port", port_names_sorted, index=0)
chosen_port_row = port_locations[port_locations["fullname"] == chosen_port_fullname].iloc[0]
chosen_portid = chosen_port_row["portid"]

port_hist_days = st.slider("Port history range (days)", 30, 365, 180, step=30)
port_hist_df = get_port_history(chosen_portid, days=port_hist_days)

if not port_hist_df.empty:
    # Same as above: vessel calls vs import/export are on very different scales.
    fig_port = make_subplots(specs=[[{"secondary_y": True}]])
    fig_port.add_trace(
        go.Scatter(
            x=port_hist_df["date"], y=port_hist_df["portcalls"],
            name="Vessel port calls", line=dict(color="#636EFA"),
        ),
        secondary_y=False,
    )
    fig_port.add_trace(
        go.Scatter(
            x=port_hist_df["date"], y=port_hist_df["import"],
            name="Import", line=dict(color="#EF553B"),
        ),
        secondary_y=True,
    )
    fig_port.add_trace(
        go.Scatter(
            x=port_hist_df["date"], y=port_hist_df["export"],
            name="Export", line=dict(color="#00CC96"),
        ),
        secondary_y=True,
    )
    fig_port.update_yaxes(title_text="Vessel port calls / day", secondary_y=False)
    fig_port.update_yaxes(title_text="Import / Export (volume)", secondary_y=True)
    fig_port.update_layout(
        height=420,
        legend=dict(orientation="h", y=1.15),
        title=f"{chosen_port_row['fullname']} — daily history",
        margin=dict(t=60),
    )
    st.plotly_chart(fig_port, use_container_width=True)

    info_cols = st.columns(3)
    info_cols[0].metric("Country", chosen_port_row.get("country", "—"))
    info_cols[1].metric("Continent", chosen_port_row.get("continent", "—"))
    info_cols[2].metric("Top industry", chosen_port_row.get("industry_top1", "—"))
else:
    st.info("No historical data available for the selected port in this time window.")

st.markdown("---")
st.caption(
    "Data: [IMF PortWatch](https://portwatch.imf.org) — a project by the IMF and the "
    "University of Oxford, provided under the IMF Open Data license. This dashboard is "
    "not an official IMF product."
)
