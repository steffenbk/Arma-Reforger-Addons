# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
from bpy.types import PropertyGroup
from bpy.props import StringProperty, BoolProperty


class WeaponRigReplacerProperties(PropertyGroup):
    """Properties for the weapon rig replacer tool."""

    weapon_filepath: StringProperty(
        name="Weapon File",
        description="Path to the weapon .blend file",
        default="",
        subtype='FILE_PATH'
    )

    magazine_filepath: StringProperty(
        name="Magazine File",
        description="Path to the magazine .blend file",
        default="",
        subtype='FILE_PATH'
    )

    weapon_name: StringProperty(
        name="Weapon Name",
        description="Name for the imported weapon armature",
        default="Weapon"
    )

    magazine_name: StringProperty(
        name="Magazine Name",
        description="Name for the imported magazine object",
        default="Magazine"
    )

    show_weapon_panel: BoolProperty(
        name="Show Weapon Tools",
        description="Show/hide the weapon replacement tools",
        default=True
    )

    show_magazine_panel: BoolProperty(
        name="Show Magazine Tools",
        description="Show/hide the magazine replacement tools",
        default=True
    )

    show_advanced: BoolProperty(
        name="Show Advanced Options",
        description="Show naming and advanced options",
        default=False
    )


classes = (
    WeaponRigReplacerProperties,
)
