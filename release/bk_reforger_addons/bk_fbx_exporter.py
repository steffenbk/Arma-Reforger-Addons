import bpy
import os
import math
import mathutils
import time
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty, CollectionProperty
from bpy_extras.io_utils import ExportHelper

bl_info = {
    "name": "BK Asset Exporter",
    "author": "steffenbk",
    "version": (1, 4),
    "blender": (4, 0, 0),
    "location": "File > Export > Arma Reforger Asset (.fbx) / Sidebar > BK Exporter",
    "description": "Export assets for Arma Reforger Enfusion Engine",
    "warning": "",
    "doc_url": "",
    "category": "Import-Export",
}

# Define scene properties early
def register_properties():
    bpy.types.Scene.ar_export_mode = EnumProperty(
        name="Export Mode",
        items=(
            ('FULL', "Full Scene", "Export the entire scene as one asset"),
            ('INDIVIDUAL', "Individual Parts", "Export selected meshes as individual assets"),
        ),
        default='FULL',
    )
    
    bpy.types.Scene.ar_apply_transform = BoolProperty(
        name="Apply Transform",
        description="Apply object transformations before export",
        default=True,
    )
    
    bpy.types.Scene.ar_export_colliders = BoolProperty(
        name="Export Colliders",
        description="Export collision meshes with the objects",
        default=True,
    )
    
    bpy.types.Scene.ar_preserve_armature = BoolProperty(
        name="Preserve Armature",
        description="Preserve rigging and armature data",
        default=True,
    )
    
    bpy.types.Scene.ar_center_to_origin = BoolProperty(
        name="Center to Origin",
        description="Center geometry to world origin before export",
        default=True,
    )
    
    # New alignment options for the sidebar
    bpy.types.Scene.ar_align_to_axis = BoolProperty(
        name="Align to Axis",
        description="Align objects to specified axis",
        default=True,
    )
    
    bpy.types.Scene.ar_alignment_axis = EnumProperty(
        name="Alignment Axis",
        items=(
            ('Y', "Y Axis (Default)", "Align to Y axis as required by Enfusion engine"),
            ('X', "X Axis", "Align to X axis"),
            ('Z', "Z Axis", "Align to Z axis"),
            ('CUSTOM', "Custom", "Use custom alignment rotation"),
        ),
        default='Y',
    )
    
    bpy.types.Scene.ar_custom_rotation_x = FloatProperty(
        name="X Rotation",
        description="Custom X rotation (degrees)",
        default=0.0,
        min=-360.0,
        max=360.0,
        subtype='ANGLE',
    )
    
    bpy.types.Scene.ar_custom_rotation_y = FloatProperty(
        name="Y Rotation",
        description="Custom Y rotation (degrees)",
        default=0.0,
        min=-360.0,
        max=360.0,
        subtype='ANGLE',
    )
    
    bpy.types.Scene.ar_custom_rotation_z = FloatProperty(
        name="Z Rotation",
        description="Custom Z rotation (degrees)",
        default=0.0,
        min=-360.0,
        max=360.0,
        subtype='ANGLE',
    )
    
    bpy.types.Scene.ar_export_path = StringProperty(
        name="Export Folder",
        description="Path to export FBX files",
        default="//",  # Default to blend file location
        subtype='DIR_PATH',
    )

def unregister_properties():
    # Check if properties exist before removing them
    props_to_remove = [
        'ar_export_mode', 'ar_apply_transform', 'ar_export_colliders', 
        'ar_preserve_armature', 'ar_center_to_origin', 'ar_align_to_axis', 
        'ar_alignment_axis', 'ar_custom_rotation_x', 'ar_custom_rotation_y', 
        'ar_custom_rotation_z', 'ar_export_path'
    ]
    
    for prop in props_to_remove:
        if hasattr(bpy.types.Scene, prop):
            delattr(bpy.types.Scene, prop)

class ExportArmaReforgerAsset(bpy.types.Operator, ExportHelper):
    """Export to Arma Reforger Enfusion Engine Format"""
    bl_idname = "export_scene.arma_reforger_asset"
    bl_label = "Export Arma Reforger Asset"
    bl_options = {'PRESET', 'UNDO'}

    filename_ext = ".fbx"
    filter_glob: StringProperty(
        default="*.fbx",
        options={'HIDDEN'},
    )

    # Export mode enum
    export_mode: EnumProperty(
        name="Export Mode",
        items=(
            ('FULL', "Full Scene", "Export the entire scene as one asset"),
            ('INDIVIDUAL', "Individual Parts", "Export selected meshes as individual assets"),
        ),
        default='FULL',
    )
    
    # Export options
    apply_transform: BoolProperty(
        name="Apply Transform",
        description="Apply object transformations before export",
        default=True,
    )
    
    export_colliders: BoolProperty(
        name="Export Colliders",
        description="Export collision meshes with the objects",
        default=True,
    )
    
    preserve_armature: BoolProperty(
        name="Preserve Armature",
        description="Preserve rigging and armature data",
        default=True,
    )
    
    preserve_sockets: BoolProperty(
        name="Preserve Sockets",
        description="Preserve socket data for the Enfusion engine",
        default=True,
    )
    
    # Specific Arma Reforger Settings - leaf bones always off
    add_leaf_bones: BoolProperty(
        name="Add Leaf Bones",
        description="Add leaf bones as seen in your reference image",
        default=False,
        options={'HIDDEN'},  # Hide this option as it should always be off
    )
    
    # Custom alignment options
    align_to_axis: BoolProperty(
        name="Align to Axis",
        description="Align objects to specified axis",
        default=False,
    )
    
    # Axis alignment options
    alignment_axis: EnumProperty(
        name="Alignment Axis",
        items=(
            ('Y', "Y Axis (Default)", "Align to Y axis as required by Enfusion engine"),
            ('X', "X Axis", "Align to X axis"),
            ('Z', "Z Axis", "Align to Z axis"),
            ('CUSTOM', "Custom", "Use custom alignment rotation"),
        ),
        default='Y',
    )
    
    # Custom rotation values when 'CUSTOM' is selected
    custom_rotation_x: FloatProperty(
        name="X Rotation",
        description="Custom X rotation (degrees)",
        default=0.0,
        min=-360.0,
        max=360.0,
        subtype='ANGLE',
    )
    
    custom_rotation_y: FloatProperty(
        name="Y Rotation",
        description="Custom Y rotation (degrees)",
        default=0.0,
        min=-360.0,
        max=360.0,
        subtype='ANGLE',
    )
    
    custom_rotation_z: FloatProperty(
        name="Z Rotation",
        description="Custom Z rotation (degrees)",
        default=0.0,
        min=-360.0,
        max=360.0,
        subtype='ANGLE',
    )
    
    center_to_origin: BoolProperty(
        name="Center to Origin",
        description="Center geometry to world origin before export",
        default=False,
    )
    
    center_mode: EnumProperty(
        name="Center Mode",
        items=(
            ('ORIGIN', "Object Origin", "Move object origin to world center"),
            ('GEOMETRY', "Geometry Center", "Center based on geometry bounds"),
            ('MASS', "Center of Mass", "Use center of mass for centering"),
        ),
        default='GEOMETRY',
    )
    
    # Add a property to control whether to use undo after export
    use_auto_undo: BoolProperty(
        name="Auto Undo After Export",
        description="Automatically undo changes after export (like pressing Ctrl+Z)",
        default=True,
    )
    
    undo_delay: IntProperty(
        name="Undo Delay (seconds)",
        description="Seconds to wait before performing undo after export",
        min=0,
        max=10,
        default=1,
    )
    
    restore_positions: BoolProperty(
        name="Restore Object Positions",
        description="Restore object positions after export (legacy method)",
        default=False,
    )
    
    # Collection deletion options
    delete_collection: BoolProperty(
        name="Delete Collection Temporarily",
        description="Temporarily delete a collection before export (will be restored with auto-undo)",
        default=False,
    )
    
    def get_collection_items(self, context):
        # Create a list of collections for the EnumProperty
        items = []
        for i, collection in enumerate(bpy.data.collections):
            items.append((collection.name, collection.name, f"Delete {collection.name} during export", i))
        if not items:
            items.append(("NONE", "No Collections", "No collections available", 0))
        return items
    
    collection_to_delete: EnumProperty(
        name="Collection to Delete",
        description="Select a collection to temporarily delete during export",
        items=get_collection_items,
    )
    
    def draw(self, context):
        layout = self.layout
        
        layout.prop(self, "export_mode")
        
        if self.export_mode == 'INDIVIDUAL':
            layout.prop(self, "apply_transform")
            layout.prop(self, "export_colliders")
        
        layout.prop(self, "preserve_armature")
        layout.prop(self, "preserve_sockets")
        
        # Custom settings specific to Arma Reforger requirements
        box = layout.box()
        box.label(text="Enfusion Engine Settings")
        # "add_leaf_bones" option removed from UI - it's always off
        box.prop(self, "align_to_axis")
        
        if self.align_to_axis:
            box.prop(self, "alignment_axis")
            
            # Show custom rotation options only when CUSTOM is selected
            if self.alignment_axis == 'CUSTOM':
                row = box.row(align=True)
                row.prop(self, "custom_rotation_x")
                row.prop(self, "custom_rotation_y")
                row.prop(self, "custom_rotation_z")
        
        # Centering options
        box = layout.box()
        box.label(text="Geometry Centering")
        box.prop(self, "center_to_origin")
        if self.center_to_origin:
            box.prop(self, "center_mode")
            box.prop(self, "use_auto_undo")
            if self.use_auto_undo:
                box.prop(self, "undo_delay")
            if not self.use_auto_undo:
                box.prop(self, "restore_positions")
        
        # Collection deletion options
        box = layout.box()
        box.label(text="Temporary Collection Deletion")
        box.prop(self, "delete_collection")
        if self.delete_collection:
            box.prop(self, "collection_to_delete")
            # Force auto-undo to be enabled if delete_collection is enabled
            if not self.use_auto_undo:
                self.use_auto_undo = True
                box.label(text="Auto-undo enabled for collection restoration", icon='INFO')
            box.label(text="Collection will be restored after export via undo", icon='INFO')
    
    def delayed_undo(self, context, delay_seconds):
        """Schedule an undo operation after a delay"""
        def undo_function():
            print(f"Auto-undo: Performing undo operation after {delay_seconds} second delay...")
            bpy.ops.ed.undo()
            # Display a message to the user
            self.report({'INFO'}, f"Export completed successfully and changes were undone")
            # Return None to unregister the timer
            return None
            
        # Register a timer that will call undo_function after delay_seconds
        if delay_seconds > 0:
            # Convert to milliseconds for the timer
            delay_ms = delay_seconds
            print(f"Auto-undo: Scheduling undo operation with {delay_seconds} second delay...")
            bpy.app.timers.register(undo_function, first_interval=delay_ms)
        else:
            # If no delay, just call it immediately
            undo_function()
    
    def delete_selected_collection(self, context):
        """Delete the selected collection"""
        collection_name = self.collection_to_delete
        if collection_name == "NONE" or collection_name not in bpy.data.collections:
            self.report({'WARNING'}, "No valid collection selected for deletion")
            return False
        
        # Get the collection by name
        collection = bpy.data.collections[collection_name]
        
        # Store the name before we delete the collection
        display_name = collection.name
        
        print(f"Temporarily deleting collection: {display_name}")
        
        # Get all objects in the collection
        objects_to_delete = [obj for obj in collection.objects]
        
        # Delete all objects in the collection
        for obj in objects_to_delete:
            bpy.data.objects.remove(obj, do_unlink=True)
        
        # Delete the collection itself
        bpy.data.collections.remove(collection)
        
        self.report({'INFO'}, f"Temporarily deleted collection: {display_name}")
        return True
        
    # Helper function to apply object transformations
    def apply_object_transform(self, obj, apply_location=False, apply_rotation=False, apply_scale=False):
        """Helper function to apply object transformations"""
        # Store current selection and active object
        original_active = bpy.context.view_layer.objects.active
        original_selected = [o for o in bpy.context.selected_objects]
        
        # Deselect all objects
        bpy.ops.object.select_all(action='DESELECT')
        
        # Select and make active our target
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        
        # Apply transformations
        bpy.ops.object.transform_apply(
            location=apply_location,
            rotation=apply_rotation,
            scale=apply_scale
        )
        
        # Restore original selection
        bpy.ops.object.select_all(action='DESELECT')
        for o in original_selected:
            if o.name in bpy.context.view_layer.objects:
                o.select_set(True)
        if original_active and original_active.name in bpy.context.view_layer.objects:
            bpy.context.view_layer.objects.active = original_active

    # FIXED: Improved alignment function that actually rotates the object
    def apply_alignment(self, obj):
        """Apply alignment rotation to object based on selected axis"""
        if not self.align_to_axis:
            return None
            
        # Store original rotation before any changes
        original_rotation = obj.rotation_euler.copy()
        original_matrix = obj.matrix_world.copy()
        
        print(f"Applying alignment to {obj.name} using {self.alignment_axis} axis")
        
        # Create a duplicate mesh for safety
        has_been_duplicated = False
        
        try:
            # Apply different alignment based on the selected axis
            if self.alignment_axis == 'Y':
                # Default Y-axis alignment
                # We'll apply a specific rotation to ensure consistent orientation
                print("Applying Y-axis alignment (default)")
                # Reset rotation first
                obj.rotation_mode = 'XYZ'
                obj.rotation_euler = (0, 0, 0)
                # Apply this to make it permanent
                self.apply_object_transform(obj, apply_rotation=True)
                
                # Ensure the object is aligned to the Y-forward axis
                # This additional rotation helps enforce the standard Enfusion orientation
                obj.rotation_euler = (math.radians(0), math.radians(0), math.radians(0))
                self.apply_object_transform(obj, apply_rotation=True)
            
            elif self.alignment_axis == 'X':
                # Rotate to align with X-axis
                print("Applying X-axis alignment")
                obj.rotation_mode = 'XYZ'
                obj.rotation_euler = (0, 0, math.radians(90))
                # Apply transformation to make it permanent
                self.apply_object_transform(obj, apply_rotation=True)
            
            elif self.alignment_axis == 'Z':
                # Rotate to align with Z-axis
                print("Applying Z-axis alignment")
                obj.rotation_mode = 'XYZ'
                obj.rotation_euler = (math.radians(90), 0, 0)
                # Apply transformation to make it permanent
                self.apply_object_transform(obj, apply_rotation=True)
            
            elif self.alignment_axis == 'CUSTOM':
                # Apply custom rotation
                print(f"Applying custom rotation: X={self.custom_rotation_x}, Y={self.custom_rotation_y}, Z={self.custom_rotation_z}")
                obj.rotation_mode = 'XYZ'
                obj.rotation_euler = (
                    math.radians(self.custom_rotation_x),
                    math.radians(self.custom_rotation_y),
                    math.radians(self.custom_rotation_z)
                )
                # Apply transformation to make it permanent
                self.apply_object_transform(obj, apply_rotation=True)
        
        except Exception as e:
            print(f"Error during alignment: {e}")
            import traceback
            print(traceback.format_exc())
            
            # If we duplicated, clean up
            if has_been_duplicated:
                # Restore the original object
                bpy.data.objects.remove(obj)
        
        print(f"Alignment complete for {obj.name}")
        return original_matrix
    
    # More advanced matrix-based alignment
    def apply_matrix_rotation(self, obj, axis='Y'):
        """Apply rotation using matrix transformation for precise axis alignment"""
        if not self.align_to_axis:
            return None
        
        # Store original world matrix
        original_matrix = obj.matrix_world.copy()
        
        print(f"Applying matrix-based alignment to {obj.name} for {axis} axis")
        
        try:
            # For custom rotation, use euler angles
            if axis == 'CUSTOM':
                # Custom rotation - create rotation matrix from Euler angles
                rot_mat = mathutils.Euler((
                    math.radians(self.custom_rotation_x),
                    math.radians(self.custom_rotation_y),
                    math.radians(self.custom_rotation_z)
                )).to_matrix().to_4x4()
                
                # Store current location
                location = obj.location.copy()
                
                # Apply rotation - this creates a new orientation
                obj.matrix_world = rot_mat @ obj.matrix_world
                
                # Apply to make permanent
                self.apply_object_transform(obj, apply_rotation=True)
                
                return original_matrix
            
            # Otherwise use prefabricated rotations for standard axes
            obj.rotation_mode = 'XYZ'
            
            if axis == 'Y':
                # Standard Y-forward configuration
                obj.rotation_euler = (0, 0, 0)
            elif axis == 'X':
                # X-forward configuration
                obj.rotation_euler = (0, 0, math.radians(90))
            elif axis == 'Z':
                # Z-forward configuration
                obj.rotation_euler = (math.radians(90), 0, 0)
            
            # Apply to make permanent
            self.apply_object_transform(obj, apply_rotation=True)
            
            print(f"Matrix alignment complete for {obj.name}")
            return original_matrix
            
        except Exception as e:
            print(f"Error in matrix alignment: {e}")
            import traceback
            print(traceback.format_exc())

    def execute(self, context):
        # Explicitly push an undo step before we start
        if (self.center_to_origin or self.delete_collection or self.align_to_axis) and self.use_auto_undo:
            bpy.ops.ed.undo_push(message="Before Arma Reforger Export")
        
        # Save current selection and mode
        original_selection = context.selected_objects.copy()
        original_active = context.active_object
        original_mode = context.object.mode if context.object else 'OBJECT'
        
        # Ensure we're in object mode if we have an active object
        if context.object and original_mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # Path to save files
        base_path = os.path.dirname(self.filepath)
        base_name = os.path.basename(self.filepath)
        base_name = os.path.splitext(base_name)[0]  # Remove extension
        
        # Print debug info
        print("Export settings:")
        print(f"- Export Mode: {self.export_mode}")
        print(f"- Center to Origin: {self.center_to_origin}")
        print(f"- Center Mode: {self.center_mode}")
        print(f"- Auto Undo: {self.use_auto_undo}")
        print(f"- Undo Delay: {self.undo_delay} seconds")
        print(f"- Restore Positions: {self.restore_positions}")
        print(f"- Align to Axis: {self.align_to_axis}")
        print(f"- Alignment Axis: {self.alignment_axis}")
        if self.alignment_axis == 'CUSTOM':
            print(f"- Custom Rotation: X={self.custom_rotation_x}, Y={self.custom_rotation_y}, Z={self.custom_rotation_z}")
        
        # Delete collection if requested
        deleted_collection = False
        if self.delete_collection and self.collection_to_delete != "NONE":
            deleted_collection = self.delete_selected_collection(context)
            if deleted_collection:
                print("Collection successfully deleted for export")
            else:
                print("Failed to delete collection for export")
            
# We need to handle each export mode in a way that doesn't rely on context-sensitive operators
        try:
            if self.export_mode == 'FULL':
                self.export_full_scene(context, self.filepath)
            else:
                self.export_individual_parts(context, base_path, base_name)
                
            # If auto-undo is enabled, perform the delayed undo
            if (self.center_to_origin or deleted_collection or self.align_to_axis) and self.use_auto_undo:
                self.delayed_undo(context, self.undo_delay)
                restoration_message = ""
                if self.center_to_origin:
                    restoration_message += "object positions"
                if self.align_to_axis:
                    if restoration_message:
                        restoration_message += ", "
                    restoration_message += "object rotations"
                if deleted_collection:
                    if restoration_message:
                        restoration_message += " and "
                    restoration_message += "deleted collection"
                self.report({'INFO'}, f"Export completed successfully, {restoration_message} will be restored in {self.undo_delay} seconds")
            else:
                self.report({'INFO'}, f"Export completed successfully")
                
            return {'FINISHED'}
        except Exception as e:
            import traceback
            self.report({'ERROR'}, f"Export failed: {str(e)}")
            # Print full traceback to system console for debugging
            print(f"Export error details: {traceback.format_exc()}")
            return {'CANCELLED'}
        finally:
            # Restore original selection and mode - context-independent approach
            # Deselect all objects without using operators
            for obj in context.view_layer.objects:
                obj.select_set(False)
                
            # Restore original selection
            for obj in original_selection:
                if obj.name in context.view_layer.objects:
                    obj.select_set(True)
                    
            # Restore active object
            if original_active and original_active.name in context.view_layer.objects:
                context.view_layer.objects.active = original_active
                
            # Restore original mode if applicable
            if context.object and original_mode != 'OBJECT':
                bpy.ops.object.mode_set(mode=original_mode)

    def export_full_scene(self, context, filepath):
        """Export the entire scene as one asset"""
        # Check if we need to center the entire scene
        original_locations = {}
        original_origins = {}
        original_rotations = {}
        meshes_to_center = []
        meshes_to_align = []
        
        # Apply alignments if requested
        if self.align_to_axis:
            print(f"Applying alignment with {self.alignment_axis} axis...")
            for obj in context.scene.objects:
                if obj.type == 'MESH':
                    # Use the improved matrix rotation function
                    original_rotations[obj] = self.apply_matrix_rotation(obj, self.alignment_axis)
                    meshes_to_align.append(obj)
        
        if self.center_to_origin:
            print("Centering objects to origin...")
            # Store original locations and data for undo
            for obj in context.scene.objects:
                if obj.type == 'MESH':
                    original_locations[obj] = obj.location.copy()
                    # Store a reference to the mesh object's data
                    original_origins[obj] = (obj.data, obj.matrix_world.copy())
                    meshes_to_center.append(obj)
                    print(f"Storing original location for {obj.name}: {original_locations[obj]}")
            
            # Center each mesh based on the selected mode
            for obj in meshes_to_center:
                self.center_object_to_origin(obj, self.center_mode)
        
        # Set up export settings
        export_settings = {
            'filepath': filepath,
            'use_selection': False,
            'axis_forward': 'Y',
            'axis_up': 'Z',
            'use_mesh_modifiers': True,
            'use_armature_deform_only': False,
            'bake_anim': self.preserve_armature,
            'add_leaf_bones': False,  # Always off regardless of property value
            'primary_bone_axis': 'Y',  # As seen in your reference image
            'secondary_bone_axis': 'X',
            'mesh_smooth_type': 'FACE',
            'use_subsurf': False,
            'use_custom_props': True  # For any custom properties
        }
        
        # Export the scene
        bpy.ops.export_scene.fbx(**export_settings)
        
        # Restore original locations if we centered objects and restoration is enabled
        if self.center_to_origin and self.restore_positions:
            print("Restoring original locations...")
            for obj, loc in original_locations.items():
                print(f"Restoring {obj.name} to {loc}")
                obj.location = loc
            
            # Restore original rotations if we applied alignment
            if self.align_to_axis:
                print("Restoring original rotations...")
                for obj, mat in original_rotations.items():
                    if mat:  # Check if we have a stored rotation
                        print(f"Restoring rotation for {obj.name}")
                        obj.matrix_world = mat

    def export_individual_parts(self, context, base_path, base_name):
        """Export selected meshes as individual assets"""
        selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not selected_objects:
            raise Exception("No mesh objects selected for individual export")
            
        for i, obj in enumerate(selected_objects):
            # Save original transform and origin data
            original_location = obj.location.copy()
            original_matrix_world = obj.matrix_world.copy()
            
            # Apply alignment if requested
            original_rotation = None
            if self.align_to_axis:
                original_rotation = self.apply_matrix_rotation(obj, self.alignment_axis)
            
            # Deselect all objects without using operators
            for scene_obj in context.view_layer.objects:
                scene_obj.select_set(False)
            
            # Select the current object and make it active
            obj.select_set(True)
            context.view_layer.objects.active = obj
            
            # Get the object name for the file
            obj_name = obj.name.replace(".", "_")
            
            # Set up the filepath for this object
            filepath = os.path.join(base_path, f"{base_name}_{obj_name}.fbx")
            
            # Find colliders if needed
            collider_obj = None
            collider_original_loc = None
            collider_original_rot = None
            
            if self.export_colliders:
                # This assumes colliders have a naming convention, adjust as needed
                # For example, if the collider is named "UTM_objectname" as in your image
                collider_name = f"UTM_{obj.name}"
                
                for coll_obj in bpy.data.objects:
                    if coll_obj.name == collider_name and coll_obj.type == 'MESH':
                        collider_obj = coll_obj
                        collider_original_loc = coll_obj.location.copy()
                        coll_obj.select_set(True)
                        
                        # Apply alignment to collider if needed
                        if self.align_to_axis:
                            collider_original_rot = self.apply_matrix_rotation(coll_obj, self.alignment_axis)
                        break
            
            # Prepare for export
            if self.apply_transform:
                # Apply transformations - create a temporary copy to avoid modifying original
                # This is a simplification - in practice, apply_transform should be handled more carefully
                bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
                
            # Center geometry if requested
            if self.center_to_origin:
                self.center_object_to_origin(obj, self.center_mode)
            
            # Export settings for individual objects
            export_settings = {
                'filepath': filepath,
                'use_selection': True,
                'axis_forward': 'Y',
                'axis_up': 'Z',
                'use_mesh_modifiers': True,
                'use_armature_deform_only': False,
                'bake_anim': False,
                'add_leaf_bones': False,  # Always off regardless of property value
                'primary_bone_axis': 'Y',
                'secondary_bone_axis': 'X',
                'mesh_smooth_type': 'FACE',
                'use_subsurf': False,
                'use_custom_props': True
            }
            
            # Export the object
            bpy.ops.export_scene.fbx(**export_settings)
            
            # Restore original transformation if restoration is enabled
            if self.restore_positions:
                print(f"Restoring {obj.name} to original position: {original_location}")
                obj.location = original_location
                
                # Restore original rotation if we applied alignment
                if original_rotation:
                    print(f"Restoring rotation for {obj.name}")
                    obj.matrix_world = original_rotation
                
                # Restore collider if found
                if collider_obj and collider_original_loc:
                    print(f"Restoring collider {collider_obj.name} to original position: {collider_original_loc}")
                    collider_obj.location = collider_original_loc
                    
                    # Restore collider rotation if we applied alignment
                    if collider_original_rot:
                        print(f"Restoring rotation for collider {collider_obj.name}")
                        collider_obj.matrix_world = collider_original_rot

    def center_object_to_origin(self, obj, center_mode):
        """Center an object to the world origin based on the specified mode"""
        # Store the original selection and active object
        original_active = bpy.context.view_layer.objects.active
        original_selected = [o for o in bpy.context.selected_objects]
        
        # Store original cursor location and object rotation
        original_cursor_location = bpy.context.scene.cursor.location.copy()
        original_rotation = obj.rotation_euler.copy()
        
        # Deselect all objects and ensure we're in object mode
        bpy.ops.object.select_all(action='DESELECT')
        
        # Select and activate our object
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        if obj.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # Implement different centering methods
        if center_mode == 'ORIGIN':
            # Simply move object to origin
            obj.location = (0, 0, 0)
        
        elif center_mode == 'GEOMETRY':
            # Set cursor to world origin
            bpy.context.scene.cursor.location = (0, 0, 0)
            
            # Set origin to geometry
            bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
            
            # Use the snap selection to cursor approach
            obj.location = bpy.context.scene.cursor.location
            
            # Preserve original rotation
            obj.rotation_euler = original_rotation
            
        elif center_mode == 'MASS':
            # Set cursor to world origin
            bpy.context.scene.cursor.location = (0, 0, 0)
            
            # Set origin to center of mass
            bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS')
            
            # Use the snap selection to cursor approach
            obj.location = bpy.context.scene.cursor.location
            
            # Preserve original rotation
            obj.rotation_euler = original_rotation
        
        # Restore cursor location
        bpy.context.scene.cursor.location = original_cursor_location
        
        # Restore selection
        bpy.ops.object.select_all(action='DESELECT')
        for o in original_selected:
            if o.name in bpy.context.view_layer.objects:
                o.select_set(True)
        
        # Restore active object
        if original_active and original_active.name in bpy.context.view_layer.objects:
            bpy.context.view_layer.objects.active = original_active
        
        
        


# Add sidebar panel for quick access - simplified version
class VIEW3D_PT_arma_reforger_tools(bpy.types.Panel):
    """Arma Reforger Tools Sidebar Panel"""
    bl_label = "BK Exporter"
    bl_idname = "VIEW3D_PT_arma_reforger_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BK Exporter'
    
    def draw(self, context):
        layout = self.layout
        
        # Export to Arma button - simplified with no options
        row = layout.row()
        row.scale_y = 2.0  # Make the button even bigger for easy access
        row.operator(ExportArmaReforgerAsset.bl_idname, text="Export to Arma", icon='EXPORT')
        
        # Show a small info text that all options are in the export dialog
        box = layout.box()
        box.label(text="Options available in export dialog", icon='INFO')


# Register and unregister functions
classes = (
    ExportArmaReforgerAsset,
    VIEW3D_PT_arma_reforger_tools,
)

def menu_func_export(self, context):
    self.layout.operator(ExportArmaReforgerAsset.bl_idname, text="Arma Reforger Asset (.fbx)")

def register():
    # Use try-except to handle any registration errors
    try:
        # First register properties
        register_properties()
        
        # Then register classes
        for cls in classes:
            bpy.utils.register_class(cls)
            
        # Add export menu item
        bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
        
        print("Arma Reforger Asset Exporter registered successfully")
    except Exception as e:
        print(f"Error registering Arma Reforger Asset Exporter: {str(e)}")
        import traceback
        print(traceback.format_exc())

def unregister():
    # Use try-except to handle any unregistration errors
    try:
        # Remove export menu item
        bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
        
        # Unregister classes
        for cls in reversed(classes):
            bpy.utils.unregister_class(cls)
            
        # Unregister properties
        unregister_properties()
        
        print("Arma Reforger Asset Exporter unregistered successfully")
    except Exception as e:
        print(f"Error unregistering Arma Reforger Asset Exporter: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    register()
