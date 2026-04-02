import bpy


class ARBUILDINGS_PT_panel(bpy.types.Panel):
    """Arma Reforger Building Tools Panel"""
    bl_label = "BK Buildings"
    bl_idname = "ARBUILDINGS_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BK Buildings'

    def draw(self, context):
        layout = self.layout

        # Orientation Tools
        box = layout.box()
        box.label(text="Orientation Tools", icon='ORIENTATION_VIEW')
        box.operator("arbuildings.orient_building", icon='EMPTY_ARROWS')

        # Component Separation
        box = layout.box()
        box.label(text="Component Tools", icon='MOD_BUILD')
        row = box.row(align=True)
        row.operator("arbuildings.separate_component", text="Separate Component", icon='UNLINKED')
        row = box.row(align=True)
        row.operator("arbuildings.create_socket", text="Create Socket", icon='EMPTY_AXIS')

        # Collision Creation
        box = layout.box()
        box.label(text="Collision Tools", icon='MESH_CUBE')
        box.operator("arbuildings.create_firegeo_collision", icon='MESH_GRID')

        # Destruction Workflow
        box = layout.box()
        box.label(text="Destruction Workflow", icon='FORCE_WIND')

        col = box.column(align=True)
        col.operator("arbuildings.fracture_part", text="1. Fracture Part", icon='MOD_EXPLODE')
        col.operator("arbuildings.suggest_removal", text="2. Suggest Removal", icon='SORTSIZE')
        col.operator("arbuildings.finalize_phase", text="3. Finalize Phases", icon='CHECKMARK')

        box.separator()
        box.operator("arbuildings.export_building", text="Export Building", icon='EXPORT')

        # Lighting Tools
        box = layout.box()
        box.label(text="Lighting & Portals", icon='LIGHT_SUN')
        row = box.row(align=True)
        row.operator("arbuildings.create_portal", text="Portal", icon='MESH_PLANE')
        row.operator("arbuildings.create_probe_volume", text="Probe Volume", icon='CUBE')
        box.operator("arbuildings.create_bsp", text="BSP Geometry", icon='MOD_DECIM')

        # Collection Management
        box = layout.box()
        box.label(text="Organization", icon='OUTLINER')
        row = box.row(align=True)
        row.operator("arbuildings.manage_collections", text="Setup Collections", icon='COLLECTION_NEW')

        # Socket Compatibility
        box = layout.box()
        box.label(text="Compatibility Fixes", icon='TOOL_SETTINGS')
        row = box.row(align=True)
        row.operator("arbuildings.convert_existing_sockets", text="Clear Socket Parents", icon='CONSTRAINT_BONE')
