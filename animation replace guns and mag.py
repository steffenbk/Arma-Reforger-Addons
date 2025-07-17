bl_info = {
    "name": "Arma reforger Weapon Rig Replacer",
    "author": "steffen",
    "version": (1, 0),
    "blender": (4, 2, 0),
    "location": "N-panel in the 3D Viewport",
    "description": "Replace weapons and magazines while preserving constraints",
    "category": "Animation",
    "support": 'COMMUNITY',
}

import bpy
import bmesh
from bpy.types import Context, Operator, Panel, PropertyGroup
from bpy.props import StringProperty, BoolProperty
from mathutils import Matrix
import os


class WeaponRigReplacerProperties(PropertyGroup):
    """Properties for the weapon rig replacer tool."""
    
    weapon_filepath: StringProperty(
        name="Weapon File",
        description="Path to the weapon .blend file",
        default="",
        subtype='FILE_PATH'
    )
    
    magazine_filepath: StringProperty(
        name="Magazine File", 
        description="Path to the magazine .blend file",
        default="",
        subtype='FILE_PATH'
    )
    
    weapon_name: StringProperty(
        name="Weapon Name",
        description="Name for the imported weapon armature",
        default="Weapon"
    )
    
    magazine_name: StringProperty(
        name="Magazine Name",
        description="Name for the imported magazine object",
        default="Magazine"
    )
    
    show_weapon_panel: BoolProperty(
        name="Show Weapon Tools",
        description="Show/hide the weapon replacement tools",
        default=True
    )
    
    show_magazine_panel: BoolProperty(
        name="Show Magazine Tools", 
        description="Show/hide the magazine replacement tools",
        default=True
    )
    
    show_advanced: BoolProperty(
        name="Show Advanced Options",
        description="Show naming and advanced options",
        default=False
    )


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


class VIEW3D_PT_weapon_rig_replacer(Panel):
    """Panel for the weapon rig replacer tool."""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Animation"
    bl_label = "Weapon Rig Replacer"

    def draw(self, context: Context) -> None:
        layout = self.layout
        props = context.scene.weapon_rig_replacer
        
        # Weapon Section
        box = layout.box()
        row = box.row()
        icon = 'DOWNARROW_HLT' if props.show_weapon_panel else 'RIGHTARROW'
        row.prop(props, "show_weapon_panel", text="Weapon Replacement", icon=icon, emboss=False)
        
        if props.show_weapon_panel:
            col = box.column(align=True)
            col.operator("weaponrig.browse_weapon_file", text="Browse for Weapon File", icon='FILEBROWSER')
            
            if props.weapon_filepath:
                col.label(text=f"Selected: {os.path.basename(props.weapon_filepath)}", icon='CHECKMARK')
            
            # Advanced naming options
            if props.show_advanced:
                col.separator()
                col.prop(props, "weapon_name", text="New Name")
            
            col.separator()
            col.operator("weaponrig.replace_weapon", text="Replace Weapon", icon='MESH_DATA')
        
        layout.separator()
        
        # Magazine Section  
        box = layout.box()
        row = box.row()
        icon = 'DOWNARROW_HLT' if props.show_magazine_panel else 'RIGHTARROW'
        row.prop(props, "show_magazine_panel", text="Magazine Replacement", icon=icon, emboss=False)
        
        if props.show_magazine_panel:
            col = box.column(align=True)
            col.operator("weaponrig.browse_magazine_file", text="Browse for Magazine File", icon='FILEBROWSER')
            
            if props.magazine_filepath:
                col.label(text=f"Selected: {os.path.basename(props.magazine_filepath)}", icon='CHECKMARK')
            
            # Advanced naming options
            if props.show_advanced:
                col.separator()
                col.prop(props, "magazine_name", text="New Name")
            
            col.separator()
            col.operator("weaponrig.replace_magazine", text="Replace Magazine", icon='OUTLINER_OB_EMPTY')
        
        layout.separator()
        
        # Advanced Options
        box = layout.box()
        row = box.row()
        icon = 'DOWNARROW_HLT' if props.show_advanced else 'RIGHTARROW'
        row.prop(props, "show_advanced", text="Advanced Options", icon=icon, emboss=False)
        
        layout.separator()
        
        # Info section
        box = layout.box()
        box.label(text="Instructions:", icon='INFO')
        col = box.column(align=True)
        col.label(text="1. Prepare weapon/magazine files")
        col.label(text="2. Parent all meshes to armatures")
        col.label(text="3. Use browse buttons to select files")
        col.label(text="4. Click replace to swap assets")
        col.separator()
        col.label(text="Check console (Window > Toggle System Console)")
        col.label(text="for detailed import information!")


# Registration
classes = (
    WeaponRigReplacerProperties,
    WEAPONRIG_OT_replace_weapon,
    WEAPONRIG_OT_replace_magazine,
    WEAPONRIG_OT_browse_weapon_file,
    WEAPONRIG_OT_browse_magazine_file,
    VIEW3D_PT_weapon_rig_replacer,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.weapon_rig_replacer = bpy.props.PointerProperty(
        type=WeaponRigReplacerProperties
    )


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Scene.weapon_rig_replacer


if __name__ == "__main__":
    register()