bl_info = {
    "name": "BK Arma Tools",
    "author": "steffenbk",
    "version": (3, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > BK Arma Tools",
    "description": "Enhanced tools for preparing and rigging vehicles and weapons for Arma Reforger",
    "category": "Object",
}

import bpy

from .operators import (
    ARVEHICLES_OT_manage_presets,
    ARVEHICLES_OT_preset_separation,
    ARVEHICLES_OT_skip_preset_item,
    ARVEHICLES_OT_reset_preset,
    ARVEHICLES_OT_create_ucx_collision,
    ARVEHICLES_OT_create_firegeo_collision,
    ARVEHICLES_OT_create_wheel_collisions,
    ARVEHICLES_OT_create_center_of_mass,
    ARVEHICLES_OT_create_socket,
    ARVEHICLES_OT_add_to_object,
    ARVEHICLES_OT_separate_components,
    ARVEHICLES_OT_parent_bones,
    ARVEHICLES_OT_add_bone_to_verts,
    ARVEHICLES_OT_create_armature,
    ARVEHICLES_OT_create_bone,
    ARVEHICLES_OT_align_bones_direction,
    ARVEHICLES_OT_setup_skinning,
    ARVEHICLES_OT_parent_to_armature,
    ARVEHICLES_OT_create_empties,
    ARVEHICLES_OT_create_vertex_group,
    ARVEHICLES_OT_cleanup_mesh,
    ARVEHICLES_OT_parent_empties,
    ARVEHICLES_OT_create_lods,
    ARVEHICLES_OT_center_vehicle,
)

from .ui import ARVEHICLES_PT_panel

classes = (
    ARVEHICLES_OT_manage_presets,
    ARVEHICLES_OT_preset_separation,
    ARVEHICLES_OT_create_ucx_collision,
    ARVEHICLES_OT_create_firegeo_collision,
    ARVEHICLES_OT_create_wheel_collisions,
    ARVEHICLES_OT_create_center_of_mass,
    ARVEHICLES_OT_create_socket,
    ARVEHICLES_OT_add_to_object,
    ARVEHICLES_OT_separate_components,
    ARVEHICLES_OT_parent_bones,
    ARVEHICLES_OT_add_bone_to_verts,
    ARVEHICLES_OT_create_armature,
    ARVEHICLES_OT_create_bone,
    ARVEHICLES_OT_align_bones_direction,
    ARVEHICLES_OT_setup_skinning,
    ARVEHICLES_OT_parent_to_armature,
    ARVEHICLES_OT_create_empties,
    ARVEHICLES_OT_create_vertex_group,
    ARVEHICLES_OT_skip_preset_item,
    ARVEHICLES_OT_parent_empties,
    ARVEHICLES_OT_create_lods,
    ARVEHICLES_OT_cleanup_mesh,
    ARVEHICLES_OT_center_vehicle,
    ARVEHICLES_PT_panel,
)

def register():
    # Register scene property for mode switching
    bpy.types.Scene.arvehicles_mode = bpy.props.EnumProperty(
        name="Asset Mode",
        description="Switch between vehicle, weapon, or custom rigging tools",
        items=[
            ('VEHICLE', "Vehicle", "Vehicle rigging mode - bones prefixed with v_"),
            ('WEAPON',  "Weapon",  "Weapon rigging mode - bones prefixed with w_"),
            ('CUSTOM',  "Custom",  "Custom prefix defined by you"),
        ],
        default='VEHICLE',
    )
    bpy.types.Scene.arvehicles_custom_prefix = bpy.props.StringProperty(
        name="Custom Prefix",
        description="Prefix applied to all bones in Custom mode (e.g. 'c_' or 'player_')",
        default="c_",
    )
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.arvehicles_mode
    del bpy.types.Scene.arvehicles_custom_prefix
