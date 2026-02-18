import bpy
from bpy.props import EnumProperty
from bpy.types import Operator


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
            bones_data = [
                ("w_root", "", "TRD"),
                ("w_sight", "w_root", "TRA"),
                ("w_sight_slider", "w_root", "TRA"),
            ]

            for bone_data in bones_data:
                track = settings.tracks.add()
                track.bone_name = bone_data[0]
                track.parent_bone = bone_data[1]
                track.flags = bone_data[2]

        # Update settings
        settings.track_count = len(settings.tracks)
        settings.default_fn = "defaultFnMB"
        settings.default_local_fn = ""

        self.report({'INFO'}, f"Loaded {self.preset_type} preset with {len(settings.tracks)} tracks")
        return {'FINISHED'}


classes = (
    ARPROFILE_OT_set_global_weapon,
    ARPROFILE_OT_set_global_char_move,
    ARPROFILE_OT_set_global_char_static,
    ARPROFILE_OT_set_global_vehicle,
    ARPROFILE_OT_set_global_vehicle_parts,
    ARPROFILE_OT_set_global_generic,
    ARPROFILE_OT_load_preset,
)
