# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
from bpy.types import Panel


class VIEW3D_PT_arma_reforger_tools(Panel):
    """Arma Reforger Tools Sidebar Panel"""
    bl_label = "BK Exporter"
    bl_idname = "VIEW3D_PT_arma_reforger_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BK Exporter'

    def draw(self, context):
        layout = self.layout

        # Export to Arma button - simplified with no options
        row = layout.row()
        row.scale_y = 2.0  # Make the button even bigger for easy access
        row.operator("export_scene.arma_reforger_asset", text="Export to Arma", icon='EXPORT')

        # Show a small info text that all options are in the export dialog
        box = layout.box()
        box.label(text="Options available in export dialog", icon='INFO')


classes = (
    VIEW3D_PT_arma_reforger_tools,
)
