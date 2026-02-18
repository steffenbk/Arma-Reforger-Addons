# SPDX-License-Identifier: GPL-2.0-or-later

import re


def generate_new_action_name(original_name, prefix, asset_type):
    """Generate new action name based on asset type and prefix"""
    if not prefix:
        return original_name + "_custom"

    # Asset type specific patterns
    if asset_type == 'WEAPON':
        patterns = [
            (r'^p_([^_]+)_(.+)$', f'Pl_{prefix}_\\2'),
            (r'^p_rfl_([^_]+)_(.+)$', f'Pl_rfl_{prefix}_\\2'),
            (r'^p_pst_([^_]+)_(.+)$', f'Pl_pst_{prefix}_\\2'),
        ]
        fallback_prefix = f'Pl_{prefix}_'
    elif asset_type == 'VEHICLE':
        patterns = [
            (r'^v_([^_]+)_(.+)$', f'v_{prefix}_\\2'),
            (r'^veh_([^_]+)_(.+)$', f'veh_{prefix}_\\2'),
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

    # Try pattern matching first
    for pattern, replacement in patterns:
        match = re.match(pattern, original_name, re.IGNORECASE)
        if match:
            new_name = re.sub(pattern, replacement, original_name, flags=re.IGNORECASE)
            return new_name

    # Fallback: prepend asset-specific prefix
    return f'{fallback_prefix}{original_name}'


def get_exclude_patterns(prefix, asset_type):
    """Get patterns to exclude from source action list (these are generated actions)"""
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
    """Get patterns to INCLUDE in switcher (these are the generated actions we want to show)"""
    # This is the same as exclude patterns - we want to show what we exclude from sources
    return get_exclude_patterns(prefix, asset_type)
