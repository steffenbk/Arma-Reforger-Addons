# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
import bmesh
from bpy.types import Operator


class MESH_OT_wg_adjust_weights(Operator):
    """Add or subtract a fixed amount from the weights of selected vertices in the active group"""
    bl_idname = "mesh.wg_adjust_weights"
    bl_label = "Adjust Weights"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object is not None
                and context.active_object.type == 'MESH'
                and context.mode == 'EDIT_MESH')

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

        offset = props.weight_adjust

        bm = bmesh.from_edit_mesh(me)
        bm.verts.ensure_lookup_table()
        selected_indices = [v.index for v in bm.verts if v.select]

        if not selected_indices:
            self.report({'WARNING'}, "No vertices selected")
            return {'CANCELLED'}

        bpy.ops.object.mode_set(mode='OBJECT')

        count = 0
        for vi in selected_indices:
            try:
                old_w = vg.weight(vi)
            except RuntimeError:
                continue  # vertex not in this group — skip
            new_w = max(0.0, min(1.0, old_w + offset))
            vg.add([vi], new_w, 'REPLACE')
            count += 1

        bpy.ops.object.mode_set(mode='EDIT')
        direction = "+" if offset >= 0 else ""
        self.report({'INFO'}, f"Adjusted {count} vertices by {direction}{offset:.3f}")
        return {'FINISHED'}


classes = (MESH_OT_wg_adjust_weights,)
