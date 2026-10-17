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


def streamed_static_limit():
    """The engine's limit of streamed statics in one frame map (chim/chim_statics.c CHIM_MAX_STATICS): tagged
    statics live in that list, built while their chunk is active, never in cl_static_entities."""
    from engine_limits import define
    return define('chim/chim_statics.c', 'CHIM_MAX_STATICS')


def static_check(rows, limit=None, streamed=None):
    """(refusals, record): the frame map's static entities (STATIC_CLASSES) fit the engine's limit. With static
    streaming on (stream_enabled, the default build setting) every one of them is tagged and streamed
    (STREAMED_CLASSES), so the limit is the streamed list's (CHIM_MAX_STATICS), not MAX_STATIC_ENTITIES
    (v0.0.41-dev2: Seyda Neen's cell-aligned frame holds 1,012)."""
    streamed = stream_enabled() if streamed is None else streamed
    if limit is None:
        limit = streamed_static_limit() if streamed else static_entity_limit()
    label = 'CHIM_MAX_STATICS, streamed' if streamed else 'MAX_STATIC_ENTITIES'
    count = sum(1 for e in rows if e.get('classname') in STATIC_CLASSES)
    refused = [] if count <= limit else ['%d static entities, the engine holds %d (%s)' % (count, limit, label)]
    return refused, {'static_entities': count, 'limit': limit, 'limit_name': label, 'headroom': limit - count}
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


def load(world_dir):
    """The CHIM world read and checked once (chim.validate.load_world): {'settings', 'files', 'sizes',
    'textures', 'models', 'frames'}. The image step loads it once and hands it to every frame map it
    writes (world=); each lookup used to read and check the whole world again, about 5 s per CHIM region
    frame on the 270-frame coast world (BUILD-IMAGE-CHIM-MAPS-SERIAL-36). Read only by its users."""
    from chim.validate import Failures, load_world
    fails = Failures()
    settings, files, sizes, textures, models, frames = load_world(world_dir, fails)
    if fails:
        raise ValueError('CHIM world does not load: ' + '; '.join(fails[:3]))
    return {'settings': settings, 'files': files, 'sizes': sizes, 'textures': textures, 'models': models,
            'frames': frames}


def chim_placements(world_dir, cell=None, world=None):
    """{ref: frame-local origin} of the CHIM world's placements (of the frame at `cell` only, if given).
    A cut placement (chim.cut) is listed under its source reference with origin None: its pieces sit at
    their chunks' centres, not at the placement's origin. world: the world already loaded (load)."""
    from chim.cut import source_ref
    frames = (world or load(world_dir))['frames']
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
    # every static is tagged: an untagged one would become a Quake static (MAX_STATIC_ENTITIES, the engine's
    # load-time fallback) while static_check counted it against the streamed list
    total = sum(1 for e in rows if e.get('classname') in STREAMED_CLASSES)
    if count != total:
        raise ValueError('Frame map statics: %d of %d tagged for streaming' % (count, total))
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


def startup_sound_scratch(id1):
    """Quick-character startup uses AmiQuake S_LoadSound's 1 KiB stack buffer.

    Larger WAVs use COM_LoadStackFile -> Hunk_TempAlloc(length + 1).
    Reserve the largest sequential temporary buffer, not their sum. Ordinary
    images without skip-census retain their existing frame reserve.
    """
    import hashlib
    root = Path(id1)
    config = root / 'default-game.cfg'
    raw = config.read_bytes() if config.is_file() else b''
    enabled = False
    for line in raw.decode('utf-8').splitlines():
        fields = line.split('//', 1)[0].split()
        if len(fields) == 2 and fields[0] == 'aw_skip_census':
            enabled = float(fields[1].strip('"')) != 0
    inputs = {'config': hashlib.sha256(raw).hexdigest()}
    peak = 0
    if enabled:
        for name in ('intro/chargen_class1.wav', 'intro/chargendock2.wav',
                     'pool/a5db2581e86f75e13.wav'):
            path = root / 'sound' / name
            if not path.is_file():
                inputs[name] = None
                continue
            data = path.read_bytes()
            inputs[name] = hashlib.sha256(data).hexdigest()
            if len(data) > 44 and len(data) + 1 > 1024:
                # 16-byte hunk header; payload aligned to 16 by Hunk_TempAlloc.
                peak = max(peak, 16 + ((len(data) + 1 + 15) & ~15))
    return {'bytes': peak, 'inputs': inputs}


def hunk_rest(id1, rows):
    """HUNK_KEY: bytes the map loads into the Hunk after the CHIM zone: the client's per-map
    allocations (engine_limits.MEASURED_HUNK), the sprites of the frame map's entities that are not
    streamed, each with SPRITE_HUNK_OVERHEAD (Mod_LoadSpriteModel allocates on the Hunk; alias models
    go to the Cache, model.c Mod_LoadAliasModel: actors measured 0), and HUNK_REST_MARGIN."""
    from engine_limits import MEASURED_HUNK
    models = {e['model'] for e in rows if e.get('model', '').endswith('.spr') and CHUNK_KEY not in e
              and (Path(id1) / e['model']).is_file()}
    return (MEASURED_HUNK['client_per_map_bytes'] + HUNK_REST_MARGIN + startup_sound_scratch(id1)['bytes']
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


def frame_world(world_dir, cell, world=None):
    """(world dict, frame index) of the frame at `cell` (chim.validate.load_world; world: already loaded)."""
    world = world or load(world_dir)
    frames, models = world['frames'], world['models']
    index = next(i for i, (_, frame, _) in enumerate(frames) if tuple(frame['cell']) == tuple(cell))
    return {'frames': frames, 'models': models}, index


ACCEPTED_ACTORS_VARIABLE = 'AMIWIND_ACCEPTED_FRAME_ACTORS'


def accepted_actor_refs():
    """Original references of frame actors the maintainer accepted as known findings for a private test build
    (build_aga.py exports them from --allow-known-actor-ground-findings; empty otherwise)."""
    import os
    return {r for r in os.environ.get(ACCEPTED_ACTORS_VARIABLE, '').split(',') if r.isdigit()}


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
        if failures and str(row['reference']) in accepted_actor_refs():
            # a maintainer-accepted known finding of a private test build: recorded, not refused
            row['status'] = 'owner-accepted-known-finding'
            print('WARNING: PRIVATE TEST ONLY: frame actor %s does not stand on the CHIM frame (accepted): %s'
                  % (row['reference'], failures[0]), flush=True)
        elif failures:
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
    alone (refit_height), else the first offset (actor_grounding.search_offsets, nearest first) whose sole
    interval fits within REFIT_DZ of the baked height, whose support is within 16 units of the original
    spot's and which the actor can walk to (actor_grounding._Fitter.path_clear); None when none fits."""
    from actor_grounding import _Fitter, contact_interval_choice, search_offsets
    z = refit_height(scene, point, samples)
    if z is not None:
        return (point[0], point[1], z)
    center = scene.floor((point[0], point[1], point[2] + 8), 40)
    if center['status'] != 'supported':
        return None
    original = (point[0], point[1], center['height'] + .25)
    for dx, dy in search_offsets():
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


def build(id1, town, world_dir, entity_rows=None, world=None, activated_rows=None):
    """Write the town's frame map maps/<town>-chim.chim under id1 (.bsp with chim_frame_ext bsp; the one
    map path helper, tools/map_files.py) from the town's final region maps; returns the record.
    entity_rows: the town's entities made from the game data (tools/chim_town.py) when the town has
    no legacy region maps (CHIM-LEGACY-CHAIN-33); the origin check needs region maps and is skipped,
    every other check runs. world: the CHIM world already loaded (load). activated_rows: with entity_rows, the
    objects the engine activates as edicts (activated_entities' rows, '_box' model-local) when the town's stage
    took them from the game data (CHIM-native Seyda Neen, tools/chim_town.py). Raises ValueError when anything
    cannot be carried."""
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
    placed = chim_placements(world_dir, town_cell, world=world)
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
    world, index = frame_world(world_dir, town_cell, world=world)
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
    if entity_rows is None:
        found, refused = activated_entities(id1, [name for name, _ in regions])
    else:
        # A CHIM-native town has no legacy region maps to take activated edicts from
        # (BUILD-IMAGE-CHIM-NATIVE-TOWN-36): its stage gives them (activated_rows), or none of its frame's
        # placements may need one.
        found = native_activated_rows(activated_rows)
        refused = native_activated_check({r: o for r, o in placed.items() if str(r) not in {f['aw_ref'] for f in found}})
    lumps, report['activated'] = keep_activated(lumps, rows, found)
    refused += activated_check(rows, found)
    if refused:
        raise ValueError('CHIM frame map for %s: %s' % (town, '; '.join(refused[:6])))
    lumps[0] = entity_text(rows)
    data = F.brush_image(lumps)[0]
    from map_files import frame_map_path, map_files
    path = frame_map_path(id1, map_name(row['name']))      # the engine: AW_MapPath("<town map>-chim")
    if map_files(id1 / 'maps', map_name(row['name'])):
        raise ValueError('CHIM frame map already present: ' + map_files(id1 / 'maps', map_name(row['name']))[0].name)
    path.write_bytes(data)
    refs = bsp_refs(data)                       # the entity tracker's own reader
    import hashlib
    return dict(report, map='maps/' + path.name, frame=list(cell), bounds=[list(lo), list(hi)],
                bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), tracker_refs=len(refs),
                entities=len(rows))


# ---------------------------------------------------------------- CHIM region frames (open world)

REGION_POINT_CLASSES = ('info_player_start', 'aw_flora', 'aw_static', 'aw_sound', 'ambient_sound')


def world_directory(id1):
    """[(name, origin xyz, core (x0, y0, x1, y1))] of the image's open-world maps (world/regions.awr, AWR2)."""
    raw = (Path(id1) / 'world/regions.awr').read_bytes()
    if raw[:4] != b'AWR2':
        raise ValueError('Invalid world region directory')
    count = struct.unpack_from('<I', raw, 4)[0]
    return [('vf%04d' % i, struct.unpack_from('<3f', raw, 64 + 52 * i + 8),
             struct.unpack_from('<4f', raw, 64 + 52 * i + 20)) for i in range(count)]


def alias_rows(raw):
    """{alias name: the row it repeats} of an open-world directory (world/regions.awr bytes, AWR2): a row whose origin,
    core and coverage are byte for byte those of an EARLIER row. The engine takes the first row whose core holds a
    point, so an alias is never a destination and has no map of its own (a divided CHIM region cell's other maps,
    prepare_world_regions.merge_chim_rows, CHIM-REGION-DIVIDED-CELLS-36)."""
    if raw[:4] != b'AWR2':
        raise ValueError('Invalid world region directory')
    count = struct.unpack_from('<I', raw, 4)[0]
    first, out = {}, {}
    for i in range(count):
        body = raw[64 + 52 * i + 8:64 + 52 * (i + 1)]
        name = 'vf%04d' % i
        if body in first:
            out[name] = first[body]
        else:
            first[body] = name
    return out


def region_map_names(id1, world_dir, primary_only=False):
    """{open-world map name: cell} of a CHIM world's region frames (chim-regions.json), by the image's region directory:
    the maps those frames own, a divided cell's alias rows included (region_owned); no stage makes a legacy map under
    these names (docs/BUILD_MANIFEST.md step 2). primary_only: only the name each frame map is installed under (one
    per cell: what the entity tracker counts). {} for a world without region frames."""
    from chim.regions import TABLE_FILE, read_table
    path = Path(world_dir) / TABLE_FILE if world_dir else None
    if path is None or not path.is_file() or not (Path(id1) / 'world/regions.awr').is_file():
        return {}
    directory = world_directory(id1)
    out = {}
    for frame in read_table(path)['frames']:
        owned = region_owned(region_sources(directory, frame), frame)
        if owned is None:
            continue
        name, aliases = owned
        for n in [name] + ([] if primary_only else aliases):
            out[n] = tuple(frame['cell'])
    return out


def region_frame_rows(id1, world_dir):
    """{open-world map name: row} of a CHIM world's region frames (chim-regions.json), one per frame under the name
    its frame map is installed under (region_map_names primary_only): the frame's id, its owned cells, its origin
    (the frame map's local coordinates are the game's x 0.25 minus it: x and y are the directory row's, z the
    frame's, set_region_origins_z) and the divided cell's alias names (never loaded by the engine). The harvest step
    writes each frame map's catalogue under that name (tools/harvest_build.py, HARVEST-CHIM-REGION-LOSS-41).
    {} for a world without region frames."""
    from chim.regions import TABLE_FILE, read_table
    path = Path(world_dir) / TABLE_FILE if world_dir else None
    if path is None or not path.is_file() or not (Path(id1) / 'world/regions.awr').is_file():
        return {}
    directory = world_directory(id1)
    out = {}
    for frame in read_table(path)['frames']:
        owned = region_owned(region_sources(directory, frame), frame)
        if owned is None:
            continue
        name, aliases = owned
        out[name] = {'frame': frame['id'], 'cells': [list(c) for c in frame.get('cells') or [frame['cell']]],
                     'origin': [float(frame['origin'][0]), float(frame['origin'][1]), float(frame['origin'][2])],
                     'aliases': list(aliases)}
    return out


def region_owned(sources, frame):
    """(name, aliases) of the directory rows a CHIM region frame owns, or None when they do not cover exactly its
    cell: one row whose core is the cell (a one-map cell), or a divided cell's rows after the world terrain stage
    widened them (prepare_world_regions.merge_chim_rows): every row's core is the cell and its origin the cell
    centre; the first (lowest index, directory order) is the name the frame map takes, the others are aliases the
    engine never picks (it takes the first row whose core holds a point). Rows of a divided cell that were not
    widened (smaller cores) are not owned this way (CHIM-REGION-DIVIDED-CELLS-36)."""
    want = (frame['core'][0][0], frame['core'][0][1], frame['core'][1][0], frame['core'][1][1])
    if not sources:
        return None
    for _, origin, core in sources:
        if (any(abs(a - b) > 1e-3 for a, b in zip(core, want))
                or any(abs(origin[k] - frame['origin'][k]) > 1e-3 for k in range(2))):
            return None
    return sources[0][0], [src[0] for src in sources[1:]]


def region_sources(directory, frame):
    """The open-world maps whose core lies wholly inside the frame's owned cell (the maps a CHIM
    region frame replaces: one, or a divided cell's widened rows, region_owned), with their origin and core,
    in directory order."""
    (x0, y0), (x1, y1) = frame['core']
    ox, oy = frame['origin'][0], frame['origin'][1]
    out = []
    for name, origin, core in directory:
        g = (origin[0] + core[0], origin[1] + core[1], origin[0] + core[2], origin[1] + core[3])
        if g[0] >= ox + x0 - 1e-3 and g[1] >= oy + y0 - 1e-3 and g[2] <= ox + x1 + 1e-3 and g[3] <= oy + y1 + 1e-3:
            out.append((name, origin, core))
    return out


def set_region_origins_z(id1, heights):
    """Set the origin z of open-world map rows in world/regions.awr (AWR2), {name: z}, in one write: a CHIM
    frame map's local heights are the game's x 0.25 (origin z 0), a legacy open-world map's are shifted to fit
    the map's range."""
    path = Path(id1) / 'world/regions.awr'
    raw = bytearray(path.read_bytes())
    count = struct.unpack_from('<I', raw, 4)[0]
    for name, z in heights.items():
        index = int(name[2:])
        if raw[:4] != b'AWR2' or not 0 <= index < count or raw[64 + 52 * index:64 + 52 * index + 7] != name.encode() + b'\0':
            raise ValueError('No row %s in the world region directory' % name)
        struct.pack_into('<f', raw, 64 + 52 * index + 16, float(z))
    path.unlink()                   # a new file (the staged directory may be read-only or hard-linked)
    path.write_bytes(bytes(raw))


def set_region_origin_z(id1, name, z):
    """Set the origin z of one open-world map's row in world/regions.awr (set_region_origins_z)."""
    set_region_origins_z(id1, {name: z})


def region_task(id1, frame, world_dir, world=None, directory=None, rows=None, hand_fields=None,
                source_sections=None):
    """The inputs of one CHIM region frame map (build_region), checked and picklable for a pool worker:
    the open-world map the frame replaces (exactly one, covering exactly the frame's cell), its origin and
    core, and the frame's CHIM placement references. world: the CHIM world already loaded (load);
    directory: world_directory(id1) already read. rows: region_rows_mode() ('game-data' needs world and hand_fields:
    the worldspawn and the start come from them, the legacy map is not read)."""
    id1 = Path(id1)
    cell = tuple(frame['cell'])
    sources = region_sources(world_directory(id1) if directory is None else directory, frame)
    if not sources:
        raise ValueError('CHIM region frame %s: cell %d,%d has no open-world map' % (frame['id'], cell[0], cell[1]))
    owned = region_owned(sources, frame)
    if owned is None:
        if len(sources) > 1:
            raise ValueError('CHIM region frame %s: cell %d,%d is %d open-world maps whose directory rows do not each '
                             'cover the cell: a divided cell needs the world terrain stage to widen its rows '
                             '(--chim-regions-cells, CHIM-REGION-DIVIDED-CELLS-36)'
                             % (frame['id'], cell[0], cell[1], len(sources)))
        name, origin, core = sources[0]
        raise ValueError('CHIM region frame %s: map %s does not cover exactly cell %d,%d (origin %s, core %s)'
                         % (frame['id'], name, cell[0], cell[1], list(origin), list(core)))
    name, aliases = owned
    _, origin, core = sources[0]
    mode = region_rows_mode('legacy' if rows is None and hand_fields is None else rows)
    if aliases and mode != 'game-data':
        raise ValueError('CHIM region frame %s: cell %d,%d is a divided cell (%d open-world maps); the earlier region '
                         'method (--chim-region-rows legacy) copies one legacy map: use game-data rows'
                         % (frame['id'], cell[0], cell[1], len(aliases) + 1))
    placed = sorted(chim_placements(world_dir, cell, world=world))
    stream = stream_enabled()
    if world is not None:
        # the frame's bounds and chunk grid from the world already read (as frame_record / frame_grid read them)
        from chim.terrain import TERRAIN_CEILING
        _, record, chunks = next(f for f in world['frames'] if tuple(f[1]['cell']) == cell)
        g, (lx, ly) = record['grain'], record['low']
        lo = (lx, ly, min(c['zmin'] for c in chunks) - FLOOR_MARGIN)
        hi = (lx + record['nx'] * g, ly + record['ny'] * g, float(TERRAIN_CEILING))
        grid = ([{'cx': c['cx'], 'cy': c['cy'], 'index': c['index']} for c in chunks], tuple(record['low']), g,
                record['nx'], record['ny'])
    else:
        _, lo, hi = frame_bounds(world_dir, cell)
        grid = None
        if stream:
            chunks, low, g, nx, ny = frame_grid(world_dir, cell)
            grid = ([{'cx': c['cx'], 'cy': c['cy'], 'index': c['index']} for c in chunks], low, g, nx, ny)
    task = {'id1': str(id1), 'frame': frame, 'name': name, 'origin': list(origin), 'core': list(core),
            'placed': placed, 'bounds': [list(lo), list(hi)], 'grid': json.loads(json.dumps(grid)), 'stream': stream,
            'rows': mode, 'aliases': list(aliases)}
    if source_sections is None:
        source_sections = region_source_sections(world_dir)
    if cell in source_sections:
        section = source_sections[cell]
        sprite_rows = section.get('sprite_entities', [])
        if sprite_rows:
            if task['rows'] != 'game-data':
                raise ValueError('Recipe sprites require game-data frame rows')
            assets = {}
            for asset in section['sprite_assets']:
                path = asset['path']
                if not re.fullmatch(r'progs/aw_flora/f_[0-9a-f]{16}\.spr', path):
                    raise ValueError('Invalid recipe sprite path')
                src = (Path(world_dir) / asset['file']).resolve()
                if not src.is_relative_to(Path(world_dir).resolve()):
                    raise ValueError('Recipe sprite escapes build output')
                raw = src.read_bytes()
                if _sha256(raw) != asset['sha256'] or len(raw) != asset['bytes']:
                    raise ValueError('Recipe sprite checksum mismatch: ' + path)
                target = id1 / path
                if target.is_file() and target.read_bytes() != raw:
                    raise ValueError('Conflicting shared sprite asset: ' + path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
                assets[path] = asset['sha256']
            if any(r.get('classname') != 'aw_flora' or r.get('model') not in assets for r in sprite_rows):
                raise ValueError('Unbound recipe sprite entity')
            task['sprite_rows'], task['sprite_assets'] = sprite_rows, assets
    if task['rows'] == 'game-data':
        if world is None or hand_fields is None:
            raise ValueError('CHIM region frame %s: rows from the game data need the CHIM world and the hand fields'
                             % frame['id'])
        ground = frame_ground(world, cell)
        if ground is None:
            raise ValueError('CHIM region frame %s: no ground under the frame centre for the player start' % frame['id'])
        task['worldspawn'] = open_world_worldspawn(hand_fields)
        task['start_z'] = ground + START_HEIGHT - frame['origin'][2]
    return task


REGION_CACHE = 'chim-region-frame'
# Where a region frame map's rows come from (build setting chim_region_rows, tools/build.py --chim-region-rows):
# 'game-data' (default since v0.0.36: the open-world worldspawn and the player start on the frame's own ground, no
# legacy map read, docs/BUILD_MANIFEST.md step 2) or 'legacy' (the earlier method, kept: copied from the cell's
# compiled legacy open-world map).
REGION_ROWS_VARIABLE = 'AMIWIND_CHIM_REGION_ROWS'
REGION_ROWS_CHOICES = ('game-data', 'legacy')
DEFAULT_REGION_ROWS = 'game-data'
# The open-world maps' worldspawn message (tools/prepare_world_regions.py map_text).
OPEN_WORLD_MESSAGE = 'Vvardenfell'
# Height of the player start over the ground (tools/prepare_world_regions.py map_text: spawn = ground + 24).
START_HEIGHT = 24


def region_rows_mode(value=None):
    """The resolved chim_region_rows setting (an explicit VALUE wins over the environment)."""
    import os
    if value is None:
        value = os.environ.get(REGION_ROWS_VARIABLE, DEFAULT_REGION_ROWS).strip() or DEFAULT_REGION_ROWS
    if value not in REGION_ROWS_CHOICES:
        raise ValueError(REGION_ROWS_VARIABLE + ' must be one of ' + ', '.join(REGION_ROWS_CHOICES))
    return value


def export_region_rows(value):
    """Export chim_region_rows for the image step (tools/build.py)."""
    import os
    os.environ[REGION_ROWS_VARIABLE] = region_rows_mode(value)


def open_world_worldspawn(hand_fields):
    """The worldspawn an open-world map carries after the image passes, made from its sources instead of a compiled
    map: classname, the standing hull profile (player_hull), the message (world terrain), the shared-sky keys of an
    exterior map (exterior_sky_build), then the hand timing and eye height fields (hand_metadata.hand_fields), in the
    order the passes leave them. The world terrain converter's "wad" key (a compiler input; frame maps have no
    textures) is not carried."""
    from exterior_sky_build import SHARED_SKY_PATH
    from player_hull import PROFILE
    row = {'classname': 'worldspawn', 'aw_hull': PROFILE, 'message': OPEN_WORLD_MESSAGE,
           '_aw_sky_mode': 'exterior', '_aw_sky_asset': SHARED_SKY_PATH}
    row.update(hand_fields)
    return row


def frame_ground(world, cell, point=(0.0, 0.0), top=None, bottom=None):
    """Height of the first collision under POINT (frame-local) on the frame's own point hull (chunk terrain and
    placed models, chim.collision.FrameScene), traced from TOP down to BOTTOM (default: the frame's own height
    range, from the terrain ceiling to its lowest chunk less FLOOR_MARGIN), or None."""
    from chim.terrain import TERRAIN_CEILING
    _, record, chunks = next(f for f in world['frames'] if tuple(f[1]['cell']) == tuple(cell))
    top = float(TERRAIN_CEILING) if top is None else top
    bottom = min(c['zmin'] for c in chunks) - FLOOR_MARGIN if bottom is None else bottom
    from chim.collision import FrameScene
    index = next(i for i, (_, frame, _) in enumerate(world['frames']) if tuple(frame['cell']) == tuple(cell))
    return ground_trace(FrameScene(world, index, hull=0), point, top, bottom)


def ground_trace(scene, point, top, bottom):
    """First solid height, searched top-down with bounded exact hull sweeps.

    CHIM-FRAME-GROUND-TRACE-38: a ceiling-to-floor sweep through a shared
    point-hull DAG can exceed the offline visit guard despite having no cycle.
    Reuse the same tracer over contiguous 256-unit segments, retaining its
    cycle/visit checks and returning the first hit. No hull or runtime change.
    """
    if not all(math.isfinite(v) for v in (*point, top, bottom)):
        raise ValueError('Invalid ground trace bounds')
    z = top
    direction = -1 if bottom < top else 1
    while z != bottom:
        end = max(bottom, z - 256.0) if direction < 0 else min(bottom, z + 256.0)
        hit = scene.trace((point[0], point[1], z), (point[0], point[1], end))
        if hit is not None:
            return z + (end - z) * hit['fraction']
        z = end
    return None


def region_cache():
    """The CHIM region frame maps' share of the image pass cache (tools/pass_cache.py), or None when it is off.
    Keyed by the code the worker (_region_map) reaches, not the whole module."""
    from pass_cache import PassCache
    return PassCache.open(REGION_CACHE, {}, (__file__, '_region_map'))


def _sha256(data):
    import hashlib
    return hashlib.sha256(data).hexdigest()


def region_inputs(task, legacy):
    """SHA-256 of everything a region frame map is made from (its pass-cache key input): the legacy map's
    bytes, the frame row, the frame's placement references, bounds and chunk grid (from the CHIM world),
    every model file a legacy entity names (the streamed statics' boxes and the Hunk rest read them) and the
    engine's activated-object header. Never names, sizes or times."""
    from pass_cache import input_digest
    id1 = Path(task['id1'])
    if task.get('rows') == 'game-data':
        # a divided cell's alias names only when it has some: one-map cells keep their keys
        return input_digest({'rows': 'game-data', 'frame': task['frame'], 'name': task['name'],
                             'placed': _sha256(json.dumps(task['placed']).encode()), 'bounds': task['bounds'],
                             'grid': _sha256(json.dumps(task['grid']).encode()), 'worldspawn': task['worldspawn'],
                             'start_z': task['start_z'], 'activated': _sha256(Path(ACTIVATED_HEADER).read_bytes()),
                             'stream_statics': task['stream'], 'startup_sound': startup_sound_scratch(id1),
                             **({'aliases': task['aliases']} if task.get('aliases') else {}),
                             **({'sprite_rows': task['sprite_rows'], 'sprite_assets': task['sprite_assets']}
                                if task.get('sprite_rows') else {})})
    models = {}
    for e in entities(legacy):
        model = e.get('model', '')
        if model and not model.startswith('*') and model not in models and (id1 / model).is_file():
            models[model] = _sha256((id1 / model).read_bytes())
    return input_digest({'legacy': _sha256(legacy), 'frame': task['frame'], 'name': task['name'],
                         'origin': task['origin'], 'core': task['core'],
                         'placed': _sha256(json.dumps(task['placed']).encode()), 'bounds': task['bounds'],
                         'grid': _sha256(json.dumps(task['grid']).encode()),
                         'models': models, 'activated': _sha256(Path(ACTIVATED_HEADER).read_bytes()),
                         'stream_statics': task['stream'], 'startup_sound': startup_sound_scratch(id1)})


def region_map(task):
    """Pool worker: (frame map bytes, record, reused) of one CHIM region frame (region_task). It only reads;
    the caller writes the frame map and removes the legacy files (install_region). With task['cache'] (a
    PassCache) the result is taken from the pass cache when region_inputs is unchanged, and stored after it is
    made; the bytes are the same either way, and the record is the JSON the cache keeps."""
    legacy = None if task.get('rows') == 'game-data' else (Path(task['id1']) / 'maps' / (task['name'] + '.bsp')).read_bytes()
    cache = task.get('cache')
    key = region_inputs(task, legacy) if cache is not None else None
    if cache is not None:
        found = cache.load(key)
        if found is not None and found[1] is not None and isinstance(found[0], dict):
            return found[1], found[0], True
    data, record = (_region_map_game_data(task) if legacy is None else _region_map(task, legacy))
    record = json.loads(json.dumps(record))
    if cache is not None:
        import cache_provenance
        cache_provenance.name_unit(cache, key, lambda: task['name'], lambda: [('legacy map', legacy if legacy is not None else 'game-data'), ('frame', task['frame']), ('placed', task['placed']), ('bounds', task['bounds']), ('grid', task['grid']), ('stream statics', task['stream'])])
        cache.store(key, record, data)
    return data, record, False


def _region_map(task, legacy):
    from entity_tracker import bsp_refs
    from map_files import frame_map_path
    id1 = Path(task['id1'])
    frame, name = task['frame'], task['name']
    origin, core = task['origin'], task['core']
    cell = tuple(frame['cell'])
    placed = set(task['placed'])
    report = {'source': name, 'classes': collections.Counter(), 'refused': [],
              'statics': {'legacy': 0, 'in_chim': 0, 'missing': []}}
    shift = [origin[k] - frame['origin'][k] for k in range(3)]
    rows, world_row, start = [], None, None
    for e in entities(legacy):
        c = e.get('classname', '')
        if c == 'worldspawn':
            world_row = {k: v for k, v in e.items() if k not in PER_MAP_KEYS}
            continue
        o = [float(v) for v in e.get('origin', '0 0 0').split()]
        if not (core[0] <= o[0] < core[2] and core[1] <= o[1] < core[3]):
            continue                                  # the coverage copy of a neighbour's object
        moved = '%g %g %g' % tuple(o[k] + shift[k] for k in range(3))
        if c == 'func_wall' and e.get('aw_ref', '').isdigit():
            report['statics']['legacy'] += 1
            if int(e['aw_ref']) in placed or int(e['aw_ref']) >= TERRAIN_REF:
                report['statics']['in_chim'] += 1
            else:
                report['statics']['missing'].append(int(e['aw_ref']))
            continue
        if c == 'info_player_start':
            start = start or dict(e, origin=moved)
            continue
        if c in REGION_POINT_CLASSES and not e.get('model', '').startswith('*'):
            rows.append(dict(e, origin=moved))
            report['classes'][c] += 1
            continue
        report['refused'].append('%s: %s entity cannot be carried into a CHIM region frame' % (name, c))
    if world_row is None:
        report['refused'].append('%s has no worldspawn' % name)
    if report['statics']['missing']:
        report['refused'].append('%d statics of %s are not CHIM placements of the frame (first %d)'
                                 % (len(report['statics']['missing']), name, report['statics']['missing'][0]))
    found, refused = activated_entities(id1, [name])
    report['refused'] += refused
    if report['refused']:
        raise ValueError('CHIM region frame map %s (%s): %s' % (name, frame['id'], '; '.join(report['refused'][:6])))
    rows = [world_row, start or {'classname': 'info_player_start', 'origin': '0 0 0'}] + rows
    rows[0][FRAME_KEY] = '%d %d' % cell
    lo, hi = (tuple(v) for v in task['bounds'])
    streamed, streamed_bytes = 0, 0
    if task['stream']:
        chunks, low, g, nx, ny = task['grid']
        streamed, streamed_bytes = stream_statics(id1, rows, chunks, tuple(low), g, nx, ny)
        rows[0][COUNT_KEY] = str(streamed)
    rows[0][HUNK_KEY] = str(hunk_rest(id1, rows))
    report['streamed_statics'] = {'count': streamed, 'model_bytes': streamed_bytes,
                                  'hunk_rest': int(rows[0][HUNK_KEY])}
    lumps, report['activated'] = keep_activated(empty_world(lo, hi), rows, found)
    refused = activated_check(rows, found)
    if refused:
        raise ValueError('CHIM region frame map %s (%s): %s' % (name, frame['id'], '; '.join(refused[:6])))
    lumps[0] = entity_text(rows)
    data = F.brush_image(lumps)[0]
    replaced = [{'file': 'maps/%s.bsp' % name, 'bytes': len(legacy), 'sha256': _sha256(legacy),
                 'town': frame['id'], 'reason': 'replaced in place by the CHIM region frame map'}]
    report['classes'] = dict(sorted(report['classes'].items()))
    report['statics'] = dict(report['statics'], missing=len(report['statics']['missing']))
    return data, dict(report, map='maps/' + frame_map_path(id1, name).name, frame=list(cell), id=frame['id'],
                      bounds=[list(lo), list(hi)], bytes=len(data), sha256=_sha256(data),
                      tracker_refs=len(bsp_refs(data)), entities=len(rows), replaced=replaced,
                      legacy_origin_z=origin[2])


def _region_map_game_data(task):
    """A region frame map from the game data (docs/BUILD_MANIFEST.md step 2): the open-world worldspawn and the player
    start at (0, 0) on the frame's own ground + START_HEIGHT, angle 90, as the world terrain converter places it; no
    legacy map. An object the engine activates among the frame's placements is refused (its edict came from the
    legacy map: such a cell needs the legacy method, --chim-region-rows legacy)."""
    from entity_tracker import bsp_refs
    from map_files import frame_map_path
    id1, frame, name = Path(task['id1']), task['frame'], task['name']
    cell = tuple(frame['cell'])
    refused = native_activated_check(task['placed'])
    if refused:
        raise ValueError('CHIM region frame map %s (%s): %s' % (name, frame['id'], '; '.join(refused[:6])))
    rows = [dict(task['worldspawn']),
            {'angle': '90', 'classname': 'info_player_start', 'origin': '%g %g %g' % (0, 0, task['start_z'])}]
    rows.extend(dict(r) for r in task.get('sprite_rows', []))
    problems, _ = static_check(rows)
    if problems:
        raise ValueError('; '.join(problems))
    rows[0][FRAME_KEY] = '%d %d' % cell
    lo, hi = (tuple(v) for v in task['bounds'])
    streamed, streamed_bytes = 0, 0
    if task['stream']:
        chunks, low, g, nx, ny = task['grid']
        streamed, streamed_bytes = stream_statics(id1, rows, chunks, tuple(low), g, nx, ny)
        rows[0][COUNT_KEY] = str(streamed)
    rows[0][HUNK_KEY] = str(hunk_rest(id1, rows))
    lumps, activated = keep_activated(empty_world(lo, hi), rows, [])
    lumps[0] = entity_text(rows)
    data = F.brush_image(lumps)[0]
    report = {'source': 'game data (no legacy map)', 'rows': 'game-data', 'classes': {}, 'refused': [],
              'statics': {'legacy': 0, 'in_chim': 0, 'missing': 0}, 'activated': activated,
              'streamed_statics': {'count': streamed, 'model_bytes': streamed_bytes, 'hunk_rest': int(rows[0][HUNK_KEY])}}
    if task.get('aliases'):
        report['aliases'] = list(task['aliases'])     # a divided cell's other directory rows (never a destination)
    return data, dict(report, map='maps/' + frame_map_path(id1, name).name, frame=list(cell), id=frame['id'],
                      bounds=[list(lo), list(hi)], bytes=len(data), sha256=_sha256(data),
                      tracker_refs=len(bsp_refs(data)), entities=len(rows), replaced=[], legacy_origin_z=task['origin'][2])


def install_region(id1, task, data, record, keep_catalogues=None):
    """Write one region frame map (region_map's result) in place of its open-world map: the map's harvest
    catalogue leaves (recorded), the legacy map leaves (if a stage made it), maps/<name>.chim is written. The caller
    sets the directory row's origin z (set_region_origins_z). keep_catalogues: {map name: SHA-256} of the catalogues
    the harvest step wrote for the CHIM frame maps (tools/harvest_build.py: frame origin, AWH4 proxies that need no
    map entity): a catalogue with exactly that content stays with the frame map (recorded as 'harvest_catalogue');
    any other catalogue of the replaced map leaves as before (HARVEST-CHIM-REGION-LOSS-41). Returns the record with
    every replaced file."""
    from map_files import frame_map_path, is_chim_frame
    id1, name, frame = Path(id1), task['name'], task['frame']
    keep_catalogues = keep_catalogues or {}
    kept = None
    if name in keep_catalogues:
        own = id1 / ('harvest-%s.txt' % name)
        raw = own.read_bytes() if own.is_file() else b''
        if _sha256(raw) != keep_catalogues[name] or not raw.startswith(b'AWH4 '):
            raise ValueError('CHIM region frame map %s (frame %s): the harvest catalogue the harvest step wrote for it '
                             '(SHA-256 %s) is missing or changed' % (name, frame['id'], keep_catalogues[name]))
    legacy_path = id1 / 'maps' / (name + '.bsp')
    replaced = list(record['replaced'])
    if replaced:
        if _sha256(legacy_path.read_bytes()) != replaced[0]['sha256']:
            raise ValueError('CHIM region frame map %s: the legacy map is not the one its frame map was made from' % name)
    elif legacy_path.is_file():
        # game-data rows: a legacy map an earlier stage still made leaves too, recorded (it never ships)
        raw = legacy_path.read_bytes()
        replaced.append({'file': 'maps/%s.bsp' % name, 'bytes': len(raw), 'sha256': _sha256(raw), 'town': frame['id'],
                         'reason': 'legacy map of a CHIM region cell (the frame map is made from the game data)'})
    for alias in task.get('aliases') or ():
        # a divided cell's other maps: no stage makes them (step 2b); one an earlier stage still made leaves, recorded
        path = id1 / 'maps' / (alias + '.bsp')
        if path.is_file() and not is_chim_frame(path):
            raw = path.read_bytes()
            replaced.append({'file': 'maps/%s.bsp' % alias, 'bytes': len(raw), 'sha256': _sha256(raw),
                             'town': frame['id'], 'reason': 'legacy map of a divided CHIM region cell (its directory '
                                                            'row is an alias of %s)' % name})
            path.unlink()
    for owner in [name] + list(task.get('aliases') or ()):
        catalogue = id1 / ('harvest-%s.txt' % owner)
        if catalogue.is_file():
            raw = catalogue.read_bytes()
            if owner == name and keep_catalogues.get(name) == _sha256(raw) and raw.startswith(b'AWH4 '):
                kept = {'file': catalogue.name, 'bytes': len(raw), 'sha256': _sha256(raw)}
                continue
            replaced.append({'file': catalogue.name, 'bytes': len(raw), 'sha256': _sha256(raw),
                             'town': frame['id'], 'reason': 'harvest catalogue of a replaced map (its plants are not '
                                                            'on the CHIM region frame map yet)'})
            catalogue.unlink()
    if legacy_path.is_file() and not is_chim_frame(legacy_path):
        legacy_path.unlink()        # a new file (the staged legacy map may be read-only or hard-linked)
    frame_path = frame_map_path(id1, name)
    if frame_path.exists():
        raise ValueError('CHIM region frame map already present: ' + frame_path.name)
    frame_path.write_bytes(data)
    return dict(record, replaced=replaced, **({'harvest_catalogue': kept} if kept else {}))


def build_region(id1, frame, world_dir, world=None, rows=None, hand_fields=None, keep_catalogues=None):
    """Replace a cell's open-world map IN PLACE by the frame map of its CHIM region frame (chim.regions: one
    exterior cell on CHIM inside the open world): maps/vfNNNN.bsp of the cell gives way to maps/vfNNNN.chim
    (chim_frame_ext; with bsp the file is replaced under its own name), an empty world with the worldspawn
    "_chim_frame", so the engine's open-world directory, hand-over, saves and every tool keep the map name
    (the engine and the tools resolve it: AW_MapPath, tools/map_files.py). Carried from the legacy map (read before it is replaced): its worldspawn, player start and point
    entities (flora sprites, sounds, as the legacy chain made them) moved to the frame's origin; its statics
    must all be CHIM placements of the frame (counted); objects the engine activates keep their edicts
    (keep_activated). The map's harvest catalogue leaves (its plants are not on the frame map: recorded). The
    directory row keeps its core and cover (the frame's ground reaches the same +-896) and gets origin z 0.
    No clip walls: the engine hands the player to the neighbouring map at the open edges (aw_world.c).
    Returns the record ('replaced': the legacy files with their hashes). One frame in this process;
    build_regions makes many on the shared worker pool."""
    task = region_task(id1, frame, world_dir, world=world, rows=rows, hand_fields=hand_fields)
    data, record, _ = region_map(task)
    record = install_region(id1, task, data, record, keep_catalogues)
    doors = install_region_doors(id1, task['name'], region_door_rows(world_dir, frame, placed=task['placed']))
    if doors:
        record['door_bank'] = doors
    set_region_origins_z(id1, {n: frame['origin'][2] for n in [task['name']] + task['aliases']})
    return record


def region_source_sections(world_dir):
    """Read sprite provenance once per batch, preserving the first section for each cell."""
    source_path = Path(world_dir) / 'chim-source.json'
    sections = {}
    if source_path.is_file():
        source = json.loads(source_path.read_text(encoding='utf-8'))
        for section in source['frames']:
            sections.setdefault(tuple(section['cell']), section)
    return sections


DOOR_BANK = 'AWD3'
DOOR_LABEL_DEFAULT = 'Exterior world'


def region_door_rows(world_dir, frame, rooms=None, placed=None):
    """The door bank rows (AWD3, engine aw_scene.c read_links_for) of one CHIM region frame: every original load
    door (DOOR with a destination) the frame's own cell places, its box frame-local ((Morrowind - frame centre)
    x 0.25, z less the frame origin), its label the destination cell. A door into a converted room (rooms:
    {original cell casefold: room map}, town_interiors.exterior_link) gets its target and arrival; every other
    door the target "-", so the engine shows "Interior unavailable" (CHIM-REGION-DOORS-NO-PROMPT-42). Read from
    the frame's scenery index (WORLD/work/<frame id>/scenery/scenery-index.json); a frame without one is refused
    unless it places nothing (placed: its CHIM placement references, [] = none: open sea, an empty seabed)."""
    from town_interiors import exterior_link
    index_path = Path(world_dir) / 'work' / frame['id'] / 'scenery' / 'scenery-index.json'
    if not index_path.is_file():
        if placed is not None and not placed:
            return []
        raise ValueError('CHIM region frame %s: no scenery index for its door bank (%s)' % (frame['id'], index_path))
    index = json.loads(index_path.read_text(encoding='utf-8'))
    cell = list(frame['cell'])
    origin = frame['origin']
    rows = []
    for ref in sorted(index.get('references') or [], key=lambda r: r['number']):
        if ref.get('type') != 'DOOR' or not ref.get('destination') or list(ref.get('cell') or []) != cell:
            continue
        low, high = ref['bounds']
        box = [[v * 0.25 - origin[k] for k, v in enumerate(corner)] for corner in (low, high)]
        label = ref.get('destination_cell') or DOOR_LABEL_DEFAULT
        if any(c in label for c in '\r\n\t'):
            raise ValueError('CHIM region frame %s: door %d has an invalid label' % (frame['id'], ref['number']))
        link = exterior_link(ref, rooms) if rooms else None
        target, place = ('-', [0, 0, 0, 0]) if link is None else (link[0], [*link[1], link[2]])
        rows.append({'reference': ref['number'], 'target': target, 'box': box, 'place': place, 'label': label})
    return rows


def door_bank_text(name, rows):
    """AWD3 text of a door bank: one line per door, source map NAME (the engine compares it with sv.name)."""
    from town_interiors import BANK_ROWS
    if len(rows) > BANK_ROWS:
        raise ValueError('door bank of %s: %d doors, the engine keeps %d' % (name, len(rows), BANK_ROWS))
    lines = [DOOR_BANK]
    for r in rows:
        values = [*r['box'][0], *r['box'][1], *r['place']]
        lines.append('%s %s %d %s %s' % (name, r['target'], r['reference'], ' '.join('%.5f' % v for v in values),
                                         r['label']))
    return '\n'.join(lines) + '\n'


def install_region_doors(id1, name, rows):
    """Write id1/doors-<name>.txt for a region frame map with doors (none written without doors). Returns its
    record ({'file', 'doors', 'unavailable', 'sha256'}) or None."""
    if not rows:
        return None
    raw = door_bank_text(name, rows).encode('cp1252')
    path = Path(id1) / ('doors-%s.txt' % name)
    if path.exists() and path.read_bytes() != raw:
        raise ValueError('door bank %s already present with other content' % path.name)
    path.write_bytes(raw)
    return {'file': path.name, 'doors': len(rows), 'unavailable': sum(1 for r in rows if r['target'] == '-'),
            'sha256': _sha256(raw)}


def build_regions(id1, frames, world_dir, world=None, jobs=1, cache=None, progress=None, rows=None,
                  hand_fields=None, keep_catalogues=None, rooms=None):
    """build_region for every CHIM region frame: the frame maps are made on the shared worker pool
    (build_parallel.ordered_map; independent read-only workers) and written here in table order, so the image
    is byte-identical with any worker count (BUILD-IMAGE-CHIM-MAPS-SERIAL-36). cache: a PassCache (region_cache):
    an unchanged frame map (region_inputs, by SHA-256) is taken from it. progress(record, reused): called after
    each map is written. keep_catalogues: the harvest step's frame map catalogues (install_region). rooms: the
    converted rooms by original cell (region_door_rows); each frame with load doors gets its door bank. Returns
    (records, number taken from the cache)."""
    from build_parallel import ordered_map
    id1 = Path(id1)
    directory = world_directory(id1)
    source_sections = region_source_sections(world_dir)
    tasks = [region_task(id1, frame, world_dir, world=world, directory=directory, rows=rows,
                         hand_fields=hand_fields, source_sections=source_sections)
             for frame in frames]
    if len({t['name'] for t in tasks}) != len(tasks):
        raise ValueError('CHIM region frames: two frames replace the same open-world map')
    if cache is not None:
        tasks = [dict(t, cache=cache) for t in tasks]
    records, reused, heights = [], 0, {}
    for task, (data, record, hit) in zip(tasks, ordered_map(region_map, tasks, jobs)):
        records.append(install_region(id1, task, data, record, keep_catalogues))
        # the frame's load doors: a door bank under the map's name, so every door shows its prompt
        doors = install_region_doors(id1, task['name'], region_door_rows(world_dir, task['frame'], rooms, task['placed']))
        if doors:
            records[-1]['door_bank'] = doors
        for n in [task['name']] + task['aliases']:     # a divided cell's alias rows stay equal to its row
            heights[n] = task['frame']['origin'][2]
        reused += bool(hit)
        if progress is not None:
            progress(records[-1], hit)
    if heights:
        set_region_origins_z(id1, heights)
    return records, reused


def is_region_frame_map(data):
    """True for a CHIM frame map that replaced an open-world map (worldspawn names a frame): by the key, never
    by the file name (the one test: map_files.is_chim_frame)."""
    from map_files import is_chim_frame
    return is_chim_frame(data)



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


def native_activated_rows(rows):
    """activated_entities' rows from a CHIM-native town stage's record (JSON: '_box' as lists), in its form."""
    return [dict(r, _box=tuple(tuple(round(float(v), 4) for v in b) for b in r['_box'])) for r in (rows or [])]


def native_activated_check(placed, refs=None):
    """Refusals for a CHIM-native town (tools/chim_town.py: no legacy region maps,
    BUILD-IMAGE-CHIM-NATIVE-TOWN-36): an object the engine activates gets its edict only from the
    legacy region maps (activated_entities), so none may be among the frame's CHIM placements
    `placed` ({ref: origin}, chim_placements); such a town is built with --legacy-area instead."""
    refs = activated_refs() if refs is None else refs
    keys = {int(r) for r in placed if str(r).isdigit()}
    return ['activated object %d (%s) is placed in a CHIM-native town, whose frame map has no legacy region '
            'maps to take its edict from: build the town with --legacy-area' % (r, refs[r])
            for r in sorted(refs) if r in keys]


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


def activated_expected(exterior, bounds, polygon=None, centre=None, scale=0.25, refs=None):
    """The activated objects (aw_activated.h) a map of a town must carry, from the game data alone: the
    exterior references `exterior` (prepare_opening_refs.opening_references) whose original position, in
    the town's units ((position - centre) * scale), lies in the map's XY bounds (x0, y0, x1, y1) and, for
    a special map with a route polygon (prepare_seyda_regions.special_polygon), inside it. Any such object
    is kept by the maps' selection rule (select_entities), so it must arrive. Sorted reference numbers."""
    refs = activated_refs() if refs is None else refs
    if centre is None:
        from prepare_quake import CENTRE as centre
    x0, y0, x1, y1 = bounds
    out = set()
    for r in exterior:
        if r['number'] not in refs:
            continue
        x, y = ((r['position'][i] - centre[i]) * scale for i in (0, 1))
        if not (x0 <= x <= x1 and y0 <= y <= y1):
            continue
        if polygon and any((q[0] - p[0]) * (y - p[1]) - (q[1] - p[1]) * (x - p[0]) < 0
                           for p, q in zip(polygon, polygon[1:] + polygon[:1])):
            continue
        out.add(r['number'])
    return sorted(out)


def activated_missing(map_name, expected, rows, refs=None):
    """Refusals, one per activated object of `expected` (reference numbers) that has no func_wall edict
    with a brush model among `rows` (entity dicts), naming the reference, its AW_REF_ name and the map."""
    refs = activated_refs() if refs is None else refs
    have = {str(e.get('aw_ref')) for e in rows if e.get('classname') == 'func_wall'
            and str(e.get('model', '*')).startswith('*')}
    return ['%s: activated object %d (%s) is missing from the map\'s activated entities'
            % (map_name, r, refs.get(r, 'AW_REF_?')) for r in expected if str(r) not in have]


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
# Measured on the legacy special maps (v0.0.35 release 61ab0a9 and v0.0.36-dev3 3b5e7a9, identical): the legacy map's
# reachable samples and its distance from each escort route goal to reachable floor. A CHIM-native Seyda Neen has no
# legacy special map to walk; its walk check compares with these (BUILD-LEGACY-TOWN-MAPS-SHIPPED-36).
LEGACY_WALK_REFERENCE = {'intro_docks': {'reachable': 7157, 'route': (6.9, 107.2)}, 'sncourt': {'reachable': 603}}


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
    elif name in LEGACY_WALK_REFERENCE:
        # no legacy map (CHIM-native Seyda Neen): the measured legacy reach is the reference
        expected = LEGACY_WALK_REFERENCE[name]['reachable']
        record.update(legacy_reachable_reference=expected, reference='measured legacy map (LEGACY_WALK_REFERENCE)')
        if len(reach) < WALK_COVERAGE * expected:
            refused.append("%s: CHIM reaches %d samples, less than %.0f %% of the legacy map's %d"
                           % (name, len(reach), 100 * WALK_COVERAGE, expected))
    if name == DOCKS:
        record['route'] = []
        reference = LEGACY_WALK_REFERENCE[DOCKS]['route'] if lreach is None else None
        for k, (px, py) in enumerate(DOCK_ROUTE):
            near = nearest_reach(reach, bounds, (px, py))
            limit = ROUTE_TOLERANCE + (nearest_reach(lreach, bounds, (px, py)) if lreach else
                                       reference[k] if reference else 0.0)
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


def build_docks(id1, world_dir, town='seyda', name=DOCKS, world=None, entity_rows=None, activated_rows=None):
    """maps/<special>-chim.chim (.bsp with chim_frame_ext bsp): the intro docks (or the Census
    courtyard, sncourt) as another frame map of Seyda Neen's frame.

    The legacy docks map (prepare_seyda_regions specials: the bounded town with the route mask,
    prepare_intro_docks.derive) holds a subset of the town's statics and the intro's own entities.
    Here its statics must all be in the CHIM frame (one way: the frame draws the whole town around
    the docks), its point entities are copied (the start, the intro actors, flora sprites), and its
    standing boundary becomes four clip walls (func_wall brush models without faces). Coordinates and
    origin are the town's. entity_rows / activated_rows: the special map's rows and activated objects made from
    the game data (CHIM-native Seyda Neen, tools/chim_town.py: no legacy special map); the origin check needs
    the legacy map and is skipped, every other check runs."""
    from entity_tracker import bsp_refs
    from harvest_build import town_origin
    from chim.seyda import source_cell
    BOUNDS = special_bounds(name)
    id1 = Path(id1)
    cell = tuple(source_cell())
    placed = chim_placements(world_dir, cell, world=world)
    if entity_rows is None:
        maps = {name: entities((id1 / 'maps' / (name + '.bsp')).read_bytes())}
        rows, report = frame_entities(maps, set(placed), name)
        # one way: the docks map's statics are in the frame; the frame holds the rest of the town as well
        report['refused'] = [r for r in report['refused'] if 'CHIM statics are not in the final region maps' not in r]
        report['chim_statics_not_in_maps'] = len(report['chim_statics_not_in_maps'])
        _, _, _, _, frame_centre = frame_record(world_dir, cell)
        refused, report['origin_check'] = origin_check(maps, placed, frame_centre, town_origin(town))
        report['refused'] += refused
    else:
        rows = [dict(e) for e in entity_rows]
        counts = collections.Counter(e.get('classname', '') for e in rows)
        report = {'source': 'game data (tools/chim_town.py); no legacy special map',
                  'classes': {c: {'written': n} for c, n in sorted(counts.items())}, 'refused': [],
                  'origin_check': 'not applicable: no legacy special map'}
    refused, report['harvest_check'] = harvest_check(id1, [name])
    report['refused'] += refused
    refused, report['static_check'] = static_check(rows)
    report['refused'] += refused
    world, index = frame_world(world_dir, cell, world=world)
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
    if entity_rows is None:
        found, refused = activated_entities(id1, [name])
    else:
        found, refused = native_activated_rows(activated_rows), []
    lumps, report['activated'] = keep_activated(lumps, rows, found)
    refused += activated_check(rows, found)
    if refused:
        raise ValueError('CHIM frame map for %s: %s' % (name, '; '.join(refused[:6])))
    lumps[0] = entity_text(rows)
    data = F.brush_image(lumps)[0]
    from map_files import frame_map_path, map_files
    path = frame_map_path(id1, map_name(name))
    if map_files(id1 / 'maps', map_name(name)):
        raise ValueError('CHIM frame map already present: ' + map_files(id1 / 'maps', map_name(name))[0].name)
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
