import bpy
from bpy.types import Panel, UIList


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

        col = box.column()
        col.label(text="Load Preset:")
        row = col.row(align=True)
        row.operator("arprofile.load_preset", text="Full Body Add").preset_type = 'fullbody_add'
        row.operator("arprofile.load_preset", text="Weapon").preset_type = 'weapon_basic'

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


classes = (
    ARPROFILE_UL_tracks,
    ARPROFILE_PT_main,
    ARPROFILE_PT_tracks,
)
