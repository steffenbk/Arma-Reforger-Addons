bl_info = {
    "name": "BK Animation Export Profile",
    "author": "steffenbk",
    "version": (1, 1, 0),
    "blender": (4, 2, 0),
    "location": "3D Viewport > Sidebar > BK Anim Export",
    "description": "Create and manage animation export profiles (.apr) for Arma Reforger",
    "category": "Animation",
}

import bpy
from .properties import classes as _prop_classes, ARPROFILE_PG_settings
from .operators import classes as _op_classes
from .ui.panels import classes as _ui_classes

classes = (
    *_prop_classes,
    *_op_classes,
    *_ui_classes,
)


def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            print(f"Failed to register {cls}: {e}")

    bpy.types.Scene.arprofile_settings = bpy.props.PointerProperty(type=ARPROFILE_PG_settings)


def unregister():
    if hasattr(bpy.types.Scene, 'arprofile_settings'):
        del bpy.types.Scene.arprofile_settings

    for cls in reversed(classes):
        try:
            if hasattr(cls, 'bl_rna'):
                bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"Failed to unregister {cls}: {e}")


if __name__ == "__main__":
    register()
