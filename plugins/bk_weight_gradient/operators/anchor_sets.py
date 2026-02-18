# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
import bmesh
from bpy.types import Operator
from bpy.props import IntProperty, StringProperty

from ..utils import _get_selected_verts, _parse_indices


class MESH_OT_wg_save_anchor_set(Operator):
    """Save the current vertex selection as an anchor set"""
    bl_idname = "mesh.wg_save_anchor_set"
    bl_label = "Save Anchors"
    bl_options = {'REGISTER', 'UNDO'}

    name: StringProperty(name="Name", default="Anchors")

    @classmethod
    def poll(cls, context):
        return (context.active_object is not None
                and context.active_object.type == 'MESH'
                and context.mode == 'EDIT_MESH')

    def invoke(self, context, event):
        props = context.scene.weight_gradient
        self.name = f"Anchors {len(props.saved_anchor_sets) + 1}"
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        import json
        indices, _ = _get_selected_verts(context)
        if not indices:
            self.report({'WARNING'}, "No vertices selected")
            return {'CANCELLED'}

        props = context.scene.weight_gradient
        slot = props.saved_anchor_sets.add()
        slot.name = self.name
        slot.data_json = json.dumps(indices)
        slot.anchor_count = len(indices)
        props.active_anchor_set_index = len(props.saved_anchor_sets) - 1

        # Auto-assign to the active group (if one is selected).
        if (props.saved_anchor_groups
                and 0 <= props.active_anchor_group_index < len(props.saved_anchor_groups)):
            slot.group_name = props.saved_anchor_groups[props.active_anchor_group_index].name

        self.report({'INFO'}, f"Saved '{self.name}' ({len(indices)} verts)")
        return {'FINISHED'}


class MESH_OT_wg_load_anchor_set(Operator):
    """Load a saved anchor set — selects its vertices in Edit Mode"""
    bl_idname = "mesh.wg_load_anchor_set"
    bl_label = "Load Anchors"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Slot Index", default=0)

    def execute(self, context):
        props = context.scene.weight_gradient
        if self.index < 0 or self.index >= len(props.saved_anchor_sets):
            self.report({'WARNING'}, "Invalid anchor set slot")
            return {'CANCELLED'}

        slot = props.saved_anchor_sets[self.index]
        idx_set = _parse_indices(slot.data_json)
        if not idx_set:
            self.report({'WARNING'}, "Anchor set is empty")
            return {'CANCELLED'}

        props.active_anchor_set_index = self.index

        obj = context.active_object
        if not obj or obj.type != 'MESH':
            return {'CANCELLED'}

        if context.mode != 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='EDIT')
        context.tool_settings.mesh_select_mode = (True, False, False)

        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        for v in bm.verts:
            v.select = False
        for e in bm.edges:
            e.select = False
        for f in bm.faces:
            f.select = False
        for v in bm.verts:
            if v.index in idx_set:
                v.select = True
        bm.select_flush_mode()
        bmesh.update_edit_mesh(obj.data)

        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

        self.report({'INFO'}, f"Loaded '{slot.name}' ({slot.anchor_count} verts)")
        return {'FINISHED'}


class MESH_OT_wg_load_checked_anchor_sets(Operator):
    """Select the union of all checked anchor sets"""
    bl_idname = "mesh.wg_load_checked_anchor_sets"
    bl_label = "Load Checked"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.weight_gradient
        checked = [(i, s) for i, s in enumerate(props.saved_anchor_sets) if s.selected]
        if not checked:
            self.report({'WARNING'}, "No anchor sets checked")
            return {'CANCELLED'}

        all_indices = set()
        slot_names = []
        for _, slot in checked:
            all_indices.update(_parse_indices(slot.data_json))
            slot_names.append(slot.name)

        if not all_indices:
            self.report({'WARNING'}, "No vertex data found")
            return {'CANCELLED'}

        props.active_anchor_set_index = checked[-1][0]

        obj = context.active_object
        if not obj or obj.type != 'MESH':
            return {'CANCELLED'}

        if context.mode != 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='EDIT')
        context.tool_settings.mesh_select_mode = (True, False, False)

        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        for v in bm.verts:
            v.select = False
        for e in bm.edges:
            e.select = False
        for f in bm.faces:
            f.select = False
        for v in bm.verts:
            if v.index in all_indices:
                v.select = True
        bm.select_flush_mode()
        bmesh.update_edit_mesh(obj.data)

        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

        self.report({'INFO'}, f"Loaded '{' + '.join(slot_names)}' ({len(all_indices)} verts)")
        return {'FINISHED'}


class MESH_OT_wg_add_anchor_group(Operator):
    """Add a new anchor group"""
    bl_idname = "mesh.wg_add_anchor_group"
    bl_label = "Add Anchor Group"
    bl_options = {'REGISTER', 'UNDO'}

    name: StringProperty(name="Name", default="Group")

    def invoke(self, context, event):
        props = context.scene.weight_gradient
        self.name = f"Group {len(props.saved_anchor_groups) + 1}"
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        props = context.scene.weight_gradient
        grp = props.saved_anchor_groups.add()
        grp.name = self.name
        props.active_anchor_group_index = len(props.saved_anchor_groups) - 1
        self.report({'INFO'}, f"Added group '{self.name}'")
        return {'FINISHED'}


class MESH_OT_wg_delete_anchor_group(Operator):
    """Delete an anchor group (anchor sets in it become ungrouped)"""
    bl_idname = "mesh.wg_delete_anchor_group"
    bl_label = "Delete Anchor Group"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Group Index", default=0)

    def execute(self, context):
        props = context.scene.weight_gradient
        if self.index < 0 or self.index >= len(props.saved_anchor_groups):
            return {'CANCELLED'}

        grp_name = props.saved_anchor_groups[self.index].name
        # Ungroup any anchor sets that belong to this group.
        for s in props.saved_anchor_sets:
            if s.group_name == grp_name:
                s.group_name = ""

        props.saved_anchor_groups.remove(self.index)
        if props.active_anchor_group_index >= len(props.saved_anchor_groups):
            props.active_anchor_group_index = max(0, len(props.saved_anchor_groups) - 1)
        self.report({'INFO'}, f"Deleted group '{grp_name}'")
        return {'FINISHED'}


class MESH_OT_wg_assign_to_group(Operator):
    """Assign the selected anchor set to the active group (or ungroup if no group is active)"""
    bl_idname = "mesh.wg_assign_to_group"
    bl_label = "Assign to Group"
    bl_options = {'REGISTER', 'UNDO'}

    set_index: IntProperty(name="Anchor Set Index", default=0)

    def execute(self, context):
        props = context.scene.weight_gradient
        if self.set_index < 0 or self.set_index >= len(props.saved_anchor_sets):
            return {'CANCELLED'}

        slot = props.saved_anchor_sets[self.set_index]
        if (props.saved_anchor_groups
                and 0 <= props.active_anchor_group_index < len(props.saved_anchor_groups)):
            grp_name = props.saved_anchor_groups[props.active_anchor_group_index].name
            slot.group_name = grp_name
            self.report({'INFO'}, f"Assigned '{slot.name}' to group '{grp_name}'")
        else:
            slot.group_name = ""
            self.report({'INFO'}, f"Ungrouped '{slot.name}'")
        return {'FINISHED'}


class MESH_OT_wg_delete_anchor_set(Operator):
    """Delete a saved anchor setup"""
    bl_idname = "mesh.wg_delete_anchor_set"
    bl_label = "Delete Anchor Set"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Slot Index", default=0)

    def execute(self, context):
        props = context.scene.weight_gradient
        if self.index < 0 or self.index >= len(props.saved_anchor_sets):
            return {'CANCELLED'}

        name = props.saved_anchor_sets[self.index].name
        props.saved_anchor_sets.remove(self.index)
        if props.active_anchor_set_index >= len(props.saved_anchor_sets):
            props.active_anchor_set_index = max(0, len(props.saved_anchor_sets) - 1)
        self.report({'INFO'}, f"Deleted '{name}'")
        return {'FINISHED'}
