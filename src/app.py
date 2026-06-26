"""Streamlit dashboard for the Greek Civil Protection fire-risk archive."""

import calendar
import datetime as dt
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
PROCESSED_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "risk_history.csv"

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

tab_gallery, tab_trends, tab_overview = st.tabs(
    ["Monthly map gallery", "District trends", "Overview dashboard"]
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
