import bpy
import bmesh
from mathutils import Vector
from ..constants import VEHICLE_SOCKET_TYPES

def _get_bone_items(self, context):
    items = [('NONE', "Don't Parent to Bone", "Parent to armature root only")]
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            for bone in obj.data.bones:
                items.append((bone.name, bone.name, ""))
            break
    return items


class ARVEHICLES_OT_create_socket(bpy.types.Operator):
    bl_idname = "arvehicles.create_socket"
    bl_label = "Create Vehicle Socket"
    bl_options = {'REGISTER', 'UNDO'}

    socket_type: bpy.props.EnumProperty(name="Socket Type", items=VEHICLE_SOCKET_TYPES, default='door')
    custom_name: bpy.props.StringProperty(name="Custom Name", default="")
    parent_bone: bpy.props.EnumProperty(
        name="Parent to Bone",
        items=_get_bone_items,
        description="Select a bone to parent the socket to (or leave as Don't Parent to Bone)"
    )

    def execute(self, context):
        socket_location = (0, 0, 0)  # Default to origin

        # Check if we're in edit mode with faces selected
        if context.mode == 'EDIT_MESH' and context.active_object and context.active_object.type == 'MESH':
            obj = context.active_object
            mesh = obj.data

            if mesh.total_face_sel > 0:
                # Calculate center of selected faces
                bm = bmesh.from_edit_mesh(mesh)
                selected_faces = [f for f in bm.faces if f.select]

                if selected_faces:
                    center = Vector((0, 0, 0))
                    for face in selected_faces:
                        center += face.calc_center_median()
                    center /= len(selected_faces)

                    # Transform to world space
                    socket_location = obj.matrix_world @ center

                    # Switch to object mode for socket creation
                    bpy.ops.object.mode_set(mode='OBJECT')
                else:
                    self.report({'WARNING'}, "No faces selected, using object center")
                    bbox_center = sum((obj.matrix_world @ Vector(corner) for corner in obj.bound_box), Vector()) / 8
                    socket_location = bbox_center
                    bpy.ops.object.mode_set(mode='OBJECT')
            else:
                self.report({'WARNING'}, "No faces selected, using object center")
                bbox_center = sum((obj.matrix_world @ Vector(corner) for corner in obj.bound_box), Vector()) / 8
                socket_location = bbox_center
                bpy.ops.object.mode_set(mode='OBJECT')

        # Fallback: If a mesh object is selected in object mode, use its center
        elif context.selected_objects:
            mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
            if mesh_objects:
                obj = mesh_objects[0]
                bbox_center = sum((obj.matrix_world @ Vector(corner) for corner in obj.bound_box), Vector()) / 8
                socket_location = bbox_center

        # Generate socket name
        if self.custom_name:
            socket_name = self.custom_name
        else:
            socket_name = f"Socket_{self.socket_type.replace('_', ' ').title().replace(' ', '_')}"
            existing_sockets = [o for o in bpy.data.objects if socket_name in o.name]
            if existing_sockets:
                socket_name = f"{socket_name}_{len(existing_sockets) + 1:02d}"

        # Create socket
        socket = bpy.data.objects.new(socket_name, None)
        socket.empty_display_type = 'ARROWS'
        socket.empty_display_size = 0.15
        socket.location = socket_location

        context.collection.objects.link(socket)

        socket["socket_type"] = self.socket_type
        socket["vehicle_part"] = "attachment_point"

        # Parent to armature / bone
        armature = None
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                armature = obj
                break

        if armature:
            if self.parent_bone != 'NONE' and self.parent_bone in armature.data.bones:
                socket.parent = armature
                socket.parent_type = 'BONE'
                socket.parent_bone = self.parent_bone
                pb = armature.pose.bones.get(self.parent_bone)
                socket.matrix_parent_inverse = (armature.matrix_world @ pb.matrix).inverted() if pb else armature.matrix_world.inverted()
                self.report({'INFO'}, f"Socket parented to bone '{self.parent_bone}'")
            else:
                socket.parent = armature
                socket.parent_type = 'OBJECT'
                socket.matrix_parent_inverse = armature.matrix_world.inverted()
                self.report({'INFO'}, f"Socket parented to armature '{armature.name}'")
        else:
            self.report({'WARNING'}, "No armature found to parent socket to")

        # Select the socket
        bpy.ops.object.select_all(action='DESELECT')
        socket.select_set(True)
        context.view_layer.objects.active = socket

        self.report({'INFO'}, f"Created vehicle socket '{socket_name}'")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "socket_type")
        layout.prop(self, "custom_name")
        layout.separator()
        layout.label(text="Parenting:", icon='CONSTRAINT_BONE')
        layout.prop(self, "parent_bone", text="")


class ARVEHICLES_OT_parent_socket_to_bone(bpy.types.Operator):
    bl_idname = "arvehicles.parent_socket_to_bone"
    bl_label = "Parent Empty to Bone"
    bl_description = "Parent selected empties/sockets to a specific armature bone"
    bl_options = {'REGISTER', 'UNDO'}

    target_bone: bpy.props.EnumProperty(name="Parent To", items=_get_bone_items)

    def execute(self, context):
        if self.target_bone == 'NONE':
            self.report({'ERROR'}, "Please select a target bone")
            return {'CANCELLED'}

        armature = None
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                armature = obj
                break

        if not armature:
            self.report({'ERROR'}, "No armature found in scene")
            return {'CANCELLED'}

        if self.target_bone not in armature.data.bones:
            self.report({'ERROR'}, f"Bone '{self.target_bone}' not found")
            return {'CANCELLED'}

        selected_empties = [obj for obj in context.selected_objects if obj.type == 'EMPTY']
        if not selected_empties:
            self.report({'ERROR'}, "No empties selected")
            return {'CANCELLED'}

        pb = armature.pose.bones.get(self.target_bone)
        parent_inv = (armature.matrix_world @ pb.matrix).inverted() if pb else armature.matrix_world.inverted()
        for empty in selected_empties:
            empty.parent = armature
            empty.parent_type = 'BONE'
            empty.parent_bone = self.target_bone
            empty.matrix_parent_inverse = parent_inv

        self.report({'INFO'}, f"Parented {len(selected_empties)} empty/empties to bone '{self.target_bone}'")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        selected_empties = [obj for obj in context.selected_objects if obj.type == 'EMPTY']

        box = layout.box()
        box.label(text=f"Selected Empties: {len(selected_empties)}", icon='EMPTY_DATA')
        for obj in selected_empties[:5]:
            box.label(text=f"  - {obj.name}")
        if len(selected_empties) > 5:
            box.label(text=f"  ... and {len(selected_empties) - 5} more")

        layout.separator()
        layout.label(text="Parent To:", icon='CONSTRAINT_BONE')
        layout.prop(self, "target_bone", text="")


classes = (
    ARVEHICLES_OT_create_socket,
    ARVEHICLES_OT_parent_socket_to_bone,
)
