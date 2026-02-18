# SPDX-License-Identifier: GPL-2.0-or-later

import os

import bpy


def find_weapon_armature():
    """Find the weapon armature in the scene."""
    # First, look for armatures with 'weapon' in name
    for obj in bpy.context.scene.objects:
        if obj.type == 'ARMATURE' and 'weapon' in obj.name.lower():
            return obj

    # Then look for armatures with weapon-related bones
    for obj in bpy.context.scene.objects:
        if obj.type == 'ARMATURE':
            # Check if it has weapon-specific bones
            weapon_bones = ['w_root', 'w_bolt', 'w_trigger', 'w_fire_mode']
            for bone_name in weapon_bones:
                if bone_name in [bone.name for bone in obj.data.bones]:
                    return obj

    # Look for armatures with weapon-related constraints (like Copy Transforms to RightHandProp)
    for obj in bpy.context.scene.objects:
        if obj.type == 'ARMATURE' and obj.constraints:
            for constraint in obj.constraints:
                if hasattr(constraint, 'subtarget') and constraint.subtarget == 'RightHandProp':
                    return obj

    # Finally, return any armature that's not the character rig
    character_indicators = ['rig', 'character', 'metarig']
    for obj in bpy.context.scene.objects:
        if obj.type == 'ARMATURE':
            # Skip if it's likely a character rig
            is_character = any(indicator in obj.name.lower() for indicator in character_indicators)
            if not is_character:
                return obj

    return None


def find_magazine_socket():
    """Find the magazine socket object in the scene."""
    # First, look for objects with 'magazine' in name
    for obj in bpy.context.scene.objects:
        if 'magazine' in obj.name.lower():
            return obj

    # Then look for objects with 'mag' in name
    for obj in bpy.context.scene.objects:
        if 'mag' in obj.name.lower():
            return obj

    # Look for slot objects
    for obj in bpy.context.scene.objects:
        if 'slot' in obj.name.lower() and ('mag' in obj.name.lower() or 'magazine' in obj.name.lower()):
            return obj

    return None


def backup_constraints(obj):
    """Backup all constraints from an object or bone."""
    constraint_data = []

    if obj.type == 'ARMATURE':
        # First backup bone constraints
        for bone in obj.pose.bones:
            if bone.constraints:
                bone_constraints = []
                for constraint in bone.constraints:
                    constraint_info = {
                        'name': constraint.name,
                        'type': constraint.type,
                        'influence': constraint.influence,
                        'target': constraint.target.name if constraint.target else None,
                        'subtarget': constraint.subtarget if hasattr(constraint, 'subtarget') else None,
                        'bone_name': bone.name
                    }
                    bone_constraints.append(constraint_info)
                if bone_constraints:
                    constraint_data.append({
                        'bone': bone.name,
                        'constraints': bone_constraints
                    })

        # ALSO backup object constraints on the armature itself
        if obj.constraints:
            print(f"Found {len(obj.constraints)} object constraints on armature")
            for constraint in obj.constraints:
                constraint_info = {
                    'name': constraint.name,
                    'type': constraint.type,
                    'influence': constraint.influence,
                    'target': constraint.target.name if constraint.target else None,
                    'subtarget': constraint.subtarget if hasattr(constraint, 'subtarget') else None,
                    'is_object_constraint': True  # Flag to identify object constraints
                }
                constraint_data.append(constraint_info)
                print(f"Backed up object constraint: {constraint.name} -> {constraint_info['target']}")
    else:
        # Backup object constraints for non-armature objects
        if obj.constraints:
            for constraint in obj.constraints:
                constraint_info = {
                    'name': constraint.name,
                    'type': constraint.type,
                    'influence': constraint.influence,
                    'target': constraint.target.name if constraint.target else None,
                    'subtarget': constraint.subtarget if hasattr(constraint, 'subtarget') else None,
                }
                constraint_data.append(constraint_info)

    return constraint_data


def restore_constraints(obj, constraint_data):
    """Restore constraints to an object or armature."""
    if not constraint_data:
        return

    if obj.type == 'ARMATURE':
        # Restore bone constraints and object constraints
        for constraint_info in constraint_data:
            # Check if this is an object constraint (has the flag)
            if isinstance(constraint_info, dict) and constraint_info.get('is_object_constraint'):
                try:
                    print(f"Restoring object constraint: {constraint_info['name']}")
                    # Add constraint to the armature object itself
                    constraint = obj.constraints.new(type=constraint_info['type'])
                    constraint.name = constraint_info['name']
                    constraint.influence = constraint_info['influence']

                    # Set target
                    if constraint_info['target']:
                        target_obj = bpy.context.scene.objects.get(constraint_info['target'])
                        if target_obj:
                            constraint.target = target_obj
                            print(f"Set target to: {target_obj.name}")

                    # Set subtarget
                    if constraint_info['subtarget'] and hasattr(constraint, 'subtarget'):
                        constraint.subtarget = constraint_info['subtarget']
                        print(f"Set subtarget to: {constraint_info['subtarget']}")

                    print(f"Successfully restored object constraint: {constraint.name}")

                except Exception as e:
                    print(f"Error restoring object constraint: {e}")
            else:
                # This is a bone constraint
                bone_name = constraint_info['bone']
                if bone_name in obj.pose.bones:
                    bone = obj.pose.bones[bone_name]
                    for bone_constraint_info in constraint_info['constraints']:
                        try:
                            # Add constraint to bone
                            constraint = bone.constraints.new(type=bone_constraint_info['type'])
                            constraint.name = bone_constraint_info['name']
                            constraint.influence = bone_constraint_info['influence']

                            # Set target
                            if bone_constraint_info['target']:
                                target_obj = bpy.context.scene.objects.get(bone_constraint_info['target'])
                                if target_obj:
                                    constraint.target = target_obj

                            # Set subtarget (bone name)
                            if bone_constraint_info['subtarget'] and hasattr(constraint, 'subtarget'):
                                constraint.subtarget = bone_constraint_info['subtarget']

                        except Exception as e:
                            print(f"Error restoring bone constraint: {e}")
    else:
        # Restore object constraints for non-armature objects
        for constraint_info in constraint_data:
            try:
                constraint = obj.constraints.new(type=constraint_info['type'])
                constraint.name = constraint_info['name']
                constraint.influence = constraint_info['influence']

                # Set target
                if constraint_info['target']:
                    target_obj = bpy.context.scene.objects.get(constraint_info['target'])
                    if target_obj:
                        constraint.target = target_obj

                # Set subtarget
                if constraint_info['subtarget'] and hasattr(constraint, 'subtarget'):
                    constraint.subtarget = constraint_info['subtarget']

            except Exception as e:
                print(f"Error restoring constraint: {e}")


def import_from_blend(filepath, object_names=None, collection_name=None):
    """Import specific objects from a .blend file."""
    if not os.path.exists(filepath):
        print(f"ERROR: File does not exist: {filepath}")
        return None

    imported_objects = []

    try:
        print(f"Attempting to load: {filepath}")

        with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
            print(f"Available objects in file: {list(data_from.objects)}")

            if object_names:
                # Import specific objects
                data_to.objects = [name for name in data_from.objects if name in object_names]
            elif collection_name:
                # Import by collection
                data_to.collections = [collection_name]
            else:
                # Import all objects
                data_to.objects = data_from.objects

        print(f"Objects to import: {[obj.name if obj else 'None' for obj in data_to.objects]}")

        # Link imported objects to scene
        for obj in data_to.objects:
            if obj:
                try:
                    if obj.name not in bpy.context.scene.objects:
                        bpy.context.collection.objects.link(obj)
                        imported_objects.append(obj)
                        print(f"Successfully imported: {obj.name}")
                    else:
                        print(f"Object already exists in scene: {obj.name}")
                except Exception as e:
                    print(f"Error linking object {obj.name}: {e}")

        print(f"Total imported objects: {len(imported_objects)}")
        return imported_objects

    except Exception as e:
        print(f"Critical error in import_from_blend: {e}")
        import traceback
        traceback.print_exc()
        return None


def delete_object_hierarchy(obj):
    """Delete an object and all its children safely."""
    if not obj:
        return

    try:
        print(f"Preparing to delete object hierarchy starting with: {obj.name}")

        # Switch to object mode to ensure safe deletion
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        # Deselect all objects first
        bpy.ops.object.select_all(action='DESELECT')

        # Collect all children recursively
        to_delete = []

        def collect_hierarchy(parent):
            to_delete.append(parent)
            for child in parent.children:
                collect_hierarchy(child)

        collect_hierarchy(obj)

        print(f"Objects to delete: {[o.name for o in to_delete]}")

        # Delete in reverse order (children first, then parents)
        for obj_to_delete in reversed(to_delete):
            try:
                print(f"Deleting: {obj_to_delete.name}")

                # Make sure object exists and is not already deleted
                if obj_to_delete.name in bpy.data.objects:
                    # Remove from all collections
                    for collection in obj_to_delete.users_collection:
                        collection.objects.unlink(obj_to_delete)

                    # Remove the object data and object itself
                    bpy.data.objects.remove(obj_to_delete, do_unlink=True)
                else:
                    print(f"Object {obj_to_delete.name} already deleted")

            except Exception as e:
                print(f"Error deleting {obj_to_delete.name}: {e}")

        print("Deletion completed")

    except Exception as e:
        print(f"Error in delete_object_hierarchy: {e}")
        import traceback
        traceback.print_exc()
