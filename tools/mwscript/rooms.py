# SPDX-License-Identifier: GPL-3.0-only
"""The rooms a script can move the player into (PositionCell, v0.0.54): each interior cell's room map name and its
recentring, from the repo's own room lists, and a position in the original's units to that room map's arrival.

The same rules the doors use (tools/room_batches.py, tools/town_interiors.py): a room a town or scene list holds keeps
its map name, every other room of config/room-batches.json has its batch map name; a recentred room has its offset
subtracted first; the arrival is the position at a quarter scale with the feet lifted, its yaw from the rotation.
"""
import json
import math


def room_table(root=None):
    """{interior cell (casefolded): {'map': name, 'offset': [x, y, z] or None}} of every room the repo's lists name;
    {} when the lists cannot be read (then PositionCell into a room stays "not yet")."""
    try:
        import room_batches
        from town_interiors import room_offsets
        listed = room_batches.listed_maps(root)
        doc = room_batches.load(root)
        offsets = room_offsets(root)
    except (ImportError, OSError, ValueError, KeyError):
        return {}
    out = {}
    for row in room_batches.rows(doc):
        key = row['room'].casefold()
        name = room_batches.build_map(row, listed)
        if name:
            out[key] = {'map': name, 'offset': offsets.get(key)}
    for key, name in listed.items():
        if name and key not in out:
            out[key] = {'map': name, 'offset': offsets.get(key)}
    return out


def table_digest(table):
    """SHA-256 of a room table: the mwscript unit's key reads what the table holds, not which files made it."""
    import hashlib
    return hashlib.sha256(json.dumps(table, sort_keys=True).encode()).hexdigest()


def arrival(position, z_degrees, offset=None):
    """(local x, y, z, yaw) in a room map for the player put at POSITION (original units) facing Z_DEGREES (the
    player's PositionCell rotation is in degrees: rule from OpenMW apps/openmw/mwscript/transformationextensions.cpp
    OpPositionCell), as a load door's arrival (room_batches.room_arrival)."""
    from room_batches import room_arrival
    point, yaw = room_arrival({'position': list(position), 'rotation_radians': [0.0, 0.0, math.radians(z_degrees)]},
                              offset=offset)
    return point[0], point[1], point[2], yaw
