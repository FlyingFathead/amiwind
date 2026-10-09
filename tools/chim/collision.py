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


def _stair_frame(out, frame_index):
    """Per worker process: the world read once, the frame's scenes and polygons built once."""
    key = (str(out), frame_index)
    if key not in _STAIR_CACHE:
        from chim.validate import Failures, load_world
        fails = Failures()
        settings, files, sizes, textures, models, frames = load_world(out, fails)
        world = {'frames': frames, 'models': models}
        _STAIR_CACHE.clear()
        _STAIR_CACHE[key] = (frames[frame_index][0], FrameScene(world, frame_index),
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


def stair_gate(out, frames, jobs=1):
    """The stair walkability gate (COLLISION-STAIR-SLOPE-32) on every frame of a CHIM world:
    every flight of stairs of the placed models is walked up and down by the standing box on
    the frame's own collision (chunk terrain and placements' standing hulls, chunk borders
    included). Report as stair_walk.check: a failure is a flight step that cannot be walked."""
    import math
    from build_parallel import ordered_map
    from player_hull import STEP_HEIGHT, WALKABLE_Z
    from stair_walk import _gating
    from build_jobs import resolve_jobs
    tasks = stair_tasks(out, frames)
    rows = []
    for found in ordered_map(stair_task, tasks, max(1, min(resolve_jobs(jobs), len(tasks) or 1))):
        rows.extend(found)
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
                tested=len(rows))


from chim.known import KNOWN_STAIR_FINDINGS, known_stair_findings  # noqa: E402,F401 (light: build.py reads it)


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
        frames = load_world(out, fails)[5]
        if fails:
            raise ValueError('Stair gate: the CHIM world does not read back (%s)' % fails[0])
        report = stair_gate(out, frames, jobs)
    if accepted and report.get('failures') is not None:
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
