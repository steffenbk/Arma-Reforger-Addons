import bpy
from mathutils import Vector


class ARBUILDINGS_OT_create_portal(bpy.types.Operator):
    bl_idname = "arbuildings.create_portal"
    bl_label = "Create Portal"
    bl_description = "Create a PRT_ portal plane at selected faces or cursor location"
    bl_options = {'REGISTER', 'UNDO'}

    portal_width: bpy.props.FloatProperty(name="Width", default=1.2, min=0.1, max=10.0)
    portal_height: bpy.props.FloatProperty(name="Height", default=2.2, min=0.1, max=10.0)

    @classmethod
    def poll(cls, context):
        return context.active_object is not None or context.scene.cursor is not None

    def execute(self, context):
        idx = 1
        while f"PRT_{idx:02d}" in bpy.data.objects:
            idx += 1
        name = f"PRT_{idx:02d}"

        # Create 4-vertex plane (no triangulation -- portals must be quads)
        mesh = bpy.data.meshes.new(name)
        w, h = self.portal_width / 2.0, self.portal_height / 2.0
        verts = [(-w, 0, -h), (w, 0, -h), (w, 0, h), (-w, 0, h)]
        faces = [(0, 1, 2, 3)]
        mesh.from_pydata(verts, [], faces)
        mesh.update()

        obj = bpy.data.objects.new(name, mesh)
        obj.location = context.scene.cursor.location
        obj.display_type = 'WIRE'
        context.scene.collection.objects.link(obj)

        # Assign MatLightPortal material (required by Enfusion)
        mat_name = "MatLightPortal"
        if mat_name in bpy.data.materials:
            mat = bpy.data.materials[mat_name]
        else:
            mat = bpy.data.materials.new(name=mat_name)
            mat.diffuse_color = (0.0, 0.5, 1.0, 0.4)
        obj.data.materials.append(mat)

        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj

        self.report({'INFO'}, f"Created portal: {name} ({self.portal_width}x{self.portal_height}m)")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "portal_width")
        layout.prop(self, "portal_height")
        layout.label(text="Place at cursor, orient normal inward", icon='INFO')


class ARBUILDINGS_OT_create_probe_volume(bpy.types.Operator):
    bl_idname = "arbuildings.create_probe_volume"
    bl_label = "Create Probe Volume"
    bl_description = "Create BOXVOL_ or SPHVOL_ probe volume from selected objects"
    bl_options = {'REGISTER', 'UNDO'}

    probe_type: bpy.props.EnumProperty(
        name="Probe Type",
        items=[
            ('BOXVOL', "Box Probe", "Interior box lighting probe (BOXVOL_)"),
            ('SPHVOL', "Sphere Probe", "Sphere lighting probe (SPHVOL_) -- still uses box shape"),
        ],
        default='BOXVOL'
    )
    padding: bpy.props.FloatProperty(
        name="Padding",
        description="Extra space around bounding box",
        default=0.1, min=0.0, max=2.0
    )

    @classmethod
    def poll(cls, context):
        return bool(context.selected_objects)

    def execute(self, context):
        prefix = self.probe_type + "_"
        idx = 1
        while f"{prefix}{idx:02d}" in bpy.data.objects:
            idx += 1
        name = f"{prefix}{idx:02d}"

        min_co = Vector((float('inf'), float('inf'), float('inf')))
        max_co = Vector((float('-inf'), float('-inf'), float('-inf')))
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                for corner in obj.bound_box:
                    world_co = obj.matrix_world @ Vector(corner)
                    min_co.x = min(min_co.x, world_co.x)
                    min_co.y = min(min_co.y, world_co.y)
                    min_co.z = min(min_co.z, world_co.z)
                    max_co.x = max(max_co.x, world_co.x)
                    max_co.y = max(max_co.y, world_co.y)
                    max_co.z = max(max_co.z, world_co.z)

        if min_co.x == float('inf'):
            self.report({'ERROR'}, "No mesh objects in selection")
            return {'CANCELLED'}

        min_co -= Vector((self.padding, self.padding, self.padding))
        max_co += Vector((self.padding, self.padding, self.padding))

        center = (min_co + max_co) / 2.0
        size = max_co - min_co

        # Create box (SPHVOL also uses box shape per Enfusion rules)
        bpy.ops.mesh.primitive_cube_add(location=center)
        probe = context.active_object
        probe.scale = size / 2.0
        bpy.ops.object.transform_apply(scale=True)
        probe.name = name
        probe.data.name = name
        probe.display_type = 'WIRE'

        mat_name = "dummyvolume"
        if mat_name in bpy.data.materials:
            mat = bpy.data.materials[mat_name]
        else:
            mat = bpy.data.materials.new(name=mat_name)
            mat.diffuse_color = (0.5, 0.0, 0.5, 0.3)
        probe.data.materials.append(mat)

        self.report({'INFO'}, f"Created probe volume: {name} ({size.x:.1f}x{size.y:.1f}x{size.z:.1f}m)")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "probe_type")
        layout.prop(self, "padding")


class ARBUILDINGS_OT_create_bsp(bpy.types.Operator):
    bl_idname = "arbuildings.create_bsp"
    bl_label = "Create BSP Geometry"
    bl_description = "Create simplified BSP_ room mesh from selected objects (for interior lighting)"
    bl_options = {'REGISTER', 'UNDO'}

    simplify: bpy.props.FloatProperty(
        name="Simplify Ratio",
        description="Decimate ratio (1.0 = no simplification)",
        default=0.3, min=0.05, max=1.0
    )

    @classmethod
    def poll(cls, context):
        return any(obj.type == 'MESH' for obj in context.selected_objects)

    def execute(self, context):
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not mesh_objects:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}

        idx = 1
        while f"BSP_{idx:03d}" in bpy.data.objects:
            idx += 1
        name = f"BSP_{idx:03d}"

        # Join copies of selected objects
        bpy.ops.object.select_all(action='DESELECT')
        copies = []
        for obj in mesh_objects:
            copy = obj.copy()
            copy.data = obj.data.copy()
            context.scene.collection.objects.link(copy)
            copy.select_set(True)
            copies.append(copy)

        context.view_layer.objects.active = copies[0]
        if len(copies) > 1:
            bpy.ops.object.join()

        bsp = context.active_object
        bsp.name = name
        bsp.data.name = name

        if self.simplify < 1.0:
            mod = bsp.modifiers.new(name="BSP_Decimate", type='DECIMATE')
            mod.ratio = self.simplify
            bpy.ops.object.modifier_apply(modifier=mod.name)

        # Assign dummyvolume material
        bsp.data.materials.clear()
        mat_name = "dummyvolume"
        if mat_name in bpy.data.materials:
            mat = bpy.data.materials[mat_name]
        else:
            mat = bpy.data.materials.new(name=mat_name)
            mat.diffuse_color = (0.5, 0.0, 0.5, 0.3)
        bsp.data.materials.append(mat)
        bsp.display_type = 'WIRE'

        self.report({'INFO'}, f"Created BSP geometry: {name} ({len(bsp.data.polygons)} faces)")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "simplify")


classes = (
    ARBUILDINGS_OT_create_portal,
    ARBUILDINGS_OT_create_probe_volume,
    ARBUILDINGS_OT_create_bsp,
)
