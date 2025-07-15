bl_info = {
    "name": "Arma Reforger Weapon Tools",
    "author": "Your Name",
    "version": (1, 3),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > AR Weapons",
    "description": "Tools for scaling and rigging weapons for Arma Reforger - Official Documentation Compliant",
    "warning": "",
    "doc_url": "",
    "category": "Object",
}

import bpy
import math
from mathutils import Vector, Matrix
import bmesh

# Standard dimensions for Arma Reforger weapons
STANDARD_WEAPON_LENGTH = 0.7  # From barrel_muzzle to back of weapon
STANDARD_WEAPON_HEIGHT = 0.25  # From bottom to top
STANDARD_WEAPON_WIDTH = 0.07   # Width of weapon (X axis)
STANDARD_BARREL_HEIGHT = 0.062  # Height of barrel from ground

# Default locations for empty objects - Updated with official Arma Reforger slots
EMPTY_LOCATIONS = {
    # Official weapon attachment slots
    "slot_magazine": (0, 0, -0.06),
    "slot_optics": (0, 0.1, 0.09),
    "slot_barrel_muzzle": (0, 0.35, 0.065),
    "slot_underbarrel": (0, 0.2, -0.03),
    "slot_bayonet": (0, 0.32, 0.065),
    "slot_flashlight": (0.02, 0.25, 0.05),
    
    # Hand IK points
    "snap_hand_right": (0.03, 0, 0.02),
    "snap_hand_left": (-0.03, 0.15, 0.02),
    
    # Simulation points (used by components)
    "eye": (0, 0.1, 0.085),
    "barrel_chamber": (0, -0.1, 0.065),
    "barrel_muzzle": (0, 0.35, 0.065),
    
    # Legacy slot names (for backward compatibility)
    "slot_ironsight_front": (0, 0.3, 0.085),
    "slot_ironsight_rear": (0, 0.15, 0.085),
}

SOCKET_NAMES = {
    "slot_magazine": "slot_magazine",
    "slot_optics": "slot_optics", 
    "slot_barrel_muzzle": "slot_barrel_muzzle",
    "slot_underbarrel": "slot_underbarrel",
    "slot_bayonet": "slot_bayonet",
    "slot_flashlight": "slot_flashlight",
    "eye": "eye",
    "barrel_chamber": "barrel_chamber",
    "barrel_muzzle": "barrel_muzzle"
}

# Socket types for weapons - Updated with official Arma Reforger slots
SOCKET_TYPES = [
    ('slot_magazine', "Magazine Well", "Magazine attachment slot"),
    ('slot_optics', "Optics Mount", "Optics attachment slot (non-standard rail)"),
    ('slot_barrel_muzzle', "Muzzle", "Muzzle attachment slot (suppressors, compensators)"),
    ('slot_underbarrel', "Underbarrel", "Underbarrel attachment slot (UGL, grip)"),
    ('slot_bayonet', "Bayonet Mount", "Bayonet attachment slot"),
    ('slot_flashlight', "Flashlight", "Flashlight attachment slot"),
    ('eye', "Eye (Aiming)", "Aiming down sight point"),
    ('barrel_chamber', "Barrel Chamber", "Barrel chamber position"),
    ('barrel_muzzle', "Barrel Muzzle", "Barrel muzzle direction"),
]

class CREATE_SOCKET_OT_create_socket(bpy.types.Operator):
    """Create a weapon attachment socket at selected face or object location"""
    bl_idname = "object.create_weapon_socket"
    bl_label = "Create Weapon Socket"
    bl_options = {'REGISTER', 'UNDO'}
    
    socket_type: bpy.props.EnumProperty(
        name="Socket Type",
        description="Type of weapon socket to create",
        items=SOCKET_TYPES,
        default='slot_barrel_muzzle'
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
        # Get the active object
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
            socket_name = f"{SOCKET_NAMES[self.socket_type]}_{len([o for o in bpy.data.objects if SOCKET_NAMES[self.socket_type] in o.name]) + 1}"
        
        # Create socket empty
        socket = bpy.data.objects.new(socket_name, None)
        socket.empty_display_type = 'PLAIN_AXES'
        socket.empty_display_size = 0.05  # Smaller size for weapon sockets
        
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
        
        # Add socket properties
        socket["socket_type"] = self.socket_type
        socket["weapon_part"] = "attachment_point"
        
        # Switch to Object mode if we're in Edit mode
        if current_mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')
            
        # Now we can safely select objects
        for obj in context.selected_objects:
            obj.select_set(False)
        
        socket.select_set(True)
        context.view_layer.objects.active = socket
        
        # Restore previous mode if needed
        if current_mode == 'EDIT_MESH':
            if obj and obj.type == 'MESH':
                context.view_layer.objects.active = obj
                bpy.ops.object.mode_set(mode='EDIT')
            else:
                self.report({'WARNING'}, "Couldn't restore edit mode, original object no longer available")
        
        self.report({'INFO'}, f"Created weapon socket '{socket_name}'")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class ARWEAPONS_OT_center_weapon(bpy.types.Operator):
    """Center weapon at origin and align barrel along Y+ axis"""
    bl_idname = "arweapons.center_weapon"
    bl_label = "Center Weapon"
    bl_options = {'REGISTER', 'UNDO'}
    
    align_barrel: bpy.props.BoolProperty(
        name="Align Barrel to Y+",
        description="Rotate weapon so barrel points along Y+ axis",
        default=False
    )
    
    adjust_height: bpy.props.BoolProperty(
        name="Set Standard Barrel Height",
        description="Position weapon at standard barrel height for Arma Reforger",
        default=False
    )
    
    def execute(self, context):
        if len(context.selected_objects) == 0:
            self.report({'ERROR'}, "Please select the weapon meshes")
            return {'CANCELLED'}
        
        # Get all selected mesh objects
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
    """Scale weapon to match Arma Reforger standards or custom dimensions"""
    bl_idname = "arweapons.scale_weapon"
    bl_label = "Scale Weapon"
    bl_options = {'REGISTER', 'UNDO'}
    
    scale_method: bpy.props.EnumProperty(
        name="Scaling Method",
        description="How to determine the scaling factor",
        items=[
            ('standard', "Arma Standard", "Scale to standard Arma Reforger weapon dimensions"),
            ('custom', "Custom Dimensions", "Scale to custom real-world weapon dimensions"),
        ],
        default='standard'
    )
    
    # Custom real-world dimensions (in meters)
    custom_length: bpy.props.FloatProperty(
        name="Real Length (m)",
        description="Real-world weapon length in meters",
        default=0.9,
        min=0.1,
        max=3.0,
        precision=3
    )
    
    custom_height: bpy.props.FloatProperty(
        name="Real Height (m)",
        description="Real-world weapon height in meters",
        default=0.3,
        min=0.05,
        max=1.0,
        precision=3
    )
    
    custom_width: bpy.props.FloatProperty(
        name="Real Width (m)",
        description="Real-world weapon width in meters",
        default=0.1,
        min=0.01,
        max=0.5,
        precision=3
    )
    
    preserve_proportions: bpy.props.BoolProperty(
        name="Preserve Proportions",
        description="Use uniform scaling to preserve the weapon's proportions",
        default=True
    )
    
    center_after_scale: bpy.props.BoolProperty(
        name="Center After Scaling",
        description="Center the weapon at origin after scaling",
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
        
        # Determine target dimensions
        if self.scale_method == 'standard':
            target_length = STANDARD_WEAPON_LENGTH
            target_height = STANDARD_WEAPON_HEIGHT
            target_width = STANDARD_WEAPON_WIDTH
        else:
            target_length = self.custom_length
            target_height = self.custom_height
            target_width = self.custom_width
        
        # Calculate scaling factors
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
        if self.preserve_proportions:
            pivot.scale = (scale_factor, scale_factor, scale_factor)
        else:
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
        if self.preserve_proportions:
            final_length = current_length * scale_factor
            final_height = current_height * scale_factor
            final_width = current_width * scale_factor
        else:
            final_length = current_length * scale_y
            final_height = current_height * scale_z
            final_width = current_width * scale_x
        
        method_msg = "standard Arma dimensions" if self.scale_method == 'standard' else "custom dimensions"
        scale_msg = f"uniform scale of {scale_factor:.4f}" if self.preserve_proportions else \
                   f"non-uniform scale of X:{scale_x:.4f}, Y:{scale_y:.4f}, Z:{scale_z:.4f}"
        center_msg = " and centered at origin" if self.center_after_scale else ""
        
        self.report({'INFO'}, f"Weapon scaled to {method_msg} using {scale_msg}{center_msg}. " + 
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
        else:
            layout.label(text="Custom Real-World Dimensions:")
            layout.prop(self, "custom_length")
            layout.prop(self, "custom_width")
            layout.prop(self, "custom_height")
        
        layout.prop(self, "preserve_proportions")
        layout.prop(self, "center_after_scale")

class ARWEAPONS_OT_create_collision_box(bpy.types.Operator):
    """Create a simplified collision box matching the weapon shape"""
    bl_idname = "arweapons.create_collision_box"
    bl_label = "Create UCX Collision Box"
    bl_options = {'REGISTER', 'UNDO'}
    
    target_faces: bpy.props.IntProperty(
        name="Target Faces",
        description="Target number of faces for the collision mesh",
        default=30,
        min=10,
        max=100
    )
    
    padding: bpy.props.FloatProperty(
        name="Padding",
        description="Extra padding around weapon (in meters)",
        default=0.005,
        min=0.0,
        max=0.05,
        step=0.001
    )
    
    def execute(self, context):
        if len(context.selected_objects) == 0:
            self.report({'ERROR'}, "Please select meshes")
            return {'CANCELLED'}
        
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not mesh_objects:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}
        
        # Create collision object
        collision_mesh = bpy.data.meshes.new("UCX_body_mesh")
        collision_obj = bpy.data.objects.new("UCX_body", collision_mesh)
        context.collection.objects.link(collision_obj)
        
        # Combine vertices from all meshes
        all_verts = []
        for obj in mesh_objects:
            for vert in obj.data.vertices:
                world_co = obj.matrix_world @ vert.co
                all_verts.append(world_co)
        
        # Create temp mesh for convex hull
        temp_mesh = bpy.data.meshes.new("temp_mesh")
        temp_obj = bpy.data.objects.new("temp_obj", temp_mesh)
        context.collection.objects.link(temp_obj)
        temp_mesh.from_pydata(all_verts, [], [])
        temp_mesh.update()
        
        # Create convex hull
        bpy.ops.object.select_all(action='DESELECT')
        temp_obj.select_set(True)
        context.view_layer.objects.active = temp_obj
        
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.convex_hull()
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Simplify mesh
        decimate = temp_obj.modifiers.new(name="Decimate", type='DECIMATE')
        current_faces = len(temp_obj.data.polygons)
        decimate.ratio = min(1.0, self.target_faces / max(1, current_faces))
        bpy.ops.object.modifier_apply(modifier=decimate.name)
        
        # Add padding if needed
        if self.padding > 0:
            solidify = temp_obj.modifiers.new(name="Solidify", type='SOLIDIFY')
            solidify.thickness = self.padding
            solidify.offset = 1.0
            bpy.ops.object.modifier_apply(modifier=solidify.name)
        
        # Transfer to collision object
        collision_obj.data = temp_obj.data.copy()
        bpy.data.objects.remove(temp_obj)
        
        # Create material
        if "UCX_Material" not in bpy.data.materials:
            mat = bpy.data.materials.new(name="UCX_Material")
            mat.diffuse_color = (0.1, 0.1, 0.1, 0.7)
        else:
            mat = bpy.data.materials["UCX_Material"]
        
        collision_obj.data.materials.append(mat)
        
        # Select the collision object
        bpy.ops.object.select_all(action='DESELECT')
        collision_obj.select_set(True)
        context.view_layer.objects.active = collision_obj
        
        self.report({'INFO'}, f"Created UCX collision with {len(collision_obj.data.polygons)} faces")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class ARWEAPONS_OT_create_detailed_collision(bpy.types.Operator):
    """Create FireGeo collision (bullet penetration) for the weapon"""
    bl_idname = "arweapons.create_detailed_collision"
    bl_label = "Create FireGeo Collision"
    bl_options = {'REGISTER', 'UNDO'}
    
    method: bpy.props.EnumProperty(
        name="Method",
        description="Method to create FireGeo collision",
        items=[
            ('CONVEX', "Convex Hull (Stable)", "Create a simplified convex hull"),
            ('DETAILED', "Detailed (Better Shape)", "Create a more detailed shape"),
        ],
        default='DETAILED'
    )
    
    max_faces: bpy.props.IntProperty(
        name="Max Faces (Convex)",
        description="Maximum number of faces for convex hull method",
        default=200,
        min=20,
        max=100000
    )
    
    target_faces: bpy.props.IntProperty(
        name="Target Faces (Detailed)",
        description="Target number of faces for detailed method",
        default=150,
        min=50,
        max=100000
    )
    
    preserve_details: bpy.props.BoolProperty(
        name="Preserve Details",
        description="Maintain important weapon features (Detailed method only)",
        default=True
    )
    
    offset: bpy.props.FloatProperty(
        name="Offset",
        description="Expand the collision mesh outward by this amount (in meters)",
        default=0.007,
        min=0.0,
        max=0.05,
        step=0.001
    )
    
    def execute(self, context):
        if len(context.selected_objects) == 0:
            self.report({'ERROR'}, "Please select at least one mesh to use as collision")
            return {'CANCELLED'}
        
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not mesh_objects:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}
        
        # Check for high-poly models
        total_faces = sum(len(obj.data.polygons) for obj in mesh_objects)
        if total_faces > 10000 and self.method == 'DETAILED':
            self.report({'WARNING'}, f"High-poly model detected ({total_faces} faces). Consider using Convex Hull method.")

        # Create collision parent
        collision_parent = bpy.data.objects.new("UTM_weapon", None)
        context.collection.objects.link(collision_parent)
        
        if self.method == 'CONVEX':
            self._create_convex_hull(context, mesh_objects, collision_parent)
        else:
            self._create_detailed(context, mesh_objects, collision_parent)
        
        return {'FINISHED'}
    
    def _create_convex_hull(self, context, mesh_objects, collision_parent):
        """Create a convex hull based FireGeo collision"""
        
        collision_mesh = bpy.data.meshes.new("UTM_weapon_mesh_data")
        fire_geo_obj = bpy.data.objects.new("UTM_weapon_mesh", collision_mesh)
        context.collection.objects.link(fire_geo_obj)
        
        # Get vertices from all objects
        all_verts = []
        for obj in mesh_objects:
            if len(obj.data.vertices) > 100:
                sample_rate = min(1.0, 100 / len(obj.data.vertices))
                for i, vert in enumerate(obj.data.vertices):
                    if i % int(1/sample_rate) == 0:
                        world_co = obj.matrix_world @ vert.co
                        all_verts.append(world_co)
            else:
                for vert in obj.data.vertices:
                    world_co = obj.matrix_world @ vert.co
                    all_verts.append(world_co)
        
        if len(all_verts) > 1000:
            step = len(all_verts) // 1000
            all_verts = all_verts[::step]
        
        # Create temporary mesh for convex hull
        temp_mesh = bpy.data.meshes.new("temp_hull_mesh")
        temp_obj = bpy.data.objects.new("temp_hull", temp_mesh)
        context.collection.objects.link(temp_obj)
        
        temp_mesh.from_pydata(all_verts, [], [])
        temp_mesh.update()
        
        # Create convex hull
        bpy.ops.object.select_all(action='DESELECT')
        temp_obj.select_set(True)
        context.view_layer.objects.active = temp_obj
        
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.convex_hull()
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Apply decimate if needed
        if len(temp_obj.data.polygons) > self.max_faces:
            decimate = temp_obj.modifiers.new(name="Decimate", type='DECIMATE')
            decimate.ratio = self.max_faces / len(temp_obj.data.polygons)
            bpy.ops.object.modifier_apply(modifier=decimate.name)
        
        # Add offset if needed
        if self.offset > 0:
            solidify = temp_obj.modifiers.new(name="Solidify", type='SOLIDIFY')
            solidify.thickness = self.offset
            solidify.offset = 1.0
            bpy.ops.object.modifier_apply(modifier=solidify.name)
        
        # Transfer data to fire geo object
        fire_geo_obj.data = temp_obj.data.copy()
        bpy.data.objects.remove(temp_obj)
        
        # Create and assign material
        if "FireGeo_Material" not in bpy.data.materials:
            mat = bpy.data.materials.new(name="FireGeo_Material")
            mat.diffuse_color = (0.0, 0.8, 0.0, 0.5)
        else:
            mat = bpy.data.materials["FireGeo_Material"]
        
        fire_geo_obj.data.materials.clear()
        fire_geo_obj.data.materials.append(mat)
        
        # Parent to collision parent
        fire_geo_obj.parent = collision_parent
        
        # Set properties
        fire_geo_obj["layer_preset"] = "Collision_Vehicle"
        fire_geo_obj["usage"] = "FireGeo"
        
        # Select new objects
        bpy.ops.object.select_all(action='DESELECT')
        collision_parent.select_set(True)
        fire_geo_obj.select_set(True)
        context.view_layer.objects.active = fire_geo_obj
        
        self.report({'INFO'}, f"Created FireGeo collision with {len(fire_geo_obj.data.polygons)} faces (Convex Hull method)")
    
    def _create_detailed(self, context, mesh_objects, collision_parent):
        """Create a detailed FireGeo collision"""
        
        collision_objects = []
        total_faces = 0
        
        for idx, source_obj in enumerate(mesh_objects):
            bpy.ops.object.select_all(action='DESELECT')
            source_obj.select_set(True)
            context.view_layer.objects.active = source_obj
            
            # Duplicate the object
            bpy.ops.object.duplicate()
            dup_obj = context.selected_objects[0]
            
            if len(mesh_objects) == 1:
                dup_obj.name = "UTM_weapon_mesh"
            else:
                dup_obj.name = f"UTM_weapon_part_{idx}"
                
            collision_objects.append(dup_obj)
            
            # Simplify mesh
            part_target_faces = int(self.target_faces / len(mesh_objects))
            
            if self.preserve_details and len(dup_obj.data.polygons) > part_target_faces * 2:
                remesh = dup_obj.modifiers.new(name="Remesh", type='REMESH')
                max_dim = max(dup_obj.dimensions)
                remesh.voxel_size = max_dim * 0.03
                bpy.ops.object.modifier_apply(modifier=remesh.name)
            
            # Apply decimate
            decimate = dup_obj.modifiers.new(name="Decimate", type='DECIMATE')
            current_faces = len(dup_obj.data.polygons)
            decimate.ratio = min(1.0, part_target_faces / max(1, current_faces))
            bpy.ops.object.modifier_apply(modifier=decimate.name)
            
            # Add offset if specified
            if self.offset > 0:
                solidify = dup_obj.modifiers.new(name="Solidify", type='SOLIDIFY')
                solidify.thickness = self.offset
                solidify.offset = 1.0
                bpy.ops.object.modifier_apply(modifier=solidify.name)
            
            # Clean up mesh
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.remove_doubles(threshold=0.001)
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # Create material
            if "FireGeo_Material" not in bpy.data.materials:
                mat = bpy.data.materials.new(name="FireGeo_Material")
                mat.diffuse_color = (0.0, 0.8, 0.0, 0.5)
            else:
                mat = bpy.data.materials["FireGeo_Material"]
            
            dup_obj.data.materials.clear()
            dup_obj.data.materials.append(mat)
            
            # Parent and set properties
            dup_obj.parent = collision_parent
            dup_obj["layer_preset"] = "Collision_Vehicle"
            dup_obj["usage"] = "FireGeo"
            
            total_faces += len(dup_obj.data.polygons)
        
        if len(collision_objects) == 1:
            collision_parent.name = "UTM_weapon_parent"
        
        # Select collision objects
        bpy.ops.object.select_all(action='DESELECT')
        collision_parent.select_set(True)
        for obj in collision_objects:
            obj.select_set(True)
        context.view_layer.objects.active = collision_parent
        
        self.report({'INFO'}, f"Created FireGeo collision with {total_faces} total faces (Detailed method)")
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=350)
    
    def draw(self, context):
        layout = self.layout
        
        # Count faces and show warning for high-poly models
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        total_faces = sum(len(obj.data.polygons) for obj in mesh_objects)
        
        if total_faces > 8000:
            box = layout.box()
            box.label(text=f"High-poly model detected: {total_faces} faces", icon='ERROR')
            box.label(text="'Convex Hull' method recommended for stability")
        
        layout.prop(self, "method")
        
        if self.method == 'CONVEX':
            box = layout.box()
            box.label(text="Convex Hull Parameters:")
            box.prop(self, "max_faces")
        else:
            box = layout.box()
            box.label(text="Detailed Parameters:")
            box.prop(self, "target_faces")
            box.prop(self, "preserve_details")
            
            if total_faces > 8000:
                box.label(text="Warning: May crash with this model", icon='ERROR')
        
        layout.prop(self, "offset")

class ARWEAPONS_OT_create_bone(bpy.types.Operator):
    """Add a bone to the weapon rig"""
    bl_idname = "arweapons.create_bone"
    bl_label = "Add Bone"
    bl_options = {'REGISTER', 'UNDO'}
    
    bone_type: bpy.props.EnumProperty(
        name="Bone Type",
        description="Type of bone to add",
        items=[
            ('w_root', "Root Bone", "Main weapon bone"),
            ('w_fire_mode', "Fire Mode", "Fire selector bone"),
            ('w_ch_handle', "Charging Handle", "Charging handle bone (official naming)"),
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
            ('custom', "Custom Bone", "Add a custom bone"),
        ],
        default='w_root'
    )
    
    custom_bone_name: bpy.props.StringProperty(
        name="Bone Name",
        description="Name for the custom bone",
        default="w_custom"
    )
    
    def invoke(self, context, event):
        # For custom bones, always show the dialog
        if self.bone_type == 'custom':
            return context.window_manager.invoke_props_dialog(self, width=300)
        else:
            # For predefined bones, execute directly
            return self.execute(context)
    
    def draw(self, context):
        layout = self.layout
        
        # Only show bone type if it's custom (since predefined bones execute directly)
        if self.bone_type == 'custom':
            layout.prop(self, "bone_type")
            
            box = layout.box()
            box.label(text="Custom Bone Properties:")
            box.prop(self, "custom_bone_name")
    
    def execute(self, context):
        # Find or create armature
        armature = None
        armature_name = "Armature"
        
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                armature = obj
                break
        
        if not armature and self.bone_type == 'w_root':
            armature_data = bpy.data.armatures.new(armature_name)
            armature = bpy.data.objects.new(armature_name, armature_data)
            context.collection.objects.link(armature)
        elif not armature:
            self.report({'ERROR'}, "No armature found. Please create w_root first.")
            return {'CANCELLED'}
        
        context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='EDIT')
        
        bone_length = 0.087
        
        # Determine bone name
        bone_name = self.bone_type
        if self.bone_type == 'custom':
            bone_name = self.custom_bone_name
            
            if bone_name in armature.data.edit_bones:
                base_name = bone_name
                counter = 1
                while bone_name in armature.data.edit_bones:
                    bone_name = f"{base_name}.{counter:03d}"
                    counter += 1
        
        # Check if bone already exists (for non-custom bones)
        elif bone_name in armature.data.edit_bones:
            if bone_name == 'w_root':
                self.report({'INFO'}, "w_root already exists")
                bpy.ops.object.mode_set(mode='OBJECT')
                return {'FINISHED'}
            else:
                self.report({'WARNING'}, f"{bone_name} already exists")
                bpy.ops.object.mode_set(mode='OBJECT')
                return {'CANCELLED'}
        
        # Check for root bone dependency
        if self.bone_type != 'w_root' and 'w_root' not in armature.data.edit_bones:
            self.report({'ERROR'}, "w_root bone not found. Please create it first.")
            bpy.ops.object.mode_set(mode='OBJECT')
            return {'CANCELLED'}
        
        # Get parent bone
        parent_bone = None
        if self.bone_type != 'w_root':
            parent_bone = armature.data.edit_bones['w_root']
        
        # Create bones based on type with official Arma Reforger positioning
        if self.bone_type == 'w_root':
            bone = armature.data.edit_bones.new('w_root')
            bone.head = (0, 0, 0)
            bone.tail = (0, bone_length, 0)
            bone.roll = 0.0
            
        elif self.bone_type == 'w_fire_mode':
            bone = armature.data.edit_bones.new('w_fire_mode')
            bone.head = (-0.001, -0.014, 0.025)
            bone.tail = (-0.001, 0.073, 0.025)
            bone.parent = parent_bone
            
        elif self.bone_type == 'w_ch_handle':  # Official naming
            bone = armature.data.edit_bones.new('w_ch_handle')
            bone.head = (-0.001, -0.086, 0.083)
            bone.tail = (-0.001, 0.001, 0.083)
            bone.parent = parent_bone
            
        elif self.bone_type == 'w_trigger':
            bone = armature.data.edit_bones.new('w_trigger')
            bone.head = (-0.005, 0.019, 0.012)
            bone.tail = (-0.005, 0.106, 0.012)
            bone.parent = parent_bone
            
        elif self.bone_type == 'w_bolt':
            bone = armature.data.edit_bones.new('w_bolt')
            bone.head = (0, -0.166, 0.065)
            bone.tail = (0, -0.079, 0.065)
            bone.parent = parent_bone
            
        elif self.bone_type == 'w_mag_release':
            bone = armature.data.edit_bones.new('w_mag_release')
            bone.head = (0.015, 0.019, 0.012)
            bone.tail = (0.015, 0.106, 0.012)
            bone.parent = parent_bone
            
        elif self.bone_type == 'w_safety':
            bone = armature.data.edit_bones.new('w_safety')
            bone.head = (0.01, -0.01, 0.02)
            bone.tail = (0.01, 0.077, 0.02)
            bone.parent = parent_bone
            
        elif self.bone_type == 'w_buttstock':
            bone = armature.data.edit_bones.new('w_buttstock')
            bone.head = (0, -0.3, 0.05)
            bone.tail = (0, -0.213, 0.05)
            bone.parent = parent_bone
            
        elif self.bone_type == 'w_ejection_port':
            bone = armature.data.edit_bones.new('w_ejection_port')
            bone.head = (0.02, -0.05, 0.065)
            bone.tail = (0.02, 0.037, 0.065)
            bone.parent = parent_bone
            
        elif self.bone_type == 'w_bolt_release':
            bone = armature.data.edit_bones.new('w_bolt_release')
            bone.head = (-0.01, 0.03, 0.03)
            bone.tail = (-0.01, 0.117, 0.03)
            bone.parent = parent_bone
            
        elif self.bone_type == 'w_slide':
            bone = armature.data.edit_bones.new('w_slide')
            bone.head = (0, -0.08, 0.065)
            bone.tail = (0, 0.007, 0.065)
            bone.parent = parent_bone
            
        elif self.bone_type == 'w_hammer':
            bone = armature.data.edit_bones.new('w_hammer')
            bone.head = (0, -0.04, 0.04)
            bone.tail = (0, 0.047, 0.04)
            bone.parent = parent_bone
            
        elif self.bone_type == 'w_striker':
            bone = armature.data.edit_bones.new('w_striker')
            bone.head = (0, -0.05, 0.065)
            bone.tail = (0, 0.037, 0.065)
            bone.parent = parent_bone
            
        elif self.bone_type == 'w_cylinder':
            bone = armature.data.edit_bones.new('w_cylinder')
            bone.head = (0, 0.02, 0.065)
            bone.tail = (0, 0.107, 0.065)
            bone.parent = parent_bone
            
        elif self.bone_type == 'w_rear_sight':
            bone = armature.data.edit_bones.new('w_rear_sight')
            bone.head = (0, 0.15, 0.09)
            bone.tail = (0, 0.237, 0.09)
            bone.parent = parent_bone
            
        elif self.bone_type == 'w_front_sight':
            bone = armature.data.edit_bones.new('w_front_sight')
            bone.head = (0, 0.3, 0.09)
            bone.tail = (0, 0.387, 0.09)
            bone.parent = parent_bone
            
        elif self.bone_type == 'w_barrel':
            bone = armature.data.edit_bones.new('w_barrel')
            bone.head = (0, 0.1, 0.065)
            bone.tail = (0, 0.187, 0.065)
            bone.parent = parent_bone
            
        elif self.bone_type == 'w_bipodleg':
            bone = armature.data.edit_bones.new('w_bipodleg')
            bone.head = (0, 0.2, -0.05)
            bone.tail = (0, 0.287, -0.05)
            bone.parent = parent_bone
            
        elif self.bone_type == 'w_bipodleg_left':
            bone = armature.data.edit_bones.new('w_bipodleg_left')
            bone.head = (-0.03, 0.2, -0.05)
            bone.tail = (-0.03, 0.287, -0.05)
            bone.parent = parent_bone
            
        elif self.bone_type == 'w_bipodleg_right':
            bone = armature.data.edit_bones.new('w_bipodleg_right')
            bone.head = (0.03, 0.2, -0.05)
            bone.tail = (0.03, 0.287, -0.05)
            bone.parent = parent_bone
            
        elif self.bone_type == 'custom':
            bone = armature.data.edit_bones.new(bone_name)
            bone.head = (0, 0, 0)
            bone.tail = (0, bone_length, 0)
            bone.roll = 0.0
            if parent_bone:
                bone.parent = parent_bone
        
        bpy.ops.object.mode_set(mode='OBJECT')
        self.report({'INFO'}, f"Created {bone_name} bone")
        return {'FINISHED'}

class ARWEAPONS_OT_parent_to_armature(bpy.types.Operator):
    """Parent selected non-mesh objects (empties, etc.) to the armature"""
    bl_idname = "arweapons.parent_to_armature"
    bl_label = "Parent Empties to Armature"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Find the armature
        armature = None
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                armature = obj
                break
        
        if not armature:
            self.report({'ERROR'}, "No armature found. Please create bones first.")
            return {'CANCELLED'}
        
        # Get selected NON-MESH objects
        non_mesh_objects = [obj for obj in context.selected_objects if obj.type != 'MESH']
        
        # Filter out mesh objects and warn user
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if mesh_objects:
            mesh_names = [obj.name for obj in mesh_objects[:3]]
            if len(mesh_objects) > 3:
                mesh_names.append(f"and {len(mesh_objects) - 3} more...")
            self.report({'WARNING'}, f"Skipped mesh objects: {', '.join(mesh_names)}. Use 'Setup Skinning' for mesh objects instead.")
        
        if not non_mesh_objects:
            self.report({'ERROR'}, "No non-mesh objects selected. This operator is for empties, curves, etc. Use 'Setup Skinning' for mesh objects.")
            return {'CANCELLED'}
        
        bpy.ops.object.select_all(action='DESELECT')
        
        # Select non-mesh objects and make armature active
        for obj in non_mesh_objects:
            obj.select_set(True)
        
        armature.select_set(True)
        context.view_layer.objects.active = armature
        
        # Parent without automatic weights (simple parenting)
        bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)
        
        self.report({'INFO'}, f"Parented {len(non_mesh_objects)} non-mesh objects to armature")
        return {'FINISHED'}

class ARWEAPONS_OT_create_empties(bpy.types.Operator):
    """Create empty objects for weapon attachment points and components"""
    bl_idname = "arweapons.create_empties"
    bl_label = "Create Attachment Points"
    bl_options = {'REGISTER', 'UNDO'}
    
    create_slots: bpy.props.BoolProperty(
        name="Create Attachment Slots",
        description="Create empty objects for weapon attachment slots",
        default=True
    )
    
    create_snap_points: bpy.props.BoolProperty(
        name="Create Hand IK Points",
        description="Create empty objects for hand IK targets",
        default=True
    )
    
    create_barrel_points: bpy.props.BoolProperty(
        name="Create Barrel Points",
        description="Create empty objects for barrel chamber and muzzle",
        default=True
    )
    
    create_eye_point: bpy.props.BoolProperty(
        name="Create Eye Point",
        description="Create empty object for aiming down sights",
        default=True
    )
    
    def execute(self, context):
        # Get or create collection
        weapon_collection = None
        collection_name = "Weapon_Components"
        
        if collection_name in bpy.data.collections:
            weapon_collection = bpy.data.collections[collection_name]
        else:
            weapon_collection = bpy.data.collections.new(collection_name)
            context.scene.collection.children.link(weapon_collection)
        
        created_empties = []
        
        # Create slots based on official documentation
        if self.create_slots:
            slot_empties = [
                "slot_magazine",
                "slot_optics",
                "slot_barrel_muzzle",
                "slot_underbarrel",
                "slot_bayonet",
                "slot_flashlight",
            ]
            for name in slot_empties:
                if name not in bpy.data.objects:
                    empty = self._create_empty(name, EMPTY_LOCATIONS[name], weapon_collection, 'PLAIN_AXES', 0.03)
                    created_empties.append(name)
        
        if self.create_snap_points:
            snap_empties = [
                "snap_hand_right",
                "snap_hand_left",
            ]
            for name in snap_empties:
                if name not in bpy.data.objects:
                    empty = self._create_empty(name, EMPTY_LOCATIONS[name], weapon_collection, 'PLAIN_AXES', 0.04)
                    created_empties.append(name)
        
        if self.create_barrel_points:
            barrel_empties = [
                "barrel_chamber",
                "barrel_muzzle",
            ]
            for name in barrel_empties:
                if name not in bpy.data.objects:
                    empty = self._create_empty(name, EMPTY_LOCATIONS[name], weapon_collection, 'SPHERE', 0.01)
                    created_empties.append(name)
        
        if self.create_eye_point:
            if "eye" not in bpy.data.objects:
                empty = self._create_empty("eye", EMPTY_LOCATIONS["eye"], weapon_collection, 'CUBE', 0.01)
                created_empties.append("eye")
        
        if created_empties:
            self.report({'INFO'}, f"Created {len(created_empties)} empty objects (unparented)")
        else:
            self.report({'WARNING'}, "No new empties created, they may already exist")
            
        return {'FINISHED'}
    
    def _create_empty(self, name, location, collection, display_type, size):
        """Helper function to create an empty object"""
        empty = bpy.data.objects.new(name, None)
        empty.empty_display_type = display_type
        empty.empty_display_size = size
        empty.location = location
        collection.objects.link(empty)
        return empty
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class ARVEHICLES_OT_separate_components(bpy.types.Operator):
    """Separate selected components and optionally add sockets for Arma Reforger"""
    bl_idname = "arvehicles.separate_components"
    bl_label = "Separate Vehicle Components"
    bl_options = {'REGISTER', 'UNDO'}
    
    component_type: bpy.props.EnumProperty(
        name="Component Type",
        description="Type of component being separated",
        items=[
            ('Sight', "Sight", "Sight component"),
            ('light', "Light", "Emissive light component"),
            ('Trigger', "Trigger", "Trigger or movable component"),
            ('Bolt', "Bolt", "Bolt or movable component"),
            ('Charging_handle', "Charging Handle", "Charging handle component"),
            ('accessory', "Accessory", "Optional accessory component"),
            ('Custom', "Other", "Other component type"),
        ],
        default='Trigger'
    )
    
    custom_name: bpy.props.StringProperty(
        name="Custom Name",
        description="Custom name for the separated component",
        default=""
    )
    
    add_socket: bpy.props.BoolProperty(
        name="Add Socket",
        description="Add a socket empty at the component's location",
        default=False
    )
    
    socket_type: bpy.props.EnumProperty(
        name="Socket Type",
        description="Type of socket for this component",
        items=[
            ('snap_weapon', "Snap Weapon", "Standard attachment snap point"),
            ('slot_magazine', "Slot Magazine", "Magazine well slot"),
            ('slot_optics', "Slot Optics", "Optics mount slot"),
            ('slot_barrel_muzzle', "Slot Barrel Muzzle", "Muzzle slot"),
            ('slot_underbarrel', "Slot Underbarrel", "Underbarrel slot"),
            ('slot_bayonet', "Slot Bayonet", "Bayonet mount slot"),
            ('slot_flashlight', "Slot Flashlight", "Flashlight slot"),
            ('eye', "Eye Point", "Aiming eye point"),
            ('barrel_chamber', "Barrel Chamber", "Barrel chamber point"),
            ('barrel_muzzle', "Barrel Muzzle", "Barrel muzzle point"),
            ('custom', "Custom", "Custom socket name"),
        ],
        default='snap_weapon'
    )
    
    custom_socket_name: bpy.props.StringProperty(
        name="Custom Socket Name",
        description="Custom name for the socket (leave empty for auto-generated name)",
        default=""
    )
    
    set_origin_to_socket: bpy.props.BoolProperty(
        name="Set Origin to Socket",
        description="Set the object's origin to the same location as the socket",
        default=True
    )
    
    add_bone: bpy.props.BoolProperty(
        name="Add Bone",
        description="Add a bone at the component's location",
        default=False
    )
    
    bone_type: bpy.props.EnumProperty(
        name="Bone Type",
        description="Type of bone to create",
        items=[
            ('w_bolt', "Bolt", "Bolt bone"),
            ('w_trigger', "Trigger", "Trigger bone"),
            ('w_fire_mode', "Fire Mode", "Fire mode selector bone"),
            ('w_ch_handle', "Charging Handle", "Charging handle bone"),
            ('w_mag_release', "Mag Release", "Magazine release bone"),
            ('w_safety', "Safety", "Safety lever bone"),
            ('w_slide', "Slide", "Slide bone (pistols)"),
            ('w_hammer', "Hammer", "Hammer bone"),
            ('w_striker', "Striker", "Striker bone"),
            ('custom', "Custom", "Custom bone name"),
        ],
        default='custom'
    )
    
    custom_bone_name: bpy.props.StringProperty(
        name="Custom Bone Name",
        description="Custom name for the bone (leave empty for auto-generated name)",
        default=""
    )
    
    def execute(self, context):
        if context.mode != 'EDIT_MESH':
            self.report({'ERROR'}, "Must be in Edit Mode with faces selected")
            return {'CANCELLED'}
            
        mesh = context.active_object.data
        if not mesh.total_face_sel:
            self.report({'ERROR'}, "No faces selected")
            return {'CANCELLED'}
        
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "No active mesh object")
            return {'CANCELLED'}
        
        # Calculate center of selected faces
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
        
        # Generate name for new object
        prefix = ""
        if self.component_type == 'Sight':
            prefix = "Sight_"
        elif self.component_type == 'light':
            prefix = "light_"
        elif self.component_type == 'Trigger':
            prefix = "Trigger_"
        elif self.component_type == 'accessory':
            prefix = "acc_"
        elif self.component_type == 'Bolt':
            prefix = "Bolt_"
                
        new_name = self.custom_name if self.custom_name else f"{prefix}{obj.name}"
        
        # Separate the selected faces
        bpy.ops.mesh.separate(type='SELECTED')
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Get the newly created object
        new_obj = context.selected_objects[-1]
        new_obj.name = new_name
        new_obj["component_type"] = self.component_type
        
        socket = None
        bone = None
        
        # Create socket if requested
        if self.add_socket:
            if self.custom_socket_name:
                socket_name = self.custom_socket_name
            else:
                socket_name = f"{self.socket_type}_{len([o for o in bpy.data.objects if self.socket_type in o.name]) + 1}"
            
            socket = bpy.data.objects.new(socket_name, None)
            socket.empty_display_type = 'PLAIN_AXES'
            socket.empty_display_size = 0.05
            socket.location = world_center
            
            context.collection.objects.link(socket)
            
            socket["socket_type"] = self.socket_type
            socket["attached_part"] = new_obj.name
            socket["weapon_part"] = "attachment_point"
        
        # Create bone if requested
        if self.add_bone:
            # Find or create armature
            armature = None
            for armature_obj in bpy.data.objects:
                if armature_obj.type == 'ARMATURE':
                    armature = armature_obj
                    break
            
            if not armature:
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
            if self.bone_type == 'custom' and self.custom_bone_name:
                bone_name = self.custom_bone_name
            elif self.bone_type == 'custom':
                bone_name = f"w_{new_name.lower().replace(' ', '_')}"
            else:
                bone_name = f"{self.bone_type}_{len([o for o in bpy.data.objects if self.bone_type in str(o)]) + 1}"
            
            # Create bone
            context.view_layer.objects.active = armature
            bpy.ops.object.mode_set(mode='EDIT')
            
            # Auto-increment if name exists
            original_bone_name = bone_name
            counter = 1
            while bone_name in armature.data.edit_bones:
                bone_name = f"{original_bone_name}.{counter:03d}"
                counter += 1
            
            bone = armature.data.edit_bones.new(bone_name)
            bone.head = (world_center.x, world_center.y, world_center.z)
            bone.tail = (world_center.x, world_center.y + 0.087, world_center.z)
            
            if 'w_root' in armature.data.edit_bones:
                bone.parent = armature.data.edit_bones['w_root']
            
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # Set origin to socket position if requested
        if self.add_socket and self.set_origin_to_socket:
            bpy.ops.object.select_all(action='DESELECT')
            new_obj.select_set(True)
            context.view_layer.objects.active = new_obj
            
            cursor_location = context.scene.cursor.location.copy()
            context.scene.cursor.location = socket.location
            bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
            context.scene.cursor.location = cursor_location
        
        # Select new object
        bpy.ops.object.select_all(action='DESELECT')
        new_obj.select_set(True)
        context.view_layer.objects.active = new_obj
        
        # Build report message
        report_msg = f"Separated component '{new_name}'"
        if self.add_socket:
            report_msg += f" with socket '{socket.name}'"
        if self.add_bone:
            report_msg += f" with bone '{bone_name}'"
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
        
        layout.prop(self, "add_socket")
        
        if self.add_socket:
            layout.prop(self, "socket_type")
            layout.prop(self, "custom_socket_name")
            layout.prop(self, "set_origin_to_socket")
        
        layout.prop(self, "add_bone")
        
        if self.add_bone:
            layout.prop(self, "bone_type")
            if self.bone_type == 'custom':
                layout.prop(self, "custom_bone_name")

class ARWEAPONS_OT_setup_skinning(bpy.types.Operator):
    """Setup skinning for weapon mesh objects"""
    bl_idname = "arweapons.setup_skinning"
    bl_label = "Setup Weapon Skinning"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Find the armature
        armature = None
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                armature = obj
                break
        
        if not armature:
            self.report({'ERROR'}, "No armature found. Please create bones first.")
            return {'CANCELLED'}
        
        # Get selected mesh objects
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not mesh_objects:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}
        
        skinned_objects = 0
        
        for obj in mesh_objects:
            # Check if armature modifier already exists
            armature_mod = None
            for mod in obj.modifiers:
                if mod.type == 'ARMATURE':
                    armature_mod = mod
                    break
            
            # Add armature modifier if it doesn't exist
            if not armature_mod:
                armature_mod = obj.modifiers.new(name="Armature", type='ARMATURE')
                armature_mod.object = armature
            
            # Ensure w_root vertex group exists (all faces must be skinned)
            if "w_root" not in obj.vertex_groups:
                w_root_group = obj.vertex_groups.new(name="w_root")
                
                # Enter edit mode and select all vertices
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                
                # Assign all vertices to w_root with full weight
                obj.vertex_groups.active = w_root_group
                bpy.ops.object.vertex_group_assign()
                
                bpy.ops.object.mode_set(mode='OBJECT')
            
            skinned_objects += 1
        
        self.report({'INFO'}, f"Setup skinning for {skinned_objects} objects")
        return {'FINISHED'}

class ARWEAPONS_OT_create_vertex_group(bpy.types.Operator):
    """Create vertex group for selected faces and assign to bone"""
    bl_idname = "arweapons.create_vertex_group"
    bl_label = "Assign Selection to Bone"
    bl_options = {'REGISTER', 'UNDO'}
    
    def get_bone_items(self, context):
        """Dynamically generate bone list from armature in scene"""
        items = []
        
        # Find the armature in the scene
        armature = None
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                armature = obj
                break
        
        if armature:
            # Add all bones from the armature
            for bone in armature.data.bones:
                items.append((bone.name, bone.name, f"Assign to {bone.name} bone"))
        
        # If no armature found, provide default option
        if not items:
            items.append(('NO_ARMATURE', "No Armature Found", "No armature found in scene"))
            
        return items
    
    bone_name: bpy.props.EnumProperty(
        name="Bone Name",
        description="Name of the bone to create vertex group for",
        items=get_bone_items
    )
    
    def execute(self, context):
        obj = context.active_object
        
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Active object must be a mesh")
            return {'CANCELLED'}
        
        if bpy.context.mode != 'EDIT_MESH':
            self.report({'ERROR'}, "Must be in Edit mode with faces selected")
            return {'CANCELLED'}
        
        # Check if "No Armature" was selected
        if self.bone_name == 'NO_ARMATURE':
            self.report({'ERROR'}, "No armature found in scene")
            return {'CANCELLED'}
        
        # Verify the bone still exists
        armature = None
        for armature_obj in bpy.data.objects:
            if armature_obj.type == 'ARMATURE':
                armature = armature_obj
                break
        
        if not armature or self.bone_name not in armature.data.bones:
            self.report({'ERROR'}, f"Bone '{self.bone_name}' not found in armature")
            return {'CANCELLED'}
        
        # Create or get vertex group
        if self.bone_name in obj.vertex_groups:
            vgroup = obj.vertex_groups[self.bone_name]
        else:
            vgroup = obj.vertex_groups.new(name=self.bone_name)
        
        # Remove selected faces from w_root group first (to avoid double-weighting)
        if "w_root" in obj.vertex_groups and self.bone_name != "w_root":
            w_root_group = obj.vertex_groups["w_root"]
            obj.vertex_groups.active = w_root_group
            bpy.ops.object.vertex_group_remove_from()
        
        # Assign selected faces to the bone's vertex group
        obj.vertex_groups.active = vgroup
        bpy.ops.object.vertex_group_assign()
        
        self.report({'INFO'}, f"Assigned selection to {self.bone_name} vertex group")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "bone_name")

class ARWEAPONS_PT_panel(bpy.types.Panel):
    """Arma Reforger Weapons Panel"""
    bl_label = "AR Weapons"
    bl_idname = "ARWEAPONS_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'AR Weapons'
    
    def draw(self, context):
        layout = self.layout
        
        # Preparation section
        box = layout.box()
        box.label(text="Preparation", icon='ORIENTATION_VIEW')
        
        row = box.row(align=True)
        row.operator("arweapons.center_weapon", text="Center", icon='PIVOT_BOUNDBOX')
        row.operator("arweapons.scale_weapon", text="Scale", icon='FULLSCREEN_ENTER')
        
        # Component Separation section
        box = layout.box()
        box.label(text="Component Separation", icon='MOD_BUILD')
        box.operator("arvehicles.separate_components", text="Separate Component", icon='UNLINKED')
        
        # Collision boxes section
        box = layout.box()
        box.label(text="Collision", icon='MESH_CUBE')
        box.operator("arweapons.create_collision_box")
        box.operator("arweapons.create_detailed_collision")
        
        # Empty Objects section
        box = layout.box()
        box.label(text="Attachment Points", icon='EMPTY_DATA')
        
        # Socket creation - organized like bones
        col = box.column(align=True)
        col.label(text="Create Sockets:")
        
        # Primary weapon sockets
        row = col.row(align=True)
        op = row.operator("object.create_weapon_socket", text="Magazine")
        op.socket_type = 'slot_magazine'
        op = row.operator("object.create_weapon_socket", text="Optics")
        op.socket_type = 'slot_optics'
        
        row = col.row(align=True)
        op = row.operator("object.create_weapon_socket", text="Muzzle")
        op.socket_type = 'slot_barrel_muzzle'
        op = row.operator("object.create_weapon_socket", text="Underbarrel")
        op.socket_type = 'slot_underbarrel'
        
        # Additional sockets
        row = col.row(align=True)
        op = row.operator("object.create_weapon_socket", text="Bayonet")
        op.socket_type = 'slot_bayonet'
        op = row.operator("object.create_weapon_socket", text="Flashlight")
        op.socket_type = 'slot_flashlight'
        
        # Simulation points
        col.separator()
        col.label(text="Simulation Points:")
        
        row = col.row(align=True)
        op = row.operator("object.create_weapon_socket", text="Eye Point")
        op.socket_type = 'eye'
        op = row.operator("object.create_weapon_socket", text="Custom")
        # Custom will use the dialog as normal
        
        row = col.row(align=True)
        op = row.operator("object.create_weapon_socket", text="Chamber")
        op.socket_type = 'barrel_chamber'
        op = row.operator("object.create_weapon_socket", text="Muzzle Point")
        op.socket_type = 'barrel_muzzle'
        
        # Legacy empty creation
        col.separator()
        box.operator("arweapons.create_empties", text="Create All Attachment Points")
        
        # Rigging section
        box = layout.box()
        box.label(text="Rigging", icon='ARMATURE_DATA')
        
        # Bone creation
        col = box.column(align=True)
        col.label(text="Add Bones:")
        
        # Root bone first
        col.operator("arweapons.create_bone", text="Add w_root").bone_type = 'w_root'
        
        # Primary action bones
        row = col.row(align=True)
        row.operator("arweapons.create_bone", text="Trigger").bone_type = 'w_trigger'
        row.operator("arweapons.create_bone", text="Fire Mode").bone_type = 'w_fire_mode'
        
        row = col.row(align=True)
        row.operator("arweapons.create_bone", text="Bolt").bone_type = 'w_bolt'
        row.operator("arweapons.create_bone", text="Charging").bone_type = 'w_ch_handle'
        
        # Release/control bones
        row = col.row(align=True)
        row.operator("arweapons.create_bone", text="Mag Release").bone_type = 'w_mag_release'
        row.operator("arweapons.create_bone", text="Safety").bone_type = 'w_safety'
        
        # Sight bones
        row = col.row(align=True)
        row.operator("arweapons.create_bone", text="Front Sight").bone_type = 'w_front_sight'
        row.operator("arweapons.create_bone", text="Rear Sight").bone_type = 'w_rear_sight'
        
        # Additional bones
        col.separator()
        col.label(text="Additional Bones:")
        
        row = col.row(align=True)
        row.operator("arweapons.create_bone", text="Slide").bone_type = 'w_slide'
        row.operator("arweapons.create_bone", text="Hammer").bone_type = 'w_hammer'
        
        row = col.row(align=True)
        row.operator("arweapons.create_bone", text="Buttstock").bone_type = 'w_buttstock'
        row.operator("arweapons.create_bone", text="Barrel").bone_type = 'w_barrel'
        
        col.operator("arweapons.create_bone", text="Custom").bone_type = 'custom'
        
        # Skinning
        col.separator()
        col.label(text="Skinning:")
        col.operator("arweapons.setup_skinning", text="Setup Skinning")
        col.operator("arweapons.create_vertex_group", text="Assign to Bone")
        
        # Parenting (kept for non-mesh objects)
        col.separator()
        col.operator("arweapons.parent_to_armature", text="Parent Empties")

# Registration
classes = (
    ARWEAPONS_OT_center_weapon,
    ARWEAPONS_OT_scale_weapon,
    ARWEAPONS_OT_create_collision_box,
    ARWEAPONS_OT_create_detailed_collision,
    ARWEAPONS_OT_create_bone,
    ARWEAPONS_OT_parent_to_armature,
    ARWEAPONS_OT_create_empties,
    ARWEAPONS_OT_setup_skinning,
    ARWEAPONS_OT_create_vertex_group,
    ARWEAPONS_PT_panel,
    ARVEHICLES_OT_separate_components,
    CREATE_SOCKET_OT_create_socket,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
