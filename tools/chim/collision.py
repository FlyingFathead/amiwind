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


def stair_task(task):
    """Worker: the shared stair gate (stair_walk.check_polys) on one core of a frame, with the
    frame's own collision (standing hull), contents and point hull."""
    from stair_walk import check_polys
    out, frame_index, core = task
    path, scene, points, polys = _stair_frame(out, frame_index)
    m = STAIR_MARGIN
    near = [(pts, ref) for pts, ref in polys
            if (lambda b: b[2] >= core[0] - m and b[0] <= core[2] + m and b[3] >= core[1] - m
                and b[1] <= core[3] + m)(_poly_box(pts))]
    rows = check_polys(near, scene, core, points.contents, points)
    for row in rows:
        row['map'] = path
    return rows


def stair_tasks(out, frames):
    """(out, frame index, core) for every core tile of every frame; the cores tile each frame
    exactly, so every step is tested once (in the core holding its riser point)."""
    tasks = []
    for fi, (path, frame, _) in enumerate(frames):
        g, (lx, ly) = frame['grain'], frame['low']
        hx, hy = lx + frame['nx'] * g, ly + frame['ny'] * g
        y = ly
        while y < hy:
            x = lx
            while x < hx:
                # the outermost cores run to infinity: nothing outside the frame is skipped
                core = (x if x > lx else -1e9, y if y > ly else -1e9,
                        x + STAIR_TILE if x + STAIR_TILE < hx else 1e9,
                        y + STAIR_TILE if y + STAIR_TILE < hy else 1e9)
                tasks.append((str(out), fi, core))
                x += STAIR_TILE
            y += STAIR_TILE
    return tasks


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


def stair_key_sources():
    """The walker's code digest in the frame records' keys: the frame worker stair_task and what it reaches
    (BUILD-STAIR-KEY-BOOKKEEPING-36), never the orchestration, the progress counter or the known-findings table."""
    from pass_cache import source_digest
    return source_digest((__file__, 'stair_task'))


def stair_unit(task):
    """Worker: one unit of a frame's walk, (out, frame index, [core...], unit id) -> (unit id, rows): the cores'
    stair_task rows in core order (a unit is a run of one frame's cores: one frame read serves them all)."""
    out, frame_index, cores, uid = task
    rows = []
    for core in cores:
        rows.extend(stair_task((out, frame_index, core)))
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
    """Why a frame is walked: what changed since its last stored walk in the pool (remember_frame)."""
    import json
    if candidate:
        return 'its stored walk has no check mark of a passed master build'
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
    record (stair_records.py): reused only when a build of the master builder that wrote it passed every gate.
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
    from pass_cache import PassCache
    import progress_line
    import stair_progress
    import stair_records
    import time
    tasks = stair_tasks(out, frames)
    # keyed by the frame worker and what it reaches (BUILD-STAIR-KEY-BOOKKEEPING-36): the progress counter, the
    # records' bookkeeping and the known-findings table never rekey a stored frame walk
    cache = PassCache.open('stair-walk', {'stair_mode': stair_mode(), 'world': 'chim-frame', 'tile': STAIR_TILE},
                           (__file__, 'stair_task')) if models is not None and walk_cache_mode() == 'cached' else None
    parts = [frame_stair_parts(f, models) for f in frames] if cache is not None else None
    keys = [_parts_key(p) for p in parts] if parts else None
    cached, todo, sample, origin, candidates, stored = {}, tasks, [], {}, 0, []
    if keys:
        for fi, key in enumerate(keys):
            record, mark = stair_records.lookup(cache, key)
            if record is not None and mark is not None:
                cached[fi] = record['rows']
                origin[fi] = stair_records.provenance(mark)
            elif record is not None:
                candidates += 1                  # a record no passed master build has checked: walked again
            if fi not in cached:
                origin[fi] = 'walked: ' + walk_reason(cache, frames[fi][0], key, parts[fi], record is not None)
        sample = pick_sample(sorted(cached), walk_sample(), keys[0])
        if cached:
            print('CHIM stair gate: %d of %d frames reused by content; walked again to check the cache: %s'
                  % (len(cached), len(frames), ', '.join(frames[fi][0] for fi in sample) or 'none'), flush=True)
        for fi in sample:
            origin[fi] = 'walked again: ' + origin[fi]
        if candidates:
            print('CHIM stair gate: %d frames have a stored walk no passed master build has checked: walked again'
                  % candidates, flush=True)
        todo = [t for t in tasks if t[1] not in cached or t[1] in sample]
    # The progress counter counts the real work: the steps and ramps each walked frame checks (counted first,
    # polygons only, in parallel) and each reused frame's recorded rows; then the frames.
    walk_frames = sorted({t[1] for t in todo})
    cores = {fi: [t[2] for t in todo if t[1] == fi] for fi in walk_frames}
    workers = max(1, resolve_jobs(jobs))
    count_started = time.monotonic()
    # per core: the steps and ramps it will check (the scheduler's cost; a core without any walks nothing)
    counts = dict(completed_map(stair_progress.chim_core_counts_task,
                                sorted([(str(out), fi, cores[fi]) for fi in walk_frames], key=lambda t: -len(t[2])),
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
        if keys and fi in cached:
            if rows_digest(rows) != rows_digest(cached[fi]):
                raise ValueError('Stair gate cache: %s walked again differs from its cached rows (key %s): '
                                 'the key does not cover everything the walk reads' % (frames[fi][0], keys[fi]))
            return
        if keys:
            import cache_provenance
            cache_provenance.name_unit(cache, keys[fi], lambda: frames[fi][0], lambda: parts[fi])
            stored.append(stair_records.store(cache, keys[fi], rows))   # a candidate record; never fails the gate
            remember_frame(cache, frames[fi][0], keys[fi], parts[fi])
    for fi in walk_frames:
        if not left[fi]:
            finish(fi)                           # no step or ramp in any core: no rows, nothing to walk
    unit_frame = {u[3]: u[1] for u in units}
    for uid, found in completed_map(stair_unit, [(str(out), u[1], u[2], u[3]) for u in units],
                                    max(1, min(workers, len(units) or 1))):
        fi = unit_frame[uid]
        parts_of[fi][uid] = found
        left[fi] -= 1
        if not left[fi]:
            finish(fi)
    for fi, rows in cached.items():
        per_frame[fi] = rows                     # (a sampled frame was compared equal above)
    rows = [r for fi in range(len(frames)) for r in per_frame[fi]]
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
                tested=len(rows), pass_cache={
                    'mode': walk_cache_mode(), 'reused': len(cached) - len(sample), 'walked': len(walk_frames) - len(sample),
                    'units': len(units),
                    'sampled': [frames[fi][0] for fi in sample], 'unchecked_candidates': candidates,
                    'stored': stored,
                    'frames': {frames[fi][0]: origin.get(fi, 'walked') for fi in range(len(frames))}})


# (chim.known is imported where it is used: a module-level import put the known-findings table into every frame
# walk's key, BUILD-CHIM-STAIR-WALK-UNCACHED-36)


def require_stairs(out, jobs=1, report_path=None, accepted=()):
    """The build's stair gate: OUT/chim-stairs.json, and a ValueError naming the first flight step
    that cannot be walked. Skipped (and recorded as skipped) when the stair rule is off, as the
    legacy image step skips its gate (mesh_geometry_env).

    accepted: tracker IDs of known stair findings a private -devN test accepts (the caller checks
    the version): their failures move to accepted_known_findings, each with its ID; every other
    failure still stops the build."""
    import json
    from pathlib import Path
    from mesh_geometry_env import stair_mode
    from chim.validate import Failures, load_world
    report_path = Path(report_path or Path(out) / 'chim-stairs.json')
    if stair_mode() == 'off':
        report = dict(format=1, status='skipped', stair_rule='off')
    else:
        fails = Failures()
        world = load_world(out, fails)
        frames = world[5]
        if fails:
            raise ValueError('Stair gate: the CHIM world does not read back (%s)' % fails[0])
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
