# BK's Arma Reforger Blender Addons

A collection of Blender plugins for Arma Reforger modding, by **steffenbk**.

Requires **Blender 4.2+**

## All-in-One Install

Download the latest **[bk_reforger_addons.zip from Releases](https://github.com/steffenbk/bk-reforger-blender-addons/releases/latest)** to get every plugin in a single install. In Blender, go to **Edit > Preferences > Add-ons > Install from Disk** and select the zip.

### Toggle Plugins On/Off

You can enable or disable individual plugins from the addon preferences. Go to **Edit > Preferences > Add-ons**, find **BK Reforger Addons**, and expand it to see the toggle options.

![Addon Preferences](https://i.imgur.com/TeOPsmo.png)

## Plugins

### Individual plugins (if you only want specific ones)

| Plugin | File | Description |
|--------|------|-------------|
| **BK Arma Tools** | `plugins/bk_arma_tools/` | Vehicle and weapon rigging, collisions, sockets, LODs, presets — **install as zip** (see below) |
| **BK NLA Automation** | `plugins/bk_nla_automation.py` | Automate NLA strip creation and action management |
| **BK Animation Export Profile** | `plugins/bk_animation_export_profile.py` | Create and manage `.apr` animation export profiles |
| **BK Weapon Rig Replacer** | `plugins/bk_weapon_rig_replacer.py` | Replace weapons/magazines while preserving constraints |
| **BK Building Destruction** | `plugins/bk_building_destruction.py` | Tools for preparing destructible buildings |
| **BK Asset Exporter** | `plugins/bk_fbx_exporter.py` | FBX export tailored for Enfusion Engine |
| **BK Selective Location Copy** | `plugins/bk_selective_location_copy.py` | Copy specific X/Y/Z location components between objects or bones |

### Standalone plugins (not included in the all-in-one install)

| Plugin | File | Description |
|--------|------|-------------|
| **BK Crater** | `plugins/bk_crater_generator.py` | Game-ready crater meshes with FireGeo collision and LODs |

### Installing individually

1. In Blender, go to **Edit > Preferences > Add-ons > Install from Disk**
2. For standalone `.py` plugins — select the file directly

## Other Resources

- `presets/simplecollider_presets/` — Simple Collider preset for Arma Reforger
- `guides/` — HTML reference guides for animation and export profiles

## Archive

The `archive/` folder contains older versions of plugins kept for reference.

## Links

- YouTube: https://www.youtube.com/@steffenbk1
- If you'd like to support this work, no obligation — I'm just doing this for fun:
  [PayPal Donation](https://www.paypal.com/donate/?business=48EMTMZWYCXVN&no_recurring=0&item_name=Thanks+for+all+support%21+%3AD&currency_code=NOK)
