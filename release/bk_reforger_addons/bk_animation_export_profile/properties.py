import bpy
from bpy.props import StringProperty, EnumProperty, BoolProperty, IntProperty, CollectionProperty
from bpy.types import PropertyGroup


class ARPROFILE_PG_track(PropertyGroup):
    bone_name: StringProperty(
        name="Bone Name",
        description="Name of the bone",
        default=""
    )

    parent_bone: StringProperty(
        name="Parent Bone",
        description="Parent bone name (empty for root or #movement)",
        default=""
    )

    flags: EnumProperty(
        name="Flags",
        description="Export flags for this bone",
        items=[
            ('TRA', "TRA - Translation & Rotation Absolute", "Full transform absolute (replaces underlying animation)"),
            ('TRD', "TRD - Translation & Rotation Differential", "Full transform differential/additive (adds to underlying animation)"),
            ('TRG', "TRG - Translation & Rotation Generated", "Generated bone in global space"),
            ('RA', "RA - Rotation Absolute", "Rotation only absolute (replaces underlying rotation)"),
            ('TA', "TA - Translation Absolute", "Translation only absolute"),
        ],
        default='TRD'
    )

    # Advanced functions (rarely used)
    use_bone_fn: BoolProperty(name="Use Bone Function", default=False)
    bone_fn_name: StringProperty(name="Function Name", default="")
    use_bone_fn_local: BoolProperty(name="Use Local Function", default=False)
    bone_fn_local_name: StringProperty(name="Function Name", default="")
    use_gen_fn: BoolProperty(name="Use Generator Function", default=False)
    gen_fn_name: StringProperty(name="Generator Function", default="")


class ARPROFILE_PG_settings(PropertyGroup):
    track_count: IntProperty(
        name="Track Count",
        description="Number of tracks (auto-calculated)",
        default=0,
        min=0
    )

    movement_bone: StringProperty(
        name="Movement Bone",
        description="Model base bone & movement base (EntityPosition for characters, v_root for vehicles, empty for weapons/parts)",
        default=""
    )

    default_fn: StringProperty(
        name="Default Function",
        description="Default GlobalSpace export modifier (MUST be empty for Blender! Use defaultFnMB only for MotionBuilder)",
        default="defaultFnMB"
    )

    default_local_fn: StringProperty(
        name="Default Local Function",
        description="Default LocalSpace export modifier (usually empty)",
        default=""
    )

    active_track_index: IntProperty(
        name="Active Track",
        default=0
    )

    show_advanced_functions: BoolProperty(
        name="Show Advanced Functions",
        description="Show advanced bone functions (rarely used)",
        default=False
    )

    tracks: CollectionProperty(
        type=ARPROFILE_PG_track,
        name="Tracks"
    )


classes = (
    ARPROFILE_PG_track,
    ARPROFILE_PG_settings,
)
