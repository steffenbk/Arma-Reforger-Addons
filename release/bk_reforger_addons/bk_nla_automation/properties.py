# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
from bpy.props import (
    StringProperty, BoolProperty, CollectionProperty,
    EnumProperty, FloatVectorProperty, PointerProperty,
)
from bpy.types import PropertyGroup

from .utils import refresh_switcher, do_switch_animation


def _on_switcher_index_changed(props, context):
    idx = props.switcher_index
    if 0 <= idx < len(props.switcher_actions):
        action_name = props.switcher_actions[idx].action_name
        if do_switch_animation(context, action_name):
            refresh_switcher(context.scene, context)


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
    target_armature: PointerProperty(
        name="Armature",
        description="Main armature the NLA plugin operates on. Set automatically on first Process",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'ARMATURE',
    )

    secondary_armature: PointerProperty(
        name="Secondary Rig",
        description="Optional secondary armature (e.g. weapon, prop). When set, the active action is synced to it so its bone keyframes go into the same action",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'ARMATURE',
    )

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
    switcher_index: bpy.props.IntProperty(
        default=-1,
        update=lambda self, context: _on_switcher_index_changed(self, context)
    )

    # Location copy/paste for quick bone positioning between strips
    loc_stored: FloatVectorProperty(name="Stored Location", size=3)
    loc_source_name: StringProperty(name="Source", default="")
    loc_copy_x: BoolProperty(name="X", default=True)
    loc_copy_y: BoolProperty(name="Y", default=True)
    loc_copy_z: BoolProperty(name="Z", default=True)


classes = (
    SwitcherActionItem,
    ActionListItem,
    ArmaReforgerNLAProperties,
)
