"""Extract per-district fire-risk levels from a daily Civil Protection map image."""

import json
from pathlib import Path
from typing import Union

import numpy as np
from PIL import Image
from shapely.geometry import shape

from calibration import geo_to_pixel, get_template

BOUNDARIES_PATH = Path(__file__).resolve().parent.parent / "Boundaries" / "Dasarxeia.geojson"

# RGB reference colors sampled from the map's own legend swatches.
LEGEND_COLORS = {
    1: (167, 253, 170),  # ΧΑΜΗΛΗ (low)
    2: (167, 200, 242),  # ΜΕΣΗ (medium)
    3: (255, 255, 0),    # ΥΨΗΛΗ (high)
    4: (253, 172, 2),    # ΠΟΛΥ ΥΨΗΛΗ (very high)
    5: (253, 0, 2),       # ΚΑΤΑΣΤΑΣΗ ΣΥΝΑΓΕΡΜΟΥ (alarm)
}

LEGEND_NAMES = {
    1: "ΧΑΜΗΛΗ",
    2: "ΜΕΣΗ",
    3: "ΥΨΗΛΗ",
    4: "ΠΟΛΥ ΥΨΗΛΗ",
    5: "ΚΑΤΑΣΤΑΣΗ ΣΥΝΑΓΕΡΜΟΥ",
}

# Distance above which a color match is considered unreliable (e.g. sample
# point landed on a boundary line, label text, or anti-aliasing).
LOW_CONFIDENCE_THRESHOLD = 200


def _load_districts():
    data = json.loads(BOUNDARIES_PATH.read_text(encoding="utf-8"))
    return [(f["properties"]["DASARXEIO"], shape(f["geometry"])) for f in data["features"]]


def _classify_color(rgb):
    best_level, best_dist = None, float("inf")
    for level, ref_rgb in LEGEND_COLORS.items():
        dist = sum((a - b) ** 2 for a, b in zip(rgb, ref_rgb))
        if dist < best_dist:
            best_dist, best_level = dist, level
    return best_level, best_dist


def _sample_district_color(arr, px, py, h, w, radius=4):
    """Median color over a small patch, falling back to a larger radius
    if the patch is dominated by near-black boundary-line pixels."""
    for r in (radius, radius * 2, radius * 4):
        y0, y1 = max(0, py - r), min(h, py + r + 1)
        x0, x1 = max(0, px - r), min(w, px + r + 1)
        patch = arr[y0:y1, x0:x1].reshape(-1, 3)
        # drop near-black (boundary lines/text) and near-white (gaps) pixels
        brightness = patch.sum(axis=1)
        keep = (brightness > 60) & (brightness < 720)
        candidate = patch[keep] if keep.any() else patch
        rgb = np.median(candidate, axis=0)
        level, dist = _classify_color(rgb)
        if dist <= LOW_CONFIDENCE_THRESHOLD:
            return rgb, level, dist
    return rgb, level, dist  # best effort after exhausting radii


def extract_risk_levels(image_path: Union[str, Path]) -> list:
    """Return a list of {district, risk_level, risk_name, confidence_ok} dicts."""
    image_path = Path(image_path)
    im = Image.open(image_path).convert("RGB")
    template = get_template(im.size)
    arr = np.array(im)
    h, w, _ = arr.shape

    results = []
    for name, geom in _load_districts():
        rp = geom.representative_point()
        px, py = geo_to_pixel(rp.x, rp.y, template)
        px, py = int(round(px)), int(round(py))
        if not (0 <= px < w and 0 <= py < h):
            results.append(
                {"district": name, "risk_level": None, "risk_name": None, "confidence_ok": False}
            )
            continue
        rgb, level, dist = _sample_district_color(arr, px, py, h, w)
        results.append(
            {
                "district": name,
                "risk_level": level,
                "risk_name": LEGEND_NAMES[level],
                "confidence_ok": dist <= LOW_CONFIDENCE_THRESHOLD,
            }
        )
    return results


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "../Images/250809.jpg"
    rows = extract_risk_levels(path)
    low_conf = [r for r in rows if not r["confidence_ok"]]
    print(f"Extracted {len(rows)} districts, {len(low_conf)} low-confidence")
    for r in low_conf:
        print("  low-confidence:", r)
