# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
from bpy.types import Operator

from ..utils import _sync_control_points


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


class MESH_OT_wg_reset_cp(Operator):
    """Set all control point weights to 0.5"""
    bl_idname = "mesh.wg_reset_cp"
    bl_label = "Set All to 0.5"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.weight_gradient
        if props.segments == 0:
            props.segments = 5
        _sync_control_points(props)
        for cp in props.control_points:
            cp.weight = 0.5
        self.report({'INFO'}, f"Set {len(props.control_points)} control points to 0.5")
        return {'FINISHED'}


classes = (
    MESH_OT_wg_sync_points,
    MESH_OT_wg_reset_cp,
)
