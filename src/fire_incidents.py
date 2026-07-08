"""Merge the National Fire Service's yearly forest-fire incident logs
(tables/Dasikes_Pyrkagies_<year>.xlsx) into one normalized, cleaned dataset.

Each yearly file has slightly different columns/headers (extra leased-aircraft
columns from 2021 on, a different header row and a few renamed columns in
2025), so columns are matched by a normalized key rather than exact name.

Cleaning steps applied (each logged into a per-year report row):
  - add a globally unique `incident_id` (record_id is only unique per year)
  - drop records where end_date is before start_date (data-entry errors)
  - null out placeholder coordinates ("Not Found" / (0,0))
  - normalize prefecture name spelling (old vs. modern genitive forms)
"""

import re
from pathlib import Path

import pandas as pd

TABLES_DIR = Path(__file__).resolve().parent.parent / "tables"
CLEAN_OUTPUT_PATH = TABLES_DIR / "Dasikes_Pyrkagies_Merged_Clean.csv"
REPORT_OUTPUT_PATH = TABLES_DIR / "Dasikes_Pyrkagies_Cleaning_Report.csv"

# canonical_column -> normalized variant names seen across years
COLUMN_MAP = {
    "record_id": ["Α/Α ΕΓΓΡΑΦΗΣ"],
    "engage_id": ["Α/Α ENGAGE", "A/A ENGAGE"],
    "x_engage": ["X-ENGAGE"],
    "y_engage": ["Y-ENGAGE"],
    "service": ["Υπηρεσία"],
    "prefecture": ["Νομός"],
    "start_date": ["Ημερ/νία Έναρξης"],
    "start_time": ["Ώρα Έναρξης"],
    "end_date": ["Ημερ/νία Κατασβεσης"],
    "end_time": ["Ώρα Κατάσβεσης"],
    "forestry_district": ["Δασαρχείο"],
    "municipality": ["Δήμος"],
    "area": ["Περιοχή"],
    "incident_category": ["Κατηγορία Συμβάντος"],
    "address": ["Διεύθυνση"],
    "burned_forest": ["Δάση"],
    "burned_forest_land": ["Δασική Έκταση"],
    "burned_grove": ["Άλση"],
    "burned_grassland": ["Χορτ/κές Εκτάσεις"],
    "burned_reeds_marsh": ["Καλάμια - Βάλτοι"],
    "burned_agricultural": ["Γεωργικές Εκτάσεις"],
    "burned_crop_residue": ["Υπολλείματα Καλλιεργειών"],
    "burned_dump": ["Σκουπι-δότοποι", "Σκουπιδότοποι"],
    "personnel_fire_service": ["ΠΥΡΟΣ. ΣΩΜΑ"],
    "personnel_foot_teams": ["ΠΕΖΟΠΟΡΑ ΤΜΗΜΑΤΑ"],
    "personnel_volunteers": ["ΕΘΕΛΟ-ΝΤΕΣ", "ΕΘΕΛΟΝΤΕΣ"],
    "personnel_army": ["ΣΤΡΑΤΟΣ"],
    "personnel_other": ["ΑΛΛΕΣ ΔΥΝΑΜΕΙΣ"],
    "vehicles_fire": ["ΠΥΡΟΣ. ΟΧΗΜ."],
    "vehicles_municipal": ["ΟΧΗΜ. ΟΤΑ", "ΟΧΗΜ. ΥΠΗΡΕΣΙΑΚΑ"],
    "vehicles_water_tanker": ["ΒΥΤΙΟ- ΦΟΡΑ", "ΒΥΤΙΟΦΟΡΑ"],
    "vehicles_machinery": ["ΜΗΧΑΝΗ-ΜΑΤΑ", "ΜΗΧΑΝΗΜΑΤΑ"],
    "aircraft_helicopter": ["ΕΛΙΚΟ- ΠΤΕΡΑ", "ΕΛΙΚΟΠΤΕΡΑ"],
    "aircraft_cl415": ["Α/Φ CL415"],
    "aircraft_cl215": ["Α/Φ CL215"],
    "aircraft_pzl": ["Α/Φ PZL"],
    "aircraft_gru": ["Α/Φ GRU."],
    "aircraft_leased_helicopter": ["ΜΙΣΘ. ΕΛΙΚΟΠΤ."],
    "aircraft_leased_plane": ["ΜΙΣΘ. ΑΕΡΟΣΚ."],
    "resources_other_agency": ["ΑΛΛΩΝ ΦΟΡΕΩΝ"],
}

BURNED_AREA_COLUMNS = [
    "burned_forest",
    "burned_forest_land",
    "burned_grove",
    "burned_grassland",
    "burned_reeds_marsh",
    "burned_agricultural",
    "burned_crop_residue",
    "burned_dump",
]

# old (katharevousa) genitive -> modern genitive, matching the spelling
# convention already used by Boundaries/Dasarxeia.geojson
PREFECTURE_NORMALIZATION = {
    "ΑΡΓΟΛΙΔΟΣ": "ΑΡΓΟΛΙΔΑΣ",
    "ΛΕΥΚΑΔΟΣ": "ΛΕΥΚΑΔΑΣ",
    "ΠΡΕΒΕΖΗΣ": "ΠΡΕΒΕΖΑΣ",
    "ΦΩΚΙΔΟΣ": "ΦΩΚΙΔΑΣ",
    "ΚΕΦΑΛΛΟΝΙΑΣ": "ΚΕΦΑΛΛΗΝΙΑΣ",
}


def _normalize(name: str) -> str:
    return re.sub(r"[\s\-.]+", "", str(name)).upper()


_LOOKUP = {_normalize(variant): canonical for canonical, variants in COLUMN_MAP.items() for variant in variants}


def _rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {}
    for col in df.columns:
        canonical = _LOOKUP.get(_normalize(col))
        if canonical:
            renamed[col] = canonical
    return df.rename(columns=renamed)[[c for c in renamed.values()]]


def _load_year(path: Path, sheet_name, header_row: int, year: int) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=sheet_name, header=header_row)
    df = df.dropna(how="all")
    df = df[df["Α/Α ΕΓΓΡΑΦΗΣ"].notna()] if "Α/Α ΕΓΓΡΑΦΗΣ" in df.columns else df
    df = _rename_columns(df)
    df["source_year"] = year
    return df


def load_and_merge() -> pd.DataFrame:
    frames = [
        _load_year(TABLES_DIR / "Dasikes_Pyrkagies_2020.xlsx", "2020", 1, 2020),
        _load_year(TABLES_DIR / "Dasikes_Pyrkagies_2021.xlsx", "2021", 1, 2021),
        _load_year(TABLES_DIR / "Dasikes_Pyrkagies_2022.xlsx", "2022", 1, 2022),
        _load_year(TABLES_DIR / "Dasikes_Pyrkagies_2023.xlsx", "2023", 1, 2023),
        _load_year(TABLES_DIR / "Dasikes_Pyrkagies_2024.xlsx", "2024", 1, 2024),
        _load_year(TABLES_DIR / "Dasikes_Pyrkagies_2025.xlsx", "Sheet0", 3, 2025),
    ]
    merged = pd.concat(frames, ignore_index=True, sort=False)

    merged["start_date"] = pd.to_datetime(merged["start_date"], errors="coerce")
    merged["end_date"] = pd.to_datetime(merged["end_date"], errors="coerce")
    merged["burned_total"] = merged[BURNED_AREA_COLUMNS].sum(axis=1, skipna=True)

    return merged


def clean_and_report(merged: pd.DataFrame):
    """Apply cleaning steps, returning (clean_df, report_df).

    report_df has one row per (year, issue_type) with the affected count.
    """
    df = merged.copy()
    report_rows = []

    # 1. Globally unique incident id (record_id is only unique within a year)
    df["incident_id"] = df["source_year"].astype(str) + "-" + df["record_id"].astype("Int64").astype(str)
    dup_record_ids = df["record_id"].duplicated(keep=False).sum()
    if dup_record_ids:
        for year, count in df[df["record_id"].duplicated(keep=False)].groupby("source_year").size().items():
            report_rows.append(
                {
                    "year": year,
                    "issue_type": "record_id reused across years (kept, given unique incident_id)",
                    "affected_rows": count,
                }
            )

    # 2. Drop rows where end_date is before start_date (data-entry errors)
    bad_dates_mask = df["end_date"].notna() & (df["end_date"] < df["start_date"])
    for year, count in df[bad_dates_mask].groupby("source_year").size().items():
        report_rows.append(
            {"year": year, "issue_type": "end_date before start_date (row dropped)", "affected_rows": count}
        )
    df = df[~bad_dates_mask].copy()

    # 3. Null out placeholder coordinates
    df["x_engage"] = pd.to_numeric(df["x_engage"], errors="coerce")
    df["y_engage"] = pd.to_numeric(df["y_engage"], errors="coerce")
    placeholder_mask = (df["x_engage"] == 0) & (df["y_engage"] == 0)
    for year, count in df[placeholder_mask].groupby("source_year").size().items():
        report_rows.append(
            {"year": year, "issue_type": "placeholder (0,0)/Not Found coordinates (nulled)", "affected_rows": count}
        )
    df.loc[placeholder_mask, ["x_engage", "y_engage"]] = pd.NA

    # 4. Normalize prefecture spelling
    variant_mask = df["prefecture"].isin(PREFECTURE_NORMALIZATION.keys())
    for year, count in df[variant_mask].groupby("source_year").size().items():
        report_rows.append(
            {"year": year, "issue_type": "prefecture spelling normalized", "affected_rows": count}
        )
    df["prefecture"] = df["prefecture"].replace(PREFECTURE_NORMALIZATION)

    report_df = pd.DataFrame(report_rows).sort_values(["year", "issue_type"]).reset_index(drop=True)
    return df, report_df


if __name__ == "__main__":
    merged = load_and_merge()
    clean, report = clean_and_report(merged)

    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    clean.to_csv(CLEAN_OUTPUT_PATH, index=False)
    report.to_csv(REPORT_OUTPUT_PATH, index=False)

    print(f"Merged {len(merged)} raw incidents -> {len(clean)} clean incidents")
    print(f"Clean data -> {CLEAN_OUTPUT_PATH}")
    print(f"Cleaning report -> {REPORT_OUTPUT_PATH}")
    print()
    print(report.to_string(index=False))
