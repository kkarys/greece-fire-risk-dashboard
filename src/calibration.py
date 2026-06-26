"""Geo-calibration constants mapping the Dasarxeia.geojson (EPSG:2100) to
pixel coordinates of the Civil Protection daily fire-risk map JPGs.

Fitted once against Images/250809.jpg by registering district boundary
lines (rendered from the GeoJSON) onto the dark-pixel edges detected in
the JPG. See scripts/fit_calibration.py to redo this if the agency changes
the map template.
"""

EXPECTED_IMAGE_SIZE = (1384, 1453)  # (width, height) of calibration source image

# Bounding box (EGSA87 / EPSG:2100 meters) of the reference render, with 4% padding,
# and the px-per-meter scale used when rendering it to a 1600px-wide reference image.
GEO_MIN_X = 67865.6016
GEO_MIN_Y = 3819855.01
GEO_MAX_X = 1044113.91
GEO_MAX_Y = 4654978.26
REF_SCALE = 0.0016389272990986452  # px (in 1600-wide reference render) per meter

# Affine transform from reference-render pixels to actual JPG pixels.
TRANSFORM_SCALE = 0.8877435897435897
TRANSFORM_TX = -26.0
TRANSFORM_TY = 141.0


class CalibrationMismatch(Exception):
    """Raised when a downloaded map image doesn't match the calibrated template."""


def check_image_size(size) -> None:
    if size != EXPECTED_IMAGE_SIZE:
        raise CalibrationMismatch(
            f"Image size {size} != expected {EXPECTED_IMAGE_SIZE}; "
            "the agency may have changed the map template. Recalibration needed."
        )


def geo_to_pixel(x: float, y: float):
    """Project EGSA87 (EPSG:2100) meters to JPG pixel coordinates."""
    rx = (x - GEO_MIN_X) * REF_SCALE
    ry = (GEO_MAX_Y - y) * REF_SCALE
    return rx * TRANSFORM_SCALE + TRANSFORM_TX, ry * TRANSFORM_SCALE + TRANSFORM_TY
