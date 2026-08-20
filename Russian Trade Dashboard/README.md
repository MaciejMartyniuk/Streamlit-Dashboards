# Rosyjski handel: eksport 2021 vs import 2023 — dashboard

## Najprostszy sposob uruchomienia (Windows)

1. Kliknij dwa razy **`Uruchom dashboard.bat`**.
2. Jesli Windows pokaze ostrzezenie SmartScreen ("Windows chronil Twoj
   komputer"), kliknij **"Wiecej informacji"** -> **"Uruchom mimo to"**.
3. Skrypt sam sprawdzi/doinstaluje Pythona i biblioteki (`streamlit`,
   `pandas`, `numpy`, `plotly`) i otworzy dashboard w przegladarce.
   Pierwsze uruchomienie moze potrwac kilka minut.

**Wymaganie:** Python 3.9+ musi byc juz zainstalowany na komputerze (z
opcja "Add python.exe to PATH" podczas instalacji). Jesli go nie ma,
skrypt otworzy strone pobierania.

## Alternatywa (recznie, dowolny system — Windows / macOS / Linux)

```bash
pip install -r requirements.txt
python russia_trade_dashboard.py
```

Albo klasyczne `streamlit run russia_trade_dashboard.py` — w tym
przypadku dashboard wymusza ciemny motyw kolorystyczny (ciemne tlo,
biale napisy) przez wbudowany CSS, ale nie zapisze pliku
`.streamlit/config.toml`, ktory jest dodatkowym zabezpieczeniem na
wypadek jasnego trybu w systemie/przegladarce.

> Antarktyda zostala usunieta z danych (byla to znikoma, nieistotna
> pozycja we wszystkich zestawieniach eksportu/importu) — nie pojawia
> sie juz nigdzie w dashboardzie.

## Co jest w srodku

| Plik | Opis |
|---|---|
| `Uruchom dashboard.bat` | Klikalny launcher dla Windows (kod apki jest zapisany wprost w tym pliku). |
| `russia_trade_dashboard.py` | Ten sam dashboard jako pojedynczy plik Pythona. Dane WITS/Comtrade sa wbudowane wprost w srodku tego pliku, wiec do dzialania dashboardu pliki CSV ponizej **nie sa potrzebne** — `.py` oraz `.bat` dzialaja samodzielnie. |
| `requirements.txt` | Lista bibliotek Pythona potrzebnych do recznego uruchomienia (`pip install -r requirements.txt`) — przydatne np. przy sciaganiu tego folderu z GitHuba i uruchamianiu na macOS/Linux, gdzie `.bat` nie dziala. |
| `trade_data.csv` | Surowe dane zrodlowe: eksport Rosji 2021 (wlasne raportowanie Rosji) vs. import partnerow od Rosji 2023 (dane lustrzane). Uzywane w zakladkach "2021 vs 2023 maps", "Change map", "Top movers", "Data table". |
| `trade_data_imports.csv` | Jak wyzej, ale dla importu Rosji 2021 vs. eksportu partnerow do Rosji 2023 (druga strona przelacznika "Russia's exports" / "Russia's imports"). |
| `eu_fsu_trade.csv` | Surowe dane zrodlowe dla zakladki "EU vs Former USSR" (eksport/import miedzy 27 krajami UE a 12 krajami bylego ZSRR, 2021 i 2023, z oznaczeniem, ktore rekordy sa danymi lustrzanymi). |

### Kolumny w `trade_data.csv` / `trade_data_imports.csv`

- `Code` / `iso3` — kod ISO3 kraju
- `Country` — nazwa kraju
- `Value2021` / `Value2023` — wartosc w tys. USD
- `Share2021` / `Share2023` — udzial w swiatowym handlu
- `abs_change` / `pct_change` — zmiana 2021 -> 2023
- `status` — czy kraj ma dane w obu latach, tylko w 2021, czy tylko w
  2023 (patrz uwaga w opisie "Change map" ponizej — dlaczego "tylko w
  2021" **nie** oznacza realnego spadku o 100%)

### Kolumny w `eu_fsu_trade.csv`

- `eu_country` / `eu_iso3` — kraj UE
- `fsu_country` / `fsu_iso3` — kraj bylego ZSRR
- `year` — rok
- `flow` — export / import
- `value_th` — wartosc w tys. USD
- `is_mirror` — czy to dane lustrzane (dot. Rosji od 2022)

## Widoki w dashboardzie

- **"2021 vs 2023 maps"** — mapa 2021 vs 2023 obok siebie (ta sama
  skala logarytmiczna).
- **"Change map"** — mapa zmiany, z przelacznikiem eksport/import
  Rosji ("Russia's exports" / "Russia's imports") na gorze zakladki:
  2021 to wlasne dane Rosji, 2023 to dane partnerow (lustrzane), dla
  wybranego kierunku. Niebieski = wzrost, czerwony = spadek. Tytul na
  mapie i podpis wprost mowia, ktory kierunek jest pokazany. Skala
  kolorow jest wspolna dla obu kierunkow (ta sama kwota w dolarach
  wyglada tak samo niezaleznie od wyboru eksport/import). Mapa
  pokazuje **tylko** kraje z prawdziwym porownaniem 2021 vs 2023 —
  kraje, ktore w 2023 wypadly z danych lustrzanych (brak raportu
  partnera), sa z mapy wylaczone, zamiast byc pokazywane jako falszywy
  spadek o ~100% (brak raportu w 2023 nie znaczy, ze handel realnie
  spadl do zera). Takie kraje sa zamiast tego wypisane w osobnej
  tabeli w zakladce "Top movers".
- **"Top movers"** — top 15 najwiekszych wzrostow i spadkow (w
  dolarach), z tym samym przelacznikiem eksport/import i tym samym
  zastrzezeniem 2021 (Rosja) vs 2023 (partnerzy/dane lustrzane). Uwaga:
  dane lustrzane dla importu Rosji (czyli eksportu innych krajow DO
  Rosji w 2023) maja wieksza luke sprawozdawcza niz dane eksportowe
  (90 krajow wypada z zestawienia zamiast ok. 20) — opisane w zakladce
  Methodology.
- **"Data table"** — pelna tabela z filtrowaniem i eksportem do CSV.
- **"EU vs Former USSR"** — zakladka: eksport DO lub import OD (do
  wyboru) z 12 krajami bylego ZSRR, wliczajac Rosje (panstwa baltyckie
  liczone jako UE), zawsze pokazany jako 2021 (lewa mapa) vs 2023
  (prawa mapa). Wszystkie 4 mapy i oba wykresy rankingowe w tej sekcji
  dziela jedna wspolna skale kolorow/wielkosci slupkow (nie tylko w
  obrebie pary) — dana kwota w dolarach zawsze wyglada tak samo,
  niezaleznie od tego, ktory wykres ogladasz albo czy wybrales eksport
  czy import. Pod kazda para map jest tez wykres slupkowy z tymi samymi
  wartosciami w dolarach, posortowany od najwiekszego do najmniejszego
  kraju (2021 i 2023 slupek obok siebie dla latwego porownania). Nizej
  dwie klikalne mapy UE dla tego samego kierunku handlu (2021 i 2023) —
  klikniecie (lub wybor z listy) kraju UE pokazuje procentowy rozklad
  jego handlu wsrod 12 panstw bylego ZSRR (te wykresy procentowe tez
  maja wspolna, stala skale 0-100%, wiec 70% zawsze wyglada jak dwa
  razy dluzszy slupek niz 35%, w kazdym takim wykresie). Dane dla 11 z
  12 krajow sa pierwszorzedowe (raportowanie kazdego kraju UE); dane
  dla Rosji sa lustrzane (bo Rosja przestala raportowac po 2022) i sa
  oznaczone w dashboardzie (gwiazdka na wykresach slupkowych, kolumna
  "Mirror data" w tabeli danych).
- **"Methodology"** — dokladne zapytania zrodlowe (WITS SDMX API, UN
  Comtrade).
