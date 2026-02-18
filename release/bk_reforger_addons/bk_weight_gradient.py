# SPDX-License-Identifier: GPL-2.0-or-later

"""
BK Weight Gradient

Apply weight gradients between anchor vertices with selectable curve types.
Set anchor points (2–10), assign weight values, then apply a gradient across
selected vertices for fast, precise weight painting.
"""

bl_info = {
    "name": "BK Weight Gradient",
    "author": "steffenbk",
    "version": (2, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > BK Tools",
    "description": "Apply weight gradients between anchor vertices with selectable curves",
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
    CollectionProperty, StringProperty,
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

_WG_BRUSH_NAME = ".WG_CustomCurve"


def _get_curve_mapping():
    """Get or create the hidden brush that hosts our custom CurveMapping."""
    brush = bpy.data.brushes.get(_WG_BRUSH_NAME)
    if not brush:
        brush = bpy.data.brushes.new(_WG_BRUSH_NAME, mode='SCULPT')
        brush.use_fake_user = True
        # Set default curve to linear (0,0) -> (1,1)
        mapping = brush.curve
        mapping.clip_min_x = 0.0
        mapping.clip_min_y = 0.0
        mapping.clip_max_x = 1.0
        mapping.clip_max_y = 1.0
        mapping.use_clip = True
        # Reset to a simple linear curve
        curve = mapping.curves[0]
        # Remove default points and set to linear
        while len(curve.points) > 2:
            curve.points.remove(curve.points[1])
        curve.points[0].location = (0.0, 0.0)
        curve.points[-1].location = (1.0, 1.0)
        mapping.update()
    return brush


# Curve preset definitions: list of (x, y) points
CURVE_PRESETS = {
    'LINEAR':    [(0.0, 0.0), (1.0, 1.0)],
    'EASE_IN':   [(0.0, 0.0), (0.5, 0.1), (1.0, 1.0)],
    'EASE_OUT':  [(0.0, 0.0), (0.5, 0.9), (1.0, 1.0)],
    'S_CURVE':   [(0.0, 0.0), (0.25, 0.05), (0.75, 0.95), (1.0, 1.0)],
    'BELL':      [(0.0, 0.0), (0.25, 0.8), (0.5, 1.0), (0.75, 0.8), (1.0, 0.0)],
    'VALLEY':    [(0.0, 1.0), (0.25, 0.2), (0.5, 0.0), (0.75, 0.2), (1.0, 1.0)],
    'STEPS_3':   [(0.0, 0.0), (0.33, 0.0), (0.34, 0.5), (0.66, 0.5), (0.67, 1.0), (1.0, 1.0)],
    'SHARP_IN':  [(0.0, 0.0), (0.8, 0.0), (1.0, 1.0)],
    'SHARP_OUT': [(0.0, 0.0), (0.2, 1.0), (1.0, 1.0)],
}


def _apply_curve_points(points):
    """Set the hidden brush curve to the given list of (x, y) points."""
    brush = _get_curve_mapping()
    mapping = brush.curve
    curve = mapping.curves[0]

    # Remove all except 2 (minimum Blender allows)
    while len(curve.points) > 2:
        curve.points.remove(curve.points[1])

    # Set first and last
    curve.points[0].location = points[0]
    curve.points[-1].location = points[-1]

    # Add middle points
    for pt in points[1:-1]:
        curve.points.new(pt[0], pt[1])

    mapping.update()


def _apply_curve_preset(preset_key):
    """Set the hidden brush curve to a preset shape."""
    _apply_curve_points(CURVE_PRESETS[preset_key])


def _read_curve_points():
    """Read the current curve points from the brush as a list of (x, y) tuples."""
    brush = _get_curve_mapping()
    curve = brush.curve.curves[0]
    pts = [(p.location[0], p.location[1]) for p in curve.points]
    pts.sort(key=lambda p: p[0])
    return pts


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------

class WG_Anchor(PropertyGroup):
    indices_json: StringProperty(name="Indices", default="")
    co: FloatVectorProperty(name="Position", size=3)
    weight: FloatProperty(
        name="Weight", default=0.5, min=0.0, max=1.0,
        description="Weight value at this anchor",
    )
    is_set: BoolProperty(name="Is Set", default=False)
    vert_count: IntProperty(name="Vertex Count", default=0)


class WG_SavedAnchorSet(PropertyGroup):
    name: StringProperty(name="Name", default="Anchors")
    data_json: StringProperty(name="Data", default="[]")
    anchor_count: IntProperty(name="Anchor Count", default=2)


class WG_SavedCurve(PropertyGroup):
    name: bpy.props.StringProperty(name="Name", default="Curve")
    points_json: bpy.props.StringProperty(name="Points", default="[]")
    point_count: IntProperty(name="Points", default=0)


class WG_SavedSelection(PropertyGroup):
    name: bpy.props.StringProperty(name="Name", default="Selection")
    indices_json: bpy.props.StringProperty(name="Indices", default="[]")
    count: IntProperty(name="Count", default=0)


def _on_anchor_count_update(self, context):
    """Grow or shrink the anchors collection to match anchor_count."""
    n = self.anchor_count
    anchors = self.anchors

    # Grow
    while len(anchors) < n:
        anchors.add()

    # Shrink
    while len(anchors) > n:
        anchors.remove(len(anchors) - 1)

    # Set default weights: first=1.0, last=0.0, middle=linear interpolation
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

    curve_type: EnumProperty(
        name="Curve",
        items=[
            ('LINEAR', "Linear", "Straight-line interpolation"),
            ('EASE_IN', "Ease In", "Slow start, fast end (t squared)"),
            ('EASE_OUT', "Ease Out", "Fast start, slow end"),
            ('EASE_IN_OUT', "Ease In/Out", "Smooth S-curve (smoothstep)"),
            ('SHARP', "Sharp", "Fast ramp then plateau (sqrt)"),
            ('CUSTOM_POWER', "Custom Power", "t raised to a custom exponent"),
            ('CUSTOM_CURVE', "Custom Curve", "User-defined curve with editable points"),
        ],
        default='LINEAR',
    )

    curve_power: FloatProperty(
        name="Power", default=2.0, min=0.1, max=10.0,
        description="Exponent for the custom power curve",
    )

    show_curve_editor: BoolProperty(
        name="Show Curve Editor",
        default=False,
        description="Expand the custom curve editor panel",
    )

    saved_curves: CollectionProperty(type=WG_SavedCurve)
    active_curve_index: IntProperty(name="Active Curve", default=0)

    saved_anchor_sets: CollectionProperty(type=WG_SavedAnchorSet)
    active_anchor_set_index: IntProperty(name="Active Anchor Set", default=0)

    saved_selections: CollectionProperty(type=WG_SavedSelection)
    active_selection_index: IntProperty(name="Active Selection", default=0)


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


def _ensure_anchors(props):
    """Make sure the anchors collection matches anchor_count (e.g. on first access)."""
    n = props.anchor_count
    while len(props.anchors) < n:
        props.anchors.add()
    while len(props.anchors) > n:
        props.anchors.remove(len(props.anchors) - 1)


def _build_stops(props):
    """Build sorted (t, weight) stops by projecting all set anchors onto the first→last line.

    Returns the stops list and the (a_co, ab, ab_len_sq) projection data,
    or (None, None, None, None) if the first/last anchors aren't set or coincide.
    """
    _ensure_anchors(props)
    anchors = props.anchors
    n = len(anchors)
    first = anchors[0]
    last = anchors[n - 1]

    if not first.is_set or not last.is_set:
        return None, None, None, None

    a_co = Vector(first.co)
    b_co = Vector(last.co)
    ab = b_co - a_co
    ab_len_sq = ab.length_squared

    if ab_len_sq < 1e-10:
        return None, None, None, None

    # Build stops: first and last are t=0 and t=1, middle anchors are projected
    stops = [(0.0, first.weight)]

    for i in range(1, n - 1):
        a = anchors[i]
        if not a.is_set:
            continue
        t = (Vector(a.co) - a_co).dot(ab) / ab_len_sq
        t = max(0.0, min(1.0, t))
        stops.append((t, a.weight))

    stops.append((1.0, last.weight))
    stops.sort(key=lambda s: s[0])
    return stops, a_co, ab, ab_len_sq


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------

class MESH_OT_wg_set_anchor(Operator):
    """Store selected vertices as an anchor point (averaged position)"""
    bl_idname = "mesh.wg_set_anchor"
    bl_label = "Set Anchor"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Anchor Index", default=0)

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
        _ensure_anchors(props)

        if self.index < 0 or self.index >= len(props.anchors):
            self.report({'WARNING'}, "Invalid anchor index")
            return {'CANCELLED'}

        a = props.anchors[self.index]
        a.indices_json = json.dumps(indices)
        a.co = avg_co
        a.is_set = True
        a.vert_count = len(indices)
        _paint_anchor_verts(context, indices, a.weight)

        label = self.index + 1
        self.report({'INFO'},
            f"Anchor {label} set ({len(indices)} vert{'s' if len(indices) > 1 else ''}) "
            f"weight {a.weight:.2f}")
        return {'FINISHED'}


class MESH_OT_wg_apply_gradient(Operator):
    """Apply weight gradient to selected vertices between the anchors"""
    bl_idname = "mesh.wg_apply_gradient"
    bl_label = "Apply Gradient"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if not (context.active_object and context.active_object.type == 'MESH'
                and context.mode == 'EDIT_MESH'):
            return False
        props = context.scene.weight_gradient
        anchors = props.anchors
        n = len(anchors)
        return n >= 2 and anchors[0].is_set and anchors[n - 1].is_set

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

        # Build stops from anchors --------------------------------------
        stops, a_co, ab, ab_len_sq = _build_stops(props)
        if stops is None:
            self.report({'WARNING'}, "First and last anchors must be set and not coincide")
            return {'CANCELLED'}

        # Collect anchor vertex indices for exact-weight assignment -----
        anchor_indices = {}  # vert_index -> weight
        for a in props.anchors:
            if a.is_set:
                for idx in _parse_indices(a.indices_json):
                    anchor_indices[idx] = a.weight

        # Curve function ------------------------------------------------
        curve = props.curve_type
        use_direct_curve = False

        if curve == 'CUSTOM_POWER':
            power = props.curve_power
            def apply_curve(t):
                return curve_custom_power(t, power)
        elif curve == 'CUSTOM_CURVE':
            # Direct mode: curve Y = final weight value
            use_direct_curve = True
            brush = _get_curve_mapping()
            mapping = brush.curve
            mapping.initialize()
            crv = mapping.curves[0]
        else:
            apply_curve = CURVE_FUNCS[curve]

        # Switch to object mode so vg.add() works ----------------------
        bpy.ops.object.mode_set(mode='OBJECT')

        count = 0
        for v in me.vertices:
            if not v.select:
                continue

            v_world = obj.matrix_world @ v.co
            t = (v_world - a_co).dot(ab) / ab_len_sq
            t = max(0.0, min(1.0, t))

            if use_direct_curve:
                # Custom curve: Y value IS the weight
                weight = mapping.evaluate(crv, t)
                weight = max(0.0, min(1.0, weight))
            else:
                if v.index in anchor_indices:
                    weight = anchor_indices[v.index]
                else:
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


class MESH_OT_wg_init_curve_from_anchors(Operator):
    """Set curve endpoints to match first/last anchor weights"""
    bl_idname = "mesh.wg_init_curve_from_anchors"
    bl_label = "Init from Anchors"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.weight_gradient
        _ensure_anchors(props)
        anchors = props.anchors
        wa = anchors[0].weight
        wb = anchors[len(anchors) - 1].weight
        _apply_curve_points([(0.0, wa), (1.0, wb)])
        self.report({'INFO'}, f"Curve set: first={wa:.2f} to last={wb:.2f}")
        return {'FINISHED'}


class MESH_OT_wg_save_curve(Operator):
    """Save the current custom curve"""
    bl_idname = "mesh.wg_save_curve"
    bl_label = "Save Curve"
    bl_options = {'REGISTER', 'UNDO'}

    name: bpy.props.StringProperty(name="Name", default="My Curve")

    def invoke(self, context, event):
        props = context.scene.weight_gradient
        self.name = f"Curve {len(props.saved_curves) + 1}"
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        props = context.scene.weight_gradient
        pts = _read_curve_points()
        slot = props.saved_curves.add()
        slot.name = self.name
        slot.points_json = json.dumps(pts)
        slot.point_count = len(pts)
        props.active_curve_index = len(props.saved_curves) - 1
        self.report({'INFO'}, f"Saved curve '{self.name}' ({len(pts)} points)")
        return {'FINISHED'}


class MESH_OT_wg_load_curve(Operator):
    """Load a saved custom curve"""
    bl_idname = "mesh.wg_load_curve"
    bl_label = "Load Curve"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Slot Index", default=0)

    def execute(self, context):
        props = context.scene.weight_gradient
        if self.index < 0 or self.index >= len(props.saved_curves):
            self.report({'WARNING'}, "Invalid curve slot")
            return {'CANCELLED'}
        slot = props.saved_curves[self.index]
        try:
            pts = [tuple(p) for p in json.loads(slot.points_json)]
        except (json.JSONDecodeError, TypeError):
            self.report({'WARNING'}, "Corrupt curve data")
            return {'CANCELLED'}
        if len(pts) < 2:
            self.report({'WARNING'}, "Curve needs at least 2 points")
            return {'CANCELLED'}
        _apply_curve_points(pts)
        props.active_curve_index = self.index
        self.report({'INFO'}, f"Loaded curve '{slot.name}'")
        return {'FINISHED'}


class MESH_OT_wg_delete_curve(Operator):
    """Delete a saved custom curve"""
    bl_idname = "mesh.wg_delete_curve"
    bl_label = "Delete Curve"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Slot Index", default=0)

    def execute(self, context):
        props = context.scene.weight_gradient
        if self.index < 0 or self.index >= len(props.saved_curves):
            return {'CANCELLED'}
        name = props.saved_curves[self.index].name
        props.saved_curves.remove(self.index)
        if props.active_curve_index >= len(props.saved_curves):
            props.active_curve_index = max(0, len(props.saved_curves) - 1)
        self.report({'INFO'}, f"Deleted curve '{name}'")
        return {'FINISHED'}


class MESH_OT_wg_curve_preset(Operator):
    """Apply a preset shape to the custom curve"""
    bl_idname = "mesh.wg_curve_preset"
    bl_label = "Curve Preset"
    bl_options = {'REGISTER', 'UNDO'}

    preset: EnumProperty(
        name="Preset",
        items=[
            ('LINEAR',    "Linear",    "Straight line"),
            ('EASE_IN',   "Ease In",   "Slow start, fast end"),
            ('EASE_OUT',  "Ease Out",  "Fast start, slow end"),
            ('S_CURVE',   "S-Curve",   "Smooth sigmoid"),
            ('BELL',      "Bell",      "Peak in the middle"),
            ('VALLEY',    "Valley",    "Dip in the middle"),
            ('STEPS_3',   "3 Steps",   "Staircase with 3 levels"),
            ('SHARP_IN',  "Sharp In",  "Flat then sudden ramp"),
            ('SHARP_OUT', "Sharp Out", "Sudden ramp then flat"),
        ],
    )

    def execute(self, context):
        _apply_curve_preset(self.preset)
        return {'FINISHED'}


class MESH_OT_wg_save_selection(Operator):
    """Save the current vertex selection to a named slot"""
    bl_idname = "mesh.wg_save_selection"
    bl_label = "Save Selection"
    bl_options = {'REGISTER', 'UNDO'}

    name: bpy.props.StringProperty(name="Name", default="Selection")

    @classmethod
    def poll(cls, context):
        return (context.active_object is not None
                and context.active_object.type == 'MESH'
                and context.mode == 'EDIT_MESH')

    def invoke(self, context, event):
        props = context.scene.weight_gradient
        self.name = f"Selection {len(props.saved_selections) + 1}"
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        indices, _ = _get_selected_verts(context)
        if not indices:
            self.report({'WARNING'}, "No vertices selected")
            return {'CANCELLED'}

        props = context.scene.weight_gradient
        slot = props.saved_selections.add()
        slot.name = self.name
        slot.indices_json = json.dumps(indices)
        slot.count = len(indices)
        props.active_selection_index = len(props.saved_selections) - 1
        self.report({'INFO'}, f"Saved '{self.name}' ({len(indices)} verts)")
        return {'FINISHED'}


class MESH_OT_wg_load_selection(Operator):
    """Load a saved vertex selection"""
    bl_idname = "mesh.wg_load_selection"
    bl_label = "Load Selection"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Slot Index", default=0)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            return False
        return context.mode in {'EDIT_MESH', 'OBJECT'}

    def execute(self, context):
        props = context.scene.weight_gradient
        if self.index < 0 or self.index >= len(props.saved_selections):
            self.report({'WARNING'}, "Invalid selection slot")
            return {'CANCELLED'}

        slot = props.saved_selections[self.index]
        idx_set = _parse_indices(slot.indices_json)
        if not idx_set:
            self.report({'WARNING'}, "Selection is empty")
            return {'CANCELLED'}

        obj = context.active_object

        # Enter edit mode if in object mode
        was_object = (context.mode == 'OBJECT')
        if was_object:
            bpy.ops.object.mode_set(mode='EDIT')

        # Switch to vertex select mode so the selection is visible
        context.tool_settings.mesh_select_mode = (True, False, False)

        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()

        # Deselect all first, then select saved verts
        for v in bm.verts:
            v.select = False
        for e in bm.edges:
            e.select = False
        for f in bm.faces:
            f.select = False

        for v in bm.verts:
            if v.index in idx_set:
                v.select = True
        bm.select_flush_mode()
        bmesh.update_edit_mesh(obj.data)

        # Force viewport redraw
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

        props.active_selection_index = self.index
        self.report({'INFO'}, f"Loaded '{slot.name}' ({slot.count} verts)")
        return {'FINISHED'}


class MESH_OT_wg_delete_selection(Operator):
    """Delete a saved vertex selection"""
    bl_idname = "mesh.wg_delete_selection"
    bl_label = "Delete Selection"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Slot Index", default=0)

    def execute(self, context):
        props = context.scene.weight_gradient
        if self.index < 0 or self.index >= len(props.saved_selections):
            return {'CANCELLED'}

        name = props.saved_selections[self.index].name
        props.saved_selections.remove(self.index)
        if props.active_selection_index >= len(props.saved_selections):
            props.active_selection_index = max(0, len(props.saved_selections) - 1)
        self.report({'INFO'}, f"Deleted '{name}'")
        return {'FINISHED'}


class MESH_OT_wg_clear_anchors(Operator):
    """Clear all anchor points"""
    bl_idname = "mesh.wg_clear_anchors"
    bl_label = "Clear Anchors"
    bl_options = {'REGISTER'}

    def execute(self, context):
        props = context.scene.weight_gradient
        for a in props.anchors:
            a.is_set = False
            a.indices_json = ""
            a.vert_count = 0
        self.report({'INFO'}, "Anchors cleared")
        return {'FINISHED'}


class MESH_OT_wg_save_anchor_set(Operator):
    """Save the current anchor setup to a named slot"""
    bl_idname = "mesh.wg_save_anchor_set"
    bl_label = "Save Anchors"
    bl_options = {'REGISTER', 'UNDO'}

    name: StringProperty(name="Name", default="Anchors")

    def invoke(self, context, event):
        props = context.scene.weight_gradient
        self.name = f"Anchors {len(props.saved_anchor_sets) + 1}"
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        props = context.scene.weight_gradient
        _ensure_anchors(props)

        data = []
        for a in props.anchors:
            data.append({
                "indices_json": a.indices_json,
                "co": list(a.co),
                "weight": a.weight,
                "is_set": a.is_set,
                "vert_count": a.vert_count,
            })

        slot = props.saved_anchor_sets.add()
        slot.name = self.name
        slot.data_json = json.dumps(data)
        slot.anchor_count = len(data)
        props.active_anchor_set_index = len(props.saved_anchor_sets) - 1

        n_set = sum(1 for a in props.anchors if a.is_set)
        self.report({'INFO'}, f"Saved '{self.name}' ({slot.anchor_count} anchors, {n_set} set)")
        return {'FINISHED'}


class MESH_OT_wg_load_anchor_set(Operator):
    """Load a saved anchor setup"""
    bl_idname = "mesh.wg_load_anchor_set"
    bl_label = "Load Anchors"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Slot Index", default=0)

    def execute(self, context):
        props = context.scene.weight_gradient
        if self.index < 0 or self.index >= len(props.saved_anchor_sets):
            self.report({'WARNING'}, "Invalid anchor set slot")
            return {'CANCELLED'}

        slot = props.saved_anchor_sets[self.index]
        try:
            data = json.loads(slot.data_json)
        except (json.JSONDecodeError, TypeError):
            self.report({'WARNING'}, "Corrupt anchor data")
            return {'CANCELLED'}

        if not data:
            self.report({'WARNING'}, "Anchor set is empty")
            return {'CANCELLED'}

        # Set anchor count (triggers collection resize)
        props.anchor_count = max(2, min(10, len(data)))
        _ensure_anchors(props)

        for i, entry in enumerate(data):
            if i >= len(props.anchors):
                break
            a = props.anchors[i]
            a.indices_json = entry.get("indices_json", "")
            a.co = entry.get("co", (0, 0, 0))
            a.weight = entry.get("weight", 0.5)
            a.is_set = entry.get("is_set", False)
            a.vert_count = entry.get("vert_count", 0)

        props.active_anchor_set_index = self.index
        self.report({'INFO'}, f"Loaded '{slot.name}'")
        return {'FINISHED'}


class MESH_OT_wg_delete_anchor_set(Operator):
    """Delete a saved anchor setup"""
    bl_idname = "mesh.wg_delete_anchor_set"
    bl_label = "Delete Anchor Set"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Slot Index", default=0)

    def execute(self, context):
        props = context.scene.weight_gradient
        if self.index < 0 or self.index >= len(props.saved_anchor_sets):
            return {'CANCELLED'}

        name = props.saved_anchor_sets[self.index].name
        props.saved_anchor_sets.remove(self.index)
        if props.active_anchor_set_index >= len(props.saved_anchor_sets):
            props.active_anchor_set_index = max(0, len(props.saved_anchor_sets) - 1)
        self.report({'INFO'}, f"Deleted '{name}'")
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# Panel
# ---------------------------------------------------------------------------

class WG_UL_saved_curves(bpy.types.UIList):
    bl_idname = "WG_UL_saved_curves"

    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        row = layout.row(align=True)
        row.prop(item, "name", text="", emboss=False, icon='CURVE_DATA')
        row.label(text=f"({item.point_count}pt)")
        op_del = row.operator("mesh.wg_delete_curve", text="", icon='X')
        op_del.index = index


class WG_UL_saved_selections(bpy.types.UIList):
    bl_idname = "WG_UL_saved_selections"

    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        row = layout.row(align=True)
        row.prop(item, "name", text="", emboss=False, icon='RESTRICT_SELECT_OFF')
        row.label(text=f"({item.count})")
        op_del = row.operator("mesh.wg_delete_selection", text="", icon='X')
        op_del.index = index


class WG_UL_saved_anchor_sets(bpy.types.UIList):
    bl_idname = "WG_UL_saved_anchor_sets"

    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        row = layout.row(align=True)
        row.prop(item, "name", text="", emboss=False, icon='ANCHOR_CENTER')
        row.label(text=f"({item.anchor_count})")
        op_del = row.operator("mesh.wg_delete_anchor_set", text="", icon='X')
        op_del.index = index


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

        # -- Anchor Count -----------------------------------------------
        layout.prop(props, "anchor_count")

        # -- Anchors ----------------------------------------------------
        for i, a in enumerate(props.anchors):
            box = layout.box()
            row = box.row(align=True)
            label = i + 1
            op = row.operator("mesh.wg_set_anchor", text=f"Set Anchor {label}",
                              icon='VERTEXSEL')
            op.index = i
            if a.is_set:
                n = a.vert_count
                row.label(text=f"{n} vert{'s' if n > 1 else ''}", icon='CHECKMARK')
            else:
                row.label(text="Not set", icon='X')
            box.prop(a, "weight", slider=True)

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
        elif props.curve_type == 'CUSTOM_CURVE':
            box_cv = layout.box()
            row = box_cv.row(align=True)
            icon = 'TRIA_DOWN' if props.show_curve_editor else 'TRIA_RIGHT'
            row.prop(props, "show_curve_editor", text="Curve Editor",
                     icon=icon, emboss=False)

            if props.show_curve_editor:
                brush = _get_curve_mapping()
                box_cv.label(text="X = position (A\u2192B)   Y = weight value", icon='INFO')
                box_cv.template_curve_mapping(brush, "curve")
                box_cv.operator("mesh.wg_init_curve_from_anchors", icon='ANCHOR_CENTER')

                # Presets
                sub_box = box_cv.box()
                sub_box.label(text="Presets:")
                row = sub_box.row(align=True)
                for key in ('LINEAR', 'EASE_IN', 'EASE_OUT', 'S_CURVE'):
                    label = key.replace('_', ' ').title()
                    op = row.operator("mesh.wg_curve_preset", text=label)
                    op.preset = key
                row = sub_box.row(align=True)
                for key in ('BELL', 'VALLEY', 'STEPS_3', 'SHARP_IN', 'SHARP_OUT'):
                    label = key.replace('_', ' ').title()
                    op = row.operator("mesh.wg_curve_preset", text=label)
                    op.preset = key

                # Saved curves
                sub_box = box_cv.box()
                row = sub_box.row(align=True)
                row.label(text="Saved Curves", icon='CURVE_DATA')
                sub_box.template_list(
                    "WG_UL_saved_curves", "",
                    props, "saved_curves",
                    props, "active_curve_index",
                    rows=2, maxrows=5,
                )
                row = sub_box.row(align=True)
                row.operator("mesh.wg_save_curve", text="Save", icon='ADD')
                sub = row.row(align=True)
                sub.enabled = len(props.saved_curves) > 0
                op = sub.operator("mesh.wg_load_curve", text="Load", icon='CHECKMARK')
                op.index = props.active_curve_index

        layout.separator()

        # -- Actions ----------------------------------------------------
        row = layout.row(align=True)
        row.scale_y = 1.5
        row.operator("mesh.wg_apply_gradient", icon='MOD_VERTEX_WEIGHT')

        layout.operator("mesh.wg_clear_anchors", icon='TRASH')

        # -- Saved Anchor Sets ------------------------------------------
        layout.separator()
        box = layout.box()
        row = box.row(align=True)
        row.label(text="Saved Anchors", icon='ANCHOR_CENTER')

        box.template_list(
            "WG_UL_saved_anchor_sets", "",
            props, "saved_anchor_sets",
            props, "active_anchor_set_index",
            rows=2, maxrows=5,
        )

        row = box.row(align=True)
        row.operator("mesh.wg_save_anchor_set", text="Save", icon='ADD')
        sub = row.row(align=True)
        sub.enabled = len(props.saved_anchor_sets) > 0
        op = sub.operator("mesh.wg_load_anchor_set", text="Load", icon='CHECKMARK')
        op.index = props.active_anchor_set_index

        # -- Saved Selections -------------------------------------------
        layout.separator()
        box = layout.box()
        row = box.row(align=True)
        row.label(text="Saved Selections", icon='BOOKMARKS')

        box.template_list(
            "WG_UL_saved_selections", "",
            props, "saved_selections",
            props, "active_selection_index",
            rows=3, maxrows=5,
        )

        row = box.row(align=True)
        row.operator("mesh.wg_save_selection", text="Save", icon='ADD')
        sub = row.row(align=True)
        sub.enabled = len(props.saved_selections) > 0
        op = sub.operator("mesh.wg_load_selection", text="Load", icon='CHECKMARK')
        op.index = props.active_selection_index


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

classes = (
    WG_Anchor,
    WG_SavedAnchorSet,
    WG_SavedCurve,
    WG_SavedSelection,
    WeightGradientProperties,
    WG_UL_saved_curves,
    WG_UL_saved_selections,
    WG_UL_saved_anchor_sets,
    MESH_OT_wg_set_anchor,
    MESH_OT_wg_apply_gradient,
    MESH_OT_wg_init_curve_from_anchors,
    MESH_OT_wg_save_curve,
    MESH_OT_wg_load_curve,
    MESH_OT_wg_delete_curve,
    MESH_OT_wg_curve_preset,
    MESH_OT_wg_save_selection,
    MESH_OT_wg_load_selection,
    MESH_OT_wg_delete_selection,
    MESH_OT_wg_clear_anchors,
    MESH_OT_wg_save_anchor_set,
    MESH_OT_wg_load_anchor_set,
    MESH_OT_wg_delete_anchor_set,
    VIEW3D_PT_weight_gradient,
)


@bpy.app.handlers.persistent
def _wg_load_post(_dummy=None):
    """Ensure every scene has its anchors collection populated after file load."""
    for scene in bpy.data.scenes:
        props = scene.weight_gradient
        _ensure_anchors(props)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.weight_gradient = PointerProperty(type=WeightGradientProperties)
    bpy.app.handlers.load_post.append(_wg_load_post)
    # Initialize for scenes that already exist
    bpy.app.timers.register(lambda: (_wg_load_post(), None)[-1], first_interval=0.0)


def unregister():
    if _wg_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_wg_load_post)
    del bpy.types.Scene.weight_gradient
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
