# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
from bpy.props import StringProperty, BoolProperty, CollectionProperty, EnumProperty
from bpy.types import PropertyGroup

from .utils import refresh_switcher


class SwitcherActionItem(PropertyGroup):
    name: StringProperty()
    action_name: StringProperty()
    is_active: BoolProperty(default=False)
    has_fake_user: BoolProperty(default=False)
    track_name: StringProperty(default="")


class ActionListItem(PropertyGroup):
    name: StringProperty()
    selected: BoolProperty(default=False)
    original_name: StringProperty()


class ArmaReforgerNLAProperties(PropertyGroup):
    asset_prefix: StringProperty(
        name="Asset Prefix",
        description="Prefix for your asset (e.g., M50, UAZ469, Door01)",
        default="M50"
    )

    asset_type: EnumProperty(
        name="Asset Type",
        description="Type of asset being worked on",
        items=[
            ('WEAPON', "Weapon", "Weapon animations (Pl_ prefix)"),
            ('VEHICLE', "Vehicle", "Vehicle animations (v_ prefix)"),
            ('PROP', "Prop", "Prop/object animations (prop_ prefix)"),
            ('CUSTOM', "Custom", "Custom prefix pattern"),
        ],
        default='WEAPON'
    )

    set_active_action: BoolProperty(
        name="Set First as Active",
        description="After processing, set the first new action as the active action",
        default=True
    )

    # Filter options
    show_generated: BoolProperty(
        name="Show Generated",
        description="Show generated actions in source list",
        default=False
    )

    # Search functionality — uses refresh_switcher directly to avoid bpy.ops in callbacks
    search_filter: StringProperty(
        name="Search",
        description="Filter animations by name",
        default="",
        update=lambda self, context: refresh_switcher(context.scene, context)
    )

    action_list: CollectionProperty(type=ActionListItem)
    action_list_index: bpy.props.IntProperty(default=0)

    switcher_actions: CollectionProperty(type=SwitcherActionItem)
    switcher_index: bpy.props.IntProperty(default=-1)


classes = (
    SwitcherActionItem,
    ActionListItem,
    ArmaReforgerNLAProperties,
)
