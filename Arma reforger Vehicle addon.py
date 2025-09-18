bl_info = {
    "name": "Arma Reforger Vehicle Tools Enhanced",
    "author": "steffen",
    "version": (2, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > AR Vehicles",
    "description": "Enhanced tools for preparing and rigging vehicles for Arma Reforger",
    "category": "Object",
}

import bpy
import bmesh
import math
from mathutils import Vector, Matrix

VEHICLE_SOCKET_TYPES = [
    ('window', "Window", "Vehicle window socket"),
    ('door', "Door", "Vehicle door socket"),
    ('hood', "Hood", "Vehicle hood socket"),
    ('trunk', "Trunk", "Vehicle trunk socket"),
    ('wheel', "Wheel", "Vehicle wheel socket"),
    ('light', "Light", "Vehicle light socket"),
    ('mirror', "Mirror", "Vehicle mirror socket"),
    ('antenna', "Antenna", "Vehicle antenna socket"),
    ('turret', "Turret", "Vehicle turret socket"),
    ('hatch', "Hatch", "Vehicle hatch socket"),
    ('panel', "Panel", "Vehicle panel socket"),
    ('seat', "Seat", "Vehicle seat socket"),
    ('dashboard', "Dashboard", "Vehicle dashboard socket"),
    ('steering_wheel', "Steering Wheel", "Steering wheel socket"),
    ('gear_shifter', "Gear Shifter", "Gear shifter socket"),
    ('handbrake', "Handbrake", "Handbrake socket"),
    ('pedal', "Pedal", "Vehicle pedal socket"),
    ('engine', "Engine", "Engine socket"),
    ('exhaust', "Exhaust", "Exhaust socket"),
    ('suspension', "Suspension", "Suspension socket"),
    ('rotor', "Rotor", "Helicopter rotor socket"),
    ('landing_gear', "Landing Gear", "Landing gear socket"),
    ('fuel_tank', "Fuel Tank", "Fuel tank socket"),
    ('battery', "Battery", "Battery socket"),
    ('radiator', "Radiator", "Radiator socket"),
    ('custom', "Custom", "Custom socket type"),
]

VEHICLE_COMPONENT_TYPES = [
    ('window', "Window", "Vehicle window component"),
    ('door', "Door", "Vehicle door component"),
    ('hood', "Hood", "Vehicle hood/bonnet component"),
    ('trunk', "Trunk", "Vehicle trunk/boot component"),
    ('wheel', "Wheel", "Vehicle wheel component"),
    ('light', "Light", "Vehicle light component"),
    ('mirror', "Mirror", "Vehicle mirror component"),
    ('seat', "Seat", "Vehicle seat component"),
    ('dashboard', "Dashboard", "Vehicle dashboard component"),
    ('steering_wheel', "Steering Wheel", "Steering wheel component"),
    ('gear_shifter', "Gear Shifter", "Gear shifter component"),
    ('handbrake', "Handbrake", "Handbrake component"),
    ('pedal', "Pedal", "Vehicle pedal component"),
    ('engine', "Engine", "Engine component"),
    ('exhaust', "Exhaust", "Exhaust component"),
    ('suspension', "Suspension", "Suspension component"),
    ('rotor', "Rotor", "Helicopter rotor component"),
    ('landing_gear', "Landing Gear", "Landing gear component"),
    ('fuel_tank', "Fuel Tank", "Fuel tank component"),
    ('battery', "Battery", "Battery component"),
    ('radiator', "Radiator", "Radiator component"),
    ('panel', "Panel", "Body panel component"),
    ('hatch', "Hatch", "Vehicle hatch component"),
    ('antenna', "Antenna", "Antenna component"),
    ('custom', "Custom", "Custom component type"),
]

VEHICLE_BONE_TYPES = [
    ('v_root', "Root Bone", "Main vehicle bone"),
    ('v_body', "Body", "Vehicle body bone"),
    ('v_door_left', "Door Left", "Left door bone"),
    ('v_door_right', "Door Right", "Right door bone"),
    ('v_door_rear', "Door Rear", "Rear door bone"),
    ('v_hood', "Hood", "Hood bone"),
    ('v_trunk', "Trunk", "Trunk bone"),
    ('v_wheel_1', "Wheel 1", "Wheel 1 bone"),
    ('v_wheel_2', "Wheel 2", "Wheel 2 bone"),
    ('v_wheel_3', "Wheel 3", "Wheel 3 bone"),
    ('v_wheel_4', "Wheel 4", "Wheel 4 bone"),
    ('v_wheel_5', "Wheel 5", "Wheel 5 bone"),
    ('v_wheel_6', "Wheel 6", "Wheel 6 bone"),
    ('v_steeringwheel', "Steering Wheel", "Steering wheel bone"),
    ('v_steering_wheel', "Steering Wheel Alt", "Alternative steering wheel bone"),
    ('v_turret_base', "Turret Base", "Turret base bone"),
    ('v_turret_gun', "Turret Gun", "Turret gun bone"),
    ('v_rotor', "Rotor", "Helicopter rotor bone"),
    ('v_tail_rotor', "Tail Rotor", "Tail rotor bone"),
    ('v_landing_gear', "Landing Gear", "Landing gear bone"),
    ('v_landing_gear_L', "Landing Gear L", "Left landing gear bone"),
    ('v_landing_gear_R', "Landing Gear R", "Right landing gear bone"),
    ('v_suspension1', "Suspension 1", "Suspension 1 bone"),
    ('v_suspension2', "Suspension 2", "Suspension 2 bone"),
    ('v_suspension3', "Suspension 3", "Suspension 3 bone"),
    ('v_suspension4', "Suspension 4", "Suspension 4 bone"),
    ('v_exhaust', "Exhaust", "Exhaust bone"),
    ('v_engine_inlet', "Engine Inlet", "Engine inlet bone"),
    ('v_dashboard_arm', "Dashboard Arm", "Dashboard arm bone"),
    ('v_pedal_brake', "Pedal Brake", "Brake pedal bone"),
    ('v_pedal_throttle', "Pedal Throttle", "Throttle pedal bone"),
    ('v_handbrake', "Handbrake", "Handbrake bone"),
    ('v_gearshift', "Gearshift", "Gearshift bone"),
    ('v_light_switch', "Light Switch", "Light switch bone"),
    ('v_starter_switch', "Starter Switch", "Starter switch bone"),
    ('v_cloth_cover_jiggle', "Cloth Cover", "Cloth cover jiggle bone"),
    ('v_antenna', "Antenna", "Antenna bone"),
    ('v_mirror_left', "Mirror Left", "Left mirror bone"),
    ('v_mirror_right', "Mirror Right", "Right mirror bone"),
    ('v_wiper_L', "Wiper Left", "Left wiper bone"),
    ('v_wiper_R', "Wiper Right", "Right wiper bone"),
    ('v_steps', "Steps", "Vehicle steps bone"),
    ('v_steps_piston', "Steps Piston", "Steps piston bone"),
    ('v_steps_string', "Steps String", "Steps string bone"),
    ('v_axis_shaft', "Axis Shaft", "Axis shaft bone"),
    ('v_back_door_L', "Back Door L", "Back door left bone"),
    ('v_back_door_R', "Back Door R", "Back door right bone"),
    ('v_back_door_holder_L', "Back Door Holder L", "Back door holder left bone"),
    ('v_back_door_holder_R', "Back Door Holder R", "Back door holder right bone"),
    ('v_canister', "Canister", "Canister bone"),
    ('v_dashboard_ammeter', "Dashboard Ammeter", "Dashboard ammeter bone"),
    ('v_dashboard_coolant_temp', "Dashboard Coolant", "Dashboard coolant temp bone"),
    ('v_dashboard_fuel', "Dashboard Fuel", "Dashboard fuel bone"),
    ('v_dashboard_oil_pressure', "Dashboard Oil", "Dashboard oil pressure bone"),
    ('v_dashboard_speed', "Dashboard Speed", "Dashboard speed bone"),
    ('v_water_temp_dial', "Water Temp Dial", "Water temperature dial bone"),
    ('v_transfer', "Transfer", "Transfer bone"),
    ('v_trim_vane', "Trim Vane", "Trim vane bone"),
    ('v_turret_slot', "Turret Slot", "Turret slot bone"),
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
        description="Comma-separated list of socket names (must match bone count)"
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
        
        # Validate list lengths match
        if len(bones) != len(sockets):
            self.report({'ERROR'}, f"List lengths must match: {len(bones)} bones, {len(sockets)} sockets")
            return {'CANCELLED'}
        
        # Store preset data as individual scene properties
        preset_prefix = f"arvehicles_preset_{self.preset_name}_"
        
        # Clear any existing preset data
        keys_to_remove = [key for key in scene.keys() if key.startswith(preset_prefix)]
        for key in keys_to_remove:
            del scene[key]
        
        # Store new preset data
        scene[f"{preset_prefix}count"] = len(bones)
        scene[f"{preset_prefix}bone_index"] = 0
        scene[f"{preset_prefix}socket_index"] = 0
        scene[f"{preset_prefix}phase"] = "bones"  # Start with bones phase
        scene[f"{preset_prefix}parent_meshes"] = self.parent_meshes  # Store the option
        
        for i, (bone, socket) in enumerate(zip(bones, sockets)):
            scene[f"{preset_prefix}bone_{i}"] = bone
            scene[f"{preset_prefix}socket_{i}"] = socket
        
        # Set as active preset
        scene["arvehicles_active_preset"] = self.preset_name
        
        self.report({'INFO'}, f"Created preset '{self.preset_name}' with {len(bones)} items. Starting with bone separation phase!")
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


class ARVEHICLES_OT_preset_separation(bpy.types.Operator):
    bl_idname = "arvehicles.preset_separation"
    bl_label = "Preset Separation"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Separate component or place socket using current preset item"
    
    auto_skinning: bpy.props.BoolProperty(name="Auto Skinning", default=True)
    
    def execute(self, context):
        scene = context.scene
        
        # Check if we have an active preset
        if "arvehicles_active_preset" not in scene:
            self.report({'ERROR'}, "No active preset. Create a preset first.")
            return {'CANCELLED'}
        
        preset_name = scene["arvehicles_active_preset"]
        preset_prefix = f"arvehicles_preset_{preset_name}_"
        
        # Check if preset data exists
        count_key = f"{preset_prefix}count"
        if count_key not in scene:
            self.report({'ERROR'}, f"Preset '{preset_name}' data not found. Create the preset again.")
            return {'CANCELLED'}
        
        preset_count = scene[count_key]
        current_phase = scene.get(f"{preset_prefix}phase", "bones")
        
        if current_phase == "bones":
            return self._handle_bone_phase(context, scene, preset_prefix, preset_count)
        else:
            return self._handle_socket_phase(context, scene, preset_prefix, preset_count)
    
    def _handle_bone_phase(self, context, scene, preset_prefix, preset_count):
        bone_index = scene.get(f"{preset_prefix}bone_index", 0)
        
        if bone_index >= preset_count:
            # Move to socket phase
            scene[f"{preset_prefix}phase"] = "sockets"
            scene[f"{preset_prefix}socket_index"] = 0
            self.report({'INFO'}, "Bone phase complete! Now place sockets using face selection.")
            return {'FINISHED'}
        
        # Get current bone name
        bone_name = scene[f"{preset_prefix}bone_{bone_index}"]
        mesh_name = f"Mesh_{bone_name}"
        
        # Check if we're in edit mode with faces selected
        if context.mode != 'EDIT_MESH':
            self.report({'ERROR'}, "Must be in Edit Mode with faces selected")
            return {'CANCELLED'}
            
        mesh = context.active_object.data
        if not mesh.total_face_sel:
            self.report({'ERROR'}, "No faces selected")
            return {'CANCELLED'}
        
        obj = context.active_object
        
        # Calculate face center
        bm = bmesh.from_edit_mesh(mesh)
        selected_faces = [f for f in bm.faces if f.select]
        
        center = Vector((0, 0, 0))
        for face in selected_faces:
            center += face.calc_center_median()
        center /= len(selected_faces)
        world_center = obj.matrix_world @ center
        
        # Separate the selected faces
        bpy.ops.mesh.separate(type='SELECTED')
        bpy.ops.object.mode_set(mode='OBJECT')
        
        new_obj = context.selected_objects[-1]
        new_obj.name = mesh_name
        
        # Find armature and create bone
        armature = None
        for armature_obj in bpy.data.objects:
            if armature_obj.type == 'ARMATURE':
                armature = armature_obj
                break
        
        if armature:
            context.view_layer.objects.active = armature
            bpy.ops.object.mode_set(mode='EDIT')
            
            # Check for duplicate and increment if needed
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
            
            # Setup skinning
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
            
        # Parent to armature only if option is enabled
        parent_meshes = scene.get(f"{preset_prefix}parent_meshes", True)
        if armature and parent_meshes:
            bpy.ops.object.select_all(action='DESELECT')
            new_obj.select_set(True)
            armature.select_set(True)
            context.view_layer.objects.active = armature
            bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)
        
        # Advance bone index
        scene[f"{preset_prefix}bone_index"] = bone_index + 1
        
        # Report progress
        remaining = preset_count - (bone_index + 1)
        if remaining > 0:
            next_bone = scene[f"{preset_prefix}bone_{bone_index + 1}"]
            self.report({'INFO'}, f"Created '{mesh_name}'. Next bone: {next_bone} ({remaining} remaining)")
        else:
            self.report({'INFO'}, f"Created '{mesh_name}'. Bone phase complete! Ready for socket phase.")
        
        return {'FINISHED'}
    
    def _handle_socket_phase(self, context, scene, preset_prefix, preset_count):
        socket_index = scene.get(f"{preset_prefix}socket_index", 0)
        
        if socket_index >= preset_count:
            self.report({'INFO'}, "All sockets placed! Preset complete.")
            return {'FINISHED'}
        
        # Get current socket name
        socket_name = scene[f"{preset_prefix}socket_{socket_index}"]
        
        # Determine socket position using face selection (like existing socket creation)
        socket_location = (0, 0, 0)
        
        if context.mode == 'EDIT_MESH' and context.active_object and context.active_object.type == 'MESH':
            obj = context.active_object
            mesh = obj.data
            
            if mesh.total_face_sel > 0:
                bm = bmesh.from_edit_mesh(mesh)
                selected_faces = [f for f in bm.faces if f.select]
                
                if selected_faces:
                    center = Vector((0, 0, 0))
                    for face in selected_faces:
                        center += face.calc_center_median()
                    center /= len(selected_faces)
                    socket_location = obj.matrix_world @ center
                    bpy.ops.object.mode_set(mode='OBJECT')
                else:
                    self.report({'ERROR'}, "No faces selected for socket placement")
                    return {'CANCELLED'}
            else:
                self.report({'ERROR'}, "No faces selected for socket placement")
                return {'CANCELLED'}
        else:
            self.report({'ERROR'}, "Must be in Edit Mode with faces selected for socket placement")
            return {'CANCELLED'}
        
        # Create socket
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
        
        # Parent to armature if it exists
        armature = None
        for armature_obj in bpy.data.objects:
            if armature_obj.type == 'ARMATURE':
                armature = armature_obj
                break
        
        if armature:
            socket.parent = armature
        
        # Advance socket index
        scene[f"{preset_prefix}socket_index"] = socket_index + 1
        
        # Report progress
        remaining = preset_count - (socket_index + 1)
        if remaining > 0:
            next_socket = scene[f"{preset_prefix}socket_{socket_index + 1}"]
            self.report({'INFO'}, f"Placed '{final_socket_name}'. Next socket: {next_socket} ({remaining} remaining)")
        else:
            self.report({'INFO'}, f"Placed '{final_socket_name}'. All presets complete!")
        
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


class ARVEHICLES_OT_create_ucx_collision(bpy.types.Operator):
    bl_idname = "arvehicles.create_ucx_collision"
    bl_label = "Create Collision"
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
        default=50, 
        min=12, 
        max=200,
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
            name = f"{self.method}_body"
        else:
            name = f"{self.method}_body_part_{idx:02d}"
        
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
        
        # Apply transforms (required by documentation)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        
        # Set origin to geometry center (required for UCL, USP, UCS)
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
        """Fix non-planar faces - the critical fix"""
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        
        # Select all
        bpy.ops.mesh.select_all(action='SELECT')
        
        # Remove tiny edges that cause non-planar faces
        bpy.ops.mesh.remove_doubles(threshold=0.0001)
        
        # Remove loose geometry
        bpy.ops.mesh.delete_loose()
        
        # Force all faces to be triangular (guarantees planar faces)
        bpy.ops.mesh.quads_convert_to_tris(quad_method='FIXED', ngon_method='BEAUTY')
        
        # Recalculate normals
        bpy.ops.mesh.normals_make_consistent(inside=False)
        
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Apply rotation and scale as required by documentation
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
        obj["usage"] = "Vehicle"
        obj["layer_preset"] = "Vehicle"
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)




class ARVEHICLES_OT_create_firegeo_collision(bpy.types.Operator):
    bl_idname = "arvehicles.create_firegeo_collision"
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
    target_faces: bpy.props.IntProperty(name="Target Faces", default=400, min=100, max=5000)
    offset: bpy.props.FloatProperty(name="Offset", default=0.01, min=0.0, max=0.05)
    
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
                dup_obj.name = "UTM_vehicle"
            else:
                dup_obj.name = f"UTM_vehicle_part_{idx}"
                
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
        
        # Select all collision objects instead of creating empty parent
        bpy.ops.object.select_all(action='DESELECT')
        for obj in collision_objects:
            obj.select_set(True)
        
        if collision_objects:
            context.view_layer.objects.active = collision_objects[0]
        
        self.report({'INFO'}, f"Created FireGeo collision with {total_faces} total faces")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
class ARVEHICLES_OT_create_wheel_collisions(bpy.types.Operator):
    bl_idname = "arvehicles.create_wheel_collisions"
    bl_label = "Create Wheel Collisions"
    bl_options = {'REGISTER', 'UNDO'}
    
    num_wheels: bpy.props.IntProperty(name="Number of Wheels", default=4, min=2, max=16)
    wheel_radius: bpy.props.FloatProperty(name="Wheel Radius", default=0.35, min=0.1, max=1.5)
    wheel_width: bpy.props.FloatProperty(name="Wheel Width", default=0.25, min=0.1, max=0.8)
    
    def execute(self, context):
        positions = []
        for i in range(self.num_wheels):
            if i < 2:
                y_pos = 1.5
            else:
                y_pos = -1.5
            
            x_pos = 0.8 if i % 2 == 0 else -0.8
            z_pos = 0.3
            
            positions.append((f"wheel_{i+1}", (x_pos, y_pos, z_pos)))
        
        created_wheels = []
        
        for wheel_name, (pos_x, pos_y, pos_z) in positions:
            bpy.ops.mesh.primitive_cylinder_add(
                radius=self.wheel_radius,
                depth=self.wheel_width,
                location=(pos_x, pos_y, pos_z),
                rotation=(0, math.pi/2, 0)
            )
            
            cylinder = bpy.context.active_object
            cylinder.name = f"UCS_{wheel_name}"
            
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
            
            if "UCS_Material" not in bpy.data.materials:
                mat = bpy.data.materials.new(name="UCS_Material")
                mat.diffuse_color = (0.8, 0.5, 0.0, 0.6)
            else:
                mat = bpy.data.materials["UCS_Material"]
            
            if cylinder.data.materials:
                cylinder.data.materials[0] = mat
            else:
                cylinder.data.materials.append(mat)
            
            cylinder["layer_preset"] = "Collision_Vehicle"
            cylinder["usage"] = "PhyCol"
            created_wheels.append(cylinder)
        
        self.report({'INFO'}, f"Created {len(created_wheels)} wheel collision objects")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class ARVEHICLES_OT_create_center_of_mass(bpy.types.Operator):
    bl_idname = "arvehicles.create_center_of_mass"
    bl_label = "Create Center of Mass"
    bl_options = {'REGISTER', 'UNDO'}
    
    com_size: bpy.props.FloatProperty(name="COM Size", default=0.15, min=0.05, max=0.5)
    com_height_offset: bpy.props.FloatProperty(name="Height Offset", default=-0.15, min=-0.8, max=0.5)
    
    def execute(self, context):
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0))
        
        box = bpy.context.active_object
        box.name = "COM_vehicle"
        
        box.scale.x = self.com_size
        box.scale.y = self.com_size * 2
        box.scale.z = self.com_size
        
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        
        if "COM_Material" not in bpy.data.materials:
            mat = bpy.data.materials.new(name="COM_Material")
            mat.diffuse_color = (0.3, 1.0, 0.3, 0.6)
        else:
            mat = bpy.data.materials["COM_Material"]
        
        if box.data.materials:
            box.data.materials[0] = mat
        else:
            box.data.materials.append(mat)
        
        box["layer_preset"] = "Collision_Vehicle"
        box["usage"] = "CenterOfMass"
        
        self.report({'INFO'}, "Created center of mass object")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


class ARVEHICLES_OT_create_socket(bpy.types.Operator):
    bl_idname = "arvehicles.create_socket"
    bl_label = "Create Vehicle Socket"
    bl_options = {'REGISTER', 'UNDO'}
    
    socket_type: bpy.props.EnumProperty(name="Socket Type", items=VEHICLE_SOCKET_TYPES, default='door')
    custom_name: bpy.props.StringProperty(name="Custom Name", default="")
    parent_to_armature: bpy.props.BoolProperty(
        name="Parent to Armature", 
        default=True,
        description="Automatically parent socket to vehicle armature"
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
        socket.empty_display_size = 0.15
        socket.location = socket_location
        
        context.collection.objects.link(socket)
        
        socket["socket_type"] = self.socket_type
        socket["vehicle_part"] = "attachment_point"
        
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
        
        self.report({'INFO'}, f"Created vehicle socket '{socket_name}' at selected faces")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class ARVEHICLES_OT_add_to_object(bpy.types.Operator):
    bl_idname = "arvehicles.add_to_object"
    bl_label = "Add Bone/Socket to Object"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Add bone and/or socket to existing separated object"
    
    # Component type (unified for both bone and socket)
    component_type: bpy.props.EnumProperty(name="Component Type", items=VEHICLE_COMPONENT_TYPES, default='door')
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
            'window': 'window', 'door': 'door', 'hood': 'hood', 'trunk': 'trunk',
            'wheel': 'wheel', 'light': 'light', 'mirror': 'mirror', 'antenna': 'antenna',
            'hatch': 'hatch', 'panel': 'panel', 'seat': 'seat', 'dashboard': 'dashboard',
            'steering_wheel': 'steering_wheel', 'gear_shifter': 'gear_shifter',
            'handbrake': 'handbrake', 'pedal': 'pedal', 'engine': 'engine',
            'exhaust': 'exhaust', 'suspension': 'suspension', 'rotor': 'rotor',
            'landing_gear': 'landing_gear', 'fuel_tank': 'fuel_tank',
            'battery': 'battery', 'radiator': 'radiator',
        }
        return component_to_socket.get(component_type, 'custom')
    
    def _get_bone_type_for_component(self, component_type):
        """Get the matching bone type for a component type"""
        component_to_bone = {
            'door': 'v_door_left', 'hood': 'v_hood', 'trunk': 'v_trunk',
            'wheel': 'v_wheel_1', 'steering_wheel': 'v_steering_wheel',
            'gear_shifter': 'v_gearshift', 'handbrake': 'v_handbrake',
            'pedal': 'v_pedal_brake', 'exhaust': 'v_exhaust',
            'suspension': 'v_suspension1', 'rotor': 'v_rotor',
            'landing_gear': 'v_landing_gear', 'antenna': 'v_antenna',
            'mirror': 'v_mirror_left', 'dashboard': 'v_dashboard_arm',
        }
        return component_to_bone.get(component_type, 'custom')
    
    def _get_component_type_for_object(self, obj_name):
        """Guess component type from object name"""
        name_lower = obj_name.lower()
        if 'door' in name_lower:
            return 'door'
        elif 'window' in name_lower:
            return 'window'
        elif 'hood' in name_lower or 'bonnet' in name_lower:
            return 'hood'
        elif 'trunk' in name_lower or 'boot' in name_lower:
            return 'trunk'
        elif 'wheel' in name_lower:
            return 'wheel'
        elif 'light' in name_lower:
            return 'light'
        elif 'mirror' in name_lower:
            return 'mirror'
        elif 'antenna' in name_lower:
            return 'antenna'
        elif 'steering' in name_lower:
            return 'steering_wheel'
        elif 'exhaust' in name_lower:
            return 'exhaust'
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
                    bone_name = f"v_{self.custom_name.lower().replace(' ', '_')}"
                else:
                    bone_name = f"v_{target_obj.name.lower().replace(' ', '_')}"
            else:
                bone_name = bone_type
                # Handle left/right detection for doors
                if self.component_type == 'door' and target_obj.name:
                    name_lower = target_obj.name.lower()
                    if 'right' in name_lower or '_r' in name_lower:
                        bone_name = 'v_door_right'
            
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
            bone.tail = (location.x, location.y + 0.2, location.z)
            bone.roll = 0.0
            
            # Parent to v_root if it exists
            if 'v_root' in armature.data.edit_bones:
                bone.parent = armature.data.edit_bones['v_root']
            
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # Set up skinning if requested
            if self.auto_skinning:
                bpy.ops.object.select_all(action='DESELECT')
                target_obj.select_set(True)
                context.view_layer.objects.active = target_obj
                
                # Create vertex group for the bone
                if bone_name not in target_obj.vertex_groups:
                    vertex_group = target_obj.vertex_groups.new(name=bone_name)
                    
                    # Create v_root group if it doesn't exist
                    if bone_name != "v_root" and "v_root" not in target_obj.vertex_groups:
                        v_root_group = target_obj.vertex_groups.new(name="v_root")
                    
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
            socket.empty_display_size = 0.15
            socket.location = location
            
            context.collection.objects.link(socket)
            
            socket["socket_type"] = socket_type
            socket["attached_part"] = target_obj.name
            socket["vehicle_part"] = "attachment_point"
            
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


class ARVEHICLES_OT_separate_components(bpy.types.Operator):
    bl_idname = "arvehicles.separate_components"
    bl_label = "Separate Vehicle Components"
    bl_options = {'REGISTER', 'UNDO'}
    
    component_type: bpy.props.EnumProperty(name="Component Type", items=VEHICLE_COMPONENT_TYPES, default='door')
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
            'window': 'window', 'door': 'door', 'hood': 'hood', 'trunk': 'trunk',
            'wheel': 'wheel', 'light': 'light', 'mirror': 'mirror', 'antenna': 'antenna',
            'hatch': 'hatch', 'panel': 'panel', 'seat': 'seat', 'dashboard': 'dashboard',
            'steering_wheel': 'steering_wheel', 'gear_shifter': 'gear_shifter',
            'handbrake': 'handbrake', 'pedal': 'pedal', 'engine': 'engine',
            'exhaust': 'exhaust', 'suspension': 'suspension', 'rotor': 'rotor',
            'landing_gear': 'landing_gear', 'fuel_tank': 'fuel_tank',
            'battery': 'battery', 'radiator': 'radiator',
        }
        return component_to_socket.get(component_type, 'custom')
    
    def _get_bone_type_for_component(self, component_type):
        """Get the matching bone type for a component type"""
        component_to_bone = {
            'door': 'v_door_left', 'hood': 'v_hood', 'trunk': 'v_trunk',
            'wheel': 'v_wheel_1', 'steering_wheel': 'v_steering_wheel',
            'gear_shifter': 'v_gearshift', 'handbrake': 'v_handbrake',
            'pedal': 'v_pedal_brake', 'exhaust': 'v_exhaust',
            'suspension': 'v_suspension1', 'rotor': 'v_rotor',
            'landing_gear': 'v_landing_gear', 'antenna': 'v_antenna',
            'mirror': 'v_mirror_left', 'dashboard': 'v_dashboard_arm',
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
            'window': "window_", 'door': "door_", 'hood': "hood_", 'trunk': "trunk_",
            'wheel': "wheel_", 'light': "light_", 'mirror': "mirror_", 'seat': "seat_",
            'dashboard': "dashboard_", 'steering_wheel': "steering_wheel_", 'gear_shifter': "gear_shifter_",
            'handbrake': "handbrake_", 'pedal': "pedal_", 'engine': "engine_", 'exhaust': "exhaust_",
            'suspension': "suspension_", 'rotor': "rotor_", 'landing_gear': "landing_gear_",
            'fuel_tank': "fuel_tank_", 'battery': "battery_", 'radiator': "radiator_",
            'panel': "panel_", 'hatch': "hatch_", 'antenna': "antenna_",
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
                armature_data = bpy.data.armatures.new("VehicleArmature")
                armature = bpy.data.objects.new("VehicleArmature", armature_data)
                context.collection.objects.link(armature)
                
                # Create v_root bone first
                context.view_layer.objects.active = armature
                bpy.ops.object.mode_set(mode='EDIT')
                root_bone = armature.data.edit_bones.new('v_root')
                root_bone.head = (0, 0, 0)
                root_bone.tail = (0, 0.2, 0)
                root_bone.roll = 0.0
                bpy.ops.object.mode_set(mode='OBJECT')
            
            # Generate bone name
            if self.custom_bone_name:
                bone_name = self.custom_bone_name
                if not bone_name.startswith('v_'):
                    bone_name = 'v_' + bone_name
            elif bone_type == 'custom':
                if self.custom_name:
                    bone_name = f"v_{self.custom_name.lower().replace(' ', '_')}"
                else:
                    bone_name = f"v_{new_name.lower().replace(' ', '_')}"
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
            bone.tail = (world_center.x, world_center.y + 0.2, world_center.z)
            bone.roll = 0.0
            
            # Parent to v_root if it exists
            if 'v_root' in armature.data.edit_bones:
                bone.parent = armature.data.edit_bones['v_root']
            
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # Set up skinning for the separated component (if enabled)
            if self.auto_skinning:
                bpy.ops.object.select_all(action='DESELECT')
                new_obj.select_set(True)
                context.view_layer.objects.active = new_obj
                
                # Create vertex group for the bone
                vertex_group = new_obj.vertex_groups.new(name=bone_name)
                
                # Also create v_root group for the main body (standard vehicle rigging)
                if bone_name != "v_root":
                    v_root_group = new_obj.vertex_groups.new(name="v_root")
                
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
            socket.empty_display_size = 0.15
            socket.location = world_center
            
            context.collection.objects.link(socket)
            
            socket["socket_type"] = socket_type
            socket["attached_part"] = new_obj.name
            socket["vehicle_part"] = "attachment_point"
            
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
        report_msg = f"Separated component '{new_name}' and parented to armature"
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
class ARVEHICLES_OT_create_armature(bpy.types.Operator):
    bl_idname = "arvehicles.create_armature"
    bl_label = "Create Vehicle Armature"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Create a minimal vehicle armature with v_root bone following Arma Reforger standards"
    
    def execute(self, context):
        # Check if armature already exists
        existing_armature = None
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE' and obj.name in ["Armature", "VehicleArmature"]:
                existing_armature = obj
                break
        
        if existing_armature:
            self.report({'INFO'}, f"Vehicle armature '{existing_armature.name}' already exists")
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
        
        # Create v_root bone - the essential root bone for all vehicles
        root_bone = armature_data.edit_bones.new('v_root')
        root_bone.head = (0, 0, 0)  # At world origin as specified
        root_bone.tail = (0, 0.2, 0)  # Y+ orientation as recommended
        root_bone.roll = 0.0
        
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Set display properties for easier bone visibility
        armature_data.display_type = 'OCTAHEDRAL'
        armature_data.show_names = True
        armature_obj.show_in_front = True
        
        self.report({'INFO'}, "Created minimal vehicle armature with v_root bone")
        return {'FINISHED'}
class ARVEHICLES_OT_create_bone(bpy.types.Operator):
    bl_idname = "arvehicles.create_bone"
    bl_label = "Add Bone"
    bl_options = {'REGISTER', 'UNDO'}
    
    bone_type: bpy.props.EnumProperty(name="Bone Type", items=VEHICLE_BONE_TYPES, default='v_door_left')
    custom_bone_name: bpy.props.StringProperty(name="Bone Name", default="custom")
    
    def execute(self, context):
        armature = None
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                armature = obj
                break
        
        if not armature:
            self.report({'ERROR'}, "No vehicle armature found")
            return {'CANCELLED'}
        
        context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='EDIT')
        
        bone_length = 0.2
        
        if self.bone_type == 'custom':
            bone_name = self.custom_bone_name
            if not bone_name.startswith('v_'):
                bone_name = 'v_' + bone_name
        else:
            bone_name = self.bone_type
        
        if bone_name in armature.data.edit_bones:
            if bone_name == 'v_root':
                self.report({'INFO'}, "v_root already exists")
                bpy.ops.object.mode_set(mode='OBJECT')
                return {'FINISHED'}
            else:
                base_name = bone_name
                counter = 1
                while bone_name in armature.data.edit_bones:
                    bone_name = f"{base_name}_{counter:02d}"
                    counter += 1
        
        parent_bone = None
        if self.bone_type != 'v_root' and 'v_root' in armature.data.edit_bones:
            parent_bone = armature.data.edit_bones['v_root']
        
        bone = armature.data.edit_bones.new(bone_name)
        bone.roll = 0.0
        if parent_bone:
            bone.parent = parent_bone
        
        if self.bone_type == 'v_root':
            bone.head = (0, 0, 0)
            bone.tail = (0, bone_length, 0)
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
        else:
            return self.execute(context)

class ARVEHICLES_OT_setup_skinning(bpy.types.Operator):
    bl_idname = "arvehicles.setup_skinning"
    bl_label = "Setup Vehicle Skinning"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        armature = None
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE' and "VehicleArmature" in obj.name:
                armature = obj
                break
        
        if not armature:
            self.report({'ERROR'}, "No vehicle armature found")
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
            
            if "v_root" not in obj.vertex_groups:
                v_root_group = obj.vertex_groups.new(name="v_root")
                
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                
                obj.vertex_groups.active = v_root_group
                bpy.ops.object.vertex_group_assign()
                
                bpy.ops.object.mode_set(mode='OBJECT')
            
            skinned_objects += 1
        
        self.report({'INFO'}, f"Setup skinning for {skinned_objects} objects")
        return {'FINISHED'}

class ARVEHICLES_OT_parent_to_armature(bpy.types.Operator):
    bl_idname = "arvehicles.parent_to_armature"
    bl_label = "Parent to Armature"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        armature = None
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE' and "VehicleArmature" in obj.name:
                armature = obj
                break
        
        if not armature:
            self.report({'ERROR'}, "No vehicle armature found")
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

class ARVEHICLES_OT_create_empties(bpy.types.Operator):
    bl_idname = "arvehicles.create_empties"
    bl_label = "Create All Vehicle Points"
    bl_options = {'REGISTER', 'UNDO'}
    
    num_crew: bpy.props.IntProperty(name="Number of Crew", default=4, min=1, max=8)
    vehicle_type: bpy.props.EnumProperty(
        name="Vehicle Type",
        items=[
            ('car', "Car", "Standard car"),
            ('truck', "Truck", "Truck"),
            ('apc', "APC", "Armored vehicle"),
        ],
        default='car'
    )
    
    def execute(self, context):
        collection_name = "Vehicle_Components"
        if collection_name in bpy.data.collections:
            vehicle_collection = bpy.data.collections[collection_name]
        else:
            vehicle_collection = bpy.data.collections.new(collection_name)
            context.scene.collection.children.link(vehicle_collection)
        
        created_empties = []
        
        crew_positions = [
            ("driver", (0.35, 0.2, 0.85)),
            ("codriver", (-0.35, 0.2, 0.85)),
            ("cargo01", (0.35, -0.5, 0.85)),
            ("cargo02", (-0.35, -0.5, 0.85)),
        ]
        
        component_positions = [
            ("engine", (0, 1.4, 0.5)),
            ("exhaust", (0.3, -1.7, 0.2)),
            ("frontlight_left", (0.7, 1.9, 0.5)),
            ("frontlight_right", (-0.7, 1.9, 0.5)),
            ("backlight_left", (0.7, -1.9, 0.5)),
            ("backlight_right", (-0.7, -1.9, 0.5)),
        ]
        
        wheel_positions = [
            ("wheel_1_1", (0.75, 1.4, 0.3)),
            ("wheel_1_2", (-0.75, 1.4, 0.3)),
            ("wheel_2_1", (0.75, -1.4, 0.3)),
            ("wheel_2_2", (-0.75, -1.4, 0.3)),
        ]
        
        if self.vehicle_type in ['truck', 'apc']:
            wheel_positions.extend([
                ("wheel_3_1", (0.75, 0, 0.3)),
                ("wheel_3_2", (-0.75, 0, 0.3)),
            ])
        
        damage_positions = [
            ("dmg_zone_engine", (0, 1.4, 0.5)),
            ("dmg_zone_fueltank", (0, -1.4, 0.5)),
            ("dmg_zone_body", (0, 0, 0.7)),
        ]
        
        all_positions = crew_positions[:self.num_crew] + component_positions + wheel_positions + damage_positions
        
        for name, pos in all_positions:
            if name not in bpy.data.objects:
                empty = bpy.data.objects.new(name, None)
                empty.empty_display_type = 'ARROWS'
                empty.empty_display_size = 0.1
                empty.location = pos
                vehicle_collection.objects.link(empty)
                created_empties.append(name)
        
        self.report({'INFO'}, f"Created {len(created_empties)} empty objects")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class ARVEHICLES_OT_create_vertex_group(bpy.types.Operator):
    bl_idname = "arvehicles.create_vertex_group"
    bl_label = "Assign Selection to Bone"
    bl_options = {'REGISTER', 'UNDO'}
    
    def get_bone_items(self, context):
        items = []
        armature = None
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE' and "VehicleArmature" in obj.name:
                armature = obj
                break
        
        if armature:
            for bone in armature.data.bones:
                items.append((bone.name, bone.name, f"Assign to {bone.name} bone"))
        
        if not items:
            items.append(('NO_ARMATURE', "No Vehicle Armature Found", "No vehicle armature found"))
            
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
            self.report({'ERROR'}, "No vehicle armature found")
            return {'CANCELLED'}
        
        if self.bone_name in obj.vertex_groups:
            vgroup = obj.vertex_groups[self.bone_name]
        else:
            vgroup = obj.vertex_groups.new(name=self.bone_name)
        
        if "v_root" in obj.vertex_groups and self.bone_name != "v_root":
            v_root_group = obj.vertex_groups["v_root"]
            obj.vertex_groups.active = v_root_group
            bpy.ops.object.vertex_group_remove_from()
        
        obj.vertex_groups.active = vgroup
        bpy.ops.object.vertex_group_assign()
        
        self.report({'INFO'}, f"Assigned selection to {self.bone_name} vertex group")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)



class ARVEHICLES_OT_cleanup_mesh(bpy.types.Operator):
    bl_idname = "arvehicles.cleanup_mesh"
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
    
    remove_interior: bpy.props.BoolProperty(
        name="Remove Interior Faces", 
        default=False,
        description="Remove faces that are inside the mesh"
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
        
        # Ensure we're in vertex selection mode for all operations
        bpy.ops.mesh.select_mode(type='VERT')
        
        # Select all geometry
        bpy.ops.mesh.select_all(action='SELECT')
        
        # Step 1: Remove duplicate vertices
        bpy.ops.mesh.remove_doubles(threshold=self.merge_threshold)
        
        # Step 2: Delete loose geometry
        bpy.ops.mesh.delete_loose()
        
        # Step 3: Fill holes if enabled
        if self.fill_holes:
            bpy.ops.mesh.fill_holes(sides=0)
        
        # Step 4: Fix non-manifold geometry (simplified)
        if self.fix_non_manifold:
            self._fix_non_manifold_geometry()
        
        # Step 5: Limited dissolve to remove unnecessary edges
        bpy.ops.mesh.select_all(action='SELECT')
        dissolve_angle_rad = math.radians(self.dissolve_angle)
        bpy.ops.mesh.dissolve_limited(angle_limit=dissolve_angle_rad)
        
        # Step 6: Final cleanup
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.normals_make_consistent(inside=False)
        try:
            bpy.ops.mesh.beautify_fill()  # Improve triangle quality
        except:
            pass  # Skip if it fails
        
        bpy.ops.object.mode_set(mode='OBJECT')
    
    def _fix_non_manifold_geometry(self):
        """Fix non-manifold edges and vertices"""
        # Select non-manifold geometry
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.select_non_manifold()
        
        # Try to fix by filling or dissolving
        selected_edges = bpy.context.tool_settings.mesh_select_mode[1]
        if selected_edges:
            # Try to fill non-manifold edges
            bpy.ops.mesh.edge_face_add()
        else:
            # Delete problematic vertices/edges as last resort
            bpy.ops.mesh.delete(type='VERT')
    
    def _remove_interior_faces(self):
        """Remove faces that are completely inside the mesh"""
        # This is a simplified approach - select faces with all normals pointing inward
        bpy.ops.mesh.select_all(action='DESELECT')
        
        # Select faces by normal direction (experimental)
        # This would need more sophisticated geometry analysis
        # For now, just ensure normals are consistent
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.normals_make_consistent(inside=False)
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)





class ARVEHICLES_OT_parent_empties(bpy.types.Operator):
    bl_idname = "arvehicles.parent_empties"
    bl_label = "Parent Empties to Armature"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        armature = None
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE' and "VehicleArmature" in obj.name:
                armature = obj
                break
        
        if not armature:
            self.report({'ERROR'}, "No vehicle armature found")
            return {'CANCELLED'}
        
        non_mesh_objects = [obj for obj in context.selected_objects if obj.type != 'MESH']
        
        if not non_mesh_objects:
            self.report({'ERROR'}, "No non-mesh objects selected")
            return {'CANCELLED'}
        
        bpy.ops.object.select_all(action='DESELECT')
        for obj in non_mesh_objects:
            obj.select_set(True)
        
        armature.select_set(True)
        context.view_layer.objects.active = armature
        bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)
        
        self.report({'INFO'}, f"Parented {len(non_mesh_objects)} empties to armature")
        return {'FINISHED'}

class ARVEHICLES_OT_create_lods(bpy.types.Operator):
    bl_idname = "arvehicles.create_lods"
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
        
        # Get base name from first object or use "Vehicle" as default
        first_obj = mesh_objects[0]
        base_name = first_obj.name.replace("_LOD0", "").split("_")[0] if "_" in first_obj.name else "Vehicle"
        
        # Create collection if requested
        if self.create_collection:
            collection_name = f"{base_name}_LOD_Collection"
            # Check if collection already exists
            if collection_name not in bpy.data.collections:
                new_collection = bpy.data.collections.new(collection_name)
                context.scene.collection.children.link(new_collection)
            else:
                new_collection = bpy.data.collections[collection_name]
        
        # Choose reduction ratios
        if self.aggressive_reduction:
            ratios = [0.3, 0.15, 0.08, 0.06, 0.05]  # More conservative at high LODs to prevent spikes
        else:
            ratios = [0.5, 0.25, 0.125, 0.0625, 0.03125]  # Conservative reduction
        
        created_lods = 0
        all_lod_objects = {i: [] for i in range(1, self.lod_levels + 1)}  # Track objects by LOD level
        
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
                if len(lod_objects) > 1:  # Only join if multiple objects
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
        
        # Select remaining LOD objects (avoid invalid references)
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
class ARVEHICLES_OT_center_vehicle(bpy.types.Operator):
    bl_idname = "arvehicles.center_vehicle"
    bl_label = "Center Vehicle"
    bl_options = {'REGISTER', 'UNDO'}
    
    align_to_y_axis: bpy.props.BoolProperty(name="Align to Y+ Axis", default=True)
    adjust_ground_level: bpy.props.BoolProperty(name="Set Ground Level", default=True)
    
    def execute(self, context):
        if not context.selected_objects:
            self.report({'ERROR'}, "No objects selected")
            return {'CANCELLED'}
        
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not mesh_objects:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}
        
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
        
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        center_z = (min_z + max_z) / 2
        
        offset_x = -center_x
        offset_y = -center_y
        offset_z = -center_z
        
        if self.adjust_ground_level:
            offset_z = -min_z
        
        for obj in mesh_objects:
            obj.location.x += offset_x
            obj.location.y += offset_y
            obj.location.z += offset_z
        
        if self.align_to_y_axis:
            pivot = bpy.data.objects.new("AlignPivot", None)
            context.collection.objects.link(pivot)
            pivot.location = (0, 0, 0)
            
            original_parents = {}
            for obj in mesh_objects:
                original_parents[obj] = obj.parent
                obj.parent = pivot
            
            pivot.rotation_euler = (0, 0, math.radians(90))
            
            bpy.ops.object.select_all(action='DESELECT')
            pivot.select_set(True)
            context.view_layer.objects.active = pivot
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=False)
            
            for obj in mesh_objects:
                obj.parent = original_parents[obj]
            
            bpy.data.objects.remove(pivot)
        
        self.report({'INFO'}, "Vehicle centered and aligned")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class ARVEHICLES_PT_panel(bpy.types.Panel):
    bl_label = "AR Vehicles Enhanced"
    bl_idname = "ARVEHICLES_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'AR Vehicles'
    
    def draw(self, context):
        layout = self.layout
        
        box = layout.box()
        box.label(text="Component Separation", icon='MOD_BUILD')
        box.operator("arvehicles.separate_components", text="Separate Component", icon='UNLINKED')

        
        col = box.column(align=True)
        col.separator()
        col.label(text="Add to Existing Objects:")
        col.operator("arvehicles.add_to_object", text="Add Bone/Socket to Object", icon='EMPTY_ARROWS')
        box = layout.box()
        box.label(text="Collision", icon='MESH_CUBE')
        
        row = box.row(align=True)
        row.operator("arvehicles.create_ucx_collision", text="UCX Physics", icon='MESH_CUBE')
        row.operator("arvehicles.create_firegeo_collision", text="FireGeo", icon='MESH_ICOSPHERE')
        
        row = box.row(align=True)
        row.operator("arvehicles.create_wheel_collisions", text="Wheel Collision", icon='MESH_CYLINDER')
        row.operator("arvehicles.create_center_of_mass", text="Center of Mass", icon='EMPTY_SINGLE_ARROW')
        
        box = layout.box()
        box.label(text="Attachment Points", icon='EMPTY_DATA')
        
        # In the ARVEHICLES_PT_panel class, update this section:
        col = box.column(align=True)
        col.label(text="Create Sockets:")
        
        row = col.row(align=True)


        op = col.operator("arvehicles.create_socket", text="Add Socket")
        op.socket_type = 'custom'
                
        box = layout.box()
        box.label(text="Mesh Tools", icon='EDITMODE_HLT')
        
        row = box.row(align=True)
        row.operator("arvehicles.cleanup_mesh", text="Cleanup Mesh", icon='BRUSH_DATA')
        row.operator("arvehicles.create_lods", text="Create LODs", icon='MOD_DECIM')
        
        box = layout.box()
        box.label(text="Preparation", icon='ORIENTATION_VIEW')
        
        box.operator("arvehicles.center_vehicle", text="Center Vehicle", icon='PIVOT_BOUNDBOX')
        
        box = layout.box()
        box.label(text="Rigging", icon='ARMATURE_DATA')
        
        col = box.column(align=True)
        col.operator("arvehicles.create_armature", text="Create Vehicle Armature", icon='ARMATURE_DATA')
        
        col.separator()
        col.label(text="Add Bones:")
        

        
        col.operator("arvehicles.create_bone", text="Add bone").bone_type = 'custom'
        
        col.separator()
        col.label(text="Skinning:")
        col.operator("arvehicles.setup_skinning", text="Setup Skinning")
        col.operator("arvehicles.create_vertex_group", text="Assign to Bone")
        
        col.separator()
        col.label(text="Parenting:")
        row = col.row(align=True)
        row.operator("arvehicles.parent_to_armature", text="Parent Meshes")
        row.operator("arvehicles.parent_empties", text="Parent Empties")
        
        
        # Add this new section to your ARVEHICLES_PT_panel after the Component Separation box:

        # Replace the preset section in your panel with this:
        
        box = layout.box()
        box.label(text="Two-Phase Preset Manager", icon='PRESET')
        
        col = box.column(align=True)
        col.operator("arvehicles.manage_presets", text="Create/Edit Preset", icon='PLUS')
        
        row = col.row(align=True)
        row.operator("arvehicles.preset_separation", text="Preset Action", icon='LOOP_FORWARDS')
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
    ARVEHICLES_OT_create_ucx_collision,
    ARVEHICLES_OT_create_firegeo_collision,
    ARVEHICLES_OT_create_wheel_collisions,
    ARVEHICLES_OT_create_center_of_mass,
    ARVEHICLES_OT_create_socket,
    ARVEHICLES_OT_manage_presets,
    ARVEHICLES_OT_preset_separation, 
    ARVEHICLES_OT_reset_preset,
    ARVEHICLES_OT_separate_components,
    ARVEHICLES_OT_create_armature,
    ARVEHICLES_OT_create_bone,
    ARVEHICLES_OT_setup_skinning,
    ARVEHICLES_OT_add_to_object, 
    ARVEHICLES_OT_parent_to_armature,
    ARVEHICLES_OT_create_empties,
    ARVEHICLES_OT_create_vertex_group,
    ARVEHICLES_OT_parent_empties,
    ARVEHICLES_OT_create_lods,
    ARVEHICLES_OT_cleanup_mesh,  # Added the cleanup operator
    ARVEHICLES_OT_center_vehicle,
    ARVEHICLES_PT_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
