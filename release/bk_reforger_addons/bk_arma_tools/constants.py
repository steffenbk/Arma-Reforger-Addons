import bpy

# ============================================================================
# HELPER — returns component/bone/socket lists based on scene mode
# ============================================================================
def get_mode(context):
    """Returns 'VEHICLE' or 'WEAPON' based on scene property."""
    return getattr(context.scene, "arvehicles_mode", "VEHICLE")

def get_bone_prefix(context):
    mode = get_mode(context)
    if mode == "WEAPON":
        return "w_"
    if mode == "CUSTOM":
        return getattr(context.scene, "arvehicles_custom_prefix", "c_")
    return "v_"

def get_component_types(context):
    return WEAPON_COMPONENT_TYPES if get_mode(context) == "WEAPON" else VEHICLE_COMPONENT_TYPES

def get_bone_types(context):
    return WEAPON_BONE_TYPES if get_mode(context) == "WEAPON" else VEHICLE_BONE_TYPES

def get_socket_types(context):
    return WEAPON_SOCKET_TYPES if get_mode(context) == "WEAPON" else VEHICLE_SOCKET_TYPES

def get_root_bones(context):
    """Returns (root_name, body_name) for armature creation."""
    mode = get_mode(context)
    if mode == "WEAPON":
        return ("w_root", None)
    if mode == "CUSTOM":
        prefix = get_bone_prefix(context)
        return (prefix + "root", None)
    return ("v_root", "v_body")


# ============================================================================
# VEHICLE TYPES
# ============================================================================
VEHICLE_SOCKET_TYPES = [
    ('window', "Window", "Vehicle window socket"),
    ('door', "Door", "Vehicle door socket"),
    ('hood', "Hood", "Vehicle hood socket"),
    ('trunk', "Trunk", "Vehicle trunk socket"),
    ('wheel', "Wheel", "Vehicle wheel socket"),
    ('light', "Light", "Vehicle light socket"),
    ('mirror', "Mirror", "Vehicle mirror socket"),
    ('antenna', "Antenna", "Vehicle antenna socket"),
    ('turret', "Turret", "Vehicle turret socket"),
    ('hatch', "Hatch", "Vehicle hatch socket"),
    ('panel', "Panel", "Vehicle panel socket"),
    ('seat', "Seat", "Vehicle seat socket"),
    ('dashboard', "Dashboard", "Vehicle dashboard socket"),
    ('steering_wheel', "Steering Wheel", "Steering wheel socket"),
    ('gear_shifter', "Gear Shifter", "Gear shifter socket"),
    ('handbrake', "Handbrake", "Handbrake socket"),
    ('pedal', "Pedal", "Vehicle pedal socket"),
    ('engine', "Engine", "Engine socket"),
    ('exhaust', "Exhaust", "Exhaust socket"),
    ('suspension', "Suspension", "Suspension socket"),
    ('rotor', "Rotor", "Helicopter rotor socket"),
    ('landing_gear', "Landing Gear", "Landing gear socket"),
    ('fuel_tank', "Fuel Tank", "Fuel tank socket"),
    ('battery', "Battery", "Battery socket"),
    ('radiator', "Radiator", "Radiator socket"),
    ('custom', "Custom", "Custom socket type"),
]

VEHICLE_COMPONENT_TYPES = [
    ('window', "Window", "Vehicle window component"),
    ('door', "Door", "Vehicle door component"),
    ('hood', "Hood", "Vehicle hood/bonnet component"),
    ('trunk', "Trunk", "Vehicle trunk/boot component"),
    ('wheel', "Wheel", "Vehicle wheel component"),
    ('light', "Light", "Vehicle light component"),
    ('mirror', "Mirror", "Vehicle mirror component"),
    ('seat', "Seat", "Vehicle seat component"),
    ('dashboard', "Dashboard", "Vehicle dashboard component"),
    ('steering_wheel', "Steering Wheel", "Steering wheel component"),
    ('gear_shifter', "Gear Shifter", "Gear shifter component"),
    ('handbrake', "Handbrake", "Handbrake component"),
    ('pedal', "Pedal", "Vehicle pedal component"),
    ('engine', "Engine", "Engine component"),
    ('exhaust', "Exhaust", "Exhaust component"),
    ('suspension', "Suspension", "Suspension component"),
    ('rotor', "Rotor", "Helicopter rotor component"),
    ('landing_gear', "Landing Gear", "Landing gear component"),
    ('fuel_tank', "Fuel Tank", "Fuel tank component"),
    ('battery', "Battery", "Battery component"),
    ('radiator', "Radiator", "Radiator component"),
    ('panel', "Panel", "Body panel component"),
    ('hatch', "Hatch", "Vehicle hatch component"),
    ('antenna', "Antenna", "Antenna component"),
    ('custom', "Custom", "Custom component type"),
]

VEHICLE_BONE_TYPES = [
    ('v_root', "Root Bone", "Main vehicle bone"),
    ('v_body', "Body", "Vehicle body bone"),
    ('v_door_left', "Door Left", "Left door bone"),
    ('v_door_right', "Door Right", "Right door bone"),
    ('v_door_rear', "Door Rear", "Rear door bone"),
    ('v_hood', "Hood", "Hood bone"),
    ('v_trunk', "Trunk", "Trunk bone"),
    ('v_wheel_1', "Wheel 1", "Wheel 1 bone"),
    ('v_wheel_2', "Wheel 2", "Wheel 2 bone"),
    ('v_wheel_3', "Wheel 3", "Wheel 3 bone"),
    ('v_wheel_4', "Wheel 4", "Wheel 4 bone"),
    ('v_wheel_5', "Wheel 5", "Wheel 5 bone"),
    ('v_wheel_6', "Wheel 6", "Wheel 6 bone"),
    ('v_steeringwheel', "Steering Wheel", "Steering wheel bone"),
    ('v_steering_wheel', "Steering Wheel Alt", "Alternative steering wheel bone"),
    ('v_turret_base', "Turret Base", "Turret base bone"),
    ('v_turret_gun', "Turret Gun", "Turret gun bone"),
    ('v_rotor', "Rotor", "Helicopter rotor bone"),
    ('v_tail_rotor', "Tail Rotor", "Tail rotor bone"),
    ('v_landing_gear', "Landing Gear", "Landing gear bone"),
    ('v_landing_gear_L', "Landing Gear L", "Left landing gear bone"),
    ('v_landing_gear_R', "Landing Gear R", "Right landing gear bone"),
    ('v_suspension1', "Suspension 1", "Suspension 1 bone"),
    ('v_suspension2', "Suspension 2", "Suspension 2 bone"),
    ('v_suspension3', "Suspension 3", "Suspension 3 bone"),
    ('v_suspension4', "Suspension 4", "Suspension 4 bone"),
    ('v_exhaust', "Exhaust", "Exhaust bone"),
    ('v_engine_inlet', "Engine Inlet", "Engine inlet bone"),
    ('v_dashboard_arm', "Dashboard Arm", "Dashboard arm bone"),
    ('v_pedal_brake', "Pedal Brake", "Brake pedal bone"),
    ('v_pedal_throttle', "Pedal Throttle", "Throttle pedal bone"),
    ('v_handbrake', "Handbrake", "Handbrake bone"),
    ('v_gearshift', "Gearshift", "Gearshift bone"),
    ('v_light_switch', "Light Switch", "Light switch bone"),
    ('v_starter_switch', "Starter Switch", "Starter switch bone"),
    ('v_cloth_cover_jiggle', "Cloth Cover", "Cloth cover jiggle bone"),
    ('v_antenna', "Antenna", "Antenna bone"),
    ('v_mirror_left', "Mirror Left", "Left mirror bone"),
    ('v_mirror_right', "Mirror Right", "Right mirror bone"),
    ('v_wiper_L', "Wiper Left", "Left wiper bone"),
    ('v_wiper_R', "Wiper Right", "Right wiper bone"),
    ('v_steps', "Steps", "Vehicle steps bone"),
    ('v_steps_piston', "Steps Piston", "Steps piston bone"),
    ('v_steps_string', "Steps String", "Steps string bone"),
    ('v_axis_shaft', "Axis Shaft", "Axis shaft bone"),
    ('v_back_door_L', "Back Door L", "Back door left bone"),
    ('v_back_door_R', "Back Door R", "Back door right bone"),
    ('v_back_door_holder_L', "Back Door Holder L", "Back door holder left bone"),
    ('v_back_door_holder_R', "Back Door Holder R", "Back door holder right bone"),
    ('v_canister', "Canister", "Canister bone"),
    ('v_dashboard_ammeter', "Dashboard Ammeter", "Dashboard ammeter bone"),
    ('v_dashboard_coolant_temp', "Dashboard Coolant", "Dashboard coolant temp bone"),
    ('v_dashboard_fuel', "Dashboard Fuel", "Dashboard fuel bone"),
    ('v_dashboard_oil_pressure', "Dashboard Oil", "Dashboard oil pressure bone"),
    ('v_dashboard_speed', "Dashboard Speed", "Dashboard speed bone"),
    ('v_water_temp_dial', "Water Temp Dial", "Water temperature dial bone"),
    ('v_transfer', "Transfer", "Transfer bone"),
    ('v_trim_vane', "Trim Vane", "Trim vane bone"),
    ('v_turret_slot', "Turret Slot", "Turret slot bone"),
    ('custom', "Custom Bone", "Add a custom bone"),
]


# ============================================================================
# WEAPON TYPES
# ============================================================================
WEAPON_SOCKET_TYPES = [
    ('slot_magazine', "Magazine Well", "Magazine attachment slot"),
    ('slot_optics', "Optics Mount", "Optics attachment slot"),
    ('slot_barrel_muzzle', "Muzzle", "Muzzle attachment slot"),
    ('slot_underbarrel', "Underbarrel", "Underbarrel attachment slot"),
    ('slot_bayonet', "Bayonet Mount", "Bayonet attachment slot"),
    ('slot_flashlight', "Flashlight", "Flashlight attachment slot"),
    ('snap_hand_right', "Hand Right", "Right hand IK target"),
    ('snap_hand_left', "Hand Left", "Left hand IK target"),
    ('eye', "Eye Point", "Aiming down sight point"),
    ('barrel_chamber', "Barrel Chamber", "Barrel chamber position"),
    ('barrel_muzzle', "Barrel Muzzle", "Barrel muzzle direction"),
    ('custom', "Custom", "Custom socket type"),
]

WEAPON_COMPONENT_TYPES = [
    ('sight', "Sight", "Sight component"),
    ('light', "Light", "Light component"),
    ('trigger', "Trigger", "Trigger component"),
    ('bolt', "Bolt", "Bolt component"),
    ('charging_handle', "Charging Handle", "Charging handle component"),
    ('mag_release', "Magazine Release", "Magazine release component"),
    ('safety', "Safety", "Safety component"),
    ('fire_mode', "Fire Mode", "Fire mode selector component"),
    ('hammer', "Hammer", "Hammer component"),
    ('striker', "Striker", "Striker component"),
    ('slide', "Slide", "Slide component"),
    ('barrel', "Barrel", "Barrel component"),
    ('buttstock', "Buttstock", "Buttstock component"),
    ('ejection_port', "Ejection Port", "Ejection port component"),
    ('bipod', "Bipod", "Bipod component"),
    ('accessory', "Accessory", "Accessory component"),
    ('custom', "Custom", "Custom component type"),
]

WEAPON_BONE_TYPES = [
    ('w_root', "Root Bone", "Main weapon bone"),
    ('w_fire_mode', "Fire Mode", "Fire selector bone"),
    ('w_ch_handle', "Charging Handle", "Charging handle bone"),
    ('w_trigger', "Trigger", "Trigger bone"),
    ('w_bolt', "Bolt", "Bolt/slide bone"),
    ('w_mag_release', "Mag Release", "Magazine release bone"),
    ('w_safety', "Safety", "Safety lever bone"),
    ('w_buttstock', "Buttstock", "Buttstock bone"),
    ('w_ejection_port', "Ejection Port", "Ejection port bone"),
    ('w_bolt_release', "Bolt Release", "Bolt release bone"),
    ('w_slide', "Slide", "Slide bone (pistols)"),
    ('w_hammer', "Hammer", "Hammer bone"),
    ('w_striker', "Striker", "Striker bone"),
    ('w_cylinder', "Cylinder", "Cylinder bone (revolvers)"),
    ('w_rear_sight', "Rear Sight", "Rear sight bone"),
    ('w_front_sight', "Front Sight", "Front sight bone"),
    ('w_barrel', "Barrel", "Barrel bone"),
    ('w_bipodleg', "Bipod Leg", "Bipod leg bone"),
    ('w_bipodleg_left', "Bipod Left", "Left bipod leg bone"),
    ('w_bipodleg_right', "Bipod Right", "Right bipod leg bone"),
    ('w_fire_hammer', "Fire Hammer", "Fire hammer bone"),
    ('w_sight', "Sight", "Sight bone"),
    ('w_sight_slider', "Sight Slider", "Sight slider bone"),
    ('custom', "Custom Bone", "Add a custom bone"),
]
