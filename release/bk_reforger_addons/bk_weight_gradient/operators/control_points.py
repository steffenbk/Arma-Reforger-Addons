# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
from bpy.types import Operator
from bpy.props import StringProperty

from ..utils import _sync_control_points


def _cp_weight(t, preset):
    """Return the weight value for a control point at position t given a preset name."""
    if preset == 'LINEAR':
        return t
    elif preset == 'EASE_IN':
        return t * t
    elif preset == 'EASE_OUT':
        return 1.0 - (1.0 - t) ** 2
    elif preset == 'EASE_IN_OUT':
        return 3.0 * t * t - 2.0 * t * t * t
    elif preset == 'SHARP':
        return t ** 0.5
    return t


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
        pts = props.control_points
        n = len(pts)
        if n == 0:
            self.report({'WARNING'}, "No control points — increase Segments first")
            return {'CANCELLED'}
        n_total = n + 1
        for i, cp in enumerate(pts):
            t = (i + 1) / n_total
            cp.weight = round(_cp_weight(t, self.preset), 4)
        self.report({'INFO'}, f"Applied {self.preset.replace('_', ' ').title()} preset to {n} control points")
        return {'FINISHED'}


classes = (
    MESH_OT_wg_sync_points,
    MESH_OT_wg_cp_preset,
)
