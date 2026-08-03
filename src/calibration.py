"""Geo-calibration constants mapping the Dasarxeia.geojson (EPSG:2100) to
pixel coordinates of the Civil Protection daily fire-risk map JPGs.

The agency has used more than one map template/resolution over the years.
Each template is calibrated independently (same method: render district
boundary lines from the GeoJSON, register them onto the dark-pixel edges
detected in a sample JPG of that template) and selected by image size.
"""

# Bounding box (EGSA87 / EPSG:2100 meters) of the reference render, with 4% padding,
# and the px-per-meter scale used when rendering it to a 1600px-wide reference image.
# Shared across all templates since it's just an intermediate reference frame.
GEO_MIN_X = 67865.6016
GEO_MIN_Y = 3819855.01
GEO_MAX_X = 1044113.91
GEO_MAX_Y = 4654978.26
REF_SCALE = 0.0016389272990986452  # px (in 1600-wide reference render) per meter

# Per-template affine transform from reference-render pixels to JPG pixels,
# keyed by (width, height) of that template's images.
TEMPLATES = {
    (1384, 1453): {  # 2023 onward
        "scale": 0.8877435897435897,
        "tx": -26.0,
        "ty": 141.0,
    },
    (830, 872): {  # 2022 and earlier
        "scale": 0.5327586206896552,
        "tx": -15.172413793103452,
        "ty": 84.82758620689654,
    },
    (767, 805): {  # 2017 archive (GIF format)
        "scale": 0.4960822350398015,
        "tx": -11.275010985196305,
        "ty": 61.42967209728422,
        # This era's map generator used a visibly different (dimmer) palette;
        # sampled directly from the legend swatches in a reference image.
        "legend_colors": {
            1: (160, 224, 128),
            2: (166, 202, 240),
            3: (255, 255, 0),
            4: (224, 160, 0),
            5: (255, 0, 0),
        },
    },
    (1187, 1246): {  # one-off 2017 template (170624.jpg)
        "scale": 0.7754670777485281,
        "tx": -30.181826568189216,
        "ty": 92.67461634443441,
        # Level 1/3/4/5 sampled from this image's legend swatches (level 1's
        # swatch matches its actual district fill exactly). Level 2's swatch
        # reads (201,195,255) but every level-2 district fill actually samples
        # as (174,165,254) -- a real, consistent mismatch between this map's
        # legend box and its fill layer -- so level 2 uses the fill color.
        "legend_colors": {
            1: (166, 255, 165),
            2: (174, 165, 254),
            3: (255, 255, 0),
            4: (255, 173, 1),
            5: (254, 0, 0),
        },
    },
}


class CalibrationMismatch(Exception):
    """Raised when a downloaded map image doesn't match any calibrated template."""


def get_template(size):
    template = TEMPLATES.get(tuple(size))
    if template is None:
        raise CalibrationMismatch(
            f"Image size {size} doesn't match any calibrated template "
            f"{list(TEMPLATES.keys())}; the agency may have changed the map "
            "template. Recalibration needed."
        )
    return template


def geo_to_pixel(x: float, y: float, template: dict):
    """Project EGSA87 (EPSG:2100) meters to JPG pixel coordinates for the given template."""
    rx = (x - GEO_MIN_X) * REF_SCALE
    ry = (GEO_MAX_Y - y) * REF_SCALE
    return rx * template["scale"] + template["tx"], ry * template["scale"] + template["ty"]
