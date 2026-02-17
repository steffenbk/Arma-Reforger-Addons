# SPDX-License-Identifier: GPL-2.0-or-later

"""
Selective Location Copy

Simple add-on for copying specific location components (X, Y, Z) between objects/bones.
Perfect for animation editing when you only need certain axis values.
"""

bl_info = {
    "name": "BK Selective Location Copy",
    "author": "steffenbk",
    "version": (1, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > BK Location Copy",
    "category": "Animation",
    "support": 'COMMUNITY',
    "doc_url": "",
    "tracker_url": "",
}

import bpy
from bpy.types import Context, Operator, Panel, PropertyGroup
from bpy.props import BoolProperty, FloatVectorProperty, StringProperty


class SelectiveLocationCopyProperties(PropertyGroup):
    """Properties for the selective location copy tool."""
    
    # Stored location values
    stored_location: FloatVectorProperty(
        name="Stored Location",
        description="Stored location values (X, Y, Z)",
        size=3,
        default=(0.0, 0.0, 0.0)
    )
    
    # Which axes to copy
    copy_x: BoolProperty(name="X", default=True, description="Copy X location")
    copy_y: BoolProperty(name="Y", default=True, description="Copy Y location")
    copy_z: BoolProperty(name="Z", default=True, description="Copy Z location")
    
    # Info about what was stored
    stored_object_name: StringProperty(
        name="Stored Object",
        description="Name of the object/bone that was stored",
        default=""
    )
    
    # UI toggle
    show_panel: BoolProperty(
        name="Show Copy Location Tools",
        description="Show/hide the copy location tools",
        default=False
    )


class ANIM_OT_store_location(Operator):
    """Store current location values from the active object/bone"""
    bl_idname = "anim.store_location"
    bl_label = "Copy"
    bl_description = "Copy the selected location axes from the active object or pose bone"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return bool(context.active_pose_bone) or bool(context.active_object)

    def execute(self, context: Context) -> set[str]:
        props = context.scene.selective_location_copy
        
        # Get the active bone or object
        bone = context.active_pose_bone
        if bone:
            target = bone
            obj_name = f"{context.active_object.name} > {bone.name}"
        else:
            target = context.active_object
            obj_name = target.name
            
        if not target:
            self.report({'ERROR'}, "No active object or pose bone")
            return {'CANCELLED'}
        
        # Store the location values
        props.stored_location = target.location
        props.stored_object_name = obj_name
        
        # Show which axes were copied
        axes_copied = []
        if props.copy_x:
            axes_copied.append("X")
        if props.copy_y:
            axes_copied.append("Y")
        if props.copy_z:
            axes_copied.append("Z")
        
        axes_str = ", ".join(axes_copied) if axes_copied else "No axes selected"
        self.report({'INFO'}, f"Copied {axes_str} from {obj_name}")
        
        return {'FINISHED'}


class ANIM_OT_paste_location(Operator):
    """Paste selected location components to the current object/bone"""
    bl_idname = "anim.paste_location"
    bl_label = "Paste"
    bl_description = "Paste the selected location axes to the current object/bone"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        props = context.scene.selective_location_copy
        return (bool(context.active_pose_bone) or bool(context.active_object)) and props.stored_object_name != ""

    def execute(self, context: Context) -> set[str]:
        props = context.scene.selective_location_copy
        
        # Get the active bone or object
        bone = context.active_pose_bone
        if bone:
            target = bone
            obj_name = f"{context.active_object.name} > {bone.name}"
        else:
            target = context.active_object
            obj_name = target.name
            
        if not target:
            self.report({'ERROR'}, "No active object or pose bone")
            return {'CANCELLED'}
        
        # Check if any axis is selected
        if not any([props.copy_x, props.copy_y, props.copy_z]):
            self.report({'WARNING'}, "No axes selected for copying")
            return {'CANCELLED'}
        
        # Apply selective location
        current_loc = target.location.copy()
        copied_axes = []
        
        if props.copy_x:
            current_loc.x = props.stored_location[0]
            copied_axes.append("X")
        if props.copy_y:
            current_loc.y = props.stored_location[1]
            copied_axes.append("Y")
        if props.copy_z:
            current_loc.z = props.stored_location[2]
            copied_axes.append("Z")
        
        target.location = current_loc
        
        # Auto-key the changes if auto-keying is enabled
        if context.scene.tool_settings.use_keyframe_insert_auto:
            target.keyframe_insert(data_path="location")
        
        axes_str = ", ".join(copied_axes)
        self.report({'INFO'}, f"Pasted {axes_str} to {obj_name}")
        
        return {'FINISHED'}


class VIEW3D_PT_selective_location_copy(Panel):
    """Panel for the selective location copy tool."""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "BK Location Copy"
    bl_label = "Copy Location"

    def draw(self, context: Context) -> None:
        layout = self.layout
        props = context.scene.selective_location_copy
        
        # Toggle button to show/hide the panel content
        row = layout.row()
        icon = 'DOWNARROW_HLT' if props.show_panel else 'RIGHTARROW'
        row.prop(props, "show_panel", text="Copy Location Tools", icon=icon, emboss=False)
        
        if not props.show_panel:
            return
        
        # Select which axes to work with
        box = layout.box()
        box.label(text="Select Location Axes:")
        row = box.row(align=True)
        row.prop(props, "copy_x", toggle=True)
        row.prop(props, "copy_y", toggle=True)
        row.prop(props, "copy_z", toggle=True)
        
        # Copy and Paste buttons
        col = layout.column(align=True)
        col.operator("anim.store_location", text="Copy", icon='COPYDOWN')
        
        # Only show paste if we have stored data and at least one axis selected
        if props.stored_object_name != "" and any([props.copy_x, props.copy_y, props.copy_z]):
            col.operator("anim.paste_location", text="Paste", icon='PASTEDOWN')
            
            # Show what's stored and what will be pasted
            box = layout.box()
            box.label(text=f"From: {props.stored_object_name}")
            
            axes_to_copy = []
            if props.copy_x:
                axes_to_copy.append(f"X: {props.stored_location[0]:.3f}")
            if props.copy_y:
                axes_to_copy.append(f"Y: {props.stored_location[1]:.3f}")
            if props.copy_z:
                axes_to_copy.append(f"Z: {props.stored_location[2]:.3f}")
            
            box.label(text="Will paste: " + ", ".join(axes_to_copy))


# Registration
classes = (
    SelectiveLocationCopyProperties,
    ANIM_OT_store_location,
    ANIM_OT_paste_location,
    VIEW3D_PT_selective_location_copy,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.selective_location_copy = bpy.props.PointerProperty(
        type=SelectiveLocationCopyProperties
    )


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Scene.selective_location_copy


if __name__ == "__main__":
    register()