# SPDX-License-Identifier: GPL-2.0-or-later

import json
import random

import bpy
import bmesh
from bpy.types import Operator
from bpy.props import IntProperty

from ..curve_utils import _ensure_curve_mapping
from ..utils import _get_selected_verts, _ensure_anchors, _paint_anchor_verts, _build_stops, _parse_indices


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _interp_stops(t, stops):
    """Linear interpolation between sorted (t, weight) stops."""
    result = stops[-1][1]
    for i in range(len(stops) - 1):
        t0, w0 = stops[i]
        t1, w1 = stops[i + 1]
        if t <= t1 or i == len(stops) - 2:
            seg_len = t1 - t0
            seg_t = (t - t0) / seg_len if seg_len > 1e-10 else 0.0
            seg_t = max(0.0, min(1.0, seg_t))
            result = w0 + (w1 - w0) * seg_t
            break
    return result


def _apply_noise(t, noise):
    """Add uniform jitter to t and clamp result to [0, 1]."""
    if noise > 1e-6:
        t += random.uniform(-noise, noise)
    return max(0.0, min(1.0, t))


def _build_stops_from_props(props):
    """Build sorted (t, weight) stops from anchors[0]/[-1] weights + control points."""
    _ensure_anchors(props)
    w_start = props.anchors[0].weight if props.anchors else 1.0
    w_end   = props.anchors[-1].weight if len(props.anchors) > 1 else 0.0
    stops = [(0.0, w_start)]
    n_cp = len(props.control_points)
    if n_cp > 0:
        n_total = n_cp + 1
        for i, cp in enumerate(props.control_points):
            stops.append(((i + 1) / n_total, cp.weight))
    stops.append((1.0, w_end))
    return stops


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------

class MESH_OT_wg_set_anchor(Operator):
    """Store selected vertices as an anchor point (averaged position)"""
    bl_idname = "mesh.wg_set_anchor"
    bl_label = "Set Anchor"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Anchor Index", default=0)

    @classmethod
    def poll(cls, context):
        return (context.active_object is not None
                and context.active_object.type == 'MESH'
                and context.mode == 'EDIT_MESH')

    def execute(self, context):
        indices, avg_co = _get_selected_verts(context)
        if not indices:
            self.report({'WARNING'}, "Select at least one vertex")
            return {'CANCELLED'}

        props = context.scene.weight_gradient
        _ensure_anchors(props)

        if self.index < 0 or self.index >= len(props.anchors):
            self.report({'WARNING'}, "Invalid anchor index")
            return {'CANCELLED'}

        a = props.anchors[self.index]
        a.indices_json = json.dumps(indices)
        a.co = avg_co
        a.is_set = True
        a.vert_count = len(indices)
        _paint_anchor_verts(context, indices, a.weight)

        label = self.index + 1
        self.report({'INFO'},
            f"Anchor {label} set ({len(indices)} vert{'s' if len(indices) > 1 else ''}) "
            f"weight {a.weight:.2f}")
        return {'FINISHED'}


class MESH_OT_wg_apply_gradient(Operator):
    """Apply weight gradient to selected vertices between the anchors"""
    bl_idname = "mesh.wg_apply_gradient"
    bl_label = "Apply Gradient"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if not (context.active_object and context.active_object.type == 'MESH'
                and context.mode == 'EDIT_MESH'):
            return False
        props = context.scene.weight_gradient
        if props.gradient_source == 'AXIS':
            return True
        # ANCHORS
        anchors = props.anchors
        n = len(anchors)
        return n >= 2 and anchors[0].is_set and anchors[n - 1].is_set

    def execute(self, context):
        obj = context.active_object
        me = obj.data
        props = context.scene.weight_gradient

        if not obj.vertex_groups:
            self.report({'WARNING'}, "No vertex groups on this object")
            return {'CANCELLED'}
        vg_name = props.target_vg_name
        vg = obj.vertex_groups.get(vg_name) if (vg_name and vg_name != 'NONE') else None
        if vg is None:
            self.report({'WARNING'}, "No vertex group selected — pick one in the 'Group' field")
            return {'CANCELLED'}

        curve_mode = props.curve_mode
        offset = props.weight_offset
        noise = props.gradient_noise
        curve_symmetry = props.curve_symmetry

        if curve_mode == 'CURVE_GRAPH':
            brush = _ensure_curve_mapping()
            mapping = brush.curve
            mapping.initialize()
            crv = mapping.curves[0]
        elif curve_mode == 'SIMPLE':
            _sw = props.simple_start
            _ew = props.simple_end
            _spow = 4.0 ** props.simple_shape

        count = 0
        last_painted = []

        # ------------------------------------------------------------------ #
        # AXIS mode                                                            #
        # ------------------------------------------------------------------ #
        if props.gradient_source == 'AXIS':
            stops = _build_stops_from_props(props)

            axis = props.gradient_axis
            axis_idx = {'X': 0, 'Y': 1, 'Z': 2, 'NEG_X': 0, 'NEG_Y': 1, 'NEG_Z': 2}[axis]
            sign = -1 if axis.startswith('NEG') else 1

            _ensure_anchors(props)
            a0 = props.anchors[0] if len(props.anchors) > 0 else None
            a1 = props.anchors[-1] if len(props.anchors) > 1 else None

            bm = bmesh.from_edit_mesh(me)
            bm.verts.ensure_lookup_table()
            sel_verts = [v for v in bm.verts if v.select]
            if not sel_verts:
                self.report({'WARNING'}, "No vertices selected")
                return {'CANCELLED'}

            coords = [(obj.matrix_world @ v.co)[axis_idx] * sign for v in sel_verts]

            # Anchor positions (when set) define the gradient range ends;
            # fall back to selection min/max when not set.
            min_c = a0.co[axis_idx] * sign if (a0 and a0.is_set) else min(coords)
            max_c = a1.co[axis_idx] * sign if (a1 and a1.is_set) else max(coords)
            span = max_c - min_c

            # Anchor vertices are pinned to their anchor weight (same as ANCHORS mode).
            anchor_indices = {}
            if a0 and a0.is_set:
                for idx in _parse_indices(a0.indices_json):
                    anchor_indices[idx] = a0.weight
            if a1 and a1.is_set:
                for idx in _parse_indices(a1.indices_json):
                    anchor_indices[idx] = a1.weight

            vert_t = {}
            for v, c in zip(sel_verts, coords):
                t = (c - min_c) / span if span > 1e-10 else 0.0
                vert_t[v.index] = _apply_noise(t, noise)

            bpy.ops.object.mode_set(mode='OBJECT')
            for v in me.vertices:
                if v.index not in vert_t:
                    continue
                if v.index in anchor_indices:
                    weight = anchor_indices[v.index]
                else:
                    t = vert_t[v.index]
                    if curve_mode == 'CURVE_GRAPH':
                        t_s = 1.0 - abs(2.0 * t - 1.0) if curve_symmetry else t
                        weight = max(0.0, min(1.0, mapping.evaluate(crv, t_s)))
                    elif curve_mode == 'SIMPLE':
                        t_s = 1.0 - abs(2.0 * t - 1.0) if curve_symmetry else t
                        t_p = (t_s ** _spow) if t_s > 1e-10 else 0.0
                        if curve_symmetry:
                            weight = max(0.0, min(1.0, _ew + (_sw - _ew) * t_p))
                        else:
                            weight = max(0.0, min(1.0, _sw + (_ew - _sw) * t_p))
                    else:
                        weight = _interp_stops(t, stops)
                weight = max(0.0, min(1.0, weight + offset))
                vg.add([v.index], weight, 'REPLACE')
                last_painted.append(v.index)
                count += 1

        # ------------------------------------------------------------------ #
        # ANCHORS mode                                                         #
        # ------------------------------------------------------------------ #
        else:
            stops, a_co, ab, ab_len_sq = _build_stops(props)
            if stops is None:
                self.report({'WARNING'}, "First and last anchors must be set and not coincide")
                return {'CANCELLED'}

            anchor_indices = {}
            for a in props.anchors:
                if a.is_set:
                    for idx in _parse_indices(a.indices_json):
                        anchor_indices[idx] = a.weight

            bpy.ops.object.mode_set(mode='OBJECT')
            for v in me.vertices:
                if not v.select:
                    continue
                v_world = obj.matrix_world @ v.co
                t = (v_world - a_co).dot(ab) / ab_len_sq
                t = max(0.0, min(1.0, t))

                if v.index in anchor_indices:
                    weight = anchor_indices[v.index]
                else:
                    t = _apply_noise(t, noise)
                    if curve_mode == 'CURVE_GRAPH':
                        t_s = 1.0 - abs(2.0 * t - 1.0) if curve_symmetry else t
                        weight = max(0.0, min(1.0, mapping.evaluate(crv, t_s)))
                    elif curve_mode == 'SIMPLE':
                        t_s = 1.0 - abs(2.0 * t - 1.0) if curve_symmetry else t
                        t_p = (t_s ** _spow) if t_s > 1e-10 else 0.0
                        if curve_symmetry:
                            weight = max(0.0, min(1.0, _ew + (_sw - _ew) * t_p))
                        else:
                            weight = max(0.0, min(1.0, _sw + (_ew - _sw) * t_p))
                    else:
                        weight = _interp_stops(t, stops)

                weight = max(0.0, min(1.0, weight + offset))
                vg.add([v.index], weight, 'REPLACE')
                last_painted.append(v.index)
                count += 1

        props.last_gradient_indices_json = json.dumps(last_painted)
        bpy.ops.object.mode_set(mode='EDIT')
        self.report({'INFO'}, f"Gradient applied to {count} vertices")
        return {'FINISHED'}


class MESH_OT_wg_flip_gradient(Operator):
    """Flip the gradient direction — swap start/end weights and reverse control points"""
    bl_idname = "mesh.wg_flip_gradient"
    bl_label = "Flip Gradient"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.weight_gradient

        # Swap anchor weights (first ↔ last, second ↔ second-last, …)
        anchors = props.anchors
        n = len(anchors)
        for i in range(n // 2):
            j = n - 1 - i
            anchors[i].weight, anchors[j].weight = anchors[j].weight, anchors[i].weight

        # Reverse control point weights
        pts = props.control_points
        np_ = len(pts)
        for i in range(np_ // 2):
            j = np_ - 1 - i
            pts[i].weight, pts[j].weight = pts[j].weight, pts[i].weight

        # Flip Simple mode start/end
        if props.curve_mode == 'SIMPLE':
            props.simple_start, props.simple_end = props.simple_end, props.simple_start

        # Flip curve graph horizontally (mirror along x = 0.5)
        elif props.curve_mode == 'CURVE_GRAPH':
            from ..curve_utils import _read_curve_points, _apply_curve_points
            pts_curve = _read_curve_points()
            if pts_curve:
                flipped = sorted([(1.0 - x, y) for x, y in pts_curve], key=lambda p: p[0])
                _apply_curve_points(flipped)

        self.report({'INFO'}, "Gradient direction flipped")
        return {'FINISHED'}


class MESH_OT_wg_init_curve_from_anchors(Operator):
    """Set curve endpoints to match first/last anchor weights"""
    bl_idname = "mesh.wg_init_curve_from_anchors"
    bl_label = "Init from Anchors"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        from ..curve_utils import _apply_curve_points
        props = context.scene.weight_gradient
        _ensure_anchors(props)
        anchors = props.anchors
        wa = anchors[0].weight
        wb = anchors[len(anchors) - 1].weight
        _apply_curve_points([(0.0, wa), (1.0, wb)])
        self.report({'INFO'}, f"Curve set: first={wa:.2f} to last={wb:.2f}")
        return {'FINISHED'}


class MESH_OT_wg_select_anchor_verts(Operator):
    """Select the vertices stored in this anchor"""
    bl_idname = "mesh.wg_select_anchor_verts"
    bl_label = "Select Anchor Vertices"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Anchor Index", default=0)

    @classmethod
    def poll(cls, context):
        return (context.active_object is not None
                and context.active_object.type == 'MESH'
                and context.mode == 'EDIT_MESH')

    def execute(self, context):
        props = context.scene.weight_gradient
        _ensure_anchors(props)
        if self.index < 0 or self.index >= len(props.anchors):
            self.report({'WARNING'}, "Invalid anchor index")
            return {'CANCELLED'}
        a = props.anchors[self.index]
        if not a.is_set:
            self.report({'WARNING'}, "Anchor not set")
            return {'CANCELLED'}
        indices = _parse_indices(a.indices_json)
        if not indices:
            self.report({'WARNING'}, "No vertices stored in this anchor")
            return {'CANCELLED'}

        obj = context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        for v in bm.verts:
            v.select = v.index in indices
        bm.select_flush_mode()
        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Selected {len(indices)} anchor vert{'s' if len(indices) != 1 else ''}")
        return {'FINISHED'}


class MESH_OT_wg_clear_anchors(Operator):
    """Clear all anchor points"""
    bl_idname = "mesh.wg_clear_anchors"
    bl_label = "Clear Anchors"
    bl_options = {'REGISTER'}

    def execute(self, context):
        props = context.scene.weight_gradient
        for a in props.anchors:
            a.is_set = False
            a.indices_json = ""
            a.vert_count = 0
        self.report({'INFO'}, "Anchors cleared")
        return {'FINISHED'}


class MESH_OT_wg_select_last_gradient(Operator):
    """Select the vertices that the last Apply Gradient was applied to"""
    bl_idname = "mesh.wg_select_last_gradient"
    bl_label = "Select Last Gradient"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object is not None
                and context.active_object.type == 'MESH'
                and context.mode == 'EDIT_MESH'
                and bool(context.scene.weight_gradient.last_gradient_indices_json))

    def execute(self, context):
        props = context.scene.weight_gradient
        try:
            indices = set(json.loads(props.last_gradient_indices_json))
        except (json.JSONDecodeError, TypeError):
            self.report({'WARNING'}, "No gradient data stored")
            return {'CANCELLED'}
        if not indices:
            self.report({'WARNING'}, "No gradient data stored")
            return {'CANCELLED'}

        obj = context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        for v in bm.verts:
            v.select = v.index in indices
        bm.select_flush_mode()
        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Selected {len(indices)} gradient vert{'s' if len(indices) != 1 else ''}")
        return {'FINISHED'}
