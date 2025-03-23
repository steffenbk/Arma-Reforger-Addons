bl_info = {
    "name": "Arma Reforger Weapon Tools",
    "author": "Your Name",
    "version": (1, 2),
    "blender": (2, 93, 0),
    "location": "View3D > Sidebar > AR Weapons",
    "description": "Tools for scaling and rigging weapons for Arma Reforger",
    "warning": "",
    "doc_url": "",
    "category": "Object",
}

import bpy
import math
from mathutils import Vector

# Standard dimensions for Arma Reforger weapons
STANDARD_WEAPON_LENGTH = 0.7  # From barrel_muzzle to back of weapon
STANDARD_WEAPON_HEIGHT = 0.25  # From bottom to top
STANDARD_WEAPON_WIDTH = 0.07   # Width of weapon (X axis)
STANDARD_BARREL_HEIGHT = 0.062  # Height of barrel from ground

# Default locations for empty objects
EMPTY_LOCATIONS = {
    "slot_ironsight_front": (0, 0.3, 0.085),
    "slot_ironsight_rear": (0, 0.15, 0.085),
    "slot_magazine": (0, 0, -0.06),
    "slot_optics": (0, 0.1, 0.09),
    "slot_underbarrel": (0, 0.2, -0.03),
    "snap_hand_right": (0.03, 0, 0.02),
    "snap_hand_left": (-0.03, 0.15, 0.02),
    "barrel_chamber": (0, -0.1, 0.065),
    "barrel_muzzle": (0, 0.35, 0.065),
    "eye": (0, 0.1, 0.085),
}

class ARWEAPONS_OT_center_weapon(bpy.types.Operator):
    """Center weapon at origin and align barrel along Y+ axis"""
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
        
        # Get all selected mesh objects
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not mesh_objects:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}
        
        # Create an empty at the world origin to use as a pivot
        pivot = bpy.data.objects.new("CenterPivot", None)
        context.collection.objects.link(pivot)
        pivot.location = (0, 0, 0)
        
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
        
        # Store original parents
        original_parents = {}
        for obj in mesh_objects:
            original_parents[obj] = obj.parent
            obj.parent = pivot
        
        # Align the weapon if requested
        if self.align_barrel:
            # Orient the weapon to Y+ axis (barrel pointing along Y+)
            # This assumes the weapon is already mostly aligned with major axes
            pivot.rotation_euler = (0, 0, 0)
            
            # Apply rotation to ensure weapon faces Y+
            bpy.ops.object.select_all(action='DESELECT')
            pivot.select_set(True)
            context.view_layer.objects.active = pivot
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
        
        # Move pivot to center of weapon
        pivot.location = (-center_x, -center_y, -center_z)
        
        # Apply location to center the weapon at world origin
        bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
        
        # Additionally ensure barrel alignment if requested
        if self.adjust_height:
            # Adjust for standard weapon position - barrel at STANDARD_BARREL_HEIGHT
            height_adjustment = STANDARD_BARREL_HEIGHT - center_z
            
            for obj in mesh_objects:
                obj.location.z += height_adjustment
        
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
    
    # Automatic centering
    center_after_scale: bpy.props.BoolProperty(
        name="Center After Scaling",
        description="Center the weapon at origin after scaling",
        default=True
    )
    
    def execute(self, context):
        # Check if objects are selected
        if len(context.selected_objects) == 0:
            self.report({'ERROR'}, "Please select the weapon meshes")
            return {'CANCELLED'}
        
        # Find all mesh objects in selection
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
        
        # Calculate current dimensions
        current_length = max_y - min_y  # Assuming Y is length axis
        current_height = max_z - min_z  # Assuming Z is height axis
        current_width = max_x - min_x   # Assuming X is width axis
        
        # Determine target dimensions based on scaling method
        if self.scale_method == 'standard':
            target_length = STANDARD_WEAPON_LENGTH
            target_height = STANDARD_WEAPON_HEIGHT
            target_width = STANDARD_WEAPON_WIDTH
        else:  # custom
            target_length = self.custom_length
            target_height = self.custom_height
            target_width = self.custom_width
        
        # Calculate scaling factors
        length_scale = target_length / current_length if current_length > 0 else 1.0
        height_scale = target_height / current_height if current_height > 0 else 1.0
        width_scale = target_width / current_width if current_width > 0 else 1.0
        
        # Determine final scale factors
        if self.preserve_proportions:
            # Use the smallest scale to ensure weapon fits within all target dimensions
            scale_factor = min(length_scale, height_scale, width_scale)
            scale_x = scale_y = scale_z = scale_factor
        else:
            # Non-uniform scaling
            scale_x = width_scale
            scale_y = length_scale
            scale_z = height_scale
        
        # Create an empty at the center to use as a scaling pivot
        pivot = bpy.data.objects.new("ScalePivot", None)
        context.collection.objects.link(pivot)
        pivot.location = (center_x, center_y, center_z)
        
        # Parent all mesh objects to the pivot temporarily
        original_parents = {}
        original_locations = {}
        for obj in mesh_objects:
            original_parents[obj] = obj.parent
            original_locations[obj] = obj.location.copy()
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
        
        # Center the weapon if requested
        if self.center_after_scale:
            # Apply location to center at origin
            pivot.location = (0, 0, 0)
            bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
        
        # Restore original parenting
        for obj in mesh_objects:
            obj.parent = original_parents[obj]
        
        # Remove the temporary pivot
        bpy.data.objects.remove(pivot)
        
        # Calculate final dimensions for reporting
        if self.preserve_proportions:
            final_length = current_length * scale_factor
            final_height = current_height * scale_factor
            final_width = current_width * scale_factor
        else:
            final_length = current_length * scale_y
            final_height = current_height * scale_z
            final_width = current_width * scale_x
        
        # Prepare report message
        if self.scale_method == 'standard':
            method_msg = "standard Arma dimensions"
        else:
            method_msg = "custom dimensions"
            
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
        
        # Scaling method selection
        layout.prop(self, "scale_method")
        
        # Options based on selected method
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
        
        # Common options
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
        
        # Create a new object for collision
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
        
        # Select and make active
        bpy.ops.object.select_all(action='DESELECT')
        temp_obj.select_set(True)
        context.view_layer.objects.active = temp_obj
        
        # Create convex hull
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
        
        # Remove temp object
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
    """Create FireGeo collision mesh from selected weapon meshes"""
    bl_idname = "arweapons.create_detailed_collision"
    bl_label = "Create FireGeo Collision"
    bl_options = {'REGISTER', 'UNDO'}
    
    target_faces: bpy.props.IntProperty(
        name="Target Faces",
        description="Target number of faces for the collision mesh",
        default=150,
        min=50,
        max=500
    )
    
    preserve_details: bpy.props.BoolProperty(
        name="Preserve Details",
        description="Maintain important features at the cost of more faces",
        default=True
    )
    
    def execute(self, context):
        if len(context.selected_objects) == 0:
            self.report({'ERROR'}, "Please select meshes")
            return {'CANCELLED'}
        
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not mesh_objects:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}
        
        # Create parent empty
        collision_parent = bpy.data.objects.new("UTM_weapon", None)
        context.collection.objects.link(collision_parent)
        
        collision_objects = []
        total_faces = 0
        
        for idx, source_obj in enumerate(mesh_objects):
            # Duplicate object
            bpy.ops.object.select_all(action='DESELECT')
            source_obj.select_set(True)
            context.view_layer.objects.active = source_obj
            bpy.ops.object.duplicate_move()
            dup_obj = context.selected_objects[0]
            
            # Rename
            if len(mesh_objects) == 1:
                dup_obj.name = "UTM_weapon_mesh"
            else:
                dup_obj.name = f"UTM_weapon_part_{idx}"
                
            collision_objects.append(dup_obj)
            
            # Simplify based on preserve_details setting
            part_target_faces = int(self.target_faces / len(mesh_objects))
            
            if self.preserve_details and len(dup_obj.data.polygons) > part_target_faces * 2:
                # Use remesh for better topology preservation
                remesh = dup_obj.modifiers.new(name="Remesh", type='REMESH')
                max_dim = max(dup_obj.dimensions)
                remesh.voxel_size = max_dim * 0.03
                bpy.ops.object.modifier_apply(modifier=remesh.name)
            
            # Apply decimate regardless of method
            decimate = dup_obj.modifiers.new(name="Decimate", type='DECIMATE')
            current_faces = len(dup_obj.data.polygons)
            decimate.ratio = min(1.0, part_target_faces / max(1, current_faces))
            bpy.ops.object.modifier_apply(modifier=decimate.name)
            
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
            
            # Parent to collision parent
            dup_obj.parent = collision_parent
            
            total_faces += len(dup_obj.data.polygons)
        
        # Rename parent if only one object
        if len(collision_objects) == 1:
            collision_parent.name = "UTM_weapon_parent"
        
        # Select all
        bpy.ops.object.select_all(action='DESELECT')
        collision_parent.select_set(True)
        for obj in collision_objects:
            obj.select_set(True)
        context.view_layer.objects.active = collision_parent
        
        self.report({'INFO'}, f"Created FireGeo collision with {total_faces} faces")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

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
            ('w_charging_handle', "Charging Handle", "Charging handle bone"),
            ('w_trigger', "Trigger", "Trigger bone"),
            ('w_bolt', "Bolt", "Bolt/slide bone"),
        ],
        default='w_root'
    )
    
    def execute(self, context):
        # Find or create the armature
        armature = None
        armature_name = "Armature"
        
        # Check if armature already exists
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                armature = obj
                break
        
        # If no armature exists, create one
        if not armature and self.bone_type == 'w_root':
            armature_data = bpy.data.armatures.new(armature_name)
            armature = bpy.data.objects.new(armature_name, armature_data)
            context.collection.objects.link(armature)
        elif not armature:
            self.report({'ERROR'}, "No armature found. Please create w_root first.")
            return {'CANCELLED'}
        
        # Make the armature active
        context.view_layer.objects.active = armature
        
        # Enter edit mode
        bpy.ops.object.mode_set(mode='EDIT')
        
        # Standard bone length
        bone_length = 0.087
        
        # Check if the bone already exists
        if self.bone_type in armature.data.edit_bones:
            # If w_root already exists, just report and return success
            if self.bone_type == 'w_root':
                self.report({'INFO'}, "w_root already exists")
                bpy.ops.object.mode_set(mode='OBJECT')
                return {'FINISHED'}
            else:
                self.report({'WARNING'}, f"{self.bone_type} already exists")
                bpy.ops.object.mode_set(mode='OBJECT')
                return {'CANCELLED'}
        
        # For non-root bones, check if root exists
        if self.bone_type != 'w_root' and 'w_root' not in armature.data.edit_bones:
            self.report({'ERROR'}, "w_root bone not found. Please create it first.")
            bpy.ops.object.mode_set(mode='OBJECT')
            return {'CANCELLED'}
        
        # Get parent bone for non-root bones
        parent_bone = None
        if self.bone_type != 'w_root':
            parent_bone = armature.data.edit_bones['w_root']
        
        # Create the appropriate bone based on type
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
            
        elif self.bone_type == 'w_charging_handle':
            bone = armature.data.edit_bones.new('w_charging_handle')
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
        
        # Exit edit mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        self.report({'INFO'}, f"Created {self.bone_type} bone")
        return {'FINISHED'}

class ARWEAPONS_OT_parent_to_armature(bpy.types.Operator):
    """Parent selected meshes to the armature"""
    bl_idname = "arweapons.parent_to_armature"
    bl_label = "Parent to Armature"
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
        
        # Deselect all objects
        bpy.ops.object.select_all(action='DESELECT')
        
        # Select mesh objects and make armature active
        for obj in mesh_objects:
            obj.select_set(True)
        
        armature.select_set(True)
        context.view_layer.objects.active = armature
        
        # Parent with automatic weights
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')
        
        self.report({'INFO'}, f"Parented {len(mesh_objects)} objects to armature")
        return {'FINISHED'}

class ARWEAPONS_OT_create_empties(bpy.types.Operator):
    """Create empty objects for weapon attachment points and components"""
    bl_idname = "arweapons.create_empties"
    bl_label = "Create Attachment Points"
    bl_options = {'REGISTER', 'UNDO'}
    
    # Properties for which empties to create
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
        # Get or create the parent collection for organization
        weapon_collection = None
        collection_name = "Weapon_Components"
        
        if collection_name in bpy.data.collections:
            weapon_collection = bpy.data.collections[collection_name]
        else:
            weapon_collection = bpy.data.collections.new(collection_name)
            context.scene.collection.children.link(weapon_collection)
        
        # Dictionary to track created empties
        created_empties = []
        
        # Create empty objects based on selected options
        if self.create_slots:
            slot_empties = [
                "slot_ironsight_front",
                "slot_ironsight_rear",
                "slot_magazine",
                "slot_optics",
                "slot_underbarrel",
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
                    empty = self._create_empty(name, EMPTY_LOCATIONS[name], weapon_collection, 'ARROWS', 0.04)
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
        
        # Parent empties to armature if it exists
        armature = None
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                armature = obj
                break
        
        if armature:
            for name in created_empties:
                if name in bpy.data.objects:
                    obj = bpy.data.objects[name]
                    obj.parent = armature
        
        if created_empties:
            self.report({'INFO'}, f"Created {len(created_empties)} empty objects")
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
    """Separate selected components into individual objects for Arma Reforger"""
    bl_idname = "arvehicles.separate_components"
    bl_label = "Separate Vehicle Components"
    bl_options = {'REGISTER', 'UNDO'}
    
    component_type: bpy.props.EnumProperty(
        name="Component Type",
        description="Type of component being separated",
        items=[
            ('Sight', "Sight", "Sight component"),
            ('light', "Light", "Emissive light component"),
            ('Trigger', "Trigger", "Trigger or movable component"),('Bolt', "Bolt", "Bolt or movable component"),
            ('accessory', "Accessory", "Optional accessory component"),
            ('other', "Other", "Other component type"),
        ],
        default='Trigger'
    )
    
    custom_name: bpy.props.StringProperty(
        name="Custom Name",
        description="Custom name for the separated component",
        default=""
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
        
        # Generate a name for the new object
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
        new_name = self.custom_name
        if not new_name:
            new_name = f"{prefix}{obj.name}"
        
        # Separate the selected faces
        bpy.ops.mesh.separate(type='SELECTED')
        
        # Get the newly created object (last selected)
        new_obj = context.selected_objects[-1]
        new_obj.name = new_name
        
        # Switch back to object mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Select only the new object
        bpy.ops.object.select_all(action='DESELECT')
        new_obj.select_set(True)
        context.view_layer.objects.active = new_obj
        
        self.report({'INFO'}, f"Separated component as '{new_name}'")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        if context.mode != 'EDIT_MESH':
            self.report({'ERROR'}, "Must be in Edit Mode with faces selected")
            return {'CANCELLED'}
        return context.window_manager.invoke_props_dialog(self)

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
        
        # Center and Scale operators
        row = box.row(align=True)
        row.operator("arweapons.center_weapon", text="Center", icon='PIVOT_BOUNDBOX')
        row.operator("arweapons.scale_weapon", text="Scale", icon='FULLSCREEN_ENTER')
        
        # Collision boxes section
        box = layout.box()
        box.label(text="Collision", icon='MESH_CUBE')
        box.operator("arweapons.create_collision_box")
        box.operator("arweapons.create_detailed_collision")
        
        # Empty Objects section
        box = layout.box()
        box.label(text="Attachment Points", icon='EMPTY_DATA')
        box.operator("arweapons.create_empties")
        
        # Rigging section
        box = layout.box()
        box.label(text="Rigging", icon='ARMATURE_DATA')
        
        # Bone creation
        col = box.column(align=True)
        col.label(text="Add Bones:")
        
        # Root bone first
        col.operator("arweapons.create_bone", text="Add w_root").bone_type = 'w_root'
        
        # Other bones
        row = col.row(align=True)
        row.operator("arweapons.create_bone", text="Fire Mode").bone_type = 'w_fire_mode'
        row.operator("arweapons.create_bone", text="Charging").bone_type = 'w_charging_handle'
        
        row = col.row(align=True)
        row.operator("arweapons.create_bone", text="Trigger").bone_type = 'w_trigger'
        row.operator("arweapons.create_bone", text="Bolt").bone_type = 'w_bolt'
        
        box = layout.box()
        box.label(text="Component Separation", icon='MOD_BUILD')
        row = box.row(align=True)
        row.operator("arvehicles.separate_components", text="Separate Selection", icon='UNLINKED')
        
        # Parenting
        col.separator()
        col.operator("arweapons.parent_to_armature")
        


# Registration
classes = (
    ARWEAPONS_OT_center_weapon,
    ARWEAPONS_OT_scale_weapon,
    ARWEAPONS_OT_create_collision_box,
    ARWEAPONS_OT_create_detailed_collision,
    ARWEAPONS_OT_create_bone,
    ARWEAPONS_OT_parent_to_armature,
    ARWEAPONS_OT_create_empties,
    ARWEAPONS_PT_panel,ARVEHICLES_OT_separate_components,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
