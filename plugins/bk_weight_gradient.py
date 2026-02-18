# SPDX-License-Identifier: GPL-2.0-or-later

"""
BK Weight Gradient

Apply weight gradients between two anchor vertices with selectable curve types.
Select two anchor points, assign weight values, then apply a gradient across
selected vertices for fast, precise weight painting.
"""

bl_info = {
    "name": "BK Weight Gradient",
    "author": "steffenbk",
    "version": (1, 1, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > BK Tools",
    "description": "Apply weight gradients between two anchor vertices with selectable curves",
    "category": "Mesh",
    "support": 'COMMUNITY',
    "doc_url": "",
    "tracker_url": "",
}

import json

import bpy
import bmesh
from mathutils import Vector
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import (
    FloatProperty, IntProperty, BoolProperty,
    EnumProperty, PointerProperty, FloatVectorProperty,
    CollectionProperty,
)


# ---------------------------------------------------------------------------
# Curve helpers
# ---------------------------------------------------------------------------

def curve_linear(t):
    return t

def curve_ease_in(t):
    return t * t

def curve_ease_out(t):
    return 1.0 - (1.0 - t) * (1.0 - t)

def curve_ease_in_out(t):
    return 3.0 * t * t - 2.0 * t * t * t

def curve_sharp(t):
    return t ** 0.5

def curve_custom_power(t, power):
    return t ** power


CURVE_FUNCS = {
    'LINEAR': curve_linear,
    'EASE_IN': curve_ease_in,
    'EASE_OUT': curve_ease_out,
    'EASE_IN_OUT': curve_ease_in_out,
    'SHARP': curve_sharp,
}


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------

_mirror_updating = False  # guard against recursive update


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
    # Find our index
    my_idx = -1
    for i in range(n):
        if pts[i] == self:
            my_idx = i
            break
    if my_idx < 0:
        return
    mirror_idx = n - 1 - my_idx
    if mirror_idx == my_idx:
        return  # middle point, no pair
    _mirror_updating = True
    pts[mirror_idx].weight = self.weight
    _mirror_updating = False


class WG_ControlPoint(PropertyGroup):
    weight: FloatProperty(
        name="Weight", default=0.5, min=0.0, max=1.0,
        description="Weight at this control point",
        update=_on_cp_weight_update,
    )


def _on_segments_update(self, context):
    """Resize the control_points collection when count changes."""
    n_needed = self.segments
    n_total = n_needed + 1  # total segments = control points + 1
    pts = self.control_points

    # Grow — auto-fill with linear interpolation
    wa = self.anchor_a_weight
    wb = self.anchor_b_weight
    while len(pts) < n_needed:
        item = pts.add()
        i = len(pts) - 1
        t = (i + 1) / n_total
        item.weight = round(wa + (wb - wa) * t, 4)

    # Shrink
    while len(pts) > n_needed:
        pts.remove(len(pts) - 1)


class WeightGradientProperties(PropertyGroup):
    # Stored as JSON strings so we can hold variable-length index lists
    anchor_a_indices: bpy.props.StringProperty(name="Anchor A Indices", default="")
    anchor_b_indices: bpy.props.StringProperty(name="Anchor B Indices", default="")

    anchor_a_co: FloatVectorProperty(name="Anchor A Position", size=3)
    anchor_b_co: FloatVectorProperty(name="Anchor B Position", size=3)

    anchor_a_set: BoolProperty(name="Anchor A Set", default=False)
    anchor_b_set: BoolProperty(name="Anchor B Set", default=False)

    anchor_a_count: IntProperty(name="Anchor A Vertex Count", default=0)
    anchor_b_count: IntProperty(name="Anchor B Vertex Count", default=0)

    anchor_a_weight: FloatProperty(
        name="Weight A", default=1.0, min=0.0, max=1.0,
        description="Weight value at Anchor A",
    )
    anchor_b_weight: FloatProperty(
        name="Weight B", default=0.0, min=0.0, max=1.0,
        description="Weight value at Anchor B",
    )

    segments: IntProperty(
        name="Control Points",
        default=0, min=0, max=20,
        description="Number of control points between anchors (0 = simple A to B)",
        update=_on_segments_update,
    )

    control_points: CollectionProperty(type=WG_ControlPoint)

    mirror: BoolProperty(
        name="Mirror",
        default=False,
        description="Lock symmetric control points so they stay in sync (1+last, 2+second-last, etc.)",
        update=lambda self, ctx: _on_mirror_toggle(self, ctx),
    )

    curve_type: EnumProperty(
        name="Curve",
        items=[
            ('LINEAR', "Linear", "Straight-line interpolation"),
            ('EASE_IN', "Ease In", "Slow start, fast end (t squared)"),
            ('EASE_OUT', "Ease Out", "Fast start, slow end"),
            ('EASE_IN_OUT', "Ease In/Out", "Smooth S-curve (smoothstep)"),
            ('SHARP', "Sharp", "Fast ramp then plateau (sqrt)"),
            ('CUSTOM_POWER', "Custom Power", "t raised to a custom exponent"),
        ],
        default='LINEAR',
    )

    curve_power: FloatProperty(
        name="Power", default=2.0, min=0.1, max=10.0,
        description="Exponent for the custom power curve",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_selected_verts(context):
    """Return list of selected vertex indices and their average world position, or ([], None)."""
    obj = context.active_object
    if obj is None or obj.type != 'MESH':
        return [], None
    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    sel = [v for v in bm.verts if v.select]
    if not sel:
        return [], None
    indices = [v.index for v in sel]
    avg = sum((obj.matrix_world @ v.co for v in sel), Vector((0, 0, 0))) / len(sel)
    return indices, avg


def _parse_indices(json_str):
    """Parse a JSON string of indices back to a set of ints."""
    if not json_str:
        return set()
    try:
        return set(json.loads(json_str))
    except (json.JSONDecodeError, TypeError):
        return set()


def _paint_anchor_verts(context, indices, weight):
    """Immediately paint the weight onto anchor vertices so the user sees feedback."""
    obj = context.active_object
    if not obj or not obj.vertex_groups or not obj.vertex_groups.active:
        return
    vg = obj.vertex_groups.active
    idx_set = set(indices)
    bpy.ops.object.mode_set(mode='OBJECT')
    for v in obj.data.vertices:
        if v.index in idx_set:
            vg.add([v.index], weight, 'REPLACE')
    bpy.ops.object.mode_set(mode='EDIT')


def _on_mirror_toggle(props, context):
    """When mirror is turned on, sync pairs using the first-half values."""
    if not props.mirror:
        return
    pts = props.control_points
    n = len(pts)
    global _mirror_updating
    _mirror_updating = True
    for i in range(n // 2):
        pts[n - 1 - i].weight = pts[i].weight
    _mirror_updating = False


def _build_stops(props):
    """Build the list of (position, weight) stops from anchors + control points."""
    wa = props.anchor_a_weight
    wb = props.anchor_b_weight
    n_pts = len(props.control_points)
    n_total = n_pts + 1  # total segments between A and B
    stops = [(0.0, wa)]
    for i, cp in enumerate(props.control_points):
        stops.append(((i + 1) / n_total, cp.weight))
    stops.append((1.0, wb))
    return stops


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------

class MESH_OT_wg_set_anchor_a(Operator):
    """Store selected vertices as Anchor A (averaged position)"""
    bl_idname = "mesh.wg_set_anchor_a"
    bl_label = "Set Anchor A"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object is not None
                and context.active_object.type == 'MESH'
                and context.mode == 'EDIT_MESH')

    def execute(self, context):
        indices, avg_co = _get_selected_verts(context)
        if not indices:
            self.report({'WARNING'}, "Select at least one vertex")
            return {'CANCELLED'}

        props = context.scene.weight_gradient
        props.anchor_a_indices = json.dumps(indices)
        props.anchor_a_co = avg_co
        props.anchor_a_set = True
        props.anchor_a_count = len(indices)
        _paint_anchor_verts(context, indices, props.anchor_a_weight)
        self.report({'INFO'}, f"Anchor A set ({len(indices)} vert{'s' if len(indices) > 1 else ''}) weight {props.anchor_a_weight:.2f}")
        return {'FINISHED'}


class MESH_OT_wg_set_anchor_b(Operator):
    """Store selected vertices as Anchor B (averaged position)"""
    bl_idname = "mesh.wg_set_anchor_b"
    bl_label = "Set Anchor B"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object is not None
                and context.active_object.type == 'MESH'
                and context.mode == 'EDIT_MESH')

    def execute(self, context):
        indices, avg_co = _get_selected_verts(context)
        if not indices:
            self.report({'WARNING'}, "Select at least one vertex")
            return {'CANCELLED'}

        props = context.scene.weight_gradient
        props.anchor_b_indices = json.dumps(indices)
        props.anchor_b_co = avg_co
        props.anchor_b_set = True
        props.anchor_b_count = len(indices)
        _paint_anchor_verts(context, indices, props.anchor_b_weight)
        self.report({'INFO'}, f"Anchor B set ({len(indices)} vert{'s' if len(indices) > 1 else ''}) weight {props.anchor_b_weight:.2f}")
        return {'FINISHED'}


class MESH_OT_wg_apply_gradient(Operator):
    """Apply weight gradient to selected vertices between the two anchors"""
    bl_idname = "mesh.wg_apply_gradient"
    bl_label = "Apply Gradient"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if not (context.active_object and context.active_object.type == 'MESH'
                and context.mode == 'EDIT_MESH'):
            return False
        props = context.scene.weight_gradient
        return props.anchor_a_set and props.anchor_b_set

    def execute(self, context):
        obj = context.active_object
        me = obj.data
        props = context.scene.weight_gradient

        # Vertex group --------------------------------------------------
        if not obj.vertex_groups:
            self.report({'WARNING'}, "No vertex groups on this object")
            return {'CANCELLED'}
        vg = obj.vertex_groups.active
        if vg is None:
            self.report({'WARNING'}, "No active vertex group")
            return {'CANCELLED'}

        # Anchor data ---------------------------------------------------
        anchor_a_ids = _parse_indices(props.anchor_a_indices)
        anchor_b_ids = _parse_indices(props.anchor_b_indices)

        a_co = Vector(props.anchor_a_co)
        b_co = Vector(props.anchor_b_co)
        ab = b_co - a_co
        ab_len_sq = ab.length_squared

        if ab_len_sq < 1e-10:
            self.report({'WARNING'}, "Anchors are at the same position")
            return {'CANCELLED'}

        # Curve function ------------------------------------------------
        curve = props.curve_type
        if curve == 'CUSTOM_POWER':
            power = props.curve_power
            def apply_curve(t):
                return curve_custom_power(t, power)
        else:
            apply_curve = CURVE_FUNCS[curve]

        wa = props.anchor_a_weight
        wb = props.anchor_b_weight
        stops = _build_stops(props)

        # Switch to object mode so vg.add() works ----------------------
        bpy.ops.object.mode_set(mode='OBJECT')

        count = 0
        for v in me.vertices:
            if not v.select:
                continue

            if v.index in anchor_a_ids:
                weight = wa
            elif v.index in anchor_b_ids:
                weight = wb
            else:
                v_world = obj.matrix_world @ v.co
                # Project onto line A->B  (t: 0 at A, 1 at B)
                t = (v_world - a_co).dot(ab) / ab_len_sq
                t = max(0.0, min(1.0, t))

                # Find which segment this t falls in
                weight = stops[-1][1]  # fallback
                for i in range(len(stops) - 1):
                    t0, w0 = stops[i]
                    t1, w1 = stops[i + 1]
                    if t <= t1 or i == len(stops) - 2:
                        seg_len = t1 - t0
                        seg_t = (t - t0) / seg_len if seg_len > 1e-10 else 0.0
                        seg_t = max(0.0, min(1.0, seg_t))
                        seg_t = apply_curve(seg_t)
                        weight = w0 + (w1 - w0) * seg_t
                        break

            vg.add([v.index], weight, 'REPLACE')
            count += 1

        # Return to edit mode -------------------------------------------
        bpy.ops.object.mode_set(mode='EDIT')
        self.report({'INFO'}, f"Gradient applied to {count} vertices")
        return {'FINISHED'}


class MESH_OT_wg_clear_anchors(Operator):
    """Clear both anchor points"""
    bl_idname = "mesh.wg_clear_anchors"
    bl_label = "Clear Anchors"
    bl_options = {'REGISTER'}

    def execute(self, context):
        props = context.scene.weight_gradient
        props.anchor_a_set = False
        props.anchor_b_set = False
        props.anchor_a_indices = ""
        props.anchor_b_indices = ""
        props.anchor_a_count = 0
        props.anchor_b_count = 0
        self.report({'INFO'}, "Anchors cleared")
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# Panel
# ---------------------------------------------------------------------------

class VIEW3D_PT_weight_gradient(Panel):
    bl_label = "Weight Gradient"
    bl_idname = "VIEW3D_PT_weight_gradient"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "BK Tools"

    @classmethod
    def poll(cls, context):
        return (context.active_object is not None
                and context.active_object.type == 'MESH')

    def draw(self, context):
        layout = self.layout
        props = context.scene.weight_gradient
        obj = context.active_object

        # -- Anchor A ---------------------------------------------------
        box = layout.box()
        row = box.row(align=True)
        row.operator("mesh.wg_set_anchor_a", icon='VERTEXSEL')
        if props.anchor_a_set:
            n = props.anchor_a_count
            row.label(text=f"{n} vert{'s' if n > 1 else ''}", icon='CHECKMARK')
        else:
            row.label(text="Not set", icon='X')
        box.prop(props, "anchor_a_weight", slider=True)

        # -- Anchor B ---------------------------------------------------
        box = layout.box()
        row = box.row(align=True)
        row.operator("mesh.wg_set_anchor_b", icon='VERTEXSEL')
        if props.anchor_b_set:
            n = props.anchor_b_count
            row.label(text=f"{n} vert{'s' if n > 1 else ''}", icon='CHECKMARK')
        else:
            row.label(text="Not set", icon='X')
        box.prop(props, "anchor_b_weight", slider=True)

        # -- Control Points ---------------------------------------------
        box = layout.box()
        row = box.row(align=True)
        row.prop(props, "segments")
        n_segs = props.segments
        n_pts = len(props.control_points)
        if n_pts >= 2:
            row.prop(props, "mirror", text="", icon='MOD_MIRROR', toggle=True)

        if n_pts > 0:
            n_total = n_pts + 1  # total segments
            mirroring = props.mirror and n_pts >= 2
            for i, cp in enumerate(props.control_points):
                pct = int(round((i + 1) / n_total * 100))
                mirror_idx = n_pts - 1 - i
                is_middle = (mirror_idx == i)
                is_mirrored_slave = mirroring and i > mirror_idx

                r = box.row(align=True)
                if mirroring and not is_middle and not is_mirrored_slave:
                    pct2 = int(round((mirror_idx + 1) / n_total * 100))
                    r.label(text="", icon='LINKED')
                    r.prop(cp, "weight", slider=True, text=f"{pct}% + {pct2}%")
                elif is_mirrored_slave:
                    r.enabled = False
                    r.label(text="", icon='LINKED')
                    r.prop(cp, "weight", slider=True, text=f"{pct}%")
                elif mirroring and is_middle:
                    r.label(text="", icon='DECORATE')
                    r.prop(cp, "weight", slider=True, text=f"{pct}% (mid)")
                else:
                    r.prop(cp, "weight", slider=True, text=f"{pct}%")

        layout.separator()

        # -- Vertex group -----------------------------------------------
        if obj.vertex_groups:
            layout.prop_search(obj.vertex_groups, "active", obj, "vertex_groups", text="Group")
        else:
            layout.label(text="No vertex groups", icon='ERROR')

        # -- Curve type -------------------------------------------------
        layout.prop(props, "curve_type")
        if props.curve_type == 'CUSTOM_POWER':
            layout.prop(props, "curve_power", slider=True)

        layout.separator()

        # -- Actions ----------------------------------------------------
        row = layout.row(align=True)
        row.scale_y = 1.5
        row.operator("mesh.wg_apply_gradient", icon='MOD_VERTEX_WEIGHT')

        layout.operator("mesh.wg_clear_anchors", icon='TRASH')


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

classes = (
    WG_ControlPoint,
    WeightGradientProperties,
    MESH_OT_wg_set_anchor_a,
    MESH_OT_wg_set_anchor_b,
    MESH_OT_wg_apply_gradient,
    MESH_OT_wg_clear_anchors,
    VIEW3D_PT_weight_gradient,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.weight_gradient = PointerProperty(type=WeightGradientProperties)


def unregister():
    del bpy.types.Scene.weight_gradient
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
