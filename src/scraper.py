"""Download daily fire-risk map images from the Greek Civil Protection archive.

The agency has changed both file format and URL layout over time. Known
layouts seen on https://civilprotection.gov.gr/arxeio-imerision-xartwn :
    - .../sites/default/files/YYYY-MM/YYMMDD.{jpg,jpeg,png}   (2023 onward)
    - .../sites/default/files/YYMMDD.{jpg,jpeg,png}            (2022 and earlier, flat path)
    - .../sites/default/files/YYMMDD_0.gif                     (very old archive, ~2005-2008)

We try each known layout/extension combo and take the first that resolves.
"""

import datetime as dt
import time
from pathlib import Path
from typing import Optional

import requests

BASE_URL = "https://civilprotection.gov.gr/sites/default/files"
KNOWN_EXTENSIONS = ["jpg", "jpeg", "png"]
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
REQUEST_TIMEOUT = 15
REQUEST_DELAY_SECONDS = 1.0  # be polite to the agency's server


def build_candidate_urls(date: dt.date) -> list:
    yymmdd = date.strftime("%y%m%d")
    yyyy_mm = date.strftime("%Y-%m")
    urls = []
    for ext in KNOWN_EXTENSIONS:
        urls.append((f"{BASE_URL}/{yyyy_mm}/{yymmdd}.{ext}", ext))  # 2023 onward
        urls.append((f"{BASE_URL}/{yymmdd}.{ext}", ext))  # 2022 and earlier, flat path
    urls.append((f"{BASE_URL}/{yymmdd}_0.gif", "gif"))  # very old archive (~2005-2008)
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
