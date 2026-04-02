import bpy
from mathutils import Vector

from ..constants import BUILDING_SOCKET_NAMES


class ARBUILDINGS_OT_orient_building(bpy.types.Operator):
    """Orient building along the Y+ axis (Blender) as required by Arma Reforger"""
    bl_idname = "arbuildings.orient_building"
    bl_label = "Orient Building to Center"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if len(context.selected_objects) == 0:
            self.report({'ERROR'}, "Please select the building meshes")
            return {'CANCELLED'}

        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']

        if not mesh_objects:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}

        # Compute world-space bounding box center
        min_co = Vector((float('inf'), float('inf'), float('inf')))
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

        # Also move related objects (sockets, colliders) that are children
        all_objects = set(mesh_objects)
        for obj in mesh_objects:
            for child in obj.children_recursive:
                all_objects.add(child)

        # Include sockets from Memory Points collection
        if "Memory Points" in bpy.data.collections:
            for obj in bpy.data.collections["Memory Points"].objects:
                all_objects.add(obj)

        # Offset everything so center lands at origin
        offset = -center
        for obj in all_objects:
            # Only move root objects; children follow via parenting
            if obj.parent not in all_objects:
                obj.location += offset

        self.report({'INFO'}, f"Building centered at origin (offset {offset.x:.2f}, {offset.y:.2f}, {offset.z:.2f})")
        return {'FINISHED'}


class ARBUILDINGS_OT_manage_collections(bpy.types.Operator):
    """Create and organize collections for Arma Reforger building workflow"""
    bl_idname = "arbuildings.manage_collections"
    bl_label = "Setup AR Collections"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        collection_names = [
            "Memory Points",
            "Building_Components",
            "Fire_Geometries",
            "LODs"
        ]

        for name in collection_names:
            if name not in bpy.data.collections:
                new_collection = bpy.data.collections.new(name)
                context.scene.collection.children.link(new_collection)
                self.report({'INFO'}, f"Created collection: {name}")

        # Gather existing Fracture_/Phases_ collection names for sorting
        fracture_colls = {c.name for c in bpy.data.collections if c.name.startswith("Fracture_")}
        phase_colls = {c.name for c in bpy.data.collections if c.name.startswith("Phases_")}

        for obj in bpy.data.objects:
            if obj.type == 'EMPTY' and any(socket_name in obj.name.lower() for socket_name in [s.lower() for s in BUILDING_SOCKET_NAMES.values()]):
                self._move_to_collection(obj, "Memory Points")
            elif obj.name.startswith("UTM_") or ("usage" in obj and obj["usage"] == "FireGeo"):
                self._move_to_collection(obj, "Fire_Geometries")
            elif "component_type" in obj:
                self._move_to_collection(obj, "Building_Components")
            elif any(lod_suffix in obj.name.lower() for lod_suffix in ["_lod1", "_lod2", "_lod3"]):
                self._move_to_collection(obj, "LODs")
            elif "destruction_part" in obj:
                # Fracture pieces -- move to their Fracture_ collection
                frac_coll = obj.get("destruction_part", "")
                target = f"Fracture_{frac_coll}"
                if target in fracture_colls:
                    self._move_to_collection(obj, target)
            elif "source_part" in obj:
                # Finalized phase meshes -- move to their Phases_ collection
                src_part = obj.get("source_part", "")
                target = f"Phases_{src_part}"
                if target in phase_colls:
                    self._move_to_collection(obj, target)

        self.report({'INFO'}, "AR collections setup complete")
        return {'FINISHED'}

    def _move_to_collection(self, obj, collection_name):
        """Move an object to a specific collection, removing it from others."""
        if collection_name not in bpy.data.collections:
            return

        target_collection = bpy.data.collections[collection_name]

        for coll in obj.users_collection:
            if coll == target_collection:
                return

        target_collection.objects.link(obj)

        for coll in obj.users_collection:
            if coll != target_collection:
                coll.objects.unlink(obj)


classes = (
    ARBUILDINGS_OT_orient_building,
    ARBUILDINGS_OT_manage_collections,
)
