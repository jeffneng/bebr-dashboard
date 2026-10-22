# BEBR Dashboard

Interactive dashboard for BCA's **Building Energy Benchmarking Report (BEBR)** — public data on the
energy use intensity (EUI, kWh/m²/yr) of Singapore buildings of 5,000 m² GFA and above.

- **My Building** — quartile, rank among same-type peers, trend 2022–2025, gap to the next quartile,
  what could help (chiller efficiency/age, audit), and a map of nearby buildings of the same type.
- **Sector Insights** — distributions, trends, drivers of EUI, map and a filterable data table with CSV download.

Source: [BCA BEBR](https://www1.bca.gov.sg/sustainability/legislation-on-environmental-sustainability-for-buildings/existing-buildings/building-energy-benchmarking-report)
(public data, published 2026). Not official BCA advice.

## Run locally

```bash
pip install -r requirements.txt
python3 -m streamlit run app.py
```

## Update the data

1. Replace `bca-bebr-data.xlsx` with the new BCA file (same file name, same sheet layout).
2. Rebuild the cleaned data (the geocoder only looks up postal codes it hasn't seen):
   ```bash
   python3 scripts/clean_data.py
   python3 scripts/geocode.py
   ```
3. Run the app and check it, then commit and push `bca-bebr-data.xlsx` and `data/`. Community Cloud redeploys automatically.

Years (2022–2025) and the latest year are currently fixed in `scripts/clean_data.py` and `lib/data.py`;
a new data year needs a code change. Set `REPORT_PUBLISHED` in `lib/data.py` for the footer.

## Layout

| Path | Purpose |
|---|---|
| `app.py` | entry point and navigation |
| `views/` | Home, My Building, Sector Insights pages |
| `lib/` | data loading (`data.py`) and colours/chart styling (`theme.py`) |
| `scripts/clean_data.py` | Excel → tidy CSVs in `data/` (flags implausible values) |
| `scripts/geocode.py` | postal code → latitude/longitude via OneMap (no token needed) |
| `data/` | cleaned data the app reads; no secrets are needed at runtime |

## Data notes

- "Combined" buildings share a meter and have no EUI of their own.
- Zero, negative or implausibly low (< 5) EUI, and implausible chiller/audit/year fields, are treated as missing.
- BCA's quartile label sometimes differs from a ranking by the published cut-offs (BCA applies adjustments
  not in the public file). The app uses BCA's label and skips the "gap to next quartile" in those cases.
