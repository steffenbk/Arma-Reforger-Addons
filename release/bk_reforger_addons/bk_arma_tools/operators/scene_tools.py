import bpy
import re
from mathutils import Vector


# Prefixes/suffixes used for auto-sorting
_PREFIX_COLLECTION_MAP = {
    'UCL_':    'Colliders',
    'UCX_':    'Colliders',
    'UBX_':    'Colliders',
    'UTM_':    'Colliders',
    'USP_':    'Colliders',
    'UCS_':    'Colliders',
    'COM_':    'Colliders',
    'LC_':     'Colliders',
    'PRT_':    'Portals',
    'BOXVOL_': 'Probe Volumes',
    'SPHVOL_': 'Probe Volumes',
    'OCC_':    'Occluders',
    'SOCKET_': 'Memory Points',
}

_COLLIDER_PREFIXES = ('UBX_', 'UCX_', 'UTM_', 'USP_', 'UCS_', 'UCL_')


def _get_or_create_collection(name, scene):
    if name in bpy.data.collections:
        col = bpy.data.collections[name]
    else:
        col = bpy.data.collections.new(name)
        scene.collection.children.link(col)
    return col


def _move_to_collection(obj, target_col):
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    target_col.objects.link(obj)


class ARVEHICLES_OT_sort_into_collections(bpy.types.Operator):
    bl_idname = "arvehicles.sort_into_collections"
    bl_label = "Sort Objects into Collections"
    bl_description = "Auto-sort all scene objects into collections by Enfusion prefix/suffix conventions"
    bl_options = {'REGISTER', 'UNDO'}

    hide_non_lod0: bpy.props.BoolProperty(
        name="Hide Non-LOD0",
        default=True,
        description="Hide all collections except LOD0"
    )
    fold_collections: bpy.props.BoolProperty(
        name="Fold Collections",
        default=False,
        description="Collapse all collections in the outliner after sorting"
    )

    @classmethod
    def poll(cls, context):
        return context.scene is not None

    def execute(self, context):
        scene = context.scene
        sorted_count = 0

        all_objects = list(scene.objects)

        for obj in all_objects:
            name = obj.name
            name_upper = name.upper()
            target_col_name = None

            # Check prefix map first (case-insensitive)
            for prefix, col_name in _PREFIX_COLLECTION_MAP.items():
                if name_upper.startswith(prefix):
                    target_col_name = col_name
                    break

            # Check LOD suffixes if no prefix matched
            if target_col_name is None:
                lod_match = re.search(r'_LOD(\d)$', name_upper)
                if lod_match:
                    lod_num = int(lod_match.group(1))
                    if 0 <= lod_num <= 5:
                        target_col_name = f'LOD{lod_num}'

            if target_col_name is not None:
                target_col = _get_or_create_collection(target_col_name, scene)
                if obj.name not in target_col.objects:
                    _move_to_collection(obj, target_col)
                    sorted_count += 1

        if self.hide_non_lod0:
            lod0_col = bpy.data.collections.get('LOD0')
            for col in bpy.data.collections:
                if col.name != 'LOD0':
                    # Hide in viewport via layer_collection
                    layer_col = self._find_layer_collection(context.view_layer.layer_collection, col.name)
                    if layer_col:
                        layer_col.hide_viewport = True

        if self.fold_collections:
            def _collapse_recursive(layer_col):
                layer_col.is_expanded = False
                for child in layer_col.children:
                    _collapse_recursive(child)
            for child in context.view_layer.layer_collection.children:
                _collapse_recursive(child)

        self.report({'INFO'}, f"Sorted {sorted_count} objects into collections")
        return {'FINISHED'}

    def _find_layer_collection(self, layer_col, name):
        if layer_col.name == name:
            return layer_col
        for child in layer_col.children:
            result = self._find_layer_collection(child, name)
            if result:
                return result
        return None

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "hide_non_lod0")
        layout.prop(self, "fold_collections")


class ARVEHICLES_OT_batch_collider_setup(bpy.types.Operator):
    bl_idname = "arvehicles.batch_collider_setup"
    bl_label = "Batch Collider Setup"
    bl_description = "Batch-assign Layer Preset and Game Material to selected collider objects"
    bl_options = {'REGISTER', 'UNDO'}

    layer_preset: bpy.props.EnumProperty(
        name="Layer Preset",
        items=[
            ('FireGeo',           "FireGeo",           "Fire geometry"),
            ('FireView',          "FireView",          "Fire view layer"),
            ('PropFireView',      "PropFireView",      "Prop fire view"),
            ('BuildingFireView',  "BuildingFireView",  "Building fire view"),
            ('Vehicle',           "Vehicle",           "Standard vehicle collision"),
            ('VehicleFire',       "VehicleFire",       "Vehicle fire collision"),
            ('VehicleFireView',   "VehicleFireView",   "Vehicle fire view"),
            ('WeaponFire',        "WeaponFire",        "Weapon fire collision (FireGeometry + Weapon)"),
            ('ItemFireView',      "ItemFireView",      "Item fire view"),
            ('Door',              "Door",              "Door collision"),
            ('DoorFireView',      "DoorFireView",      "Door fire view"),
            ('Tree',              "Tree",              "Tree collision"),
            ('Wheel',             "Wheel",             "Wheel collision"),
            ('Glass',             "Glass",             "Glass collision"),
            ('Character',         "Character",         "Character collision"),
            ('Terrain',           "Terrain",           "Terrain collision"),
        ],
        default='FireGeo'
    )
    game_material: bpy.props.StringProperty(
        name="Game Material",
        description="Material name with GUID suffix (e.g. Weapon_metal_3B2D2687F56BB4EF)",
        default=""
    )
    apply_layer_preset: bpy.props.BoolProperty(
        name="Apply Layer Preset",
        default=True
    )
    apply_game_material: bpy.props.BoolProperty(
        name="Apply Game Material",
        default=False
    )

    @classmethod
    def poll(cls, context):
        return bool(context.selected_objects)

    def execute(self, context):
        colliders = [
            obj for obj in context.selected_objects
            if any(obj.name.startswith(p) for p in _COLLIDER_PREFIXES)
        ]

        if not colliders:
            self.report({'WARNING'}, "No collider objects in selection (expected UBX_, UCX_, UTM_, USP_, UCS_, UCL_ prefix)")
            return {'CANCELLED'}

        modified = 0
        for obj in colliders:
            if self.apply_layer_preset:
                obj["usage"] = self.layer_preset

            if self.apply_game_material and self.game_material:
                if obj.type == 'MESH':
                    if obj.data.materials:
                        obj.data.materials[0].name = self.game_material
                    else:
                        mat = bpy.data.materials.new(name=self.game_material)
                        obj.data.materials.append(mat)
            modified += 1

        self.report({'INFO'}, f"Modified {modified} collider object(s)")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "apply_layer_preset")
        row = layout.row()
        row.enabled = self.apply_layer_preset
        row.prop(self, "layer_preset")
        layout.separator()
        layout.prop(self, "apply_game_material")
        row = layout.row()
        row.enabled = self.apply_game_material
        row.prop(self, "game_material")


class ARVEHICLES_OT_game_material_rename(bpy.types.Operator):
    bl_idname = "arvehicles.game_material_rename"
    bl_label = "Rename Game Material"
    bl_description = "Rename the active material to Enfusion format: MaterialName_MaterialGUID"
    bl_options = {'REGISTER', 'UNDO'}

    material_name: bpy.props.StringProperty(
        name="Material Name",
        default=""
    )
    material_guid: bpy.props.StringProperty(
        name="Material GUID",
        description="16-char hex GUID from Workbench",
        default=""
    )

    @classmethod
    def poll(cls, context):
        return (
            context.active_object is not None
            and context.active_object.type == 'MESH'
            and context.active_object.active_material is not None
        )

    def execute(self, context):
        obj = context.active_object
        mat = obj.active_material

        if not mat:
            self.report({'ERROR'}, "No active material on the active object")
            return {'CANCELLED'}

        guid = self.material_guid.strip()

        if guid:
            if not re.fullmatch(r'[0-9A-Fa-f]{16}', guid):
                self.report({'ERROR'}, "GUID must be exactly 16 hexadecimal characters")
                return {'CANCELLED'}

        base_name = self.material_name.strip()

        if not base_name:
            # Strip existing GUID suffix if present (trailing _<16hex>)
            existing = mat.name
            match = re.match(r'^(.+?)_([0-9A-Fa-f]{16})$', existing)
            if match:
                base_name = match.group(1)
            else:
                base_name = existing

        if not guid:
            self.report({'ERROR'}, "A GUID is required")
            return {'CANCELLED'}

        new_name = f"{base_name}_{guid}"
        mat.name = new_name

        self.report({'INFO'}, f"Renamed material to: {new_name}")
        return {'FINISHED'}

    def invoke(self, context, event):
        # Pre-fill material_name from existing material
        obj = context.active_object
        if obj and obj.active_material:
            existing = obj.active_material.name
            match = re.match(r'^(.+?)_([0-9A-Fa-f]{16})$', existing)
            if match:
                self.material_name = match.group(1)
                self.material_guid = match.group(2)
            else:
                self.material_name = existing
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "material_name")
        layout.prop(self, "material_guid")
        if self.material_name and self.material_guid:
            layout.label(text=f"Result: {self.material_name}_{self.material_guid}", icon='INFO')


class ARVEHICLES_OT_auto_center_of_mass(bpy.types.Operator):
    bl_idname = "arvehicles.auto_center_of_mass"
    bl_label = "Auto Center of Mass"
    bl_description = "Create or move COM_ empty to volume center of selected mesh objects"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return any(obj.type == 'MESH' for obj in context.selected_objects)

    def execute(self, context):
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not mesh_objects:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}

        # Calculate world-space bounding box center across all selected meshes
        min_co = Vector((float('inf'),  float('inf'),  float('inf')))
        max_co = Vector((float('-inf'), float('-inf'), float('-inf')))

        for obj in mesh_objects:
            for corner in obj.bound_box:
                world_co = obj.matrix_world @ Vector(corner)
                min_co.x = min(min_co.x, world_co.x)
                min_co.y = min(min_co.y, world_co.y)
                min_co.z = min(min_co.z, world_co.z)
                max_co.x = max(max_co.x, world_co.x)
                max_co.y = max(max_co.y, world_co.y)
                max_co.z = max(max_co.z, world_co.z)

        center = (min_co + max_co) / 2.0

        # Find existing COM_ empty or create one
        com_obj = None
        for obj in context.scene.objects:
            if obj.name.startswith('COM_') and obj.type == 'EMPTY':
                com_obj = obj
                break

        if com_obj:
            com_obj.location = center
            self.report({'INFO'}, f"Moved {com_obj.name} to ({center.x:.3f}, {center.y:.3f}, {center.z:.3f})")
        else:
            com_obj = bpy.data.objects.new('COM_center', None)
            com_obj.empty_display_type = 'PLAIN_AXES'
            com_obj.empty_display_size = 0.1
            com_obj.location = center
            context.scene.collection.objects.link(com_obj)
            self.report({'INFO'}, f"Created COM_center at ({center.x:.3f}, {center.y:.3f}, {center.z:.3f})")

        return {'FINISHED'}


class ARVEHICLES_OT_create_occluder(bpy.types.Operator):
    bl_idname = "arvehicles.create_occluder"
    bl_label = "Create Occluder"
    bl_description = "Create an OCC_ occluder plane or box from selected faces or objects"
    bl_options = {'REGISTER', 'UNDO'}

    occluder_type: bpy.props.EnumProperty(
        name="Occluder Type",
        items=[
            ('PLANE', "Plane", "Single occluder plane"),
            ('BOX',   "Box",   "Box occluder"),
        ],
        default='PLANE'
    )

    @classmethod
    def poll(cls, context):
        return bool(context.selected_objects) or context.mode == 'EDIT_MESH'

    def _next_occ_name(self, scene):
        existing = [obj.name for obj in scene.objects if obj.name.startswith('OCC_')]
        index = 1
        while True:
            candidate = f"OCC_{index:02d}"
            if candidate not in existing:
                return candidate
            index += 1

    def execute(self, context):
        scene = context.scene
        name = self._next_occ_name(scene)

        if context.mode == 'EDIT_MESH':
            occ_obj = self._create_from_edit_mode(context, name)
        else:
            occ_obj = self._create_from_object_mode(context, name)

        if occ_obj is None:
            return {'CANCELLED'}

        occ_obj.display_type = 'WIRE'

        # Deselect all and select new occluder
        bpy.ops.object.select_all(action='DESELECT')
        occ_obj.select_set(True)
        context.view_layer.objects.active = occ_obj

        self.report({'INFO'}, f"Created occluder: {occ_obj.name}")
        return {'FINISHED'}

    def _create_from_edit_mode(self, context, name):
        import bmesh as bm_module

        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Active object must be a mesh in Edit Mode")
            return None

        bm = bm_module.from_edit_mesh(obj.data)
        selected_faces = [f for f in bm.faces if f.select]

        if not selected_faces:
            self.report({'ERROR'}, "No faces selected in Edit Mode")
            return None

        # Average position and normal
        avg_pos = sum((obj.matrix_world @ f.calc_center_median() for f in selected_faces), Vector()) / len(selected_faces)
        avg_normal = sum((obj.matrix_world.to_3x3() @ f.normal for f in selected_faces), Vector()).normalized()

        # Approximate size from selection bounds
        all_verts = {v for f in selected_faces for v in f.verts}
        positions = [obj.matrix_world @ v.co for v in all_verts]
        min_v = Vector((min(p.x for p in positions), min(p.y for p in positions), min(p.z for p in positions)))
        max_v = Vector((max(p.x for p in positions), max(p.y for p in positions), max(p.z for p in positions)))
        size_x = max(max_v.x - min_v.x, 0.01)
        size_y = max(max_v.y - min_v.y, 0.01)

        # Switch to Object Mode to create the new mesh
        bpy.ops.object.mode_set(mode='OBJECT')

        if self.occluder_type == 'BOX':
            size_z = max(max_v.z - min_v.z, 0.01)
            bpy.ops.mesh.primitive_cube_add(location=avg_pos)
            occ_obj = context.active_object
            occ_obj.scale = (size_x / 2.0, size_y / 2.0, size_z / 2.0)
        else:
            bpy.ops.mesh.primitive_plane_add(size=1.0, location=avg_pos)
            occ_obj = context.active_object
            occ_obj.scale = (size_x, size_y, 1.0)

        bpy.ops.object.transform_apply(scale=True)
        occ_obj.name = name
        occ_obj.data.name = name

        return occ_obj

    def _create_from_object_mode(self, context, name):
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not mesh_objects:
            self.report({'ERROR'}, "No mesh objects selected")
            return None

        min_co = Vector((float('inf'),  float('inf'),  float('inf')))
        max_co = Vector((float('-inf'), float('-inf'), float('-inf')))

        for obj in mesh_objects:
            for corner in obj.bound_box:
                world_co = obj.matrix_world @ Vector(corner)
                min_co.x = min(min_co.x, world_co.x)
                min_co.y = min(min_co.y, world_co.y)
                min_co.z = min(min_co.z, world_co.z)
                max_co.x = max(max_co.x, world_co.x)
                max_co.y = max(max_co.y, world_co.y)
                max_co.z = max(max_co.z, world_co.z)

        center = (min_co + max_co) / 2.0
        size_x = max(max_co.x - min_co.x, 0.01)
        size_y = max(max_co.y - min_co.y, 0.01)
        size_z = max(max_co.z - min_co.z, 0.01)

        if self.occluder_type == 'BOX':
            bpy.ops.mesh.primitive_cube_add(location=center)
            occ_obj = context.active_object
            occ_obj.scale = (size_x / 2.0, size_y / 2.0, size_z / 2.0)
        else:
            bpy.ops.mesh.primitive_plane_add(size=1.0, location=center)
            occ_obj = context.active_object
            occ_obj.scale = (size_x, size_y, 1.0)

        bpy.ops.object.transform_apply(scale=True)
        occ_obj.name = name
        occ_obj.data.name = name

        return occ_obj

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.prop(self, "occluder_type")


class ARVEHICLES_OT_create_land_contacts(bpy.types.Operator):
    bl_idname = "arvehicles.create_land_contacts"
    bl_label = "Create Land Contacts"
    bl_description = "Auto-place LC_ empties at bottom corners of selected objects' bounding box"
    bl_options = {'REGISTER', 'UNDO'}

    count: bpy.props.IntProperty(
        name="Contact Points",
        default=4,
        min=2,
        max=8
    )

    @classmethod
    def poll(cls, context):
        return any(obj.type == 'MESH' for obj in context.selected_objects)

    def execute(self, context):
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not mesh_objects:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}

        min_co = Vector((float('inf'),  float('inf'),  float('inf')))
        max_co = Vector((float('-inf'), float('-inf'), float('-inf')))

        for obj in mesh_objects:
            for corner in obj.bound_box:
                world_co = obj.matrix_world @ Vector(corner)
                min_co.x = min(min_co.x, world_co.x)
                min_co.y = min(min_co.y, world_co.y)
                min_co.z = min(min_co.z, world_co.z)
                max_co.x = max(max_co.x, world_co.x)
                max_co.y = max(max_co.y, world_co.y)
                max_co.z = max(max_co.z, world_co.z)

        bx, by, bz = min_co.x, min_co.y, min_co.z
        tx, ty, tz = max_co.x, max_co.y, max_co.z
        cx = (bx + tx) / 2.0
        cy = (by + ty) / 2.0

        if self.count == 2:
            positions = [
                Vector((cx, ty, bz)),   # front-center bottom
                Vector((cx, by, bz)),   # back-center bottom
            ]
        elif self.count == 4:
            positions = [
                Vector((tx, ty, bz)),   # front-right bottom
                Vector((bx, ty, bz)),   # front-left bottom
                Vector((tx, by, bz)),   # back-right bottom
                Vector((bx, by, bz)),   # back-left bottom
            ]
        else:
            # 8 corners of the full bounding box
            positions = [
                Vector((tx, ty, bz)),
                Vector((bx, ty, bz)),
                Vector((tx, by, bz)),
                Vector((bx, by, bz)),
                Vector((tx, ty, tz)),
                Vector((bx, ty, tz)),
                Vector((tx, by, tz)),
                Vector((bx, by, tz)),
            ]
            positions = positions[:self.count]

        created = []
        for i, pos in enumerate(positions, start=1):
            empty = bpy.data.objects.new(f"LC_{i:02d}", None)
            empty.empty_display_type = 'PLAIN_AXES'
            empty.empty_display_size = 0.05
            empty.location = pos
            context.scene.collection.objects.link(empty)
            created.append(empty)

        bpy.ops.object.select_all(action='DESELECT')
        for emp in created:
            emp.select_set(True)
        if created:
            context.view_layer.objects.active = created[0]

        self.report({'INFO'}, f"Created {len(created)} LC_ land contact point(s)")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "count")
        layout.label(text="2 = front/back center, 4 = bottom corners, 8 = all corners", icon='INFO')


classes = (
    ARVEHICLES_OT_sort_into_collections,
    ARVEHICLES_OT_batch_collider_setup,
    ARVEHICLES_OT_game_material_rename,
    ARVEHICLES_OT_auto_center_of_mass,
    ARVEHICLES_OT_create_occluder,
    ARVEHICLES_OT_create_land_contacts,
)
