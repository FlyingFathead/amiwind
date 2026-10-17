# SPDX-License-Identifier: GPL-3.0-only
"""A CHIM frame's standing hull as one audit_walkability.Scene, for offline collision checks.

The engine collides a frame's chunk terrain (each chunk's standing hull under
the frame grid) and every placement (its model's standing hull, moved by the
record's origin and yaw, as SV_ClipMoveToEntity traces a brush entity). Here
the hull clipnodes and planes of every chunk image and of every model the
frame places are relocated into one plane and node list, and each chunk and
placement becomes one brush of an audit_walkability.Scene: the same trace the
legacy walkability and stair gates use on a region map (no second tracer).
"""
from pathlib import Path
import struct

from audit_walkability import Scene, axes
from chim.cut import source_ref  # noqa: E402
from chim import format as F
from player_hull import MINS, MAXS

HULL_ROOT = 10                  # dmodel field: head node 1, the standing hull


class FrameScene(Scene):
    """Standing-hull scene of one frame (chunks and placements), traced like a region map."""

    def __init__(self, world, frame_index=0, hull=1):
        if hull not in (0, 1):
            raise ValueError('Expected the point (0) or standing (1) hull')
        path, frame, chunks = world['frames'][frame_index]
        self.sha256 = 'chim:' + path
        self.hull = hull
        self.planes, self.nodes, self.brushes, self.boxes = [], [], [], []
        self.chunk_roots = {}
        images = {}

        def add_image(key, image):
            if key in images:
                return images[key]
            lumps = F.read_brush_image(image)
            plane_base, node_base = len(self.planes), len(self.nodes)
            self.planes += list(struct.iter_unpack('<4fi', lumps[1]))
            if hull == 1:
                # clipnodes: children are node indices or contents (-1 empty, -2 solid ...)
                for p, front, back in struct.iter_unpack('<iHH', lumps[9]):
                    self.nodes.append((p + plane_base,
                                       *(c - 65536 if c >= 0xFFF0 else c + node_base for c in (front, back))))
            else:
                # the node tree (hull 0, SV_HullForEntity's point hull): a negative child is a
                # leaf, whose contents end the walk (audit_walkability.Scene hull 0)
                leaves = [r[0] for r in struct.iter_unpack('<ii6h2H4B', lumps[10])]
                for p, front, back, *_ in struct.iter_unpack('<i2h6h2H', lumps[5]):
                    self.nodes.append((p + plane_base,
                                       *(c + node_base if c >= 0 else leaves[-c - 1] for c in (front, back))))
            root = struct.unpack_from('<9f7i', lumps[14])[HULL_ROOT - 1 + hull]
            images[key] = root + node_base if root >= 0 else root
            return images[key]
        margin = (abs(MINS[0]) + 2, abs(MINS[1]) + 2, abs(MINS[2]) + 2)
        g, (lx, ly) = frame['grain'], frame['low']
        for c in chunks:
            cell = (c['cx'], c['cy'])
            root = add_image(('chunk', cell), c['image'])
            self.chunk_roots[cell] = root
            x0, y0 = lx + cell[0] * g, ly + cell[1] * g
            self.brushes.append((root, (0., 0., 0.), axes((0., 0., 0.)), 'chunk %d,%d' % cell))
            self.boxes.append((x0 - margin[0], y0 - margin[1], -1e9, x0 + g + margin[0], y0 + g + margin[1], 1e9))
        for c in chunks:
            for r in c['owned']:
                root = add_image(('model', r['model']), world['models'][r['model']]['image'])
                # the source reference: a cut placement's pieces are one object (chim.cut)
                self.brushes.append((root, tuple(r['origin']), axes((0., r['yaw'], 0.)), source_ref(r['ref'])))
                lo, hi = r['box']
                self.boxes.append(tuple(lo[k] - margin[k] for k in range(3)) +
                                  tuple(hi[k] + margin[k] for k in range(3)))
        self.frame = frame
        self.span = (frame['nx'], frame['ny'])

    def contents(self, p):
        """World contents at a frame-local point as SV_PointContents reads them (the world only:
        the chunk holding the point; placed models are entities): -1 empty, -2 solid, -3 water.
        Meant for a point-hull scene (hull=0)."""
        g, (lx, ly) = self.frame['grain'], self.frame['low']
        cell = (min(self.span[0] - 1, max(0, int((p[0] - lx) // g))),
                min(self.span[1] - 1, max(0, int((p[1] - ly) // g))))
        node = self.chunk_roots.get(cell, -2)
        guard = 0
        while node >= 0:
            plane, front, back = self.nodes[node]
            n = self.planes[plane]
            node = front if p[0] * n[0] + p[1] * n[1] + p[2] * n[2] - n[3] >= 0 else back
            guard += 1
            if guard > 4096:
                raise ValueError('Cyclic node tree')
        return node

    GRID = 128.0       # spatial index cell (CHIM-STAIRGATE-SLOW-33): a trace tests only nearby brushes

    def _index(self):
        grid = {}
        g = self.GRID
        for i, box in enumerate(self.boxes):
            for gx in range(int(box[0] // g), int(box[3] // g) + 1):
                for gy in range(int(box[1] // g), int(box[4] // g) + 1):
                    grid.setdefault((gx, gy), []).append(i)
        self._grid = grid
        return grid

    def _trace_brushes(self, start, end):
        grid = getattr(self, '_grid', None) or self._index()
        g = self.GRID
        x0, x1 = min(start[0], end[0]), max(start[0], end[0])
        y0, y1 = min(start[1], end[1]), max(start[1], end[1])
        cells = [(gx, gy) for gx in range(int(x0 // g), int(x1 // g) + 1) for gy in range(int(y0 // g), int(y1 // g) + 1)]
        if len(cells) > 64:            # a long trace: the plain scan is as fast
            candidates = range(len(self.brushes))
        else:
            candidates = sorted({i for c in cells for i in grid.get(c, ())})   # the scan's order: same result
        for i in candidates:
            box = self.boxes[i]
            if all(max(start[k], end[k]) >= box[k] and min(start[k], end[k]) <= box[k + 3] for k in range(3)):
                yield self.brushes[i]


def frame_polys(world, frame_index=0):
    """World-space polygons of a frame as the stair gate reads a region map (stair_walk._faces):
    [(points, ref)], the chunks' terrain as 'world', each placement's model faces moved by its
    origin and yaw, by reference number; vertices in the faces' own order (their winding)."""
    from chim.validate import face_polygons
    _, _, chunks = world['frames'][frame_index]
    out = []
    for c in chunks:
        for pts, _, _, _ in face_polygons(F.read_brush_image(c['image'])):
            out.append(([tuple(float(v) for v in p) for p in pts], 'world'))
    faces = {}
    for c in chunks:
        for r in c['owned']:
            if r['model'] not in faces:
                faces[r['model']] = face_polygons(F.read_brush_image(world['models'][r['model']]['image']))
            origin, basis = r['origin'], axes((0., r['yaw'], 0.))
            for pts, _, _, _ in faces[r['model']]:
                out.append(([tuple(origin[i] + x * basis[0][i] + y * basis[1][i] + z * basis[2][i] for i in range(3))
                             for x, y, z in pts], source_ref(r['ref'])))
    return out


def stand_height(scene, x, y, top=4096.0):
    """Standing origin z at (x, y): where a box dropped from `top` comes to rest, or None."""
    hit = scene.trace((x, y, top), (x, y, -4096.0))
    if not hit:
        return None
    return top + (-4096.0 - top) * hit['fraction']


# ---------------------------------------------------------------- the stair gate on a frame

STAIR_TILE = 1024.0     # frame-local units per gate task (a core, as a region map's core)
STAIR_MARGIN = 128.0    # geometry kept around a core: the walk's reach, the box and a ramp's far edge
_STAIR_CACHE = {}
_STAIR_CACHE_FRAMES = 4  # frames a worker keeps built: largest-first tasks of a few frames interleave


def _stair_frame(out, frame_index):
    """Per worker process: the frame's scenes and polygons, built from the frame's own files
    (chim.validate.load_frame) and kept for the next cores of the same frame. Reading the whole
    world here (load_world, 8.9 s for 273 frames) for every frame a worker switched to cost most of
    the dev3 stair walk (CHIM-STAIR-GATE-WORLD-RELOAD-36)."""
    key = (str(out), frame_index)
    if key not in _STAIR_CACHE:
        from chim.validate import load_frame
        row, models = load_frame(out, frame_index)
        world = {'frames': {frame_index: row}, 'models': models}
        while len(_STAIR_CACHE) >= _STAIR_CACHE_FRAMES:
            _STAIR_CACHE.pop(next(iter(_STAIR_CACHE)))
        _STAIR_CACHE[key] = (row[0], FrameScene(world, frame_index),
                             FrameScene(world, frame_index, hull=0), frame_polys(world, frame_index))
    return _STAIR_CACHE[key]


def _poly_box(pts):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def stair_polys(polys, core):
    """(near, wide) polygons of a frame for one core: near (the core plus STAIR_MARGIN) is the geometry the walk
    reads; wide adds stair_walk.FLIGHT_MARGIN, the steps around the core that mark the flights crossing its edge
    (STAIR-FLIGHT-CORE-SPLIT-41). POLYS: [(points, ref)] or [(points, ref, box)]."""
    from stair_walk import FLIGHT_MARGIN
    near, wide = [], []
    m, w = STAIR_MARGIN, STAIR_MARGIN + FLIGHT_MARGIN
    for poly in polys:
        pts, ref = poly[0], poly[1]
        b = poly[2] if len(poly) > 2 else _poly_box(pts)
        if b[2] >= core[0] - w and b[0] <= core[2] + w and b[3] >= core[1] - w and b[1] <= core[3] + w:
            wide.append((pts, ref))
            if b[2] >= core[0] - m and b[0] <= core[2] + m and b[3] >= core[1] - m and b[1] <= core[3] + m:
                near.append((pts, ref))
    return near, wide


def stair_task(task):
    """Worker: the shared stair gate (stair_walk._check_items on stair_walk.candidates, as check_polys) on one core
    of a frame, with the frame's own collision (standing hull), contents and point hull."""
    from stair_walk import _check_items, candidates
    out, frame_index, core = task
    path, scene, points, polys = _stair_frame(out, frame_index)
    near, wide = stair_polys(polys, core)
    rows = _check_items(candidates(wide, core), near, scene, points.contents, points)
    for row in rows:
        row['map'] = path
    return rows


def in_walk_area(area, point):
    """Is a step's riser point in a frame's walk area (x0, y0, x1, y1; half-open, as a core)? The point is taken
    rounded as its row stores it (3 decimals), so a walk restricted to the area and the rows of a whole-frame walk
    filtered by it keep exactly the same steps (stair_gate derives one from the other)."""
    x, y = round(float(point[0]), 3), round(float(point[1]), 3)
    return area[0] <= x < area[2] and area[1] <= y < area[3]


def stair_task_in(task):
    """Worker: stair_task restricted to a frame's walk area, (out, frame index, core, area) -> rows. The core's
    steps and ramps are found and their flights marked on the whole core, exactly as stair_task does; only those
    whose riser point lies in the area are walked (in_walk_area). So every row is the row stair_task gives for the
    same step, in the same order, and a flight that crosses the area's edge keeps its flight mark
    (BUILD-STAIR-WALK-BORDER-COPIES-41)."""
    from stair_walk import _check_items, candidates
    out, frame_index, core, area = task
    path, scene, points, polys = _stair_frame(out, frame_index)
    near, wide = stair_polys(polys, core)
    items = [item for item in candidates(wide, core) if in_walk_area(area, item['point'])]
    rows = _check_items(items, near, scene, points.contents, points)
    for row in rows:
        row['map'] = path
    return rows


def stair_tasks(out, frames, areas=None):
    """(out, frame index, core) for every core tile of every frame; the cores tile each frame
    exactly, so every step is tested once (in the core holding its riser point). AREAS ({frame index:
    walk area}, frame_walk_areas): a frame with an area gets (out, frame index, core, area) tasks for the cores
    that meet its area only; a core outside it has no step to walk there."""
    tasks = []
    areas = areas or {}
    for fi, (path, frame, _) in enumerate(frames):
        g, (lx, ly) = frame['grain'], frame['low']
        hx, hy = lx + frame['nx'] * g, ly + frame['ny'] * g
        area = areas.get(fi)
        y = ly
        while y < hy:
            x = lx
            while x < hx:
                # the outermost cores run to infinity: nothing outside the frame is skipped
                core = (x if x > lx else -1e9, y if y > ly else -1e9,
                        x + STAIR_TILE if x + STAIR_TILE < hx else 1e9,
                        y + STAIR_TILE if y + STAIR_TILE < hy else 1e9)
                if area is None:
                    tasks.append((str(out), fi, core))
                elif core[0] < area[2] and area[0] < core[2] and core[1] < area[3] and area[1] < core[3]:
                    tasks.append((str(out), fi, core, area))
                x += STAIR_TILE
            y += STAIR_TILE
    return tasks


def walk_area_mode():
    """AMIWIND_STAIR_WALK_AREA (tools/build.py --stair-walk-area): 'owned' (default): a CHIM region frame walks the
    flights of the cell it owns plus the engine's map-switch margin (frame_walk_areas); 'frame': every flight of
    the frame's map, its border copies of the neighbouring cells included (the method before v0.0.42)."""
    import os
    value = os.environ.get('AMIWIND_STAIR_WALK_AREA', '') or 'owned'
    if value not in ('owned', 'frame'):
        raise ValueError('AMIWIND_STAIR_WALK_AREA must be owned or frame, not %r' % value)
    return value


def frame_walk_areas(out, frames, mode=None):
    """({frame index: (x0, y0, x1, y1)}, note) in frame-local units: the part of each CHIM region frame a player can
    stand in while the frame's map is loaded, where its stair walk walks (BUILD-STAIR-WALK-BORDER-COPIES-41). From
    the build's ownership table OUT/chim-regions.json (aw-chim-ownership-1): the cell the frame owns ('core') plus
    'leave_margin' (the engine keeps an open-world map loaded until the player is that far past its core:
    aw_world.c AW_WorldDestination) plus the standing box's half width (the box reaches a riser that far ahead of
    its origin). Everything farther out is a border copy: walked in the frame that owns it, or for a classic cell
    in that map's own stair walk. Frames without a row (a town's frame: the player walks all of it) keep the
    whole-frame walk. Mode 'frame' (walk_area_mode) or no table: {} (every frame walked whole)."""
    import json
    mode = walk_area_mode() if mode is None else mode
    table_path = Path(out) / 'chim-regions.json'
    if mode == 'frame':
        return {}, 'every frame walked whole (stair walk area: frame)'
    if not table_path.is_file():
        return {}, 'every frame walked whole (no region ownership table %s)' % table_path.name
    try:
        table = json.loads(table_path.read_text(encoding='utf-8'))
        if table.get('format') != 'aw-chim-ownership-1':
            raise ValueError('format %r' % table.get('format'))
        margin = float(table['leave_margin']) + float(MAXS[0])
        rows = {tuple(int(v) for v in f['cell']): f for f in table['frames']}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ValueError('Stair gate: the region ownership table %s does not read (%s)' % (table_path, exc))
    areas = {}
    for fi, (path, frame, _) in enumerate(frames):
        row = rows.get(tuple(int(v) for v in frame['cell']))
        if row is None:
            continue
        origin = row.get('origin') or ()
        if len(origin) < 2 or any(abs(4.0 * float(origin[k]) - float(frame['centre'][k])) > 0.5 for k in range(2)):
            raise ValueError('Stair gate: frame %s (cell %s) is not placed where the ownership table %s puts it '
                             '(origin %s, frame centre %s)' % (path, list(frame['cell']), table_path.name, origin,
                                                              list(frame['centre'])))
        (cx0, cy0), (cx1, cy1) = row['core']
        areas[fi] = (float(cx0) - margin, float(cy0) - margin, float(cx1) + margin, float(cy1) + margin)
    return areas, ('%d of %d frames walk the cell they own plus %g units (map-switch margin %g + box %g); %d walked '
                   'whole' % (len(areas), len(frames), margin, float(table['leave_margin']), float(MAXS[0]),
                              len(frames) - len(areas)))


# What a frame's stair walk reads, and nothing else (BUILD-CHIM-STAIR-WALK-UNCACHED-36, persisting): the walk
# (FrameScene, frame_polys, stair_task) reads a brush image's planes, vertexes, nodes, texinfo, faces, clipnodes,
# leafs, edges, surfedges and models lumps; never its entities, textures, visibility, lighting or marksurfaces.
# The textures lump holds the world's texture table entries, so a new frame anywhere in the world changed it in
# every chunk; model numbers and placement ids are world-global numbering. Keyed by those, 220 of the 237 frames
# the dev5 and coast2 worlds share were walked again although their collision was byte-identical.
STAIR_KEY_FORM = 'chim-stair-key-2'
STAIR_WALK_LUMPS = (1, 3, 5, 6, 7, 9, 10, 12, 13, 14)
STAIR_FRAME_FIELDS = ('grain', 'low', 'nx', 'ny')            # what stair_tasks and FrameScene read of a frame
STAIR_PLACEMENT_FIELDS = ('ref', 'origin', 'yaw', 'box')    # what FrameScene and frame_polys read of a placement


def brush_walk_digest(image):
    """SHA-256 of the lumps of a brush image the stair walk reads (STAIR_WALK_LUMPS), each with its number and
    length: a change to any of them changes the digest, a change to the others does not."""
    import hashlib
    lumps = F.read_brush_image(image)
    h = hashlib.sha256(STAIR_KEY_FORM.encode())
    for k in STAIR_WALK_LUMPS:
        h.update(struct.pack('<ii', k, len(lumps[k])))
        h.update(lumps[k])
    return h.hexdigest()


def frame_stair_parts(frame_row, models):
    """[(name, SHA-256)] of everything one frame's stair walk reads, in walk order: the frame's path (the rows
    name it), the tile and the frame grid; per chunk its place and the walk lumps of its terrain image, and its
    owned placements in order (reference, origin, yaw, box and the walk lumps of the placed model's image: by
    content, never by the world's model number). Reach records are not read by the walk (FrameScene and
    frame_polys place a chunk's owned records only)."""
    import hashlib
    import json

    def sha(value):
        return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()
    path, frame, chunks = frame_row
    parts = [('frame', sha([path, STAIR_TILE, [frame.get(k) for k in STAIR_FRAME_FIELDS]]))]
    digests = {}

    def model(m):
        if m not in digests:
            known = (0 <= m < len(models)) if isinstance(models, (list, tuple)) else (m in models)
            digests[m] = brush_walk_digest(models[m]['image']) if known else 'missing'
        return digests[m]
    for c in chunks:
        cell = '%s,%s' % (c.get('cx'), c.get('cy'))
        parts.append(('chunk %s terrain' % cell, sha([c.get('cx'), c.get('cy'), brush_walk_digest(c['image'])])))
        parts.append(('chunk %s placements' % cell,
                      sha([[[r.get(k) for k in STAIR_PLACEMENT_FIELDS], model(r['model'])] for r in c['owned']])))
    return parts


def _parts_key(parts):
    import hashlib
    import json
    return hashlib.sha256(json.dumps([STAIR_KEY_FORM, parts]).encode()).hexdigest()


def frame_stair_key(frame_row, models):
    """SHA-256 of everything a frame's stair walk reads (frame_stair_parts, key form STAIR_KEY_FORM). The walk's
    own code and the stair rule are the pass cache's key (pass_cache.PassCache: stair_key_sources, options)."""
    return _parts_key(frame_stair_parts(frame_row, models))


# The walker's code in a frame walk's key (BUILD-STAIR-PASS-NOT-KEPT-41): the frame worker stair_task and the code
# of it that a walk runs, in these files only: the stair rule and the walk (stair_walk.py), the frame's scene, its
# polygons and its trace (this module, audit_walkability.py, player_hull.py), and the frame reader (chim/validate.py
# load_frame and face_polygons, chim/format.py, chim/cut.py, chim/__init__.py's format numbers). Inside these files
# only the units stair_task reaches count (build_cache.SourceIndex scope 'units'). Everything else the reach finds
# is left out: chim/validate.py imports chim.terrain at import time, and that import chain names the collision
# compilers (chim/models.py, prepare_mesh_bsp.py, routed_hull.py, scenery_reduce.py, collision_bsp.py ...), the
# CHIM_VERSION label and two town configs. No walk runs any of them; what the compilers made is in the key already,
# as the frame's collision lumps (frame_stair_parts, STAIR_WALK_LUMPS). Before this form an edit to any of them
# rekeyed every frame: v0.0.41-dev5 walked 604 unchanged frames again because CHIM_VERSION went 0.2.0 -> 0.2.1.
# tests/test_chim_stair_pass.py holds the list to the code a walk runs: a traced walk calls nothing outside it, and
# no reached function of these files imports or names a repository module outside it.
# STAIR_CODE_FORM names this key form; records written under the earlier form (the whole reach of stair_task,
# chim-stair-key-2 parts) are not found under it, so nothing is reused across the change without being walked.
STAIR_CODE_FORM = 'chim-stair-code-1'
STAIR_WALK_CODE = ('tools/stair_walk.py', 'tools/chim/collision.py', 'tools/audit_walkability.py',
                   'tools/player_hull.py', 'tools/chim/validate.py', 'tools/chim/format.py', 'tools/chim/cut.py',
                   'tools/chim/__init__.py')
_WALKER_SOURCES = {}


def stair_code_selection(entry='stair_task'):
    """({repository path: SHA-256 of its reached units}, uncertain) of the walker's code (STAIR_WALK_CODE, the
    units ENTRY reaches in those files: stair_task, or stair_task_in for a walk restricted to a walk area).
    uncertain: the reach could not be followed (a file that does not parse); then every repository file counts, as
    in every other pass key."""
    from build_cache import SourceIndex
    from pass_cache import PASS_KEY_FORM, PASS_KEY_NEUTRAL, ROOT
    index = SourceIndex(ROOT, top_format=PASS_KEY_FORM)
    script = Path(__file__).resolve()
    _, _, uncertain = index.entry_digest(script, entry, PASS_KEY_NEUTRAL)
    python, data, _, _ = index._closures['%s::%s' % (script, entry)]
    files = index.files
    if uncertain:
        return {path: files[path] for path in files if path not in PASS_KEY_NEUTRAL}, True
    units = index._reached.get('%s::%s' % (script, entry)) or {}
    selected = {}
    for path in sorted(python | data):
        if path not in STAIR_WALK_CODE or path not in files:
            continue
        selected[path] = index.unit_digest(path, units[path]) if path in units else files[path]
    return selected, False


def stair_key_sources():
    """The walker's code digest in the frame records' keys (key form STAIR_CODE_FORM): stair_task and the code of
    it a walk runs (STAIR_WALK_CODE), never the orchestration, the progress counter, the records' bookkeeping, the
    known-findings table (BUILD-STAIR-KEY-BOOKKEEPING-36) or the collision compilers (BUILD-STAIR-PASS-NOT-KEPT-41).
    Computed once per process."""
    if 'digest' not in _WALKER_SOURCES:
        import hashlib
        import json
        selected, uncertain = stair_code_selection()
        _WALKER_SOURCES['digest'] = hashlib.sha256(json.dumps(
            [STAIR_CODE_FORM, sorted(selected.items()), uncertain], sort_keys=True).encode()).hexdigest()
    return _WALKER_SOURCES['digest']


def stair_area_key_sources():
    """The walker's code digest in the keys of walks restricted to a walk area (stair_task_in, key form
    'chim-stair-area-code-1'): stair_task_in and the code of it a walk runs, in STAIR_WALK_CODE only, as
    stair_key_sources does for stair_task. Whole-frame walks keep stair_key_sources, so their records stay
    valid. Computed once per process."""
    if 'area' not in _WALKER_SOURCES:
        import hashlib
        import json
        selected, uncertain = stair_code_selection('stair_task_in')
        _WALKER_SOURCES['area'] = hashlib.sha256(json.dumps(
            ['chim-stair-area-code-1', sorted(selected.items()), uncertain], sort_keys=True).encode()).hexdigest()
    return _WALKER_SOURCES['area']


# Which stored frame walks a build reuses (BUILD-STAIR-PASS-NOT-KEPT-41). 'passes': a walk that passed (no flight
# step it cannot walk) is reused while its key is unchanged, whatever the rest of the build that walked it did;
# a walk with a gating failure only with the check mark of a passed master build (an accepted known finding of a
# private test). 'checked': the earlier rule, only walks with a check mark (tools/stair_records.py promote).
# Development builds and stand-alone runs default to 'passes'; release candidates and finals always use
# 'checked' (and reuse anything at all only with --allow-release-reuse, pass_cache.setting).
WALK_REUSE_ENV = 'AMIWIND_STAIR_WALK_REUSE'
WALK_REUSE_RULES = ('passes', 'checked')


def walk_reuse_rule(version=None):
    """The reuse rule of this run: AMIWIND_STAIR_WALK_REUSE, else by the run's version (AMIWIND_RUN_VERSION):
    'checked' for release candidates and finals, 'passes' otherwise. 'passes' for an rc or final is refused."""
    import os
    from cache_provenance import version_class
    version = os.environ.get('AMIWIND_RUN_VERSION') if version is None else version
    release = version_class(version or '') in ('rc', 'final')
    rule = os.environ.get(WALK_REUSE_ENV, '') or ('checked' if release else 'passes')
    if rule not in WALK_REUSE_RULES:
        raise ValueError('%s must be one of %s, not %r' % (WALK_REUSE_ENV, ', '.join(WALK_REUSE_RULES), rule))
    if release and rule != 'checked':
        raise ValueError('%s=%s is refused for %s: a release build reuses only stair walks a passed master build '
                         'checked' % (WALK_REUSE_ENV, rule, version))
    return rule


def walk_passed(rows):
    """True when a frame's walk has no gating failure (stair_walk._gating: a flight step the box cannot walk)."""
    from stair_walk import _gating
    return not any(_gating(r) for r in rows)


def stair_unit(task):
    """Worker: one unit of a frame's walk, (out, frame index, [core...], unit id[, walk area]) -> (unit id, rows): the
    cores' stair_task rows (stair_task_in with a walk area) in core order (a unit is a run of one frame's cores: one
    frame read serves them all)."""
    out, frame_index, cores, uid = task[:4]
    area = task[4] if len(task) > 4 else None
    rows = []
    for core in cores:
        rows.extend(stair_task((out, frame_index, core)) if area is None
                    else stair_task_in((out, frame_index, core, area)))
    return uid, rows


def stair_units(walk_frames, cores, counts, workers):
    """[(steps, frame index, [core...], unit id)] largest first. Only the cores with steps or ramps to check go
    in (a core without candidates walks nothing: stair_walk.check_polys returns no rows for it), cut in core
    order into runs of about total / (4 x workers) steps, so one large frame never tails the gate; unit ids
    follow frame and core order (a frame's rows are its units' rows in id order)."""
    import math
    total = sum(sum(counts[fi]) for fi in walk_frames)
    budget = max(1, int(math.ceil(total / float(4 * max(1, workers))))) if total else 1
    units = []
    for fi in walk_frames:
        group, size = [], 0
        for core, n in zip(cores[fi], counts[fi]):
            if not n:
                continue
            group.append(core)
            size += n
            if size >= budget:
                units.append((size, fi, group, len(units)))
                group, size = [], 0
        if group:
            units.append((size, fi, group, len(units)))
    return sorted(units, key=lambda u: (-u[0], u[3]))


def _frame_index_path(root, path):
    import hashlib
    h = hashlib.sha256(('chim-frame:' + path).encode()).hexdigest()
    return Path(root) / 'stair-walk-frames' / h[:2] / (h + '.json')


def remember_frame(cache, path, key, parts):
    """Note in the pool the key of this frame's last stored walk and its inputs one by one, so a later build can
    say what changed when it walks the frame again. Bookkeeping only: never fails the gate, never part of a key."""
    import json
    import os
    try:
        target = _frame_index_path(cache.root, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + '.%d.tmp' % os.getpid())
        tmp.write_text(json.dumps({'path': path, 'key': key, 'sources': cache.sources, 'options': cache.options,
                                   'parts': parts}, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
        os.replace(tmp, target)
    except (OSError, TypeError, ValueError):
        pass


def walk_reason(cache, path, key, parts, candidate=False):
    """Why a frame is walked: what changed since its last stored walk in the pool (remember_frame). candidate: a
    stored walk exists but is not reused (True: it has no check mark; a text: why not)."""
    import json
    if candidate:
        return candidate if isinstance(candidate, str) else 'its stored walk has no check mark of a passed master build'
    try:
        last = json.loads(_frame_index_path(cache.root, path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return 'no earlier walk of this frame in the pool'
    why = []
    if last.get('sources') != cache.sources:
        why.append('walker code changed (sources %s -> %s)' % (str(last.get('sources'))[:12], cache.sources[:12]))
    if last.get('options') != cache.options:
        why.append('walk options changed (%s -> %s)' % (json.dumps(last.get('options'), sort_keys=True),
                                                         json.dumps(cache.options, sort_keys=True)))
    old, new = {n: d for n, d in last.get('parts') or []}, dict(parts)
    changed = [n for n in list(new) + [n for n in old if n not in new] if old.get(n) != new.get(n)]
    if changed:
        why.append('inputs changed: %d of %d (%s%s)' % (len(changed), len(new), ', '.join(changed[:4]),
                                                        ', ...' if len(changed) > 4 else ''))
    if not why:
        return 'its stored walk is missing or damaged' if last.get('key') == key else 'key form changed'
    return '; '.join(why)


def area_part(area):
    """The walk area as one of a frame's key parts (frame_stair_parts): an area walk reads exactly that box."""
    import hashlib
    import json
    return ('walk area', hashlib.sha256(json.dumps([float(v) for v in area]).encode()).hexdigest())


def derive_area_rows(cache, whole_key, area, rule):
    """(rows, provenance, source) of a frame's area walk taken from its stored whole-frame walk (WHOLE_KEY in the
    whole-frame CACHE), or None: the whole-frame rows whose riser point is in AREA (in_walk_area), which are exactly
    the rows stair_task_in walks (the same cores, steps, flight marks and order). Under the reuse rule 'checked' only
    from a record a passed master build checked; under 'passes' also from any intact record whose area rows pass
    (a whole-frame walk that failed only on a border copy gives a pass of the cell)."""
    import stair_records
    if cache is None:
        return None
    record, mark = stair_records.lookup(cache, whole_key)
    if record is None:
        return None
    rows = [r for r in record['rows'] if in_walk_area(area, r['point'])]
    if mark is not None:
        how = stair_records.provenance(mark)
    elif rule == 'passes' and walk_passed(rows):
        how = stair_records.pass_provenance(record)
    else:
        return None
    return rows, how, {'key': record.get('key'), 'record_sha256': record.get('record_sha256'),
                       'run': record.get('run'), 'checked': mark is not None}


def walk_caches(root, areas):
    """(whole-frame cache, area cache or None) of the frame walks' records (pass_cache.PassCache 'stair-walk' under
    ROOT; ROOT None: keys only, nothing stored or read). A walk restricted to its area is its own record, keyed by
    its own walker (stair_task_in) and its area; the whole-frame records (towns, --stair-walk-area frame) keep their
    keys, and an area walk is derived from an unchanged whole-frame walk without walking (its rows filtered by the
    area: the same rows, derive_area_rows)."""
    from mesh_geometry_env import stair_mode
    from pass_cache import PassCache
    options = {'stair_mode': stair_mode(), 'world': 'chim-frame', 'tile': STAIR_TILE}
    return (PassCache('stair-walk', options, stair_key_sources(), root),
            PassCache('stair-walk', options, stair_area_key_sources(), root) if areas else None)


def walk_input_keys(frames, models, areas):
    """(whole-frame parts, parts, input keys) of every frame's walk: frame_stair_parts, plus the walk area of a
    frame that has one (area_part); the key is the SHA-256 of the parts (_parts_key)."""
    whole_parts = [frame_stair_parts(f, models) for f in frames]
    parts = [p + [area_part(areas[fi])] if fi in areas else p for fi, p in enumerate(whole_parts)]
    return whole_parts, parts, [_parts_key(p) for p in parts]


def shipped_entries(out, frames, models, root):
    """(entries, missing) of the known-good stair records (stair_records.shipped_entry) of a CHIM world whose every
    frame was walked into the pass cache at ROOT (a stair gate in 'cached' mode): one entry per frame, under the
    frame walk's full key; missing names the frames without a stored walk (nothing is walked here)."""
    from mesh_geometry_env import stair_mode
    import stair_records
    areas, _ = frame_walk_areas(out, frames)
    cache, area_cache = walk_caches(root, areas)
    _, _, keys = walk_input_keys(frames, models, areas)
    entries, missing = [], []
    for fi, (path, frame, _) in enumerate(frames):
        c = area_cache if fi in areas else cache
        record, _ = stair_records.lookup(c, keys[fi])
        if record is None:
            missing.append(path)
            continue
        rows = record['rows']
        outcome = record.get('outcome') or ('passed' if walk_passed(rows) else 'failed')
        entries.append(stair_records.shipped_entry(path, [int(v) for v in frame['cell']], c.key(keys[fi]),
                                                   c.sources, stair_mode(), rows, fi in areas, outcome))
    return entries, missing


def walk_counts(frames, per_frame):
    """Rows in the report against distinct places (BUILD-STAIR-WALK-BORDER-COPIES-41 prevention): a step or ramp
    copied into several frames is one place (its placement, kind and riser point in the island's frame units,
    centre / 4 + local, to the unit)."""
    seen = set()
    total = 0
    for fi, (_, frame, _) in enumerate(frames):
        cx, cy = float(frame['centre'][0]) / 4.0, float(frame['centre'][1]) / 4.0
        for r in per_frame.get(fi, ()):
            p = r['point']
            total += 1
            seen.add((str(r.get('ref')), r.get('kind'), round(cx + float(p[0])), round(cy + float(p[1])),
                      round(float(p[2]))))
    return {'rows': total, 'distinct': len(seen), 'ratio': round(total / float(len(seen)), 3) if seen else 0.0}


def stair_gate(out, frames, jobs=1, models=None):
    """The stair walkability gate (COLLISION-STAIR-SLOPE-32) on every frame of a CHIM world:
    every flight of stairs of the placed models is walked up and down by the standing box on
    the frame's own collision (chunk terrain and placements' standing hulls, chunk borders
    included). Report as stair_walk.check: a failure is a flight step that cannot be walked.
    With models (the world's model records) and the pass cache on (stair_walk.walk_cache_mode 'cached', the
    legacy maps' own cache, pass_cache.py), each frame's rows are kept by frame_stair_key: a frame is walked
    once until what the walk reads changes; one progress line per frame as it finishes. Every run walks a
    seeded sample of the reused frames again (stair_walk.walk_sample, logged) and fails on any difference: that
    would be a key that does not cover the walk's inputs (BUILD-CHIM-HEAP-GATE-LATE-36). A frame's walk is a
    record (stair_records.py) with its outcome and provenance. A walk that passed is a pass: reused while its key
    is unchanged, whatever else the build that walked it did (walk_reuse_rule 'passes', development builds;
    BUILD-STAIR-PASS-NOT-KEPT-41); a failed walk, and in release candidates and finals every walk ('checked'),
    is reused only when a build of the master builder that wrote it passed every gate (its check mark).
    Work goes to the worker pool as units (stair_units): runs of one frame's cores that have steps or ramps to
    check, sized by those counts, largest first, so one large frame never tails the gate and a worker reads a
    frame once per unit (BUILD-CHIM-STAIR-WALK-UNCACHED-36); rows are byte for byte the per-core walk's.
    Every walked frame names why (walk_reason: the input that changed since its last stored walk)."""
    import json
    import math
    from build_parallel import completed_map, ordered_map
    from player_hull import STEP_HEIGHT, WALKABLE_Z
    from stair_walk import _gating, pick_sample, rows_digest, walk_cache_mode, walk_sample
    from build_jobs import resolve_jobs
    from mesh_geometry_env import stair_mode
    import progress_line
    import stair_progress
    import stair_records
    import time
    # Each region frame walks the cell it owns plus the map-switch margin; its border copies are walked where they
    # are owned (frame_walk_areas, BUILD-STAIR-WALK-BORDER-COPIES-41; AMIWIND_STAIR_WALK_AREA frame: the whole frame)
    areas, area_note = frame_walk_areas(out, frames)
    print('CHIM stair gate: walk area: %s' % area_note, flush=True)
    tasks = stair_tasks(out, frames, areas)
    cores_skipped = len(stair_tasks(out, frames)) - len(tasks) if areas else 0
    # keyed by the frame worker and what it reaches (BUILD-STAIR-KEY-BOOKKEEPING-36): the progress counter, the
    # records' bookkeeping and the known-findings table never rekey a stored frame walk, nor do the collision
    # compilers (their output is the frame's collision, in the parts): stair_key_sources, STAIR_WALK_CODE
    from pass_cache import folder
    mode = walk_cache_mode()
    root = folder() if models is not None and mode in ('cached', 'records') else None
    # records (the default without --developer-mode): a frame neither the workspace's own walks nor the known-good
    # stair records shipped with the source hold is reported, not walked (stair_records.load_shipped, B14)
    shipped, shipped_notes = (stair_records.load_shipped() if models is not None and mode == 'records'
                              else (None, None))
    keyed = root is not None or shipped is not None
    cache, area_cache = walk_caches(root, areas) if keyed else (None, None)

    def cache_of(fi):
        return area_cache if fi in areas else cache
    rule = walk_reuse_rule() if cache is not None else None
    whole_parts, parts, keys = walk_input_keys(frames, models, areas) if cache is not None else (None, None, None)
    cached, todo, sample, origin, candidates, stored, passes = {}, tasks, [], {}, 0, [], 0
    derived = {}                                 # frame index -> the whole-frame record its rows came from
    from_records, unmatched = {}, []             # frames taken from the shipped records; frames in neither
    if keys:
        for fi, key in enumerate(keys):
            record, mark = stair_records.lookup(cache_of(fi), key) if root is not None else (None, None)
            why_not = None
            if record is not None and mark is not None:
                cached[fi] = record['rows']
                origin[fi] = stair_records.provenance(mark)
            elif record is not None and rule == 'passes' and stair_records.passed(record)                     and walk_passed(record['rows']):
                cached[fi] = record['rows']      # a pass is a pass: kept whatever the rest of its build did
                origin[fi] = stair_records.pass_provenance(record)
                passes += 1
            elif record is not None:
                candidates += 1                  # a failed walk, or (release rule) one no passed master build checked
                why_not = (True if rule == 'checked' else
                           'its stored walk did not pass and has no check mark of a passed master build')
            if fi not in cached and fi in areas and root is not None:
                found = derive_area_rows(cache, _parts_key(whole_parts[fi]), areas[fi], rule)
                if found is not None:
                    cached[fi], derived[fi] = found[0], found[2]
                    origin[fi] = 'derived from its whole-frame walk, ' + found[1]
            if fi not in cached and shipped is not None:
                entry = shipped.get(cache_of(fi).key(key))
                if entry is not None:
                    cached[fi] = stair_records.shipped_rows(entry, frames[fi][0])
                    from_records[fi] = entry
                    origin[fi] = stair_records.shipped_provenance(entry)
                else:
                    unmatched.append(fi)
                    origin[fi] = ("not walked: its key is in neither the workspace's walks nor the shipped stair "
                                  "records (another converter or other game data); --stair-walk-cache cached walks it")
            if fi not in cached and fi not in unmatched:
                origin[fi] = 'walked: ' + walk_reason(cache_of(fi), frames[fi][0], key, parts[fi], why_not or False)
        if shipped is not None:
            print('CHIM stair gate: known-good stair records: %d files (%s), %d of %d frames match%s%s' % (
                len(shipped_notes['files']), ', '.join('%s %s' % (f['file'], f['version']) for f in
                                                        shipped_notes['files']) or 'none',
                len(from_records), len(frames),
                '; %d damaged entries left out' % len(shipped_notes['damaged']) if shipped_notes['damaged'] else '',
                '; %d frames in neither, NOT WALKED (reported)' % len(unmatched) if unmatched else ''), flush=True)
            for fi in unmatched:
                print('CHIM stair gate: %s: %s' % (frames[fi][0], origin[fi]), flush=True)
        sample = pick_sample(sorted(cached), walk_sample(), keys[0])
        if derived:
            print('CHIM stair gate: %d frames take their walk from an unchanged whole-frame walk, its rows outside '
                  'the walk area left out (nothing walked)' % len(derived), flush=True)
        if cached:
            print('CHIM stair gate: %d of %d frames reused by content; walked again to check the cache: %s'
                  % (len(cached), len(frames), ', '.join(frames[fi][0] for fi in sample) or 'none'), flush=True)
        for fi in sample:
            origin[fi] = 'walked again: ' + origin[fi]
        if passes:
            print('CHIM stair gate: %d of the reused frames are passed walks of earlier runs (reuse rule %s)'
                  % (passes, rule), flush=True)
        if candidates:
            print('CHIM stair gate: %d frames have a stored walk that is not reused (reuse rule %s: %s): walked again'
                  % (candidates, rule, 'only walks a passed master build checked' if rule == 'checked'
                     else 'it did not pass, and no passed master build checked it'), flush=True)
        todo = [t for t in tasks if (t[1] not in cached and t[1] not in unmatched) or t[1] in sample]
    # The progress counter counts the real work: the steps and ramps each walked frame checks (counted first,
    # polygons only, in parallel) and each reused frame's recorded rows; then the frames.
    walk_frames = sorted({t[1] for t in todo})
    cores = {fi: [t[2] for t in todo if t[1] == fi] for fi in walk_frames}
    workers = max(1, resolve_jobs(jobs))
    from chim.stair_pool import (WORKER_BASE_MIB, frame_walk_mib, memory_killed, memory_room, memory_workers,
                                 stair_unit_sized)
    # Workers by cores and by memory (CHIM-STAIR-GATE-POOL-BROKEN-42): each worker reads a whole frame; the largest
    # frame to walk sets every worker's share, and the container's own limit how many shares fit
    frame_mib = {fi: frame_walk_mib(frames[fi], models) for fi in walk_frames}
    per_worker = max(frame_mib.values()) if frame_mib else WORKER_BASE_MIB
    room = memory_room()
    by_cores = workers
    workers, memory_note = memory_workers(workers, per_worker, room)
    if walk_frames:
        big = max(walk_frames, key=lambda fi: frame_mib[fi])
        print('CHIM stair gate: workers: %s; largest frame %s about %.0f MiB a worker' % (
            memory_note, frames[big][0], frame_mib[big]), flush=True)
    count_started = time.monotonic()
    # per core: the steps and ramps it will check (the scheduler's cost; a core without any walks nothing)
    counts = dict(completed_map(stair_progress.chim_core_counts_task,
                                sorted([(str(out), fi, cores[fi]) + ((areas[fi],) if fi in areas else ())
                                        for fi in walk_frames], key=lambda t: -len(t[2])),
                                max(1, min(workers, len(walk_frames) or 1))))
    to_check = {fi: sum(counts[fi]) for fi in walk_frames}
    reused_only = [fi for fi in sorted(cached) if fi not in sample]
    stairs_total = sum(to_check.values()) + sum(len(cached[fi]) for fi in reused_only)
    units = stair_units(walk_frames, cores, counts, workers)
    print('CHIM stair gate: %d steps and ramps to check in %d frames (counted in %.1f s), %d recorded in %d reused '
          'frames; %d walk units on %d workers, largest first (%d of %d cores have steps or ramps)'
          % (sum(to_check.values()), len(walk_frames), time.monotonic() - count_started,
             sum(len(cached[fi]) for fi in reused_only), len(reused_only), len(units),
             max(1, min(workers, len(units) or 1)), sum(len(u[2]) for u in units),
             sum(len(c) for c in cores.values())), flush=True)
    if workers < by_cores:
        print('CHIM stair gate: %d of %d workers: the memory left in the container holds no more frames of this size'
              % (workers, by_cores), flush=True)
    if keys and walk_frames:
        why = {}
        for fi in walk_frames:
            if fi not in sample:
                reason = origin[fi][len('walked: '):].split(' (')[0]
                why[reason] = why.get(reason, 0) + 1
        print('CHIM stair gate: %d frames walked, %d reused; why walked: %s' % (
            len(walk_frames), len(reused_only),
            ', '.join('%d %s' % (n, r) for r, n in sorted(why.items(), key=lambda i: -i[1])) or 'sample only'),
            flush=True)
    stairs_done = frames_done = 0
    for fi in reused_only:
        # one line per frame, reused ones too: the log names where each frame's walk comes from
        stairs_done += len(cached[fi]); frames_done += 1
        progress_line.emit('CHIM stair gate', frames[fi][0], '%d steps and ramps, %d failed (%s)' % (
            len(cached[fi]), sum(1 for r in cached[fi] if _gating(r)), origin[fi]),
            (stairs_done, stairs_total, 'stairs'), (frames_done, len(frames), 'frames'))
    per_frame = {fi: [] for fi in range(len(frames))}
    parts_of = {fi: {} for fi in walk_frames}       # unit id -> rows, joined in id (core) order
    left = {fi: 0 for fi in walk_frames}
    for u in units:
        left[u[1]] += 1

    def finish(fi):
        nonlocal stairs_done, frames_done
        rows = [r for uid in sorted(parts_of[fi]) for r in parts_of[fi][uid]]
        per_frame[fi] = rows
        stairs_done += to_check.get(fi, 0); frames_done += 1
        progress_line.emit('CHIM stair gate', frames[fi][0], '%d steps and ramps, %d failed (%s)' % (
            len(rows), sum(1 for r in rows if _gating(r)),
            'walked again: sample, matches its record' if fi in sample else origin.get(fi, 'walked')),
            (stairs_done, stairs_total, 'stairs'), (frames_done, len(frames), 'frames'))
        if keys and fi in from_records:
            # a sampled frame of the shipped records: its flight steps walked again must be the shipped ones
            if stair_records.sha256_of(stair_records.flight_rows(rows)) != from_records[fi]['flights_sha256']:
                raise ValueError('Stair gate records: %s walked again differs from its shipped record (%s, key %s): '
                                 'the key does not cover everything the walk reads' % (
                                     frames[fi][0], from_records[fi].get('file'), keys[fi]))
            return
        if keys and fi in cached:
            if rows_digest(rows) != rows_digest(cached[fi]):
                raise ValueError('Stair gate cache: %s walked again differs from its cached rows (key %s): '
                                 'the key does not cover everything the walk reads' % (frames[fi][0], keys[fi]))
            return
        if keys and root is not None:
            keep(fi, rows)

    def keep(fi, rows, source=None):
        import cache_provenance
        c = cache_of(fi)
        cache_provenance.name_unit(c, keys[fi], lambda: frames[fi][0], lambda: parts[fi])
        # the frame's walk with its outcome: a passed walk is reused by later runs whatever this build does
        # next; never fails the gate
        stored.append(stair_records.store(c, keys[fi], rows, outcome='passed' if walk_passed(rows) else 'failed',
                                          derived_from=source))
        remember_frame(c, frames[fi][0], keys[fi], parts[fi])
    for fi in walk_frames:
        if not left[fi]:
            finish(fi)                           # no step or ramp in any core: no rows, nothing to walk
    unit_frame = {u[3]: u[1] for u in units}
    unit_of = {u[3]: u for u in units}
    done_units, peaks = set(), []
    from concurrent.futures.process import BrokenProcessPool
    try:
        for uid, found, peak in completed_map(
                stair_unit_sized, [((str(out), u[1], u[2], u[3]) + ((areas[u[1]],) if u[1] in areas else ()),
                                    frame_mib.get(u[1], WORKER_BASE_MIB), per_worker) for u in units],
                max(1, min(workers, len(units) or 1))):
            fi = unit_frame[uid]
            parts_of[fi][uid] = found
            done_units.add(uid)
            if peak is not None:
                peaks.append(peak)
            left[fi] -= 1
            if not left[fi]:
                finish(fi)
    except BrokenProcessPool as error:
        # name what was walking, never a bare broken pool (VERBOSE LOGS rule; CHIM-STAIR-GATE-POOL-BROKEN-42)
        open_units = [unit_of[uid] for uid in sorted(unit_of) if uid not in done_units]
        _, room_after = memory_room()
        killed = memory_killed()
        raise ValueError(
            'Stair gate: a walk worker was killed (%s) with %d of %d units unfinished, first %s; workers %d (%s); '
            'largest frame about %.0f MiB a worker; peak of the finished units %s; %s; out-of-memory kills in this '
            'container: %s' % (
                type(error).__name__, len(open_units), len(units),
                ', '.join('%s unit %d (%d steps, %d cores, about %.0f MiB)' % (
                    frames[u[1]][0], u[3], u[0], len(u[2]), frame_mib.get(u[1], 0.)) for u in open_units[:4]),
                max(1, min(workers, len(units) or 1)), memory_note, per_worker,
                '%.0f MiB' % max(peaks) if peaks else 'none finished', room_after,
                'unknown' if killed is None else killed)) from error
    for fi, rows in cached.items():
        per_frame[fi] = rows                     # (a sampled frame was compared equal above)
    for fi in sorted(derived):
        keep(fi, cached[fi], derived[fi])        # a derived walk is kept as its own record once the gate checked it
    rows = [r for fi in range(len(frames)) for r in per_frame[fi]]
    counted = walk_counts(frames, per_frame)
    print('CHIM stair gate: %d steps and ramps in the report, %d distinct places (%.2f per place)%s'
          % (counted['rows'], counted['distinct'], counted['ratio'],
             ': WARNING, over 1.2: flights are walked in several frames (BUILD-STAIR-WALK-BORDER-COPIES-41)'
             if counted['ratio'] > 1.2 else ''), flush=True)
    failures = [r for r in rows if _gating(r)]
    advisory = [r for r in rows if r['result'] == 'failed' and not _gating(r)]
    summary, reasons = {}, {}
    for r in rows:
        if r['result'] == 'untestable':
            why = str((r.get('detail') or {}).get('error') or (r.get('detail') or {}).get('status'))
            reasons[why] = reasons.get(why, 0) + 1
        kind = 'flight step' if r['kind'] == 'step' and r.get('flight') else r['kind']
        bucket = summary.setdefault(r['map'], {}).setdefault(kind, {})
        bucket[r['result']] = bucket.get(r['result'], 0) + 1
    return dict(format=1, status='failed' if failures else 'passed', frames=len(frames), tasks=len(tasks),
                stair_rule=__import__('mesh_geometry_env').stair_mode(), step_height=STEP_HEIGHT,
                walkable_normal_z=WALKABLE_Z, walkable_degrees=round(math.degrees(math.acos(WALKABLE_Z)), 2),
                gate='flights of stairs (3+ steps, 2+ vertical risers) the standing box cannot walk up and down',
                summary=summary, untestable_reasons=reasons, failures=failures, advisory_failures=advisory,
                tested=len(rows), walk_counts=counted,
                walk_area={'mode': walk_area_mode(), 'note': area_note, 'frames': len(areas),
                           'cores_skipped': cores_skipped, 'derived': len(derived)}, pass_cache={
                    'mode': walk_cache_mode(), 'reused': len(cached) - len(sample), 'walked': len(walk_frames) - len(sample),
                    'units': len(units), 'reuse_rule': rule, 'reused_passes': passes,
                    'sampled': [frames[fi][0] for fi in sample], 'unchecked_candidates': candidates,
                    'stored': stored,
                    'frames': {frames[fi][0]: origin.get(fi, 'walked') for fi in range(len(frames))}},
                records=None if shipped is None else {
                    'files': shipped_notes['files'], 'damaged': shipped_notes['damaged'],
                    'matched': len(from_records), 'unmatched': [frames[fi][0] for fi in unmatched],
                    'advisory_rows_not_listed': sum(e['counts'].get('rows', 0) - len(e['flights'])
                                                    for e in from_records.values())})


# (chim.known is imported where it is used: a module-level import put the known-findings table into every frame
# walk's key, BUILD-CHIM-STAIR-WALK-UNCACHED-36)


def require_stairs(out, jobs=1, report_path=None, accepted=(), world=None):
    """The build's stair gate: OUT/chim-stairs.json, and a ValueError naming the first flight step
    that cannot be walked. Skipped (and recorded as skipped) when the stair rule is off, as the
    legacy image step skips its gate (mesh_geometry_env).

    accepted: tracker IDs of known stair findings a private -devN test accepts (the caller checks
    the version): their failures move to accepted_known_findings, each with its ID; every other
    failure still stops the build. world: the world the step's validation read (chim.validate.loaded_world),
    else the files are read again."""
    import json
    from pathlib import Path
    from mesh_geometry_env import stair_mode
    from chim.validate import loaded_world
    report_path = Path(report_path or Path(out) / 'chim-stairs.json')
    if stair_mode() == 'off':
        report = dict(format=1, status='skipped', stair_rule='off')
    else:
        try:
            world = loaded_world(out, world)
        except ValueError as exc:
            raise ValueError('Stair gate: the CHIM world does not read back (%s)' % exc)
        frames = world[5]
        report = stair_gate(out, frames, jobs, models=world[4])
    if accepted and report.get('failures') is not None:
        from chim.known import known_stair_findings
        by_ref = known_stair_findings(accepted)
        from chim.cut import source_ref
        key = lambda r: source_ref(r['ref']) if isinstance(r['ref'], int) else r['ref']  # noqa: E731
        report['accepted_known_findings'] = [dict(r, finding=by_ref[key(r)]) for r in report['failures']
                                             if key(r) in by_ref]
        report['failures'] = [r for r in report['failures'] if key(r) not in by_ref]
        report['accepted_ids'] = sorted(accepted)
        if report['failures'] == [] and report['status'] == 'failed':
            report['status'] = 'passed with accepted known findings'
    report_path.write_text(json.dumps(report, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    if report.get('failures'):
        first = report['failures'][0]
        raise ValueError('Stair walkability gate failed on the CHIM world: %d flight steps cannot be walked '
                         '(first %s ref %s at %s, rise %s); see %s'
                         % (len(report['failures']), first['map'], first['ref'], first['point'], first.get('rise'),
                            report_path))
    return report


__all__ = ['FrameScene', 'frame_polys', 'stand_height', 'stair_gate', 'require_stairs', 'MAXS']
