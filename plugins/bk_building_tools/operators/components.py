import bpy
import math
import bmesh
from mathutils import Vector, Matrix

from ..constants import BUILDING_SOCKET_NAMES, BUILDING_PART_TYPES


def get_memory_points_collection():
    """Get or create the Memory Points collection."""
    if "Memory Points" in bpy.data.collections:
        return bpy.data.collections["Memory Points"]

    memory_points = bpy.data.collections.new("Memory Points")
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

    snap_to_axis: bpy.props.BoolProperty(
        name="Snap Socket to Axis",
        description="Snap socket to the closest global axis (X, Y, or Z)",
        default=False
    )

    snap_axis_preference: bpy.props.EnumProperty(
        name="Preferred Axis",
        description="Preferred axis for snapping (if distances are close)",
        items=[
            ('X', "X Axis", "Prefer X axis"),
            ('Y', "Y Axis", "Prefer Y axis"),
            ('Z', "Z Axis", "Prefer Z axis"),
            ('AUTO', "Auto (Closest)", "Automatically choose closest axis"),
        ],
        default='AUTO'
    )

    add_firegeo: bpy.props.BoolProperty(
        name="Add FireGeo",
        description="Add a FireGeo collision mesh for the component",
        default=True
    )

    set_origin_to_socket: bpy.props.BoolProperty(
        name="Set Origin to Socket",
        description="Set the object's origin to the same location as the socket",
        default=True
    )

    flip_normals: bpy.props.BoolProperty(
        name="Flip Normals",
        description="Flip the normals of the separated component",
        default=False
    )

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "No active mesh object")
            return {'CANCELLED'}

        if context.mode != 'EDIT_MESH':
            self.report({'ERROR'}, "Must be in Edit Mode with faces selected")
            return {'CANCELLED'}

        mesh = obj.data
        if not mesh.total_face_sel:
            self.report({'ERROR'}, "No faces selected")
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(mesh)
        selected_faces = [f for f in bm.faces if f.select]

        if not selected_faces:
            self.report({'ERROR'}, "No faces selected")
            return {'CANCELLED'}

        center = Vector((0, 0, 0))
        for face in selected_faces:
            center += face.calc_center_median()
        center /= len(selected_faces)

        world_center = obj.matrix_world @ center

        prefix = f"{self.component_type}_"
        new_name = self.custom_name if self.custom_name else f"{prefix}{obj.name}"

        bpy.ops.mesh.separate(type='SELECTED')
        bpy.ops.object.mode_set(mode='OBJECT')

        new_obj = context.selected_objects[-1]
        new_obj.name = new_name
        new_obj["component_type"] = self.component_type

        socket = None
        if self.add_socket:
            base_name = BUILDING_SOCKET_NAMES[self.component_type]
            idx = 1
            while f"{base_name}_{idx:02d}" in bpy.data.objects:
                idx += 1
            socket_name = f"{base_name}_{idx:02d}"
            socket = bpy.data.objects.new(socket_name, None)
            socket.empty_display_type = 'PLAIN_AXES'
            socket.empty_display_size = 0.05

            socket_position = world_center.copy()

            if self.snap_to_axis:
                socket_position = self._snap_to_closest_axis(socket_position)

            socket.location = socket_position

            memory_points = get_memory_points_collection()
            memory_points.objects.link(socket)

            socket["socket_type"] = self.component_type
            socket["attached_part"] = new_obj.name
            socket["building_part"] = "attachment_point"

        if self.add_socket and self.set_origin_to_socket:
            bpy.ops.object.select_all(action='DESELECT')
            new_obj.select_set(True)
            context.view_layer.objects.active = new_obj

            cursor_location = context.scene.cursor.location.copy()
            context.scene.cursor.location = socket.location
            bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
            context.scene.cursor.location = cursor_location

        if self.flip_normals:
            bpy.ops.object.select_all(action='DESELECT')
            new_obj.select_set(True)
            context.view_layer.objects.active = new_obj

            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.flip_normals()
            bpy.ops.object.mode_set(mode='OBJECT')

        if self.add_firegeo:
            self._create_firegeo(context, new_obj)

        bpy.ops.object.select_all(action='DESELECT')
        new_obj.select_set(True)
        context.view_layer.objects.active = new_obj

        report_msg = f"Separated component '{new_name}'"
        if self.add_socket:
            report_msg += " with socket"
            if self.snap_to_axis:
                report_msg += " (axis-snapped)"
        if self.set_origin_to_socket:
            report_msg += ", origin set to socket"
        if self.flip_normals:
            report_msg += ", normals flipped"

        self.report({'INFO'}, report_msg)
        return {'FINISHED'}

    def _snap_to_closest_axis(self, position):
        """Snap the given position to the closest global axis."""
        pos = position.copy()

        if self.snap_axis_preference == 'AUTO':
            dist_to_x = math.sqrt(pos.y**2 + pos.z**2)
            dist_to_y = math.sqrt(pos.x**2 + pos.z**2)
            dist_to_z = math.sqrt(pos.x**2 + pos.y**2)

            min_dist = min(dist_to_x, dist_to_y, dist_to_z)

            if min_dist == dist_to_x:
                pos.y = 0
                pos.z = 0
            elif min_dist == dist_to_y:
                pos.x = 0
                pos.z = 0
            else:
                pos.x = 0
                pos.y = 0
        else:
            if self.snap_axis_preference == 'X':
                pos.y = 0
                pos.z = 0
            elif self.snap_axis_preference == 'Y':
                pos.x = 0
                pos.z = 0
            elif self.snap_axis_preference == 'Z':
                pos.x = 0
                pos.y = 0

        return pos

    def _create_firegeo(self, context, obj):
        """Create a simplified FireGeo collision mesh for the component."""
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj
        bpy.ops.object.duplicate()

        firegeo_obj = context.active_object
        firegeo_obj.name = f"UTM_{obj.name}"

        decimate = firegeo_obj.modifiers.new(name="Decimate", type='DECIMATE')
        decimate.ratio = 0.5
        bpy.ops.object.modifier_apply(modifier=decimate.name)

        solidify = firegeo_obj.modifiers.new(name="Solidify", type='SOLIDIFY')
        solidify.thickness = 0.01
        solidify.offset = 1.0
        bpy.ops.object.modifier_apply(modifier=solidify.name)

        if "FireGeo_Material" not in bpy.data.materials:
            mat = bpy.data.materials.new(name="FireGeo_Material")
            mat.diffuse_color = (0.0, 0.8, 0.0, 0.5)
        else:
            mat = bpy.data.materials["FireGeo_Material"]

        firegeo_obj.data.materials.clear()
        firegeo_obj.data.materials.append(mat)

        firegeo_obj["layer_preset"] = "Collision_Building"
        firegeo_obj["usage"] = "FireGeo"

        firegeo_obj.parent = obj
        firegeo_obj.matrix_parent_inverse = obj.matrix_world.inverted()

        return firegeo_obj

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=350)

    def draw(self, context):
        layout = self.layout

        layout.prop(self, "component_type")
        layout.prop(self, "custom_name")

        layout.prop(self, "add_socket")

        if self.add_socket:
            box = layout.box()
            box.prop(self, "set_origin_to_socket")
            box.prop(self, "snap_to_axis")

            if self.snap_to_axis:
                box.prop(self, "snap_axis_preference")

        layout.prop(self, "add_firegeo")
        layout.prop(self, "flip_normals")


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
        obj = context.active_object

        if not obj:
            self.report({'ERROR'}, "No active object selected")
            return {'CANCELLED'}

        current_mode = context.mode

        if self.custom_name:
            socket_name = self.custom_name
        else:
            socket_name = f"{BUILDING_SOCKET_NAMES[self.socket_type]}_{len([o for o in bpy.data.objects if BUILDING_SOCKET_NAMES[self.socket_type] in o.name]) + 1}"

        socket_location = obj.location.copy()
        socket_rotation = (0, 0, 0)

        if current_mode == 'EDIT_MESH' and self.snap_to_face:
            mesh = obj.data
            bm = bmesh.from_edit_mesh(mesh)
            selected_faces = [f for f in bm.faces if f.select]

            if selected_faces:
                active_face = selected_faces[0]
                face_center = active_face.calc_center_median()
                socket_location = obj.matrix_world @ face_center

                if self.align_to_normal:
                    normal = active_face.normal.normalized()
                    world_normal = obj.matrix_world.to_3x3() @ normal
                    up_vector = Vector((0, 0, 1))

                    if abs(world_normal.dot(up_vector)) > 0.99:
                        rot_axis = Vector((1, 0, 0))
                    else:
                        rot_axis = world_normal.cross(up_vector).normalized()

                    angle = world_normal.angle(up_vector)
                    rot_mat = Matrix.Rotation(angle, 4, rot_axis)
                    socket_rotation = rot_mat.to_euler()

        if current_mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')

        socket = bpy.data.objects.new(socket_name, None)
        socket.empty_display_type = 'PLAIN_AXES'
        socket.empty_display_size = self.display_size

        socket.location = socket_location
        socket.rotation_euler = socket_rotation

        memory_points = get_memory_points_collection()
        memory_points.objects.link(socket)

        socket["socket_type"] = self.socket_type
        socket["building_part"] = "attachment_point"

        for sel_obj in context.selected_objects:
            sel_obj.select_set(False)

        socket.select_set(True)
        context.view_layer.objects.active = socket

        if current_mode == 'EDIT_MESH':
            if obj and obj.type == 'MESH':
                context.view_layer.objects.active = obj
                bpy.ops.object.mode_set(mode='EDIT')
            else:
                self.report({'WARNING'}, "Couldn't restore edit mode, original object no longer available")

        self.report({'INFO'}, f"Created building socket '{socket_name}' in Memory Points collection")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "socket_type")
        layout.prop(self, "custom_name")
        layout.prop(self, "snap_to_face")
        layout.prop(self, "align_to_normal")
        layout.prop(self, "display_size")


class ARBUILDINGS_OT_convert_existing_sockets(bpy.types.Operator):
    """Clear parent relationships from socket empties to make them compatible with Arma Reforger"""
    bl_idname = "arbuildings.convert_existing_sockets"
    bl_label = "Clear Socket Parents"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        memory_points = None
        if "Memory Points" in bpy.data.collections:
            memory_points = bpy.data.collections["Memory Points"]
        else:
            self.report({'ERROR'}, "Memory Points collection not found")
            return {'CANCELLED'}

        modified_count = 0

        for obj in memory_points.objects:
            if obj.type == 'EMPTY' and obj.parent is not None:
                original_matrix = obj.matrix_world.copy()
                obj.parent = None
                obj.matrix_world = original_matrix
                modified_count += 1

        if modified_count > 0:
            self.report({'INFO'}, f"Cleared parent relationships for {modified_count} socket empties")
        else:
            self.report({'INFO'}, "No socket empties with parent relationships found")

        return {'FINISHED'}


classes = (
    ARBUILDINGS_OT_separate_component,
    ARBUILDINGS_OT_create_building_socket,
    ARBUILDINGS_OT_convert_existing_sockets,
)
