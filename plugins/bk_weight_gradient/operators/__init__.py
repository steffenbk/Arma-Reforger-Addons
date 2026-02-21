# SPDX-License-Identifier: GPL-2.0-or-later

from .gradient import (
    MESH_OT_wg_set_anchor,
    MESH_OT_wg_select_anchor_verts,
    MESH_OT_wg_apply_gradient,
    MESH_OT_wg_flip_gradient,
    MESH_OT_wg_init_curve_from_anchors,
    MESH_OT_wg_clear_anchors,
    MESH_OT_wg_select_last_gradient,
)
from .curves import (
    MESH_OT_wg_save_curve,
    MESH_OT_wg_load_curve,
    MESH_OT_wg_delete_curve,
    MESH_OT_wg_curve_preset,
    MESH_OT_wg_export_presets,
    MESH_OT_wg_import_presets,
)
from .selections import (
    MESH_OT_wg_save_selection,
    MESH_OT_wg_load_selection,
    MESH_OT_wg_delete_selection,
    MESH_OT_wg_add_selection_group,
    MESH_OT_wg_delete_selection_group,
    MESH_OT_wg_assign_selection_to_group,
)
from .anchor_sets import (
    MESH_OT_wg_save_anchor_set,
    MESH_OT_wg_load_anchor_set,
    MESH_OT_wg_delete_anchor_set,
    MESH_OT_wg_load_checked_anchor_sets,
    MESH_OT_wg_add_anchor_group,
    MESH_OT_wg_delete_anchor_group,
    MESH_OT_wg_assign_to_group,
)
from .control_points import (
    MESH_OT_wg_sync_points,
    MESH_OT_wg_reset_cp,
)
from .remap import (
    MESH_OT_wg_adjust_weights,
)
from .full_presets import (
    MESH_OT_wg_save_full_preset,
    MESH_OT_wg_load_full_preset,
    MESH_OT_wg_delete_full_preset,
)

classes = (
    MESH_OT_wg_set_anchor,
    MESH_OT_wg_select_anchor_verts,
    MESH_OT_wg_apply_gradient,
    MESH_OT_wg_flip_gradient,
    MESH_OT_wg_init_curve_from_anchors,
    MESH_OT_wg_save_curve,
    MESH_OT_wg_load_curve,
    MESH_OT_wg_delete_curve,
    MESH_OT_wg_curve_preset,
    MESH_OT_wg_export_presets,
    MESH_OT_wg_import_presets,
    MESH_OT_wg_save_selection,
    MESH_OT_wg_load_selection,
    MESH_OT_wg_delete_selection,
    MESH_OT_wg_add_selection_group,
    MESH_OT_wg_delete_selection_group,
    MESH_OT_wg_assign_selection_to_group,
    MESH_OT_wg_clear_anchors,
    MESH_OT_wg_save_anchor_set,
    MESH_OT_wg_load_anchor_set,
    MESH_OT_wg_delete_anchor_set,
    MESH_OT_wg_load_checked_anchor_sets,
    MESH_OT_wg_add_anchor_group,
    MESH_OT_wg_delete_anchor_group,
    MESH_OT_wg_assign_to_group,
    MESH_OT_wg_sync_points,
    MESH_OT_wg_reset_cp,
    MESH_OT_wg_adjust_weights,
    MESH_OT_wg_save_full_preset,
    MESH_OT_wg_load_full_preset,
    MESH_OT_wg_delete_full_preset,
    MESH_OT_wg_select_last_gradient,
)
