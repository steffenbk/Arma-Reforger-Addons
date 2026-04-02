# Shared constants for BK Building Tools

# Default socket names for different building parts
BUILDING_SOCKET_NAMES = {
    "wall": "SOCKET_building_wall",
    "door": "SOCKET_building_door",
    "window": "SOCKET_building_window",
    "roof": "SOCKET_building_roof",
    "floor": "SOCKET_building_floor",
    "stairs": "SOCKET_building_stairs",
    "column": "SOCKET_building_column",
    "railing": "SOCKET_building_railing",
    "beam": "SOCKET_building_beam",
    "other": "SOCKET_building_part"
}

# Building part types for separation and socket creation
BUILDING_PART_TYPES = [
    ('wall', "Wall", "Wall component"),
    ('door', "Door", "Door component"),
    ('window', "Window", "Window component"),
    ('roof', "Roof", "Roof component"),
    ('floor', "Floor", "Floor component"),
    ('stairs', "Stairs", "Stairs component"),
    ('column', "Column", "Column or support beam"),
    ('railing', "Railing", "Railing component"),
    ('beam', "Beam", "Structural beam"),
    ('other', "Other", "Other component type"),
]

# Piece removal pattern strategies for destruction phases
# Each pattern is a callable description; actual logic lives in the operator
REMOVAL_PATTERNS = {
    "outside_in": {
        "label": "Outside-In",
        "description": "Remove outermost pieces first (edges, corners), leaving center intact longest",
    },
    "random_scatter": {
        "label": "Random Scatter",
        "description": "Remove random pieces each phase for natural-looking damage",
    },
    "top_down": {
        "label": "Top-Down",
        "description": "Remove pieces from top first (roof collapse pattern)",
    },
    "bottom_up": {
        "label": "Bottom-Up",
        "description": "Remove pieces from bottom first (foundation crumble)",
    },
    "impact_point": {
        "label": "Impact Point",
        "description": "Remove pieces radiating outward from cursor/selected point",
    },
}

# Subfolder names for exported building parts
BUILDING_PART_TYPE_FOLDERS = {
    "wall": "Walls",
    "door": "Doors",
    "window": "Windows",
    "roof": "Roof",
    "floor": "Floors",
    "stairs": "Stairs",
    "column": "Columns",
    "railing": "Railings",
    "beam": "Beams",
    "other": "Parts",
}
