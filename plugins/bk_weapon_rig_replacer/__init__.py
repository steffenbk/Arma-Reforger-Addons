# SPDX-License-Identifier: GPL-2.0-or-later

bl_info = {
    "name": "BK Weapon Rig Replacer",
    "author": "steffenbk",
    "version": (1, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > BK Rig Replacer",
    "description": "Replace weapons and magazines while preserving constraints",
    "category": "Animation",
    "support": 'COMMUNITY',
}

import bpy
from bpy.props import PointerProperty

from .properties import classes as property_classes, WeaponRigReplacerProperties
from .operators import classes as operator_classes
from .ui.panels import classes as ui_classes

classes = (
    *property_classes,
    *operator_classes,
    *ui_classes,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.weapon_rig_replacer = PointerProperty(type=WeaponRigReplacerProperties)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.weapon_rig_replacer


if __name__ == "__main__":
    register()
