#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The solid boxes of the game (OPENING-BARRIERS-PER-BOX-68, INVISIBLE-WALLS-NOT-BUILT-68, v0.0.68).

In the original every collision marker is solid: an MRK model whose only drawn shape is the editor marker
(tools/editor_markers.py classes it 'collision marker'), a box the player cannot walk or fly through until a script
disables it. The opening's boxes (CharGenCollision - extra) keep their own AWB1 tables (tools/prepare_character.py
barriers). Every other collision marker of the game masters is written here, as the image step's
id1/world-barriers.txt (tools/build_aga.py write_world_barriers; the engine's aw_barrier.c reads it), with the
references of the opening's boxes so a script's Disable reaches each one. For the three game files: the five lids
over Mournhold's districts, the wall at exterior cell 15,5 and the falling mage's platform.

Kept apart from tools/editor_markers.py on purpose: the CHIM world stages read that module, and only the image step
reads this one, so a change here re-keys the engine and image stages alone.
"""
import io
from pathlib import Path
import struct

from editor_markers import EditorMarkers, read_masters
from mwad.audit import string, subrecords
from mwad.esm import GAME_MASTERS
from mwad.paths import child_ci

WORLD_BARRIERS = 'world-barriers.txt'        # id1/: the solid boxes (engine aw_barrier.c world_read_file)
OPENING_BOX_ID = 'chargencollision - extra'  # the opening's boxes: tools/prepare_character.py barriers, AWB1 tables
OPENING_SHIP = 'imperial prison ship'        # its one interior box (prepare_character.SHIP_CELL)
SLAB = 0.5                                   # a plane of no thickness collides as a slab one original unit thick
KEY_STRIDE = 1 << 22                         # tools/mwscript/gamedata.py ADDON_KEY_STRIDE: an add-on's reference keys
WORLD_BOXES = 16                             # engine aw_barrier.c AW_WORLD_BOXES: the rows it holds


def collision_extents(raw, N=None):
    """(centre, half) of a model's collision shapes (the triangles under its RootCollisionNode, through the node
    transforms) in the model's own units, the box around them; None without any. A plane of no thickness keeps SLAB."""
    import numpy as np
    if N is None:
        from prepare_scenery import nif_reader
        N = nif_reader()
    data = N.Data()
    data.read(io.BytesIO(raw))
    points = []

    def walk(node, parent, inside):
        if not isinstance(node, N.NiAVObject):
            return
        world = np.array(node.get_transform().as_list()) @ parent
        inside = inside or isinstance(node, N.RootCollisionNode)
        if inside and isinstance(node, N.NiTriShape) and node.data is not None and node.data.num_vertices:
            points.append(np.array([(v.x, v.y, v.z, 1.0) for v in node.data.vertices]) @ world)
        for child in getattr(node, 'children', []):
            if child is not None:
                walk(child, world, inside)
    for root in data.roots:
        walk(root, np.eye(4), False)
    if not points:
        return None
    p = np.concatenate(points)[:, :3]
    low, high = p.min(axis=0), p.max(axis=0)
    centre, half = (low + high) / 2, (high - low) / 2
    return [float(v) for v in centre], [max(float(v), SLAB) for v in half]


def placement_axes(rotation):
    """The three axes (columns) of a placement's rotation as tools/prepare_character.py barriers turns its boxes
    (TES3 applies Z, then Y, then X to column vectors; OpenMW Misc::Convert::makeOsgQuat)."""
    import math
    import numpy as np
    rx, ry, rz = [-v for v in rotation]
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    return (np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]]) @ np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]) @
            np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]))


def reference_key(master, number, master_lists):
    """The engine's key of placement NUMBER of MASTER (as tools/mwscript/gamedata.py GameData.addon_key: the owning
    file's place in GAME_MASTERS times KEY_STRIDE plus the low bits), None when its owner is not a game master."""
    top, low = number >> 24, number & 0xFFFFFF
    if top == 0:
        owner = master
    else:
        lists = master_lists.get(master, [])
        owner = lists[top - 1] if top <= len(lists) else None
    owners = [m.casefold() for m in GAME_MASTERS]
    if owner is None or owner.casefold() not in owners or low >= KEY_STRIDE:
        return None
    return owners.index(owner.casefold()) * KEY_STRIDE + low


def master_lists(data):
    """{master: [its MAST names in order]} of the game masters present."""
    out = {}
    for name in GAME_MASTERS:
        try:
            path = child_ci(Path(data), name)
        except (FileNotFoundError, ValueError):
            continue
        if not path.is_file():
            continue
        with path.open('rb') as f:
            head = f.read(16)
            size = struct.unpack_from('<I', head, 4)[0]
            payload = f.read(size)
        out[name] = [string(d, errors='replace') for t, d in subrecords(payload) if t == 'MAST']
    return out


def collision_boxes(data, places=None):
    """(boxes, opening): every collision-marker placement of the game masters as a solid box, and the references of
    the opening's boxes in the order tools/prepare_character.py writes them (exterior, then the prison ship's).

    A box: {'key' (the engine's reference key), 'id', 'master', 'cell', 'script', 'centre' (x, y, z, the original's
    units), 'axes' (three unit columns), 'half' (x, y, z, the original's units)}, in load order. The opening's boxes
    (OPENING_BOX_ID) stay in their own tables and are left out here. A box in a district the build presents as exterior
    cells (PLACES: tools/presented_exterior.py receipt_places) is at its moved place (moved_position: x and y plus
    the district's offset). A box in any other interior is refused: the engine places these boxes outdoors only, and
    no game master has one (measured 2026-11-21)."""
    import numpy as np
    places = places or {}
    markers = EditorMarkers(data, masters=GAME_MASTERS)
    _, objects, scripts, _, cells = read_masters(data, with_cells=True)
    lists = master_lists(data)
    boxes, opening, ship, seen = [], [], [], set()
    for master, cell in cells:
        interior = bool(cell['flags'] & 1)
        name = cell.get('name') or ''
        for ref in cell['refs']:
            if ref.get('deleted'):
                continue
            ident = ref.get('id', '').casefold()
            obj = objects.get(ident)
            if obj is None or not obj['model']:
                continue
            if ident == OPENING_BOX_ID:
                if master == GAME_MASTERS[0]:
                    (ship if interior and name.casefold() == OPENING_SHIP else opening if not interior else []).append(
                        ref['number'])
                continue
            row = {'id': ref['id'], 'type': obj['type'], 'model': obj['model'],
                   'script_text': scripts.get(obj['script'], '')}
            if markers.kind(row) != 'collision marker':
                continue
            key = reference_key(master, ref['number'], lists)
            if key is None or key in seen:
                continue
            seen.add(key)
            extents = collision_extents(markers.raw(obj['model']), markers._N)
            if extents is None:
                continue
            centre, half = extents
            scale = float(ref.get('scale', 1) or 1)
            axes = placement_axes(ref['rotation_radians'])
            at = np.array(ref['position'], dtype=float) + axes @ (np.array(centre) * scale)
            if interior:
                place = places.get(name.casefold())
                if place is None:
                    raise ValueError('collision box %s (%s, %s) in the room %r: the engine places solid boxes '
                                     'outdoors only' % (ref['id'], master, ref['number'], name))
                at[0] += place['offset'][0]
                at[1] += place['offset'][1]
            boxes.append({'key': key, 'id': ref['id'], 'master': master,
                          'cell': name if interior else [cell['x'], cell['y']], 'script': obj['script'],
                          'centre': [round(float(v), 3) for v in at],
                          'axes': [[round(float(axes[k][j]), 6) for k in range(3)] for j in range(3)],
                          'half': [round(max(v * scale, SLAB), 3) for v in half]})
    return boxes, {'exterior': opening, 'ship': ship}


def world_barriers_text(boxes, opening):
    """id1/world-barriers.txt: "AWWB1", "opening N REF ..." (the rows of intro/barriers.awb in order), "ship N REF ..."
    (intro/barriers-ship.awb's), then one line a box: "box KEY CX CY CZ A0x A0y A0z A1x A1y A1z A2x A2y A2z HX HY HZ"
    in the original's units (the axes as unit columns). ASCII, at most 255 bytes a line."""
    lines = ['AWWB1', ' '.join(['opening', str(len(opening['exterior']))] + [str(r) for r in opening['exterior']]),
             ' '.join(['ship', str(len(opening['ship']))] + [str(r) for r in opening['ship']])]
    for b in boxes:
        lines.append(' '.join(['box', str(b['key'])] + ['%.3f' % v for v in b['centre']] +
                              ['%.6f' % v for axis in b['axes'] for v in axis] + ['%.3f' % v for v in b['half']]))
    if any(len(line) > 255 for line in lines):
        raise ValueError('world-barriers.txt: a line past 255 bytes')
    if len(boxes) > WORLD_BOXES:
        raise ValueError('world-barriers.txt: %d boxes, the engine holds %d (aw_barrier.c AW_WORLD_BOXES)' %
                         (len(boxes), WORLD_BOXES))
    return '\n'.join(lines) + '\n'
