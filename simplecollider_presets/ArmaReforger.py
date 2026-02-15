import bpy

prefs = bpy.context.preferences.addons["simple_collider"].preferences

prefs.naming_position = 'PREFIX'
prefs.replace_name = False
prefs.obj_basename = 'geo'
prefs.separator = '_'
prefs.collision_string_prefix = ''
prefs.collision_string_suffix = ''
prefs.collision_digits = 2
prefs.box_shape = 'UBX'
prefs.sphere_shape = 'USP'
prefs.capsule_shape = 'UCS'
prefs.convex_shape = 'UCX'
prefs.mesh_shape = 'UTM'
prefs.rigid_body_naming_position = 'PREFIX'
prefs.rigid_body_extension = ''
prefs.rigid_body_separator = '_'
prefs.collider_groups_enabled = True
prefs.user_group_01 = 'FireGeo'
prefs.user_group_02 = 'ViewGeo'
prefs.user_group_03 = 'Geo'
prefs.user_group_01_name = 'Fire Geometry'
prefs.user_group_02_name = 'View Geometry'
prefs.user_group_03_name = 'Geometry'
prefs.use_physics_material = False
prefs.material_naming_position = 'PREFIX'
prefs.physics_material_separator = '_'
prefs.use_random_color = True
prefs.physics_material_su_prefix = ''
prefs.physics_material_name = 'MI_COL'
prefs.physics_material_filter = 'COL'
