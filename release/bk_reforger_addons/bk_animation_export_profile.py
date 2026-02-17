bl_info = {
    "name": "BK Animation Export Profile",
    "author": "steffenbk",
    "version": (1, 1, 0),
    "blender": (4, 2, 0),
    "location": "3D Viewport > Sidebar > BK Anim Export",
    "description": "Create and manage animation export profiles (.apr) for Arma Reforger",
    "category": "Animation",
}

import bpy
import bmesh
from bpy.props import StringProperty, EnumProperty, BoolProperty, IntProperty, CollectionProperty
from bpy.types import PropertyGroup, Panel, Operator, UIList
import os

# Property Groups
class ARPROFILE_PG_track(PropertyGroup):
    bone_name: StringProperty(
        name="Bone Name",
        description="Name of the bone",
        default=""
    )
    
    parent_bone: StringProperty(
        name="Parent Bone", 
        description="Parent bone name (empty for root or #movement)",
        default=""
    )
    
    flags: EnumProperty(
        name="Flags",
        description="Export flags for this bone",
        items=[
            ('TRA', "TRA - Translation & Rotation Absolute", "Full transform absolute (replaces underlying animation)"),
            ('TRD', "TRD - Translation & Rotation Differential", "Full transform differential/additive (adds to underlying animation)"),
            ('TRG', "TRG - Translation & Rotation Generated", "Generated bone in global space"),
            ('RA', "RA - Rotation Absolute", "Rotation only absolute (replaces underlying rotation)"),
            ('TA', "TA - Translation Absolute", "Translation only absolute"),
        ],
        default='TRD'
    )
    
    # Advanced functions (rarely used)
    use_bone_fn: BoolProperty(name="Use Bone Function", default=False)
    bone_fn_name: StringProperty(name="Function Name", default="")
    use_bone_fn_local: BoolProperty(name="Use Local Function", default=False)
    bone_fn_local_name: StringProperty(name="Function Name", default="")
    use_gen_fn: BoolProperty(name="Use Generator Function", default=False)
    gen_fn_name: StringProperty(name="Generator Function", default="")

class ARPROFILE_PG_settings(PropertyGroup):
    track_count: IntProperty(
        name="Track Count",
        description="Number of tracks (auto-calculated)",
        default=0,
        min=0
    )
    
    movement_bone: StringProperty(
        name="Movement Bone",
        description="Model base bone & movement base (EntityPosition for characters, v_root for vehicles, empty for weapons/parts)",
        default=""
    )
    
    default_fn: StringProperty(
        name="Default Function",
        description="Default GlobalSpace export modifier (MUST be empty for Blender! Use defaultFnMB only for MotionBuilder)",
        default="defaultFnMB"
    )
    
    default_local_fn: StringProperty(
        name="Default Local Function", 
        description="Default LocalSpace export modifier (usually empty)",
        default=""
    )
    
    active_track_index: IntProperty(
        name="Active Track",
        default=0
    )
    
    show_advanced_functions: BoolProperty(
        name="Show Advanced Functions",
        description="Show advanced bone functions (rarely used)",
        default=False
    )
    
    tracks: CollectionProperty(
        type=ARPROFILE_PG_track,
        name="Tracks"
    )

# UI Lists
class ARPROFILE_UL_tracks(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.prop(item, "bone_name", text="", emboss=False)
            row.label(text=f"→ {item.parent_bone if item.parent_bone else 'ROOT'}")
            row.label(text=item.flags)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text=item.bone_name)

# Operators
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
            # In Object mode, get all bones if none specifically selected
            self.report({'WARNING'}, "Enter Pose or Edit mode to select specific bones")
            return {'CANCELLED'}
        
        if not selected_bones:
            self.report({'ERROR'}, "No bones selected. Select bones in Pose or Edit mode.")
            return {'CANCELLED'}
        
        # Add selected bones
        added_count = 0
        for bone in selected_bones:
            # Check if bone already exists
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

# Simple global preset operators
class ARPROFILE_OT_set_global_weapon(Operator):
    """Set global settings for weapon animations"""
    bl_idname = "arprofile.set_global_weapon"
    bl_label = "Weapon Global Settings"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        settings = context.scene.arprofile_settings
        settings.movement_bone = ""
        settings.default_fn = "defaultFnMB"
        settings.default_local_fn = ""
        self.report({'INFO'}, "Applied weapon global settings")
        return {'FINISHED'}

class ARPROFILE_OT_set_global_char_move(Operator):
    """Set global settings for character movement animations"""
    bl_idname = "arprofile.set_global_char_move"
    bl_label = "Character Movement Global Settings"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        settings = context.scene.arprofile_settings
        settings.movement_bone = "EntityPosition"
        settings.default_fn = ""
        settings.default_local_fn = ""
        self.report({'INFO'}, "Applied character movement global settings")
        return {'FINISHED'}

class ARPROFILE_OT_set_global_char_static(Operator):
    """Set global settings for static character animations"""
    bl_idname = "arprofile.set_global_char_static"
    bl_label = "Character Static Global Settings"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        settings = context.scene.arprofile_settings
        settings.movement_bone = ""
        settings.default_fn = ""
        settings.default_local_fn = ""
        self.report({'INFO'}, "Applied character static global settings")
        return {'FINISHED'}

class ARPROFILE_OT_set_global_vehicle(Operator):
    """Set global settings for vehicle animations"""
    bl_idname = "arprofile.set_global_vehicle"
    bl_label = "Vehicle Global Settings"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        settings = context.scene.arprofile_settings
        settings.movement_bone = "v_root"
        settings.default_fn = ""
        settings.default_local_fn = ""
        self.report({'INFO'}, "Applied vehicle global settings")
        return {'FINISHED'}

class ARPROFILE_OT_set_global_vehicle_parts(Operator):
    """Set global settings for vehicle parts animations"""
    bl_idname = "arprofile.set_global_vehicle_parts"
    bl_label = "Vehicle Parts Global Settings"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        settings = context.scene.arprofile_settings
        settings.movement_bone = ""
        settings.default_fn = ""
        settings.default_local_fn = ""
        self.report({'INFO'}, "Applied vehicle parts global settings")
        return {'FINISHED'}

class ARPROFILE_OT_set_global_generic(Operator):
    """Set global settings for generic animations"""
    bl_idname = "arprofile.set_global_generic"
    bl_label = "Generic Global Settings"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        settings = context.scene.arprofile_settings
        settings.movement_bone = ""
        settings.default_fn = ""
        settings.default_local_fn = ""
        self.report({'INFO'}, "Applied generic global settings")
        return {'FINISHED'}

class ARPROFILE_OT_load_preset(Operator):
    """Load a preset profile configuration"""
    bl_idname = "arprofile.load_preset"
    bl_label = "Load Preset"
    bl_options = {'REGISTER', 'UNDO'}
    
    preset_type: EnumProperty(
        name="Preset Type",
        items=[
            ('fullbody_abs', "Full Body Absolute", "Complete character skeleton with absolute transforms"),
            ('fullbody_add', "Full Body Additive", "Complete character skeleton with additive transforms"),
            ('upperbody_abs', "Upper Body Absolute", "Upper body only with absolute transforms"),
            ('weapon_basic', "Basic Weapon", "Basic weapon bone setup"),
            ('weapon_sight', "Weapon Sight", "Weapon sight animation setup"),
            ('vehicle_basic', "Basic Vehicle", "Basic vehicle bone setup"),
        ],
        default='fullbody_add'
    )
    
    def execute(self, context):
        settings = context.scene.arprofile_settings
        settings.tracks.clear()
        
        if self.preset_type == 'fullbody_add':
            # Create full body additive preset similar to FullBody_additive.apr
            bones_data = [
                ("Scene_Root", "", "TRG", True, "generateSceneRootMB"),
                ("EntityPosition", "Scene_Root", "TRA"),
                ("Collision", "EntityPosition", "TRA"),
                ("Hips", "EntityPosition", "TRA"),
                ("LeftLeg", "Hips", "TRD"),
                ("LeftLegVolume", "LeftLeg", "TRD"),
                ("LeftLegTwist", "LeftLeg", "TRD"),
                ("LeftKnee", "LeftLegTwist", "TRD"),
                ("LeftFoot", "LeftKnee", "TRD"),
                ("RightLeg", "Hips", "TRD"),
                ("RightKnee", "RightLeg", "TRD"),
                ("RightFoot", "RightKnee", "TRD"),
                ("Spine1", "Hips", "TRD"),
                ("Spine2", "Spine1", "TRD"),
                ("Spine3", "Spine2", "TRD"),
                ("Spine4", "Spine3", "TRD"),
                ("Spine5", "Spine4", "TRD"),
                ("Neck1", "Spine5", "TRD"),
                ("Head", "Neck1", "TRD"),
                ("LeftShoulder", "Spine5", "TRD"),
                ("LeftArm", "LeftShoulder", "TRD"),
                ("LeftForeArm", "LeftArm", "TRD"),
                ("LeftHand", "LeftForeArm", "TRD"),
                ("RightShoulder", "Spine5", "TRD"),
                ("RightArm", "RightShoulder", "TRD"),
                ("RightForeArm", "RightArm", "TRD"),
                ("RightHand", "RightForeArm", "TRD"),
            ]
            
            for bone_data in bones_data:
                track = settings.tracks.add()
                track.bone_name = bone_data[0]
                track.parent_bone = bone_data[1]
                track.flags = bone_data[2]
                if len(bone_data) > 3 and bone_data[3]:
                    track.use_gen_fn = True
                    track.gen_fn_name = bone_data[4]
                    
        elif self.preset_type == 'weapon_basic':
            bones_data = [
                ("w_root", "", "TRA"),
                ("w_trigger", "w_root", "TRD"),
                ("w_bolt", "w_root", "TRD"),
                ("w_mag_release", "w_root", "TRD"),
                ("w_fire_mode", "w_root", "TRD"),
                ("w_safety", "w_root", "TRD"),
                ("w_sight", "w_root", "TRD"),
                ("w_sight_slider", "w_root", "TRD"),
            ]
            
            for bone_data in bones_data:
                track = settings.tracks.add()
                track.bone_name = bone_data[0]
                track.parent_bone = bone_data[1] 
                track.flags = bone_data[2]
                
        elif self.preset_type == 'weapon_sight':
            # Weapon sight setup with reserved bone names
            bones_data = [
                ("w_root", "", "TRD"),  # Weapon root with differential
                ("w_sight", "w_root", "TRA"),  # Standard sight bone
                ("w_sight_slider", "w_root", "TRA"),  # Standard slider bone
            ]
            
            for bone_data in bones_data:
                track = settings.tracks.add()
                track.bone_name = bone_data[0]
                track.parent_bone = bone_data[1] 
                track.flags = bone_data[2]
        
        # Update settings
        settings.track_count = len(settings.tracks)
        settings.default_fn = "defaultFnMB"  # Always use defaultFnMB for presets
        settings.default_local_fn = ""
        
        self.report({'INFO'}, f"Loaded {self.preset_type} preset with {len(settings.tracks)} tracks")
        return {'FINISHED'}

class ARPROFILE_OT_info_gen_fn(Operator):
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

class ARPROFILE_OT_info_bone_fn(Operator):
    """Show info about Bone Function"""
    bl_idname = "arprofile.info_bone_fn"
    bl_label = "Bone Function Info"
    
    def execute(self, context):
        self.report({'INFO'}, "$boneFn: Modifies bone transform in MODEL SPACE. Used for global adjustments like coordinate conversion or scaling.")
        return {'FINISHED'}

class ARPROFILE_OT_info_bone_fn_local(Operator):
    """Show info about Local Bone Function"""
    bl_idname = "arprofile.info_bone_fn_local"
    bl_label = "Local Bone Function Info"
    
    def execute(self, context):
        self.report({'INFO'}, "$boneFnLocal: Modifies bone transform in PARENT SPACE. Used for local adjustments relative to parent bone.")
        return {'FINISHED'}

def is_reserved_bone_name(bone_name):
    """Check if bone name is potentially reserved in Arma Reforger"""
    reserved_names = [
        'w_sight', 'w_trigger', 'w_bolt', 'w_magazine', 'w_mag_release',
        'w_safety', 'w_fire_mode', 'w_charging_handle', 'w_ch_handle',
        'w_ejection_port', 'w_bolt_release', 'w_slide', 'w_hammer',
        'w_striker', 'w_cylinder', 'w_rear_sight', 'w_front_sight',
        'w_barrel', 'w_bipodleg', 'w_fire_hammer'
    ]
    return bone_name.lower() in reserved_names
    """Show info about Generator Function"""
    bl_idname = "arprofile.info_gen_fn"
    bl_label = "Generator Function Info"
    
    def execute(self, context):
        self.report({'INFO'}, "$genFn: GENERATES bone transforms programmatically. Common for Scene_Root (generateSceneRootMB) or procedural bones.")
        return {'FINISHED'}

class ARPROFILE_OT_export_profile(Operator):
    """Export the animation profile to .apr file"""
    bl_idname = "arprofile.export_profile"
    bl_label = "Export Profile"
    bl_options = {'REGISTER', 'UNDO'}
    
    filepath: StringProperty(
        name="File Path",
        description="Path to save the .apr file",
        subtype='FILE_PATH'
    )
    
    filename: StringProperty(
        name="File Name", 
        description="Name of the .apr file",
        default="CustomProfile.apr"
    )
    
    def invoke(self, context, event):
        self.filepath = self.filename
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
    def execute(self, context):
        settings = context.scene.arprofile_settings
        
        if not settings.tracks:
            self.report({'ERROR'}, "No tracks defined. Add bones first.")
            return {'CANCELLED'}
        
        # Ensure .apr extension
        if not self.filepath.endswith('.apr'):
            self.filepath += '.apr'
        
        try:
            with open(self.filepath, 'w') as f:
                f.write("$animExportProfile {\n")
                f.write(f" #trackCount {len(settings.tracks)}\n")
                f.write(f' #movement "{settings.movement_bone}"\n')
                f.write(f' #defaultFn "{settings.default_fn}"\n')
                f.write(f' #defaultLocalFn "{settings.default_local_fn}"\n')
                f.write(" $tracks {\n")
                
                # Sort tracks to put root bones first (bones with no parent)
                sorted_tracks = []
                root_tracks = []
                child_tracks = []
                
                for track in settings.tracks:
                    if track.parent_bone == "":
                        root_tracks.append(track)
                    else:
                        child_tracks.append(track)
                
                # Root bones first, then child bones
                sorted_tracks = root_tracks + child_tracks
                
                for track in sorted_tracks:
                    line = f'  "{track.bone_name}" "{track.parent_bone}" "{track.flags}"'
                    
                    # Add function modifiers
                    if track.use_bone_fn and track.bone_fn_name:
                        line += f' $boneFn {{ "{track.bone_fn_name}" }}'
                    
                    if track.use_bone_fn_local and track.bone_fn_local_name:
                        line += f' $boneFnLocal {{ "{track.bone_fn_local_name}" }}'
                    
                    if track.use_gen_fn and track.gen_fn_name:
                        line += f' $genFn {{ "{track.gen_fn_name}" }}'
                    
                    f.write(line + "\n")
                
                f.write(" }\n")
                f.write("}\n")
                
            self.report({'INFO'}, f"Exported profile to {self.filepath}")
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to export: {str(e)}")
            return {'CANCELLED'}
            
        return {'FINISHED'}

class ARPROFILE_OT_import_profile(Operator):
    """Import an existing .apr file"""
    bl_idname = "arprofile.import_profile"
    bl_label = "Import Profile"
    bl_options = {'REGISTER', 'UNDO'}
    
    filepath: StringProperty(
        name="File Path",
        description="Path to the .apr file to import",
        subtype='FILE_PATH'
    )
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
    def execute(self, context):
        if not os.path.exists(self.filepath):
            self.report({'ERROR'}, "File not found")
            return {'CANCELLED'}
            
        settings = context.scene.arprofile_settings
        settings.tracks.clear()
        
        try:
            with open(self.filepath, 'r') as f:
                content = f.read()
                
            # Simple parsing - this could be improved with proper parser
            lines = content.split('\n')
            in_tracks = False
            
            for line in lines:
                line = line.strip()
                
                if line.startswith('#trackCount'):
                    settings.track_count = int(line.split()[1])
                elif line.startswith('#movement'):
                    settings.movement_bone = line.split('"')[1] if '"' in line else ""
                elif line.startswith('#defaultFn'):
                    settings.default_fn = line.split('"')[1] if '"' in line else ""
                elif line.startswith('#defaultLocalFn'):
                    settings.default_local_fn = line.split('"')[1] if '"' in line else ""
                elif line == "$tracks {":
                    in_tracks = True
                elif line == "}" and in_tracks:
                    in_tracks = False
                elif in_tracks and line.startswith('"'):
                    # Parse track line
                    parts = line.split('"')
                    if len(parts) >= 6:
                        track = settings.tracks.add()
                        track.bone_name = parts[1]
                        track.parent_bone = parts[3]
                        # Parse flags and functions - simplified
                        remaining = ' '.join(parts[5:])
                        if 'TRA' in remaining:
                            track.flags = 'TRA'
                        elif 'TRD' in remaining:
                            track.flags = 'TRD'
                        elif 'TRG' in remaining:
                            track.flags = 'TRG'
                        
                        # Check for functions
                        if '$genFn' in remaining:
                            track.use_gen_fn = True
                            # Extract function name
                            gen_start = remaining.find('$genFn { "') + 10
                            gen_end = remaining.find('"', gen_start)
                            if gen_end > gen_start:
                                track.gen_fn_name = remaining[gen_start:gen_end]
            
            self.report({'INFO'}, f"Imported {len(settings.tracks)} tracks from {os.path.basename(self.filepath)}")
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to import: {str(e)}")
            return {'CANCELLED'}
            
        return {'FINISHED'}

# Panels
class ARPROFILE_PT_main(Panel):
    """Main panel for animation export profiles"""
    bl_label = "Animation Export Profiles"
    bl_idname = "ARPROFILE_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "BK Anim Export"
    
    def draw(self, context):
        layout = self.layout
        settings = context.scene.arprofile_settings
        
        # Export at the very top
        box = layout.box()
        box.label(text="Export:", icon='EXPORT')
        box.operator("arprofile.export_profile", icon='EXPORT')
        
        # Global settings (simplified)
        box = layout.box()
        box.label(text="Global Settings:", icon='SETTINGS')
        
        # Global preset buttons
        col = box.column()
        col.label(text="Global Presets:")
        
        row = col.row(align=True)
        row.operator("arprofile.set_global_weapon", text="Weapon")
        row.operator("arprofile.set_global_char_move", text="Char Move") 
        row.operator("arprofile.set_global_char_static", text="Char Static")
        
        row2 = col.row(align=True)
        row2.operator("arprofile.set_global_vehicle", text="Vehicle")
        row2.operator("arprofile.set_global_vehicle_parts", text="Vehicle Parts")
        row2.operator("arprofile.set_global_generic", text="Generic")
        
        # Advanced settings toggle
        col.separator()
        col.prop(settings, "show_advanced_functions", icon='PREFERENCES')
        
        # Advanced global settings (hidden by default)
        if settings.show_advanced_functions:
            adv_box = box.box()
            adv_box.label(text="Advanced Global Settings:")
            adv_box.prop(settings, "movement_bone")
            adv_box.prop(settings, "default_fn")
            adv_box.prop(settings, "default_local_fn")
        
        col = box.column()
        col.enabled = False
        col.prop(settings, "track_count", text="Track Count (Auto)")
        
        # Presets and Import combined
        box = layout.box()
        box.label(text="Presets & Import:", icon='PRESET')
        
        # Preset buttons
        col = box.column()
        col.label(text="Load Preset:")
        row = col.row(align=True)
        row.operator("arprofile.load_preset", text="Full Body Add").preset_type = 'fullbody_add'
        row.operator("arprofile.load_preset", text="Weapon").preset_type = 'weapon_basic'
        
        # Import
        col.separator()
        col.label(text="Import from File:")
        col.operator("arprofile.import_profile", icon='IMPORT')
        
        # Bones from scene
        box = layout.box()
        box.label(text="Bones from Scene:", icon='ARMATURE_DATA')
        
        col = box.column()
        col.operator("arprofile.add_bones_from_armature", icon='OUTLINER_OB_ARMATURE')
        col.operator("arprofile.add_selected_bones", icon='RESTRICT_SELECT_OFF')

class ARPROFILE_PT_tracks(Panel):
    """Panel for managing tracks"""
    bl_label = "Tracks"
    bl_idname = "ARPROFILE_PT_tracks"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "BK Anim Export"
    bl_parent_id = "ARPROFILE_PT_main"
    
    def draw(self, context):
        layout = self.layout
        settings = context.scene.arprofile_settings
        
        # Track list
        row = layout.row()
        row.template_list("ARPROFILE_UL_tracks", "", settings, "tracks", 
                         settings, "active_track_index", rows=6)
        
        col = row.column(align=True)
        col.operator("arprofile.add_track", icon='ADD', text="")
        col.operator("arprofile.remove_track", icon='REMOVE', text="")
        
        # Track details
        if settings.tracks and settings.active_track_index < len(settings.tracks):
            track = settings.tracks[settings.active_track_index]
            
            box = layout.box()
            box.label(text=f"Track: {track.bone_name}", icon='BONE_DATA')
            
            # Reserved bone warning at top if applicable
            if is_reserved_bone_name(track.bone_name):
                warning_box = box.box()
                warning_box.alert = True
                warning_box.label(text="⚠ Reserved Bone Name", icon='ERROR')
                warning_box.label(text="Reserved bones (w_sight, w_trigger, w_bolt, etc.) may have")
                warning_box.label(text="hardcoded behaviors when inheriting weapon prefabs.")
                warning_box.label(text="Use custom names if conflicts occur.")
            
            # Bone name - read only with info
            row = box.row()
            row.label(text="Bone Name:")
            row.label(text=track.bone_name, icon='LOCKED')
            row.operator("arprofile.rename_bone", text="", icon='GREASEPENCIL').track_index = settings.active_track_index
            
            # Parent bone - simple input with helper buttons
            box.label(text="Parent Bone:")
            row = box.row()
            row.prop(track, "parent_bone", text="")
            row.operator("arprofile.select_parent", text="", icon='DOWNARROW_HLT').track_index = settings.active_track_index
            row.operator("arprofile.clear_parent", text="", icon='X').track_index = settings.active_track_index
            
            # Flags with better descriptions
            box.prop(track, "flags")
            
            # Advanced functions toggle
            box.prop(settings, "show_advanced_functions", icon='PREFERENCES')
            
            # Advanced function modifiers (hidden by default)
            if settings.show_advanced_functions:
                func_box = box.box()
                func_box.label(text="Advanced Functions:", icon='SCRIPTPLUGINS')
                func_box.label(text="(For expert users only)")
                
                col = func_box.column()
                col.prop(track, "use_bone_fn")
                if track.use_bone_fn:
                    col.prop(track, "bone_fn_name")
                    
                col.prop(track, "use_bone_fn_local")
                if track.use_bone_fn_local:
                    col.prop(track, "bone_fn_local_name")
                    
                col.prop(track, "use_gen_fn")
                if track.use_gen_fn:
                    col.prop(track, "gen_fn_name")

# Registration
classes = [
    ARPROFILE_PG_track,
    ARPROFILE_PG_settings,
    ARPROFILE_UL_tracks,
    ARPROFILE_OT_add_track,
    ARPROFILE_OT_remove_track,
    ARPROFILE_OT_add_bones_from_armature,
    ARPROFILE_OT_add_selected_bones,
    ARPROFILE_OT_set_global_weapon,
    ARPROFILE_OT_set_global_char_move,
    ARPROFILE_OT_set_global_char_static,
    ARPROFILE_OT_set_global_vehicle,
    ARPROFILE_OT_set_global_vehicle_parts,
    ARPROFILE_OT_set_global_generic,
    ARPROFILE_OT_load_preset,
    ARPROFILE_OT_rename_bone,
    ARPROFILE_OT_select_parent,
    ARPROFILE_OT_clear_parent,
    ARPROFILE_OT_export_profile,
    ARPROFILE_OT_import_profile,
    ARPROFILE_PT_main,
    ARPROFILE_PT_tracks,
]

def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            print(f"Failed to register {cls}: {e}")
    
    bpy.types.Scene.arprofile_settings = bpy.props.PointerProperty(type=ARPROFILE_PG_settings)

def unregister():
    # Remove scene property first
    if hasattr(bpy.types.Scene, 'arprofile_settings'):
        del bpy.types.Scene.arprofile_settings
    
    # Unregister classes in reverse order
    for cls in reversed(classes):
        try:
            if hasattr(cls, 'bl_rna'):
                bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"Failed to unregister {cls}: {e}")

if __name__ == "__main__":
    register()
