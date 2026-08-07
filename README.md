# 🔥 Greece Historical Daily Fire Risk Dashboard

**Live app:** https://greece-fire-risk-dashboard.streamlit.app/

A public Streamlit dashboard that combines Greece's daily fire-risk prediction maps with historical fire incident records, letting you explore fire risk and fire activity across Greek forestry districts and municipalities over time.

> **⚠️ Disclaimer:** This app was built largely with AI assistance (data scraping, geo-calibration, and dashboard code). While care has been taken to validate the pipeline, the underlying data extraction (e.g. classifying risk levels from map images) is automated and may contain errors, gaps, or misclassifications. Do not use this dashboard as an authoritative source for safety decisions — always consult the official sources linked below directly.

## What's in the dashboard

The app has 5 tabs:

### Monthly map gallery
Browse the original daily fire-risk prediction map images by year and month.
- **Data source:** [Greek Ministry of Climate Crisis & Civil Protection](https://civilprotection.gov.gr/arxeio-imerision-xartwn) — daily fire-risk prediction map archive.

### District trends
Risk-level history for a single forestry district (Δασαρχείο) over time, plus its all-time risk-level distribution.
- **Data source:** derived from the same daily maps above. Risk levels are extracted programmatically by geo-registering each map image and color-sampling each forestry district's area against the map's legend colors.

### Overview dashboard
Risk-level distribution across all districts, both for the most recent date on record and cumulatively across the whole dataset.
- **Data source:** same extracted risk-level dataset as District trends.

### Fire incidents
National fire incident log (2020-2025): incident counts, burned area by year/month/municipality, a browsable records table, and a data-cleaning report.
- **Data source:** [Hellenic Fire Service](https://www.fireservice.gr/) (Πυροσβεστικό Σώμα) — yearly forest-fire incident records, merged and cleaned across years (column names and formats vary by year; see the "Data quality / cleaning report" section in this tab for details on what was corrected).

### Map synthesis
An interactive map overlaying forestry district boundaries (colored by fire-risk level), municipality boundaries, and fire incident locations (sized by burned area) for a chosen date or month.
- **Data sources:**
  - Forestry district (Δασαρχεία) and municipality (Δήμοι) boundaries: [geodata.gov.gr](https://geodata.gov.gr/) — Greek national open geospatial data portal.
  - Risk-level coloring: same extracted risk-level dataset as above.
  - Fire incident markers: same Hellenic Fire Service incident log as the Fire incidents tab.

## Tech stack

Python, Streamlit, Pandas, Altair, Folium/streamlit-folium, Pillow, Shapely, PyProj.

## Local development

```bash
pip install -r requirements.txt
streamlit run src/app.py
```

Daily data updates (scrape new maps, extract risk levels, commit, push) are handled by `scripts/daily_update.sh`, scheduled via `scripts/com.kkarys.firerisk.dailyupdate.plist` (macOS `launchd`).

## License

[MIT](LICENSE.md)
