bl_info = {
    "name": "BK Reforger Addons",
    "author": "steffenbk",
    "version": (1, 1, 0),
    "blender": (4, 2, 0),
    "description": "All-in-one Arma Reforger Blender tools by steffenbk",
    "category": "Object",
}

import bpy
import importlib
from bpy.props import BoolProperty
from bpy.types import AddonPreferences

# Map of module name -> (display name, default enabled)
_submodule_info = {
    "bk_arma_tools":              ("BK Arma Tools",              True),
    "bk_nla_automation":          ("BK NLA Automation",          True),
    "bk_animation_export_profile":("BK Animation Export Profile", True),
    "bk_weapon_rig_replacer":     ("BK Weapon Rig Replacer",     True),
    "bk_building_destruction":    ("BK Building Destruction",     True),
    "bk_fbx_exporter":            ("BK Asset Exporter",          True),
    "bk_selective_location_copy": ("BK Selective Location Copy",  True),
}

_modules = {}   # name -> module
_active = set() # currently registered module names


def _import_module(name):
    if name not in _modules:
        _modules[name] = importlib.import_module(f".{name}", package=__name__)
    else:
        _modules[name] = importlib.reload(_modules[name])
    return _modules[name]


def _enable_module(name):
    if name in _active:
        return
    mod = _import_module(name)
    if hasattr(mod, "register"):
        mod.register()
    _active.add(name)


def _disable_module(name):
    if name not in _active:
        return
    mod = _modules.get(name)
    if mod and hasattr(mod, "unregister"):
        mod.unregister()
    _active.discard(name)


def _make_update(mod_name):
    def update(self, context):
        if getattr(self, mod_name):
            _enable_module(mod_name)
        else:
            _disable_module(mod_name)
    return update


class BKReforgerPreferences(AddonPreferences):
    bl_idname = __package__

    bk_arma_tools: BoolProperty(
        name="BK Arma Tools",
        default=True,
        update=_make_update("bk_arma_tools"),
    )
    bk_nla_automation: BoolProperty(
        name="BK NLA Automation",
        default=True,
        update=_make_update("bk_nla_automation"),
    )
    bk_animation_export_profile: BoolProperty(
        name="BK Animation Export Profile",
        default=True,
        update=_make_update("bk_animation_export_profile"),
    )
    bk_weapon_rig_replacer: BoolProperty(
        name="BK Weapon Rig Replacer",
        default=True,
        update=_make_update("bk_weapon_rig_replacer"),
    )
    bk_building_destruction: BoolProperty(
        name="BK Building Destruction",
        default=True,
        update=_make_update("bk_building_destruction"),
    )
    bk_fbx_exporter: BoolProperty(
        name="BK Asset Exporter",
        default=True,
        update=_make_update("bk_fbx_exporter"),
    )
    bk_selective_location_copy: BoolProperty(
        name="BK Selective Location Copy",
        default=True,
        update=_make_update("bk_selective_location_copy"),
    )

    def draw(self, context):
        layout = self.layout
        layout.label(text="Toggle individual plugins on or off:")
        for name, (label, _) in _submodule_info.items():
            row = layout.row()
            row.prop(self, name, text=label)


def register():
    bpy.utils.register_class(BKReforgerPreferences)

    prefs = bpy.context.preferences.addons.get(__package__)
    for name, (_, default) in _submodule_info.items():
        enabled = default
        if prefs and hasattr(prefs.preferences, name):
            enabled = getattr(prefs.preferences, name)
        if enabled:
            _enable_module(name)


def unregister():
    for name in list(_active):
        _disable_module(name)
    bpy.utils.unregister_class(BKReforgerPreferences)
    _modules.clear()
