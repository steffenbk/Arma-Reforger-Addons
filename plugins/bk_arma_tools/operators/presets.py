import bpy
import bmesh
from mathutils import Vector

class ARVEHICLES_OT_manage_presets(bpy.types.Operator):
    bl_idname = "arvehicles.manage_presets"
    bl_label = "Manage Vehicle Presets"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Create and manage lists of bone/socket names for two-phase separation"
    
    preset_name: bpy.props.StringProperty(name="Preset Name", default="MyVehicle")
    
    bone_names: bpy.props.StringProperty(
        name="Bone Names", 
        default="v_door_left,v_door_right,v_hood,v_trunk,v_wheel_1,v_wheel_2,v_wheel_3,v_wheel_4",
        description="Comma-separated list of bone names"
    )
    socket_names: bpy.props.StringProperty(
        name="Socket Names",
        default="Socket_Door,Socket_Door,Socket_Hood,Socket_Trunk,Socket_Wheel,Socket_Wheel,Socket_Wheel,Socket_Wheel", 
        description="Comma-separated list of socket names"
    )
    
    parent_meshes: bpy.props.BoolProperty(
        name="Parent Meshes to Armature",
        default=True,
        description="Automatically parent separated meshes to the armature"
    )
    
    def execute(self, context):
        scene = context.scene
        
        # Parse the lists
        bones = [name.strip() for name in self.bone_names.split(",") if name.strip()]
        sockets = [name.strip() for name in self.socket_names.split(",") if name.strip()]
        
        # Store preset data as individual scene properties
        preset_prefix = f"arvehicles_preset_{self.preset_name}_"
        
        # Clear any existing preset data
        keys_to_remove = [key for key in scene.keys() if key.startswith(preset_prefix)]
        for key in keys_to_remove:
            del scene[key]
        
        # Use the longer list as the count - bones take priority
        max_count = max(len(bones), len(sockets)) if sockets else len(bones)
        
        # Store new preset data
        scene[f"{preset_prefix}count"] = max_count
        scene[f"{preset_prefix}bone_index"] = 0
        scene[f"{preset_prefix}socket_index"] = 0
        scene[f"{preset_prefix}phase"] = "bones"
        scene[f"{preset_prefix}parent_meshes"] = self.parent_meshes
        
        # Store bone data - all bones get stored
        for i in range(max_count):
            if i < len(bones):
                scene[f"{preset_prefix}bone_{i}"] = bones[i]
            else:
                # If we run out of bones, create generic names
                scene[f"{preset_prefix}bone_{i}"] = f"v_component_{i+1:03d}"
        
        # Store socket data - pad with generic names if needed
        for i in range(max_count):
            if i < len(sockets):
                scene[f"{preset_prefix}socket_{i}"] = sockets[i]
            else:
                # If we run out of sockets, create generic names
                scene[f"{preset_prefix}socket_{i}"] = f"Socket_Component_{i+1:03d}"
        
        # Set as active preset
        scene["arvehicles_active_preset"] = self.preset_name
        
        # Debug info
        print(f"Debug: Parsed {len(bones)} bones, {len(sockets)} sockets")
        print(f"Debug: Stored {max_count} items total")
        
        # Report with length information
        if len(bones) != len(sockets):
            self.report({'WARNING'}, f"Created preset '{self.preset_name}' with {max_count} items. Note: {len(bones)} bones, {len(sockets)} sockets - padded shorter list")
        else:
            self.report({'INFO'}, f"Created preset '{self.preset_name}' with {max_count} items. Starting with bone separation phase!")
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=400)
    
    def draw(self, context):
        layout = self.layout
        
        layout.prop(self, "preset_name")
        layout.separator()
        
        layout.label(text="Bone Names (comma-separated):")
        layout.prop(self, "bone_names", text="")
        
        layout.label(text="Socket Names (comma-separated):")  
        layout.prop(self, "socket_names", text="")
        
        layout.separator()
        layout.prop(self, "parent_meshes")
        
        layout.separator()
        layout.label(text="Phase 1: Bone separation with auto mesh naming")
        layout.label(text="Phase 2: Socket placement using face selection")
        layout.separator()
        layout.label(text="Note: Lists can have different lengths - shorter list will be padded")

class ARVEHICLES_OT_preset_separation(bpy.types.Operator):
    bl_idname = "arvehicles.preset_separation"
    bl_label = "Separate Action"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Separate component using current preset item — opens full separation dialog pre-filled with preset values"

    # ---- All the same properties as ARVEHICLES_OT_separate_components ----
    from ..constants import VEHICLE_COMPONENT_TYPES as _comp_types
    component_type: bpy.props.EnumProperty(name="Component Type", items=_comp_types, default='door')
    custom_name: bpy.props.StringProperty(name="Custom Name", default="")

    add_socket: bpy.props.BoolProperty(name="Add Socket", default=True)
    custom_socket_name: bpy.props.StringProperty(name="Custom Socket Name", default="")
    set_origin_to_socket: bpy.props.BoolProperty(name="Set Origin to Socket", default=True)
    parent_socket_to_armature: bpy.props.BoolProperty(name="Parent Socket to Armature", default=True)

    add_bone: bpy.props.BoolProperty(name="Add Bone", default=True)
    custom_bone_name: bpy.props.StringProperty(name="Custom Bone Name", default="")
    auto_skinning: bpy.props.BoolProperty(name="Auto Skinning", default=True)
    invert_bone_direction: bpy.props.BoolProperty(name="Invert Bone Direction", default=False)

    use_world_direction: bpy.props.BoolProperty(name="Use World Direction", default=False)
    world_direction: bpy.props.EnumProperty(
        name="World Direction",
        items=[
            ('POS_Y', "+Y (Forward)", ""),
            ('NEG_Y', "-Y (Backward)", ""),
            ('POS_X', "+X (Right)", ""),
            ('NEG_X', "-X (Left)", ""),
            ('POS_Z', "+Z (Up)", ""),
            ('NEG_Z', "-Z (Down)", ""),
        ],
        default='POS_Y'
    )
    preserve_angle: bpy.props.BoolProperty(name="Preserve Angle", default=False)
    bone_primary_axis: bpy.props.EnumProperty(
        name="Primary Rotation Axis",
        items=[
            ('Y', "Y Axis (Default)", ""),
            ('X', "X Axis", ""),
            ('Z', "Z Axis", ""),
        ],
        default='Y'
    )
    swap_yz_axes: bpy.props.BoolProperty(name="Swap Y↔Z Axes", default=False)
    align_roll_to_axis: bpy.props.EnumProperty(
        name="Align Roll To",
        items=[
            ('NONE',    "Auto (Roll=0)", ""),
            ('WORLD_Z', "World Z (Up)", ""),
            ('WORLD_X', "World X", ""),
            ('WORLD_Y', "World Y", ""),
        ],
        default='WORLD_Z'
    )
    set_mesh_origin_to_bone: bpy.props.BoolProperty(name="Set Mesh Origin to Bone", default=True)
    parent_to_specific_bone: bpy.props.BoolProperty(
        name="Parent Bone to Specific Bone",
        default=False
    )

    def get_available_bones(self, context):
        items = [('NONE', "v_body (Default)", "Parent to v_body or v_root")]
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                for bone in obj.data.bones:
                    items.append((bone.name, bone.name, f"Parent new bone to {bone.name}"))
                break
        return items

    target_bone: bpy.props.EnumProperty(
        name="Parent Bone",
        description="Existing bone to parent the new bone to",
        items=get_available_bones
    )

    parent_to_existing_bone: bpy.props.BoolProperty(
        name="Skin to Existing Bone",
        default=False
    )

    def get_existing_bones(self, context):
        items = [('NONE', "— Select Bone —", "No bone selected")]
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                for bone in obj.data.bones:
                    items.append((bone.name, bone.name, f"Skin mesh to {bone.name}"))
                break
        return items

    existing_target_bone: bpy.props.EnumProperty(
        name="Target Bone",
        items=get_existing_bones
    )

    # ---- Preset tracking (internal) ----
    _preset_prefix: bpy.props.StringProperty(options={'HIDDEN'}, default="")

    def invoke(self, context, event):
        scene = context.scene

        if "arvehicles_active_preset" not in scene:
            self.report({'ERROR'}, "No active preset. Create a preset first.")
            return {'CANCELLED'}

        preset_name = scene["arvehicles_active_preset"]
        preset_prefix = f"arvehicles_preset_{preset_name}_"
        self._preset_prefix = preset_prefix

        if f"{preset_prefix}count" not in scene:
            self.report({'ERROR'}, f"Preset '{preset_name}' data not found.")
            return {'CANCELLED'}

        preset_count = scene[f"{preset_prefix}count"]
        current_phase = scene.get(f"{preset_prefix}phase", "bones")

        if current_phase == "bones":
            bone_index = scene.get(f"{preset_prefix}bone_index", 0)
            if bone_index >= preset_count:
                # Transition to socket phase without showing dialog
                scene[f"{preset_prefix}phase"] = "sockets"
                scene[f"{preset_prefix}socket_index"] = 0
                self.report({'INFO'}, "Bone phase complete! Now place sockets.")
                return {'FINISHED'}
            bone_name = scene[f"{preset_prefix}bone_{bone_index}"]
            self.custom_bone_name = bone_name
            self.custom_name = f"Mesh_{bone_name}"
            self.add_bone = True
        else:
            # Socket phase — no full dialog needed, but we open it anyway
            # so user can confirm socket placement settings
            socket_index = scene.get(f"{preset_prefix}socket_index", 0)
            if socket_index >= preset_count:
                self.report({'INFO'}, "All preset items complete!")
                return {'FINISHED'}
            socket_name = scene[f"{preset_prefix}socket_{socket_index}"]
            self.custom_socket_name = socket_name
            self.add_bone = False
            self.add_socket = True

        return context.window_manager.invoke_props_dialog(self, width=420)

    def execute(self, context):
        scene = context.scene
        preset_prefix = self._preset_prefix

        if not preset_prefix or f"{preset_prefix}count" not in scene:
            self.report({'ERROR'}, "Preset data lost — re-invoke the operator")
            return {'CANCELLED'}

        # Delegate the actual work to separate_components with all our current prop values
        result = bpy.ops.arvehicles.separate_components(
            'EXEC_DEFAULT',
            component_type=self.component_type,
            custom_name=self.custom_name,
            add_socket=self.add_socket,
            custom_socket_name=self.custom_socket_name,
            set_origin_to_socket=self.set_origin_to_socket,
            parent_socket_to_armature=self.parent_socket_to_armature,
            add_bone=self.add_bone,
            custom_bone_name=self.custom_bone_name,
            auto_skinning=self.auto_skinning,
            invert_bone_direction=self.invert_bone_direction,
            use_world_direction=self.use_world_direction,
            world_direction=self.world_direction,
            preserve_angle=self.preserve_angle,
            bone_primary_axis=self.bone_primary_axis,
            swap_yz_axes=self.swap_yz_axes,
            align_roll_to_axis=self.align_roll_to_axis,
            set_mesh_origin_to_bone=self.set_mesh_origin_to_bone,
            parent_to_specific_bone=self.parent_to_specific_bone,
            target_bone=self.target_bone,
            parent_to_existing_bone=self.parent_to_existing_bone,
            existing_target_bone=self.existing_target_bone,
        )

        if 'FINISHED' not in result:
            return result

        # Advance preset index
        preset_count = scene[f"{preset_prefix}count"]
        current_phase = scene.get(f"{preset_prefix}phase", "bones")

        if current_phase == "bones":
            bone_index = scene.get(f"{preset_prefix}bone_index", 0)
            new_index = bone_index + 1
            scene[f"{preset_prefix}bone_index"] = new_index
            if new_index >= preset_count:
                scene[f"{preset_prefix}phase"] = "sockets"
                scene[f"{preset_prefix}socket_index"] = 0
                self.report({'INFO'}, f"Created '{self.custom_name}'. Bone phase complete! Ready for socket phase.")
            else:
                next_bone = scene.get(f"{preset_prefix}bone_{new_index}", "?")
                remaining = preset_count - new_index
                self.report({'INFO'}, f"Created '{self.custom_name}'. Next: Mesh_{next_bone} ({remaining} remaining)")
        else:
            socket_index = scene.get(f"{preset_prefix}socket_index", 0)
            new_index = socket_index + 1
            scene[f"{preset_prefix}socket_index"] = new_index
            if new_index >= preset_count:
                self.report({'INFO'}, f"Placed '{self.custom_socket_name}'. All presets complete!")
            else:
                next_socket = scene.get(f"{preset_prefix}socket_{new_index}", "?")
                remaining = preset_count - new_index
                self.report({'INFO'}, f"Placed '{self.custom_socket_name}'. Next: {next_socket} ({remaining} remaining)")

        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        preset_prefix = self._preset_prefix
        current_phase = scene.get(f"{preset_prefix}phase", "bones") if preset_prefix else "bones"

        # Show preset context
        box = layout.box()
        if preset_prefix:
            preset_name = scene.get("arvehicles_active_preset", "?")
            box.label(text=f"Preset: {preset_name}", icon='PRESET')
            if current_phase == "bones":
                box.label(text=f"Phase: Bones → {self.custom_name}", icon='BONE_DATA')
            else:
                box.label(text=f"Phase: Sockets → {self.custom_socket_name}", icon='EMPTY_DATA')

        layout.prop(self, "component_type")
        layout.prop(self, "custom_name")

        # Socket options
        layout.separator()
        box = layout.box()
        box.label(text="Socket Options", icon='EMPTY_DATA')
        box.prop(self, "add_socket")
        if self.add_socket:
            box.prop(self, "custom_socket_name")
            box.prop(self, "set_origin_to_socket")
            box.prop(self, "parent_socket_to_armature")

        # Bone options
        layout.separator()
        box = layout.box()
        box.label(text="Bone Options", icon='BONE_DATA')
        box.prop(self, "add_bone")
        if self.add_bone:
            box.prop(self, "custom_bone_name")
            box.prop(self, "auto_skinning")
            box.prop(self, "set_mesh_origin_to_bone")

            box.separator()
            box.label(text="Bone Direction:")
            box.prop(self, "use_world_direction")
            if self.use_world_direction:
                box.prop(self, "world_direction")
                box.prop(self, "preserve_angle")
            else:
                box.prop(self, "invert_bone_direction")

            box.separator()
            box.label(text="Bone Orientation:")
            box.prop(self, "bone_primary_axis")
            box.prop(self, "swap_yz_axes")
            box.prop(self, "align_roll_to_axis")

            box.separator()
            box.label(text="Bone Hierarchy:", icon='OUTLINER')
            box.prop(self, "parent_to_specific_bone")
            if self.parent_to_specific_bone:
                box.prop(self, "target_bone", text="", icon='BONE_DATA')
                if self.target_bone != 'NONE':
                    ib = box.box()
                    ib.label(text=f"New Bone → {self.target_bone}", icon='INFO')
            else:
                ib = box.box()
                ib.label(text="Default: Bone → v_body", icon='INFO')
        else:
            box.separator()
            box.prop(self, "parent_to_existing_bone")
            if self.parent_to_existing_bone:
                box.prop(self, "existing_target_bone", text="", icon='BONE_DATA')
                if self.existing_target_bone != 'NONE':
                    ib = box.box()
                    ib.label(text=f"Mesh → {self.existing_target_bone}", icon='INFO')
                else:
                    ib = box.box()
                    ib.label(text="Select a bone to skin to", icon='ERROR')



class ARVEHICLES_OT_skip_preset_item(bpy.types.Operator):
    bl_idname = "arvehicles.skip_preset_item"
    bl_label = "Skip"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Skip the current preset item and move to the next"
    
    def execute(self, context):
        scene = context.scene
        
        if "arvehicles_active_preset" not in scene:
            self.report({'ERROR'}, "No active preset")
            return {'CANCELLED'}
        
        preset_name = scene["arvehicles_active_preset"]
        preset_prefix = f"arvehicles_preset_{preset_name}_"
        
        count_key = f"{preset_prefix}count"
        if count_key not in scene:
            self.report({'ERROR'}, f"Preset '{preset_name}' data not found")
            return {'CANCELLED'}
        
        preset_count = scene[count_key]
        current_phase = scene.get(f"{preset_prefix}phase", "bones")
        
        if current_phase == "bones":
            bone_index = scene.get(f"{preset_prefix}bone_index", 0)
            if bone_index >= preset_count:
                scene[f"{preset_prefix}phase"] = "sockets"
                scene[f"{preset_prefix}socket_index"] = 0
                self.report({'INFO'}, "Bone phase complete! Now in socket phase.")
                return {'FINISHED'}
            
            # Get current bone name before incrementing
            skipped_bone = scene[f"{preset_prefix}bone_{bone_index}"]
            scene[f"{preset_prefix}bone_index"] = bone_index + 1
            
            # Calculate remaining AFTER incrementing
            new_bone_index = bone_index + 1
            remaining = preset_count - new_bone_index
            
            if remaining > 0:
                # Check if next bone exists before accessing it
                next_bone_key = f"{preset_prefix}bone_{new_bone_index}"
                if next_bone_key in scene:
                    next_bone = scene[next_bone_key]
                    self.report({'INFO'}, f"Skipped '{skipped_bone}'. Next: {next_bone} ({remaining} remaining)")
                else:
                    self.report({'INFO'}, f"Skipped '{skipped_bone}'. ({remaining} remaining)")
            else:
                scene[f"{preset_prefix}phase"] = "sockets"
                scene[f"{preset_prefix}socket_index"] = 0
                self.report({'INFO'}, f"Skipped '{skipped_bone}'. Bone phase complete! Now in socket phase.")
                
        else:
            socket_index = scene.get(f"{preset_prefix}socket_index", 0)
            if socket_index >= preset_count:
                self.report({'INFO'}, "All preset items complete!")
                return {'FINISHED'}
            
            # Get current socket name before incrementing
            skipped_socket = scene[f"{preset_prefix}socket_{socket_index}"]
            scene[f"{preset_prefix}socket_index"] = socket_index + 1
            
            # Calculate remaining AFTER incrementing
            new_socket_index = socket_index + 1
            remaining = preset_count - new_socket_index
            
            if remaining > 0:
                # Check if next socket exists before accessing it
                next_socket_key = f"{preset_prefix}socket_{new_socket_index}"
                if next_socket_key in scene:
                    next_socket = scene[next_socket_key]
                    self.report({'INFO'}, f"Skipped '{skipped_socket}'. Next: {next_socket} ({remaining} remaining)")
                else:
                    self.report({'INFO'}, f"Skipped '{skipped_socket}'. ({remaining} remaining)")
            else:
                self.report({'INFO'}, f"Skipped '{skipped_socket}'. All presets complete!")
        
        return {'FINISHED'}

class ARVEHICLES_OT_reset_preset(bpy.types.Operator):
    bl_idname = "arvehicles.reset_preset"
    bl_label = "Reset Preset"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Reset preset to bone phase"
    
    def execute(self, context):
        scene = context.scene
        
        if "arvehicles_active_preset" not in scene:
            self.report({'ERROR'}, "No active preset")
            return {'CANCELLED'}
        
        preset_name = scene["arvehicles_active_preset"]
        preset_prefix = f"arvehicles_preset_{preset_name}_"
        
        scene[f"{preset_prefix}bone_index"] = 0
        scene[f"{preset_prefix}socket_index"] = 0
        scene[f"{preset_prefix}phase"] = "bones"
        
        self.report({'INFO'}, f"Reset preset '{preset_name}' to bone phase")
        return {'FINISHED'}