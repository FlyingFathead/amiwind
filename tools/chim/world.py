# SPDX-License-Identifier: GPL-3.0-only
"""Assemble a CHIM world: chunks, placements, shared models and textures, sector files, index.

Generic over its inputs: the units (models, textures, chunk terrain) are
built and cached by chim.build through chim.units; this module lays them out.
Rules (docs/chim/WORLD_FORMAT.md):

- a frame is a square of 3 x 3 exterior cells cut into chunks of `grain`
  units, grouped in sectors of sector_chunks x sector_chunks chunks; one file
  per sector, sectors and the chunks inside them in Hilbert order (pack
  order = read order);
- a placement is owned by the chunk holding its origin (one owner record,
  exactly once) and copied, as a placement record only, into every other
  chunk its drawn bounds touch (reach copies; the bounds rule);
- models and textures get ids in the order a walk through the pack first
  meets them (chunk order; a chunk's ground, then its placements by id), are
  stored in the sector file where they are first met (their home sector),
  after that sector's chunks, and identical content is stored once.
"""
import hashlib
import json
import math
import os
import struct
from pathlib import Path

from chim import BUILDER, CHIM_VERSION, FORMAT_VERSION, REFS_FORMAT_VERSION
from chim import format as F
from chim.visibility import bits_to_row, compress_row

DEFAULT_SETTINGS = {'draw_distance': 540.0, 'hysteresis': 96.0, 'collision_margin': 224.0,
                    'prefetch_margin': 256.0, 'grain': 256, 'sector_chunks': 3}


def frame_dir(cell):
    return 'x%+03d' % cell[0]


def frame_subdir(cell):
    return 'y%+03d' % cell[1]


def f32(x):
    return struct.unpack('>f', struct.pack('>f', x))[0]


def stored_box(lo, hi):
    """The drawn box as a record stores it: shorts, one unit outward (AW_SceneryCapture's +-1), rounded out."""
    return (tuple(int(math.floor(v - 1)) for v in lo), tuple(int(math.ceil(v + 1)) for v in hi))


def yaw_points(points, origin, yaw):
    """Model-frame points placed with an entity origin and yaw (degrees)."""
    import numpy as np
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    p = np.asarray(points, float)
    return np.column_stack([p[:, 0] * c - p[:, 1] * s, p[:, 0] * s + p[:, 1] * c, p[:, 2]]) + np.asarray(origin)


def placed_box(origin, yaw, lo, hi):
    """Drawn box of a placement, as the engine computes it (aw_scenery.c AW_SceneryCapture). yaw: degrees, or the
    three Quake angles (pitch, yaw, roll) of a format 0.8 record (chim.placed)."""
    from world_chunk_estimate import placed_box as box
    return box(origin, tuple(yaw) if isinstance(yaw, (tuple, list)) else (0.0, yaw, 0.0), lo, hi)


def turn_of(p):
    """What turns a placement row: its format 0.8 angles (single precision), else its yaw (single precision)."""
    return tuple(f32(a) for a in p['angles']) if 'angles' in p else f32(p['yaw'])


class World:
    def __init__(self, frame, settings=None):
        self.frame = dict(frame)
        self.settings = dict(DEFAULT_SETTINGS, **(settings or {}))
        g = self.settings['grain']
        self.frame['grain'] = g
        span = self.frame['span']
        if span[0] % g or span[1] % g:
            raise ValueError('Chunk grain must divide the frame span')
        self.nx, self.ny = int(span[0] // g), int(span[1] // g)
        self.sector_chunks = int(self.settings['sector_chunks'])
        self.order, self.sectors = F.sector_order(self.nx, self.ny, self.sector_chunks)
        self.chunk_index = {c: i for i, c in enumerate(self.order)}

    def chunk_of(self, x, y):
        g, (lx, ly) = self.settings['grain'], self.frame['low']
        return (min(self.nx - 1, max(0, int((x - lx) // g))), min(self.ny - 1, max(0, int((y - ly) // g))))

    def chunk_box(self, c):
        g, (lx, ly) = self.settings['grain'], self.frame['low']
        return (lx + c[0] * g, ly + c[1] * g, lx + (c[0] + 1) * g, ly + (c[1] + 1) * g)

    def touched(self, lo, hi):
        a, b = self.chunk_of(lo[0], lo[1]), self.chunk_of(hi[0], hi[1])
        return {(x, y) for x in range(a[0], b[0] + 1) for y in range(a[1], b[1] + 1)}


PVS_BLOCKS = 32         # visibility rows are computed in this many blocks of source chunks


def chunk_visibility(world, terrain, by_chunk, variants, visibility, jobs=1, cache=None):
    """Cluster PVS of every chunk ({chunk: set of chunks}) and its statistics.

    visibility: None (every chunk of the ring is visible) or {'heights',
    'step', 'low'}: ground heights at tile corners, or (format 0.5) {'triangles',
    'step', 'low', 'size'}: the ground's own triangles. The pair tests run in
    blocks of source chunks through the unit pool; the result does not depend
    on the block size or the worker count."""
    from asset_census import ring_offsets
    from chim.units import fingerprint, run_units
    from chim.visibility import CELL, Ground, Occluders, pvs_unit
    s = world.settings
    offsets = ring_offsets(s['grain'], s['draw_distance'] + s['hysteresis'])
    inside = lambda c: 0 <= c[0] < world.nx and 0 <= c[1] < world.ny  # noqa: E731
    ring = {c: {(c[0] + dx, c[1] + dy) for dx, dy in offsets if inside((c[0] + dx, c[1] + dy))} for c in world.order}
    candidates, near = {}, {}
    for c in world.order:
        cand = set()
        for b in ring[c]:
            cand.update(p['_pid'] for kind in ('owned', 'reach') for p in by_chunk[b][kind])
        candidates[c] = sorted(cand)
        nb = set()
        for b in ((c[0] + dx, c[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
            if b in by_chunk:
                nb.update(p['_pid'] for kind in ('owned', 'reach') for p in by_chunk[b][kind])
        near[c] = sorted(nb)
    if visibility is None:
        return ring, {c: set(candidates[c]) for c in world.order}, {'method': 'ring (no occlusion data)'}
    from scipy.spatial import ConvexHull
    if visibility.get('triangles') is not None:
        from chim.ground import TriangleGround
        ground = TriangleGround(visibility['triangles'], visibility['step'], visibility['low'], visibility['size'])
        ground_key = ('triangles', ground.rows(), ground.step, ground.low)
    else:
        ground = Ground(visibility['heights'], visibility['step'], visibility['low'])
        ground_key = (ground.h, ground.step, ground.low)
    occ = Occluders(world.frame['low'], world.frame['span'])
    from chim.occluders import place_columns
    mesh_pieces = 0
    for c in world.order:
        for p in sorted(by_chunk[c]['owned'], key=lambda q: q['_pid']):
            v = variants[p['variant']]
            # format 0.8 (chim.placed): a record turned by pitch or roll too places its pieces with its three angles
            tilted = 'angles' in p and (p['angles'][0] or p['angles'][2])
            for pts in v['occluders']:
                if tilted:
                    from chim.placed import place_points
                    q = place_points(pts, p['origin'], p['angles'])
                else:
                    q = yaw_points(pts, p['origin'], p['yaw'])
                try:
                    occ.add(ConvexHull(q).equations, q)
                except Exception:  # noqa: BLE001 - a flat or degenerate piece occludes nothing
                    continue
            # the solid columns of a hollow shell are placed by yaw only: a tilted 0.8 record adds none (it then
            # occludes less, never more)
            if v.get('occluder_grid') and visibility.get('mesh_occluders', True) and not tilted:
                mesh_pieces += 1
                for i, j, z0, z1 in place_columns(v['occluder_grid'], p['origin'], p['yaw'], CELL,
                                                  world.frame['low'], occ.nx, occ.ny):
                    occ.add_interval(i, j, z0, z1)
    tops = {}
    for c in world.order:
        top = terrain[c]['info']['zmax']
        for kind in ('owned', 'reach'):
            for p in by_chunk[c][kind]:
                top = max(top, p['_box'][1][2])
        tops[c] = top
    args = (world.nx, world.ny, s['grain'], world.frame['low'], ground, occ, tops, offsets)
    whole = fingerprint('pvs', *ground_key, occ.lo, occ.hi, sorted(tops.items()), offsets,
                        world.nx, world.ny, s['grain'], world.frame['low'])
    # A fixed block count: the cached units do not depend on the worker count (CHIM-PVS-CACHE-JOBS-33).
    blocks = max(1, min(len(world.order), PVS_BLOCKS))
    sources = [world.order[k::blocks] for k in range(blocks)]
    items = [(fingerprint('pvs', whole, src), {'args': args, 'sources': src}) for src in sources]
    seen = {c: {c} for c in world.order}
    stats = {'pairs_tested': 0, 'pairs_blocked': 0}
    for res in run_units('pvs', items, pvs_unit, jobs, cache):
        for a, b in res['pairs']:
            seen[a].add(b)
            seen[b].add(a)
        for k in stats:
            stats[k] += res['stats'][k]
    stats.update(method='sampled sight lines over ground and solid occluders', occluder_pieces=occ.pieces,
                 occluder_meshes=mesh_pieces, occluder_cells=occ.cells())
    # potentially visible placements per chunk: the same sight lines to each placement's drawn box
    from chim.visibility import pvl_unit
    boxes = {p['_pid']: p['_box'] for c in world.order for p in by_chunk[c]['owned']}
    pargs = (s['grain'], world.frame['low'], ground, occ)
    # Placement ids run on across frames (frame_layout), so one placement more in an earlier frame renumbered every
    # later frame's: keyed by those ids, every placement-visibility unit of the island was computed again for a
    # change elsewhere (BUILD-CHIM-VIS-RECOMPUTED-48). A unit is keyed and computed in the frame's own numbering (id
    # minus the frame's first id) and by what it reads: the ground, the occluder grid, grain and frame corner, its
    # viewers, their candidates and near sets and the boxes of those candidates (not the chunk tops, the ring or the
    # other placements' boxes); its result is renumbered back.
    base = min(boxes) if boxes else 0
    plocal = fingerprint('pvs', 'placement inputs', *ground_key, occ.lo, occ.hi, s['grain'], world.frame['low'])
    pwhole = None
    pitems, earlier = [], []
    for src in sources:
        cand = {c: [p - base for p in candidates[c]] for c in src}
        nr = {c: [p - base for p in near[c]] for c in src}
        used = sorted({p for c in src for p in cand[c]})
        task = {'args': pargs, 'viewers': src, 'candidates': cand, 'near': nr,
                'boxes': {p: boxes[p + base] for p in used}}
        pitems.append((fingerprint('pvs', 'placements local', plocal, src, [cand[c] for c in src],
                                   [nr[c] for c in src], [task['boxes'][p] for p in used]), task))
        if cache is not None:
            # the unit as keyed before (frame-wide ids, whole-frame inputs): reused once, renumbered
            if pwhole is None:
                pwhole = fingerprint('pvs', whole, sorted(boxes.items()))
            earlier.append(fingerprint('pvs', 'placements', pwhole, src, [candidates[c] for c in src],
                                       [near[c] for c in src]))
    results, todo = {}, []
    for i, (fp, task) in enumerate(pitems):
        hit = cache.get('pvs', fp) if cache is not None else None
        if hit is None and cache is not None:
            old = cache.get('pvs', earlier[i])
            if old is None and getattr(earlier[i], 'previous', None):
                old = cache.get('pvs', earlier[i].previous)
            if old is not None:
                hit = {'visible': {key: [p - base for p in pids] for key, pids in old['visible'].items()},
                       'stats': old['stats']}
                cache.put('pvs', fp, hit)
                counts = cache.stats.setdefault('pvs', {})
                counts['reused_earlier_key'] = counts.get('reused_earlier_key', 0) + 1
        if hit is None:
            todo.append(i)
        else:
            results[i] = hit
    if results:
        cache.count('pvs', 0, len(results))
    results.update(zip(todo, run_units('pvs', [pitems[i] for i in todo], pvl_unit, jobs, cache)))
    pvl = {}
    pstats = {'placements_tested': 0, 'placements_blocked': 0}
    for i in range(len(pitems)):
        res = results[i]
        for key, pids in res['visible'].items():
            pvl[tuple(int(v) for v in key.split(','))] = {p + base for p in pids}
        for k in pstats:
            pstats[k] += res['stats'][k]
    stats.update(pstats)
    return {c: seen[c] & ring[c] for c in world.order}, pvl, stats


def placed_tree(unit, cache):
    """The tree a placement's leaves are counted on: the unit's own TerrainTree, or for a referenced unit
    ('offset', format 0.7) the tree of its image as the engine places it (chim.format.translate_image, single
    precision planes), so the builder, the validator and the engine count the same leaves."""
    d = unit.get('offset')
    if not d:
        return unit['info']['tree']
    key = id(unit)
    if key not in cache:
        import numpy as np
        from chim.terrain import TerrainTree
        lumps = F.read_brush_image(F.translate_image(F.brush_image(unit['lumps'])[0], d))
        planes = list(struct.iter_unpack('<4fi', lumps[1]))
        tree = TerrainTree()
        tree.nodes = [(np.array(planes[n[0]][:3]), planes[n[0]][3], n[1], n[2])
                      for n in struct.iter_unpack('<ihh6h2H', lumps[5])]
        tree.leaves = [lf[0] for lf in struct.iter_unpack('<2i6h2H4B', lumps[10])]
        cache[key] = tree
    return cache[key]


def resolved_image(lumps, texture_keys, texture_id_of):
    """A unit's brush image with its texture keys turned into global texture ids.

    Two keys may name one stored texture (identical content); their local
    indices are merged, so every texture is referenced once per image."""
    lumps = list(lumps)
    ids = [texture_id_of(k) for k in texture_keys]
    unique = list(dict.fromkeys(ids))
    if len(unique) != len(ids):
        local = {i: unique.index(t) for i, t in enumerate(ids)}
        texinfo = bytearray(lumps[6])
        for at in range(32, len(texinfo), 40):
            struct.pack_into('<i', texinfo, at, local[struct.unpack_from('<i', texinfo, at)[0]])
        lumps[6] = bytes(texinfo)
    lumps[2] = F.texture_refs(unique)
    return F.brush_image(lumps)


def write_if_changed(path, data):
    """Write a pack whole; an identical existing file is left as it is. Returns True when written."""
    path = Path(path)
    if path.is_file() and path.stat().st_size == len(data) and path.read_bytes() == data:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_bytes(data)
    tmp.replace(path)
    return True


SECTOR_GROUP = 64       # sector files per subdirectory of a frame too large for one FFS directory


def sector_path(index, count):
    """A sector file's path below its frame directory: beside frame.ccf while the frame's files fit one
    classic FFS directory (every frame up to 8 x 8 sectors: the paths are unchanged), else in groups
    of SECTOR_GROUP (g0/, g1/, ...), as a frame with a terrain-only margin needs (10 x 10 sectors for
    bcoast_x7y2, CHIM-FAR-BAND-GAP-36). The engine opens every file by its index path."""
    if count + 1 <= F.FFS_MAX_DIRECTORY_ENTRIES:
        return F.sector_name(index)
    return 'g%d/%s' % (index // SECTOR_GROUP, F.sector_name(index))


CHIM_SUFFIXES = ('.cwi', '.ccf', '.ccs', '.ccp', '.cmp', '.ctp', '.tmp')


def remove_stale(root, keep):
    """Remove CHIM files under root that this build did not write (an older layout or frame), then
    empty directories. Only files with CHIM suffixes are touched. Returns the removed paths."""
    removed = []
    root = Path(root)
    for p in sorted(root.rglob('*')):
        rel = p.relative_to(root).as_posix()
        if p.is_file() and p.suffix in CHIM_SUFFIXES and rel not in keep:
            p.unlink()
            removed.append(rel)
    for d in sorted((p for p in root.rglob('*') if p.is_dir()), key=lambda p: -len(p.parts)):
        if not any(d.iterdir()):
            d.rmdir()
    return removed


def build_world(out, frame, placements, variants, textures, terrain, settings=None, terrain_light=12,
                visibility=None, jobs=1, cache=None, timer=None):
    """A world of one frame (build_frames with one frame input); returns the receipt.

    placements: [dict(ref, cell, origin, yaw, variant)];
    variants: {key: dict(name, lo, hi, lumps, texture_keys, occluders)};
    textures: {key: dict(identity, miptex, size, engine)}: engine (kind, glow)
    names the texture by its id (surfaceN, emitG_N, flatN), None keeps the
    miptex's own name;
    terrain: {chunk: dict(lumps, texture_keys, info)} for every chunk."""
    return build_frames(out, [{'frame': frame, 'placements': placements, 'variants': variants,
                               'textures': textures, 'terrain': terrain, 'visibility': visibility}],
                        settings, terrain_light, jobs, cache, timer)


def frame_box(frame):
    """A frame's owned box in Morrowind units (x0, y0, x1, y1): centre + 4 x the frame-local box. The box
    is the frame's ground, or, for a frame with a terrain-only margin, the box it owns ('owned': its bounds):
    neighbouring frames may share margin terrain (each stores its own copy), never placements."""
    c = frame['centre']
    if frame.get('owned'):
        (lx, ly), (hx, hy) = frame['owned']
        return (c[0] + 4 * lx, c[1] + 4 * ly, c[0] + 4 * hx, c[1] + 4 * hy)
    (lx, ly), (sx, sy) = frame['low'], frame['span']
    return (c[0] + 4 * lx, c[1] + 4 * ly, c[0] + 4 * (lx + sx), c[1] + 4 * (ly + sy))


def frame_order(frames):
    """Frames in pack order: Hilbert order of their cells (ties by cell)."""
    cells = [tuple(f['frame']['cell']) for f in frames]
    if len(set(cells)) != len(cells):
        raise ValueError('Two frames share the cell %s' % (sorted(c for c in cells if cells.count(c) > 1)[0],))
    boxes = [frame_box(f['frame']) for f in frames]
    # every pair of frames that share a grid bucket (a cell) is compared, not every pair of the world (1,351 frames:
    # 912,000 pairs on one core, BUILD-CHIM-SERIAL-SECTIONS-44); the first overlapping pair in frame order is named
    grid = {}
    for k, (x0, y0, x1, y1) in enumerate(boxes):
        for bx in range(int(math.floor(x0 / 8192.0)), int(math.floor(x1 / 8192.0)) + 1):
            for by in range(int(math.floor(y0 / 8192.0)), int(math.floor(y1 / 8192.0)) + 1):
                grid.setdefault((bx, by), []).append(k)
    pairs = set()
    for members in grid.values():
        for n, i in enumerate(members):
            for j in members[n + 1:]:
                a, b = boxes[i], boxes[j]
                if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                    pairs.add((min(i, j), max(i, j)))
    if pairs:
        i, j = min(pairs)
        raise ValueError('Frames %s and %s overlap: a placement or tile would be stored twice' % (cells[i], cells[j]))
    lo = (min(c[0] for c in cells), min(c[1] for c in cells))
    side = 1
    while side < max(max(c[0] - lo[0], c[1] - lo[1]) + 1 for c in cells):
        side *= 2
    return sorted(range(len(frames)), key=lambda k: (F.hilbert_index(side, cells[k][0] - lo[0], cells[k][1] - lo[1]),
                                                     cells[k]))


VIS_ROWS_ENV = 'AMIWIND_CHIM_VIS_ROWS'
# frames (default since v0.0.44): each frame's layout and visibility rows made together on a worker; frames-parent
# (the method of v0.0.43): the layouts made in the parent while the pool works out the rows; serial (before v0.0.42)
VIS_ROWS_MODES = ('frames', 'frames-parent', 'serial')
# A frame of at most this many chunks (a region frame: one cell, 15 x 15 chunks) has its visibility rows worked out
# whole on one worker; larger frames (towns: 576 to 2,916 chunks in dev5) spread their own blocks over every
# worker, one frame after another.
FRAME_VIS_CHUNKS = 256


def _visibility_inputs(spec, layout, settings):
    """What chunk_visibility reads of one frame, without the terrain images and model lumps."""
    world, by_chunk, _, _, _ = layout
    keep = ('_pid', '_box', 'variant', 'origin', 'yaw', 'angles')      # angles: format 0.8 records only
    rows = {c: {kind: [{k: p[k] for k in keep if k in p} for p in by_chunk[c][kind]] for kind in ('owned', 'reach')}
            for c in world.order}
    # variant keys mix model numbers and ('tile', ...) tuples (chim/build.py terrain tiles): order them by repr
    used = {p['variant'] for c in world.order for p in by_chunk[c]['owned']}
    variants = {k: {'occluders': spec['variants'][k]['occluders'],
                    **({'occluder_grid': spec['variants'][k]['occluder_grid']}
                       if spec['variants'][k].get('occluder_grid') else {})} for k in sorted(used, key=repr)}
    terrain = {c: {'info': {'zmax': spec['terrain'][c]['info']['zmax']}} for c in world.order}
    return spec['frame'], settings, terrain, rows, variants, spec.get('visibility')


def _frame_visibility_task(task):
    """Worker of frame_visibility: one frame's visibility rows on one worker, and its unit counts."""
    frame, settings, terrain, rows, variants, visibility, cache = task
    world = World(frame, settings)
    result = chunk_visibility(world, terrain, rows, variants, visibility, 1, cache)
    if cache is None:
        return result, {}, None
    return result, cache.stats, getattr(cache, 'pool_stats', None)


def _layout_inputs(spec):
    """What frame_layout and the visibility rows read of one frame, sent to a worker: the placements whole, of each
    variant its bounds and occluders, of each chunk's terrain the tree a placement's leaves are counted on (or the
    referenced image it is made from) and its top; no model lumps, textures or terrain images otherwise."""
    variants = {}
    for k in {p['variant'] for p in spec['placements']}:
        v = spec['variants'][k]
        variants[k] = {'lo': v['lo'], 'hi': v['hi'], 'occluders': v['occluders'],
                       **({'occluder_grid': v['occluder_grid']} if v.get('occluder_grid') else {})}
    terrain = {}
    for c, t in spec['terrain'].items():
        row = {'info': {'zmax': t['info']['zmax']}}
        if 'offset' in t:
            row.update(offset=t['offset'], lumps=t['lumps'])
        if not t.get('offset'):
            row['info']['tree'] = t['info']['tree']
        terrain[c] = row
    return {'frame': spec['frame'], 'placements': spec['placements'], 'variants': variants, 'terrain': terrain,
            'visibility': spec.get('visibility')}


def packed_rows(order, base, owned_total, pvs, pvl, chunks=None):
    """{chunk: (compressed PVS row, compressed placement row)} of one frame: the parts of its chunk records that do
    not depend on the model and texture ids the pack walk hands out, so they are made on the workers
    (BUILD-CHIM-SERIAL-SECTIONS-44). ORDER: the frame's chunks in pack order; BASE: its first placement id;
    CHUNKS: only these (default every chunk of ORDER)."""
    index = {c: k for k, c in enumerate(order)}
    out = {}
    for c in order if chunks is None else chunks:
        bits = [False] * len(order)
        for b in pvs[c]:
            bits[index[b]] = True
        pbits = [False] * owned_total
        for q in pvl[c]:
            pbits[q - base] = True
        out[c] = (compress_row(bits_to_row(bits)), compress_row(bits_to_row(pbits)))
    return out


def shift_refusals(terrain):
    """{chunk: why} of the referenced chunk terrain that cannot be placed at its shift (F.refuse_shift on the
    unit's own image: the check reads the texture axes, which the pack's texture ids leave as they are)."""
    out = {}
    for c, t in terrain.items():
        if 'offset' in t:
            out[c] = F.refuse_shift(F.brush_image(t['lumps'])[0], t['offset'])
    return out


def _packed_rows_task(task):
    """Worker: packed_rows of one large frame's chunk slice. TASK: (order, base, owned count, slice, pvs, pvl)."""
    order, base, owned_total, part, pvs, pvl = task
    return packed_rows(order, base, owned_total, pvs, pvl, part)


def _frame_rows_task(task):
    """Worker of frame_rows: one frame's placement layout (ids from BASE) and, with ROWS, its visibility rows.
    Returns ((by_chunk, placement rows, first id, owned count, next id), rows or None, unit counts, pool counts)."""
    inputs, settings, base, rows, cache = task
    layout, end = frame_layout(inputs, settings, base)
    world, by_chunk, rows_in, first, owned_total = layout
    refused = shift_refusals(inputs['terrain'])
    if not rows:
        return (by_chunk, rows_in, first, owned_total, end, refused), None, {}, None
    result, stats, pool_stats = _frame_visibility_task((*_visibility_inputs(inputs, layout, settings), cache))
    pvs, pvl, vis_stats = result
    packed = packed_rows(world.order, first, owned_total, pvs, pvl)
    return (by_chunk, rows_in, first, owned_total, end, refused), (packed, vis_stats), stats, pool_stats


def _add_unit_counts(cache, stats, pool_stats):
    """A worker's unit counts added to the parent's cache counts."""
    if cache is None:
        return
    for kind, counts in stats.items():
        mine = cache.stats.setdefault(kind, {})
        for k, v in counts.items():
            mine[k] = mine.get(k, 0) + v
    if pool_stats and hasattr(cache, 'pool_stats'):
        for k, v in pool_stats.items():
            cache.pool_stats[k] = cache.pool_stats.get(k, 0) + v


def frame_rows(specs, bases, settings=None, jobs=1, cache=None):
    """([layout], [rows], [shift refusals or None]) of every frame, in the order given (BUILD-CHIM-SERIAL-SECTIONS-44).
    A frame's rows are (pvs, pvl, stats) (the earlier methods) or ({chunk: packed rows}, stats) (packed_rows); its
    shift refusals ({chunk: why}, shift_refusals) or None when the pack checks them itself.

    Each frame's placement layout (ids from BASES[i]) is made on a worker, and a frame of at most FRAME_VIS_CHUNKS
    chunks works out its visibility rows on the same worker in the same task; larger frames (towns) get their
    layout there too and then spread their own row blocks over every worker, one after another. In v0.0.43 the
    layouts were made in the parent while the pool asked for them (frame_visibility with a layout function): the
    parent could not keep up and the workers starved (v0.0.44-dev1: 3 min 7 s at 4.9 of 24 cores, 523 frames
    queued and none running). Same layouts, same unit keys, same rows: the world files are byte-identical.
    AMIWIND_CHIM_VIS_ROWS=frames-parent or serial keep the earlier methods."""
    mode = os.environ.get(VIS_ROWS_ENV, 'frames')
    if mode not in VIS_ROWS_MODES:
        raise ValueError('%s=%s: choose %s' % (VIS_ROWS_ENV, mode, ' or '.join(VIS_ROWS_MODES)))
    made = [None] * len(specs)

    def check(i, end):
        if end != bases[i] + len(specs[i]['placements']):
            raise ValueError('Frame %s: placement ids %d-%d, expected %d' % (
                specs[i]['frame'].get('cell'), bases[i], end, len(specs[i]['placements'])))

    def layout_of(i):
        if made[i] is None:
            layout, end = frame_layout(specs[i], settings, bases[i])
            check(i, end)
            made[i] = layout
        return made[i]
    from build_parallel import stage_ceiling
    if mode != 'frames' or stage_ceiling(jobs) <= 1 or len(specs) <= 1:
        results = frame_visibility(specs, layout_of, settings, jobs, cache)
        return [layout_of(i) for i in range(len(specs))], results, [None] * len(specs)
    from build_parallel import ordered_map
    import progress_line
    jobs = stage_ceiling(jobs)
    worlds = [World(spec['frame'], settings) for spec in specs]
    chunks = [w.nx * w.ny for w in worlds]
    small = {i for i in range(len(specs)) if chunks[i] <= FRAME_VIS_CHUNKS}
    results = [None] * len(specs)
    prepared = [None] * len(specs)      # per frame: the shift refusals of its referenced terrain
    # largest first by the frame's own size (its placements and chunks): the towns' layouts lead
    order = sorted(range(len(specs)), key=lambda i: (-(len(specs[i]['placements']) + chunks[i]), i))

    def tasks():
        for i in order:
            yield (_layout_inputs(specs[i]), settings, bases[i], i in small, _unit_cache_copy(cache))
    done = 0
    for i, (parts, result, stats, pool_stats) in zip(order, ordered_map(_frame_rows_task, tasks(),
                                                                        max(1, min(jobs, len(specs))))):
        by_chunk, rows_in, first, owned_total, end, refused = parts
        check(i, end)
        made[i] = (worlds[i], by_chunk, rows_in, first, owned_total)
        prepared[i] = refused
        if result is not None:
            results[i] = result
            _add_unit_counts(cache, stats, pool_stats)
        done += 1
        if done % 50 == 0 or done == len(specs):
            progress_line.emit('CHIM visibility rows', 'frames', 'layout and rows, one frame per worker',
                               (done, len(specs), 'frames'))
    for i in range(len(specs)):
        if results[i] is None:
            # a large frame spreads its own blocks over every worker (one frame after another), then its packed
            # rows in slices of chunks (a town: thousands of chunks times thousands of placements)
            world, by_chunk, _, first, owned_total = made[i]
            pvs, pvl, vis_stats = chunk_visibility(world, specs[i]['terrain'], by_chunk, specs[i]['variants'],
                                                   specs[i].get('visibility'), jobs, cache)
            step = max(1, -(-len(world.order) // (4 * jobs)))
            parts = [world.order[k:k + step] for k in range(0, len(world.order), step)]
            packed = {}
            for found in ordered_map(_packed_rows_task, [(world.order, first, owned_total, part,
                                                          {c: pvs[c] for c in part}, {c: pvl[c] for c in part})
                                                         for part in parts], max(1, min(jobs, len(parts)))):
                packed.update(found)
            results[i] = (packed, vis_stats)
    return made, results, prepared


def frame_visibility(specs, layouts, settings=None, jobs=1, cache=None):
    """[(pvs, pvl, stats)] of every frame, in the order given (B5, v0.0.42).

    The method before v0.0.42 (AMIWIND_CHIM_VIS_ROWS=serial) worked each frame out in turn, its blocks on the
    workers: the hundreds of one-cell region frames of a regional world (32 blocks each, most of them reused
    from the unit cache, looked up and decoded here) then kept one core busy for about four minutes (dev5).
    Now frames of at most FRAME_VIS_CHUNKS chunks go whole to the workers, largest first, beside each other;
    larger frames keep their blocks spread over every worker. The unit keys do not change, so the rows are the
    same and the cached units are reused.

    LAYOUTS: the frames' layouts (a list), or layout(i) -> the layout of frame i, made when first asked: the
    small frames' layouts are then made while the workers already work out the rows of the frames before them
    (BUILD-CHIM-REGION-FRAMES-TAIL-43: the layouts of 1,351 frames took 3 min 42 s on one core before the rows
    started). The size order comes from the frames themselves (their placements and chunks), so no layout is
    needed to choose it."""
    mode = os.environ.get(VIS_ROWS_ENV, 'frames')
    if mode not in VIS_ROWS_MODES:
        raise ValueError('%s=%s: choose %s' % (VIS_ROWS_ENV, mode, ' or '.join(VIS_ROWS_MODES)))
    mode = 'frames' if mode == 'frames-parent' else mode
    layout_of = layouts if callable(layouts) else layouts.__getitem__
    results = [None] * len(specs)
    small, large = [], []
    # the stage's ceiling, not its launch share: a stage started on one worker still sends its frames to the pool,
    # which follows the scheduler's live allowance (build_parallel.stage_ceiling, BUILD-CHIM-STAIR-JOBS-AT-LAUNCH-42)
    from build_parallel import stage_ceiling
    jobs = stage_ceiling(jobs)
    chunks = [World(spec['frame'], settings) for spec in specs]
    chunks = [w.nx * w.ny for w in chunks]
    for i in range(len(specs)):
        if mode == 'frames' and jobs > 1 and len(specs) > 1 and chunks[i] <= FRAME_VIS_CHUNKS:
            small.append(i)
        else:
            large.append(i)
    if small:
        from build_parallel import ordered_map
        import progress_line
        # largest first by the frame's own size; the generator makes each layout when the pool asks for the task
        small.sort(key=lambda i: (-(len(specs[i]['placements']) + chunks[i]), i))

        def tasks():
            for i in small:
                yield (*_visibility_inputs(specs[i], layout_of(i), settings), _unit_cache_copy(cache))
        done = 0
        for i, (result, stats, pool_stats) in zip(small, ordered_map(_frame_visibility_task, tasks(),
                                                                     max(1, min(jobs, len(small))))):
            results[i] = result
            if cache is not None:
                for kind, counts in stats.items():
                    mine = cache.stats.setdefault(kind, {})
                    for k, v in counts.items():
                        mine[k] = mine.get(k, 0) + v
                if pool_stats and hasattr(cache, 'pool_stats'):
                    for k, v in pool_stats.items():
                        cache.pool_stats[k] = cache.pool_stats.get(k, 0) + v
            done += 1
            if done % 50 == 0 or done == len(small):
                progress_line.emit('CHIM visibility rows', 'frames', 'one frame per worker', (done, len(small), 'frames'))
    for i in large:
        # a large frame spreads its own blocks over every worker (one frame after another)
        world, by_chunk = layout_of(i)[0], layout_of(i)[1]
        results[i] = chunk_visibility(world, specs[i]['terrain'], by_chunk, specs[i]['variants'],
                                      specs[i].get('visibility'), jobs, cache)
    return results


def _unit_cache_copy(cache):
    """A worker's copy of the unit cache: the same folder (and pool), its own counts."""
    if cache is None:
        return None
    import copy
    clone = copy.copy(cache)
    clone.stats = {}
    if hasattr(clone, 'pool_stats'):
        clone.pool_stats = {k: 0 for k in clone.pool_stats}
        clone._keys = {}
    return clone


def frame_layout(spec, settings, pid):
    """((world, by_chunk, placement rows, first id, owned count), next id) of one frame: every placement with its
    stored origin, box, owning chunk, touched chunks, leaves and id (ids run on from PID, chunk by chunk)."""
    world = World(spec['frame'], settings)
    variants, terrain = spec['variants'], spec['terrain']
    by_chunk = {c: {'owned': [], 'reach': []} for c in world.order}
    seen_refs = set()
    rows_in = []
    for p in spec['placements']:
        if p['ref'] in seen_refs:
            raise ValueError('Placement %d listed twice' % p['ref'])
        seen_refs.add(p['ref'])
        v = variants[p['variant']]
        # origin, yaw and model bounds as stored (single precision), so the engine and
        # the validator derive the same box from the files
        p = dict(p, origin=tuple(f32(x) for x in p['origin']), yaw=f32(p['yaw']))
        if 'angles' in p:
            p['angles'] = turn_of(p)        # format 0.8 (chim.placed): the stored angles turn the box
        box = stored_box(*placed_box(p['origin'], turn_of(p), [f32(x) for x in v['lo']], [f32(x) for x in v['hi']]))
        owner = world.chunk_of(p['origin'][0], p['origin'][1])
        p = dict(p, _owner=owner, _box=box, _touched=world.touched(*box) | {owner})
        by_chunk[owner]['owned'].append(p)
        rows_in.append(p)
    base = pid
    trees = {}
    for c in world.order:
        for p in sorted(by_chunk[c]['owned'], key=lambda q: q['ref']):
            p['_pid'] = pid
            pid += 1
            for t in sorted(p['_touched'] - {c}):
                by_chunk[t]['reach'].append(p)
    owned_total = pid - base
    for p in rows_in:
        lo, hi = p['_box']
        p['_leaves'] = sum(len(placed_tree(terrain[c], trees).leaves_touched(lo, hi)) for c in p['_touched'])
    return (world, by_chunk, rows_in, base, owned_total), pid


def build_frames(out, frames, settings=None, terrain_light=12, jobs=1, cache=None, timer=None):
    """Write chim/ under `out` for one or more frames; returns the receipt.

    frames: [dict(frame, placements, variants, textures, terrain, visibility)]
    (build_world's arguments per frame). Variant and texture keys are local to
    their frame; identical content is stored once across all frames. Frames
    are laid out in Hilbert order of their cells; placement ids run on across
    frames; model and texture ids follow the pack walk over every frame."""
    from contextlib import nullcontext
    from chim.models import engine_texture_name
    section = timer.section if timer else (lambda name: nullcontext())
    if not frames:
        raise ValueError('A world needs at least one frame')
    order = frame_order(frames)
    import progress_line
    root = Path(out) / 'chim'
    texture_ids, texture_content, texture_records, texture_names = {}, {}, [], {}
    model_ids, model_content, model_records, aliases, model_names = {}, {}, [], [], {}
    homed = {'textures': [], 'models': [], 'terrain': []}     # ids first met in the sector being assembled
    # Terrain references (format 0.7): a chunk terrain unit with an 'offset' is chunk-local; its image is stored
    # once per content (a TERR record homed in the sector that first meets it) and placed by every chunk with it.
    refs = any('offset' in t for spec in frames for t in spec['terrain'].values())
    # Format0.7 readers already accept both CHK0 inline and CHK1 referenced terrain.
    # Keep earlier frames inline when new ocean frames use shared TERR records.
    version = REFS_FORMAT_VERSION if refs else FORMAT_VERSION
    # EXPERIMENTAL world format 0.8 (chim.placed): placement rows with three angles; 56-byte records in every chunk
    placed = any('angles' in p for spec in frames for p in spec['placements'])
    if placed:
        from chim import placed as P
        version = P.FORMAT_VERSION
        write_record = lambda *a, **k: P.placement(*a, **k)                    # noqa: E731
        write_chunk, write_chunk_ref = P.chunk_record, P.chunk_record_ref
    else:
        write_record, write_chunk, write_chunk_ref = F.placement, F.chunk_record, F.chunk_record_ref
    # EXPERIMENTAL world format 0.9 (chim.reach, build setting reach_index refs): a reach copy becomes a 4-byte
    # reference to the owner record; off (default), nothing below changes
    reach_refs = (settings or {}).get('reach_index', 'copies') != 'copies'
    if reach_refs:
        from chim import reach as RI
        RI.reach_mode(settings)                         # refused before any file is written (fail fast)
        if not placed:
            raise ValueError('The reach index (world format 0.9) needs placement format 0.8 records')
        version = RI.FORMAT_VERSION
        write_chunk, write_chunk_ref = RI.chunk_record, RI.chunk_record_ref
    # EXPERIMENTAL world format 0.10 (chim.terc, build setting terrain_pack compact): a TERR record stored compact when
    # that is smaller and fits the engine's loading buffer (the engine expands it to the same bytes); off (default),
    # nothing below changes
    terc_on = (settings or {}).get('terrain_pack', 'bsp29') != 'bsp29'
    if terc_on:
        from chim import terc as TC
        generate_on = TC.terrain_pack(settings) == 'generate'     # refused before any file is written (fail fast)
        if not refs:
            raise ValueError('The compact terrain pack (world format 0.10) needs terrain references')
        version = TC.FORMAT_VERSION
        if generate_on:
            # EXPERIMENTAL world format 0.11 (chim.thgt): a regular-path record as heights and facts the engine
            # generates the same bytes from; every other record compact as above
            from chim import thgt as TG
            version = TG.FORMAT_VERSION
    terc_count, terc_saved, thgt_count, thgt_saved = 0, 0, 0, 0
    generate_on = False if not terc_on else generate_on
    terrain_content, terrain_records, terrain_at = {}, [], {}

    def texture_id_of(fi, key):
        if (fi, key) not in texture_ids:
            src = frames[fi]['textures'][key]
            mip = src['miptex']
            engine = mip[:16].split(b'\0')[0].decode('ascii') if src['engine'] is None else \
                engine_texture_name(src['engine'][0], src['engine'][1], len(texture_records))
            digest = hashlib.sha256(F.texture_content(engine, mip)).hexdigest()
            if digest not in texture_content:
                # an identity is unique in the world: another frame's different texture under the same
                # key (its own ground materials, its own texture indices) gets #n
                identity, n = src['identity'], 1
                while identity in texture_names and texture_names[identity] != digest:
                    n += 1
                    identity = '%s#%d' % (src['identity'], n)
                texture_names[identity] = digest
                texture_content[digest] = len(texture_records)
                named = engine.encode('ascii').ljust(16, b'\0') + mip[16:]
                texture_records.append((identity, named, *src['size']))
                homed['textures'].append(texture_content[digest])
            texture_ids[(fi, key)] = texture_content[digest]
        return texture_ids[(fi, key)]

    def model_id_of(fi, key):
        if (fi, key) not in model_ids:
            v = frames[fi]['variants'][key]
            image, render = resolved_image(v['lumps'], v['texture_keys'], lambda k: texture_id_of(fi, k))
            digest = hashlib.sha256(image).hexdigest()
            if digest not in model_content:
                # a name is unique in the world: another frame's different model of the same name gets #n
                name, n = v['name'], 1
                while name in model_names and model_names[name] != digest:
                    n += 1
                    name = '%s#%d' % (v['name'], n)
                model_names[name] = digest
                model_content[digest] = len(model_records)
                model_records.append((name, image, render))
                homed['models'].append(model_content[digest])
            else:
                aliases.append([v['name'], model_records[model_content[digest]][0]])
            model_ids[(fi, key)] = model_content[digest]
        return model_ids[(fi, key)]
    files, written, frame_recs, terrain_info = [], [], [], {}
    model_at, texture_at = {}, {}
    pid = 0
    vis_totals, reach_total, over_total, largest = {}, 0, 0, 0
    # Every frame's placement layout first (ids run on across frames in pack order), then the visibility rows of
    # all frames on the workers, then the pack in order (B5, v0.0.42; frame_visibility). Same files.
    # A frame's ids start after every placement of the frames before it (each placement is owned by exactly one
    # chunk), so each layout is made on its own, when the visibility rows first need it: the layouts overlap the
    # rows on the workers instead of running before them on one core (BUILD-CHIM-REGION-FRAMES-TAIL-43). Same ids.
    bases = []
    for fi in order:
        bases.append(pid)
        pid += len(frames[fi]['placements'])
    import build_profile      # timed phases: start/end lines with time and cores (never part of a key)
    with section('visibility rows'), build_profile.phase('CHIM world: visibility rows', '%d frames' % len(frames)):
        layouts, visible, refusals = frame_rows([frames[fi] for fi in order], bases, settings, jobs, cache)
    # Placement light levels (chim.placement_light, hybrid lighting part 2): the light the original's light sources
    # give each placement, in the placed record's flags (world format 0.12). Off, or a world without placed records:
    # nothing below changes.
    from chim import placement_light as PL
    light_mode, light_sources = PL.environment_sources()
    light_levels, light_note = {}, None
    if light_mode != 'off':
        if not placed:
            light_note = 'not stored: placement light levels need placed records (placement format 0.8)'
            print('CHIM world: placement light %s' % light_note, flush=True)
        else:
            with build_profile.phase('CHIM world: placement light levels', '%d frames' % len(frames)):
                for fi, layout in zip(order, layouts):
                    by_chunk = layout[1]
                    light_levels.update(PL.frame_levels(frames[fi]['frame'],
                                                        [p for c in by_chunk for p in by_chunk[c]['owned']],
                                                        light_sources))
            if light_levels:
                version = max(version, PL.FORMAT_VERSION)
            print('CHIM world: placement light: %d of %d placements lit by %d sources (world format %d.%d)'
                  % (len(light_levels), pid, len(light_sources), *version), flush=True)
    pack_timer = build_profile.phase('CHIM world: pack', '%d frames' % len(frames)).__enter__()
    # The pack itself stays one walk in this process: model, texture and terrain ids are handed out in the order
    # the walk first meets them and every sector holds the records first met there, so each frame depends on the
    # ids of every frame before it (inherently serial). The parts that do not depend on the ids (the packed
    # visibility rows, the terrain shift checks) were made on the workers with the rows (frame_rows).
    if len(frames) > 1:
        print('CHIM world: pack: one walk in pack order (ids are handed out as the walk first meets them: serial); '
              'visibility rows and terrain shift checks %s' % (
                  'came packed from the workers' if all(len(v) == 2 for v in visible) else 'packed here'), flush=True)
    for fi, layout, rows_of, refused in zip(order, layouts, visible, refusals):
        if len(rows_of) == 2:
            packed, vis_stats = rows_of
        else:
            pvs, pvl, vis_stats = rows_of
            packed = None
        spec = frames[fi]
        world, by_chunk, rows_in, base, owned_total = layout
        variants, terrain = spec['variants'], spec['terrain']
        for k, v in vis_stats.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                vis_totals[k] = vis_totals.get(k, 0) + v
            else:
                vis_totals.setdefault(k, v)
        with section('pack assembly'):
            cell = world.frame['cell']
            S = world.sector_chunks
            fdir = 'frames/%s/%s' % (frame_dir(cell), frame_subdir(cell))
            chunk_rows, sector_rows, sector_blobs = [], [], []
            first_row = len(files) + 1                     # the frame file's row; its sectors follow
            # format 0.9 (chim.reach): every chunk's references to its frame's owner records
            refs_of = RI.frame_refs(by_chunk, world.chunk_index) if reach_refs else None
            for si, sector in enumerate(world.sectors):
                homed['textures'], homed['models'], homed['terrain'] = [], [], []
                records, chunk_meta, ref_at = [], [], {}
                for c in world.order[si * S * S:(si + 1) * S * S]:
                    info = terrain[c]['info']
                    image, image_render = resolved_image(terrain[c]['lumps'], terrain[c]['texture_keys'],
                                                         lambda k: texture_id_of(fi, k))
                    referenced = 'offset' in terrain[c]
                    if referenced:
                        shift = terrain[c]['offset']
                        why = refused[c] if refused is not None else F.refuse_shift(image, shift)
                        if why:
                            raise ValueError('Chunk %s of frame %s: terrain cannot be referenced: %s' % (c, cell, why))
                        digest = hashlib.sha256(image).hexdigest()
                        if digest not in terrain_content:
                            terrain_content[digest] = len(terrain_records)
                            # format 0.11 record version 2: the converter's own triangles of this chunk,
                            # when the frame's ground is irregular (the regular path needs none)
                            made = TG.encode(image, TG.chunk_triangles(spec.get('visibility'), shift)) \
                                if terc_on and generate_on else None
                            compact = TC.encode(image) if terc_on and made is None else None
                            if made is not None:
                                # format 0.11: the generated record, read whole
                                thgt_count += 1
                                thgt_saved += len(image) - len(made)
                                terrain_records.append((made, len(made)))
                            elif compact is not None:
                                # format 0.10: the compact record, read whole (its block names it as render bytes)
                                terc_count += 1
                                terc_saved += len(image) - len(compact)
                                terrain_records.append((compact, len(compact)))
                            else:
                                terrain_records.append((image, image_render))
                            homed['terrain'].append(terrain_content[digest])
                        ref_at[c] = (terrain_content[digest], shift)
                    rows = {}
                    for kind in ('owned', 'reach'):
                        rows[kind] = [PL.with_light(
                                          write_record(p['_pid'], p['ref'], model_id_of(fi, p['variant']), p['origin'],
                                                       (p.get('angles') or (0.0, p['yaw'], 0.0)) if placed else p['yaw'],
                                                       world.chunk_index[p['_owner']], p['cell'][0] - cell[0],
                                                       p['cell'][1] - cell[1], p['_box'], p['_leaves'],
                                                       p.get('story_hidden', False)),
                                          light_levels.get(p['_pid'], 0))
                                      for p in sorted(by_chunk[c][kind], key=lambda q: q['_pid'])]
                    if reach_refs:
                        rows['reach'] = refs_of[c]      # format 0.9: references in place of the reach copies
                    if packed is not None:
                        pvs_row, pvl_row = packed[c]
                    else:
                        bits = [False] * len(world.order)
                        for b in pvs[c]:
                            bits[world.chunk_index[b]] = True
                        pbits = [False] * owned_total
                        for q in pvl[c]:
                            pbits[q - base] = True
                        pvs_row, pvl_row = compress_row(bits_to_row(bits)), compress_row(bits_to_row(pbits))
                    if referenced:
                        # the reference block is written with its record's place once the sector is laid out
                        tid, shift = ref_at[c]
                        data, render, collision = write_chunk_ref(
                            rows['owned'], rows['reach'], pvs_row,
                            F.terrain_ref(tid, 0, 0, 0, 0, shift), info.get('leaves', 0), pvl_row)
                    else:
                        data, render, collision = write_chunk(rows['owned'], rows['reach'], pvs_row, image,
                                                                 image_render, info.get('leaves', 0), pvl_row)
                    records.append((b'CHNK', world.chunk_index[c], data))
                    chunk_meta.append((c, render, collision, len(rows['owned']), len(rows['reach']),
                                       int(math.floor(info['zmin'])), int(math.ceil(info['zmax']))))
                    terrain_info['%d,%d/%d,%d' % (cell[0], cell[1], c[0], c[1])] = \
                        {k: v for k, v in info.items() if k != 'tree'}
                # Terrain, models and textures first needed in this sector live here, after its chunks.
                records += [(b'TERR', tid, terrain_records[tid][0]) for tid in homed['terrain']]
                records += [(b'MODL', mid, model_records[mid][1]) for mid in homed['models']]
                records += [(b'TEXR', tid, texture_records[tid][1]) for tid in homed['textures']]
                blob = F.sector_file(records, version)
                if len(blob) > F.FFS_MAX_PACK:
                    raise ValueError('Sector file exceeds the 1 GiB file limit')
                file_row = first_row + si
                offsets = {(r['kind'], r['id']): r['offset'] for r in F.read_sector(blob)}
                if refs:
                    for tid in homed['terrain']:
                        terrain_at[tid] = (file_row, offsets[(b'TERR', tid)])
                    # every reference names its record's file row and offset (fixed size: the layout stays)
                    for k, (kind, cid, data) in enumerate(records):
                        if kind != b'CHNK':
                            continue
                        if world.order[cid] not in ref_at:
                            continue
                        tid, shift = ref_at[world.order[cid]]
                        at = len(data) - F.TERRAIN_REF.size
                        image, image_render = terrain_records[tid]
                        records[k] = (kind, cid, data[:at] + F.terrain_ref(
                            tid, terrain_at[tid][0], terrain_at[tid][1], len(image), image_render, shift))
                    blob = F.sector_file(records, version)
                for c, render, collision, owned, reach, zmin, zmax in chunk_meta:
                    chunk_rows.append((c[0], c[1], si, offsets[(b'CHNK', world.chunk_index[c])], render, collision,
                                       owned, reach, zmin, zmax))
                for mid in homed['models']:
                    model_at[mid] = (file_row, offsets[(b'MODL', mid)])
                for tid in homed['textures']:
                    texture_at[tid] = (file_row, offsets[(b'TEXR', tid)])
                sector_rows.append((sector[0], sector[1], len(blob), F.crc32(blob)))
                sector_blobs.append(('%s/%s' % (fdir, sector_path(si, len(world.sectors))), blob, len(records)))
            frame_rec = {'cell': cell, 'centre': world.frame['centre'], 'low': world.frame['low'],
                         'grain': world.settings['grain'], 'nx': world.nx, 'ny': world.ny, 'sector_chunks': S,
                         'owned_total': owned_total}
            frame_blob = F.frame_file(frame_rec, chunk_rows, sector_rows, version)
            written += [(fdir + '/frame.ccf', frame_blob)] + [(path, blob) for path, blob, _ in sector_blobs]
            files.append({'kind': b'FRAM', 'sector': 0, 'cell': cell, 'bytes': len(frame_blob),
                          'crc': F.crc32(frame_blob), 'entries': len(chunk_rows), 'path': fdir + '/frame.ccf'})
            files += [{'kind': b'SECT', 'sector': si, 'cell': cell, 'bytes': len(blob), 'crc': F.crc32(blob),
                       'entries': n, 'path': path} for si, (path, blob, n) in enumerate(sector_blobs)]
            frame_recs.append({'frame': frame_rec, 'sectors': len(sector_rows), 'placements': owned_total,
                               'chunks': len(chunk_rows)})
            reach_total += sum(len(v['reach']) for v in by_chunk.values())
            over_total += sum(1 for p in rows_in if p['_leaves'] > F.MAX_ENT_LEAFS)
            largest = max([largest] + [r[2] for r in sector_rows])
        if len(frames) > 1:
            # one line per frame: the visibility rows and the pack of a world of hundreds of frames are minutes
            # of work (fixlist B2: dev5 printed nothing here)
            progress_line.emit('CHIM world frames', fdir, '%d placements, %d chunks, %d sectors'
                               % (owned_total, len(chunk_rows), len(sector_rows)),
                               (len(frame_recs), len(frames), 'frames'))
    pack_timer.__exit__(None, None, None)
    with section('pack assembly'):
        if len(model_records) > 65535 or len(texture_records) > 65535:
            raise ValueError('Model or texture count beyond format 0.2 ids')
        models_dir = [(name, model_at[mid][0], model_at[mid][1], len(image), render)
                      for mid, (name, image, render) in enumerate(model_records)]
        textures_dir = [(name, texture_at[tid][0], texture_at[tid][1], len(mip), w, h)
                        for tid, (name, mip, w, h) in enumerate(texture_records)]
        first = World(frames[order[0]]['frame'], settings)
        idx_settings = dict(first.settings, terrain_light=terrain_light, placements=pid, models=len(model_records),
                            textures=len(texture_records), frames=len(frames), sector_chunks=first.sector_chunks)
        index = F.index_file(idx_settings, files, models_dir, textures_dir, version)
    with section('pack write'):
        # Written whole, one after another, in the order they are read: the index, then
        # per frame its frame file and its sector files in pack order (docs/chim/WORLD_FORMAT.md).
        changed = [rel for rel, blob in [('world.cwi', index)] + written if write_if_changed(root / rel, blob)]
        removed = remove_stale(root, {rel for rel, _ in [('world.cwi', index)] + written})

    def plain(rec):
        return {k: list(v) if isinstance(v, tuple) else v for k, v in rec.items()}
    receipt = {'builder': BUILDER, 'chim_version': CHIM_VERSION, 'world_format': '%d.%d' % version,
               'settings': idx_settings,
               'frame': plain(frame_recs[0]['frame']),
               'frames': [dict(r, frame=plain(r['frame'])) for r in frame_recs],
               'files': [{'path': 'chim/' + f['path'], 'kind': f['kind'].decode(), 'bytes': f['bytes'],
                          'crc32': '%08x' % f['crc'], 'entries': f['entries']} for f in files]
               + [{'path': 'chim/world.cwi', 'kind': 'INDX', 'bytes': len(index), 'crc32': '%08x' % F.crc32(index),
                   'entries': len(files)}],
               'files_rewritten': ['chim/' + rel for rel in changed],
               'files_removed': ['chim/' + rel for rel in removed],
               'sectors': sum(r['sectors'] for r in frame_recs), 'largest_sector_bytes': largest,
               'placements': pid, 'reach_copies': reach_total,
               # off: no key, the receipt as before
               **({'placement_light': dict(PL.summary(light_levels, pid, light_sources, light_mode),
                                           **({'note': light_note} if light_note else {}))}
                  if light_mode != 'off' else {}),
               **({'reach_index': {'references': reach_total, 'reference_bytes': RI.reach_bytes(reach_total)[1],
                                   'copy_bytes': RI.reach_bytes(reach_total)[0]}} if reach_refs else {}),
               'models': len(model_records), 'model_variants': len(model_ids), 'model_aliases': aliases,
               'textures': len(texture_records), 'texture_keys': len(texture_ids),
               'chunks': sum(r['chunks'] for r in frame_recs),
               **({'terrain_pack': {'compact_records': terc_count, 'bytes_saved': terc_saved,
                                    **({'generated_records': thgt_count, 'generated_bytes_saved': thgt_saved}
                                       if generate_on else {})}} if terc_on else {}),
               **({'terrain_refs': {'records': len(terrain_records),
                                    'record_bytes': sum(len(i) for i, _ in terrain_records)}} if refs else {}),
               'visibility': vis_totals,
               'placements_over_16_leaves': over_total,
               'terrain': {'tiles': sum(i['tiles'] for i in terrain_info.values()),
                           'faces': sum(i['faces'] for i in terrain_info.values()),
                           'water_faces': sum(i['water_faces'] for i in terrain_info.values()),
                           # compiled standing hulls that failed the exactness check and kept the routed hull
                           # (CHIM-COMPILED-HULL-SHORT-36): frame cell / chunk and the measured shortfall
                           'compiled_hull_fallbacks': sorted(
                               '%s %s' % (k, i['hull_check']['short']) for k, i in terrain_info.items()
                               if (i.get('hull_check') or {}).get('fallback')),
                           # compiled standing hulls the check patched with lost pieces (kept compiled)
                           'compiled_hull_patched': sorted(
                               '%s +%d nodes' % (k, i['hull_check'].get('patched_nodes', 0))
                               for k, i in terrain_info.items()
                               if (i.get('hull_check') or {}).get('patched_rounds'))}}
    return receipt


def write_json(path, value, split=(), jobs=1):
    """VALUE as indented JSON (sorted keys) at PATH. SPLIT: paths of large lists encoded on the worker pool
    (tools/parallel_json.py: the same bytes; BUILD-CHIM-SERIAL-SECTIONS-44)."""
    if split:
        import parallel_json
        text = parallel_json.dumps(value, split, jobs=jobs)
    else:
        text = json.dumps(value, indent=1, sort_keys=True)
    Path(path).write_text(text + '\n', encoding='utf-8', newline='\n')
