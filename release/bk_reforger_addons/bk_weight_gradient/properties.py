# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
from bpy.types import PropertyGroup
from bpy.props import (
    FloatProperty, IntProperty, BoolProperty,
    EnumProperty, FloatVectorProperty,
    CollectionProperty, StringProperty,
)


_mirror_updating = False  # guard against recursive mirror updates


def _on_cp_weight_update(self, context):
    """Sync mirrored control point when mirror mode is on."""
    global _mirror_updating
    if _mirror_updating:
        return
    props = context.scene.weight_gradient
    if not props.mirror:
        return
    pts = props.control_points
    n = len(pts)
    if n < 2:
        return
    my_idx = next((i for i in range(n) if pts[i] == self), -1)
    if my_idx < 0:
        return
    mirror_idx = n - 1 - my_idx
    if mirror_idx == my_idx:
        return
    _mirror_updating = True
    pts[mirror_idx].weight = self.weight
    _mirror_updating = False


def _on_mirror_toggle(props, context):
    """When mirror is turned on, sync pairs from the first-half values."""
    if not props.mirror:
        return
    pts = props.control_points
    n = len(pts)
    global _mirror_updating
    _mirror_updating = True
    for i in range(n // 2):
        pts[n - 1 - i].weight = pts[i].weight
    _mirror_updating = False


def _on_segments_update(self, context):
    """Resize the control_points collection when segments count changes."""
    n_needed = self.segments
    pts = self.control_points
    anchors = self.anchors
    wa = anchors[0].weight if len(anchors) > 0 else 1.0
    wb = anchors[-1].weight if len(anchors) > 1 else 0.0
    n_total = n_needed + 1
    while len(pts) < n_needed:
        item = pts.add()
        i = len(pts) - 1
        t = (i + 1) / n_total
        item.weight = round(wa + (wb - wa) * t, 4)
    while len(pts) > n_needed:
        pts.remove(len(pts) - 1)


class WG_ControlPoint(PropertyGroup):
    weight: FloatProperty(
        name="Weight", default=0.5, min=0.0, max=1.0,
        description="Weight at this control point",
        update=_on_cp_weight_update,
    )


class WG_Anchor(PropertyGroup):
    indices_json: StringProperty(name="Indices", default="")
    co: FloatVectorProperty(name="Position", size=3)
    weight: FloatProperty(
        name="Weight", default=0.5, min=0.0, max=1.0,
        description="Weight value at this anchor",
    )
    is_set: BoolProperty(name="Is Set", default=False)
    vert_count: IntProperty(name="Vertex Count", default=0)


class WG_AnchorGroup(PropertyGroup):
    name: StringProperty(name="Name", default="Group")


class WG_SavedAnchorSet(PropertyGroup):
    name: StringProperty(name="Name", default="Anchors")
    data_json: StringProperty(name="Data", default="[]")
    anchor_count: IntProperty(name="Anchor Count", default=2)
    group_name: StringProperty(name="Group", default="")
    selected: BoolProperty(name="Selected", default=False)


class WG_SavedCurve(PropertyGroup):
    name: StringProperty(name="Name", default="Curve")
    points_json: StringProperty(name="Points", default="[]")
    point_count: IntProperty(name="Points", default=0)


class WG_SavedSelection(PropertyGroup):
    name: StringProperty(name="Name", default="Selection")
    indices_json: StringProperty(name="Indices", default="[]")
    count: IntProperty(name="Count", default=0)
    group_name: StringProperty(name="Group", default="")


def _on_anchor_count_update(self, context):
    """Grow or shrink the anchors collection to match anchor_count."""
    n = self.anchor_count
    anchors = self.anchors

    while len(anchors) < n:
        anchors.add()

    while len(anchors) > n:
        anchors.remove(len(anchors) - 1)

    for i, a in enumerate(anchors):
        if not a.is_set:
            if n == 1:
                a.weight = 1.0
            else:
                a.weight = round(1.0 - i / (n - 1), 4)


class WeightGradientProperties(PropertyGroup):
    anchors: CollectionProperty(type=WG_Anchor)

    anchor_count: IntProperty(
        name="Anchor Count",
        default=2, min=2, max=10,
        description="Number of anchor points along the gradient (2–10)",
        update=_on_anchor_count_update,
    )

    gradient_source: EnumProperty(
        name="Gradient Source",
        items=[
            ('ANCHORS', "Anchors", "Define gradient direction by placing anchor vertices"),
            ('AXIS',    "Axis",    "Define gradient direction along a world axis"),
        ],
        default='ANCHORS',
    )

    gradient_axis: EnumProperty(
        name="Axis",
        items=[
            ('X',     "+X", "Gradient along positive X"),
            ('Y',     "+Y", "Gradient along positive Y"),
            ('Z',     "+Z", "Gradient along positive Z"),
            ('NEG_X', "-X", "Gradient along negative X"),
            ('NEG_Y', "-Y", "Gradient along negative Y"),
            ('NEG_Z', "-Z", "Gradient along negative Z"),
        ],
        default='Z',
    )

    curve_mode: EnumProperty(
        name="Mode",
        items=[
            ('CONTROL_POINTS', "Control Points",
             "Shape the gradient using manually placed weight stops"),
            ('CURVE_GRAPH', "Curve Graph",
             "Draw the gradient shape using a graphical curve editor"),
        ],
        default='CONTROL_POINTS',
    )

    curve_power: FloatProperty(
        name="Power", default=0.0, min=0.0, max=9.0,
        description=(
            "Post-process power boost applied to the final weight. "
            "0 = no effect, higher = slower start then rush at end"
        ),
    )

    show_curve_editor: BoolProperty(
        name="Show Curve Editor",
        default=False,
        description="Expand the custom curve editor panel",
    )

    saved_curves: CollectionProperty(type=WG_SavedCurve)
    active_curve_index: IntProperty(name="Active Curve", default=0)

    saved_anchor_groups: CollectionProperty(type=WG_AnchorGroup)
    active_anchor_group_index: IntProperty(name="Active Group", default=0)
    show_saved_anchors: BoolProperty(name="Saved Anchors", default=True)

    saved_anchor_sets: CollectionProperty(type=WG_SavedAnchorSet)
    active_anchor_set_index: IntProperty(name="Active Anchor Set", default=0)

    saved_selection_groups: CollectionProperty(type=WG_AnchorGroup)
    active_selection_group_index: IntProperty(name="Active Selection Group", default=0)
    show_saved_selections: BoolProperty(name="Saved Gradient Vertices", default=True)

    saved_selections: CollectionProperty(type=WG_SavedSelection)
    active_selection_index: IntProperty(name="Active Selection", default=0)

    target_vg_name: StringProperty(name="Group", default="")

    segments: IntProperty(
        name="Control Points",
        default=0, min=0, max=20,
        description="Number of evenly-spaced control points between first and last anchors",
        update=_on_segments_update,
    )
    control_points: CollectionProperty(type=WG_ControlPoint)
    mirror: BoolProperty(
        name="Mirror",
        default=False,
        description="Keep symmetric control points in sync (1st+last, 2nd+2nd-last, …)",
        update=lambda self, ctx: _on_mirror_toggle(self, ctx),
    )


classes = (
    WG_ControlPoint,
    WG_Anchor,
    WG_AnchorGroup,
    WG_SavedAnchorSet,
    WG_SavedCurve,
    WG_SavedSelection,
    WeightGradientProperties,
)
