# SPDX-License-Identifier: GPL-2.0-or-later

import json

import bpy
from bpy.types import Operator
from bpy.props import IntProperty, StringProperty

from ..utils import _sync_control_points


class MESH_OT_wg_save_full_preset(Operator):
    """Save the current gradient settings as a named preset (excludes vertex/anchor positions)"""
    bl_idname = "mesh.wg_save_full_preset"
    bl_label = "Save Settings Preset"
    bl_options = {'REGISTER', 'UNDO'}

    name: StringProperty(name="Name", default="Preset")

    def invoke(self, context, event):
        props = context.scene.weight_gradient
        self.name = f"Preset {len(props.saved_full_presets) + 1}"
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        props = context.scene.weight_gradient
        slot = props.saved_full_presets.add()
        slot.name = self.name
        slot.gradient_source = props.gradient_source
        slot.gradient_axis = props.gradient_axis
        slot.anchor_count = props.anchor_count
        slot.anchor_weights_json = json.dumps([a.weight for a in props.anchors])
        slot.curve_mode = props.curve_mode
        slot.weight_offset = props.weight_offset
        slot.segments = props.segments
        slot.control_points_json = json.dumps([cp.weight for cp in props.control_points])
        slot.gradient_noise = props.gradient_noise
        slot.simple_shape = props.simple_shape
        slot.simple_start = props.simple_start
        slot.simple_end = props.simple_end
        props.active_full_preset_index = len(props.saved_full_presets) - 1
        self.report({'INFO'}, f"Saved preset '{self.name}'")
        return {'FINISHED'}


class MESH_OT_wg_load_full_preset(Operator):
    """Load a saved settings preset"""
    bl_idname = "mesh.wg_load_full_preset"
    bl_label = "Load Settings Preset"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Slot Index", default=0)

    def execute(self, context):
        props = context.scene.weight_gradient
        if self.index < 0 or self.index >= len(props.saved_full_presets):
            self.report({'WARNING'}, "Invalid preset slot")
            return {'CANCELLED'}

        slot = props.saved_full_presets[self.index]

        props.gradient_source = slot.gradient_source
        props.gradient_axis = slot.gradient_axis
        props.curve_mode = slot.curve_mode
        props.weight_offset = slot.weight_offset
        props.gradient_noise = slot.gradient_noise
        props.simple_shape = slot.simple_shape
        props.simple_start = slot.simple_start
        props.simple_end = slot.simple_end

        # Anchor count + weights (does not affect vertex selections)
        props.anchor_count = slot.anchor_count
        try:
            anchor_weights = json.loads(slot.anchor_weights_json)
        except (json.JSONDecodeError, TypeError):
            anchor_weights = []
        for i, a in enumerate(props.anchors):
            if i < len(anchor_weights):
                a.weight = anchor_weights[i]

        # Control points
        props.segments = slot.segments
        _sync_control_points(props)
        try:
            cp_weights = json.loads(slot.control_points_json)
        except (json.JSONDecodeError, TypeError):
            cp_weights = []
        for i, cp in enumerate(props.control_points):
            if i < len(cp_weights):
                cp.weight = cp_weights[i]

        self.report({'INFO'}, f"Loaded preset '{slot.name}'")
        return {'FINISHED'}


class MESH_OT_wg_delete_full_preset(Operator):
    """Delete a saved settings preset"""
    bl_idname = "mesh.wg_delete_full_preset"
    bl_label = "Delete Settings Preset"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Slot Index", default=0)

    def execute(self, context):
        props = context.scene.weight_gradient
        if self.index < 0 or self.index >= len(props.saved_full_presets):
            return {'CANCELLED'}
        name = props.saved_full_presets[self.index].name
        props.saved_full_presets.remove(self.index)
        if props.active_full_preset_index >= len(props.saved_full_presets):
            props.active_full_preset_index = max(0, len(props.saved_full_presets) - 1)
        self.report({'INFO'}, f"Deleted preset '{name}'")
        return {'FINISHED'}


classes = (
    MESH_OT_wg_save_full_preset,
    MESH_OT_wg_load_full_preset,
    MESH_OT_wg_delete_full_preset,
)
