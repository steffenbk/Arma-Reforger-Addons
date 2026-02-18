# BK's Arma Reforger Blender Addons

A collection of Blender plugins for Arma Reforger modding, by **steffenbk**.

Requires **Blender 4.2+**

> **Important:** After installing or updating the addon, **restart Blender** before using the plugins. Some features register handlers and properties that require a fresh session to work correctly.

## Links

- YouTube: https://www.youtube.com/@steffenbk1
- If you'd like to support this work, no obligation — I'm just doing this for fun:
  [PayPal Donation](https://www.paypal.com/donate/?business=48EMTMZWYCXVN&no_recurring=0&item_name=Thanks+for+all+support%21+%3AD&currency_code=NOK)
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
| **BK Weight Gradient** | `plugins/bk_weight_gradient.py` | Apply weight gradients between anchor vertices with selectable curves |

### Standalone plugins (not included in the all-in-one install)

| Plugin | File | Description |
|--------|------|-------------|
| **BK Crater** | `plugins/bk_crater_generator.py` | Game-ready crater meshes with FireGeo collision and LODs |

### Installing individually

1. In Blender, go to **Edit > Preferences > Add-ons > Install from Disk**
2. For standalone `.py` plugins — select the file directly

---

## User Manual

### BK Arma Tools

**Location:** 3D Viewport > Sidebar > BK Arma Tools

The main rigging and asset-preparation suite. Supports two modes — **Vehicle** and **Weapon** — toggled at the top of the panel. Each mode adjusts bone prefixes and available socket types.

#### Asset Mode

- **Vehicle:** Uses `v_` prefix bones (`v_root`, `v_body`, `v_wheel_1`, etc.)
- **Weapon:** Uses `w_` prefix bones (`w_root`, `w_trigger`, `w_bolt`, etc.)

#### Mesh Tools

- **Cleanup Mesh** — Remove doubles and degenerate geometry.
- **Create LODs** — Generate decimated LOD versions (`.lod0`, `.lod1`, `.lod2`).

#### Collision Tools

- **UCX Physics Collision** — Creates a convex-hull physics collision mesh.
- **FireGeo Collision** — Detailed collision for destruction and bullet penetration.
- **Wheel Collisions** (vehicle mode) — Auto-creates cylinder collisions for each wheel.
- **Center of Mass** (vehicle mode) — Places an empty at the calculated center of mass.

#### Component Separation

- **Separate Components** — Select faces in Edit Mode, then split them into individual component objects. Optionally auto-creates sockets and FireGeo.
- **Add to Object** — Add bones or sockets to existing objects.

#### Attachment Points (Sockets)

- **Create Socket** — Adds an empty at the selected location.
  - Vehicle: 26+ types (Window, Door, Hood, Wheel, Light, Mirror, Antenna, Turret, etc.)
  - Weapon: 12 types (Magazine Well, Optics, Muzzle, Underbarrel, Bayonet, etc.)

#### Rigging

- **Create Armature** — Sets up the root bone hierarchy for your asset mode.
- **Create Bone** — Add individual bones from 50+ preset types.
- **Align Bones** — Orient bones along a specific axis.
- **Setup Skinning** — Initialize vertex groups and weights.
- **Parent to Armature** — Skin meshes with automatic weights.

#### Preset Manager

A two-phase guided workflow:

1. **Phase 1 — Bones:** Walk through a preset list adding bones one by one.
2. **Phase 2 — Sockets:** Walk through adding attachment points.

Use **Skip** to skip items you don't need, or **Reset** to start over.

#### Typical Vehicle Workflow

1. Set mode to **Vehicle** → Cleanup Mesh → Center Vehicle
2. Create Armature (`v_root`, `v_body`)
3. Add bones for wheels, doors, turrets, etc.
4. Separate components and create sockets
5. Create collisions (UCX, FireGeo, Wheel Collisions)
6. Parent meshes to armature → Create LODs → Export

#### Typical Weapon Workflow

1. Set mode to **Weapon** → Cleanup Mesh
2. Create Armature (`w_root`)
3. Add bones (trigger, bolt, safety, charging handle, etc.)
4. Add sockets (magazine well, optics rail, muzzle)
5. Create collision → Parent meshes → Export

---

### BK NLA Automation

**Location:** 3D Viewport > Sidebar > BK NLA

Automates converting source actions into NLA strips with proper Arma Reforger naming conventions.

#### Settings

- **Asset Type:** Weapon (`Pl_` prefix), Vehicle (`v_` prefix), Prop (`prop_` prefix), or Custom.
- **Asset Prefix:** Your asset designation (e.g. `M50`, `BTR`).
- **Set First as Active:** Auto-activates the first processed action.

#### Workflow

1. Select your armature and set the **Asset Type** and **Prefix**.
2. Click **Refresh Actions** to load available animations.
3. Select which actions to process (use Select All / Deselect All for bulk).
4. Click **Process NLA** — each selected action becomes an NLA strip and a new editable action is created with the proper prefix.
5. Use the **Animation Switcher** to quickly filter and swap between animations.
6. **Create New Action** to add blank actions with correct naming.

---

### BK Animation Export Profile

**Location:** 3D Viewport > Sidebar > BK Anim Export

Creates `.apr` animation export profile files for Arma Reforger.

#### Concepts

- **Tracks** are bones with export flags that define how their animation data is handled.
- **Export Flags:** TRA (absolute), TRD (differential/additive), TRG (generated), RA (rotation only), TA (translation only).

#### Workflow

1. Click **Add from Armature** or **Add from Selected** to populate tracks from your scene bones.
2. Set parent relationships for each track.
3. Assign export flags per bone (e.g. TRA for the movement bone, TRD for limb joints).
4. Configure the **Movement Bone** (`EntityPosition` for characters, `v_root` for vehicles, empty for weapons).
5. Use **Global Presets** (Weapon, Character, Vehicle, etc.) to auto-configure common setups.
6. Click **Export** and save the `.apr` file.

---

### BK Asset Exporter

**Location:** File > Export > Arma Reforger Asset (.fbx) / Sidebar > BK Exporter

FBX export tailored for the Enfusion engine.

#### Export Modes

- **Full Scene** — Export the entire scene as a single FBX.
- **Individual Parts** — Export each selected mesh as a separate FBX file.

#### Key Options

| Option | Description |
|--------|-------------|
| Apply Transforms | Bake object transforms before export |
| Preserve Armature | Keep rigging and skeletal data |
| Center to Origin | Move geometry to world center (Origin / Geometry Center / Center of Mass) |
| Alignment Axis | Orient the asset (Y-forward is Enfusion default) |
| Custom Rotation | Fine-tune rotation on X/Y/Z axes |
| Auto-Undo | Restore original positions after export |

#### Workflow

1. Prepare your scene (meshes, armature, collisions named `UTM_*`).
2. **File > Export > Arma Reforger Asset**.
3. Set export mode, alignment, and centering options.
4. Choose destination folder and export.
5. Auto-Undo restores everything — your scene stays intact.

---

### BK Building Destruction

**Location:** 3D Viewport > Sidebar > BK Buildings

Prepares destructible building models with proper component separation and socket placement.

#### Socket Types

Wall, Door, Window, Roof, Floor, Stairs, Column, Railing, Beam, Other.

#### Workflow

1. **Orient Building** — Centers and aligns the building along Y+.
2. Enter **Edit Mode** and select faces belonging to a component.
3. **Separate Component** — Splits the selection into its own object with a socket empty at its center.
4. Choose a socket type (e.g. `wall_socket`, `door_socket`).
5. **Create FireGeo** — Generate collision for the component (Convex Hull or Detailed method).
6. **Setup Collections** — Auto-organize into `Building_Components`, `Fire_Geometries`, `LODs`, `Memory_Points`.
7. **Clear Socket Parents** — Final step for Arma Reforger compatibility.

---

### BK Weapon Rig Replacer

**Location:** 3D Viewport > Sidebar > BK Rig Replacer

Swap weapon and magazine armatures while preserving all bone constraints.

#### Workflow

1. Open your scene with the existing weapon rig.
2. In the **Weapon Replacement** section, click **Browse** and select the new weapon `.blend` file.
3. Click **Replace Weapon** — all constraints (Copy Transforms, IK, etc.) are backed up and restored onto the new rig.
4. For magazines, use the **Magazine Replacement** section the same way.
5. Check **Window > Toggle System Console** for detailed operation logs.

---

### BK Selective Location Copy

**Location:** 3D Viewport > Sidebar > BK Location Copy

Copy specific location axes between objects or pose bones without affecting the other axes.

#### Workflow

1. Select the source object or bone in Pose Mode.
2. Check which axes to copy (**X**, **Y**, **Z** — any combination).
3. Click **Copy** — the values are stored and displayed in the info box.
4. Select the target object or bone.
5. Click **Paste** — only the selected axes are applied.
6. If auto-keying is enabled, a keyframe is inserted automatically.

---

### BK Weight Gradient

**Location:** 3D Viewport > Sidebar > BK Tools > Weight Gradient

Apply precise weight gradients between anchor vertices using mathematical curves.

#### Anchor System

Set 2 to 10 anchor points along your mesh. The first and last anchors define the gradient line; middle anchors become weight stops along that line.

#### Curve Types

| Curve | Effect |
|-------|--------|
| Linear | Straight-line interpolation |
| Ease In | Slow start, fast end |
| Ease Out | Fast start, slow end |
| Ease In/Out | Smooth S-curve |
| Sharp | Fast ramp then plateau |
| Custom Power | `t` raised to a custom exponent |
| Custom Curve | Full graphical curve editor with presets |

#### Workflow

1. Select your mesh and enter **Edit Mode**. Make sure you have an active **vertex group**.
2. Set the **Anchor Count** (default 2).
3. Select vertices for your first anchor, click **Set Anchor 1**.
4. Select vertices for your last anchor, click **Set Anchor N**.
5. Optionally set middle anchors with different weight values for multi-stop gradients.
6. Choose a **curve type** (Linear, Ease In, etc.).
7. Select the vertices you want to paint, then click **Apply Gradient**.

#### Saving & Loading

- **Saved Anchors** — Store and recall full anchor setups (positions, weights, vertex assignments).
- **Saved Curves** — Store custom curve shapes for reuse.
- **Saved Selections** — Store vertex selections for quick recall.

#### Custom Curve Editor

When using Custom Curve mode, click the **Curve Editor** arrow to expand the graphical editor. Use the 9 built-in presets (Linear, Ease In/Out, S-Curve, Bell, Valley, Steps, Sharp In/Out) or draw your own. In this mode the curve Y value directly equals the output weight.

---

### BK Crater Generator

**Location:** Add > Mesh > Game Crater

Generates game-ready crater meshes with realistic geometry, dual materials, collision, and LODs.

> **Note:** This is a standalone plugin, not included in the all-in-one install. Install the `.py` file directly.

#### Properties

| Property | Description | Default |
|----------|-------------|---------|
| Outer Radius | Ground-level radius | 2.6 |
| Inner Radius | Rim/lip radius | 1.3 |
| Crater Depth | How deep the crater goes | 0.5 |
| Rim Height | Elevation of the rim above ground | 0.58 |
| Noise Amount | Surface irregularity | 0.0 |

#### Workflow

1. **Add > Mesh > Game Crater**.
2. Adjust radius, depth, rim height, and noise in the operator properties panel (bottom-left).
3. The crater is generated with:
   - Dual materials (exposed earth + intact ground)
   - Optimized UV mapping
   - FireGeo collision mesh (`UTM_` prefix)
   - LOD versions (`.lod0`, `.lod1`, `.lod2`)
4. Ready to export to Arma Reforger.

---

## Other Resources

- `presets/simplecollider_presets/` — Simple Collider preset for Arma Reforger
- `guides/` — HTML reference guides for animation and export profiles

## Archive

The `archive/` folder contains older versions of plugins kept for reference.

