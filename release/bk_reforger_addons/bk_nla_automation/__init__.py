# SPDX-License-Identifier: GPL-2.0-or-later

bl_info = {
    "name": "BK NLA Automation",
    "author": "steffenbk",
    "version": (2, 2, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > BK NLA",
    "description": "Automate NLA strip creation and action management for any Arma Reforger asset",
    "category": "Animation",
}

import bpy

from .properties import classes as property_classes, ArmaReforgerNLAProperties
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
    bpy.types.Scene.arma_nla_props = bpy.props.PointerProperty(type=ArmaReforgerNLAProperties)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    if hasattr(bpy.types.Scene, 'arma_nla_props'):
        del bpy.types.Scene.arma_nla_props


if __name__ == "__main__":
    register()
