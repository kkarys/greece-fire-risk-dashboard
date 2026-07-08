"""Download daily fire-risk map images from the Greek Civil Protection archive.

The agency has changed both file format and URL layout over time. Known
layouts seen on https://civilprotection.gov.gr/arxeio-imerision-xartwn :
    - .../sites/default/files/YYYY-MM/YYMMDD.{jpg,jpeg,png}   (2023 onward)
    - .../sites/default/files/YYMMDD.{jpg,jpeg,png,gif}        (2022 and earlier, flat path)
    - .../sites/default/files/YYMMDD_N.{jpg,jpeg,png,gif}      (flat path, Drupal de-dupe suffix;
                                                                 seen as _0 and _1 in the 2017 archive
                                                                 when a file was re-uploaded)

We try each known layout/extension combo and take the first that resolves.
"""

import datetime as dt
import time
from pathlib import Path
from typing import Optional

import requests

BASE_URL = "https://civilprotection.gov.gr/sites/default/files"
KNOWN_EXTENSIONS = ["jpg", "jpeg", "png"]
FLAT_EXTENSIONS = ["jpg", "jpeg", "png", "gif"]
DEDUPE_SUFFIXES = range(0, 4)  # observed _0 and _1 in the wild; a couple extra for safety margin
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
REQUEST_TIMEOUT = 15
REQUEST_DELAY_SECONDS = 1.0  # be polite to the agency's server


def build_candidate_urls(date: dt.date) -> list:
    yymmdd = date.strftime("%y%m%d")
    yyyy_mm = date.strftime("%Y-%m")
    # The agency sometimes uploads a map to the previous month's folder (e.g.
    # the July 1 map lands under 2026-06/). Try both current and previous month.
    prev_month = (date.replace(day=1) - dt.timedelta(days=1)).strftime("%Y-%m")
    urls = []
    for ext in KNOWN_EXTENSIONS:
        urls.append((f"{BASE_URL}/{yyyy_mm}/{yymmdd}.{ext}", ext))  # 2023 onward, current month
        urls.append((f"{BASE_URL}/{prev_month}/{yymmdd}.{ext}", ext))  # same layout, prev month folder
    for ext in FLAT_EXTENSIONS:
        urls.append((f"{BASE_URL}/{yymmdd}.{ext}", ext))  # 2022 and earlier, flat path
    for ext in FLAT_EXTENSIONS:
        for n in DEDUPE_SUFFIXES:
            urls.append((f"{BASE_URL}/{yymmdd}_{n}.{ext}", ext))  # Drupal de-dupe suffix, flat path
    return urls


def download_map_for_date(date: dt.date, dest_dir: Path = RAW_DIR, session: Optional[requests.Session] = None) -> Optional[Path]:
    """Try each known URL layout/extension for the given date; save the first
    that returns 200. Returns the saved path, or None if nothing was found."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    sess = session or requests.Session()

    for url, ext in build_candidate_urls(date):
        out_path = dest_dir / f"{date.strftime('%y%m%d')}.{ext}"
        if out_path.exists():
            return out_path
        resp = sess.get(url, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image/"):
            out_path.write_bytes(resp.content)
            return out_path
        time.sleep(REQUEST_DELAY_SECONDS)
    return None


def download_range(start: dt.date, end: dt.date, dest_dir: Path = RAW_DIR) -> dict:
    """Download every date in [start, end]. Returns {date: path_or_None}."""
    sess = requests.Session()
    results = {}
    current = start
    while current <= end:
        results[current] = download_map_for_date(current, dest_dir, sess)
        current += dt.timedelta(days=1)
    return results


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: python scraper.py YYYY-MM-DD YYYY-MM-DD")
        sys.exit(1)
    start = dt.date.fromisoformat(sys.argv[1])
    end = dt.date.fromisoformat(sys.argv[2])
    results = download_range(start, end)
    found = {d: p for d, p in results.items() if p}
    missing = [d for d, p in results.items() if not p]
    print(f"Downloaded {len(found)}/{len(results)}")
    if missing:
        print("Missing dates:", missing)
