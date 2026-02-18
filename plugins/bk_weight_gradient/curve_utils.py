# SPDX-License-Identifier: GPL-2.0-or-later

import bpy


# ---------------------------------------------------------------------------
# Math curve functions
# ---------------------------------------------------------------------------

def curve_linear(t):
    return t

def curve_ease_in(t):
    return t * t

def curve_ease_out(t):
    return 1.0 - (1.0 - t) * (1.0 - t)

def curve_ease_in_out(t):
    return 3.0 * t * t - 2.0 * t * t * t

def curve_sharp(t):
    return t ** 0.5

def curve_custom_power(t, power):
    return t ** power


CURVE_FUNCS = {
    'LINEAR': curve_linear,
    'EASE_IN': curve_ease_in,
    'EASE_OUT': curve_ease_out,
    'EASE_IN_OUT': curve_ease_in_out,
    'SHARP': curve_sharp,
}


# ---------------------------------------------------------------------------
# Custom curve brush helpers
# ---------------------------------------------------------------------------

_WG_BRUSH_NAME = ".WG_CustomCurve"


def _get_curve_mapping():
    """Get or create the hidden brush that hosts our custom CurveMapping."""
    brush = bpy.data.brushes.get(_WG_BRUSH_NAME)
    if not brush:
        brush = bpy.data.brushes.new(_WG_BRUSH_NAME, mode='SCULPT')
        brush.use_fake_user = True
        mapping = brush.curve
        mapping.clip_min_x = 0.0
        mapping.clip_min_y = 0.0
        mapping.clip_max_x = 1.0
        mapping.clip_max_y = 1.0
        mapping.use_clip = True
        curve = mapping.curves[0]
        while len(curve.points) > 2:
            curve.points.remove(curve.points[1])
        curve.points[0].location = (0.0, 0.0)
        curve.points[-1].location = (1.0, 1.0)
        mapping.update()
    return brush


# Curve preset definitions: list of (x, y) points
CURVE_PRESETS = {
    'LINEAR':    [(0.0, 0.0), (1.0, 1.0)],
    'EASE_IN':   [(0.0, 0.0), (0.5, 0.1), (1.0, 1.0)],
    'EASE_OUT':  [(0.0, 0.0), (0.5, 0.9), (1.0, 1.0)],
    'S_CURVE':   [(0.0, 0.0), (0.25, 0.05), (0.75, 0.95), (1.0, 1.0)],
    'BELL':      [(0.0, 0.0), (0.25, 0.8), (0.5, 1.0), (0.75, 0.8), (1.0, 0.0)],
    'VALLEY':    [(0.0, 1.0), (0.25, 0.2), (0.5, 0.0), (0.75, 0.2), (1.0, 1.0)],
    'STEPS_3':   [(0.0, 0.0), (0.33, 0.0), (0.34, 0.5), (0.66, 0.5), (0.67, 1.0), (1.0, 1.0)],
    'SHARP_IN':  [(0.0, 0.0), (0.8, 0.0), (1.0, 1.0)],
    'SHARP_OUT': [(0.0, 0.0), (0.2, 1.0), (1.0, 1.0)],
}


def _apply_curve_points(points):
    """Set the hidden brush curve to the given list of (x, y) points."""
    brush = _get_curve_mapping()
    mapping = brush.curve
    curve = mapping.curves[0]

    while len(curve.points) > 2:
        curve.points.remove(curve.points[1])

    curve.points[0].location = points[0]
    curve.points[-1].location = points[-1]

    for pt in points[1:-1]:
        curve.points.new(pt[0], pt[1])

    mapping.update()


def _apply_curve_preset(preset_key):
    """Set the hidden brush curve to a preset shape."""
    _apply_curve_points(CURVE_PRESETS[preset_key])


def _read_curve_points():
    """Read the current curve points from the brush as a list of (x, y) tuples."""
    brush = _get_curve_mapping()
    curve = brush.curve.curves[0]
    pts = [(p.location[0], p.location[1]) for p in curve.points]
    pts.sort(key=lambda p: p[0])
    return pts
