import bpy
import bmesh
from mathutils import Vector
from ..constants import VEHICLE_SOCKET_TYPES

class ARVEHICLES_OT_create_socket(bpy.types.Operator):
    bl_idname = "arvehicles.create_socket"
    bl_label = "Create Vehicle Socket"
    bl_options = {'REGISTER', 'UNDO'}
    
    socket_type: bpy.props.EnumProperty(name="Socket Type", items=VEHICLE_SOCKET_TYPES, default='door')
    custom_name: bpy.props.StringProperty(name="Custom Name", default="")
    parent_to_armature: bpy.props.BoolProperty(
        name="Parent to Armature", 
        default=True,
        description="Automatically parent socket to vehicle armature"
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
        
        # Parent to armature if requested
        if self.parent_to_armature:
            armature = None
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE':
                    armature = obj
                    break
            
            if armature:
                socket.parent = armature
                self.report({'INFO'}, f"Socket parented to armature '{armature.name}'")
            else:
                self.report({'WARNING'}, "No armature found to parent socket to")
        
        # Select the socket
        bpy.ops.object.select_all(action='DESELECT')
        socket.select_set(True)
        context.view_layer.objects.active = socket
        
        self.report({'INFO'}, f"Created vehicle socket '{socket_name}' at selected faces")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
