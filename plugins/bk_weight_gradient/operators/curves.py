# SPDX-License-Identifier: GPL-2.0-or-later

import json
import os

import bpy
from bpy.types import Operator
from bpy.props import IntProperty, StringProperty, EnumProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper

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


# ---------------------------------------------------------------------------
# Export / Import
# ---------------------------------------------------------------------------

class MESH_OT_wg_export_presets(Operator, ExportHelper):
    """Export all saved curves, anchor sets, selections and settings presets to a JSON file"""
    bl_idname = "mesh.wg_export_presets"
    bl_label = "Export Presets"
    bl_options = {'REGISTER'}

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})

    def execute(self, context):
        props = context.scene.weight_gradient

        data = {
            "version": 1,
            "curves": [
                {
                    "name": c.name,
                    "points_json": c.points_json,
                    "point_count": c.point_count,
                }
                for c in props.saved_curves
            ],
            "anchor_sets": [
                {
                    "name": s.name,
                    "data_json": s.data_json,
                    "anchor_count": s.anchor_count,
                    "group_name": s.group_name,
                }
                for s in props.saved_anchor_sets
            ],
            "selections": [
                {
                    "name": s.name,
                    "indices_json": s.indices_json,
                    "count": s.count,
                    "group_name": s.group_name,
                }
                for s in props.saved_selections
            ],
            "full_presets": [
                {
                    "name": p.name,
                    "gradient_source": p.gradient_source,
                    "gradient_axis": p.gradient_axis,
                    "anchor_count": p.anchor_count,
                    "anchor_weights_json": p.anchor_weights_json,
                    "curve_mode": p.curve_mode,
                    "weight_offset": p.weight_offset,
                    "segments": p.segments,
                    "control_points_json": p.control_points_json,
                    "gradient_noise": p.gradient_noise,
                    "simple_shape": p.simple_shape,
                }
                for p in props.saved_full_presets
            ],
        }

        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            self.report({'ERROR'}, f"Could not write file: {e}")
            return {'CANCELLED'}

        total = (len(props.saved_curves) + len(props.saved_anchor_sets)
                 + len(props.saved_selections) + len(props.saved_full_presets))
        self.report({'INFO'}, f"Exported {total} items to {os.path.basename(self.filepath)}")
        return {'FINISHED'}


class MESH_OT_wg_import_presets(Operator, ImportHelper):
    """Import curves, anchor sets, selections and settings presets from a JSON file"""
    bl_idname = "mesh.wg_import_presets"
    bl_label = "Import Presets"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})

    def execute(self, context):
        props = context.scene.weight_gradient

        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            self.report({'ERROR'}, f"Could not read file: {e}")
            return {'CANCELLED'}

        if data.get("version", 0) != 1:
            self.report({'WARNING'}, "Unrecognized file version — attempting import anyway")

        added = 0

        for c in data.get("curves", []):
            slot = props.saved_curves.add()
            slot.name = c.get("name", "Curve")
            slot.points_json = c.get("points_json", "[]")
            slot.point_count = c.get("point_count", 0)
            added += 1

        for s in data.get("anchor_sets", []):
            slot = props.saved_anchor_sets.add()
            slot.name = s.get("name", "Anchors")
            slot.data_json = s.get("data_json", "[]")
            slot.anchor_count = s.get("anchor_count", 2)
            slot.group_name = s.get("group_name", "")
            added += 1

        for s in data.get("selections", []):
            slot = props.saved_selections.add()
            slot.name = s.get("name", "Selection")
            slot.indices_json = s.get("indices_json", "[]")
            slot.count = s.get("count", 0)
            slot.group_name = s.get("group_name", "")
            added += 1

        for p in data.get("full_presets", []):
            slot = props.saved_full_presets.add()
            slot.name = p.get("name", "Preset")
            slot.gradient_source = p.get("gradient_source", "ANCHORS")
            slot.gradient_axis = p.get("gradient_axis", "Z")
            slot.anchor_count = p.get("anchor_count", 2)
            slot.anchor_weights_json = p.get("anchor_weights_json", "[]")
            slot.curve_mode = p.get("curve_mode", "CONTROL_POINTS")
            slot.weight_offset = p.get("weight_offset", 0.0)
            slot.segments = p.get("segments", 0)
            slot.control_points_json = p.get("control_points_json", "[]")
            slot.gradient_noise = p.get("gradient_noise", 0.0)
            slot.simple_shape = p.get("simple_shape", 0.0)
            added += 1

        self.report({'INFO'}, f"Imported {added} items from {os.path.basename(self.filepath)}")
        return {'FINISHED'}
