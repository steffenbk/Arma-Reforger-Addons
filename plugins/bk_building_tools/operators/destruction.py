import bpy
import json
import os
from mathutils import Vector

from ..constants import (
    REMOVAL_PATTERNS,
    BUILDING_PART_TYPE_FOLDERS,
    BUILDING_SOCKET_NAMES,
)


def _ensure_cell_fracture():
    """Check that the Cell Fracture addon is enabled."""
    import addon_utils
    loaded_default, loaded_state = addon_utils.check("bl_ext.blender_org.cell_fracture")
    if not loaded_state:
        try:
            addon_utils.enable("bl_ext.blender_org.cell_fracture")
        except Exception:
            return False
    return True


class ARBUILDINGS_OT_fracture_part(bpy.types.Operator):
    """Fracture a building part into pieces for destruction phases using Cell Fracture"""
    bl_idname = "arbuildings.fracture_part"
    bl_label = "Fracture Part"
    bl_options = {'REGISTER', 'UNDO'}

    piece_count: bpy.props.IntProperty(
        name="Piece Count",
        description="Target number of fracture pieces",
        default=8, min=2, max=100
    )

    noise: bpy.props.FloatProperty(
        name="Noise",
        description="Random variation in fracture pattern",
        default=0.0, min=0.0, max=1.0
    )

    margin: bpy.props.FloatProperty(
        name="Margin",
        description="Gap between fracture pieces",
        default=0.001, min=0.0, max=0.1
    )

    use_smooth: bpy.props.BoolProperty(
        name="Smooth Faces",
        description="Smooth faces on fracture cuts",
        default=False
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and context.mode == 'OBJECT'

    def execute(self, context):
        if not _ensure_cell_fracture():
            self.report({'ERROR'}, "Cell Fracture addon not available. Enable it in Preferences > Add-ons")
            return {'CANCELLED'}

        obj = context.active_object
        part_name = obj.name
        component_type = obj.get("component_type", "other")

        # Create collection for fracture pieces
        coll_name = f"Fracture_{part_name}"
        if coll_name in bpy.data.collections:
            fracture_coll = bpy.data.collections[coll_name]
        else:
            fracture_coll = bpy.data.collections.new(coll_name)
            context.scene.collection.children.link(fracture_coll)

        # Select only the target object
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj

        # Run Cell Fracture
        try:
            bpy.ops.object.add_fracture_cell_objects(
                source={'PARTICLE_OWN'},
                source_limit=self.piece_count,
                source_noise=self.noise,
                cell_scale=(1.0, 1.0, 1.0),
                recursion=0,
                use_smooth_faces=self.use_smooth,
                use_sharp_edges=True,
                use_sharp_edges_apply=True,
                use_data_match=True,
                use_island_split=True,
                margin=self.margin,
                use_recenter=True,
                use_remove_original=False,
                collection_name=coll_name,
            )
        except Exception as e:
            self.report({'ERROR'}, f"Cell Fracture failed: {e}")
            return {'CANCELLED'}

        # Rename and tag pieces
        pieces = [o for o in fracture_coll.objects if o.type == 'MESH']
        for i, piece in enumerate(pieces):
            piece.name = f"{part_name}_piece_{i + 1:03d}"
            piece["destruction_part"] = part_name
            piece["source_component"] = component_type
            piece["piece_index"] = i + 1

        # Store metadata on original object
        obj["fracture_collection"] = coll_name
        obj["fracture_piece_count"] = len(pieces)

        self.report({'INFO'}, f"Fractured '{part_name}' into {len(pieces)} pieces in '{coll_name}'")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "piece_count")
        layout.prop(self, "noise")
        layout.prop(self, "margin")
        layout.prop(self, "use_smooth")


class ARBUILDINGS_OT_suggest_removal(bpy.types.Operator):
    """Suggest piece removal order for destruction phases"""
    bl_idname = "arbuildings.suggest_removal"
    bl_label = "Suggest Removal Pattern"
    bl_options = {'REGISTER', 'UNDO'}

    pattern: bpy.props.EnumProperty(
        name="Pattern",
        description="Removal pattern strategy",
        items=[
            (key, pat["label"], pat["description"])
            for key, pat in REMOVAL_PATTERNS.items()
        ],
        default='outside_in'
    )

    phase_count: bpy.props.IntProperty(
        name="Phase Count",
        description="Number of destruction phases (1-5)",
        default=3, min=1, max=5
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and "fracture_collection" in obj

    def execute(self, context):
        obj = context.active_object
        coll_name = obj["fracture_collection"]

        if coll_name not in bpy.data.collections:
            self.report({'ERROR'}, f"Fracture collection '{coll_name}' not found")
            return {'CANCELLED'}

        fracture_coll = bpy.data.collections[coll_name]
        pieces = sorted(
            [o for o in fracture_coll.objects if o.type == 'MESH'],
            key=lambda o: o.name
        )

        if not pieces:
            self.report({'ERROR'}, "No pieces found in fracture collection")
            return {'CANCELLED'}

        # Score each piece based on pattern
        scores = self._score_pieces(pieces, context)

        # Sort by score and divide into phases
        scored = sorted(zip(pieces, scores), key=lambda x: x[1], reverse=True)
        pieces_per_phase = max(1, len(scored) // self.phase_count)

        for i, (piece, score) in enumerate(scored):
            phase = min(i // pieces_per_phase, self.phase_count - 1)
            piece["destruction_phase"] = phase + 1  # 1-indexed
            piece["removal_score"] = score

        # Color-code phases for visual feedback
        phase_colors = [
            (0.2, 0.8, 0.2, 1.0),   # green = removed first (phase 1)
            (0.8, 0.8, 0.0, 1.0),   # yellow
            (0.8, 0.4, 0.0, 1.0),   # orange
            (0.8, 0.0, 0.0, 1.0),   # red
            (0.4, 0.0, 0.4, 1.0),   # purple = removed last
        ]

        for piece in pieces:
            phase = piece.get("destruction_phase", 1)
            color = phase_colors[min(phase - 1, len(phase_colors) - 1)]
            mat_name = f"Phase_{phase}_Preview"
            if mat_name not in bpy.data.materials:
                mat = bpy.data.materials.new(name=mat_name)
                mat.diffuse_color = color
                mat.use_nodes = False
            else:
                mat = bpy.data.materials[mat_name]

            if piece.data.materials:
                piece.data.materials[0] = mat
            else:
                piece.data.materials.append(mat)

        phase_counts = {}
        for piece in pieces:
            p = piece.get("destruction_phase", 0)
            phase_counts[p] = phase_counts.get(p, 0) + 1

        report = ", ".join(f"Phase {p}: {c} pieces" for p, c in sorted(phase_counts.items()))
        self.report({'INFO'}, f"Suggested removal ({self.pattern}): {report}")
        return {'FINISHED'}

    def _score_pieces(self, pieces, context):
        """Score pieces based on selected removal pattern. Higher score = removed earlier."""
        centers = [p.matrix_world.translation.copy() for p in pieces]

        if not centers:
            return []

        if self.pattern == 'outside_in':
            # Distance from centroid -- farther = removed first
            centroid = sum(centers, Vector((0, 0, 0))) / len(centers)
            return [(c - centroid).length for c in centers]

        elif self.pattern == 'top_down':
            # Higher Z = removed first
            return [c.z for c in centers]

        elif self.pattern == 'bottom_up':
            # Lower Z = removed first (invert)
            max_z = max(c.z for c in centers)
            return [max_z - c.z for c in centers]

        elif self.pattern == 'impact_point':
            # Distance from 3D cursor -- closer = removed first (invert)
            cursor = context.scene.cursor.location
            max_dist = max((c - cursor).length for c in centers) or 1.0
            return [max_dist - (c - cursor).length for c in centers]

        elif self.pattern == 'random_scatter':
            import random
            return [random.random() for _ in centers]

        return [0.0] * len(centers)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "pattern")
        layout.prop(self, "phase_count")
        layout.label(text="Pieces color-coded by phase after apply", icon='INFO')


class ARBUILDINGS_OT_finalize_phase(bpy.types.Operator):
    """Create destruction phase meshes from fracture pieces"""
    bl_idname = "arbuildings.finalize_phase"
    bl_label = "Finalize Destruction Phases"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and "fracture_collection" in obj

    def execute(self, context):
        obj = context.active_object
        part_name = obj.name
        coll_name = obj["fracture_collection"]

        if coll_name not in bpy.data.collections:
            self.report({'ERROR'}, f"Fracture collection '{coll_name}' not found")
            return {'CANCELLED'}

        fracture_coll = bpy.data.collections[coll_name]
        pieces = [o for o in fracture_coll.objects if o.type == 'MESH']

        if not pieces:
            self.report({'ERROR'}, "No pieces in fracture collection")
            return {'CANCELLED'}

        # Determine max phase
        max_phase = max((p.get("destruction_phase", 1) for p in pieces), default=1)

        # Check if pieces have been assigned to phases via suggest_removal
        has_phase_assignments = any(p.get("destruction_phase", 1) > 1 for p in pieces)
        if not has_phase_assignments:
            self.report({'WARNING'},
                "All pieces are in phase 1. Run 'Suggest Removal' first to assign "
                "pieces to multiple phases, or manually set 'destruction_phase' on pieces.")
            return {'CANCELLED'}

        # Create phase collection
        phase_coll_name = f"Phases_{part_name}"
        if phase_coll_name in bpy.data.collections:
            phase_coll = bpy.data.collections[phase_coll_name]
            # Clear existing phase meshes
            for o in list(phase_coll.objects):
                bpy.data.objects.remove(o, do_unlink=True)
        else:
            phase_coll = bpy.data.collections.new(phase_coll_name)
            context.scene.collection.children.link(phase_coll)

        created_phases = []

        for phase_num in range(1, max_phase + 1):
            # For phase N, include all pieces NOT removed in phases 1..N
            # Phase 1 = dst_01 = pieces from phase 2+ remain (phase 1 pieces removed)
            # Phase 2 = dst_02 = pieces from phase 3+ remain (phase 1+2 removed)
            # Phase N = dst_0N = only pieces from phases > N remain
            remaining = [p for p in pieces if p.get("destruction_phase", 1) > phase_num]

            if not remaining:
                # Final phase -- nothing remains (fully destroyed)
                # Create empty placeholder or skip
                continue

            # Duplicate remaining pieces and join into one mesh
            bpy.ops.object.select_all(action='DESELECT')
            copies = []
            for piece in remaining:
                copy = piece.copy()
                copy.data = piece.data.copy()
                phase_coll.objects.link(copy)
                copies.append(copy)

            # Update view layer so new objects are selectable
            context.view_layer.update()
            for copy in copies:
                copy.select_set(True)

            if copies:
                context.view_layer.objects.active = copies[0]
                if len(copies) > 1:
                    bpy.ops.object.join()

                phase_mesh = context.active_object
                dst_suffix = f"_dst_{phase_num:02d}"
                phase_mesh.name = f"{part_name}{dst_suffix}"
                phase_mesh.data.name = f"{part_name}{dst_suffix}"

                # Clear preview materials, restore original
                phase_mesh.data.materials.clear()

                # Store phase metadata
                phase_mesh["destruction_phase_index"] = phase_num
                phase_mesh["source_part"] = part_name

                created_phases.append(phase_mesh.name)

        # Store phase info on the source object
        obj["destruction_phases"] = json.dumps(created_phases)
        obj["phase_count"] = len(created_phases)

        self.report({'INFO'}, f"Created {len(created_phases)} destruction phases for '{part_name}': {', '.join(created_phases)}")
        return {'FINISHED'}


class ARBUILDINGS_OT_export_building(bpy.types.Operator):
    """Export building manifest and optionally FBX files for MCP tool"""
    bl_idname = "arbuildings.export_building"
    bl_label = "Export Building"
    bl_options = {'REGISTER'}

    building_name: bpy.props.StringProperty(
        name="Building Name",
        description="Name for the building (used in file/folder naming)",
        default=""
    )

    export_root: bpy.props.StringProperty(
        name="Export Root",
        description="Root folder for exported files",
        default="",
        subtype='DIR_PATH'
    )

    export_fbx: bpy.props.BoolProperty(
        name="Export FBX Files",
        description="Also export FBX files for each part (requires bk_fbx_exporter)",
        default=True
    )

    @classmethod
    def poll(cls, context):
        return any(
            obj.get("component_type") is not None
            for obj in bpy.data.objects
            if obj.type == 'MESH'
        )

    def execute(self, context):
        if not self.building_name:
            self.report({'ERROR'}, "Building name is required")
            return {'CANCELLED'}

        if not self.export_root:
            self.report({'ERROR'}, "Export root folder is required")
            return {'CANCELLED'}

        export_dir = os.path.join(bpy.path.abspath(self.export_root), self.building_name)
        os.makedirs(export_dir, exist_ok=True)

        # Gather building components
        components = [
            obj for obj in bpy.data.objects
            if obj.type == 'MESH' and obj.get("component_type") is not None
        ]

        # Gather sockets from Memory Points
        sockets = []
        if "Memory Points" in bpy.data.collections:
            sockets = [
                obj for obj in bpy.data.collections["Memory Points"].objects
                if obj.type == 'EMPTY'
            ]

        # Count socket prefixes to determine unique vs repeated
        prefix_counts = {}
        for sock in sockets:
            # Extract prefix: everything before the last _NN
            name = sock.name
            parts = name.rsplit("_", 1)
            if len(parts) == 2 and parts[1].isdigit():
                prefix = parts[0]
            else:
                prefix = name
            prefix_counts[prefix] = prefix_counts.get(prefix, 0) + 1

        # Build manifest
        manifest = {
            "building_name": self.building_name,
            "export_root": export_dir,
            "structure": {
                "fbx": f"{self.building_name}.fbx",
                "sockets": [s.name for s in sockets],
            },
            "parts": [],
        }

        for comp in components:
            comp_type = comp.get("component_type", "other")
            subfolder = BUILDING_PART_TYPE_FOLDERS.get(comp_type, "Parts")

            # Find matching socket
            socket_name = None
            socket_prefix = None
            for sock in sockets:
                attached = sock.get("attached_part", "")
                if attached == comp.name:
                    socket_name = sock.name
                    # Derive prefix
                    parts = sock.name.rsplit("_", 1)
                    if len(parts) == 2 and parts[1].isdigit():
                        socket_prefix = parts[0]
                    else:
                        socket_prefix = sock.name
                    break

            if not socket_prefix:
                socket_prefix = BUILDING_SOCKET_NAMES.get(comp_type, "SOCKET_building_part")

            is_unique = prefix_counts.get(socket_prefix, 1) == 1

            # Gather destruction phases
            phases = []
            phases_json = comp.get("destruction_phases")
            if phases_json:
                try:
                    phase_names = json.loads(phases_json)
                    for idx, pname in enumerate(phase_names, 1):
                        phase_fbx = f"{subfolder}/{pname}.fbx"
                        phases.append({"index": idx, "fbx": phase_fbx})
                except (json.JSONDecodeError, TypeError):
                    pass

            part_entry = {
                "name": comp.name,
                "type": comp_type,
                "socket_prefix": socket_prefix,
                "socket_name": socket_name or "",
                "unique": is_unique,
                "fbx": f"{subfolder}/{comp.name}.fbx",
                "phases": phases,
            }
            manifest["parts"].append(part_entry)

            # Create subfolder
            os.makedirs(os.path.join(export_dir, subfolder), exist_ok=True)

        # Write manifest
        manifest_path = os.path.join(export_dir, "building_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        # Optionally export FBX files
        exported_count = 0
        if self.export_fbx:
            exported_count = self._export_fbx_files(context, manifest, export_dir)

        msg = f"Manifest saved: {manifest_path} ({len(manifest['parts'])} parts)"
        if self.export_fbx:
            msg += f", {exported_count} FBX files exported"
        self.report({'INFO'}, msg)
        return {'FINISHED'}

    def _export_fbx_files(self, context, manifest, export_dir):
        """Export FBX files for structure and each part. Uses standard FBX export."""
        count = 0

        # Export the building structure mesh (shell with sockets)
        # Only consider meshes in the scene root collection (not in sub-collections)
        # that aren't components, colliders, phases, fracture pieces, or lighting volumes
        excluded_prefixes = ("UTM_", "UCX_", "UBX_", "BSP_", "PRT_", "BOXVOL_", "SPHVOL_")
        excluded_collections = set()
        for coll in bpy.data.collections:
            if coll.name.startswith("Fracture_") or coll.name.startswith("Phases_"):
                excluded_collections.add(coll.name)
            if coll.name in ("Fire_Geometries", "LODs", "Building_Components"):
                excluded_collections.add(coll.name)

        def _in_excluded_collection(obj):
            return any(c.name in excluded_collections for c in obj.users_collection)

        structure_candidates = [
            obj for obj in context.scene.collection.objects
            if obj.type == 'MESH'
            and obj.get("component_type") is None
            and "destruction_phase_index" not in obj
            and "destruction_part" not in obj
            and not any(obj.name.startswith(p) for p in excluded_prefixes)
            and not _in_excluded_collection(obj)
        ]
        if structure_candidates:
            structure_fbx = os.path.join(export_dir, manifest["structure"]["fbx"])
            # Export all structure candidates together (walls shell, etc.)
            self._export_multi_fbx(context, structure_candidates, structure_fbx)
            count += 1

        for part in manifest["parts"]:
            part_obj = bpy.data.objects.get(part["name"])
            if not part_obj:
                continue

            # Export part mesh
            fbx_path = os.path.join(export_dir, part["fbx"])
            self._export_single_fbx(context, part_obj, fbx_path)
            count += 1

            # Export destruction phases
            for phase in part.get("phases", []):
                phase_fbx = os.path.join(export_dir, phase["fbx"])
                # Find phase mesh by deriving name from part + dst suffix
                phase_name = os.path.splitext(os.path.basename(phase_fbx))[0]
                phase_obj = bpy.data.objects.get(phase_name)
                if phase_obj:
                    self._export_single_fbx(context, phase_obj, phase_fbx)
                    count += 1

        return count

    def _export_single_fbx(self, context, obj, filepath):
        """Export a single object to FBX with Enfusion-compatible settings."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # Store current selection
        prev_selected = context.selected_objects[:]
        prev_active = context.active_object

        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj

        bpy.ops.export_scene.fbx(
            filepath=filepath,
            use_selection=True,
            apply_scale_options='FBX_SCALE_ALL',
            axis_forward='-Z',
            axis_up='Y',
            use_mesh_modifiers=True,
            mesh_smooth_type='OFF',
            add_leaf_bones=False,
        )

        # Restore selection
        bpy.ops.object.select_all(action='DESELECT')
        for o in prev_selected:
            if o:
                o.select_set(True)
        if prev_active:
            context.view_layer.objects.active = prev_active

    def _export_multi_fbx(self, context, objects, filepath):
        """Export multiple objects together to a single FBX."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        prev_selected = context.selected_objects[:]
        prev_active = context.active_object

        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:
            obj.select_set(True)
        context.view_layer.objects.active = objects[0]

        bpy.ops.export_scene.fbx(
            filepath=filepath,
            use_selection=True,
            apply_scale_options='FBX_SCALE_ALL',
            axis_forward='-Z',
            axis_up='Y',
            use_mesh_modifiers=True,
            mesh_smooth_type='OFF',
            add_leaf_bones=False,
        )

        bpy.ops.object.select_all(action='DESELECT')
        for o in prev_selected:
            if o:
                o.select_set(True)
        if prev_active:
            context.view_layer.objects.active = prev_active

    def invoke(self, context, event):
        # Auto-fill building name from .blend filename
        if not self.building_name:
            blend_name = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
            if blend_name:
                self.building_name = blend_name

        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "building_name")
        layout.prop(self, "export_root")
        layout.separator()
        layout.prop(self, "export_fbx")
        if self.export_fbx:
            layout.label(text="Exports structure + parts + phases as FBX", icon='INFO')


classes = (
    ARBUILDINGS_OT_fracture_part,
    ARBUILDINGS_OT_suggest_removal,
    ARBUILDINGS_OT_finalize_phase,
    ARBUILDINGS_OT_export_building,
)
