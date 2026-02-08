import bpy
from bpy.props import StringProperty, BoolProperty, CollectionProperty, EnumProperty
from bpy.types import Panel, Operator, PropertyGroup
import re

bl_info = {
    "name": "Arma Reforger NLA Automation (Generic)",
    "author": "Your Name", 
    "version": (2, 0, 1),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > AR NLA",
    "description": "Automate NLA strip creation and action management for any Arma Reforger asset",
    "category": "Animation",
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================
def generate_new_action_name(original_name, prefix, asset_type):
    """Generate new action name based on asset type and prefix"""
    if not prefix:
        return original_name + "_custom"
    
    # Asset type specific patterns
    if asset_type == 'WEAPON':
        patterns = [
            (r'^p_([^_]+)_(.+)$', f'Pl_{prefix}_\\2'),
            (r'^p_rfl_([^_]+)_(.+)$', f'Pl_rfl_{prefix}_\\2'),
            (r'^p_pst_([^_]+)_(.+)$', f'Pl_pst_{prefix}_\\2'),
        ]
        fallback_prefix = f'Pl_{prefix}_'
    elif asset_type == 'VEHICLE':
        patterns = [
            (r'^v_([^_]+)_(.+)$', f'v_{prefix}_\\2'),
            (r'^veh_([^_]+)_(.+)$', f'veh_{prefix}_\\2'),
        ]
        fallback_prefix = f'v_{prefix}_'
    elif asset_type == 'PROP':
        patterns = [
            (r'^prop_([^_]+)_(.+)$', f'prop_{prefix}_\\2'),
            (r'^p_([^_]+)_(.+)$', f'p_{prefix}_\\2'),
        ]
        fallback_prefix = f'prop_{prefix}_'
    else:  # CUSTOM
        patterns = []
        fallback_prefix = f'{prefix}_'
    
    # Try pattern matching first
    for pattern, replacement in patterns:
        match = re.match(pattern, original_name, re.IGNORECASE)
        if match:
            new_name = re.sub(pattern, replacement, original_name, flags=re.IGNORECASE)
            return new_name
    
    # Fallback: prepend asset-specific prefix
    return f'{fallback_prefix}{original_name}'

def get_exclude_patterns(prefix, asset_type):
    """Get patterns to exclude from source action list (these are generated actions)"""
    if not prefix:
        return []
    
    if asset_type == 'WEAPON':
        return [
            f"Pl_{prefix}_",
            f"Pl_rfl_{prefix}_",
            f"Pl_pst_{prefix}_",
        ]
    elif asset_type == 'VEHICLE':
        return [
            f"v_{prefix}_",
            f"veh_{prefix}_",
        ]
    elif asset_type == 'PROP':
        return [
            f"prop_{prefix}_",
            f"p_{prefix}_",
        ]
    else:  # CUSTOM
        return [f"{prefix}_"]

def get_include_patterns(prefix, asset_type):
    """Get patterns to INCLUDE in switcher (these are the generated actions we want to show)"""
    # This is the same as exclude patterns - we want to show what we exclude from sources
    return get_exclude_patterns(prefix, asset_type)

# ============================================================================
# PROPERTY GROUPS
# ============================================================================

class SwitcherActionItem(PropertyGroup):
    name: StringProperty()
    action_name: StringProperty()
    is_active: BoolProperty(default=False)
    has_fake_user: BoolProperty(default=False)
    track_name: StringProperty(default="")

class ActionListItem(PropertyGroup):
    name: StringProperty()
    selected: BoolProperty(default=False)
    original_name: StringProperty()

class ArmaReforgerNLAProperties(PropertyGroup):
    asset_prefix: StringProperty(
        name="Asset Prefix",
        description="Prefix for your asset (e.g., M50, UAZ469, Door01)",
        default="M50"
    )
    
    asset_type: EnumProperty(
        name="Asset Type",
        description="Type of asset being worked on",
        items=[
            ('WEAPON', "Weapon", "Weapon animations (Pl_ prefix)"),
            ('VEHICLE', "Vehicle", "Vehicle animations (v_ prefix)"),
            ('PROP', "Prop", "Prop/object animations (prop_ prefix)"),
            ('CUSTOM', "Custom", "Custom prefix pattern"),
        ],
        default='WEAPON'
    )
    
    set_active_action: BoolProperty(
        name="Set First as Active",
        description="Set the first processed action as the active action",
        default=True
    )
    
    # Filter options
    show_generated: BoolProperty(
        name="Show Generated",
        description="Show generated actions in source list",
        default=False
    )
    
    # Search functionality
    search_filter: StringProperty(
        name="Search",
        description="Filter animations by name",
        default="",
        update=lambda self, context: bpy.ops.arma.update_switcher()
    )
    
    action_list: CollectionProperty(type=ActionListItem)
    action_list_index: bpy.props.IntProperty(default=0)
    
    switcher_actions: CollectionProperty(type=SwitcherActionItem)
    switcher_index: bpy.props.IntProperty(default=-1)

# ============================================================================
# OPERATORS
# ============================================================================

class ARMA_OT_refresh_actions(Operator):
    bl_idname = "arma.refresh_actions"
    bl_label = "Refresh Actions"
    bl_description = "Refresh the list of available actions"
    
    def execute(self, context):
        scene = context.scene
        arma_props = scene.arma_nla_props
        
        arma_props.action_list.clear()
        
        # Get exclusion patterns
        prefix = arma_props.asset_prefix.strip()
        exclude_patterns = get_exclude_patterns(prefix, arma_props.asset_type)
        
        for action in sorted(bpy.data.actions, key=lambda x: x.name):
            # Skip generated actions unless show_generated is enabled
            should_skip = False
            if not arma_props.show_generated:
                for pattern in exclude_patterns:
                    if action.name.startswith(pattern):
                        should_skip = True
                        break
            
            if should_skip:
                continue
                
            item = arma_props.action_list.add()
            item.name = action.name
            item.original_name = action.name
            item.selected = False
            
        self.report({'INFO'}, f"Found {len(arma_props.action_list)} source actions")
        return {'FINISHED'}

class ARMA_OT_select_all_actions(Operator):
    bl_idname = "arma.select_all_actions"
    bl_label = "Select All"
    bl_description = "Select or deselect all actions"
    
    select_all: BoolProperty(default=True)
    
    def execute(self, context):
        scene = context.scene
        arma_props = scene.arma_nla_props
        
        for item in arma_props.action_list:
            item.selected = self.select_all
            
        action_word = "Selected" if self.select_all else "Deselected"
        self.report({'INFO'}, f"{action_word} all actions")
        return {'FINISHED'}

class ARMA_OT_process_nla(Operator):
    bl_idname = "arma.process_nla"
    bl_label = "Process NLA"
    bl_description = "Convert selected actions to NLA strips and create new editable actions"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        arma_props = scene.arma_nla_props
        
        armature = None
        if context.active_object and context.active_object.type == 'ARMATURE':
            armature = context.active_object
        else:
            for obj in scene.objects:
                if obj.type == 'ARMATURE':
                    armature = obj
                    break
                    
        if not armature:
            self.report({'ERROR'}, "No armature found. Please select an armature object.")
            return {'CANCELLED'}
        
        if not armature.animation_data:
            armature.animation_data_create()
            
        selected_actions = [item for item in arma_props.action_list if item.selected]
        
        if not selected_actions:
            self.report({'ERROR'}, "No actions selected")
            return {'CANCELLED'}
        
        processed_count = 0
        skipped_count = 0
        error_count = 0
        prefix = arma_props.asset_prefix.strip()
        asset_type = arma_props.asset_type
        
        for i, item in enumerate(selected_actions):
            action_name = item.original_name
            action = bpy.data.actions.get(action_name)
            
            if not action:
                error_count += 1
                continue
                
            try:
                new_name = generate_new_action_name(action_name, prefix, asset_type)
                
                if bpy.data.actions.get(new_name):
                    skipped_count += 1
                    continue
                
                # Push down to NLA
                armature.animation_data.action = action
                
                track_name = f"{new_name}_track"
                track = armature.animation_data.nla_tracks.new()
                track.name = track_name
                
                strip = track.strips.new(action.name, int(action.frame_range[0]), action)
                strip.name = f"ref_{action_name}"
                strip.blend_type = 'COMBINE'
                
                armature.animation_data.action = None
                
                # Create new editable action
                new_action = bpy.data.actions.new(new_name)
                new_action.use_fake_user = True
                
                armature.animation_data.action = new_action
                
                # Mute other tracks
                for other_track in armature.animation_data.nla_tracks:
                    if other_track != track:
                        other_track.mute = True
                    else:
                        other_track.mute = False
                
                processed_count += 1
                
            except Exception as e:
                print(f"Error processing {action_name}: {str(e)}")
                error_count += 1
                continue
        
        result_msg = f"Processed: {processed_count}, Skipped: {skipped_count}, Errors: {error_count}"
        
        if processed_count > 0:
            self.report({'INFO'}, f"Success! {result_msg}")
        elif skipped_count > 0:
            self.report({'WARNING'}, f"All actions already exist. {result_msg}")
        else:
            self.report({'ERROR'}, f"No actions processed. {result_msg}")
        
        # Auto-refresh switcher
        bpy.ops.arma.update_switcher()
            
        return {'FINISHED'}

class ARMA_OT_switch_animation(Operator):
    bl_idname = "arma.switch_animation"
    bl_label = "Switch Animation"
    bl_description = "Switch to the selected animation and enable its corresponding NLA track"
    bl_options = {'REGISTER', 'UNDO'}
    
    action_name: StringProperty(default="")
    
    def execute(self, context):
        scene = context.scene
        
        armature = None
        if context.active_object and context.active_object.type == 'ARMATURE':
            armature = context.active_object
        else:
            for obj in scene.objects:
                if obj.type == 'ARMATURE':
                    armature = obj
                    break
                    
        if not armature or not armature.animation_data:
            self.report({'ERROR'}, "No armature with animation data found")
            return {'CANCELLED'}
        
        action = bpy.data.actions.get(self.action_name)
        if not action:
            self.report({'ERROR'}, f"Action '{self.action_name}' not found")
            return {'CANCELLED'}
        
        # Set active action
        armature.animation_data.action = action
        
        # Find and select the corresponding track
        target_track_name = f"{self.action_name}_track"
        target_track = None
        
        for track in armature.animation_data.nla_tracks:
            if track.name == target_track_name:
                target_track = track
                track.mute = False
                # Select this track in NLA editor
                track.select = True
            else:
                track.mute = True
                # Deselect other tracks
                track.select = False
        
        # Set the target track as active (this makes it highlighted in NLA editor)
        if target_track:
            armature.animation_data.nla_tracks.active = target_track
        
        # Update switcher to refresh highlighting
        bpy.ops.arma.update_switcher()
        
        self.report({'INFO'}, f"Switched to: {self.action_name}")
        return {'FINISHED'}
    

class ARMA_OT_create_new_action(Operator):
    bl_idname = "arma.create_new_action"
    bl_label = "Create New Action"
    bl_description = "Create a new blank action with NLA track and fake user"
    bl_options = {'REGISTER', 'UNDO'}
    
    action_name: StringProperty(
        name="Action Name",
        description="Name for the new action (prefix will be added automatically)",
        default="new_animation"
    )
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        arma_props = context.scene.arma_nla_props
        
        layout.prop(self, "action_name")
        
        # Preview the full name
        if arma_props.asset_prefix:
            prefix = arma_props.asset_prefix.strip()
            asset_type = arma_props.asset_type
            
            if asset_type == 'WEAPON':
                full_name = f"Pl_{prefix}_{self.action_name}"
            elif asset_type == 'VEHICLE':
                full_name = f"v_{prefix}_{self.action_name}"
            elif asset_type == 'PROP':
                full_name = f"prop_{prefix}_{self.action_name}"
            else:  # CUSTOM
                full_name = f"{prefix}_{self.action_name}"
            
            box = layout.box()
            box.label(text="Will create:", icon='INFO')
            box.label(text=full_name)
    
    def execute(self, context):
        scene = context.scene
        arma_props = scene.arma_nla_props
        
        # Find armature
        armature = None
        if context.active_object and context.active_object.type == 'ARMATURE':
            armature = context.active_object
        else:
            for obj in scene.objects:
                if obj.type == 'ARMATURE':
                    armature = obj
                    break
        
        if not armature:
            self.report({'ERROR'}, "No armature found. Please select an armature object.")
            return {'CANCELLED'}
        
        if not armature.animation_data:
            armature.animation_data_create()
        
        # Generate full action name with prefix
        prefix = arma_props.asset_prefix.strip()
        asset_type = arma_props.asset_type
        
        if not prefix:
            self.report({'ERROR'}, "Please set an asset prefix first")
            return {'CANCELLED'}
        
        if asset_type == 'WEAPON':
            full_name = f"Pl_{prefix}_{self.action_name}"
        elif asset_type == 'VEHICLE':
            full_name = f"v_{prefix}_{self.action_name}"
        elif asset_type == 'PROP':
            full_name = f"prop_{prefix}_{self.action_name}"
        else:  # CUSTOM
            full_name = f"{prefix}_{self.action_name}"
        
        # Check if action already exists
        if bpy.data.actions.get(full_name):
            self.report({'ERROR'}, f"Action '{full_name}' already exists")
            return {'CANCELLED'}
        
        # Create new blank action
        new_action = bpy.data.actions.new(full_name)
        new_action.use_fake_user = True
        
        # Create NLA track
        track_name = f"{full_name}_track"
        track = armature.animation_data.nla_tracks.new()
        track.name = track_name
        
        # Set as active action
        armature.animation_data.action = new_action
        
        # Mute other tracks, select only this track
        for other_track in armature.animation_data.nla_tracks:
            if other_track == track:
                other_track.mute = False
                other_track.select = True
            else:
                other_track.mute = True
                other_track.select = False
        
        # Set as active track
        armature.animation_data.nla_tracks.active = track
        
        # Refresh switcher
        bpy.ops.arma.update_switcher()
        
        self.report({'INFO'}, f"Created: {full_name}")
        return {'FINISHED'}


class ARMA_OT_update_switcher(Operator):
    bl_idname = "arma.update_switcher"
    bl_label = "Update Switcher"
    bl_description = "Update the Quick Animation Switcher list"
    
    def execute(self, context):
        scene = context.scene
        arma_props = scene.arma_nla_props
        
        arma_props.switcher_actions.clear()
        
        prefix = arma_props.asset_prefix.strip()
        asset_type = arma_props.asset_type
        search_term = arma_props.search_filter.lower()
        
        if not prefix:
            return {'FINISHED'}
        
        # Get patterns to INCLUDE (these are the generated actions we want to show)
        include_patterns = get_include_patterns(prefix, asset_type)
        
        current_action = None
        if context.active_object and context.active_object.type == 'ARMATURE':
            if context.active_object.animation_data and context.active_object.animation_data.action:
                current_action = context.active_object.animation_data.action.name
        
        for action in sorted(bpy.data.actions, key=lambda x: x.name):
            # Check if action matches our patterns (generated actions)
            matches = False
            for pattern in include_patterns:
                if action.name.startswith(pattern):
                    matches = True
                    break
            
            if not matches:
                continue
            
            # Apply search filter
            if search_term and search_term not in action.name.lower():
                continue
            
            item = arma_props.switcher_actions.add()
            item.name = action.name
            item.action_name = action.name
            item.is_active = (action.name == current_action)
            item.has_fake_user = action.use_fake_user
            item.track_name = f"{action.name}_track"
        
        return {'FINISHED'}

class ARMA_OT_clear_search(Operator):
    bl_idname = "arma.clear_search"
    bl_label = "Clear Search"
    bl_description = "Clear the search filter"
    
    def execute(self, context):
        context.scene.arma_nla_props.search_filter = ""
        return {'FINISHED'}

# ============================================================================
# UI LISTS
# ============================================================================

class ARMA_UL_switcher_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            if item.is_active:
                layout.alert = True
                icon = 'RADIOBUT_ON'
            else:
                icon = 'RADIOBUT_OFF'
            
            # Switch button with icon indicating active state
            props = layout.operator("arma.switch_animation", text=item.name, icon=icon, emboss=False)
            props.action_name = item.action_name

class ARMA_UL_action_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.prop(item, "selected", text="")
            row.label(text=item.name, icon='ACTION')
            
            scene = context.scene
            arma_props = scene.arma_nla_props
            if arma_props.asset_prefix and item.selected:
                new_name = generate_new_action_name(
                    item.original_name, 
                    arma_props.asset_prefix,
                    arma_props.asset_type
                )
                row.label(text=f"→ {new_name}", icon='FORWARD')

# ============================================================================
# PANELS
# ============================================================================

class ARMA_PT_nla_panel(Panel):
    bl_label = "Arma NLA Automation"
    bl_idname = "ARMA_PT_nla_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "AR NLA"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        arma_props = scene.arma_nla_props
        
        # Asset Settings
        box = layout.box()
        box.label(text="Asset Settings", icon='SETTINGS')
        
        box.prop(arma_props, "asset_type", text="Type")
        box.prop(arma_props, "asset_prefix", text="Prefix")
        box.prop(arma_props, "set_active_action")
        
        # Action Management
        box = layout.box()
        box.label(text="Source Actions", icon='ACTION')
        
        row = box.row(align=True)
        row.operator("arma.refresh_actions", icon='FILE_REFRESH')
        row.prop(arma_props, "show_generated", text="", icon='FILTER', toggle=True)
        
        row = box.row(align=True)
        row.operator("arma.select_all_actions", text="All", icon='CHECKBOX_HLT').select_all = True
        row.operator("arma.select_all_actions", text="None", icon='CHECKBOX_DEHLT').select_all = False
        
        if arma_props.action_list:
            box.template_list(
                "ARMA_UL_action_list", "",
                arma_props, "action_list",
                arma_props, "action_list_index",
                rows=6
            )
            
            selected_count = sum(1 for item in arma_props.action_list if item.selected)
            box.label(text=f"Selected: {selected_count}/{len(arma_props.action_list)}", icon='INFO')
        else:
            box.label(text="Click 'Refresh' to load actions")
        
        # Process Button
        layout.separator()
        col = layout.column()
        col.scale_y = 1.5
        col.operator("arma.process_nla", icon='NLA_PUSHDOWN')
        
        # Animation Switcher
        layout.separator()
        box = layout.box()
        
        header_row = box.row(align=True)
        header_row.label(text="Animation Switcher", icon='PLAY')
        header_row.operator("arma.update_switcher", text="", icon='FILE_REFRESH')
        
        # Search bar
        search_row = box.row(align=True)
        search_row.prop(arma_props, "search_filter", text="", icon='VIEWZOOM')
        if arma_props.search_filter:
            search_row.operator("arma.clear_search", text="", icon='X')
        
        if arma_props.switcher_actions:
            box.template_list(
                "ARMA_UL_switcher_list", "",
                arma_props, "switcher_actions",
                arma_props, "switcher_index",
                rows=8, maxrows=20
            )
            
            total_count = len(arma_props.switcher_actions)
            box.label(text=f"{total_count} animations", icon='INFO')
        else:
            if arma_props.asset_prefix:
                patterns = get_include_patterns(arma_props.asset_prefix, arma_props.asset_type)
                if patterns:
                    box.label(text=f"No {patterns[0]}* actions found")
                box.label(text="Process actions first")
            else:
                box.label(text="Set asset prefix above")
            
            refresh_row = box.row()
            refresh_row.scale_y = 1.2
            refresh_row.operator("arma.update_switcher", text="Load", icon='FILE_REFRESH')
# Utilities
        layout.separator()
        box = layout.box()
        box.label(text="Utilities", icon='TOOL_SETTINGS')
        box.operator("arma.create_new_action", text="Create New Action", icon='ADD')

# ============================================================================
# REGISTRATION
# ============================================================================

classes = [
    SwitcherActionItem,
    ActionListItem,
    ArmaReforgerNLAProperties,
    ARMA_OT_refresh_actions,
    ARMA_OT_select_all_actions,
    ARMA_OT_process_nla,
    ARMA_OT_switch_animation,
    ARMA_OT_update_switcher,
    ARMA_OT_clear_search,
    ARMA_OT_create_new_action,  # <- ADD THIS
    ARMA_UL_switcher_list,
    ARMA_UL_action_list,
    ARMA_PT_nla_panel,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.arma_nla_props = bpy.props.PointerProperty(type=ArmaReforgerNLAProperties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    if hasattr(bpy.types.Scene, 'arma_nla_props'):
        del bpy.types.Scene.arma_nla_props

if __name__ == "__main__":
    register()
