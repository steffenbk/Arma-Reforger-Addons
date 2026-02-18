# SPDX-License-Identifier: GPL-2.0-or-later

import json

import bpy
import bmesh
from bpy.types import Operator
from bpy.props import IntProperty, StringProperty

from ..utils import _get_selected_verts, _parse_indices


class MESH_OT_wg_save_selection(Operator):
    """Save the current vertex selection to a named slot"""
    bl_idname = "mesh.wg_save_selection"
    bl_label = "Save Selection"
    bl_options = {'REGISTER', 'UNDO'}

    name: StringProperty(name="Name", default="Selection")

    @classmethod
    def poll(cls, context):
        return (context.active_object is not None
                and context.active_object.type == 'MESH'
                and context.mode == 'EDIT_MESH')

    def invoke(self, context, event):
        props = context.scene.weight_gradient
        self.name = f"Selection {len(props.saved_selections) + 1}"
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        indices, _ = _get_selected_verts(context)
        if not indices:
            self.report({'WARNING'}, "No vertices selected")
            return {'CANCELLED'}

        props = context.scene.weight_gradient
        slot = props.saved_selections.add()
        slot.name = self.name
        slot.indices_json = json.dumps(indices)
        slot.count = len(indices)
        props.active_selection_index = len(props.saved_selections) - 1

        # Auto-assign to the active group (if one is selected).
        if (props.saved_selection_groups
                and 0 <= props.active_selection_group_index < len(props.saved_selection_groups)):
            slot.group_name = props.saved_selection_groups[props.active_selection_group_index].name

        self.report({'INFO'}, f"Saved '{self.name}' ({len(indices)} verts)")
        return {'FINISHED'}


class MESH_OT_wg_load_selection(Operator):
    """Load a saved vertex selection"""
    bl_idname = "mesh.wg_load_selection"
    bl_label = "Load Selection"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Slot Index", default=0)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            return False
        return context.mode in {'EDIT_MESH', 'OBJECT'}

    def execute(self, context):
        props = context.scene.weight_gradient
        if self.index < 0 or self.index >= len(props.saved_selections):
            self.report({'WARNING'}, "Invalid selection slot")
            return {'CANCELLED'}

        slot = props.saved_selections[self.index]
        idx_set = _parse_indices(slot.indices_json)
        if not idx_set:
            self.report({'WARNING'}, "Selection is empty")
            return {'CANCELLED'}

        obj = context.active_object

        was_object = (context.mode == 'OBJECT')
        if was_object:
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

        props.active_selection_index = self.index
        self.report({'INFO'}, f"Loaded '{slot.name}' ({slot.count} verts)")
        return {'FINISHED'}


class MESH_OT_wg_add_selection_group(Operator):
    """Add a new gradient vertices group"""
    bl_idname = "mesh.wg_add_selection_group"
    bl_label = "Add Selection Group"
    bl_options = {'REGISTER', 'UNDO'}

    name: StringProperty(name="Name", default="Group")

    def invoke(self, context, event):
        props = context.scene.weight_gradient
        self.name = f"Group {len(props.saved_selection_groups) + 1}"
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        props = context.scene.weight_gradient
        grp = props.saved_selection_groups.add()
        grp.name = self.name
        props.active_selection_group_index = len(props.saved_selection_groups) - 1
        self.report({'INFO'}, f"Added group '{self.name}'")
        return {'FINISHED'}


class MESH_OT_wg_delete_selection_group(Operator):
    """Delete a gradient vertices group (selections in it become ungrouped)"""
    bl_idname = "mesh.wg_delete_selection_group"
    bl_label = "Delete Selection Group"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Group Index", default=0)

    def execute(self, context):
        props = context.scene.weight_gradient
        if self.index < 0 or self.index >= len(props.saved_selection_groups):
            return {'CANCELLED'}

        grp_name = props.saved_selection_groups[self.index].name
        for s in props.saved_selections:
            if s.group_name == grp_name:
                s.group_name = ""

        props.saved_selection_groups.remove(self.index)
        if props.active_selection_group_index >= len(props.saved_selection_groups):
            props.active_selection_group_index = max(0, len(props.saved_selection_groups) - 1)
        self.report({'INFO'}, f"Deleted group '{grp_name}'")
        return {'FINISHED'}


class MESH_OT_wg_assign_selection_to_group(Operator):
    """Assign the selected gradient vertices to the active group"""
    bl_idname = "mesh.wg_assign_selection_to_group"
    bl_label = "Assign to Group"
    bl_options = {'REGISTER', 'UNDO'}

    set_index: IntProperty(name="Selection Index", default=0)

    def execute(self, context):
        props = context.scene.weight_gradient
        if self.set_index < 0 or self.set_index >= len(props.saved_selections):
            return {'CANCELLED'}

        slot = props.saved_selections[self.set_index]
        if (props.saved_selection_groups
                and 0 <= props.active_selection_group_index < len(props.saved_selection_groups)):
            grp_name = props.saved_selection_groups[props.active_selection_group_index].name
            slot.group_name = grp_name
            self.report({'INFO'}, f"Assigned '{slot.name}' to group '{grp_name}'")
        else:
            slot.group_name = ""
            self.report({'INFO'}, f"Ungrouped '{slot.name}'")
        return {'FINISHED'}


class MESH_OT_wg_delete_selection(Operator):
    """Delete a saved vertex selection"""
    bl_idname = "mesh.wg_delete_selection"
    bl_label = "Delete Selection"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Slot Index", default=0)

    def execute(self, context):
        props = context.scene.weight_gradient
        if self.index < 0 or self.index >= len(props.saved_selections):
            return {'CANCELLED'}

        name = props.saved_selections[self.index].name
        props.saved_selections.remove(self.index)
        if props.active_selection_index >= len(props.saved_selections):
            props.active_selection_index = max(0, len(props.saved_selections) - 1)
        self.report({'INFO'}, f"Deleted '{name}'")
        return {'FINISHED'}
