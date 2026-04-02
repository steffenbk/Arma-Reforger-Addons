# SPDX-License-Identifier: GPL-2.0-or-later

import re
import bpy
from bpy.props import StringProperty, BoolProperty
from bpy.types import Operator

from ..utils import (
    get_armature,
    get_type_prefix,
    generate_new_action_name,
    get_exclude_patterns,
    get_include_patterns,
    refresh_switcher,
    do_switch_animation,
)


class ARMA_OT_refresh_actions(Operator):
    bl_idname = "arma.refresh_actions"
    bl_label = "Refresh Actions"
    bl_description = "Refresh the list of available actions"

    def execute(self, context):
        scene = context.scene
        arma_props = scene.arma_nla_props

        arma_props.action_list.clear()

        prefix = arma_props.asset_prefix.strip()
        exclude_patterns = get_exclude_patterns(prefix, arma_props.asset_type)

        for action in sorted(bpy.data.actions, key=lambda x: x.name):
            if not arma_props.show_generated:
                if any(action.name.startswith(p) for p in exclude_patterns):
                    continue

            item = arma_props.action_list.add()
            item.name = action.name
            item.original_name = action.name
            item.selected = False

        self.report({'INFO'}, f"Found {len(arma_props.action_list)} source actions")
        return {'FINISHED'}


class ARMA_OT_select_all_actions(Operator):
    bl_idname = "arma.select_all_actions"
    bl_label = "Select All"
    bl_description = "Select or deselect all actions"

    select_all: BoolProperty(default=True)

    def execute(self, context):
        arma_props = context.scene.arma_nla_props
        for item in arma_props.action_list:
            item.selected = self.select_all
        action_word = "Selected" if self.select_all else "Deselected"
        self.report({'INFO'}, f"{action_word} all actions")
        return {'FINISHED'}


class ARMA_OT_process_nla(Operator):
    bl_idname = "arma.process_nla"
    bl_label = "Process NLA"
    bl_description = "Convert selected actions to NLA strips and create new editable actions (requires Pose Mode)"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        armature = get_armature(context)
        if not armature:
            cls.poll_message_set("No armature found")
            return False
        if context.mode != 'POSE':
            cls.poll_message_set("Switch to Pose Mode first")
            return False
        return True

    def execute(self, context):
        scene = context.scene
        arma_props = scene.arma_nla_props

        armature = get_armature(context)
        if not armature:
            self.report({'ERROR'}, "No armature found. Please select an armature object.")
            return {'CANCELLED'}

        if not armature.animation_data:
            armature.animation_data_create()

        selected_actions = [item for item in arma_props.action_list if item.selected]
        if not selected_actions:
            self.report({'ERROR'}, "No actions selected")
            return {'CANCELLED'}

        prefix = arma_props.asset_prefix.strip()
        asset_type = arma_props.asset_type

        # Pin this armature so the plugin keeps targeting it even when
        # a weapon/secondary rig becomes the active object later.
        arma_props.target_armature = armature

        # Save state so we can restore or redirect after the loop
        original_action = armature.animation_data.action
        first_new_action = None

        processed_count = 0
        skipped_count = 0
        error_count = 0

        for item in selected_actions:
            action = bpy.data.actions.get(item.original_name)
            if not action:
                error_count += 1
                continue

            try:
                new_name = generate_new_action_name(item.original_name, prefix, asset_type)

                if bpy.data.actions.get(new_name):
                    skipped_count += 1
                    continue

                # Push original action down to an NLA track
                armature.animation_data.action = action
                track_name = f"{new_name}_track"
                track = armature.animation_data.nla_tracks.new()
                track.name = track_name
                strip = track.strips.new(action.name, int(action.frame_range[0]), action)
                strip.name = f"ref_{item.original_name}"
                strip.blend_type = 'COMBINE'
                armature.animation_data.action = None

                # Rename source action to mark it as a stash reference
                action.name = f"_{item.original_name}"
                action.use_fake_user = False

                # Create the new blank editable action
                new_action = bpy.data.actions.new(new_name)
                new_action.use_fake_user = True

                processed_count += 1
                if first_new_action is None:
                    first_new_action = new_action

            except Exception as e:
                self.report({'WARNING'}, f"Error processing {item.original_name}: {str(e)}")
                error_count += 1

        # After processing, mute all tracks then activate the first new action
        # properly via do_switch_animation (which un-mutes only the relevant track).
        if processed_count > 0:
            # Mute everything first — process_nla leaves all tracks un-muted
            for track in armature.animation_data.nla_tracks:
                track.mute = True

            if arma_props.set_active_action and first_new_action:
                do_switch_animation(context, first_new_action.name)
            else:
                armature.animation_data.action = original_action
        else:
            armature.animation_data.action = original_action

        result_msg = f"Processed: {processed_count}, Skipped: {skipped_count}, Errors: {error_count}"

        if processed_count > 0:
            self.report({'INFO'}, f"Success! {result_msg}")
        elif skipped_count > 0:
            self.report({'WARNING'}, f"All actions already exist. {result_msg}")
        else:
            self.report({'ERROR'}, f"No actions processed. {result_msg}")

        refresh_switcher(scene, context)
        return {'FINISHED'}


class ARMA_OT_switch_animation(Operator):
    bl_idname = "arma.switch_animation"
    bl_label = "Switch Animation"
    bl_description = "Switch to the selected animation and enable its corresponding NLA track"
    bl_options = {'REGISTER', 'UNDO'}

    action_name: StringProperty(default="")

    def execute(self, context):
        armature = get_armature(context)
        if not armature or not armature.animation_data:
            self.report({'ERROR'}, "No armature with animation data found")
            return {'CANCELLED'}

        if not bpy.data.actions.get(self.action_name):
            self.report({'ERROR'}, f"Action '{self.action_name}' not found")
            return {'CANCELLED'}

        do_switch_animation(context, self.action_name)
        refresh_switcher(context.scene, context)
        self.report({'INFO'}, f"Switched to: {self.action_name}")
        return {'FINISHED'}


class ARMA_OT_edit_stash_action(Operator):
    bl_idname = "arma.edit_stash_action"
    bl_label = "Edit Stash Action"
    bl_description = "Set the stashed reference action as the active action for editing"
    bl_options = {'REGISTER', 'UNDO'}

    action_name: StringProperty(default="")

    def execute(self, context):
        armature = get_armature(context)
        if not armature or not armature.animation_data:
            self.report({'ERROR'}, "No armature with animation data found")
            return {'CANCELLED'}

        track_name = f"{self.action_name}_track"
        target_track = None
        for track in armature.animation_data.nla_tracks:
            if track.name == track_name:
                target_track = track
                break

        if not target_track or not target_track.strips:
            self.report({'ERROR'}, f"No stash track found for '{self.action_name}'")
            return {'CANCELLED'}

        stash_action = target_track.strips[0].action
        if not stash_action:
            self.report({'ERROR'}, "No action found in stash track")
            return {'CANCELLED'}

        armature.animation_data.action = stash_action

        for track in armature.animation_data.nla_tracks:
            if track == target_track:
                track.mute = False
                track.select = True
                for strip in track.strips:
                    strip.select = True
            else:
                track.mute = False
                track.select = False
                for strip in track.strips:
                    strip.select = False

        armature.animation_data.nla_tracks.active = target_track

        if context.screen:
            for area in context.screen.areas:
                if area.type == 'NLA_EDITOR':
                    area.tag_redraw()

        refresh_switcher(context.scene, context)
        self.report({'INFO'}, f"Editing stash action: {stash_action.name}")
        return {'FINISHED'}


class ARMA_OT_create_new_action(Operator):
    bl_idname = "arma.create_new_action"
    bl_label = "Create New Action"
    bl_description = "Create a new blank action with NLA track and fake user"
    bl_options = {'REGISTER', 'UNDO'}

    action_name: StringProperty(
        name="Action Name",
        description="Name for the new action (prefix will be added automatically)",
        default="new_animation"
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        arma_props = context.scene.arma_nla_props
        layout.prop(self, "action_name")

        if arma_props.asset_prefix:
            prefix = arma_props.asset_prefix.strip()
            full_name = f"{get_type_prefix(arma_props.asset_type, prefix)}{self.action_name}"
            box = layout.box()
            box.label(text="Will create:", icon='INFO')
            box.label(text=full_name)

    def execute(self, context):
        arma_props = context.scene.arma_nla_props

        armature = get_armature(context)
        if not armature:
            self.report({'ERROR'}, "No armature found. Please select an armature object.")
            return {'CANCELLED'}

        if not armature.animation_data:
            armature.animation_data_create()

        prefix = arma_props.asset_prefix.strip()
        if not prefix:
            self.report({'ERROR'}, "Please set an asset prefix first")
            return {'CANCELLED'}

        full_name = f"{get_type_prefix(arma_props.asset_type, prefix)}{self.action_name}"

        if bpy.data.actions.get(full_name):
            self.report({'ERROR'}, f"Action '{full_name}' already exists")
            return {'CANCELLED'}

        new_action = bpy.data.actions.new(full_name)
        new_action.use_fake_user = True

        track_name = f"{full_name}_track"
        track = armature.animation_data.nla_tracks.new()
        track.name = track_name

        armature.animation_data.action = new_action

        for other_track in armature.animation_data.nla_tracks:
            if other_track == track:
                other_track.mute = False
                other_track.select = True
            else:
                other_track.mute = True
                other_track.select = False

        armature.animation_data.nla_tracks.active = track

        refresh_switcher(context.scene, context)
        self.report({'INFO'}, f"Created: {full_name}")
        return {'FINISHED'}


class ARMA_OT_delete_action(Operator):
    bl_idname = "arma.delete_action"
    bl_label = "Delete Action"
    bl_description = "Delete this generated action and its NLA reference track"
    bl_options = {'REGISTER', 'UNDO'}

    action_name: StringProperty(default="")

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        action = bpy.data.actions.get(self.action_name)
        if not action:
            self.report({'ERROR'}, f"Action '{self.action_name}' not found")
            return {'CANCELLED'}

        armature = get_armature(context)
        if armature and armature.animation_data:
            # Clear active action if it's the one being deleted
            if armature.animation_data.action == action:
                armature.animation_data.action = None
            # Remove the corresponding NLA reference track
            track_name = f"{self.action_name}_track"
            tracks_to_remove = [
                t for t in armature.animation_data.nla_tracks
                if t.name == track_name
            ]
            for track in tracks_to_remove:
                armature.animation_data.nla_tracks.remove(track)

        action.use_fake_user = False
        bpy.data.actions.remove(action)

        refresh_switcher(context.scene, context)
        self.report({'INFO'}, f"Deleted: {self.action_name}")
        return {'FINISHED'}


class ARMA_OT_update_switcher(Operator):
    bl_idname = "arma.update_switcher"
    bl_label = "Update Switcher"
    bl_description = "Update the Quick Animation Switcher list"

    def execute(self, context):
        refresh_switcher(context.scene, context)
        return {'FINISHED'}


class ARMA_OT_clear_search(Operator):
    bl_idname = "arma.clear_search"
    bl_label = "Clear Search"
    bl_description = "Clear the search filter"

    def execute(self, context):
        # Setting the property triggers the update callback which calls refresh_switcher
        context.scene.arma_nla_props.search_filter = ""
        return {'FINISHED'}


class ARMA_OT_export_action_list(Operator):
    bl_idname = "arma.export_action_list"
    bl_label = "Export Action List"
    bl_description = (
        "Export a text file listing all managed actions with frame ranges, "
        "useful for setting up .asi files in Workbench"
    )

    filepath: StringProperty(subtype='FILE_PATH', default="//action_list.txt")
    filter_glob: StringProperty(default="*.txt", options={'HIDDEN'})

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        import os

        arma_props = context.scene.arma_nla_props
        prefix = arma_props.asset_prefix.strip()
        asset_type = arma_props.asset_type

        if not prefix:
            self.report({'ERROR'}, "Set an asset prefix first")
            return {'CANCELLED'}

        include_patterns = get_include_patterns(prefix, asset_type)
        armature = get_armature(context)

        lines = []
        lines.append(f"# Arma Reforger Action List")
        lines.append(f"# Asset Type: {asset_type}  Prefix: {prefix}")
        if armature:
            lines.append(f"# Armature: {armature.name}")
        lines.append(f"# {'Action Name':<50} {'Start':>8} {'End':>8} {'Frames':>8}")
        lines.append(f"# {'-'*50} {'-'*8} {'-'*8} {'-'*8}")

        count = 0
        for action in sorted(bpy.data.actions, key=lambda a: a.name):
            if not any(action.name.startswith(p) for p in include_patterns):
                continue
            start = int(action.frame_range[0])
            end = int(action.frame_range[1])
            length = end - start
            lines.append(f"  {action.name:<50} {start:>8} {end:>8} {length:>8}")
            count += 1

        if count == 0:
            self.report({'WARNING'}, "No matching actions found")
            return {'CANCELLED'}

        filepath = bpy.path.abspath(self.filepath)
        try:
            dirpath = os.path.dirname(filepath)
            if dirpath:
                os.makedirs(dirpath, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines) + '\n')
        except OSError as e:
            self.report({'ERROR'}, f"Cannot write file: {e}")
            return {'CANCELLED'}

        self.report({'INFO'}, f"Exported {count} action(s) to {filepath}")
        return {'FINISHED'}


class ARMA_OT_cleanup_export_duplicates(Operator):
    bl_idname = "arma.cleanup_export_duplicates"
    bl_label = "Clean Up Export Duplicates"
    bl_description = (
        "Remove .001/.002 action copies left behind by the Enfusion TXA exporter. "
        "Only removes a copy when its base-name action also exists"
    )
    bl_options = {'REGISTER', 'UNDO'}

    _suffix_re = re.compile(r'^(.+)\.\d{3,}$')

    def execute(self, context):
        to_remove = []
        for action in bpy.data.actions:
            match = self._suffix_re.match(action.name)
            if match and match.group(1) in bpy.data.actions:
                to_remove.append(action)

        if not to_remove:
            self.report({'INFO'}, "No export duplicate actions found")
            return {'FINISHED'}

        for action in to_remove:
            # Clear from any armature that might still reference it
            armature = get_armature(context)
            if armature and armature.animation_data:
                if armature.animation_data.action == action:
                    armature.animation_data.action = None
            action.use_fake_user = False
            bpy.data.actions.remove(action)

        refresh_switcher(context.scene, context)
        self.report({'INFO'}, f"Removed {len(to_remove)} duplicate action(s)")
        return {'FINISHED'}


class ARMA_OT_copy_bone_location(Operator):
    bl_idname = "arma.copy_bone_location"
    bl_label = "Copy"
    bl_description = "Copy location from the active pose bone"

    @classmethod
    def poll(cls, context):
        return context.active_pose_bone is not None

    def execute(self, context):
        props = context.scene.arma_nla_props
        bone = context.active_pose_bone
        props.loc_stored = bone.location
        props.loc_source_name = bone.name

        axes = []
        if props.loc_copy_x:
            axes.append(f"X:{bone.location.x:.3f}")
        if props.loc_copy_y:
            axes.append(f"Y:{bone.location.y:.3f}")
        if props.loc_copy_z:
            axes.append(f"Z:{bone.location.z:.3f}")
        self.report({'INFO'}, f"Copied {', '.join(axes)} from {bone.name}")
        return {'FINISHED'}


class ARMA_OT_paste_bone_location(Operator):
    bl_idname = "arma.paste_bone_location"
    bl_label = "Paste"
    bl_description = "Paste stored location to the active pose bone (selected axes only)"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        props = context.scene.arma_nla_props
        return (context.active_pose_bone is not None
                and props.loc_source_name != "")

    def execute(self, context):
        props = context.scene.arma_nla_props
        bone = context.active_pose_bone

        if not any((props.loc_copy_x, props.loc_copy_y, props.loc_copy_z)):
            self.report({'WARNING'}, "No axes selected")
            return {'CANCELLED'}

        loc = bone.location.copy()
        axes = []
        if props.loc_copy_x:
            loc.x = props.loc_stored[0]
            axes.append("X")
        if props.loc_copy_y:
            loc.y = props.loc_stored[1]
            axes.append("Y")
        if props.loc_copy_z:
            loc.z = props.loc_stored[2]
            axes.append("Z")
        bone.location = loc

        if context.scene.tool_settings.use_keyframe_insert_auto:
            bone.keyframe_insert(data_path="location")

        self.report({'INFO'}, f"Pasted {', '.join(axes)} to {bone.name}")
        return {'FINISHED'}
