# Russian trade: 2021 exports vs 2023 imports — dashboard

## Easiest way to run it (Windows)

1. Double-click **`Uruchom dashboard.bat`**.
2. If Windows shows a SmartScreen warning ("Windows protected your PC"),
   click **"More info"** -> **"Run anyway"**.
3. The script will check/install Python and the required libraries
   (`streamlit`, `pandas`, `numpy`, `plotly`) itself and open the
   dashboard in your browser. The first run can take a few minutes.

**Requirement:** Python 3.9+ must already be installed on the computer
(with the "Add python.exe to PATH" option checked during installation).
If it isn't installed, the script will open the download page.

## Alternative (manual, any OS — Windows / macOS / Linux)

```bash
pip install -r requirements.txt
python russia_trade_dashboard.py
```

Or the classic `streamlit run russia_trade_dashboard.py` — in that case
the dashboard still forces its dark color theme (dark background, white
text) via built-in CSS, but it won't write the `.streamlit/config.toml`
file, which is an extra safeguard against a light theme in your
OS/browser.

> Antarctica has been removed from the data (it was a negligible,
> irrelevant entry in every export/import breakdown) — it no longer
> appears anywhere in the dashboard.

## What's inside

| File | Description |
|---|---|
| `Uruchom dashboard.bat` | Clickable launcher for Windows (the app's code is written directly into this file). |
| `russia_trade_dashboard.py` | The same dashboard as a single Python file. The WITS/Comtrade data is embedded directly inside this file, so the CSV files below are **not required** for the dashboard to run — the `.py` and the `.bat` both work standalone. |
| `requirements.txt` | The list of Python libraries needed to run it manually (`pip install -r requirements.txt`) — useful e.g. when pulling this folder from GitHub and running it on macOS/Linux, where the `.bat` won't work. |
| `trade_data.csv` | Raw source data: Russia's 2021 exports (Russia's own reporting) vs. partner countries' 2023 imports from Russia (mirror data). Used in the "2021 vs 2023 maps", "Change map", "Top movers", and "Data table" tabs. |
| `trade_data_imports.csv` | Same as above, but for Russia's 2021 imports vs. partner countries' 2023 exports to Russia (the other side of the "Russia's exports" / "Russia's imports" toggle). |
| `eu_fsu_trade.csv` | Raw source data for the "EU vs Former USSR" tab (exports/imports between the 27 EU countries and 12 former-USSR countries, 2021 and 2023, flagging which records are mirror data). |

### Columns in `trade_data.csv` / `trade_data_imports.csv`

- `Code` / `iso3` — the country's ISO3 code
- `Country` — country name
- `Value2021` / `Value2023` — value in US$ thousand
- `Share2021` / `Share2023` — share of world trade
- `abs_change` / `pct_change` — change from 2021 to 2023
- `status` — whether the country has data in both years, only in 2021,
  or only in 2023 (see the note in the "Change map" section below on
  why "2021 only" does **not** mean trade actually fell by 100%)

### Columns in `eu_fsu_trade.csv`

- `eu_country` / `eu_iso3` — EU country
- `fsu_country` / `fsu_iso3` — former-USSR country
- `year` — year
- `flow` — export / import
- `value_th` — value in US$ thousand
- `is_mirror` — whether this is mirror data (applies to Russia from 2022 onward)

## Views in the dashboard

- **"2021 vs 2023 maps"** — 2021 and 2023 maps side by side (same
  logarithmic scale).
- **"Change map"** — a map of the change, with a toggle for Russia's
  export/import direction ("Russia's exports" / "Russia's imports") at
  the top of the tab: 2021 is Russia's own data, 2023 is partner
  countries' data (mirror data), for whichever direction is selected.
  Blue = grew from 2021 to 2023, red = shrank. The map title and
  caption spell out exactly which direction is shown. The color scale
  is shared between both directions (the same dollar amount always
  looks the same regardless of the export/import choice). The map
  shows **only** countries with a genuine 2021-vs-2023 comparison —
  countries that dropped out of the 2023 mirror data (no partner
  report) are excluded from the map, instead of being shown as a false
  ~100% decline (a missing 2023 report doesn't mean trade actually fell
  to zero). Those countries are listed instead in a separate table in
  the "Top movers" tab.
- **"Top movers"** — the top 15 largest increases and decreases (in
  dollars), with the same export/import toggle and the same 2021
  (Russia) vs. 2023 (partners/mirror data) caveat. Note: the mirror
  data for Russia's imports (i.e. other countries' exports TO Russia in
  2023) has a much bigger reporting gap than the export-side data (90
  countries drop out instead of about 20) — described in the
  Methodology tab.
- **"Data table"** — the full table, with filtering and CSV export.
- **"EU vs Former USSR"** — a tab for exports TO or imports FROM
  (selectable) the 12 former-USSR countries, including Russia (the
  Baltic states are counted as EU), always shown as 2021 (left map) vs.
  2023 (right map). All 4 maps and both ranking charts in this section
  share ONE common color/bar-size scale (not just within a pair) — a
  given dollar amount always looks the same regardless of which chart
  you're looking at, or whether you selected exports or imports. Below
  each map pair is a bar chart with the same dollar values, sorted from
  largest to smallest country (2021 and 2023 bars side by side for easy
  comparison). Further below are two clickable EU maps for the same
  trade direction (2021 and 2023) — clicking (or selecting from the
  list) an EU country shows the percentage breakdown of its trade among
  the 12 former-USSR countries (these percentage charts also share a
  fixed 0-100% scale, so 70% always looks like twice the bar length of
  35% in every such chart). Data for 11 of the 12 countries is
  first-party (each EU country's own reporting); data for Russia is
  mirror data (since Russia stopped reporting after 2022) and is
  flagged in the dashboard (an asterisk on the bar charts, a "Mirror
  data" column in the data table).
- **"Methodology"** — the exact source queries used (WITS SDMX API, UN
  Comtrade).
