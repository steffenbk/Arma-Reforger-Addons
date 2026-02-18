# SPDX-License-Identifier: GPL-2.0-or-later

import json

import bpy
from bpy.types import Operator
from bpy.props import IntProperty

from ..curve_utils import _get_curve_mapping
from ..utils import _get_selected_verts, _ensure_anchors, _paint_anchor_verts, _build_stops, _parse_indices


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
        vg = obj.vertex_groups.active
        if vg is None:
            self.report({'WARNING'}, "No active vertex group")
            return {'CANCELLED'}

        stops, a_co, ab, ab_len_sq = _build_stops(props)
        if stops is None:
            self.report({'WARNING'}, "First and last anchors must be set and not coincide")
            return {'CANCELLED'}

        anchor_indices = {}
        for a in props.anchors:
            if a.is_set:
                for idx in _parse_indices(a.indices_json):
                    anchor_indices[idx] = a.weight

        curve_mode = props.curve_mode
        power = props.curve_power

        if curve_mode == 'CURVE_GRAPH':
            brush = _get_curve_mapping()
            mapping = brush.curve
            mapping.initialize()
            crv = mapping.curves[0]

        bpy.ops.object.mode_set(mode='OBJECT')

        count = 0
        for v in me.vertices:
            if not v.select:
                continue

            v_world = obj.matrix_world @ v.co
            t = (v_world - a_co).dot(ab) / ab_len_sq
            t = max(0.0, min(1.0, t))

            if curve_mode == 'CURVE_GRAPH':
                weight = mapping.evaluate(crv, t)
                weight = max(0.0, min(1.0, weight))
            else:  # CONTROL_POINTS — linear lerp between stops
                if v.index in anchor_indices:
                    weight = anchor_indices[v.index]
                else:
                    weight = stops[-1][1]
                    for i in range(len(stops) - 1):
                        t0, w0 = stops[i]
                        t1, w1 = stops[i + 1]
                        if t <= t1 or i == len(stops) - 2:
                            seg_len = t1 - t0
                            seg_t = (t - t0) / seg_len if seg_len > 1e-10 else 0.0
                            seg_t = max(0.0, min(1.0, seg_t))
                            weight = w0 + (w1 - w0) * seg_t
                            break

            # Power post-processing (0 = no effect)
            if power > 1e-6:
                weight = max(0.0, min(1.0, weight)) ** (1.0 + power)

            vg.add([v.index], weight, 'REPLACE')
            count += 1

        bpy.ops.object.mode_set(mode='EDIT')
        self.report({'INFO'}, f"Gradient applied to {count} vertices")
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
