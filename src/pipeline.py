"""Run risk extraction over every downloaded map and maintain the dataset
in data/processed/risk_history.csv (one row per district per date)."""

import csv
import datetime as dt
from pathlib import Path

from calibration import CalibrationMismatch
from risk_extraction import extract_risk_levels

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
PROCESSED_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "risk_history.csv"
FIELDNAMES = ["date", "district", "risk_level", "risk_name", "confidence_ok"]


def _parse_date_from_filename(path: Path) -> dt.date:
    yymmdd = path.stem
    return dt.datetime.strptime(yymmdd, "%y%m%d").date()


def _already_processed_dates() -> set:
    if not PROCESSED_PATH.exists():
        return set()
    with PROCESSED_PATH.open(newline="", encoding="utf-8") as f:
        return {row["date"] for row in csv.DictReader(f)}


def process_new_images() -> int:
    """Extract risk levels for any raw image not yet in the processed dataset.
    Returns the number of dates newly processed."""
    PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
    done_dates = _already_processed_dates()
    image_paths = sorted(p for p in RAW_DIR.glob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"})

    new_rows = []
    processed_count = 0
    for path in image_paths:
        date = _parse_date_from_filename(path)
        if date.isoformat() in done_dates:
            continue
        try:
            districts = extract_risk_levels(path)
        except CalibrationMismatch as e:
            print(f"Skipping {path.name}: {e}")
            continue
        for d in districts:
            new_rows.append({"date": date.isoformat(), **d})
        processed_count += 1

    if new_rows:
        write_header = not PROCESSED_PATH.exists()
        with PROCESSED_PATH.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            if write_header:
                writer.writeheader()
            writer.writerows(new_rows)

    return processed_count


if __name__ == "__main__":
    n = process_new_images()
    print(f"Processed {n} new date(s) into {PROCESSED_PATH}")
