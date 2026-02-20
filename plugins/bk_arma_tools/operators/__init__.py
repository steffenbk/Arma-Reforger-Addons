from .presets import (
    ARVEHICLES_OT_manage_presets,
    ARVEHICLES_OT_preset_separation,
    ARVEHICLES_OT_skip_preset_item,
    ARVEHICLES_OT_reset_preset,
    # REMOVE ARVEHICLES_OT_parent_bones FROM HERE
)

from .collisions import (
    ARVEHICLES_OT_create_ucx_collision,
    ARVEHICLES_OT_create_firegeo_collision,
    ARVEHICLES_OT_create_wheel_collisions,
    ARVEHICLES_OT_create_center_of_mass,
)

from .sockets import ARVEHICLES_OT_create_socket, ARVEHICLES_OT_parent_socket_to_bone

from .components import (
    ARVEHICLES_OT_add_to_object,
    ARVEHICLES_OT_separate_components,
    ARVEHICLES_OT_parent_bones,
    ARVEHICLES_OT_add_bone_to_verts,
)

from .armature import (
    ARVEHICLES_OT_create_armature,
    ARVEHICLES_OT_create_bone,
    ARVEHICLES_OT_align_bones_direction,
)

from .misc import (
    ARVEHICLES_OT_setup_skinning,
    ARVEHICLES_OT_parent_to_armature,
    ARVEHICLES_OT_create_empties,
    ARVEHICLES_OT_create_vertex_group,
    ARVEHICLES_OT_cleanup_mesh,
    ARVEHICLES_OT_parent_empties,
    ARVEHICLES_OT_create_lods,
    ARVEHICLES_OT_center_vehicle,
)