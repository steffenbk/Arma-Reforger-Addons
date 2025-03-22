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
            # Standard width can be derived from standard length (typical proportion)
            target_width = STANDARD_WEAPON_LENGTH * 0.1  # Approximate standard width
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
            # Show approximate standard width
            box.label(text=f"Width: {STANDARD_WEAPON_LENGTH * 0.1:.3f}m (approximate)")
        else:
            layout.label(text="Custom Real-World Dimensions:")
            layout.prop(self, "custom_length")
            layout.prop(self, "custom_width")
            layout.prop(self, "custom_height")
        
        # Common options
        layout.prop(self, "preserve_proportions")
        layout.prop(self, "center_after_scale")
        
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