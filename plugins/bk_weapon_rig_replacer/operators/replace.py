# SPDX-License-Identifier: GPL-2.0-or-later

import os

import bpy
from bpy.types import Context, Operator
from bpy.props import StringProperty

from ..utils import (
    find_weapon_armature,
    find_magazine_socket,
    backup_constraints,
    restore_constraints,
    import_from_blend,
    delete_object_hierarchy,
)


class WEAPONRIG_OT_replace_weapon(Operator):
    """Replace the current weapon while preserving constraints"""
    bl_idname = "weaponrig.replace_weapon"
    bl_label = "Replace Weapon"
    bl_description = "Replace the current weapon with a new one"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        props = context.scene.weapon_rig_replacer
        return props.weapon_filepath != ""

    def execute(self, context: Context) -> set[str]:
        try:
            props = context.scene.weapon_rig_replacer

            print("=== WEAPON REPLACEMENT STARTED ===")

            # Find current weapon
            old_weapon = find_weapon_armature()
            if not old_weapon:
                self.report({'ERROR'}, "No weapon armature found in scene")
                return {'CANCELLED'}

            print(f"Found current weapon armature: '{old_weapon.name}'")
            self.report({'INFO'}, f"Found current weapon armature: '{old_weapon.name}'")

            # Backup constraints
            print("Backing up constraints...")
            constraint_data = backup_constraints(old_weapon)
            print(f"Backed up {len(constraint_data)} constraint groups")
            print(f"Constraint data: {constraint_data}")  # Debug: show actual data

            # Import new weapon
            print(f"Importing weapon from: {props.weapon_filepath}")
            self.report({'INFO'}, f"Importing weapon from: {os.path.basename(props.weapon_filepath)}")

            imported_objects = import_from_blend(props.weapon_filepath)
            if not imported_objects:
                self.report({'ERROR'}, "Failed to import weapon from file")
                return {'CANCELLED'}

            print(f"Successfully imported {len(imported_objects)} objects")

            # Find the weapon armature in imported objects
            new_weapon = None
            imported_armatures = [obj for obj in imported_objects if obj.type == 'ARMATURE']

            print(f"Found {len(imported_armatures)} armature(s) in imported file")
            self.report({'INFO'}, f"Found {len(imported_armatures)} armature(s) in imported file")

            if len(imported_armatures) == 1:
                new_weapon = imported_armatures[0]
                print(f"Using armature: '{new_weapon.name}'")
                self.report({'INFO'}, f"Using armature: '{new_weapon.name}'")
            elif len(imported_armatures) > 1:
                # Multiple armatures - try to find the best one
                for obj in imported_armatures:
                    print(f"Available armature: '{obj.name}'")
                    self.report({'INFO'}, f"Available armature: '{obj.name}'")
                    # Use first non-character armature
                    character_indicators = ['rig', 'character', 'metarig']
                    is_character = any(indicator in obj.name.lower() for indicator in character_indicators)
                    if not is_character:
                        new_weapon = obj
                        break

                if not new_weapon:
                    new_weapon = imported_armatures[0]  # Fallback to first

                print(f"Selected armature: '{new_weapon.name}' from multiple options")
                self.report({'INFO'}, f"Selected armature: '{new_weapon.name}' from multiple options")

            if not new_weapon:
                self.report({'ERROR'}, "No armature found in imported weapon file")
                return {'CANCELLED'}

            # Restore constraints to new weapon FIRST (before deletion and renaming)
            print(f"Restoring {len(constraint_data)} constraint groups to new weapon")
            print(f"New weapon before constraints: {new_weapon.name}, has {len(new_weapon.constraints)} constraints")
            self.report({'INFO'}, f"Restoring {len(constraint_data)} constraint groups to new weapon")
            restore_constraints(new_weapon, constraint_data)
            print(f"New weapon after constraints: {new_weapon.name}, has {len(new_weapon.constraints)} constraints")

            # Store old weapon name before deletion
            old_weapon_name = old_weapon.name

            # Delete old weapon
            print(f"Removing old weapon: '{old_weapon.name}' and its children")
            self.report({'INFO'}, f"Removing old weapon: '{old_weapon.name}'")
            delete_object_hierarchy(old_weapon)

            # Rename new weapon after deletion
            if props.weapon_name and props.weapon_name != "Weapon":
                new_weapon.name = props.weapon_name
                print(f"Renamed weapon armature to: '{props.weapon_name}'")
                self.report({'INFO'}, f"Renamed weapon armature to: '{props.weapon_name}'")
            else:
                new_weapon.name = old_weapon_name
                print(f"Renamed weapon armature to original name: '{old_weapon_name}'")
                self.report({'INFO'}, f"Renamed weapon armature to: '{old_weapon_name}'")

            print("=== WEAPON REPLACEMENT COMPLETED ===")
            self.report({'INFO'}, f"Weapon replacement completed successfully!")

        except Exception as e:
            print(f"CRITICAL ERROR in weapon replacement: {e}")
            import traceback
            traceback.print_exc()
            self.report({'ERROR'}, f"Critical error: {str(e)}")
            return {'CANCELLED'}

        return {'FINISHED'}


class WEAPONRIG_OT_replace_magazine(Operator):
    """Replace the current magazine while preserving constraints"""
    bl_idname = "weaponrig.replace_magazine"
    bl_label = "Replace Magazine"
    bl_description = "Replace the current magazine with a new one"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        props = context.scene.weapon_rig_replacer
        return props.magazine_filepath != ""

    def execute(self, context: Context) -> set[str]:
        props = context.scene.weapon_rig_replacer

        # Find current magazine
        old_magazine = find_magazine_socket()
        if not old_magazine:
            self.report({'ERROR'}, "No magazine object found in scene")
            return {'CANCELLED'}

        self.report({'INFO'}, f"Found current magazine: '{old_magazine.name}'")

        # Backup constraints
        constraint_data = backup_constraints(old_magazine)

        # Import new magazine
        try:
            self.report({'INFO'}, f"Importing magazine from: {os.path.basename(props.magazine_filepath)}")
            imported_objects = import_from_blend(props.magazine_filepath)
            if not imported_objects:
                self.report({'ERROR'}, "Failed to import magazine from file")
                return {'CANCELLED'}

            # Find the magazine socket in imported objects
            new_magazine = None
            magazine_candidates = []

            for obj in imported_objects:
                self.report({'INFO'}, f"Found imported object: '{obj.name}' (type: {obj.type})")
                if 'magazine' in obj.name.lower() or 'mag' in obj.name.lower():
                    magazine_candidates.append(obj)

            if len(magazine_candidates) == 1:
                new_magazine = magazine_candidates[0]
                self.report({'INFO'}, f"Using magazine object: '{new_magazine.name}'")
            elif len(magazine_candidates) > 1:
                # Prefer empty objects for sockets
                for obj in magazine_candidates:
                    if obj.type == 'EMPTY':
                        new_magazine = obj
                        break
                if not new_magazine:
                    new_magazine = magazine_candidates[0]  # Fallback
                self.report({'INFO'}, f"Selected magazine: '{new_magazine.name}' from multiple options")
            else:
                # No magazine-named objects, use first imported object
                new_magazine = imported_objects[0]
                self.report({'WARNING'}, f"No magazine-named objects found, using: '{new_magazine.name}'")

            if not new_magazine:
                self.report({'ERROR'}, "No suitable magazine object found in imported file")
                return {'CANCELLED'}

            # Restore constraints to new magazine
            self.report({'INFO'}, f"Restoring {len(constraint_data)} constraints to new magazine")
            restore_constraints(new_magazine, constraint_data)

            # Rename new magazine
            new_magazine.name = props.magazine_name
            self.report({'INFO'}, f"Renamed magazine to: '{props.magazine_name}'")

            # Delete old magazine
            self.report({'INFO'}, f"Removing old magazine: '{old_magazine.name}'")
            delete_object_hierarchy(old_magazine)

            self.report({'INFO'}, f"Magazine replacement completed successfully!")

        except Exception as e:
            self.report({'ERROR'}, f"Error replacing magazine: {str(e)}")
            return {'CANCELLED'}

        return {'FINISHED'}


class WEAPONRIG_OT_browse_weapon_file(Operator):
    """Browse for weapon file"""
    bl_idname = "weaponrig.browse_weapon_file"
    bl_label = "Browse"
    bl_description = "Browse for weapon .blend file"

    filepath: StringProperty(
        name="File Path",
        description="Choose a weapon .blend file",
        maxlen=1024,
        subtype='FILE_PATH'
    )

    filter_glob: StringProperty(
        default="*.blend",
        options={'HIDDEN'}
    )

    def execute(self, context):
        context.scene.weapon_rig_replacer.weapon_filepath = self.filepath
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class WEAPONRIG_OT_browse_magazine_file(Operator):
    """Browse for magazine file"""
    bl_idname = "weaponrig.browse_magazine_file"
    bl_label = "Browse"
    bl_description = "Browse for magazine .blend file"

    filepath: StringProperty(
        name="File Path",
        description="Choose a magazine .blend file",
        maxlen=1024,
        subtype='FILE_PATH'
    )

    filter_glob: StringProperty(
        default="*.blend",
        options={'HIDDEN'}
    )

    def execute(self, context):
        context.scene.weapon_rig_replacer.magazine_filepath = self.filepath
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
