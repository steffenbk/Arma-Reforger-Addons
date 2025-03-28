import bpy
import os
import math
import mathutils
import time
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty, CollectionProperty
from bpy_extras.io_utils import ExportHelper

bl_info = {
    "name": "Arma Reforger Asset Exporter",
    "author": "Your Name",
    "version": (1, 2),
    "blender": (4, 0, 0),
    "location": "File > Export > Arma Reforger Asset (.fbx) / Sidebar > AR Tools",
    "description": "Export assets for Arma Reforger Enfusion Engine",
    "warning": "",
    "doc_url": "",
    "category": "Import-Export",
}

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
    
    align_to_y_axis: BoolProperty(
        name="Align to Y-Axis",
        description="Align objects to Y-axis as required by Enfusion engine",
        default=True,
    )
    
    center_to_origin: BoolProperty(
        name="Center to Origin",
        description="Center geometry to world origin before export",
        default=True,
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
        box.prop(self, "align_to_y_axis")
        
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
            
    def execute(self, context):
        # Explicitly push an undo step before we start
        if (self.center_to_origin or self.delete_collection) and self.use_auto_undo:
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
            if (self.center_to_origin or deleted_collection) and self.use_auto_undo:
                self.delayed_undo(context, self.undo_delay)
                restoration_message = ""
                if self.center_to_origin:
                    restoration_message += "object positions"
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
        meshes_to_center = []
        
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
            'axis_forward': 'Y',  # For correct Y-axis alignment
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

    def export_individual_parts(self, context, base_path, base_name):
        """Export selected meshes as individual assets"""
        selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not selected_objects:
            raise Exception("No mesh objects selected for individual export")
            
        for i, obj in enumerate(selected_objects):
            # Save original transform and origin data
            original_location = obj.location.copy()
            original_matrix_world = obj.matrix_world.copy()
            
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
            
            if self.export_colliders:
                # This assumes colliders have a naming convention, adjust as needed
                # For example, if the collider is named "UTM_objectname" as in your image
                collider_name = f"UTM_{obj.name}"
                
                for coll_obj in bpy.data.objects:
                    if coll_obj.name == collider_name and coll_obj.type == 'MESH':
                        collider_obj = coll_obj
                        collider_original_loc = coll_obj.location.copy()
                        coll_obj.select_set(True)
                        break
            
            # Prepare for export
            if self.apply_transform:
                # Apply transformations - create a temporary copy to avoid modifying original
                # This is a simplification - in practice, apply_transform should be handled more carefully
                bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
                
            if self.align_to_y_axis:
                # Align to Y-axis if requested
                # This would depend on how your models are oriented initially
                pass
                
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
                
                # Restore collider if found
                if collider_obj and collider_original_loc:
                    print(f"Restoring collider {collider_obj.name} to original position: {collider_original_loc}")
                    collider_obj.location = collider_original_loc

    def center_object_to_origin(self, obj, center_mode):
        """Center an object to the world origin based on the specified mode"""
        # Store the original selection and active object
        original_active = bpy.context.view_layer.objects.active
        original_selected = [o for o in bpy.context.selected_objects]
        
        # Deselect all objects without using operators
        for scene_obj in bpy.context.view_layer.objects:
            scene_obj.select_set(False)
        
        # Select and activate our object
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        
        # Remember original location
        orig_location = obj.location.copy()
        
        if center_mode == 'ORIGIN':
            # Simply set the location to world origin
            obj.location = (0, 0, 0)
        
        elif center_mode == 'GEOMETRY':
            # Calculate the geometry center directly without using operators
            # First enter edit mode safely
            if obj.mode != 'EDIT':
                bpy.ops.object.mode_set(mode='EDIT')
            
            # Get mesh data
            mesh = obj.data
            
            if hasattr(mesh, "vertices"):
                # Calculate geometric center directly
                vert_sum = [0, 0, 0]
                vert_count = len(mesh.vertices)
                
                # Sum up all vertex positions in object's local space
                for v in mesh.vertices:
                    vert_sum[0] += v.co[0]
                    vert_sum[1] += v.co[1]
                    vert_sum[2] += v.co[2]
                
                if vert_count > 0:
                    # Get average position (geometric center)
                    geo_center = [
                        vert_sum[0] / vert_count,
                        vert_sum[1] / vert_count,
                        vert_sum[2] / vert_count
                    ]
                    
                    # Store 3D cursor location
                    cursor_loc = bpy.context.scene.cursor.location.copy()
                    
                    # Switch back to object mode
                    bpy.ops.object.mode_set(mode='OBJECT')
                    
                    # Set cursor to calculated center in world space
                    world_center = obj.matrix_world @ mathutils.Vector(geo_center)
                    bpy.context.scene.cursor.location = world_center
                    
                    # Move origin to 3D cursor
                    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
                    
                    # Reset cursor
                    bpy.context.scene.cursor.location = cursor_loc
                    
                    # Move object to world origin
                    obj.location = (0, 0, 0)
                else:
                    # If no vertices, just move object origin to world center
                    bpy.ops.object.mode_set(mode='OBJECT')
                    obj.location = (0, 0, 0)
            else:
                # If not a mesh with vertices, just set location to origin
                bpy.ops.object.mode_set(mode='OBJECT')
                obj.location = (0, 0, 0)
            
        elif center_mode == 'MASS':
            # Set origin to center of mass
            bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS')
            
            # Move to world center
            obj.location = (0, 0, 0)
        
        # Restore selection without using operators
        for scene_obj in bpy.context.view_layer.objects:
            scene_obj.select_set(False)
            
        for o in original_selected:
            if o.name in bpy.context.view_layer.objects:
                o.select_set(True)
                
        if original_active and original_active.name in bpy.context.view_layer.objects:
            bpy.context.view_layer.objects.active = original_active


# Add sidebar panel for quick access
class VIEW3D_PT_arma_reforger_tools(bpy.types.Panel):
    """Arma Reforger Tools Sidebar Panel"""
    bl_label = "AR Export"
    bl_idname = "VIEW3D_PT_arma_reforger_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'AR Export'  # This will create a new tab in the sidebar
    
    def draw(self, context):
        layout = self.layout
        
        # Export to Arma button - simplified with no options
        row = layout.row()
        row.scale_y = 2.0  # Make the button even bigger for easy access
        row.operator(ExportArmaReforgerAsset.bl_idname, text="Export to Arma", icon='EXPORT')


# Register and unregister functions
classes = (
    ExportArmaReforgerAsset,
    VIEW3D_PT_arma_reforger_tools,
)

def menu_func_export(self, context):
    self.layout.operator(ExportArmaReforgerAsset.bl_idname, text="Arma Reforger Asset (.fbx)")

# Define scene properties for the sidebar
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
    
    bpy.types.Scene.ar_export_path = StringProperty(
        name="Export Folder",
        description="Path to export FBX files",
        default="//",  # Default to blend file location
        subtype='DIR_PATH',
    )

def unregister_properties():
    del bpy.types.Scene.ar_export_mode
    del bpy.types.Scene.ar_apply_transform
    del bpy.types.Scene.ar_export_colliders
    del bpy.types.Scene.ar_preserve_armature
    del bpy.types.Scene.ar_center_to_origin
    del bpy.types.Scene.ar_export_path

def register():
    # Use try-except to handle any registration errors
    try:
        for cls in classes:
            bpy.utils.register_class(cls)
        bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
        # We're not using properties in the simplified version
        # but keeping registration in case we need them again
        register_properties()
        print("Arma Reforger Asset Exporter registered successfully")
    except Exception as e:
        print(f"Error registering Arma Reforger Asset Exporter: {str(e)}")

def unregister():
    # Use try-except to handle any unregistration errors
    try:
        bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
        unregister_properties()
        for cls in reversed(classes):
            bpy.utils.unregister_class(cls)
        print("Arma Reforger Asset Exporter unregistered successfully")
    except Exception as e:
        print(f"Error unregistering Arma Reforger Asset Exporter: {str(e)}")

if __name__ == "__main__":
    register()
