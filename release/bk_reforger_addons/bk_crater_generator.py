bl_info = {
    "name": "BK Crater Generator",
    "author": "steffenbk",
    "version": (1, 1, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Add > Mesh > Game Crater",
    "description": "Generate clean game-ready crater meshes with dual materials, optimized UV mapping, FireGeo collision and LODs",
    "category": "Add Mesh",
    "doc_url": "",
    "tracker_url": "",
}

import bpy
import bmesh
import mathutils
import math
import random
from mathutils import Vector, noise
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import (
    FloatProperty, IntProperty, BoolProperty, 
    EnumProperty, PointerProperty
)

class CraterProperties(PropertyGroup):
    """Properties for crater generation based on real crater analysis"""
    
    outer_radius: FloatProperty(
        name="Outer Radius",
        description="Outer radius of crater (base/ground level)",
        default=2.6,
        min=0.5,
        max=100.0,
        unit='LENGTH',
        step=10
    )
    
    inner_radius: FloatProperty(
        name="Inner Radius", 
        description="Inner radius of crater (rim/lip)",
        default=1.3,
        min=0.1,
        max=50.0,
        unit='LENGTH',
        step=10
    )
    
    depth: FloatProperty(
        name="Crater Depth", 
        description="Maximum crater depth",
        default=0.5,
        min=0.1,
        max=100.0,
        unit='LENGTH',
        step=10
    )
    
    rim_height: FloatProperty(
        name="Rim Height",
        description="Height of crater rim above ground level",
        default=0.58,
        min=0.0,
        max=100.0,
        unit='LENGTH',
        step=10
    )
    
    resolution: IntProperty(
        name="Resolution",
        description="Crater mesh resolution (higher = more detail)",
        default=24,
        min=8,
        max=500,
        step=4
    )
    
    noise_strength: FloatProperty(
        name="Inside Surface Noise",
        description="Surface detail noise strength inside crater rim",
        default=0.05,
        min=0.0,
        max=30.0,
        step=1
    )
    
    outside_noise_strength: FloatProperty(
        name="Outside Surface Noise", 
        description="Surface detail noise strength outside crater rim",
        default=0.02,
        min=0.0,
        max=30.0,
        step=1
    )
    
    create_materials: BoolProperty(
        name="Create Materials",
        description="Generate dual-zone crater materials",
        default=True
    )
    
    auto_uv: BoolProperty(
        name="Auto UV Mapping",
        description="Generate optimized UV mapping",
        default=True
    )
    
    optimize_for_games: BoolProperty(
        name="Game Optimization",
        description="Apply game-ready mesh optimizations",
        default=True
    )
    
    close_bottom: BoolProperty(
        name="Close Bottom",
        description="Create a closed bottom for the crater (solid geometry)",
        default=True
    )
    
    center_origin: BoolProperty(
        name="Center Origin at Bottom",
        description="Place the object origin at the bottom/underside of the crater instead of at ground level",
        default=False
    )
    
    center_origin_z_offset: FloatProperty(
        name="Center Origin Z Offset",
        description="Additional Z-axis offset when centering origin at bottom (positive = higher, negative = lower)",
        default=0.0,
        min=-10.0,
        max=10.0,
        unit='LENGTH',
        step=10
    )
    
    bottom_thickness: FloatProperty(
        name="Bottom Thickness",
        description="Thickness of the crater bottom (how deep below ground level)",
        default=1.0,
        min=0.1,
        max=10.0,
        unit='LENGTH',
        step=10
    )
    
    outer_wall_angle: FloatProperty(
        name="Outer Wall Angle",
        description="Angle of the outer bottom walls (0 = vertical, positive = slanted outward)",
        default=0.0,
        min=-89.0,
        max=89.0,
        unit='ROTATION',
        step=100
    )
    
    inner_wall_angle: FloatProperty(
        name="Inner Wall Angle",
        description="Angle of the inner crater walls (0 = vertical, positive = slanted outward)",
        default=0.0,
        min=-89.0,
        max=89.0,
        unit='ROTATION',
        step=100
    )
    
    outer_edge_rounding: FloatProperty(
        name="Outer Edge Rounding",
        description="Round the outer edges of the crater for smoother ground transition",
        default=0.0,
        min=0.0,
        max=1.0,
        step=1
    )
    
    rim_edge_rounding: FloatProperty(
        name="Rim Edge Rounding",
        description="Make the crater rim edge more rounded and smooth (simulates weathered/eroded crater)",
        default=0.0,
        min=0.0,
        max=1.0,
        step=1
    )
    
    crater_outline_irregularity: FloatProperty(
        name="Crater Outline Irregularity",
        description="Make the overall crater outline more jagged and less circular (simulates irregular explosion)",
        default=0.0,
        min=0.0,
        max=50.0,
        step=1
    )
    
    inner_asymmetry: FloatProperty(
        name="Inner Circle Asymmetry",
        description="Make the inner crater circle less round and more irregular",
        default=0.0,
        min=0.0,
        max=1.0,
        step=1
    )
    
    blast_asymmetry: FloatProperty(
        name="Blast Asymmetry",
        description="How asymmetric the explosion was (0 = perfect circle)",
        default=0.0,
        min=0.0,
        max=1.0,
        step=1
    )
    
    edge_fragmentation: FloatProperty(
        name="Edge Fragmentation",
        description="How broken/jagged the crater rim is",
        default=0.0,
        min=0.0,
        max=100.0,
        step=1
    )
    
    rim_height_variation: FloatProperty(
        name="Rim Height Variation",
        description="Random height variation across the rim (0 = uniform)",
        default=0.0,
        min=0.0,
        max=1.0,
        step=1
    )
    
    rim_noise_scale: FloatProperty(
        name="Rim Noise Scale",
        description="Scale of the noise pattern on rim",
        default=3.0,
        min=0.5,
        max=10.0
    )
    
    # Random range controls for all parameters with tighter, more reasonable ranges
    random_outer_radius_min: FloatProperty(
        name="Random Outer Radius Min",
        description="Minimum outer radius for random generation",
        default=2.0,
        min=0.1,
        max=99.0,
        unit='LENGTH'
    )
    
    random_outer_radius_max: FloatProperty(
        name="Random Outer Radius Max", 
        description="Maximum outer radius for random generation",
        default=3.5,
        min=1.0,
        max=200.0,
        unit='LENGTH'
    )
    
    random_inner_radius_min: FloatProperty(
        name="Random Inner Radius Min",
        description="Minimum inner radius for random generation",
        default=1.0,
        min=0.1,
        max=99.0,
        unit='LENGTH'
    )
    
    random_inner_radius_max: FloatProperty(
        name="Random Inner Radius Max", 
        description="Maximum inner radius for random generation",
        default=1.8,
        min=1.0,
        max=200.0,
        unit='LENGTH'
    )
    
    random_depth_min: FloatProperty(
        name="Random Depth Min",
        default=0.3, min=0.1, max=99.0, unit='LENGTH'
    )
    random_depth_max: FloatProperty(
        name="Random Depth Max", 
        default=0.8, min=1.0, max=100.0, unit='LENGTH'
    )
    
    random_rim_height_min: FloatProperty(
        name="Random Rim Height Min",
        default=0.3, min=0.0, max=99.0, unit='LENGTH'
    )
    random_rim_height_max: FloatProperty(
        name="Random Rim Height Max",
        default=0.9, min=1.0, max=100.0, unit='LENGTH'
    )
    
    random_resolution_min: IntProperty(
        name="Random Resolution Min",
        default=20, min=8, max=499
    )
    random_resolution_max: IntProperty(
        name="Random Resolution Max",
        default=32, min=9, max=500
    )
    
    random_noise_min: FloatProperty(
        name="Random Noise Min",
        default=0.02, min=0.0, max=29.9
    )
    random_noise_max: FloatProperty(
        name="Random Noise Max",
        default=0.1, min=0.01, max=30.0
    )
    
    random_outside_noise_min: FloatProperty(
        name="Random Outside Noise Min",
        default=0.01, min=0.0, max=29.9
    )
    random_outside_noise_max: FloatProperty(
        name="Random Outside Noise Max",
        default=0.05, min=0.01, max=30.0
    )
    
    # Random ranges for explosion realism - tighter ranges
    random_blast_asymmetry_min: FloatProperty(
        name="Random Blast Asymmetry Min",
        default=0.0, min=0.0, max=0.99
    )
    random_blast_asymmetry_max: FloatProperty(
        name="Random Blast Asymmetry Max",
        default=0.2, min=0.01, max=1.0
    )
    
    random_edge_fragmentation_min: FloatProperty(
        name="Random Edge Fragmentation Min", 
        default=0.0, min=0.0, max=99.9
    )
    random_edge_fragmentation_max: FloatProperty(
        name="Random Edge Fragmentation Max",
        default=8.0, min=0.01, max=100.0
    )
    
    random_rim_variation_min: FloatProperty(
        name="Random Rim Variation Min",
        default=0.0, min=0.0, max=0.99
    )
    random_rim_variation_max: FloatProperty(
        name="Random Rim Variation Max",
        default=0.15, min=0.01, max=1.0
    )
    
    random_outline_irregularity_min: FloatProperty(
        name="Random Outline Irregularity Min",
        default=0.0, min=0.0, max=49.9
    )
    random_outline_irregularity_max: FloatProperty(
        name="Random Outline Irregularity Max",
        default=5.0, min=0.1, max=50.0
    )
    
    random_inner_asymmetry_min: FloatProperty(
        name="Random Inner Asymmetry Min",
        default=0.0, min=0.0, max=0.99
    )
    random_inner_asymmetry_max: FloatProperty(
        name="Random Inner Asymmetry Max",
        default=0.15, min=0.01, max=1.0
    )
    
    random_outer_edge_rounding_min: FloatProperty(
        name="Random Outer Edge Rounding Min",
        default=0.0, min=0.0, max=0.99
    )
    random_outer_edge_rounding_max: FloatProperty(
        name="Random Outer Edge Rounding Max",
        default=0.25, min=0.01, max=1.0
    )
    
    random_rim_edge_rounding_min: FloatProperty(
        name="Random Rim Edge Rounding Min",
        default=0.0, min=0.0, max=0.99
    )
    random_rim_edge_rounding_max: FloatProperty(
        name="Random Rim Edge Rounding Max",
        default=0.2, min=0.01, max=1.0
    )
    
    random_wall_angle_min: FloatProperty(
        name="Random Wall Angle Min",
        default=-10.0, min=-89.0, max=88.0, unit='ROTATION'
    )
    random_wall_angle_max: FloatProperty(
        name="Random Wall Angle Max",
        default=10.0, min=-88.0, max=89.0, unit='ROTATION'
    )


class MESH_OT_add_crater(Operator):
    """Generate clean game-ready crater mesh based on real crater analysis"""
    bl_idname = "mesh.add_crater"
    bl_label = "Add Game Crater"
    bl_options = {'REGISTER', 'UNDO', 'PRESET'}
    
    # Operator properties for undo panel - MUST MATCH PropertyGroup names exactly
    outer_radius: FloatProperty(name="Outer Radius", default=2.6, min=0.5, max=100.0)
    inner_radius: FloatProperty(name="Inner Radius", default=1.3, min=0.1, max=50.0)
    depth: FloatProperty(name="Depth", default=0.5, min=0.1, max=100.0)
    rim_height: FloatProperty(name="Rim Height", default=0.58, min=0.0, max=100.0)
    resolution: IntProperty(name="Resolution", default=24, min=8, max=500)
    noise_strength: FloatProperty(name="Inside Noise", default=0.0, min=0.0, max=30.0)
    outside_noise_strength: FloatProperty(name="Outside Noise", default=0.0, min=0.0, max=30.0)
    create_materials: BoolProperty(name="Materials", default=True)
    auto_uv: BoolProperty(name="Auto UV", default=True)
    optimize_for_games: BoolProperty(name="Game Optimization", default=True)
    close_bottom: BoolProperty(name="Close Bottom", default=True)
    center_origin: BoolProperty(name="Center Origin", default=False)
    bottom_thickness: FloatProperty(name="Bottom Thickness", default=1.0, min=0.1, max=10.0)
    outer_wall_angle: FloatProperty(name="Outer Wall Angle", default=0.0, min=-89.0, max=89.0)
    inner_wall_angle: FloatProperty(name="Inner Wall Angle", default=0.0, min=-89.0, max=89.0)
    rim_height_variation: FloatProperty(name="Rim Variation", default=0.0, min=0.0, max=1.0)
    rim_noise_scale: FloatProperty(name="Rim Noise Scale", default=3.0, min=0.5, max=10.0)
    blast_asymmetry: FloatProperty(name="Blast Asymmetry", default=0.0, min=0.0, max=1.0)
    edge_fragmentation: FloatProperty(name="Edge Fragmentation", default=0.0, min=0.0, max=100.0)
    inner_asymmetry: FloatProperty(name="Inner Asymmetry", default=0.0, min=0.0, max=1.0)
    crater_outline_irregularity: FloatProperty(name="Crater Outline Irregularity", default=0.0, min=0.0, max=50.0)
    rim_edge_rounding: FloatProperty(name="Rim Edge Rounding", default=0.0, min=0.0, max=1.0)
    outer_edge_rounding: FloatProperty(name="Outer Edge Rounding", default=0.0, min=0.0, max=1.0)
    center_origin_z_offset: FloatProperty(name="Center Origin Z Offset", default=0.0, min=-10.0, max=10.0)
    
    def execute(self, context):
        try:
            # Generate clean crater mesh
            crater_data = self.generate_clean_crater()
            if not crater_data:
                self.report({'ERROR'}, "Failed to generate crater mesh")
                return {'CANCELLED'}
            
            # Create mesh object
            mesh = bpy.data.meshes.new("GameCrater")
            obj = bpy.data.objects.new("GameCrater", mesh)
            
            # Calculate origin position with Z offset
            if self.center_origin:
                # Place origin at the underside/bottom of the crater with additional offset
                origin_z = -self.depth + self.center_origin_z_offset  # Bottom of crater + user offset
                obj.location = (
                    context.scene.cursor.location.x,
                    context.scene.cursor.location.y,
                    context.scene.cursor.location.z + origin_z
                )
                # Offset all mesh vertices to compensate for the new origin
                mesh_offset_z = -origin_z  # Inverse of the origin offset
                for i, vert in enumerate(crater_data['vertices']):
                    crater_data['vertices'][i] = [vert[0], vert[1], vert[2] + mesh_offset_z]
            else:
                # Standard behavior - origin at ground level
                obj.location = context.scene.cursor.location
            
            # Apply mesh data
            mesh.from_pydata(crater_data['vertices'], [], crater_data['faces'])
            mesh.update()
            
            # Apply game optimizations
            if self.optimize_for_games:
                self.optimize_mesh_for_games(mesh)
            
            # Link to scene and select
            context.collection.objects.link(obj)
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            context.view_layer.objects.active = obj
            
            # Apply materials and UVs
            if self.create_materials:
                self.setup_clean_materials(obj)
            if self.auto_uv:
                self.generate_crater_uvs(obj)
            
            # Report results
            tri_count = len(mesh.polygons)
            vertex_count = len(mesh.vertices)
            
            origin_info = "at crater bottom" if self.center_origin else "at ground level"
            self.report({'INFO'}, f"Crater: {tri_count} triangles, {vertex_count} vertices, origin {origin_info}")
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Crater generation failed: {str(e)}")
            return {'CANCELLED'}
    
    def generate_clean_crater(self):
        """Generate clean crater based on analysis data"""
        bm = bmesh.new()
        
        try:
            # Generate clean base geometry
            self.create_clean_crater_geometry(bm)
            
            # Add minimal surface detail
            self.apply_minimal_detail(bm)
            
            # Optimize topology
            if self.optimize_for_games:
                self.optimize_crater_topology(bm)
            
            # Extract mesh data
            vertices = [[v.co.x, v.co.y, v.co.z] for v in bm.verts]
            faces = [[v.index for v in f.verts] for f in bm.faces]
            
            return {'vertices': vertices, 'faces': faces}
            
        finally:
            bm.free()
    
    def create_clean_crater_geometry(self, bm):
        """Create clean crater geometry based on real crater analysis"""
        all_ring_verts = []
        
        # Use new dual radius system
        base_radius = self.outer_radius
        rim_radius = self.inner_radius
        
        # Calculate random asymmetry direction if asymmetric
        if self.blast_asymmetry > 0:
            blast_angle_rad = random.uniform(0, 2 * math.pi)  # Random direction each time
        else:
            blast_angle_rad = 0.0
        
        # Create outer ground-level base ring with outline irregularity and outer edge rounding
        all_ring_verts = []
        
        # Improved outer edge rounding with better geometry and scaling
        if self.outer_edge_rounding > 0:
            # Create more rings for smoother transitions
            outer_rings = max(3, int(self.outer_edge_rounding * 5 + 3))
            extended_radius = base_radius * (1.0 + self.outer_edge_rounding * 0.8)  # More extension
            
            for outer_ring in range(outer_rings):
                ring_factor = outer_ring / outer_rings
                # Smoother radius transition with curved falloff
                radius_curve = 1.0 - (ring_factor ** 1.5)
                ring_radius = extended_radius - (extended_radius - base_radius) * radius_curve
                
                # Improved height transition with more natural curve
                height_curve = 1.0 - ring_factor
                ring_height = -self.outer_edge_rounding * 0.25 * (1.0 - height_curve ** 1.8)
                
                ring_verts = []
                for i in range(self.resolution):
                    angle = 2 * math.pi * i / self.resolution
                    
                    # Apply blast asymmetry to outer rings with falloff
                    point_direction = angle - blast_angle_rad
                    alignment = math.cos(point_direction)
                    asymmetry_strength = 2.5 * (1.0 - ring_factor * 0.7)  # Reduce with distance
                    asymmetry_factor = 1.0 + self.blast_asymmetry * alignment * asymmetry_strength
                    
                    # Apply crater outline irregularity to outer rings with falloff
                    irregularity_factor = 1.0
                    if self.crater_outline_irregularity > 0:
                        noise_pos = Vector((math.cos(angle), math.sin(angle), ring_factor))
                        outline_noise = (
                            noise.noise(noise_pos * 2.0) * 0.5 +
                            noise.noise(noise_pos * 6.0) * 0.3 +
                            noise.noise(noise_pos * 12.0) * 0.2
                        )
                        irregularity_strength = 0.8 * (1.0 - ring_factor * 0.6)  # Reduce with distance
                        irregularity_factor = 1.0 + outline_noise * (self.crater_outline_irregularity / 50.0) * irregularity_strength
                    
                    combined_factor = asymmetry_factor * irregularity_factor
                    
                    x = ring_radius * math.cos(angle) * combined_factor
                    y = ring_radius * math.sin(angle) * combined_factor
                    z = ring_height
                    
                    ring_verts.append(bm.verts.new((x, y, z)))
                all_ring_verts.append(ring_verts)
        
        # Create main base ring
        base_verts = []
        for i in range(self.resolution):
            angle = 2 * math.pi * i / self.resolution
            
            # Apply blast asymmetry - crater extends further in blast direction
            # Calculate how aligned this point is with the blast direction
            point_direction = angle - blast_angle_rad
            alignment = math.cos(point_direction)  # -1 to 1, where 1 is perfectly aligned
            
            # Improved asymmetry with more realistic scaling
            asymmetry_factor = 1.0 + self.blast_asymmetry * alignment * 2.5  # Increased impact
            
            # Apply crater outline irregularity with improved noise function
            irregularity_factor = 1.0
            if self.crater_outline_irregularity > 0:
                # Use multiple noise octaves for more natural variation
                noise_pos = Vector((math.cos(angle), math.sin(angle), 0))
                outline_noise = (
                    noise.noise(noise_pos * 2.0) * 0.5 +      # Large-scale variation
                    noise.noise(noise_pos * 6.0) * 0.3 +      # Medium detail
                    noise.noise(noise_pos * 12.0) * 0.2       # Fine detail
                )
                # More aggressive scaling for visible effect (adjusted for 0-50 range)
                irregularity_factor = 1.0 + outline_noise * (self.crater_outline_irregularity / 50.0) * 0.8
            
            # Combine asymmetry and irregularity
            combined_factor = asymmetry_factor * irregularity_factor
            
            x = base_radius * math.cos(angle) * combined_factor
            y = base_radius * math.sin(angle) * combined_factor
            z = 0.0  # Ground level
            
            base_verts.append(bm.verts.new((x, y, z)))
        all_ring_verts.append(base_verts)
        
        # Create slope rings - minimal for clean geometry
        slope_rings = max(2, min(3, self.resolution // 16))
        
        for slope_ring in range(1, slope_rings + 1):
            ring_factor = slope_ring / slope_rings
            # Linear radius reduction from outer to inner radius
            ring_radius = base_radius - (base_radius - rim_radius) * ring_factor
            
            # Gentle slope rise (24° average from analysis)
            slope_height = self.rim_height * (ring_factor ** 0.8)
            
            ring_verts = []
            for i in range(self.resolution):
                angle = 2 * math.pi * i / self.resolution
                
                # Apply blast asymmetry to slope rings too
                point_direction = angle - blast_angle_rad
                alignment = math.cos(point_direction)
                asymmetry_factor = 1.0 + self.blast_asymmetry * alignment * 0.8  # Increased from 0.3 to 0.8
                
                # Apply crater outline irregularity to slope rings
                irregularity_factor = 1.0
                if self.crater_outline_irregularity > 0:
                    noise_pos = Vector((math.cos(angle), math.sin(angle), ring_factor)) * 2.0
                    outline_noise = (
                        noise.noise(noise_pos * 3.0) * 0.4 +
                        noise.noise(noise_pos * 8.0) * 0.3 +
                        noise.noise(noise_pos * 1.5) * 0.3
                    )
                    irregularity_factor = 1.0 + outline_noise * (self.crater_outline_irregularity / 50.0) * 0.3
                
                combined_factor = asymmetry_factor * irregularity_factor
                
                x = ring_radius * math.cos(angle) * combined_factor
                y = ring_radius * math.sin(angle) * combined_factor
                z = slope_height
                
                ring_verts.append(bm.verts.new((x, y, z)))
            all_ring_verts.append(ring_verts)
        
        # Create crater rim with improved variation and fragmentation
        rim_verts = []
        
        # Add extra rim rings for top edge rounding if enabled
        if self.rim_edge_rounding > 0:
            # Create additional rings above the main rim for smooth top edge
            rim_rings = max(2, int(self.rim_edge_rounding * 3 + 2))
            
            for rim_ring in range(rim_rings):
                ring_factor = rim_ring / rim_rings
                # Smooth radius transition inward for rounded top
                radius_factor = 1.0 - (ring_factor * self.rim_edge_rounding * 0.15)
                # Smooth height transition downward from peak
                height_factor = 1.0 - (ring_factor ** (2.0 - self.rim_edge_rounding * 0.8)) * self.rim_edge_rounding * 0.3
                
                ring_verts = []
                for i in range(self.resolution):
                    angle = 2 * math.pi * i / self.resolution
                    
                    # Apply blast asymmetry to rim rings
                    point_direction = angle - blast_angle_rad
                    alignment = math.cos(point_direction)
                    asymmetry_factor = 1.0 + self.blast_asymmetry * alignment * 0.6
                    
                    # Apply crater outline irregularity to rim rings
                    irregularity_factor = 1.0
                    if self.crater_outline_irregularity > 0:
                        noise_pos = Vector((math.cos(angle), math.sin(angle), ring_factor))
                        outline_noise = (
                            noise.noise(noise_pos * 2.0) * 0.5 +
                            noise.noise(noise_pos * 6.0) * 0.3 +
                            noise.noise(noise_pos * 12.0) * 0.2
                        )
                        irregularity_factor = 1.0 + outline_noise * (self.crater_outline_irregularity / 50.0) * 0.25
                    
                    combined_factor = asymmetry_factor * irregularity_factor * radius_factor
                    
                    x = rim_radius * math.cos(angle) * combined_factor
                    y = rim_radius * math.sin(angle) * combined_factor
                    
                    # Calculate height with rim edge rounding affecting the top
                    base_height = self.rim_height * height_factor
                    
                    ring_verts.append(bm.verts.new((x, y, base_height)))
                all_ring_verts.append(ring_verts)
        
        # Create main rim ring
        for i in range(self.resolution):
            angle = 2 * math.pi * i / self.resolution
            
            # Apply blast asymmetry to rim
            point_direction = angle - blast_angle_rad
            alignment = math.cos(point_direction)
            asymmetry_factor = 1.0 + self.blast_asymmetry * alignment * 0.6
            
            # Apply crater outline irregularity to rim
            irregularity_factor = 1.0
            if self.crater_outline_irregularity > 0:
                noise_pos = Vector((math.cos(angle), math.sin(angle), 1.0))
                outline_noise = (
                    noise.noise(noise_pos * 2.0) * 0.5 +
                    noise.noise(noise_pos * 6.0) * 0.3 +
                    noise.noise(noise_pos * 12.0) * 0.2
                )
                irregularity_factor = 1.0 + outline_noise * (self.crater_outline_irregularity / 50.0) * 0.25
            
            combined_factor = asymmetry_factor * irregularity_factor
            
            x = rim_radius * math.cos(angle) * combined_factor
            y = rim_radius * math.sin(angle) * combined_factor
            
            # Completely rebuilt rim height variation with much better noise
            height_variation = 0.0
            if self.rim_height_variation > 0:
                # Use multiple noise layers for realistic geological variation
                height_pos = Vector((x, y, 0)) * (self.rim_noise_scale * 0.03)  # Better base scaling
                height_noise = (
                    noise.noise(height_pos * 1.0) * 0.6 +     # Large geological features
                    noise.noise(height_pos * 3.5) * 0.25 +   # Medium undulation
                    noise.noise(height_pos * 8.0) * 0.15     # Fine surface detail
                )
                # Much more dramatic and realistic height variation
                height_variation = height_noise * self.rim_height_variation * self.rim_height * 2.0
            
            # Completely rebuilt edge fragmentation with realistic crater damage
            fragmentation_factor = 1.0
            if self.edge_fragmentation > 0:
                # Multiple fragmentation patterns for realistic explosive damage
                frag_pos = Vector((x, y, 0)) * 0.008  # Fine-tuned scale
                
                # Large blast chunks
                large_chunks = noise.noise(frag_pos * 6.0) * 0.5
                # Medium debris patterns  
                medium_chunks = noise.noise(frag_pos * 15.0) * 0.3
                # Fine fragmentation detail
                fine_detail = noise.noise(frag_pos * 35.0) * 0.2
                
                frag_noise = large_chunks + medium_chunks + fine_detail
                
                # Improved fragmentation with realistic damage patterns
                frag_intensity = self.edge_fragmentation / 100.0
                frag_threshold = 0.4 - (frag_intensity * 0.7)  # More aggressive threshold
                
                if frag_noise > frag_threshold:
                    # Create realistic chunk removal with varied damage
                    damage_amount = ((frag_noise - frag_threshold) / (1.0 - frag_threshold))
                    # Use power curve for more realistic damage distribution
                    damage_curve = damage_amount ** (0.8 - frag_intensity * 0.3)
                    fragmentation_factor = max(0.02, 1.0 - damage_curve * frag_intensity * 1.8)
            
            # Apply fragmentation to both position and height
            final_rim_height = (self.rim_height + height_variation) * fragmentation_factor
            
            rim_verts.append(bm.verts.new((x, y, final_rim_height)))
        all_ring_verts.append(rim_verts)
        
        # Create inner crater bowl with inner wall angle support and inner asymmetry
        inner_rings = max(1, min(2, self.resolution // 20))
        
        # Calculate inner wall angle offset
        inner_wall_angle_rad = math.radians(self.inner_wall_angle)
        inner_wall_offset_factor = math.tan(inner_wall_angle_rad) * 2.0  # Multiplier for effect
        
        # Generate random direction for inner asymmetry (different from blast asymmetry)
        if self.inner_asymmetry > 0:
            inner_asymmetry_angle = random.uniform(0, 2 * math.pi)
        else:
            inner_asymmetry_angle = 0.0
        
        for ring in range(1, inner_rings + 1):
            ring_factor = ring / inner_rings
            base_ring_radius = rim_radius * (1.0 - ring_factor * 0.7)
            
            # Apply inner wall angle - affects how the crater walls slope inward
            depth_factor = (self.rim_height + self.depth) * ring_factor
            wall_radius_adjustment = depth_factor * inner_wall_offset_factor
            ring_radius = base_ring_radius + wall_radius_adjustment
            
            # Crater depth calculation
            z = self.rim_height - depth_factor
            
            ring_verts = []
            for i in range(self.resolution):
                angle = 2 * math.pi * i / self.resolution
                
                # Apply blast asymmetry to inner crater
                point_direction = angle - blast_angle_rad
                alignment = math.cos(point_direction)
                blast_asymmetry_factor = 1.0 + self.blast_asymmetry * alignment * 0.4  # Increased from 0.1 to 0.4
                
                # Improved inner asymmetry with better noise and directional effects
                if self.inner_asymmetry > 0:
                    inner_point_direction = angle - inner_asymmetry_angle
                    inner_alignment = math.cos(inner_point_direction)
                    
                    # Multiple noise layers for more natural irregular patterns
                    noise_input = Vector((math.cos(angle), math.sin(angle), ring_factor)) * 3.0
                    noise_variation = (
                        noise.noise(noise_input * 1.0) * 0.4 +      # Large-scale deformation
                        noise.noise(noise_input * 4.0) * 0.35 +     # Medium bumps/indents
                        noise.noise(noise_input * 10.0) * 0.25      # Fine surface variation
                    )
                    
                    # Improved asymmetry combining directional bias with organic noise
                    directional_component = inner_alignment * 0.4  # Directional blast pattern
                    noise_component = noise_variation * 0.8        # Organic irregularity
                    
                    inner_asymmetry_factor = 1.0 + self.inner_asymmetry * (
                        directional_component + noise_component
                    )
                else:
                    inner_asymmetry_factor = 1.0
                
                # Combine both asymmetry effects
                combined_asymmetry = blast_asymmetry_factor * inner_asymmetry_factor
                
                x = ring_radius * math.cos(angle) * combined_asymmetry
                y = ring_radius * math.sin(angle) * combined_asymmetry
                
                ring_verts.append(bm.verts.new((x, y, z)))
            all_ring_verts.append(ring_verts)
        
        # Create center point at the bottom of the crater with inner wall angle consideration
        center_height = -self.depth  # Center is at full crater depth below ground
        
        # Apply inner wall angle to center position
        total_depth = self.rim_height + self.depth
        center_radius_adjustment = total_depth * inner_wall_offset_factor
        
        # Apply inner asymmetry to center point as well
        if self.inner_asymmetry > 0:
            center_noise = noise.noise(Vector((0, 0, 1)) * 3.0) * self.inner_asymmetry * 0.2
            center_x = center_radius_adjustment * 0.1 + center_noise
            center_y = center_radius_adjustment * 0.1 + center_noise * 0.7
        else:
            center_x = center_radius_adjustment * 0.1  # Small offset for realistic effect
            center_y = center_radius_adjustment * 0.1
        
        center_vert = bm.verts.new((center_x, center_y, center_height))
        all_ring_verts.append([center_vert])
        
        # Connect rings with quads
        for ring_idx in range(len(all_ring_verts) - 1):
            current_ring = all_ring_verts[ring_idx]
            next_ring = all_ring_verts[ring_idx + 1]
            
            if len(next_ring) == 1:  # Connect to center
                for i in range(len(current_ring)):
                    next_i = (i + 1) % len(current_ring)
                    tri_verts = [current_ring[i], current_ring[next_i], next_ring[0]]
                    bm.faces.new(tri_verts)
            else:  # Connect rings
                for i in range(len(current_ring)):
                    next_i = (i + 1) % len(current_ring)
                    quad_verts = [
                        current_ring[i], current_ring[next_i],
                        next_ring[next_i], next_ring[i]
                    ]
                    try:
                        bm.faces.new(quad_verts)
                    except:
                        pass
        
        # Close the bottom if requested
        if self.close_bottom:
            self.create_crater_bottom(bm, all_ring_verts)
        
        bm.normal_update()
        bm.faces.ensure_lookup_table()
    
    def create_crater_bottom(self, bm, all_ring_verts):
        """Create a closed bottom for the crater with slanted outer walls"""
        # Get the outermost ring (base ring)
        base_ring = all_ring_verts[0]
        
        # Create bottom vertices at a depth below the crater
        bottom_depth = -self.bottom_thickness
        bottom_verts = []
        
        # Calculate outer wall offset based on outer wall angle
        outer_wall_angle_rad = math.radians(self.outer_wall_angle)
        # Increased multiplier for more visible effect
        wall_offset = self.bottom_thickness * math.tan(outer_wall_angle_rad) * 3.0
        
        # Create intermediate rings for slanted walls - more rings for smoother effect
        wall_rings = 5  # Increased from 3 to 5 for smoother slant
        all_wall_rings = []
        
        # Add the base ring as first wall ring
        all_wall_rings.append(base_ring)
        
        # Create intermediate rings with progressive offset
        for ring_idx in range(1, wall_rings):
            ring_factor = ring_idx / wall_rings
            ring_depth = -self.bottom_thickness * ring_factor
            # Use exponential curve for more dramatic effect
            ring_offset = wall_offset * (ring_factor ** 1.5)
            
            ring_verts = []
            for vert in base_ring:
                # Calculate direction from center for offset
                direction_x = vert.co.x
                direction_y = vert.co.y
                distance = math.sqrt(direction_x**2 + direction_y**2)
                
                if distance > 0:
                    # Normalize direction and apply progressive offset
                    norm_x = direction_x / distance
                    norm_y = direction_y / distance
                    
                    new_x = vert.co.x + norm_x * ring_offset
                    new_y = vert.co.y + norm_y * ring_offset
                else:
                    new_x = vert.co.x
                    new_y = vert.co.y
                
                ring_verts.append(bm.verts.new((new_x, new_y, ring_depth)))
            
            all_wall_rings.append(ring_verts)
        
        # Create final bottom ring with full offset
        for vert in base_ring:
            # Calculate direction from center for offset
            direction_x = vert.co.x
            direction_y = vert.co.y
            distance = math.sqrt(direction_x**2 + direction_y**2)
            
            if distance > 0:
                # Normalize direction and apply full offset
                norm_x = direction_x / distance
                norm_y = direction_y / distance
                
                bottom_x = vert.co.x + norm_x * wall_offset
                bottom_y = vert.co.y + norm_y * wall_offset
            else:
                bottom_x = vert.co.x
                bottom_y = vert.co.y
            
            bottom_z = bottom_depth
            bottom_verts.append(bm.verts.new((bottom_x, bottom_y, bottom_z)))
        
        all_wall_rings.append(bottom_verts)
        
        # Create center bottom vertex - also offset it based on outer wall angle
        center_offset_x = 0
        center_offset_y = 0
        if abs(self.outer_wall_angle) > 1:  # Only offset if significant angle
            # Create slight center offset for more realistic slanted bottom
            center_offset_x = wall_offset * 0.1
            center_offset_y = wall_offset * 0.1
        
        center_bottom = bm.verts.new((center_offset_x, center_offset_y, bottom_depth))
        
        # Connect wall rings to create slanted walls
        for ring_idx in range(len(all_wall_rings) - 1):
            current_ring = all_wall_rings[ring_idx]
            next_ring = all_wall_rings[ring_idx + 1]
            
            for i in range(len(current_ring)):
                next_i = (i + 1) % len(current_ring)
                try:
                    # Create quad connecting current ring to next ring
                    quad_face = bm.faces.new([
                        current_ring[i], current_ring[next_i],
                        next_ring[next_i], next_ring[i]
                    ])
                    # Don't set material here - let material assignment function handle it
                except:
                    pass
        
        # Create bottom faces (close the bottom)
        for i in range(len(bottom_verts)):
            next_i = (i + 1) % len(bottom_verts)
            try:
                # Create triangular faces from outer bottom ring to center
                tri_face = bm.faces.new([bottom_verts[i], bottom_verts[next_i], center_bottom])
                # Don't set material here - let material assignment function handle it
            except:
                pass
    
    def apply_minimal_detail(self, bm):
        """Apply surface noise with different levels inside vs outside rim"""
        if self.noise_strength <= 0 and self.outside_noise_strength <= 0:
            return
            
        for vert in bm.verts:
            # Multiple octave noise for smoother result
            pos = vert.co
            noise_val = (
                noise.noise(pos * 1.0) * 0.5 +      # Large features
                noise.noise(pos * 3.0) * 0.3 +      # Medium features  
                noise.noise(pos * 8.0) * 0.2        # Fine detail
            )
            
            # Determine if vertex is inside or outside crater rim with transition zone
            distance_from_center = math.sqrt(vert.co.x**2 + vert.co.y**2)
            rim_radius = self.inner_radius  # FIXED: use inner_radius consistently
            transition_width = rim_radius * 0.3  # 30% transition zone
            
            # Create smooth transition between inside and outside
            if distance_from_center < rim_radius - transition_width:
                # Clearly inside
                noise_strength = self.noise_strength
            elif distance_from_center > rim_radius + transition_width:
                # Clearly outside  
                noise_strength = self.outside_noise_strength
            else:
                # Transition zone - blend between inside and outside
                blend_factor = (distance_from_center - (rim_radius - transition_width)) / (2 * transition_width)
                blend_factor = max(0, min(1, blend_factor))
                noise_strength = self.noise_strength * (1 - blend_factor) + self.outside_noise_strength * blend_factor
            
            # Apply noise with much gentler scaling
            final_noise = noise_val * noise_strength * 0.1  # Reduced from 0.3 to 0.1
            
            # Apply with falloff and clamping to prevent spikes
            base_radius = self.outer_radius * 2.0  # FIXED: use outer_radius
            if distance_from_center < base_radius:
                falloff = 1.0 - (distance_from_center / base_radius)
                noise_offset = final_noise * falloff * 0.3  # Reduced from 0.5 to 0.3
                
                # Clamp noise to prevent extreme spikes
                max_noise = min(self.rim_height * 0.2, 0.5)  # Max 20% of rim height or 0.5m
                noise_offset = max(-max_noise, min(max_noise, noise_offset))
                
                vert.co.z += noise_offset
    
    def optimize_crater_topology(self, bm):
        """Clean up topology for games"""
        # Remove duplicate vertices
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
        
        # Remove degenerate geometry
        bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=0.0001)
        
        # Recalculate normals
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        
        # Triangulate for game engines
        bmesh.ops.triangulate(
            bm, 
            faces=bm.faces,
            quad_method='BEAUTY',
            ngon_method='BEAUTY'
        )
    
    def optimize_mesh_for_games(self, mesh):
        """Final game optimizations"""
        mesh.validate(verbose=False, clean_customdata=True)
        mesh.calc_loop_triangles()
        mesh.update()
        
        # Set smooth shading
        for poly in mesh.polygons:
            poly.use_smooth = True
    
    def setup_clean_materials(self, obj):
        """Create clean materials for crater"""
        try:
            obj.data.materials.clear()
            
            # Inner crater material - use the specified dirt material if available
            inner_mat = self.create_inner_material()
            obj.data.materials.append(inner_mat)
            
            # Outer slope material
            outer_mat = self.create_outer_material()
            obj.data.materials.append(outer_mat)
            
            # Assign materials
            self.assign_materials_clean(obj)
            
        except Exception as e:
            print(f"Material setup error: {e}")
    
    def create_inner_material(self):
        """Create inner crater material"""
        # Create standard inner crater material (not using the dirt material)
        mat = bpy.data.materials.new(name="Crater_Inner")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()
        
        # Simple material setup
        output = nodes.new('ShaderNodeOutputMaterial')
        principled = nodes.new('ShaderNodeBsdfPrincipled')
        
        # Dark crater color
        principled.inputs['Base Color'].default_value = (0.15, 0.1, 0.08, 1.0)
        principled.inputs['Roughness'].default_value = 0.9
        
        links.new(principled.outputs['BSDF'], output.inputs['Surface'])
        return mat
    
    def create_outer_material(self):
        """Create outer slope material"""
        mat = bpy.data.materials.new(name="Crater_Outer")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()
        
        # Simple material setup
        output = nodes.new('ShaderNodeOutputMaterial')
        principled = nodes.new('ShaderNodeBsdfPrincipled')
        
        # Earth color
        principled.inputs['Base Color'].default_value = (0.5, 0.4, 0.3, 1.0)
        principled.inputs['Roughness'].default_value = 0.8
        
        links.new(principled.outputs['BSDF'], output.inputs['Surface'])
        return mat
    
    def assign_materials_clean(self, obj):
        """Assign materials based on analyzed crater geometry"""
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        
        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        
        # Based on your analysis: rim peak at distance 1.622, base at 2.575
        # Scale these proportionally to the current crater size
        rim_distance = self.inner_radius
        base_distance = self.outer_radius
        
        for face in bm.faces:
            face_center = face.calc_center_median()
            distance_from_center = math.sqrt(face_center.x**2 + face_center.y**2)
            
            # Special handling for bottom closure geometry
            if self.close_bottom:
                # Flat bottom: at the bottom thickness level (regardless of distance)
                if face_center.z <= (-self.bottom_thickness + 0.05):
                    face.material_index = 1  # Outer material for flat bottom
                    continue
                    
                # Side walls: below ground AND outside the main crater area
                if (face_center.z < -0.05 and  # Below ground
                    distance_from_center > self.outer_radius * 0.8):  # Outside main crater
                    face.material_index = 1  # Outer material for side walls
                    continue
            
            # Normal crater material assignment
            # Inner material: rim area and inner crater (steep areas)
            # Outer material: gentle outer slopes
            is_inner = (
                # Around rim peak area
                distance_from_center < rim_distance * 1.2 or
                # High elevation areas (above 40% of rim height)
                face_center.z > self.rim_height * 0.4 or
                # Steep slopes (your analysis showed steep inner areas)
                face.normal.z < 0.4
            )
            
            face.material_index = 0 if is_inner else 1
        
        bmesh.update_edit_mesh(obj.data)
        bpy.ops.object.mode_set(mode='OBJECT')
    
    def generate_crater_uvs(self, obj):
        """Generate clean UV mapping optimized for craters"""
        try:
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            
            if not obj.data.uv_layers:
                bpy.ops.mesh.uv_texture_add()
            
            # Clear any existing UV data
            bpy.ops.mesh.select_all(action='SELECT')
            
            # Use cylindrical projection which works well for crater geometry
            bpy.ops.uv.cylinder_project(
                direction='VIEW_ON_EQUATOR',
                align='POLAR_ZZ',
                scale_to_bounds=False,
                correct_aspect=True
            )
            
            # Follow up with angle-based seams for better unwrapping
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.angle_based_unwrap(
                angle_limit=math.radians(66),  # More generous angle limit
                margin=0.001
            )
            
            # Pack islands efficiently
            bpy.ops.uv.pack_islands(
                rotate=True,
                margin=0.01,  # Smaller margin for better space usage
                scale=True,
                merge_overlap=False
            )
            
            # Additional cleanup: remove doubles in UV space
            bpy.ops.uv.remove_doubles(threshold=0.02, use_unselected=False)
            
            bpy.ops.object.mode_set(mode='OBJECT')
            return True
            
        except Exception as e:
            print(f"UV mapping error: {e}")
            # Fallback to simpler method if advanced unwrapping fails
            try:
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                
                # Simple project from view as fallback
                bpy.ops.uv.project_from_view(
                    camera_bounds=True,
                    correct_aspect=True,
                    scale_to_bounds=False
                )
                
                bpy.ops.object.mode_set(mode='OBJECT')
                return True
            except:
                bpy.ops.object.mode_set(mode='OBJECT')
                return False
    
    def invoke(self, context, event):
        """Called when the operator is invoked from the panel"""
        # Copy values from scene properties to operator properties
        if hasattr(context.scene, 'crater_properties'):
            props = context.scene.crater_properties
            self.outer_radius = props.outer_radius
            self.inner_radius = props.inner_radius
            self.depth = props.depth
            self.rim_height = props.rim_height
            self.resolution = props.resolution
            self.noise_strength = props.noise_strength
            self.outside_noise_strength = props.outside_noise_strength
            self.create_materials = props.create_materials
            self.auto_uv = props.auto_uv
            self.optimize_for_games = props.optimize_for_games
            self.close_bottom = props.close_bottom
            self.center_origin = props.center_origin
            self.bottom_thickness = props.bottom_thickness
            self.outer_wall_angle = props.outer_wall_angle
            self.inner_wall_angle = props.inner_wall_angle
            self.rim_height_variation = props.rim_height_variation
            self.rim_noise_scale = props.rim_noise_scale
            self.blast_asymmetry = props.blast_asymmetry
            self.edge_fragmentation = props.edge_fragmentation
            self.inner_asymmetry = props.inner_asymmetry
            self.crater_outline_irregularity = props.crater_outline_irregularity
            self.rim_edge_rounding = props.rim_edge_rounding
            self.outer_edge_rounding = props.outer_edge_rounding
            self.center_origin_z_offset = props.center_origin_z_offset
        
        return self.execute(context)


class MESH_OT_add_random_crater(Operator):
    """Generate randomized crater with varied parameters"""
    bl_idname = "mesh.add_random_crater"
    bl_label = "Add Random Crater"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Randomize all crater parameters using user-defined ranges
        scene = context.scene
        props = scene.crater_properties
        
        # Basic dimensions with realistic ranges
        props.outer_radius = random.uniform(props.random_outer_radius_min, props.random_outer_radius_max)
        props.inner_radius = random.uniform(props.random_inner_radius_min, props.random_inner_radius_max)
        
        # Ensure inner radius is smaller than outer radius
        if props.inner_radius >= props.outer_radius:
            props.inner_radius = props.outer_radius * 0.7
        
        props.depth = random.uniform(props.random_depth_min, props.random_depth_max)
        props.rim_height = random.uniform(props.random_rim_height_min, props.random_rim_height_max)
        props.resolution = random.randint(props.random_resolution_min, props.random_resolution_max)
        
        # Surface noise
        props.noise_strength = random.uniform(props.random_noise_min, props.random_noise_max)
        props.outside_noise_strength = random.uniform(props.random_outside_noise_min, props.random_outside_noise_max)
        
        # Explosion realism features
        props.blast_asymmetry = random.uniform(props.random_blast_asymmetry_min, props.random_blast_asymmetry_max)
        props.edge_fragmentation = random.uniform(props.random_edge_fragmentation_min, props.random_edge_fragmentation_max)
        props.crater_outline_irregularity = random.uniform(props.random_outline_irregularity_min, props.random_outline_irregularity_max)
        props.inner_asymmetry = random.uniform(props.random_inner_asymmetry_min, props.random_inner_asymmetry_max)
        
        # Rim features
        props.rim_height_variation = random.uniform(props.random_rim_variation_min, props.random_rim_variation_max)
        props.rim_noise_scale = random.uniform(1.0, 8.0)
        props.outer_edge_rounding = random.uniform(props.random_outer_edge_rounding_min, props.random_outer_edge_rounding_max)
        props.rim_edge_rounding = random.uniform(props.random_rim_edge_rounding_min, props.random_rim_edge_rounding_max)
        
        # Wall angles
        props.outer_wall_angle = random.uniform(props.random_wall_angle_min, props.random_wall_angle_max)
        props.inner_wall_angle = random.uniform(props.random_wall_angle_min, props.random_wall_angle_max)
        
        # Always keep these true for working results
        props.create_materials = True
        props.auto_uv = True  
        props.optimize_for_games = True
        
        # Generate single crater
        bpy.ops.mesh.add_crater(
            outer_radius=props.outer_radius,
            inner_radius=props.inner_radius,
            depth=props.depth, 
            rim_height=props.rim_height,
            resolution=props.resolution,
            noise_strength=props.noise_strength,
            outside_noise_strength=props.outside_noise_strength,
            create_materials=props.create_materials,
            auto_uv=props.auto_uv,
            optimize_for_games=props.optimize_for_games,
            rim_height_variation=props.rim_height_variation,
            rim_noise_scale=props.rim_noise_scale,
            blast_asymmetry=props.blast_asymmetry,
            edge_fragmentation=props.edge_fragmentation,
            inner_asymmetry=props.inner_asymmetry,
            crater_outline_irregularity=props.crater_outline_irregularity,
            rim_edge_rounding=props.rim_edge_rounding,
            outer_edge_rounding=props.outer_edge_rounding,
            center_origin_z_offset=props.center_origin_z_offset,
            close_bottom=props.close_bottom,
            center_origin=props.center_origin,
            bottom_thickness=props.bottom_thickness,
            outer_wall_angle=props.outer_wall_angle,
            inner_wall_angle=props.inner_wall_angle
        )
        
        self.report({'INFO'}, f"Random: Outer={props.outer_radius:.1f} Inner={props.inner_radius:.1f} H={props.rim_height:.1f} Res={props.resolution}")
        
        return {'FINISHED'}


class MESH_OT_crater_create_firegeo_collision(Operator):
    """Create FireGeo collision for selected crater objects"""
    bl_idname = "mesh.crater_create_firegeo_collision"
    bl_label = "Create FireGeo Collision"
    bl_options = {'REGISTER', 'UNDO'}
    
    method: EnumProperty(
        name="Method",
        items=[
            ('CONVEX', "Convex Hull", "Simplified convex hull"),
            ('DETAILED', "Detailed", "Preserves shape better"),
        ],
        default='DETAILED'
    )
    target_faces: IntProperty(name="Target Faces", default=400, min=100, max=5000)
    offset: FloatProperty(name="Offset", default=0.01, min=0.0, max=0.05)
    
    def execute(self, context):
        if not context.selected_objects:
            self.report({'ERROR'}, "No objects selected")
            return {'CANCELLED'}
        
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not mesh_objects:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}
        
        collision_objects = []
        total_faces = 0
        
        # Create or get BuildingFireView collection
        collection_name = "BuildingFireView"
        if collection_name not in bpy.data.collections:
            fireview_collection = bpy.data.collections.new(collection_name)
            context.scene.collection.children.link(fireview_collection)
        else:
            fireview_collection = bpy.data.collections[collection_name]
        
        for idx, source_obj in enumerate(mesh_objects):
            bpy.ops.object.select_all(action='DESELECT')
            source_obj.select_set(True)
            context.view_layer.objects.active = source_obj
            
            bpy.ops.object.duplicate()
            dup_obj = context.selected_objects[0]
            
            if len(mesh_objects) == 1:
                dup_obj.name = "UTM_crater"
            else:
                dup_obj.name = f"UTM_crater_part_{idx}"
                
            collision_objects.append(dup_obj)
            
            part_target_faces = int(self.target_faces / len(mesh_objects))
            current_faces = len(dup_obj.data.polygons)
            
            if current_faces > part_target_faces:
                obj_dimensions = dup_obj.dimensions
                is_flat = min(obj_dimensions) < max(obj_dimensions) * 0.1
                
                if is_flat:
                    target_ratio = max(0.8, part_target_faces / current_faces)
                else:
                    target_ratio = part_target_faces / current_faces
                
                if target_ratio < 1.0:
                    decimate = dup_obj.modifiers.new(name="Decimate", type='DECIMATE')
                    decimate.ratio = max(0.1, target_ratio)
                    bpy.ops.object.modifier_apply(modifier=decimate.name)
            
            if self.offset > 0:
                solidify = dup_obj.modifiers.new(name="Solidify", type='SOLIDIFY')
                solidify.thickness = self.offset
                solidify.offset = 1.0
                bpy.ops.object.modifier_apply(modifier=solidify.name)
            
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            obj_dimensions = dup_obj.dimensions
            is_flat = min(obj_dimensions) < max(obj_dimensions) * 0.1
            merge_threshold = 0.0001 if is_flat else 0.001
            bpy.ops.mesh.remove_doubles(threshold=merge_threshold)
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # Create or use the specific dirt material for FireGeo collision
            mat_name = "dirt_C3691F2D8FE0234F"
            if mat_name in bpy.data.materials:
                mat = bpy.data.materials[mat_name]
            else:
                # Create fallback FireGeo material if specific dirt material doesn't exist
                if "FireGeo_Material" not in bpy.data.materials:
                    mat = bpy.data.materials.new(name="FireGeo_Material")
                    mat.diffuse_color = (0.0, 0.8, 0.0, 0.5)
                else:
                    mat = bpy.data.materials["FireGeo_Material"]
            
            dup_obj.data.materials.clear()
            dup_obj.data.materials.append(mat)
            dup_obj["layer_preset"] = "BuildingFireView"
            dup_obj["usage"] = "BuildingFireView"
            
            # Move to BuildingFireView collection
            if dup_obj.name in context.scene.collection.objects:
                context.scene.collection.objects.unlink(dup_obj)
            fireview_collection.objects.link(dup_obj)
            
            total_faces += len(dup_obj.data.polygons)
        
        # Select all collision objects
        bpy.ops.object.select_all(action='DESELECT')
        for obj in collision_objects:
            obj.select_set(True)
        
        if collision_objects:
            context.view_layer.objects.active = collision_objects[0]
        
        self.report({'INFO'}, f"Created FireGeo collision with {total_faces} total faces")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


class MESH_OT_crater_create_lods(Operator):
    """Create LOD levels for selected crater objects"""
    bl_idname = "mesh.crater_create_lods"
    bl_label = "Create LOD Levels"
    bl_options = {'REGISTER', 'UNDO'}
    
    lod_levels: IntProperty(
        name="LOD Levels", 
        default=3, 
        min=1, 
        max=5,
        description="Number of LOD levels to create"
    )
    
    create_collection: BoolProperty(
        name="Create Collection", 
        default=True,
        description="Organize LODs in a collection"
    )
    
    join_lod_levels: BoolProperty(
        name="Join LOD Levels", 
        default=True,
        description="Join all parts of each LOD level into single objects"
    )
    
    aggressive_reduction: BoolProperty(
        name="Aggressive Reduction", 
        default=True,
        description="Use more dramatic reduction ratios for visible LOD differences"
    )
    
    def execute(self, context):
        if not context.selected_objects:
            self.report({'ERROR'}, "No objects selected")
            return {'CANCELLED'}
        
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not mesh_objects:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}
        
        # Get base name from first object or use "Crater" as default
        first_obj = mesh_objects[0]
        base_name = first_obj.name.replace("_LOD0", "").split("_")[0] if "_" in first_obj.name else "Crater"
        
        # Create collection if requested
        if self.create_collection:
            collection_name = f"{base_name}_LOD_Collection"
            # Check if collection already exists
            if collection_name not in bpy.data.collections:
                new_collection = bpy.data.collections.new(collection_name)
                context.scene.collection.children.link(new_collection)
            else:
                new_collection = bpy.data.collections[collection_name]
        
        # Improved reduction ratios for complex crater geometry
        if self.aggressive_reduction:
            ratios = [0.6, 0.35, 0.2, 0.12, 0.08]  # More conservative for complex meshes
        else:
            ratios = [0.75, 0.5, 0.3, 0.2, 0.15]  # Very conservative reduction
        
        created_lods = 0
        all_lod_objects = {i: [] for i in range(1, self.lod_levels + 1)}  # Track objects by LOD level
        
        # Process each selected object
        for source_obj in mesh_objects:
            obj_base_name = source_obj.name.replace("_LOD0", "")
            
            for lod in range(1, min(self.lod_levels + 1, 6)):  # Max 5 LODs
                # Duplicate from source
                bpy.ops.object.select_all(action='DESELECT')
                source_obj.select_set(True)
                context.view_layer.objects.active = source_obj
                
                bpy.ops.object.duplicate_move(
                    OBJECT_OT_duplicate={"linked": False, "mode": 'TRANSLATION'}, 
                    TRANSFORM_OT_translate={"value": (0, 0, 0)}
                )
                
                lod_obj = context.active_object
                lod_obj.name = f"{obj_base_name}_LOD{lod}"
                
                # Pre-processing for complex crater meshes
                self.preprocess_crater_for_lod(lod_obj, lod)
                
                # Apply improved decimation for crater geometry
                self.apply_crater_decimation(lod_obj, ratios[lod - 1], lod)
                
                # Post-processing cleanup
                self.cleanup_lod_mesh(lod_obj)
                
                # Add to collection if enabled
                if self.create_collection:
                    if lod_obj.name in context.scene.collection.objects:
                        context.scene.collection.objects.unlink(lod_obj)
                    new_collection.objects.link(lod_obj)
                
                # Track for joining
                all_lod_objects[lod].append(lod_obj)
                created_lods += 1
        
        # Join LOD levels if requested
        if self.join_lod_levels:
            for lod_level, lod_objects in all_lod_objects.items():
                if len(lod_objects) > 1:  # Only join if multiple objects
                    self._join_lod_objects(lod_objects, f"{base_name}_LOD{lod_level}")
        
        # Rename source objects to LOD0
        for source_obj in mesh_objects:
            if "_LOD0" not in source_obj.name:
                source_obj.name = f"{source_obj.name}_LOD0"
            
            # Add source to collection too
            if self.create_collection:
                if source_obj.name in context.scene.collection.objects:
                    context.scene.collection.objects.unlink(source_obj)
                new_collection.objects.link(source_obj)
        
        # Select remaining LOD objects (avoid invalid references)
        bpy.ops.object.select_all(action='DESELECT')
        valid_lod_objects = []
        
        for obj_name in bpy.data.objects.keys():
            if "_LOD" in obj_name and any(obj_name.startswith(f"{base_name}_LOD") for base_name in [obj.name.split("_")[0] for obj in mesh_objects]):
                obj = bpy.data.objects[obj_name]
                obj.select_set(True)
                valid_lod_objects.append(obj)
        
        self.report({'INFO'}, f"Created {created_lods} LOD objects, joined into {len(valid_lod_objects)} final LOD levels")
        return {'FINISHED'}
    
    def preprocess_crater_for_lod(self, obj, lod_level):
        """Pre-process crater mesh to improve LOD generation"""
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        
        # Remove doubles first to clean up overlapping vertices from complex generation
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles(threshold=0.001)
        
        # For higher LOD levels, simplify small details that cause decimation issues
        if lod_level >= 3:
            # Smooth out extreme surface detail that causes decimation problems
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.vertices_smooth(factor=0.2)
        
        bpy.ops.object.mode_set(mode='OBJECT')
    
    def apply_crater_decimation(self, obj, target_ratio, lod_level):
        """Apply optimized decimation for crater geometry"""
        # Use different decimation strategies based on LOD level
        if lod_level <= 2:
            # For early LODs, use collapse decimation which preserves overall shape better
            decimate = obj.modifiers.new(name="Decimate", type='DECIMATE')
            decimate.decimate_type = 'COLLAPSE'
            decimate.ratio = max(0.1, target_ratio)
            # Preserve crater rim and major features
            decimate.use_collapse_triangulate = True
        else:
            # For higher LODs, use unsubdivided decimation which is more predictable
            decimate = obj.modifiers.new(name="Decimate", type='DECIMATE')
            decimate.decimate_type = 'UNSUBDIV'
            decimate.iterations = min(3, lod_level)
            
            # Follow up with collapse if still too complex
            current_faces = len(obj.data.polygons)
            if current_faces > 200:  # Still too complex
                bpy.ops.object.modifier_apply(modifier=decimate.name)
                
                collapse_decimate = obj.modifiers.new(name="Decimate_Collapse", type='DECIMATE')
                collapse_decimate.decimate_type = 'COLLAPSE'
                collapse_decimate.ratio = min(0.3, 150 / current_faces)  # Target ~150 faces max
                bpy.ops.object.modifier_apply(modifier=collapse_decimate.name)
                return
        
        bpy.ops.object.modifier_apply(modifier=decimate.name)
    
    def cleanup_lod_mesh(self, obj):
        """Clean up LOD mesh after decimation"""
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        
        # Clean up any resulting geometry issues
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles(threshold=0.001)
        bpy.ops.mesh.delete_loose()
        bpy.ops.mesh.fill_holes(sides=10)
        
        # Recalculate normals for proper shading
        bpy.ops.mesh.normals_make_consistent(inside=False)
        
        bpy.ops.object.mode_set(mode='OBJECT')
    
    def _join_lod_objects(self, lod_objects, joined_name):
        """Join multiple LOD objects into a single object"""
        if not lod_objects:
            return
        
        # Select all objects for this LOD level
        bpy.ops.object.select_all(action='DESELECT')
        for obj in lod_objects:
            obj.select_set(True)
        
        # Set the first object as active
        bpy.context.view_layer.objects.active = lod_objects[0]
        
        # Join all selected objects
        bpy.ops.object.join()
        
        # Renamed the joined object
        joined_obj = bpy.context.active_object
        joined_obj.name = joined_name
        
        return joined_obj
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


class MESH_OT_reset_crater_settings(Operator):
    """Reset all crater settings to defaults"""
    bl_idname = "mesh.reset_crater_settings"
    bl_label = "Reset to Defaults"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        props = context.scene.crater_properties
        
        # Reset main parameters
        props.outer_radius = 2.6
        props.inner_radius = 1.3
        props.depth = 0.5
        props.rim_height = 0.58
        props.resolution = 24
        props.noise_strength = 0.05
        props.outside_noise_strength = 0.02
        props.create_materials = True
        props.auto_uv = True
        props.optimize_for_games = True
        props.close_bottom = True
        props.center_origin = False
        props.bottom_thickness = 1.0
        props.outer_wall_angle = 0.0
        props.inner_wall_angle = 0.0
        props.center_origin_z_offset = 0.0
        
        # Reset main parameters to original defaults (surface features now default to 0)
        props.outer_radius = 2.6
        props.inner_radius = 1.3
        props.depth = 0.5
        props.rim_height = 0.58
        props.resolution = 24
        props.noise_strength = 0.0
        props.outside_noise_strength = 0.0
        props.create_materials = True
        props.auto_uv = True
        props.optimize_for_games = True
        props.close_bottom = True
        props.center_origin = False
        props.bottom_thickness = 1.0
        props.outer_wall_angle = 0.0
        props.inner_wall_angle = 0.0
        props.center_origin_z_offset = 0.0
        
        # Reset explosion realism features to defaults (all 0)
        props.blast_asymmetry = 0.0
        props.edge_fragmentation = 0.0
        props.inner_asymmetry = 0.0
        props.crater_outline_irregularity = 0.0
        props.rim_edge_rounding = 0.0
        props.outer_edge_rounding = 0.0
        
        # Reset rim variation to defaults (variation = 0, scale = 3.0)
        props.rim_height_variation = 0.0
        props.rim_noise_scale = 3.0
        
        # Reset random ranges with tighter, more reasonable values
        props.random_outer_radius_min = 2.0
        props.random_outer_radius_max = 3.5
        props.random_inner_radius_min = 1.0
        props.random_inner_radius_max = 1.8
        props.random_depth_min = 0.3
        props.random_depth_max = 0.8
        props.random_rim_height_min = 0.3
        props.random_rim_height_max = 0.9
        props.random_resolution_min = 20
        props.random_resolution_max = 32
        props.random_noise_min = 0.02
        props.random_noise_max = 0.1
        props.random_outside_noise_min = 0.01
        props.random_outside_noise_max = 0.05
        
        # Reset explosion realism ranges - tighter ranges
        props.random_blast_asymmetry_min = 0.0
        props.random_blast_asymmetry_max = 0.2
        props.random_edge_fragmentation_min = 0.0
        props.random_edge_fragmentation_max = 8.0
        props.random_outline_irregularity_min = 0.0
        props.random_outline_irregularity_max = 5.0
        props.random_inner_asymmetry_min = 0.0
        props.random_inner_asymmetry_max = 0.15
        props.random_rim_variation_min = 0.0
        props.random_rim_variation_max = 0.15
        props.random_outer_edge_rounding_min = 0.0
        props.random_outer_edge_rounding_max = 0.25
        props.random_rim_edge_rounding_min = 0.0
        props.random_rim_edge_rounding_max = 0.2
        props.random_wall_angle_min = -10.0
        props.random_wall_angle_max = 10.0
        
        # Reset rim variation
        props.rim_height_variation = 0.0
        props.rim_noise_scale = 3.0
        
        self.report({'INFO'}, "Settings reset to defaults")
        return {'FINISHED'}


class VIEW3D_PT_crater_generator(Panel):
    """Main crater generator panel"""
    bl_label = "Game Crater Generator"
    bl_idname = "VIEW3D_PT_crater_generator"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Create"
    bl_context = "objectmode"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.crater_properties
        
        # Main generation buttons
        col = layout.column(align=True)
        
        # Regular crater button
        row = col.row()
        row.scale_y = 1.8
        op = row.operator(
            "mesh.add_crater", 
            text="Generate Clean Crater", 
            icon='OUTLINER_OB_META'
        )
        # Pass current property values to the operator
        op.outer_radius = props.outer_radius
        op.inner_radius = props.inner_radius
        op.depth = props.depth
        op.rim_height = props.rim_height
        op.resolution = props.resolution
        op.noise_strength = props.noise_strength
        op.outside_noise_strength = props.outside_noise_strength
        op.create_materials = props.create_materials
        op.auto_uv = props.auto_uv
        op.optimize_for_games = props.optimize_for_games
        op.close_bottom = props.close_bottom
        op.center_origin = props.center_origin
        op.bottom_thickness = props.bottom_thickness
        op.outer_wall_angle = props.outer_wall_angle
        op.inner_wall_angle = props.inner_wall_angle
        op.rim_height_variation = props.rim_height_variation
        op.rim_noise_scale = props.rim_noise_scale
        op.blast_asymmetry = props.blast_asymmetry
        op.edge_fragmentation = props.edge_fragmentation
        op.inner_asymmetry = props.inner_asymmetry
        op.crater_outline_irregularity = props.crater_outline_irregularity
        op.rim_edge_rounding = props.rim_edge_rounding
        op.outer_edge_rounding = props.outer_edge_rounding
        op.center_origin_z_offset = props.center_origin_z_offset
        
        # Random crater button
        row = col.row()
        row.scale_y = 1.5
        row.operator(
            "mesh.add_random_crater", 
            text="Random Crater", 
            icon='FILE_REFRESH'
        )
        
        # Reset button
        row = col.row()
        row.scale_y = 1.2
        row.operator(
            "mesh.reset_crater_settings",
            text="Reset to Defaults",
            icon='LOOP_BACK'
        )
        
        # Add separator
        layout.separator()
        
        # FireGeo and LOD section
        box = layout.box()
        box.label(text="Game Integration", icon='TOOL_SETTINGS')
        
        # FireGeo collision button
        col = box.column(align=True)
        row = col.row()
        row.scale_y = 1.3
        row.operator(
            "mesh.crater_create_firegeo_collision",
            text="Create FireGeo Collision",
            icon='PHYSICS'
        )
        
        # LOD creation button
        row = col.row()
        row.scale_y = 1.3
        row.operator(
            "mesh.crater_create_lods",
            text="Create LOD Levels",
            icon='MOD_DECIM'
        )
        
        # Add separator
        layout.separator()
        
        # Basic Crater Parameters
        box = layout.box()
        box.label(text="Basic Crater Dimensions", icon='MESH_CIRCLE')
        
        col = box.column(align=True)
        col.prop(props, "outer_radius")
        col.prop(props, "inner_radius")
        col.prop(props, "rim_height")
        col.prop(props, "depth")
        col.prop(props, "resolution")
        
        # Performance info
        estimated_tris = props.resolution * 4
        if estimated_tris > 800:
            box.label(text="Medium poly count", icon='INFO')
        else:
            box.label(text="Game-ready poly count", icon='CHECKMARK')
        
        # Outer Crater Controls
        box = layout.box()
        box.label(text="Outer Crater Shape", icon='MESH_UVSPHERE')
        
        col = box.column(align=True)
        col.prop(props, "blast_asymmetry")
        col.prop(props, "crater_outline_irregularity")
        col.prop(props, "outer_edge_rounding")
        col.prop(props, "outside_noise_strength")
        
        # Inner Crater Controls  
        box = layout.box()
        box.label(text="Inner Crater Shape", icon='MESH_ICOSPHERE')
        
        col = box.column(align=True)
        col.prop(props, "inner_asymmetry")
        col.prop(props, "noise_strength")
        col.prop(props, "inner_wall_angle")
        
        # Rim Controls
        box = layout.box()
        box.label(text="Crater Rim", icon='CURVE_NCIRCLE')
        
        col = box.column(align=True)
        col.prop(props, "edge_fragmentation")
        col.prop(props, "rim_edge_rounding")
        col.prop(props, "rim_height_variation")
        if props.rim_height_variation > 0:
            col.prop(props, "rim_noise_scale")
        
        # Bottom/Wall Controls
        box = layout.box()
        box.label(text="Crater Bottom & Walls", icon='MESH_CYLINDER')
        
        col = box.column(align=True)
        col.prop(props, "close_bottom")
        if props.close_bottom:
            col.prop(props, "bottom_thickness")
        col.prop(props, "outer_wall_angle")
        
        # Output Options
        box = layout.box()
        box.label(text="Output Options", icon='TOOL_SETTINGS')
        
        col = box.column(align=True)
        col.prop(props, "create_materials")
        col.prop(props, "auto_uv")
        col.prop(props, "optimize_for_games")
        col.prop(props, "center_origin")
        if props.center_origin:
            col.prop(props, "center_origin_z_offset")
        
        # Random range controls - organized by feature groups
        box = layout.box()
        box.label(text="Random Generation Ranges", icon='SETTINGS')
        
        # Basic dimensions
        sub_box = box.box()
        sub_box.label(text="Basic Dimensions", icon='MESH_CIRCLE')
        
        # Outer radius range
        row = sub_box.row(align=True)
        row.prop(props, "random_outer_radius_min", text="Outer Radius Min")
        row.prop(props, "random_outer_radius_max", text="Max")
        
        # Inner radius range
        row = sub_box.row(align=True)
        row.prop(props, "random_inner_radius_min", text="Inner Radius Min")
        row.prop(props, "random_inner_radius_max", text="Max")
        
        # Depth range  
        row = sub_box.row(align=True)
        row.prop(props, "random_depth_min", text="Depth Min")
        row.prop(props, "random_depth_max", text="Max")
        
        # Rim height range
        row = sub_box.row(align=True) 
        row.prop(props, "random_rim_height_min", text="Rim Height Min")
        row.prop(props, "random_rim_height_max", text="Max")
        
        # Resolution range
        row = sub_box.row(align=True)
        row.prop(props, "random_resolution_min", text="Resolution Min")
        row.prop(props, "random_resolution_max", text="Max")
        
        # Surface detail
        sub_box = box.box()
        sub_box.label(text="Surface Detail", icon='TEXTURE')
        
        # Inside noise range
        row = sub_box.row(align=True)
        row.prop(props, "random_noise_min", text="Inside Noise Min")
        row.prop(props, "random_noise_max", text="Max")
        
        # Outside noise range
        row = sub_box.row(align=True)
        row.prop(props, "random_outside_noise_min", text="Outside Noise Min")
        row.prop(props, "random_outside_noise_max", text="Max")
        
        # Explosion realism
        sub_box = box.box()
        sub_box.label(text="Explosion Realism", icon='FORCE_TURBULENCE')
        
        # Blast asymmetry range
        row = sub_box.row(align=True)
        row.prop(props, "random_blast_asymmetry_min", text="Blast Asymmetry Min")
        row.prop(props, "random_blast_asymmetry_max", text="Max")
        
        # Outline irregularity range
        row = sub_box.row(align=True)
        row.prop(props, "random_outline_irregularity_min", text="Outline Irregularity Min")
        row.prop(props, "random_outline_irregularity_max", text="Max")
        
        # Edge fragmentation range
        row = sub_box.row(align=True)
        row.prop(props, "random_edge_fragmentation_min", text="Edge Fragmentation Min") 
        row.prop(props, "random_edge_fragmentation_max", text="Max")
        
        # Inner asymmetry range
        row = sub_box.row(align=True)
        row.prop(props, "random_inner_asymmetry_min", text="Inner Asymmetry Min")
        row.prop(props, "random_inner_asymmetry_max", text="Max")
        
        # Rim features
        sub_box = box.box()
        sub_box.label(text="Rim Features", icon='CURVE_NCIRCLE')
        
        # Rim variation range
        row = sub_box.row(align=True)
        row.prop(props, "random_rim_variation_min", text="Rim Variation Min")
        row.prop(props, "random_rim_variation_max", text="Max")
        
        # Outer edge rounding range
        row = sub_box.row(align=True)
        row.prop(props, "random_outer_edge_rounding_min", text="Outer Edge Rounding Min")
        row.prop(props, "random_outer_edge_rounding_max", text="Max")
        
        # Rim edge rounding range
        row = sub_box.row(align=True)
        row.prop(props, "random_rim_edge_rounding_min", text="Rim Edge Rounding Min")
        row.prop(props, "random_rim_edge_rounding_max", text="Max")
        
        # Wall angles
        sub_box = box.box()
        sub_box.label(text="Wall Angles", icon='MESH_CYLINDER')
        
        # Wall angle range (shared for both inner and outer)
        row = sub_box.row(align=True)
        row.prop(props, "random_wall_angle_min", text="Wall Angle Min")
        row.prop(props, "random_wall_angle_max", text="Max")


def menu_func(self, context):
    """Add crater to the Add > Mesh menu"""
    self.layout.operator("mesh.add_crater", text="Game Crater", icon='OUTLINER_OB_META')


# Registration
classes = (
    CraterProperties,
    MESH_OT_add_crater,
    MESH_OT_add_random_crater,
    MESH_OT_crater_create_firegeo_collision,
    MESH_OT_crater_create_lods,
    MESH_OT_reset_crater_settings,
    VIEW3D_PT_crater_generator,
)

def register():
    """Register all classes"""
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.crater_properties = PointerProperty(type=CraterProperties)
    bpy.types.VIEW3D_MT_mesh_add.append(menu_func)

def unregister():
    """Unregister classes"""
    bpy.types.VIEW3D_MT_mesh_add.remove(menu_func)
    if hasattr(bpy.types.Scene, 'crater_properties'):
        del bpy.types.Scene.crater_properties
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
    print("Enhanced Game Crater Generator loaded successfully!")
    print("Access via: Add > Mesh > Game Crater")
    print("New features: FireGeo collision and LOD generation")
