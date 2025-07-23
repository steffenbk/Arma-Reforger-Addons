import bpy
from bpy.props import StringProperty, BoolProperty, CollectionProperty
from bpy.types import Panel, Operator, PropertyGroup
import re

bl_info = {
    "name": "Arma Reforger NLA Automation",
    "author": "Your Name", 
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Arma Tools",
    "description": "Automate NLA strip creation and action management for Arma Reforger weapons",
    "category": "Animation",
}

def generate_new_action_name(original_name, weapon_prefix):
    if not weapon_prefix:
        return original_name + "_custom"
        
    patterns = [
        (r'^p_([^_]+)_(.+)$', 'Pl_' + weapon_prefix + '_\\2'),
        (r'^p_rfl_([^_]+)_(.+)$', 'Pl_rfl_' + weapon_prefix + '_\\2'),
    ]
    
    for pattern, replacement in patterns:
        match = re.match(pattern, original_name, re.IGNORECASE)
        if match:
            new_name = re.sub(pattern, replacement, original_name, flags=re.IGNORECASE)
            return new_name
            
    return 'Pl_' + weapon_prefix + '_' + original_name

class SwitcherActionItem(PropertyGroup):
    name: StringProperty()
    action_name: StringProperty()
    is_active: BoolProperty(default=False)
    has_fake_user: BoolProperty(default=False)

class ActionListItem(PropertyGroup):
    name: StringProperty()
    selected: BoolProperty(default=False)
    original_name: StringProperty()

class ArmaReforgerNLAProperties(PropertyGroup):
    weapon_prefix: StringProperty(
        name="Weapon Prefix",
        description="Prefix for your weapon (e.g., M50, AK74, etc.)",
        default="M50"
    )
    
    set_active_action: BoolProperty(
        name="Set First as Active",
        description="Set the first processed action as the active action",
        default=True
    )
    
    action_list: CollectionProperty(type=ActionListItem)
    action_list_index: bpy.props.IntProperty(default=0)
    
    switcher_actions: CollectionProperty(type=SwitcherActionItem)
    switcher_index: bpy.props.IntProperty(default=0)

class ARMA_OT_refresh_actions(Operator):
    bl_idname = "arma.refresh_actions"
    bl_label = "Refresh Actions"
    bl_description = "Refresh the list of available actions"
    
    def execute(self, context):
        scene = context.scene
        arma_props = scene.arma_nla_props
        
        arma_props.action_list.clear()
        
        # Get weapon prefix to filter out custom actions
        weapon_prefix = arma_props.weapon_prefix.strip()
        exclude_patterns = []
        if weapon_prefix:
            exclude_patterns = [
                f"Pl_{weapon_prefix}_",
                f"Pl_rfl_{weapon_prefix}_"
            ]
        
        for action in bpy.data.actions:
            # Skip custom weapon actions (Pl_M50_*, Pl_rfl_M50_*, etc.)
            should_skip = False
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

class ARMA_OT_filter_weapon_actions(Operator):
    bl_idname = "arma.filter_weapon_actions"
    bl_label = "Select Weapon Actions"
    bl_description = "Auto-select actions that match common weapon animation patterns"
    
    def execute(self, context):
        scene = context.scene
        arma_props = scene.arma_nla_props
        
        weapon_patterns = [
            r'p_.*_ik$',
            r'p_.*_trigger.*',
            r'p_.*_weapon_inspection.*',
            r'p_.*_erc_.*',
            r'p_.*_pne_.*',
            r'.*_reload.*',
            r'.*_fire.*',
            r'.*_bolt.*',
            r'.*_safety.*'
        ]
        
        selected_count = 0
        for item in arma_props.action_list:
            item.selected = False
            for pattern in weapon_patterns:
                if re.match(pattern, item.name, re.IGNORECASE):
                    item.selected = True
                    selected_count += 1
                    break
                    
        self.report({'INFO'}, f"Selected {selected_count} weapon-related actions")
        return {'FINISHED'}

class ARMA_OT_process_nla(Operator):
    bl_idname = "arma.process_nla"
    bl_label = "Process NLA"
    bl_description = "Convert selected actions to NLA strips and create new editable actions"
    
    def execute(self, context):
        scene = context.scene
        arma_props = scene.arma_nla_props
        
        print("DEBUG: Starting NLA processing...")
        
        armature = None
        if context.active_object and context.active_object.type == 'ARMATURE':
            armature = context.active_object
            print(f"DEBUG: Using active armature: {armature.name}")
        else:
            for obj in scene.objects:
                if obj.type == 'ARMATURE':
                    armature = obj
                    print(f"DEBUG: Found armature in scene: {armature.name}")
                    break
                    
        if not armature:
            self.report({'ERROR'}, "No armature found. Please select an armature object.")
            return {'CANCELLED'}
        
        if not armature.animation_data:
            armature.animation_data_create()
            print("DEBUG: Created animation data for armature")
            
        selected_actions = [item for item in arma_props.action_list if item.selected]
        print(f"DEBUG: Found {len(selected_actions)} selected actions")
        
        if not selected_actions:
            self.report({'ERROR'}, "No actions selected")
            return {'CANCELLED'}
        
        processed_count = 0
        skipped_count = 0
        error_count = 0
        weapon_prefix = arma_props.weapon_prefix.strip()
        
        print(f"DEBUG: Using weapon prefix: '{weapon_prefix}'")
        
        for i, item in enumerate(selected_actions):
            action_name = item.original_name
            action = bpy.data.actions.get(action_name)
            
            print(f"DEBUG: Processing {i+1}/{len(selected_actions)}: {action_name}")
            
            if not action:
                print(f"DEBUG: Action '{action_name}' not found in bpy.data.actions")
                error_count += 1
                continue
                
            try:
                new_name = generate_new_action_name(action_name, weapon_prefix)
                print(f"DEBUG: Generated new name: {new_name}")
                
                if bpy.data.actions.get(new_name):
                    print(f"DEBUG: Action '{new_name}' already exists, skipping")
                    skipped_count += 1
                    continue
                
                armature.animation_data.action = action
                print(f"DEBUG: Set original action as active: {action.name}")
                
                track_name = f"{new_name}_track"
                track = armature.animation_data.nla_tracks.new()
                track.name = track_name
                
                strip = track.strips.new(action.name, int(action.frame_range[0]), action)
                strip.name = f"ref_{action_name}"
                print(f"DEBUG: Pushed down to NLA strip: {strip.name}")
                
                armature.animation_data.action = None
                
                new_action = bpy.data.actions.new(new_name)
                new_action.use_fake_user = True
                print(f"DEBUG: Created new blank action with fake user: {new_action.name}")
                
                armature.animation_data.action = new_action
                
                for other_track in armature.animation_data.nla_tracks:
                    if other_track != track:
                        other_track.mute = True
                    else:
                        other_track.mute = False
                
                print(f"DEBUG: Set up track influence for editing")
                processed_count += 1
                
            except Exception as e:
                print(f"DEBUG: Error processing {action_name}: {str(e)}")
                import traceback
                traceback.print_exc()
                error_count += 1
                continue
        
        result_msg = f"Processed: {processed_count}, Skipped: {skipped_count}, Errors: {error_count}"
        print(f"DEBUG: {result_msg}")
        
        if processed_count > 0:
            self.report({'INFO'}, f"Success! {result_msg}. Ready to edit your new actions!")
        elif skipped_count > 0:
            self.report({'WARNING'}, f"All actions already exist. {result_msg}")
        else:
            self.report({'ERROR'}, f"No actions processed. {result_msg}")
            
        return {'FINISHED'}

class ARMA_OT_switch_animation(Operator):
    bl_idname = "arma.switch_animation"
    bl_label = "Switch Animation"
    bl_description = "Switch to the selected animation and enable its corresponding NLA track"
    bl_options = {'REGISTER', 'UNDO'}
    
    action_name: StringProperty(
        name="Action Name",
        description="Name of the action to switch to",
        default=""
    )
    
    def execute(self, context):
        scene = context.scene
        
        print(f"DEBUG: Switch animation called with action: {self.action_name}")
        
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
        
        print(f"DEBUG: Switching to animation: {self.action_name}")
        
        armature.animation_data.action = action
        
        target_track_name = f"{self.action_name}_track"
        target_track = None
        
        for track in armature.animation_data.nla_tracks:
            if track.name == target_track_name:
                target_track = track
                track.mute = False
                print(f"DEBUG: Enabled track: {track.name}")
            else:
                track.mute = True
                print(f"DEBUG: Muted track: {track.name}")
        
        if target_track:
            self.report({'INFO'}, f"Switched to: {self.action_name}")
        else:
            self.report({'WARNING'}, f"Track '{target_track_name}' not found, but action set")
            
        return {'FINISHED'}

class ARMA_OT_update_switcher(Operator):
    bl_idname = "arma.update_switcher"
    bl_label = "Update Switcher"
    bl_description = "Update the Quick Animation Switcher list"
    
    def execute(self, context):
        scene = context.scene
        arma_props = scene.arma_nla_props
        
        arma_props.switcher_actions.clear()
        
        weapon_prefix = arma_props.weapon_prefix.strip()
        
        if weapon_prefix:
            prefix_pattern = f"Pl_{weapon_prefix}_"
            
            current_action = None
            if context.active_object and context.active_object.type == 'ARMATURE':
                if context.active_object.animation_data and context.active_object.animation_data.action:
                    current_action = context.active_object.animation_data.action.name
            
            for action in sorted(bpy.data.actions, key=lambda x: x.name):
                if action.name.startswith(prefix_pattern):
                    item = arma_props.switcher_actions.add()
                    item.name = action.name
                    item.action_name = action.name
                    item.is_active = (action.name == current_action)
                    item.has_fake_user = action.use_fake_user
        
        return {'FINISHED'}

class ARMA_UL_switcher_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            # Use the full width for the animation name
            if item.is_active:
                layout.alert = True
            
            # Create switch button that takes up most of the space
            props = layout.operator("arma.switch_animation", text=item.name, icon='PLAY', emboss=False)
            props.action_name = item.action_name

class ARMA_UL_action_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.prop(item, "selected", text="")
            row.label(text=item.name, icon='ACTION')
            
            scene = context.scene
            arma_props = scene.arma_nla_props
            if arma_props.weapon_prefix and item.selected:
                new_name = generate_new_action_name(item.original_name, arma_props.weapon_prefix)
                row.label(text=f"-> {new_name}", icon='FORWARD')

class ARMA_PT_nla_panel(Panel):
    bl_label = "Arma NLA Automation"
    bl_idname = "ARMA_PT_nla_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Arma Tools"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        arma_props = scene.arma_nla_props
        
        box = layout.box()
        box.label(text="Weapon Settings", icon='TOOL_SETTINGS')
        box.prop(arma_props, "weapon_prefix")
        box.prop(arma_props, "set_active_action")
        
        box = layout.box()
        box.label(text="Action Management", icon='ACTION')
        
        row = box.row()
        row.operator("arma.refresh_actions", icon='FILE_REFRESH')
        row.operator("arma.filter_weapon_actions", icon='FILTER')
        
        row = box.row()
        row.operator("arma.select_all_actions", text="Select All", icon='CHECKBOX_HLT').select_all = True
        row.operator("arma.select_all_actions", text="Deselect All", icon='CHECKBOX_DEHLT').select_all = False
        
        if arma_props.action_list:
            box.template_list(
                "ARMA_UL_action_list", "",
                arma_props, "action_list",
                arma_props, "action_list_index",
                rows=8
            )
            
            selected_count = sum(1 for item in arma_props.action_list if item.selected)
            box.label(text=f"Selected: {selected_count}/{len(arma_props.action_list)}")
        else:
            box.label(text="Click 'Refresh Actions' to load actions")
        
        layout.separator()
        col = layout.column()
        col.scale_y = 1.5
        col.operator("arma.process_nla", icon='NLA_PUSHDOWN')
        
        layout.separator()
        box = layout.box()
        
        header_row = box.row(align=True)
        header_row.label(text="Quick Animation Switcher", icon='PLAY')
        header_row.operator("arma.update_switcher", text="", icon='FILE_REFRESH')
        
        if arma_props.switcher_actions:
            box.template_list(
                "ARMA_UL_switcher_list", "",
                arma_props, "switcher_actions",
                arma_props, "switcher_index",
                rows=10, maxrows=20
            )
            
            info_row = box.row()
            total_count = len(arma_props.switcher_actions)
            info_row.label(text=f"{total_count} animations")
        else:
            weapon_prefix = arma_props.weapon_prefix.strip()
            if weapon_prefix:
                box.label(text=f"No Pl_{weapon_prefix}_ actions found")
                box.label(text="Click refresh to load animations")
            else:
                box.label(text="Set weapon prefix above")
                
            # Show refresh button prominently when list is empty
            refresh_row = box.row()
            refresh_row.scale_y = 1.2
            refresh_row.operator("arma.update_switcher", text="Load Animations", icon='FILE_REFRESH')

classes = [
    SwitcherActionItem,
    ActionListItem,
    ArmaReforgerNLAProperties,
    ARMA_OT_refresh_actions,
    ARMA_OT_select_all_actions,
    ARMA_OT_filter_weapon_actions,
    ARMA_OT_process_nla,
    ARMA_OT_switch_animation,
    ARMA_OT_update_switcher,
    ARMA_UL_switcher_list,
    ARMA_UL_action_list,
    ARMA_PT_nla_panel,
]

def register():
    print("DEBUG: Registering Arma NLA Automation add-on...")
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
            print(f"DEBUG: Successfully registered {cls.__name__}")
        except Exception as e:
            print(f"DEBUG: Failed to register {cls.__name__}: {e}")
    
    bpy.types.Scene.arma_nla_props = bpy.props.PointerProperty(type=ArmaReforgerNLAProperties)
    print("DEBUG: Add-on registration complete")

def unregister():
    print("DEBUG: Unregistering Arma NLA Automation add-on...")
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"DEBUG: Failed to unregister {cls.__name__}: {e}")
    
    if hasattr(bpy.types.Scene, 'arma_nla_props'):
        del bpy.types.Scene.arma_nla_props

if __name__ == "__main__":
    register()