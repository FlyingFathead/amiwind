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

    def __init__(self, world, frame_index=0, hull=1, column=None):
        """column: (x, y) frame-local, for a scene that is only traced along the vertical line there (a ground
        trace, chim.frame_map.frame_ground): only the chunks and placements whose box holds that line are
        relocated (the others are never traced there: _trace_brushes tests the same boxes), in the same order,
        and the trace's visit guard counts the whole frame's nodes (full_nodes), so every trace along the line
        gives the same result as on the whole scene (BUILD-IMAGE-REGION-MAPS-SERIAL-43)."""
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
        counted = {}

        def held(key, image, box):
            # a column scene: count the image's nodes (the whole scene's guard), relocate it only on the line
            if column is None:
                return True
            if key not in counted:
                counted[key] = _node_count(image, hull)
            return box[0] <= column[0] <= box[3] and box[1] <= column[1] <= box[4]
        for c in chunks:
            cell = (c['cx'], c['cy'])
            x0, y0 = lx + cell[0] * g, ly + cell[1] * g
            box = (x0 - margin[0], y0 - margin[1], -1e9, x0 + g + margin[0], y0 + g + margin[1], 1e9)
            if not held(('chunk', cell), c['image'], box):
                continue
            root = add_image(('chunk', cell), c['image'])
            self.chunk_roots[cell] = root
            self.brushes.append((root, (0., 0., 0.), axes((0., 0., 0.)), 'chunk %d,%d' % cell))
            self.boxes.append(box)
        for c in chunks:
            for r in c['owned']:
                lo, hi = r['box']
                box = tuple(lo[k] - margin[k] for k in range(3)) + tuple(hi[k] + margin[k] for k in range(3))
                image = world['models'][r['model']]['image']
                if not held(('model', r['model']), image, box):
                    continue
                root = add_image(('model', r['model']), image)
                # the source reference: a cut placement's pieces are one object (chim.cut)
                self.brushes.append((root, tuple(r['origin']), axes((0., r['yaw'], 0.)), source_ref(r['ref'])))
                self.boxes.append(box)
        if column is not None:
            self.full_nodes = sum(counted.values())
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


def _node_count(image, hull):
    """Nodes a brush image adds to a FrameScene (hull 0: its node tree, lump 5; hull 1: its clipnodes, lump 9),
    from its lump directory (chim.format.read_brush_image's checks of that lump)."""
    lump, size = (5, 24) if hull == 0 else (9, 8)
    if len(image) < F.BSP_HEADER or struct.unpack_from('<i', image)[0] != F.BSPVERSION:
        raise ValueError('Brush image is not BSP29')
    offset, length = struct.unpack_from('<ii', image, 4 + 8 * lump)
    if offset < F.BSP_HEADER or length < 0 or offset + length > len(image) or length % size:
        raise ValueError('Brush image lump %s outside the image' % F.LUMPS[lump])
    return length // size


def frame_polys(world, frame_index=0):
    """World-space polygons of a frame as the stair gate reads a region map (stair_walk._faces):
    [(points, ref)], the chunks' terrain as 'world', each placement's model faces moved by its
    origin and yaw, by reference number; vertices in the faces' own order (their winding)."""
    from chim.faces import face_polygons
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
_STAIR_DIGESTS = {}      # per worker process: (out, frame index) -> frame_stair_key of the frame as it was read


def _stair_frame(out, frame_index, expect=None):
    """Per worker process: the frame's scenes and polygons, built from the frame's own files
    (chim.validate.load_frame) and kept for the next cores of the same frame. Reading the whole
    world here (load_world, 8.9 s for 273 frames) for every frame a worker switched to cost most of
    the dev3 stair walk (CHIM-STAIR-GATE-WORLD-RELOAD-36).
    EXPECT: the frame_stair_key the walk's key holds (stair_gate: computed from the world it read). The frame as this
    worker reads it must have exactly that key, else nothing is walked (ValueError naming the frame): the loader is
    not part of the walk's code key (STAIR_FRAME_LOADER), so a walk is only ever stored or reused for the data it
    really walked (BUILD-REUSE-SCHEDULER-TOP-45 part 2)."""
    key = (str(out), frame_index)
    if key not in _STAIR_CACHE:
        from chim.validate import load_frame
        row, models = load_frame(out, frame_index)
        world = {'frames': {frame_index: row}, 'models': models}
        while len(_STAIR_CACHE) >= _STAIR_CACHE_FRAMES:
            _STAIR_CACHE.pop(next(iter(_STAIR_CACHE)))
        _STAIR_DIGESTS[key] = frame_stair_key(row, models)
        standing, points = FrameScene(world, frame_index), FrameScene(world, frame_index, hull=0)
        # the trace's visit guard of a walk: a fixed count, never the whole frame's node count (which far collision
        # changes), so a walk reads only the collision within its reach (WALK_GUARD_NODES, walk_reach)
        standing.full_nodes = points.full_nodes = WALK_GUARD_NODES
        _STAIR_CACHE[key] = (row[0], standing, points, frame_polys(world, frame_index))
    if expect is not None and _STAIR_DIGESTS.get(key) != expect:
        raise ValueError('Stair gate: frame %s (index %d of %s) as the walk worker reads it (chim.validate.load_frame) '
                         'has the frame data key %s, but its walk is keyed by %s (the world the gate read): the '
                         'loader returns other data than the world holds; nothing walked or stored for it'
                         % (_STAIR_CACHE[key][0], frame_index, out, _STAIR_DIGESTS.get(key), expect))
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
    rows = _check_items(scoped_items(candidates(wide, core)), near, scene, points.contents, points)
    for row in rows:
        row['map'] = path
    return rows


def scoped_items(items):
    """The candidates the walk scope walks (stair_walk.scope_setting, tools/build.py --stair-walk): 'flights' (the
    default) only the steps of flights, which gate the build; 'all' every step and ramp (the advisory findings).
    Each item is walked on its own, so a flights walk gives exactly the flight rows of an all walk
    (BUILD-STAIR-WALK-SCOPE-KEY-46: before, the CHIM gate walked every step and ramp whatever the scope)."""
    from stair_walk import flight_items, scope_setting
    return flight_items(items) if scope_setting() == 'flights' else items


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
    items = [item for item in scoped_items(candidates(wide, core)) if in_walk_area(area, item['point'])]
    rows = _check_items(items, near, scene, points.contents, points)
    for row in rows:
        row['map'] = path
    return rows


def stair_task_places(task):
    """Worker: a targeted walk (--stair-walk-places), (out, frame index, core, walk area or None, refs or None) ->
    rows: stair_task (stair_task_in with a walk area) on the steps and ramps of the named source references only
    (all of the core's with refs None). Rows of a targeted walk are reported, never stored as the frame's walk."""
    from stair_walk import _check_items, candidates
    out, frame_index, core, area, refs = task
    path, scene, points, polys = _stair_frame(out, frame_index)
    near, wide = stair_polys(polys, core)
    items = [item for item in scoped_items(candidates(wide, core))
             if (area is None or in_walk_area(area, item['point'])) and (refs is None or item['ref'] in refs)]
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
# polygons and its trace (this module, audit_walkability.py, player_hull.py), and the reading of the frame's brush
# images (chim/faces.py face_polygons, chim/format.py read_brush_image, chim/cut.py, chim/__init__.py's format
# numbers). Inside these files only the units stair_task reaches count (build_cache.SourceIndex scope 'units').
# Everything else the reach finds is left out: the collision compilers (chim/models.py, prepare_mesh_bsp.py,
# routed_hull.py, scenery_reduce.py, collision_bsp.py ...), the CHIM_VERSION label and two town configs, named by
# import chains. No walk runs any of them; what the compilers made is in the key already, as the frame's collision
# lumps (frame_stair_parts, STAIR_WALK_LUMPS). Before key form 1 an edit to any of them rekeyed every frame:
# v0.0.41-dev5 walked 604 unchanged frames again because CHIM_VERSION went 0.2.0 -> 0.2.1.
# The frame loader (STAIR_FRAME_LOADER, chim/validate.py load_frame) is not in the code key either (key form 2): a
# walk is keyed by the SHA-256 of the frame data it walks (frame_stair_parts, computed from the world the gate
# read) plus this code, and every walk worker checks that the frame it reads has exactly that data key before it
# walks (_stair_frame EXPECT), so a loader rewrite with the same output reuses every walk, and a loader that returns
# other data refuses to walk instead of storing rows under the wrong data. Before key form 2 the v0.0.45 rewrite of
# chim/validate.py (frames loaded on the worker pool, BUILD-CHIM-SERIAL-SECTIONS-44) changed only that module's
# import-time code, and all 1,351 frames of the v0.0.45 release build were walked again (BUILD-REUSE-SCHEDULER-TOP-45).
# tests/test_chim_stair_pass.py holds the list to the code a walk runs: a traced walk calls nothing outside it and
# the loader, and no reached function of these files imports or names a repository module outside it.
# STAIR_CODE_FORM names this key form; records written under an earlier form are not found under it, so nothing is
# reused across the change without being walked (tools/stair_records.py adopt carries a passed run's walks over
# after walking a sample again).
STAIR_CODE_FORM = 'chim-stair-code-2'
STAIR_WALK_CODE = ('tools/stair_walk.py', 'tools/chim/collision.py', 'tools/audit_walkability.py',
                   'tools/player_hull.py', 'tools/chim/faces.py', 'tools/chim/format.py', 'tools/chim/cut.py',
                   'tools/chim/__init__.py')
STAIR_AREA_CODE_FORM = 'chim-stair-area-code-2'     # the same for walks restricted to a walk area (stair_task_in)
STAIR_FRAME_LOADER = ('tools/chim/validate.py', 'load_frame')
_WALKER_SOURCES = {}


def stair_code_selection(entry='stair_task'):
    """({repository path: SHA-256 of its reached units}, uncertain) of the walker's code (STAIR_WALK_CODE, the
    units ENTRY reaches in those files: stair_task, or stair_task_in for a walk restricted to a walk area), the reach
    not followed into the frame loader (STAIR_FRAME_LOADER: what it returns is checked by content in every worker).
    uncertain: the reach could not be followed (a file that does not parse); then every repository file counts, as
    in every other pass key."""
    from build_cache import SourceIndex
    from pass_cache import PASS_KEY_FORM, PASS_KEY_NEUTRAL, ROOT
    index = SourceIndex(ROOT, top_format=PASS_KEY_FORM)
    script = Path(__file__).resolve()
    python, data, uncertain, units = index.entry_units(script, entry, stop={STAIR_FRAME_LOADER})
    files = index.files
    if uncertain:
        return {path: files[path] for path in files if path not in PASS_KEY_NEUTRAL}, True
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
    STAIR_AREA_CODE_FORM): stair_task_in and the code of it a walk runs, in STAIR_WALK_CODE only, as
    stair_key_sources does for stair_task. Whole-frame walks keep stair_key_sources, so their records stay
    valid. Computed once per process."""
    if 'area' not in _WALKER_SOURCES:
        import hashlib
        import json
        selected, uncertain = stair_code_selection('stair_task_in')
        _WALKER_SOURCES['area'] = hashlib.sha256(json.dumps(
            [STAIR_AREA_CODE_FORM, sorted(selected.items()), uncertain], sort_keys=True).encode()).hexdigest()
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
    """Worker: one unit of a frame's walk, (out, frame index, [core...], unit id[, walk area or None[, frame key]]) ->
    (unit id, rows): the cores' stair_task rows (stair_task_in with a walk area) in core order (a unit is a run of one
    frame's cores: one frame read serves them all). With the frame key (frame_stair_key of the world the gate read,
    the data part of the walk's key) the frame as this worker reads it must have that key (_stair_frame), so the rows
    are always the walk of the data they are stored under."""
    out, frame_index, cores, uid = task[:4]
    area = task[4] if len(task) > 4 else None
    expect = task[5] if len(task) > 5 else None
    refs = task[6] if len(task) > 6 else False      # a targeted walk (--stair-walk-places): its references or None
    _stair_frame(out, frame_index, expect)
    rows = []
    for core in cores:
        if refs is not False:
            rows.extend(stair_task_places((out, frame_index, core, area, refs)))
        else:
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


def walk_caches(root, areas, scope=None, method='frame'):
    """(whole-frame cache, area cache or None) of the frame walks' records (pass_cache.PassCache 'stair-walk' under
    ROOT; ROOT None: keys only, nothing stored or read). A walk restricted to its area is its own record, keyed by
    its own walker (stair_task_in) and its area; the whole-frame records (towns, --stair-walk-area frame) keep their
    keys, and an area walk is derived from an unchanged whole-frame walk without walking (its rows filtered by the
    area: the same rows, derive_area_rows). SCOPE 'flights' and METHOD 'reach' are in the options (a flights walk
    has other rows than an all walk; a reach key is another key form); scope 'all' with the frame key keeps the
    options, so the records and the shipped stair records written before them keep their keys."""
    from mesh_geometry_env import stair_mode
    from pass_cache import PassCache
    options = {'stair_mode': stair_mode(), 'world': 'chim-frame', 'tile': STAIR_TILE}
    if scope == 'flights':
        options['scope'] = 'flights'
    if method == 'reach':
        options['key'] = STAIR_REACH_KEY_FORM
    return (PassCache('stair-walk', options, stair_key_sources(), root),
            PassCache('stair-walk', options, stair_area_key_sources(), root) if areas else None)


def walk_input_keys(frames, models, areas):
    """(whole-frame parts, parts, input keys) of every frame's walk: frame_stair_parts, plus the walk area of a
    frame that has one (area_part); the key is the SHA-256 of the parts (_parts_key)."""
    whole_parts = [frame_stair_parts(f, models) for f in frames]
    parts = [p + [area_part(areas[fi])] if fi in areas else p for fi, p in enumerate(whole_parts)]
    return whole_parts, parts, [_parts_key(p) for p in parts]


# ---------------------------------------------------------------- the walk's reach key (BUILD-STAIR-WALK-SCOPE-KEY-46)
# The frame key (frame_stair_parts) holds every chunk and placement of a frame: a converter change to collision the
# walk never reaches (a rock's walls and underside far from any stair, CHIM-HULL-SURFACE-HEAP-46) rekeyed 1,196 of
# 1,351 frames and the v0.0.46-dev1 rebuild walked the island again. The reach key holds what the walk reads, per
# core of the frame:
#   1. the core's ITEMS, the steps and ramps the walk tests (stair_walk.candidates on the core's polygons, the walk
#      scope and the walk area applied), by the SHA-256 of the items themselves. They are found from the polygons of
#      the placements that reach the core plus STAIR_MARGIN + FLIGHT_MARGIN (stair_polys 'wide'), once, and kept in
#      the pool by the SHA-256 of those placements' reference, origin, yaw and placed polygons and of the code that
#      finds them (the items record, ITEMS_FOLDER), so an unchanged core never reads its frame to know its items;
#   2. the collision and polygons within the walk's reach of the items: every chunk and placement whose polygons or
#      collision box (FrameScene's, the box margin included) meet the polygons of the placements the items belong
#      to, grown by walk_reach() (how far a walk's traces, ground and headroom tests go beyond the step's own
#      placement), and every chunk whose point-contents cell the reach meets (FrameScene.contents clamps to the
#      frame's edge chunks), each by the SHA-256 of what the walk reads of it (brush_walk_digest, placement fields),
#      in scene order (a trace takes the first brush of equal fraction);
#   3. the frame's path, grid fields, tile, the reach, the walk scope and the walk area.
# A core without items is not in the key (it walks nothing). The trace's visit guard is a fixed count in a walk's
# scene (WALK_GUARD_NODES), never the whole frame's node count. A key that missed an input would be a correctness
# bug: every build walks a sample of the reused frames again and stops on any difference (--stair-walk-sample),
# and tests/test_chim_stair_reach_key.py traces walks and checks they read nothing outside their key.
WALK_KEY_ENV = 'AMIWIND_STAIR_WALK_KEY'
WALK_KEY_METHODS = ('reach', 'frame')
STAIR_REACH_KEY_FORM = 'chim-stair-reach-key-1'
STAIR_ITEMS_FORM = 'chim-stair-items-1'
ITEMS_FOLDER = 'stair-walk-items'
WALK_GUARD_NODES = 131072   # 32 x this many trace visits: never reached by one image's tree (< 65,520 clipnodes)
REACH_SLACK = 8.0           # rounding and the riser point's edge tolerance off its own polygons


def walk_key_method(cache_mode=None):
    """AMIWIND_STAIR_WALK_KEY (tools/build.py --stair-walk-key): 'reach' (the default with the workspace's own walks:
    the frame's cores with steps or ramps and the collision within the walk's reach) or 'frame' (the key before
    v0.0.46: every chunk and placement of the frame; the default with --stair-walk-cache records, whose shipped
    stair records are keyed by it)."""
    import os
    value = os.environ.get(WALK_KEY_ENV, '')
    if not value:
        if cache_mode is None:
            from stair_walk import walk_cache_mode
            cache_mode = walk_cache_mode()
        value = 'frame' if cache_mode == 'records' else 'reach'
    if value not in WALK_KEY_METHODS:
        raise ValueError('%s must be one of %s, not %r' % (WALK_KEY_ENV, ', '.join(WALK_KEY_METHODS), value))
    return value


def walk_reach():
    """Plan units beyond the polygons of a step's own placement within which the walk of that step traces and tests
    ground and headroom (stair_walk.test, walk, other_lines, _check_items): the start up to 3 x CLEARANCE behind the
    riser plus a sideways shift, the walk past the riser by CLEARANCE plus a move or the tread test's box length,
    the standing box, a move, the nosing offset and a slack. Made from the walker's own constants, so a change to
    them changes it (and the walker's code key)."""
    from stair_walk import CLEARANCE, EDGE_TOLERANCE, INCREMENT, SIDE_SHIFTS
    return (3 * CLEARANCE + max(abs(v) for v in SIDE_SHIFTS) + max(CLEARANCE + INCREMENT, 2 * MAXS[0] + 1)
            + max(MAXS[0], MAXS[1]) + INCREMENT + EDGE_TOLERANCE + 1 + REACH_SLACK)


def brush_poly_digest(image):
    """(SHA-256 of the polygons frame_polys takes from a brush image: each face's points in order; plan bounds
    (x0, y0, x1, y1) of its vertexes or None; plan radius of its vertexes around the image's origin)."""
    import hashlib
    import numpy as np
    lumps = F.read_brush_image(image)
    verts = np.frombuffer(lumps[3], '<f4').reshape(-1, 3)
    edges = np.frombuffer(lumps[12], '<u2').reshape(-1, 2)
    surf = np.frombuffer(lumps[13], '<i4')
    h = hashlib.sha256(STAIR_ITEMS_FORM.encode())
    for f in struct.iter_unpack('<HhihH4Bi', lumps[7]):
        se = surf[f[2]:f[2] + f[3]]
        ids = np.where(se >= 0, edges[np.abs(se), 0], edges[np.abs(se), 1]) if len(se) else se
        h.update(struct.pack('<i', len(ids)))
        h.update(np.ascontiguousarray(verts[ids]).tobytes())
    if not len(verts):
        return h.hexdigest(), None, 0.0
    v = verts.astype(float)
    bounds = (float(v[:, 0].min()), float(v[:, 1].min()), float(v[:, 0].max()), float(v[:, 1].max()))
    return h.hexdigest(), bounds, float(np.sqrt((v[:, 0] ** 2 + v[:, 1] ** 2).max()))


def _sha(value):
    import hashlib
    import json
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def reach_sources(frame_row, models, memo):
    """The chunks and placements of a frame in scene order (FrameScene, frame_polys) as arrays for the reach key:
    'placement' (bool), 'sref' (source reference, -1 for a chunk), 'poly' (plan bounds of its placed polygons),
    'trace' (FrameScene's collision box), 'cell' (a chunk's contents cell, NaN for a placement), 'items' (SHA-256
    of what the items read of it), 'walk' (SHA-256 of what a walk reads of it), 'extent' (the frame's plan box).
    MEMO: model number -> digests (one world)."""
    import numpy as np
    path, frame, chunks = frame_row
    g, (lx, ly) = frame['grain'], frame['low']
    mx, my = abs(MINS[0]) + 2, abs(MINS[1]) + 2
    nan = float('nan')
    placement, sref, poly, trace, cell, items, walk = [], [], [], [], [], [], []
    for c in chunks:
        x0, y0 = lx + c['cx'] * g, ly + c['cy'] * g
        _, bounds, _ = brush_poly_digest(c['image'])
        box = (x0, y0, x0 + g, y0 + g)
        placement.append(False)
        sref.append(-1)
        poly.append(bounds or box)
        trace.append((x0 - mx, y0 - my, x0 + g + mx, y0 + g + my))
        cell.append(box)
        items.append('')
        walk.append(_sha(['chunk', c['cx'], c['cy'], brush_walk_digest(c['image'])]))

    def model(m):
        if m not in memo:
            known = (0 <= m < len(models)) if isinstance(models, (list, tuple)) else (m in models)
            if known:
                image = models[m]['image']
                memo[m] = (brush_walk_digest(image),) + brush_poly_digest(image)
            else:
                memo[m] = ('missing', 'missing', None, 0.0)
        return memo[m]
    for c in chunks:
        for r in c['owned']:
            wd, pd, _, radius = model(r['model'])
            ox, oy = float(r['origin'][0]), float(r['origin'][1])
            (bx0, by0, _), (bx1, by1, _) = r['box']
            placement.append(True)
            sref.append(source_ref(r['ref']))
            poly.append((ox - radius, oy - radius, ox + radius, oy + radius))
            trace.append((bx0 - mx, by0 - my, bx1 + mx, by1 + my))
            cell.append((nan, nan, nan, nan))
            items.append(_sha(['placement', r['ref'], r['origin'], r['yaw'], pd]))
            walk.append(_sha(['placement', [r.get(k) for k in STAIR_PLACEMENT_FIELDS], wd]))
    return {'placement': np.array(placement, bool), 'sref': np.array(sref, np.int64),
            'poly': np.array(poly, float).reshape(-1, 4), 'trace': np.array(trace, float).reshape(-1, 4),
            'cell': np.array(cell, float).reshape(-1, 4), 'items': items, 'walk': walk,
            'extent': (lx, ly, lx + frame['nx'] * g, ly + frame['ny'] * g)}


def _meets(boxes, q):
    """Which of BOXES ((n, 4) plan boxes x0, y0, x1, y1, closed) meet the plan box Q."""
    return (boxes[:, 2] >= q[0]) & (boxes[:, 0] <= q[2]) & (boxes[:, 3] >= q[1]) & (boxes[:, 1] <= q[3])


def reach_boxes(src, owners, reach):
    """The plan boxes a core's walks stay in: the placed polygons of the placements its items belong to (OWNERS,
    indices into SRC), each grown by REACH."""
    return [(b[0] - reach, b[1] - reach, b[2] + reach, b[3] + reach) for b in src['poly'][owners]]


def reach_used(src, owners, reach):
    """Which sources of SRC (reach_sources) a core's walks can read: polygons or collision box meeting a reach box,
    or a chunk whose contents cell meets a reach box clamped into the frame (FrameScene.contents clamps)."""
    import numpy as np
    x0, y0, x1, y1 = src['extent']
    used = np.zeros(len(src['walk']), bool)
    for q in reach_boxes(src, owners, reach):
        clamped = (min(max(q[0], x0), x1), min(max(q[1], y0), y1), min(max(q[2], x0), x1), min(max(q[3], y0), y1))
        used |= _meets(src['poly'], q) | _meets(src['trace'], q)
        used |= ~src['placement'] & _meets(src['cell'], clamped)
    return used


def stair_items_key_sources():
    """The code digest in the items records' keys: stair_items_task and what it reaches of the walker's code."""
    if 'items' not in _WALKER_SOURCES:
        import hashlib
        import json
        selected, uncertain = stair_code_selection('stair_items_task')
        _WALKER_SOURCES['items'] = hashlib.sha256(json.dumps(
            [STAIR_ITEMS_FORM, sorted(selected.items()), uncertain], sort_keys=True).encode()).hexdigest()
    return _WALKER_SOURCES['items']


def core_items_key(sources, core, area, scope, code):
    """(SHA-256 of what a core's items read, the placements read): the code, the scope, the core, the walk area and
    the placements whose polygons meet the core plus STAIR_MARGIN + FLIGHT_MARGIN, in scene order."""
    import hashlib
    import numpy as np
    from stair_walk import FLIGHT_MARGIN
    w = STAIR_MARGIN + FLIGHT_MARGIN
    wide = (core[0] - w, core[1] - w, core[2] + w, core[3] + w)
    picked = np.flatnonzero(sources['placement'] & _meets(sources['poly'], wide))
    h = hashlib.sha256(_sha([STAIR_ITEMS_FORM, code, scope, list(core),
                             None if area is None else list(area)]).encode())
    for i in picked:
        h.update(sources['items'][i].encode())
    return h.hexdigest(), picked


def stair_items_task(task):
    """Worker: (frame index, [(count, items SHA-256, source references)...]) for TASK (world folder, frame index,
    [core...], walk area or None, scope, frame data key): the items each core's walk tests (scoped_items of
    stair_walk.candidates on stair_polys 'wide', the walk area applied), as stair_task and stair_task_in find them.
    The frame as this worker reads it must have the frame data key the gate computed, else nothing is returned."""
    import hashlib
    import json
    import os
    from stair_walk import SCOPE_ENV, candidates
    out, frame_index, cores, area, scope, expect = task
    os.environ[SCOPE_ENV] = scope
    from chim.validate import load_frame
    row, models = load_frame(out, frame_index)
    if expect is not None and frame_stair_key(row, models) != expect:
        raise ValueError('Stair gate items: frame %s (index %d of %s) as the worker reads it has another frame data '
                         'key than the world the gate read; nothing found or stored for it'
                         % (row[0], frame_index, out))
    world = {'frames': {frame_index: row}, 'models': models}
    polys = [(pts, ref, _poly_box(pts)) for pts, ref in frame_polys(world, frame_index)]
    found = []
    for core in cores:
        items = scoped_items(candidates(stair_polys(polys, core)[1], core))
        if area is not None:
            items = [i for i in items if in_walk_area(area, i['point'])]
        digest = hashlib.sha256(json.dumps(items, sort_keys=True, default=str).encode()).hexdigest()
        found.append((len(items), digest, sorted({int(i['ref']) for i in items})))
    return frame_index, found


def _items_path(root, key):
    return Path(root) / ITEMS_FOLDER / key[:2] / (key + '.json')


def _items_lookup(root, key):
    import json
    if root is None:
        return None
    try:
        rec = json.loads(_items_path(root, key).read_text(encoding='utf-8'))
        if rec.get('format') == STAIR_ITEMS_FORM and rec.get('key') == key:
            return int(rec['count']), str(rec['items_sha256']), [int(v) for v in rec['refs']]
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None


def _items_store(root, key, info):
    """Keep a core's items record in the pool; bookkeeping, never fails the gate."""
    import json
    import os
    if root is None:
        return
    try:
        target = _items_path(root, key)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + '.%d.tmp' % os.getpid())
        tmp.write_text(json.dumps({'format': STAIR_ITEMS_FORM, 'key': key, 'count': info[0],
                                   'items_sha256': info[1], 'refs': list(info[2])}, sort_keys=True) + '\n',
                       encoding='utf-8', newline='\n')
        os.replace(tmp, target)
    except (OSError, TypeError, ValueError):
        pass


def reach_keys(out, frames, models, areas, scope, root, jobs=1, frame_mib=None):
    """(parts, keys, items) of every frame's walk under the reach key (see above): parts [(name, SHA-256)], keys
    their SHA-256 (_parts_key), items {frame index: [(core, count)...]} in core order (the scheduler's counts).
    Items records are read from and stored in ROOT (None: found here, nothing stored); the frames with cores whose
    items are not recorded are read on the worker pool, each admitted at its frame's size (FRAME_MIB)."""
    import time
    import numpy as np
    from build_parallel import governed_map
    from chim.stair_pool import WORKER_BASE_MIB
    started = time.monotonic()
    code = stair_items_key_sources()
    reach = walk_reach()
    memo, sources, plan, missing = {}, {}, {}, {}
    for fi, frame_row in enumerate(frames):
        src = reach_sources(frame_row, models, memo)
        sources[fi] = src
        area = areas.get(fi)
        cores = [t[2] for t in stair_tasks(out, [frame_row], {0: area} if area is not None else None)]
        plan[fi] = []
        for core in cores:
            key, picked = core_items_key(src, core, area, scope, code)
            info = _items_lookup(root, key)
            plan[fi].append([core, key, picked, info])
            if info is None:
                missing.setdefault(fi, []).append(len(plan[fi]) - 1)
    keyed = time.monotonic() - started
    found_at = time.monotonic()
    if missing:
        mib = frame_mib or {}
        tasks = [(str(out), fi, [plan[fi][k][0] for k in ks], areas.get(fi), scope,
                  frame_stair_key(frames[fi], models)) for fi, ks in missing.items()]
        # largest first: a frame's read and polygons grow with its size, its candidate search with its cores
        for fi, found in governed_map(stair_items_task, tasks, max(1, min(jobs, len(tasks))),
                                      unit_mib=max(mib.get(t[1], WORKER_BASE_MIB) for t in tasks),
                                      label='CHIM stair gate items',
                                      cost=lambda t: len(t[2]) * mib.get(t[1], WORKER_BASE_MIB),
                                      item_mib=lambda t: mib.get(t[1], WORKER_BASE_MIB)):
            for k, info in zip(missing[fi], found):
                plan[fi][k][3] = info
                _items_store(root, plan[fi][k][1], info)
    parts, keys, items = [], [], {}
    for fi, (path, frame, _) in enumerate(frames):
        src = sources[fi]
        frame_parts =[('frame', _sha([STAIR_REACH_KEY_FORM, path, STAIR_TILE, reach, scope,
                                       [frame.get(k) for k in STAIR_FRAME_FIELDS]]))]
        if fi in areas:
            frame_parts.append(area_part(areas[fi]))
        items[fi] = []
        for n, (core, _, picked, info) in enumerate(plan[fi]):
            count, digest, refs = info
            items[fi].append((core, count))
            if not count:
                continue
            owners = picked[np.isin(src['sref'][picked], np.array(refs, np.int64))]
            used = reach_used(src, owners, reach)
            frame_parts.append(('core %d' % n, _sha([list(core), digest, int(len(owners)),
                                                    [src['walk'][i] for i in np.flatnonzero(used)]])))
        parts.append(frame_parts)
        keys.append(_parts_key(frame_parts))
    print('CHIM stair gate: reach keys: %d frames, %d cores (%d with steps or ramps to walk); items of %d cores '
          'found again in %d frames (%.1f s), the others from the pool; keys %.1f s'
          % (len(frames), sum(len(v) for v in plan.values()), sum(1 for v in items.values() for _, c in v if c),
             sum(len(v) for v in missing.values()), len(missing), time.monotonic() - found_at, keyed), flush=True)
    return parts, keys, items


# ---------------------------------------------------------------- the watch list and targeted walks
# The stair walk as a redundancy check for named problem places (BUILD-STAIR-WALK-SCOPE-KEY-46; decided for the
# project 20 October 2026): config/stair-watch.json lists the places stair and walkway bugs reported (cells, frames,
# source references); every build walks the frames holding them again, even when their walk is reused, and stops
# when a walk again differs from its record. A bug page that reports a stair or walkway problem adds its place.
# --stair-walk-places FILE|ID,... walks ONLY the named places (a targeted check on request, rows not stored).
WATCH_ENV = 'AMIWIND_STAIR_WATCH'          # a watch list file, or 'off'
PLACES_ENV = 'AMIWIND_STAIR_WALK_PLACES'   # a targeted walk: a watch-format file, or IDs, cells, frames, refs
WATCH_FORMAT = 'aw-stair-watch-1'


def watch_file():
    return Path(__file__).resolve().parents[2] / 'config' / 'stair-watch.json'


def load_watch(path=None):
    """The places of a watch list ([{'id', 'cells', 'frames', 'refs', ...}]); PATH None: AMIWIND_STAIR_WATCH, else
    the shipped config/stair-watch.json; 'off': []. A list that does not read is an error (never silently empty)."""
    import json
    import os
    value = path if path is not None else (os.environ.get(WATCH_ENV, '') or str(watch_file()))
    if str(value).lower() == 'off':
        return []
    try:
        data = json.loads(Path(value).read_text(encoding='utf-8'))
        if data.get('format') != WATCH_FORMAT:
            raise ValueError('format %r, expected %s' % (data.get('format'), WATCH_FORMAT))
        places = data['places']
        for p in places:
            if not (p.get('cells') or p.get('frames') or p.get('refs') or p.get('maps')):
                raise ValueError('place %r names no cell, frame, reference or map' % p.get('id'))
        return places
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise ValueError('Stair watch list %s does not read: %s' % (value, exc))


def parse_places(value, watch=None):
    """Places of a targeted walk (--stair-walk-places): a watch-format FILE, or a comma list of IDs of the watch list,
    cells 'x:y', frame paths 'frames/...', source references 'ref:N' (or a bare number) and maps 'map:NAME' (an
    interior or other map the image step walks)."""
    import re
    if not value:
        return None
    if Path(value).is_file():
        return load_watch(value)
    watch = load_watch() if watch is None else watch
    by_id = {p['id']: p for p in watch}
    places = []
    for token in [t.strip() for t in str(value).split(',') if t.strip()]:
        if token in by_id:
            places.append(by_id[token])
        elif re.fullmatch(r'-?\d+:-?\d+', token):
            places.append({'id': token, 'cells': [[int(v) for v in token.split(':')]]})
        elif token.startswith('frames/') or token.endswith('.ccf'):
            places.append({'id': token, 'frames': [token]})
        elif token.startswith('map:') and len(token) > 4:
            places.append({'id': token, 'maps': [token[4:]]})
        elif re.fullmatch(r'(ref:)?\d+', token):
            places.append({'id': token, 'refs': [int(token.split(':')[-1])]})
        else:
            raise ValueError('Stair walk places: %r is no watch list ID, cell x:y, frame path, ref:N or map:NAME'
                             % token)
    return places


def match_places(frames, places):
    """{frame index: (place IDs, source references or None)} of the frames holding a place. A place with references
    is held by every frame that places one of them (its other fields only describe it), and its walk there takes
    those references' steps; a place without references is held by the frames of its paths and cells, whole
    (references None)."""
    found = {}
    for fi, (path, frame, chunks) in enumerate(frames):
        cell = [int(v) for v in frame['cell']] if frame.get('cell') is not None else None
        owned = None
        for p in places:
            refs = {int(v) for v in p.get('refs') or ()}
            if p.get('maps') and not (refs or p.get('cells') or p.get('frames')):
                continue                         # a map place: the image step's walk (watched_maps)
            if refs:
                if owned is None:
                    owned = {source_ref(r['ref']) for c in chunks for r in c['owned']}
                held = refs & owned
                if not held:
                    continue
            elif not (path in (p.get('frames') or ()) or
                      (cell is not None and cell in [[int(v) for v in c] for c in p.get('cells') or ()])):
                continue
            else:
                held = None
            ids, have = found.get(fi, ((), set()))
            found[fi] = (ids + (p['id'],), None if (have is None or held is None) else have | held)
    return found


def watched_maps(places):
    """{map name: place IDs} of the maps (interiors and other maps of the image step's walk) PLACES name."""
    found = {}
    for p in places or ():
        for name in p.get('maps') or ():
            found.setdefault(str(name), []).append(p['id'])
    return found


def shipped_entries(out, frames, models, root):
    """(entries, missing) of the known-good stair records (stair_records.shipped_entry) of a CHIM world whose every
    frame was walked into the pass cache at ROOT (a stair gate in 'cached' mode): one entry per frame, under the
    frame walk's full key; missing names the frames without a stored walk (nothing is walked here). The walks are
    looked up as the gate stored them (walk scope, key method: walk_key_method, stair_walk.scope_setting); the
    entries are keyed by the frame key without scope, as the known-good records are read
    (--stair-walk-cache records)."""
    from mesh_geometry_env import stair_mode
    from stair_walk import scope_setting
    import stair_records
    areas, _ = frame_walk_areas(out, frames)
    scope, method = scope_setting(), walk_key_method('cached')
    cache, area_cache = walk_caches(root, areas, scope, method)
    ship, ship_area = walk_caches(None, areas)
    _, _, frame_keys = walk_input_keys(frames, models, areas)
    keys = reach_keys(out, frames, models, areas, scope, root)[1] if method == 'reach' else frame_keys
    entries, missing = [], []
    for fi, (path, frame, _) in enumerate(frames):
        c = area_cache if fi in areas else cache
        s = ship_area if fi in areas else ship
        record, _ = stair_records.lookup(c, keys[fi])
        if record is None:
            missing.append(path)
            continue
        rows = record['rows']
        outcome = record.get('outcome') or ('passed' if walk_passed(rows) else 'failed')
        entries.append(stair_records.shipped_entry(path, [int(v) for v in frame['cell']], s.key(frame_keys[fi]),
                                                   s.sources, stair_mode(), rows, fi in areas, outcome))
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
    from build_parallel import completed_map, governed_map, ordered_map
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
    import os
    from pass_cache import folder
    from stair_walk import scope_setting
    from chim.stair_pool import frame_walk_mib as _frame_mib
    scope = scope_setting()
    print('CHIM stair gate: walk scope: %s (--stair-walk %s)' % (
        'flight steps only (the steps that gate the build)' if scope == 'flights'
        else 'every step and ramp (the advisory findings too)', scope), flush=True)
    # a targeted walk (--stair-walk-places): only the named places, nothing reused or stored
    places = parse_places(os.environ.get(PLACES_ENV, ''))
    targeted = match_places(frames, places) if places is not None else None
    if targeted is not None:
        tasks = [t for t in tasks if t[1] in targeted]
        print('CHIM stair gate: TARGETED walk of %d places (%s) in %d frames (%s): nothing else is walked; rows are '
              'reported, never stored as a frame\'s walk' % (
                  len(places), ', '.join(p['id'] for p in places), len(targeted),
                  ', '.join(frames[fi][0] for fi in sorted(targeted)) or 'none'), flush=True)
    mode = walk_cache_mode()
    root = folder() if models is not None and mode in ('cached', 'records') and targeted is None else None
    # records (the default without --developer-mode): a frame neither the workspace's own walks nor the known-good
    # stair records shipped with the source hold is reported, not walked (stair_records.load_shipped, B14)
    shipped, shipped_notes = (stair_records.load_shipped() if models is not None and mode == 'records'
                              and targeted is None else (None, None))
    keyed = root is not None or shipped is not None
    method = walk_key_method(mode) if keyed else None
    cache, area_cache = walk_caches(root, areas, scope, method) if keyed else (None, None)
    # the shipped stair records are keyed by the frame key without scope (stair_records.shipped_entry)
    ship, ship_area = walk_caches(None, areas) if shipped is not None else (None, None)

    def cache_of(fi):
        return area_cache if fi in areas else cache
    rule = walk_reuse_rule() if cache is not None else None
    whole_parts, parts, keys, ship_keys, reach_items = None, None, None, None, None
    if cache is not None and method == 'reach':
        from build_parallel import stage_ceiling as _ceiling
        parts, keys, reach_items = reach_keys(out, frames, models, areas, scope, root, max(1, _ceiling(jobs)),
                                              {fi: _frame_mib(frames[fi], models) for fi in range(len(frames))})
        ship_keys = walk_input_keys(frames, models, areas)[2] if shipped is not None else None
    elif cache is not None:
        whole_parts, parts, keys = walk_input_keys(frames, models, areas)
        ship_keys = keys
    if cache is not None:
        print('CHIM stair gate: walk key: %s' % (
            'reach (per core: its steps and ramps and the collision within the walk\'s reach)' if method == 'reach'
            else 'frame (every chunk and placement of the frame)'), flush=True)
    cached, todo, sample, origin, candidates, stored, passes = {}, tasks, [], {}, 0, [], 0
    watched = {}                                 # frame index -> watch list place IDs
    reused_records = []     # unmarked passes this run reuses: a passed build marks them too (BUILD-CHIM-STAIR-NO-REUSE-42)
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
                reused_records.append(stair_records.listed(cache_of(fi), key, record))
            elif record is not None:
                candidates += 1                  # a failed walk, or (release rule) one no passed master build checked
                why_not = (True if rule == 'checked' else
                           'its stored walk did not pass and has no check mark of a passed master build')
            if fi not in cached and fi in areas and root is not None and whole_parts is not None:
                found = derive_area_rows(cache, _parts_key(whole_parts[fi]), areas[fi], rule)
                if found is not None:
                    cached[fi], derived[fi] = found[0], found[2]
                    origin[fi] = 'derived from its whole-frame walk, ' + found[1]
            if fi not in cached and shipped is not None:
                entry = shipped.get((ship_area if fi in areas else ship).key(ship_keys[fi]))
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
        # the watch list: the frames of the named problem places are walked again every build (a reused walk is
        # compared with its record, as the sample), also in records mode
        for fi, (ids, _) in sorted(match_places(frames, load_watch()).items()):
            watched[fi] = ids
            if fi in unmatched:
                unmatched.remove(fi)
                origin[fi] = 'walked: watch list (%s)' % ', '.join(ids)
            elif fi in cached and fi not in sample:
                sample.append(fi)
        sample = sorted(sample)
        if watched:
            print('CHIM stair gate: watch list: %d frames hold its places, walked again: %s' % (
                len(watched), ', '.join('%s (%s)' % (frames[fi][0], ', '.join(ids))
                                        for fi, ids in sorted(watched.items()))), flush=True)
        if derived:
            print('CHIM stair gate: %d frames take their walk from an unchanged whole-frame walk, its rows outside '
                  'the walk area left out (nothing walked)' % len(derived), flush=True)
        if cached:
            print('CHIM stair gate: %d of %d frames reused by content; walked again to check the cache: %s'
                  % (len(cached), len(frames), ', '.join(frames[fi][0] for fi in sample) or 'none'), flush=True)
        for fi in sample:
            origin[fi] = ('walked again: %s' % ('watch list (%s), ' % ', '.join(watched[fi]) if fi in watched else '')
                          + origin[fi])
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
    # the stage's ceiling, not its launch share: the scheduler's live allowance decides how many walk at each task
    # (build_parallel.stage_ceiling, BUILD-CHIM-STAIR-JOBS-AT-LAUNCH-42)
    from build_parallel import stage_ceiling
    workers = max(1, stage_ceiling(jobs))
    from chim.stair_pool import (WORKER_BASE_MIB, frame_walk_mib, memory_killed, memory_room, memory_workers,
                                 stair_unit_sized)
    # Workers by cores and by memory (CHIM-STAIR-GATE-POOL-BROKEN-42): each worker reads a whole frame. Each unit is
    # admitted at its own frame's size (BUILD-CHIM-SERIAL-SECTIONS-44: the largest frame used to set every worker's
    # share, 4 of 24 workers at 2,855 MiB each in v0.0.44-dev1 for region frames of about 300 MiB), and the pool
    # follows the live allowance (more units start when the scheduler raises it or memory frees up)
    frame_mib = {fi: frame_walk_mib(frames[fi], models) for fi in walk_frames}
    per_worker = max(frame_mib.values()) if frame_mib else WORKER_BASE_MIB
    room = memory_room()
    by_cores = workers
    fit, memory_note = memory_workers(workers, sum(frame_mib.values()) / len(frame_mib) if frame_mib else per_worker,
                                      room)
    if walk_frames:
        big = max(walk_frames, key=lambda fi: frame_mib[fi])
        print('CHIM stair gate: workers: up to %d by cores, each unit admitted at its own frame size (%s; frames '
              'about %.0f to %.0f MiB a worker, %d at once at the mean); largest frame %s about %.0f MiB a worker'
              % (by_cores, room[1], min(frame_mib.values()), per_worker, fit, frames[big][0], frame_mib[big]),
              flush=True)
    count_started = time.monotonic()
    # per core: the steps and ramps it will check (the scheduler's cost; a core without any walks nothing); each
    # count reads its frame (polygons only): admitted at the frame's own size like the walks
    count_tasks = sorted([(str(out), fi, cores[fi]) + ((areas[fi],) if fi in areas else ()) for fi in walk_frames],
                         key=lambda t: -len(t[2]))
    if reach_items is not None:
        # the reach keys know every core's steps and ramps already (the items records): nothing read to count
        by_core = {fi: dict((tuple(c), n) for c, n in reach_items[fi]) for fi in walk_frames}
        counts = {fi: [by_core[fi].get(tuple(c), 0) for c in cores[fi]] for fi in walk_frames}
    else:
        counts = dict(governed_map(stair_progress.chim_core_counts_task, count_tasks,
                                   max(1, min(by_cores, len(walk_frames) or 1)), unit_mib=per_worker,
                                   label='CHIM stair gate counts',
                                   item_mib=lambda t: frame_mib.get(t[1], WORKER_BASE_MIB)))
    to_check = {fi: sum(counts[fi]) for fi in walk_frames}
    reused_only = [fi for fi in sorted(cached) if fi not in sample]
    stairs_total = sum(to_check.values()) + sum(len(cached[fi]) for fi in reused_only)
    units = stair_units(walk_frames, cores, counts, max(workers, by_cores))   # enough units to grow back into
    print('CHIM stair gate: %d steps and ramps to check in %d frames (counted in %.1f s), %d recorded in %d reused '
          'frames; %d walk units on %d workers, largest first (%d of %d cores have steps or ramps)'
          % (sum(to_check.values()), len(walk_frames), time.monotonic() - count_started,
             sum(len(cached[fi]) for fi in reused_only), len(reused_only), len(units),
             max(1, min(workers, len(units) or 1)), sum(len(u[2]) for u in units),
             sum(len(c) for c in cores.values())), flush=True)

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
    # the data part of each walked frame's key: every worker checks the frame it reads against it (_stair_frame),
    # so a walk is stored only under the data it walked (the loader is not in the code key, STAIR_FRAME_LOADER)
    frame_keys = {fi: frame_stair_key(frames[fi], models) for fi in walk_frames} if keys else {}
    done_units, peaks = set(), []
    from concurrent.futures.process import BrokenProcessPool
    try:
        # the walks in flight follow the container's memory while the gate runs (fixlist A9): it starts with the
        # workers that fit now and grows back toward the cores' count when memory frees up, never killing a walk
        # each unit at its frame's size: a worker keeps built only the frames that fit in that unit's share
        # (stair_unit_sized), so a worker holds about the frame it walks
        for uid, found, peak in governed_map(
                stair_unit_sized, [((str(out), u[1], u[2], u[3], areas.get(u[1]), frame_keys.get(u[1]))
                                    + ((targeted[u[1]][1],) if targeted is not None else ()),
                                    frame_mib.get(u[1], WORKER_BASE_MIB), frame_mib.get(u[1], WORKER_BASE_MIB))
                                   for u in units],
                max(1, min(by_cores, len(units) or 1)), unit_mib=per_worker, label='CHIM stair gate',
                item_mib=lambda task: task[1]):
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
                tested=len(rows), walk_counts=counted, scope=scope,
                targeted=None if targeted is None else {
                    'places': [p['id'] for p in places],
                    'frames': {frames[fi][0]: {'places': list(ids), 'refs': None if refs is None else sorted(refs)}
                               for fi, (ids, refs) in sorted(targeted.items())}},
                walk_area={'mode': walk_area_mode(), 'note': area_note, 'frames': len(areas),
                           'cores_skipped': cores_skipped, 'derived': len(derived)}, pass_cache={
                    'mode': walk_cache_mode(), 'reused': len(cached) - len(sample), 'walked': len(walk_frames) - len(sample),
                    'units': len(units), 'reuse_rule': rule, 'reused_passes': passes, 'key_method': method,
                    'watched': {frames[fi][0]: list(ids) for fi, ids in sorted(watched.items())},
                    'sampled': [frames[fi][0] for fi in sample], 'unchecked_candidates': candidates,
                    'stored': stored, 'reused_records': reused_records,
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
    import stair_walk
    if stair_walk.walk_off():   # BUILD-STAIR-WALK-OFF-46: the builder's default, nothing is walked
        report = dict(format=1, status='skipped', stair_walk='off')
    elif stair_mode() == 'off':
        report = dict(format=1, status='skipped', stair_rule='off')
    else:
        try:
            world = loaded_world(out, world, jobs)
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
