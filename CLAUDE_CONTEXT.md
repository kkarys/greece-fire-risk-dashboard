# Greece Fire Risk Dashboard — Claude Session Context

Use this file to resume development in a new Claude session. Paste its full contents as your first message.

---

## Project summary

A public Streamlit dashboard that combines:
1. **Daily fire-risk prediction maps** from the Greek Civil Protection agency, geo-registered and color-sampled to extract per-district risk levels, stored in a CSV.
2. **National Fire Service incident logs** (2020–2025 xlsx files), merged, cleaned, and displayed alongside the risk maps.
3. A **map synthesis tab** with interactive Folium map: risk-colored forestry district boundaries, municipality outlines, and fire incident point overlays (graduated symbols by burned area).

**Live app:** https://greece-fire-risk-dashboard.streamlit.app/  
**GitHub repo:** https://github.com/kkarys/greece-fire-risk-dashboard.git  
**Local working directory:** `/Users/iti-thermi/Documents/SideProject`

---

## Tech stack

- Python 3.9 (system `/usr/bin/python3`)
- Streamlit (local: `/Users/iti-thermi/Library/Python/3.9/bin/streamlit`)
- Pandas, Altair, Folium, streamlit-folium, Pillow, Shapely, PyProj, openpyxl, requests
- Git remote: HTTPS with osxkeychain PAT auth (no interactive prompt needed)

---

## Directory structure

```
SideProject/
├── src/
│   ├── app.py                  # Main Streamlit dashboard (5 tabs)
│   ├── scraper.py              # Downloads daily JPG maps from civilprotection.gov.gr
│   ├── pipeline.py             # Orchestrates download → extract → append to CSV
│   ├── risk_extraction.py      # Geo-registers map image, samples colors, classifies risk
│   ├── calibration.py          # Affine transform constants for 2 image sizes
│   ├── fire_incidents.py       # Merges/cleans 6 yearly xlsx files
│   └── prepare_map_layers.py   # One-time: reproject + simplify GeoJSONs to WGS84
├── scripts/
│   ├── daily_update.sh         # Manual daily run: scrape → extract → git push
│   └── com.kkarys.firerisk.dailyupdate.plist  # launchd plist (UNLOADED — TCC issue)
├── data/
│   ├── raw/                    # 1,442 downloaded JPG map images (260101.jpg etc.)
│   └── processed/
│       ├── risk_history.csv    # 152,322 rows: date, district, risk_level, risk_name, confidence_ok
│       ├── dasarxeia_map.geojson  # 106 forestry districts, WGS84, simplified
│       └── dimoi_map.geojson      # 326 municipalities, WGS84, simplified
├── Boundaries/
│   ├── Dasarxeia.geojson       # Raw EPSG:2100 forestry district boundaries
│   └── Dimoi.geojson           # Raw EPSG:2100 municipality boundaries
├── tables/
│   ├── Dasikes_Pyrkagies_2020.xlsx … 2025.xlsx  # Raw incident logs
│   ├── Dasikes_Pyrkagies_Merged_Clean.csv        # 58,110 rows merged+cleaned
│   └── Dasikes_Pyrkagies_Cleaning_Report.csv
└── requirements.txt
```

---

## Key source files

### src/calibration.py
Two image-size templates for geo-registration (affine transform from EPSG:2100 to pixel coordinates):
```python
TEMPLATES = {
    (1384, 1453): {"scale": 0.8877435897435897, "tx": -26.0, "ty": 141.0},
    (830, 872):   {"scale": 0.5327586206896552, "tx": -15.172413793103452, "ty": 84.82758620689654},
}
```
Images at other sizes (e.g. 360×380 thumbnails from 2022-07, 1187×1246 from 2017-06-24) are skipped with a `CalibrationMismatch` warning.

### src/scraper.py
Tries multiple URL patterns per date:
- `BASE_URL/{YYYY-MM}/{YYMMDD}.{jpg,jpeg,png}` — 2023+ current month folder
- `BASE_URL/{YYYY-MM_prev}/{YYMMDD}.{jpg,jpeg,png}` — previous month folder (agency sometimes uploads late; e.g. July 1 map is under 2026-06/)
- `BASE_URL/{YYMMDD}.{jpg,jpeg,png}` — 2022 and earlier, flat path
- `BASE_URL/{YYMMDD}_0.gif` — very old archive ~2005–2008

### src/risk_extraction.py
```python
LEGEND_COLORS = {1:(167,253,170), 2:(167,200,242), 3:(255,255,0), 4:(253,172,2), 5:(253,0,2)}
LOW_CONFIDENCE_THRESHOLD = 200
```
Samples a patch at each district's `representative_point()`, classifies by nearest RGB in Euclidean distance.

### src/fire_incidents.py
Merges 6 xlsx files. Key facts:
- 2020–2024: `header=1`; 2025: `sheet_name="Sheet0"`, `header=3`
- `burned_total` = sum of 8 burned-area columns
- `incident_id` = `f"{source_year}-{record_id}"` (record_id is recycled per year)
- 136 rows dropped (end_date < start_date)
- 5 prefecture spelling normalizations applied
- Coordinates: `x_engage`/`y_engage` in EPSG:2100; nulled where "Not Found" or (0,0)

### src/app.py — Tab structure
```
tab_gallery    — Monthly map gallery (image grid by year/month)
tab_trends     — District trends (scatter + risk distribution bar)
tab_overview   — Overview dashboard (risk distribution, all-time)
tab_incidents  — Fire incidents (metrics, incident count bar, burned area chart, data table, cleaning report)
tab_map        — Map synthesis (@st.fragment)
```

**Key caching pattern:**
```python
@st.cache_data
def load_data(_mtime: float): ...
df = load_data(PROCESSED_PATH.stat().st_mtime)  # auto-invalidates on file change
```

**Map synthesis tab** (wrapped in `@st.fragment` to prevent tab-jumping on filter change):
- Checkboxes: Show Δασαρχεία / Show Δήμοι / Show fire incidents
- Selectboxes: Year / Month / Day (with session_state guards for cascade validity)
- `build_synthesis_map()` is intentionally NOT cached (removing `@st.cache_resource` fixed map disappearing after ~3 filter changes)
- Dasarxeia layer: `weight=0`, `fillOpacity=0.6`, colored by risk level
- Dimoi layer: `color="#1f78b4"`, `weight=1`, `fillOpacity=0`, rendered on top
- Fire incidents: `CircleMarker` with 3-class graduated symbol by `burned_total`:
  - Small: 0–50 στρ. → radius 5px
  - Medium: 51–200 στρ. → radius 12px
  - Large: >200 στρ. → radius 22px
- Two legends below map: 5-color risk strip + SVG size legend for incident classes

**Fire incidents tab — "Monthly fire incident trend per municipality" chart:**
- Filters: Municipality (dropdown, "All" default) + Year (dropdown, "All" default)
- X-axis: month (Jan–Dec), Y-axis: total burned area in στρέμματα
- Always shows seasonal pattern (burned area by month)

---

## Data coverage

- **Risk maps:** 2018-06-01 through 2026-07-03 (fire season only, ~May–October each year)
  - 1,442 raw JPG files in `data/raw/`
  - Known gaps: 2017 not scraped; 4 dates in July 2022 are 360×380 thumbnails (no calibration)
  - One uncalibrated image: `170624.jpg` (1187×1246) — needs a third template to process
- **Fire incidents:** 2020–2025, 58,110 clean rows

---

## Daily update workflow

The launchd scheduler is **unloaded** (macOS TCC blocks ~/Documents from background agents). Run manually:
```bash
cd /Users/iti-thermi/Documents/SideProject
./scripts/daily_update.sh
```
This fetches the last 5 days, extracts risk levels, commits new data, and pushes to GitHub.  
Streamlit Cloud auto-redeploys on push.

Output is appended to `data/daily_update.log` (gitignored).

---

## Known issues / pending work

1. **2017 maps not scraped** — scraping was started and killed (took too long). 2018–2026 done.
2. **`170624.jpg` uncalibrated** — size 1187×1246 doesn't match either template. Needs calibration.
3. **2025 prefecture granularity** — some 2025 records use prefecture-level `forestry_district` instead of actual district names. User said "I have a plan for this."
4. **Statistics on fire incidents tab** — partially done (burned area chart added). More stats TBD.

---

## Deployment

- **Streamlit Community Cloud** connected to `https://github.com/kkarys/greece-fire-risk-dashboard.git`, branch `main`, entry point `src/app.py`
- Auto-redeploys on every push to main
- Local: `streamlit run src/app.py` on port 8501

---

## Git log (recent)

```
7ded8f3 Fix graduated symbol thresholds: small ≤50, medium ≤200, large >200 στρ.
c71c96b 3-class graduated symbols for fire incidents + size legend
fdab229 Graduated symbol size for fire incident points by burned area
9d25b63 Rename chart to 'Monthly fire incident trend per municipality'
a69769d Replace district filter with municipality filter in burned area chart
a691024 Simplify burned area chart: remove view-by toggle and month filter
61b021d Replace burned area charts with single filterable chart
ac471b4 Add burned area trends charts to fire incidents tab
da8ce6c Add July 1 map and fix scraper to try previous month folder
7e79767 Add fire incident logs, map synthesis tab, and risk-colored boundary overlay
```
