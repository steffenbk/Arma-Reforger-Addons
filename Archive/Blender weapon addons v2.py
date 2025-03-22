bl_info = {
    "name": "Arma Reforger Weapon Tools",
    "author": "Your Name",
    "version": (1, 1),
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

# Standard dimensions for Arma Reforger weapons (in meters)
# These values are derived from your example model
STANDARD_WEAPON_LENGTH = 0.7  # From barrel_muzzle to back of weapon
STANDARD_WEAPON_HEIGHT = 0.25  # From bottom to top
STANDARD_BARREL_HEIGHT = 0.062  # Height of barrel from ground

# Default locations for empty objects (in meters)
# These are starting positions that can be adjusted later
EMPTY_LOCATIONS = {
    # Slots
    "slot_ironsight_front": (0, 0.3, 0.085),
    "slot_ironsight_rear": (0, 0.15, 0.085),
    "slot_magazine": (0, 0, -0.06),
    "slot_optics": (0, 0.1, 0.09),
    "slot_underbarrel": (0, 0.2, -0.03),
    
    # Snap points
    "snap_hand_right": (0.03, 0, 0.02),
    "snap_hand_left": (-0.03, 0.15, 0.02),
    
    # Barrel points
    "barrel_chamber": (0, -0.1, 0.065),
    "barrel_muzzle": (0, 0.35, 0.065),
    
    # Eye point
    "eye": (0, 0.1, 0.085),
}

class ARWEAPONS_OT_scale_weapon(bpy.types.Operator):
    """Scale weapon to match Arma Reforger standards"""
    bl_idname = "arweapons.scale_weapon"
    bl_label = "Scale Weapon"
    bl_options = {'REGISTER', 'UNDO'}
    
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
        
        # Calculate the scale factor to match standard dimensions
        length_scale = STANDARD_WEAPON_LENGTH / current_length if current_length > 0 else 1.0
        height_scale = STANDARD_WEAPON_HEIGHT / current_height if current_height > 0 else 1.0
        
        # Use the smaller scale to ensure weapon fits within standards
        scale_factor = min(length_scale, height_scale)
        
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
        pivot.scale = (scale_factor, scale_factor, scale_factor)
        
        # Apply the scale to all children
        bpy.ops.object.select_all(action='DESELECT')
        pivot.select_set(True)
        context.view_layer.objects.active = pivot
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        
        # Restore original parenting and move everything to origin
        for obj in mesh_objects:
            obj.parent = original_parents[obj]
            # Calculate the offset from center to origin
            obj.location = (0, 0, 0)
        
        # Remove the temporary pivot
        bpy.data.objects.remove(pivot)
        
        self.report({'INFO'}, f"Weapon scaled by factor: {scale_factor:.4f} and positioned at origin (0,0,0)")
        return {'FINISHED'}

class ARWEAPONS_OT_create_collision_boxes(bpy.types.Operator):
    """Create UCX_body and UTM_weapon collision boxes matching the weapon dimensions"""
    bl_idname = "arweapons.create_collision_boxes"
    bl_label = "Create Collision Boxes"
    bl_options = {'REGISTER', 'UNDO'}
    
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
        
        # Calculate dimensions
        width = max_x - min_x
        length = max_y - min_y
        height = max_z - min_z
        
        # Create UCX_body box (for collision)
        ucx_body = self._create_box("UCX_body", 
                                   center_x, center_y, center_z, 
                                   width, length, height)
        
        # Create UTM_weapon box (for collision)
        utm_weapon = self._create_box("UTM_weapon", 
                                     center_x, center_y, center_z, 
                                     width, length, height)
        
        # Select the newly created boxes
        bpy.ops.object.select_all(action='DESELECT')
        ucx_body.select_set(True)
        utm_weapon.select_set(True)
        context.view_layer.objects.active = ucx_body
        
        self.report({'INFO'}, "Created UCX_body and UTM_weapon collision boxes")
        return {'FINISHED'}
    
    def _create_box(self, name, center_x, center_y, center_z, width, length, height):
        """Helper function to create a box with given dimensions"""
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
        
        # Make it visible with material
        if name == "UCX_body":
            # Create a material for UCX_body
            mat = bpy.data.materials.new(name="UCX_Material")
            mat.diffuse_color = (1.0, 0.3, 0.3, 1.0)  # Solid red
            
            # Assign material to the object
            if box.data.materials:
                box.data.materials[0] = mat
            else:
                box.data.materials.append(mat)
        else:  # UTM_weapon
            # Create a material for UTM_weapon
            mat = bpy.data.materials.new(name="UTM_Material")
            mat.diffuse_color = (0.3, 0.3, 1.0, 1.0)  # Solid blue
            
            # Assign material to the object
            if box.data.materials:
                box.data.materials[0] = mat
            else:
                box.data.materials.append(mat)
        
        return box

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
        
        # Standard bone length from your example
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
                    # No bone parenting by default, user can set this up manually
        
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
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "create_slots")
        layout.prop(self, "create_snap_points")
        layout.prop(self, "create_barrel_points")
        layout.prop(self, "create_eye_point")

class ARWEAPONS_PT_panel(bpy.types.Panel):
    """Arma Reforger Weapons Panel"""
    bl_label = "AR Weapons"
    bl_idname = "ARWEAPONS_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'AR Weapons'
    
    def draw(self, context):
        layout = self.layout
        
        # Scaling section
        box = layout.box()
        box.label(text="Scaling")
        box.operator("arweapons.scale_weapon")
        
        # Collision boxes section
        box = layout.box()
        box.label(text="Collision")
        box.operator("arweapons.create_collision_boxes")
        
        # Empty Objects section
        box = layout.box()
        box.label(text="Attachment Points")
        box.operator("arweapons.create_empties")
        
        # Rigging section
        box = layout.box()
        box.label(text="Rigging")
        
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
        
        # Parenting
        col.separator()
        col.operator("arweapons.parent_to_armature")

classes = (
    ARWEAPONS_OT_scale_weapon,
    ARWEAPONS_OT_create_collision_boxes,
    ARWEAPONS_OT_create_bone,
    ARWEAPONS_OT_parent_to_armature,
    ARWEAPONS_OT_create_empties,
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
