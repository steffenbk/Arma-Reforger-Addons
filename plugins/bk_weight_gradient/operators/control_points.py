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


classes = (MESH_OT_wg_sync_points,)
