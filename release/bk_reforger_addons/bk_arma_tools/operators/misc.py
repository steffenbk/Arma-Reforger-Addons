import bpy
import bmesh
import math
from mathutils import Vector

class ARVEHICLES_OT_setup_skinning(bpy.types.Operator):
    bl_idname = "arvehicles.setup_skinning"
    bl_label = "Setup Vehicle Skinning"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        armature = None
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
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
            if obj.type == 'ARMATURE':
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
            if obj.type == 'ARMATURE':
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
            if obj.type == 'ARMATURE':
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
