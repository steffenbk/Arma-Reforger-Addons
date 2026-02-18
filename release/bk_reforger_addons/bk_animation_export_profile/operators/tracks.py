import bpy
from bpy.props import StringProperty, EnumProperty, IntProperty
from bpy.types import Operator


class ARPROFILE_OT_add_track(Operator):
    """Add a new track to the export profile"""
    bl_idname = "arprofile.add_track"
    bl_label = "Add Track"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.arprofile_settings
        track = settings.tracks.add()
        track.bone_name = "NewBone"
        track.parent_bone = ""
        track.flags = 'TRD'
        settings.active_track_index = len(settings.tracks) - 1
        return {'FINISHED'}


class ARPROFILE_OT_remove_track(Operator):
    """Remove the selected track"""
    bl_idname = "arprofile.remove_track"
    bl_label = "Remove Track"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.arprofile_settings
        if settings.tracks:
            settings.tracks.remove(settings.active_track_index)
            settings.active_track_index = min(settings.active_track_index, len(settings.tracks) - 1)
        return {'FINISHED'}


class ARPROFILE_OT_rename_bone(Operator):
    """Rename the selected bone"""
    bl_idname = "arprofile.rename_bone"
    bl_label = "Rename Bone"
    bl_options = {'REGISTER', 'UNDO'}

    track_index: IntProperty()
    new_name: StringProperty(name="New Name", default="")

    def invoke(self, context, event):
        settings = context.scene.arprofile_settings
        track = settings.tracks[self.track_index]
        self.new_name = track.bone_name
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "new_name")

    def execute(self, context):
        settings = context.scene.arprofile_settings
        track = settings.tracks[self.track_index]
        old_name = track.bone_name
        track.bone_name = self.new_name

        # Update any children that reference this bone
        for other_track in settings.tracks:
            if other_track.parent_bone == old_name:
                other_track.parent_bone = self.new_name

        self.report({'INFO'}, f"Renamed {old_name} to {self.new_name}")
        return {'FINISHED'}


class ARPROFILE_OT_select_parent(Operator):
    """Select parent bone from available bones"""
    bl_idname = "arprofile.select_parent"
    bl_label = "Select Parent Bone"
    bl_options = {'REGISTER', 'UNDO'}

    track_index: IntProperty()

    def get_parent_items(self, context):
        items = [("", "No Parent (Root/World)", "Export in world space or relative to #movement bone")]
        settings = context.scene.arprofile_settings
        current_track = settings.tracks[self.track_index]

        for track in settings.tracks:
            if track.bone_name != current_track.bone_name:
                items.append((track.bone_name, track.bone_name, f"Make child of {track.bone_name}"))
        return items

    parent_choice: EnumProperty(
        name="Parent Bone",
        description="Choose parent bone",
        items=get_parent_items
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "parent_choice")

    def execute(self, context):
        settings = context.scene.arprofile_settings
        track = settings.tracks[self.track_index]
        track.parent_bone = self.parent_choice

        if self.parent_choice:
            self.report({'INFO'}, f"Set {track.bone_name} parent to {self.parent_choice}")
        else:
            self.report({'INFO'}, f"Cleared parent for {track.bone_name} (now root)")
        return {'FINISHED'}


class ARPROFILE_OT_clear_parent(Operator):
    """Clear parent bone (make root)"""
    bl_idname = "arprofile.clear_parent"
    bl_label = "Clear Parent"
    bl_options = {'REGISTER', 'UNDO'}

    track_index: IntProperty()

    def execute(self, context):
        settings = context.scene.arprofile_settings
        track = settings.tracks[self.track_index]
        track.parent_bone = ""
        self.report({'INFO'}, f"Cleared parent for {track.bone_name}")
        return {'FINISHED'}


class ARPROFILE_OT_add_bones_from_armature(Operator):
    """Add bones from selected armature to the profile"""
    bl_idname = "arprofile.add_bones_from_armature"
    bl_label = "Add All Bones from Armature"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if not context.active_object or context.active_object.type != 'ARMATURE':
            self.report({'ERROR'}, "Please select an armature")
            return {'CANCELLED'}

        armature = context.active_object
        settings = context.scene.arprofile_settings

        # Clear existing tracks
        settings.tracks.clear()

        # Add bones in hierarchy order
        def add_bone_recursive(bone, parent_name=""):
            track = settings.tracks.add()
            track.bone_name = bone.name
            track.parent_bone = parent_name

            # Set default flags based on bone name patterns
            if bone.name.lower() in ['scene_root']:
                track.flags = 'TRG'
                track.use_gen_fn = True
                track.gen_fn_name = "generateSceneRootMB"
            elif bone.name.lower() in ['entityposition', 'hips', 'collision']:
                track.flags = 'TRA'
            else:
                track.flags = 'TRD'

            # Add children
            for child in bone.children:
                add_bone_recursive(child, bone.name)

        # Start with root bones (bones with no parent)
        for bone in armature.data.bones:
            if bone.parent is None:
                add_bone_recursive(bone)

        # Update track count
        settings.track_count = len(settings.tracks)

        self.report({'INFO'}, f"Added {len(settings.tracks)} bones from armature '{armature.name}'")
        return {'FINISHED'}


class ARPROFILE_OT_add_selected_bones(Operator):
    """Add only selected bones from armature to the profile"""
    bl_idname = "arprofile.add_selected_bones"
    bl_label = "Add Selected Bones (Edit/Pose Mode Required)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if not context.active_object or context.active_object.type != 'ARMATURE':
            self.report({'ERROR'}, "Please select an armature")
            return {'CANCELLED'}

        armature = context.active_object
        settings = context.scene.arprofile_settings

        # Get selected bones (in Pose or Edit mode)
        selected_bones = []
        if context.mode == 'POSE':
            selected_bones = [bone.bone for bone in context.selected_pose_bones]
        elif context.mode == 'EDIT_ARMATURE':
            selected_bones = [bone for bone in armature.data.edit_bones if bone.select]
        else:
            self.report({'WARNING'}, "Enter Pose or Edit mode to select specific bones")
            return {'CANCELLED'}

        if not selected_bones:
            self.report({'ERROR'}, "No bones selected. Select bones in Pose or Edit mode.")
            return {'CANCELLED'}

        # Add selected bones
        added_count = 0
        for bone in selected_bones:
            bone_name = bone.name
            existing = False
            for track in settings.tracks:
                if track.bone_name == bone_name:
                    existing = True
                    break

            if not existing:
                track = settings.tracks.add()
                track.bone_name = bone_name

                # Determine parent
                if hasattr(bone, 'parent') and bone.parent:
                    track.parent_bone = bone.parent.name
                else:
                    track.parent_bone = ""

                # Set default flags based on bone name patterns
                if bone_name.lower() in ['scene_root']:
                    track.flags = 'TRG'
                    track.use_gen_fn = True
                    track.gen_fn_name = "generateSceneRootMB"
                elif bone_name.lower() in ['entityposition', 'hips', 'collision']:
                    track.flags = 'TRA'
                else:
                    track.flags = 'TRD'

                added_count += 1

        # Update track count
        settings.track_count = len(settings.tracks)

        if added_count > 0:
            self.report({'INFO'}, f"Added {added_count} selected bones from armature '{armature.name}'")
        else:
            self.report({'INFO'}, "All selected bones already exist in profile")

        return {'FINISHED'}


classes = (
    ARPROFILE_OT_add_track,
    ARPROFILE_OT_remove_track,
    ARPROFILE_OT_add_bones_from_armature,
    ARPROFILE_OT_add_selected_bones,
    ARPROFILE_OT_rename_bone,
    ARPROFILE_OT_select_parent,
    ARPROFILE_OT_clear_parent,
)
