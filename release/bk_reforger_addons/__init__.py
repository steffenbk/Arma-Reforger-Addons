bl_info = {
    "name": "BK Reforger Addons",
    "author": "steffenbk",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "description": "All-in-one Arma Reforger Blender tools by steffenbk",
    "category": "Object",
}

submodules = [
    "bk_nla_automation",
    "bk_animation_export_profile",
    "bk_weapon_rig_replacer",
    "bk_building_destruction",
    "bk_fbx_exporter",
    "bk_selective_location_copy",
    "bk_arma_tools",
]

_loaded = []

def register():
    import importlib
    for name in submodules:
        mod = importlib.import_module(f".{name}", package=__name__)
        importlib.reload(mod)
        if hasattr(mod, "register"):
            mod.register()
        _loaded.append(mod)

def unregister():
    for mod in reversed(_loaded):
        if hasattr(mod, "unregister"):
            mod.unregister()
    _loaded.clear()
