# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
from bpy.props import StringProperty, BoolProperty
from bpy.types import Operator

from ..utils import generate_new_action_name, get_exclude_patterns, get_include_patterns


class ARMA_OT_refresh_actions(Operator):
    bl_idname = "arma.refresh_actions"
    bl_label = "Refresh Actions"
    bl_description = "Refresh the list of available actions"

    def execute(self, context):
        scene = context.scene
        arma_props = scene.arma_nla_props

        arma_props.action_list.clear()

        # Get exclusion patterns
        prefix = arma_props.asset_prefix.strip()
        exclude_patterns = get_exclude_patterns(prefix, arma_props.asset_type)

        for action in sorted(bpy.data.actions, key=lambda x: x.name):
            # Skip generated actions unless show_generated is enabled
            should_skip = False
            if not arma_props.show_generated:
                for pattern in exclude_patterns:
                    if action.name.startswith(pattern):
                        should_skip = True
                        break

            if should_skip:
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
        scene = context.scene
        arma_props = scene.arma_nla_props

        for item in arma_props.action_list:
            item.selected = self.select_all

        action_word = "Selected" if self.select_all else "Deselected"
        self.report({'INFO'}, f"{action_word} all actions")
        return {'FINISHED'}


class ARMA_OT_process_nla(Operator):
    bl_idname = "arma.process_nla"
    bl_label = "Process NLA"
    bl_description = "Convert selected actions to NLA strips and create new editable actions"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        arma_props = scene.arma_nla_props

        armature = None
        if context.active_object and context.active_object.type == 'ARMATURE':
            armature = context.active_object
        else:
            for obj in scene.objects:
                if obj.type == 'ARMATURE':
                    armature = obj
                    break

        if not armature:
            self.report({'ERROR'}, "No armature found. Please select an armature object.")
            return {'CANCELLED'}

        if not armature.animation_data:
            armature.animation_data_create()

        selected_actions = [item for item in arma_props.action_list if item.selected]

        if not selected_actions:
            self.report({'ERROR'}, "No actions selected")
            return {'CANCELLED'}

        processed_count = 0
        skipped_count = 0
        error_count = 0
        prefix = arma_props.asset_prefix.strip()
        asset_type = arma_props.asset_type

        for i, item in enumerate(selected_actions):
            action_name = item.original_name
            action = bpy.data.actions.get(action_name)

            if not action:
                error_count += 1
                continue

            try:
                new_name = generate_new_action_name(action_name, prefix, asset_type)

                if bpy.data.actions.get(new_name):
                    skipped_count += 1
                    continue

                # Push down to NLA
                armature.animation_data.action = action

                track_name = f"{new_name}_track"
                track = armature.animation_data.nla_tracks.new()
                track.name = track_name

                strip = track.strips.new(action.name, int(action.frame_range[0]), action)
                strip.name = f"ref_{action_name}"
                strip.blend_type = 'COMBINE'

                armature.animation_data.action = None

                # Create new editable action
                new_action = bpy.data.actions.new(new_name)
                new_action.use_fake_user = True

                armature.animation_data.action = new_action

                # Mute other tracks
                for other_track in armature.animation_data.nla_tracks:
                    if other_track != track:
                        other_track.mute = True
                    else:
                        other_track.mute = False

                processed_count += 1

            except Exception as e:
                print(f"Error processing {action_name}: {str(e)}")
                error_count += 1
                continue

        result_msg = f"Processed: {processed_count}, Skipped: {skipped_count}, Errors: {error_count}"

        if processed_count > 0:
            self.report({'INFO'}, f"Success! {result_msg}")
        elif skipped_count > 0:
            self.report({'WARNING'}, f"All actions already exist. {result_msg}")
        else:
            self.report({'ERROR'}, f"No actions processed. {result_msg}")

        # Auto-refresh switcher
        bpy.ops.arma.update_switcher()

        return {'FINISHED'}


class ARMA_OT_switch_animation(Operator):
    bl_idname = "arma.switch_animation"
    bl_label = "Switch Animation"
    bl_description = "Switch to the selected animation and enable its corresponding NLA track"
    bl_options = {'REGISTER', 'UNDO'}

    action_name: StringProperty(default="")

    def execute(self, context):
        scene = context.scene

        armature = None
        if context.active_object and context.active_object.type == 'ARMATURE':
            armature = context.active_object
        else:
            for obj in scene.objects:
                if obj.type == 'ARMATURE':
                    armature = obj
                    break

        if not armature or not armature.animation_data:
            self.report({'ERROR'}, "No armature with animation data found")
            return {'CANCELLED'}

        action = bpy.data.actions.get(self.action_name)
        if not action:
            self.report({'ERROR'}, f"Action '{self.action_name}' not found")
            return {'CANCELLED'}

        # Set active action
        armature.animation_data.action = action

        # Find and select the corresponding track
        target_track_name = f"{self.action_name}_track"
        target_track = None

        for track in armature.animation_data.nla_tracks:
            if track.name == target_track_name:
                target_track = track
                track.mute = False
                # Select this track in NLA editor
                track.select = True
            else:
                track.mute = True
                # Deselect other tracks
                track.select = False

        # Set the target track as active (this makes it highlighted in NLA editor)
        if target_track:
            armature.animation_data.nla_tracks.active = target_track

        # Update switcher to refresh highlighting
        bpy.ops.arma.update_switcher()

        self.report({'INFO'}, f"Switched to: {self.action_name}")
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

        # Preview the full name
        if arma_props.asset_prefix:
            prefix = arma_props.asset_prefix.strip()
            asset_type = arma_props.asset_type

            if asset_type == 'WEAPON':
                full_name = f"Pl_{prefix}_{self.action_name}"
            elif asset_type == 'VEHICLE':
                full_name = f"v_{prefix}_{self.action_name}"
            elif asset_type == 'PROP':
                full_name = f"prop_{prefix}_{self.action_name}"
            else:  # CUSTOM
                full_name = f"{prefix}_{self.action_name}"

            box = layout.box()
            box.label(text="Will create:", icon='INFO')
            box.label(text=full_name)

    def execute(self, context):
        scene = context.scene
        arma_props = scene.arma_nla_props

        # Find armature
        armature = None
        if context.active_object and context.active_object.type == 'ARMATURE':
            armature = context.active_object
        else:
            for obj in scene.objects:
                if obj.type == 'ARMATURE':
                    armature = obj
                    break

        if not armature:
            self.report({'ERROR'}, "No armature found. Please select an armature object.")
            return {'CANCELLED'}

        if not armature.animation_data:
            armature.animation_data_create()

        # Generate full action name with prefix
        prefix = arma_props.asset_prefix.strip()
        asset_type = arma_props.asset_type

        if not prefix:
            self.report({'ERROR'}, "Please set an asset prefix first")
            return {'CANCELLED'}

        if asset_type == 'WEAPON':
            full_name = f"Pl_{prefix}_{self.action_name}"
        elif asset_type == 'VEHICLE':
            full_name = f"v_{prefix}_{self.action_name}"
        elif asset_type == 'PROP':
            full_name = f"prop_{prefix}_{self.action_name}"
        else:  # CUSTOM
            full_name = f"{prefix}_{self.action_name}"

        # Check if action already exists
        if bpy.data.actions.get(full_name):
            self.report({'ERROR'}, f"Action '{full_name}' already exists")
            return {'CANCELLED'}

        # Create new blank action
        new_action = bpy.data.actions.new(full_name)
        new_action.use_fake_user = True

        # Create NLA track
        track_name = f"{full_name}_track"
        track = armature.animation_data.nla_tracks.new()
        track.name = track_name

        # Set as active action
        armature.animation_data.action = new_action

        # Mute other tracks, select only this track
        for other_track in armature.animation_data.nla_tracks:
            if other_track == track:
                other_track.mute = False
                other_track.select = True
            else:
                other_track.mute = True
                other_track.select = False

        # Set as active track
        armature.animation_data.nla_tracks.active = track

        # Refresh switcher
        bpy.ops.arma.update_switcher()

        self.report({'INFO'}, f"Created: {full_name}")
        return {'FINISHED'}


class ARMA_OT_update_switcher(Operator):
    bl_idname = "arma.update_switcher"
    bl_label = "Update Switcher"
    bl_description = "Update the Quick Animation Switcher list"

    def execute(self, context):
        scene = context.scene
        arma_props = scene.arma_nla_props

        arma_props.switcher_actions.clear()

        prefix = arma_props.asset_prefix.strip()
        asset_type = arma_props.asset_type
        search_term = arma_props.search_filter.lower()

        if not prefix:
            return {'FINISHED'}

        # Get patterns to INCLUDE (these are the generated actions we want to show)
        include_patterns = get_include_patterns(prefix, asset_type)

        current_action = None
        if context.active_object and context.active_object.type == 'ARMATURE':
            if context.active_object.animation_data and context.active_object.animation_data.action:
                current_action = context.active_object.animation_data.action.name

        for action in sorted(bpy.data.actions, key=lambda x: x.name):
            # Check if action matches our patterns (generated actions)
            matches = False
            for pattern in include_patterns:
                if action.name.startswith(pattern):
                    matches = True
                    break

            if not matches:
                continue

            # Apply search filter
            if search_term and search_term not in action.name.lower():
                continue

            item = arma_props.switcher_actions.add()
            item.name = action.name
            item.action_name = action.name
            item.is_active = (action.name == current_action)
            item.has_fake_user = action.use_fake_user
            item.track_name = f"{action.name}_track"

        return {'FINISHED'}


class ARMA_OT_clear_search(Operator):
    bl_idname = "arma.clear_search"
    bl_label = "Clear Search"
    bl_description = "Clear the search filter"

    def execute(self, context):
        context.scene.arma_nla_props.search_filter = ""
        return {'FINISHED'}
