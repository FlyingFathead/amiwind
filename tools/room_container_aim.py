#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Can every container in every room be aimed at? (ROOM-OBJECTS-MISSING-62)

The engine aims at a room's container by the view ray against the container's drawn placement box (aw_inventory.c
placed_target, chim_room.c ChimRoom_RayRef). This check reads a build run's own records, read-only, and for every
container row of the use table (id1/focus.awf, kind 'C') of every batch-converted room asks:

  - the room keeps a placement of that reference (its placements.json), so the engine has a box to aim at;
  - that box has a size on every axis;
  - a ray from a standing eye (EYE_HEIGHT above the box's floor) at STAND map units (2 m) from the box, toward the box
    centre, enters the box (STAND is inside the activation reach, REACH: iMaxActivateDist 192 at a quarter scale).

Units: the scenery export's positions and bounds are game units; a room map is a quarter of them (SCALE).

    python3 tools/room_container_aim.py RUN [--json]     (exit 1 when a container cannot be aimed at)
"""
import argparse
import json
import math
from pathlib import Path
import struct
import sys

SCALE = 0.25
REACH = 192 * SCALE           # the original's iMaxActivateDist (game units) in map units
STAND = 200 / 1.4 * SCALE     # 2 m: about 143 game units (1 game unit is about 1.4 cm), in map units
EYE_HEIGHT = 16.4             # the player's eye over the floor in map units (a room map's aw_eye_height)
WORK = 'chim-room-batches/scene/area-work'
FOCUS = 'image/boot/id1/focus.awf'


def focus_containers(raw):
    """{room key: [container references]} of a focus.awf (AWF1/2/3)."""
    if raw[:3] != b'AWF' or raw[3:4] not in b'123':
        raise ValueError('not a focus table')
    stride = 64 if raw[3:4] == b'1' else 96
    rooms = struct.unpack_from('<I', raw, 4)[0]
    out = {}
    for i in range(rooms):
        key, first, count = struct.unpack_from('<III', raw, 8 + 12 * i)
        base = 8 + rooms * 12 + first * stride
        refs = [struct.unpack_from('<I', raw, base + j * stride + 4)[0] for j in range(count)
                if raw[base + j * stride] == ord('C')]
        if refs:
            out[key] = refs
    return out


def ray_box(eye, direction, low, high):
    """Distance along the unit ray where it enters the box, or None."""
    near, far = 0.0, math.inf
    for k in range(3):
        if abs(direction[k]) < 1e-9:
            if not low[k] <= eye[k] <= high[k]:
                return None
            continue
        a, b = (low[k] - eye[k]) / direction[k], (high[k] - eye[k]) / direction[k]
        a, b = min(a, b), max(a, b)
        near, far = max(near, a), min(far, b)
        if near > far:
            return None
    return near


def aim_problem(bounds):
    """Why a container of these bounds (game units) cannot be aimed at, or None."""
    low = [v * SCALE for v in bounds[0]]
    high = [v * SCALE for v in bounds[1]]
    if any(h - l <= 0 for l, h in zip(low, high)):
        return 'its box has no size'
    centre = [(l + h) / 2 for l, h in zip(low, high)]
    half_x = (high[0] - low[0]) / 2
    eye = [centre[0] - half_x - STAND, centre[1], low[2] + EYE_HEIGHT]
    d = [c - e for c, e in zip(centre, eye)]
    n = math.sqrt(sum(v * v for v in d))
    hit = ray_box(eye, [v / n for v in d], low, high)
    if hit is None:
        return 'the ray toward its centre misses its box'
    # the stand is inside the reach (STAND < REACH); a tall box seen steeply from 2 m may enter a little past it, and
    # the player then steps closer, so only a miss is a problem
    return None


def room_cells(run):
    """{cell number: (room map, {reference: bounds}, kept references)} of the batch rooms (their exports)."""
    out = {}
    for work in sorted((Path(run) / WORK).iterdir()):
        index = work / 'source/scenery-index.json'
        report = work / 'conversion.json'
        if not index.is_file() or not report.is_file():
            continue
        refs = json.loads(index.read_text(encoding='utf-8'))['references']
        kept = set(json.loads((work / 'placements.json').read_text(encoding='utf-8')))
        out[work.name] = ({r['number']: r['bounds'] for r in refs if r.get('type') == 'CONT'}, kept)
    return out


def check(focus, cells, numbers):
    """(rows, problems): NUMBERS maps a room map name to its cell number (focus.awf's key)."""
    rows = problems = 0
    found = []
    for name, (boxes, kept) in sorted(cells.items()):
        key = numbers.get(name)
        if key is None:
            continue
        for ref in focus.get(key, ()):
            rows += 1
            if ref not in boxes or ref not in kept:
                why = 'no drawn placement in the room'
            else:
                why = aim_problem(boxes[ref])
            if why:
                problems += 1
                found.append({'room': name, 'reference': ref, 'why': why})
    return rows, found


def map_numbers(run):
    """{room map: cell number} from the image's room maps (worldspawn _aw_cell_int)."""
    from chim.frame_map import entities
    out = {}
    for path in sorted((Path(run) / 'image/boot/id1/maps').glob('*.chim')):
        world = entities(path.read_bytes())[0]
        if str(world.get('_aw_cell_int', '')).isdigit():
            out[path.stem] = int(world['_aw_cell_int'])
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    p.add_argument('run', type=Path)
    p.add_argument('--json', action='store_true')
    a = p.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    sys.path[:0] = [str(root / 'src'), str(root / 'tools')]
    focus = focus_containers((a.run / FOCUS).read_bytes())
    cells = room_cells(a.run)
    rows, found = check(focus, cells, map_numbers(a.run))
    if a.json:
        print(json.dumps({'rooms': len(cells), 'containers': rows, 'problems': found}, indent=1))
    else:
        print('room containers: %d rows in %d rooms, %d cannot be aimed at' % (rows, len(cells), len(found)))
        for f in found[:40]:
            print('  %(room)s %(reference)d: %(why)s' % f)
    return 1 if found else 0


if __name__ == '__main__':
    sys.exit(main())
