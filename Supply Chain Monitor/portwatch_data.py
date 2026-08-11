"""
portwatch_data.py
------------------
Data access layer for the IMF PortWatch platform (https://portwatch.imf.org).

Data comes directly from the public REST API (ArcGIS FeatureServer)
maintained by the IMF / University of Oxford. No API key required.

Services used:
- PortWatch_ports_database        -> port metadata (location, country, industries)
- PortWatch_chokepoints_database  -> shipping chokepoint metadata (location)
- Daily_Ports_Data                -> daily vessel-call and trade data per port
- Daily_Chokepoints_Data          -> daily transit data per chokepoint

Port/chokepoint data is updated by the IMF once a week (Tuesdays, 9:00 ET),
but contains daily values (one row = one day = one port/chokepoint).
"""

from __future__ import annotations

import datetime as dt
import json
from typing import Iterable, Optional

import pandas as pd
import requests

BASE = "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/ArcGIS/rest/services"

PORTS_META_URL = f"{BASE}/PortWatch_ports_database/FeatureServer/0/query"
CHOKEPOINTS_META_URL = f"{BASE}/PortWatch_chokepoints_database/FeatureServer/0/query"
PORTS_DAILY_URL = f"{BASE}/Daily_Ports_Data/FeatureServer/0/query"
CHOKEPOINTS_DAILY_URL = f"{BASE}/Daily_Chokepoints_Data/FeatureServer/0/query"

REQUEST_TIMEOUT = 30
PAGE_SIZE = 2000


class PortWatchError(RuntimeError):
    pass


def _to_datetime(series: pd.Series) -> pd.Series:
    """Converts a 'date' column to pd.Timestamp - handles both the string
    'YYYY-MM-DD' format (current ArcGIS esriFieldTypeDateOnly format) and
    epoch-milliseconds (older ArcGIS date field format), in case the
    PortWatch API ever changes this."""
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_datetime(series, unit="ms", errors="coerce")
    return pd.to_datetime(series, errors="coerce")


def _get(url: str, params: dict) -> dict:
    params = {**params, "f": "json"}
    resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and "error" in data:
        raise PortWatchError(str(data["error"]))
    return data


def fetch_all(
    url: str,
    where: str = "1=1",
    out_fields: str = "*",
    order_by: Optional[str] = None,
    page_size: int = PAGE_SIZE,
    max_pages: int = 500,
) -> pd.DataFrame:
    """Fetches all records matching the `where` clause, with pagination."""
    rows: list[dict] = []
    offset = 0
    for _ in range(max_pages):
        params = {
            "where": where,
            "outFields": out_fields,
            "resultOffset": offset,
            "resultRecordCount": page_size,
        }
        if order_by:
            params["orderByFields"] = order_by
        data = _get(url, params)
        feats = data.get("features", [])
        if not feats:
            break
        rows.extend(f["attributes"] for f in feats)
        offset += len(feats)
        if len(feats) < page_size:
            break
    return pd.DataFrame(rows)


def fetch_stats_by_date(
    url: str,
    where: str,
    sum_fields: Iterable[str],
) -> pd.DataFrame:
    """Server-side aggregated sum of the given fields, grouped by date (fast)."""
    out_stats = [
        {"statisticType": "sum", "onStatisticField": f, "outStatisticFieldName": f"{f}_sum"}
        for f in sum_fields
    ]
    params = {
        "where": where,
        "groupByFieldsForStatistics": "date",
        "outStatistics": json.dumps(out_stats),
        "orderByFields": "date",
    }
    data = _get(url, params)
    rows = [f["attributes"] for f in data.get("features", [])]
    df = pd.DataFrame(rows)
    if not df.empty and "date" in df.columns:
        df["date"] = _to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
    return df


def get_latest_date(url: str) -> str:
    """Returns the latest available date (YYYY-MM-DD) in a given daily dataset."""
    params = {
        "where": "1=1",
        "outFields": "date",
        "orderByFields": "date DESC",
        "resultRecordCount": 1,
        "returnDistinctValues": True,
    }
    data = _get(url, params)
    feats = data.get("features", [])
    if not feats:
        raise PortWatchError("No data available in this dataset.")
    raw = feats[0]["attributes"]["date"]
    if isinstance(raw, (int, float)):
        return pd.Timestamp(raw, unit="ms").date().isoformat()
    return str(raw)[:10]


# ---------------------------------------------------------------------------
# High-level functions (used directly by the dashboard)
# ---------------------------------------------------------------------------

PORT_META_FIELDS = "portid,portname,fullname,country,ISO3,continent,lat,lon,vessel_count_total,industry_top1,industry_top2,industry_top3"
CHOKE_META_FIELDS = "portid,portname,fullname,lat,lon,vessel_count_total"

PORT_DAILY_FIELDS = "date,portid,portname,country,ISO3,portcalls,portcalls_container,portcalls_dry_bulk,portcalls_tanker,portcalls_general_cargo,portcalls_roro,import,export"
CHOKE_DAILY_FIELDS = "date,portid,portname,n_total,n_container,n_dry_bulk,n_tanker,n_general_cargo,n_roro,capacity"


def load_port_locations() -> pd.DataFrame:
    df = fetch_all(PORTS_META_URL, out_fields=PORT_META_FIELDS)
    return df


def load_chokepoint_locations() -> pd.DataFrame:
    df = fetch_all(CHOKEPOINTS_META_URL, out_fields=CHOKE_META_FIELDS)
    return df


def load_latest_port_snapshot() -> tuple[pd.DataFrame, str]:
    latest = get_latest_date(PORTS_DAILY_URL)
    df = fetch_all(PORTS_DAILY_URL, where=f"date = '{latest}'", out_fields=PORT_DAILY_FIELDS)
    return df, latest


def load_port_snapshot_for_date(date_str: str) -> pd.DataFrame:
    return fetch_all(PORTS_DAILY_URL, where=f"date = '{date_str}'", out_fields=PORT_DAILY_FIELDS)


def load_port_recent_window(days: int = 8) -> pd.DataFrame:
    """Data for ALL ports over the last `days` days (used for week-over-week comparisons)."""
    latest = get_latest_date(PORTS_DAILY_URL)
    cutoff = (dt.date.fromisoformat(latest) - dt.timedelta(days=days)).isoformat()
    df = fetch_all(
        PORTS_DAILY_URL,
        where=f"date >= '{cutoff}'",
        out_fields=PORT_DAILY_FIELDS,
        order_by="date ASC",
    )
    if not df.empty:
        df["date"] = _to_datetime(df["date"])
    return df


def load_latest_chokepoint_snapshot() -> tuple[pd.DataFrame, str]:
    latest = get_latest_date(CHOKEPOINTS_DAILY_URL)
    df = fetch_all(CHOKEPOINTS_DAILY_URL, where=f"date = '{latest}'", out_fields=CHOKE_DAILY_FIELDS)
    return df, latest


def load_chokepoint_history(days: int = 120) -> pd.DataFrame:
    """Full daily history for all 28 chokepoints - a lightweight dataset."""
    latest = get_latest_date(CHOKEPOINTS_DAILY_URL)
    cutoff = (dt.date.fromisoformat(latest) - dt.timedelta(days=days)).isoformat()
    df = fetch_all(
        CHOKEPOINTS_DAILY_URL,
        where=f"date >= '{cutoff}'",
        out_fields=CHOKE_DAILY_FIELDS,
        order_by="date ASC",
    )
    if not df.empty:
        df["date"] = _to_datetime(df["date"])
    return df


def load_global_port_trend(days: int = 90) -> pd.DataFrame:
    """Aggregated (global) daily trend - computed server-side."""
    latest = get_latest_date(PORTS_DAILY_URL)
    cutoff = (dt.date.fromisoformat(latest) - dt.timedelta(days=days)).isoformat()
    df = fetch_stats_by_date(
        PORTS_DAILY_URL,
        where=f"date >= '{cutoff}'",
        sum_fields=["portcalls", "import", "export"],
    )
    return df


def load_port_history(portid: str, days: int = 180) -> pd.DataFrame:
    latest = get_latest_date(PORTS_DAILY_URL)
    cutoff = (dt.date.fromisoformat(latest) - dt.timedelta(days=days)).isoformat()
    df = fetch_all(
        PORTS_DAILY_URL,
        where=f"portid='{portid}' AND date >= '{cutoff}'",
        out_fields=PORT_DAILY_FIELDS,
        order_by="date ASC",
    )
    if not df.empty:
        df["date"] = _to_datetime(df["date"])
    return df


def load_country_trend(iso3: str, days: int = 90) -> pd.DataFrame:
    latest = get_latest_date(PORTS_DAILY_URL)
    cutoff = (dt.date.fromisoformat(latest) - dt.timedelta(days=days)).isoformat()
    df = fetch_stats_by_date(
        PORTS_DAILY_URL,
        where=f"ISO3='{iso3}' AND date >= '{cutoff}'",
        sum_fields=["portcalls", "import", "export"],
    )
    return df
