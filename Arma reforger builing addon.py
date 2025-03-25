# -*- coding: utf-8 -*-
"""
Created on Tue Mar 25 14:30:45 2025

@author: Steffen & Claude
"""

bl_info = {
    "name": "Arma Reforger Building Destruction Tools",
    "author": "Steffen & Claude",
    "version": (1, 0),
    "blender": (2, 93, 0),
    "location": "View3D > Sidebar > AR Buildings",
    "description": "Tools for preparing destructible buildings for Arma Reforger",
    "warning": "",
    "doc_url": "",
    "category": "Object",
}

import bpy
import math
import random
from mathutils import Vector, Matrix
import bmesh

# Default socket names for different building parts
BUILDING_SOCKET_NAMES = {
    "wall": "BLD_WALL_SOCKET",
    "door": "BLD_DOOR_SOCKET", 
    "window": "BLD_WINDOW_SOCKET",
    "roof": "BLD_ROOF_SOCKET",
    "floor": "BLD_FLOOR_SOCKET",
    "stairs": "BLD_STAIRS_SOCKET",
    "column": "BLD_COLUMN_SOCKET",
    "railing": "BLD_RAILING_SOCKET",
    "beam": "BLD_BEAM_SOCKET",
    "other": "BLD_PART_SOCKET"
}

# Building part types for separation and socket creation
BUILDING_PART_TYPES = [
    ('wall', "Wall", "Wall component"),
    ('door', "Door", "Door component"),
    ('window', "Window", "Window component"),
    ('roof', "Roof", "Roof component"),
    ('floor', "Floor", "Floor component"),
    ('stairs', "Stairs", "Stairs component"),
    ('column', "Column", "Column or support beam"),
    ('railing', "Railing", "Railing component"),
    ('beam', "Beam", "Structural beam"),
    ('other', "Other", "Other component type"),
]

# Vehicle part types
VEHICLE_PART_TYPES = [
    ('window', "Window", "Vehicle window"),
    ('light', "Light", "Vehicle light"),
    ('door', "Door", "Vehicle door"),
    ('wheel', "Wheel", "Vehicle wheel"),
    ('engine', "Engine", "Vehicle engine"),
    ('exhaust', "Exhaust", "Vehicle exhaust"),
    ('seat', "Seat", "Vehicle seat"),
    ('steering', "Steering", "Vehicle steering"),
    ('accessory', "Accessory", "Vehicle accessory"),
    ('other', "Other", "Other vehicle part"),
]

# Socket names for vehicle parts
VEHICLE_SOCKET_NAMES = {
    "window": "VEHICLE_WINDOW_SOCKET",
    "light": "VEHICLE_LIGHT_SOCKET",
    "door": "VEHICLE_DOOR_SOCKET",
    "wheel": "VEHICLE_WHEEL_SOCKET",
    "engine": "VEHICLE_ENGINE_SOCKET",
    "exhaust": "VEHICLE_EXHAUST_SOCKET",
    "seat": "VEHICLE_SEAT_SOCKET",
    "steering": "VEHICLE_STEERING_SOCKET",
    "accessory": "VEHICLE_ACCESSORY_SOCKET",
    "other": "VEHICLE_PART_SOCKET"
}

class ARBUILDINGS_OT_separate_component(bpy.types.Operator):
    """Separate selected component and add appropriate socket"""
    bl_idname = "arbuildings.separate_component"
    bl_label = "Separate Building Component"
    bl_options = {'REGISTER', 'UNDO'}
    
    component_type: bpy.props.EnumProperty(
        name="Component Type",
        description="Type of building component being separated",
        items=BUILDING_PART_TYPES,
        default='wall'
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
    
    add_firegeo: bpy.props.BoolProperty(
        name="Add FireGeo",
        description="Add a FireGeo collision mesh for the component",
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
        prefix = f"{self.component_type}_"
        new_name = self.custom_name if self.custom_name else f"{prefix}{obj.name}"
        
        # Separate the selected faces
        bpy.ops.mesh.separate(type='SELECTED')
        
        # Exit edit mode to work with the new object
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Get the newly created object (last selected)
        new_obj = context.selected_objects[-1]
        new_obj.name = new_name
        
        # Store the original world matrix before any parenting
        original_matrix_world = new_obj.matrix_world.copy()
        
        # Add component type property
        new_obj["component_type"] = self.component_type
        
        # Create a socket empty if requested
        if self.add_socket:
            socket_name = f"{BUILDING_SOCKET_NAMES[self.component_type]}_{len([o for o in bpy.data.objects if BUILDING_SOCKET_NAMES[self.component_type] in o.name]) + 1}"
            
            socket = bpy.data.objects.new(socket_name, None)
            socket.empty_display_type = 'ARROWS'
            socket.empty_display_size = 0.2
            socket.location = world_center
            
            # Add the socket to the current collection
            context.collection.objects.link(socket)
            
            # Parent the socket to the original building
            socket.parent = obj
            
            # Parent the new component to the socket (keeping world transform)
            # First clear parent if any
            bpy.ops.object.select_all(action='DESELECT')
            new_obj.select_set(True)
            context.view_layer.objects.active = new_obj
            
            # Parent to socket but keep transform
            new_obj.parent = socket
            new_obj.matrix_world = original_matrix_world
            
            # Add socket properties
            socket["socket_type"] = self.component_type
            socket["attached_part"] = new_obj.name
        
        # Create FireGeo for the component if requested
        if self.add_firegeo:
            self._create_firegeo(context, new_obj)
        
        # Select only the new object
        bpy.ops.object.select_all(action='DESELECT')
        new_obj.select_set(True)
        context.view_layer.objects.active = new_obj
        
        self.report({'INFO'}, f"Separated component '{new_name}' with socket")
        return {'FINISHED'}
    
    def _create_firegeo(self, context, obj):
        """Create a simplified FireGeo collision mesh for the component"""
        # Store original world matrix
        original_matrix_world = obj.matrix_world.copy()
        
        # Duplicate the object
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj
        bpy.ops.object.duplicate()
        
        firegeo_obj = context.active_object
        firegeo_obj.name = f"UTM_{obj.name}"
        
        # Apply decimate modifier to simplify
        decimate = firegeo_obj.modifiers.new(name="Decimate", type='DECIMATE')
        decimate.ratio = 0.5  # Adjust as needed
        bpy.ops.object.modifier_apply(modifier=decimate.name)
        
        # Add a slight offset
        solidify = firegeo_obj.modifiers.new(name="Solidify", type='SOLIDIFY')
        solidify.thickness = 0.01
        solidify.offset = 1.0  # Expand outward
        bpy.ops.object.modifier_apply(modifier=solidify.name)
        
        # Create a material for FireGeo
        if "FireGeo_Material" not in bpy.data.materials:
            mat = bpy.data.materials.new(name="FireGeo_Material")
            mat.diffuse_color = (0.0, 0.8, 0.0, 0.5)  # Semi-transparent green
        else:
            mat = bpy.data.materials["FireGeo_Material"]
        
        # Assign material
        firegeo_obj.data.materials.clear()
        firegeo_obj.data.materials.append(mat)
        
        # Set layer_preset custom property
        firegeo_obj["layer_preset"] = "Collision_Building"
        firegeo_obj["usage"] = "FireGeo"
        
        # Parent to the original component, keeping world transform
        firegeo_obj.parent = obj
        firegeo_obj.matrix_world = original_matrix_world
        
        return firegeo_obj
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=350)
    
    def draw(self, context):
        layout = self.layout
        
        # Component type and name
        layout.prop(self, "component_type")
        layout.prop(self, "custom_name")
        
        # Socket and FireGeo options
        layout.prop(self, "add_socket")
        layout.prop(self, "add_firegeo")
        
class ARBUILDINGS_OT_create_building_socket(bpy.types.Operator):
    """Create a socket empty for building component attachment"""
    bl_idname = "arbuildings.create_socket"
    bl_label = "Create Building Socket"
    bl_options = {'REGISTER', 'UNDO'}
    
    socket_type: bpy.props.EnumProperty(
        name="Socket Type",
        description="Type of building socket to create",
        items=BUILDING_PART_TYPES,
        default='wall'
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
        # Get the active object (building)
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
            socket_name = f"{BUILDING_SOCKET_NAMES[self.socket_type]}_{len([o for o in bpy.data.objects if BUILDING_SOCKET_NAMES[self.socket_type] in o.name]) + 1}"
        
        # Create socket empty
        socket = bpy.data.objects.new(socket_name, None)
        socket.empty_display_type = 'ARROWS'
        socket.empty_display_size = 0.2
        
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
        
        # Parent the socket to the building
        socket.parent = obj
        
        # Add socket properties
        socket["socket_type"] = self.socket_type
        
        # Switch to Object mode if we're in Edit mode
        if current_mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')
            
        # Now we can safely select objects
        for obj in context.selected_objects:
            obj.select_set(False)
        
        socket.select_set(True)
        context.view_layer.objects.active = socket
        
        # Restore previous mode if needed - but only if the active object supports edit mode
        if current_mode == 'EDIT_MESH':
            # Check if original object is still available and is a mesh
            if obj and obj.type == 'MESH':
                # Set original object as active again
                context.view_layer.objects.active = obj
                bpy.ops.object.mode_set(mode='EDIT')
            # Otherwise, stay in object mode
            else:
                self.report({'WARNING'}, "Couldn't restore edit mode, original object no longer available")
        
        self.report({'INFO'}, f"Created building socket '{socket_name}'")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class ARBUILDINGS_OT_create_firegeo_collision(bpy.types.Operator):
    """Create FireGeo collision mesh for building components"""
    bl_idname = "arbuildings.create_firegeo_collision"
    bl_label = "Create Building FireGeo"
    bl_options = {'REGISTER', 'UNDO'}
    
    method: bpy.props.EnumProperty(
        name="Method",
        description="Method to create FireGeo collision",
        items=[
            ('CONVEX', "Convex Hull (Stable)", "Create a simplified convex hull - stable even with high-poly models"),
            ('DETAILED', "Detailed (Better Shape)", "Create a more detailed shape that better preserves features"),
        ],
        default='CONVEX'
    )
    
    target_faces: bpy.props.IntProperty(
        name="Target Faces",
        description="Target number of faces for the collision mesh",
        default=100,
        min=20,
        max=500
    )
    
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
            self.report({'ERROR'}, "Please select building components to create FireGeo for")
            return {'CANCELLED'}
        
        # Find all mesh objects in selection
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not mesh_objects:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}
        
        # Create FireGeo for each selected mesh
        created_count = 0
        for obj in mesh_objects:
            # Skip if it already has a FireGeo child
            if any(child.name.startswith("UTM_") for child in obj.children):
                continue
                
            # Create a new object that will become our collision mesh
            collision_mesh = bpy.data.meshes.new(f"UTM_{obj.name}_mesh")
            fire_geo_obj = bpy.data.objects.new(f"UTM_{obj.name}", collision_mesh)
            context.collection.objects.link(fire_geo_obj)
            
            # Based on the selected method, create different collision
            if self.method == 'CONVEX':
                self._create_convex_hull(context, obj, fire_geo_obj)
            else:  # DETAILED
                self._create_detailed(context, obj, fire_geo_obj)
            
            # Parent to the original object
            fire_geo_obj.parent = obj
            
            # Create and assign material
            if "FireGeo_Material" not in bpy.data.materials:
                mat = bpy.data.materials.new(name="FireGeo_Material")
                mat.diffuse_color = (0.0, 0.8, 0.0, 0.5)  # Semi-transparent green
            else:
                mat = bpy.data.materials["FireGeo_Material"]
            
            # Remove any existing materials and assign the new one
            fire_geo_obj.data.materials.clear()
            fire_geo_obj.data.materials.append(mat)
            
            # Set layer_preset custom property
            fire_geo_obj["layer_preset"] = "Collision_Building"
            fire_geo_obj["usage"] = "FireGeo"
            
            created_count += 1
        
        # Report success
        if created_count > 0:
            self.report({'INFO'}, f"Created {created_count} FireGeo collision meshes")
        else:
            self.report({'INFO'}, "No new FireGeo meshes created (components might already have them)")
            
        return {'FINISHED'}
    
    def _create_convex_hull(self, context, source_obj, fire_geo_obj):
        """Create a convex hull based FireGeo collision"""
        # Get vertices from the source object
        all_verts = []
        
        # If too many vertices, sample them to prevent crashes
        if len(source_obj.data.vertices) > 1000:
            sample_rate = min(1.0, 500 / len(source_obj.data.vertices))
            for i, vert in enumerate(source_obj.data.vertices):
                if i % int(1/sample_rate) == 0:  # Sample vertices
                    world_co = source_obj.matrix_world @ vert.co
                    all_verts.append(world_co)
        else:
            for vert in source_obj.data.vertices:
                world_co = source_obj.matrix_world @ vert.co
                all_verts.append(world_co)
        
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
        if len(temp_obj.data.polygons) > self.target_faces:
            decimate = temp_obj.modifiers.new(name="Decimate", type='DECIMATE')
            decimate.ratio = self.target_faces / len(temp_obj.data.polygons)
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
    
    def _create_detailed(self, context, source_obj, fire_geo_obj):
        """Create a detailed FireGeo collision that preserves more building features"""
        # Duplicate the source object mesh
        temp_mesh = source_obj.data.copy()
        temp_obj = bpy.data.objects.new("temp_detailed", temp_mesh)
        context.collection.objects.link(temp_obj)
        
        # Select and make active the temporary object
        bpy.ops.object.select_all(action='DESELECT')
        temp_obj.select_set(True)
        context.view_layer.objects.active = temp_obj
        
        # Apply decimate modifier for simplification
        decimate = temp_obj.modifiers.new(name="Decimate", type='DECIMATE')
        current_faces = len(temp_obj.data.polygons)
        decimate.ratio = min(1.0, self.target_faces / max(1, current_faces))
        bpy.ops.object.modifier_apply(modifier=decimate.name)
        
        # If offset is specified, add a solidify modifier
        if self.offset > 0:
            # Apply solidify modifier
            solidify = temp_obj.modifiers.new(name="Solidify", type='SOLIDIFY')
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
        
        # Transfer data to the FireGeo object
        fire_geo_obj.data = temp_obj.data.copy()
        
        # Remove the temporary object
        bpy.data.objects.remove(temp_obj)
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class ARBUILDINGS_OT_create_dependency_link(bpy.types.Operator):
    """Create structural dependency between building parts"""
    bl_idname = "arbuildings.create_dependency"
    bl_label = "Create Structural Dependency"
    bl_options = {'REGISTER', 'UNDO'}
    
    dependency_type: bpy.props.EnumProperty(
        name="Dependency Type",
        description="Type of structural dependency",
        items=[
            ('support', "Support", "Selected part supports dependent part"),
            ('attachment', "Attachment", "Selected part is attached to dependent part"),
            ('adjacent', "Adjacent", "Parts are adjacent and affect each other"),
        ],
        default='support'
    )
    
    def execute(self, context):
        selected_objects = context.selected_objects
        
        # Need at least two objects selected
        if len(selected_objects) < 2:
            self.report({'ERROR'}, "Please select at least two building parts")
            return {'CANCELLED'}
        
        # The active object is the supporting/main part
        active_obj = context.active_object
        if not active_obj or active_obj not in selected_objects:
            self.report({'ERROR'}, "No active object among selected objects")
            return {'CANCELLED'}
        
        # Create dependencies
        dependency_count = 0
        for obj in selected_objects:
            if obj != active_obj:
                # Add dependency property to the dependent object
                if "dependencies" not in obj:
                    obj["dependencies"] = []
                
                # Create a new dependency
                dependency = {
                    "supporting_part": active_obj.name,
                    "dependency_type": self.dependency_type
                }
                
                # Check if this dependency already exists
                existing_deps = obj["dependencies"]
                if isinstance(existing_deps, list):
                    # Check if already exists
                    if not any(d.get("supporting_part") == active_obj.name for d in existing_deps):
                        existing_deps.append(dependency)
                        obj["dependencies"] = existing_deps
                        dependency_count += 1
                else:
                    # Initialize as a new list
                    obj["dependencies"] = [dependency]
                    dependency_count += 1
                
                # Also update the supporting part to know it supports something
                if "supports" not in active_obj:
                    active_obj["supports"] = []
                
                # Add the supported object to the list
                support_info = {
                    "supported_part": obj.name,
                    "dependency_type": self.dependency_type
                }
                
                # Check if this support relationship already exists
                existing_supports = active_obj["supports"]
                if isinstance(existing_supports, list):
                    if not any(s.get("supported_part") == obj.name for s in existing_supports):
                        existing_supports.append(support_info)
                        active_obj["supports"] = existing_supports
                else:
                    active_obj["supports"] = [support_info]
        
        if dependency_count > 0:
            self.report({'INFO'}, f"Created {dependency_count} dependencies")
        else:
            self.report({'WARNING'}, "No new dependencies created, they may already exist")
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
class ARBUILDINGS_OT_visualize_dependencies(bpy.types.Operator):
    """Create visual indicators of structural dependencies"""
    bl_idname = "arbuildings.visualize_dependencies"
    bl_label = "Visualize Dependencies"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Get all objects in the scene
        all_objects = context.scene.objects
        
        # Find all building parts with dependencies
        parts_with_deps = [obj for obj in all_objects if "dependencies" in obj and obj.get("dependencies")]
        
        if not parts_with_deps:
            self.report({'INFO'}, "No building parts with dependencies found")
            return {'CANCELLED'}
        
        # Create a new collection for visualizers if it doesn't exist
        collection_name = "Dependency_Visualizers"
        if collection_name in bpy.data.collections:
            vis_collection = bpy.data.collections[collection_name]
            # Clear existing visualizers
            for obj in list(vis_collection.objects):
                bpy.data.objects.remove(obj)
        else:
            vis_collection = bpy.data.collections.new(collection_name)
            context.scene.collection.children.link(vis_collection)
        
        # Create a material for the dependency visualizers
        if "Dependency_Material" not in bpy.data.materials:
            mat = bpy.data.materials.new(name="Dependency_Material")
            mat.diffuse_color = (1.0, 0.6, 0.0, 0.5)  # Semi-transparent orange
        else:
            mat = bpy.data.materials["Dependency_Material"]
        
        # Create visualizers for each dependency
        created_count = 0
        for part in parts_with_deps:
            dependencies = part.get("dependencies")
            if not dependencies or not isinstance(dependencies, list):
                continue
                
            for dep in dependencies:
                if not isinstance(dep, dict):
                    continue
                
                supporting_name = dep.get("supporting_part")
                if not supporting_name:
                    continue
                
                # Find the supporting part
                supporting_part = next((obj for obj in all_objects if obj.name == supporting_name), None)
                if not supporting_part:
                    continue
                
                # Create a line between the parts
                visualizer = self._create_dependency_line(part, supporting_part, dep.get("dependency_type", "support"))
                
                if visualizer:
                    # Add to collection
                    vis_collection.objects.link(visualizer)
                    
                    # Assign material
                    visualizer.data.materials.append(mat)
                    
                    created_count += 1
        
        if created_count > 0:
            self.report({'INFO'}, f"Created {created_count} dependency visualizers")
        else:
            self.report({'WARNING'}, "No dependency visualizers created")
        
        return {'FINISHED'}
    
    def _create_dependency_line(self, dependent_part, supporting_part, dependency_type):
        """Create a line object between dependent and supporting parts"""
        # Calculate centers
        dep_center = dependent_part.location
        sup_center = supporting_part.location
        
        # Calculate midpoint
        midpoint = (dep_center + sup_center) / 2
        
        # Calculate distance
        distance = (dep_center - sup_center).length
        
        # Create a cylinder between the points
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.02,
            depth=distance,
            location=midpoint
        )
        
        # Get the created cylinder
        cylinder = bpy.context.active_object
        
        # Name based on parts and dependency type
        cylinder.name = f"Dependency_{dependent_part.name}_to_{supporting_part.name}"
        
        # Rotate to point from dependent to supporting
        direction = (sup_center - dep_center).normalized()
        
        # Calculate rotation to align cylinder with the direction
        # Default cylinder is aligned with Z axis, so we need to rotate it to align with our direction
        z_axis = Vector((0, 0, 1))
        rotation_axis = z_axis.cross(direction).normalized()
        
        if rotation_axis.length > 0.001:  # Avoid zero-length rotation axis
            angle = z_axis.angle(direction)
            cylinder.rotation_euler = Matrix.Rotation(angle, 4, rotation_axis).to_euler()
        
        # Set properties to identify the visualizer
        cylinder["vis_type"] = "dependency"
        cylinder["dependent_part"] = dependent_part.name
        cylinder["supporting_part"] = supporting_part.name
        cylinder["dependency_type"] = dependency_type
        
        return cylinder
    
class ARVEHICLES_OT_create_vehicle_socket(bpy.types.Operator):
    """Create a socket empty for vehicle component attachment"""
    bl_idname = "arvehicles.create_socket"
    bl_label = "Create Vehicle Socket"
    bl_options = {'REGISTER', 'UNDO'}
    
    socket_type: bpy.props.EnumProperty(
        name="Socket Type",
        description="Type of vehicle socket to create",
        items=VEHICLE_PART_TYPES,
        default='wheel'
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
    
    def execute(self, context):
        # Get the active object (vehicle)
        obj = context.active_object
        
        if not obj:
            self.report({'ERROR'}, "No active object selected")
            return {'CANCELLED'}
        
        # Generate socket name
        if self.custom_name:
            socket_name = self.custom_name
        else:
            socket_name = f"{VEHICLE_SOCKET_NAMES[self.socket_type]}_{len([o for o in bpy.data.objects if VEHICLE_SOCKET_NAMES[self.socket_type] in o.name]) + 1}"
        
        # Create socket empty
        socket = bpy.data.objects.new(socket_name, None)
        socket.empty_display_type = 'ARROWS'
        socket.empty_display_size = 0.2
        
        # Default location is at the object's location
        socket.location = obj.location.copy()
        
        # If in edit mode, try to snap to the selected face
        if context.mode == 'EDIT_MESH' and self.snap_to_face:
            mesh = obj.data
            bm = bmesh.from_edit_mesh(mesh)
            selected_faces = [f for f in bm.faces if f.select]
            
            if selected_faces:
                # Get the active face
                active_face = selected_faces[0]
                
                # Calculate face center
                face_center = active_face.calc_center_median()
                socket.location = obj.matrix_world @ face_center
        
        # Add the socket to the current collection
        context.collection.objects.link(socket)
        
        # Parent the socket to the vehicle
        socket.parent = obj
        
        # Add socket properties
        socket["socket_type"] = self.socket_type
        
        # Select the socket
        bpy.ops.object.select_all(action='DESELECT')
        socket.select_set(True)
        context.view_layer.objects.active = socket
        
        self.report({'INFO'}, f"Created vehicle socket '{socket_name}'")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class ARBUILDINGS_PT_panel(bpy.types.Panel):
    """Arma Reforger Building Destruction Panel"""
    bl_label = "AR Buildings"
    bl_idname = "ARBUILDINGS_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'AR Buildings'
    
    def draw(self, context):
        layout = self.layout
        
        # Component Separation
        box = layout.box()
        box.label(text="Component Tools", icon='MOD_BUILD')
        row = box.row(align=True)
        row.operator("arbuildings.separate_component", text="Separate Component", icon='UNLINKED')
        row = box.row(align=True)
        row.operator("arbuildings.create_socket", text="Create Socket", icon='EMPTY_AXIS')
        
        # Collision Creation
        box = layout.box()
        box.label(text="Collision Tools", icon='MESH_CUBE')
        box.operator("arbuildings.create_firegeo_collision", icon='MESH_GRID')
        
        # Dependency Management
        box = layout.box()
        box.label(text="Structural Dependencies", icon='CONSTRAINT')
        box.operator("arbuildings.create_dependency", icon='LINKED')
        box.operator("arbuildings.visualize_dependencies", icon='HIDE_OFF')
        
        # Vehicle attachment points
        box = layout.box()
        box.label(text="Vehicle Attachment Points", icon='EMPTY_DATA')
        box.operator("arvehicles.create_socket", icon='EMPTY_ARROWS')

# Registration
classes = (
    ARBUILDINGS_OT_separate_component,
    ARBUILDINGS_OT_create_building_socket,
    ARBUILDINGS_OT_create_firegeo_collision,
    ARBUILDINGS_OT_create_dependency_link,
    ARBUILDINGS_OT_visualize_dependencies,
    ARVEHICLES_OT_create_vehicle_socket,
    ARBUILDINGS_PT_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()