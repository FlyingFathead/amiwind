#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The CHIM frame map: maps/<town>-chim.bsp, the map the engine loads for a town when CHIM is on.

It holds what the CHIM chunks do not: the town's map entities (actors and the
player start), with an empty world whose bounds cover the frame, and the
worldspawn key "_chim_frame" "CX CY" naming the frame's FRAM row (its cell in
world.cwi). Coordinates are frame-local, the same as the town's region maps
((Morrowind position - town centre) x 0.25), so entities are copied as they are.
The legacy region maps stay untouched and selectable (docs/chim/WORLD_FORMAT.md,
"Activation").

Every entity class of the town's final region maps is accounted for:
  worldspawn         identical in every region map; merged, plus "_chim_frame"
  info_player_start  one per region map; the town's default region's (the region
                     whose core holds the region table's default point)
  func_wall + aw_ref a static object: in the CHIM chunks, not copied; an object the
                     engine activates by its aw_ref (engine aw_activated.h, the one
                     list) also keeps its edict: a collision-only brush model (no
                     faces) of its region-map model's box, same keys and origin
  point entities     copied once (same aw_ref, or the same keys, in several regions)
Anything else (another brush entity, a static missing from the CHIM world, the
same aw_ref with different keys) is refused: nothing is dropped silently.

Two more gates, so a town whose maps disagree with the CHIM frame fails loudly:
  frame origin   the frame's centre x 0.25 is the town's region-map origin (the
                 origin door arrivals, the region directory, harvest catalogues
                 and saves use), and every static the region maps and the CHIM
                 world share sits at the same frame-local origin (within 0.01)
  harvest        every harvest catalogue of the town's regions is AWH4 (shared
                 alias models, representation 4): brush catalogues (0) bind plants
                 to func_wall edicts by aw_ref, and the frame map has none

    python3 tools/chim/frame_map.py ID1 TOWN CHIM_WORLD [--json REPORT]
"""
import argparse
import collections
import json
import math
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import format as F  # noqa: E402

FRAME_KEY = '_chim_frame'
SUFFIX = '-chim'
ENTITY = re.compile(r'\{([^{}]*)\}')
FIELD = re.compile(r'"([^"]*)"\s+"([^"]*)"')
FLOOR_MARGIN = 256.0
# Worldspawn keys that describe one region map only, not the town: the region's pool of terrain-culled
# placement faces (canonical_bsp_cull, aw_render_ranges.c). CHIM draws placed models whole, so the frame
# map has none; they are left out of the worldspawn comparison and recorded.
PER_MAP_KEYS = ('aw_render_pool',)
# Converted terrain in region maps is a brush entity with a reference number at or above this (the recorded
# Seyda Neen stage: "Canonical terrain visual and collision"; stair_walk._placement uses the same bound): in a
# CHIM frame the ground is the chunks' world terrain, so it is accounted for as terrain, not a static.
TERRAIN_REF = 2147483000
# Point entities whose spawn function makes them Quake static entities (engine/aga/qc/world.qc: makestatic).
STATIC_CLASSES = ('aw_static', 'aw_flora')


def static_entity_limit():
    """The engine's static-entity limit as its source states it (client.h MAX_STATIC_ENTITIES, read by
    tools/engine_limits.py), so the frame map is checked against whatever limit the engine has."""
    from engine_limits import limits
    return limits()['max_static_entities']


def static_check(rows, limit=None):
    """(refusals, record): the frame map's static entities (STATIC_CLASSES) fit the engine's limit."""
    limit = static_entity_limit() if limit is None else limit
    count = sum(1 for e in rows if e.get('classname') in STATIC_CLASSES)
    refused = [] if count <= limit else ['%d static entities, the engine holds %d (MAX_STATIC_ENTITIES)' % (count, limit)]
    return refused, {'static_entities': count, 'limit': limit, 'headroom': limit - count}
ORIGIN_TOLERANCE = 0.01
EMPTY, SOLID = -1, -2


def map_name(town):
    return town + SUFFIX


def entities(data):
    """Entity dicts of a BSP29 map, in file order."""
    version, offset, size = struct.unpack_from('<iii', data, 0)
    if version != 29:
        raise ValueError('not a BSP29 map')
    text = data[offset:offset + size].decode('latin-1').rstrip('\0')
    return [dict(FIELD.findall(block)) for block in ENTITY.findall(text)]


def entity_text(rows):
    out = []
    for e in rows:
        out.append('{\n' + ''.join('"%s" "%s"\n' % (k, v) for k, v in e.items()) + '}\n')
    return (''.join(out) + '\0').encode('latin-1')


def region_table(path):
    """(default point, [(name, core box)]) of a region table (AWBR1)."""
    rows = Path(path).read_text(encoding='ascii').splitlines()
    head = rows[0].split()
    if head[0] != 'AWBR1':
        raise ValueError('Unknown region table: ' + str(path))
    point = (float(head[4]), float(head[5]))
    regions = [(r.split()[0], tuple(float(v) for v in r.split()[1:5])) for r in rows[1:] if r.strip()]
    return point, regions


def default_region(point, regions):
    for name, (x0, y0, x1, y1) in regions:
        if x0 <= point[0] < x1 and y0 <= point[1] < y1:
            return name
    raise ValueError('No region core holds the default point %.1f %.1f' % point)


def origin_check(region_maps, chim_origins, frame_centre, town_origin):
    """(refusals, record): the frame's origin against the town's region-map origin, and the
    statics both sides hold at the same frame-local origin."""
    refused = []
    frame_origin = [frame_centre[0] * 0.25, frame_centre[1] * 0.25]
    if any(abs(a - b) > 1e-3 for a, b in zip(frame_origin, town_origin[:2])):
        refused.append('frame origin %.3f %.3f differs from the town region maps\' origin %.3f %.3f'
                       % (*frame_origin, *town_origin[:2]))
    worst, compared, far = 0.0, 0, []
    for name in sorted(region_maps):
        for e in region_maps[name]:
            ref = e.get('aw_ref', '')
            if e.get('classname') != 'func_wall' or not ref.isdigit() or chim_origins.get(int(ref)) is None:
                continue                      # absent, or cut by chunk (chim.cut: no single origin)
            here = [float(v) for v in e.get('origin', '0 0 0').split()]
            off = max(abs(a - b) for a, b in zip(here, chim_origins[int(ref)]))
            compared += 1
            worst = max(worst, off)
            if off > ORIGIN_TOLERANCE:
                far.append(ref)
    if far:
        refused.append('%d statics sit elsewhere in the region maps than in the CHIM frame (first %s, up to %.3f '
                       'units): the town\'s coordinates differ' % (len(far), far[0], worst))
    return refused, {'frame_origin': frame_origin, 'town_origin': list(town_origin[:2]),
                     'statics_compared': compared, 'largest_offset': round(worst, 6)}


def harvest_check(id1, region_names):
    """(refusals, record): every harvest catalogue of the town's regions is AWH4 (representation 4)."""
    found, refused = {}, []
    for name in region_names:
        path = Path(id1) / ('harvest-%s.txt' % name)
        if not path.is_file():
            continue
        magic = path.read_bytes()[:8].split()[0].decode('ascii', 'replace') if path.stat().st_size else ''
        found[name] = magic
        if magic != 'AWH4':
            refused.append('harvest-%s.txt is %s, not AWH4: its plants bind to func_wall edicts the frame map '
                           'does not have' % (name, magic or 'empty'))
    counts = collections.Counter(found.values())
    return refused, {'catalogues': len(found), 'by_header': dict(sorted(counts.items())),
                     'representation': 4 if found and set(found.values()) == {'AWH4'} else None}


def frame_entities(region_maps, chim_refs, default):
    """The frame map's entities and the accounting of every class.

    region_maps: {region name: [entity dicts]}; chim_refs: the placement refs of
    the CHIM world. Returns (entities, report); report['refused'] lists what
    cannot be carried (the caller stops on it)."""
    counts = collections.Counter()
    worldspawns, starts, points, refused = {}, {}, {}, []
    by_ref = {}
    map_statics = set()
    terrain_walls = 0
    for name in sorted(region_maps):
        for e in region_maps[name]:
            c = e.get('classname', '')
            counts[c] += 1
            model = e.get('model', '')
            if c == 'worldspawn':
                worldspawns[name] = e
            elif c == 'info_player_start':
                starts.setdefault(name, e)
            elif model.startswith('*'):
                ref = e.get('aw_ref', '')
                if c == 'func_wall' and ref.isdigit() and int(ref) >= TERRAIN_REF:
                    terrain_walls += 1
                elif c == 'func_wall' and ref.isdigit():
                    map_statics.add(int(ref))
                else:
                    refused.append('%s: brush entity %s %s has no CHIM form' % (name, c, model))
            else:
                key = ('ref', e['aw_ref']) if e.get('aw_ref', '').isdigit() else ('keys', tuple(sorted(e.items())))
                if key in by_ref and by_ref[key] != e:
                    refused.append('%s: %s %s differs between regions' % (name, c, key[1]))
                    continue
                by_ref[key] = e
                points.setdefault(c, {})[key] = e
    if not worldspawns:
        raise ValueError('No region maps')
    per_map = sorted({k for w in worldspawns.values() for k in w if k in PER_MAP_KEYS})
    worldspawns = {n: {k: v for k, v in w.items() if k not in PER_MAP_KEYS} for n, w in worldspawns.items()}
    first = worldspawns[sorted(worldspawns)[0]]
    for name, w in worldspawns.items():
        if w != first:
            diff = sorted(k for k in set(w) | set(first) if w.get(k) != first.get(k))
            refused.append('%s: worldspawn differs from the other regions (%s)' % (name, ', '.join(diff)))
    if default not in starts:
        refused.append('default region %s has no info_player_start' % default)
    maps_only = sorted(map_statics - set(chim_refs))
    if maps_only:
        refused.append('%d statics of the region maps are not in the CHIM world (%s)'
                       % (len(maps_only), ', '.join(map(str, maps_only[:8]))))
    chim_only = sorted(set(chim_refs) - map_statics)
    if chim_only:
        refused.append('%d CHIM statics are not in the final region maps (first: %s)'
                       % (len(chim_only), ', '.join(map(str, chim_only[:5]))))
    out = [dict(first), *([dict(starts[default])] if default in starts else [])]
    for c in sorted(points):
        out += [points[c][k] for k in sorted(points[c], key=lambda k: (k[0], str(k[1])))]
    written = collections.Counter(e.get('classname', '') for e in out)
    rules = {'worldspawn': 'merged (identical in every region) plus %s' % FRAME_KEY,
             'info_player_start': 'one per region; the default region\'s (%s)' % default,
             'func_wall': 'static objects: in the CHIM chunks; converted terrain (aw_ref >= %d): the chunk '
                          'ground' % TERRAIN_REF}
    report = {'classes': {c: {'in_regions': counts[c], 'written': written.get(c, 0),
                              'rule': rules.get(c, 'copied once')} for c in sorted(counts)},
              'default_region': default, 'regions': len(region_maps),
              'statics_in_chunks': len(map_statics & set(chim_refs)), 'chim_statics_not_in_maps': chim_only,
              'map_statics_not_in_chim': maps_only, 'per_map_worldspawn_keys_left_out': per_map,
              'terrain_brush_entities': terrain_walls,
              'refused': refused}
    return out, report


def empty_world(lo, hi):
    """The 15 lumps of a world with no faces: one node splitting the frame into two empty
    leaves, a standing hull that is empty everywhere, no visibility (everything visible)."""
    lumps = [b''] * 15
    mid = (lo[0] + hi[0]) / 2.0
    lumps[1] = struct.pack('<4fi', 1.0, 0.0, 0.0, mid, 0)                       # plane x = mid
    lumps[2] = struct.pack('<i', 0)                                              # no textures
    box = [int(v) for v in (*lo, *hi)]
    left, right = list(box), list(box)
    left[3], right[0] = int(mid), int(mid)
    lumps[5] = struct.pack('<ihh6h2H', 0, -3, -2, *box, 0, 0)                    # front leaf 2, back leaf 1
    lumps[9] = struct.pack('<iHH', 0, EMPTY & 65535, EMPTY & 65535)              # standing hull: empty
    lumps[10] = (struct.pack('<2i6h2H4B', SOLID, -1, *[0] * 6, 0, 0, 0, 0, 0, 0)
                 + struct.pack('<2i6h2H4B', EMPTY, -1, *left, 0, 0, 0, 0, 0, 0)
                 + struct.pack('<2i6h2H4B', EMPTY, -1, *right, 0, 0, 0, 0, 0, 0))
    lumps[12] = struct.pack('<HH', 0, 0)
    lumps[14] = struct.pack('<9f7i', *lo, *hi, 0.0, 0.0, 0.0, 0, 0, 0, 0, 2, 0, 0)
    return lumps


def frame_record(world_dir, cell=None):
    """(cell, low corner, high corner, chunks, centre) of a frame of the CHIM world: the one with
    `cell`, or the only one."""
    from chim.terrain import TERRAIN_CEILING
    root = Path(world_dir) / 'chim'
    _, files, _, _ = F.read_index((root / 'world.cwi').read_bytes())
    frames = [f for f in files if f['kind'] == b'FRAM' and (cell is None or tuple(f['cell']) == tuple(cell))]
    if len(frames) != 1:
        raise ValueError('The CHIM world has %d frames %s' % (len(frames), 'at cell %s' % (cell,) if cell else ''))
    frame, chunks, _ = F.read_frame((root / frames[0]['path']).read_bytes())
    g, (lx, ly) = frame['grain'], frame['low']
    zlo = min(c['zmin'] for c in chunks) - FLOOR_MARGIN
    return (tuple(frame['cell']), (lx, ly, zlo), (lx + frame['nx'] * g, ly + frame['ny'] * g, float(TERRAIN_CEILING)),
            chunks, tuple(frame['centre']))


def frame_bounds(world_dir, cell=None):
    """Frame-local bounds of a frame of the CHIM world (x, y from the frame record, z from the chunks)."""
    cell, lo, hi, _, _ = frame_record(world_dir, cell)
    return cell, lo, hi


def chim_placements(world_dir, cell=None):
    """{ref: frame-local origin} of the CHIM world's placements (of the frame at `cell` only, if given).
    A cut placement (chim.cut) is listed under its source reference with origin None: its pieces sit at
    their chunks' centres, not at the placement's origin."""
    from chim.cut import source_ref
    from chim.validate import Failures, load_world
    fails = Failures()
    _, _, _, _, _, frames = load_world(world_dir, fails)
    if fails:
        raise ValueError('CHIM world does not load: ' + '; '.join(fails[:3]))
    out = {}
    for _, frame, chunks in frames:
        if cell is not None and tuple(frame['cell']) != tuple(cell):
            continue
        for c in chunks:
            for r in c['owned']:
                src = source_ref(r['ref'])
                if src != r['ref']:
                    out[src] = None
                elif src not in out:
                    out[src] = tuple(r['origin'])
    return out


def chim_placement_refs(world_dir):
    return set(chim_placements(world_dir))


# ---------------------------------------------------------------- statics streamed with their chunks

STREAMED_CLASSES = ('aw_static', 'aw_flora')     # world.qc: precache_model + setmodel + makestatic, nothing else
CHUNK_KEY, BOX_KEY, COUNT_KEY, HUNK_KEY = '_chim_chunk', '_chim_box', '_chim_streamed_statics', '_chim_hunk_rest'


def model_radius(raw):
    """Bounding radius of a Quake sprite (IDSP) or alias model (IDPO), model units."""
    magic = raw[:4]
    if magic == b'IDSP':
        return struct.unpack_from('<f', raw, 12)[0]
    if magic == b'IDPO':
        radius = struct.unpack_from('<f', raw, 32)[0]       # modelgen: the farthest vertex from the origin
        if radius > 0:
            return radius
        scale = struct.unpack_from('<3f', raw, 8)            # unset: the largest extent the header allows
        origin = struct.unpack_from('<3f', raw, 20)
        return math.sqrt(sum((abs(origin[k]) + abs(scale[k]) * 255) ** 2 for k in range(3)))
    raise ValueError('Not a sprite or alias model')


def frame_grid(world_dir, cell):
    """(chunks, low (x, y), grain, nx, ny) of the frame at cell."""
    root = Path(world_dir) / 'chim'
    _, files, _, _ = F.read_index((root / 'world.cwi').read_bytes())
    path = next(f['path'] for f in files if f['kind'] == b'FRAM' and tuple(f['cell']) == tuple(cell))
    frame, chunks, _ = F.read_frame((root / path).read_bytes())
    return chunks, tuple(frame['low']), frame['grain'], frame['nx'], frame['ny']


def stream_statics(id1, rows, chunks, frame_low, grain, nx, ny):
    """Tag the frame map's static models for streaming with their chunks (CHIM-SEYDA-MEMORY: their
    models cost the Hunk ~1 MB in Seyda Neen when all load at once). Each aw_static / aw_flora gets
    CHUNK_KEY (the chunk holding its origin, as an index into the frame's chunk directory) and
    BOX_KEY (frame-local drawn box: origin +- the model's bounding radius, times aw_scale for an
    aw_flora; PF_makestatic sends aw_scale for aw_flora only, which must be a sprite), every key
    PF_makestatic reads unchanged; the engine skips them at load and builds the same static entities
    when the chunk is active. Returns the count and the models' bytes (left out of HUNK_KEY)."""
    by_cell = {(c['cx'], c['cy']): c['index'] for c in chunks}
    radii, sizes, sprites, count = {}, {}, {}, 0
    for e in rows:
        if e.get('classname') not in STREAMED_CLASSES:
            continue
        name = e.get('model', '')
        if name not in radii:
            raw = (Path(id1) / name).read_bytes()
            radii[name], sizes[name], sprites[name] = model_radius(raw), len(raw), raw[:4] == b'IDSP'
        scale = 1.0                           # PF_makestatic: aw_scale applies to aw_flora only
        if e['classname'] == 'aw_flora':
            scale = float(e.get('aw_scale', 'nan'))
            if not sprites[name]:             # CL_ParseStatic refuses a scaled static that is not a sprite
                raise ValueError('aw_flora %s (aw_ref %s) is not a sprite' % (name, e.get('aw_ref')))
            if not (math.isfinite(scale) and scale > 0):
                raise ValueError('aw_flora %s (aw_ref %s) needs a finite positive aw_scale' % (name, e.get('aw_ref')))
        x, y, z = map(float, e['origin'].split())
        cx = min(nx - 1, max(0, int((x - frame_low[0]) // grain)))
        cy = min(ny - 1, max(0, int((y - frame_low[1]) // grain)))
        r = radii[name] * scale
        if (cx, cy) not in by_cell:          # a cell without a chunk (open water): the nearest chunk owns it
            cx, cy = min(by_cell, key=lambda k: ((k[0] - cx) ** 2 + (k[1] - cy) ** 2, k))
        e[CHUNK_KEY] = str(by_cell[(cx, cy)])
        e[BOX_KEY] = ' '.join('%d' % v for v in (math.floor(x - r), math.floor(y - r), math.floor(z - r),
                                                  math.ceil(x + r), math.ceil(y + r), math.ceil(z + r)))
        count += 1
    return count, sum(sizes.values())


# What a map loads into the Hunk after the CHIM zone beyond the client's per-map allocations and its
# sprites, measured in FS-UAE on the CHIM engine (CHIM-ZONE-RESERVE-EARLY-33, engine job, 9 October 2026):
# Balmora 1,609,600 B after the zone = client + 20,256 B (no sprites); Seyda Neen 2,580,400 B = client +
# 964,624 B of sprites + 26,432 B. The load peak includes a 12,768-byte temporary block. HUNK_REST_MARGIN
# covers Balmora's measured load (+4,320 B) and stays below the point where Balmora's zone would drop a
# 16 KiB step (about +6,300 B) and its active ring (6,239,776 B) would no longer fit; Seyda Neen's figure is
# 1,856 B higher, which the engine measures and keeps on its first load (CHIM-ZONE-RESERVE-EARLY-33).
HUNK_REST_MARGIN = 24 * 1024
# A sprite's Hunk blocks beyond its file size (msprite_t, frame headers, Hunk headers and alignment):
# Seyda Neen measured 964,624 B for 26 sprites whose files total 954,414 B, 393 B each; rounded up.
SPRITE_HUNK_OVERHEAD = 512
STREAM_VARIABLE = 'AMIWIND_CHIM_STREAM_STATICS'


def stream_enabled():
    """Whether frame maps tag their statics to stream with their chunks (build setting
    chim_stream_statics, on by default and exported by tools/build.py; an engine without the support
    would load the tagged statics as ordinary ones, so their models would miss the Hunk rest the map
    states). Without the variable (a frame map written outside tools/build.py): off."""
    import os
    value = os.environ.get(STREAM_VARIABLE, '0').strip() or '0'
    if value not in ('0', '1'):
        raise ValueError(STREAM_VARIABLE + ' must be 0 or 1')
    return value == '1'


def hunk_rest(id1, rows):
    """HUNK_KEY: bytes the map loads into the Hunk after the CHIM zone: the client's per-map
    allocations (engine_limits.MEASURED_HUNK), the sprites of the frame map's entities that are not
    streamed, each with SPRITE_HUNK_OVERHEAD (Mod_LoadSpriteModel allocates on the Hunk; alias models
    go to the Cache, model.c Mod_LoadAliasModel: actors measured 0), and HUNK_REST_MARGIN."""
    from engine_limits import MEASURED_HUNK
    models = {e['model'] for e in rows if e.get('model', '').endswith('.spr') and CHUNK_KEY not in e
              and (Path(id1) / e['model']).is_file()}
    return (MEASURED_HUNK['client_per_map_bytes'] + HUNK_REST_MARGIN
            + sum((Path(id1) / m).stat().st_size + SPRITE_HUNK_OVERHEAD for m in models))


# ---------------------------------------------------------------- parity on the frame's own collision

EDGE_KEY = '_chim_edge'
ACTOR_CLASSES = ('aw_npc', 'aw_corpse')
GAP_MIN, GAP_MAX = -0.5, 1.0         # check_actor_ground's support tolerance
# Refit of a ground actor on the frame (CHIM-SEYDA-ACTOR-CONTACT-33): the legacy support fitting baked each
# actor on its region maps' terrain (for Seyda Neen the converted or recorded region maps); the frame's terrain is the
# current builder's and can sit a few units off it. The frame map refits an actor that no longer stands with
# the legacy fitter itself (actor_grounding: the contact interval rule, every sole within GAP_MIN..GAP_MAX,
# its offset order up to 32 units, its walkable-path check from the original spot): first the height alone
# within REFIT_LIMIT of the baked height, then the nearest offset whose height stays within REFIT_DZ.
# The region maps keep their baked placements; only the frame map's row changes, and the change is recorded.
REFIT_LIMIT = 4.5
REFIT_DZ = 8.0


def frame_world(world_dir, cell):
    """(world dict, frame index) of the frame at `cell` (chim.validate.load_world)."""
    from chim.validate import Failures, load_world
    fails = Failures()
    settings, files, sizes, textures, models, frames = load_world(world_dir, fails)
    if fails:
        raise ValueError('CHIM world does not load: ' + '; '.join(fails[:3]))
    index = next(i for i, (_, frame, _) in enumerate(frames) if tuple(frame['cell']) == tuple(cell))
    return {'frames': frames, 'models': models}, index


def actor_contact(id1, rows, world, index):
    """(refusals, record): every ground-resident actor the frame map carries stands on the frame's own
    collision as on the legacy maps. The legacy measurement (check_actor_ground: the lowest
    rendered vertices of the initial idle poses, point hull, gap -0.5..1.0) on the CHIM frame's point
    hull (chunk terrain and placed models, chim.collision.FrameScene). Actors stay actor records:
    only their model's poses are read."""
    from actor_grounding import initial_state
    from check_actor_ground import contact_samples, layout_of, model_frames
    from chim.collision import FrameScene
    scene = FrameScene(world, index, hull=0)
    models, record, refused = {}, [], []
    for e in rows:
        if e.get('classname') not in ACTOR_CLASSES:
            continue
        row = {'reference': e.get('aw_ref'), 'model': e.get('model')}
        try:
            if initial_state(e.get('aw_source_id', '')) != 'ground':
                row['status'] = 'explicit-exception'
                record.append(row)
                continue
        except (ValueError, KeyError):
            pass
        point = tuple(map(float, e['origin'].split()))
        angles = tuple(map(float, e.get('angles', '0 0 0').split()))
        name = e.get('model', '')
        if name not in models:
            # the model's frame layout (tools/actor_frames.py): kit models are checked on their idle group
            models[name] = (model_frames((Path(id1) / name).read_bytes()), layout_of(Path(id1) / name))
        samples = contact_samples(models[name][0], angles, bool(float(e.get('aw_intro_role', 0) or 0)), models[name][1])
        gaps, failures = contact(scene, point, samples)
        if failures:
            new = refit(scene, point, samples)
            if new is not None:
                gaps, failures = contact(scene, new, samples)
                if not failures:
                    text = '%.5f %.5f %.5f' % new
                    row.update(refit_from=[round(v, 5) for v in point],
                               refit_offset=[round(new[k] - point[k], 5) for k in range(3)],
                               refit_dz=round(new[2] - point[2], 5))
                    e['origin'] = text
                    if 'aw_ground_baked' in e:
                        e['aw_ground_baked'] = text
                    point = new
        row.update(status='failed-contact' if failures else 'refitted' if 'refit_dz' in row else 'grounded',
                   samples=len(samples),
                   minimum_gap=round(min(gaps), 3) if gaps else None, maximum_gap=round(max(gaps), 3) if gaps else None,
                   failures=failures[:4])
        if failures:
            refused.append('actor %s (%s) does not stand on the CHIM frame: %s' % (row['reference'], name,
                                                                               failures[0]))
        record.append(row)
    return refused, {'actors': len(record), 'grounded': sum(r['status'] in ('grounded', 'refitted') for r in record),
                     'refitted': sum(r['status'] == 'refitted' for r in record),
                     'tolerance': [GAP_MIN, GAP_MAX], 'refit_limit': REFIT_LIMIT, 'rows': record}


def contact(scene, point, samples):
    """(gaps, failures) of the sole samples at point on the frame's point hull (check_actor_ground)."""
    gaps, failures = [], []
    for local in samples:
        foot = tuple(point[k] + local[k] for k in range(3))
        hit = scene.floor((foot[0], foot[1], foot[2] + 2), 6)
        if hit['status'] == 'supported':
            gap = foot[2] - hit['height']
            gaps.append(gap)
            if not GAP_MIN <= gap <= GAP_MAX:
                failures.append({'foot': [round(v, 3) for v in foot], 'gap': round(gap, 3)})
        else:
            failures.append({'foot': [round(v, 3) for v in foot], 'support': hit['status']})
    return gaps, failures


def refit(scene, point, samples):
    """A standing placement for a ground actor on the frame, by the legacy fitter's rules: the height
    alone (refit_height), else the first offset (actor_grounding.OFFSETS, nearest first) whose sole
    interval fits within REFIT_DZ of the baked height, whose support is within 16 units of the original
    spot's and which the actor can walk to (actor_grounding._Fitter.path_clear); None when none fits."""
    from actor_grounding import OFFSETS, _Fitter, contact_interval_choice
    z = refit_height(scene, point, samples)
    if z is not None:
        return (point[0], point[1], z)
    center = scene.floor((point[0], point[1], point[2] + 8), 40)
    if center['status'] != 'supported':
        return None
    original = (point[0], point[1], center['height'] + .25)
    for dx, dy in OFFSETS:
        x, y = point[0] + dx, point[1] + dy
        support = scene.floor((x, y, point[2] + 8), 40)
        if support['status'] != 'supported' or abs(support['height'] - center['height']) > 16:
            continue
        low, high = point[2] - REFIT_DZ, point[2] + REFIT_DZ
        for local in samples:
            hit = scene.floor((x + local[0], y + local[1], support['height'] + local[2] + 8), 24)
            if hit['status'] != 'supported':
                low = float('inf')
                break
            low = max(low, hit['height'] - local[2] + GAP_MIN)
            high = min(high, hit['height'] - local[2] + GAP_MAX)
            if low > high:
                break
        if low > high:
            continue
        cand = (round(x, 5), round(y, 5), round(contact_interval_choice(low, high, point[2]), 5))
        if _Fitter.contact(scene, cand, samples) and _Fitter.path_clear(scene, original, cand, center['height']):
            return cand
    return None


def refit_height(scene, point, samples):
    """The actor's height on the frame with every sole within GAP_MIN..GAP_MAX (the legacy fitter's
    contact interval, actor_grounding.contact_interval_choice, nearest the baked height), x and y kept;
    None when no height within REFIT_LIMIT of the baked one fits."""
    from actor_grounding import contact_interval_choice
    low, high = point[2] - REFIT_LIMIT, point[2] + REFIT_LIMIT
    for local in samples:
        x, y = point[0] + local[0], point[1] + local[1]
        hit = scene.floor((x, y, point[2] + local[2] + REFIT_LIMIT + 2), 2 * REFIT_LIMIT + 8)
        if hit['status'] != 'supported':
            return None
        low = max(low, hit['height'] - local[2] + GAP_MIN)
        high = min(high, hit['height'] - local[2] + GAP_MAX)
        if low > high:
            return None
    return contact_interval_choice(low, high, point[2])


def arrival_check(id1, town_row, world, index):
    """(refusals, record): the town's arrival is a standing spot on the frame's own collision, by the
    engine's arrival search (arrival_spot.standing / standing_spot) on chim.collision.FrameScene."""
    from arrival_spot import read_directory, standing, standing_spot
    from chim.collision import FrameScene

    class FrameCollision:
        def __init__(self):
            self.hull = FrameScene(world, index)
            self.point = FrameScene(world, index, hull=0)

        def solid(self, p):
            hit = self.hull.trace(p, (p[0], p[1], p[2] - 1e-3))
            return bool(hit and hit['fraction'] == 0)

        def dry(self, p):
            from player_hull import MINS
            return self.point.contents((p[0], p[1], p[2] + MINS[2] + 1)) == -1

        def ground(self, p, depth):
            from player_hull import WALKABLE_Z
            hit = self.hull.trace(p, (p[0], p[1], p[2] - depth))
            if not hit or hit['fraction'] == 0 or hit['normal'][2] < WALKABLE_Z:
                return None
            return p[2] - depth * hit['fraction']
    directory = read_directory(Path(id1) / town_row['regions'])
    point = directory['arrival']
    c = FrameCollision()
    spot = standing_spot(c, point)
    ok = spot is not None and standing(c, point)
    record = {'arrival': list(point), 'spot': list(spot) if spot else None, 'standing': ok}
    return ([] if ok else ['arrival %s is not a standing spot on the CHIM frame' % (list(point),)]), record


def closed_edge(town):
    """True for a town whose frame joins no open world (config/towns.json world_slot < 0): its frame
    map closes the frame with clip walls and tells the engine (EDGE_KEY), which says the area beyond
    is unavailable, as the legacy preview's edge does."""
    from town_config import load_registry
    row = next(t for t in load_registry()['towns'] if t['id'] == town)
    return row.get('world_slot', 0) < 0


def frame_walls(lo, hi, thick=64.0):
    """Four solid boxes just outside the frame bounds, floor to ceiling."""
    return wall_boxes((lo[0], lo[1], hi[0], hi[1]), lo, hi, thick)


def build(id1, town, world_dir, entity_rows=None):
    """Write maps/<town>-chim.bsp under id1 from the town's final region maps; returns the record.
    entity_rows: the town's entities made from the game data (tools/chim_town.py) when the town has
    no legacy region maps (CHIM-LEGACY-CHAIN-33); the origin check needs region maps and is skipped,
    every other check runs. Raises ValueError when anything cannot be carried."""
    from entity_tracker import bsp_refs
    from town_config import runtime_towns
    id1 = Path(id1)
    row = next((t for t in runtime_towns() if t['id'] == town), None)
    if row is None:
        raise ValueError('Unknown town: ' + town)
    from harvest_build import town_origin
    from town_config import load_settings
    point, regions = region_table(id1 / row['regions'])
    maps = None if entity_rows is not None else \
        {name: entities((id1 / 'maps' / (name + '.bsp')).read_bytes()) for name, _ in regions}
    # the town's frame: the frame at its source cell (a world may hold several areas)
    if town == 'seyda':
        from chim.seyda import source_cell     # format 0.5: Seyda Neen's frame (no town converter settings)
        town_cell = tuple(source_cell())
    else:
        town_cell = tuple(load_settings(town)['source_cell'])
    placed = chim_placements(world_dir, town_cell)
    if entity_rows is None:
        rows, report = frame_entities(maps, set(placed), default_region(point, regions))
    else:
        rows = [dict(e) for e in entity_rows]
        counts = collections.Counter(e.get('classname', '') for e in rows)
        report = {'source': 'game data (tools/chim_town.py); no legacy region maps',
                  'classes': {c: {'written': n} for c, n in sorted(counts.items())}, 'refused': []}
    _, _, _, _, frame_centre = frame_record(world_dir, town_cell)
    if entity_rows is None:
        refused, report['origin_check'] = origin_check(maps, placed, frame_centre, town_origin(town))
        report['refused'] += refused
    else:
        report['origin_check'] = 'not applicable: no legacy region maps'
    refused, report['harvest_check'] = harvest_check(id1, [name for name, _ in regions])
    report['refused'] += refused
    refused, report['static_check'] = static_check(rows)
    report['refused'] += refused
    # Parity on the frame's own collision (M3): actors stand, the arrival is a standing spot.
    world, index = frame_world(world_dir, town_cell)
    refused, report['actor_contact'] = actor_contact(id1, rows, world, index)
    report['refused'] += refused
    refused, report['arrival_check'] = arrival_check(id1, row, world, index)
    report['refused'] += refused
    if report['refused']:
        raise ValueError('CHIM frame map for %s: %s' % (town, '; '.join(report['refused'][:6])))
    cell, lo, hi = frame_bounds(world_dir, town_cell)
    rows[0][FRAME_KEY] = '%d %d' % cell
    streamed, streamed_bytes = 0, 0
    if stream_enabled():
        streamed, streamed_bytes = stream_statics(id1, rows, *frame_grid(world_dir, cell))
        rows[0][COUNT_KEY] = str(streamed)
    rows[0][HUNK_KEY] = str(hunk_rest(id1, rows))
    report['streamed_statics'] = {'count': streamed, 'model_bytes': streamed_bytes, 'hunk_rest': int(rows[0][HUNK_KEY])}
    lumps = empty_world(lo, hi)
    report['closed_edge'] = closed_edge(town)
    if report['closed_edge']:
        rows[0][EDGE_KEY] = 'closed'
        lumps, numbers = add_clip_models(lumps, frame_walls(lo, hi))
        rows += [{'classname': 'func_wall', 'model': '*%d' % n, 'aw_clip': town + ' frame edge'} for n in numbers]
    found, refused = activated_entities(id1, [name for name, _ in regions])
    lumps, report['activated'] = keep_activated(lumps, rows, found)
    refused += activated_check(rows, found)
    if refused:
        raise ValueError('CHIM frame map for %s: %s' % (town, '; '.join(refused[:6])))
    lumps[0] = entity_text(rows)
    data = F.brush_image(lumps)[0]
    path = id1 / 'maps' / (map_name(row['name']) + '.bsp')      # the engine: maps/<town map>-chim.bsp
    if path.exists():
        raise ValueError('CHIM frame map already present: ' + path.name)
    path.write_bytes(data)
    refs = bsp_refs(data)                       # the entity tracker's own reader
    import hashlib
    return dict(report, map='maps/' + path.name, frame=list(cell), bounds=[list(lo), list(hi)],
                bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), tracker_refs=len(refs),
                entities=len(rows))


# ---------------------------------------------------------------- Seyda Neen's special maps (format 0.5)

DOCKS = 'intro_docks'
DOCKS_WALL = 64.0          # thickness of each boundary clip wall (frame-local units)


def special_bounds(name):
    """The route bounds of Seyda Neen's special maps (prepare_seyda_regions specials): the intro docks
    and the Census courtyard."""
    if name == DOCKS:
        from prepare_intro_docks import BOUNDS
        return tuple(BOUNDS)
    if name == 'sncourt':
        from prepare_seyda_regions import COURTYARD
        return tuple(COURTYARD)
    raise ValueError('Not a special map of Seyda Neen: ' + name)


SPECIALS = (DOCKS, 'sncourt')


# ---------------------------------------------------------------- objects the engine activates by aw_ref

ACTIVATED_HEADER = ROOT / 'engine' / 'aga' / 'src' / 'aw_activated.h'
ACTIVATED_DEFINE = re.compile(r'^#define\s+(AW_REF_\w+)\s+(\d+)\s*$', re.M)
# The kept edict's box is the region-map model's box grown by this much, so a trace toward the object
# meets the edict before the chunk placement's own collision (world.c AW_MergeCollisionTrace keeps the
# earlier hit; a tie keeps the world).
ACTIVATED_MARGIN = 1.0


def activated_refs(path=ACTIVATED_HEADER):
    """{aw_ref: name} of the objects the engine activates as func_wall edicts (aw_activated.h:
    one "#define AW_REF_<NAME> <number>" per object; the engine's code uses the same names)."""
    found = {int(v): n for n, v in ACTIVATED_DEFINE.findall(Path(path).read_text(encoding='ascii'))}
    if not found:
        raise ValueError('No AW_REF_ defines in ' + Path(path).name)
    return found


def model_bounds(data, number):
    """(mins, maxs) of brush model `number` of a BSP29 map (model-local)."""
    offset, size = struct.unpack_from('<ii', data, 4 + 14 * 8)
    if number < 1 or (number + 1) * 64 > size:
        raise ValueError('brush model *%d is not in the map' % number)
    m = struct.unpack_from('<6f', data, offset + 64 * number)
    return m[:3], m[3:]


def activated_entities(id1, names, refs=None):
    """(rows, refusals): the func_walls of the region maps `names` whose aw_ref the engine activates,
    once per reference, each with its model's box ('_box': (mins, maxs), model-local). The same
    reference with other keys or another box in another region is refused."""
    refs = activated_refs() if refs is None else refs
    found, refused = {}, []
    for name in sorted(names):
        data = (Path(id1) / 'maps' / (name + '.bsp')).read_bytes()
        for e in entities(data):
            ref = e.get('aw_ref', '')
            if e.get('classname') != 'func_wall' or not ref.isdigit() or int(ref) not in refs:
                continue
            if not e.get('model', '').startswith('*'):
                refused.append('%s: activated object %s has no brush model' % (name, ref))
                continue
            row = {k: v for k, v in e.items() if k != 'model'}
            row['_box'] = tuple(tuple(round(v, 4) for v in b) for b in model_bounds(data, int(e['model'][1:])))
            if ref in found and found[ref] != row:
                refused.append('%s: activated object %s (%s) differs between regions'
                               % (name, ref, refs[int(ref)]))
                continue
            found[ref] = row
    return [found[k] for k in sorted(found, key=int)], refused


def keep_activated(lumps, rows, found, refs=None):
    """Append the activated objects (activated_entities) to a frame map: one collision-only brush
    model each (add_clip_models: the model's box grown by ACTIVATED_MARGIN, nothing drawn) and its
    func_wall with the region map's keys. Returns (lumps, record)."""
    refs = activated_refs() if refs is None else refs
    boxes = [(tuple(v - ACTIVATED_MARGIN for v in r['_box'][0]), tuple(v + ACTIVATED_MARGIN for v in r['_box'][1]))
             for r in found]
    numbers = []
    if boxes:
        lumps, numbers = add_clip_models(lumps, boxes)
    for r, n in zip(found, numbers):
        rows.append({**{k: v for k, v in r.items() if k != '_box'}, 'model': '*%d' % n})
    return lumps, {'kept': [{'ref': int(r['aw_ref']), 'name': refs[int(r['aw_ref'])], 'model': '*%d' % n}
                            for r, n in zip(found, numbers)], 'margin': ACTIVATED_MARGIN}


def activated_check(rows, found):
    """Refusals: every activated object of the region maps has its func_wall edict in the frame map."""
    have = {e.get('aw_ref') for e in rows if e.get('classname') == 'func_wall' and e.get('model', '').startswith('*')}
    return ['activated object %s has no edict in the frame map' % r['aw_ref'] for r in found
            if r['aw_ref'] not in have]


def wall_boxes(bounds, lo, hi, thick=DOCKS_WALL):
    """Four solid boxes just outside the docks' route bounds (x0, y0, x1, y1), floor to ceiling:
    the standing boundary the legacy docks map has as four clip planes (prepare_intro_docks)."""
    x0, y0, x1, y1 = bounds
    z0, z1 = lo[2], hi[2]
    return [((x0 - thick, y0 - thick, z0), (x0, y1 + thick, z1)), ((x1, y0 - thick, z0), (x1 + thick, y1 + thick, z1)),
            ((x0, y0 - thick, z0), (x1, y0, z1)), ((x0, y1, z0), (x1, y1 + thick, z1))]


def add_clip_models(lumps, boxes):
    """Append collision-only brush models (no faces) to a map's lumps: one per box, point hull and
    standing hull made by the shared model writer (chim.models.model_image_lumps, the placed models'
    own collision chain), relocated into the map's planes, nodes, leaves and clipnodes. Quake's
    clip brushes as func_wall entities: the server collides with them, nothing is drawn.
    Returns the new model numbers."""
    import numpy as np
    from chim.models import model_image_lumps
    lumps = [bytearray(x) for x in lumps]
    numbers = []
    for lo, hi in boxes:
        corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])], float)
        w = model_image_lumps([], [(corners, None, [], 0.)], lo, hi, lambda m: 0)[0]
        pbase, nbase, lbase, cbase = len(lumps[1]) // 20, len(lumps[5]) // 24, len(lumps[10]) // 28, len(lumps[9]) // 8
        lumps[1] += w[1]
        leaf_map = list(range(lbase, lbase + len(w[10]) // 28))
        lumps[10] += w[10]

        def child(c):
            return c + nbase if c >= 0 else -(leaf_map[-c - 1]) - 1
        for p, a, b, *rest in struct.iter_unpack('<ihh6h2H', bytes(w[5])):
            lumps[5] += struct.pack('<ihh6h2H', p + pbase, child(a), child(b), *rest)
        for p, a, b in struct.iter_unpack('<iHH', bytes(w[9])):
            lumps[9] += struct.pack('<iHH', p + pbase, *((c if c >= 0xFFF0 else c + cbase) for c in (a, b)))
        m = list(struct.unpack('<9f7i', bytes(w[14][:64])))
        m[9] = m[9] + nbase if m[9] >= 0 else -(leaf_map[-m[9] - 1]) - 1
        for k in (10, 11, 12):
            m[k] = m[k] + cbase if m[k] >= 0 else m[k]
        m[14], m[15] = 0, 0
        numbers.append(len(lumps[14]) // 64)
        lumps[14] += struct.pack('<9f7i', *m)
    return [bytes(x) for x in lumps], numbers


# The intro's escort route (aw_opening.c dock_route: the guard's two goals, town-local units).
DOCK_ROUTE = ((587.5, -353.25), (299.0, -202.0))
WALK_SPACING = 16.0
ROUTE_TOLERANCE = 24.0     # a route goal counts as reached within this distance (aw_nav arrival radius)
WALK_COVERAGE = 0.95        # CHIM must reach at least this share of what the legacy map lets the player reach


def walkable_area(scene, bounds, seed, spacing=WALK_SPACING, drop=64.0, void=2048.0):
    """The player's reachable floor inside bounds from seed (x, y, z): a flood fill that walks the
    standing box from sample to sample at its own level (step up STEP_HEIGHT, then down to the next
    walkable floor), so ground under roofs, decks and gangways counts. A step whose floor lies more
    than `drop` below is a ledge (not followed); one with no floor within `void` is a hole in the
    collision. Returns {'reachable': {(i, j): height}, 'holes': [(i, j)], 'shape', 'spacing'}."""
    from collections import deque
    from player_hull import STEP_HEIGHT, WALKABLE_Z
    x0, y0, x1, y1 = bounds
    nx, ny = int((x1 - x0) // spacing) + 1, int((y1 - y0) // spacing) + 1
    sx, sy, sz = seed

    def floor(x, y, top, reach=void):
        hit = scene.trace((x, y, top), (x, y, top - reach))
        if not hit or hit['fraction'] == 0:
            return None, hit
        return top - reach * hit['fraction'], hit
    i0, j0 = round((sx - x0) / spacing), round((sy - y0) / spacing)
    h, hit = floor(x0 + i0 * spacing, y0 + j0 * spacing, sz + STEP_HEIGHT)
    if h is None or hit['normal'][2] < WALKABLE_Z:
        raise ValueError('the start has no walkable floor')
    reach, holes = {(i0, j0): h}, set()
    queue = deque([(i0, j0)])
    while queue:
        i, j = queue.popleft()
        hz = reach[(i, j)]
        ax, ay = x0 + i * spacing, y0 + j * spacing
        up = hz + STEP_HEIGHT + 0.125
        if scene.trace((ax, ay, hz + 0.125), (ax, ay, up)):
            continue                                            # a low ceiling: no step from here
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            k = (i + di, j + dj)
            if k in reach or not (0 <= k[0] < nx and 0 <= k[1] < ny):
                continue
            bx, by = x0 + k[0] * spacing, y0 + k[1] * spacing
            if scene.trace((ax, ay, up), (bx, by, up)):
                continue                                        # a wall: not this way
            # the walkable floor is within the drop; only a step past it needs the long look for a hole
            fz, fhit = floor(bx, by, up, STEP_HEIGHT + drop + 0.25)
            if fz is None and fhit is None:
                fz, fhit = floor(bx, by, up)
            if fz is None:
                if fhit is None:
                    holes.add(k)                                # nothing below: a hole in the collision
                continue
            if fhit['normal'][2] < WALKABLE_Z or hz - fz > drop:
                continue                                        # too steep, or a ledge
            reach[k] = fz
            queue.append(k)
    return {'reachable': reach, 'holes': sorted(holes), 'shape': [nx, ny], 'spacing': spacing}


def walk_check(id1, name, world, index, rows, bounds):
    """(refusals, record) for a special map's walkable area on the CHIM frame (owner, 9 October 2026:
    "be mindful of the walkable areas"):
    1. the area the player can reach from the map's start has no holes: no reachable floor next to a
       sample with no floor at all;
    2. the intro's escort route goals (intro docks) are as close to reachable floor on CHIM as on the
       legacy map (within ROUTE_TOLERANCE; the second goal is the Census door, inside the wall's solid
       on both: the guard stops at the nearest floor);
    3. the legacy map (still in id1) lets the player reach no floor that CHIM does not: at least
       WALK_COVERAGE of the legacy reachable samples are reachable on CHIM.
    Nothing leads outside: the frame map's clip walls close the bounds from floor to ceiling
    (wall_boxes); the scan stays inside them."""
    from chim.collision import FrameScene
    start = next((e for e in rows if e.get('classname') == 'info_player_start'), None)
    if start is None:
        return ['%s: no info_player_start to walk from' % name], {}
    seed = tuple(map(float, start['origin'].split()))
    scene = FrameScene(world, index)
    x0, y0, x1, y1 = bounds
    try:
        chim = walkable_area(scene, bounds, seed)
    except ValueError as exc:
        return ['%s: the start %s is not on CHIM floor (%s)' % (name, list(seed), exc)], {}
    refused = []
    reach = set(chim['reachable'])
    holes = chim['holes']
    if holes:
        refused.append('%s: %d places next to a hole in the CHIM collision (first %.0f %.0f)'
                       % (name, len(holes), x0 + holes[0][0] * WALK_SPACING, y0 + holes[0][1] * WALK_SPACING))
    record = {'spacing': WALK_SPACING, 'samples': chim['shape'][0] * chim['shape'][1], 'reachable': len(reach),
              'holes': len(holes)}
    lreach = None
    legacy_path = Path(id1) / 'maps' / (name + '.bsp')
    if legacy_path.is_file():
        # the stair gate's legacy scene: traces only brush models whose bounds reach the segment, as the
        # engine links them (the plain scan walked every model's hull: 10 minutes on the intro docks)
        from stair_walk import Collision
        try:
            legacy = walkable_area(Collision(legacy_path.read_bytes()), bounds, seed)
            lreach = set(legacy['reachable'])
            share = len(lreach & reach) / max(1, len(lreach))
            record.update(legacy_reachable=len(lreach), legacy_covered=round(share, 4),
                          chim_only=len(reach - lreach))
            if share < WALK_COVERAGE:
                refused.append('%s: CHIM reaches %.1f %% of the legacy walkable area (at least %.0f %%)'
                               % (name, 100 * share, 100 * WALK_COVERAGE))
        except ValueError as exc:
            record['legacy'] = 'not compared: %s' % exc
    if name == DOCKS:
        record['route'] = []
        for px, py in DOCK_ROUTE:
            near = nearest_reach(reach, bounds, (px, py))
            limit = ROUTE_TOLERANCE + (nearest_reach(lreach, bounds, (px, py)) if lreach else 0.0)
            record['route'].append({'point': [px, py], 'nearest': round(near, 1), 'limit': round(limit, 1)})
            if near > limit:
                refused.append('%s: the escort route goal %.1f %.1f is %.0f units from reachable CHIM floor '
                               '(at most %.0f)' % (name, px, py, near, limit))
    return refused, record


def nearest_reach(reach, bounds, point):
    """Distance from point (x, y) to the nearest reachable sample of a walkable_area grid."""
    x0, y0 = bounds[0], bounds[1]
    return min(((x0 + i * WALK_SPACING - point[0]) ** 2 + (y0 + j * WALK_SPACING - point[1]) ** 2) ** 0.5
               for i, j in reach) if reach else float('inf')


def build_docks(id1, world_dir, town='seyda', name=DOCKS):
    """maps/<special>-chim.bsp: the intro docks (or the Census courtyard, sncourt) as another frame
    map of Seyda Neen's frame.

    The legacy docks map (prepare_seyda_regions specials: the bounded town with the route mask,
    prepare_intro_docks.derive) holds a subset of the town's statics and the intro's own entities.
    Here its statics must all be in the CHIM frame (one way: the frame draws the whole town around
    the docks), its point entities are copied (the start, the intro actors, flora sprites), and its
    standing boundary becomes four clip walls (func_wall brush models without faces). Coordinates and
    origin are the town's."""
    from entity_tracker import bsp_refs
    from harvest_build import town_origin
    from chim.seyda import source_cell
    BOUNDS = special_bounds(name)
    id1 = Path(id1)
    maps = {name: entities((id1 / 'maps' / (name + '.bsp')).read_bytes())}
    cell = tuple(source_cell())
    placed = chim_placements(world_dir, cell)
    rows, report = frame_entities(maps, set(placed), name)
    # one way: the docks map's statics are in the frame; the frame holds the rest of the town as well
    report['refused'] = [r for r in report['refused'] if 'CHIM statics are not in the final region maps' not in r]
    report['chim_statics_not_in_maps'] = len(report['chim_statics_not_in_maps'])
    _, _, _, _, frame_centre = frame_record(world_dir, cell)
    refused, report['origin_check'] = origin_check(maps, placed, frame_centre, town_origin(town))
    report['refused'] += refused
    refused, report['harvest_check'] = harvest_check(id1, [name])
    report['refused'] += refused
    refused, report['static_check'] = static_check(rows)
    report['refused'] += refused
    world, index = frame_world(world_dir, cell)
    refused, report['walk_check'] = walk_check(id1, name, world, index, rows, BOUNDS)
    report['refused'] += refused
    if report['refused']:
        raise ValueError('CHIM frame map for %s: %s' % (name, '; '.join(report['refused'][:6])))
    cell, lo, hi = frame_bounds(world_dir, cell)
    rows[0][FRAME_KEY] = '%d %d' % cell
    streamed, streamed_bytes = 0, 0
    if stream_enabled():
        streamed, streamed_bytes = stream_statics(id1, rows, *frame_grid(world_dir, cell))
        rows[0][COUNT_KEY] = str(streamed)
    rows[0][HUNK_KEY] = str(hunk_rest(id1, rows))
    report['streamed_statics'] = {'count': streamed, 'model_bytes': streamed_bytes, 'hunk_rest': int(rows[0][HUNK_KEY])}
    lumps, numbers = add_clip_models(empty_world(lo, hi), wall_boxes(BOUNDS, lo, hi))
    for n in numbers:
        rows.append({'classname': 'func_wall', 'model': '*%d' % n, 'aw_clip': name + ' boundary'})
    found, refused = activated_entities(id1, [name])
    lumps, report['activated'] = keep_activated(lumps, rows, found)
    refused += activated_check(rows, found)
    if refused:
        raise ValueError('CHIM frame map for %s: %s' % (name, '; '.join(refused[:6])))
    lumps[0] = entity_text(rows)
    data = F.brush_image(lumps)[0]
    path = id1 / 'maps' / (map_name(name) + '.bsp')
    if path.exists():
        raise ValueError('CHIM frame map already present: ' + path.name)
    path.write_bytes(data)
    import hashlib
    return dict(report, map='maps/' + path.name, frame=list(cell), bounds=[list(lo), list(hi)], route=list(BOUNDS),
                clip_walls=len(numbers), bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                tracker_refs=len(bsp_refs(data)), entities=len(rows))


# ---------------------------------------------------------------- pure CHIM images

def legacy_area_maps(id1, town):
    """The legacy exterior maps of a town in an image: every region map its region table names, the
    town's own map name (the fallback region alias, e.g. seyda.bsp) and, for Seyda Neen, its special
    maps (intro_docks.bsp, sncourt.bsp). Paths relative to id1 that exist. The region table stays: the
    engine's per-region harvest catalogues follow it under CHIM (AW_RegionAt)."""
    from town_config import runtime_towns
    id1 = Path(id1)
    row = next((t for t in runtime_towns() if t['id'] == town), None)
    if row is None:
        raise ValueError('Unknown town: ' + town)
    names = []
    if (id1 / row['regions']).is_file():
        names += [name for name, _ in region_table(id1 / row['regions'])[1]]
    names.append(row['name'])
    if town == 'seyda':
        names += list(SPECIALS)
    return [('maps/%s.bsp' % n) for n in dict.fromkeys(names) if (id1 / 'maps' / (n + '.bsp')).is_file()]


def remove_legacy_areas(id1, towns, reason):
    """Remove the legacy exterior maps of these towns from an image's id1 (legacy_area_maps); returns
    one row per removed file (file, bytes, sha256, town, reason) for the build record. The one
    mechanism for a pure CHIM image (reason: the town runs on CHIM) and for leaving out areas a
    partial image does not build."""
    import hashlib
    id1 = Path(id1)
    rows = []
    for town in towns:
        for rel in legacy_area_maps(id1, town):
            path = id1 / rel
            data = path.read_bytes()
            rows.append({'file': rel, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                         'town': town, 'reason': reason})
            path.unlink()
    return rows


NOT_ON_CHIM = 'not on CHIM yet'


def town_files(id1, town):
    """Every image file of an extra town that serves its exterior only: its legacy exterior maps
    (legacy_area_maps), any region map left by its prefix, its region table, its door table and the
    harvest catalogues of its regions. Paths relative to id1 that exist."""
    from town_config import load_settings, runtime_towns, town_field
    id1 = Path(id1)
    row = next((t for t in runtime_towns() if t['id'] == town), None)
    if row is None:
        raise ValueError('Unknown town: ' + town)
    names = list(legacy_area_maps(id1, town))
    regions = [name for name, _ in region_table(id1 / row['regions'])[1]] if (id1 / row['regions']).is_file() else []
    names += sorted('maps/' + p.name for p in (id1 / 'maps').glob(row['prefix'] + '[0-9][0-9][0-9].bsp'))
    names += [row['regions'], town_field(load_settings(town), 'door_file')]
    names += ['harvest-%s.txt' % name for name in regions]
    return [n for n in dict.fromkeys(names) if (id1 / n).is_file()]


def remove_towns_not_on_chim(id1, towns):
    """Leave extra towns that are not on CHIM yet out of a CHIM image (town_files: exterior maps,
    region and door tables, harvest catalogues); their destinations are then not found in the engine
    (AW_SceneMapSize). Seyda Neen and Balmora are refused: the game starts there. Returns one row per
    removed file, as remove_legacy_areas (reason NOT_ON_CHIM)."""
    import hashlib
    from town_config import FIXED_TOWNS
    id1 = Path(id1)
    fixed = [t for t in towns if t in FIXED_TOWNS]
    if fixed:
        raise ValueError('Not an extra town: ' + ', '.join(fixed))
    rows = []
    for town in towns:
        for rel in town_files(id1, town):
            path = id1 / rel
            data = path.read_bytes()
            rows.append({'file': rel, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                         'town': town, 'reason': NOT_ON_CHIM})
            path.unlink()
    return rows


def require_no_legacy_areas(id1, towns, where, not_on_chim=()):
    """The safety net of a CHIM image: no legacy exterior map of a CHIM town (legacy_area_maps) is in
    id1 when the image is packed. Raises ValueError naming every such map; returns the record for
    build.json (status, areas, where the check ran, maps checked = 0 found). not_on_chim: extra
    towns left out of the image (remove_towns_not_on_chim); none of their files may be there either."""
    found = [(town, rel) for town in towns for rel in legacy_area_maps(id1, town)]
    found += [(town, rel) for town in not_on_chim for rel in town_files(id1, town)]
    if found:
        raise ValueError('CHIM build: %d legacy exterior map(s) of CHIM areas in the image (%s): %s'
                         % (len(found), where, ', '.join('%s (%s)' % (rel, town) for town, rel in found)))
    return {'status': 'passed', 'areas': list(towns), 'not_on_chim': list(not_on_chim), 'checked': where,
            'legacy_maps_found': 0}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('id1', type=Path, help='the boot id1 folder holding the final region maps')
    ap.add_argument('town')
    ap.add_argument('chim_world', type=Path, help='tools/chim_build.py output folder')
    ap.add_argument('--json', type=Path)
    a = ap.parse_args(argv)
    try:
        record = (build_docks(a.id1, a.chim_world, name=a.town) if a.town in SPECIALS
                  else build(a.id1, a.town, a.chim_world))
    except ValueError as exc:
        ap.exit(1, 'Error: %s\n' % exc)
    text = json.dumps(record, indent=1, sort_keys=True) + '\n'
    if a.json:
        a.json.write_text(text, encoding='utf-8', newline='\n')
    sys.stdout.write(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
