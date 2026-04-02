bl_info = {
    "name": "BK Building Tools",
    "author": "steffenbk",
    "version": (2, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > BK Buildings",
    "description": "Tools for preparing buildings for Arma Reforger (components, collisions, BSP, portals, probes)",
    "category": "Object",
}

import bpy

from .operators import (
    ARBUILDINGS_OT_orient_building,
    ARBUILDINGS_OT_separate_component,
    ARBUILDINGS_OT_create_building_socket,
    ARBUILDINGS_OT_create_firegeo_collision,
    ARBUILDINGS_OT_manage_collections,
    ARBUILDINGS_OT_convert_existing_sockets,
    ARBUILDINGS_OT_create_portal,
    ARBUILDINGS_OT_create_probe_volume,
    ARBUILDINGS_OT_create_bsp,
    ARBUILDINGS_OT_fracture_part,
    ARBUILDINGS_OT_suggest_removal,
    ARBUILDINGS_OT_finalize_phase,
    ARBUILDINGS_OT_export_building,
)

from .ui import ARBUILDINGS_PT_panel

classes = (
    ARBUILDINGS_OT_orient_building,
    ARBUILDINGS_OT_separate_component,
    ARBUILDINGS_OT_create_building_socket,
    ARBUILDINGS_OT_create_firegeo_collision,
    ARBUILDINGS_OT_manage_collections,
    ARBUILDINGS_OT_convert_existing_sockets,
    ARBUILDINGS_OT_create_portal,
    ARBUILDINGS_OT_create_probe_volume,
    ARBUILDINGS_OT_create_bsp,
    ARBUILDINGS_OT_fracture_part,
    ARBUILDINGS_OT_suggest_removal,
    ARBUILDINGS_OT_finalize_phase,
    ARBUILDINGS_OT_export_building,
    ARBUILDINGS_PT_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
