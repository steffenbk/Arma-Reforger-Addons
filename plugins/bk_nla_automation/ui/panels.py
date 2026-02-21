# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
from bpy.types import Panel

from ..utils import generate_new_action_name, get_include_patterns


class ARMA_UL_switcher_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)

            if item.is_active:
                icon = 'RADIOBUT_ON'
                name_row = row.row()
                name_row.alert = True
                props = name_row.operator("arma.switch_animation", text=item.name, icon=icon, emboss=False)
            else:
                icon = 'RADIOBUT_OFF'
                props = row.operator("arma.switch_animation", text=item.name, icon=icon, emboss=False)

            props.action_name = item.action_name

            del_props = row.operator("arma.delete_action", text="", icon='X', emboss=False)
            del_props.action_name = item.action_name


class ARMA_UL_action_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.prop(item, "selected", text="")
            row.label(text=item.name, icon='ACTION')

            scene = context.scene
            arma_props = scene.arma_nla_props
            if arma_props.asset_prefix and item.selected:
                new_name = generate_new_action_name(
                    item.original_name,
                    arma_props.asset_prefix,
                    arma_props.asset_type
                )
                row.label(text=f"→ {new_name}", icon='FORWARD')


class ARMA_PT_nla_panel(Panel):
    bl_label = "Arma NLA Automation"
    bl_idname = "ARMA_PT_nla_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "BK NLA"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        arma_props = scene.arma_nla_props

        # Asset Settings
        box = layout.box()
        box.label(text="Asset Settings", icon='SETTINGS')
        box.prop(arma_props, "asset_type", text="Type")
        box.prop(arma_props, "asset_prefix", text="Prefix")
        box.prop(arma_props, "set_active_action")

        # Action Management
        box = layout.box()
        box.label(text="Source Actions", icon='ACTION')

        row = box.row(align=True)
        row.operator("arma.refresh_actions", icon='FILE_REFRESH')
        row.prop(arma_props, "show_generated", text="", icon='FILTER', toggle=True)

        row = box.row(align=True)
        row.operator("arma.select_all_actions", text="All", icon='CHECKBOX_HLT').select_all = True
        row.operator("arma.select_all_actions", text="None", icon='CHECKBOX_DEHLT').select_all = False

        if arma_props.action_list:
            box.template_list(
                "ARMA_UL_action_list", "",
                arma_props, "action_list",
                arma_props, "action_list_index",
                rows=6
            )
            selected_count = sum(1 for item in arma_props.action_list if item.selected)
            box.label(text=f"Selected: {selected_count}/{len(arma_props.action_list)}", icon='INFO')
        else:
            box.label(text="Click 'Refresh' to load actions")

        # Process Button
        layout.separator()
        col = layout.column()
        col.scale_y = 1.5
        col.operator("arma.process_nla", icon='NLA_PUSHDOWN')

        # Animation Switcher
        layout.separator()
        box = layout.box()

        header_row = box.row(align=True)
        header_row.label(text="Animation Switcher", icon='PLAY')
        header_row.operator("arma.update_switcher", text="", icon='FILE_REFRESH')

        # Search bar
        search_row = box.row(align=True)
        search_row.prop(arma_props, "search_filter", text="", icon='VIEWZOOM')
        if arma_props.search_filter:
            search_row.operator("arma.clear_search", text="", icon='X')

        if arma_props.switcher_actions:
            box.template_list(
                "ARMA_UL_switcher_list", "",
                arma_props, "switcher_actions",
                arma_props, "switcher_index",
                rows=8, maxrows=20
            )
            total_count = len(arma_props.switcher_actions)
            box.label(text=f"{total_count} animations", icon='INFO')
        else:
            if arma_props.asset_prefix:
                patterns = get_include_patterns(arma_props.asset_prefix, arma_props.asset_type)
                if patterns:
                    box.label(text=f"No {patterns[0]}* actions found")
                box.label(text="Process actions first")
            else:
                box.label(text="Set asset prefix above")

            refresh_row = box.row()
            refresh_row.scale_y = 1.2
            refresh_row.operator("arma.update_switcher", text="Load", icon='FILE_REFRESH')

        # Utilities
        layout.separator()
        box = layout.box()
        box.label(text="Utilities", icon='TOOL_SETTINGS')
        box.operator("arma.create_new_action", text="Create New Action", icon='ADD')
        box.operator("arma.cleanup_export_duplicates", text="Clean Up Export Duplicates", icon='TRASH')


classes = (
    ARMA_UL_switcher_list,
    ARMA_UL_action_list,
    ARMA_PT_nla_panel,
)
