import bpy


class ARVEHICLES_PT_panel(bpy.types.Panel):
    bl_label = "BK Arma Tools"
    bl_idname = "ARVEHICLES_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BK Arma Tools'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        mode = getattr(context.scene, "arvehicles_mode", "VEHICLE")

        # ============================================================
        # MODE SWITCH
        # ============================================================
        box = layout.box()
        box.label(text="Asset Mode", icon='OBJECT_DATA')
        row = box.row(align=True)
        row.prop_enum(scene, "arvehicles_mode", 'VEHICLE')
        row.prop_enum(scene, "arvehicles_mode", 'WEAPON')
        row.prop_enum(scene, "arvehicles_mode", 'CUSTOM')
        if mode == 'CUSTOM':
            box.prop(scene, "arvehicles_custom_prefix", text="Prefix")

        # ============================================================
        # MESH TOOLS
        # ============================================================
        box = layout.box()
        box.label(text="Mesh Tools", icon='EDITMODE_HLT')
        row = box.row(align=True)
        row.operator("arvehicles.cleanup_mesh", text="Cleanup Mesh", icon='BRUSH_DATA')
        row.operator("arvehicles.create_lods", text="Create LODs", icon='MOD_DECIM')

        # ============================================================
        # PREPARATION
        # ============================================================
        box = layout.box()
        box.label(text="Preparation", icon='ORIENTATION_VIEW')
        box.operator("arvehicles.center_vehicle", text="Center Vehicle", icon='PIVOT_BOUNDBOX')

        # ============================================================
        # COLLISION
        # ============================================================
        box = layout.box()
        box.label(text="Collision", icon='MESH_CUBE')
        row = box.row(align=True)
        row.operator("arvehicles.create_ucx_collision", text="UCX Physics", icon='MESH_CUBE')
        row.operator("arvehicles.create_firegeo_collision", text="FireGeo", icon='MESH_ICOSPHERE')
        if mode == 'VEHICLE':
            row = box.row(align=True)
            row.operator("arvehicles.create_wheel_collisions", text="Wheel Collision", icon='MESH_CYLINDER')
            row.operator("arvehicles.create_center_of_mass", text="Center of Mass", icon='EMPTY_SINGLE_ARROW')

        # ============================================================
        # COMPONENT SEPARATION
        # ============================================================
        box = layout.box()
        box.label(text="Component Separation", icon='MOD_BUILD')
        box.operator("arvehicles.separate_components", text="Separate Component", icon='UNLINKED')

        col = box.column(align=True)
        col.separator()
        col.label(text="Add to Existing Objects:")
        col.operator("arvehicles.add_to_object", text="Add Bone/Socket to Object", icon='EMPTY_ARROWS')

        # ============================================================
        # ATTACHMENT POINTS
        # ============================================================
        box = layout.box()
        box.label(text="Attachment Points", icon='EMPTY_DATA')
        col = box.column(align=True)
        col.label(text="Create Sockets:")
        op = col.operator("arvehicles.create_socket", text="Add Socket")
        op.socket_type = 'custom'

        # ============================================================
        # RIGGING
        # ============================================================
        box = layout.box()
        box.label(text="Rigging", icon='ARMATURE_DATA')

        label = "Create Weapon Armature" if mode == 'WEAPON' else "Create Vehicle Armature"
        col = box.column(align=True)
        col.operator("arvehicles.create_armature", text=label, icon='ARMATURE_DATA')

        col.separator()
        col.label(text="Add Bones:")
        col.operator("arvehicles.create_bone", text="Add Bone").bone_type = 'custom'
        col.operator("arvehicles.add_bone_to_verts", text="Add Bone to Selected Verts", icon='VERTEXSEL')

        col.separator()
        col.label(text="Bone Hierarchy:")
        col.operator("arvehicles.parent_bones", text="Parent Bones", icon='CONSTRAINT_BONE')
        col.operator("arvehicles.align_bones_direction", text="Align Bone Directions", icon='ORIENTATION_GLOBAL')
        col.operator("arvehicles.create_vertex_group", text="Assign to Bone", icon='WPAINT_HLT')

        col.separator()
        col.label(text="Parenting:")
        row = col.row(align=True)
        row.operator("arvehicles.parent_to_armature", text="Parent Meshes")
        row.operator("arvehicles.parent_empties", text="Parent Empties")

        # ============================================================
        # TWO-PHASE PRESET MANAGER
        # ============================================================
        box = layout.box()
        box.label(text="Two-Phase Preset Manager", icon='PRESET')

        col = box.column(align=True)
        col.operator("arvehicles.manage_presets", text="Create/Edit Preset", icon='PLUS')

        row = col.row(align=True)
        row.operator("arvehicles.preset_separation", text="Separate Action", icon='LOOP_FORWARDS')
        row.operator("arvehicles.skip_preset_item", text="Skip", icon='FORWARD')

        row = col.row(align=True)
        row.operator("arvehicles.reset_preset", text="Reset", icon='FILE_REFRESH')

        # Preset status
        if "arvehicles_active_preset" in scene:
            preset_name   = scene["arvehicles_active_preset"]
            preset_prefix = f"arvehicles_preset_{preset_name}_"
            count_key     = f"{preset_prefix}count"

            if count_key in scene:
                preset_count  = scene[count_key]
                current_phase = scene.get(f"{preset_prefix}phase", "bones")

                col.separator()
                col.label(text=f"Active: {preset_name}")
                col.label(text=f"Phase: {current_phase.title()}")

                if current_phase == "bones":
                    bone_index = scene.get(f"{preset_prefix}bone_index", 0)
                    if bone_index < preset_count:
                        bone_key = f"{preset_prefix}bone_{bone_index}"
                        if bone_key in scene:
                            col.label(text=f"Next: {scene[bone_key]}")
                            col.label(text=f"Mesh: Mesh_{scene[bone_key]}")
                            col.label(text=f"Progress: {bone_index + 1}/{preset_count}")
                        else:
                            col.label(text="Error: Bone data missing")
                    else:
                        col.label(text="Ready for socket phase!")
                else:
                    socket_index = scene.get(f"{preset_prefix}socket_index", 0)
                    if socket_index < preset_count:
                        socket_key = f"{preset_prefix}socket_{socket_index}"
                        if socket_key in scene:
                            col.label(text=f"Next: {scene[socket_key]}")
                            col.label(text=f"Progress: {socket_index + 1}/{preset_count}")
                        else:
                            col.label(text="Error: Socket data missing")
                    else:
                        col.label(text="All complete!")
        else:
            col.separator()
            col.label(text="No active preset")