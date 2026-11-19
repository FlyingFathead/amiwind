# SPDX-License-Identifier: GPL-3.0-only
"""The builder switches of a classic room map's weight (the prison ship's hold; PRISON-SHIP-POLY-COLLISION-65).

Standard library only: tools/build.py exports them before any stage runs, and the builder's own start may load no
third-party module (test_build_bootstrap_imports). The methods are tools/bsp_model_tiles.py (draw tiles),
tools/room_map_parts.py (small parts as boxes) and tools/room_map_shapes.py (listed shapes as drawn); the shell bevels are
tools/room_map_collision.py.
"""
import os

# --room-draw-tiles (AMIWIND_ROOM_DRAW_TILES): the most faces a draw tile of a room map's shell holds, 0 = off (the
# shell drawn as one model, the method before). 512 measured on the v0.0.65 hold (docs/SHIP_INTERIOR.md).
ROOM_DRAW_TILES_VARIABLE = 'AMIWIND_ROOM_DRAW_TILES'
ROOM_DRAW_TILES_DEFAULT = 512

# --room-small-parts box|off (AMIWIND_ROOM_SMALL_PARTS): the listed props' small closed parts as their boxes (box,
# the default) or as authored (off, the method before)
ROOM_SMALL_PARTS_VARIABLE = 'AMIWIND_ROOM_SMALL_PARTS'
ROOM_SMALL_PARTS_MODES = ('box', 'off')

# --room-shapes on|off (AMIWIND_ROOM_SHAPES): the listed source shapes of a room map's models drawn as the original
# draws them through the visual reduction, kept whole or as the boxes of their parts (on, the default: the prison
# ship's masts and table bands, PRISON-SHIP-FLOOR-STUCK-67) or reduced like the rest (off, the method before)
ROOM_SHAPES_VARIABLE = 'AMIWIND_ROOM_SHAPES'
ROOM_SHAPES_MODES = ('on', 'off')


def room_draw_tiles():
    """The faces per draw tile of a room map's shell: the builder option, else ROOM_DRAW_TILES_DEFAULT; 0 = off."""
    text = os.environ.get(ROOM_DRAW_TILES_VARIABLE, '').strip()
    if not text:
        return ROOM_DRAW_TILES_DEFAULT
    if not text.isdigit():
        raise ValueError('%s must be a whole number of faces (0 = off)' % ROOM_DRAW_TILES_VARIABLE)
    return int(text)


def export_room_draw_tiles(value):
    """Export the builder option --room-draw-tiles for the interior stage (None: the default)."""
    if value is None:
        os.environ.pop(ROOM_DRAW_TILES_VARIABLE, None)
    else:
        if int(value) < 0:
            raise ValueError('--room-draw-tiles must be 0 (off) or a number of faces')
        os.environ[ROOM_DRAW_TILES_VARIABLE] = str(int(value))
    return room_draw_tiles()


def room_small_parts():
    """The builder option --room-small-parts: 'box' (default) or 'off'."""
    value = os.environ.get(ROOM_SMALL_PARTS_VARIABLE, '').strip() or 'box'
    if value not in ROOM_SMALL_PARTS_MODES:
        raise ValueError('%s must be box or off' % ROOM_SMALL_PARTS_VARIABLE)
    return value


def export_room_small_parts(value):
    """Export the builder option --room-small-parts for the interior stage (None: the default)."""
    if value is None:
        os.environ.pop(ROOM_SMALL_PARTS_VARIABLE, None)
    elif value not in ROOM_SMALL_PARTS_MODES:
        raise ValueError('--room-small-parts must be box or off')
    else:
        os.environ[ROOM_SMALL_PARTS_VARIABLE] = value
    return room_small_parts()


def room_shapes():
    """The builder option --room-shapes: 'on' (default) or 'off'."""
    value = os.environ.get(ROOM_SHAPES_VARIABLE, '').strip() or 'on'
    if value not in ROOM_SHAPES_MODES:
        raise ValueError('%s must be on or off' % ROOM_SHAPES_VARIABLE)
    return value


def export_room_shapes(value):
    """Export the builder option --room-shapes for the interior stage (None: the default)."""
    if value is None:
        os.environ.pop(ROOM_SHAPES_VARIABLE, None)
    elif value not in ROOM_SHAPES_MODES:
        raise ValueError('--room-shapes must be on or off')
    else:
        os.environ[ROOM_SHAPES_VARIABLE] = value
    return room_shapes()
