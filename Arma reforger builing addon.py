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
# Format follows the same pattern as working weapon tool sockets
# Default socket names for different building parts
BUILDING_SOCKET_NAMES = {
    "wall": "slot_building_wall_socket",
    "door": "slot_building_door_socket", 
    "window": "slot_building_window_socket",
    "roof": "slot_building_roof_socket",
    "floor": "slot_building_floor_socket",
    "stairs": "slot_building_stairs_socket",
    "column": "slot_building_column_socket",
    "railing": "slot_building_railing_socket",
    "beam": "slot_building_beam_socket",
    "other": "slot_building_part_socket"
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
# Keeping the same naming convention that works in the weapon tool
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

# Modified socket creation functions that mimic exactly what happens
# when manually creating plain axes empties in Blender

def get_memory_points_collection():
    """Get or create the Memory Points collection"""
    if "Memory Points" in bpy.data.collections:
        return bpy.data.collections["Memory Points"]
    
    # Create new collection
    memory_points = bpy.data.collections.new("Memory Points")
    
    # Link it to the scene collection
    bpy.context.scene.collection.children.link(memory_points)
    
    return memory_points


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
        
        # Add component type property
        new_obj["component_type"] = self.component_type
        
        # Create a socket empty if requested
        if self.add_socket:
            socket_name = f"{BUILDING_SOCKET_NAMES[self.component_type].lower()}_{len([o for o in bpy.data.objects if BUILDING_SOCKET_NAMES[self.component_type].lower() in o.name.lower()]) + 1}"
            socket = bpy.data.objects.new(socket_name, None)
            socket.empty_display_type = 'PLAIN_AXES'
            socket.empty_display_size = 0.05
            socket.location = world_center
            
            # Get the Memory Points collection for this socket
            memory_points = get_memory_points_collection()
            
            # Add the socket to the Memory Points collection
            memory_points.objects.link(socket)
            
            # Add socket properties (matching the pattern from weapon tools)
            socket["socket_type"] = self.component_type
            socket["attached_part"] = new_obj.name
            socket["building_part"] = "attachment_point"
            
            # DO NOT PARENT THE SOCKET - removed parenting line
        
        # Create FireGeo for the component if requested
        if self.add_firegeo:
            self._create_firegeo(context, new_obj)
        
        # Select only the new object
        bpy.ops.object.select_all(action='DESELECT')
        new_obj.select_set(True)
        context.view_layer.objects.active = new_obj
        
        self.report({'INFO'}, f"Separated component '{new_name}'" + (" with socket" if self.add_socket else ""))
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
    
    display_size: bpy.props.FloatProperty(
        name="Size",
        description="Size of the socket empty",
        default=0.05,
        min=0.01,
        max=1.0
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
        
        # Switch to Object mode if we're in Edit mode
        if current_mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # Create socket empty
        socket = bpy.data.objects.new(socket_name, None)
        socket.empty_display_type = 'PLAIN_AXES'
        socket.empty_display_size = self.display_size
        
        # Set socket location and rotation
        socket.location = socket_location
        socket.rotation_euler = socket_rotation
        
        # Get the Memory Points collection
        memory_points = get_memory_points_collection()
        
        # Add the socket to the Memory Points collection
        memory_points.objects.link(socket)
        
        # Add socket properties
        socket["socket_type"] = self.socket_type
        socket["building_part"] = "attachment_point"
        
        # DO NOT PARENT THE SOCKET - removed parenting line
        
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
        
        self.report({'INFO'}, f"Created building socket '{socket_name}' in Memory Points collection")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        
        # Socket type and name
        layout.prop(self, "socket_type")
        layout.prop(self, "custom_name")
        
        # Options
        layout.prop(self, "snap_to_face")
        layout.prop(self, "align_to_normal")
        layout.prop(self, "display_size")

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
        max=1000000
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


class ARBUILDINGS_OT_convert_existing_sockets(bpy.types.Operator):
    """Clear parent relationships from socket empties to make them compatible with Arma Reforger"""
    bl_idname = "arbuildings.convert_existing_sockets"
    bl_label = "Clear Socket Parents"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Get the Memory Points collection
        memory_points = None
        if "Memory Points" in bpy.data.collections:
            memory_points = bpy.data.collections["Memory Points"]
        else:
            self.report({'ERROR'}, "Memory Points collection not found")
            return {'CANCELLED'}
        
        # Count of modified sockets
        modified_count = 0
        
        # Process all objects in the Memory Points collection
        for obj in memory_points.objects:
            if obj.type == 'EMPTY' and obj.parent is not None:
                # Store original world matrix
                original_matrix = obj.matrix_world.copy()
                
                # Clear parent
                obj.parent = None
                
                # Restore world position/rotation
                obj.matrix_world = original_matrix
                
                modified_count += 1
        
        if modified_count > 0:
            self.report({'INFO'}, f"Cleared parent relationships for {modified_count} socket empties")
        else:
            self.report({'INFO'}, "No socket empties with parent relationships found")
            
        return {'FINISHED'}

class ARBUILDINGS_OT_manage_collections(bpy.types.Operator):
    """Create and organize collections for Arma Reforger building workflow"""
    bl_idname = "arbuildings.manage_collections"
    bl_label = "Setup AR Collections"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Create standard collections for AR building workflow
        collection_names = [
            "Memory Points",
            "Building_Components",
            "Fire_Geometries",
            "LODs"
        ]
        
        for name in collection_names:
            if name not in bpy.data.collections:
                new_collection = bpy.data.collections.new(name)
                context.scene.collection.children.link(new_collection)
                self.report({'INFO'}, f"Created collection: {name}")
        
        # Auto-organize existing objects based on naming or properties
        for obj in bpy.data.objects:
            # Memory points (sockets)
            if obj.type == 'EMPTY' and any(socket_name in obj.name.lower() for socket_name in [s.lower() for s in BUILDING_SOCKET_NAMES.values()]):
                self._move_to_collection(obj, "Memory Points")
            
            # FireGeo
            elif obj.name.startswith("UTM_") or (len(obj.keys()) > 0 and "usage" in obj and obj["usage"] == "FireGeo"):
                self._move_to_collection(obj, "Fire_Geometries")
            
            # Building components
            elif len(obj.keys()) > 0 and "component_type" in obj:
                self._move_to_collection(obj, "Building_Components")
            
            # LODs
            elif any(lod_suffix in obj.name.lower() for lod_suffix in ["_lod1", "_lod2", "_lod3"]):
                self._move_to_collection(obj, "LODs")
        
        self.report({'INFO'}, "AR collections setup complete")
        return {'FINISHED'}
    
    def _move_to_collection(self, obj, collection_name):
        """Move an object to a specific collection, removing it from others"""
        if collection_name not in bpy.data.collections:
            return
            
        target_collection = bpy.data.collections[collection_name]
        
        # Check if already in the correct collection
        for coll in obj.users_collection:
            if coll == target_collection:
                return
                
        # Link to target collection
        target_collection.objects.link(obj)
        
        # Remove from other collections
        for coll in obj.users_collection:
            if coll != target_collection:
                coll.objects.unlink(obj)

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
        
        # Collection Management
        box = layout.box()
        box.label(text="Organization", icon='OUTLINER')
        row = box.row(align=True)
        row.operator("arbuildings.manage_collections", text="Setup Collections", icon='COLLECTION_NEW')
        
        # Socket Compatibility
        box = layout.box()
        box.label(text="Compatibility Fixes", icon='TOOL_SETTINGS')
        row = box.row(align=True)
        row.operator("arbuildings.convert_existing_sockets", text="Clear Socket Parents", icon='CONSTRAINT_BONE')
        row.operator_context = 'INVOKE_DEFAULT'

# Registration
classes = (
    ARBUILDINGS_OT_separate_component,
    ARBUILDINGS_OT_create_building_socket,
    ARBUILDINGS_OT_create_firegeo_collision,
    ARBUILDINGS_OT_manage_collections,
    ARBUILDINGS_OT_convert_existing_sockets,
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
