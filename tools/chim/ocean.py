# SPDX-License-Identifier: GPL-3.0-only
"""The shared ocean chunk: the open sea of every exterior cell without a LAND record, stored once.

Morrowind's base master has LAND records for 1,292 exterior cells; the sea around and between them has
none. OpenMW (0.51, components/esm3/loadland.hpp:77 ESM::Land::DEFAULT_HEIGHT; apps/openmw/mwworld/scene.cpp
454-458 and components/esmterrain/storage.cpp 576-580) gives such a cell a flat heightfield at -2048 units,
and a cell without a record is created with water (apps/openmw/mwworld/worldmodel.cpp 55-62, HasWater; an
exterior cell's water is the sea level, apps/openmw/mwworld/cell.cpp 98-102). The legacy region maps sample the
same depth (tools/prepare_world_regions.py Terrain.sample: -512 local = -2048 x 0.25) under a water brush at 0.

Every such cell is the same: water at the sea level over a flat seabed at -2048. So the CHIM builder makes ONE
chunk of it, with the chunk terrain code every other chunk uses (chim.terrain.chunk_terrain: ground plane,
water plane and leaves, the standing hull of the chunk and its ring of tiles), in CHUNK-LOCAL coordinates (the
chunk's low corner at 0, 0). Being flat, it tiles the plane: chunk (i, j) of any ocean cell is this chunk moved
by (i, j) x grain. It is stored once (a content-keyed unit; with the storage pool, one pooled file) and every
ocean cell is a small reference to it (CHIMport, `aw-chim-ocean-ref-1`).

File (format 0.5 addition, docs/chim/WORLD_FORMAT.md "Shared ocean chunk"): the common 32-byte header with kind
`OCEN`; the ocean block (OCEAN_BLOCK, 40 bytes, big-endian); a record directory as in a sector file (16-byte
rows: `CHNK` 0, then `TEXR` 0..n-1); the records, 4-byte aligned: one 0.5 chunk record (no placements, no
PVS row: Quake's "no visibility data" = everything visible) and the miptexes its terrain image references
(lump 2 holds local texture ids 0..n-1 into this file). A 0.5 world never lists an OCEN file, so no 0.5
reader meets one.
"""
import hashlib
import json
import struct

from chim import FORMAT_VERSION
from chim import format as F
from chim.terrain import (CONTENTS_EMPTY, CONTENTS_SOLID, CONTENTS_WATER, TERRAIN_CEILING, TERRAIN_LIGHT,
                          WATER_LEVEL, terrain_unit)

OCEAN_KIND = b'OCEN'
OCEAN_FORMAT = 'aw-chim-ocean-1'       # the ocean chunk's key format (bump when its inputs change shape)
REF_FORMAT = 'aw-chim-ocean-ref-1'     # one ocean cell's reference to the shared chunk
# f32 water level (local), f32 seabed (local), f32 seabed (Morrowind units), f32 world scale,
# u16 grain, u16 terrain step, u16 textures, u16 reserved,
# u32 chunk record render bytes, u32 chunk record collision bytes, u32 chunk record CRC-32, u32 CRC-32 of the
# texture records (each in file order, unpadded).
OCEAN_BLOCK = struct.Struct('>ffffHHHHIIII')
DEFAULT_LAND_HEIGHT = -2048      # Morrowind units: OpenMW ESM::Land::DEFAULT_HEIGHT (mwad.audit.DEFAULT_LAND_HEIGHT)
SCALE = 0.25                     # world scale of every CHIM frame
GRAIN = 256                      # chunk size in local units (CHIMport FRAME_SETTINGS grain)
STEP = 128                       # terrain tile (cell_settings terrain_step)
FLOOR = -1024                    # the converter's terrain floor (import_town.TERRAIN_FLOOR)
SEABED_MATERIAL = 0              # LAND material 0: the default land texture (mwad.audit.default_land)
SEAM_TOLERANCE = 8               # Morrowind units: one LAND height step (VHGT stores heights in 8-unit steps)
CELL_UNITS = 8192                # Morrowind units per exterior cell
LAND_SIZE = 65                   # LAND vertices per side


def seabed_local(default=DEFAULT_LAND_HEIGHT, scale=SCALE):
    return float(default) * scale


def ocean_task(grain=GRAIN, step=STEP, seabed=None, water=WATER_LEVEL, floor=FLOOR, ceiling=TERRAIN_CEILING,
               light=TERRAIN_LIGHT):
    """The terrain unit task of the ocean chunk (chim.terrain.terrain_unit), chunk-local: box (0, 0, grain,
    grain), the collision box one tile wider on every side (the same flat seabed), so the standing hull is
    seamless where copies of the chunk lie side by side."""
    if grain % step:
        raise ValueError('The chunk grain must be a whole number of terrain tiles')
    seabed = seabed_local() if seabed is None else float(seabed)
    if seabed >= water:
        raise ValueError('The seabed must lie below the water level')
    per = grain // step
    corners = per + 3                       # chunk tiles + one tile each side, corner rows
    return {'box': (0, 0, grain, grain), 'step': step,
            'heights': [[seabed] * corners for _ in range(corners)],
            'materials': [[SEABED_MATERIAL] * per for _ in range(per)],
            'floor': float(floor), 'ceiling': float(ceiling), 'water': float(water), 'light': int(light),
            'collision_box': (-step, -step, grain + step, grain + step)}


def texture_digests(ground_textures):
    return {name: hashlib.sha256(bytes(mip)).hexdigest() for name, mip in sorted(ground_textures.items())}


def ocean_key(task, ground_textures, palette=None):
    """The chunk's content key: the task, the miptexes it may use, the palette (sky-bank move), the tool sources
    (unit kind 'ocean') and the format."""
    from chim.units import fingerprint
    return fingerprint('ocean', OCEAN_FORMAT, list(FORMAT_VERSION), task,
                       {k: v for k, v in texture_digests(ground_textures).items() if k in (
                           'g%d' % SEABED_MATERIAL, '*water')},
                       hashlib.sha256(bytes(palette)).hexdigest() if palette else None)


def build_ocean(ground_textures, palette=None, task=None, cache=None):
    """(file bytes, info) of the shared ocean chunk. ground_textures: {'gN' / '*water': miptex bytes} (the
    builder's ground WAD); palette: the game palette (textures moved off the sky bank as every CHIM texture)."""
    from chim.units import fingerprint, run_units
    task = task or ocean_task()
    fp = fingerprint('terrain', task, 'routed', None)          # the same key a frame's chunk would get
    res = run_units('terrain', [(fp, task)], terrain_unit, 1, cache)[0]
    lumps = [bytearray(x) for x in res['lumps']]
    keys = [tuple(k) for k in res['texture_keys']]
    miptex = []
    for kind, name in keys:
        if kind != 'ground' or name not in ground_textures:
            raise ValueError('The ocean chunk needs the ground texture %r' % (name,))
        miptex.append(bytes(ground_textures[name]))
    if palette:
        from sky_palette_overlay import bank_safe, remap_miptex
        if bank_safe(palette):
            miptex = [remap_miptex(m) for m in miptex]
    lumps[2] = bytearray(F.texture_refs(list(range(len(keys)))))
    image, render = F.brush_image(lumps)
    chunk, crender, ccoll = F.chunk_record([], [], b'', image, render, res['info']['leaves'])
    seabed = task['heights'][0][0]
    block = OCEAN_BLOCK.pack(task['water'], seabed, seabed / SCALE, SCALE, task['box'][2], task['step'], len(miptex),
                             0, crender, ccoll, F.crc32(chunk), F.crc32(b''.join(miptex)))
    records = [(b'CHNK', 0, chunk)] + [(b'TEXR', i, m) for i, m in enumerate(miptex)]
    diro = F.HEADER.size + OCEAN_BLOCK.size
    datao = F.align(diro + len(records) * F.RECORD_ENTRY.size)
    body, entries = bytearray(), []
    for kind, rid, data in records:
        entries.append(F.RECORD_ENTRY.pack(kind, rid, datao + len(body), len(data)))
        body += F.pad(data)
    total = datao + len(body)
    out = bytearray(F.header(OCEAN_KIND, len(records), diro, datao, total)) + block + b''.join(entries)
    out += bytes(datao - len(out)) + body
    info = {k: res['info'][k] for k in ('tiles', 'faces', 'water_faces', 'pieces', 'ring_tiles', 'hull_chain_max',
                                         'clipnodes', 'leaves', 'nodes', 'depth', 'zmin', 'zmax')}
    info.update(bytes=len(out), chunk_bytes=len(chunk), render_bytes=crender, collision_bytes=ccoll,
                textures=[name for _, name in keys], texture_bytes=sum(len(m) for m in miptex),
                unit=fp)
    return bytes(out), info


def read_ocean(data):
    """The parts of an ocean chunk file; raises ValueError when it does not read back."""
    if len(data) < F.HEADER.size + OCEAN_BLOCK.size:
        raise ValueError('Ocean chunk file shorter than its header')
    magic, kind, major, minor, size, count, diro, datao, total = F.HEADER.unpack_from(data)
    if magic != F.MAGIC or kind != OCEAN_KIND:
        raise ValueError('Not a CHIM ocean chunk file')
    if (major, minor) != FORMAT_VERSION:
        raise ValueError('CHIM world format %d.%d, expected %d.%d' % (major, minor, *FORMAT_VERSION))
    if size != F.HEADER.size or total != len(data) or diro != size + OCEAN_BLOCK.size or not diro <= datao <= total:
        raise ValueError('Ocean chunk header offsets do not match the file')
    (water, seabed, seabed_mw, scale, grain, step, ntex, _, crender, ccoll, crc, tcrc) = OCEAN_BLOCK.unpack_from(data, size)
    if count != ntex + 1:
        raise ValueError('Ocean chunk record count does not match its textures')
    at, chunk, textures = datao, None, []
    for i in range(count):
        rkind, rid, o, n = F.RECORD_ENTRY.unpack_from(data, diro + i * F.RECORD_ENTRY.size)
        if o != at or o + n > len(data):
            raise ValueError('Ocean chunk record %d is not where the previous one ended' % i)
        raw = data[o:o + n]
        if i == 0:
            if rkind != b'CHNK' or rid != 0:
                raise ValueError('The first ocean record must be the chunk')
            chunk = raw
        elif rkind != b'TEXR' or rid != i - 1:
            raise ValueError('Ocean record %d must be texture %d' % (i, i - 1))
        else:
            textures.append(raw)
        at = F.align(o + n)
    if at != len(data):
        raise ValueError('Ocean chunk file has bytes after its last record')
    if F.crc32(chunk) != crc:
        raise ValueError('Ocean chunk CRC-32 does not match')
    if F.crc32(b''.join(textures)) != tcrc:
        raise ValueError('Ocean texture CRC-32 does not match')
    parts = F.read_chunk(chunk)
    if parts['owned'] or parts['reach'] or parts['render'] != crender or len(chunk) - crender != ccoll:
        raise ValueError('Ocean chunk record sizes do not match its block')
    return {'water': water, 'seabed': seabed, 'seabed_mw': seabed_mw, 'scale': scale, 'grain': grain, 'step': step,
            'textures': textures, 'chunk': parts, 'lumps': F.read_brush_image(parts['image'])}


def _point_contents(nodes, leaves, p):
    num = 0
    while num >= 0:
        normal, dist, front, back = nodes[num]
        num = front if float(normal @ p) - dist >= 0 else back
    return leaves[-1 - num]


def validate_ocean(data, eps=0.25):
    """(failures, figures) of an ocean chunk file: it reads back; brush and world-tree rules (chim.validate);
    point contents (solid under the seabed, water up to the water level, air above); the standing hull at
    the seabed everywhere the chunk and its copies meet (seamless tiling); every tile covered by ground and
    by water seen from above and below."""
    import numpy as np
    from chim.validate import Failures, brush_checks, face_polygons, hull_contents, world_tree
    from player_hull import MINS
    fails = Failures()
    try:
        o = read_ocean(data)
    except ValueError as exc:
        return ['ocean chunk: %s' % exc], {}
    lumps = o['lumps']
    brush_checks(lumps, len(o['textures']), 'ocean chunk', fails)
    nodes, leaves = world_tree(lumps, 'ocean chunk', fails)
    g, seabed, water = float(o['grain']), o['seabed'], o['water']
    figures = {'grain': o['grain'], 'step': o['step'], 'seabed': seabed, 'seabed_mw': o['seabed_mw'], 'water': water,
               'textures': len(o['textures']), 'bytes': len(data)}
    if nodes:
        samples = [(x, y) for x in (0.5, g / 2, g - 0.5) for y in (0.5, g / 2, g - 0.5)]
        for x, y in samples:
            for z, want, label in ((seabed - 4, CONTENTS_SOLID, 'solid under the seabed'),
                                   ((seabed + water) / 2, CONTENTS_WATER, 'water between seabed and sea level'),
                                   (water + 4, CONTENTS_EMPTY, 'air above the sea level')):
                got = _point_contents(nodes, leaves, np.array([x, y, z]))
                fails.check(got == want, 'ocean chunk: point %.1f %.1f %.1f is %d, expected %s' % (x, y, z, got, label))
    m = struct.unpack('<9f7i', lumps[14][:64])
    root = m[10]
    edge = [0.0, 0.25, g / 2, g - 0.25, g]
    checked = 0
    for x in edge + [-3.0, g + 3.0]:
        for y in edge:
            for px, py in ((x, y), (y, x)):
                low = hull_contents(lumps, root, (px, py, seabed - MINS[2] - eps))
                high = hull_contents(lumps, root, (px, py, seabed - MINS[2] + eps))
                checked += 1
                fails.check(low == CONTENTS_SOLID and high == CONTENTS_EMPTY,
                            'ocean chunk: seam - standing hull at %.2f %.2f is %d/%d, expected solid just under '
                            'and empty just over the seabed' % (px, py, low, high))
    area = {'ground': 0.0, 'water_up': 0.0, 'water_down': 0.0}
    for pts, n, flags, lit in face_polygons(lumps):
        xs, ys = pts[:, 0], pts[:, 1]
        a = 0.5 * abs(float(np.dot(xs, np.roll(ys, -1)) - np.dot(ys, np.roll(xs, -1))))
        z = float(pts[:, 2].mean())
        if abs(z - seabed) < 1e-3 and n[2] > 0:
            area['ground'] += a
        elif abs(z - water) < 1e-3:
            area['water_up' if n[2] > 0 else 'water_down'] += a
    for k, v in area.items():
        fails.check(abs(v - g * g) < 1e-3, 'ocean chunk: %s faces cover %.1f of %.1f square units' % (k, v, g * g))
    figures.update(hull_points=checked, ground_area=area['ground'], water_area=area['water_up'],
                   clipnodes=len(lumps[9]) // 8)
    return list(fails), figures


# ---------------------------------------------------------------- the seam where real seabed meets the default floor

def edge_row(heights, side):
    """LAND heights (rows by y, south to north; columns west to east) along one edge: 'w', 'e', 's' or 'n'."""
    if side == 'w':
        return [row[0] for row in heights]
    if side == 'e':
        return [row[-1] for row in heights]
    if side == 's':
        return list(heights[0])
    return list(heights[-1])


SIDES = (('w', (-1, 0), 'e'), ('e', (1, 0), 'w'), ('s', (0, -1), 'n'), ('n', (0, 1), 's'))


def seam_steps(cell, lands, default=DEFAULT_LAND_HEIGHT, tolerance=SEAM_TOLERANCE):
    """The height step on each edge of a cell WITHOUT land where a neighbour WITH land meets it: the neighbour's
    edge row (LAND vertices, Morrowind units) against the default floor the ocean cell lies at. Only edges facing
    a LAND cell are listed; an ocean-to-ocean edge has no step. Corners: a diagonal LAND neighbour's corner
    vertex. Returns {'edges': [...], 'max_step', 'over': edges with a step above TOLERANCE}."""
    x, y = cell
    edges = []
    for side, (dx, dy), facing in SIDES:
        other = lands.get((x + dx, y + dy))
        if other is None:
            continue
        row = edge_row(other, facing)
        steps = [abs(float(h) - default) for h in row]
        edges.append({'side': side, 'neighbour': [x + dx, y + dy], 'max_step': max(steps),
                      'mean_step': round(sum(steps) / len(steps), 2), 'vertices': len(steps),
                      'over': sum(1 for s in steps if s > tolerance), 'highest': max(float(h) for h in row)})
    corners = []
    for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        other = lands.get((x + dx, y + dy))
        if other is None:
            continue
        h = other[-1 if dy < 0 else 0][-1 if dx < 0 else 0]
        corners.append({'neighbour': [x + dx, y + dy], 'step': abs(float(h) - default)})
    worst = max([e['max_step'] for e in edges] + [c['step'] for c in corners] + [0.0])
    return {'edges': edges, 'corners': corners, 'max_step': worst,
            'over': [e['side'] for e in edges if e['max_step'] > tolerance]
            + ['corner %d,%d' % tuple(c['neighbour']) for c in corners if c['step'] > tolerance],
            'tolerance': tolerance}


def reference(cell, digest, size, info, default=DEFAULT_LAND_HEIGHT):
    """One ocean cell's reference to the shared chunk (format aw-chim-ocean-ref-1): the cell's frame as 8 x 8
    copies of the chunk, chunk (i, j) at local low corner (-1024 + i x grain, -1024 + j x grain)."""
    x, y = cell
    half = int(CELL_UNITS * SCALE) // 2
    n = 2 * half // info.get('grain', GRAIN)
    return {'format': REF_FORMAT, 'cell': [x, y],
            'centre': [x * CELL_UNITS + CELL_UNITS // 2, y * CELL_UNITS + CELL_UNITS // 2],
            'chunk': {'sha256': digest, 'bytes': size, 'kind': OCEAN_KIND.decode(), 'world_format': '%d.%d' % FORMAT_VERSION},
            'tiling': {'low': [-half, -half], 'grain': info.get('grain', GRAIN), 'chunks': [n, n]},
            'water_level': WATER_LEVEL, 'seabed': default}


def dumps(value):
    return json.dumps(value, indent=1, sort_keys=True) + '\n'
