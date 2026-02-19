import bpy
import os
from bpy.props import StringProperty
from bpy.types import Operator


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
                if settings.movement_bone:
                    f.write(f' #movement "{settings.movement_bone}"\n')
                f.write(f' #defaultFn "{settings.default_fn}"\n')
                f.write(f' #defaultLocalFn "{settings.default_local_fn}"\n')
                f.write(" $tracks {\n")

                # Sort tracks to put root bones first (bones with no parent)
                root_tracks = []
                child_tracks = []

                for track in settings.tracks:
                    if track.parent_bone == "":
                        root_tracks.append(track)
                    else:
                        child_tracks.append(track)

                sorted_tracks = root_tracks + child_tracks

                for track in sorted_tracks:
                    line = f'  "{track.bone_name}" "{track.parent_bone}" "{track.flags}"'

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
                    parts = line.split('"')
                    if len(parts) >= 6:
                        track = settings.tracks.add()
                        track.bone_name = parts[1]
                        track.parent_bone = parts[3]
                        remaining = ' '.join(parts[5:])
                        if 'TRA' in remaining:
                            track.flags = 'TRA'
                        elif 'TRD' in remaining:
                            track.flags = 'TRD'
                        elif 'TRG' in remaining:
                            track.flags = 'TRG'

                        if '$genFn' in remaining:
                            track.use_gen_fn = True
                            gen_start = remaining.find('$genFn { "') + 10
                            gen_end = remaining.find('"', gen_start)
                            if gen_end > gen_start:
                                track.gen_fn_name = remaining[gen_start:gen_end]

            self.report({'INFO'}, f"Imported {len(settings.tracks)} tracks from {os.path.basename(self.filepath)}")

        except Exception as e:
            self.report({'ERROR'}, f"Failed to import: {str(e)}")
            return {'CANCELLED'}

        return {'FINISHED'}


classes = (
    ARPROFILE_OT_export_profile,
    ARPROFILE_OT_import_profile,
)
