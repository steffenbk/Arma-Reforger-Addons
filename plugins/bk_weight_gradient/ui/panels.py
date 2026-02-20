# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
from bpy.types import Panel

from ..curve_utils import _get_curve_mapping
from ..utils import _ensure_anchors


class WG_UL_saved_curves(bpy.types.UIList):
    bl_idname = "WG_UL_saved_curves"

    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        row = layout.row(align=True)
        row.prop(item, "name", text="", emboss=False, icon='CURVE_DATA')
        row.label(text=f"({item.point_count}pt)")
        op_del = row.operator("mesh.wg_delete_curve", text="", icon='X')
        op_del.index = index


class WG_UL_saved_selections(bpy.types.UIList):
    bl_idname = "WG_UL_saved_selections"

    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        row = layout.row(align=True)
        row.prop(item, "name", text="", emboss=False, icon='RESTRICT_SELECT_OFF')
        row.label(text=f"({item.count})")
        op_del = row.operator("mesh.wg_delete_selection", text="", icon='X')
        op_del.index = index

    def filter_items(self, context, data, propname):
        sets = getattr(data, propname)
        if (not data.saved_selection_groups
                or data.active_selection_group_index < 0
                or data.active_selection_group_index >= len(data.saved_selection_groups)):
            return [self.bitflag_filter_item] * len(sets), []
        active_name = data.saved_selection_groups[data.active_selection_group_index].name
        flt_flags = [
            self.bitflag_filter_item if (s.group_name == active_name or s.group_name == "") else 0
            for s in sets
        ]
        return flt_flags, []


class WG_UL_selection_groups(bpy.types.UIList):
    bl_idname = "WG_UL_selection_groups"

    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        props = context.scene.weight_gradient
        count = sum(1 for s in props.saved_selections if s.group_name == item.name)
        row = layout.row(align=True)
        row.prop(item, "name", text="", emboss=False, icon='FILE_FOLDER')
        row.label(text=f"({count})")
        op_del = row.operator("mesh.wg_delete_selection_group", text="", icon='X')
        op_del.index = index


class WG_UL_anchor_groups(bpy.types.UIList):
    bl_idname = "WG_UL_anchor_groups"

    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        props = context.scene.weight_gradient
        count = sum(1 for s in props.saved_anchor_sets if s.group_name == item.name)
        row = layout.row(align=True)
        row.prop(item, "name", text="", emboss=False, icon='FILE_FOLDER')
        row.label(text=f"({count})")
        op_del = row.operator("mesh.wg_delete_anchor_group", text="", icon='X')
        op_del.index = index


class WG_UL_saved_anchor_sets(bpy.types.UIList):
    bl_idname = "WG_UL_saved_anchor_sets"

    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        row = layout.row(align=True)
        row.prop(item, "name", text="", emboss=False, icon='ANCHOR_CENTER')
        row.label(text=f"({item.anchor_count})")
        op_del = row.operator("mesh.wg_delete_anchor_set", text="", icon='X')
        op_del.index = index

    def filter_items(self, context, data, propname):
        sets = getattr(data, propname)
        if (not data.saved_anchor_groups
                or data.active_anchor_group_index < 0
                or data.active_anchor_group_index >= len(data.saved_anchor_groups)):
            return [self.bitflag_filter_item] * len(sets), []
        active_name = data.saved_anchor_groups[data.active_anchor_group_index].name
        flt_flags = [
            self.bitflag_filter_item if (s.group_name == active_name or s.group_name == "") else 0
            for s in sets
        ]
        return flt_flags, []


class VIEW3D_PT_weight_gradient(Panel):
    bl_label = "Weight Gradient"
    bl_idname = "VIEW3D_PT_weight_gradient"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "BK Weight Gradient"

    @classmethod
    def poll(cls, context):
        return (context.active_object is not None
                and context.active_object.type == 'MESH')

    def draw(self, context):
        layout = self.layout
        props = context.scene.weight_gradient
        obj = context.active_object

        # -- Gradient Source toggle -------------------------------------
        row = layout.row(align=True)
        row.prop(props, "gradient_source", expand=True)

        # -- Anchors / Axis setup ---------------------------------------
        if props.gradient_source == 'AXIS':
            box_axis = layout.box()
            row = box_axis.row(align=True)
            row.label(text="Axis:")
            row.prop(props, "gradient_axis", expand=True)
            _ensure_anchors(props)
            if props.anchors:
                row2 = box_axis.row(align=True)
                row2.prop(props.anchors[0], "weight", slider=True, text="Start Weight")
                row2.prop(props.anchors[-1], "weight", slider=True, text="End Weight")
        else:
            # -- Anchor Count -------------------------------------------
            layout.prop(props, "anchor_count")
            # -- Anchor boxes -------------------------------------------
            for i, a in enumerate(props.anchors):
                box = layout.box()
                row = box.row(align=True)
                label = i + 1
                op = row.operator("mesh.wg_set_anchor", text=f"Set Anchor {label}",
                                  icon='VERTEXSEL')
                op.index = i
                if a.is_set:
                    n = a.vert_count
                    row.label(text=f"{n} vert{'s' if n > 1 else ''}", icon='CHECKMARK')
                else:
                    row.label(text="Not set", icon='X')
                box.prop(a, "weight", slider=True)

        layout.separator()

        # -- Vertex group -----------------------------------------------
        if obj.vertex_groups:
            layout.prop_search(props, "target_vg_name", obj, "vertex_groups", text="Group")
        else:
            layout.label(text="No vertex groups", icon='ERROR')

        # -- Curve & Control Points -------------------------------------
        box_curve = layout.box()

        # Main mode toggle: Control Points | Curve Graph
        row = box_curve.row(align=True)
        row.prop(props, "curve_mode", expand=True)

        if props.curve_mode == 'CURVE_GRAPH':
            # Collapsible graphical editor
            row = box_curve.row(align=True)
            icon = 'TRIA_DOWN' if props.show_curve_editor else 'TRIA_RIGHT'
            row.prop(props, "show_curve_editor", text="Curve Editor",
                     icon=icon, emboss=False)

            if props.show_curve_editor:
                brush = _get_curve_mapping()
                if brush:
                    box_curve.label(text="X = position (A\u2192B)   Y = weight value", icon='INFO')
                    box_curve.template_curve_mapping(brush, "curve")
                    box_curve.operator("mesh.wg_init_curve_from_anchors", icon='ANCHOR_CENTER')
                else:
                    box_curve.label(text="Apply a preset to initialise the curve", icon='INFO')

            # Presets
            sub_box = box_curve.box()
            sub_box.label(text="Presets:")
            row = sub_box.row(align=True)
            for key in ('LINEAR', 'EASE_IN', 'EASE_OUT', 'S_CURVE'):
                op = row.operator("mesh.wg_curve_preset", text=key.replace('_', ' ').title())
                op.preset = key
            row = sub_box.row(align=True)
            for key in ('BELL', 'VALLEY', 'STEPS_3', 'SHARP_IN', 'SHARP_OUT'):
                op = row.operator("mesh.wg_curve_preset", text=key.replace('_', ' ').title())
                op.preset = key

            # Saved curves
            sub_box = box_curve.box()
            row = sub_box.row(align=True)
            row.label(text="Saved Curves", icon='CURVE_DATA')
            sub_box.template_list(
                "WG_UL_saved_curves", "",
                props, "saved_curves",
                props, "active_curve_index",
                rows=2, maxrows=5,
            )
            row = sub_box.row(align=True)
            row.operator("mesh.wg_save_curve", text="Save", icon='ADD')
            sub = row.row(align=True)
            sub.enabled = len(props.saved_curves) > 0
            op = sub.operator("mesh.wg_load_curve", text="Load", icon='CHECKMARK')
            op.index = props.active_curve_index

        else:  # CONTROL_POINTS
            # Segments + sync + mirror + reset
            row = box_curve.row(align=True)
            row.prop(props, "segments")
            row.operator("mesh.wg_sync_points", text="", icon='FILE_REFRESH')
            row.operator("mesh.wg_reset_cp", text="", icon='LOOP_BACK')
            n_segs = props.segments
            n_pts = len(props.control_points)
            if n_pts >= 2:
                row.prop(props, "mirror", text="", icon='MOD_MIRROR', toggle=True)

            if n_pts != n_segs:
                box_curve.label(text=f"Out of sync ({n_pts}/{n_segs}) — hit refresh", icon='ERROR')

            if n_pts > 0:
                n_total = n_pts + 1
                mirroring = props.mirror and n_pts >= 2
                for i, cp in enumerate(props.control_points):
                    pct = int(round((i + 1) / n_total * 100))
                    mirror_idx = n_pts - 1 - i
                    is_middle = (mirror_idx == i)
                    is_mirrored_slave = mirroring and i > mirror_idx

                    r = box_curve.row(align=True)
                    if mirroring and not is_middle and not is_mirrored_slave:
                        pct2 = int(round((mirror_idx + 1) / n_total * 100))
                        r.label(text="", icon='LINKED')
                        r.prop(cp, "weight", slider=True, text=f"{pct}% + {pct2}%")
                    elif is_mirrored_slave:
                        r.enabled = False
                        r.label(text="", icon='LINKED')
                        r.prop(cp, "weight", slider=True, text=f"{pct}%")
                    elif mirroring and is_middle:
                        r.label(text="", icon='DECORATE')
                        r.prop(cp, "weight", slider=True, text=f"{pct}% (mid)")
                    else:
                        r.prop(cp, "weight", slider=True, text=f"{pct}%")

        # -- Power (always accessible) ----------------------------------
        box_power = layout.box()
        box_power.prop(props, "curve_power", slider=True)

        layout.separator()

        # -- Actions ----------------------------------------------------
        row = layout.row(align=True)
        row.scale_y = 1.5
        row.operator("mesh.wg_apply_gradient", icon='MOD_VERTEX_WEIGHT')

        layout.operator("mesh.wg_clear_anchors", icon='TRASH')

        # -- Saved Anchor Sets ------------------------------------------
        layout.separator()
        box = layout.box()
        row = box.row(align=True)
        icon = 'TRIA_DOWN' if props.show_saved_anchors else 'TRIA_RIGHT'
        row.prop(props, "show_saved_anchors", text="Saved Anchors",
                 icon=icon, emboss=False)

        if props.show_saved_anchors:
            # Groups sub-section
            grp_box = box.box()
            row = grp_box.row(align=True)
            row.label(text="Groups:", icon='FILE_FOLDER')
            row.operator("mesh.wg_add_anchor_group", text="", icon='ADD')
            grp_box.template_list(
                "WG_UL_anchor_groups", "",
                props, "saved_anchor_groups",
                props, "active_anchor_group_index",
                rows=2, maxrows=4,
            )

            n_groups = len(props.saved_anchor_groups)
            if n_groups > 0 and 0 <= props.active_anchor_group_index < n_groups:
                active_grp = props.saved_anchor_groups[props.active_anchor_group_index].name
                box.label(text=f"In '{active_grp}':", icon='FILTER')
            else:
                box.label(text="All anchor sets:")
                n_groups = 0  # disable Assign when no groups exist

            box.template_list(
                "WG_UL_saved_anchor_sets", "",
                props, "saved_anchor_sets",
                props, "active_anchor_set_index",
                rows=2, maxrows=5,
            )

            row = box.row(align=True)
            row.operator("mesh.wg_save_anchor_set", text="Save", icon='ADD')
            sub = row.row(align=True)
            sub.enabled = len(props.saved_anchor_sets) > 0
            op = sub.operator("mesh.wg_load_anchor_set", text="Load", icon='CHECKMARK')
            op.index = props.active_anchor_set_index
            sub2 = row.row(align=True)
            sub2.enabled = (len(props.saved_anchor_sets) > 0 and n_groups > 0)
            op2 = sub2.operator("mesh.wg_assign_to_group", text="Assign", icon='LINK_BLEND')
            op2.set_index = props.active_anchor_set_index

        # -- Saved Selections -------------------------------------------
        layout.separator()
        box = layout.box()
        row = box.row(align=True)
        icon = 'TRIA_DOWN' if props.show_saved_selections else 'TRIA_RIGHT'
        row.prop(props, "show_saved_selections", text="Saved Gradient Vertices",
                 icon=icon, emboss=False)

        if props.show_saved_selections:
            # Groups sub-section
            n_sel_groups = len(props.saved_selection_groups)
            sel_grp_box = box.box()
            row = sel_grp_box.row(align=True)
            row.label(text="Groups:", icon='FILE_FOLDER')
            row.operator("mesh.wg_add_selection_group", text="", icon='ADD')
            sel_grp_box.template_list(
                "WG_UL_selection_groups", "",
                props, "saved_selection_groups",
                props, "active_selection_group_index",
                rows=2, maxrows=4,
            )

            if n_sel_groups > 0 and 0 <= props.active_selection_group_index < n_sel_groups:
                active_sel_grp = props.saved_selection_groups[props.active_selection_group_index].name
                box.label(text=f"In '{active_sel_grp}':", icon='FILTER')
            else:
                box.label(text="All gradient vertices:")
                n_sel_groups = 0  # disable Assign when no groups exist

            box.template_list(
                "WG_UL_saved_selections", "",
                props, "saved_selections",
                props, "active_selection_index",
                rows=3, maxrows=5,
            )

            row = box.row(align=True)
            row.operator("mesh.wg_save_selection", text="Save", icon='ADD')
            sub = row.row(align=True)
            sub.enabled = len(props.saved_selections) > 0
            op = sub.operator("mesh.wg_load_selection", text="Load", icon='CHECKMARK')
            op.index = props.active_selection_index
            sub2 = row.row(align=True)
            sub2.enabled = (len(props.saved_selections) > 0 and n_sel_groups > 0)
            op2 = sub2.operator("mesh.wg_assign_selection_to_group", text="Assign", icon='LINK_BLEND')
            op2.set_index = props.active_selection_index


classes = (
    WG_UL_saved_curves,
    WG_UL_saved_selections,
    WG_UL_selection_groups,
    WG_UL_anchor_groups,
    WG_UL_saved_anchor_sets,
    VIEW3D_PT_weight_gradient,
)
