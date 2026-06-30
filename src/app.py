"""Streamlit dashboard for the Greek Civil Protection fire-risk archive."""

import calendar
import datetime as dt
import json
from pathlib import Path

import altair as alt
import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
PROCESSED_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "risk_history.csv"
FIRE_INCIDENTS_PATH = Path(__file__).resolve().parent.parent / "tables" / "Dasikes_Pyrkagies_Merged_Clean.csv"
FIRE_INCIDENTS_REPORT_PATH = Path(__file__).resolve().parent.parent / "tables" / "Dasikes_Pyrkagies_Cleaning_Report.csv"
DASARXEIA_MAP_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "dasarxeia_map.geojson"
DIMOI_MAP_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "dimoi_map.geojson"

RISK_COLORS = {
    1: "#a7fdaa",
    2: "#a7caf2",
    3: "#ffff00",
    4: "#fda502",
    5: "#fd0002",
}
RISK_NAMES = {
    1: "ΧΑΜΗΛΗ (Low)",
    2: "ΜΕΣΗ (Medium)",
    3: "ΥΨΗΛΗ (High)",
    4: "ΠΟΛΥ ΥΨΗΛΗ (Very High)",
    5: "ΣΥΝΑΓΕΡΜΟΣ (Alarm)",
}

st.set_page_config(page_title="Greece Fire Risk Dashboard", layout="wide")


@st.cache_data
def load_data(_mtime: float):
    df = pd.read_csv(PROCESSED_PATH, parse_dates=["date"])
    return df


@st.cache_data
def load_fire_incidents(_mtime: float):
    df = pd.read_csv(FIRE_INCIDENTS_PATH, low_memory=False, parse_dates=["start_date", "end_date"])
    return df


@st.cache_data
def load_fire_incidents_report(_mtime: float):
    return pd.read_csv(FIRE_INCIDENTS_REPORT_PATH)


@st.cache_data
def load_geojson(path: Path, _mtime: float):
    return json.loads(path.read_text(encoding="utf-8"))


def _district_risk_colors(risk_mtime: float, year: int, month: int, day: int = None):
    """Risk level per district mapped to RISK_COLORS. If day is None, uses the
    average risk level across the whole month; otherwise uses that exact date."""
    risk_df = load_data(risk_mtime)
    if day is None:
        scoped = risk_df[(risk_df["date"].dt.year == year) & (risk_df["date"].dt.month == month)]
        level_per_district = scoped.groupby("district")["risk_level"].mean().round().clip(1, 5).astype(int)
    else:
        scoped = risk_df[
            (risk_df["date"].dt.year == year)
            & (risk_df["date"].dt.month == month)
            & (risk_df["date"].dt.day == day)
        ]
        level_per_district = scoped.set_index("district")["risk_level"].dropna().astype(int)
    return {district: RISK_COLORS[level] for district, level in level_per_district.items()}


def _matching_fire_incidents(incidents_mtime: float, year: int, month: int, day: int = None):
    """Incidents whose start_date falls in the given year/month(/day), with valid coordinates."""
    incidents_df = load_fire_incidents(incidents_mtime)
    scoped = incidents_df[
        (incidents_df["start_date"].dt.year == year) & (incidents_df["start_date"].dt.month == month)
    ]
    if day is not None:
        scoped = scoped[scoped["start_date"].dt.day == day]
    return scoped.dropna(subset=["x_engage", "y_engage"])


def build_synthesis_map(
    _dasarxeia_mtime: float,
    _dimoi_mtime: float,
    show_dasarxeia: bool,
    show_dimoi: bool,
    risk_mtime: float = None,
    risk_year: int = None,
    risk_month: int = None,
    risk_day: int = None,
    incidents_mtime: float = None,
    show_incidents: bool = False,
):
    m = folium.Map(location=[38.5, 23.7], zoom_start=7, tiles="CartoDB positron")

    if show_dasarxeia:
        dasarxeia_geo = load_geojson(DASARXEIA_MAP_PATH, _dasarxeia_mtime)
        district_colors = (
            _district_risk_colors(risk_mtime, risk_year, risk_month, risk_day)
            if risk_mtime is not None
            else {}
        )

        def dasarxeia_style(feature):
            color = district_colors.get(feature["properties"]["name"])
            return {
                "weight": 0,
                "fillOpacity": 0.6 if color else 0,
                "fillColor": color or "#e31a1c",
            }

        folium.GeoJson(
            dasarxeia_geo,
            name="Δασαρχεία (Forestry districts)",
            style_function=dasarxeia_style,
            tooltip=folium.GeoJsonTooltip(fields=["name"], aliases=["Δασαρχείο:"]),
        ).add_to(m)

    if show_dimoi:
        dimoi_geo = load_geojson(DIMOI_MAP_PATH, _dimoi_mtime)
        folium.GeoJson(
            dimoi_geo,
            name="Δήμοι (Municipalities)",
            style_function=lambda f: {"color": "#1f78b4", "weight": 1, "fillOpacity": 0},
            tooltip=folium.GeoJsonTooltip(fields=["name"], aliases=["Δήμος:"]),
        ).add_to(m)

    if show_incidents and incidents_mtime is not None:
        matched = _matching_fire_incidents(incidents_mtime, risk_year, risk_month, risk_day)
        incidents_layer = folium.FeatureGroup(name=f"Fire incidents ({len(matched)})")
        for _, row in matched.iterrows():
            popup_html = (
                f"<b>{row['start_date'].date()}</b> {row.get('start_time', '')}<br>"
                f"{row.get('service', '')}<br>"
                f"{row.get('prefecture', '')} — {row.get('area', '')}<br>"
                f"Burned: {row.get('burned_total', 0):.2f} στρέμματα"
            )
            folium.CircleMarker(
                location=[row["y_engage"], row["x_engage"]],
                radius=5,
                color="#000000",
                weight=1,
                fillColor="#ff6f00",
                fillOpacity=0.85,
                popup=folium.Popup(popup_html, max_width=250),
            ).add_to(incidents_layer)
        incidents_layer.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    return m


def risk_distribution_df(series):
    """Build a count-per-risk-level dataframe covering all 5 levels (0 where absent)."""
    counts = series.value_counts().reindex([1, 2, 3, 4, 5], fill_value=0)
    return pd.DataFrame(
        {
            "risk_level": counts.index,
            "count": counts.values,
            "risk_name": [RISK_NAMES[lvl] for lvl in counts.index],
        }
    )


def image_path_for_date(date: dt.date):
    stem = date.strftime("%y%m%d")
    for ext in ("jpg", "jpeg", "png"):
        p = RAW_DIR / f"{stem}.{ext}"
        if p.exists():
            return p
    return None


df = load_data(PROCESSED_PATH.stat().st_mtime)
available_dates = sorted(df["date"].dt.date.unique())
available_months = sorted({(d.year, d.month) for d in available_dates}, reverse=True)

st.title("🔥 Greece Daily Fire Risk Dashboard")
st.caption("Source: Greek Ministry of Climate Crisis & Civil Protection — daily risk prediction maps")

tab_gallery, tab_trends, tab_overview, tab_incidents, tab_map = st.tabs(
    ["Monthly map gallery", "District trends", "Overview dashboard", "Fire incidents", "Map synthesis"]
)

with tab_gallery:
    years = sorted({y for y, m in available_months}, reverse=True)
    col_year, col_month = st.columns(2)
    with col_year:
        sel_year = st.selectbox("Year", years)
    months_for_year = sorted({m for y, m in available_months if y == sel_year})
    month_options = {m: calendar.month_name[m] for m in months_for_year}
    with col_month:
        sel_month = st.selectbox(
            "Month", list(month_options.keys()), format_func=lambda m: month_options[m]
        )

    month_dates = [d for d in available_dates if d.year == sel_year and d.month == sel_month]
    st.write(f"{len(month_dates)} map(s) available for {calendar.month_name[sel_month]} {sel_year}")

    cols_per_row = 5
    for i in range(0, len(month_dates), cols_per_row):
        row_dates = month_dates[i : i + cols_per_row]
        cols = st.columns(cols_per_row)
        for col, date in zip(cols, row_dates):
            path = image_path_for_date(date)
            with col:
                if path:
                    st.image(str(path), caption=date.isoformat(), width='stretch')
                else:
                    st.write(f"{date.isoformat()} (missing)")

with tab_trends:
    districts = sorted(df["district"].unique())
    selected_district = st.selectbox("District (Δασαρχείο)", districts)

    d_df = df[df["district"] == selected_district].sort_values("date")
    d_df = d_df.dropna(subset=["risk_level"])

    chart = (
        alt.Chart(d_df)
        .mark_point(size=120, filled=True)
        .encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("risk_level:Q", title="Risk level", scale=alt.Scale(domain=[0.5, 5.5])),
            color=alt.Color(
                "risk_level:N",
                scale=alt.Scale(
                    domain=list(RISK_COLORS.keys()), range=list(RISK_COLORS.values())
                ),
                legend=alt.Legend(title="Risk level"),
            ),
            tooltip=["date:T", "risk_name", "confidence_ok"],
        )
        .properties(height=350)
    )
    line = (
        alt.Chart(d_df)
        .mark_line(opacity=0.3)
        .encode(x="date:T", y="risk_level:Q")
    )
    st.altair_chart(line + chart, use_container_width=True)

    low_conf_count = (d_df["confidence_ok"] == False).sum()  # noqa: E712
    if low_conf_count:
        st.caption(f"⚠️ {low_conf_count} low-confidence reading(s) for this district — color sample landed near a boundary.")

    st.subheader(f"Risk level distribution for {selected_district}")
    dist_df = risk_distribution_df(d_df["risk_level"])
    district_bar = (
        alt.Chart(dist_df)
        .mark_bar()
        .encode(
            x=alt.X("risk_name:N", sort=None, title=None),
            y=alt.Y("count:Q", title="Number of days"),
            color=alt.Color(
                "risk_level:N",
                scale=alt.Scale(domain=list(RISK_COLORS.keys()), range=list(RISK_COLORS.values())),
                legend=None,
            ),
        )
        .properties(height=250)
    )
    st.caption(f"Across all {len(d_df)} day(s) on record for this district")
    st.altair_chart(district_bar, use_container_width=True)

with tab_overview:
    st.subheader("Risk level distribution across all districts")
    latest_date = max(available_dates)
    latest_df = df[df["date"].dt.date == latest_date]
    dist_df = risk_distribution_df(latest_df["risk_level"])
    bar = (
        alt.Chart(dist_df)
        .mark_bar()
        .encode(
            x=alt.X("risk_name:N", sort=None, title=None),
            y=alt.Y("count:Q"),
            color=alt.Color(
                "risk_level:N",
                scale=alt.Scale(domain=list(RISK_COLORS.keys()), range=list(RISK_COLORS.values())),
                legend=None,
            ),
        )
        .properties(height=250)
    )
    st.caption(f"As of {latest_date.isoformat()}")
    st.altair_chart(bar, use_container_width=True)

    st.subheader("Risk level distribution across all districts and all years")
    alltime_df = risk_distribution_df(df["risk_level"])
    alltime_bar = (
        alt.Chart(alltime_df)
        .mark_bar()
        .encode(
            x=alt.X("risk_name:N", sort=None, title=None),
            y=alt.Y("count:Q", title="Number of district-days"),
            color=alt.Color(
                "risk_level:N",
                scale=alt.Scale(domain=list(RISK_COLORS.keys()), range=list(RISK_COLORS.values())),
                legend=None,
            ),
        )
        .properties(height=250)
    )
    st.caption(
        f"Across {len(available_dates)} day(s) on record, "
        f"from {available_dates[0].isoformat()} to {available_dates[-1].isoformat()}"
    )
    st.altair_chart(alltime_bar, use_container_width=True)

with tab_incidents:
    st.subheader("National Fire Service incident log (merged 2020-2025)")
    incidents_df = load_fire_incidents(FIRE_INCIDENTS_PATH.stat().st_mtime)

    years = sorted(incidents_df["source_year"].unique())
    selected_years = st.multiselect("Year(s)", years, default=years)
    filtered = incidents_df[incidents_df["source_year"].isin(selected_years)]

    col1, col2, col3 = st.columns(3)
    col1.metric("Incidents", f"{len(filtered):,}")
    col2.metric("Total burned area", f"{filtered['burned_total'].sum():,.0f} στρέμματα")
    col3.metric(
        "Date range",
        f"{filtered['start_date'].min().date()} – {filtered['start_date'].max().date()}"
        if len(filtered)
        else "—",
    )

    incidents_per_year = filtered["source_year"].value_counts().sort_index().reset_index()
    incidents_per_year.columns = ["year", "incidents"]
    year_bar = (
        alt.Chart(incidents_per_year)
        .mark_bar()
        .encode(
            x=alt.X("year:O", title=None),
            y=alt.Y("incidents:Q"),
            tooltip=["year", "incidents"],
        )
        .properties(height=250)
    )
    st.altair_chart(year_bar, use_container_width=True)

    st.subheader("Incident records")
    display_columns = [
        "start_date",
        "start_time",
        "end_date",
        "end_time",
        "service",
        "prefecture",
        "municipality",
        "area",
        "forestry_district",
        "burned_total",
        "source_year",
    ]
    st.dataframe(
        filtered[display_columns].sort_values("start_date", ascending=False),
        use_container_width=True,
        height=500,
    )

    with st.expander("Data quality / cleaning report"):
        st.caption(
            "Issues found and corrected while merging the yearly source files "
            "(tables/Dasikes_Pyrkagies_<year>.xlsx) into one dataset."
        )
        report_df = load_fire_incidents_report(FIRE_INCIDENTS_REPORT_PATH.stat().st_mtime)
        st.dataframe(report_df, use_container_width=True, hide_index=True)

@st.fragment
def render_map_synthesis_tab():
    st.subheader("Boundary layers")
    st.caption(
        "Δασαρχεία (forestry district) boundaries — used for the daily fire-risk maps — "
        "and Δήμοι (municipal/administrative) boundaries, overlaid on the same map."
    )

    col1, col2, col_incidents = st.columns(3)
    show_dasarxeia = col1.checkbox("Show Δασαρχεία (forestry districts)", value=True)
    show_dimoi = col2.checkbox("Show Δήμοι (municipalities)", value=True)
    show_incidents = col_incidents.checkbox(
        "Show fire incidents matching the date filter below", value=True
    )

    st.caption(
        "Color the Δασαρχεία layer by that district's fire-risk level for a "
        "specific day, or by the average risk level across a whole month."
    )
    map_years = sorted({y for y, m in available_months}, reverse=True)
    col3, col4, col5 = st.columns(3)

    # Guard against a stale session_state value (from a previous year/month
    # selection) no longer being a valid option, which would otherwise raise.
    if st.session_state.get("map_year") not in map_years:
        st.session_state["map_year"] = map_years[0]
    map_sel_year = col3.selectbox("Year", map_years, key="map_year")

    map_months_for_year = sorted({m for y, m in available_months if y == map_sel_year})
    map_month_options = {m: calendar.month_name[m] for m in map_months_for_year}
    if st.session_state.get("map_month") not in map_months_for_year:
        st.session_state["map_month"] = map_months_for_year[0]
    map_sel_month = col4.selectbox(
        "Month", list(map_month_options.keys()), format_func=lambda m: map_month_options[m], key="map_month"
    )

    days_in_month = sorted(
        d.day for d in available_dates if d.year == map_sel_year and d.month == map_sel_month
    )
    day_options = ["Whole month (average)"] + days_in_month
    if st.session_state.get("map_day") not in day_options:
        st.session_state["map_day"] = day_options[0]
    map_sel_day_choice = col5.selectbox("Day", day_options, key="map_day")
    map_sel_day = None if map_sel_day_choice == "Whole month (average)" else map_sel_day_choice

    synthesis_map = build_synthesis_map(
        DASARXEIA_MAP_PATH.stat().st_mtime,
        DIMOI_MAP_PATH.stat().st_mtime,
        show_dasarxeia,
        show_dimoi,
        risk_mtime=PROCESSED_PATH.stat().st_mtime,
        risk_year=map_sel_year,
        risk_month=map_sel_month,
        risk_day=map_sel_day,
        incidents_mtime=FIRE_INCIDENTS_PATH.stat().st_mtime,
        show_incidents=show_incidents,
    )
    st_folium(
        synthesis_map,
        use_container_width=True,
        height=650,
        returned_objects=[],
        key="synthesis_map",
    )

    legend_cols = st.columns(5)
    for col, level in zip(legend_cols, [1, 2, 3, 4, 5]):
        col.markdown(
            f"<div style='background:{RISK_COLORS[level]};padding:4px;border-radius:4px;"
            f"text-align:center;font-size:0.8em'>{RISK_NAMES[level]}</div>",
            unsafe_allow_html=True,
        )


with tab_map:
    render_map_synthesis_tab()
