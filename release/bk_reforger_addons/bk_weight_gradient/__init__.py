# SPDX-License-Identifier: GPL-2.0-or-later

"""
BK Weight Gradient

Apply weight gradients between anchor vertices with selectable curve types.
Set anchor points (2–10), assign weight values, then apply a gradient across
selected vertices for fast, precise weight painting.
"""

bl_info = {
    "name": "BK Weight Gradient",
    "author": "steffenbk",
    "version": (2, 2, 1),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > BK Tools",
    "description": "Apply weight gradients between anchor vertices with selectable curves",
    "category": "Mesh",
    "support": 'COMMUNITY',
    "doc_url": "",
    "tracker_url": "",
}

import bpy
from bpy.props import PointerProperty

from .properties import classes as property_classes, WeightGradientProperties
from .operators import classes as operator_classes
from .ui.panels import classes as ui_classes
from .utils import _ensure_anchors

classes = (
    *property_classes,
    *operator_classes,
    *ui_classes,
)


@bpy.app.handlers.persistent
def _wg_load_post(_dummy=None):
    """Ensure every scene has its anchors collection populated after file load."""
    for scene in bpy.data.scenes:
        props = scene.weight_gradient
        _ensure_anchors(props)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.weight_gradient = PointerProperty(type=WeightGradientProperties)
    bpy.app.handlers.load_post.append(_wg_load_post)
    bpy.app.timers.register(lambda: (_wg_load_post(), None)[-1], first_interval=0.0)


def unregister():
    if _wg_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_wg_load_post)
    del bpy.types.Scene.weight_gradient
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
