bl_info = {
    "name": "Arma Reforger Weapon Tools Enhanced",
    "author": "steffen",
    "version": (2, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > AR Weapons",
    "description": "Enhanced tools for preparing and rigging weapons for Arma Reforger",
    "category": "Object",
}

import bpy
import bmesh
import math
from mathutils import Vector, Matrix

# Standard dimensions for Arma Reforger weapons
STANDARD_WEAPON_LENGTH = 0.7  # From barrel_muzzle to back of weapon
STANDARD_WEAPON_HEIGHT = 0.25  # From bottom to top
STANDARD_WEAPON_WIDTH = 0.07   # Width of weapon (X axis)
STANDARD_BARREL_HEIGHT = 0.062  # Height of barrel from ground

WEAPON_SOCKET_TYPES = [
    ('slot_magazine', "Magazine Well", "Magazine attachment slot"),
    ('slot_optics', "Optics Mount", "Optics attachment slot"),
    ('slot_barrel_muzzle', "Muzzle", "Muzzle attachment slot"),
    ('slot_underbarrel', "Underbarrel", "Underbarrel attachment slot"),
    ('slot_bayonet', "Bayonet Mount", "Bayonet attachment slot"),
    ('slot_flashlight', "Flashlight", "Flashlight attachment slot"),
    ('snap_hand_right', "Hand Right", "Right hand IK target"),
    ('snap_hand_left', "Hand Left", "Left hand IK target"),
    ('eye', "Eye Point", "Aiming down sight point"),
    ('barrel_chamber', "Barrel Chamber", "Barrel chamber position"),
    ('barrel_muzzle', "Barrel Muzzle", "Barrel muzzle direction"),
    ('custom', "Custom", "Custom socket type"),
]

WEAPON_COMPONENT_TYPES = [
    ('sight', "Sight", "Sight component"),
    ('light', "Light", "Light component"),
    ('trigger', "Trigger", "Trigger component"),
    ('bolt', "Bolt", "Bolt component"),
    ('charging_handle', "Charging Handle", "Charging handle component"),
    ('mag_release', "Magazine Release", "Magazine release component"),
    ('safety', "Safety", "Safety component"),
    ('fire_mode', "Fire Mode", "Fire mode selector component"),
    ('hammer', "Hammer", "Hammer component"),
    ('striker', "Striker", "Striker component"),
    ('slide', "Slide", "Slide component"),
    ('barrel', "Barrel", "Barrel component"),
    ('buttstock', "Buttstock", "Buttstock component"),
    ('ejection_port', "Ejection Port", "Ejection port component"),
    ('bipod', "Bipod", "Bipod component"),
    ('accessory', "Accessory", "Accessory component"),
    ('custom', "Custom", "Custom component type"),
]

WEAPON_BONE_TYPES = [
    ('w_root', "Root Bone", "Main weapon bone"),
    ('w_fire_mode', "Fire Mode", "Fire selector bone"),
    ('w_ch_handle', "Charging Handle", "Charging handle bone"),
    ('w_trigger', "Trigger", "Trigger bone"),
    ('w_bolt', "Bolt", "Bolt/slide bone"),
    ('w_mag_release', "Mag Release", "Magazine release bone"),
    ('w_safety', "Safety", "Safety lever bone"),
    ('w_buttstock', "Buttstock", "Buttstock bone"),
    ('w_ejection_port', "Ejection Port", "Ejection port bone"),
    ('w_bolt_release', "Bolt Release", "Bolt release bone"),
    ('w_slide', "Slide", "Slide bone (pistols)"),
    ('w_hammer', "Hammer", "Hammer bone"),
    ('w_striker', "Striker", "Striker bone"),
    ('w_cylinder', "Cylinder", "Cylinder bone (revolvers)"),
    ('w_rear_sight', "Rear Sight", "Rear sight bone"),
    ('w_front_sight', "Front Sight", "Front sight bone"),
    ('w_barrel', "Barrel", "Barrel bone"),
    ('w_bipodleg', "Bipod Leg", "Bipod leg bone"),
    ('w_bipodleg_left', "Bipod Left", "Left bipod leg bone"),
    ('w_bipodleg_right', "Bipod Right", "Right bipod leg bone"),
    ('w_fire_hammer', "Fire Hammer", "Fire hammer bone"),
    ('w_sight', "Sight", "Sight bone"),
    ('w_sight_slider', "Sight Slider", "Sight slider bone"),
    ('custom', "Custom Bone", "Add a custom bone"),
]



class ARVEHICLES_OT_manage_presets(bpy.types.Operator):
    bl_idname = "arvehicles.manage_presets"
    bl_label = "Manage Vehicle Presets"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Create and manage lists of bone/socket names for two-phase separation"
    
    preset_name: bpy.props.StringProperty(name="Preset Name", default="MyVehicle")
    
    bone_names: bpy.props.StringProperty(
        name="Bone Names", 
        default="v_door_left,v_door_right,v_hood,v_trunk,v_wheel_1,v_wheel_2,v_wheel_3,v_wheel_4",
        description="Comma-separated list of bone names"
    )
    socket_names: bpy.props.StringProperty(
        name="Socket Names",
        default="Socket_Door,Socket_Door,Socket_Hood,Socket_Trunk,Socket_Wheel,Socket_Wheel,Socket_Wheel,Socket_Wheel", 
        description="Comma-separated list of socket names"
    )
    
    parent_meshes: bpy.props.BoolProperty(
        name="Parent Meshes to Armature",
        default=True,
        description="Automatically parent separated meshes to the armature"
    )
    
    def execute(self, context):
        scene = context.scene
        
        # Parse the lists
        bones = [name.strip() for name in self.bone_names.split(",") if name.strip()]
        sockets = [name.strip() for name in self.socket_names.split(",") if name.strip()]
        
        # Store preset data as individual scene properties
        preset_prefix = f"arvehicles_preset_{self.preset_name}_"
        
        # Clear any existing preset data
        keys_to_remove = [key for key in scene.keys() if key.startswith(preset_prefix)]
        for key in keys_to_remove:
            del scene[key]
        
        # Use the longer list as the count - bones take priority
        max_count = max(len(bones), len(sockets)) if sockets else len(bones)
        
        # Store new preset data
        scene[f"{preset_prefix}count"] = max_count
        scene[f"{preset_prefix}bone_index"] = 0
        scene[f"{preset_prefix}socket_index"] = 0
        scene[f"{preset_prefix}phase"] = "bones"
        scene[f"{preset_prefix}parent_meshes"] = self.parent_meshes
        
        # Store bone data - all bones get stored
        for i in range(max_count):
            if i < len(bones):
                scene[f"{preset_prefix}bone_{i}"] = bones[i]
            else:
                # If we run out of bones, create generic names
                scene[f"{preset_prefix}bone_{i}"] = f"v_component_{i+1:03d}"
        
        # Store socket data - pad with generic names if needed
        for i in range(max_count):
            if i < len(sockets):
                scene[f"{preset_prefix}socket_{i}"] = sockets[i]
            else:
                # If we run out of sockets, create generic names
                scene[f"{preset_prefix}socket_{i}"] = f"Socket_Component_{i+1:03d}"
        
        # Set as active preset
        scene["arvehicles_active_preset"] = self.preset_name
        
        # Debug info
        print(f"Debug: Parsed {len(bones)} bones, {len(sockets)} sockets")
        print(f"Debug: Stored {max_count} items total")
        
        # Report with length information
        if len(bones) != len(sockets):
            self.report({'WARNING'}, f"Created preset '{self.preset_name}' with {max_count} items. Note: {len(bones)} bones, {len(sockets)} sockets - padded shorter list")
        else:
            self.report({'INFO'}, f"Created preset '{self.preset_name}' with {max_count} items. Starting with bone separation phase!")
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=400)
    
    def draw(self, context):
        layout = self.layout
        
        layout.prop(self, "preset_name")
        layout.separator()
        
        layout.label(text="Bone Names (comma-separated):")
        layout.prop(self, "bone_names", text="")
        
        layout.label(text="Socket Names (comma-separated):")  
        layout.prop(self, "socket_names", text="")
        
        layout.separator()
        layout.prop(self, "parent_meshes")
        
        layout.separator()
        layout.label(text="Phase 1: Bone separation with auto mesh naming")
        layout.label(text="Phase 2: Socket placement using face selection")
        layout.separator()
        layout.label(text="Note: Lists can have different lengths - shorter list will be padded")

class ARVEHICLES_OT_preset_separation(bpy.types.Operator):
    bl_idname = "arvehicles.preset_separation"
    bl_label = "Preset Action"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Separate component or place socket using current preset item"
    
    auto_skinning: bpy.props.BoolProperty(name="Auto Skinning", default=True)
    
    def execute(self, context):
        scene = context.scene
        
        if "arvehicles_active_preset" not in scene:
            self.report({'ERROR'}, "No active preset. Create a preset first.")
            return {'CANCELLED'}
        
        preset_name = scene["arvehicles_active_preset"]
        preset_prefix = f"arvehicles_preset_{preset_name}_"
        
        count_key = f"{preset_prefix}count"
        if count_key not in scene:
            self.report({'ERROR'}, f"Preset '{preset_name}' data not found. Create the preset again.")
            return {'CANCELLED'}
        
        preset_count = scene[count_key]
        current_phase = scene.get(f"{preset_prefix}phase", "bones")
        
        if current_phase == "bones":
            return self._do_bone_separation(context, scene, preset_prefix, preset_count)
        else:
            return self._do_socket_placement(context, scene, preset_prefix, preset_count)
    
    def _do_bone_separation(self, context, scene, preset_prefix, preset_count):
        bone_index = scene.get(f"{preset_prefix}bone_index", 0)
        
        if bone_index >= preset_count:
            scene[f"{preset_prefix}phase"] = "sockets"
            scene[f"{preset_prefix}socket_index"] = 0
            self.report({'INFO'}, "Bone phase complete! Now place sockets using face selection.")
            return {'FINISHED'}
        
        bone_name = scene[f"{preset_prefix}bone_{bone_index}"]
        mesh_name = f"Mesh_{bone_name}"
        
        if context.mode != 'EDIT_MESH':
            self.report({'ERROR'}, "Must be in Edit Mode with faces selected")
            return {'CANCELLED'}
            
        mesh = context.active_object.data
        if not mesh.total_face_sel:
            self.report({'ERROR'}, "No faces selected")
            return {'CANCELLED'}
        
        obj = context.active_object
        
        bm = bmesh.from_edit_mesh(mesh)
        selected_faces = [f for f in bm.faces if f.select]
        
        center = Vector((0, 0, 0))
        for face in selected_faces:
            center += face.calc_center_median()
        center /= len(selected_faces)
        world_center = obj.matrix_world @ center
        
        bpy.ops.mesh.separate(type='SELECTED')
        bpy.ops.object.mode_set(mode='OBJECT')
        
        new_obj = context.selected_objects[-1]
        new_obj.name = mesh_name
        
        armature = None
        for armature_obj in bpy.data.objects:
            if armature_obj.type == 'ARMATURE':
                armature = armature_obj
                break
        
        if armature:
            context.view_layer.objects.active = armature
            bpy.ops.object.mode_set(mode='EDIT')
            
            final_bone_name = bone_name
            counter = 1
            while final_bone_name in armature.data.bones:
                final_bone_name = f"{bone_name}_{counter:02d}"
                counter += 1
            
            bone = armature.data.edit_bones.new(final_bone_name)
            bone.head = (world_center.x, world_center.y, world_center.z)
            bone.tail = (world_center.x, world_center.y + 0.2, world_center.z)
            bone.roll = 0.0
            
            if 'v_root' in armature.data.edit_bones:
                bone.parent = armature.data.edit_bones['v_root']
            
            bpy.ops.object.mode_set(mode='OBJECT')
            
            if self.auto_skinning:
                bpy.ops.object.select_all(action='DESELECT')
                new_obj.select_set(True)
                context.view_layer.objects.active = new_obj
                
                vertex_group = new_obj.vertex_groups.new(name=final_bone_name)
                if final_bone_name != "v_root":
                    v_root_group = new_obj.vertex_groups.new(name="v_root")
                
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                new_obj.vertex_groups.active = vertex_group
                bpy.ops.object.vertex_group_assign()
                bpy.ops.object.mode_set(mode='OBJECT')
                
                armature_mod = new_obj.modifiers.new(name="Armature", type='ARMATURE')
                armature_mod.object = armature
                armature_mod.vertex_group = final_bone_name
            
            parent_meshes = scene.get(f"{preset_prefix}parent_meshes", True)
            if parent_meshes:
                bpy.ops.object.select_all(action='DESELECT')
                new_obj.select_set(True)
                armature.select_set(True)
                context.view_layer.objects.active = armature
                bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)
        
        scene[f"{preset_prefix}bone_index"] = bone_index + 1
        
        remaining = preset_count - (bone_index + 1)
        if remaining > 0:
            next_bone = scene[f"{preset_prefix}bone_{bone_index + 1}"]
            self.report({'INFO'}, f"Created '{mesh_name}'. Next bone: {next_bone} ({remaining} remaining)")
        else:
            self.report({'INFO'}, f"Created '{mesh_name}'. Bone phase complete! Ready for socket phase.")
        
        return {'FINISHED'}
    
    def _do_socket_placement(self, context, scene, preset_prefix, preset_count):
        socket_index = scene.get(f"{preset_prefix}socket_index", 0)
        
        if socket_index >= preset_count:
            self.report({'INFO'}, "All sockets placed! Preset complete.")
            return {'FINISHED'}
        
        socket_name = scene[f"{preset_prefix}socket_{socket_index}"]
        
        if context.mode != 'EDIT_MESH':
            self.report({'ERROR'}, "Must be in Edit Mode with faces selected for socket placement")
            return {'CANCELLED'}
        
        obj = context.active_object
        mesh = obj.data
        
        if not mesh.total_face_sel:
            self.report({'ERROR'}, "No faces selected for socket placement")
            return {'CANCELLED'}
        
        bm = bmesh.from_edit_mesh(mesh)
        selected_faces = [f for f in bm.faces if f.select]
        
        center = Vector((0, 0, 0))
        for face in selected_faces:
            center += face.calc_center_median()
        center /= len(selected_faces)
        socket_location = obj.matrix_world @ center
        bpy.ops.object.mode_set(mode='OBJECT')
        
        final_socket_name = socket_name
        existing_sockets = [o for o in bpy.data.objects if final_socket_name in o.name]
        if existing_sockets:
            final_socket_name = f"{socket_name}_{len(existing_sockets) + 1:02d}"
        
        socket = bpy.data.objects.new(final_socket_name, None)
        socket.empty_display_type = 'ARROWS'
        socket.empty_display_size = 0.15
        socket.location = socket_location
        
        context.collection.objects.link(socket)
        socket["vehicle_part"] = "attachment_point"
        
        armature = None
        for armature_obj in bpy.data.objects:
            if armature_obj.type == 'ARMATURE':
                armature = armature_obj
                break
        
        if armature:
            socket.parent = armature
        
        scene[f"{preset_prefix}socket_index"] = socket_index + 1
        
        remaining = preset_count - (socket_index + 1)
        if remaining > 0:
            next_socket = scene[f"{preset_prefix}socket_{socket_index + 1}"]
            self.report({'INFO'}, f"Placed '{final_socket_name}'. Next socket: {next_socket} ({remaining} remaining)")
        else:
            self.report({'INFO'}, f"Placed '{final_socket_name}'. All presets complete!")
        
        return {'FINISHED'}


class ARVEHICLES_OT_skip_preset_item(bpy.types.Operator):
    bl_idname = "arvehicles.skip_preset_item"
    bl_label = "Skip"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Skip the current preset item and move to the next"
    
    def execute(self, context):
        scene = context.scene
        
        if "arvehicles_active_preset" not in scene:
            self.report({'ERROR'}, "No active preset")
            return {'CANCELLED'}
        
        preset_name = scene["arvehicles_active_preset"]
        preset_prefix = f"arvehicles_preset_{preset_name}_"
        
        count_key = f"{preset_prefix}count"
        if count_key not in scene:
            self.report({'ERROR'}, f"Preset '{preset_name}' data not found")
            return {'CANCELLED'}
        
        preset_count = scene[count_key]
        current_phase = scene.get(f"{preset_prefix}phase", "bones")
        
        if current_phase == "bones":
            bone_index = scene.get(f"{preset_prefix}bone_index", 0)
            if bone_index >= preset_count:
                scene[f"{preset_prefix}phase"] = "sockets"
                scene[f"{preset_prefix}socket_index"] = 0
                self.report({'INFO'}, "Bone phase complete! Now in socket phase.")
                return {'FINISHED'}
            
            # Get current bone name before incrementing
            skipped_bone = scene[f"{preset_prefix}bone_{bone_index}"]
            scene[f"{preset_prefix}bone_index"] = bone_index + 1
            
            # Calculate remaining AFTER incrementing
            new_bone_index = bone_index + 1
            remaining = preset_count - new_bone_index
            
            if remaining > 0:
                # Check if next bone exists before accessing it
                next_bone_key = f"{preset_prefix}bone_{new_bone_index}"
                if next_bone_key in scene:
                    next_bone = scene[next_bone_key]
                    self.report({'INFO'}, f"Skipped '{skipped_bone}'. Next: {next_bone} ({remaining} remaining)")
                else:
                    self.report({'INFO'}, f"Skipped '{skipped_bone}'. ({remaining} remaining)")
            else:
                scene[f"{preset_prefix}phase"] = "sockets"
                scene[f"{preset_prefix}socket_index"] = 0
                self.report({'INFO'}, f"Skipped '{skipped_bone}'. Bone phase complete! Now in socket phase.")
                
        else:
            socket_index = scene.get(f"{preset_prefix}socket_index", 0)
            if socket_index >= preset_count:
                self.report({'INFO'}, "All preset items complete!")
                return {'FINISHED'}
            
            # Get current socket name before incrementing
            skipped_socket = scene[f"{preset_prefix}socket_{socket_index}"]
            scene[f"{preset_prefix}socket_index"] = socket_index + 1
            
            # Calculate remaining AFTER incrementing
            new_socket_index = socket_index + 1
            remaining = preset_count - new_socket_index
            
            if remaining > 0:
                # Check if next socket exists before accessing it
                next_socket_key = f"{preset_prefix}socket_{new_socket_index}"
                if next_socket_key in scene:
                    next_socket = scene[next_socket_key]
                    self.report({'INFO'}, f"Skipped '{skipped_socket}'. Next: {next_socket} ({remaining} remaining)")
                else:
                    self.report({'INFO'}, f"Skipped '{skipped_socket}'. ({remaining} remaining)")
            else:
                self.report({'INFO'}, f"Skipped '{skipped_socket}'. All presets complete!")
        
        return {'FINISHED'}

class ARVEHICLES_OT_reset_preset(bpy.types.Operator):
    bl_idname = "arvehicles.reset_preset"
    bl_label = "Reset Preset"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Reset preset to bone phase"
    
    def execute(self, context):
        scene = context.scene
        
        if "arvehicles_active_preset" not in scene:
            self.report({'ERROR'}, "No active preset")
            return {'CANCELLED'}
        
        preset_name = scene["arvehicles_active_preset"]
        preset_prefix = f"arvehicles_preset_{preset_name}_"
        
        scene[f"{preset_prefix}bone_index"] = 0
        scene[f"{preset_prefix}socket_index"] = 0
        scene[f"{preset_prefix}phase"] = "bones"
        
        self.report({'INFO'}, f"Reset preset '{preset_name}' to bone phase")
        return {'FINISHED'}

class ARWEAPONS_OT_create_ucx_collision(bpy.types.Operator):
    bl_idname = "arweapons.create_ucx_collision"
    bl_label = "Create UCX Collision"
    bl_options = {'REGISTER', 'UNDO'}
    
    method: bpy.props.EnumProperty(
        name="Method",
        items=[
            ('UCX', "Convex", "UCX convex collision"),
            ('UCL', "Cylinder", "UCL cylinder collision"),
            ('UBX', "Box", "UBX box collision"),
            ('USP', "Sphere", "USP sphere collision"),
        ],
        default='UCX'
    )
    
    target_faces: bpy.props.IntProperty(
        name="Target Faces", 
        default=30, 
        min=12, 
        max=100,
        description="Target face count for UCX collisions"
    )
    
    def execute(self, context):
        if not context.selected_objects:
            self.report({'ERROR'}, "No objects selected")
            return {'CANCELLED'}
        
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not mesh_objects:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}
        
        collision_objects = []
        
        for idx, source_obj in enumerate(mesh_objects):
            collision_obj = self._create_collision(source_obj, idx, len(mesh_objects))
            if collision_obj:
                collision_objects.append(collision_obj)
        
        # Select all created collisions
        bpy.ops.object.select_all(action='DESELECT')
        for obj in collision_objects:
            obj.select_set(True)
        
        if collision_objects:
            context.view_layer.objects.active = collision_objects[0]
        
        self.report({'INFO'}, f"Created {len(collision_objects)} {self.method} collision(s)")
        return {'FINISHED'}
    
    def _create_collision(self, source_obj, idx, total_objects):
        """Create collision based on selected method"""
        # Generate proper name
        if total_objects == 1:
            name = f"{self.method}_weapon"
        else:
            name = f"{self.method}_weapon_part_{idx:02d}"
        
        if self.method == 'UCX':
            return self._create_ucx_collision(source_obj, name)
        else:
            return self._create_primitive_collision(source_obj, name)
    
    def _create_ucx_collision(self, source_obj, name):
        """Create UCX convex collision with proper cleanup"""
        bpy.ops.object.select_all(action='DESELECT')
        source_obj.select_set(True)
        bpy.context.view_layer.objects.active = source_obj
        
        # Duplicate source
        bpy.ops.object.duplicate()
        collision_obj = bpy.context.active_object
        collision_obj.name = name
        
        # Simplify before convex hull
        face_count = len(collision_obj.data.polygons)
        if face_count > self.target_faces * 2:
            # Heavy reduction for very complex meshes
            self._apply_decimation(collision_obj, max(0.1, (self.target_faces * 2) / face_count))
        
        # Create convex hull
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.convex_hull()
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Final optimization
        face_count = len(collision_obj.data.polygons)
        if face_count > self.target_faces:
            self._apply_decimation(collision_obj, max(0.7, self.target_faces / face_count))
        
        # Critical cleanup for non-planar faces
        self._fix_non_planar_faces(collision_obj)
        
        # Apply collision properties
        self._apply_collision_properties(collision_obj)
        
        return collision_obj
    
    def _create_primitive_collision(self, source_obj, name):
        """Create primitive collision (UCL, UBX, USP)"""
        # Get bounding box info
        bbox_center = sum((source_obj.matrix_world @ Vector(corner) for corner in source_obj.bound_box), Vector()) / 8
        dims = source_obj.dimensions
        
        bpy.ops.object.select_all(action='DESELECT')
        
        # Create appropriate primitive
        if self.method == 'UCL':
            # Cylinder - align to longest axis
            max_dim_idx = dims[:].index(max(dims))
            radius = max([dims[i] for i in range(3) if i != max_dim_idx]) / 2
            depth = dims[max_dim_idx]
            
            if max_dim_idx == 0:  # X longest
                bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, 
                                                  location=bbox_center, rotation=(0, 1.5708, 0))
            elif max_dim_idx == 1:  # Y longest
                bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, 
                                                  location=bbox_center, rotation=(1.5708, 0, 0))
            else:  # Z longest
                bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, location=bbox_center)
                
        elif self.method == 'UBX':
            # Box
            bpy.ops.mesh.primitive_cube_add(location=bbox_center)
            collision_obj = bpy.context.active_object
            collision_obj.scale = dims
            
        elif self.method == 'USP':
            # Sphere
            radius = max(dims) / 2
            bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=bbox_center)
        
        collision_obj = bpy.context.active_object
        collision_obj.name = name
        
        # Apply transforms
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        
        # Set origin to geometry center
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')
        
        # Apply collision properties
        self._apply_collision_properties(collision_obj)
        
        return collision_obj
    
    def _apply_decimation(self, obj, ratio):
        """Apply decimation modifier"""
        decimate = obj.modifiers.new(name="Decimate", type='DECIMATE')
        decimate.ratio = ratio
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=decimate.name)
    
    def _fix_non_planar_faces(self, obj):
        """Fix non-planar faces"""
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        
        # Select all
        bpy.ops.mesh.select_all(action='SELECT')
        
        # Remove tiny edges that cause non-planar faces
        bpy.ops.mesh.remove_doubles(threshold=0.0001)
        
        # Remove loose geometry
        bpy.ops.mesh.delete_loose()
        
        # Force all faces to be triangular
        bpy.ops.mesh.quads_convert_to_tris(quad_method='FIXED', ngon_method='BEAUTY')
        
        # Recalculate normals
        bpy.ops.mesh.normals_make_consistent(inside=False)
        
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Apply rotation and scale
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    
    def _apply_collision_properties(self, obj):
        """Apply proper collision properties"""
        # Create collision material
        if "Collision_Material" not in bpy.data.materials:
            mat = bpy.data.materials.new(name="Collision_Material")
            mat.diffuse_color = (0.2, 0.8, 0.2, 0.6)  # Green semi-transparent
            mat.use_backface_culling = False
        else:
            mat = bpy.data.materials["Collision_Material"]
        
        # Assign material
        obj.data.materials.clear()
        obj.data.materials.append(mat)
        
        # Set required properties
        obj["usage"] = "Weapon"
        obj["layer_preset"] = "Weapon"
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class ARWEAPONS_OT_create_firegeo_collision(bpy.types.Operator):
    bl_idname = "arweapons.create_firegeo_collision"
    bl_label = "Create FireGeo Collision"
    bl_options = {'REGISTER', 'UNDO'}
    
    method: bpy.props.EnumProperty(
        name="Method",
        items=[
            ('CONVEX', "Convex Hull", "Simplified convex hull"),
            ('DETAILED', "Detailed", "Preserves shape better"),
        ],
        default='DETAILED'
    )
    target_faces: bpy.props.IntProperty(name="Target Faces", default=150, min=50, max=1000)
    offset: bpy.props.FloatProperty(name="Offset", default=0.007, min=0.0, max=0.05)
    
    def execute(self, context):
        if not context.selected_objects:
            self.report({'ERROR'}, "No objects selected")
            return {'CANCELLED'}
        
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not mesh_objects:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}
        
        collision_objects = []
        total_faces = 0
        
        for idx, source_obj in enumerate(mesh_objects):
            bpy.ops.object.select_all(action='DESELECT')
            source_obj.select_set(True)
            context.view_layer.objects.active = source_obj
            
            bpy.ops.object.duplicate()
            dup_obj = context.selected_objects[0]
            
            if len(mesh_objects) == 1:
                dup_obj.name = "UTM_weapon"
            else:
                dup_obj.name = f"UTM_weapon_part_{idx}"
                
            collision_objects.append(dup_obj)
            
            part_target_faces = int(self.target_faces / len(mesh_objects))
            current_faces = len(dup_obj.data.polygons)
            
            if current_faces > part_target_faces:
                obj_dimensions = dup_obj.dimensions
                is_flat = min(obj_dimensions) < max(obj_dimensions) * 0.1
                
                if is_flat:
                    target_ratio = max(0.8, part_target_faces / current_faces)
                else:
                    target_ratio = part_target_faces / current_faces
                
                if target_ratio < 1.0:
                    decimate = dup_obj.modifiers.new(name="Decimate", type='DECIMATE')
                    decimate.ratio = max(0.1, target_ratio)
                    bpy.ops.object.modifier_apply(modifier=decimate.name)
            
            if self.offset > 0:
                solidify = dup_obj.modifiers.new(name="Solidify", type='SOLIDIFY')
                solidify.thickness = self.offset
                solidify.offset = 1.0
                bpy.ops.object.modifier_apply(modifier=solidify.name)
            
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            obj_dimensions = dup_obj.dimensions
            is_flat = min(obj_dimensions) < max(obj_dimensions) * 0.1
            merge_threshold = 0.0001 if is_flat else 0.001
            bpy.ops.mesh.remove_doubles(threshold=merge_threshold)
            bpy.ops.object.mode_set(mode='OBJECT')
            
            if "FireGeo_Material" not in bpy.data.materials:
                mat = bpy.data.materials.new(name="FireGeo_Material")
                mat.diffuse_color = (0.0, 0.8, 0.0, 0.5)
            else:
                mat = bpy.data.materials["FireGeo_Material"]
            
            dup_obj.data.materials.clear()
            dup_obj.data.materials.append(mat)
            dup_obj["layer_preset"] = "FireGeo"
            dup_obj["usage"] = "FireGeo"
            
            total_faces += len(dup_obj.data.polygons)
        
        # Select all collision objects
        bpy.ops.object.select_all(action='DESELECT')
        for obj in collision_objects:
            obj.select_set(True)
        
        if collision_objects:
            context.view_layer.objects.active = collision_objects[0]
        
        self.report({'INFO'}, f"Created FireGeo collision with {total_faces} total faces")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class ARWEAPONS_OT_center_weapon(bpy.types.Operator):
    bl_idname = "arweapons.center_weapon"
    bl_label = "Center Weapon"
    bl_options = {'REGISTER', 'UNDO'}
    
    align_barrel: bpy.props.BoolProperty(
        name="Align Barrel to Y+",
        description="Rotate weapon so barrel points along Y+ axis",
        default=True
    )
    
    adjust_height: bpy.props.BoolProperty(
        name="Set Standard Barrel Height",
        description="Position weapon at standard barrel height for Arma Reforger",
        default=True
    )
    
    def execute(self, context):
        if len(context.selected_objects) == 0:
            self.report({'ERROR'}, "Please select the weapon meshes")
            return {'CANCELLED'}
        
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not mesh_objects:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}
        
        # Calculate current weapon dimensions and center
        min_x, min_y, min_z = float('inf'), float('inf'), float('inf')
        max_x, max_y, max_z = float('-inf'), float('-inf'), float('-inf')
        
        for obj in mesh_objects:
            for vert in obj.data.vertices:
                world_co = obj.matrix_world @ vert.co
                min_x = min(min_x, world_co.x)
                min_y = min(min_y, world_co.y)
                min_z = min(min_z, world_co.z)
                max_x = max(max_x, world_co.x)
                max_y = max(max_y, world_co.y)
                max_z = max(max_z, world_co.z)
        
        # Calculate center of weapon
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        center_z = (min_z + max_z) / 2
        
        # Calculate the offset needed to center at origin
        offset_x = -center_x
        offset_y = -center_y
        offset_z = -center_z
        
        # Apply height adjustment if requested
        if self.adjust_height:
            offset_z = STANDARD_BARREL_HEIGHT - center_z
        
        # Move all mesh objects by the calculated offset
        for obj in mesh_objects:
            obj.location.x += offset_x
            obj.location.y += offset_y
            obj.location.z += offset_z
        
        # Apply barrel alignment if requested
        if self.align_barrel:
            # Create a temporary empty to use as a pivot for rotation
            pivot = bpy.data.objects.new("AlignPivot", None)
            context.collection.objects.link(pivot)
            pivot.location = (0, 0, STANDARD_BARREL_HEIGHT if self.adjust_height else 0)
            
            # Store original parents and parent all objects to the pivot
            original_parents = {}
            for obj in mesh_objects:
                original_parents[obj] = obj.parent
                obj.parent = pivot
            
            # Apply the transform
            bpy.ops.object.select_all(action='DESELECT')
            pivot.select_set(True)
            context.view_layer.objects.active = pivot
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=False)
            
            # Restore original parenting
            for obj in mesh_objects:
                obj.parent = original_parents[obj]
            
            # Remove the temporary pivot
            bpy.data.objects.remove(pivot)
        
        self.report({'INFO'}, "Weapon centered at origin" + 
                   (" and aligned to Y+ axis" if self.align_barrel else "") +
                   (" at standard barrel height" if self.adjust_height else ""))
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class ARWEAPONS_OT_scale_weapon(bpy.types.Operator):
    bl_idname = "arweapons.scale_weapon"
    bl_label = "Scale Weapon"
    bl_options = {'REGISTER', 'UNDO'}
    
    scale_method: bpy.props.EnumProperty(
        name="Scaling Method",
        items=[
            ('standard', "Arma Standard", "Scale to standard Arma Reforger weapon dimensions"),
            ('testing', "3m Testing Scale", "Scale to 3 meters for easy testing and adjustment"),
            ('custom', "Custom Dimensions", "Scale to custom real-world weapon dimensions"),
        ],
        default='testing'
    )
    
    custom_length: bpy.props.FloatProperty(
        name="Real Length (m)",
        default=0.9,
        min=0.1,
        max=3.0,
        precision=3
    )
    
    custom_height: bpy.props.FloatProperty(
        name="Real Height (m)",
        default=0.3,
        min=0.05,
        max=1.0,
        precision=3
    )
    
    custom_width: bpy.props.FloatProperty(
        name="Real Width (m)",
        default=0.1,
        min=0.01,
        max=0.5,
        precision=3
    )
    
    preserve_proportions: bpy.props.BoolProperty(
        name="Preserve Proportions",
        default=True
    )
    
    center_after_scale: bpy.props.BoolProperty(
        name="Center After Scaling",
        default=True
    )
    
    def execute(self, context):
        if len(context.selected_objects) == 0:
            self.report({'ERROR'}, "Please select the weapon meshes")
            return {'CANCELLED'}
        
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not mesh_objects:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}
        
        # Calculate current weapon dimensions and center
        min_x, min_y, min_z = float('inf'), float('inf'), float('inf')
        max_x, max_y, max_z = float('-inf'), float('-inf'), float('-inf')
        
        for obj in mesh_objects:
            for vert in obj.data.vertices:
                world_co = obj.matrix_world @ vert.co
                min_x = min(min_x, world_co.x)
                min_y = min(min_y, world_co.y)
                min_z = min(min_z, world_co.z)
                max_x = max(max_x, world_co.x)
                max_y = max(max_y, world_co.y)
                max_z = max(max_z, world_co.z)
        
        # Calculate center and dimensions
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        center_z = (min_z + max_z) / 2
        
        current_length = max_y - min_y
        current_height = max_z - min_z
        current_width = max_x - min_x
        
        # Calculate the overall size
        current_max_dimension = max(current_length, current_height, current_width)
        
        # Determine target dimensions
        if self.scale_method == 'standard':
            target_length = STANDARD_WEAPON_LENGTH
            target_height = STANDARD_WEAPON_HEIGHT
            target_width = STANDARD_WEAPON_WIDTH
        elif self.scale_method == 'testing':
            target_scale = 3.0 / current_max_dimension if current_max_dimension > 0 else 1.0
            scale_x = scale_y = scale_z = target_scale
        else:  # custom
            target_length = self.custom_length
            target_height = self.custom_height
            target_width = self.custom_width
        
        # Calculate scaling factors
        if self.scale_method != 'testing':
            length_scale = target_length / current_length if current_length > 0 else 1.0
            height_scale = target_height / current_height if current_height > 0 else 1.0
            width_scale = target_width / current_width if current_width > 0 else 1.0
            
            if self.preserve_proportions:
                scale_factor = min(length_scale, height_scale, width_scale)
                scale_x = scale_y = scale_z = scale_factor
            else:
                scale_x = width_scale
                scale_y = length_scale
                scale_z = height_scale
        
        # Create scaling pivot
        pivot = bpy.data.objects.new("ScalePivot", None)
        context.collection.objects.link(pivot)
        pivot.location = (center_x, center_y, center_z)
        
        # Store original parenting
        original_parents = {}
        for obj in mesh_objects:
            original_parents[obj] = obj.parent
            obj.parent = pivot
        
        # Apply scaling
        pivot.scale = (scale_x, scale_y, scale_z)
        
        bpy.ops.object.select_all(action='DESELECT')
        pivot.select_set(True)
        context.view_layer.objects.active = pivot
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        
        # Center if requested
        if self.center_after_scale:
            pivot.location = (0, 0, 0)
            bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
        
        # Restore original parenting
        for obj in mesh_objects:
            obj.parent = original_parents[obj]
        
        # Remove pivot
        bpy.data.objects.remove(pivot)
        
        # Report results
        if self.scale_method == 'testing':
            final_length = current_length * scale_x
            final_height = current_height * scale_x
            final_width = current_width * scale_x
            method_msg = f"3m testing scale (uniform scale of {scale_x:.4f})"
        elif self.preserve_proportions or self.scale_method == 'standard':
            final_length = current_length * scale_x
            final_height = current_height * scale_x
            final_width = current_width * scale_x
            method_msg = "standard Arma dimensions" if self.scale_method == 'standard' else "custom dimensions"
            method_msg += f" using uniform scale of {scale_x:.4f}"
        else:
            final_length = current_length * scale_y
            final_height = current_height * scale_z
            final_width = current_width * scale_x
            method_msg = f"custom dimensions using non-uniform scale of X:{scale_x:.4f}, Y:{scale_y:.4f}, Z:{scale_z:.4f}"
        
        center_msg = " and centered at origin" if self.center_after_scale else ""
        
        self.report({'INFO'}, f"Weapon scaled to {method_msg}{center_msg}. " + 
                             f"Final dimensions: {final_length:.3f}m × {final_width:.3f}m × {final_height:.3f}m")
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)
    
    def draw(self, context):
        layout = self.layout
        
        layout.prop(self, "scale_method")
        
        if self.scale_method == 'standard':
            box = layout.box()
            box.label(text="Standard Arma Reforger Dimensions:")
            row = box.row()
            row.label(text=f"Length: {STANDARD_WEAPON_LENGTH:.3f}m")
            row.label(text=f"Height: {STANDARD_WEAPON_HEIGHT:.3f}m")
            box.label(text=f"Width: {STANDARD_WEAPON_WIDTH:.3f}m")
        elif self.scale_method == 'testing':
            box = layout.box()
            box.label(text="3 Meter Testing Scale:")
            box.label(text="• Uniform scale based on longest dimension")
            box.label(text="• Easy to test and adjust in-game")
            box.label(text="• Good starting point for fine-tuning")
        else:  # custom
            layout.label(text="Custom Real-World Dimensions:")
            layout.prop(self, "custom_length")
            layout.prop(self, "custom_width")
            layout.prop(self, "custom_height")
        
        # Only show preserve proportions for non-testing modes
        if self.scale_method != 'testing':
            layout.prop(self, "preserve_proportions")
        
        layout.prop(self, "center_after_scale")

class ARWEAPONS_OT_create_socket(bpy.types.Operator):
    bl_idname = "arweapons.create_socket"
    bl_label = "Create Weapon Socket"
    bl_options = {'REGISTER', 'UNDO'}
    
    socket_type: bpy.props.EnumProperty(name="Socket Type", items=WEAPON_SOCKET_TYPES, default='slot_barrel_muzzle')
    custom_name: bpy.props.StringProperty(name="Custom Name", default="")
    parent_to_armature: bpy.props.BoolProperty(
        name="Parent to Armature", 
        default=True,
        description="Automatically parent socket to weapon armature"
    )
    
    def execute(self, context):
        socket_location = (0, 0, 0)  # Default to origin
        
        # Check if we're in edit mode with faces selected
        if context.mode == 'EDIT_MESH' and context.active_object and context.active_object.type == 'MESH':
            obj = context.active_object
            mesh = obj.data
            
            if mesh.total_face_sel > 0:
                # Calculate center of selected faces
                bm = bmesh.from_edit_mesh(mesh)
                selected_faces = [f for f in bm.faces if f.select]
                
                if selected_faces:
                    center = Vector((0, 0, 0))
                    for face in selected_faces:
                        center += face.calc_center_median()
                    center /= len(selected_faces)
                    
                    # Transform to world space
                    socket_location = obj.matrix_world @ center
                    
                    # Switch to object mode for socket creation
                    bpy.ops.object.mode_set(mode='OBJECT')
                else:
                    self.report({'WARNING'}, "No faces selected, using object center")
                    bbox_center = sum((obj.matrix_world @ Vector(corner) for corner in obj.bound_box), Vector()) / 8
                    socket_location = bbox_center
                    bpy.ops.object.mode_set(mode='OBJECT')
            else:
                self.report({'WARNING'}, "No faces selected, using object center")
                bbox_center = sum((obj.matrix_world @ Vector(corner) for corner in obj.bound_box), Vector()) / 8
                socket_location = bbox_center
                bpy.ops.object.mode_set(mode='OBJECT')
        
        # Fallback: If a mesh object is selected in object mode, use its center
        elif context.selected_objects:
            mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
            if mesh_objects:
                obj = mesh_objects[0]
                bbox_center = sum((obj.matrix_world @ Vector(corner) for corner in obj.bound_box), Vector()) / 8
                socket_location = bbox_center
        
        # Generate socket name
        if self.custom_name:
            socket_name = self.custom_name
        else:
            socket_name = f"Socket_{self.socket_type.replace('_', ' ').title().replace(' ', '_')}"
            existing_sockets = [o for o in bpy.data.objects if socket_name in o.name]
            if existing_sockets:
                socket_name = f"{socket_name}_{len(existing_sockets) + 1:02d}"
        
        # Create socket
        socket = bpy.data.objects.new(socket_name, None)
        socket.empty_display_type = 'ARROWS'
        socket.empty_display_size = 0.05
        socket.location = socket_location
        
        context.collection.objects.link(socket)
        
        socket["socket_type"] = self.socket_type
        socket["weapon_part"] = "attachment_point"
        
        # Parent to armature if requested
        if self.parent_to_armature:
            armature = None
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE':
                    armature = obj
                    break
            
            if armature:
                socket.parent = armature
                self.report({'INFO'}, f"Socket parented to armature '{armature.name}'")
            else:
                self.report({'WARNING'}, "No armature found to parent socket to")
        
        # Select the socket
        bpy.ops.object.select_all(action='DESELECT')
        socket.select_set(True)
        context.view_layer.objects.active = socket
        
        self.report({'INFO'}, f"Created weapon socket '{socket_name}' at selected faces")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class ARWEAPONS_OT_add_to_object(bpy.types.Operator):
    bl_idname = "arweapons.add_to_object"
    bl_label = "Add Bone/Socket to Object"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Add bone and/or socket to existing separated object"
    
    # Component type (unified for both bone and socket)
    component_type: bpy.props.EnumProperty(name="Component Type", items=WEAPON_COMPONENT_TYPES, default='trigger')
    custom_name: bpy.props.StringProperty(name="Custom Name", default="")
    
    # What to create
    add_socket: bpy.props.BoolProperty(name="Add Socket", description="Add a socket empty at the object's location", default=True)
    add_bone: bpy.props.BoolProperty(name="Add Bone", description="Add a bone at the object's location", default=False)
    auto_skinning: bpy.props.BoolProperty(name="Auto Skinning", description="Automatically setup skinning when adding bone", default=True)
    
    # Common options
    use_object_center: bpy.props.BoolProperty(name="Use Object Center", description="Place at object center instead of origin", default=True)
    
    def _get_socket_type_for_component(self, component_type):
        """Get the matching socket type for a component type"""
        component_to_socket = {
            'sight': 'slot_optics', 'light': 'slot_flashlight', 'trigger': 'custom',
            'bolt': 'custom', 'charging_handle': 'custom', 'mag_release': 'custom',
            'safety': 'custom', 'fire_mode': 'custom', 'hammer': 'custom',
            'striker': 'custom', 'slide': 'custom', 'barrel': 'barrel_muzzle',
            'buttstock': 'custom', 'ejection_port': 'custom', 'bipod': 'slot_underbarrel',
            'accessory': 'custom',
        }
        return component_to_socket.get(component_type, 'custom')
    
    def _get_bone_type_for_component(self, component_type):
        """Get the matching bone type for a component type"""
        component_to_bone = {
            'trigger': 'w_trigger', 'bolt': 'w_bolt', 'charging_handle': 'w_ch_handle',
            'mag_release': 'w_mag_release', 'safety': 'w_safety', 'fire_mode': 'w_fire_mode',
            'hammer': 'w_hammer', 'striker': 'w_striker', 'slide': 'w_slide',
            'barrel': 'w_barrel', 'buttstock': 'w_buttstock', 'ejection_port': 'w_ejection_port',
            'bipod': 'w_bipodleg', 'sight': 'w_sight',
        }
        return component_to_bone.get(component_type, 'custom')
    
    def _get_component_type_for_object(self, obj_name):
        """Guess component type from object name"""
        name_lower = obj_name.lower()
        if 'trigger' in name_lower:
            return 'trigger'
        elif 'bolt' in name_lower:
            return 'bolt'
        elif 'charging' in name_lower or 'ch_handle' in name_lower:
            return 'charging_handle'
        elif 'mag' in name_lower and 'release' in name_lower:
            return 'mag_release'
        elif 'safety' in name_lower:
            return 'safety'
        elif 'sight' in name_lower:
            return 'sight'
        elif 'light' in name_lower:
            return 'light'
        elif 'barrel' in name_lower:
            return 'barrel'
        return 'custom'
    
    def execute(self, context):
        if not context.selected_objects:
            self.report({'ERROR'}, "No objects selected")
            return {'CANCELLED'}
        
        target_obj = context.active_object
        if not target_obj:
            self.report({'ERROR'}, "No active object")
            return {'CANCELLED'}
        
        # Find existing armature
        armature = None
        for armature_obj in bpy.data.objects:
            if armature_obj.type == 'ARMATURE':
                armature = armature_obj
                break
        
        # Determine position (object center or origin)
        if self.use_object_center and target_obj.type == 'MESH':
            bbox_center = sum((target_obj.matrix_world @ Vector(corner) for corner in target_obj.bound_box), Vector()) / 8
            location = bbox_center
        else:
            location = target_obj.matrix_world.translation
        
        bone_name = None
        socket = None
        
        # Get the matching socket and bone types based on component type
        socket_type = self._get_socket_type_for_component(self.component_type)
        bone_type = self._get_bone_type_for_component(self.component_type)
        
        # Create bone if requested
        if self.add_bone:
            if not armature:
                self.report({'ERROR'}, "No armature found. Create an armature first.")
                return {'CANCELLED'}
            
            # Generate bone name
            if self.component_type == 'custom':
                if self.custom_name:
                    bone_name = f"w_{self.custom_name.lower().replace(' ', '_')}"
                else:
                    bone_name = f"w_{target_obj.name.lower().replace(' ', '_')}"
            else:
                bone_name = bone_type
            
            # Check for duplicate bone names and increment
            original_bone_name = bone_name
            counter = 1
            while bone_name in armature.data.bones:
                bone_name = f"{original_bone_name}_{counter:02d}"
                counter += 1
            
            # Create the bone
            context.view_layer.objects.active = armature
            bpy.ops.object.mode_set(mode='EDIT')
            
            bone = armature.data.edit_bones.new(bone_name)
            bone.head = (location.x, location.y, location.z)
            bone.tail = (location.x, location.y + 0.087, location.z)
            bone.roll = 0.0
            
            # Parent to w_root if it exists
            if 'w_root' in armature.data.edit_bones:
                bone.parent = armature.data.edit_bones['w_root']
            
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # Set up skinning if requested
            if self.auto_skinning:
                bpy.ops.object.select_all(action='DESELECT')
                target_obj.select_set(True)
                context.view_layer.objects.active = target_obj
                
                # Create vertex group for the bone
                if bone_name not in target_obj.vertex_groups:
                    vertex_group = target_obj.vertex_groups.new(name=bone_name)
                    
                    # Create w_root group if it doesn't exist
                    if bone_name != "w_root" and "w_root" not in target_obj.vertex_groups:
                        w_root_group = target_obj.vertex_groups.new(name="w_root")
                    
                    # Assign all vertices to the specific bone group
                    bpy.ops.object.mode_set(mode='EDIT')
                    bpy.ops.mesh.select_all(action='SELECT')
                    target_obj.vertex_groups.active = vertex_group
                    bpy.ops.object.vertex_group_assign()
                    bpy.ops.object.mode_set(mode='OBJECT')
                    
                    # Create or update armature modifier
                    armature_mod = None
                    for mod in target_obj.modifiers:
                        if mod.type == 'ARMATURE':
                            armature_mod = mod
                            break
                    
                    if not armature_mod:
                        armature_mod = target_obj.modifiers.new(name="Armature", type='ARMATURE')
                    
                    # Always set/update the armature object reference
                    armature_mod.object = armature
                    armature_mod.vertex_group = bone_name
        
        # Parent the object to the armature if it exists and isn't already parented
        if armature and target_obj.parent != armature:
            bpy.ops.object.select_all(action='DESELECT')
            target_obj.select_set(True)
            armature.select_set(True)
            context.view_layer.objects.active = armature
            bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)
        
        # Create socket if requested
        if self.add_socket:
            # Generate socket name
            if self.component_type == 'custom':
                if self.custom_name:
                    socket_name = f"Socket_{self.custom_name.replace(' ', '_').title()}"
                else:
                    socket_name = f"Socket_{target_obj.name.replace(' ', '_').title()}"
            else:
                socket_name = f"Socket_{socket_type.replace('_', ' ').title().replace(' ', '_')}"
                existing_sockets = [o for o in bpy.data.objects if socket_name in o.name]
                if existing_sockets:
                    socket_name = f"{socket_name}_{len(existing_sockets) + 1:02d}"
            
            # Create socket
            socket = bpy.data.objects.new(socket_name, None)
            socket.empty_display_type = 'ARROWS'
            socket.empty_display_size = 0.05
            socket.location = location
            
            context.collection.objects.link(socket)
            
            socket["socket_type"] = socket_type
            socket["attached_part"] = target_obj.name
            socket["weapon_part"] = "attachment_point"
            
            # Parent socket to armature if it exists
            if armature:
                socket.parent = armature
        
        # Select the target object again
        bpy.ops.object.select_all(action='DESELECT')
        target_obj.select_set(True)
        context.view_layer.objects.active = target_obj
        
        # Build report message
        report_msg = f"Added to object '{target_obj.name}'"
        if self.add_socket and self.add_bone:
            report_msg += f" with socket and bone '{bone_name}'"
        elif self.add_socket:
            report_msg += f" with socket"
        elif self.add_bone:
            report_msg += f" with bone '{bone_name}'"
        
        if self.add_bone and self.auto_skinning:
            report_msg += " and automatic skinning"
        
        self.report({'INFO'}, report_msg)
        return {'FINISHED'}
    
    def invoke(self, context, event):
        # Auto-guess component type from selected object name
        if context.active_object:
            guessed_component_type = self._get_component_type_for_object(context.active_object.name)
            if guessed_component_type != 'custom':
                self.component_type = guessed_component_type
        
        return context.window_manager.invoke_props_dialog(self, width=350)
    
    def draw(self, context):
        layout = self.layout
        
        layout.prop(self, "component_type")
        layout.prop(self, "custom_name")
        
        layout.separator()
        layout.prop(self, "use_object_center")
        
        layout.separator()
        layout.prop(self, "add_socket")
        
        layout.separator()
        layout.prop(self, "add_bone")
        if self.add_bone:
            layout.prop(self, "auto_skinning")

class ARWEAPONS_OT_separate_components(bpy.types.Operator):
    bl_idname = "arweapons.separate_components"
    bl_label = "Separate Weapon Components"
    bl_options = {'REGISTER', 'UNDO'}
    
    component_type: bpy.props.EnumProperty(name="Component Type", items=WEAPON_COMPONENT_TYPES, default='trigger')
    custom_name: bpy.props.StringProperty(name="Custom Name", default="")
    
    add_socket: bpy.props.BoolProperty(name="Add Socket", description="Add a socket empty at the component's location", default=True)
    custom_socket_name: bpy.props.StringProperty(name="Custom Socket Name", default="")
    set_origin_to_socket: bpy.props.BoolProperty(name="Set Origin to Socket", default=True)
    
    add_bone: bpy.props.BoolProperty(name="Add Bone", description="Add a bone at the component's location", default=False)
    custom_bone_name: bpy.props.StringProperty(name="Custom Bone Name", default="")
    auto_skinning: bpy.props.BoolProperty(name="Auto Skinning", description="Automatically setup skinning when adding bone", default=True)
    
    # Parenting options
    parent_mesh_to_armature: bpy.props.BoolProperty(name="Parent Mesh to Armature", description="Parent separated mesh to armature", default=True)
    parent_socket_to_armature: bpy.props.BoolProperty(name="Parent Socket to Armature", description="Parent socket to armature", default=True)
    
    def _get_socket_type_for_component(self, component_type):
        """Get the matching socket type for a component type"""
        component_to_socket = {
            'sight': 'slot_optics', 'light': 'slot_flashlight', 'trigger': 'custom',
            'bolt': 'custom', 'charging_handle': 'custom', 'mag_release': 'custom',
            'safety': 'custom', 'fire_mode': 'custom', 'hammer': 'custom',
            'striker': 'custom', 'slide': 'custom', 'barrel': 'barrel_muzzle',
            'buttstock': 'custom', 'ejection_port': 'custom', 'bipod': 'slot_underbarrel',
            'accessory': 'custom',
        }
        return component_to_socket.get(component_type, 'custom')
    
    def _get_bone_type_for_component(self, component_type):
        """Get the matching bone type for a component type"""
        component_to_bone = {
            'trigger': 'w_trigger', 'bolt': 'w_bolt', 'charging_handle': 'w_ch_handle',
            'mag_release': 'w_mag_release', 'safety': 'w_safety', 'fire_mode': 'w_fire_mode',
            'hammer': 'w_hammer', 'striker': 'w_striker', 'slide': 'w_slide',
            'barrel': 'w_barrel', 'buttstock': 'w_buttstock', 'ejection_port': 'w_ejection_port',
            'bipod': 'w_bipodleg', 'sight': 'w_sight',
        }
        return component_to_bone.get(component_type, 'custom')
    
    def execute(self, context):
        if context.mode != 'EDIT_MESH':
            self.report({'ERROR'}, "Must be in Edit Mode with faces selected")
            return {'CANCELLED'}
            
        mesh = context.active_object.data
        if not mesh.total_face_sel:
            self.report({'ERROR'}, "No faces selected")
            return {'CANCELLED'}
        
        obj = context.active_object
        
        # Calculate the center of the selected faces
        bm = bmesh.from_edit_mesh(mesh)
        selected_faces = [f for f in bm.faces if f.select]
        
        if not selected_faces:
            self.report({'ERROR'}, "No faces selected")
            return {'CANCELLED'}
        
        center = Vector((0, 0, 0))
        for face in selected_faces:
            center += face.calc_center_median()
        center /= len(selected_faces)
        
        # Transform to world space
        world_center = obj.matrix_world @ center
        
        prefix_map = {
            'sight': "sight_", 'light': "light_", 'trigger': "trigger_", 'bolt': "bolt_",
            'charging_handle': "ch_handle_", 'mag_release': "mag_release_", 'safety': "safety_",
            'fire_mode': "fire_mode_", 'hammer': "hammer_", 'striker': "striker_",
            'slide': "slide_", 'barrel': "barrel_", 'buttstock': "buttstock_",
            'ejection_port': "ejection_port_", 'bipod': "bipod_", 'accessory': "acc_",
        }
        
        prefix = prefix_map.get(self.component_type, "component_")
        new_name = self.custom_name if self.custom_name else f"{prefix}{obj.name}"
        
        # Separate the selected faces
        bpy.ops.mesh.separate(type='SELECTED')
        bpy.ops.object.mode_set(mode='OBJECT')
        
        new_obj = context.selected_objects[-1]
        new_obj.name = new_name
        new_obj["component_type"] = self.component_type

        # Find existing armature - check for any armature first
        armature = None
        for armature_obj in bpy.data.objects:
            if armature_obj.type == 'ARMATURE':
                armature = armature_obj
                break
        
        socket = None
        bone = None
        bone_name = None
        
        # Get the matching socket and bone types based on component type
        socket_type = self._get_socket_type_for_component(self.component_type)
        bone_type = self._get_bone_type_for_component(self.component_type)
        
        # If component type is custom, use the custom name for socket and bone naming
        if self.component_type == 'custom' and self.custom_name:
            socket_type = 'custom'
            bone_type = 'custom'
        
        # Create a bone if requested
        if self.add_bone:
            if not armature:
                # Create armature if it doesn't exist
                armature_data = bpy.data.armatures.new("Armature")
                armature = bpy.data.objects.new("Armature", armature_data)
                context.collection.objects.link(armature)
                
                # Create w_root bone first
                context.view_layer.objects.active = armature
                bpy.ops.object.mode_set(mode='EDIT')
                root_bone = armature.data.edit_bones.new('w_root')
                root_bone.head = (0, 0, 0)
                root_bone.tail = (0, 0.087, 0)
                root_bone.roll = 0.0
                bpy.ops.object.mode_set(mode='OBJECT')
            
            # Generate bone name
            if self.custom_bone_name:
                bone_name = self.custom_bone_name
                if not bone_name.startswith('w_'):
                    bone_name = 'w_' + bone_name
            elif bone_type == 'custom':
                if self.custom_name:
                    bone_name = f"w_{self.custom_name.lower().replace(' ', '_')}"
                else:
                    bone_name = f"w_{new_name.lower().replace(' ', '_')}"
            else:
                bone_name = bone_type
                original_bone_name = bone_name
                counter = 1
                while bone_name in armature.data.bones:
                    bone_name = f"{original_bone_name}_{counter:02d}"
                    counter += 1
            
            # Make armature active and enter edit mode
            context.view_layer.objects.active = armature
            bpy.ops.object.mode_set(mode='EDIT')
            
            # Create the bone
            bone = armature.data.edit_bones.new(bone_name)
            bone.head = (world_center.x, world_center.y, world_center.z)
            bone.tail = (world_center.x, world_center.y + 0.087, world_center.z)
            bone.roll = 0.0
            
            # Parent to w_root if it exists
            if 'w_root' in armature.data.edit_bones:
                bone.parent = armature.data.edit_bones['w_root']
            
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # Set up skinning for the separated component (if enabled)
            if self.auto_skinning:
                bpy.ops.object.select_all(action='DESELECT')
                new_obj.select_set(True)
                context.view_layer.objects.active = new_obj
                
                # Create vertex group for the bone
                vertex_group = new_obj.vertex_groups.new(name=bone_name)
                
                # Also create w_root group for the main body (standard weapon rigging)
                if bone_name != "w_root":
                    w_root_group = new_obj.vertex_groups.new(name="w_root")
                
                # Assign all vertices to the specific bone group
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                new_obj.vertex_groups.active = vertex_group
                bpy.ops.object.vertex_group_assign()
                bpy.ops.object.mode_set(mode='OBJECT')
                
                # Create armature modifier
                armature_mod = new_obj.modifiers.new(name="Armature", type='ARMATURE')
                armature_mod.object = armature
                armature_mod.vertex_group = bone_name
        
        # Parent the separated component to the armature if option is enabled
        if armature and self.parent_mesh_to_armature:
            bpy.ops.object.select_all(action='DESELECT')
            new_obj.select_set(True)
            armature.select_set(True)
            context.view_layer.objects.active = armature
            bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)
        
        # Create a socket empty if requested
        if self.add_socket:
            if self.custom_socket_name:
                socket_name = self.custom_socket_name
            elif socket_type == 'custom' and self.custom_name:
                socket_name = f"Socket_{self.custom_name.replace(' ', '_').title()}"
            else:
                socket_name = f"Socket_{socket_type.replace('_', ' ').title().replace(' ', '_')}"
                existing_sockets = [o for o in bpy.data.objects if socket_name in o.name]
                if existing_sockets:
                    socket_name = f"{socket_name}_{len(existing_sockets) + 1:02d}"
            
            socket = bpy.data.objects.new(socket_name, None)
            socket.empty_display_type = 'ARROWS'
            socket.empty_display_size = 0.05
            socket.location = world_center
            
            context.collection.objects.link(socket)
            
            socket["socket_type"] = socket_type
            socket["attached_part"] = new_obj.name
            socket["weapon_part"] = "attachment_point"
            
            # Parent socket to armature if option is enabled
            if armature and self.parent_socket_to_armature:
                socket.parent = armature
        
        # Set origin to socket position if requested
        if self.add_socket and self.set_origin_to_socket:
            bpy.ops.object.select_all(action='DESELECT')
            new_obj.select_set(True)
            context.view_layer.objects.active = new_obj
            
            cursor_location = context.scene.cursor.location.copy()
            context.scene.cursor.location = socket.location
            bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
            context.scene.cursor.location = cursor_location
        
        # Select only the new object
        bpy.ops.object.select_all(action='DESELECT')
        new_obj.select_set(True)
        context.view_layer.objects.active = new_obj
        
        # Build report message
        report_msg = f"Separated component '{new_name}'"
        if self.parent_mesh_to_armature and armature:
            report_msg += " and parented to armature"
        if self.add_socket:
            report_msg += f" with socket (type: {socket_type})"
        if self.add_bone:
            report_msg += f" with bone '{bone_name}' and automatic skinning"
        if self.set_origin_to_socket and self.add_socket:
            report_msg += ", origin set to socket"
            
        self.report({'INFO'}, report_msg)
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=350)
    
    def draw(self, context):
        layout = self.layout
        
        layout.prop(self, "component_type")
        layout.prop(self, "custom_name")
        
        layout.separator()
        layout.prop(self, "add_socket")
        if self.add_socket:
            layout.prop(self, "custom_socket_name")
            layout.prop(self, "set_origin_to_socket")
            layout.prop(self, "parent_socket_to_armature")
        
        layout.separator()
        layout.prop(self, "add_bone")
        if self.add_bone:
            layout.prop(self, "custom_bone_name")
            layout.prop(self, "auto_skinning")
        
        layout.separator()
        layout.label(text="Parenting Options:")
        layout.prop(self, "parent_mesh_to_armature")


class ARWEAPONS_OT_create_armature(bpy.types.Operator):
    bl_idname = "arweapons.create_armature"
    bl_label = "Create Weapon Armature"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Create a minimal weapon armature with w_root bone following Arma Reforger standards"
    
    def execute(self, context):
        # Check if armature already exists
        existing_armature = None
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE' and obj.name in ["Armature", "WeaponArmature"]:
                existing_armature = obj
                break
        
        if existing_armature:
            self.report({'INFO'}, f"Weapon armature '{existing_armature.name}' already exists")
            context.view_layer.objects.active = existing_armature
            return {'FINISHED'}
        
        # Create armature - keep name as "Armature" per Arma standards
        armature_data = bpy.data.armatures.new("Armature")
        armature_obj = bpy.data.objects.new("Armature", armature_data)
        context.collection.objects.link(armature_obj)
        
        # Set armature at world origin with proper scale (required by Arma)
        armature_obj.location = (0, 0, 0)
        armature_obj.rotation_euler = (0, 0, 0)
        armature_obj.scale = (1.0, 1.0, 1.0)
        
        context.view_layer.objects.active = armature_obj
        bpy.ops.object.mode_set(mode='EDIT')
        
        # Create w_root bone - the essential root bone for all weapons
        root_bone = armature_data.edit_bones.new('w_root')
        root_bone.head = (0, 0, 0)  # At world origin as specified
        root_bone.tail = (0, 0.087, 0)  # Y+ orientation as recommended
        root_bone.roll = 0.0
        
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Set display properties for easier bone visibility
        armature_data.display_type = 'OCTAHEDRAL'
        armature_data.show_names = True
        armature_obj.show_in_front = True
        
        self.report({'INFO'}, "Created minimal weapon armature with w_root bone")
        return {'FINISHED'}

class ARWEAPONS_OT_create_bone(bpy.types.Operator):
    bl_idname = "arweapons.create_bone"
    bl_label = "Add Bone"
    bl_options = {'REGISTER', 'UNDO'}
    
    bone_type: bpy.props.EnumProperty(name="Bone Type", items=WEAPON_BONE_TYPES, default='w_trigger')
    custom_bone_name: bpy.props.StringProperty(name="Bone Name", default="custom")
    
    def execute(self, context):
        armature = None
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                armature = obj
                break
        
        if not armature:
            self.report({'ERROR'}, "No weapon armature found")
            return {'CANCELLED'}
        
        context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='EDIT')
        
        bone_length = 0.087
        
        if self.bone_type == 'custom':
            bone_name = self.custom_bone_name
            if not bone_name.startswith('w_'):
                bone_name = 'w_' + bone_name
        else:
            bone_name = self.bone_type
        
        if bone_name in armature.data.edit_bones:
            if bone_name == 'w_root':
                self.report({'INFO'}, "w_root already exists")
                bpy.ops.object.mode_set(mode='OBJECT')
                return {'FINISHED'}
            else:
                base_name = bone_name
                counter = 1
                while bone_name in armature.data.edit_bones:
                    bone_name = f"{base_name}_{counter:02d}"
                    counter += 1
        
        parent_bone = None
        if self.bone_type != 'w_root' and 'w_root' in armature.data.edit_bones:
            parent_bone = armature.data.edit_bones['w_root']
        
        bone = armature.data.edit_bones.new(bone_name)
        bone.roll = 0.0
        if parent_bone:
            bone.parent = parent_bone
        
        # Position bones based on weapon anatomy
        if self.bone_type == 'w_root':
            bone.head = (0, 0, 0)
            bone.tail = (0, bone_length, 0)
        elif self.bone_type == 'w_trigger':
            bone.head = (-0.005, 0.019, 0.012)
            bone.tail = (-0.005, 0.019 + bone_length, 0.012)
        elif self.bone_type == 'w_fire_mode':
            bone.head = (-0.001, -0.014, 0.025)
            bone.tail = (-0.001, -0.014 + bone_length, 0.025)
        elif self.bone_type == 'w_ch_handle':
            bone.head = (-0.001, -0.086, 0.083)
            bone.tail = (-0.001, -0.086 + bone_length, 0.083)
        elif self.bone_type == 'w_bolt':
            bone.head = (0, -0.166, 0.065)
            bone.tail = (0, -0.166 + bone_length, 0.065)
        elif self.bone_type == 'w_mag_release':
            bone.head = (0.015, 0.019, 0.012)
            bone.tail = (0.015, 0.019 + bone_length, 0.012)
        elif self.bone_type == 'w_safety':
            bone.head = (0.01, -0.01, 0.02)
            bone.tail = (0.01, -0.01 + bone_length, 0.02)
        elif self.bone_type == 'w_buttstock':
            bone.head = (0, -0.3, 0.05)
            bone.tail = (0, -0.3 + bone_length, 0.05)
        elif self.bone_type == 'w_slide':
            bone.head = (0, -0.08, 0.065)
            bone.tail = (0, -0.08 + bone_length, 0.065)
        elif self.bone_type == 'w_hammer':
            bone.head = (0, -0.04, 0.04)
            bone.tail = (0, -0.04 + bone_length, 0.04)
        elif self.bone_type == 'w_striker':
            bone.head = (0, -0.05, 0.065)
            bone.tail = (0, -0.05 + bone_length, 0.065)
        elif self.bone_type == 'w_rear_sight':
            bone.head = (0, 0.15, 0.09)
            bone.tail = (0, 0.15 + bone_length, 0.09)
        elif self.bone_type == 'w_front_sight':
            bone.head = (0, 0.3, 0.09)
            bone.tail = (0, 0.3 + bone_length, 0.09)
        elif self.bone_type == 'w_barrel':
            bone.head = (0, 0.1, 0.065)
            bone.tail = (0, 0.1 + bone_length, 0.065)
        elif self.bone_type == 'w_bipodleg':
            bone.head = (0, 0.2, -0.05)
            bone.tail = (0, 0.2 + bone_length, -0.05)
        elif self.bone_type == 'w_bipodleg_left':
            bone.head = (-0.03, 0.2, -0.05)
            bone.tail = (-0.03, 0.2 + bone_length, -0.05)
        elif self.bone_type == 'w_bipodleg_right':
            bone.head = (0.03, 0.2, -0.05)
            bone.tail = (0.03, 0.2 + bone_length, -0.05)
        elif self.bone_type == 'w_sight':
            bone.head = (0, 0.25, 0.095)
            bone.tail = (0, 0.25 + bone_length, 0.095)
        elif self.bone_type == 'w_sight_slider':
            bone.head = (0, 0.18, 0.085)
            bone.tail = (0, 0.18 + bone_length, 0.085)
        else:
            bone.head = (0, 0, 0.05)
            bone.tail = (0, bone_length, 0.05)
        
        bpy.ops.object.mode_set(mode='OBJECT')
        self.report({'INFO'}, f"Created {bone_name} bone")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        if self.bone_type == 'custom':
            return context.window_manager.invoke_props_dialog(self)
        else:
            return self.execute(context)

class ARWEAPONS_OT_setup_skinning(bpy.types.Operator):
    bl_idname = "arweapons.setup_skinning"
    bl_label = "Setup Weapon Skinning"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        armature = None
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                armature = obj
                break
        
        if not armature:
            self.report({'ERROR'}, "No weapon armature found")
            return {'CANCELLED'}
        
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not mesh_objects:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}
        
        skinned_objects = 0
        
        for obj in mesh_objects:
            armature_mod = None
            for mod in obj.modifiers:
                if mod.type == 'ARMATURE':
                    armature_mod = mod
                    break
            
            if not armature_mod:
                armature_mod = obj.modifiers.new(name="Armature", type='ARMATURE')
                armature_mod.object = armature
            
            if "w_root" not in obj.vertex_groups:
                w_root_group = obj.vertex_groups.new(name="w_root")
                
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                
                obj.vertex_groups.active = w_root_group
                bpy.ops.object.vertex_group_assign()
                
                bpy.ops.object.mode_set(mode='OBJECT')
            
            skinned_objects += 1
        
        self.report({'INFO'}, f"Setup skinning for {skinned_objects} objects")
        return {'FINISHED'}

class ARWEAPONS_OT_parent_to_armature(bpy.types.Operator):
    bl_idname = "arweapons.parent_to_armature"
    bl_label = "Parent to Armature"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        armature = None
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                armature = obj
                break
        
        if not armature:
            self.report({'ERROR'}, "No weapon armature found")
            return {'CANCELLED'}
        
        selected_objects = [obj for obj in context.selected_objects if obj != armature]
        
        if not selected_objects:
            self.report({'ERROR'}, "No objects selected for parenting")
            return {'CANCELLED'}
        
        bpy.ops.object.select_all(action='DESELECT')
        for obj in selected_objects:
            obj.select_set(True)
        armature.select_set(True)
        context.view_layer.objects.active = armature
        bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)
        
        self.report({'INFO'}, f"Parented {len(selected_objects)} objects to armature")
        return {'FINISHED'}

class ARWEAPONS_OT_create_empties(bpy.types.Operator):
    bl_idname = "arweapons.create_empties"
    bl_label = "Create All Weapon Points"
    bl_options = {'REGISTER', 'UNDO'}
    
    create_slots: bpy.props.BoolProperty(
        name="Create Attachment Slots",
        default=True
    )
    
    create_snap_points: bpy.props.BoolProperty(
        name="Create Hand IK Points",
        default=True
    )
    
    create_barrel_points: bpy.props.BoolProperty(
        name="Create Barrel Points",
        default=True
    )
    
    create_eye_point: bpy.props.BoolProperty(
        name="Create Eye Point",
        default=True
    )
    
    def execute(self, context):
        collection_name = "Weapon_Components"
        if collection_name in bpy.data.collections:
            weapon_collection = bpy.data.collections[collection_name]
        else:
            weapon_collection = bpy.data.collections.new(collection_name)
            context.scene.collection.children.link(weapon_collection)
        
        created_empties = []
        
        # Default empty locations
        empty_positions = {
            # Attachment slots
            "slot_magazine": (0, 0, -0.06),
            "slot_optics": (0, 0.1, 0.09),
            "slot_barrel_muzzle": (0, 0.35, 0.065),
            "slot_underbarrel": (0, 0.2, -0.03),
            "slot_bayonet": (0, 0.32, 0.065),
            "slot_flashlight": (0.02, 0.25, 0.05),
            
            # Hand IK points
            "snap_hand_right": (0.03, 0, 0.02),
            "snap_hand_left": (-0.03, 0.15, 0.02),
            
            # Simulation points
            "eye": (0, 0.1, 0.085),
            "barrel_chamber": (0, -0.1, 0.065),
            "barrel_muzzle": (0, 0.35, 0.065),
        }
        
        if self.create_slots:
            slot_names = ["slot_magazine", "slot_optics", "slot_barrel_muzzle", 
                         "slot_underbarrel", "slot_bayonet", "slot_flashlight"]
            for name in slot_names:
                if name not in bpy.data.objects:
                    empty = self._create_empty(name, empty_positions[name], weapon_collection, 'PLAIN_AXES', 0.03)
                    created_empties.append(name)
        
        if self.create_snap_points:
            snap_names = ["snap_hand_right", "snap_hand_left"]
            for name in snap_names:
                if name not in bpy.data.objects:
                    empty = self._create_empty(name, empty_positions[name], weapon_collection, 'PLAIN_AXES', 0.04)
                    created_empties.append(name)
        
        if self.create_barrel_points:
            barrel_names = ["barrel_chamber", "barrel_muzzle"]
            for name in barrel_names:
                if name not in bpy.data.objects:
                    empty = self._create_empty(name, empty_positions[name], weapon_collection, 'SPHERE', 0.01)
                    created_empties.append(name)
        
        if self.create_eye_point:
            if "eye" not in bpy.data.objects:
                empty = self._create_empty("eye", empty_positions["eye"], weapon_collection, 'CUBE', 0.01)
                created_empties.append("eye")
        
        self.report({'INFO'}, f"Created {len(created_empties)} empty objects")
        return {'FINISHED'}
    
    def _create_empty(self, name, location, collection, display_type, size):
        empty = bpy.data.objects.new(name, None)
        empty.empty_display_type = display_type
        empty.empty_display_size = size
        empty.location = location
        collection.objects.link(empty)
        return empty
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class ARWEAPONS_OT_create_vertex_group(bpy.types.Operator):
    bl_idname = "arweapons.create_vertex_group"
    bl_label = "Assign Selection to Bone"
    bl_options = {'REGISTER', 'UNDO'}
    
    def get_bone_items(self, context):
        items = []
        armature = None
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                armature = obj
                break
        
        if armature:
            for bone in armature.data.bones:
                items.append((bone.name, bone.name, f"Assign to {bone.name} bone"))
        
        if not items:
            items.append(('NO_ARMATURE', "No Weapon Armature Found", "No weapon armature found"))
            
        return items
    
    bone_name: bpy.props.EnumProperty(name="Bone Name", items=get_bone_items)
    
    def execute(self, context):
        obj = context.active_object
        
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Active object must be a mesh")
            return {'CANCELLED'}
        
        if bpy.context.mode != 'EDIT_MESH':
            self.report({'ERROR'}, "Must be in Edit mode with faces selected")
            return {'CANCELLED'}
        
        if self.bone_name == 'NO_ARMATURE':
            self.report({'ERROR'}, "No weapon armature found")
            return {'CANCELLED'}
        
        if self.bone_name in obj.vertex_groups:
            vgroup = obj.vertex_groups[self.bone_name]
        else:
            vgroup = obj.vertex_groups.new(name=self.bone_name)
        
        if "w_root" in obj.vertex_groups and self.bone_name != "w_root":
            w_root_group = obj.vertex_groups["w_root"]
            obj.vertex_groups.active = w_root_group
            bpy.ops.object.vertex_group_remove_from()
        
        obj.vertex_groups.active = vgroup
        bpy.ops.object.vertex_group_assign()
        
        self.report({'INFO'}, f"Assigned selection to {self.bone_name} vertex group")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class ARWEAPONS_OT_cleanup_mesh(bpy.types.Operator):
    bl_idname = "arweapons.cleanup_mesh"
    bl_label = "Cleanup Mesh"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Fix common mesh issues: duplicates, holes, non-manifold geometry, etc."
    
    merge_threshold: bpy.props.FloatProperty(
        name="Merge Distance", 
        default=0.001, 
        min=0.0001, 
        max=0.01,
        description="Distance threshold for merging duplicate vertices"
    )
    
    dissolve_angle: bpy.props.FloatProperty(
        name="Dissolve Angle", 
        default=5.0, 
        min=0.1, 
        max=15.0,
        description="Angle threshold for dissolving unnecessary edges (degrees)"
    )
    
    fix_non_manifold: bpy.props.BoolProperty(
        name="Fix Non-Manifold", 
        default=False,
        description="Fix non-manifold geometry that causes decimation artifacts"
    )
    
    fill_holes: bpy.props.BoolProperty(
        name="Fill Holes", 
        default=False,
        description="Fill holes in the mesh"
    )
    
    def execute(self, context):
        if not context.selected_objects:
            self.report({'ERROR'}, "No objects selected")
            return {'CANCELLED'}
        
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not mesh_objects:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}
        
        cleaned_objects = 0
        
        for obj in mesh_objects:
            original_faces = len(obj.data.polygons)
            self._cleanup_mesh(obj)
            final_faces = len(obj.data.polygons)
            
            self.report({'INFO'}, f"Cleaned {obj.name}: {original_faces} -> {final_faces} faces")
            cleaned_objects += 1
        
        self.report({'INFO'}, f"Cleaned {cleaned_objects} mesh objects - ready for modeling/LODs/export")
        return {'FINISHED'}
    
    def _cleanup_mesh(self, obj):
        """Comprehensive mesh cleanup"""
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        
        bpy.ops.mesh.select_mode(type='VERT')
        bpy.ops.mesh.select_all(action='SELECT')
        
        # Remove duplicate vertices
        bpy.ops.mesh.remove_doubles(threshold=self.merge_threshold)
        
        # Delete loose geometry
        bpy.ops.mesh.delete_loose()
        
        # Fill holes if enabled
        if self.fill_holes:
            bpy.ops.mesh.fill_holes(sides=0)
        
        # Fix non-manifold geometry
        if self.fix_non_manifold:
            self._fix_non_manifold_geometry()
        
        # Limited dissolve to remove unnecessary edges
        bpy.ops.mesh.select_all(action='SELECT')
        dissolve_angle_rad = math.radians(self.dissolve_angle)
        bpy.ops.mesh.dissolve_limited(angle_limit=dissolve_angle_rad)
        
        # Final cleanup
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.normals_make_consistent(inside=False)
        try:
            bpy.ops.mesh.beautify_fill()
        except:
            pass
        
        bpy.ops.object.mode_set(mode='OBJECT')
    
    def _fix_non_manifold_geometry(self):
        """Fix non-manifold edges and vertices"""
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.select_non_manifold()
        
        selected_edges = bpy.context.tool_settings.mesh_select_mode[1]
        if selected_edges:
            bpy.ops.mesh.edge_face_add()
        else:
            bpy.ops.mesh.delete(type='VERT')
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class ARWEAPONS_OT_create_lods(bpy.types.Operator):
    bl_idname = "arweapons.create_lods"
    bl_label = "Create LOD Levels"
    bl_options = {'REGISTER', 'UNDO'}
    
    lod_levels: bpy.props.IntProperty(
        name="LOD Levels", 
        default=3, 
        min=1, 
        max=5,
        description="Number of LOD levels to create"
    )
    
    create_collection: bpy.props.BoolProperty(
        name="Create Collection", 
        default=True,
        description="Organize LODs in a collection"
    )
    
    join_lod_levels: bpy.props.BoolProperty(
        name="Join LOD Levels", 
        default=True,
        description="Join all parts of each LOD level into single objects"
    )
    
    aggressive_reduction: bpy.props.BoolProperty(
        name="Aggressive Reduction", 
        default=True,
        description="Use more dramatic reduction ratios for visible LOD differences"
    )
    
    def execute(self, context):
        if not context.selected_objects:
            self.report({'ERROR'}, "No objects selected")
            return {'CANCELLED'}
        
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not mesh_objects:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}
        
        # Get base name from first object or use "Weapon" as default
        first_obj = mesh_objects[0]
        base_name = first_obj.name.replace("_LOD0", "").split("_")[0] if "_" in first_obj.name else "Weapon"
        
        # Create collection if requested
        if self.create_collection:
            collection_name = f"{base_name}_LOD_Collection"
            if collection_name not in bpy.data.collections:
                new_collection = bpy.data.collections.new(collection_name)
                context.scene.collection.children.link(new_collection)
            else:
                new_collection = bpy.data.collections[collection_name]
        
        # Choose reduction ratios
        if self.aggressive_reduction:
            ratios = [0.5, 0.25, 0.15, 0.1, 0.08]  # Weapon-appropriate reduction
        else:
            ratios = [0.7, 0.4, 0.25, 0.15, 0.1]  # Conservative reduction
        
        created_lods = 0
        all_lod_objects = {i: [] for i in range(1, self.lod_levels + 1)}
        
        # Process each selected object
        for source_obj in mesh_objects:
            obj_base_name = source_obj.name.replace("_LOD0", "")
            
            for lod in range(1, min(self.lod_levels + 1, 6)):  # Max 5 LODs
                # Duplicate from source
                bpy.ops.object.select_all(action='DESELECT')
                source_obj.select_set(True)
                context.view_layer.objects.active = source_obj
                
                bpy.ops.object.duplicate_move(
                    OBJECT_OT_duplicate={"linked": False, "mode": 'TRANSLATION'}, 
                    TRANSFORM_OT_translate={"value": (0, 0, 0)}
                )
                
                lod_obj = context.active_object
                lod_obj.name = f"{obj_base_name}_LOD{lod}"
                
                # Apply decimation
                bpy.ops.object.modifier_add(type='DECIMATE')
                decimate_mod = lod_obj.modifiers["Decimate"]
                decimate_mod.ratio = ratios[lod - 1]
                bpy.ops.object.modifier_apply(modifier="Decimate")
                
                # Add to collection if enabled
                if self.create_collection:
                    if lod_obj.name in context.scene.collection.objects:
                        context.scene.collection.objects.unlink(lod_obj)
                    new_collection.objects.link(lod_obj)
                
                # Track for joining
                all_lod_objects[lod].append(lod_obj)
                created_lods += 1
        
        # Join LOD levels if requested
        if self.join_lod_levels:
            for lod_level, lod_objects in all_lod_objects.items():
                if len(lod_objects) > 1:
                    self._join_lod_objects(lod_objects, f"{base_name}_LOD{lod_level}")
        
        # Rename source objects to LOD0
        for source_obj in mesh_objects:
            if "_LOD0" not in source_obj.name:
                source_obj.name = f"{source_obj.name}_LOD0"
            
            # Add source to collection too
            if self.create_collection:
                if source_obj.name in context.scene.collection.objects:
                    context.scene.collection.objects.unlink(source_obj)
                new_collection.objects.link(source_obj)
        
        # Select remaining LOD objects
        bpy.ops.object.select_all(action='DESELECT')
        valid_lod_objects = []
        
        for obj_name in bpy.data.objects.keys():
            if "_LOD" in obj_name and any(obj_name.startswith(f"{base_name}_LOD") for base_name in [obj.name.split("_")[0] for obj in mesh_objects]):
                obj = bpy.data.objects[obj_name]
                obj.select_set(True)
                valid_lod_objects.append(obj)
        
        self.report({'INFO'}, f"Created {created_lods} LOD objects, joined into {len(valid_lod_objects)} final LOD levels")
        return {'FINISHED'}
    
    def _join_lod_objects(self, lod_objects, joined_name):
        """Join multiple LOD objects into a single object"""
        if not lod_objects:
            return
        
        # Select all objects for this LOD level
        bpy.ops.object.select_all(action='DESELECT')
        for obj in lod_objects:
            obj.select_set(True)
        
        # Set the first object as active
        bpy.context.view_layer.objects.active = lod_objects[0]
        
        # Join all selected objects
        bpy.ops.object.join()
        
        # Rename the joined object
        joined_obj = bpy.context.active_object
        joined_obj.name = joined_name
        
        return joined_obj
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class ARWEAPONS_PT_panel(bpy.types.Panel):
    bl_label = "AR Weapons Enhanced"
    bl_idname = "ARWEAPONS_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'AR Weapons'
    
    def draw(self, context):
        layout = self.layout
        
        box = layout.box()
        box.label(text="Component Separation", icon='MOD_BUILD')
        box.operator("arweapons.separate_components", text="Separate Component", icon='UNLINKED')
        
        col = box.column(align=True)
        col.separator()
        col.label(text="Add to Existing Objects:")
        col.operator("arweapons.add_to_object", text="Add Bone/Socket to Object", icon='EMPTY_ARROWS')
        
        box = layout.box()
        box.label(text="Collision", icon='MESH_CUBE')
        
        row = box.row(align=True)
        row.operator("arweapons.create_ucx_collision", text="UCX Physics", icon='MESH_CUBE')
        row.operator("arweapons.create_firegeo_collision", text="FireGeo", icon='MESH_ICOSPHERE')
        
        box = layout.box()
        box.label(text="Attachment Points", icon='EMPTY_DATA')
        

        
        col.separator()
        col.label(text="Socket:")
        op = col.operator("arweapons.create_socket", text="Add Socket")
        op.socket_type = 'custom'
        
        box = layout.box()
        box.label(text="Mesh Tools", icon='EDITMODE_HLT')
        
        row = box.row(align=True)
        row.operator("arweapons.cleanup_mesh", text="Cleanup Mesh", icon='BRUSH_DATA')
        row.operator("arweapons.create_lods", text="Create LODs", icon='MOD_DECIM')
        
        box = layout.box()
        box.label(text="Preparation", icon='ORIENTATION_VIEW')
        
        row = box.row(align=True)
        row.operator("arweapons.center_weapon", text="Center", icon='PIVOT_BOUNDBOX')
        row.operator("arweapons.scale_weapon", text="Scale", icon='FULLSCREEN_ENTER')
        
        box = layout.box()
        box.label(text="Rigging", icon='ARMATURE_DATA')
        
        col = box.column(align=True)
        col.operator("arweapons.create_armature", text="Create Weapon Armature", icon='ARMATURE_DATA')
        
        col.separator()
        col.label(text="Bones:")
        

        col.operator("arweapons.create_bone", text="Add bones").bone_type = 'custom'
        
        col.separator()
        col.label(text="Skinning:")
        col.operator("arweapons.setup_skinning", text="Setup Skinning")
        col.operator("arweapons.create_vertex_group", text="Assign to Bone")
        
        col.separator()
        col.label(text="Parenting:")
        col.operator("arweapons.parent_to_armature", text="Parent to Armature")


        # Replace the preset section in your panel with this:
        
        col.separator()
        col.label(text="Parenting:")
        row = col.row(align=True)
        row.operator("arvehicles.parent_to_armature", text="Parent Meshes")
        row.operator("arvehicles.parent_empties", text="Parent Empties")
        
        
        box = layout.box()
        box.label(text="Two-Phase Preset Manager", icon='PRESET')
        
        col = box.column(align=True)
        col.operator("arvehicles.manage_presets", text="Create/Edit Preset", icon='PLUS')
        
        row = col.row(align=True)
        row.operator("arvehicles.preset_separation", text="Preset Action", icon='LOOP_FORWARDS')
        row.operator("arvehicles.skip_preset_item", text="Skip", icon='FORWARD')  # New skip button
        
        row = col.row(align=True)
        row.operator("arvehicles.reset_preset", text="Reset", icon='FILE_REFRESH')
        
        # Show current preset status
        scene = context.scene
        if "arvehicles_active_preset" in scene:
            preset_name = scene["arvehicles_active_preset"]
            preset_prefix = f"arvehicles_preset_{preset_name}_"
            
            count_key = f"{preset_prefix}count"
            if count_key in scene:
                preset_count = scene[count_key]
                current_phase = scene.get(f"{preset_prefix}phase", "bones")
                
                col.separator()
                col.label(text=f"Active: {preset_name}")
                col.label(text=f"Phase: {current_phase.title()}")
                
                if current_phase == "bones":
                    bone_index = scene.get(f"{preset_prefix}bone_index", 0)
                    if bone_index < preset_count:
                        next_bone = scene[f"{preset_prefix}bone_{bone_index}"]
                        col.label(text=f"Next: {next_bone}")
                        col.label(text=f"Mesh: Mesh_{next_bone}")
                        col.label(text=f"Progress: {bone_index + 1}/{preset_count}")
                    else:
                        col.label(text="Ready for socket phase!")
                else:
                    socket_index = scene.get(f"{preset_prefix}socket_index", 0)
                    if socket_index < preset_count:
                        next_socket = scene[f"{preset_prefix}socket_{socket_index}"]
                        col.label(text=f"Next: {next_socket}")
                        col.label(text=f"Progress: {socket_index + 1}/{preset_count}")
                    else:
                        col.label(text="All complete!")
        else:
            col.separator()
            col.label(text="No active preset")




classes = (
    ARWEAPONS_OT_create_ucx_collision,
    ARWEAPONS_OT_create_firegeo_collision,
    ARWEAPONS_OT_center_weapon,
    ARWEAPONS_OT_scale_weapon,
    ARWEAPONS_OT_create_socket,
    ARWEAPONS_OT_separate_components,
    ARWEAPONS_OT_create_armature,
    ARWEAPONS_OT_create_bone,
    ARVEHICLES_OT_manage_presets,
    ARVEHICLES_OT_preset_separation, 
    ARVEHICLES_OT_reset_preset,
    ARWEAPONS_OT_setup_skinning,
    ARWEAPONS_OT_add_to_object,
    ARWEAPONS_OT_parent_to_armature,
    ARWEAPONS_OT_create_empties,
    ARVEHICLES_OT_skip_preset_item,
    ARWEAPONS_OT_create_vertex_group,
    ARWEAPONS_OT_cleanup_mesh,
    ARWEAPONS_OT_create_lods,
    ARWEAPONS_PT_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
