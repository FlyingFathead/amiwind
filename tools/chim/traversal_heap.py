# SPDX-License-Identifier: GPL-3.0-only
"""The traversal memory check: every frame of every CHIM store, every room, and every crossing between them, on the
32 MB minimum of Fast RAM, before the image step does any slow work (SOL-SEA-CROSSING-68,
IMAGE-FRAME-HEAP-LAYER-STORES-UNCHECKED-68).

The image step's per-map heap gate (tools/chim/heap.py frame_map_heap) runs late and read only the base world's frame
maps; Solstheim's (store chimsol) and Mournhold's (store chimmh) were checked by their own stage's ring gate against
the 16 MB budget, without their own store index at 32 MB. This check reads, in seconds, what every world stage and the
rooms stage already measured:

- each store's frames: the stage's heap gate (chim-heap.json: the gated ring of each frame) with THAT store's own
  index (chim/world.cwi: a 28-byte row per file and 24 bytes per model and texture, as the image gate counts it) and the
  frame's chunk index and loading buffer, by the image gate's own 32 MB rule (heap.zone_32mb);
- each room: the rooms stage's early heap gate (chim-interiors/chim-room-heap-early.json: headroom_32mb_bytes);
- each traversal, with what the engine holds at that moment. A traversal changes the map: the area left behind is
  freed and the new one loaded (AREA-CHANGE-MEMORY-64), so its peak is the larger of the two ends plus what is kept
  across (KEPT). The kinds:
  * store-edge: two neighbouring frames of different stores (the open sea between Vvardenfell and Solstheim: a level
    change, CHIM-STORE-ONE-AT-A-TIME-64);
  * door: a room and the frame its exterior door stands in (interior to exterior and back);
  * arrival: a teleport or travel arrival (the boat, dbg tp) is a map change into one frame or room: every frame and
    room is its own arrival, so every endpoint above is checked.

An overflow fails the image step at once, naming the place (store and cell, room, face or door). The report:
image/traversal-memory.json.
"""
import json
import struct
from pathlib import Path

FORMAT = 'aw-traversal-memory-1'
FRAME_HEADER_BYTES = 64          # the common header (32) and the frame block (32) of a frame.ccf
# What the engine keeps across each traversal, in the CHIM zone and the cache bank, with where that is decided. A
# change of store drops the index and every model and texture kept (chim_world.c Chim_StoreSelect: IndexDrop,
# ChimZone_EvictKind); a door between a room (its room store) and a frame (its world store) is such a change; an
# arrival is a map change whose area left behind is freed (AREA-CHANGE-MEMORY-64). The Fast RAM a town may still hold
# outside the Hunk at a room load (ROOM-LOAD-KEEPS-EXTERIOR-CACHE-64, about 3 MB after Balmora, holder not yet named)
# is counted by the rooms stage's own gate from the measured free Fast RAM, not here.
KEPT = {'store-edge': 0, 'door': 0, 'arrival': 0}
KEPT_SOURCE = {'store-edge': 'chim_world.c Chim_StoreSelect: a change of store drops the index, models and textures',
               'door': 'a room and a frame are in different stores: the same drop at the map change',
               'arrival': 'a map change: the area left behind is freed (AREA-CHANGE-MEMORY-64)'}
SIDES = ((1, 0), (-1, 0), (0, 1), (0, -1))


def index_counts(world_dir):
    """(files, models, textures) of a store's index (chim/world.cwi): its table of contents only."""
    from chim import format as F
    with (Path(world_dir) / 'chim' / 'world.cwi').open('rb') as stream:
        raw = stream.read(F.HEADER.size + F.SETTINGS.size + F.INDEX_TOC.size)
    if F.HEADER.unpack_from(raw)[1] != b'INDX':
        raise ValueError('%s: not a CHIM index' % world_dir)
    v = F.INDEX_TOC.unpack_from(raw, F.HEADER.size + F.SETTINGS.size)
    return v[1], v[3], v[6]


def frame_block(world_dir, rel):
    """{nx, ny, owned_total} of a frame file (its header and frame block only)."""
    from chim import format as F
    with (Path(world_dir) / 'chim' / rel).open('rb') as stream:
        raw = stream.read(FRAME_HEADER_BYTES)
    if F.HEADER.unpack_from(raw)[1] != b'FRAM':
        raise ValueError('%s: not a CHIM frame file' % rel)
    v = F.FRAME_BLOCK.unpack_from(raw, F.HEADER.size)
    return {'nx': v[7], 'ny': v[8], 'owned_total': v[10]}


def cell_of(rel):
    """(x, y) of a frame path 'frames/x-07/y+04[/gG]/frame.ccf'."""
    parts = [p for p in rel.split('/') if p[:1] in 'xy' and p[1:2] in '+-']
    return int(parts[0][1:]), int(parts[1][1:])


def store_needs(store, world_dir, memory=None, buffer_bytes=None):
    """{(x, y): row} of every frame of a store: its 32 MB need and budget from its stage's heap gate and its own
    index (heap.nonring_zone_users, heap.zone_32mb), 'fits'."""
    from chim import heap as H
    report = json.loads((Path(world_dir) / 'chim-heap.json').read_text(encoding='utf-8'))
    files, models, textures = index_counts(world_dir)
    out = {}
    for fr in report.get('frames') or []:
        rel = fr['frame']
        frame = frame_block(world_dir, rel)
        gated = fr['peak_bytes'] if fr.get('gated_ring', 'active') == 'active' else fr['load_ring']['peak_bytes']
        users = H.nonring_zone_users(files, models, textures, frame, frame['nx'] * frame['ny'], 0, {},
                                     buffer_bytes=buffer_bytes)
        z = H.zone_32mb(fr, users, gated, memory)
        out[cell_of(rel)] = {'store': store, 'frame': rel, 'need': z['need_32mb_bytes'], 'budget': fr['budget_bytes'],
                             'headroom': z['headroom_32mb_bytes'], 'fits': z['fits_32mb_engine'],
                             'store_index': users['store_index']}
    return out


def room_needs(early_report):
    """{room map: row} from the rooms stage's early heap gate: need and headroom at 32 MB, 'fits'."""
    report = json.loads(Path(early_report).read_text(encoding='utf-8'))
    out = {}
    for name, r in (report.get('rooms') or {}).items():
        head = r.get('headroom_32mb_bytes')
        out[name] = {'need': r.get('need_bytes'), 'headroom': head, 'fits': head is None or head >= 0}
    return out


def store_edges(frames):
    """[((x, y), (x, y))]: neighbouring cells whose frames are in different stores (each face once)."""
    out = []
    for cell, row in sorted(frames.items()):
        for dx, dy in SIDES[::2]:
            other = (cell[0] + dx, cell[1] + dy)
            if other in frames and frames[other]['store'] != row['store']:
                out.append((cell, other))
    return out


def exterior_doors(master):
    """[((x, y), room name)]: every live exterior door of the merged master that leads into a room (DNAM)."""
    from mwad.audit import records, subrecords, cell_data
    out = set()
    for tag, flags, payload in records(master):
        if tag != 'CELL' or flags & 0x20:
            continue
        d = cell_data(list(subrecords(payload)))
        if d['flags'] & 1:
            continue
        for ref in d['refs']:
            if ref.get('destination_cell') and not ref.get('deleted'):
                out.add(((d['x'], d['y']), ref['destination_cell']))
    return sorted(out)


def check(stores, rooms=None, doors=(), room_maps=None, memory=None):
    """The report and [problem] of every frame of STORES ({store: world dir}), every room (ROOMS: the early room
    report's path), every store edge and every door (DOORS: [((x, y), room name)], ROOM_MAPS: {room name: room map})."""
    frames, problems = {}, []
    per_store = {}
    for store, world_dir in stores.items():
        rows = store_needs(store, world_dir, memory)
        per_store[store] = {'frames': len(rows), 'store_index': next(iter(rows.values()))['store_index'] if rows else 0,
                            'worst_headroom': min((r['headroom'] for r in rows.values()), default=None)}
        for cell, row in rows.items():
            if cell in frames:
                problems.append('cell %d,%d has a frame in store %s and in store %s' % (cell + (frames[cell]['store'],
                                                                                         store)))
            frames[cell] = row
            if not row['fits']:
                problems.append('frame %s of store %s (cell %d,%d) needs %d bytes at 32 MB, %d over its budget'
                                % (row['frame'], store, cell[0], cell[1], row['need'], -row['headroom']))
    room_rows = room_needs(rooms) if rooms and Path(rooms).is_file() else {}
    for name, row in sorted(room_rows.items()):
        if not row['fits']:
            problems.append('room %s needs %d bytes at 32 MB, %d over' % (name, row['need'] or 0, -row['headroom']))
    edges = []
    for a, b in store_edges(frames):
        peak = max(frames[a]['need'] - frames[a]['budget'], frames[b]['need'] - frames[b]['budget']) + KEPT['store-edge']
        edges.append({'from': list(a), 'to': list(b), 'stores': [frames[a]['store'], frames[b]['store']],
                      'over_budget_bytes': peak})
        if peak > 0:
            problems.append('store edge %d,%d (%s) | %d,%d (%s): %d bytes over at 32 MB'
                            % (a + (frames[a]['store'],) + b + (frames[b]['store'], peak)))
    door_rows, unmatched = [], 0
    for cell, room in doors:
        rmap = (room_maps or {}).get(room)
        if cell not in frames or rmap not in room_rows:
            unmatched += 1
            continue
        fr, rr = frames[cell], room_rows[rmap]
        over = max(fr['need'] - fr['budget'], -(rr['headroom'] if rr['headroom'] is not None else 0)) + KEPT['door']
        door_rows.append({'cell': list(cell), 'room': room, 'map': rmap, 'store': fr['store'], 'over_budget_bytes': over})
        if over > 0:
            problems.append('door %d,%d (%s) <-> room %s (%s): %d bytes over at 32 MB'
                            % (cell + (fr['store'], room, rmap, over)))
    worst = sorted(door_rows, key=lambda r: -r['over_budget_bytes'])[:5]
    report = {'format': FORMAT, 'ok': not problems, 'kept': KEPT, 'kept_source': KEPT_SOURCE, 'stores': per_store,
              'frames': len(frames), 'rooms': len(room_rows), 'store_edges': edges,
              'doors': {'checked': len(door_rows), 'not_matched': unmatched, 'worst': worst},
              'arrivals': 'every frame and room above is its own arrival (a map change frees the area left behind)',
              'problems': problems}
    return report, problems


def run(out, chim_world=None, layer_worlds=(), chim_interiors=None, room_batches=None, data_files=None, log=print):
    """The image step's early check: OUT/traversal-memory.json; a ValueError naming every overflow. LAYER_WORLDS: the
    image's --chim-layer-world values (STORE=WORLD); the stores of rooms (no frames) are left to the room report."""
    from chim.layer_stores import parse, store_kinds
    stores = {}
    if chim_world and (Path(chim_world) / 'chim-heap.json').is_file():
        stores['chim'] = Path(chim_world)
    kinds = store_kinds()
    for store, world in parse(layer_worlds or ()):
        if kinds.get(store) == 'frames' and (Path(world) / 'chim-heap.json').is_file():
            stores[store] = Path(world)
    if not stores:
        return None
    rooms = Path(chim_interiors) / 'chim-room-heap-early.json' if chim_interiors else None
    doors, room_maps = (), {}
    if data_files and room_batches and (Path(room_batches) / 'room-batches.json').is_file():
        from mwad.masters import master_path
        doors = exterior_doors(master_path(Path(data_files)).read_bytes())
        batches = json.loads((Path(room_batches) / 'room-batches.json').read_text(encoding='utf-8'))
        room_maps = {r['room']: r['map'] for r in batches.get('rooms') or [] if r.get('made')}
    report, problems = check(stores, rooms, doors, room_maps)
    Path(out, 'traversal-memory.json').write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8', newline='\n')
    log('Image: traversal memory at 32 MB: %d frames in %d stores (%s), %d rooms, %d store edges, %d doors: %s'
        % (report['frames'], len(stores), ', '.join('%s %d, index %d B, worst headroom %s B'
                                                    % (s, v['frames'], v['store_index'], v['worst_headroom'])
                                                    for s, v in report['stores'].items()),
           report['rooms'], len(report['store_edges']), report['doors']['checked'],
           'ok' if not problems else '%d over' % len(problems)))
    if problems:
        raise ValueError('The traversal memory check at 32 MB failed before the image step did its work (%d): %s'
                         % (len(problems), '; '.join(problems[:12])))
    return report
