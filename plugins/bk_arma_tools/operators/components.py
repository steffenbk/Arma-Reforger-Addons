import bpy
import bmesh
from mathutils import Vector
from ..constants import (
    VEHICLE_COMPONENT_TYPES, WEAPON_COMPONENT_TYPES,
    get_mode, get_bone_prefix, get_component_types,
)


def _component_type_items(self, context):
    return get_component_types(context)


def _get_available_bones(self, context):
    """Module-level bone picker — usable before class methods are defined."""
    default_label = "w_root (Default)" if get_mode(context) == 'WEAPON' else "v_body (Default)"
    items = [('NONE', default_label, "")]
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            for bone in obj.data.bones:
                items.append((bone.name, bone.name, ""))
            break
    return items


# ============================================================================
# MODE-AWARE LOOKUP HELPERS
# ============================================================================
_VEHICLE_SOCKET_MAP = {
    'window': 'window', 'door': 'door', 'hood': 'hood', 'trunk': 'trunk',
    'wheel': 'wheel', 'light': 'light', 'mirror': 'mirror', 'antenna': 'antenna',
    'hatch': 'hatch', 'panel': 'panel', 'seat': 'seat', 'dashboard': 'dashboard',
    'steering_wheel': 'steering_wheel', 'gear_shifter': 'gear_shifter',
    'handbrake': 'handbrake', 'pedal': 'pedal', 'engine': 'engine',
    'exhaust': 'exhaust', 'suspension': 'suspension', 'rotor': 'rotor',
    'landing_gear': 'landing_gear', 'fuel_tank': 'fuel_tank',
    'battery': 'battery', 'radiator': 'radiator',
}
_VEHICLE_BONE_MAP = {
    'door': 'v_door_left', 'hood': 'v_hood', 'trunk': 'v_trunk',
    'wheel': 'v_wheel_1', 'steering_wheel': 'v_steering_wheel',
    'gear_shifter': 'v_gearshift', 'handbrake': 'v_handbrake',
    'pedal': 'v_pedal_brake', 'exhaust': 'v_exhaust',
    'suspension': 'v_suspension1', 'rotor': 'v_rotor',
    'landing_gear': 'v_landing_gear', 'antenna': 'v_antenna',
    'mirror': 'v_mirror_left', 'dashboard': 'v_dashboard_arm',
}
_WEAPON_SOCKET_MAP = {
    'sight': 'slot_optics', 'barrel': 'slot_barrel_muzzle',
    'bipod': 'slot_underbarrel', 'accessory': 'slot_flashlight',
}
_WEAPON_BONE_MAP = {
    'trigger': 'w_trigger', 'bolt': 'w_bolt',
    'charging_handle': 'w_ch_handle', 'mag_release': 'w_mag_release',
    'safety': 'w_safety', 'fire_mode': 'w_fire_mode',
    'hammer': 'w_hammer', 'striker': 'w_striker',
    'slide': 'w_slide', 'barrel': 'w_barrel',
    'buttstock': 'w_buttstock', 'ejection_port': 'w_ejection_port',
    'bipod': 'w_bipodleg', 'sight': 'w_sight',
}

def _get_socket_type(context, component_type):
    if get_mode(context) == 'WEAPON':
        return _WEAPON_SOCKET_MAP.get(component_type, 'custom')
    return _VEHICLE_SOCKET_MAP.get(component_type, 'custom')

def _get_bone_type(context, component_type):
    if get_mode(context) == 'WEAPON':
        return _WEAPON_BONE_MAP.get(component_type, 'custom')
    return _VEHICLE_BONE_MAP.get(component_type, 'custom')

def _default_component(context):
    """Return a sensible default for the component_type enum."""
    return 'trigger' if get_mode(context) == 'WEAPON' else 'door'


# ============================================================================
# SHARED BONE PREFIX ENFORCEMENT
# ============================================================================
def _enforce_prefix(name, prefix):
    if not name.startswith(prefix):
        return prefix + name
    return name


# ============================================================================
# COMPONENT SEPARATION OPERATOR
# ============================================================================
class ARVEHICLES_OT_separate_components(bpy.types.Operator):
    bl_idname = "arvehicles.separate_components"
    bl_label = "Separate Component"
    bl_options = {'REGISTER', 'UNDO'}

    component_type: bpy.props.EnumProperty(name="Component Type", items=_component_type_items)
    custom_name: bpy.props.StringProperty(name="Custom Name", default="")

    # Socket
    add_socket: bpy.props.BoolProperty(name="Add Socket", default=True)
    custom_socket_name: bpy.props.StringProperty(name="Custom Socket Name", default="")
    set_origin_to_socket: bpy.props.BoolProperty(name="Set Origin to Socket", default=True)
    socket_parent_mode: bpy.props.EnumProperty(
        name="Parent Socket",
        items=[
            ('ARMATURE', "Parent to Armature", "Parent socket to the armature object"),
            ('BONE',     "Parent to Bone",     "Parent socket to a specific existing bone"),
            ('NEW_BONE', "Parent to New Bone", "Parent socket to the bone being created (requires Add Bone)"),
            ('NONE',     "Don't Parent",       "Leave socket unparented"),
        ],
        default='ARMATURE',
    )
    socket_target_bone: bpy.props.EnumProperty(
        name="Socket Parent Bone", items=_get_available_bones
    )

    # Bone
    add_bone: bpy.props.BoolProperty(name="Add Bone", default=False)
    custom_bone_name: bpy.props.StringProperty(name="Custom Bone Name", default="")
    auto_skinning: bpy.props.BoolProperty(name="Auto Skinning", default=True)
    invert_bone_direction: bpy.props.BoolProperty(name="Invert Bone Direction", default=False)

    use_world_direction: bpy.props.BoolProperty(name="Use World Direction", default=False)
    world_direction: bpy.props.EnumProperty(
        name="World Direction",
        items=[
            ('POS_Y', "+Y (Forward)", ""), ('NEG_Y', "-Y (Backward)", ""),
            ('POS_X', "+X (Right)", ""),   ('NEG_X', "-X (Left)", ""),
            ('POS_Z', "+Z (Up)", ""),      ('NEG_Z', "-Z (Down)", ""),
        ],
        default='POS_Y'
    )
    preserve_angle: bpy.props.BoolProperty(name="Preserve Angle", default=False)
    bone_primary_axis: bpy.props.EnumProperty(
        name="Primary Rotation Axis",
        items=[('Y', "Y Axis (Default)", ""), ('X', "X Axis", ""), ('Z', "Z Axis", "")],
        default='Y'
    )
    swap_yz_axes: bpy.props.BoolProperty(name="Swap Y<>Z Axes", default=False)
    align_roll_to_axis: bpy.props.EnumProperty(
        name="Align Roll To",
        items=[
            ('NONE', "Auto (Roll=0)", ""), ('WORLD_Z', "World Z (Up)", ""),
            ('WORLD_X', "World X", ""),    ('WORLD_Y', "World Y", ""),
        ],
        default='WORLD_Z'
    )
    set_mesh_origin_to_bone: bpy.props.BoolProperty(name="Set Mesh Origin to Bone", default=True)

    parent_to_specific_bone: bpy.props.BoolProperty(
        name="Parent Bone to Specific Bone", default=False
    )

    def get_available_bones(self, context):
        prefix = get_bone_prefix(context)
        default_label = "w_root (Default)" if get_mode(context) == 'WEAPON' else "v_body (Default)"
        items = [('NONE', default_label, "")]
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                for bone in obj.data.bones:
                    items.append((bone.name, bone.name, ""))
                break
        return items

    target_bone: bpy.props.EnumProperty(
        name="Parent Bone", items=get_available_bones
    )

    parent_to_existing_bone: bpy.props.BoolProperty(name="Skin to Existing Bone", default=False)

    def get_existing_bones(self, context):
        items = [('NONE', "Select Bone", "")]
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                for bone in obj.data.bones:
                    items.append((bone.name, bone.name, ""))
                break
        return items

    existing_target_bone: bpy.props.EnumProperty(
        name="Target Bone", items=get_existing_bones
    )

    # -------------------------------------------------------------------------
    def execute(self, context):
        if context.mode != 'EDIT_MESH':
            self.report({'ERROR'}, "Must be in Edit Mode with faces selected")
            return {'CANCELLED'}

        mesh = context.active_object.data
        if not mesh.total_face_sel:
            self.report({'ERROR'}, "No faces selected")
            return {'CANCELLED'}

        obj = context.active_object
        prefix = get_bone_prefix(context)
        mode   = get_mode(context)

        bm = bmesh.from_edit_mesh(mesh)
        selected_faces = [f for f in bm.faces if f.select]
        if not selected_faces:
            self.report({'ERROR'}, "No faces selected")
            return {'CANCELLED'}

        center     = sum((f.calc_center_median() for f in selected_faces), Vector()) / len(selected_faces)
        avg_normal = sum((f.normal for f in selected_faces), Vector()).normalized()

        world_center = obj.matrix_world @ center
        world_normal = (obj.matrix_world.to_3x3() @ avg_normal).normalized()

        # Name
        comp = self.component_type
        new_name = self.custom_name if self.custom_name else f"{comp}_{obj.name}"

        # Separate
        bpy.ops.mesh.separate(type='SELECTED')
        bpy.ops.object.mode_set(mode='OBJECT')

        new_obj = context.selected_objects[-1]
        new_obj.name = new_name
        new_obj["component_type"] = comp

        # Origin to geometry
        bpy.ops.object.select_all(action='DESELECT')
        new_obj.select_set(True)
        context.view_layer.objects.active = new_obj
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')

        # Clean up
        for mod in list(new_obj.modifiers):
            if mod.type == 'ARMATURE':
                new_obj.modifiers.remove(mod)
        new_obj.vertex_groups.clear()

        armature = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
        socket = None
        bone_name = None

        socket_type = _get_socket_type(context, comp)
        bone_type   = _get_bone_type(context, comp)

        # Default parent bone name based on mode
        default_parent = 'w_root' if mode == 'WEAPON' else 'v_body'

        # ---- BONE ----
        if self.add_bone:
            if not armature:
                arm_data = bpy.data.armatures.new("Armature")
                armature = bpy.data.objects.new("Armature", arm_data)
                context.collection.objects.link(armature)
                context.view_layer.objects.active = armature
                bpy.ops.object.mode_set(mode='EDIT')
                rb = arm_data.edit_bones.new(default_parent if mode == 'WEAPON' else 'v_root')
                rb.head = (0, 0, 0); rb.tail = (0, 0.2, 0)
                if mode == 'VEHICLE':
                    bb = arm_data.edit_bones.new('v_body')
                    bb.head = (0, 0, 0.35); bb.tail = (0, 0.2, 0.35); bb.parent = rb
                bpy.ops.object.mode_set(mode='OBJECT')

            if self.custom_bone_name:
                bone_name = _enforce_prefix(self.custom_bone_name, prefix)
            elif bone_type == 'custom':
                bone_name = _enforce_prefix(new_name.lower().replace(' ', '_'), prefix)
            else:
                bone_name = bone_type
                base = bone_name; counter = 1
                while bone_name in armature.data.bones:
                    bone_name = f"{base}_{counter:02d}"; counter += 1

            context.view_layer.objects.active = armature
            bpy.ops.object.mode_set(mode='EDIT')

            bone = armature.data.edit_bones.new(bone_name)

            if self.parent_to_specific_bone and self.target_bone != 'NONE':
                if self.target_bone in armature.data.edit_bones:
                    bone.parent = armature.data.edit_bones[self.target_bone]
                    bone.use_connect = False
            else:
                for pb in [default_parent, 'v_root']:
                    if pb in armature.data.edit_bones:
                        bone.parent = armature.data.edit_bones[pb]; break

            # Direction
            if self.use_world_direction:
                dmap = {
                    'POS_Y': Vector((0,1,0)), 'NEG_Y': Vector((0,-1,0)),
                    'POS_X': Vector((1,0,0)), 'NEG_X': Vector((-1,0,0)),
                    'POS_Z': Vector((0,0,1)), 'NEG_Z': Vector((0,0,-1)),
                }
                wd = dmap[self.world_direction]
                if self.preserve_angle:
                    up = Vector((0,0,1)) if abs(wd.dot(Vector((0,0,1)))) < 0.9 else Vector((1,0,0))
                    right = wd.cross(up).normalized()
                    up = right.cross(wd).normalized()
                    bd = (wd * world_normal.dot(wd) + up * world_normal.dot(up)).normalized() * 0.2
                else:
                    bd = wd * 0.2
            else:
                bd = world_normal * 0.2

            if self.invert_bone_direction: bd = -bd
            if self.bone_primary_axis == 'X': bd = Vector((bd.y, bd.z, bd.x))
            elif self.bone_primary_axis == 'Z': bd = Vector((bd.z, bd.x, bd.y))

            wh = world_center; wt = world_center + bd
            if self.swap_yz_axes:
                wh = Vector((wh.x, wh.z, wh.y)); wt = Vector((wt.x, wt.z, wt.y))

            bone.head = wh; bone.tail = wt
            rmap = {'WORLD_Z': Vector((0,0,1)), 'WORLD_X': Vector((1,0,0)), 'WORLD_Y': Vector((0,1,0))}
            if self.align_roll_to_axis in rmap:
                bone.align_roll(rmap[self.align_roll_to_axis])
            else:
                bone.roll = 0.0

            bpy.ops.object.mode_set(mode='OBJECT')

            if self.set_mesh_origin_to_bone:
                bpy.ops.object.select_all(action='DESELECT')
                new_obj.select_set(True)
                context.view_layer.objects.active = new_obj
                saved = context.scene.cursor.location.copy()
                context.scene.cursor.location = world_center
                bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
                context.scene.cursor.location = saved

            if self.auto_skinning:
                bpy.ops.object.select_all(action='DESELECT')
                new_obj.select_set(True)
                context.view_layer.objects.active = new_obj
                vg = new_obj.vertex_groups.new(name=bone_name)
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                new_obj.vertex_groups.active = vg
                bpy.ops.object.vertex_group_assign()
                bpy.ops.object.mode_set(mode='OBJECT')
                am = new_obj.modifiers.new(name="Armature", type='ARMATURE')
                am.object = armature

        elif self.parent_to_existing_bone and self.existing_target_bone != 'NONE':
            if armature and self.existing_target_bone in armature.data.bones:
                bpy.ops.object.select_all(action='DESELECT')
                new_obj.select_set(True)
                context.view_layer.objects.active = new_obj
                vg = new_obj.vertex_groups.new(name=self.existing_target_bone)
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                new_obj.vertex_groups.active = vg
                bpy.ops.object.vertex_group_assign()
                bpy.ops.object.mode_set(mode='OBJECT')
                am = new_obj.modifiers.new(name="Armature", type='ARMATURE')
                am.object = armature
            else:
                self.report({'WARNING'}, f"Bone '{self.existing_target_bone}' not found")

        # ---- SOCKET ----
        if self.add_socket:
            socket_name = self.custom_socket_name or \
                f"Socket_{socket_type.replace('_',' ').title().replace(' ','_')}"
            if not self.custom_socket_name:
                existing = [o for o in bpy.data.objects if socket_name in o.name]
                if existing:
                    socket_name = f"{socket_name}_{len(existing)+1:02d}"

            socket = bpy.data.objects.new(socket_name, None)
            socket.empty_display_type = 'ARROWS'
            socket.empty_display_size = 0.15
            socket.location = world_center
            context.collection.objects.link(socket)
            socket["socket_type"] = socket_type
            socket["attached_part"] = new_obj.name
            socket["vehicle_part"] = "attachment_point"

            if armature and self.socket_parent_mode != 'NONE':
                if self.socket_parent_mode == 'ARMATURE':
                    socket.parent = armature
                    socket.parent_type = 'OBJECT'
                    socket.matrix_parent_inverse = armature.matrix_world.inverted()
                elif self.socket_parent_mode == 'BONE' and self.socket_target_bone != 'NONE':
                    if self.socket_target_bone in armature.data.bones:
                        socket.parent = armature
                        socket.parent_type = 'BONE'
                        socket.parent_bone = self.socket_target_bone
                        pb = armature.pose.bones.get(self.socket_target_bone)
                        socket.matrix_parent_inverse = (armature.matrix_world @ pb.matrix).inverted() if pb else armature.matrix_world.inverted()
                elif self.socket_parent_mode == 'NEW_BONE' and bone_name and bone_name in armature.data.bones:
                    socket.parent = armature
                    socket.parent_type = 'BONE'
                    socket.parent_bone = bone_name
                    pb = armature.pose.bones.get(bone_name)
                    socket.matrix_parent_inverse = (armature.matrix_world @ pb.matrix).inverted() if pb else armature.matrix_world.inverted()

        if self.add_socket and self.set_origin_to_socket and socket:
            bpy.ops.object.select_all(action='DESELECT')
            new_obj.select_set(True)
            context.view_layer.objects.active = new_obj
            saved = context.scene.cursor.location.copy()
            context.scene.cursor.location = socket.location
            bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
            context.scene.cursor.location = saved

        bpy.ops.object.select_all(action='DESELECT')
        new_obj.select_set(True)
        context.view_layer.objects.active = new_obj

        msg = f"Separated '{new_name}'"
        if self.add_bone and bone_name: msg += f" + bone '{bone_name}'"
        if self.add_socket: msg += " + socket"
        self.report({'INFO'}, msg)
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=420)

    def draw(self, context):
        layout = self.layout
        mode = get_mode(context)
        prefix = get_bone_prefix(context)

        layout.prop(self, "component_type")
        layout.prop(self, "custom_name")

        layout.separator()
        box = layout.box()
        box.label(text="Socket Options", icon='EMPTY_DATA')
        box.prop(self, "add_socket")
        if self.add_socket:
            box.prop(self, "custom_socket_name")
            box.prop(self, "set_origin_to_socket")
            box.prop(self, "socket_parent_mode", text="Parent")
            if self.socket_parent_mode == 'BONE':
                box.prop(self, "socket_target_bone", text="", icon='BONE_DATA')
            elif self.socket_parent_mode == 'NEW_BONE' and not self.add_bone:
                box.label(text="Enable 'Add Bone' to use this option", icon='ERROR')

        layout.separator()
        box = layout.box()
        box.label(text="Bone Options", icon='BONE_DATA')
        box.prop(self, "add_bone")
        if self.add_bone:
            box.prop(self, "custom_bone_name")
            box.label(text=f"(prefix: {prefix})", icon='INFO')
            box.prop(self, "auto_skinning")
            box.prop(self, "set_mesh_origin_to_bone")
            box.separator()
            box.label(text="Bone Direction:")
            box.prop(self, "use_world_direction")
            if self.use_world_direction:
                box.prop(self, "world_direction")
                box.prop(self, "preserve_angle")
            else:
                box.prop(self, "invert_bone_direction")
            box.separator()
            box.label(text="Bone Orientation:")
            box.prop(self, "bone_primary_axis")
            box.prop(self, "swap_yz_axes")
            box.prop(self, "align_roll_to_axis")
            box.separator()
            box.label(text="Bone Hierarchy:", icon='OUTLINER')
            box.prop(self, "parent_to_specific_bone")
            if self.parent_to_specific_bone:
                box.prop(self, "target_bone", text="", icon='BONE_DATA')
            else:
                default = "w_root" if mode == 'WEAPON' else "v_body"
                box.box().label(text=f"Default parent: {default}", icon='INFO')
        else:
            box.separator()
            box.prop(self, "parent_to_existing_bone")
            if self.parent_to_existing_bone:
                box.prop(self, "existing_target_bone", text="", icon='BONE_DATA')


# ============================================================================
# PARENT BONES OPERATOR
# ============================================================================
class ARVEHICLES_OT_parent_bones(bpy.types.Operator):
    bl_idname = "arvehicles.parent_bones"
    bl_label = "Parent Bones to Bones"
    bl_description = "Parent selected bones to a target bone"
    bl_options = {'REGISTER', 'UNDO'}

    def get_bone_items(self, context):
        mode = get_mode(context)
        default = "w_root (Default)" if mode == 'WEAPON' else "v_body (Default)"
        items = [('NONE', default, "")]
        arm = context.active_object if context.active_object and context.active_object.type == 'ARMATURE' else None
        if arm:
            for bone in arm.data.bones:
                items.append((bone.name, bone.name, ""))
        return items

    target_bone: bpy.props.EnumProperty(name="Parent To", items=get_bone_items)

    def execute(self, context):
        if not context.active_object or context.active_object.type != 'ARMATURE':
            self.report({'ERROR'}, "Active object must be an armature")
            return {'CANCELLED'}
        if context.mode != 'EDIT_ARMATURE':
            self.report({'ERROR'}, "Must be in Armature Edit Mode")
            return {'CANCELLED'}

        armature = context.active_object
        mode = get_mode(context)
        selected = [b for b in armature.data.edit_bones if b.select]
        if not selected:
            self.report({'ERROR'}, "No bones selected")
            return {'CANCELLED'}

        default_parent = 'w_root' if mode == 'WEAPON' else 'v_body'
        target_name = default_parent if self.target_bone == 'NONE' else self.target_bone

        if target_name not in armature.data.edit_bones:
            self.report({'ERROR'}, f"Bone '{target_name}' not found")
            return {'CANCELLED'}

        parent_bone = armature.data.edit_bones[target_name]
        count = 0
        for bone in selected:
            if bone.name != target_name:
                bone.parent = parent_bone
                bone.use_connect = False
                count += 1

        self.report({'INFO'}, f"Parented {count} bone(s) to '{target_name}'")
        return {'FINISHED'}

    def invoke(self, context, event):
        if context.active_object and context.active_object.type == 'ARMATURE':
            return context.window_manager.invoke_props_dialog(self)
        self.report({'ERROR'}, "Select an armature first")
        return {'CANCELLED'}

    def draw(self, context):
        layout = self.layout
        arm = context.active_object
        selected = [b for b in arm.data.edit_bones if b.select] if context.mode == 'EDIT_ARMATURE' else []

        box = layout.box()
        box.label(text=f"Selected Bones: {len(selected)}", icon='BONE_DATA')
        for bone in selected[:5]:
            box.label(text=f"  - {bone.name}")
        if len(selected) > 5:
            box.label(text=f"  ... and {len(selected) - 5} more")

        layout.separator()
        layout.label(text="Parent To:", icon='OUTLINER')
        layout.prop(self, "target_bone", text="")


# ============================================================================
# ADD BONE TO SELECTED VERTICES OPERATOR
# ============================================================================
class ARVEHICLES_OT_add_bone_to_verts(bpy.types.Operator):
    bl_idname = "arvehicles.add_bone_to_verts"
    bl_label = "Add Bone to Selected Verts"
    bl_description = "Create a bone at the center of selected vertices, assign them to a vertex group with weight control"
    bl_options = {'REGISTER', 'UNDO'}

    custom_bone_name: bpy.props.StringProperty(name="Bone Name", default="")
    vertex_weight: bpy.props.FloatProperty(
        name="Vertex Weight", default=1.0, min=0.0, max=1.0,
        description="Weight to assign selected vertices in the vertex group"
    )

    # Bone direction options (same as Separate Component)
    invert_bone_direction: bpy.props.BoolProperty(name="Invert Bone Direction", default=False)
    use_world_direction: bpy.props.BoolProperty(name="Use World Direction", default=False)
    world_direction: bpy.props.EnumProperty(
        name="World Direction",
        items=[
            ('POS_Y', "+Y (Forward)", ""), ('NEG_Y', "-Y (Backward)", ""),
            ('POS_X', "+X (Right)", ""),   ('NEG_X', "-X (Left)", ""),
            ('POS_Z', "+Z (Up)", ""),      ('NEG_Z', "-Z (Down)", ""),
        ],
        default='POS_Y'
    )
    preserve_angle: bpy.props.BoolProperty(name="Preserve Angle", default=False)
    bone_primary_axis: bpy.props.EnumProperty(
        name="Primary Rotation Axis",
        items=[('Y', "Y Axis (Default)", ""), ('X', "X Axis", ""), ('Z', "Z Axis", "")],
        default='Y'
    )
    swap_yz_axes: bpy.props.BoolProperty(name="Swap Y<>Z Axes", default=False)
    align_roll_to_axis: bpy.props.EnumProperty(
        name="Align Roll To",
        items=[
            ('NONE', "Auto (Roll=0)", ""), ('WORLD_Z', "World Z (Up)", ""),
            ('WORLD_X', "World X", ""),    ('WORLD_Y', "World Y", ""),
        ],
        default='WORLD_Z'
    )

    # Bone hierarchy
    parent_to_specific_bone: bpy.props.BoolProperty(
        name="Parent Bone to Specific Bone", default=False
    )

    def get_available_bones(self, context):
        prefix = get_bone_prefix(context)
        default_label = "w_root (Default)" if get_mode(context) == 'WEAPON' else "v_body (Default)"
        items = [('NONE', default_label, "")]
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                for bone in obj.data.bones:
                    items.append((bone.name, bone.name, ""))
                break
        return items

    target_bone: bpy.props.EnumProperty(
        name="Parent Bone", items=get_available_bones
    )

    # -------------------------------------------------------------------------
    def execute(self, context):
        if context.mode != 'EDIT_MESH':
            self.report({'ERROR'}, "Must be in Edit Mode with vertices selected")
            return {'CANCELLED'}

        obj = context.active_object
        mesh = obj.data
        prefix = get_bone_prefix(context)
        mode = get_mode(context)

        bm = bmesh.from_edit_mesh(mesh)
        selected_verts = [v for v in bm.verts if v.select]
        if not selected_verts:
            self.report({'ERROR'}, "No vertices selected")
            return {'CANCELLED'}

        # Calculate center of selected vertices
        center = sum((v.co for v in selected_verts), Vector()) / len(selected_verts)
        world_center = obj.matrix_world @ center

        # Calculate average normal from connected faces of selected verts
        connected_faces = set()
        for v in selected_verts:
            for f in v.link_faces:
                connected_faces.add(f)
        if connected_faces:
            avg_normal = sum((f.normal for f in connected_faces), Vector()).normalized()
        else:
            avg_normal = Vector((0, 0, 1))
        world_normal = (obj.matrix_world.to_3x3() @ avg_normal).normalized()

        # Bone name
        if self.custom_bone_name:
            bone_name = _enforce_prefix(self.custom_bone_name, prefix)
        else:
            bone_name = _enforce_prefix("bone", prefix)

        # Store selected vertex indices before leaving edit mode
        vert_indices = [v.index for v in selected_verts]

        # Find or create armature
        armature = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
        default_parent = 'w_root' if mode == 'WEAPON' else 'v_body'

        bpy.ops.object.mode_set(mode='OBJECT')

        if not armature:
            arm_data = bpy.data.armatures.new("Armature")
            armature = bpy.data.objects.new("Armature", arm_data)
            context.collection.objects.link(armature)
            context.view_layer.objects.active = armature
            bpy.ops.object.mode_set(mode='EDIT')
            rb = arm_data.edit_bones.new(default_parent if mode == 'WEAPON' else 'v_root')
            rb.head = (0, 0, 0); rb.tail = (0, 0.2, 0)
            if mode == 'VEHICLE':
                bb = arm_data.edit_bones.new('v_body')
                bb.head = (0, 0, 0.35); bb.tail = (0, 0.2, 0.35); bb.parent = rb
            bpy.ops.object.mode_set(mode='OBJECT')

        # Deduplicate bone name
        base_name = bone_name; counter = 1
        while bone_name in armature.data.bones:
            bone_name = f"{base_name}_{counter:02d}"; counter += 1

        # Create the bone
        context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='EDIT')

        bone = armature.data.edit_bones.new(bone_name)

        # Parent bone
        if self.parent_to_specific_bone and self.target_bone != 'NONE':
            if self.target_bone in armature.data.edit_bones:
                bone.parent = armature.data.edit_bones[self.target_bone]
                bone.use_connect = False
        else:
            for pb in [default_parent, 'v_root']:
                if pb in armature.data.edit_bones:
                    bone.parent = armature.data.edit_bones[pb]; break

        # Direction
        if self.use_world_direction:
            dmap = {
                'POS_Y': Vector((0,1,0)), 'NEG_Y': Vector((0,-1,0)),
                'POS_X': Vector((1,0,0)), 'NEG_X': Vector((-1,0,0)),
                'POS_Z': Vector((0,0,1)), 'NEG_Z': Vector((0,0,-1)),
            }
            wd = dmap[self.world_direction]
            if self.preserve_angle:
                up = Vector((0,0,1)) if abs(wd.dot(Vector((0,0,1)))) < 0.9 else Vector((1,0,0))
                right = wd.cross(up).normalized()
                up = right.cross(wd).normalized()
                bd = (wd * world_normal.dot(wd) + up * world_normal.dot(up)).normalized() * 0.2
            else:
                bd = wd * 0.2
        else:
            bd = world_normal * 0.2

        if self.invert_bone_direction: bd = -bd
        if self.bone_primary_axis == 'X': bd = Vector((bd.y, bd.z, bd.x))
        elif self.bone_primary_axis == 'Z': bd = Vector((bd.z, bd.x, bd.y))

        wh = world_center; wt = world_center + bd
        if self.swap_yz_axes:
            wh = Vector((wh.x, wh.z, wh.y)); wt = Vector((wt.x, wt.z, wt.y))

        bone.head = wh; bone.tail = wt
        rmap = {'WORLD_Z': Vector((0,0,1)), 'WORLD_X': Vector((1,0,0)), 'WORLD_Y': Vector((0,1,0))}
        if self.align_roll_to_axis in rmap:
            bone.align_roll(rmap[self.align_roll_to_axis])
        else:
            bone.roll = 0.0

        bpy.ops.object.mode_set(mode='OBJECT')

        # Create vertex group and assign vertices with weight
        context.view_layer.objects.active = obj
        vg = obj.vertex_groups.get(bone_name) or obj.vertex_groups.new(name=bone_name)
        vg.add(vert_indices, self.vertex_weight, 'REPLACE')

        # Add armature modifier if not present
        if not any(mod.type == 'ARMATURE' and mod.object == armature for mod in obj.modifiers):
            am = obj.modifiers.new(name="Armature", type='ARMATURE')
            am.object = armature

        # Return to edit mode so user can continue selecting
        bpy.ops.object.mode_set(mode='EDIT')

        self.report({'INFO'},
            f"Created bone '{bone_name}', assigned {len(vert_indices)} verts (weight={self.vertex_weight:.2f})")
        return {'FINISHED'}

    def invoke(self, context, event):
        if context.mode != 'EDIT_MESH':
            self.report({'ERROR'}, "Must be in Edit Mode")
            return {'CANCELLED'}
        bm = bmesh.from_edit_mesh(context.active_object.data)
        if not any(v.select for v in bm.verts):
            self.report({'ERROR'}, "No vertices selected")
            return {'CANCELLED'}
        return context.window_manager.invoke_props_dialog(self, width=420)

    def draw(self, context):
        layout = self.layout
        mode = get_mode(context)
        prefix = get_bone_prefix(context)

        box = layout.box()
        box.label(text="Bone Settings", icon='BONE_DATA')
        box.prop(self, "custom_bone_name")
        box.label(text=f"(prefix: {prefix})", icon='INFO')

        box.separator()
        box.prop(self, "vertex_weight", slider=True)

        layout.separator()
        box = layout.box()
        box.label(text="Bone Direction:", icon='ORIENTATION_GLOBAL')
        box.prop(self, "use_world_direction")
        if self.use_world_direction:
            box.prop(self, "world_direction")
            box.prop(self, "preserve_angle")
        else:
            box.prop(self, "invert_bone_direction")

        layout.separator()
        box = layout.box()
        box.label(text="Bone Orientation:", icon='DRIVER_ROTATIONAL_DIFFERENCE')
        box.prop(self, "bone_primary_axis")
        box.prop(self, "swap_yz_axes")
        box.prop(self, "align_roll_to_axis")

        layout.separator()
        box = layout.box()
        box.label(text="Bone Hierarchy:", icon='OUTLINER')
        box.prop(self, "parent_to_specific_bone")
        if self.parent_to_specific_bone:
            box.prop(self, "target_bone", text="", icon='BONE_DATA')
        else:
            default = "w_root" if mode == 'WEAPON' else "v_body"
            box.box().label(text=f"Default parent: {default}", icon='INFO')


# ============================================================================
# ADD TO OBJECT OPERATOR
# ============================================================================
class ARVEHICLES_OT_add_to_object(bpy.types.Operator):
    bl_idname = "arvehicles.add_to_object"
    bl_label = "Add Bone/Socket to Object"
    bl_description = "Add bone and/or socket to already-separated mesh objects (object mode)"
    bl_options = {'REGISTER', 'UNDO'}

    component_type: bpy.props.EnumProperty(name="Component Type", items=_component_type_items)
    custom_name: bpy.props.StringProperty(name="Rename Object", default="")

    add_socket: bpy.props.BoolProperty(name="Add Socket", default=True)
    custom_socket_name: bpy.props.StringProperty(name="Custom Socket Name", default="")
    set_origin_to_socket: bpy.props.BoolProperty(name="Set Origin to Socket", default=True)
    socket_parent_mode: bpy.props.EnumProperty(
        name="Parent Socket",
        items=[
            ('ARMATURE', "Parent to Armature", "Parent socket to the armature object"),
            ('BONE',     "Parent to Bone",     "Parent socket to a specific existing bone"),
            ('NEW_BONE', "Parent to New Bone", "Parent socket to the bone being created (requires Add Bone)"),
            ('NONE',     "Don't Parent",       "Leave socket unparented"),
        ],
        default='ARMATURE',
    )
    socket_target_bone: bpy.props.EnumProperty(
        name="Socket Parent Bone", items=_get_available_bones
    )

    add_bone: bpy.props.BoolProperty(name="Add Bone", default=False)
    custom_bone_name: bpy.props.StringProperty(name="Custom Bone Name", default="")
    auto_skinning: bpy.props.BoolProperty(name="Auto Skinning", default=True)
    set_mesh_origin_to_bone: bpy.props.BoolProperty(name="Set Mesh Origin to Bone", default=True)
    invert_bone_direction: bpy.props.BoolProperty(name="Invert Bone Direction", default=False)

    world_direction: bpy.props.EnumProperty(
        name="Bone Direction",
        items=[
            ('POS_Y', "+Y (Forward)", ""), ('NEG_Y', "-Y (Backward)", ""),
            ('POS_X', "+X (Right)", ""),   ('NEG_X', "-X (Left)", ""),
            ('POS_Z', "+Z (Up)", ""),      ('NEG_Z', "-Z (Down)", ""),
        ],
        default='POS_Y'
    )
    bone_primary_axis: bpy.props.EnumProperty(
        name="Primary Rotation Axis",
        items=[('Y', "Y Axis (Default)", ""), ('X', "X Axis", ""), ('Z', "Z Axis", "")],
        default='Y'
    )
    swap_yz_axes: bpy.props.BoolProperty(name="Swap Y<>Z Axes", default=False)
    align_roll_to_axis: bpy.props.EnumProperty(
        name="Align Roll To",
        items=[
            ('NONE', "Auto (Roll=0)", ""), ('WORLD_Z', "World Z (Up)", ""),
            ('WORLD_X', "World X", ""),    ('WORLD_Y', "World Y", ""),
        ],
        default='WORLD_Z'
    )
    parent_to_specific_bone: bpy.props.BoolProperty(name="Parent Bone to Specific Bone", default=False)

    def get_available_bones(self, context):
        mode = get_mode(context)
        default = "w_root (Default)" if mode == 'WEAPON' else "v_body (Default)"
        items = [('NONE', default, "")]
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                for bone in obj.data.bones:
                    items.append((bone.name, bone.name, ""))
                break
        return items

    target_bone: bpy.props.EnumProperty(name="Parent Bone", items=get_available_bones)

    parent_to_existing_bone: bpy.props.BoolProperty(name="Skin to Existing Bone", default=False)

    def get_existing_bones(self, context):
        items = [('NONE', "Select Bone", "")]
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                for bone in obj.data.bones:
                    items.append((bone.name, bone.name, ""))
                break
        return items

    existing_target_bone: bpy.props.EnumProperty(name="Target Bone", items=get_existing_bones)

    def execute(self, context):
        if context.mode != 'OBJECT':
            self.report({'ERROR'}, "Must be in Object Mode")
            return {'CANCELLED'}

        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not mesh_objects:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}

        prefix = get_bone_prefix(context)
        mode   = get_mode(context)
        default_parent = 'w_root' if mode == 'WEAPON' else 'v_body'

        armature = next((obj for obj in bpy.data.objects if obj.type == 'ARMATURE'), None)

        dmap = {
            'POS_Y': Vector((0,1,0)), 'NEG_Y': Vector((0,-1,0)),
            'POS_X': Vector((1,0,0)), 'NEG_X': Vector((-1,0,0)),
            'POS_Z': Vector((0,0,1)), 'NEG_Z': Vector((0,0,-1)),
        }
        rmap = {'WORLD_Z': Vector((0,0,1)), 'WORLD_X': Vector((1,0,0)), 'WORLD_Y': Vector((0,1,0))}

        socket_type = _get_socket_type(context, self.component_type)
        bone_type   = _get_bone_type(context, self.component_type)

        processed = 0
        for obj in mesh_objects:
            world_center = sum(
                (obj.matrix_world @ Vector(c) for c in obj.bound_box), Vector()
            ) / 8

            if self.custom_name and len(mesh_objects) == 1:
                obj.name = self.custom_name
            obj["component_type"] = self.component_type

            bd = dmap[self.world_direction].copy()
            if self.invert_bone_direction: bd = -bd
            if self.bone_primary_axis == 'X': bd = Vector((bd.y, bd.z, bd.x))
            elif self.bone_primary_axis == 'Z': bd = Vector((bd.z, bd.x, bd.y))
            if self.swap_yz_axes: bd = Vector((bd.x, bd.z, bd.y))
            bd.normalize()

            bone_name = None

            if self.add_bone:
                if not armature:
                    arm_data = bpy.data.armatures.new("Armature")
                    armature = bpy.data.objects.new("Armature", arm_data)
                    context.collection.objects.link(armature)
                    context.view_layer.objects.active = armature
                    bpy.ops.object.mode_set(mode='EDIT')
                    rb = arm_data.edit_bones.new(default_parent if mode == 'WEAPON' else 'v_root')
                    rb.head = (0,0,0); rb.tail = (0,0.2,0)
                    if mode == 'VEHICLE':
                        bb = arm_data.edit_bones.new('v_body')
                        bb.head = (0,0,0.35); bb.tail = (0,0.2,0.35); bb.parent = rb
                    bpy.ops.object.mode_set(mode='OBJECT')

                if self.custom_bone_name:
                    bone_name = _enforce_prefix(self.custom_bone_name, prefix)
                elif bone_type == 'custom':
                    bone_name = _enforce_prefix(obj.name.lower().replace(' ','_'), prefix)
                else:
                    bone_name = bone_type
                    base = bone_name; counter = 1
                    while bone_name in armature.data.bones:
                        bone_name = f"{base}_{counter:02d}"; counter += 1

                context.view_layer.objects.active = armature
                bpy.ops.object.mode_set(mode='EDIT')
                bone = armature.data.edit_bones.new(bone_name)

                if self.parent_to_specific_bone and self.target_bone != 'NONE':
                    if self.target_bone in armature.data.edit_bones:
                        bone.parent = armature.data.edit_bones[self.target_bone]
                        bone.use_connect = False
                elif default_parent in armature.data.edit_bones:
                    bone.parent = armature.data.edit_bones[default_parent]
                elif 'v_root' in armature.data.edit_bones:
                    bone.parent = armature.data.edit_bones['v_root']

                bone.head = world_center
                bone.tail = world_center + bd * 0.2
                if self.align_roll_to_axis in rmap:
                    bone.align_roll(rmap[self.align_roll_to_axis])
                else:
                    bone.roll = 0.0

                bpy.ops.object.mode_set(mode='OBJECT')

                if self.set_mesh_origin_to_bone:
                    bpy.ops.object.select_all(action='DESELECT')
                    obj.select_set(True)
                    context.view_layer.objects.active = obj
                    saved = context.scene.cursor.location.copy()
                    context.scene.cursor.location = world_center
                    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
                    context.scene.cursor.location = saved

                if self.auto_skinning:
                    bpy.ops.object.select_all(action='DESELECT')
                    obj.select_set(True)
                    context.view_layer.objects.active = obj
                    for mod in list(obj.modifiers):
                        if mod.type == 'ARMATURE': obj.modifiers.remove(mod)
                    obj.vertex_groups.clear()
                    vg = obj.vertex_groups.new(name=bone_name)
                    bpy.ops.object.mode_set(mode='EDIT')
                    bpy.ops.mesh.select_all(action='SELECT')
                    obj.vertex_groups.active = vg
                    bpy.ops.object.vertex_group_assign()
                    bpy.ops.object.mode_set(mode='OBJECT')
                    am = obj.modifiers.new(name="Armature", type='ARMATURE')
                    am.object = armature

            elif self.parent_to_existing_bone and self.existing_target_bone != 'NONE':
                if armature and self.existing_target_bone in armature.data.bones:
                    bpy.ops.object.select_all(action='DESELECT')
                    obj.select_set(True)
                    context.view_layer.objects.active = obj
                    for mod in list(obj.modifiers):
                        if mod.type == 'ARMATURE': obj.modifiers.remove(mod)
                    obj.vertex_groups.clear()
                    vg = obj.vertex_groups.new(name=self.existing_target_bone)
                    bpy.ops.object.mode_set(mode='EDIT')
                    bpy.ops.mesh.select_all(action='SELECT')
                    obj.vertex_groups.active = vg
                    bpy.ops.object.vertex_group_assign()
                    bpy.ops.object.mode_set(mode='OBJECT')
                    am = obj.modifiers.new(name="Armature", type='ARMATURE')
                    am.object = armature
                else:
                    self.report({'WARNING'}, f"Bone '{self.existing_target_bone}' not found")

            if self.add_socket:
                socket_name = self.custom_socket_name or \
                    f"Socket_{socket_type.replace('_',' ').title().replace(' ','_')}"
                if not self.custom_socket_name:
                    existing = [o for o in bpy.data.objects if socket_name in o.name]
                    if existing:
                        socket_name = f"{socket_name}_{len(existing)+1:02d}"
                sock = bpy.data.objects.new(socket_name, None)
                sock.empty_display_type = 'ARROWS'
                sock.empty_display_size = 0.15
                sock.location = world_center
                context.collection.objects.link(sock)
                sock["socket_type"]   = socket_type
                sock["attached_part"] = obj.name
                sock["vehicle_part"]  = "attachment_point"
                if armature and self.socket_parent_mode != 'NONE':
                    if self.socket_parent_mode == 'ARMATURE':
                        sock.parent = armature
                        sock.parent_type = 'OBJECT'
                        sock.matrix_parent_inverse = armature.matrix_world.inverted()
                    elif self.socket_parent_mode == 'BONE' and self.socket_target_bone != 'NONE':
                        if self.socket_target_bone in armature.data.bones:
                            sock.parent = armature
                            sock.parent_type = 'BONE'
                            sock.parent_bone = self.socket_target_bone
                            pb = armature.pose.bones.get(self.socket_target_bone)
                            sock.matrix_parent_inverse = (armature.matrix_world @ pb.matrix).inverted() if pb else armature.matrix_world.inverted()
                    elif self.socket_parent_mode == 'NEW_BONE' and bone_name and bone_name in armature.data.bones:
                        sock.parent = armature
                        sock.parent_type = 'BONE'
                        sock.parent_bone = bone_name
                        pb = armature.pose.bones.get(bone_name)
                        sock.matrix_parent_inverse = (armature.matrix_world @ pb.matrix).inverted() if pb else armature.matrix_world.inverted()
                if self.set_origin_to_socket:
                    bpy.ops.object.select_all(action='DESELECT')
                    obj.select_set(True)
                    context.view_layer.objects.active = obj
                    saved = context.scene.cursor.location.copy()
                    context.scene.cursor.location = sock.location
                    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
                    context.scene.cursor.location = saved

            processed += 1

        bpy.ops.object.select_all(action='DESELECT')
        for obj in mesh_objects:
            obj.select_set(True)
        if mesh_objects:
            context.view_layer.objects.active = mesh_objects[0]

        self.report({'INFO'}, f"Processed {processed} object(s)")
        return {'FINISHED'}

    def invoke(self, context, event):
        if context.mode != 'OBJECT':
            self.report({'ERROR'}, "Must be in Object Mode")
            return {'CANCELLED'}
        if not [obj for obj in context.selected_objects if obj.type == 'MESH']:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}
        return context.window_manager.invoke_props_dialog(self, width=420)

    def draw(self, context):
        layout = self.layout
        mode = get_mode(context)
        prefix = get_bone_prefix(context)
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']

        box = layout.box()
        box.label(text=f"Selected Objects: {len(mesh_objects)}", icon='OBJECT_DATA')
        for obj in mesh_objects[:4]:
            box.label(text=f"  - {obj.name}")
        if len(mesh_objects) > 4:
            box.label(text=f"  ... and {len(mesh_objects) - 4} more")

        layout.prop(self, "component_type")
        if len(mesh_objects) == 1:
            layout.prop(self, "custom_name")

        layout.separator()
        box = layout.box()
        box.label(text="Socket Options", icon='EMPTY_DATA')
        box.prop(self, "add_socket")
        if self.add_socket:
            box.prop(self, "custom_socket_name")
            box.prop(self, "set_origin_to_socket")
            box.prop(self, "socket_parent_mode", text="Parent")
            if self.socket_parent_mode == 'BONE':
                box.prop(self, "socket_target_bone", text="", icon='BONE_DATA')
            elif self.socket_parent_mode == 'NEW_BONE' and not self.add_bone:
                box.label(text="Enable 'Add Bone' to use this option", icon='ERROR')

        layout.separator()
        box = layout.box()
        box.label(text="Bone Options", icon='BONE_DATA')
        box.prop(self, "add_bone")
        if self.add_bone:
            box.prop(self, "custom_bone_name")
            box.label(text=f"(prefix: {prefix})", icon='INFO')
            box.prop(self, "auto_skinning")
            box.prop(self, "set_mesh_origin_to_bone")
            box.separator()
            box.label(text="Bone Direction:")
            box.prop(self, "world_direction")
            box.prop(self, "invert_bone_direction")
            box.separator()
            box.label(text="Bone Orientation:")
            box.prop(self, "bone_primary_axis")
            box.prop(self, "swap_yz_axes")
            box.prop(self, "align_roll_to_axis")
            box.separator()
            box.prop(self, "parent_to_specific_bone")
            if self.parent_to_specific_bone:
                box.prop(self, "target_bone", text="", icon='BONE_DATA')
            else:
                default = "w_root" if mode == 'WEAPON' else "v_body"
                box.box().label(text=f"Default parent: {default}", icon='INFO')
        else:
            box.separator()
            box.prop(self, "parent_to_existing_bone")
            if self.parent_to_existing_bone:
                box.prop(self, "existing_target_bone", text="", icon='BONE_DATA')
