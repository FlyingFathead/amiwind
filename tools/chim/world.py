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
import struct
from pathlib import Path

from chim import BUILDER, CHIM_VERSION, FORMAT_VERSION
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
    """Drawn box of a placement, as the engine computes it (aw_scenery.c AW_SceneryCapture)."""
    from world_chunk_estimate import placed_box as box
    return box(origin, (0.0, yaw, 0.0), lo, hi)


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
            for pts in v['occluders']:
                q = yaw_points(pts, p['origin'], p['yaw'])
                try:
                    occ.add(ConvexHull(q).equations, q)
                except Exception:  # noqa: BLE001 - a flat or degenerate piece occludes nothing
                    continue
            if v.get('occluder_grid') and visibility.get('mesh_occluders', True):
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
    pwhole = fingerprint('pvs', whole, sorted(boxes.items()))
    pitems = []
    for src in sources:
        cand = {c: candidates[c] for c in src}
        nr = {c: near[c] for c in src}
        used = sorted({p for c in src for p in candidates[c]})
        task = {'args': pargs, 'viewers': src, 'candidates': cand, 'near': nr, 'boxes': {p: boxes[p] for p in used}}
        pitems.append((fingerprint('pvs', 'placements', pwhole, src, [cand[c] for c in src], [nr[c] for c in src]),
                       task))
    pvl = {}
    pstats = {'placements_tested': 0, 'placements_blocked': 0}
    for res in run_units('pvs', pitems, pvl_unit, jobs, cache):
        for key, pids in res['visible'].items():
            pvl[tuple(int(v) for v in key.split(','))] = set(pids)
        for k in pstats:
            pstats[k] += res['stats'][k]
    stats.update(pstats)
    return {c: seen[c] & ring[c] for c in world.order}, pvl, stats


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
    """A frame's ground box in Morrowind units (x0, y0, x1, y1): centre + 4 x the frame-local box."""
    c, (lx, ly), (sx, sy) = frame['centre'], frame['low'], frame['span']
    return (c[0] + 4 * lx, c[1] + 4 * ly, c[0] + 4 * (lx + sx), c[1] + 4 * (ly + sy))


def frame_order(frames):
    """Frames in pack order: Hilbert order of their cells (ties by cell)."""
    cells = [tuple(f['frame']['cell']) for f in frames]
    if len(set(cells)) != len(cells):
        raise ValueError('Two frames share the cell %s' % (sorted(c for c in cells if cells.count(c) > 1)[0],))
    boxes = [frame_box(f['frame']) for f in frames]
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[j]
            if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                raise ValueError('Frames %s and %s overlap: a placement or tile would be stored twice'
                                 % (cells[i], cells[j]))
    lo = (min(c[0] for c in cells), min(c[1] for c in cells))
    side = 1
    while side < max(max(c[0] - lo[0], c[1] - lo[1]) + 1 for c in cells):
        side *= 2
    return sorted(range(len(frames)), key=lambda k: (F.hilbert_index(side, cells[k][0] - lo[0], cells[k][1] - lo[1]),
                                                     cells[k]))


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
    root = Path(out) / 'chim'
    texture_ids, texture_content, texture_records, texture_names = {}, {}, [], {}
    model_ids, model_content, model_records, aliases, model_names = {}, {}, [], [], {}
    homed = {'textures': [], 'models': []}      # ids first met in the sector being assembled

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
    for fi in order:
        spec = frames[fi]
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
            box = stored_box(*placed_box(p['origin'], p['yaw'], [f32(x) for x in v['lo']], [f32(x) for x in v['hi']]))
            owner = world.chunk_of(p['origin'][0], p['origin'][1])
            p = dict(p, _owner=owner, _box=box, _touched=world.touched(*box) | {owner})
            by_chunk[owner]['owned'].append(p)
            rows_in.append(p)
        base = pid
        for c in world.order:
            for p in sorted(by_chunk[c]['owned'], key=lambda q: q['ref']):
                p['_pid'] = pid
                pid += 1
                for t in sorted(p['_touched'] - {c}):
                    by_chunk[t]['reach'].append(p)
        owned_total = pid - base
        for p in rows_in:
            lo, hi = p['_box']
            p['_leaves'] = sum(len(terrain[c]['info']['tree'].leaves_touched(lo, hi)) for c in p['_touched'])
        with section('visibility rows'):
            pvs, pvl, vis_stats = chunk_visibility(world, terrain, by_chunk, variants, spec.get('visibility'),
                                                   jobs, cache)
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
            for si, sector in enumerate(world.sectors):
                homed['textures'], homed['models'] = [], []
                records, chunk_meta = [], []
                for c in world.order[si * S * S:(si + 1) * S * S]:
                    info = terrain[c]['info']
                    image, image_render = resolved_image(terrain[c]['lumps'], terrain[c]['texture_keys'],
                                                         lambda k: texture_id_of(fi, k))
                    rows = {}
                    for kind in ('owned', 'reach'):
                        rows[kind] = [F.placement(p['_pid'], p['ref'], model_id_of(fi, p['variant']), p['origin'],
                                                  p['yaw'], world.chunk_index[p['_owner']], p['cell'][0] - cell[0],
                                                  p['cell'][1] - cell[1], p['_box'], p['_leaves'],
                                                  p.get('story_hidden', False))
                                      for p in sorted(by_chunk[c][kind], key=lambda q: q['_pid'])]
                    bits = [False] * len(world.order)
                    for b in pvs[c]:
                        bits[world.chunk_index[b]] = True
                    pbits = [False] * owned_total
                    for q in pvl[c]:
                        pbits[q - base] = True
                    data, render, collision = F.chunk_record(rows['owned'], rows['reach'],
                                                             compress_row(bits_to_row(bits)), image, image_render,
                                                             info.get('leaves', 0), compress_row(bits_to_row(pbits)))
                    records.append((b'CHNK', world.chunk_index[c], data))
                    chunk_meta.append((c, render, collision, len(rows['owned']), len(rows['reach']),
                                       int(math.floor(info['zmin'])), int(math.ceil(info['zmax']))))
                    terrain_info['%d,%d/%d,%d' % (cell[0], cell[1], c[0], c[1])] = \
                        {k: v for k, v in info.items() if k != 'tree'}
                # Models and textures first needed in this sector live here, after its chunks.
                records += [(b'MODL', mid, model_records[mid][1]) for mid in homed['models']]
                records += [(b'TEXR', tid, texture_records[tid][1]) for tid in homed['textures']]
                blob = F.sector_file(records)
                if len(blob) > F.FFS_MAX_PACK:
                    raise ValueError('Sector file exceeds the 1 GiB file limit')
                file_row = first_row + si
                offsets = {(r['kind'], r['id']): r['offset'] for r in F.read_sector(blob)}
                for c, render, collision, owned, reach, zmin, zmax in chunk_meta:
                    chunk_rows.append((c[0], c[1], si, offsets[(b'CHNK', world.chunk_index[c])], render, collision,
                                       owned, reach, zmin, zmax))
                for mid in homed['models']:
                    model_at[mid] = (file_row, offsets[(b'MODL', mid)])
                for tid in homed['textures']:
                    texture_at[tid] = (file_row, offsets[(b'TEXR', tid)])
                sector_rows.append((sector[0], sector[1], len(blob), F.crc32(blob)))
                sector_blobs.append(('%s/%s' % (fdir, F.sector_name(si)), blob, len(records)))
            frame_rec = {'cell': cell, 'centre': world.frame['centre'], 'low': world.frame['low'],
                         'grain': world.settings['grain'], 'nx': world.nx, 'ny': world.ny, 'sector_chunks': S,
                         'owned_total': owned_total}
            frame_blob = F.frame_file(frame_rec, chunk_rows, sector_rows)
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
        index = F.index_file(idx_settings, files, models_dir, textures_dir)
    with section('pack write'):
        # Written whole, one after another, in the order they are read: the index, then
        # per frame its frame file and its sector files in pack order (docs/chim/WORLD_FORMAT.md).
        changed = [rel for rel, blob in [('world.cwi', index)] + written if write_if_changed(root / rel, blob)]
        removed = remove_stale(root, {rel for rel, _ in [('world.cwi', index)] + written})

    def plain(rec):
        return {k: list(v) if isinstance(v, tuple) else v for k, v in rec.items()}
    receipt = {'builder': BUILDER, 'chim_version': CHIM_VERSION, 'world_format': '%d.%d' % FORMAT_VERSION,
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
               'models': len(model_records), 'model_variants': len(model_ids), 'model_aliases': aliases,
               'textures': len(texture_records), 'texture_keys': len(texture_ids),
               'chunks': sum(r['chunks'] for r in frame_recs),
               'visibility': vis_totals,
               'placements_over_16_leaves': over_total,
               'terrain': {'tiles': sum(i['tiles'] for i in terrain_info.values()),
                           'faces': sum(i['faces'] for i in terrain_info.values()),
                           'water_faces': sum(i['water_faces'] for i in terrain_info.values())}}
    return receipt


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
