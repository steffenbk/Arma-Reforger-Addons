# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty

bl_info = {
    "name": "BK Asset Exporter",
    "author": "steffenbk",
    "version": (1, 4),
    "blender": (4, 0, 0),
    "location": "File > Export > Arma Reforger Asset (.fbx) / Sidebar > BK Exporter",
    "description": "Export assets for Arma Reforger Enfusion Engine",
    "warning": "",
    "doc_url": "",
    "category": "Import-Export",
}

from .operators import classes as operator_classes
from .ui.panels import classes as ui_classes

classes = (
    *operator_classes,
    *ui_classes,
)


def register_properties():
    bpy.types.Scene.ar_export_mode = EnumProperty(
        name="Export Mode",
        items=(
            ('FULL', "Full Scene", "Export the entire scene as one asset"),
            ('INDIVIDUAL', "Individual Parts", "Export selected meshes as individual assets"),
        ),
        default='FULL',
    )

    bpy.types.Scene.ar_apply_transform = BoolProperty(
        name="Apply Transform",
        description="Apply object transformations before export",
        default=True,
    )

    bpy.types.Scene.ar_export_colliders = BoolProperty(
        name="Export Colliders",
        description="Export collision meshes with the objects",
        default=True,
    )

    bpy.types.Scene.ar_preserve_armature = BoolProperty(
        name="Preserve Armature",
        description="Preserve rigging and armature data",
        default=True,
    )

    bpy.types.Scene.ar_center_to_origin = BoolProperty(
        name="Center to Origin",
        description="Center geometry to world origin before export",
        default=True,
    )

    bpy.types.Scene.ar_align_to_axis = BoolProperty(
        name="Align to Axis",
        description="Align objects to specified axis",
        default=True,
    )

    bpy.types.Scene.ar_alignment_axis = EnumProperty(
        name="Alignment Axis",
        items=(
            ('Y', "Y Axis (Default)", "Align to Y axis as required by Enfusion engine"),
            ('X', "X Axis", "Align to X axis"),
            ('Z', "Z Axis", "Align to Z axis"),
            ('CUSTOM', "Custom", "Use custom alignment rotation"),
        ),
        default='Y',
    )

    bpy.types.Scene.ar_custom_rotation_x = FloatProperty(
        name="X Rotation",
        description="Custom X rotation (degrees)",
        default=0.0,
        min=-360.0,
        max=360.0,
        subtype='ANGLE',
    )

    bpy.types.Scene.ar_custom_rotation_y = FloatProperty(
        name="Y Rotation",
        description="Custom Y rotation (degrees)",
        default=0.0,
        min=-360.0,
        max=360.0,
        subtype='ANGLE',
    )

    bpy.types.Scene.ar_custom_rotation_z = FloatProperty(
        name="Z Rotation",
        description="Custom Z rotation (degrees)",
        default=0.0,
        min=-360.0,
        max=360.0,
        subtype='ANGLE',
    )

    bpy.types.Scene.ar_export_path = StringProperty(
        name="Export Folder",
        description="Path to export FBX files",
        default="//",
        subtype='DIR_PATH',
    )


def unregister_properties():
    props_to_remove = [
        'ar_export_mode', 'ar_apply_transform', 'ar_export_colliders',
        'ar_preserve_armature', 'ar_center_to_origin', 'ar_align_to_axis',
        'ar_alignment_axis', 'ar_custom_rotation_x', 'ar_custom_rotation_y',
        'ar_custom_rotation_z', 'ar_export_path'
    ]

    for prop in props_to_remove:
        if hasattr(bpy.types.Scene, prop):
            delattr(bpy.types.Scene, prop)


def menu_func_export(self, context):
    self.layout.operator("export_scene.arma_reforger_asset", text="Arma Reforger Asset (.fbx)")


def register():
    try:
        register_properties()

        for cls in classes:
            bpy.utils.register_class(cls)

        bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

        print("Arma Reforger Asset Exporter registered successfully")
    except Exception as e:
        print(f"Error registering Arma Reforger Asset Exporter: {str(e)}")
        import traceback
        print(traceback.format_exc())


def unregister():
    try:
        bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)

        for cls in reversed(classes):
            bpy.utils.unregister_class(cls)

        unregister_properties()

        print("Arma Reforger Asset Exporter unregistered successfully")
    except Exception as e:
        print(f"Error unregistering Arma Reforger Asset Exporter: {str(e)}")
        import traceback
        print(traceback.format_exc())


if __name__ == "__main__":
    register()
