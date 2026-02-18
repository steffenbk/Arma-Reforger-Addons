from .tracks import classes as _tracks_classes
from .presets import classes as _presets_classes
from .io import classes as _io_classes

classes = (
    *_tracks_classes,
    *_presets_classes,
    *_io_classes,
)
