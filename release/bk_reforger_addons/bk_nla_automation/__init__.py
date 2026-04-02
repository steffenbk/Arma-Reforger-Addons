# SPDX-License-Identifier: GPL-2.0-or-later

bl_info = {
    "name": "BK NLA Automation",
    "author": "steffenbk",
    "version": (2, 2, 5),
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

_syncing = False


def _sync_secondary_handler(scene, depsgraph=None):
    """Keep secondary armature action in sync with the main armature."""
    global _syncing
    if _syncing:
        return

    arma_props = getattr(scene, 'arma_nla_props', None)
    if not arma_props:
        return

    main = arma_props.target_armature
    secondary = arma_props.secondary_armature
    if not main or not secondary or main == secondary:
        return
    if not main.animation_data or not main.animation_data.action:
        return

    target_action = main.animation_data.action

    if not secondary.animation_data:
        secondary.animation_data_create()

    if secondary.animation_data.action is not target_action:
        _syncing = True
        secondary.animation_data.action = target_action
        _syncing = False


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.arma_nla_props = bpy.props.PointerProperty(type=ArmaReforgerNLAProperties)
    if _sync_secondary_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_sync_secondary_handler)


def unregister():
    if _sync_secondary_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_sync_secondary_handler)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    if hasattr(bpy.types.Scene, 'arma_nla_props'):
        del bpy.types.Scene.arma_nla_props


if __name__ == "__main__":
    register()
