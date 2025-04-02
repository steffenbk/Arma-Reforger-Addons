# -*- coding: utf-8 -*-
"""
Created on Sat Mar 22 12:30:45 2025

@author: Steffen
"""

bl_info = {
    "name": "Arma Reforger Vehicle Tools",
    "author": "Your Name",
    "version": (1, 1),
    "blender": (2, 93, 0),
    "location": "View3D > Sidebar > AR Vehicles",
    "description": "Tools for preparing and rigging vehicles for Arma Reforger",
    "warning": "",
    "doc_url": "",
    "category": "Object",
}

import bpy
import math
from mathutils import Vector
import bmesh
from mathutils import Vector, Matrix

# Reference VW Golf measurements (as used in Arma Reforger examples)
REFERENCE_VEHICLE = {
    "name": "VW Golf (Reference)",
    "length": 4.282,  # meters
    "width": 1.789,   # meters
    "height": 1.483   # meters
}

# Scale presets for different vehicle types
VEHICLE_SCALES = {
    "your_model": (4.07, 1.8, 1.46),  # Your exact measurements
    "golf_reference": (REFERENCE_VEHICLE["length"], REFERENCE_VEHICLE["width"], REFERENCE_VEHICLE["height"]),
    "sedan": (4.5, 1.8, 1.5),
    "suv": (4.7, 1.9, 1.8),
    "truck": (5.5, 2.0, 2.0),
    "jeep": (4.2, 1.8, 1.8),
    "van": (5.0, 2.0, 2.2),
    "apc": (6.5, 2.5, 2.8),
}
# Default locations for empty objects (in meters)
# These locations are adjusted for your specific vehicle dimensions: 4.07 x 1.8 x 1.46 meters
EMPTY_LOCATIONS = {
    # Crew positions - adjusted for your vehicle height
    "driver": (0.35, 0.2, 0.85),
    "codriver": (-0.35, 0.2, 0.85),
    "cargo01": (0.35, -0.5, 0.85),
    "cargo02": (-0.35, -0.5, 0.85),
    "cargo03": (0.35, -1.0, 0.85),
    "cargo04": (-0.35, -1.0, 0.85),
    
    # Vehicle component points - adjusted for your vehicle dimensions
    "engine": (0, 1.4, 0.5),
    "exhaust": (0.3, -1.7, 0.2),
    "frontlight_left": (0.7, 1.9, 0.5),
    "frontlight_right": (-0.7, 1.9, 0.5),
    "backlight_left": (0.7, -1.9, 0.5),
    "backlight_right": (-0.7, -1.9, 0.5),
    
    # Wheel positions - standard 4-wheel layout
    "wheel_1_1": (0.75, 1.4, 0.3),   # Front right
    "wheel_1_2": (-0.75, 1.4, 0.3),  # Front left
    "wheel_2_1": (0.75, -1.4, 0.3),  # Rear right
    "wheel_2_2": (-0.75, -1.4, 0.3), # Rear left
    
    # Additional wheels for APC/trucks - middle wheels
    "wheel_3_1": (0.75, 0, 0.3),     # Middle right
    "wheel_3_2": (-0.75, 0, 0.3),    # Middle left
    
    # Additional wheels for longer vehicles - second rear axle
    "wheel_4_1": (0.75, -2.0, 0.3),  # Second rear right
    "wheel_4_2": (-0.75, -2.0, 0.3), # Second rear left
    
    # Damage zones - adjusted for your vehicle
    "dmg_zone_engine": (0, 1.4, 0.5),
    "dmg_zone_fueltank": (0, -1.4, 0.5),
    "dmg_zone_body": (0, 0, 0.7),
    "dmg_zone_turret": (0, 0, 1.2),  # For military vehicles with turrets
}
class ARVEHICLES_OT_create_vehicle_socket(bpy.types.Operator):
    """Create a socket empty for vehicle component attachment"""
    bl_idname = "arvehicles.create_socket"
    bl_label = "Create Vehicle Socket"
    bl_options = {'REGISTER', 'UNDO'}
    
    socket_type: bpy.props.EnumProperty(
        name="Socket Type",
        description="Type of vehicle socket to create",
        items=[
            ('window', "Window", "Window socket"),
            ('light', "Light", "Light socket"),
            ('door', "Door", "Door socket"), 
            ('Wheel', "Wheel", "Wheel socket"),
            ('accessory', "Accessory", "Accessory socket"),
            ('other', "Other", "Other socket type"),
        ],
        default='door'
    )
    
    custom_name: bpy.props.StringProperty(
        name="Custom Name",
        description="Custom name for the socket (leave blank for auto-naming)",
        default=""
    )
    
    snap_to_face: bpy.props.BoolProperty(
        name="Snap to Face",
        description="Snap socket to the selected face (if in edit mode)",
        default=True
    )
    
    align_to_normal: bpy.props.BoolProperty(
        name="Align to Normal",
        description="Align socket with the face normal",
        default=True
    )
    
    def execute(self, context):
        # Get the active object (vehicle)
        obj = context.active_object
        
        if not obj:
            self.report({'ERROR'}, "No active object selected")
            return {'CANCELLED'}
        
        # Save current mode to restore it later
        current_mode = context.mode
        
        # Generate socket name
        if self.custom_name:
            socket_name = self.custom_name
        else:
            socket_name = f"VEHICLE_{self.socket_type.upper()}_SOCKET_{len([o for o in bpy.data.objects if f'VEHICLE_{self.socket_type.upper()}_SOCKET' in o.name]) + 1}"
        
        # Create socket empty
        socket = bpy.data.objects.new(socket_name, None)
        socket.empty_display_type = 'ARROWS'
        socket.empty_display_size = 0.1  # Smaller for vehicle parts
        
        # Default location is at the object's location
        socket_location = obj.location.copy()
        socket_rotation = (0, 0, 0)
        
        # If in edit mode, snap to the selected face
        if current_mode == 'EDIT_MESH' and self.snap_to_face:
            mesh = obj.data
            bm = bmesh.from_edit_mesh(mesh)
            selected_faces = [f for f in bm.faces if f.select]
            
            if selected_faces:
                # Get the active face
                active_face = selected_faces[0]
                
                # Calculate face center
                face_center = active_face.calc_center_median()
                socket_location = obj.matrix_world @ face_center
                
                # Align to normal if requested
                if self.align_to_normal:
                    normal = active_face.normal.normalized()
                    
                    # Convert local normal to world space
                    world_normal = obj.matrix_world.to_3x3() @ normal
                    
                    # Create rotation matrix from normal
                    up_vector = Vector((0, 0, 1))
                    
                    if abs(world_normal.dot(up_vector)) > 0.99:
                        # If normal is nearly parallel to up, use X as the rotation axis
                        rot_axis = Vector((1, 0, 0))
                    else:
                        # Otherwise use the cross product
                        rot_axis = world_normal.cross(up_vector).normalized()
                    
                    # Calculate the angle
                    angle = world_normal.angle(up_vector)
                    
                    # Create a rotation matrix
                    rot_mat = Matrix.Rotation(angle, 4, rot_axis)
                    
                    # Convert rotation matrix to euler angles
                    socket_rotation = rot_mat.to_euler()
        
        # Set socket location and rotation
        socket.location = socket_location
        socket.rotation_euler = socket_rotation
        
        # Add the socket to the current collection
        context.collection.objects.link(socket)
        
        # NOTE: We do NOT parent the socket to ensure compatibility with Arma Reforger
        # socket.parent = obj  <-- This line is removed
        
        # Add socket properties
        socket["socket_type"] = self.socket_type
        socket["vehicle_part"] = "attachment_point"
        
        # Switch to Object mode if we're in Edit mode
        if current_mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')
            
        # Now we can safely select objects
        for obj in context.selected_objects:
            obj.select_set(False)
        
        socket.select_set(True)
        context.view_layer.objects.active = socket
        
        # Restore previous mode if needed - but only if the original object supports edit mode
        if current_mode == 'EDIT_MESH':
            # Check if original object is still available and is a mesh
            if obj and obj.type == 'MESH':
                # Set original object as active again
                context.view_layer.objects.active = obj
                bpy.ops.object.mode_set(mode='EDIT')
            # Otherwise, stay in object mode
            else:
                self.report({'WARNING'}, "Couldn't restore edit mode, original object no longer available")
        
        self.report({'INFO'}, f"Created unparented vehicle socket '{socket_name}'")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)    
    
class ARVEHICLES_OT_orient_vehicle(bpy.types.Operator):
    """Orient vehicle along the Y+ axis (Blender) as required by Arma Reforger"""
    bl_idname = "arvehicles.orient_vehicle"
    bl_label = "Orient Vehicle to center"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        if len(context.selected_objects) == 0:
            self.report({'ERROR'}, "Please select the vehicle meshes")
            return {'CANCELLED'}
        
        # Get all selected mesh objects
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not mesh_objects:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}
        
        # Create an empty at the world origin to use as a pivot
        pivot = bpy.data.objects.new("RotationPivot", None)
        context.collection.objects.link(pivot)
        pivot.location = (0, 0, 0)
        
        # Calculate current vehicle dimensions and center
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
        
        # Calculate center of vehicle
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        center_z = (min_z + max_z) / 2
        
        # Store original parents and parenting temporarily
        original_parents = {}
        original_locations = {}
        for obj in mesh_objects:
            original_parents[obj] = obj.parent
            original_locations[obj] = obj.location.copy()
            obj.parent = pivot
        
        # Orient the vehicle to Y+ axis (this assumes vehicle is initially facing along X+ or Z+)
        # You may need to adjust this rotation based on your initial orientation
        pivot.rotation_euler = (0, 0, 0)
        
        # First apply rotation to ensure vehicle faces Y+
        bpy.ops.object.select_all(action='DESELECT')
        pivot.select_set(True)
        context.view_layer.objects.active = pivot
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
        
        # Move pivot to center of vehicle
        pivot.location = (-center_x, -center_y, -center_z)
        
        # Apply location to center the vehicle at world origin
        bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
        
        # Restore original parenting
        for obj in mesh_objects:
            obj.parent = original_parents[obj]
        
        # Remove the temporary pivot
        bpy.data.objects.remove(pivot)
        
        self.report({'INFO'}, "Vehicle oriented along Y+ axis and centered at origin")
        return {'FINISHED'}
    
class ARVEHICLES_OT_scale_vehicle(bpy.types.Operator):
    """Scale vehicle to match Arma Reforger standards or real-world dimensions"""
    bl_idname = "arvehicles.scale_vehicle"
    bl_label = "Scale Vehicle"
    bl_options = {'REGISTER', 'UNDO'}
    
    scale_method: bpy.props.EnumProperty(
        name="Scaling Method",
        description="How to determine the scaling factor",
        items=[
            ('preset', "Preset Dimensions", "Use standard preset dimensions"),
            ('realworld', "Real-world Vehicle", "Scale based on real-world vehicle dimensions"),
            ('custom', "Custom", "Use custom dimensions")
        ],
        default='preset'
    )
    
    vehicle_type: bpy.props.EnumProperty(
        name="Vehicle Type",
        description="Type of vehicle for appropriate scaling",
        items=[
            ('your_model', "Your Model (4.07×1.8×1.46m)", "Use your exact vehicle measurements"),
            ('golf_reference', "VW Golf Reference (4.282×1.789×1.483m)", "Use VW Golf as reference (Arma example)"),
            ('sedan', "Sedan", "Standard sedan car"),
            ('suv', "SUV", "Sport utility vehicle"),
            ('truck', "Truck", "Pickup or larger truck"),
            ('jeep', "Jeep", "Military jeep or similar"),
            ('van', "Van", "Delivery van or similar"),
            ('apc', "APC", "Armored Personnel Carrier"),
        ],
        default='your_model'
    )
    
    # Real-world vehicle dimensions
    realworld_length: bpy.props.FloatProperty(
        name="Real Length",
        description="Real-world vehicle length in meters",
        default=4.5,
        min=1.0,
        max=20.0
    )
    
    realworld_width: bpy.props.FloatProperty(
        name="Real Width",
        description="Real-world vehicle width in meters",
        default=1.8,
        min=0.5,
        max=5.0
    )
    
    realworld_height: bpy.props.FloatProperty(
        name="Real Height",
        description="Real-world vehicle height in meters",
        default=1.5,
        min=0.5,
        max=5.0
    )
    
    custom_length: bpy.props.FloatProperty(
        name="Target Length",
        description="Target vehicle length in meters",
        default=4.07,
        min=1.0,
        max=20.0
    )
    
    custom_width: bpy.props.FloatProperty(
        name="Target Width",
        description="Target vehicle width in meters",
        default=1.8,
        min=0.5,
        max=5.0
    )
    
    custom_height: bpy.props.FloatProperty(
        name="Target Height",
        description="Target vehicle height in meters",
        default=1.46,
        min=0.5,
        max=5.0
    )
    # Option to preserve or adjust proportions
    preserve_proportions: bpy.props.BoolProperty(
        name="Preserve Proportions",
        description="Scale uniformly to fit within target dimensions while preserving original proportions",
        default=True
    )
    
    # Store the current dimensions for UI display
    current_length: bpy.props.FloatProperty(default=0.0)
    current_width: bpy.props.FloatProperty(default=0.0)
    current_height: bpy.props.FloatProperty(default=0.0)
    
    def invoke(self, context, event):
        # Calculate current vehicle dimensions
        if len(context.selected_objects) > 0:
            mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
            if mesh_objects:
                min_x, min_y, min_z, max_x, max_y, max_z = self._get_dimensions(mesh_objects)
                
                self.current_length = max_y - min_y  # Assuming Y is length
                self.current_width = max_x - min_x   # Width is along X
                self.current_height = max_z - min_z  # Height is along Z
        
        return context.window_manager.invoke_props_dialog(self, width=350)
    
    def _get_dimensions(self, mesh_objects):
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
                
        return min_x, min_y, min_z, max_x, max_y, max_z
    def execute(self, context):
        # Check if objects are selected
        if len(context.selected_objects) == 0:
            self.report({'ERROR'}, "Please select the vehicle meshes")
            return {'CANCELLED'}
        
        # Find all mesh objects in selection
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not mesh_objects:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}
        
        # Calculate current vehicle dimensions and center
        min_x, min_y, min_z, max_x, max_y, max_z = self._get_dimensions(mesh_objects)
        
        # Calculate center of vehicle
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        center_z = (min_z + max_z) / 2
        
        # Calculate current dimensions
        current_length = max_y - min_y  # Assuming Y is length axis after orientation
        current_width = max_x - min_x   # Width is along X
        current_height = max_z - min_z  # Height is along Z
        
        # Get target dimensions based on scaling method
        if self.scale_method == 'preset':
            # Use the selected vehicle preset
            vehicle_dims = VEHICLE_SCALES.get(self.vehicle_type, VEHICLE_SCALES['your_model'])
            target_length = vehicle_dims[0]
            target_width = vehicle_dims[1]
            target_height = vehicle_dims[2]
            
        elif self.scale_method == 'realworld':
            # Calculate scaling relative to the reference vehicle (VW Golf)
            # This uses the real-world dimensions provided by the user
            ref_length = REFERENCE_VEHICLE["length"]
            ref_width = REFERENCE_VEHICLE["width"]
            ref_height = REFERENCE_VEHICLE["height"]
            
            # Calculate ratios between real world and reference
            length_ratio = self.realworld_length / ref_length
            width_ratio = self.realworld_width / ref_width
            height_ratio = self.realworld_height / ref_height
            
            # Apply these ratios to determine target dimensions
            target_length = ref_length * length_ratio
            target_width = ref_width * width_ratio
            target_height = ref_height * height_ratio
            
        else:  # custom
            target_length = self.custom_length
            target_width = self.custom_width
            target_height = self.custom_height
        
        # Calculate the scale factors
        length_scale = target_length / current_length if current_length > 0 else 1.0
        width_scale = target_width / current_width if current_width > 0 else 1.0
        height_scale = target_height / current_height if current_height > 0 else 1.0
        
        # If preserving proportions, use the smallest scale to ensure it fits within limits
        if self.preserve_proportions:
            scale_factor = min(length_scale, width_scale, height_scale)
            # Use uniform scaling
            scale_x = scale_y = scale_z = scale_factor
        else:
            # Use non-uniform scaling to match exact dimensions
            scale_x = width_scale
            scale_y = length_scale
            scale_z = height_scale
        
        # Create an empty at the center to use as a scaling pivot
        pivot = bpy.data.objects.new("ScalePivot", None)
        context.collection.objects.link(pivot)
        pivot.location = (center_x, center_y, center_z)
        
        # Parent all mesh objects to the pivot temporarily
        original_parents = {}
        for obj in mesh_objects:
            original_parents[obj] = obj.parent
            obj.parent = pivot
        
        # Scale the pivot, which scales all children around the center
        if self.preserve_proportions:
            pivot.scale = (scale_factor, scale_factor, scale_factor)
        else:
            pivot.scale = (scale_x, scale_y, scale_z)
        
        # Apply the scale to all children
        bpy.ops.object.select_all(action='DESELECT')
        pivot.select_set(True)
        context.view_layer.objects.active = pivot
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        
        # Restore original parenting
        for obj in mesh_objects:
            obj.parent = original_parents[obj]
        
        # Remove the temporary pivot
        bpy.data.objects.remove(pivot)
        
        # Log the dimensions for reference
        if self.preserve_proportions:
            self.report({'INFO'}, 
                f"Vehicle scaled uniformly by factor: {scale_factor:.4f}\n"
                f"Dimensions (L×W×H): {current_length*scale_factor:.2f}m × {current_width*scale_factor:.2f}m × {current_height*scale_factor:.2f}m")
        else:
            self.report({'INFO'}, 
                f"Vehicle scaled non-uniformly (L×W×H): {length_scale:.2f} × {width_scale:.2f} × {height_scale:.2f}\n"
                f"Final dimensions: {current_length*length_scale:.2f}m × {current_width*width_scale:.2f}m × {current_height*height_scale:.2f}m")
        
        return {'FINISHED'}
    
    def draw(self, context):
        layout = self.layout
        
        # Scaling method selection
        layout.prop(self, "scale_method", expand=True)
        
        # Current vehicle dimensions
        if self.current_length > 0:
            box = layout.box()
            box.label(text="Current Dimensions:")
            row = box.row()
            row.label(text=f"Length: {self.current_length:.2f}m")
            row.label(text=f"Width: {self.current_width:.2f}m")
            row.label(text=f"Height: {self.current_height:.2f}m")
        
        # Options based on scaling method
        if self.scale_method == 'preset':
            layout.prop(self, "vehicle_type")
            
            # Show selected preset dimensions
            if self.vehicle_type in VEHICLE_SCALES:
                dims = VEHICLE_SCALES[self.vehicle_type]
                box = layout.box()
                box.label(text="Target Dimensions:")
                row = box.row()
                row.label(text=f"Length: {dims[0]:.2f}m")
                row.label(text=f"Width: {dims[1]:.2f}m")
                row.label(text=f"Height: {dims[2]:.2f}m")
                
        elif self.scale_method == 'realworld':
            box = layout.box()
            box.label(text="Real-world Vehicle Dimensions:")
            box.prop(self, "realworld_length")
            box.prop(self, "realworld_width")
            box.prop(self, "realworld_height")
            
            # Show reference vehicle info
            ref_box = layout.box()
            ref_box.label(text="Reference Vehicle (VW Golf):")
            row = ref_box.row()
            row.label(text=f"L: {REFERENCE_VEHICLE['length']:.2f}m")
            row.label(text=f"W: {REFERENCE_VEHICLE['width']:.2f}m")
            row.label(text=f"H: {REFERENCE_VEHICLE['height']:.2f}m")
            
            # Show calculated target dimensions
            if self.current_length > 0:
                # Calculate scaling ratios
                length_ratio = self.realworld_length / REFERENCE_VEHICLE["length"]
                width_ratio = self.realworld_width / REFERENCE_VEHICLE["width"]
                height_ratio = self.realworld_height / REFERENCE_VEHICLE["height"]
                
                target_box = layout.box()
                target_box.label(text="Calculated Target Dimensions:")
                row = target_box.row()
                row.label(text=f"Length: {REFERENCE_VEHICLE['length'] * length_ratio:.2f}m")
                row.label(text=f"Width: {REFERENCE_VEHICLE['width'] * width_ratio:.2f}m")
                row.label(text=f"Height: {REFERENCE_VEHICLE['height'] * height_ratio:.2f}m")
            
        else:  # custom
            box = layout.box()
            box.label(text="Custom Target Dimensions:")
            box.prop(self, "custom_length")
            box.prop(self, "custom_width")
            box.prop(self, "custom_height")
        
        # Proportional scaling option
        layout.prop(self, "preserve_proportions")

class ARVEHICLES_OT_create_ucx_collision(bpy.types.Operator):
    """Create UCX collision (physics) for the vehicle with optimized face count"""
    bl_idname = "arvehicles.create_ucx_collision"
    bl_label = "Create UCX Collision"
    bl_options = {'REGISTER', 'UNDO'}
    
    target_faces: bpy.props.IntProperty(
        name="Target Faces",
        description="Target number of faces for the collision mesh",
        default=60,
        min=20,
        max=300
    )
    
    padding: bpy.props.FloatProperty(
        name="Padding",
        description="Extra padding around vehicle (in meters)",
        default=0.01,
        min=0.0,
        max=0.1,
        step=0.001
    )
    
    def execute(self, context):
        # Make sure we're in Object mode
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
            
        # Check if objects are selected
        if len(context.selected_objects) == 0:
            self.report({'ERROR'}, "Please select the vehicle meshes")
            return {'CANCELLED'}
        
        # Find all mesh objects in selection
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not mesh_objects:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}
        
        # Create a new object that will become our collision mesh
        collision_mesh = bpy.data.meshes.new("UCX_body_mesh")
        collision_obj = bpy.data.objects.new("UCX_body", collision_mesh)
        context.collection.objects.link(collision_obj)
        
        # Combine all selected meshes into temporary mesh
        temp_mesh = bpy.data.meshes.new("temp_mesh")
        temp_obj = bpy.data.objects.new("temp_obj", temp_mesh)
        context.collection.objects.link(temp_obj)
        
        # Add vertices from all selected objects
        all_verts = []
        for obj in mesh_objects:
            for vert in obj.data.vertices:
                world_co = obj.matrix_world @ vert.co
                all_verts.append(world_co)
        
        # Create the temporary mesh from vertices
        temp_mesh.from_pydata(all_verts, [], [])
        temp_mesh.update()
        
        # Deselect all objects
        for obj in context.selected_objects:
            obj.select_set(False)
            
        # Select the temporary object
        temp_obj.select_set(True)
        context.view_layer.objects.active = temp_obj
        
        # Enter edit mode
        bpy.ops.object.mode_set(mode='EDIT')
        
        # Select all vertices
        bpy.ops.mesh.select_all(action='SELECT')
        
        # Create convex hull
        bpy.ops.mesh.convex_hull()
        
        # Return to object mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Apply decimate modifier to reduce face count
        decimate = temp_obj.modifiers.new(name="Decimate", type='DECIMATE')
        current_faces = len(temp_obj.data.polygons)
        decimate.ratio = min(1.0, self.target_faces / max(1, current_faces))
        bpy.ops.object.modifier_apply(modifier=decimate.name)
        
        # Add padding if needed
        if self.padding > 0:
            # Apply solidify modifier
            solidify = temp_obj.modifiers.new(name="Solidify", type='SOLIDIFY')
            solidify.thickness = self.padding
            solidify.offset = 1.0  # Expand outward
            bpy.ops.object.modifier_apply(modifier=solidify.name)
        
        # Transfer the mesh data to our collision object
        collision_obj.data = temp_obj.data.copy()
        
        # Remove the temporary object
        bpy.data.objects.remove(temp_obj)
        
        # Create and assign material
        if "UCX_Material" not in bpy.data.materials:
            mat = bpy.data.materials.new(name="UCX_Material")
            mat.diffuse_color = (0.1, 0.1, 0.1, 0.7)  # Dark with some transparency
        else:
            mat = bpy.data.materials["UCX_Material"]
        
        # Assign material
        collision_obj.data.materials.append(mat)
        
        # Deselect all objects and select the collision object
        for obj in context.selected_objects:
            obj.select_set(False)
        collision_obj.select_set(True)
        context.view_layer.objects.active = collision_obj
        
        # Set layer_preset custom property
        collision_obj["layer_preset"] = "Collision_Vehicle"
        collision_obj["usage"] = "PhyCol"
        
        # Report number of faces
        self.report({'INFO'}, f"Created UCX collision with {len(collision_obj.data.polygons)} faces")
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class ARVEHICLES_OT_create_firegeo_collision(bpy.types.Operator):
    """Create FireGeo collision (bullet penetration) for the vehicle"""
    bl_idname = "arvehicles.create_firegeo_collision"
    bl_label = "Create FireGeo Collision"
    bl_options = {'REGISTER', 'UNDO'}
    
    method: bpy.props.EnumProperty(
        name="Method",
        description="Method to create FireGeo collision",
        items=[
            ('CONVEX', "Convex Hull (Stable)", "Create a simplified convex hull - stable even with high-poly models"),
            ('DETAILED', "Detailed (Better Shape)", "Create a more detailed shape that better preserves features - may crash with very high-poly models"),
        ],
        default='CONVEX'
    )
    
    # Parameters for Convex Hull method
    max_faces: bpy.props.IntProperty(
        name="Max Faces (Convex)",
        description="Maximum number of faces for convex hull method",
        default=200,
        min=20,
        max=100000
    )
    
    # Parameters for Detailed method
    target_faces: bpy.props.IntProperty(
        name="Target Faces (Detailed)",
        description="Target number of faces for detailed method",
        default=200,
        min=50,
        max=100000
    )
    
    preserve_details: bpy.props.BoolProperty(
        name="Preserve Details",
        description="Maintain important vehicle features (Detailed method only)",
        default=True
    )
    
    # Common parameters
    offset: bpy.props.FloatProperty(
        name="Offset",
        description="Expand the collision mesh outward by this amount (in meters)",
        default=0.01,
        min=0.0,
        max=0.1,
        step=0.01
    )
    
    def execute(self, context):
        # Check if objects are selected
        if len(context.selected_objects) == 0:
            self.report({'ERROR'}, "Please select at least one mesh to use as collision")
            return {'CANCELLED'}
        
        # Find all mesh objects in selection
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not mesh_objects:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}
        
        # Check if we're dealing with a high-poly model and warn the user
        total_faces = sum(len(obj.data.polygons) for obj in mesh_objects)
        if total_faces > 10000 and self.method == 'DETAILED':
            self.report({'WARNING'}, f"High-poly model detected ({total_faces} faces). Detailed method may crash. Consider using Convex Hull method instead.")

        # Create a new empty object to parent the collision mesh to
        collision_parent = bpy.data.objects.new("UTM_vehicle", None)
        context.collection.objects.link(collision_parent)
        
        # Based on the selected method, call the appropriate function
        if self.method == 'CONVEX':
            self._create_convex_hull(context, mesh_objects, collision_parent)
        else:  # DETAILED
            self._create_detailed(context, mesh_objects, collision_parent)
        
        return {'FINISHED'}
    
    def _create_convex_hull(self, context, mesh_objects, collision_parent):
        """Create a convex hull based FireGeo collision"""
        
        # Create a new object that will become our collision mesh
        collision_mesh = bpy.data.meshes.new("UTM_vehicle_mesh_data")
        fire_geo_obj = bpy.data.objects.new("UTM_vehicle_mesh", collision_mesh)
        context.collection.objects.link(fire_geo_obj)
        
        # Get a reduced set of vertices from all objects to create a convex hull
        all_verts = []
        
        for obj in mesh_objects:
            # If too many vertices, sample them to prevent crashes
            if len(obj.data.vertices) > 100:
                sample_rate = min(1.0, 100 / len(obj.data.vertices))
                for i, vert in enumerate(obj.data.vertices):
                    if i % int(1/sample_rate) == 0:  # Sample vertices
                        world_co = obj.matrix_world @ vert.co
                        all_verts.append(world_co)
            else:
                for vert in obj.data.vertices:
                    world_co = obj.matrix_world @ vert.co
                    all_verts.append(world_co)
        
        # If still too many vertices, reduce further
        if len(all_verts) > 1000:
            step = len(all_verts) // 1000
            all_verts = all_verts[::step]
        
        # Create a temporary mesh for the convex hull
        temp_mesh = bpy.data.meshes.new("temp_hull_mesh")
        temp_obj = bpy.data.objects.new("temp_hull", temp_mesh)
        context.collection.objects.link(temp_obj)
        
        # Fill the temporary mesh with our vertices
        temp_mesh.from_pydata(all_verts, [], [])
        temp_mesh.update()
        
        # Make the temp object active
        bpy.ops.object.select_all(action='DESELECT')
        temp_obj.select_set(True)
        context.view_layer.objects.active = temp_obj
        
        # Create convex hull
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.convex_hull()
        
        # Return to object mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Apply decimate to the convex hull if needed
        if len(temp_obj.data.polygons) > self.max_faces:
            decimate = temp_obj.modifiers.new(name="Decimate", type='DECIMATE')
            decimate.ratio = self.max_faces / len(temp_obj.data.polygons)
            bpy.ops.object.modifier_apply(modifier=decimate.name)
        
        # Add offset if needed
        if self.offset > 0:
            # Apply solidify modifier
            solidify = temp_obj.modifiers.new(name="Solidify", type='SOLIDIFY')
            solidify.thickness = self.offset
            solidify.offset = 1.0  # Expand outward only
            bpy.ops.object.modifier_apply(modifier=solidify.name)
        
        # Transfer data to our fire geo object
        fire_geo_obj.data = temp_obj.data.copy()
        
        # Remove the temporary object
        bpy.data.objects.remove(temp_obj)
        
        # Create and assign material
        if "FireGeo_Material" not in bpy.data.materials:
            mat = bpy.data.materials.new(name="FireGeo_Material")
            mat.diffuse_color = (0.0, 0.8, 0.0, 0.5)  # Semi-transparent green
        else:
            mat = bpy.data.materials["FireGeo_Material"]
        
        # Remove any existing materials and assign the new one
        fire_geo_obj.data.materials.clear()
        fire_geo_obj.data.materials.append(mat)
        
        # Parent to the collision parent
        fire_geo_obj.parent = collision_parent
        
        # Set layer_preset custom property
        fire_geo_obj["layer_preset"] = "Collision_Vehicle"
        fire_geo_obj["usage"] = "FireGeo"
        
        # Select our new objects
        bpy.ops.object.select_all(action='DESELECT')
        collision_parent.select_set(True)
        fire_geo_obj.select_set(True)
        context.view_layer.objects.active = fire_geo_obj
        
        # Report success
        self.report({'INFO'}, f"Created FireGeo collision with {len(fire_geo_obj.data.polygons)} faces (Convex Hull method)")
    
    def _create_detailed(self, context, mesh_objects, collision_parent):
        """Create a detailed FireGeo collision that preserves more vehicle features"""
        
        # For each selected mesh, create a collision component
        collision_objects = []
        total_faces = 0
        
        for idx, source_obj in enumerate(mesh_objects):
            # Deselect all objects
            bpy.ops.object.select_all(action='DESELECT')
            
            # Select and make active the source object
            source_obj.select_set(True)
            context.view_layer.objects.active = source_obj
            
            # Duplicate the object
            bpy.ops.object.duplicate()
            dup_obj = context.selected_objects[0]
            
            # Rename the duplicated object
            if len(mesh_objects) == 1:
                dup_obj.name = "UTM_vehicle_mesh"
            else:
                dup_obj.name = f"UTM_vehicle_part_{idx}"
                
            collision_objects.append(dup_obj)
            
            # Simplify mesh based on preserve_details setting
            part_target_faces = int(self.target_faces / len(mesh_objects))
            
            # For more complex vehicle parts, use different simplification strategy
            if self.preserve_details and len(dup_obj.data.polygons) > part_target_faces * 2:
                # Use remesh for better topology preservation
                remesh = dup_obj.modifiers.new(name="Remesh", type='REMESH')
                max_dim = max(dup_obj.dimensions)
                remesh.voxel_size = max_dim * 0.05  # Larger voxel size for vehicles
                bpy.ops.object.modifier_apply(modifier=remesh.name)
            
            # Apply decimate regardless of method
            decimate = dup_obj.modifiers.new(name="Decimate", type='DECIMATE')
            current_faces = len(dup_obj.data.polygons)
            decimate.ratio = min(1.0, part_target_faces / max(1, current_faces))
            bpy.ops.object.modifier_apply(modifier=decimate.name)
            
            # If offset is specified, add a solidify modifier
            if self.offset > 0:
                # Apply solidify modifier
                solidify = dup_obj.modifiers.new(name="Solidify", type='SOLIDIFY')
                solidify.thickness = self.offset
                solidify.offset = 1.0  # Expand outward only
                bpy.ops.object.modifier_apply(modifier=solidify.name)
            
            # Enter edit mode to clean up the mesh
            bpy.ops.object.mode_set(mode='EDIT')
            
            # Select all vertices
            bpy.ops.mesh.select_all(action='SELECT')
            
            # Remove doubles to clean up the mesh
            bpy.ops.mesh.remove_doubles(threshold=0.001)
            
            # Return to object mode
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # Create a material for the collision mesh if it doesn't exist
            if "FireGeo_Material" not in bpy.data.materials:
                mat = bpy.data.materials.new(name="FireGeo_Material")
                mat.diffuse_color = (0.0, 0.8, 0.0, 0.5)  # Semi-transparent green
            else:
                mat = bpy.data.materials["FireGeo_Material"]
            
            # Remove any existing materials and assign the new one
            dup_obj.data.materials.clear()
            dup_obj.data.materials.append(mat)
            
            # Parent to the collision parent
            dup_obj.parent = collision_parent
            
            # Set layer_preset custom property
            dup_obj["layer_preset"] = "Collision_Vehicle"
            dup_obj["usage"] = "FireGeo"
            
            total_faces += len(dup_obj.data.polygons)
        
        # If only one mesh was selected and it's already named appropriately, rename the parent
        if len(collision_objects) == 1:
            collision_parent.name = "UTM_vehicle_parent"
        
        # Select the collision parent and its children
        bpy.ops.object.select_all(action='DESELECT')
        collision_parent.select_set(True)
        for obj in collision_objects:
            obj.select_set(True)
        context.view_layer.objects.active = collision_parent
        
        # Report success
        self.report({'INFO'}, f"Created FireGeo collision with {total_faces} total faces (Detailed method)")
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=350)
    
    def draw(self, context):
        """Custom draw for better UI with method-specific parameters"""
        layout = self.layout
        
        # Count faces in selected objects for warning
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        total_faces = sum(len(obj.data.polygons) for obj in mesh_objects)
        
        # Display warning for high-poly models
        if total_faces > 8000:
            box = layout.box()
            box.label(text=f"High-poly model detected: {total_faces} faces", icon='ERROR')
            box.label(text="'Convex Hull' method recommended for stability")
        
        # Method selection
        layout.prop(self, "method")
        
        # Method-specific parameters
        if self.method == 'CONVEX':
            box = layout.box()
            box.label(text="Convex Hull Parameters:")
            box.prop(self, "max_faces")
        else:  # DETAILED
            box = layout.box()
            box.label(text="Detailed Parameters:")
            box.prop(self, "target_faces")
            box.prop(self, "preserve_details")
            
            if total_faces > 8000:
                box.label(text="Warning: May crash with this model", icon='ERROR')
        
        # Common parameters
        layout.prop(self, "offset")
    
class ARVEHICLES_OT_create_wheel_collisions(bpy.types.Operator):
    """Create wheel collision cylinders for the vehicle"""
    bl_idname = "arvehicles.create_wheel_collisions"
    bl_label = "Create Wheel Collisions"
    bl_options = {'REGISTER', 'UNDO'}
    
    vehicle_type: bpy.props.EnumProperty(
        name="Vehicle Type",
        description="Type of vehicle for appropriate wheel setup",
        items=[
            ('car', "Car (4 wheels)", "Standard car with 4 wheels"),
            ('truck', "Truck (6 wheels)", "Truck with 6 wheels"),
            ('apc', "APC (8 wheels)", "Armored Personnel Carrier with 8 wheels"),
            ('custom', "Custom", "Custom wheel configuration"),
        ],
        default='car'
    )
    
    num_wheels: bpy.props.IntProperty(
        name="Number of Wheels",
        description="Total number of wheels for custom vehicles",
        default=4,
        min=2,
        max=12
    )
    
    wheel_radius: bpy.props.FloatProperty(
        name="Wheel Radius",
        description="Radius of wheel collisions (in meters)",
        default=0.35,
        min=0.1,
        max=1.0
    )
    
    wheel_width: bpy.props.FloatProperty(
        name="Wheel Width",
        description="Width of wheel collisions (in meters)",
        default=0.2,
        min=0.1,
        max=0.5
    )
    
    def execute(self, context):
        # Check if objects are selected to get vehicle dimensions
        if len(context.selected_objects) == 0:
            self.report({'WARNING'}, "No objects selected, using default dimensions")
            # Use default dimensions
            length = 4.0
            width = 1.8
            height = 1.5
            center_x = 0
            center_y = 0
            center_z = 0
        else:
            # Find all mesh objects in selection
            mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
            
            if not mesh_objects:
                self.report({'WARNING'}, "No mesh objects selected, using default dimensions")
                # Use default dimensions
                length = 4.0
                width = 1.8
                height = 1.5
                center_x = 0
                center_y = 0
                center_z = 0
            else:
                # Calculate current vehicle dimensions and center
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
                length = max_y - min_y
                width = max_x - min_x
                height = max_z - min_z
        
        # Determine number of wheels based on vehicle type
        if self.vehicle_type == 'car':
            num_wheels = 4
        elif self.vehicle_type == 'truck':
            num_wheels = 6
        elif self.vehicle_type == 'apc':
            num_wheels = 8
        else:  # custom
            num_wheels = self.num_wheels
        
        # Generate wheel positions
        wheel_positions = self._generate_wheel_positions(num_wheels, length, width, center_x, center_y, center_z)
        
        # Create wheel colliders
        created_wheels = []
        
        for idx, (pos_x, pos_y, pos_z) in enumerate(wheel_positions):
            wheel_name = f"UCS_wheel_{idx+1}"
            wheel_obj = self._create_wheel_cylinder(wheel_name, pos_x, pos_y, pos_z, self.wheel_radius, self.wheel_width)
            created_wheels.append(wheel_obj)
            
            # Set layer_preset custom property
            wheel_obj["layer_preset"] = "Collision_Vehicle"
            wheel_obj["usage"] = "PhyCol"
        
        # Select all created wheels
        bpy.ops.object.select_all(action='DESELECT')
        for wheel in created_wheels:
            wheel.select_set(True)
        
        if created_wheels:
            context.view_layer.objects.active = created_wheels[0]
            self.report({'INFO'}, f"Created {len(created_wheels)} wheel collision objects")
        
        return {'FINISHED'}
    
    def _create_wheel_cylinder(self, name, center_x, center_y, center_z, radius, width):
        """Create a wheel collision cylinder"""
        # Create a cylinder mesh
        bpy.ops.mesh.primitive_cylinder_add(
            radius=radius,
            depth=width,
            enter_editmode=False, 
            align='WORLD', 
            location=(center_x, center_y, center_z),
            rotation=(0, math.pi/2, 0)  # Rotate to align with Y axis
        )
        
        # Get the created object and rename it
        cylinder = bpy.context.active_object
        cylinder.name = name
        
        # Apply rotation
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
        
        # Create material
        if "UCS_Material" not in bpy.data.materials:
            mat = bpy.data.materials.new(name="UCS_Material")
            mat.diffuse_color = (0.8, 0.5, 0.0, 0.5)  # Semi-transparent orange
            
            # Enable transparency
            if hasattr(mat, 'blend_method'):
                mat.blend_method = 'BLEND'
                mat.show_transparent_back = False
        else:
            mat = bpy.data.materials["UCS_Material"]
        
        # Assign material to the object
        if cylinder.data.materials:
            cylinder.data.materials[0] = mat
        else:
            cylinder.data.materials.append(mat)
        
        return cylinder
    
    def _generate_wheel_positions(self, num_wheels, length, width, center_x, center_y, center_z):
        """Generate wheel positions based on the number of wheels and vehicle dimensions"""
        positions = []
        
        # Distance from center to wheels
        front_offset = length * 0.4  # Front axle position
        rear_offset = length * 0.4  # Rear axle position
        side_offset = width * 0.45   # Side offset (left/right)
        wheel_z = center_z + (self.wheel_radius * 0.8)  # Wheel height position
        
        # Front wheels (right, left)
        positions.append((center_x + side_offset, center_y + front_offset, wheel_z))
        positions.append((center_x - side_offset, center_y + front_offset, wheel_z))
        
        # Rear wheels (right, left)
        positions.append((center_x + side_offset, center_y - rear_offset, wheel_z))
        positions.append((center_x - side_offset, center_y - rear_offset, wheel_z))
        
        # If more than 4 wheels, add middle axles
        if num_wheels > 4:
            num_middle_axles = (num_wheels - 4) // 2
            
            # Space the middle axles evenly between front and rear
            axle_spacing = (front_offset + rear_offset) / (num_middle_axles + 1)
            
            for i in range(1, num_middle_axles + 1):
                middle_y = center_y + front_offset - (axle_spacing * i)
                positions.append((center_x + side_offset, middle_y, wheel_z))
                positions.append((center_x - side_offset, middle_y, wheel_z))
        
        return positions
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class ARVEHICLES_OT_create_center_of_mass(bpy.types.Operator):
    """Create center of mass object for the vehicle"""
    bl_idname = "arvehicles.create_center_of_mass"
    bl_label = "Create Center of Mass"
    bl_options = {'REGISTER', 'UNDO'}
    
    com_size: bpy.props.FloatProperty(
        name="COM Size",
        description="Size of the center of mass object (relative to vehicle size)",
        default=0.2,
        min=0.05,
        max=0.5
    )
    
    com_height_offset: bpy.props.FloatProperty(
        name="Height Offset",
        description="Vertical offset for center of mass (negative = lower)",
        default=-0.1,
        min=-0.5,
        max=0.5
    )
    
    def execute(self, context):
        # Calculate vehicle dimensions from selection
        if len(context.selected_objects) == 0:
            self.report({'WARNING'}, "No objects selected, using origin as center")
            center_x, center_y, center_z = 0, 0, 0
            width, length, height = 2.0, 4.0, 1.5
        else:
            # Find all mesh objects in selection
            mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
            
            if not mesh_objects:
                self.report({'WARNING'}, "No mesh objects selected, using origin as center")
                center_x, center_y, center_z = 0, 0, 0
                width, length, height = 2.0, 4.0, 1.5
            else:
                # Calculate current vehicle dimensions and center
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
                width = max_x - min_x
                length = max_y - min_y
                height = max_z - min_z
        
        # Create the center of mass object
        com_obj = self._create_com_box("COM_vehicle", 
                           center_x, center_y, center_z + (height * self.com_height_offset), 
                           width * self.com_size, length * self.com_size, height * self.com_size)
        
        # Set layer_preset custom property
        com_obj["layer_preset"] = "Collision_Vehicle"
        com_obj["usage"] = "CenterOfMass"
        
        # Select the COM object
        bpy.ops.object.select_all(action='DESELECT')
        com_obj.select_set(True)
        context.view_layer.objects.active = com_obj
        
        self.report({'INFO'}, "Created center of mass object")
        return {'FINISHED'}
    
    def _create_com_box(self, name, center_x, center_y, center_z, width, length, height):
        """Create a center of mass box"""
        # Create a cube mesh
        bpy.ops.mesh.primitive_cube_add(
            size=1.0, 
            enter_editmode=False, 
            align='WORLD', 
            location=(center_x, center_y, center_z)
        )
        
        # Get the created object and rename it
        box = bpy.context.active_object
        box.name = name
        
        # Scale to match dimensions
        box.scale.x = width / 2
        box.scale.y = length / 2
        box.scale.z = height / 2
        
        # Apply scale
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        
        # Create material
        if "COM_Material" not in bpy.data.materials:
            mat = bpy.data.materials.new(name="COM_Material")
            mat.diffuse_color = (0.3, 1.0, 0.3, 0.5)  # Semi-transparent green
            
            # Enable transparency
            if hasattr(mat, 'blend_method'):
                mat.blend_method = 'BLEND'
                mat.show_transparent_back = False
        else:
            mat = bpy.data.materials["COM_Material"]
        
        # Assign material to the object
        if box.data.materials:
            box.data.materials[0] = mat
        else:
            box.data.materials.append(mat)
        
        return box
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
class ARVEHICLES_OT_create_vehicle_armature(bpy.types.Operator):
    """Create a basic armature for a vehicle"""
    bl_idname = "arvehicles.create_armature"
    bl_label = "Create Vehicle Armature"
    bl_options = {'REGISTER', 'UNDO'}
    
    vehicle_type: bpy.props.EnumProperty(
        name="Vehicle Type",
        description="Type of vehicle for appropriate armature setup",
        items=[
            ('car', "Car (4 wheels)", "Standard car with 4 wheels"),
            ('truck', "Truck (6 wheels)", "Truck with 6 wheels"),
            ('apc', "APC (8 wheels)", "Armored Personnel Carrier with 8 wheels"),
            ('custom', "Custom", "Custom wheel configuration"),
        ],
        default='car'
    )
    
    num_wheels: bpy.props.IntProperty(
        name="Number of Wheels",
        description="Total number of wheels for custom vehicles",
        default=4,
        min=2,
        max=12
    )
    
    add_doors: bpy.props.BoolProperty(
        name="Add Door Bones",
        description="Add bones for vehicle doors",
        default=True
    )
    
    add_turret: bpy.props.BoolProperty(
        name="Add Turret",
        description="Add bones for a weapon turret (military vehicles)",
        default=False
    )
    
    def execute(self, context):
        # Create an armature
        armature_data = bpy.data.armatures.new("VehicleArmature")
        armature_obj = bpy.data.objects.new("VehicleArmature", armature_data)
        context.collection.objects.link(armature_obj)
        
        # Make the armature active
        context.view_layer.objects.active = armature_obj
        
        # Enter edit mode
        bpy.ops.object.mode_set(mode='EDIT')
        
        # Create root bone - point along Y axis
        root_bone = armature_data.edit_bones.new('v_root')
        root_bone.head = (0, 0, 0)
        root_bone.tail = (0, 0.2, 0)  # Points along Y axis
        root_bone.roll = 0  # Important for correct bone orientation
        
        # Determine number of wheels based on vehicle type
        if self.vehicle_type == 'car':
            num_wheels = 4
        elif self.vehicle_type == 'truck':
            num_wheels = 6
        elif self.vehicle_type == 'apc':
            num_wheels = 8
        else:  # custom
            num_wheels = self.num_wheels
        
        # Create wheel bones - all pointing along Y axis
        wheel_bones = []
        for i in range(num_wheels):
            # Generate wheel position
            x_sign = 1 if i % 2 == 0 else -1  # Right/left side
            y_offset = ((i // 2) / (num_wheels // 2)) - 0.5  # Distribute wheels front to back
            
            bone = armature_data.edit_bones.new(f'v_wheel_{i+1}')
            bone.head = (x_sign * 0.8, y_offset * 3, 0.3)
            bone.tail = (x_sign * 0.8, y_offset * 3 + 0.2, 0.3)  # Add length along Y axis
            bone.roll = 0
            bone.parent = root_bone
            wheel_bones.append(bone)
        
        # Create steering wheel bone - pointing along Y axis
        steer_bone = armature_data.edit_bones.new('v_steeringwheel')
        steer_bone.head = (0, 0.5, 0.9)
        steer_bone.tail = (0, 0.7, 0.9)  # Points along Y axis
        steer_bone.roll = 0
        steer_bone.parent = root_bone
        
        # Create door bones if needed - pointing along Y axis
        if self.add_doors:
            door_left = armature_data.edit_bones.new('v_door_left')
            door_left.head = (0.85, 0.2, 0.8)
            door_left.tail = (0.85, 0.4, 0.8)  # Points along Y axis
            door_left.roll = 0
            door_left.parent = root_bone
            
            door_right = armature_data.edit_bones.new('v_door_right')
            door_right.head = (-0.85, 0.2, 0.8)
            door_right.tail = (-0.85, 0.4, 0.8)  # Points along Y axis
            door_right.roll = 0
            door_right.parent = root_bone
        
        # Create turret bones if needed - horizontal base, gun points along Y
        if self.add_turret:
            turret_base = armature_data.edit_bones.new('v_turret_base')
            turret_base.head = (0, 0, 1.0)
            turret_base.tail = (0, 0.2, 1.0)  # Points along Y axis for rotation
            turret_base.roll = 0
            turret_base.parent = root_bone
            
            turret_gun = armature_data.edit_bones.new('v_turret_gun')
            turret_gun.head = (0, 0.2, 1.0)  # Connect to the tail of turret_base
            turret_gun.tail = (0, 1.0, 1.0)  # Points along Y axis
            turret_gun.roll = 0
            turret_gun.parent = turret_base
        
        # Create body bone for main vehicle body - pointing along Y axis
        body_bone = armature_data.edit_bones.new('v_body')
        body_bone.head = (0, 0, 0.5)
        body_bone.tail = (0, 0.2, 0.5)  # Points along Y axis
        body_bone.roll = 0
        body_bone.parent = root_bone
        
        # Exit edit mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        self.report({'INFO'}, f"Created vehicle armature with {num_wheels} wheel bones" + 
                             (" and door bones" if self.add_doors else "") + 
                             (" and turret" if self.add_turret else ""))
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class ARVEHICLES_OT_create_empties(bpy.types.Operator):
    """Create empty objects for vehicle attachment points and components"""
    bl_idname = "arvehicles.create_empties"
    bl_label = "Create Vehicle Points"
    bl_options = {'REGISTER', 'UNDO'}
    
    # Properties for which empties to create
    create_crew_positions: bpy.props.BoolProperty(
        name="Create Crew Positions",
        description="Create empty objects for driver and passenger positions",
        default=True
    )
    
    create_vehicle_components: bpy.props.BoolProperty(
        name="Create Vehicle Components",
        description="Create empty objects for vehicle components (engine, lights, etc.)",
        default=True
    )
    
    create_wheel_positions: bpy.props.BoolProperty(
        name="Create Wheel Positions",
        description="Create empty objects for wheel positions",
        default=True
    )
    
    create_damage_zones: bpy.props.BoolProperty(
        name="Create Damage Zones",
        description="Create empty objects for damage zones",
        default=True
    )
    
    vehicle_type: bpy.props.EnumProperty(
        name="Vehicle Type",
        description="Type of vehicle for appropriate empty setup",
        items=[
            ('car', "Car (4 wheels)", "Standard car with 4 wheels"),
            ('truck', "Truck (6 wheels)", "Truck with 6 wheels"),
            ('apc', "APC (8 wheels)", "Armored Personnel Carrier with 8 wheels"),
            ('custom', "Custom", "Custom wheel configuration"),
        ],
        default='car'
    )
    
    num_wheels: bpy.props.IntProperty(
        name="Number of Wheels",
        description="Total number of wheels for custom vehicles",
        default=4,
        min=2,
        max=12
    )
    
    num_crew: bpy.props.IntProperty(
        name="Number of Crew",
        description="Total number of crew positions",
        default=4,
        min=1,
        max=12
    )
    
    def execute(self, context):
        # Get or create the parent collection for organization
        vehicle_collection = None
        collection_name = "Vehicle_Components"
        
        if collection_name in bpy.data.collections:
            vehicle_collection = bpy.data.collections[collection_name]
        else:
            vehicle_collection = bpy.data.collections.new(collection_name)
            context.scene.collection.children.link(vehicle_collection)
        
        # Dictionary to track created empties
        created_empties = []
        
        # Determine vehicle dimensions from selection if possible
        dimensions, center = self._get_selected_dimensions(context)
        length, width, height = dimensions
        
        # Determine number of wheels based on vehicle type
        if self.vehicle_type == 'car':
            num_wheels = 4
        elif self.vehicle_type == 'truck':
            num_wheels = 6
        elif self.vehicle_type == 'apc':
            num_wheels = 8
        else:  # custom
            num_wheels = self.num_wheels
        
        # Create empty objects based on selected options
        if self.create_crew_positions:
            crew_positions = self._generate_crew_positions(self.num_crew, dimensions, center)
            
            for i, (name, pos) in enumerate(crew_positions):
                if name not in bpy.data.objects:
                    empty = self._create_empty(name, pos, vehicle_collection, 'ARROWS', 0.2)
                    created_empties.append(name)
        
        if self.create_vehicle_components:
            component_positions = self._generate_component_positions(dimensions, center)
            
            for name, pos in component_positions:
                if name not in bpy.data.objects:
                    empty = self._create_empty(name, pos, vehicle_collection, 'PLAIN_AXES', 0.1)
                    created_empties.append(name)
        
        if self.create_wheel_positions:
            wheel_positions = self._generate_wheel_positions(num_wheels, dimensions, center)
            
            for i, (name, pos) in enumerate(wheel_positions):
                if name not in bpy.data.objects:
                    empty = self._create_empty(name, pos, vehicle_collection, 'SPHERE', 0.1)
                    created_empties.append(name)
        
        if self.create_damage_zones:
            damage_positions = self._generate_damage_zones(dimensions, center, self.vehicle_type)
            
            for name, pos in damage_positions:
                if name not in bpy.data.objects:
                    empty = self._create_empty(name, pos, vehicle_collection, 'CUBE', 0.1)
                    created_empties.append(name)
        
        # NOTE: We do NOT parent empties to the armature to ensure compatibility with Arma Reforger
        # The following code has been removed:
        # armature = None
        # for obj in bpy.data.objects:
        #     if obj.type == 'ARMATURE' and "VehicleArmature" in obj.name:
        #         armature = obj
        #         break
        # 
        # if armature:
        #     for name in created_empties:
        #         if name in bpy.data.objects:
        #             obj = bpy.data.objects[name]
        #             obj.parent = armature
        
        if created_empties:
            self.report({'INFO'}, f"Created {len(created_empties)} unparented empty objects")
        else:
            self.report({'WARNING'}, "No new empties created, they may already exist")
            
        return {'FINISHED'}



class ARVEHICLES_OT_separate_components(bpy.types.Operator):
    """Separate selected components into individual objects for Arma Reforger"""
    bl_idname = "arvehicles.separate_components"
    bl_label = "Separate Vehicle Components"
    bl_options = {'REGISTER', 'UNDO'}
    
    component_type: bpy.props.EnumProperty(
        name="Component Type",
        description="Type of component being separated",
        items=[
            ('window', "Window", "Window component"),
            ('light', "Light", "Emissive light component"),
            ('door', "Door", "Door or movable component"),
            ('Wheel', "Wheel", "Wheel or movable component"),
            ('accessory', "Accessory", "Optional accessory component"),
            ('other', "Other", "Other component type"),
        ],
        default='window'
    )
    
    custom_name: bpy.props.StringProperty(
        name="Custom Name",
        description="Custom name for the separated component",
        default=""
    )
    
    add_socket: bpy.props.BoolProperty(
        name="Add Socket",
        description="Add a socket empty at the component's location",
        default=True
    )
    
    set_origin_to_socket: bpy.props.BoolProperty(
        name="Set Origin to Socket",
        description="Set the object's origin to the same location as the socket",
        default=True
    )
    
    def execute(self, context):
        # Check if we're in edit mode with selected faces
        if context.mode != 'EDIT_MESH':
            self.report({'ERROR'}, "Must be in Edit Mode with faces selected")
            return {'CANCELLED'}
            
        mesh = context.active_object.data
        if not mesh.total_face_sel:
            self.report({'ERROR'}, "No faces selected")
            return {'CANCELLED'}
        
        # Get the active object
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "No active mesh object")
            return {'CANCELLED'}
        
        # Calculate the center of the selected faces
        bm = bmesh.from_edit_mesh(mesh)
        selected_faces = [f for f in bm.faces if f.select]
        
        if not selected_faces:
            self.report({'ERROR'}, "No faces selected")
            return {'CANCELLED'}
        
        # Calculate the center of the selected faces
        center = Vector((0, 0, 0))
        for face in selected_faces:
            center += face.calc_center_median()
        center /= len(selected_faces)
        
        # Transform to world space
        world_center = obj.matrix_world @ center
        
        # Generate a name for the new object
        prefix = ""
        if self.component_type == 'window':
            prefix = "window_"
        elif self.component_type == 'light':
            prefix = "light_"
        elif self.component_type == 'door':
            prefix = "door_"
        elif self.component_type == 'accessory':
            prefix = "acc_"
        elif self.component_type == 'Wheel':
            prefix = "Wheel_"        
            
        new_name = self.custom_name if self.custom_name else f"{prefix}{obj.name}"
        
        # Separate the selected faces
        bpy.ops.mesh.separate(type='SELECTED')
        
        # Exit edit mode to work with the new object
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Get the newly created object (last selected)
        new_obj = context.selected_objects[-1]
        new_obj.name = new_name
        
        # Add component type property
        new_obj["component_type"] = self.component_type
        
        # Create a socket empty if requested
        socket = None
        if self.add_socket:
            socket_name = f"VEHICLE_{self.component_type.upper()}_SOCKET_{len([o for o in bpy.data.objects if f'VEHICLE_{self.component_type.upper()}_SOCKET' in o.name]) + 1}"
            
            socket = bpy.data.objects.new(socket_name, None)
            socket.empty_display_type = 'ARROWS'
            socket.empty_display_size = 0.1
            socket.location = world_center
            
            # Add the socket to the current collection
            context.collection.objects.link(socket)
            
            # Add socket properties
            socket["socket_type"] = self.component_type
            socket["attached_part"] = new_obj.name
            socket["vehicle_part"] = "attachment_point"
        
        # Set origin to socket position if requested
        if self.add_socket and self.set_origin_to_socket:
            # Store the object's world matrix before changing origin
            original_world_matrix = new_obj.matrix_world.copy()
            
            # Select only the new object and make it active
            bpy.ops.object.select_all(action='DESELECT')
            new_obj.select_set(True)
            context.view_layer.objects.active = new_obj
            
            # Set the cursor to the socket's position
            cursor_location = context.scene.cursor.location.copy()
            context.scene.cursor.location = socket.location
            
            # Set the origin to the cursor position
            bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
            
            # Restore cursor position
            context.scene.cursor.location = cursor_location
        
        # Select only the new object
        bpy.ops.object.select_all(action='DESELECT')
        new_obj.select_set(True)
        context.view_layer.objects.active = new_obj
        
        # Build report message
        report_msg = f"Separated component '{new_name}'"
        if self.add_socket:
            report_msg += " with socket"
        if self.set_origin_to_socket and self.add_socket:
            report_msg += ", origin set to socket"
            
        self.report({'INFO'}, report_msg)
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=350)
    
    def draw(self, context):
        layout = self.layout
        
        # Component type and name
        layout.prop(self, "component_type")
        layout.prop(self, "custom_name")
        
        # Socket options
        layout.prop(self, "add_socket")
        
        # Only show set_origin_to_socket option if add_socket is enabled
        if self.add_socket:
            layout.prop(self, "set_origin_to_socket")

class ARVEHICLES_OT_parent_to_armature(bpy.types.Operator):
    """Parent selected meshes to the vehicle armature"""
    bl_idname = "arvehicles.parent_to_armature"
    bl_label = "Parent to Armature"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Find the armature
        armature = None
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE' and "VehicleArmature" in obj.name:
                armature = obj
                break
        
        if not armature:
            self.report({'ERROR'}, "No vehicle armature found. Please create one first.")
            return {'CANCELLED'}
        
        # Get selected mesh objects
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not mesh_objects:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}
        
        # Deselect all objects
        bpy.ops.object.select_all(action='DESELECT')
        
        # Select mesh objects and make armature active
        for obj in mesh_objects:
            obj.select_set(True)
        
        armature.select_set(True)
        context.view_layer.objects.active = armature
        
        # Parent with automatic weights
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')
        
        self.report({'INFO'}, f"Parented {len(mesh_objects)} objects to the vehicle armature")
        return {'FINISHED'}

class ARVEHICLES_OT_setup_export(bpy.types.Operator):
    """Setup FBX export settings for Arma Reforger"""
    bl_idname = "arvehicles.setup_export"
    bl_label = "Setup FBX Export"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Set default export settings
        # These would be reflected in Blender's FBX export dialog
        # We're just displaying tips here
        
        self.report({'INFO'}, "FBX export settings configured")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        
        box = layout.box()
        box.label(text="Arma Reforger FBX Export Settings", icon='EXPORT')
        
        col = box.column(align=True)
        col.label(text="✓ Binary Format")
        col.label(text="✓ Version 2014/2015")
        col.label(text="✓ Include: Empty, Armature, Mesh")
        col.label(text="✓ Include Custom Properties")
        
        col = box.column(align=True)
        col.label(text="✗ Triangulate Faces - OFF")
        col.label(text="✗ Leaf Bones - OFF")
        col.label(text="✗ All Actions - OFF (use specific animations)")
        
        box.label(text="Orient along Y+ axis in Blender!")
        box.label(text="File > Export > FBX (.fbx)")

class ARVEHICLES_PT_panel(bpy.types.Panel):
    """Arma Reforger Vehicles Panel"""
    bl_label = "AR Vehicles"
    bl_idname = "ARVEHICLES_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'AR Vehicles'
    
    def draw(self, context):
        layout = self.layout
        
        # Orientation and Scaling section
        box = layout.box()
        box.label(text="Preparation", icon='AUTO')
        box.operator("arvehicles.orient_vehicle", icon='ORIENTATION_VIEW')
        box.operator("arvehicles.scale_vehicle", icon='FULLSCREEN_ENTER')
        
        # Component Separation
        box = layout.box()
        box.label(text="Component Separation", icon='MOD_BUILD')
        row = box.row(align=True)
        row.operator("arvehicles.separate_components", text="Separate Selection", icon='UNLINKED')
        
        # Collision boxes section
        box = layout.box()
        box.label(text="Collision", icon='MESH_CUBE')
        
        # UCX Collision
        col = box.column(align=True)
        col.operator("arvehicles.create_ucx_collision", icon='CUBE')
        
        # FireGeo Collision
        col = box.column(align=True)
        col.operator("arvehicles.create_firegeo_collision", icon='MESH_GRID')
        
        # Wheel Collisions
        col = box.column(align=True)
        col.operator("arvehicles.create_wheel_collisions", icon='MESH_CYLINDER')
        
        # Center of Mass
        col = box.column(align=True)
        col.operator("arvehicles.create_center_of_mass", icon='SPHERE')
        
        # Layer Presets
        col = box.column(align=True)
        col.operator("arvehicles.setup_layer_presets", icon='PRESET')
        

        # Rigging section
        box = layout.box()
        box.label(text="Rigging", icon='ARMATURE_DATA')
        box.operator("arvehicles.create_armature", icon='BONE_DATA')
        box.operator("arvehicles.parent_to_armature", icon='ARMATURE_DATA')
        box.operator("arvehicles.create_custom_bone", icon='BONE_DATA')
        

        # In your ARVEHICLES_PT_panel draw method, in the "Attachment Points" section:
        box = layout.box()
        box.label(text="Attachment Points", icon='EMPTY_DATA')
        box.operator("arvehicles.create_empties", icon='EMPTY_AXIS')
        # Add this line:
        box.operator("arvehicles.create_socket", icon='EMPTY_ARROWS')
        
        # Export section
        box = layout.box()
        box.label(text="Export", icon='EXPORT')
        box.operator("arvehicles.setup_export", icon='FILEBROWSER')
        

class ARVEHICLES_OT_create_custom_bone(bpy.types.Operator):
    """Add a custom bone to the vehicle armature"""
    bl_idname = "arvehicles.create_custom_bone"
    bl_label = "Add Custom Bone"
    bl_options = {'REGISTER', 'UNDO'}
    
    bone_name: bpy.props.StringProperty(
        name="Bone Name",
        description="Name for the custom bone (v_ prefix will be added automatically if not present)",
        default="custom"
    )
    
    bone_head_x: bpy.props.FloatProperty(
        name="Head X", 
        description="X position of bone head",
        default=0.0
    )
    
    bone_head_y: bpy.props.FloatProperty(
        name="Head Y", 
        description="Y position of bone head",
        default=0.0
    )
    
    bone_head_z: bpy.props.FloatProperty(
        name="Head Z", 
        description="Z position of bone head",
        default=0.5
    )
    
    bone_tail_x: bpy.props.FloatProperty(
        name="Tail X", 
        description="X position of bone tail",
        default=0.0
    )
    
    bone_tail_y: bpy.props.FloatProperty(
        name="Tail Y", 
        description="Y position of bone tail",
        default=0.2
    )
    
    bone_tail_z: bpy.props.FloatProperty(
        name="Tail Z", 
        description="Z position of bone tail",
        default=0.5
    )
    
    def execute(self, context):
        # Find the vehicle armature
        armature = None
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE' and "VehicleArmature" in obj.name:
                armature = obj
                break
        
        if not armature:
            self.report({'ERROR'}, "No vehicle armature found. Please create one first.")
            return {'CANCELLED'}
        
        # Make the armature active
        context.view_layer.objects.active = armature
        
        # Enter edit mode
        bpy.ops.object.mode_set(mode='EDIT')
        
        # Check if v_root exists
        if 'v_root' not in armature.data.edit_bones:
            self.report({'ERROR'}, "v_root bone not found. Please create the armature first.")
            bpy.ops.object.mode_set(mode='OBJECT')
            return {'CANCELLED'}
        
        # Add v_ prefix if not already present
        bone_name = self.bone_name
        if not bone_name.startswith('v_'):
            bone_name = 'v_' + bone_name
        
        # Check if bone already exists and auto-increment if needed
        if bone_name in armature.data.edit_bones:
            base_name = bone_name
            counter = 1
            while bone_name in armature.data.edit_bones:
                bone_name = f"{base_name}_{counter:02d}"
                counter += 1
        
        # Create the custom bone
        bone = armature.data.edit_bones.new(bone_name)
        bone.head = (self.bone_head_x, self.bone_head_y, self.bone_head_z)
        bone.tail = (self.bone_tail_x, self.bone_tail_y, self.bone_tail_z)
        
        # Parent to v_root
        bone.parent = armature.data.edit_bones['v_root']
        
        # Exit edit mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        self.report({'INFO'}, f"Created custom bone '{bone_name}' under v_root")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
        
    def draw(self, context):
        layout = self.layout
        
        box = layout.box()
        box.label(text="Bone Name:")
        box.prop(self, "bone_name", text="")
        
        # Create two columns for head and tail coordinates
        split = layout.split(factor=0.5)
        col1 = split.column()
        col2 = split.column()
        
        col1.label(text="Head Position:")
        col1.prop(self, "bone_head_x")
        col1.prop(self, "bone_head_y")
        col1.prop(self, "bone_head_z")
        
        col2.label(text="Tail Position:")
        col2.prop(self, "bone_tail_x")
        col2.prop(self, "bone_tail_y")
        col2.prop(self, "bone_tail_z")

# List of all classes to register
classes = (
    ARVEHICLES_OT_orient_vehicle,
    ARVEHICLES_OT_scale_vehicle,
    ARVEHICLES_OT_create_ucx_collision,
    ARVEHICLES_OT_create_firegeo_collision,
    ARVEHICLES_OT_create_wheel_collisions,
    ARVEHICLES_OT_create_center_of_mass,
    ARVEHICLES_OT_create_vehicle_armature,
    ARVEHICLES_OT_create_empties,
    ARVEHICLES_OT_separate_components,
    ARVEHICLES_OT_parent_to_armature,
    ARVEHICLES_OT_create_custom_bone,  # Added the custom bone operator
    ARVEHICLES_OT_setup_export,
    ARVEHICLES_PT_panel,
    ARVEHICLES_OT_create_vehicle_socket,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
