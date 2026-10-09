#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Asset census for the world streamer: every asset stored once, placed by reference.

Reads your own Morrowind files (and, optionally, maps converted by this
repository) and measures what a streamer that stores each mesh, hull and
texture once would hold. Nothing derived from your files is part of this
repository; see docs/ASSET_CENSUS.md.

Subcommands:
  census   --data-files DIR --out DIR [--jobs N] [--work DIR] [--grains 256 512 1024]
           [--draw-distance 540] [--hysteresis 96] [--route-cell NAME ...]
      Unique meshes and textures placed (exterior / interior) with their sizes
      in AmiWind form (converter functions: faces after split_surface, unique
      vertexes and edges, texture mappings, planes, lightmap samples, hull
      nodes and clipnodes; textures as 8-bit miptex at the converter's sizes);
      scale and tilt histograms per mesh class; variant counts under scale and
      tilt policies; per-chunk ring bytes for each grain; a simulated walk
      through the load doors of each named exterior town (unique-mesh cache);
      the quantized heightfield size for every LAND cell.
  bakes    --data-files DIR --maps DIR --out FILE [--census FILE]
      Lightmap bytes per placement measured in converted interior maps
      (aw_ref of each func_wall), per piece class, before and after the
      lightmap sharing in the stored lump; exterior maps: lit faces of
      appended objects.
  terrain  --maps DIR --out FILE [--listing FILE]
      Terrain (world model) bytes of converted open-world maps, per map and
      extrapolated to every map in a size listing.
  disk     --census FILE [--bakes FILE] [--terrain FILE] [--extra FILE] --out FILE
      Total disk for the streamer by kind, partitions and drive images.

Measured vs estimated: counts read from your files and maps are measured;
geometry of scaled variants (unit-scale counts reused), lightmaps at other
scales and every disk total are estimated, and labelled so in the output.
"""
import argparse
import bisect
import collections
import hashlib
import json
import math
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))
import world_estimate_data as D  # noqa: E402

FORMAT = 'aw-asset-census-1'
CENSUS_VERSION = 1           # bump when mesh_census changes; invalidates the cache
SCALE = D.SCALE              # Morrowind units -> Quake units
CELL_Q = D.CELL * SCALE      # 2048 Quake units per exterior cell
DISK = {'faces': 20, 'texinfo': 40, 'planes': 20, 'vertexes': 12, 'edges': 4, 'surfedges': 4,
        'nodes': 24, 'clipnodes': 8, 'models': 64}
PLACEMENT_RECORD = 24        # bytes per placement record (model index, origin, angles, scale, flags)
CLASSES = ('rocks', 'flora', 'buildings', 'furniture', 'clutter')
STRUCTURAL = ('rocks', 'buildings', 'furniture')   # lighting tier 2 candidates; flora/clutter tier 3
SCALE_EDGES = (0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.01, 1.05, 1.1, 1.2, 1.3, 1.5, 1.75, 2.0)
TILT_EDGES = (0.0, 1.0, 2.0, 5.0, 10.0, 20.0, 45.0, 90.0)
OCTAVE_STEPS = (4, 8, 16)
TILT_STEP_DEG = 5.0          # 'quant' tilt policy: pitch/roll step
TILT_YAW_STEP_DEG = 15.0     # 'quant' tilt policy: yaw step of tilted placements
TILT_POLICIES = ('exact', 'quant', 'runtime')
MESH_LEVELS = (4, 8, 16)
GIB = 1 << 30


# ---------------------------------------------------------------- classes and angles

def mesh_class(model, otype=''):
    """rocks / flora / buildings (architecture kits) / furniture / clutter, by mesh name."""
    stem = model.replace('\\', '/').rsplit('/', 1)[-1].casefold()
    stem = re.sub(r'^bm_?', '', stem)
    if 'rock' in stem or 'boulder' in stem:
        return 'rocks'
    if 'flora' in stem or stem.startswith(('tree', 'kelp', 'plant')):
        return 'flora'
    if stem.startswith(('ex_', 'in_')):
        return 'buildings'
    if stem.startswith(('furn_', 'contain_')) or otype in ('CONT', 'DOOR'):
        return 'furniture'
    return 'clutter'


def tilt_degrees(r):
    """Angle between the placement's up axis and world up (Morrowind XYZ Euler, radians)."""
    return math.degrees(math.acos(max(-1.0, min(1.0, math.cos(r[0]) * math.cos(r[1])))))


def quantize_octave(s, steps):
    """Nearest of `steps` log-spaced levels per octave; 1.0 is always a level."""
    return 2.0 ** (round(math.log2(s) * steps) / steps)


def mesh_levels(scales, n):
    """n log-spaced levels over one mesh's own scale range."""
    lo, hi = min(scales), max(scales)
    if hi <= lo * (1 + 1e-6) or n < 2:
        return [lo]
    return [lo * (hi / lo) ** (k / (n - 1)) for k in range(n)]


def nearest_level(s, levels):
    i = bisect.bisect_left(levels, s)
    best = [levels[j] for j in (i - 1, i) if 0 <= j < len(levels)]
    return min(best, key=lambda v: abs(math.log(v / s)))


def histogram(values, edges):
    """Counts for (-inf, e0), [e0, e1), ..., [e_last, inf)."""
    counts = [0] * (len(edges) + 1)
    for v in values:
        counts[bisect.bisect_right(edges, v)] += 1
    return counts


def scale_histogram(scales):
    """Exact 1.0 separately; otherwise binned by SCALE_EDGES."""
    exact = sum(1 for s in scales if abs(s - 1.0) <= 1e-6)
    rest = [s for s in scales if abs(s - 1.0) > 1e-6]
    return {'exact_1': exact, 'edges': list(SCALE_EDGES), 'bins': histogram(rest, SCALE_EDGES),
            'distinct_values': len({round(s, 6) for s in scales})}


# ---------------------------------------------------------------- per-mesh census (converter functions)

def texture_key(material, size):
    """The converter's texture identity (prepare_mesh_bsp texture(): source, size, tint, glow)."""
    src = D.normpath(material.get('texture_source') or '')
    if src and not src.startswith('textures/'):
        src = 'textures/' + src
    src = re.sub(r'\.(dds|tga|bmp)$', '', src)
    tint = tuple(round(float(x), 2) for x in material.get('diffuse', (1.0, 1.0, 1.0)))
    return '%s|%d|%s|%d' % (src, size, ','.join('%g' % x for x in tint), int(material.get('emissive', 0) or 0))


def miptex_bytes(size_w, size_h=None):
    """Quake miptex: 40-byte header plus four mip levels of 8-bit pixels."""
    h = size_w if size_h is None else size_h
    return 40 + size_w * h * 85 // 64


def mesh_census(vertices, faces, collision, profile, materials):
    """BSP model cost of one mesh under one converter profile (unit scale, no tilt).

    Mirrors prepare_mesh_bsp (_prepare_model, the vertex/edge/plane caches of
    append_meshes and collider): faces after split_surface, unique vertexes
    (rounded to 1e-5) and edges, surfedges, texture mappings, planes, lightmap
    samples (and their scale terms), point-hull nodes, standing-box clipnodes
    and collision planes, and the textures the emitted faces use."""
    import numpy as np
    from mesh_geometry import surface_polygons, split_surface, collision_pieces
    from prepare_mesh_bsp import standing_planes
    v, f = vertices, faces
    visual_v, visual_f = v, f
    ratio = profile.get('ratio')
    if ratio and ratio < 1:
        from static_lod import reduce_mesh
        visual_v, visual_f, _ = reduce_mesh(v, f, ratio)
    texsize = int(profile.get('texture_size', 64))
    out = {'faces': 0, 'vertexes': 0, 'edges': 0, 'surfedges': 0, 'texinfo': 0, 'planes': 0,
           'luxels': 0, 'lux_s1': 0.0, 'lux_s2': 0.0, 'nodes': 0, 'clipnodes': 0, 'cplanes': 0,
           'texture_size': texsize, 'textures': []}
    used = set()
    if not profile.get('collision_only'):
        verts, edges, planes, mappings = {}, set(), set(), set()

        def vid(p):
            return verts.setdefault(tuple(np.round(p, 5)), len(verts))
        for poly, material, axes, offset, normal in surface_polygons(visual_v, visual_f):
            ax = np.column_stack((axes.T * texsize, offset * texsize))
            mappings.add((int(material), *np.round(ax.flatten(), 4)))
            for patch in split_surface(poly, ax):
                out['faces'] += 1
                used.add(int(material))
                ids = [vid(p) for p in patch]
                out['surfedges'] += len(ids)
                for k in range(len(ids)):
                    a, b = ids[k], ids[(k + 1) % len(ids)]
                    edges.add((min(a, b), max(a, b)))
                planes.add(tuple(np.round([*normal, float(np.dot(normal, patch[0]))], 5)))
                uv = patch @ ax[:, :3].T + ax[:, 3]
                es = math.ceil(uv[:, 0].max() / 16) * 16 - math.floor(uv[:, 0].min() / 16) * 16
                et = math.ceil(uv[:, 1].max() / 16) * 16 - math.floor(uv[:, 1].min() / 16) * 16
                out['luxels'] += int((es // 16 + 1) * (et // 16 + 1))
                a_ = float(uv[:, 0].max() - uv[:, 0].min()) / 16
                b_ = float(uv[:, 1].max() - uv[:, 1].min()) / 16
                out['lux_s1'] += a_ + b_
                out['lux_s2'] += a_ * b_
        out['vertexes'], out['edges'], out['planes'], out['texinfo'] = len(verts), len(edges), len(planes), len(mappings)
    out['textures'] = sorted({texture_key(materials[m], texsize) for m in used if m < len(materials)})
    if not profile.get('collision_none'):
        cv, cf = collision if (collision is not None and profile.get('collision_source')) else (v, f)
        pieces, exact, _ = collision_pieces(cv, cf, profile)
        cpl = set()
        for k, (points, hull, ids, error) in enumerate(pieces):
            point_eq = np.unique(np.round(hull.equations, 5), axis=0)
            out['nodes'] += len(point_eq)
            standing = standing_planes(points, point_eq, exact is True or (bool(exact) and k in exact))
            out['clipnodes'] += len(standing)
            cpl.update(tuple(np.round(e, 5)) for e in point_eq)
            cpl.update(tuple(np.round(e, 5)) for e in standing)
        out['cplanes'] = len(cpl)
    out['lux_s1'] = round(out['lux_s1'], 3)
    out['lux_s2'] = round(out['lux_s2'], 3)
    return out


def geometry_bytes(c):
    """Disk bytes of one brush model's render part (BSP29 lumps; lightmaps separate)."""
    return (c['faces'] * DISK['faces'] + c['surfedges'] * DISK['surfedges'] + c['edges'] * DISK['edges']
            + c['vertexes'] * DISK['vertexes'] + c['texinfo'] * DISK['texinfo'] + c['planes'] * DISK['planes']
            + DISK['models'])


def hull_bytes(c):
    """Disk bytes of one model's collision part: clipnodes (hulls 1-3 share them), point nodes, planes."""
    return c['clipnodes'] * DISK['clipnodes'] + c['nodes'] * DISK['nodes'] + c['cplanes'] * DISK['planes']


def luxels_at(c, s):
    """Lightmap samples of a placement at scale s (exact at s=1; estimated elsewhere)."""
    return max(c['faces'], c['luxels'] + c['lux_s1'] * (s - 1) + c['lux_s2'] * (s * s - 1))


_SOURCE = {}


def _census_worker(task):
    data_files, name = task
    if data_files not in _SOURCE:
        _SOURCE.clear()
        _SOURCE[data_files] = D.MeshSource(data_files)
    return scan_mesh(_SOURCE[data_files], name)


def scan_mesh(source, name):
    """Census row of one mesh; never raises (status 'missing' / 'nogeom')."""
    import numpy as np
    from prepare_scenery import nif_reader, model_geometry
    from mwad.scene import unpack_geometry
    out = {'model': name, 'census_version': CENSUS_VERSION}
    try:
        raw, src = source.read(name)
    except (OSError, ValueError, KeyError) as exc:
        out.update(status='missing', error=str(exc)[:200])
        return out
    out.update(source=src, sha256=hashlib.sha256(raw).hexdigest())
    N = nif_reader()
    try:
        geometry, materials, bounds, _ = model_geometry(raw, N, repair_uv=True)
        vv, ff, _ = unpack_geometry(geometry)
        v = np.array(vv, dtype=float)
        f = np.array(ff, dtype=int)
        out.update(status='ok', tris=int(len(f)), bounds=bounds)
    except Exception as exc:  # noqa: BLE001 - any reader failure is a per-mesh status
        out.update(status='nogeom', error=('%s: %s' % (type(exc).__name__, exc))[:200])
        return out
    collision = None
    try:
        cg, _, _, _ = model_geometry(raw, N, collision=True)
        cvv, cff, _ = unpack_geometry(cg)
        collision = (np.array(cvv, dtype=float), np.array(cff, dtype=int))
    except Exception:  # noqa: BLE001 - no collision node: converters fall back to the visual mesh
        pass
    out['spaces'] = {}
    for space, profile in (('interior', D.interior_profile(name, out['tris'])),
                           ('exterior', D.exterior_profile(name, out['tris']))):
        try:
            out['spaces'][space] = mesh_census(v, f, collision, profile, materials)
        except Exception as exc:  # noqa: BLE001
            out['spaces'][space] = {'error': ('%s: %s' % (type(exc).__name__, exc))[:200]}
    return out


def scan_meshes(data_files, names, cache_path=None, jobs=1, progress=None):
    from build_parallel import ordered_map
    cache = {}
    if cache_path is not None and Path(cache_path).is_file():
        cache = json.loads(Path(cache_path).read_text(encoding='utf-8'))
    source = D.MeshSource(data_files)
    rows, todo = {}, []
    for name in names:
        row = cache.get(name)
        if row and row.get('census_version') == CENSUS_VERSION and row.get('status') != 'missing':
            try:
                raw, _ = source.read(name)
            except (OSError, ValueError, KeyError):
                raw = None
            if raw is not None and hashlib.sha256(raw).hexdigest() == row.get('sha256'):
                rows[name] = row
                continue
        todo.append(name)
    for i, row in enumerate(ordered_map(_census_worker, [(str(data_files), n) for n in todo], jobs)):
        rows[row['model']] = row
        if progress and (i % 250 == 0 or i == len(todo) - 1):
            progress('mesh census %d/%d' % (i + 1, len(todo)))
    if cache_path is not None:
        Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
        Path(cache_path).write_text(json.dumps(rows, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    return rows


# ---------------------------------------------------------------- placements

def collect_placements(masters, meshes, excluded=frozenset()):
    """Every placed object with a mesh ('evr' policy of the world estimate), per set.

    Expansions contribute only cells that Morrowind.esm does not have (as in the
    world estimate). Returns {set: [placement dict]}."""
    base_int = {c['name'].casefold() for c in masters['Morrowind.esm']['cells'] if c['interior']}
    base_ext = {(c['x'], c['y']) for c in masters['Morrowind.esm']['cells'] if not c['interior']}
    out = {}
    for master in D.MASTERS:
        if master not in masters:
            continue
        label = D.SET_OF_MASTER[master]
        world = D.World(masters, master, meshes)
        rows = []
        for c in world.cells:
            if c['deleted']:
                continue
            if c['interior'] and c['name'].casefold() in excluded:
                continue
            if master != 'Morrowind.esm' and (c['name'].casefold() in base_int if c['interior']
                                              else (c['x'], c['y']) in base_ext):
                continue
            space = 'interior' if c['interior'] else 'exterior'
            for ref in c['refs']:
                info = D.ref_info(world, ref, space)
                if info is None:
                    continue
                o, mesh, cur, evr = info
                if evr is not None:
                    continue
                rows.append({'space': space, 'model': o['model'], 'type': o['type'], 'n': ref['n'],
                             's': float(ref['s']), 'r': list(ref.get('r', [0.0, 0.0, 0.0])), 'p': list(ref['p']),
                             'cls': mesh_class(o['model'], o['type']), 'cur': cur is None,
                             'cell': c['name'] if c['interior'] else (c['x'], c['y']),
                             'door': bool(o['type'] == 'DOOR' and ref.get('dest'))})
        out[label] = rows
    return out


def variant_key(p, scale_policy, tilt_policy, levels=None):
    """Converter variant identity (prepare_mesh_bsp._instance_key without lighting) under a policy.

    scale_policy: 'exact', ('octave', n), ('mesh', n) with levels {model: [levels]}, 'runtime'.
    tilt_policy: 'exact' (r0, r1 always, yaw too when tilted), 'quant' (tilted placements
    with pitch/roll in TILT_STEP_DEG and yaw in TILT_YAW_STEP_DEG steps) or 'runtime'."""
    s = p['s']
    if scale_policy == 'exact':
        sk = round(s, 6)
    elif scale_policy == 'runtime':
        sk = None
    elif scale_policy[0] == 'octave':
        sk = round(quantize_octave(s, scale_policy[1]), 6)
    else:
        sk = round(nearest_level(s, levels[p['model']]), 6)
    r = p['r']
    if tilt_policy == 'runtime':
        tk = None
    elif tilt_policy == 'quant' and D.tilted(r):
        q, qy = math.radians(TILT_STEP_DEG), math.radians(TILT_YAW_STEP_DEG)
        tk = tuple(int(round(a / st)) for a, st in ((r[0], q), (r[1], q), (r[2] % (2 * math.pi), qy)))
    else:
        tk = (round(r[0], 6), round(r[1], 6), round(r[2], 6) if D.tilted(r) else None)
    return (p['model'], sk, tk)


def scale_policies():
    return (['exact'] + [('octave', n) for n in OCTAVE_STEPS] + [('mesh', n) for n in MESH_LEVELS]
            + ['runtime'])


def policy_name(sp):
    return sp if isinstance(sp, str) else '%s%d' % sp


def variant_table(rows):
    """Variant counts and dedup factors for every scale x tilt policy, plus the scale error."""
    by_mesh = collections.defaultdict(list)
    for p in rows:
        by_mesh[p['model']].append(p['s'])
    levels = {n: {m: mesh_levels(sorted(v), n) for m, v in by_mesh.items()} for n in MESH_LEVELS}
    today = len({variant_key(p, 'exact', 'exact') for p in rows})
    table = []
    for sp in scale_policies():
        lv = levels[sp[1]] if isinstance(sp, tuple) and sp[0] == 'mesh' else None
        errs = []
        if isinstance(sp, tuple):
            for p in rows:
                q = quantize_octave(p['s'], sp[1]) if sp[0] == 'octave' else nearest_level(p['s'], lv[p['model']])
                errs.append(abs(q / p['s'] - 1))
        row = {'scale': policy_name(sp)}
        for tp in TILT_POLICIES:
            n = len({variant_key(p, sp, tp, lv) for p in rows})
            row['variants_tilt_' + tp] = n
            row['dedup_tilt_' + tp] = round(today / n, 3) if n else None
        if errs:
            errs.sort()
            row['scale_error_p95'] = round(errs[int(0.95 * (len(errs) - 1))], 4)
            row['scale_error_max'] = round(errs[-1], 4)
        table.append(row)
    return {'meshes': len(by_mesh), 'placements': len(rows), 'variants_today': today, 'policies': table}


# ---------------------------------------------------------------- chunk rings (bitsets)

def ring_offsets(grain, radius):
    """Chunk offsets whose square comes within `radius` of the owned chunk's square."""
    k = int(math.floor(radius / grain)) + 1
    out = []
    for dx in range(-k, k + 1):
        for dy in range(-k, k + 1):
            gx, gy = max(abs(dx) - 1, 0) * grain, max(abs(dy) - 1, 0) * grain
            if math.hypot(gx, gy) <= radius:
                out.append((dx, dy))
    return out


class ChunkGrid:
    """Per-chunk item bitsets: a placement marks every chunk its bounds touch (bounds rule)."""

    def __init__(self, boxes, items, nitems, grain, radius, extra_cells=(), pad=0):
        import numpy as np
        self.grain, self.radius, self.nitems = grain, radius, nitems
        self.offsets = ring_offsets(grain, radius)
        self.pad = max(pad, max(max(abs(dx), abs(dy)) for dx, dy in self.offsets) + 1)
        lo = np.floor(np.asarray(boxes, float)[:, :2] / grain).astype(int) if len(boxes) else np.zeros((0, 2), int)
        hi = np.floor(np.asarray(boxes, float)[:, 2:] / grain).astype(int) if len(boxes) else np.zeros((0, 2), int)
        cells = [(int(cx * CELL_Q // grain), int(cy * CELL_Q // grain)) for cx, cy in extra_cells]
        per = max(1, int(CELL_Q // grain))
        xs = [*lo[:, 0], *hi[:, 0], *[c[0] for c in cells], *[c[0] + per - 1 for c in cells]]
        ys = [*lo[:, 1], *hi[:, 1], *[c[1] for c in cells], *[c[1] + per - 1 for c in cells]]
        self.x0, self.y0 = min(xs) - self.pad, min(ys) - self.pad
        self.nx, self.ny = max(xs) - self.x0 + self.pad + 1, max(ys) - self.y0 + self.pad + 1
        self.words = (nitems + 63) // 64
        self.own = np.zeros((self.nx, self.ny, self.words), np.uint64)
        self.land = np.zeros((self.nx, self.ny), bool)
        for cx, cy in cells:
            self.land[cx - self.x0:cx - self.x0 + per, cy - self.y0:cy - self.y0 + per] = True
        for (ax, ay), (bx, by), it in zip(lo, hi, items):
            self.own[ax - self.x0:bx - self.x0 + 1, ay - self.y0:by - self.y0 + 1, it >> 6] |= np.uint64(1 << (int(it) & 63))

    def index(self, x, y):
        return int(math.floor(x / self.grain)) - self.x0, int(math.floor(y / self.grain)) - self.y0

    def ring_bits(self, i, j):
        import numpy as np
        out = np.zeros(self.words, np.uint64)
        for dx, dy in self.offsets:
            out |= self.own[i + dx, j + dy]
        return out

    def ring_items(self, i, j):
        import numpy as np
        bits = np.unpackbits(self.ring_bits(i, j).view(np.uint8), bitorder='little')
        return set(np.flatnonzero(bits[:self.nitems]).tolist())

    def occupied(self):
        return self.land | self.own.any(axis=2)

    def ring_totals(self, weight_sets, max_cells=1 << 25):
        """For every chunk: sum of weights of the items in its ring and the item count.

        weight_sets: {name: array(nitems)}. Rows are processed in strips to bound memory."""
        import numpy as np
        p = self.pad
        sums = {k: np.zeros((self.nx, self.ny)) for k in weight_sets}
        count = np.zeros((self.nx, self.ny), np.int64)
        W = {k: np.concatenate([np.asarray(w, np.float32), np.zeros(self.words * 64 - self.nitems, np.float32)])
             for k, w in weight_sets.items()}
        strip = max(1, max_cells // max(1, self.ny * self.words * 64))
        for a in range(p, self.nx - p, strip):
            b = min(self.nx - p, a + strip)
            ring = np.zeros((b - a, self.ny - 2 * p, self.words), np.uint64)
            for dx, dy in self.offsets:
                ring |= self.own[a + dx:b + dx, p + dy:self.ny - p + dy]
            bits = np.unpackbits(ring.reshape(-1, self.words).view(np.uint8), axis=1, bitorder='little')
            count[a:b, p:self.ny - p] = bits.sum(axis=1, dtype=np.int64).reshape(b - a, -1)
            for k, w in W.items():
                sums[k][a:b, p:self.ny - p] = (bits.astype(np.float32) @ w).reshape(b - a, -1)
        return sums, count


def ring_sum_grid(grid, values):
    """Sum of a per-chunk integer grid over each chunk's ring (e.g. placements by origin)."""
    import numpy as np
    p = grid.pad
    out = np.zeros_like(values)
    for dx, dy in grid.offsets:
        out[p:-p, p:-p] += values[p + dx:grid.nx - p + dx, p + dy:grid.ny - p + dy]
    return out


def percentiles(values, qs=(50, 95, 100)):
    import numpy as np
    if not len(values):
        return {('max' if q == 100 else 'p%d' % q): 0 for q in qs}
    return {('max' if q == 100 else 'p%d' % q): float(np.percentile(values, q)) for q in qs}


# ---------------------------------------------------------------- routes and the model cache

def door_route(points):
    """A walk through every point: nearest-neighbour tour from the westmost point."""
    pts = [tuple(map(float, p)) for p in points]
    if not pts:
        return []
    start = min(range(len(pts)), key=lambda i: (pts[i][0], pts[i][1]))
    route, left = [pts[start]], set(range(len(pts))) - {start}
    while left:
        x, y = route[-1]
        i = min(left, key=lambda k: ((pts[k][0] - x) ** 2 + (pts[k][1] - y) ** 2, k))
        route.append(pts[i])
        left.remove(i)
    return route


def walk_chunks(route, grid, step=16.0):
    """Owned chunks along a polyline, in order, without repeats in a row."""
    out = []
    for (x0, y0), (x1, y1) in zip(route, route[1:] or route):
        n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
        for k in range(n + 1):
            c = grid.index(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n)
            if not out or out[-1] != c:
                out.append(c)
    return out


def simulate_cache(chunk_sequence, ring_items, weights, extra_capacity):
    """Unique-model cache along a walk.

    At every owned-chunk change the ring's items must be resident; items already
    resident are hits, others are read (misses). Items outside the ring stay
    cached, least recently used first out, while the cache holds at most the
    ring's bytes + extra_capacity. The first ring is a cold start and is
    reported separately."""
    cache = collections.OrderedDict()
    hits = misses = 0
    loads = []
    cold = None
    for step, c in enumerate(chunk_sequence):
        need = ring_items(*c)
        read = 0
        for it in need:
            if it in cache:
                cache.move_to_end(it)
                if step:
                    hits += 1
            else:
                cache[it] = weights[it]
                read += weights[it]
                if step:
                    misses += 1
        if step == 0:
            cold = read
        else:
            loads.append(read)
        limit = sum(weights[it] for it in need) + extra_capacity
        total = sum(cache.values())
        for it in list(cache):
            if total <= limit:
                break
            if it not in need:
                total -= cache.pop(it)
    return {'crossings': len(loads), 'hits': hits, 'misses': misses,
            'hit_rate': round(hits / (hits + misses), 4) if hits + misses else None,
            'cold_bytes': cold or 0, 'bytes_read': sum(loads),
            'per_crossing_p50': statistics.median(loads) if loads else 0, 'per_crossing_max': max(loads) if loads else 0}


# ---------------------------------------------------------------- terrain heightfield

def heightfield_bytes(samples=65, material_grid=16, material_bytes=1, luxel_units=16, cell_units=CELL_Q,
                      lightmap=True):
    """Bytes of one cell as a quantized heightfield: shorts, material indices and an 8-bit lightmap."""
    lm = (int(cell_units // luxel_units) + 1) ** 2 if lightmap else 0
    return {'heights': samples * samples * 2, 'materials': material_grid * material_grid * material_bytes,
            'lightmap': lm, 'total': samples * samples * 2 + material_grid * material_grid * material_bytes + lm}


# ---------------------------------------------------------------- converted maps: bakes and terrain

def lightmap_shares(m, faces):
    """Per-face lightmap bytes before sharing, and the share of the stored lump each face owns.

    Faces that point at the same bytes of the lighting lump split them evenly."""
    import numpy as np
    size = m.lighting_len
    owners = np.zeros(max(1, size), np.int32)
    spans = {}
    for f in faces:
        n = m.lightmap_bytes(f)
        ofs = m.faces[f][9]
        if n and ofs >= 0:
            a, b = ofs, min(size, ofs + n)
            spans[f] = (a, b, n)
            owners[a:b] += 1
    out = {}
    for f in faces:
        if f in spans:
            a, b, n = spans[f]
            out[f] = (n, float((1.0 / owners[a:b]).sum()) if b > a else 0.0)
        else:
            out[f] = (0, 0.0)
    return out


def map_bakes(data):
    """Per-placement lightmap measurement of one converted map (func_wall entities with aw_ref)."""
    from world_chunk_estimate import Map
    m = Map(data)
    allfaces = range(len(m.faces))
    shares = lightmap_shares(m, allfaces)
    rows = []
    for e in m.entities:
        mod = e.get('model', '')
        if e.get('classname') != 'func_wall' or not mod.startswith('*') or 'aw_ref' not in e:
            continue
        k = int(mod[1:])
        if not 0 < k < len(m.models):
            continue
        first, num = m.models[k][14], m.models[k][15]
        fs = range(first, first + num)
        rows.append({'ref': int(e['aw_ref']), 'model': k, 'faces': num,
                     'lit_faces': sum(1 for f in fs if shares[f][0]),
                     'luxels': sum(shares[f][0] for f in fs), 'stored': round(sum(shares[f][1] for f in fs), 1)})
    w0, wn = m.models[0][14], m.models[0][15]
    world = {'faces': wn, 'luxels': sum(shares[f][0] for f in range(w0, w0 + wn)),
             'stored': round(sum(shares[f][1] for f in range(w0, w0 + wn)), 1)}
    return {'lighting_lump': m.lighting_len, 'luxels_all': sum(v[0] for v in shares.values()),
            'placements': rows, 'world': world, 'file_bytes': len(data), 'models': len(m.models)}


def terrain_cost(data):
    """Terrain part of one converted open-world map: the world model (*0)."""
    from world_chunk_estimate import Map
    m = Map(data)
    rec = m.submodel(0)
    w0, wn = m.models[0][14], m.models[0][15]
    shares = lightmap_shares(m, range(w0, w0 + wn))
    stored_light = sum(v[1] for v in shares.values())
    used_tex = {m.texinfo[m.faces[f][4]][8] for f in range(w0, w0 + wn)}
    tex = sum(m.texbytes[t] for t in used_tex if 0 <= t < len(m.texbytes))
    lumps = {k: rec[k] * DISK.get(k, 0) for k in ('faces', 'texinfo', 'planes', 'vertexes', 'edges', 'surfedges',
                                                    'nodes', 'clipnodes')}
    lumps['leafs'] = rec['leafs'] * 28
    lumps['marksurfaces'] = rec['marksurfaces'] * 2
    lumps['lighting_stored'] = round(stored_light)
    lumps['textures'] = tex
    lumps['visibility'] = m.L[4][1]
    mins, maxs = m.models[0][0:3], m.models[0][3:6]
    area_cells = max(0.0, (maxs[0] - mins[0]) * (maxs[1] - mins[1])) / (CELL_Q * CELL_Q)
    return {'file_bytes': len(data), 'faces': rec['faces'], 'luxels': rec['lighting'], 'lumps': lumps,
            'terrain_bytes': sum(lumps.values()), 'coverage_cells': round(area_cells, 4)}


# ---------------------------------------------------------------- disk plan

def disk_plan(kinds, payload_per_partition=int(1.66e9), partitions_per_image=2, max_file=1 << 30):
    """Fit the payload into <2 GiB FFS partitions and <4 GiB drive images.

    payload_per_partition: usable game bytes per partition (default 1.66 GB, the
    measured fill of today's <2 GiB partitions). Kinds larger than max_file are
    split into packs of at most max_file bytes (asset PAKs sharded by area)."""
    total = sum(kinds.values())
    partitions = max(1, math.ceil(total / payload_per_partition))
    images = math.ceil(partitions / partitions_per_image)
    packs = {k: max(1, math.ceil(v / max_file)) for k, v in kinds.items() if v}
    return {'total_bytes': total, 'partitions': partitions, 'images': images,
            'one_image_budget': payload_per_partition * partitions_per_image,
            'fits_one_image': total <= payload_per_partition * partitions_per_image,
            'over_one_image_bytes': max(0, total - payload_per_partition * partitions_per_image),
            'packs_per_kind': packs,
            'ffs_rules': {'max_pack_bytes': max_file, 'file_name_chars': 30, 'directory_hash_chains': 72,
                          'note': 'packs sharded by area; few files per directory'}}


# ---------------------------------------------------------------- census command

def _progress(msg):
    print(msg, flush=True)


def _bytes_of(meshes, model, space):
    row = meshes.get(model) or {}
    c = row.get('spaces', {}).get(space)
    if not c or 'error' in c:
        return None
    return c


def unique_assets(rows, meshes, space):
    """Unique meshes and textures of a placement list with their AmiWind sizes (measured counts)."""
    models = sorted({p['model'] for p in rows})
    geo = hull = lux = 0
    failed = 0
    textures = {}
    per_class = collections.defaultdict(lambda: {'meshes': 0, 'placements': 0, 'geometry': 0, 'hull': 0,
                                                 'placed_geometry': 0, 'placed_hull': 0})
    cls_of = {}
    for p in rows:
        cls_of.setdefault(p['model'], p['cls'])
        pc = per_class[p['cls']]
        pc['placements'] += 1
        c = _bytes_of(meshes, p['model'], space)
        if c is not None:
            # every placement stored as its own copy (today's interiors: light baked per object)
            pc['placed_geometry'] += geometry_bytes(c)
            pc['placed_hull'] += hull_bytes(c)
    for m in models:
        c = _bytes_of(meshes, m, space)
        if c is None:
            failed += 1
            continue
        g, h = geometry_bytes(c), hull_bytes(c)
        geo += g
        hull += h
        lux += c['luxels']
        pc = per_class[cls_of[m]]
        pc['meshes'] += 1
        pc['geometry'] += g
        pc['hull'] += h
        for t in c['textures']:
            textures[t] = miptex_bytes(int(t.split('|')[1]))
    by_source = {}
    for t, b in textures.items():
        src, size = t.split('|')[0], int(t.split('|')[1])
        by_source[src] = max(by_source.get(src, 0), size)
    return {'meshes': len(models), 'meshes_failed': failed, 'geometry_bytes': geo, 'hull_bytes': hull,
            'luxels_unit_scale': lux, 'textures': len(textures), 'texture_bytes': sum(textures.values()),
            'texture_sources': len(by_source),
            'texture_bytes_by_source_largest': sum(miptex_bytes(s) for s in by_source.values()),
            'texture_sizes': dict(collections.Counter(int(t.split('|')[1]) for t in textures)),
            'per_class': {k: dict(v) for k, v in sorted(per_class.items())},
            'texture_keys': sorted(textures)}


def variant_bytes(rows, meshes, space, scale_policy, tilt_policy):
    """Geometry and hull bytes when each variant under a policy is its own model (unit-scale counts)."""
    by_mesh = collections.defaultdict(list)
    for p in rows:
        by_mesh[p['model']].append(p['s'])
    lv = None
    if isinstance(scale_policy, tuple) and scale_policy[0] == 'mesh':
        lv = {m: mesh_levels(sorted(v), scale_policy[1]) for m, v in by_mesh.items()}
    keys = {variant_key(p, scale_policy, tilt_policy, lv) for p in rows}
    geo = hull = 0
    for k in keys:
        c = _bytes_of(meshes, k[0], space)
        if c is not None:
            geo += geometry_bytes(c)
            hull += hull_bytes(c)
    return {'variants': len(keys), 'geometry_bytes': geo, 'hull_bytes': hull}


def angle_tables(rows):
    out = {'all': {'scale': scale_histogram([p['s'] for p in rows]),
                   'tilt': {'edges': list(TILT_EDGES), 'bins': histogram([tilt_degrees(p['r']) for p in rows], TILT_EDGES),
                            'untilted': sum(1 for p in rows if not D.tilted(p['r']))}}}
    for cls in CLASSES:
        sub = [p for p in rows if p['cls'] == cls]
        out[cls] = {'placements': len(sub), 'scale': scale_histogram([p['s'] for p in sub]),
                    'tilt': {'edges': list(TILT_EDGES),
                             'bins': histogram([tilt_degrees(p['r']) for p in sub], TILT_EDGES),
                             'untilted': sum(1 for p in sub if not D.tilted(p['r']))}}
    return out


def chunk_census(rows, meshes, land_cells, grains, radius, cell_names, routes, extra_caps, collision_radius=224.0):
    """Item 3: per-chunk unique-model bytes in the ring, for each grain, and the route walks."""
    import numpy as np
    ok = [p for p in rows if _bytes_of(meshes, p['model'], 'exterior') is not None]
    models = sorted({p['model'] for p in ok})
    mid = {m: i for i, m in enumerate(models)}
    vkeys = sorted({variant_key(p, 'exact', 'exact') for p in ok}, key=repr)
    vid = {k: i for i, k in enumerate(vkeys)}
    tex = sorted({t for m in models for t in meshes[m]['spaces']['exterior']['textures']})
    tid = {t: i for i, t in enumerate(tex)}
    wg = np.array([geometry_bytes(meshes[m]['spaces']['exterior']) for m in models], float)
    wh = np.array([hull_bytes(meshes[m]['spaces']['exterior']) for m in models], float)
    wm = wg + wh
    wv = np.array([wm[mid[k[0]]] for k in vkeys], float)
    wt = np.array([miptex_bytes(int(t.split('|')[1])) for t in tex], float)
    boxes, origins = [], []
    for p in ok:
        b0, b1 = D.world_bounds(meshes[p['model']]['bounds'], {'r': p['r'], 's': p['s'], 'p': p['p']})
        boxes.append([b0[0] * SCALE, b0[1] * SCALE, b1[0] * SCALE, b1[1] * SCALE])
        origins.append((p['p'][0] * SCALE, p['p'][1] * SCALE))
    tboxes, titems = [], []
    for p, box in zip(ok, boxes):
        for t in meshes[p['model']]['spaces']['exterior']['textures']:
            tboxes.append(box)
            titems.append(tid[t])
    land = sorted(land_cells)
    out = {'models': len(models), 'variants': len(vkeys), 'textures': len(tex), 'radius': radius, 'grains': {}}
    for g in grains:
        gm = ChunkGrid(boxes, [mid[p['model']] for p in ok], len(models), g, radius, land)
        gv = ChunkGrid(boxes, [vid[variant_key(p, 'exact', 'exact')] for p in ok], len(vkeys), g, radius, land)
        gt = ChunkGrid(tboxes, titems, len(tex), g, radius, land) if tex else None
        sm, cm = gm.ring_totals({'bytes': wm, 'geometry': wg})
        gc = ChunkGrid(boxes, [mid[p['model']] for p in ok], len(models), g, collision_radius, land, gm.pad)
        sc, cc = gc.ring_totals({'hull': wh})
        sv, cv = gv.ring_totals({'bytes': wv})
        occ = gm.occupied()
        recs = np.zeros((gm.nx, gm.ny), np.int64)
        for x, y in origins:
            i, j = gm.index(x, y)
            recs[i, j] += 1
        rp = ring_sum_grid(gm, recs)
        res = {'chunks_occupied': int(occ.sum()), 'ring_chunks': len(gm.offsets), 'collision_ring_chunks': len(gc.offsets)}
        mask = occ
        res['mesh_bytes'] = percentiles(sm['bytes'][mask])
        res['mesh_geometry_bytes'] = percentiles(sm['geometry'][mask])
        res['mesh_hull_bytes_collision_margin'] = percentiles(sc['hull'][mask])
        res['mesh_resident_bytes'] = percentiles((sm['geometry'] + sc['hull'])[mask])
        res['mesh_models'] = percentiles(cm[mask])
        res['variant_bytes'] = percentiles(sv['bytes'][mask])
        res['variant_models'] = percentiles(cv[mask])
        res['placement_records'] = percentiles(rp[mask] * PLACEMENT_RECORD)
        if gt is not None:
            st, ct = gt.ring_totals({'bytes': wt})
            res['texture_bytes'] = percentiles(st['bytes'][mask])
        hot, seen = [], set()
        resident = (sm['geometry'] + sc['hull']) * mask
        for f in np.argsort(-resident, axis=None):
            i, j = np.unravel_index(f, resident.shape)
            x, y = (i + gm.x0) * g, (j + gm.y0) * g
            cell = (int(math.floor(x / CELL_Q)), int(math.floor(y / CELL_Q)))
            if cell in seen:
                continue
            seen.add(cell)
            if len(hot) == 12:
                break
            hot.append({'chunk': [int(i + gm.x0), int(j + gm.y0)], 'cell': list(cell), 'name': cell_names.get(cell, ''),
                        'mesh_bytes': float(sm['bytes'][i, j]), 'resident_bytes': float(resident[i, j]),
                        'variant_bytes': float(sv['bytes'][i, j]),
                        'models': int(cm[i, j])})
        res['hot'] = hot
        res['routes'] = {}
        for rname, route in routes.items():
            seq = walk_chunks(route, gm)
            rr = {'length_units': round(sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(route, route[1:])), 1),
                  'stops': len(route), 'chunks_visited': len(seq)}
            for mode, grid, w in (('mesh', gm, wm), ('variant', gv, wv)):
                memo = {}

                def ring(i, j, grid=grid, memo=memo):
                    if (i, j) not in memo:
                        memo[(i, j)] = grid.ring_items(i, j)
                    return memo[(i, j)]
                for cap in extra_caps:
                    rr['%s_extra%d' % (mode, cap)] = simulate_cache(seq, ring, w, cap)
            res['routes'][rname] = rr
        out['grains'][str(g)] = res
        _progress('chunks %d done' % g)
    return out


def census(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    work = Path(args.work) if args.work else out / 'work'
    _progress('reading masters')
    masters = D.census(args.data_files)
    import world_estimate as WE
    excluded = WE.exclusion(WE.load_config(None), masters, args.exclude)
    names = sorted(D.used_meshes(masters))
    meshes = scan_meshes(args.data_files, names, work / 'census-meshes.json', args.jobs, _progress)
    placements = collect_placements(masters, meshes, set(excluded))
    report = {'format': FORMAT, 'census_version': CENSUS_VERSION,
              'inputs': {m: masters[m]['sha256'] for m in masters},
              'original_bytes': original_sizes(args.data_files),
              'mesh_status': dict(collections.Counter(r.get('status') for r in meshes.values())),
              'excluded_interiors': len(excluded),
              'measured': ['unique meshes/textures and their per-mesh counts', 'placements', 'scale and tilt histograms',
                           'variant counts', 'LAND cells', 'ring item sets'],
              'estimated': ['bytes of scaled variants (unit-scale counts reused)', 'lightmaps at scale != 1',
                            'route walks (door tours)', 'disk totals'],
              'sets': {}}
    for label, rows in placements.items():
        sr = {}
        for space in ('exterior', 'interior'):
            sub = [p for p in rows if p['space'] == space]
            if not sub:
                continue
            ua = unique_assets(sub, meshes, space)
            keys = ua.pop('texture_keys')
            sr[space] = {'unique': ua, 'angles': angle_tables(sub), 'variants': variant_table(sub),
                         'placements_today_converters': sum(1 for p in sub if p['cur']),
                         'variant_bytes': {policy_name(sp) + '/' + tp: variant_bytes(sub, meshes, space, sp, tp)
                                           for sp in scale_policies() for tp in TILT_POLICIES}}
            sr[space]['_texture_keys'] = keys
            if space == 'interior':
                lux = collections.defaultdict(float)
                for p in sub:
                    c = _bytes_of(meshes, p['model'], 'interior')
                    if c is not None:
                        lux[p['cls']] += luxels_at(c, p['s'])
                sr[space]['luxels_per_placement_estimated'] = {k: round(v) for k, v in sorted(lux.items())}
                sr[space]['cells'] = len({p['cell'] for p in sub})
        tex_all = set(sr.get('exterior', {}).get('_texture_keys', [])) | set(sr.get('interior', {}).get('_texture_keys', []))
        for space in sr:
            sr[space].pop('_texture_keys', None)
        sr['textures_both_spaces'] = {'textures': len(tex_all),
                                      'texture_bytes': sum(miptex_bytes(int(t.split('|')[1])) for t in tex_all)}
        world = D.World(masters, [m for m in D.MASTERS if D.SET_OF_MASTER[m] == label][0], meshes)
        own_land = masters[[m for m in D.MASTERS if D.SET_OF_MASTER[m] == label][0]]['lands']
        if label != 'vvardenfell':
            own_land = {k: v for k, v in own_land.items() if k not in masters['Morrowind.esm']['lands']}
        hf16 = heightfield_bytes(luxel_units=16)
        hf32 = heightfield_bytes(luxel_units=32)
        sr['terrain'] = {'land_cells': len(own_land), 'heightfield_cell_16': hf16, 'heightfield_cell_32': hf32,
                         'heightfield_cell_none': heightfield_bytes(lightmap=False),
                         'island_16': hf16['total'] * len(own_land), 'island_32': hf32['total'] * len(own_land),
                         'island_heights_only': heightfield_bytes(lightmap=False)['total'] * len(own_land)}
        ext = [p for p in rows if p['space'] == 'exterior']
        if ext and args.grains:
            names_ = {}
            for c in world.cells:
                if not c['interior']:
                    names_[(c['x'], c['y'])] = c['name'] or c['region']
            routes = {}
            for rc in args.route_cell or []:
                pts = [(p['p'][0] * SCALE, p['p'][1] * SCALE) for p in ext
                       if p['door'] and names_.get(tuple(p['cell']), '').casefold() == rc.casefold()]
                if pts:
                    routes[rc] = door_route(pts)
            sr['chunks'] = chunk_census(ext, meshes, own_land, args.grains, args.draw_distance + args.hysteresis,
                                        names_, routes, args.cache_extra, args.collision_margin)
        report['sets'][label] = sr
        _progress('set %s done' % label)
    (out / 'census.json').write_text(json.dumps(report, indent=1, sort_keys=True, default=str) + '\n',
                                     encoding='utf-8', newline='\n')
    _progress('wrote ' + str(out / 'census.json'))
    return 0


def original_sizes(data_files):
    from mwad.paths import child_ci
    out = {}
    for name in ('Morrowind.esm', 'Morrowind.bsa', 'Tribunal.esm', 'Tribunal.bsa', 'Bloodmoon.esm', 'Bloodmoon.bsa'):
        p = child_ci(Path(data_files), name, required=False)
        if p is not None and p.is_file():
            out[name] = p.stat().st_size
    return out


# ---------------------------------------------------------------- bakes command

def interior_map_cells():
    """{map name: interior cell name} from this repository's area configurations."""
    out = {}

    def walk(x):
        if isinstance(x, dict):
            if isinstance(x.get('map'), str) and isinstance(x.get('cell'), str):
                out.setdefault(x['map'], x['cell'])
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    for name in ('balmora_interiors.json', 'seyda_area.json'):
        p = ROOT / 'config' / name
        if p.is_file():
            walk(json.loads(p.read_text(encoding='utf-8')))
    return out


def bakes(args):
    masters = D.census(args.data_files)
    objects = dict(masters['Morrowind.esm']['objects'])
    cells = {c['name'].casefold(): c for c in masters['Morrowind.esm']['cells'] if c['interior']}
    meshes = {}
    if args.census_meshes and Path(args.census_meshes).is_file():
        meshes = json.loads(Path(args.census_meshes).read_text(encoding='utf-8'))
    mapping = interior_map_cells()
    per_class = collections.defaultdict(lambda: {'placements': 0, 'luxels': 0, 'stored': 0.0, 'predicted': 0.0,
                                                 'faces': 0, 'values': []})
    maps_out, ext_out = {}, {}
    for path in sorted(Path(args.maps).glob('*.bsp')):
        name = path.stem
        data = path.read_bytes()
        if name in mapping and mapping[name].casefold() in cells and cells[mapping[name].casefold()]['interior']:
            res = map_bakes(data)
            refs = {r['n']: r for r in cells[mapping[name].casefold()]['refs']}
            for row in res['placements']:
                ref = refs.get(row['ref'])
                o = objects.get(ref['id']) if ref else None
                model = o['model'] if o else ''
                cls = mesh_class(model, o['type'] if o else '') if o else 'unknown'
                c = (meshes.get(model) or {}).get('spaces', {}).get('interior')
                pred = luxels_at(c, float(ref.get('s', 1.0))) if c and 'error' not in c else None
                pc = per_class[cls]
                pc['placements'] += 1
                pc['luxels'] += row['luxels']
                pc['stored'] += row['stored']
                pc['faces'] += row['faces']
                pc['values'].append(row['stored'])
                if pred is not None:
                    pc['predicted'] += pred
            maps_out[name] = {k: v for k, v in res.items() if k != 'placements'}
            maps_out[name]['placements'] = len(res['placements'])
            maps_out[name]['luxels_placements'] = sum(r['luxels'] for r in res['placements'])
            maps_out[name]['stored_placements'] = round(sum(r['stored'] for r in res['placements']))
        elif re.match(r'(bm|sn)\d{3}$', name):
            res = map_bakes(data)
            ext_out[name] = {'placements': len(res['placements']),
                             'placements_with_lit_faces': sum(1 for r in res['placements'] if r['lit_faces']),
                             'placement_luxels': sum(r['luxels'] for r in res['placements']),
                             'world_luxels': res['world']['luxels'], 'lighting_lump': res['lighting_lump']}
    classes = {}
    for cls, pc in sorted(per_class.items()):
        vals = sorted(pc.pop('values'))
        classes[cls] = {**{k: (round(v) if isinstance(v, float) else v) for k, v in pc.items()},
                        'stored_per_placement': percentiles(vals),
                        'luxels_per_placement_mean': round(pc['luxels'] / pc['placements'], 1) if pc['placements'] else 0,
                        'stored_over_luxels': round(pc['stored'] / pc['luxels'], 4) if pc['luxels'] else None,
                        'luxels_over_predicted': round(pc['luxels'] / pc['predicted'], 4) if pc['predicted'] else None}
    report = {'format': FORMAT + '-bakes', 'interior_maps': maps_out, 'per_class': classes,
              'exterior_maps': ext_out,
              'totals': {'interior_maps': len(maps_out),
                         'luxels': sum(v['luxels_all'] for v in maps_out.values()),
                         'lighting_lumps': sum(v['lighting_lump'] for v in maps_out.values()),
                         'exterior_maps': len(ext_out),
                         'exterior_placements_lit': sum(v['placements_with_lit_faces'] for v in ext_out.values()),
                         'exterior_placements': sum(v['placements'] for v in ext_out.values())}}
    Path(args.out).write_text(json.dumps(report, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    print('wrote', args.out)
    return 0


# ---------------------------------------------------------------- terrain command

def terrain(args):
    rows = {}
    for path in sorted(Path(args.maps).glob(args.pattern)):
        rows[path.stem] = terrain_cost(path.read_bytes())
    sample_file = sum(r['file_bytes'] for r in rows.values())
    sample_terrain = sum(r['terrain_bytes'] for r in rows.values())
    report = {'format': FORMAT + '-terrain', 'maps': rows, 'sample_maps': len(rows),
              'sample_file_bytes': sample_file, 'sample_terrain_bytes': sample_terrain,
              'terrain_share': round(sample_terrain / sample_file, 4) if sample_file else None,
              'per_map_terrain': percentiles([r['terrain_bytes'] for r in rows.values()]),
              'per_covered_cell': percentiles([r['terrain_bytes'] / r['coverage_cells'] for r in rows.values()
                                              if r['coverage_cells']])}
    if args.listing:
        sizes = {}
        for line in Path(args.listing).read_text(encoding='utf-8').splitlines():
            m = re.match(r'\s*(\d+)\s+\S*?/?([^/\s]+)\.bsp\s*$', line)
            if m and re.match(args.pattern.replace('*', '.*').replace('.bsp', '') + '$', m.group(2)):
                sizes[m.group(2)] = int(m.group(1))
        total = sum(sizes.values())
        report['all_maps'] = len(sizes)
        report['all_file_bytes'] = total
        report['all_terrain_bytes_estimated'] = round(total * report['terrain_share']) if report['terrain_share'] else None
    Path(args.out).write_text(json.dumps(report, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    print('wrote', args.out)
    return 0


# ---------------------------------------------------------------- disk command

SCENARIOS = {
    # name: geometry policy, hull policy, interior luxel factor, terrain, interior kit pieces per placement
    'today-rules': ('exact/exact', 'exact/exact', 1.0, 'island_16', False),
    'recommended': ('runtime/runtime', 'octave8/quant', 1.0, 'island_32', False),
    'kit-in-maps': ('runtime/runtime', 'octave8/quant', 1.0, 'island_32', True),
    'lean': ('runtime/runtime', 'runtime/quant', 0.25, 'island_32', False),
}


def streamer_kinds(census_report, bakes_report=None, geometry_policy='runtime/runtime', hull_policy='octave8/quant',
                   interior_luxel_factor=1.0, terrain_choice='island_32', kit_in_maps=False, extra=None):
    """Bytes by kind for the streamer (estimated from the measured census).

    Geometry: one model per variant under geometry_policy ('runtime/runtime':
    one per mesh, scale and tilt applied when drawing). Hulls: one per variant
    under hull_policy (a Quake hull cannot be rotated off-axis or scaled at run
    time unless stored unexpanded). kit_in_maps: interior architecture pieces
    are compiled into each interior map (one copy per placement) instead of
    shared. Interior lightmaps per placement for structural classes (tier 2),
    scaled by the measured stored/luxel ratio of the bakes and by
    interior_luxel_factor (0.25 = 32-unit luxels); one byte per flora/clutter
    placement (tier 3). Textures once per set, placement records, terrain."""
    kinds = collections.Counter()
    ratio = 1.0
    if bakes_report:
        tot_l = sum(v['luxels'] for k, v in bakes_report['per_class'].items() if k in STRUCTURAL)
        tot_s = sum(v['stored'] for k, v in bakes_report['per_class'].items() if k in STRUCTURAL)
        ratio = tot_s / tot_l if tot_l else 1.0
    for label, sr in census_report['sets'].items():
        for space in ('exterior', 'interior'):
            if space not in sr:
                continue
            s = sr[space]
            geo = s['variant_bytes'][geometry_policy]['geometry_bytes']
            if kit_in_maps and space == 'interior':
                b = s['unique']['per_class'].get('buildings', {})
                geo += b.get('placed_geometry', 0) - b.get('geometry', 0)
            kinds[space + ' geometry'] += geo
            kinds[space + ' hulls'] += s['variant_bytes'][hull_policy]['hull_bytes']
            kinds['placement records'] += s['variants']['placements'] * PLACEMENT_RECORD
            if space == 'interior':
                lux = s['luxels_per_placement_estimated']
                kinds['interior lightmaps (tier 2)'] += round(sum(v for k, v in lux.items() if k in STRUCTURAL)
                                                              * ratio * interior_luxel_factor)
                kinds['interior light levels (tier 3)'] += sum(
                    s['angles'][k]['placements'] for k in CLASSES if k not in STRUCTURAL)
        kinds['textures'] += sr['textures_both_spaces']['texture_bytes']
        kinds['terrain'] += sr['terrain'][terrain_choice]
    for k, v in (extra or {}).items():
        kinds[k] += int(v)
    return dict(kinds)


def disk(args):
    rep = json.loads(Path(args.census).read_text(encoding='utf-8'))
    bk = json.loads(Path(args.bakes).read_text(encoding='utf-8')) if args.bakes else None
    extra = json.loads(Path(args.extra).read_text(encoding='utf-8')) if args.extra else {}
    out = {'format': FORMAT + '-disk', 'estimated': True, 'original_bytes': rep.get('original_bytes', {}),
           'scenarios': {}}
    for name, (gp, hp, lf, terr, kit) in SCENARIOS.items():
        kinds = streamer_kinds(rep, bk, gp, hp, lf, terr, kit, extra)
        world = streamer_kinds(rep, bk, gp, hp, lf, terr, kit, None)
        out['scenarios'][name] = {'geometry_policy': gp, 'hull_policy': hp, 'interior_luxel_factor': lf,
                                  'terrain': terr, 'kit_in_maps': kit, 'kinds': kinds,
                                  'world_bytes': sum(world.values()),
                                  'plan': disk_plan(kinds, args.payload_per_partition)}
    Path(args.out).write_text(json.dumps(out, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    print('wrote', args.out)
    return 0


# ---------------------------------------------------------------- CLI

def add_census_options(p):
    p.add_argument('--data-files', type=Path, required=True, help='Your Morrowind installation root or Data Files')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--work', type=Path, help='Mesh census cache directory (default OUT/work)')
    p.add_argument('--jobs', type=int, default=0)
    p.add_argument('--exclude', choices=('default', 'listed', 'none'), default='default',
                   help='Development interior exclusion, as in the world estimate')
    p.add_argument('--grains', type=int, nargs='*', default=[256, 512, 1024])
    p.add_argument('--draw-distance', type=float, default=540.0)
    p.add_argument('--hysteresis', type=float, default=96.0)
    p.add_argument('--collision-margin', type=float, default=224.0,
                   help='Hulls are resident only for chunks within this distance (units)')
    p.add_argument('--route-cell', action='append', help='Exterior cell name: walk through its load doors')
    p.add_argument('--cache-extra', type=int, nargs='*', default=[0, 1 << 19, 1 << 20, 1 << 21],
                   help='Model cache bytes kept beyond the ring for the route walk')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='action', required=True)
    add_census_options(sub.add_parser('census', help='Measure unique assets, variants, chunks and terrain'))
    b = sub.add_parser('bakes', help='Lightmap bytes per placement in converted maps')
    b.add_argument('--data-files', type=Path, required=True)
    b.add_argument('--maps', type=Path, required=True)
    b.add_argument('--census-meshes', type=Path, help='census-meshes.json from census (predicted luxels)')
    b.add_argument('--out', type=Path, required=True)
    t = sub.add_parser('terrain', help='Terrain bytes of converted open-world maps')
    t.add_argument('--maps', type=Path, required=True)
    t.add_argument('--pattern', default='vf*.bsp')
    t.add_argument('--listing', type=Path, help='Lines "BYTES path/NAME.bsp" of every map, to extrapolate')
    t.add_argument('--out', type=Path, required=True)
    d = sub.add_parser('disk', help='Streamer disk totals, partitions and drive images')
    d.add_argument('--census', type=Path, required=True)
    d.add_argument('--bakes', type=Path)
    d.add_argument('--extra', type=Path, help='JSON {kind: bytes} of payload outside the world (sound, music, ...)')
    d.add_argument('--payload-per-partition', type=int, default=int(1.66e9))
    d.add_argument('--out', type=Path, required=True)
    args = p.parse_args(argv)
    if getattr(args, 'jobs', None) == 0:
        from build_jobs import resolve_jobs
        args.jobs = resolve_jobs(None)
    try:
        return {'census': census, 'bakes': bakes, 'terrain': terrain, 'disk': disk}[args.action](args)
    except (OSError, ValueError) as exc:
        p.exit(1, 'Error: %s\n' % exc)


if __name__ == '__main__':
    raise SystemExit(main())
