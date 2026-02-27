# SPDX-License-Identifier: GPL-2.0-or-later

import re
import bpy


def get_armature(context):
    """Return the active armature, or the first armature in the scene."""
    if context.active_object and context.active_object.type == 'ARMATURE':
        return context.active_object
    for obj in context.scene.objects:
        if obj.type == 'ARMATURE':
            return obj
    return None


def get_type_prefix(asset_type, prefix):
    """Return the full name prefix string for the given asset type (e.g. 'Pl_M50_')."""
    if asset_type == 'WEAPON':
        return f"Pl_{prefix}_"
    elif asset_type == 'VEHICLE':
        return f"v_{prefix}_"
    elif asset_type == 'PROP':
        return f"prop_{prefix}_"
    else:  # CUSTOM
        return f"{prefix}_"


def generate_new_action_name(original_name, prefix, asset_type):
    """Generate new action name based on asset type and prefix."""
    if not prefix:
        return original_name + "_custom"

    # Specific patterns must come before generic ones to avoid early matching.
    if asset_type == 'WEAPON':
        patterns = [
            (r'^p_rfl_([^_]+)_(.+)$', f'Pl_rfl_{prefix}_\\2'),
            (r'^p_pst_([^_]+)_(.+)$', f'Pl_pst_{prefix}_\\2'),
            (r'^p_([^_]+)_(.+)$', f'Pl_{prefix}_\\2'),
        ]
        fallback_prefix = f'Pl_{prefix}_'
    elif asset_type == 'VEHICLE':
        patterns = [
            (r'^veh_([^_]+)_(.+)$', f'veh_{prefix}_\\2'),
            (r'^v_([^_]+)_(.+)$', f'v_{prefix}_\\2'),
        ]
        fallback_prefix = f'v_{prefix}_'
    elif asset_type == 'PROP':
        patterns = [
            (r'^prop_([^_]+)_(.+)$', f'prop_{prefix}_\\2'),
            (r'^p_([^_]+)_(.+)$', f'p_{prefix}_\\2'),
        ]
        fallback_prefix = f'prop_{prefix}_'
    else:  # CUSTOM
        patterns = []
        fallback_prefix = f'{prefix}_'

    for pattern, replacement in patterns:
        if re.match(pattern, original_name, re.IGNORECASE):
            return re.sub(pattern, replacement, original_name, flags=re.IGNORECASE)

    return f'{fallback_prefix}{original_name}'


def get_exclude_patterns(prefix, asset_type):
    """Get patterns to exclude from source action list (these are generated actions)."""
    if not prefix:
        return []

    if asset_type == 'WEAPON':
        return [
            f"Pl_{prefix}_",
            f"Pl_rfl_{prefix}_",
            f"Pl_pst_{prefix}_",
        ]
    elif asset_type == 'VEHICLE':
        return [
            f"v_{prefix}_",
            f"veh_{prefix}_",
        ]
    elif asset_type == 'PROP':
        return [
            f"prop_{prefix}_",
            f"p_{prefix}_",
        ]
    else:  # CUSTOM
        return [f"{prefix}_"]


def get_include_patterns(prefix, asset_type):
    """Get patterns to INCLUDE in switcher (the generated actions we want to show)."""
    return get_exclude_patterns(prefix, asset_type)


def do_switch_animation(context, action_name):
    """Switch armature active action and manage NLA tracks. Caller is responsible for refresh_switcher."""
    armature = get_armature(context)
    if not armature or not armature.animation_data:
        return False
    action = bpy.data.actions.get(action_name)
    if not action:
        return False

    armature.animation_data.action = action

    target_track_name = f"{action_name}_track"
    target_track = None

    for track in armature.animation_data.nla_tracks:
        if track.name == target_track_name:
            target_track = track
            track.mute = False
            track.select = True
        else:
            track.mute = True
            track.select = False
            for strip in track.strips:
                strip.select = False

    if target_track:
        armature.animation_data.nla_tracks.active = target_track
        for strip in target_track.strips:
            strip.select = True

    for area in context.screen.areas:
        if area.type == 'NLA_EDITOR':
            area.tag_redraw()

    return True


def refresh_switcher(scene, context):
    """Populate switcher_actions from bpy.data.actions. Use instead of bpy.ops.arma.update_switcher."""
    arma_props = scene.arma_nla_props
    arma_props.switcher_actions.clear()

    prefix = arma_props.asset_prefix.strip()
    asset_type = arma_props.asset_type
    search_term = arma_props.search_filter.lower()

    if not prefix:
        return

    include_patterns = get_include_patterns(prefix, asset_type)

    current_action = None
    armature = get_armature(context)
    if armature and armature.animation_data and armature.animation_data.action:
        current_action = armature.animation_data.action.name

    for action in sorted(bpy.data.actions, key=lambda x: x.name):
        if not any(action.name.startswith(p) for p in include_patterns):
            continue
        if search_term and search_term not in action.name.lower():
            continue

        item = arma_props.switcher_actions.add()
        item.name = action.name
        item.action_name = action.name
        item.is_active = (action.name == current_action)
        item.has_fake_user = action.use_fake_user
        item.track_name = f"{action.name}_track"
