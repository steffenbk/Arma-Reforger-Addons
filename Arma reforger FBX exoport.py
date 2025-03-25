import bpy
import os
from bpy.types import PropertyGroup, Operator, Panel
from bpy.props import (BoolProperty, StringProperty, EnumProperty, 
                      FloatVectorProperty, FloatProperty, PointerProperty)

bl_info = {
    "name": "Arma Reforger Building Exporter",
    "author": "Your Name",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > AR Export",
    "description": "Export tools for Arma Reforger buildings and structures",
    "warning": "",
    "doc_url": "",
    "category": "Import-Export",
}

class ARBuildingExportSettings(PropertyGroup):
    """Properties for the Arma Reforger Building Exporter"""
    
    # Export Directory
    export_path: StringProperty(
        name="Export Path",
        description="Directory to export building parts to",
        default="//",
        subtype='DIR_PATH',
    )
    
    # File naming options
    use_prefix: BoolProperty(
        name="Use Prefix",
        description="Add a prefix to all exported file names",
        default=False
    )
    
    prefix: StringProperty(
        name="Prefix",
        description="Prefix for all exported files",
        default="bld_"
    )
    
    use_suffix: BoolProperty(
        name="Use Suffix",
        description="Add a suffix to all exported file names",
        default=False
    )
    
    suffix: StringProperty(
        name="Suffix",
        description="Suffix for all exported files",
        default="_lod0"
    )
    
    # FBX Export Settings
    use_selection: BoolProperty(
        name="Selected Objects Only",
        description="Export only selected objects",
        default=True
    )
    
    use_active_collection: BoolProperty(
        name="Active Collection Only",
        description="Export only objects in the active collection",
        default=False
    )
    
    # Important settings for Arma Reforger
    use_triangulate: BoolProperty(
        name="Triangulate",
        description="Triangulate meshes (recommended for Arma Reforger)",
        default=True
    )
    
    preserve_edge_orientation: BoolProperty(
        name="Preserve Edge Orientation",
        description="Preserve edge orientation (recommended for Arma Reforger)",
        default=True
    )
    
    use_custom_props: BoolProperty(
        name="Export Custom Properties",
        description="Export custom properties (required for LayerPresets)",
        default=True
    )
    
    apply_modifiers: BoolProperty(
        name="Apply Modifiers",
        description="Apply modifiers before export",
        default=True
    )
    
    # Export modes
    export_mode: EnumProperty(
        name="Export Mode",
        items=[
            ('INDIVIDUAL', "Individual Objects", "Export each object as a separate file"),
            ('BY_COLLECTION', "By Collection", "Export each collection as a separate file"),
            ('BY_MATERIAL', "By Material", "Group objects by material and export each group")
        ],
        default='INDIVIDUAL'
    )
    
    # Transform options
    apply_unit_scale: BoolProperty(
        name="Apply Unit Scale",
        description="Apply unit scale for correct sizing in Arma Reforger",
        default=True
    )
    
    global_scale: FloatProperty(
        name="Scale",
        description="Scale factor for the export",
        default=1.0,
        min=0.001,
        max=1000.0
    )
    
    # Axis conversion for Arma Reforger
    axis_forward: EnumProperty(
        name="Forward Axis",
        items=[
            ('X', "X Forward", ""),
            ('Y', "Y Forward", ""),
            ('Z', "Z Forward", ""),
            ('-X', "-X Forward", ""),
            ('-Y', "-Y Forward", ""),
            ('-Z', "-Z Forward", ""),
        ],
        default='Z'
    )
    
    axis_up: EnumProperty(
        name="Up Axis",
        items=[
            ('X', "X Up", ""),
            ('Y', "Y Up", ""),
            ('Z', "Z Up", ""),
            ('-X', "-X Up", ""),
            ('-Y', "-Y Up", ""),
            ('-Z', "-Z Up", ""),
        ],
        default='Y'
    )


class EXPORT_OT_arma_reforger_building(Operator):
    """Export building parts for Arma Reforger"""
    bl_idname = "export.arma_reforger_building"
    bl_label = "Export Building Parts"
    bl_description = "Export building parts for Arma Reforger"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        settings = context.scene.ar_building_export
        
        # Check if the export path exists
        export_dir = bpy.path.abspath(settings.export_path)
        if not os.path.exists(export_dir):
            self.report({'ERROR'}, f"Export directory does not exist: {export_dir}")
            return {'CANCELLED'}
        
        # Store original selection
        original_selected = context.selected_objects
        original_active = context.active_object
        
        # Determine which objects to export based on settings
        objects_to_process = []
        
        if settings.use_selection:
            objects_to_process = [obj for obj in context.selected_objects if obj.type == 'MESH']
        elif settings.use_active_collection:
            objects_to_process = [obj for obj in context.collection.objects if obj.type == 'MESH']
        else:
            objects_to_process = [obj for obj in context.scene.objects if obj.type == 'MESH']
        
        if not objects_to_process:
            self.report({'ERROR'}, "No mesh objects found to export")
            return {'CANCELLED'}
        
        # Track successfully exported files
        exported_count = 0
        
        # Process objects based on export mode
        if settings.export_mode == 'INDIVIDUAL':
            for obj in objects_to_process:
                # Deselect all
                bpy.ops.object.select_all(action='DESELECT')
                
                # Select only this object
                obj.select_set(True)
                context.view_layer.objects.active = obj
                
                # Generate filename
                filename = self.generate_filename(obj.name, settings)
                filepath = os.path.join(export_dir, filename)
                
                # Export the object
                self.export_fbx(filepath, settings)
                exported_count += 1
                
        elif settings.export_mode == 'BY_COLLECTION':
            # Get all collections with objects to process
            collections_dict = {}
            
            for obj in objects_to_process:
                for collection in obj.users_collection:
                    if collection not in collections_dict:
                        collections_dict[collection] = []
                    collections_dict[collection].append(obj)
            
            # Export each collection separately
            for collection, objects in collections_dict.items():
                # Deselect all
                bpy.ops.object.select_all(action='DESELECT')
                
                # Select objects in this collection
                for obj in objects:
                    obj.select_set(True)
                
                if context.selected_objects:
                    context.view_layer.objects.active = context.selected_objects[0]
                    
                    # Generate filename
                    filename = self.generate_filename(collection.name, settings)
                    filepath = os.path.join(export_dir, filename)
                    
                    # Export the collection
                    self.export_fbx(filepath, settings)
                    exported_count += 1
                
        elif settings.export_mode == 'BY_MATERIAL':
            # Group objects by material
            material_dict = {}
            
            for obj in objects_to_process:
                if len(obj.material_slots) > 0:
                    # Use the first material as the grouping key
                    mat = obj.material_slots[0].material
                    if mat:
                        mat_name = mat.name
                        if mat_name not in material_dict:
                            material_dict[mat_name] = []
                        material_dict[mat_name].append(obj)
                else:
                    # Handle objects with no material
                    if "No_Material" not in material_dict:
                        material_dict["No_Material"] = []
                    material_dict["No_Material"].append(obj)
            
            # Export each material group separately
            for mat_name, objects in material_dict.items():
                # Deselect all
                bpy.ops.object.select_all(action='DESELECT')
                
                # Select objects with this material
                for obj in objects:
                    obj.select_set(True)
                
                if context.selected_objects:
                    context.view_layer.objects.active = context.selected_objects[0]
                    
                    # Generate filename
                    filename = self.generate_filename(mat_name, settings)
                    filepath = os.path.join(export_dir, filename)
                    
                    # Export the material group
                    self.export_fbx(filepath, settings)
                    exported_count += 1
        
        # Restore original selection
        bpy.ops.object.select_all(action='DESELECT')
        for obj in original_selected:
            obj.select_set(True)
        if original_active:
            context.view_layer.objects.active = original_active
        
        self.report({'INFO'}, f"Successfully exported {exported_count} FBX files")
        return {'FINISHED'}
    
    def generate_filename(self, base_name, settings):
        """Generate a filename based on settings"""
        clean_name = bpy.path.clean_name(base_name)
        
        if settings.use_prefix:
            clean_name = settings.prefix + clean_name
            
        if settings.use_suffix:
            clean_name = clean_name + settings.suffix
            
        return clean_name + ".fbx"
    
    def export_fbx(self, filepath, settings):
        """Export the selected objects to FBX with proper Arma Reforger settings"""
        # FBX export with optimized settings for Arma Reforger
        bpy.ops.export_scene.fbx(
            filepath=filepath,
            use_selection=True,
            use_active_collection=False,
            global_scale=settings.global_scale,
            apply_unit_scale=settings.apply_unit_scale,
            apply_scale_options='FBX_SCALE_ALL',
            use_space_transform=True,
            bake_space_transform=False,
            object_types={'MESH', 'EMPTY'},
            use_mesh_modifiers=settings.apply_modifiers,
            mesh_smooth_type='FACE',
            use_mesh_edges=False,
            use_tspace=False,
            use_custom_props=settings.use_custom_props,
            add_leaf_bones=False,
            primary_bone_axis='Y',
            secondary_bone_axis='X',
            use_armature_deform_only=True,
            armature_nodetype='NULL',
            axis_forward=settings.axis_forward,
            axis_up=settings.axis_up,
            path_mode='AUTO',
            embed_textures=False,
            batch_mode='OFF',
            use_metadata=True,
            # Arma Reforger specific settings
            use_triangles=settings.use_triangulate
        )
        return True


class VIEW3D_PT_arma_reforger_building_export(Panel):
    """Panel for Arma Reforger Building Export"""
    bl_label = "AR Building Export"
    bl_idname = "VIEW3D_PT_arma_reforger_building_export"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "AR Export"
    
    def draw(self, context):
        layout = self.layout
        settings = context.scene.ar_building_export
        
        # Main export button
        row = layout.row()
        row.scale_y = 1.5
        row.operator("export.arma_reforger_building", icon='EXPORT')
        
        # Export path
        box = layout.box()
        box.label(text="Export Location", icon='FOLDER_REDIRECT')
        box.prop(settings, "export_path", text="")
        
        # File naming options
        box = layout.box()
        box.label(text="File Naming", icon='FILE')
        
        # Prefix
        row = box.row()
        row.prop(settings, "use_prefix", text="")
        sub = row.row()
        sub.enabled = settings.use_prefix
        sub.prop(settings, "prefix")
        
        # Suffix
        row = box.row()
        row.prop(settings, "use_suffix", text="")
        sub = row.row()
        sub.enabled = settings.use_suffix
        sub.prop(settings, "suffix")
        
        # Export Mode
        box = layout.box()
        box.label(text="Export Settings", icon='SETTINGS')
        box.prop(settings, "export_mode")
        
        # Object selection options
        box.separator()
        row = box.row()
        row.prop(settings, "use_selection", text="Selected Only")
        row = box.row()
        row.enabled = not settings.use_selection
        row.prop(settings, "use_active_collection", text="Active Collection Only")
        
        # Arma Reforger critical settings
        box = layout.box()
        box.label(text="Arma Reforger Settings", icon='MOD_ARMATURE')
        box.prop(settings, "use_triangulate")
        box.prop(settings, "preserve_edge_orientation")
        box.prop(settings, "use_custom_props")
        box.prop(settings, "apply_modifiers")
        
        # Transform settings
        box = layout.box()
        box.label(text="Transform", icon='ORIENTATION_GLOBAL')
        box.prop(settings, "global_scale")
        box.prop(settings, "apply_unit_scale")
        box.prop(settings, "axis_forward")
        box.prop(settings, "axis_up")


class VIEW3D_PT_arma_reforger_building_help(Panel):
    """Help panel for Arma Reforger Building Export"""
    bl_label = "Help & Tips"
    bl_idname = "VIEW3D_PT_arma_reforger_building_help"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "AR Buildings"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        
        box = layout.box()
        box.label(text="Critical Settings for Arma Reforger:", icon='ERROR')
        col = box.column(align=True)
        col.label(text="• Binary format in 2014/2015")
        col.label(text="• Triangulation enabled")
        col.label(text="• Preserve Edge Orientation")
        col.label(text="• Custom Properties enabled")
        
        box = layout.box()
        box.label(text="Export Modes:", icon='PRESET')
        col = box.column(align=True)
        col.label(text="Individual: Export each object separately")
        col.label(text="By Collection: Export objects grouped by collection")
        col.label(text="By Material: Export objects grouped by material")
        
        box = layout.box()
        box.label(text="Recommended Workflow:", icon='SEQUENCE')
        col = box.column(align=True)
        col.label(text="1. Organize building parts into collections")
        col.label(text="2. Apply proper materials to each part")
        col.label(text="3. Set up custom properties if needed")
        col.label(text="4. Select the parts to export")
        col.label(text="5. Choose export mode and run export")


# Registration
classes = (
    ARBuildingExportSettings,
    EXPORT_OT_arma_reforger_building,
    VIEW3D_PT_arma_reforger_building_export,
    VIEW3D_PT_arma_reforger_building_help
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.ar_building_export = PointerProperty(type=ARBuildingExportSettings)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.ar_building_export

if __name__ == "__main__":
    register()