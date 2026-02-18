# SPDX-License-Identifier: GPL-2.0-or-later

import json

import bpy
from bpy.types import Operator
from bpy.props import IntProperty, StringProperty, EnumProperty

from ..curve_utils import _read_curve_points, _apply_curve_points, _apply_curve_preset


class MESH_OT_wg_save_curve(Operator):
    """Save the current custom curve"""
    bl_idname = "mesh.wg_save_curve"
    bl_label = "Save Curve"
    bl_options = {'REGISTER', 'UNDO'}

    name: StringProperty(name="Name", default="My Curve")

    def invoke(self, context, event):
        props = context.scene.weight_gradient
        self.name = f"Curve {len(props.saved_curves) + 1}"
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        props = context.scene.weight_gradient
        pts = _read_curve_points()
        slot = props.saved_curves.add()
        slot.name = self.name
        slot.points_json = json.dumps(pts)
        slot.point_count = len(pts)
        props.active_curve_index = len(props.saved_curves) - 1
        self.report({'INFO'}, f"Saved curve '{self.name}' ({len(pts)} points)")
        return {'FINISHED'}


class MESH_OT_wg_load_curve(Operator):
    """Load a saved custom curve"""
    bl_idname = "mesh.wg_load_curve"
    bl_label = "Load Curve"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Slot Index", default=0)

    def execute(self, context):
        props = context.scene.weight_gradient
        if self.index < 0 or self.index >= len(props.saved_curves):
            self.report({'WARNING'}, "Invalid curve slot")
            return {'CANCELLED'}
        slot = props.saved_curves[self.index]
        try:
            pts = [tuple(p) for p in json.loads(slot.points_json)]
        except (json.JSONDecodeError, TypeError):
            self.report({'WARNING'}, "Corrupt curve data")
            return {'CANCELLED'}
        if len(pts) < 2:
            self.report({'WARNING'}, "Curve needs at least 2 points")
            return {'CANCELLED'}
        _apply_curve_points(pts)
        props.active_curve_index = self.index
        self.report({'INFO'}, f"Loaded curve '{slot.name}'")
        return {'FINISHED'}


class MESH_OT_wg_delete_curve(Operator):
    """Delete a saved custom curve"""
    bl_idname = "mesh.wg_delete_curve"
    bl_label = "Delete Curve"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Slot Index", default=0)

    def execute(self, context):
        props = context.scene.weight_gradient
        if self.index < 0 or self.index >= len(props.saved_curves):
            return {'CANCELLED'}
        name = props.saved_curves[self.index].name
        props.saved_curves.remove(self.index)
        if props.active_curve_index >= len(props.saved_curves):
            props.active_curve_index = max(0, len(props.saved_curves) - 1)
        self.report({'INFO'}, f"Deleted curve '{name}'")
        return {'FINISHED'}


class MESH_OT_wg_curve_preset(Operator):
    """Apply a preset shape to the custom curve"""
    bl_idname = "mesh.wg_curve_preset"
    bl_label = "Curve Preset"
    bl_options = {'REGISTER', 'UNDO'}

    preset: EnumProperty(
        name="Preset",
        items=[
            ('LINEAR',    "Linear",    "Straight line"),
            ('EASE_IN',   "Ease In",   "Slow start, fast end"),
            ('EASE_OUT',  "Ease Out",  "Fast start, slow end"),
            ('S_CURVE',   "S-Curve",   "Smooth sigmoid"),
            ('BELL',      "Bell",      "Peak in the middle"),
            ('VALLEY',    "Valley",    "Dip in the middle"),
            ('STEPS_3',   "3 Steps",   "Staircase with 3 levels"),
            ('SHARP_IN',  "Sharp In",  "Flat then sudden ramp"),
            ('SHARP_OUT', "Sharp Out", "Sudden ramp then flat"),
        ],
    )

    def execute(self, context):
        _apply_curve_preset(self.preset)
        return {'FINISHED'}
