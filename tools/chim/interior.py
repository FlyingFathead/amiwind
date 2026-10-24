# SPDX-License-Identifier: GPL-3.0-only
"""CHIM rooms: every converted interior on one shared interior store (docs/chim/INTERIOR_STORE.md).

EXPERIMENTAL (v0.0.48 line). A room is its own record, not a frame of a world: its models (store ids) and its
placements (world format 0.8 placed records, three angles, the light level in the flags' high byte, world format
0.12). Every mesh model (one per mesh and scale, the tilt applied at run time) and every texture is stored once in
the interior store, chimi/, an index of the exterior world's layout with no frames.

A room is made from the room the builder converts today (prepare_area.build_room): its own scenery export (the
placements, profiles and meshes) and its compiled room map (which placements it holds), so a CHIM room places the
same meshes at the same spots with the same profiles and collision rules. Its light is one level per placement, from
the same light function that bakes today's rooms (interior_lighting.point_light), sampled at the placement.

    python3 tools/chim/interior.py --room-work DIR [--room-work DIR ...] --palette PALETTE --out OUT
        [--qbsp QBSP] [--unit-cache DIR] [--jobs N]

writes OUT/chimi/world.cwi, its packs (OUT/chimi/pNN.ccs), the room records (OUT/chimi/rooms/<room>.crm) and
OUT/chim-rooms-receipt.json. Nothing derived from your files is part of this repository.
"""
import argparse
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import format as F  # noqa: E402
from chim import placed as P  # noqa: E402  (registers world format 0.8)
from map_files import ROOM_KEY  # noqa: E402

STORE = 'chimi'
ROOM_KIND = b'ROOM'
ROOM_BLOCK = struct.Struct('>6fII')          # bounds mins, maxs; model count; 0
# World format 0.12: the placement light level in the high byte of a placed record's flags.
FORMAT_VERSION = (0, 12)
FLAGS_AT = 46                                # the flags' offset in a placed record (chim.format.PLACEMENT)
PACK_BYTES = 64 << 20                        # a pack is closed past this size (classic FFS: files well under 1 GiB)
if FORMAT_VERSION not in F.READ_VERSIONS:
    F.READ_VERSIONS = F.READ_VERSIONS + (FORMAT_VERSION,)
if ROOM_KIND not in F.KINDS:
    F.KINDS = F.KINDS + (ROOM_KIND,)
SCALE = 0.25


def _log(msg):
    print('[chim rooms] ' + msg, flush=True)


def light_level(value):
    """A light value (interior_lighting.point_light: 0..255 before clamping) as a stored level: 1 to 255 (0 means
    'no level' in the record, so a dark placement keeps level 1, the darkest)."""
    return max(1, min(255, int(round(value))))


def with_light(record, level):
    """A placed record with its light level in the flags' high byte (bits 0 and 1 kept)."""
    if not 0 <= level <= 255:
        raise ValueError('Light level %r outside 0..255' % level)
    flags = struct.unpack_from('>H', record, FLAGS_AT)[0]
    if flags & 0xFF00:
        raise ValueError('Placed record flags already use the high byte')
    out = bytearray(record)
    struct.pack_into('>H', out, FLAGS_AT, flags | (level << 8))
    return bytes(out)


def room_record(bounds, model_ids, records):
    """chimi/rooms/<room>.crm: header (kind ROOM, count = placements), room block, model list, placed records."""
    block = ROOM_BLOCK.pack(*bounds[0], *bounds[1], len(model_ids), 0)
    models = struct.pack('>%dI' % len(model_ids), *model_ids)
    body = block + models + b''.join(records)
    total = F.HEADER.size + len(body)
    # the directory field points at the model list, the data field at the placements (engine chim/chim_room.c)
    models_at = F.HEADER.size + ROOM_BLOCK.size
    return F.header(ROOM_KIND, len(records), models_at, models_at + len(models), total, FORMAT_VERSION) + body


def read_room_record(data):
    head = F.read_header(data, ROOM_KIND)
    v = ROOM_BLOCK.unpack_from(data, F.HEADER.size)
    n = v[6]
    if head['directory'] != F.HEADER.size + ROOM_BLOCK.size or head['data'] != head['directory'] + 4 * n:
        raise ValueError('Room record offsets do not match its model list')
    models = list(struct.unpack_from('>%dI' % n, data, head['directory']))
    at = head['data']
    if at + head['count'] * P.PLACEMENT.size != len(data):
        raise ValueError('Room record size does not match its placements')
    records = [P.read_placement(data, at + i * P.PLACEMENT.size) for i in range(head['count'])]
    for i, r in enumerate(records):
        r['light'] = struct.unpack_from('>H', data, at + i * P.PLACEMENT.size + FLAGS_AT)[0] >> 8
    return {'bounds': (v[0:3], v[3:6]), 'models': models, 'placements': records}


def installed_room(map_path):
    """The room record of an installed CHIM room map (maps/<room>.chim beside <store>/rooms/<room>.crm in the same
    id1), read: {'bounds', 'models', 'placements'} plus 'store' (the store folder) and 'room'; None for a map that is
    not a CHIM room. Raises ValueError when the room map names a record the image does not hold."""
    from map_files import room_record, room_record_path
    map_path = Path(map_path)
    found = room_record(map_path)
    if found is None:
        return None
    path = room_record_path(map_path.parent.parent, map_path)
    if not path.is_file():
        raise ValueError('CHIM room map %s names %s/rooms/%s.crm, which the image does not hold'
                         % (map_path.name, found[0], found[1]))
    return dict(read_room_record(path.read_bytes()), store=found[0], room=found[1])


def installed_room_refs(map_path):
    """Reference numbers a CHIM room map places: its entities' aw_ref (residents, activated objects, sounds) and its
    room record's placements (the placed meshes the room map no longer carries as entities); empty for another map.
    The image checks that count placements by map read both (IMAGE-ROOM-MAPS-LATE-PASSES-48)."""
    from chim.cut import source_ref
    room = installed_room(map_path)
    return set() if room is None else {source_ref(p['ref']) for p in room['placements']}


def store_model_images(id1, store, ids):
    """{model id: brush image bytes} of the store models IDS, read from id1/<store>/world.cwi and only the pack files
    that hold them (the whole store is never read for one room)."""
    root = Path(id1) / store
    _, files, models, _ = F.read_index((root / 'world.cwi').read_bytes())
    packs, out = {}, {}
    for i in sorted(set(ids)):
        if not 0 <= i < len(models):
            raise ValueError('%s: model %d is not in the store (%d models)' % (store, i, len(models)))
        m = models[i]
        path = files[m['file']]['path']
        if path not in packs:
            packs[path] = (root / path).read_bytes()
        data = packs[path][m['offset']:m['offset'] + m['bytes']]
        if len(data) != m['bytes']:
            raise ValueError('%s: model %d runs past its pack %s' % (store, i, path))
        out[i] = data
    return out


def room_placements(room_map):
    """aw_ref numbers of the placed meshes a room map holds (func_wall with an inline model)."""
    from chim.frame_map import entities
    out = set()
    for e in entities(Path(room_map).read_bytes()):
        if e.get('classname') == 'func_wall' and e.get('model', '').startswith('*') and e.get('aw_ref', '').isdigit():
            out.add(int(e['aw_ref']))
    return out


PLACEMENTS_FILE = 'placements.json'      # a batch room's kept placements (tools/chim_room_batches.py)
SHELL_KEY = '_chim_room_shell'          # worldspawn key of a shell room map: it holds no placed mesh


def kept_placements(work):
    """aw_ref numbers of the placements a room keeps: a batch room's placements.json (its room map is a shell with no
    placed mesh: tools/chim_room_batches.py), else the placed meshes of its compiled room map."""
    work = Path(work)
    if (work / PLACEMENTS_FILE).is_file():
        return set(json.loads((work / PLACEMENTS_FILE).read_text(encoding='utf-8')))
    return room_placements(work / 'room.bsp')


def room_harvest_numbers(harvest, data_files):
    """Reference numbers of the interior placements the harvest step makes harvestable (harvest_build.prepare: every
    representable interior small mushroom; none with --interiors off). A CHIM room leaves them out of its record and
    the image places each as its harvest entity from the room's catalogue (harvest_build.install chim_room_rows), as
    the CHIM world does outdoors (chim.build.harvest_numbers; CHIM-ROOM-HARVEST-DOUBLE-48)."""
    from harvest_build import interior, source_placements
    return {r['number'] for r in source_placements(harvest, data_files)[2] if interior(r)}


def room_selection(room, references, wanted, harvest=None):
    """(every kept placement, the placements the record holds, the harvest plants left out or None) of one room: the
    scenery export's references the room keeps (`wanted`, kept_placements), less those in `harvest` (reference
    numbers, room_harvest_numbers; None: none left out, the earlier form). A kept placement missing from the export,
    or a room left with nothing to place, is a ValueError naming the room."""
    every = [r for r in references if r['number'] in wanted]
    missing = set(wanted) - {r['number'] for r in every}
    if missing:
        raise ValueError('%s: %d placements of the room map are not in its scenery export (%s)'
                         % (room, len(missing), ', '.join(map(str, sorted(missing)[:5]))))
    if harvest is None:
        return every, every, None
    left_out = sorted(set(wanted) & set(harvest))
    selected = [r for r in every if r['number'] not in set(left_out)]
    if not selected:
        raise ValueError('%s: every placement of the room is a harvestable plant; the room has nothing to place' % room)
    return every, selected, left_out


def room_input(work, pal_bytes, qbsp, jobs, cache, timer, collision_cache, harvest=None):
    """One room's models, textures and placements (chim.build.frame_input with no ground), its light levels and
    bounds, from the room's own scenery export and compiled map (prepare_area.build_room's work folder).

    harvest: reference numbers the harvest step makes harvestable (room_harvest_numbers); the room's own are left out
    of its placements (returned as 'harvest_left_out', the image places them as harvest entities) and still count
    for its bounds, so the room's box is the same either way. None: every kept placement is placed (the earlier
    form: a harvestable plant stays a placed mesh, drawn and solid, not pickable)."""
    import numpy as np
    from chim.build import frame_input, mesh_fingerprint, mesh_unit
    from chim.units import run_units
    from interior_lighting import point_light
    from prepare_mesh_bsp import rock_profile
    from surface_flatten import load_profiles, mount_references
    from visual_offsets import apply_visual_offsets
    work = Path(work)
    index = json.loads((work / 'source/scenery-index.json').read_text())
    archive = work / 'source/scenery.mwpak'
    every, selected, left_out = room_selection(work.name, index['references'], kept_placements(work), harvest)
    # profiles exactly as prepare_mesh_bsp._append_meshes chooses them for a room
    profiles = {name: profile for group in index.get('groups', {}).values()
                for name, profile in group.get('visual_profiles', {}).items()}
    flatten = load_profiles(scene_kind='interior')
    used = sorted({r['model_index'] for r in selected})
    for mi in used:
        model = index['models'][mi]
        profiles.setdefault(model['source'], rock_profile(model['source'], model['triangles']))
        if model['source'] in flatten:
            profiles[model['source']] = {**profiles[model['source']], 'flatten': flatten[model['source']]}
    models = list(index['models'])
    items = []
    for mi in used:
        model = models[mi]
        profile = profiles[model['source']]
        model['_profile'] = profile
        items.append((mesh_fingerprint(model, profile, index['textures']), (mi, model, profile, archive, index['textures'])))
    with timer.section('meshes'):
        prepared = dict(zip(used, run_units('mesh', items, mesh_unit, jobs, cache)))
    from chim.build import mesh_result_keys
    mesh_fps = mesh_result_keys(items, prepared, used)
    centre = [0.0, 0.0]
    mount_references(index, selected, prepared, centre, SCALE)
    apply_visual_offsets(index, selected)
    # the left-out harvest plants count too: the room's box (its closed edge) is the same with or without them
    boxes = np.array([b for r in every for b in r['bounds']], dtype=float) * SCALE
    lo, hi = boxes.min(axis=0), boxes.max(axis=0)
    grain = 256.0
    low = [float(np.floor(lo[i] / grain) * grain) for i in range(2)]
    span = [float(np.ceil((hi[i] - low[i]) / grain) * grain) or grain for i in range(2)]
    frame = {'cell': (0, 0), 'centre': tuple(centre), 'low': tuple(low), 'span': tuple(span)}
    spec = frame_input(frame=frame, centre=centre, models=models, references=selected, prepared=prepared,
                       profiles=profiles, mesh_fps=mesh_fps, texture_records=index['textures'], archive=archive,
                       palette=pal_bytes, heights=None, materials=None, step=grain, floor=0.0, ceiling=0.0,
                       ground_textures={}, qbsp=qbsp, collision_cache=collision_cache, jobs=jobs,
                       cache=cache, timer=timer, settings={'placement_format': '0.8'}, mesh_occluders=False,
                       terrain_on=False)
    lighting = index.get('lighting') or {}
    by_number = {r['number']: r for r in selected}
    levels = {}
    from chim.cut import source_ref
    for p in spec['placements']:
        # a tile of a model over the image budget has its own number; its light is its source placement's
        ref = by_number[source_ref(p['ref'])]
        centre_point = np.mean(np.array(ref['bounds'], dtype=float), axis=0) * SCALE
        levels[p['ref']] = light_level(point_light(centre_point, lighting)) if lighting else 0
    out = {'room': work.name, 'spec': spec, 'levels': levels,
           'bounds': (tuple(float(v) for v in lo), tuple(float(v) for v in hi)),
           'cell': index.get('cell'), 'fallbacks': spec['fallbacks']}
    if left_out is not None:
        # the record's coordinates are quarter-scale original ones less the frame centre: the harvest catalogue's
        # map origin (harvest_build: map position = quarter-scale original position - origin)
        out['harvest_left_out'] = left_out
        out['harvest_origin'] = [float(centre[0]), float(centre[1]), 0.0]
    return out


EDGE_MARGIN = 64.0         # the closed edge stands this far outside the room's placements (today's void box: 32 + 8)
WALL = 64.0                # its thickness
ORIGIN_TOLERANCE = 0.01    # a room map's placement and the room record's: the same origin (chim.frame_map origin_check)


LIQUID_TOLERANCE = 0.01   # a liquid brush of room.map and the conversion's record: the same height
WATER_TEXTURE = '*water'
MAP_FACE = re.compile(r'^\s*\(([^)]*)\)\s*\(([^)]*)\)\s*\(([^)]*)\)\s*(\S+)')


def map_brushes(text):
    """The world brushes of a room map's source (room.map, prepare_quake.brush): [(textures, points)] with the set of
    face textures and every face point as (x, y, z)."""
    out, depth, faces = [], 0, None
    for line in text.splitlines():
        s = line.strip()
        if s == '{':
            depth += 1
            if depth == 2:
                faces = []
        elif s == '}':
            if depth == 2:
                out.append(({t for t, _ in faces}, [p for _, ps in faces for p in ps]))
                faces = None
            depth -= 1
            if depth == 0 and out:
                break                       # the worldspawn alone: its brushes are the world
        elif depth == 2 and faces is not None:
            m = MAP_FACE.match(s)
            if m:
                faces.append((m.group(4), [tuple(float(v) for v in m.group(k).split()) for k in (1, 2, 3)]))
    return out


def room_liquids(work):
    """(liquids, why) of a converted room: liquids None when it has none, else {'water': the water level or None,
    'lava': [{'hull': counter-clockwise [[x, y], ...], 'top': z}]} in the room map's units, taken from the brushes
    its room map compiles (room.map: the "*water" brush, one "*lava" prism per pool, tools/lava.pool_brushes) and
    checked against its conversion record (water_height x SCALE, the pools' tops). why: the reason a room with
    liquids cannot be a CHIM room yet (None when it can)."""
    import lava
    work = Path(work)
    conversion = json.loads((work / 'conversion.json').read_text())
    height = conversion.get('water_height')
    pools = (conversion.get('lava') or {}).get('pools') or []
    if height is None and not pools:
        return None, None
    brushes = map_brushes((work / 'room.map').read_text(encoding='cp1252'))
    water = None
    if height is not None:
        level = float(height) * SCALE
        tops = [max(p[2] for p in pts) for textures, pts in brushes if textures == {WATER_TEXTURE}]
        if len(tops) != 1 or abs(tops[0] - level) > LIQUID_TOLERANCE:
            return None, 'water: the room map has %d water brushes, none at the water height %.3f' % (len(tops), level)
        water = level
    prisms = []
    for textures, pts in brushes:
        if textures == {lava.TEXTURE}:
            top = max(p[2] for p in pts)
            hull = lava.convex_hull_2d([(p[0], p[1]) for p in pts if abs(p[2] - top) <= LIQUID_TOLERANCE])
            prisms.append({'hull': hull, 'top': round(top, 3)})
    beds = sum(1 for textures, _ in brushes if textures == {lava.BED_TEXTURE})
    # the record keeps a pool's top to 2 decimals (tools/lava.map_parts), the brush to 3: compared unrounded, so a top
    # such as -66.555 (record -66.55, brush -66.555) is the same height (CHIM-ROOM-LAVA-TOP-ROUNDING-48)
    want = sorted(float(p['top']) for p in pools)
    have = sorted(p['top'] for p in prisms)
    if len(have) != len(want) or beds != len(want) or any(abs(a - b) > LIQUID_TOLERANCE for a, b in zip(have, want)):
        return None, ('lava: the room map has %d lava and %d bed brushes for %d pools (tops %s, records %s)'
                      % (len(have), beds, len(want), have[:4], want[:4]))
    if any(len(p['hull']) < 3 for p in prisms):
        return None, 'lava: a pool brush without a plan polygon'
    # a pool whose bed reaches under the water level is carved into the water too (liquid_world: the lava wins inside
    # its prism, CHIM-ROOM-LAVA-UNDER-WATER-48); before, such a room kept its room map
    return {'water': water, 'lava': prisms}, None


def unsupported(work):
    """Why a room cannot be a CHIM room yet (None when it can). Water and lava come over as the CHIM room map's
    liquids (room_liquids, liquid_world); a room whose liquid brushes do not match its record, or with lava under its
    water, keeps its room map."""
    return room_liquids(work)[1]


def miptex_named(room_bsp_data, names):
    """{name: miptex bytes} of the named textures in a compiled map's texture lump (the room map's own "*water" and
    "*lava", made from the room's wad)."""
    lump = F.read_brush_image(room_bsp_data)[2]
    out = {}
    if len(lump) < 4:
        return out
    n = struct.unpack_from('<i', lump)[0]
    for o in struct.unpack_from('<%di' % n, lump, 4):
        if o < 0:
            continue
        name = lump[o:o + 16].split(b'\0')[0].decode('ascii', 'replace')
        w, h = struct.unpack_from('<II', lump, o + 16)
        if name in names and name not in out:
            out[name] = bytes(lump[o:o + 40 + w * h * 85 // 64])
    return out


def liquid_world(lo, hi, liquids, miptex):
    """The 15 lumps of a CHIM room map's world with the room's liquids, written directly as the exterior chunks write
    theirs (chim.terrain: water plane and lava cells, docs/chim/WORLD_FORMAT.md "Terrain of a chunk"), no qbsp:

    - water: the plane z = level across the room box: below it a CONTENTS_WATER leaf (swimming), above it the open
      air; the "*water" face on the plane seen from above and below (TEX_SPECIAL, no lightmap), as qbsp emits a
      liquid face and as the original game's interior water is one flat plane over the whole cell;
    - lava: each pool's prism (tools/lava.pool_brushes: LIQUID_DEPTH deep) carved out of the open air by the plan BSP
      the exterior chunks use (chim.terrain.lava_plan): a CONTENTS_LAVA leaf under the "*lava" warp face, seen from
      above and below. Its bed is a collision model of the room map (room_map, lava_beds).

    The standing hull is empty (the room edge and the beds are clip models). miptex: {texture name: miptex bytes}.
    Returns (lumps, report)."""
    import numpy as np
    from chim.frame_map import EMPTY
    from chim.models import SOLID_LEAF, BrushLumps
    from chim.terrain import (CONTENTS_EMPTY, CONTENTS_LAVA, CONTENTS_WATER, TEX_SPECIAL, lava_plan, lava_prisms,
                              polygon_area_xy, quake_texture_axes, short_box)
    import lava
    w = BrushLumps()
    up = np.array([0., 0., 1.])
    region = [(lo[0], lo[1]), (hi[0], lo[1]), (hi[0], hi[1]), (lo[0], hi[1])]
    water = liquids.get('water')
    nodes, leaves, faces = [], [SOLID_LEAF], []
    counts = {'water_faces': 0, 'lava_faces': 0, 'lava_leaves': 0, 'water_leaves': 0}

    def emit(poly2d, z, texture):
        flat = np.array([(x, y, z) for x, y in poly2d], dtype=float)
        if polygon_area_xy(flat) < 0:
            flat = flat[::-1].copy()
        pi = w.plane(up, z)
        first, num = w.faces([(flat, up, quake_texture_axes(up), np.zeros(2), texture),
                              (flat[::-1].copy(), -up, quake_texture_axes(-up), np.zeros(2), texture)],
                             lambda m: m, flags_of=lambda s: TEX_SPECIAL, light_of=lambda s: None,
                             plane_of=lambda s: (pi, 0 if s[1][2] > 0 else 1))
        ids = list(range(first, first + num))
        faces.extend(ids)
        return ids

    def add_node(normal, dist, bounds, ids=()):
        w.plane(normal, dist)
        nodes.append([normal, dist, None, None, bounds, ids[0] if ids else 0, len(ids)])
        return len(nodes) - 1

    def add_leaf(contents, bounds):
        leaves.append((contents, bounds))
        return -len(leaves)                     # -1 - index

    def carve(plan, bounds, fill=CONTENTS_EMPTY):
        """The plan's cells inside BOUNDS (one side of the water plane, or the whole box): FILL (the open air above
        the water, the water under it) around the lava prisms; inside a prism the lava wins (a pool whose bed reaches
        under the water level: its part under the plane is lava in the water, CHIM-ROOM-LAVA-UNDER-WATER-48). A
        pool's surface face is emitted on the side that holds it."""
        if plan[0] == 'air':
            return add_leaf(fill, bounds)
        if plan[0] == 'split':
            me = add_node(plan[1], plan[2], bounds)
            nodes[me][2] = carve(plan[3], bounds, fill)
            nodes[me][3] = carve(plan[4], bounds, fill)
            return me
        _, cell, top, bottom = plan[:4]
        z0, z1 = bounds[2], bounds[5]
        if top <= z0 or bottom >= z1:
            return add_leaf(fill, bounds)            # the prism lies wholly on the other side of the water plane
        ids = emit(cell, top, lava.TEXTURE) if z0 < top <= z1 else []
        counts['lava_faces'] += len(ids)
        me = add_node(up, top, bounds, ids)
        nodes[me][2] = add_leaf(fill, bounds)
        low = add_node(-up, -bottom, bounds)
        nodes[me][3] = low
        nodes[low][2] = add_leaf(fill, bounds)
        xs, ys = [x for x, _ in cell], [y for _, y in cell]
        nodes[low][3] = add_leaf(CONTENTS_LAVA, (min(xs), min(ys), max(bottom, z0), max(xs), max(ys), min(top, z1)))
        counts['lava_leaves'] += 1
        return me

    plan = lava_plan(region, lava_prisms(liquids.get('lava'), lava.LIQUID_DEPTH))
    box = (*lo, *hi)
    if water is not None:
        if not lo[2] < water < hi[2]:
            raise ValueError('The water level %.3f is outside the room box' % water)
        ids = emit(region, water, WATER_TEXTURE)
        counts['water_faces'] = len(ids)
        root = add_node(up, water, box, ids)
        nodes[root][2] = carve(plan, (lo[0], lo[1], water, hi[0], hi[1], hi[2]))
        # under the plane: the water, and the lava of every pool that reaches below it (carved the same way)
        nodes[root][3] = carve(plan, (lo[0], lo[1], lo[2], hi[0], hi[1], water), CONTENTS_WATER)
        counts['water_leaves'] = sum(1 for c, _ in leaves[1:] if c == CONTENTS_WATER)
    else:
        root = carve(plan, box)
        if root < 0:
            raise ValueError('No liquid lies in the room box')
    missing = sorted({t for t in w.textures} - set(miptex))
    if missing:
        raise ValueError('The room map has no %s texture' % ', '.join(missing))
    lumps = w.lumps
    for normal, dist, front, back, bounds, firstface, numfaces in nodes:
        lumps[5] += struct.pack('<ihh6h2H', w.plane(normal, dist), front, back, *short_box(bounds), firstface, numfaces)
    # every open leaf lists every liquid face (a handful): no visibility, every leaf is drawn
    lumps[10] = bytearray(SOLID_LEAF)
    for contents, bounds in leaves[1:]:
        lumps[10] += struct.pack('<2i6h2H4B', contents, -1, *short_box(bounds), 0, len(faces), 0, 0, 0, 0)
    lumps[11] = bytearray(struct.pack('<%dH' % len(faces), *faces))
    lumps[9] = bytearray(struct.pack('<iHH', 0, EMPTY & 65535, EMPTY & 65535))     # standing hull: empty
    names = list(w.textures)
    offsets, data = [], b''
    head = 4 + 4 * len(names)
    for name in names:
        offsets.append(head + len(data))
        data += miptex[name] + bytes(-len(miptex[name]) % 4)
    lumps[2] = bytearray(struct.pack('<i%di' % len(names), len(names), *offsets) + data)
    lumps[14] = bytearray(struct.pack('<9f7i', *lo, *hi, 0.0, 0.0, 0.0, root, 0, 0, 0, len(leaves) - 1,
                                      0, len(lumps[7]) // 20))
    return [bytes(x) for x in lumps], dict(counts, nodes=len(nodes), leaves=len(leaves) - 1, faces=len(faces),
                                           textures=names)


def lava_beds(liquids):
    """The solid bed under each lava pool (tools/lava.pool_brushes: BED_THICKNESS under the liquid), as convex
    collision pieces (points, lo, hi) for chim.frame_map.add_clip_pieces."""
    import numpy as np
    import lava
    out = []
    for p in liquids.get('lava') or ():
        bottom = float(p['top']) - lava.LIQUID_DEPTH
        pts = np.array([(x, y, bottom) for x, y in p['hull']] + [(x, y, bottom - lava.BED_THICKNESS)
                                                                 for x, y in p['hull']], dtype=float)
        out.append((pts, tuple(pts.min(axis=0)), tuple(pts.max(axis=0))))
    return out


def liquid_extent(liquids):
    """(lo, hi) the room box must hold for the liquids: the water level and every pool with its bed."""
    import lava
    lo, hi = [float('inf')] * 3, [float('-inf')] * 3
    if liquids.get('water') is not None:
        lo[2] = hi[2] = float(liquids['water'])
    for p in liquids.get('lava') or ():
        for x, y in p['hull']:
            lo[0], lo[1], hi[0], hi[1] = min(lo[0], x), min(lo[1], y), max(hi[0], x), max(hi[1], y)
        lo[2] = min(lo[2], float(p['top']) - lava.LIQUID_DEPTH - lava.BED_THICKNESS)
        hi[2] = max(hi[2], float(p['top']))
    return lo, hi


def room_map(room_bsp, name, record, bounds, liquids=None, store=None):
    """maps/<room>.chim: the room map's entities with its placed meshes taken out (they are the room record's
    placements, checked at the same origins), the activated objects as collision-only edicts, and a shell world:
    empty space closed by clip walls on six sides. A room with liquids (room_liquids) gets them in that world
    (liquid_world: the water plane and the lava cells, with the room map's own "*water" and "*lava" textures) and
    each lava bed as one more clip model; the box grows to hold them. store: the interior store folder the record's
    model ids name (a batch room's shell map gets its static flames from it). Returns (bytes, report); raises
    ValueError on anything that cannot be carried."""
    from chim.frame_map import (FRAME_KEY, activated_refs, add_clip_models, add_clip_pieces, empty_world, entities,
                                entity_text, keep_activated, model_bounds)
    data = Path(room_bsp).read_bytes()
    from chim.cut import source_ref
    placed = {p['ref']: p['origin'] for p in read_room_record(record)['placements']}
    # tiles of a model over the image budget (chim.cut.budget_tile_unit): their source placement in the room map
    # stands for all of them (their origins are the tiles' centres, not the placement's)
    tiles_of = {}
    for r in placed:
        if source_ref(r) != r:
            tiles_of.setdefault(source_ref(r), []).append(r)
    act = activated_refs()
    rows, found, refused, carried = [], [], [], set()
    every = entities(data)
    shell = bool(every and every[0].get('classname') == 'worldspawn' and every[0].get(SHELL_KEY) == '1')
    if shell:
        # a batch room's shell map (tools/chim_room_batches.py): no placed mesh in it; its placements are the room
        # record's by construction (the same scenery export and kept list), so there is no origin to compare
        carried = set(placed)
        refused += ['activated object %d has no CHIM room form in a batch room' % r for r in sorted(set(placed) & set(act))]
        every[0] = {k: v for k, v in every[0].items() if k != SHELL_KEY}
    for e in every:
        model, ref = e.get('model', ''), e.get('aw_ref', '')
        if e.get('classname') == 'func_wall' and model.startswith('*') and ref.isdigit():
            r = int(ref)
            if r not in placed and r in tiles_of and r not in act:
                carried.update(tiles_of[r])
                continue
            if r not in placed:
                refused.append('placed mesh %s is not in the room record' % ref)
                continue
            origin = [float(v) for v in e.get('origin', '0 0 0').split()]
            if max(abs(a - b) for a, b in zip(origin, placed[r])) > ORIGIN_TOLERANCE:
                refused.append('placed mesh %s: origin %s in the room map, %s in the record'
                               % (ref, origin, [round(v, 4) for v in placed[r]]))
            if r in act:
                row = {k: v for k, v in e.items() if k != 'model'}
                row['_box'] = tuple(tuple(round(v, 4) for v in b) for b in model_bounds(data, int(model[1:])))
                found.append(row)
            carried.add(r)
            continue
        if model.startswith('*'):
            refused.append('brush entity %s %s has no CHIM room form' % (e.get('classname'), model))
            continue
        rows.append(dict(e))
    missing = sorted(set(placed) - carried)
    if missing:
        refused.append('%d record placements are not in the room map (first: %s)' % (len(missing), missing[:5]))
    if not rows or rows[0].get('classname') != 'worldspawn':
        refused.append('the room map has no worldspawn first')
    if refused:
        raise ValueError('CHIM room %s: %s' % (name, '; '.join(refused[:6])))
    flame_report = None
    if shell and store is not None:
        # A batch room's shell map has no aw_flame (the room converter wrote them beside its placed meshes): the
        # room record's placements give them, from the store models' emitters (chim.flames,
        # CHIM-EXTERIOR-FLAMES-MISSING-48). A room converted whole keeps its own map's flames unchanged.
        from chim.flames import frame_rows, store_models
        flames, flame_report = frame_rows([{'owned': read_room_record(record)['placements']}], store_models(store))
        rows += flames
    world = rows[0]
    if shell and 'aw_hull' not in world:
        # The room world below (empty space, clip walls, liquids) is built here for both kinds of room; a room
        # converted whole inherits the declaration from its compiled map, a batch shell map never had one, so the
        # actor ground check refused every batch room resident (CHIM-ROOM-SHELL-NO-HULL-48)
        from player_hull import PROFILE
        world['aw_hull'] = PROFILE
    world.pop('wad', None)
    world.pop(FRAME_KEY, None)
    world['_chim_world'] = STORE
    world[ROOM_KEY] = name
    lo = [v - EDGE_MARGIN for v in bounds[0]]
    hi = [v + EDGE_MARGIN for v in bounds[1]]
    liquid_report = None
    if liquids:
        ext_lo, ext_hi = liquid_extent(liquids)
        lo = [min(a, b - EDGE_MARGIN) for a, b in zip(lo, ext_lo)]
        hi = [max(a, b + EDGE_MARGIN) for a, b in zip(hi, ext_hi)]
        lumps, liquid_report = liquid_world(lo, hi, liquids, miptex_named(data, (WATER_TEXTURE, '*lava')))
    else:
        lumps = empty_world(lo, hi)
    t = WALL
    boxes = [((lo[0] - t, lo[1] - t, lo[2] - t), (lo[0], hi[1] + t, hi[2] + t)),
             ((hi[0], lo[1] - t, lo[2] - t), (hi[0] + t, hi[1] + t, hi[2] + t)),
             ((lo[0], lo[1] - t, lo[2] - t), (hi[0], lo[1], hi[2] + t)),
             ((lo[0], hi[1], lo[2] - t), (hi[0], hi[1] + t, hi[2] + t)),
             ((lo[0], lo[1], lo[2] - t), (hi[0], hi[1], lo[2])),
             ((lo[0], lo[1], hi[2]), (hi[0], hi[1], hi[2] + t))]
    lumps, numbers = add_clip_models(lumps, boxes)
    rows += [{'classname': 'func_wall', 'model': '*%d' % n, 'aw_clip': name + ' room edge'} for n in numbers]
    if liquids and liquids.get('lava'):
        lumps, beds = add_clip_pieces(lumps, lava_beds(liquids))
        rows += [{'classname': 'func_wall', 'model': '*%d' % n, 'aw_clip': name + ' lava bed'} for n in beds]
        liquid_report['beds'] = len(beds)
    lumps, kept = keep_activated(lumps, rows, found)
    lumps[0] = entity_text(rows)
    out = F.brush_image(lumps)[0]
    report = {'entities': len(rows), 'placements_checked': len(carried), 'activated': kept,
              'edge': {'margin': EDGE_MARGIN, 'thickness': WALL, 'walls': len(numbers)}}
    if liquid_report is not None:
        report['liquids'] = dict(liquid_report, water=liquids.get('water'), lava_pools=len(liquids.get('lava') or ()))
    if flame_report is not None:
        report['flames'] = flame_report
    return out, report


class Store:
    """The interior store being written: models and textures once by content, homed in the pack of the room that
    first uses them (rooms in build order, so a room's models lie together)."""

    def __init__(self):
        self.texture_content, self.texture_records, self.texture_names = {}, [], {}
        self.model_content, self.model_records, self.model_names = {}, [], {}
        self.packs, self.current, self.current_bytes = [], [], 0
        self.home = {}                       # ('MODL'|'TEXR', id) -> pack index

    def _homed(self, kind, rid, data):
        self.current.append((kind, rid, data))
        self.current_bytes += len(data)
        self.home[(kind, rid)] = len(self.packs)

    def close_pack(self):
        if self.current:
            self.packs.append(self.current)
            self.current, self.current_bytes = [], 0

    def texture_id(self, src):
        from chim.models import engine_texture_name
        mip = src['miptex']
        engine = mip[:16].split(b'\0')[0].decode('ascii') if src['engine'] is None else \
            engine_texture_name(src['engine'][0], src['engine'][1], len(self.texture_records))
        digest = hashlib.sha256(F.texture_content(engine, mip)).hexdigest()
        if digest not in self.texture_content:
            identity, n = src['identity'], 1
            while identity in self.texture_names and self.texture_names[identity] != digest:
                n += 1
                identity = '%s#%d' % (src['identity'], n)
            self.texture_names[identity] = digest
            tid = len(self.texture_records)
            self.texture_content[digest] = tid
            named = engine.encode('ascii').ljust(16, b'\0') + mip[16:]
            self.texture_records.append((identity, named, *src['size']))
            self._homed(b'TEXR', tid, named)
        return self.texture_content[digest]

    def model_id(self, variant, textures):
        from chim.world import resolved_image
        image, render = resolved_image(variant['lumps'], variant['texture_keys'],
                                       lambda k: self.texture_id(textures[k]))
        digest = hashlib.sha256(image).hexdigest()
        if digest not in self.model_content:
            name, n = variant['name'], 1
            while name in self.model_names and self.model_names[name] != digest:
                n += 1
                name = '%s#%d' % (variant['name'], n)
            self.model_names[name] = digest
            mid = len(self.model_records)
            self.model_content[digest] = mid
            self.model_records.append((name, image, render))
            self._homed(b'MODL', mid, image)
        return self.model_content[digest]

    def add_room(self, room):
        """Store a room's models and textures; returns its record bytes and receipt row."""
        from chim.world import stored_box
        spec = room['spec']
        ids, records, placed_models = [], [], {}
        for pid, p in enumerate(spec['placements']):
            v = spec['variants'][p['variant']]
            if p['variant'] not in placed_models:
                placed_models[p['variant']] = self.model_id(v, spec['textures'])
            mid = placed_models[p['variant']]
            if mid not in ids:
                ids.append(mid)
            angles = p.get('angles') or (0.0, p['yaw'], 0.0)
            # the drawn box as every record stores it (chim.world.stored_box: shorts, one unit outward)
            rec = P.placement(pid, p['ref'], mid, p['origin'], angles, 0, 0, 0,
                              stored_box(*P.placed_box(p['origin'], angles, v['lo'], v['hi'])), 1,
                              p.get('story_hidden', False))
            records.append(with_light(rec, room['levels'].get(p['ref'], 0)))
        if self.current_bytes >= PACK_BYTES:
            self.close_pack()
        data = room_record(room['bounds'], ids, records)
        return data, {'room': room['room'], 'cell': room['cell'], 'placements': len(records), 'models': len(ids),
                      'record_bytes': len(data), 'collision_union_fallbacks': room['fallbacks'],
                      'over_budget_tiles': spec.get('over_budget_tiles', {}),
                      'light_levels': [min(room['levels'].values() or [0]), max(room['levels'].values() or [0])]}

    def write(self, out):
        """Write OUT/chimi/: the index and the packs."""
        self.close_pack()
        root = Path(out) / STORE
        root.mkdir(parents=True, exist_ok=True)
        files, at = [], {}
        for pi, records in enumerate(self.packs):
            blob = F.sector_file(records, FORMAT_VERSION)
            if len(blob) > F.FFS_MAX_PACK:
                raise ValueError('Interior store pack exceeds the 1 GiB file limit')
            name = 'p%02d.ccs' % pi
            (root / name).write_bytes(blob)
            for r in F.read_sector(blob):
                at[(r['kind'], r['id'])] = (pi, r['offset'])
            files.append({'kind': b'SECT', 'sector': pi, 'cell': (0, 0), 'bytes': len(blob), 'crc': F.crc32(blob),
                          'entries': len(records), 'path': name})
        from chim.world import DEFAULT_SETTINGS
        settings = dict(DEFAULT_SETTINGS, terrain_light=0, placements=0, models=len(self.model_records),
                        textures=len(self.texture_records), frames=0)
        models_dir = [(name, *at[(b'MODL', mid)], len(image), render)
                      for mid, (name, image, render) in enumerate(self.model_records)]
        textures_dir = [(name, *at[(b'TEXR', tid)], len(mip), w, h)
                        for tid, (name, mip, w, h) in enumerate(self.texture_records)]
        index = F.index_file(settings, files, models_dir, textures_dir, FORMAT_VERSION)
        (root / 'world.cwi').write_bytes(index)
        return {'store': STORE, 'world_format': '%d.%d' % FORMAT_VERSION, 'models': len(self.model_records),
                'textures': len(self.texture_records), 'packs': len(self.packs),
                'model_bytes': sum(len(i) for _, i, _ in self.model_records),
                'texture_bytes': sum(len(m) for _, m, _, _ in self.texture_records),
                'index_bytes': len(index), 'pack_bytes': sum(f['bytes'] for f in files)}


def _room_task(task):
    """One room's input on a pool worker (its own unit cache handle on the shared cache folder and its own timer)."""
    from chim.units import Timer, UnitCache
    work, palette, qbsp, unit_cache, collision_cache = task[:5]
    harvest = task[5] if len(task) > 5 else None
    cache, timer = UnitCache(Path(unit_cache)), Timer()
    try:
        room = room_input(work, Path(palette).read_bytes(), qbsp, 1, cache, timer, Path(collision_cache), harvest)
    except Exception as error:  # noqa: BLE001 (one room's failure costs that room only, named: CHIM-ROOM-FAIL-STAGE-48)
        import traceback
        where = traceback.extract_tb(error.__traceback__)[-1]
        return {'room': Path(work).name, 'failed': '%s: %s (%s:%d %s)' % (
            type(error).__name__, error, Path(where.filename).name, where.lineno, where.name)}
    room['units'], room['timing'] = cache.stats, timer.report()
    return room


def room_cost(task):
    """A room's work, for largest first: the size of its room map (meshes, placements and light grow it alike); a batch
    room's shell map holds no mesh, so its scenery export's size (the meshes its models are made from)."""
    work = Path(task[0])
    if (work / PLACEMENTS_FILE).is_file():
        return (work / 'source/scenery.mwpak').stat().st_size
    return (work / 'room.bsp').stat().st_size


def build(room_works, palette, out, qbsp=None, jobs=1, unit_cache=None, harvest=None, data_files=None):
    """Every room side by side, one room per worker, largest first (as the CHIM areas: one room's own steps are
    serial and a room has few meshes, so rooms one after another left most cores idle); the store is then written
    here alone, rooms in their input order, so a room's models lie together.

    harvest, data_files: the harvest step's output and the game data (builder default): each room leaves its
    harvestable plants out of its record (room_harvest_numbers; receipt row harvest_left_out) and the image places
    them as harvest entities (CHIM-ROOM-HARVEST-DOUBLE-48). Without them (--no-harvest), every plant stays a placed
    mesh of its room, as before."""
    from build_parallel import ordered_map
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    unit_cache = Path(unit_cache) if unit_cache else out / 'work' / 'chim-units'
    numbers, harvest_receipt = None, None
    if harvest:
        if not data_files:
            raise ValueError('CHIM rooms: --harvest needs --data-files (the master the harvest source was made from)')
        numbers = frozenset(room_harvest_numbers(harvest, data_files))
        from harvest_build import SOURCE_RECEIPT
        harvest_receipt = {'source_sha256': hashlib.sha256((Path(harvest) / SOURCE_RECEIPT).read_bytes()).hexdigest(),
                           'interior_placements': len(numbers),
                           'rule': 'harvestable interior plants are left out of the room records; the image places '
                                   'each as its harvest entity (CHIM-ROOM-HARVEST-DOUBLE-48)'}
        _log('harvest: %d harvestable interior plants are left out of the room records' % len(numbers))
    store = Store()
    rows, kept_bsp, tasks, liquids = [], [], [], {}
    (out / STORE / 'rooms').mkdir(parents=True, exist_ok=True)
    for work in room_works:
        work = Path(work)
        found, why = room_liquids(work)
        if found:
            liquids[work.name] = found
        if why:
            # the room keeps its room map (today's form), named in the receipt
            kept_bsp.append({'room': work.name, 'reason': why})
            _log('%s: kept as a room map: %s' % (work.name, why))
            continue
        tasks.append((str(work), str(palette), qbsp and str(qbsp), str(unit_cache), str(out / 'work' / 'collision-cache'),
                      numbers))
    units, timing, failed = {}, {}, []
    for room in ordered_map(_room_task, tasks, max(1, int(jobs or 1)), cost=room_cost):
        if room.get('failed'):
            # the room is not made; the image leaves it out (a batch room's shell map too) and its doors stay inert
            failed.append({'room': room['room'], 'reason': room['failed']})
            _log('%s: FAILED, not made: %s' % (room['room'], room['failed']))
            continue
        for kind, counts in room.pop('units').items():
            for k, v in counts.items():
                units.setdefault(kind, {}).setdefault(k, 0)
                units[kind][k] += v if isinstance(v, (int, float)) else 0
        timing[room['room']] = room.pop('timing')
        data, row = store.add_room(room)
        (out / STORE / 'rooms' / (room['room'] + '.crm')).write_bytes(data)
        row['bounds'] = [list(room['bounds'][0]), list(room['bounds'][1])]
        row['record_sha256'] = hashlib.sha256(data).hexdigest()
        if room['room'] in liquids:
            # the image step's room map writes them into its world (room_map)
            row['liquids'] = liquids[room['room']]
        if 'harvest_left_out' in room:
            # the image places these as harvest entities (harvest_build.chim_room_rows)
            row['harvest_left_out'] = room['harvest_left_out']
            row['harvest_origin'] = room['harvest_origin']
        rows.append(row)
        _log('%s: %d placements, %d models%s' % (row['room'], row['placements'], row['models'],
                                                 ', %d harvestable plants left out' % len(row['harvest_left_out'])
                                                 if row.get('harvest_left_out') else ''))
    receipt = {'format': 'aw-chim-rooms-1', 'store': store.write(out), 'rooms': rows, 'kept_room_maps': kept_bsp,
               'failed_rooms': failed, 'units': units, 'timing': timing, 'jobs': int(jobs or 1)}
    if harvest_receipt is not None:
        harvest_receipt['left_out'] = sum(len(r.get('harvest_left_out', ())) for r in rows)
        receipt['harvest'] = harvest_receipt
    if failed:
        _log('%d rooms FAILED and are not made (receipt failed_rooms): %s' % (
            len(failed), '; '.join('%s: %s' % (f['room'], f['reason']) for f in failed)))
    (out / 'chim-rooms-receipt.json').write_text(json.dumps(receipt, indent=1, sort_keys=True, default=str) + '\n',
                                                 encoding='utf-8', newline='\n')
    return receipt


def is_shell_map(data):
    """True for a batch room's shell map (tools/chim_room_batches.py shell_map: its worldspawn says SHELL_KEY)."""
    from chim.frame_map import entities
    try:
        first = entities(data)[:1]
    except (ValueError, struct.error, UnicodeDecodeError):
        return False
    return bool(first) and first[0].get('classname') == 'worldspawn' and first[0].get(SHELL_KEY) == '1'


def _room_map_task(task):
    """One room's CHIM room map on a pool worker: (room, bytes, report); the caller alone writes the files."""
    bsp, name, record_path, bounds, liquids = task
    # the store is the folder above rooms/<room>.crm
    data, report = room_map(bsp, name, Path(record_path).read_bytes(), bounds, liquids,
                            store=Path(record_path).parent.parent)
    return name, data, report


def install(rooms_out, id1, jobs=1):
    """The image step: the interior store into id1/chimi/ and, for every room record whose room map the image holds
    (id1/maps/<room>.bsp, final: residents and banks in), its room map id1/maps/<room>.chim made from that map; the
    .bsp is removed (the engine loads the .chim). The room maps are made side by side (one room per worker, largest
    first); the files are written here alone. Returns the install record."""
    from build_parallel import ordered_map
    from map_files import frame_map_path
    from mwad.paths import copy_tree
    rooms_out, id1 = Path(rooms_out), Path(id1)
    receipt = json.loads((rooms_out / 'chim-rooms-receipt.json').read_text())
    target = id1 / STORE
    if target.exists():
        raise ValueError('An interior store is already installed: %s' % target)
    copy_tree(rooms_out / STORE, target)        # writable copies (the stage output may be read-only in the pool)
    installed, absent, tasks = [], [], []
    for row in receipt['rooms']:
        bsp = id1 / 'maps' / (row['room'] + '.bsp')
        if not bsp.is_file():
            absent.append(row['room'])
            continue
        tasks.append((str(bsp), row['room'], str(target / 'rooms' / (row['room'] + '.crm')), row['bounds'],
                      row.get('liquids')))
    for name, data, report in ordered_map(_room_map_task, tasks, max(1, int(jobs or 1)),
                                          cost=lambda t: Path(t[0]).stat().st_size):
        bsp = id1 / 'maps' / (name + '.bsp')
        frame_map_path(id1, name, 'chim').write_bytes(data)
        installed.append(dict(report, room=name, room_map_bytes=len(data), bsp_bytes=bsp.stat().st_size,
                              sha256=hashlib.sha256(data).hexdigest()))
        bsp.unlink()
    # records of rooms the image does not hold are not shipped
    for room in absent:
        (target / 'rooms' / (room + '.crm')).unlink()
    # a batch room's shell map (no world of its own: tools/chim_room_batches.py) whose CHIM room was not made (failed,
    # or kept as a room map) is no room: it leaves the image, so its doors stay inert ("Interior unavailable")
    removed = []
    for row in list(receipt.get('failed_rooms', [])) + list(receipt.get('kept_room_maps', [])):
        bsp = id1 / 'maps' / (row['room'] + '.bsp')
        if bsp.is_file() and is_shell_map(bsp.read_bytes()):
            bsp.unlink()
            removed.append({'room': row['room'], 'reason': row['reason']})
    store_bytes = sum(p.stat().st_size for p in target.rglob('*') if p.is_file())
    return {'store': STORE, 'rooms': installed, 'not_in_image': absent, 'kept_room_maps': receipt['kept_room_maps'],
            'failed_rooms': receipt.get('failed_rooms', []), 'shell_maps_removed': removed,
            'store_bytes': store_bytes, 'room_map_bytes': sum(r['room_map_bytes'] for r in installed),
            'replaced_bsp_bytes': sum(r['bsp_bytes'] for r in installed)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--room-work', action='append', default=[], help="a converted room's work folder")
    ap.add_argument('--rooms-from', action='append', default=[],
                    help="a room stage's area-work folder: every room in it (a folder with room.bsp); absent: none")
    ap.add_argument('--palette', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--qbsp')
    ap.add_argument('--unit-cache')
    ap.add_argument('--jobs', type=int, default=1)
    ap.add_argument('--harvest', help="the harvest step's output (tools/harvest_build.py prepare): the rooms leave its "
                                      "plants out, the image places them as harvest entities; absent: plants stay "
                                      "placed meshes")
    ap.add_argument('--data-files', help='the game data the harvest source was made from (with --harvest)')
    args = ap.parse_args(argv)
    works = list(args.room_work)
    for folder in args.rooms_from:
        if Path(folder).is_dir():
            works += sorted(str(d) for d in Path(folder).iterdir() if (d / 'room.bsp').is_file())
    receipt = build(works, args.palette, args.out, args.qbsp, args.jobs, args.unit_cache, args.harvest,
                    args.data_files)
    print(json.dumps(receipt['store'], indent=1))


if __name__ == '__main__':
    main()
