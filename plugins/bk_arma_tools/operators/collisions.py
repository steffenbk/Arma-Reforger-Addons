import bpy
import bmesh
import math
import re
from mathutils import Vector


class ARVEHICLES_OT_create_ucx_collision(bpy.types.Operator):
    bl_idname = "arvehicles.create_ucx_collision"
    bl_label = "Create Collision"
    bl_options = {'REGISTER', 'UNDO'}
    
    method: bpy.props.EnumProperty(
        name="Method",
        items=[
            ('UCX', "Convex", "UCX convex collision"),
            ('UCL', "Cylinder", "UCL cylinder collision"),
            ('UBX', "Box", "UBX box collision"),
            ('USP', "Sphere", "USP sphere collision"),
        ],
        default='UCX'
    )
    
    target_faces: bpy.props.IntProperty(
        name="Target Faces", 
        default=50, 
        min=12, 
        max=200,
        description="Target face count for UCX collisions"
    )
    
    layer_preset: bpy.props.EnumProperty(
        name="Layer Preset",
        description="Collision layer preset",
        items=[
            ('Vehicle', "Vehicle", "Standard vehicle collision"),
            ('Collision_Vehicle', "Collision Vehicle", "Vehicle physics collision"),
            ('MineTrigger', "Mine Trigger", "Mine detection trigger (for wheels)"),
            ('FireGeo', "FireGeo", "Fire geometry"),
            ('Custom', "Custom", "Custom layer preset"),
        ],
        default='Vehicle'
    )
    
    custom_layer_preset: bpy.props.StringProperty(
        name="Custom Layer",
        description="Custom layer preset name",
        default=""
    )
    
    parent_to_bone: bpy.props.BoolProperty(
        name="Parent to Bone",
        description="Parent collision to a specific bone",
        default=False
    )
    
    bone_name: bpy.props.StringProperty(
        name="Bone Name",
        description="Name of bone to parent to (e.g., v_wheel_L02)",
        default=""
    )
    
    def execute(self, context):
        if not context.selected_objects:
            self.report({'ERROR'}, "No objects selected")
            return {'CANCELLED'}
        
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not mesh_objects:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}
        
        collision_objects = []
        
        for idx, source_obj in enumerate(mesh_objects):
            collision_obj = self._create_collision(source_obj, idx, len(mesh_objects))
            if collision_obj:
                collision_objects.append(collision_obj)
        
        bpy.ops.object.select_all(action='DESELECT')
        for obj in collision_objects:
            obj.select_set(True)
        
        if collision_objects:
            context.view_layer.objects.active = collision_objects[0]
        
        self.report({'INFO'}, f"Created {len(collision_objects)} {self.method} collision(s)")
        return {'FINISHED'}
    
    def _create_collision(self, source_obj, idx, total_objects):
        if total_objects == 1:
            name = f"{self.method}_body"
        else:
            name = f"{self.method}_body_part_{idx:02d}"
        
        if self.method == 'UCX':
            return self._create_ucx_collision(source_obj, name)
        else:
            return self._create_primitive_collision(source_obj, name)
    
    def _create_ucx_collision(self, source_obj, name):
        bpy.ops.object.select_all(action='DESELECT')
        source_obj.select_set(True)
        bpy.context.view_layer.objects.active = source_obj
        
        bpy.ops.object.duplicate()
        collision_obj = bpy.context.active_object
        collision_obj.name = name
        
        face_count = len(collision_obj.data.polygons)
        if face_count > self.target_faces * 2:
            self._apply_decimation(collision_obj, max(0.1, (self.target_faces * 2) / face_count))
        
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.convex_hull()
        bpy.ops.object.mode_set(mode='OBJECT')
        
        face_count = len(collision_obj.data.polygons)
        if face_count > self.target_faces:
            self._apply_decimation(collision_obj, max(0.7, self.target_faces / face_count))
        
        self._fix_non_planar_faces(collision_obj)
        self._apply_collision_properties(collision_obj)
        
        return collision_obj
    
    def _create_primitive_collision(self, source_obj, name):
        bbox_center = sum((source_obj.matrix_world @ Vector(corner) for corner in source_obj.bound_box), Vector()) / 8
        dims = source_obj.dimensions
        
        bpy.ops.object.select_all(action='DESELECT')
        
        if self.method == 'UCL':
            max_dim_idx = dims[:].index(max(dims))
            radius = max([dims[i] for i in range(3) if i != max_dim_idx]) / 2
            depth = dims[max_dim_idx]
            
            if max_dim_idx == 0:
                bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, 
                                                  location=bbox_center, rotation=(0, 1.5708, 0))
            elif max_dim_idx == 1:
                bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, 
                                                  location=bbox_center, rotation=(1.5708, 0, 0))
            else:
                bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, location=bbox_center)
                
        elif self.method == 'UBX':
            bpy.ops.mesh.primitive_cube_add(location=bbox_center)
            collision_obj = bpy.context.active_object
            collision_obj.scale = dims
            
        elif self.method == 'USP':
            radius = max(dims) / 2
            bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=bbox_center)
        
        collision_obj = bpy.context.active_object
        collision_obj.name = name
        
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')
        
        self._apply_collision_properties(collision_obj)
        
        return collision_obj
    
    def _apply_decimation(self, obj, ratio):
        decimate = obj.modifiers.new(name="Decimate", type='DECIMATE')
        decimate.ratio = ratio
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=decimate.name)
    
    def _fix_non_planar_faces(self, obj):
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles(threshold=0.0001)
        bpy.ops.mesh.delete_loose()
        bpy.ops.mesh.quads_convert_to_tris(quad_method='FIXED', ngon_method='BEAUTY')
        bpy.ops.mesh.normals_make_consistent(inside=False)
        
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    
    def _apply_collision_properties(self, obj):
        if "Collision_Material" not in bpy.data.materials:
            mat = bpy.data.materials.new(name="Collision_Material")
            mat.diffuse_color = (0.2, 0.8, 0.2, 0.6)
            mat.use_backface_culling = False
        else:
            mat = bpy.data.materials["Collision_Material"]
        
        obj.data.materials.clear()
        obj.data.materials.append(mat)
        
        if self.layer_preset == 'Custom' and self.custom_layer_preset:
            obj["layer_preset"] = self.custom_layer_preset
        else:
            obj["layer_preset"] = self.layer_preset
        
        if self.layer_preset == 'MineTrigger':
            obj["usage"] = "MineTrigger"
        elif self.layer_preset == 'FireGeo':
            obj["usage"] = "FireGeo"
        else:
            obj["usage"] = "Vehicle"
        
        if self.parent_to_bone and self.bone_name:
            armature = None
            for armature_obj in bpy.data.objects:
                if armature_obj.type == 'ARMATURE':
                    armature = armature_obj
                    break
            
            if armature and self.bone_name in armature.data.bones:
                obj.parent = armature
                obj.parent_type = 'BONE'
                obj.parent_bone = self.bone_name
            else:
                self.report({'WARNING'}, f"Bone '{self.bone_name}' not found in armature")
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=400)
    
    def draw(self, context):
        layout = self.layout
        
        layout.prop(self, "method")
        
        if self.method == 'UCX':
            layout.prop(self, "target_faces")
        
        layout.separator()
        layout.label(text="Collision Properties:", icon='SETTINGS')
        layout.prop(self, "layer_preset")
        
        if self.layer_preset == 'Custom':
            layout.prop(self, "custom_layer_preset")
        
        layout.separator()
        layout.prop(self, "parent_to_bone")
        
        if self.parent_to_bone:
            layout.prop(self, "bone_name", icon='BONE_DATA')
            
            armature = None
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE':
                    armature = obj
                    break
            
            if armature:
                box = layout.box()
                box.label(text="Available bones:", icon='INFO')
                bone_names = [b.name for b in armature.data.bones[:5]]
                for bone in bone_names:
                    box.label(text=f"  {bone}")
                if len(armature.data.bones) > 5:
                    box.label(text=f"  ... and {len(armature.data.bones) - 5} more")


class ARVEHICLES_OT_create_firegeo_collision(bpy.types.Operator):
    bl_idname = "arvehicles.create_firegeo_collision"
    bl_label = "Create FireGeo Collision"
    bl_options = {'REGISTER', 'UNDO'}
    
    method: bpy.props.EnumProperty(
        name="Method",
        items=[
            ('CONVEX', "Convex Hull", "Simplified convex hull"),
            ('DETAILED', "Detailed", "Preserves shape better"),
        ],
        default='DETAILED'
    )
    target_faces: bpy.props.IntProperty(name="Target Faces", default=400, min=100, max=5000)
    offset: bpy.props.FloatProperty(name="Offset", default=0.01, min=0.0, max=0.05)
    
    def execute(self, context):
        if not context.selected_objects:
            self.report({'ERROR'}, "No objects selected")
            return {'CANCELLED'}
        
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not mesh_objects:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}
        
        collision_objects = []
        total_faces = 0
        
        for idx, source_obj in enumerate(mesh_objects):
            bpy.ops.object.select_all(action='DESELECT')
            source_obj.select_set(True)
            context.view_layer.objects.active = source_obj
            
            bpy.ops.object.duplicate()
            dup_obj = context.selected_objects[0]
            
            if len(mesh_objects) == 1:
                dup_obj.name = "UTM_vehicle"
            else:
                dup_obj.name = f"UTM_vehicle_part_{idx}"
                
            collision_objects.append(dup_obj)
            
            part_target_faces = int(self.target_faces / len(mesh_objects))
            current_faces = len(dup_obj.data.polygons)
            
            if current_faces > part_target_faces:
                obj_dimensions = dup_obj.dimensions
                is_flat = min(obj_dimensions) < max(obj_dimensions) * 0.1
                
                if is_flat:
                    target_ratio = max(0.8, part_target_faces / current_faces)
                else:
                    target_ratio = part_target_faces / current_faces
                
                if target_ratio < 1.0:
                    decimate = dup_obj.modifiers.new(name="Decimate", type='DECIMATE')
                    decimate.ratio = max(0.1, target_ratio)
                    bpy.ops.object.modifier_apply(modifier=decimate.name)
            
            if self.offset > 0:
                solidify = dup_obj.modifiers.new(name="Solidify", type='SOLIDIFY')
                solidify.thickness = self.offset
                solidify.offset = 1.0
                bpy.ops.object.modifier_apply(modifier=solidify.name)
            
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            obj_dimensions = dup_obj.dimensions
            is_flat = min(obj_dimensions) < max(obj_dimensions) * 0.1
            merge_threshold = 0.0001 if is_flat else 0.001
            bpy.ops.mesh.remove_doubles(threshold=merge_threshold)
            bpy.ops.object.mode_set(mode='OBJECT')
            
            if "FireGeo_Material" not in bpy.data.materials:
                mat = bpy.data.materials.new(name="FireGeo_Material")
                mat.diffuse_color = (0.0, 0.8, 0.0, 0.5)
            else:
                mat = bpy.data.materials["FireGeo_Material"]
            
            dup_obj.data.materials.clear()
            dup_obj.data.materials.append(mat)
            dup_obj["layer_preset"] = "FireGeo"
            dup_obj["usage"] = "FireGeo"
            
            total_faces += len(dup_obj.data.polygons)
        
        bpy.ops.object.select_all(action='DESELECT')
        for obj in collision_objects:
            obj.select_set(True)
        
        if collision_objects:
            context.view_layer.objects.active = collision_objects[0]
        
        self.report({'INFO'}, f"Created FireGeo collision with {total_faces} total faces")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


class ARVEHICLES_OT_create_wheel_collisions(bpy.types.Operator):
    bl_idname = "arvehicles.create_wheel_collisions"
    bl_label = "Create Wheel Collisions"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Create UCL collision cylinders from selected wheel meshes"
    
    radius_offset: bpy.props.FloatProperty(
        name="Radius Offset",
        description="Adjust radius (positive = larger, negative = smaller)",
        default=0.0,
        min=-0.1,
        max=0.1,
        step=0.01
    )
    
    width_offset: bpy.props.FloatProperty(
        name="Width Offset",
        description="Adjust width (positive = wider, negative = narrower)",
        default=0.0,
        min=-0.1,
        max=0.1,
        step=0.01
    )
    
    layer_preset: bpy.props.EnumProperty(
        name="Layer Preset",
        description="Collision layer preset",
        items=[
            ('Collision_Vehicle', "Collision Vehicle", "Standard wheel collision"),
            ('MineTrigger', "Mine Trigger", "Mine detection trigger"),
            ('Custom', "Custom", "Custom layer preset"),
        ],
        default='Collision_Vehicle'
    )
    
    custom_layer_preset: bpy.props.StringProperty(
        name="Custom Layer",
        description="Custom layer preset name",
        default=""
    )
    
    parent_to_bone: bpy.props.BoolProperty(
        name="Parent to Bone",
        description="Parent collision to corresponding wheel bone",
        default=False
    )
    
    def execute(self, context):
        if not context.selected_objects:
            self.report({'ERROR'}, "No objects selected. Select wheel meshes first.")
            return {'CANCELLED'}
        
        wheel_meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not wheel_meshes:
            self.report({'ERROR'}, "No mesh objects selected. Select wheel meshes.")
            return {'CANCELLED'}
        
        created_collisions = []
        
        for wheel_obj in wheel_meshes:
            collision = self._create_wheel_collision(context, wheel_obj)
            if collision:
                created_collisions.append(collision)
        
        bpy.ops.object.select_all(action='DESELECT')
        for obj in created_collisions:
            obj.select_set(True)
        
        if created_collisions:
            context.view_layer.objects.active = created_collisions[0]
        
        self.report({'INFO'}, f"Created {len(created_collisions)} wheel collision(s)")
        return {'FINISHED'}
    
    def _create_wheel_collision(self, context, wheel_obj):
        dimensions = wheel_obj.dimensions
        world_center = wheel_obj.matrix_world.translation
        
        dims_sorted = sorted([(dimensions[i], i) for i in range(3)])
        
        wheel_width_raw = dims_sorted[0][0]
        width_axis = dims_sorted[0][1]
        
        wheel_diameter = (dims_sorted[1][0] + dims_sorted[2][0]) / 2
        wheel_radius_raw = wheel_diameter / 2
        
        wheel_radius = wheel_radius_raw + self.radius_offset
        wheel_width = wheel_width_raw + self.width_offset
        
        wheel_radius = max(0.05, wheel_radius)
        wheel_width = max(0.02, wheel_width)
        
        # For Arma wheel collisions, ALWAYS create cylinder along X-axis
        # This is the standard orientation for wheel collisions in Arma
        # X-axis = left/right (wheel axle direction)
        bpy.ops.mesh.primitive_cylinder_add(
            radius=wheel_radius,
            depth=wheel_width,
            location=world_center,
            rotation=(0, math.pi/2, 0)  # Always rotate to X-axis
        )
        
        collision_obj = context.active_object
        
        # Generate name
        wheel_name = wheel_obj.name.lower()
        
        numbers = re.findall(r'\d+', wheel_name)
        if numbers:
            wheel_num = numbers[-1]
            collision_name = f"UCL_wheel_{wheel_num}"
        elif 'left' in wheel_name or '_l' in wheel_name or '.l' in wheel_name:
            collision_name = f"UCL_wheel_L"
        elif 'right' in wheel_name or '_r' in wheel_name or '.r' in wheel_name:
            collision_name = f"UCL_wheel_R"
        else:
            collision_name = f"UCL_{wheel_obj.name}"
        
        collision_obj.name = collision_name
        
        # CRITICAL: Do NOT apply rotation for UCL collisions!
        # Only apply scale, leave rotation as-is
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        
        # Set origin to geometry center (required for UCL)
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')
        
        # ... rest stays the same ...
        
        if "UCL_Material" not in bpy.data.materials:
            mat = bpy.data.materials.new(name="UCL_Material")
            mat.diffuse_color = (0.8, 0.5, 0.0, 0.6)
        else:
            mat = bpy.data.materials["UCL_Material"]
        
        collision_obj.data.materials.clear()
        collision_obj.data.materials.append(mat)
        
        if self.layer_preset == 'Custom' and self.custom_layer_preset:
            collision_obj["layer_preset"] = self.custom_layer_preset
        else:
            collision_obj["layer_preset"] = self.layer_preset
        
        if self.layer_preset == 'MineTrigger':
            collision_obj["usage"] = "MineTrigger"
        else:
            collision_obj["usage"] = "PhyCol"
        
        if self.parent_to_bone:
            bone_name = self._find_wheel_bone(wheel_obj.name)
            
            if bone_name:
                armature = None
                for armature_obj in bpy.data.objects:
                    if armature_obj.type == 'ARMATURE':
                        armature = armature_obj
                        break
                
                if armature and bone_name in armature.data.bones:
                    collision_obj.parent = armature
                    collision_obj.parent_type = 'BONE'
                    collision_obj.parent_bone = bone_name
        
        return collision_obj
    
    def _find_wheel_bone(self, wheel_name):
        wheel_name_lower = wheel_name.lower()
        
        numbers = re.findall(r'\d+', wheel_name_lower)
        if numbers:
            num = numbers[-1]
            return f"v_wheel_{num}"
        
        if 'left' in wheel_name_lower or '_l' in wheel_name_lower:
            return "v_wheel_L"
        elif 'right' in wheel_name_lower or '_r' in wheel_name_lower:
            return "v_wheel_R"
        
        return None
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        
        layout.label(text="Size Adjustments:", icon='ARROW_LEFTRIGHT')
        layout.prop(self, "radius_offset")
        layout.prop(self, "width_offset")
        
        layout.separator()
        layout.label(text="Collision Properties:", icon='SETTINGS')
        layout.prop(self, "layer_preset")
        
        if self.layer_preset == 'Custom':
            layout.prop(self, "custom_layer_preset")
        
        layout.separator()
        layout.prop(self, "parent_to_bone")


class ARVEHICLES_OT_create_center_of_mass(bpy.types.Operator):
    bl_idname = "arvehicles.create_center_of_mass"
    bl_label = "Create Center of Mass"
    bl_options = {'REGISTER', 'UNDO'}
    
    com_size: bpy.props.FloatProperty(name="COM Size", default=0.15, min=0.05, max=0.5)
    com_height_offset: bpy.props.FloatProperty(name="Height Offset", default=-0.15, min=-0.8, max=0.5)
    
    def execute(self, context):
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, self.com_height_offset))
        
        box = bpy.context.active_object
        box.name = "COM_vehicle"
        
        box.scale.x = self.com_size
        box.scale.y = self.com_size * 2
        box.scale.z = self.com_size
        
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        
        if "COM_Material" not in bpy.data.materials:
            mat = bpy.data.materials.new(name="COM_Material")
            mat.diffuse_color = (0.3, 1.0, 0.3, 0.6)
        else:
            mat = bpy.data.materials["COM_Material"]
        
        if box.data.materials:
            box.data.materials[0] = mat
        else:
            box.data.materials.append(mat)
        
        box["layer_preset"] = "Collision_Vehicle"
        box["usage"] = "CenterOfMass"
        
        self.report({'INFO'}, "Created center of mass object")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)