#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""CHIM/legacy border audit: the stitcher, step 1 (measure, change nothing).

A CHIM area inside the legacy open world (a town table row with a world
handoff, e.g. a CHIMport test block) meets the legacy region maps (vfNNNN) at
its handoff core. The engine changes maps there (aw_world.c
AW_WorldDestination): a player in a legacy region enters the CHIM area when
he stands inside its core, and leaves it again 32 units past the core. Both
maps must agree at that line, or the player sees a step, falls on arrival or
watches objects appear.

This audit reads one finished build run (read only) and measures, for every
such area and every edge of its core (N, E, S, W):

- heights: the ground under the same point on both sides, every 8 units along
  lines parallel to the edge (offsets from -896 to +64 units, inside the
  frame's ground), legacy from the compiled region maps' ground faces, CHIM
  from the frame's chunk terrain faces; shoreline tiles (ground crossing the
  water level) are flagged, because the legacy converter refines them and the
  regular CHIM grid does not;
- contents: empty / water / solid just above the higher of the two grounds;
- arrival: where the standing hull (hull 1) rests at the handover points
  (enter at the core edge, leave at core + 32) on both maps;
- far layer: the frame's far terrain sidecar against the legacy ground at its
  sample points in the band outside the core (what the player sees from the
  CHIM side vs what he finds on the legacy side), and the depth with no ground
  at all between the frame edge and the fog plane (the far layer is drawn
  beyond the fog plane only);
- objects whose drawn box crosses the band (+-896 units around the core
  edge), per side, matched by source reference: drawn by both, only by the
  legacy map, only by the CHIM area; and those cut by the handover line.

Report format aw-stitch-report-1 (docs/chim/STITCH_AUDIT.md). Light: plain
Python and numpy; no game data beyond the run's own files.

    python3 tools/chim/stitch.py audit --run RUN [--area ID ...] [--regions all|X,Y ...] [--out REPORT.json]

CHIM region frames (--chim-regions, docs/chim/CHIM_REGIONS.md: one frame per exterior cell, core = the cell)
are audited the same way with --regions: every edge of the cell against the legacy map beside it; an edge
that meets another CHIM frame is listed as a frame neighbour, not measured. A divided cell (2 x 2 or 4 x 4
legacy maps) is one frame like any other cell (CHIM-REGION-DIVIDED-CELLS-36).
"""
import argparse
import hashlib
import json
import math
import struct
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

FORMAT = 'aw-stitch-report-1'
STEP = 8                     # units between samples along an edge (the standing box footprint)
BAND = 896                   # legacy region overlap: the band audited on each side of the core edge
HEIGHT_OFFSETS = (-896, -512, -256, -128, -64, -32, 0, 32, 64)   # outward offsets with ground on both sides
ARRIVAL = {'enter': 0.0, 'leave': 32.0}   # the engine's handover lines (aw_world.c: core, core + 32)
TILE = 128                   # terrain tile (both sides' corner samples)
WATER_LEVEL = 0.0            # global local units, both sides
CELL = 2048                  # one Morrowind cell in local units
LEGACY_STAGES = ('world-flora', 'world-scenery', 'world-terrain')   # most final first
EDGES = ('N', 'E', 'S', 'W')
LIMITS = {
    'height_fail': 4.5,      # units: the actor refit rule (a step the standing box notices)
    'height_warn': 1.0,
    'arrival_fail': 4.5,
    'arrival_warn': 1.0,
    'far_step': None,        # reported, not judged yet
    'far_gap': None,         # reported (warn when > 0), not failing yet
}
EMPTY, SOLID, WATER = -1, -2, -3
CONTENTS = {-1: 'empty', -2: 'solid', -3: 'water', -4: 'slime', -5: 'lava', -6: 'sky'}
EPS = 1e-4


# ---------------------------------------------------------------- ground sampler (pure geometry)

class Ground:
    """Upward faces of one map in global coordinates, binned for point queries.

    faces: [(points [(x, y, z)...], kind)] or [(points, kind, normal)] with kind 'ground' or
    'liquid'; only faces whose normal (given, else from the points, counter-clockwise seen from
    above) points up are kept. height(x, y) -> (ground z or None, liquid z or None): the highest
    face of each kind whose plan contains the point (edges included)."""
    BIN = 64

    def __init__(self, faces):
        self.faces = []
        self.bins = {}
        for face in faces:
            pts, kind = face[0], face[1]
            pts = [tuple(float(v) for v in p) for p in pts]
            if len(pts) < 3:
                continue
            n = tuple(face[2]) if len(face) > 2 else _normal(pts)
            if n is None or n[2] <= 1e-3:
                continue
            d = n[0] * pts[0][0] + n[1] * pts[0][1] + n[2] * pts[0][2]
            k = len(self.faces)
            self.faces.append((pts, n, d, kind))
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            for bx in range(int(math.floor(min(xs) / self.BIN)), int(math.floor(max(xs) / self.BIN)) + 1):
                for by in range(int(math.floor(min(ys) / self.BIN)), int(math.floor(max(ys) / self.BIN)) + 1):
                    self.bins.setdefault((bx, by), []).append(k)

    def height(self, x, y):
        best = {'ground': None, 'liquid': None}
        for k in self.bins.get((int(math.floor(x / self.BIN)), int(math.floor(y / self.BIN))), ()):
            pts, n, d, kind = self.faces[k]
            if not inside_xy(pts, x, y):
                continue
            z = (d - n[0] * x - n[1] * y) / n[2]
            if best[kind] is None or z > best[kind]:
                best[kind] = z
        return best['ground'], best['liquid']


def _normal(pts):
    """Unit normal of a planar polygon (Newell), or None when degenerate."""
    nx = ny = nz = 0.0
    m = len(pts)
    for i in range(m):
        x0, y0, z0 = pts[i]
        x1, y1, z1 = pts[(i + 1) % m]
        nx += (y0 - y1) * (z0 + z1)
        ny += (z0 - z1) * (x0 + x1)
        nz += (x0 - x1) * (y0 + y1)
    length = math.sqrt(nx * nx + ny * ny + nz * nz)
    if length < 1e-12:
        return None
    return (nx / length, ny / length, nz / length)


def inside_xy(pts, x, y, eps=EPS):
    """Point in a convex polygon's plan, either winding, edges included."""
    sign = 0
    m = len(pts)
    for i in range(m):
        ax, ay = pts[i][0], pts[i][1]
        bx, by = pts[(i + 1) % m][0], pts[(i + 1) % m][1]
        c = (bx - ax) * (y - ay) - (by - ay) * (x - ax)
        scale = math.hypot(bx - ax, by - ay) or 1.0
        if abs(c) <= eps * scale:
            continue
        s = 1 if c > 0 else -1
        if sign and s != sign:
            return False
        sign = s
    return True


def standing(contents, x, y, ground, resolution=1.0 / 32, rise=16.0, tries=32):
    """Origin height at which the standing hull rests at (x, y): the lowest non-solid height above
    the solid boundary nearest `ground`, by bisection. contents(point) -> contents number of the
    standing hull. None when no solid floor lies 64 units below `ground` or no free space lies
    within tries x rise above it (the result is then 'not measured', never guessed)."""
    hi = ground + 64.0
    for _ in range(tries):
        if contents((x, y, hi)) != SOLID:
            break
        hi += rise
    else:
        return None
    lo = ground - 64.0
    if contents((x, y, lo)) != SOLID:
        return None
    while hi - lo > resolution:
        mid = (hi + lo) / 2.0
        if contents((x, y, mid)) == SOLID:
            lo = mid
        else:
            hi = mid
    return hi


# ---------------------------------------------------------------- BSP29 readers

def bsp_lumps(data):
    from chim import format as F
    return F.read_brush_image(data)


def miptex_names(lump):
    if len(lump) < 4:
        return []
    n = struct.unpack_from('<i', lump)[0]
    out = []
    for k in range(n):
        o = struct.unpack_from('<i', lump, 4 + 4 * k)[0]
        out.append(lump[o:o + 16].split(b'\0')[0].decode('latin-1') if o >= 0 else '')
    return out


def model_row(lumps, index=0):
    v = struct.unpack_from('<9f4iiii', lumps[14], 64 * index)
    return {'mins': v[0:3], 'maxs': v[3:6], 'origin': v[6:9], 'headnode': v[9:13], 'firstface': v[14],
            'numfaces': v[15]}


def faces_of(lumps, names, first=0, count=None, shift=(0.0, 0.0, 0.0)):
    """[(points, texture name, front normal)] of faces first..first+count, points shifted by `shift`
    (Quake winds faces clockwise seen from the front: the normal comes from the plane and side)."""
    planes = list(struct.iter_unpack('<4fi', lumps[1]))
    verts = list(struct.iter_unpack('<3f', lumps[3]))
    texinfo = list(struct.iter_unpack('<8fii', lumps[6]))
    edges = list(struct.iter_unpack('<HH', lumps[12]))
    surfedges = [v[0] for v in struct.iter_unpack('<i', lumps[13])]
    total = len(lumps[7]) // 20
    count = total - first if count is None else count
    out = []
    for f in range(first, first + count):
        plane, side, fe, ne, ti = struct.unpack_from('<HhihH', lumps[7], 20 * f)
        ids = [edges[e][0] if e >= 0 else edges[-e][1] for e in surfedges[fe:fe + ne]]
        pts = [(verts[i][0] + shift[0], verts[i][1] + shift[1], verts[i][2] + shift[2]) for i in ids]
        mt = texinfo[ti][8]
        k = -1.0 if side else 1.0
        normal = tuple(k * v for v in planes[plane][:3])
        out.append((pts, names[mt] if 0 <= mt < len(names) else '', normal))
    return out


def face_kind(name):
    """'liquid' for Quake liquids (*water, *lava ...), 'ground' for terrain materials, None otherwise."""
    if name.startswith('*'):
        return 'liquid'
    if name.startswith('g') and name[1:].isdigit():
        return 'ground'
    return None


def node_contents(lumps, root, p):
    """Contents of a point in a point hull (the node tree), as SV_HullPointContents on hull 0."""
    planes, nodes, leafs = lumps[1], lumps[5], lumps[10]
    n = root
    while n >= 0:
        pi, front, back = struct.unpack_from('<ihh', nodes, 24 * n)
        a, b, c, d = struct.unpack_from('<4f', planes, 20 * pi)
        n = front if a * p[0] + b * p[1] + c * p[2] - d >= 0 else back
    return struct.unpack_from('<i', leafs, 28 * (-1 - n))[0]


def clip_contents(lumps, root, p):
    """Contents of a point in a clipnode hull (hull 1, the standing box)."""
    planes, clips = lumps[1], lumps[9]
    num = root
    while num >= 0:
        pi, front, back = struct.unpack_from('<iHH', clips, 8 * num)
        a, b, c, d = struct.unpack_from('<4f', planes, 20 * pi)
        child = front if a * p[0] + b * p[1] + c * p[2] - d >= 0 else back
        num = child - 65536 if child >= 0xFFF0 else child
    return num


def entities(text):
    out, cur = [], None
    for line in text.splitlines():
        line = line.strip()
        if line == '{':
            cur = {}
        elif line == '}':
            if cur is not None:
                out.append(cur)
            cur = None
        elif cur is not None and line.startswith('"'):
            parts = line.split('"')
            if len(parts) >= 4:
                cur[parts[1]] = parts[3]
    return out


def yaw_box(mins, maxs, yaw):
    """Plan box of a model box turned by yaw degrees (z unchanged)."""
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    xs, ys = [], []
    for x in (mins[0], maxs[0]):
        for y in (mins[1], maxs[1]):
            xs.append(c * x - s * y)
            ys.append(s * x + c * y)
    return (min(xs), min(ys), mins[2]), (max(xs), max(ys), maxs[2])


# ---------------------------------------------------------------- the two sides

class LegacyMap:
    """One legacy region map: its ground (global), point contents and standing hull."""

    def __init__(self, region, path):
        self.name = region['name']
        self.path = path
        data = Path(path).read_bytes()
        self.sha256 = hashlib.sha256(data).hexdigest()
        self.lumps = bsp_lumps(data)
        self.origin = tuple(float(v) for v in region['origin'])
        self.core = region['core']
        self.model = model_row(self.lumps, 0)
        names = miptex_names(self.lumps[2])
        faces = faces_of(self.lumps, names, self.model['firstface'], self.model['numfaces'], self.origin)
        self.ground = Ground([(p, face_kind(n), nv) for p, n, nv in faces if face_kind(n)])
        self.entities = entities(self.lumps[0].split(b'\0')[0].decode('latin-1'))

    def local(self, p):
        return (p[0] - self.origin[0], p[1] - self.origin[1], p[2] - self.origin[2])

    def contents(self, p):
        return node_contents(self.lumps, self.model['headnode'][0], self.local(p))

    def hull(self, p):
        return clip_contents(self.lumps, self.model['headnode'][1], self.local(p))

    def objects(self):
        """[(ref, model, origin, (mins, maxs))] global, every entity with a source reference."""
        out = []
        for e in self.entities:
            ref = e.get('aw_ref')
            if ref is None or 'origin' not in e:
                continue
            o = [float(v) for v in e['origin'].split()]
            yaw = float(e.get('angles', '0 0 0').split()[1]) if 'angles' in e else float(e.get('angle', 0) or 0)
            model = e.get('model', '')
            if model.startswith('*'):
                row = model_row(self.lumps, int(model[1:]))
                lo, hi = yaw_box(row['mins'], row['maxs'], yaw)
            else:
                lo, hi = (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)
            g = [o[k] + self.origin[k] for k in range(3)]
            out.append((str(ref), model, tuple(g), (tuple(g[k] + lo[k] for k in range(3)),
                                                     tuple(g[k] + hi[k] for k in range(3)))))
        return out


class Legacy:
    """The legacy world of a run: region directory + lazily loaded region maps."""

    def __init__(self, run):
        self.run = Path(run)
        directory = json.loads((self.run / 'world-terrain' / 'world-regions.json').read_text(encoding='utf-8'))
        self.regions = directory['regions']
        self.maps = {}

    def map_path(self, name):
        for stage in LEGACY_STAGES:
            p = self.run / stage / name / 'scene.bsp'
            if p.is_file():
                return p, stage
        return None, None

    def owner(self, x, y):
        """The region whose core holds the global point (the map the player stands in)."""
        for r in self.regions:
            ox, oy = r['origin'][0], r['origin'][1]
            (x0, y0), (x1, y1) = r['core']
            if x0 <= x - ox < x1 and y0 <= y - oy < y1:
                return r
        return None

    def regions_touching(self, x0, y0, x1, y1):
        out = []
        for r in self.regions:
            ox, oy = r['origin'][0], r['origin'][1]
            (a0, b0), (a1, b1) = r['core']
            if a0 + ox < x1 and x0 < a1 + ox and b0 + oy < y1 and y0 < b1 + oy:
                out.append(r)
        return out

    def get(self, region):
        name = region['name']
        if name not in self.maps:
            path, stage = self.map_path(name)
            self.maps[name] = (LegacyMap(region, path), stage) if path else (None, None)
        return self.maps[name][0]

    def at(self, x, y):
        r = self.owner(x, y)
        return self.get(r) if r else None


class ChimFrame:
    """One CHIM frame of a run: chunk terrain (global), contents, standing hull, placements."""

    def __init__(self, frame, chunks, textures, models, origin):
        self.frame = frame
        self.origin = (float(origin[0]), float(origin[1]), 0.0)
        self.low = frame['low']
        self.grain = frame['grain']
        self.extent = (self.low[0], self.low[1], self.low[0] + frame['nx'] * self.grain,
                       self.low[1] + frame['ny'] * self.grain)
        self.chunks = {}
        faces = []
        self.placements = []
        tnames = [t['name'] for t in textures]
        mnames = [m['name'] for m in models]
        for c in chunks:
            lumps = bsp_lumps(c['image'])
            refs = struct.unpack_from('<%di' % struct.unpack_from('<i', lumps[2])[0], lumps[2], 4)
            names = [tnames[g] if 0 <= g < len(tnames) else '' for g in refs]
            row = model_row(lumps, 0)
            self.chunks[(c['cx'], c['cy'])] = (lumps, row)
            for pts, name, nv in faces_of(lumps, names, shift=self.origin):
                faces.append((pts, 'liquid' if name.split('|')[-1].startswith('*') else 'ground', nv))
            for r in c['owned']:
                lo, hi = r['box']
                g = [r['origin'][k] + self.origin[k] for k in range(3)]
                self.placements.append((str(r['ref']), mnames[r['model']] if r['model'] < len(mnames) else '',
                                        tuple(g), (tuple(lo[k] + self.origin[k] for k in range(3)),
                                                   tuple(hi[k] + self.origin[k] for k in range(3)))))
        self.ground = Ground(faces)

    def chunk(self, p):
        lx, ly = p[0] - self.origin[0], p[1] - self.origin[1]
        key = (int(math.floor((lx - self.low[0]) / self.grain)), int(math.floor((ly - self.low[1]) / self.grain)))
        return self.chunks.get(key)

    def covers(self, x, y):
        lx, ly = x - self.origin[0], y - self.origin[1]
        return self.extent[0] <= lx < self.extent[2] and self.extent[1] <= ly < self.extent[3]

    def contents(self, p):
        c = self.chunk(p)
        if c is None:
            return None
        return node_contents(c[0], c[1]['headnode'][0], (p[0] - self.origin[0], p[1] - self.origin[1], p[2]))

    def hull(self, p):
        c = self.chunk(p)
        if c is None:
            return SOLID
        return clip_contents(c[0], c[1]['headnode'][1], (p[0] - self.origin[0], p[1] - self.origin[1], p[2]))


# ---------------------------------------------------------------- edges and sampling

def edge_line(core, edge):
    """(along low, along high, line coordinate, axis along, outward sign) of a core edge."""
    (x0, y0), (x1, y1) = core
    return {'N': (x0, x1, y1, 0, 1), 'S': (x0, x1, y0, 0, -1),
            'E': (y0, y1, x1, 1, 1), 'W': (y0, y1, x0, 1, -1)}[edge]


def edge_point(core, edge, t, offset):
    """Local point at along-coordinate t and outward offset from the core edge."""
    lo, hi, line, axis, sign = edge_line(core, edge)
    v = line + sign * offset
    return (t, v) if axis == 0 else (v, t)


def edge_coords(core, edge, x, y):
    """(along t, outward offset) of a local point relative to a core edge."""
    lo, hi, line, axis, sign = edge_line(core, edge)
    t, v = (x, y) if axis == 0 else (y, x)
    return t, sign * (v - line)


def along(core, edge, step=STEP):
    """Sample positions along an edge: every `step` units, centred in each step (never on the
    128-unit tile grid of either side)."""
    lo, hi = edge_line(core, edge)[:2]
    n = int((hi - lo) // step)
    return [lo + step / 2.0 + k * step for k in range(n)]


def cell_of(x, y):
    return (int(math.floor(x / CELL)), int(math.floor(y / CELL)))


def tile_grid_height(height, x, y):
    """Height at (x, y) of the plain tile grid through the tile's four corner heights (triangles
    0-1-2 and 0-2-3, the converter's split and the CHIM chunk terrain's), or None.
    height(x, y) -> z or None is queried at the corners."""
    i, j = math.floor(x / TILE), math.floor(y / TILE)
    z = [height(i * TILE + dx, j * TILE + dy) for dx, dy in ((0, 0), (TILE, 0), (TILE, TILE), (0, TILE))]
    if any(v is None for v in z):
        return None
    u, v = (x - i * TILE) / TILE, (y - j * TILE) / TILE
    if u >= v:
        return z[0] + (z[1] - z[0]) * u + (z[2] - z[1]) * v
    return z[0] + (z[2] - z[3]) * u + (z[3] - z[0]) * v


def refined(height, x, y, tolerance=0.01):
    """(refined, grid height): True when the ground at (x, y) is not the plain tile grid through
    its corners, i.e. the converter inserted samples there (shoreline refinement)."""
    g = tile_grid_height(height, x, y)
    z = height(x, y)
    if g is None or z is None:
        return False, g
    return abs(z - g) > tolerance, g


# ---------------------------------------------------------------- status rules

def judge(value, warn, fail):
    """'ok' | 'warn' | 'fail' of a magnitude against limits (None: not measured -> 'ok')."""
    if value is None:
        return 'ok'
    if fail is not None and value > fail:
        return 'fail'
    if warn is not None and value > warn:
        return 'warn'
    return 'ok'


def worst(statuses):
    order = ('ok', 'warn', 'fail')
    return max(statuses, key=order.index) if statuses else 'ok'


def summary(values):
    vals = [abs(v) for v in values]
    if not vals:
        return {'n': 0, 'max': None, 'mean': None}
    return {'n': len(vals), 'max': round(max(vals), 3), 'mean': round(sum(vals) / len(vals), 3)}


def cell_status(cell, limits=LIMITS):
    """Status of one border cell record and the reasons."""
    reasons = []
    st = []
    h = cell['heights']
    s = judge(h['max'], limits['height_warn'], limits['height_fail'])
    if s != 'ok':
        reasons.append('height delta %.2f > %s' % (h['max'], limits['height_%s' % s]))
    st.append(s)
    for way, a in cell['arrival'].items():
        s = judge(a['max'], limits['arrival_warn'], limits['arrival_fail'])
        if s != 'ok':
            reasons.append('%s arrival delta %.2f > %s' % (way, a['max'], limits['arrival_%s' % s]))
        st.append(s)
    if cell['contents_mismatch']:
        reasons.append('%d contents mismatches' % cell['contents_mismatch'])
        st.append('warn')
    return worst(st), reasons


# ---------------------------------------------------------------- the audit

def load_areas(run, root=None, only=()):
    """CHIM areas of the run that hand over to the legacy world: [(row, settings, frame)]."""
    from chim import validate as V
    import town_config
    run = Path(run)
    world_dir = run / 'chim-world'
    if not (world_dir / 'chim' / 'world.cwi').is_file():
        return [], None
    fails = V.Failures()
    settings, files, sizes, textures, models, frames = V.load_world(world_dir, fails)
    registry = town_config.load_registry(root)
    configs = {r['id']: r['config'] for r in registry['towns']}
    out = []
    for row in town_config.runtime_towns(root):
        if not row['handoff'] or (only and row['id'] not in only):
            continue
        if not (run / ('chim-town-' + row['id'])).is_dir():
            continue
        cfg = json.loads((town_config._root(root) / 'config' / configs[row['id']]).read_text(encoding='utf-8'))
        cell = tuple(cfg['source_cell'])
        match = [f for f in frames if tuple(f[1]['cell']) == cell]
        if not match:
            continue
        _, frame, chunks = match[0]
        out.append((row, cfg, ChimFrame(frame, chunks, textures, models, row['origin'])))
    return out, fails


REGION_DRAW_DISTANCE = 540      # a region frame's fog plane (chim.regions.frame_settings draw_distance)


def load_region_areas(run, cells=None):
    """CHIM region frames of the run (chim-world/chim-regions.json, aw-chim-ownership-1) as audit rows:
    [(row, settings, frame)] for the frames whose cell is in CELLS (None: all), and the rows of ALL region
    frames (an edge between two CHIM frames is a frame neighbour, never a legacy border)."""
    from chim import validate as V
    from chim.regions import TABLE_FILE, read_table
    run = Path(run)
    world_dir = run / 'chim-world'
    table = read_table(world_dir / TABLE_FILE)
    if table is None or not (world_dir / 'chim' / 'world.cwi').is_file():
        return [], []
    rows = [{'id': f['id'], 'origin': [float(v) for v in f['origin']], 'core': f['core'],
             'draw_distance': REGION_DRAW_DISTANCE, 'handoff': True, 'cell': tuple(f['cell'])}
            for f in table['frames']]
    wanted = [r for r in rows if cells is None or r['cell'] in cells]
    if not wanted:
        return [], rows
    fails = V.Failures()
    settings, files, sizes, textures, models, frames = V.load_world(world_dir, fails)
    by_cell = {tuple(f[1]['cell']): f for f in frames}
    out = []
    for row in wanted:
        match = by_cell.get(row['cell'])
        if match is None:
            continue
        _, frame, chunks = match
        out.append((row, {'source_cell': list(row['cell'])}, ChimFrame(frame, chunks, textures, models, row['origin'])))
    return out, rows


def far_layer(run, cell):
    from chim import far
    p = Path(run) / 'chim-world' / 'far' / far.file_name(cell)
    if not p.is_file():
        return None
    head, grid, stamps = far.decode(p.read_bytes())
    return head, grid, stamps, hashlib.sha256(p.read_bytes()).hexdigest()


def audit_area(row, cfg, chim, legacy, others=(), far_data=None, limits=LIMITS, arrival=True):
    origin = row['origin']
    core = row['core']
    ox, oy = origin[0], origin[1]
    draw = row['draw_distance']
    area = {'id': row['id'], 'cell': list(cfg['source_cell']), 'origin': list(origin), 'core': core,
            'frame_extent': list(chim.extent), 'draw_distance': draw, 'edges': {}}
    used = {}

    def legacy_at(x, y):
        m = legacy.at(x, y)
        if m is not None:
            used[m.name] = m
        return m

    def neighbour(x, y):
        for o in others:
            (a0, b0), (a1, b1) = o['core']
            if a0 <= x - o['origin'][0] < a1 and b0 <= y - o['origin'][1] < b1:
                return o['id']
        return None

    worst_samples = []
    for edge in EDGES:
        lo, hi, line, axis, sign = edge_line(core, edge)
        bound = {'N': chim.extent[3], 'S': -chim.extent[1], 'E': chim.extent[2], 'W': -chim.extent[0]}[edge]
        frame_margin = bound - sign * line         # frame edge beyond the core edge
        cells = {}

        def cell_rec(c):
            return cells.setdefault(c, {'cell': list(c), 'heights': [], 'shore': 0, 'dry': [], 'grid': [], 'contents_mismatch': 0,
                                        'contents_n': 0, 'arrival': {w: [] for w in ARRIVAL},
                                        'arrival_unrefined': {w: [] for w in ARRIVAL},
                                        'arrival_unmeasured': {w: 0 for w in ARRIVAL}, 'far': []})
        missing = {'legacy': 0, 'chim': 0}
        neighbours = set()
        for t in along(core, edge):
            ix, iy = edge_point(core, edge, t, -1.0)
            rec = cell_rec(cell_of(ix + ox, iy + oy))
            for off in HEIGHT_OFFSETS:
                if off >= frame_margin:
                    continue
                lx, ly = edge_point(core, edge, t, off)
                gx, gy = lx + ox, ly + oy
                nb = neighbour(gx, gy) if off > 0 else None
                if nb:
                    neighbours.add(nb)
                    continue
                m = legacy_at(gx, gy)
                gl = m.ground.height(gx, gy)[0] if m else None
                gc = chim.ground.height(gx, gy)[0]
                if gl is None:
                    missing['legacy'] += 1
                if gc is None:
                    missing['chim'] += 1
                if gl is None or gc is None:
                    continue
                d = gc - gl
                shore, grid_l = refined(lambda x, y: m.ground.height(x, y)[0], gx, gy)
                rec['heights'].append(d)
                if grid_l is not None:
                    rec['grid'].append(gc - grid_l)
                if shore:
                    rec['shore'] += 1
                else:
                    rec['dry'].append(d)
                worst_samples.append((abs(d), edge, off, round(gx, 2), round(gy, 2), round(gl, 3), round(gc, 3), shore))
                z = max(gl, gc) + 1.0
                cl, cc = m.contents((gx, gy, z)), chim.contents((gx, gy, z))
                if cl is not None and cc is not None:
                    rec['contents_n'] += 1
                    if (cl == SOLID) != (cc == SOLID) or (cl in (WATER, -4, -5)) != (cc in (WATER, -4, -5)):
                        rec['contents_mismatch'] += 1
            if arrival:
                for way, off in ARRIVAL.items():
                    lx, ly = edge_point(core, edge, t, off)
                    gx, gy = lx + ox, ly + oy
                    m = legacy_at(gx, gy)
                    gl = m.ground.height(gx, gy)[0] if m else None
                    gc = chim.ground.height(gx, gy)[0]
                    if m is None or gl is None or gc is None:
                        rec['arrival_unmeasured'][way] += 1
                        continue
                    sl = standing(m.hull, gx, gy, gl)
                    sc = standing(chim.hull, gx, gy, gc)
                    if sl is None or sc is None:
                        rec['arrival_unmeasured'][way] += 1
                        continue
                    rec['arrival'][way].append(sc - sl)
                    if not refined(lambda x, y: m.ground.height(x, y)[0], gx, gy)[0]:
                        rec['arrival_unrefined'][way].append(sc - sl)
        far_rec = None
        if far_data is not None:
            head, grid, stamps, _ = far_data
            x0, y0 = head['origin']
            step = head['step']
            sc = head['scale']
            steps = []
            for j in range(grid.shape[0]):
                for i in range(grid.shape[1]):
                    gx, gy = (x0 + i * step) * sc, (y0 + j * step) * sc
                    t, off = edge_coords(core, edge, gx - ox, gy - oy)
                    if not (0 <= off <= BAND and lo - BAND <= t <= hi + BAND):
                        continue
                    if neighbour(gx, gy):
                        continue
                    m = legacy_at(gx, gy)
                    gl = m.ground.height(gx, gy)[0] if m else None
                    if gl is None:
                        continue
                    d = float(grid[j, i]) - max(gl, WATER_LEVEL)
                    steps.append(d)
                    ex, ey = edge_point(core, edge, min(max(t, lo + 0.5), hi - 0.5), -1.0)
                    cell_rec(cell_of(ex + ox, ey + oy))['far'].append(d)
            far_rec = dict(summary(steps), stamps=len(stamps), step_local=step * sc)
        gap_enter = max(0.0, draw - frame_margin)
        gap_leave = max(0.0, draw - (frame_margin - ARRIVAL['leave']))
        out_cells = []
        for c in sorted(cells):
            r = cells[c]
            rec = {'cell': r['cell'], 'heights': summary(r['heights']), 'shoreline_samples': r['shore'],
                   'heights_unrefined': summary(r['dry']), 'chim_vs_legacy_grid': summary(r['grid']),
                   'contents_samples': r['contents_n'], 'contents_mismatch': r['contents_mismatch'],
                   'arrival': {w: dict(summary(r['arrival'][w]), not_measured=r['arrival_unmeasured'][w])
                               for w in ARRIVAL},
                   'arrival_unrefined': {w: summary(r['arrival_unrefined'][w]) for w in ARRIVAL},
                   'far_step': summary(r['far'])}
            rec['status'], rec['reasons'] = cell_status(rec, limits)
            out_cells.append(rec)
        all_h = [v for r in cells.values() for v in r['heights']]
        all_dry = [v for r in cells.values() for v in r['dry']]
        all_grid = [v for r in cells.values() for v in r['grid']]
        e = {'line': line, 'along': [lo, hi], 'samples_along': len(along(core, edge)), 'offsets': [
                o for o in HEIGHT_OFFSETS if o < frame_margin],
             'heights': summary(all_h), 'heights_unrefined': summary(all_dry),
             'chim_vs_legacy_grid': summary(all_grid),
             'shoreline_samples': sum(r['shore'] for r in cells.values()),
             'missing': missing, 'frame_neighbours': sorted(neighbours),
             'arrival': {w: dict(summary([v for r in cells.values() for v in r['arrival'][w]]),
                                 not_measured=sum(r['arrival_unmeasured'][w] for r in cells.values()))
                         for w in ARRIVAL} if arrival else 'not measured',
             'arrival_unrefined': {w: summary([v for r in cells.values() for v in r['arrival_unrefined'][w]])
                                   for w in ARRIVAL} if arrival else 'not measured',
             'contents_mismatch': sum(r['contents_mismatch'] for r in cells.values()),
             'far': far_rec if far_rec is not None else 'not measured',
             'far_band_gap': {'frame_edge_beyond_core': frame_margin, 'fog_distance': draw,
                              'gap_at_enter': gap_enter, 'gap_at_leave': gap_leave,
                              'status': 'warn' if gap_leave > 0 else 'ok'},
             'cells': out_cells}
        e['objects'] = edge_objects(core, edge, origin, chim, legacy, frame_margin)
        e['status'] = worst([c['status'] for c in out_cells] + [e['far_band_gap']['status']])
        area['edges'][edge] = e
    area['objects'] = area_objects(core, origin, chim, legacy)
    worst_samples.sort(reverse=True)
    area['worst_samples'] = [dict(zip(('abs', 'edge', 'offset', 'x', 'y', 'legacy', 'chim', 'shoreline'), s))
                             for s in worst_samples[:25]]
    area['legacy_maps'] = {n: {'sha256': m.sha256, 'stage': legacy.maps[n][1]} for n, m in sorted(used.items())}
    area['status'] = worst([e['status'] for e in area['edges'].values()])
    return area


def edge_objects(core, edge, origin, chim, legacy, frame_margin):
    """Objects whose drawn box crosses the band of one edge, per side, matched by source reference."""
    lo, hi, line, axis, sign = edge_line(core, edge)
    ox, oy = origin[0], origin[1]

    def span(box):
        (x0, y0, _), (x1, y1, _) = box
        a, b = edge_coords(core, edge, x0 - ox, y0 - oy), edge_coords(core, edge, x1 - ox, y1 - oy)
        return (min(a[0], b[0]), max(a[0], b[0])), (min(a[1], b[1]), max(a[1], b[1]))

    def in_band(box):
        (t0, t1), (o0, o1) = span(box)
        return t1 >= lo and t0 <= hi and o1 >= -BAND and o0 <= BAND

    # legacy: every region whose core meets the band (overlaps repeat objects: one per reference)
    corners = [edge_point(core, edge, lo, -BAND), edge_point(core, edge, hi, BAND)]
    bx0, by0 = min(c[0] for c in corners) + ox, min(c[1] for c in corners) + oy
    bx1, by1 = max(c[0] for c in corners) + ox, max(c[1] for c in corners) + oy
    leg = {}
    for r in legacy.regions_touching(bx0 - 1024, by0 - 1024, bx1 + 1024, by1 + 1024):
        m = legacy.get(r)
        if m is None:
            continue
        for ref, model, o, box in m.objects():
            if ref not in leg and in_band(box):
                leg[ref] = (model, o, box)
    chm = {}
    for ref, model, o, box in chim.placements:
        if in_band(box):
            chm.setdefault(ref, (model, o, box))

    def row(ref, item):
        model, o, box = item
        (t0, t1), (o0, o1) = span(box)
        return {'ref': ref, 'model': model, 'origin': [round(v, 2) for v in o],
                'offset': [round(o0, 1), round(o1, 1)], 'cell': list(cell_of(o[0], o[1]))}
    both = sorted(set(leg) & set(chm))
    moved = []
    for ref in both:
        d = math.dist(leg[ref][1], chm[ref][1])
        if d > 2.0:
            moved.append(dict(row(ref, chm[ref]), legacy_origin=[round(v, 2) for v in leg[ref][1]], distance=round(d, 2)))
    legacy_only = [row(r, leg[r]) for r in sorted(set(leg) - set(chm))]
    chim_only = [row(r, chm[r]) for r in sorted(set(chm) - set(leg))]
    cut_core = [dict(row(r, leg[r]), side='legacy') for r in sorted(leg) if span(leg[r][2])[1][0] < 0 < span(leg[r][2])[1][1]]
    cut_core += [dict(row(r, chm[r]), side='chim') for r in sorted(chm) if span(chm[r][2])[1][0] < 0 < span(chm[r][2])[1][1]]
    cut_frame = [row(r, chm[r]) for r in sorted(chm) if span(chm[r][2])[1][1] > frame_margin]
    return {'legacy': len(leg), 'chim': len(chm), 'both': len(both),
            'legacy_only_inside_core': sum(1 for r in legacy_only if r['offset'][1] < 0),
            'chim_only_inside_core': sum(1 for r in chim_only if r['offset'][1] < 0),
            'moved': moved, 'legacy_only': legacy_only, 'chim_only': chim_only,
            'cut_by_handover_line': cut_core, 'cut_by_frame_edge': cut_frame}


def model_class(model):
    """Coarse class of a model name for the census: its folder and stem without variant suffixes."""
    base = model.split('@')[0].split('|')[0]
    return base.rsplit('_', 1)[0] if base[-2:].isdigit() else base


def area_objects(core, origin, chim, legacy):
    """Whole-core census: CHIM placements inside the core with and without a legacy counterpart
    (a legacy region map drawing the same source reference). The ones without are not seen from
    the legacy side and appear at the handover (pop-in)."""
    (x0, y0), (x1, y1) = core
    ox, oy = origin[0], origin[1]
    refs = set()
    for r in legacy.regions_touching(x0 + ox - 1024, y0 + oy - 1024, x1 + ox + 1024, y1 + oy + 1024):
        m = legacy.get(r)
        if m is not None:
            refs.update(ref for ref, _, _, _ in m.objects())
    inside = [p for p in chim.placements if x0 <= p[2][0] - ox < x1 and y0 <= p[2][1] - oy < y1]
    missing = [p for p in inside if p[0] not in refs]
    classes = {}
    for ref, model, o, box in missing:
        k = model_class(model)
        c = classes.setdefault(k, {'count': 0, 'max_height': 0.0})
        c['count'] += 1
        c['max_height'] = round(max(c['max_height'], box[1][2] - box[0][2]), 1)
    return {'chim_inside_core': len(inside), 'drawn_by_legacy': len(inside) - len(missing),
            'chim_only': len(missing),
            'chim_only_by_class': dict(sorted(classes.items(), key=lambda kv: -kv[1]['count']))}


def _run_version():
    """The report's source_version: provenance only (project_version.run_version keys no stage)."""
    from project_version import run_version
    try:
        return run_version(ROOT)
    except (OSError, ValueError):
        return None


def run_identity(run):
    run = Path(run)
    out = {'name': run.name}
    for name in ('build-state.json', 'build-summary.json'):
        p = run / name
        if p.is_file():
            try:
                d = json.loads(p.read_text(encoding='utf-8'))
            except ValueError:
                continue
            for k in ('status', 'commit', 'git', 'source_commit', 'version'):
                if k in d and k not in out and isinstance(d[k], (str, int, float)):
                    out[k] = d[k]
    return out


def audit(run, areas=(), root=None, arrival=True, limits=LIMITS, regions=None):
    """regions: None (no region frames), 'all', or a set of cells (x, y) of CHIM region frames to audit."""
    run = Path(run)
    found, fails = load_areas(run, root, tuple(areas)) if (areas or regions is None) else ([], None)
    region_rows = []
    if regions is not None:
        more, region_rows = load_region_areas(run, None if regions == 'all' else set(regions))
        found = list(found) + more
    legacy = Legacy(run)
    others = [r for r, _, _ in found] + [r for r in region_rows if r['id'] not in {o['id'] for o, _, _ in found}]
    report = {'format': FORMAT, 'generated': time.strftime('%Y-%m-%d %H:%M %z'), 'run': run_identity(run),
              'source_version': _run_version(),
              'limits': limits,
              'sampling': {'step': STEP, 'band': BAND, 'height_offsets': list(HEIGHT_OFFSETS),
                           'arrival_offsets': ARRIVAL, 'tile': TILE, 'water_level': WATER_LEVEL,
                           'legacy_stages': list(LEGACY_STAGES)},
              'world_checks': list(fails or []), 'areas': []}
    for i, (row, cfg, chim) in enumerate(found, 1):
        far_data = far_layer(run, tuple(cfg['source_cell']))
        a = audit_area(row, cfg, chim, legacy, [o for o in others if o['id'] != row['id']], far_data, limits,
                       arrival)
        a['far_sha256'] = far_data[3] if far_data else None
        report['areas'].append(a)
        print('[%d/%d] stitch audit: %s %s' % (i, len(found), a['id'], a['status']), file=sys.stderr, flush=True)
    report['status'] = worst([a['status'] for a in report['areas']]) if report['areas'] else 'ok'
    return report


def print_summary(report, out=sys.stdout):
    for a in report['areas']:
        print('%s  %s' % (a['id'], a['status']), file=out)
        for name, e in a['edges'].items():
            arr = e['arrival']
            arr_s = 'not measured' if isinstance(arr, str) else ' '.join(
                '%s max %s (%d unmeasured)' % (w, v['max'], v['not_measured']) for w, v in arr.items())
            far = e['far']
            far_s = 'not measured' if isinstance(far, str) else 'max %s mean %s' % (far['max'], far['mean'])
            print('  %s %-4s heights max %s mean %s (unrefined max %s, %d refined/shoreline) | arrival %s | far %s | gap %s '
                  '| objects legacy %d chim %d both %d' % (
                      name, e['status'], e['heights']['max'], e['heights']['mean'], e['heights_unrefined']['max'],
                      e['shoreline_samples'], arr_s, far_s, e['far_band_gap']['gap_at_leave'],
                      e['objects']['legacy'], e['objects']['chim'], e['objects']['both']), file=out)
    if not report['areas']:
        print('no CHIM area with a world handoff in this run', file=out)
    else:
        statuses = [a['status'] for a in report['areas']]
        print('%d areas: %s' % (len(statuses), ', '.join('%d %s' % (statuses.count(s), s)
                                                       for s in sorted(set(statuses)))), file=out)


def main(argv=None):
    ap = argparse.ArgumentParser(description='CHIM/legacy border audit (read only).')
    sub = ap.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('audit', help='measure every CHIM area border of a build run')
    a.add_argument('--run', required=True, help='build run folder')
    a.add_argument('--area', action='append', default=[], help='town id (repeatable; default: all)')
    a.add_argument('--out', help='write the aw-stitch-report-1 JSON here')
    a.add_argument('--no-arrival', action='store_true', help='skip the standing hull traces')
    a.add_argument('--regions', action='append', default=[],
                   help='CHIM region frames to audit: all, or cells X,Y (repeatable); without it only town areas')
    args = ap.parse_args(argv)
    regions = None
    if args.regions:
        from chim.regions import parse_cell
        regions = 'all' if 'all' in args.regions else {parse_cell(v) for v in args.regions}
    report = audit(args.run, args.area, arrival=not args.no_arrival, regions=regions)
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8', newline='\n')
    print_summary(report)
    return 0


if __name__ == '__main__':
    sys.exit(main())
