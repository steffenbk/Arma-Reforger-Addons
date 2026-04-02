import bpy
import bmesh


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
        default='DETAILED'
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
        if len(context.selected_objects) == 0:
            self.report({'ERROR'}, "Please select building components to create FireGeo for")
            return {'CANCELLED'}

        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']

        if not mesh_objects:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}

        created_count = 0
        for obj in mesh_objects:
            if any(child.name.startswith("UTM_") for child in obj.children):
                continue

            collision_mesh = bpy.data.meshes.new(f"UTM_{obj.name}_mesh")
            fire_geo_obj = bpy.data.objects.new(f"UTM_{obj.name}", collision_mesh)
            context.collection.objects.link(fire_geo_obj)

            if self.method == 'CONVEX':
                self._create_convex_hull(context, obj, fire_geo_obj)
            else:
                self._create_detailed(context, obj, fire_geo_obj)

            fire_geo_obj.parent = obj

            if "FireGeo_Material" not in bpy.data.materials:
                mat = bpy.data.materials.new(name="FireGeo_Material")
                mat.diffuse_color = (0.0, 0.8, 0.0, 0.5)
            else:
                mat = bpy.data.materials["FireGeo_Material"]

            fire_geo_obj.data.materials.clear()
            fire_geo_obj.data.materials.append(mat)

            fire_geo_obj["layer_preset"] = "Collision_Building"
            fire_geo_obj["usage"] = "FireGeo"

            created_count += 1

        if created_count > 0:
            self.report({'INFO'}, f"Created {created_count} FireGeo collision meshes")
        else:
            self.report({'INFO'}, "No new FireGeo meshes created (components might already have them)")

        return {'FINISHED'}

    def _create_convex_hull(self, context, source_obj, fire_geo_obj):
        """Create a convex hull based FireGeo collision."""
        all_verts = []

        if len(source_obj.data.vertices) > 1000:
            sample_rate = min(1.0, 500 / len(source_obj.data.vertices))
            for i, vert in enumerate(source_obj.data.vertices):
                if i % int(1/sample_rate) == 0:
                    world_co = source_obj.matrix_world @ vert.co
                    all_verts.append(world_co)
        else:
            for vert in source_obj.data.vertices:
                world_co = source_obj.matrix_world @ vert.co
                all_verts.append(world_co)

        temp_mesh = bpy.data.meshes.new("temp_hull_mesh")
        temp_obj = bpy.data.objects.new("temp_hull", temp_mesh)
        context.collection.objects.link(temp_obj)

        temp_mesh.from_pydata(all_verts, [], [])
        temp_mesh.update()

        bpy.ops.object.select_all(action='DESELECT')
        temp_obj.select_set(True)
        context.view_layer.objects.active = temp_obj

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.convex_hull()
        bpy.ops.object.mode_set(mode='OBJECT')

        if len(temp_obj.data.polygons) > self.target_faces:
            decimate = temp_obj.modifiers.new(name="Decimate", type='DECIMATE')
            decimate.ratio = self.target_faces / len(temp_obj.data.polygons)
            bpy.ops.object.modifier_apply(modifier=decimate.name)

        if self.offset > 0:
            solidify = temp_obj.modifiers.new(name="Solidify", type='SOLIDIFY')
            solidify.thickness = self.offset
            solidify.offset = 1.0
            bpy.ops.object.modifier_apply(modifier=solidify.name)

        fire_geo_obj.data = temp_obj.data.copy()
        bpy.data.objects.remove(temp_obj)

    def _create_detailed(self, context, source_obj, fire_geo_obj):
        """Create a detailed FireGeo collision that preserves more building features."""
        temp_mesh = source_obj.data.copy()
        temp_obj = bpy.data.objects.new("temp_detailed", temp_mesh)
        temp_obj.matrix_world = source_obj.matrix_world.copy()
        context.collection.objects.link(temp_obj)

        bpy.ops.object.select_all(action='DESELECT')
        temp_obj.select_set(True)
        context.view_layer.objects.active = temp_obj

        decimate = temp_obj.modifiers.new(name="Decimate", type='DECIMATE')
        current_faces = len(temp_obj.data.polygons)
        decimate.ratio = min(1.0, self.target_faces / max(1, current_faces))
        bpy.ops.object.modifier_apply(modifier=decimate.name)

        if self.offset > 0:
            solidify = temp_obj.modifiers.new(name="Solidify", type='SOLIDIFY')
            solidify.thickness = self.offset
            solidify.offset = 1.0
            bpy.ops.object.modifier_apply(modifier=solidify.name)

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles(threshold=0.001)
        bpy.ops.object.mode_set(mode='OBJECT')

        fire_geo_obj.data = temp_obj.data.copy()
        bpy.data.objects.remove(temp_obj)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


classes = (
    ARBUILDINGS_OT_create_firegeo_collision,
)
