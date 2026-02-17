import bpy
from ..constants import (
    VEHICLE_BONE_TYPES, WEAPON_BONE_TYPES,
    get_mode, get_bone_types, get_bone_prefix, get_root_bones,
)
from mathutils import Vector


def _get_bone_type_items(self, context):
    return get_bone_types(context)


class ARVEHICLES_OT_create_armature(bpy.types.Operator):
    bl_idname = "arvehicles.create_armature"
    bl_label = "Create Armature"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Create armature with root/body bones and setup selected mesh"

    def execute(self, context):
        mode = get_mode(context)
        root_name, body_name = get_root_bones(context)

        body_mesh = None
        if context.active_object and context.active_object.type == 'MESH':
            body_mesh = context.active_object

        # Check if armature already exists
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE' and obj.name in ["Armature", "VehicleArmature"]:
                self.report({'INFO'}, f"Armature '{obj.name}' already exists")
                context.view_layer.objects.active = obj
                return {'FINISHED'}

        armature_data = bpy.data.armatures.new("Armature")
        armature_obj  = bpy.data.objects.new("Armature", armature_data)
        context.collection.objects.link(armature_obj)

        armature_obj.location       = (0, 0, 0)
        armature_obj.rotation_euler = (0, 0, 0)
        armature_obj.scale          = (1.0, 1.0, 1.0)

        context.view_layer.objects.active = armature_obj
        bpy.ops.object.mode_set(mode='EDIT')

        root_bone      = armature_data.edit_bones.new(root_name)
        root_bone.head = (0, 0, 0)
        root_bone.tail = (0, 0.2, 0)
        root_bone.roll = 0.0

        if body_name:
            body_bone        = armature_data.edit_bones.new(body_name)
            body_bone.head   = (0, 0, 0.35)
            body_bone.tail   = (0, 0.2, 0.35)
            body_bone.roll   = 0.0
            body_bone.parent = root_bone

        bpy.ops.object.mode_set(mode='OBJECT')

        armature_data.display_type = 'OCTAHEDRAL'
        armature_data.show_names   = True
        armature_obj.show_in_front = True

        skin_bone = body_name if body_name else root_name

        if body_mesh:
            vg = body_mesh.vertex_groups.get(skin_bone) or body_mesh.vertex_groups.new(name=skin_bone)
            all_verts = [v.index for v in body_mesh.data.vertices]
            vg.add(all_verts, 1.0, 'REPLACE')

            if not any(mod.type == 'ARMATURE' for mod in body_mesh.modifiers):
                arm_mod        = body_mesh.modifiers.new(name="Armature", type='ARMATURE')
                arm_mod.object = armature_obj

            world_matrix           = body_mesh.matrix_world.copy()
            body_mesh.parent       = armature_obj
            body_mesh.parent_type  = 'ARMATURE'
            body_mesh.matrix_world = world_matrix

            self.report({'INFO'}, f"Created {mode.lower()} armature, setup '{body_mesh.name}' as body")
        else:
            self.report({'INFO'}, f"Created {mode.lower()} armature (no mesh selected)")

        return {'FINISHED'}


class ARVEHICLES_OT_create_bone(bpy.types.Operator):
    bl_idname = "arvehicles.create_bone"
    bl_label = "Add Bone"
    bl_options = {'REGISTER', 'UNDO'}

    bone_type: bpy.props.EnumProperty(
        name="Bone Type",
        items=_get_bone_type_items,
    )
    custom_bone_name: bpy.props.StringProperty(name="Bone Name", default="custom")

    def execute(self, context):
        prefix = get_bone_prefix(context)
        mode   = get_mode(context)
        root_name, body_name = get_root_bones(context)

        armature = next((obj for obj in bpy.data.objects if obj.type == 'ARMATURE'), None)
        if not armature:
            self.report({'ERROR'}, "No armature found")
            return {'CANCELLED'}

        context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='EDIT')

        bone_length = 0.2

        # Naming
        if self.bone_type == 'custom':
            bone_name = self.custom_bone_name
            if not bone_name.startswith(prefix):
                bone_name = prefix + bone_name
        else:
            bone_name = self.bone_type

        # Deduplicate
        if bone_name in armature.data.edit_bones:
            if bone_name in [root_name, body_name]:
                self.report({'INFO'}, f"{bone_name} already exists")
                bpy.ops.object.mode_set(mode='OBJECT')
                return {'FINISHED'}
            base = bone_name
            counter = 1
            while bone_name in armature.data.edit_bones:
                bone_name = f"{base}_{counter:02d}"
                counter += 1

        # Parenting
        parent_bone = None
        root_bones = {root_name, body_name} - {None}
        if self.bone_type not in root_bones:
            if body_name and body_name in armature.data.edit_bones:
                parent_bone = armature.data.edit_bones[body_name]
            elif root_name in armature.data.edit_bones:
                parent_bone = armature.data.edit_bones[root_name]
        elif self.bone_type == body_name and root_name in armature.data.edit_bones:
            parent_bone = armature.data.edit_bones[root_name]

        bone = armature.data.edit_bones.new(bone_name)
        bone.roll = 0.0
        if parent_bone:
            bone.parent = parent_bone

        # Positioning — vehicles use detailed offsets, weapons all default to origin
        if mode == 'WEAPON':
            bone.head = (0, 0, 0.1)
            bone.tail = (0, bone_length, 0.1)
        else:
            if self.bone_type == root_name:
                bone.head = (0, 0, 0)
                bone.tail = (0, bone_length, 0)
            elif self.bone_type == body_name:
                bone.head = (0, 0.35, 0)
                bone.tail = (0, 0.35 + bone_length, 0)
            elif 'door_left' in self.bone_type:
                bone.head = (0.8, 0.2, 0.8)
                bone.tail = (0.8, 0.2 + bone_length, 0.8)
            elif 'door_right' in self.bone_type:
                bone.head = (-0.8, 0.2, 0.8)
                bone.tail = (-0.8, 0.2 + bone_length, 0.8)
            elif 'wheel' in self.bone_type:
                bone.head = (0.7, 1.0, 0.3)
                bone.tail = (0.7, 1.0 + bone_length, 0.3)
            elif self.bone_type == 'v_hood':
                bone.head = (0, 1.5, 1.0)
                bone.tail = (0, 1.5 + bone_length, 1.0)
            elif self.bone_type == 'v_trunk':
                bone.head = (0, -1.5, 1.0)
                bone.tail = (0, -1.5 + bone_length, 1.0)
            elif self.bone_type == 'v_steeringwheel':
                bone.head = (0.3, 0.5, 0.9)
                bone.tail = (0.3, 0.5 + bone_length, 0.9)
            else:
                bone.head = (0, 0, 0.5)
                bone.tail = (0, bone_length, 0.5)

        bpy.ops.object.mode_set(mode='OBJECT')
        self.report({'INFO'}, f"Created {bone_name} bone")
        return {'FINISHED'}

    def invoke(self, context, event):
        if self.bone_type == 'custom':
            return context.window_manager.invoke_props_dialog(self)
        return self.execute(context)


# ============================================================================
# ALIGN SELECTED BONES DIRECTION OPERATOR
# ============================================================================
class ARVEHICLES_OT_align_bones_direction(bpy.types.Operator):
    bl_idname = "arvehicles.align_bones_direction"
    bl_label = "Align Bone Directions"
    bl_description = "Force selected bones to point in a specific world direction, preserving head positions"
    bl_options = {'REGISTER', 'UNDO'}

    world_direction: bpy.props.EnumProperty(
        name="Direction",
        items=[
            ('POS_Y', "+Y (Forward)",  "Point toward +Y"),
            ('NEG_Y', "-Y (Backward)", "Point toward -Y"),
            ('POS_X', "+X (Right)",    "Point toward +X"),
            ('NEG_X', "-X (Left)",     "Point toward -X"),
            ('POS_Z', "+Z (Up)",       "Point toward +Z"),
            ('NEG_Z', "-Z (Down)",     "Point toward -Z"),
        ],
        default='POS_Y'
    )
    invert_direction: bpy.props.BoolProperty(name="Invert Direction", default=False)
    bone_primary_axis: bpy.props.EnumProperty(
        name="Primary Rotation Axis",
        items=[
            ('Y', "Y Axis (Default)", ""),
            ('X', "X Axis", ""),
            ('Z', "Z Axis", ""),
        ],
        default='Y'
    )
    swap_yz_axes: bpy.props.BoolProperty(name="Swap Y<>Z Axes", default=False)
    align_roll_to_axis: bpy.props.EnumProperty(
        name="Align Roll To",
        items=[
            ('NONE',    "Auto (Roll=0)", "Set roll to 0"),
            ('WORLD_Z', "World Z (Up)",  ""),
            ('WORLD_X', "World X",       ""),
            ('WORLD_Y', "World Y",       ""),
        ],
        default='WORLD_Z'
    )
    preserve_length: bpy.props.BoolProperty(name="Preserve Bone Length", default=True)
    fixed_length: bpy.props.FloatProperty(
        name="Fixed Length", default=0.2, min=0.001, soft_max=2.0, unit='LENGTH'
    )

    def execute(self, context):
        if context.mode != 'EDIT_ARMATURE':
            self.report({'ERROR'}, "Must be in Armature Edit Mode")
            return {'CANCELLED'}

        armature = context.active_object
        if not armature or armature.type != 'ARMATURE':
            self.report({'ERROR'}, "Active object must be an armature")
            return {'CANCELLED'}

        selected_bones = [b for b in armature.data.edit_bones if b.select]
        if not selected_bones:
            self.report({'ERROR'}, "No bones selected")
            return {'CANCELLED'}

        direction_map = {
            'POS_Y': Vector((0,  1, 0)),
            'NEG_Y': Vector((0, -1, 0)),
            'POS_X': Vector(( 1, 0, 0)),
            'NEG_X': Vector((-1, 0, 0)),
            'POS_Z': Vector((0, 0,  1)),
            'NEG_Z': Vector((0, 0, -1)),
        }
        direction = direction_map[self.world_direction].copy()

        if self.invert_direction:
            direction = -direction
        if self.bone_primary_axis == 'X':
            direction = Vector((direction.y, direction.z, direction.x))
        elif self.bone_primary_axis == 'Z':
            direction = Vector((direction.z, direction.x, direction.y))
        if self.swap_yz_axes:
            direction = Vector((direction.x, direction.z, direction.y))
        direction.normalize()

        roll_axis_map = {
            'WORLD_Z': Vector((0, 0, 1)),
            'WORLD_X': Vector((1, 0, 0)),
            'WORLD_Y': Vector((0, 1, 0)),
        }

        count = 0
        for bone in selected_bones:
            length = bone.length if self.preserve_length else self.fixed_length
            if length < 0.001:
                length = 0.2
            bone.tail = bone.head + direction * length
            if self.align_roll_to_axis in roll_axis_map:
                bone.align_roll(roll_axis_map[self.align_roll_to_axis])
            else:
                bone.roll = 0.0
            count += 1

        self.report({'INFO'}, f"Aligned {count} bone(s) to {self.world_direction}")
        return {'FINISHED'}

    def invoke(self, context, event):
        if context.mode != 'EDIT_ARMATURE':
            self.report({'ERROR'}, "Must be in Armature Edit Mode")
            return {'CANCELLED'}
        if not [b for b in context.active_object.data.edit_bones if b.select]:
            self.report({'ERROR'}, "No bones selected")
            return {'CANCELLED'}
        return context.window_manager.invoke_props_dialog(self, width=340)

    def draw(self, context):
        layout = self.layout
        armature = context.active_object
        selected = [b for b in armature.data.edit_bones if b.select] if context.mode == 'EDIT_ARMATURE' else []

        box = layout.box()
        box.label(text=f"Selected Bones: {len(selected)}", icon='BONE_DATA')
        for bone in selected[:6]:
            box.label(text=f"  - {bone.name}")
        if len(selected) > 6:
            box.label(text=f"  ... and {len(selected) - 6} more")

        layout.separator()
        box = layout.box()
        box.label(text="Direction", icon='ORIENTATION_GLOBAL')
        box.prop(self, "world_direction")
        box.prop(self, "invert_direction")

        layout.separator()
        box = layout.box()
        box.label(text="Orientation", icon='DRIVER_ROTATIONAL_DIFFERENCE')
        box.prop(self, "bone_primary_axis")
        box.prop(self, "swap_yz_axes")
        box.prop(self, "align_roll_to_axis")

        layout.separator()
        box = layout.box()
        box.label(text="Length", icon='DRIVER_DISTANCE')
        box.prop(self, "preserve_length")
        if not self.preserve_length:
            box.prop(self, "fixed_length")
