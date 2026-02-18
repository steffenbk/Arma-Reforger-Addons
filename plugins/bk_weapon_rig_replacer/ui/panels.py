# SPDX-License-Identifier: GPL-2.0-or-later

import os

import bpy
from bpy.types import Panel


class VIEW3D_PT_weapon_rig_replacer(Panel):
    """Panel for the weapon rig replacer tool."""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "BK Rig Replacer"
    bl_label = "Weapon Rig Replacer"

    def draw(self, context) -> None:
        layout = self.layout
        props = context.scene.weapon_rig_replacer

        # Weapon Section
        box = layout.box()
        row = box.row()
        icon = 'DOWNARROW_HLT' if props.show_weapon_panel else 'RIGHTARROW'
        row.prop(props, "show_weapon_panel", text="Weapon Replacement", icon=icon, emboss=False)

        if props.show_weapon_panel:
            col = box.column(align=True)
            col.operator("weaponrig.browse_weapon_file", text="Browse for Weapon File", icon='FILEBROWSER')

            if props.weapon_filepath:
                col.label(text=f"Selected: {os.path.basename(props.weapon_filepath)}", icon='CHECKMARK')

            # Advanced naming options
            if props.show_advanced:
                col.separator()
                col.prop(props, "weapon_name", text="New Name")

            col.separator()
            col.operator("weaponrig.replace_weapon", text="Replace Weapon", icon='MESH_DATA')

        layout.separator()

        # Magazine Section
        box = layout.box()
        row = box.row()
        icon = 'DOWNARROW_HLT' if props.show_magazine_panel else 'RIGHTARROW'
        row.prop(props, "show_magazine_panel", text="Magazine Replacement", icon=icon, emboss=False)

        if props.show_magazine_panel:
            col = box.column(align=True)
            col.operator("weaponrig.browse_magazine_file", text="Browse for Magazine File", icon='FILEBROWSER')

            if props.magazine_filepath:
                col.label(text=f"Selected: {os.path.basename(props.magazine_filepath)}", icon='CHECKMARK')

            # Advanced naming options
            if props.show_advanced:
                col.separator()
                col.prop(props, "magazine_name", text="New Name")

            col.separator()
            col.operator("weaponrig.replace_magazine", text="Replace Magazine", icon='OUTLINER_OB_EMPTY')

        layout.separator()

        # Advanced Options
        box = layout.box()
        row = box.row()
        icon = 'DOWNARROW_HLT' if props.show_advanced else 'RIGHTARROW'
        row.prop(props, "show_advanced", text="Advanced Options", icon=icon, emboss=False)

        layout.separator()

        # Info section
        box = layout.box()
        box.label(text="Instructions:", icon='INFO')
        col = box.column(align=True)
        col.label(text="1. Prepare weapon/magazine files")
        col.label(text="2. Parent all meshes to armatures")
        col.label(text="3. Use browse buttons to select files")
        col.label(text="4. Click replace to swap assets")
        col.separator()
        col.label(text="Check console (Window > Toggle System Console)")
        col.label(text="for detailed import information!")


classes = (
    VIEW3D_PT_weapon_rig_replacer,
)
