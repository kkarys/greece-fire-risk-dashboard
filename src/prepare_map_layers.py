"""Convert the EGSA87 (EPSG:2100) boundary GeoJSONs in Boundaries/ into
lightweight WGS84 GeoJSONs suitable for an interactive web map.

The raw files are huge (1.5M+ coordinate points combined) and in a
projected CRS that Leaflet/folium can't use directly, so this:
  1. reprojects EPSG:2100 -> EPSG:4326 (lat/lon)
  2. simplifies geometry (topology-preserving) to cut point count drastically
  3. keeps only the name property, to minimize file size
"""

import json
from pathlib import Path

import pyproj
from shapely.geometry import shape, mapping
from shapely.ops import transform

BOUNDARIES_DIR = Path(__file__).resolve().parent.parent / "Boundaries"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"

_TRANSFORMER = pyproj.Transformer.from_crs("EPSG:2100", "EPSG:4326", always_xy=True)


def _reproject(geom):
    return transform(_TRANSFORMER.transform, geom)


def simplify_layer(input_path: Path, name_property: str, output_path: Path, tolerance_m: float = 80):
    data = json.loads(input_path.read_text(encoding="utf-8"))
    # simplify in the original projected (meters) CRS so tolerance is in meters
    out_features = []
    for f in data["features"]:
        geom = shape(f["geometry"]).simplify(tolerance_m, preserve_topology=True)
        geom = _reproject(geom)
        out_features.append(
            {
                "type": "Feature",
                "properties": {"name": f["properties"].get(name_property)},
                "geometry": mapping(geom),
            }
        )
    out = {"type": "FeatureCollection", "features": out_features}
    output_path.write_text(json.dumps(out, separators=(",", ":")))
    return len(out_features)


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    n = simplify_layer(
        BOUNDARIES_DIR / "Dasarxeia.geojson", "DASARXEIO", OUTPUT_DIR / "dasarxeia_map.geojson"
    )
    print(f"Dasarxeia: {n} features -> {(OUTPUT_DIR / 'dasarxeia_map.geojson').stat().st_size / 1e6:.1f} MB")

    n = simplify_layer(BOUNDARIES_DIR / "Dimoi.geojson", "LEKTIKO", OUTPUT_DIR / "dimoi_map.geojson")
    print(f"Dimoi: {n} features -> {(OUTPUT_DIR / 'dimoi_map.geojson').stat().st_size / 1e6:.1f} MB")
