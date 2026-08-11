# Global Supply Chain Monitor (Streamlit)

A dashboard showing daily worldwide port activity and shipping chokepoint
transit data (Suez Canal, Panama Canal, Strait of Hormuz, etc.) on a world
map, fetched **directly from the public IMF PortWatch API**
(https://portwatch.imf.org — a project by the IMF and the University of
Oxford).

No API key required — the data is fully public.

## What it shows

- A world map: ports (color = % change in the selected metric over the last
  week, size = current level) and chokepoints (color = load relative to the
  90-day average).
- A historical map with a date slider.
- KPIs: global vessel port calls, import, export (day + week-over-week change).
- Trend charts: global (aggregated) and for a selected chokepoint.
- A ranking of the top 15 ports and the chokepoints under the highest strain.
- A detailed history view for any of the 2,065 ports.

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

The app opens in your browser at `http://localhost:8501`.

## Data updates

- The PortWatch API data itself has daily granularity, but the IMF
  publishes a new batch once a week (Tuesdays, around 9:00 ET) — so
  "today" in the data is usually a few days old.
- The dashboard caches fetched data for 6h (`st.cache_data(ttl=...)`) to
  avoid hitting the API on every click. The **"🔄 Refresh data now"**
  button in the sidebar clears the cache and forces a new fetch.
- To have the dashboard genuinely refresh itself every day (e.g. as a
  page running 24/7), the simplest options are:
  1. Deploy it on [Streamlit Community Cloud](https://streamlit.io/cloud)
     (free, just connect a repo with these files) — the cache refreshes
     on its own after the TTL, and a container restart re-fetches data.
  2. Or run it locally and just leave the `streamlit run` process
     running — data refreshes on its own once the 6h TTL expires.

## Files

- `app.py` — the main Streamlit app (UI, map, charts).
- `portwatch_data.py` — the PortWatch API access layer (REST queries,
  pagination, server-side aggregations). Can be used independently of
  Streamlit, e.g. in notebooks or other analyses.
- `requirements.txt` — dependencies.
- `run_dashboard.bat` — one-click launcher for Windows.

## Data sources (ArcGIS REST endpoints, no key required)

- Port metadata: `PortWatch_ports_database/FeatureServer/0`
- Chokepoint metadata: `PortWatch_chokepoints_database/FeatureServer/0`
- Daily port data: `Daily_Ports_Data/FeatureServer/0`
- Daily chokepoint data: `Daily_Chokepoints_Data/FeatureServer/0`

Full documentation: https://portwatch.imf.org/pages/data-and-methodology
