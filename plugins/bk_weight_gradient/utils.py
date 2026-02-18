# SPDX-License-Identifier: GPL-2.0-or-later

import json

import bpy
import bmesh
from mathutils import Vector


def _get_selected_verts(context):
    """Return list of selected vertex indices and their average world position, or ([], None)."""
    obj = context.active_object
    if obj is None or obj.type != 'MESH':
        return [], None
    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    sel = [v for v in bm.verts if v.select]
    if not sel:
        return [], None
    indices = [v.index for v in sel]
    avg = sum((obj.matrix_world @ v.co for v in sel), Vector((0, 0, 0))) / len(sel)
    return indices, avg


def _parse_indices(json_str):
    """Parse a JSON string of indices back to a set of ints."""
    if not json_str:
        return set()
    try:
        return set(json.loads(json_str))
    except (json.JSONDecodeError, TypeError):
        return set()


def _paint_anchor_verts(context, indices, weight):
    """Immediately paint the weight onto anchor vertices so the user sees feedback."""
    obj = context.active_object
    if not obj or not obj.vertex_groups or not obj.vertex_groups.active:
        return
    vg = obj.vertex_groups.active
    idx_set = set(indices)
    bpy.ops.object.mode_set(mode='OBJECT')
    for v in obj.data.vertices:
        if v.index in idx_set:
            vg.add([v.index], weight, 'REPLACE')
    bpy.ops.object.mode_set(mode='EDIT')


def _sync_control_points(props):
    """Ensure control_points collection matches segments count."""
    n_needed = props.segments
    pts = props.control_points
    anchors = props.anchors
    wa = anchors[0].weight if len(anchors) > 0 else 1.0
    wb = anchors[-1].weight if len(anchors) > 1 else 0.0
    n_total = n_needed + 1
    while len(pts) < n_needed:
        item = pts.add()
        i = len(pts) - 1
        t = (i + 1) / n_total
        item.weight = round(wa + (wb - wa) * t, 4)
    while len(pts) > n_needed:
        pts.remove(len(pts) - 1)


def _ensure_anchors(props):
    """Make sure the anchors collection matches anchor_count (e.g. on first access)."""
    n = props.anchor_count
    while len(props.anchors) < n:
        props.anchors.add()
    while len(props.anchors) > n:
        props.anchors.remove(len(props.anchors) - 1)


def _build_stops(props):
    """Build sorted (t, weight) stops by projecting all set anchors onto the first→last line.

    Returns the stops list and the (a_co, ab, ab_len_sq) projection data,
    or (None, None, None, None) if the first/last anchors aren't set or coincide.
    """
    _ensure_anchors(props)
    anchors = props.anchors
    n = len(anchors)
    first = anchors[0]
    last = anchors[n - 1]

    if not first.is_set or not last.is_set:
        return None, None, None, None

    a_co = Vector(first.co)
    b_co = Vector(last.co)
    ab = b_co - a_co
    ab_len_sq = ab.length_squared

    if ab_len_sq < 1e-10:
        return None, None, None, None

    stops = [(0.0, first.weight)]

    for i in range(1, n - 1):
        a = anchors[i]
        if not a.is_set:
            continue
        t = (Vector(a.co) - a_co).dot(ab) / ab_len_sq
        t = max(0.0, min(1.0, t))
        stops.append((t, a.weight))

    # Add evenly-spaced control point stops between t=0 and t=1.
    _sync_control_points(props)
    n_cp = len(props.control_points)
    if n_cp > 0:
        n_total = n_cp + 1
        for i, cp in enumerate(props.control_points):
            stops.append(((i + 1) / n_total, cp.weight))

    stops.append((1.0, last.weight))
    stops.sort(key=lambda s: s[0])
    return stops, a_co, ab, ab_len_sq
