# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
from bpy.types import Operator
from bpy.props import StringProperty

from ..utils import _sync_control_points, _ensure_anchors


def _lerp(a, b, x):
    return a + (b - a) * x


def _cp_weight(t, preset, w_a, w_b):
    """Return the weight for a control point at position t, interpolating between anchor weights."""
    if preset == 'LINEAR':
        f = t
    elif preset == 'EASE_IN':
        f = t * t
    elif preset == 'EASE_OUT':
        f = 1.0 - (1.0 - t) ** 2
    elif preset == 'EASE_IN_OUT':
        f = 3.0 * t * t - 2.0 * t * t * t
    elif preset == 'SHARP':
        f = t ** 0.5
    else:
        f = t
    return _lerp(w_a, w_b, f)


class MESH_OT_wg_sync_points(Operator):
    """Sync control points collection to match the segment count"""
    bl_idname = "mesh.wg_sync_points"
    bl_label = "Sync Control Points"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.weight_gradient
        _sync_control_points(props)
        self.report({'INFO'}, f"Synced to {props.segments} control points")
        return {'FINISHED'}


class MESH_OT_wg_cp_preset(Operator):
    """Apply a mathematical preset to the control point weights"""
    bl_idname = "mesh.wg_cp_preset"
    bl_label = "Apply Control Point Preset"
    bl_options = {'REGISTER', 'UNDO'}

    preset: StringProperty(name="Preset", default="LINEAR")

    def execute(self, context):
        props = context.scene.weight_gradient
        # Auto-initialise segments if none exist
        if props.segments == 0:
            props.segments = 5
        # Explicit sync in case the update callback didn't populate the collection
        _sync_control_points(props)
        pts = props.control_points
        n = len(pts)
        _ensure_anchors(props)
        anchors = props.anchors
        w_a = anchors[0].weight if len(anchors) > 0 else 1.0
        w_b = anchors[-1].weight if len(anchors) > 1 else 0.0
        n_total = n + 1
        for i, cp in enumerate(pts):
            t = (i + 1) / n_total
            cp.weight = round(_cp_weight(t, self.preset, w_a, w_b), 4)
        self.report({'INFO'}, f"Applied {self.preset.replace('_', ' ').title()} preset to {n} control points")
        return {'FINISHED'}


classes = (
    MESH_OT_wg_sync_points,
    MESH_OT_wg_cp_preset,
)
