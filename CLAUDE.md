# CLAUDE.md — BK Arma Reforger Blender Addons

## Project Overview

A collection of Blender 4.2+ Python plugins for Arma Reforger modding. All plugins live in `plugins/`.

## Repository Structure

```
plugins/
  bk_arma_tools/          # Multi-file plugin (install as zip)
    __init__.py
    constants.py
    operators/            # __init__.py, armature.py, collisions.py, components.py, misc.py, presets.py, sockets.py
    ui/                   # __init__.py, panels.py
  bk_animation_export_profile.py
  bk_building_destruction.py
  bk_crater_generator.py
  bk_fbx_exporter.py
  bk_nla_automation.py
  bk_selective_location_copy.py
  bk_weapon_rig_replacer.py
  bk_weight_gradient.py
presets/                  # simplecollider_presets for Arma Reforger
guides/                   # HTML reference guides
Archive/                  # Older plugin versions (reference only)
release/                  # Release artifacts
build_zip.sh              # Builds plugins/bk_arma_tools.zip from source
```

## Build

`bk_arma_tools` must be zipped before installation in Blender:

```bash
./build_zip.sh
```

This produces `plugins/bk_arma_tools.zip`. Single-file `.py` plugins are installed directly.

## Plugin Conventions

- All plugins are standard Blender add-ons using `bpy`.
- UI panels live in the **3D Viewport Sidebar** (N-panel) unless otherwise noted.
- `bk_arma_tools` follows the pattern: `constants.py` → `operators/` → `ui/panels.py` → `__init__.py` registers everything.
- Naming conventions mirror Arma Reforger/Enfusion Engine standards:
  - Vehicle bones: `v_` prefix (`v_root`, `v_body`, `v_wheel_1`)
  - Weapon bones: `w_` prefix (`w_root`, `w_trigger`)
  - Physics collisions: `UCX_` prefix
  - FireGeo/export collisions: `UTM_` prefix
  - LOD meshes: `.lod0`, `.lod1`, `.lod2` suffixes

## Development Notes

- After any structural change to `bk_arma_tools`, rebuild the zip and reinstall in Blender.
- Blender must be **restarted** after installing or updating any plugin (handlers and properties register at startup).
- `bk_crater_generator.py` is a **standalone** plugin — not included in the all-in-one zip.
- The `.gitignore` excludes `__pycache__/` and `*.pyc` but keeps `plugins/bk_arma_tools.zip`.

## Branch / Worktree

- Main branch: `main`
- This worktree: `claude/great-lovelace`
- PRs should target `main`.
