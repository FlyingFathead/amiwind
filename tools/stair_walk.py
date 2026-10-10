#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Stair and ramp walkability gate on converted maps (COLLISION-STAIR-SLOPE-32).

Finds every visible staircase step and walkable ramp of the converted meshes in
a map (placed models, not terrain) and walks the player's standing box over it
on the map's collision (hull 1, world and func_wall), up and back down, with the
engine's movement rule: move; when blocked, step up STEPSIZE (8.5), move on and
settle on a floor with normal z >= AW_WALKABLE_Z (0.69); keep within the step
height when walking down (aw_walk.c support, sv_phys.c SV_WalkMove).

Reference behaviour (Morrowind as OpenMW 0.51 implements it): steps up to
sStepSizeUp 34 units (8.5 here), slopes up to sMaxSlope 46 degrees, collision
against the authored triangles (components/misc/constants.hpp,
apps/openmw/mwphysics/stepper.cpp).

A step is a pair of level visible faces of one placement whose edges meet in
plan with a rise of 1..8.5 (a riser), each reaching 3 units from it; a ramp is a visible face of one
placement with a walkable slope on a route: visible ground continues within one
unit off its low edge and past its high edge (a roof eave or a slope ending at
a wall is not a route). Each is tested once, in the region whose core
holds it, and only where the visible geometry leaves the player's height free
above both ends (a face under a deck or inside a wall is not walkable by
design: 'covered'); collision that is solid where the visuals are open fails. A failure records the map, local position, placement reference and
model, rise, the blocking surface's angle and the walk direction.

Usage: stair_walk.py ID1_DIR [--out stair-walk.json] [--jobs N] [--maps NAME ...]
"""
import argparse
import json
import math
import os
from pathlib import Path
import re
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_walkability import Scene, axes  # noqa: E402
from player_hull import lumps, WALKABLE_Z, STEP_HEIGHT, MINS, MAXS  # noqa: E402

TREAD_NZ = .985
RISE_MIN = 1.0       # lower lips are trim, not steps
TREAD_MIN = 3.0      # each tread reaches this far from the riser
CLEARANCE = 11.0     # start/end distance from the riser: the standing box's half diagonal plus a margin
INCREMENT = 2.0
EDGE_TOLERANCE = 2.0   # risers with a chamfered nosing
MIN_OVERLAP = 16.0   # the standing box (14.6 wide) fits on the step
RAMP_MIN_AREA = 48.0
SIDE_SHIFTS = (1., -1., 2., -2., 3., -3.)  # sideways retries of a grazing line (at most about a fifth of the box width)
SHELL_MARGIN = .25   # authored collision plates stand 0.2 off each visible surface (mesh_geometry.shell_collision_parts)


def _faces(raw):
    """World-space polygons of every placed (func_wall) model: (points, ref)."""
    data = lumps(raw)
    verts = list(struct.iter_unpack('<3f', data[3]))
    edges = list(struct.iter_unpack('<HH', data[12]))
    surf = [s[0] for s in struct.iter_unpack('<i', data[13])]
    faces = list(struct.iter_unpack('<hhihhBBBBi', data[7]))
    models = list(struct.iter_unpack('<9f7i', data[14]))
    ents = [dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"', b))
            for b in re.findall(r'\{[^{}]*\}', data[0].decode('cp1252'))]
    out = []
    for e in [dict(model='*0', aw_ref='world', classname='func_wall')] + ents:
        m = e.get('model', '')
        if e.get('classname') != 'func_wall' or not re.fullmatch(r'\*\d+', m):
            continue
        origin = tuple(map(float, e.get('origin', '0 0 0').split()))
        basis = axes(tuple(map(float, e.get('angles', '0 0 0').split())))
        first, count = models[int(m[1:])][14:16]
        for fi in range(first, first + count):
            f = faces[fi]
            pts = []
            for k in range(f[3]):
                s = surf[f[2] + k]
                x, y, z = verts[edges[s][0] if s >= 0 else edges[-s][1]]
                pts.append(tuple(origin[i] + x * basis[0][i] + y * basis[1][i] + z * basis[2][i] for i in range(3)))
            out.append((pts, e.get('aw_ref', m)))
    return out


def _normal(pts):
    nx = ny = nz = 0.
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        nx += (a[1] - b[1]) * (a[2] + b[2]); ny += (a[2] - b[2]) * (a[0] + b[0]); nz += (a[0] - b[0]) * (a[1] + b[1])
    length = math.sqrt(nx * nx + ny * ny + nz * nz)
    # Quake faces wind clockwise seen from the front: the facing normal is the
    # negated counter-clockwise (Newell) normal.
    return (-nx / length, -ny / length, -nz / length, length / 2) if length > 1e-9 else None


def _placement(ref):
    """A converted placement: not the world model and not a terrain piece
    (converted terrain carries reference 2147483000 or above)."""
    try:
        return 0 < int(ref) < 2147483000
    except ValueError:
        return False


def _edge_z(a, b, ux, uy, s):
    """Height of edge a-b where it reaches s along the plan direction (ux, uy)."""
    sa, sb = ux * a[0] + uy * a[1], ux * b[0] + uy * b[1]
    t = 0. if abs(sb - sa) < 1e-9 else min(1., max(0., (s - sa) / (sb - sa)))
    return a[2] + (b[2] - a[2]) * t


def candidates(polys, core=None):
    """Steps (riser edges between level faces) and ramps of each placement."""
    def inside(p):
        return core is None or (core[0] <= p[0] < core[2] and core[1] <= p[1] < core[3])
    level, ramps, strips = {}, [], []
    for pts, ref in polys:
        if not _placement(ref):
            continue
        n = _normal(pts)
        if not n or n[2] <= .1:
            continue
        if n[2] < TREAD_NZ:
            # A sloped face. Rising at most a step next to a level tread it is a
            # stair step (crossed by stepping up when steeper than walkable, as
            # in the original); a longer walkable slope is a ramp.
            g = math.hypot(n[0], n[1]); d = (-n[0] / g, -n[1] / g)
            k = min(range(len(pts)), key=lambda i: pts[i][2] + pts[(i + 1) % len(pts)][2])
            a, b = pts[k], pts[(k + 1) % len(pts)]
            low = tuple((a[i] + b[i]) / 2 for i in range(3))
            k = max(range(len(pts)), key=lambda i: pts[i][2] + pts[(i + 1) % len(pts)][2])
            a, b = pts[k], pts[(k + 1) % len(pts)]
            high = tuple((a[i] + b[i]) / 2 for i in range(3))
            width = (high[0] - low[0]) * d[0] + (high[1] - low[1]) * d[1]
            rise = high[2] - low[2]
            across = [p[1] * d[0] - p[0] * d[1] for p in pts]
            span = max(across) - min(across)
            slope = round(math.degrees(math.acos(n[2])), 2)
            if not inside(low) or span < MIN_OVERLAP or width <= 0:
                continue
            if RISE_MIN < rise <= STEP_HEIGHT + 1e-3 and width <= 2 * CLEARANCE:
                strips.append(dict(kind='step', ref=ref, point=low, high=high, direction=d, rise=round(rise, 3),
                                   top=high[2], reach=round(width + TREAD_MIN, 3), slope=slope))
            elif n[2] >= WALKABLE_Z and n[3] >= RAMP_MIN_AREA and width >= TREAD_MIN:
                ramps.append(dict(kind='ramp', ref=ref, point=low, high=high, direction=d,
                                  reach=round(width, 3), slope=slope))
            continue
        if n[2] >= TREAD_NZ:
            z = sum(p[2] for p in pts) / len(pts)
            cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
            level.setdefault(ref, []).append((z, pts, (cx, cy)))
    steps = []
    for ref, items in level.items():
        bins = {}
        for index, (z, pts, centre) in enumerate(items):
            for i in range(len(pts)):
                a, b = pts[i], pts[(i + 1) % len(pts)]
                dx, dy = b[0] - a[0], b[1] - a[1]; length = math.hypot(dx, dy)
                if length < MIN_OVERLAP:
                    continue
                angle = math.atan2(dy, dx) % math.pi
                ux, uy = math.cos(angle), math.sin(angle)
                offset = -uy * a[0] + ux * a[1]
                key = (round(angle / .02) % 157, round(offset))
                bins.setdefault(key, []).append((index, a, b, ux, uy, offset))
        seen = set()
        for (ka, ko), group in bins.items():
            near = [e for da in (-1, 0, 1) for do in (-2, -1, 0, 1, 2) for e in bins.get(((ka + da) % 157, ko + do), [])]
            for i, a, b, ux, uy, off in group:
                for j, c, d, vx, vy, off2 in near:
                    if j == i or (min(i, j), max(i, j)) in seen:
                        continue
                    zi, zj = items[i][0], items[j][0]
                    rise = abs(zi - zj)
                    if not RISE_MIN < rise <= STEP_HEIGHT + 1e-3 or abs(ux * vy - uy * vx) > .03 or abs(off - off2) > EDGE_TOLERANCE:
                        continue
                    s = sorted([ux * a[0] + uy * a[1], ux * b[0] + uy * b[1]]); t = sorted([ux * c[0] + uy * c[1], ux * d[0] + uy * d[1]])
                    lo, hi = max(s[0], t[0]), min(s[1], t[1])
                    if hi - lo < MIN_OVERLAP:
                        continue
                    # A riser is a drop at the shared edge itself, not a difference
                    # of the two faces' mean heights: two tilted floor triangles
                    # meeting along one edge (a cave floor) are not a step
                    # (STAIRS-ADDAMASARTUS-32).
                    mid = (lo + hi) / 2
                    if abs(_edge_z(a, b, ux, uy, mid) - _edge_z(c, d, ux, uy, mid)) <= RISE_MIN:
                        continue
                    seen.add((min(i, j), max(i, j)))
                    low, high = (i, j) if zi < zj else (j, i)
                    m = (ux * (lo + hi) / 2 - uy * off, uy * (lo + hi) / 2 + ux * off)
                    hc = items[high][2]
                    nx, ny = -uy, ux
                    if (hc[0] - m[0]) * nx + (hc[1] - m[1]) * ny < 0:
                        nx, ny = -nx, -ny
                    point = (m[0], m[1], items[low][0])
                    reach_up = max((p[0] - m[0]) * nx + (p[1] - m[1]) * ny for p in items[high][1])
                    reach_down = max((m[0] - p[0]) * nx + (m[1] - p[1]) * ny for p in items[low][1])
                    if reach_up < TREAD_MIN or reach_down < TREAD_MIN:
                        continue
                    if inside(point):
                        steps.append(dict(kind='step', ref=ref, point=point, direction=(nx, ny), reach=round(reach_up, 3),
                                          rise=round(rise, 3), top=items[high][0]))
    stairs = steps + strips
    flights(stairs)
    return stairs + ramps


FLIGHT_MIN = 3  # steps in a row that make a staircase


def flights(stairs):
    """Mark steps that belong to a flight: at least FLIGHT_MIN steps of one
    placement in a row, each starting at the previous one's top and ahead of
    it in the same direction, with at least two vertical risers. Only flight steps gate a build; a lone step (a
    curb, a rock ledge, a wall foot) is reported as advisory."""
    by_ref = {}
    for s in stairs:
        by_ref.setdefault(s['ref'], []).append(s)
    for group in by_ref.values():
        n = len(group)
        nxt = {i: [] for i in range(n)}
        for i, a in enumerate(group):
            ax, ay, az = a['point']; d = a['direction']
            for j, b in enumerate(group):
                if i == j or d[0] * b['direction'][0] + d[1] * b['direction'][1] < .9:
                    continue
                bx, by, bz = b['point']
                along = (bx - ax) * d[0] + (by - ay) * d[1]
                across = abs((bx - ax) * -d[1] + (by - ay) * d[0])
                if 0 < along <= a.get('reach', TREAD_MIN) + 3 * CLEARANCE and across <= MIN_OVERLAP and abs(bz - a['top']) <= 1.:
                    nxt[i].append(j)
        depth = {}

        def longest(i, seen=()):
            if i in depth:
                return depth[i]
            best = 1 + max((longest(j, seen + (i,)) for j in nxt[i] if j not in seen), default=0)
            depth[i] = best
            return best
        prev = {j: [] for j in range(n)}
        for i in range(n):
            for j in nxt[i]:
                prev[j].append(i)
        up = {}

        def back(i, seen=()):
            if i in up:
                return up[i]
            best = 1 + max((back(j, seen + (i,)) for j in prev[i] if j not in seen), default=0)
            up[i] = best
            return best
        # Connected parts; a staircase has vertical risers between level treads
        # (rock terraces and dome rings are sloped strips only).
        part = list(range(n))

        def root(i):
            while part[i] != i:
                part[i] = part[part[i]]; i = part[i]
            return i
        for i in range(n):
            for j in nxt[i]:
                part[root(i)] = root(j)
        risers = {}
        for i, s in enumerate(group):
            if 'slope' not in s:
                risers[root(i)] = risers.get(root(i), 0) + 1
        for i, s in enumerate(group):
            s['flight'] = longest(i) + back(i) - 1 >= FLIGHT_MIN and risers.get(root(i), 0) >= 2


import numpy as np  # noqa: E402


GRID = 128.          # plan-view cell of the collision and headroom indexes (units)
GRID_MAX_CELLS = 256  # a box or query wider than this many cells is tested directly


class Headroom:
    """Visible clearance above a point: placements and terrain, as triangles.

    Queries test only the triangles whose plan bounds share a GRID cell with the
    query (kept in their original order) with the same per-triangle arithmetic
    as before, so every answer is identical to testing all of them
    (BUILD-STAIR-WALK-SLOW-33; tests/test_walk_trace_speed.py)."""

    def __init__(self, polys):
        import numpy as np
        tris = [(pts[0], pts[i], pts[i + 1]) for pts, ref in polys for i in range(1, len(pts) - 1)]
        self.t = np.array(tris, float).reshape(-1, 3, 3)
        n = np.cross(self.t[:, 1] - self.t[:, 0], self.t[:, 2] - self.t[:, 0])
        with np.errstate(all='ignore'):
            self.nz = np.abs(n[:, 2]) / np.linalg.norm(n, axis=1)
        self.tmax = self.t.max(axis=1)
        self.tmin = self.t.min(axis=1)
        cells = {}
        wide = []
        with np.errstate(all='ignore'):
            # Bounds grown by a unit: a point a rounding error outside a triangle's bounds
            # can still pass its barycentric test, so it must find the triangle too.
            x0 = np.floor((self.tmin[:, 0] - 1.) / GRID); y0 = np.floor((self.tmin[:, 1] - 1.) / GRID)
            x1 = np.floor((self.tmax[:, 0] + 1.) / GRID); y1 = np.floor((self.tmax[:, 1] + 1.) / GRID)
        for i in range(len(self.t)):
            if not (np.isfinite(x0[i]) and np.isfinite(y0[i]) and np.isfinite(x1[i]) and np.isfinite(y1[i])):
                wide.append(i); continue
            a, b, c, d = int(x0[i]), int(y0[i]), int(x1[i]), int(y1[i])
            if (c - a + 1) * (d - b + 1) > GRID_MAX_CELLS:
                wide.append(i); continue
            for gx in range(a, c + 1):
                for gy in range(b, d + 1):
                    cells.setdefault((gx, gy), []).append(i)
        self._wide = wide
        self._cells = {k: np.array(sorted(set(v + wide)), dtype=np.intp) for k, v in cells.items()}
        self._empty = np.array(sorted(wide), dtype=np.intp)

    def _near(self, x0, y0, x1, y1):
        """Indices (ascending) of every triangle whose plan bounds can meet the rectangle, or None for all."""
        import numpy as np
        try:
            a, b, c, d = (int(math.floor(x0 / GRID)), int(math.floor(y0 / GRID)),
                          int(math.floor(x1 / GRID)), int(math.floor(y1 / GRID)))
        except (OverflowError, ValueError):
            return None
        if (c - a + 1) * (d - b + 1) > GRID_MAX_CELLS:
            return None
        if a == c and b == d:
            return self._cells.get((a, b), self._empty)
        parts = [self._cells.get((gx, gy), self._empty) for gx in range(a, c + 1) for gy in range(b, d + 1)]
        return np.unique(np.concatenate(parts))

    def ground(self, x, y, z, level=False):
        """Height of the highest visible surface at or below z + 0.5 at (x, y), or
        None; level=True: None unless that surface is level (a tread)."""
        zz, nz = self._heights(x, y, True)
        keep = zz <= z + .5
        if not keep.any():
            return None
        i = int(np.argmax(np.where(keep, zz, -np.inf)))
        if level and nz[i] < TREAD_NZ:
            return None
        return float(zz[i])

    def free(self, x, y, z, height):
        zz = self._heights(x, y)
        return not ((zz > z + .1) & (zz < z + height)).any()

    def box_free(self, centre, mins=MINS, maxs=MAXS, inset=.5, side=None):
        """True when no visible triangle enters the standing box at centre
        (separating axis test; inset keeps touching surfaces out). side: a
        separate inset for the four side faces (negative grows the box
        sideways, e.g. by the collision plates' thickness, SHELL_MARGIN)."""
        import numpy as np
        ins = [inset if side is None else side] * 2 + [inset]
        lo = np.array([centre[i] + mins[i] + ins[i] for i in range(3)])
        hi = np.array([centre[i] + maxs[i] - ins[i] for i in range(3)])
        index = self._near(lo[0], lo[1], hi[0], hi[1])
        if index is None:
            t, tmax, tmin = self.t, self.tmax, self.tmin
        else:
            t, tmax, tmin = self.t[index], self.tmax[index], self.tmin[index]
        near = np.all(tmax >= lo, axis=1) & np.all(tmin <= hi, axis=1)
        if not near.any():
            return True
        c = (lo + hi) / 2; h = (hi - lo) / 2
        v = t[near] - c
        e = np.stack((v[:, 1] - v[:, 0], v[:, 2] - v[:, 1], v[:, 0] - v[:, 2]), axis=1)
        axes = [np.cross(e[:, i], np.eye(3)[j]) for i in range(3) for j in range(3)]
        axes.append(np.cross(e[:, 0], e[:, 1]))
        separated = np.zeros(len(v), bool)
        for a in axes:
            p = np.einsum('nk,nik->ni', a, v)
            r = np.abs(a) @ h
            separated |= (p.min(axis=1) > r) | (p.max(axis=1) < -r)
        return bool(separated.all())

    def _heights(self, x, y, normals=False):
        index = self._near(x, y, x, y)
        return self._heights_of(self.t if index is None else self.t[index],
                                self.nz if index is None else self.nz[index], x, y, normals)

    def reference_heights(self, x, y, normals=False):
        """Every triangle tested (byte-identity reference for tests)."""
        return self._heights_of(self.t, self.nz, x, y, normals)

    @staticmethod
    def _heights_of(t, nzs, x, y, normals):
        import numpy as np
        a, b, c = t[:, 0], t[:, 1], t[:, 2]
        d = (b[:, 1] - c[:, 1]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 1] - c[:, 1])
        ok = np.abs(d) > 1e-9
        with np.errstate(all='ignore'):
            l1 = ((b[:, 1] - c[:, 1]) * (x - c[:, 0]) + (c[:, 0] - b[:, 0]) * (y - c[:, 1])) / d
            l2 = ((c[:, 1] - a[:, 1]) * (x - c[:, 0]) + (a[:, 0] - c[:, 0]) * (y - c[:, 1])) / d
            l3 = 1 - l1 - l2
        hit = ok & (l1 >= 0) & (l2 >= 0) & (l3 >= 0)
        zz = l1[hit] * a[hit, 2] + l2[hit] * b[hit, 2] + l3[hit] * c[hit, 2]
        return (zz, nzs[hit]) if normals else zz


class Collision(Scene):
    """Scene (hull 1 by default) that traces only brush models whose bounds reach the segment."""

    def __init__(self, raw, hull=1):
        super().__init__(raw, hull=hull)
        data = lumps(raw)
        models = list(struct.iter_unpack('<9f7i', data[14]))
        ents = [dict(model='*0')] + [dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"', b))
                                     for b in re.findall(r'\{[^{}]*\}', data[0].decode('cp1252'))]
        ents = [e for e in ents if e.get('model') == '*0' or (e.get('classname') == 'func_wall' and re.fullmatch(r'\*\d+', e.get('model', '')))]
        margin = (abs(MINS[0]) + 2, abs(MINS[1]) + 2, abs(MINS[2]) + 2)
        self.boxes = []
        for brush, e in zip(self.brushes, ents):
            if e['model'] == '*0':
                self.boxes.append(None); continue
            m = models[int(e['model'][1:])]; root, origin, basis, ref = brush
            corners = [tuple(origin[i] + sum(c[j] * basis[j][i] for j in range(3)) for i in range(3))
                       for c in [(x, y, z) for x in (m[0], m[3]) for y in (m[1], m[4]) for z in (m[2], m[5])]]
            self.boxes.append(tuple(min(c[k] for c in corners) - margin[k] for k in range(3)) +
                              tuple(max(c[k] for c in corners) + margin[k] for k in range(3)))

        # Plan-view grid of the boxes (BUILD-STAIR-WALK-SLOW-33): a trace tests only the boxes
        # in the cells its segment's bounds touch, in the original order, with the same test.
        self._always = [i for i, box in enumerate(self.boxes) if box is None]
        self._grid = {}
        for i, box in enumerate(self.boxes):
            if box is None:
                continue
            x0, y0 = math.floor(box[0] / GRID), math.floor(box[1] / GRID)
            x1, y1 = math.floor(box[3] / GRID), math.floor(box[4] / GRID)
            if (x1 - x0 + 1) * (y1 - y0 + 1) > GRID_MAX_CELLS:
                self._always.append(i)
                continue
            for gx in range(x0, x1 + 1):
                for gy in range(y0, y1 + 1):
                    self._grid.setdefault((gx, gy), []).append(i)

    def _trace_brushes(self, start, end):
        lo = [min(start[k], end[k]) for k in range(3)]
        hi = [max(start[k], end[k]) for k in range(3)]
        x0, y0 = math.floor(lo[0] / GRID), math.floor(lo[1] / GRID)
        x1, y1 = math.floor(hi[0] / GRID), math.floor(hi[1] / GRID)
        if (x1 - x0 + 1) * (y1 - y0 + 1) > GRID_MAX_CELLS:
            found = range(len(self.boxes))
        else:
            found = set(self._always)
            grid = self._grid
            for gx in range(x0, x1 + 1):
                for gy in range(y0, y1 + 1):
                    found.update(grid.get((gx, gy), ()))
            found = sorted(found)
        brushes, boxes = self.brushes, self.boxes
        for i in found:
            box = boxes[i]
            if box is None or (hi[0] >= box[0] and lo[0] <= box[3] and hi[1] >= box[1] and lo[1] <= box[4]
                               and hi[2] >= box[2] and lo[2] <= box[5]):
                yield brushes[i]

    def reference_trace_brushes(self, start, end):
        """The original box filter (byte-identity reference for tests)."""
        for brush, box in zip(self.brushes, self.boxes):
            if box is None or all(max(start[k], end[k]) >= box[k] and min(start[k], end[k]) <= box[k + 3] for k in range(3)):
                yield brush


def _contents(scene, p):
    """World point contents (SV_PointContents on hull 0): -1 empty, -2 solid, -3 water."""
    node = scene.brushes[0][0]
    while node >= 0:
        plane, front, back = scene.nodes[node]
        n = scene.planes[plane]
        node = front if p[0] * n[0] + p[1] * n[1] + p[2] * n[2] - n[3] >= 0 else back
    return node


def _trace(s, a, b):
    h = s.trace(a, b)
    return (1., None, None) if not h else (h['fraction'], h['normal'], h['reference'])


def _settle(s, p, depth):
    f, n, r = _trace(s, p, (p[0], p[1], p[2] - depth))
    if 0 < f < 1 and n[2] >= WALKABLE_Z:
        return (p[0], p[1], p[2] - depth * f + .03125)
    return None


COLUMN_STEP = .25  # free-column search resolution (_start_column)


def _start_column(s, start, probe):
    """The highest free standing origin in the column start..start + probe, or
    None (STAIRS-BALMORA-B01-32). The walk settles from start + probe; under a
    low lintel that point can be solid although the player stands freely on the
    authored collision just below it (an arch over the foot of a flight whose
    collision ramp runs through the nosings, above the visible tread)."""
    k = int(probe / COLUMN_STEP)
    while k >= 0:
        q = (start[0], start[1], start[2] + k * COLUMN_STEP)
        if _trace(s, q, q)[0] == 1.:
            return q
        k -= 1
    return None


def walk(s, start, direction, distance, probe=8):
    """Engine-equivalent stepped walk of the standing origin; returns a result dict.

    The walk starts on the floor below start + probe; when that point is solid
    (a lintel just above the start), from the highest free point of the column
    start..start + probe instead (_start_column). A start with no free point in
    that column is 'start in solid'."""
    p = _settle(s, (start[0], start[1], start[2] + probe), probe + 16)
    if p is None and _trace(s, (start[0], start[1], start[2] + probe), (start[0], start[1], start[2] + probe))[0] == 0:
        top = _start_column(s, start, probe)
        if top is not None:
            p = _settle(s, top, top[2] - start[2] + 16)
    if p is None:
        f, n, r = _trace(s, start, start)
        return dict(status='start in solid' if f == 0 else 'no floor at start', reference=r)
    travelled = 0.
    while travelled < distance - 1e-6:
        q = (p[0] + direction[0] * INCREMENT, p[1] + direction[1] * INCREMENT, p[2])
        f, n, r = _trace(s, p, q)
        if f == 0:
            return dict(status='standing hull in solid', at=p, reference=r)
        if f < 1 and n[2] >= WALKABLE_Z:
            # A walkable slope: the move slides up along it (SV_FlyMove clips the
            # velocity to the plane), then the walker settles on it.
            dz = INCREMENT * math.hypot(n[0], n[1]) / n[2] + .05
            q3 = (q[0], q[1], p[2] + dz)
            f3, n3, r3 = _trace(s, p, q3)
            land = _settle(s, q3, dz + STEP_HEIGHT) if f3 == 1 else None
            if land is not None:
                p = land; travelled += INCREMENT
                continue
        if f < 1:
            fu, _, _ = _trace(s, p, (p[0], p[1], p[2] + STEP_HEIGHT))
            up = (p[0], p[1], p[2] + STEP_HEIGHT * fu)
            q2 = (up[0] + direction[0] * INCREMENT, up[1] + direction[1] * INCREMENT, up[2])
            f2, n2, r2 = _trace(s, up, q2)
            land = _settle(s, q2, STEP_HEIGHT + 1) if f2 == 1 else None
            if land is None:
                return dict(status='blocked', at=p, reference=r, surface_angle=round(math.degrees(math.acos(max(-1., min(1., n[2])))), 2))
            p = land
        else:
            land = _settle(s, q, STEP_HEIGHT + .75)
            if land is None:
                land = _settle(s, q, 256)
                if land is None:
                    return dict(status='no floor ahead', at=q)
            p = land
        travelled += INCREMENT
    return dict(status='walked', at=p)


def test(s, item, room=None):
    d = item['direction']
    x, y, z = item['point']
    lift = -MINS[2] + .25
    height = MAXS[2] - MINS[2]
    row = dict(item, point=[round(v, 3) for v in item['point']], direction=[round(v, 4) for v in d])
    # Start on visible ground before the riser or ramp, within a step below its
    # foot and with the player's height free above (a steep strip below a ramp
    # is crossed by stepping, as in the original). Collision that is solid or
    # missing where the visuals offer such a start is a failure.
    up = None
    ahead = (item['reach'] if 'slope' in item and item['kind'] == 'step'
             else max(1., min(CLEARANCE, item['reach'] - MAXS[0] - .5)))
    for back in (CLEARANCE, 1.5 * CLEARANCE, 2 * CLEARANCE, 3 * CLEARANCE):
        visual = None
        for side in (0.,) + SIDE_SHIFTS:
            if side and visual is None:
                break
            # A start that grazes a wall or post (a spiral stair against the
            # tower wall) is retried a little to the side: the player's line up
            # the flight is not unique (STAIRS-SEYDA-WAREHOUSE-32).
            sx, sy = x - d[0] * back - d[1] * side, y - d[1] * back + d[0] * side
            if room is not None:
                ground = room.ground(sx, sy, z)
                if ground is None or z - ground > STEP_HEIGHT or not room.free(sx, sy, ground + .4, height):
                    continue
                # The standing box (wider than a tread) rests on the highest edge under it.
                start = (sx, sy, max(ground, z) + lift)
                if not room.box_free(start):
                    continue  # a wall or the stair's own turn: no straight approach here
            else:
                start = (sx, sy, z + lift)
            # Stop once the standing box is on the step or ramp (not past its far end,
            # where a wall or the next feature may follow).
            result = walk(s, start, d, back + ahead)
            if room is not None and result['status'] == 'start in solid' and not room.box_free(start, side=-SHELL_MARGIN):
                # The start box grazes a visible wall or post closer than the
                # collision plates' own thickness: not an open start.
                visual = visual or result
                continue
            if side and room is not None and _visual_block(room, result, d):
                visual = result  # this sideways line meets visible geometry too
                continue
            up = result
            break
        if up is not None:
            break
        if visual is not None and visual['status'] != 'start in solid':
            up = visual  # every line meets visible geometry: reported as untestable below
            break
    if up is None:
        return dict(row, result='untestable', detail=dict(status='no visible approach'))
    if up['status'] != 'walked':
        if room is not None and _visual_block(room, up, d):
            return dict(row, result='untestable', detail=dict(_clean(up), status='visible geometry in the way'))
        return dict(row, result='failed', way='up', detail=_clean(up))
    end = up['at']
    if item['kind'] == 'step' and end[2] - lift < item['top'] - 1.:
        return dict(row, result='failed', way='up', detail=dict(status='did not rise', at=[round(v, 3) for v in end]))
    down = walk(s, end, (-d[0], -d[1]), back + ahead, probe=.5)
    if down['status'] != 'walked':
        if room is not None and _visual_block(room, down, (-d[0], -d[1])):
            return dict(row, result='untestable', detail=dict(_clean(down), status='visible geometry in the way'))
        return dict(row, result='failed', way='down', detail=_clean(down))
    return dict(row, result='passed')


def _visual_block(room, result, d):
    """A blocked straight walk whose next box (raised by a step) also meets the
    visible geometry: the path leaves the stair, the collision is not at fault.
    Sideways the box is grown by the collision plates' thickness (SHELL_MARGIN):
    a post or wall the box grazes closer than that blocks the plates as it
    blocks the visuals (STAIRS-SEYDA-WAREHOUSE-32)."""
    if result.get('status') not in ('blocked',) or 'at' not in result:
        return False
    x, y, z = result['at']
    return not room.box_free((x + d[0] * INCREMENT, y + d[1] * INCREMENT, z + STEP_HEIGHT), side=-SHELL_MARGIN)


def _clean(r):
    return {k: ([round(v, 3) for v in val] if isinstance(val, tuple) else val) for k, val in r.items()}


def check_polys(polys, scene, core=None, contents=None, proxy=None):
    """Stair gate on one map's geometry; the interface both builders share.

    polys: [(points, ref)] in map coordinates, ref 'world' for the world model
    (as _faces returns); scene: the standing-hull collision, anything with
    .trace(start, end) -> None or {'fraction', 'normal', 'reference'} like
    audit_walkability.Scene (hull 1); core: (x0, y0, x1, y1) or None for the
    whole map; contents: optional callable point -> Quake contents (-1 empty;
    water is skipped); proxy: optional point-hull scene to report the
    collision surface angle over a failing step. Returns one row per step or
    ramp: kind, ref, point, direction, rise, slope, flight, result
    (passed / failed / covered / untestable) and the walk detail."""
    return _check_items(candidates(polys, core), polys, scene, contents, proxy)


# What the walk covers (owner decision 9 October 2026): 'all' walks every step and ramp (development
# builds, the nightly full report); 'flights' walks only the steps of flights, the rows that can stop a
# build (release candidates and finals). The builder sets the variable (tools/build.py --stair-walk).
SCOPE_ENV = 'AMIWIND_STAIR_WALK'
SCOPES = ('all', 'flights')


def scope_setting():
    value = os.environ.get(SCOPE_ENV, '') or 'all'
    if value not in SCOPES:
        raise ValueError('%s must be one of %s, not %r' % (SCOPE_ENV, ', '.join(SCOPES), value))
    return value


def flight_items(items):
    """The candidates the 'flights' scope walks: every step that belongs to a flight (a sloped strip
    keeps its flight mark when check_polys later finds it is a ramp, so its row is the same as in a
    full walk)."""
    return [item for item in items if item.get('flight')]


def _check_items(items, polys, scene, contents=None, proxy=None):
    if not items:
        return []
    room = Headroom(polys)
    height = MAXS[2] - MINS[2]
    rows = []
    for item in items:
        x, y, z = item['point']; d = item['direction']
        if contents is not None and contents((x, y, z + 1)) != -1:
            continue  # under water (swimming) or inside the world
        top = item.get('top', z)
        if 'high' in item:
            # A ramp or steep strip is part of a route: visible ground continues
            # off its low edge and past its high edge (a roof eave or a slope
            # ending at a wall is not).
            below = room.ground(x - d[0], y - d[1], z)
            hx, hy, hz = item.pop('high')
            beyond = room.ground(hx + d[0], hy + d[1], hz + 1.0)
            if below is None or z - below > 1.0 or beyond is None or hz - beyond > 1.0:
                continue
            # A steep strip is a stair step only next to a level tread on one side.
            if (item['kind'] == 'step' and room.ground(x - d[0], y - d[1], z, True) is None
                    and room.ground(hx + d[0], hy + d[1], hz + 1.0, True) is None):
                item['kind'] = 'ramp'
        # The upper surface carries the standing box: visible ground at least at
        # the riser top continues a box length past it (a curb or lip in front
        # of a wall is not a step).
        far = 2 * MAXS[0] + 1
        if item['kind'] == 'step':
            ex = x + d[0] * (item['reach'] if 'slope' in item else 0) + d[0] * far
            ey = y + d[1] * (item['reach'] if 'slope' in item else 0) + d[1] * far
            g = room.ground(ex, ey, top + STEP_HEIGHT)
            if g is None or g < top - 1. or not room.free(ex, ey, g + .4, height):
                continue
        # Headroom at the riser (or the ramp's low edge), just before and after it:
        # further along, the next steps are legitimately above the walking level.
        o = EDGE_TOLERANCE + 1  # past a chamfered nosing
        if not (room.free(x - d[0] * o, y - d[1] * o, z + .4, height) and
                room.free(x + d[0] * o, y + d[1] * o, (top if item['kind'] == 'step' else
                                                       z + o * math.tan(math.radians(item['slope']))) + .4, height)):
            rows.append(dict(item, point=[round(v, 3) for v in item['point']], result='covered'))
            continue
        try:
            row = test(scene, item, room)
        except ValueError as exc:  # the offline trace's own cycle/size guard
            row = dict(item, point=[round(v, 3) for v in item['point']], result='untestable',
                       detail=dict(status='trace limit', error=str(exc)))
        if row['result'] == 'failed' and proxy is not None:
            # The collision surface the step's upper side meets (point hull).
            px, py = x + d[0] * o, y + d[1] * o
            try:
                hit = proxy.trace((px, py, top + 64), (px, py, top - 2))
            except ValueError:
                hit = None  # diagnostic only
            if hit:
                row['collision_angle'] = round(math.degrees(math.acos(max(-1., min(1., hit['normal'][2])))), 2)
                row['collision_height_over_step'] = round(64 - 66 * hit['fraction'], 2)
        rows.append(row)
    return rows


def check_map(task):
    """Worker: _faces + Collision + check_polys for one map; TASK (path, core, models[, scope])."""
    path, core, models = task[:3]
    scope = task[3] if len(task) > 3 else 'all'
    raw = Path(path).read_bytes()
    polys = _faces(raw)
    items = candidates(polys, core)
    if scope == 'flights':
        items = flight_items(items)
    if not items:
        return Path(path).stem, []
    world = Scene(raw, hull=0)
    rows = _check_items(items, polys, Collision(raw), lambda p: _contents(world, p), Collision(raw, hull=0))
    for row in rows:
        row['map'] = Path(path).stem
        row['model'] = models.get(str(row['ref']), '')
    return Path(path).stem, rows


def check_map_cached(task):
    """Worker: check_map, or the rows recorded for the same map bytes, core,
    models and stair rule (pass_cache.py, development builds only;
    BUILD-IMAGE-NOT-INCREMENTAL-33)."""
    path, core, models, cache = task[:4]
    scope = task[4] if len(task) > 4 else 'all'
    if cache is None:
        return check_map((path, core, models, scope))
    import hashlib, json
    raw = Path(path).read_bytes()
    key = hashlib.sha256(raw).hexdigest() + ':' + json.dumps(core)
    found = cache.load(key)
    name = Path(path).stem
    if found is not None:
        # Same keys in the same order; only the map name is this map's (aliases share bytes).
        return name, [{k: (name if k == 'map' else v) for k, v in row.items()} for row in found[0]['rows']]
    name, rows = check_map((path, core, models, scope))
    rows = json.loads(json.dumps(rows))  # the form cached rows have
    cache.store(key, {'rows': rows})
    return name, rows


def map_tasks(id1, models=None, only=None):
    """(map, core, ref->model) for every map of the payload: town regions with
    their cores, every other map (interiors, open-world regions) whole. Town
    alias maps (copies of a region under the town's name) are skipped."""
    from town_config import runtime_towns
    from arrival_spot import read_directory
    id1 = Path(id1); tasks = []; seen = set()
    aliases = {t['name'] for t in runtime_towns()}
    for town in runtime_towns():
        directory = id1 / town['regions']
        if not directory.is_file():
            continue
        for row in read_directory(directory)['regions']:
            seen.add(row['name'])
            path = id1 / 'maps' / (row['name'] + '.bsp')
            if path.is_file() and (not only or row['name'] in only):
                tasks.append((str(path), row['core'], models or {}))
    for path in sorted((id1 / 'maps').glob('*.bsp')):
        if path.stem in seen or path.stem in aliases or (only and path.stem not in only):
            continue
        tasks.append((str(path), None, models or {}))
    return tasks


def _map_cost(task):
    """Dispatch order of the pass: the map's size (a missing file sorts last; check_map reports it)."""
    import os
    try:
        return os.path.getsize(task[0])
    except OSError:
        return 0


def family(name):
    head = re.sub(r'\d+$', '', name)
    return head if head in ('sn', 'bm', 'va', 'vf') else 'interiors and other maps'


def check(id1, jobs=1, only=None, models=None, exempt=(), scope=None):
    """The gate over a payload; exempt: maps whose blocking failures are
    reported but do not fail it (a recorded, owner-approved stage); scope: 'all'
    (every step and ramp) or 'flights' (only the steps of flights, the rows that can
    fail the gate); default from AMIWIND_STAIR_WALK, else 'all'."""
    from build_parallel import ordered_map
    from mesh_geometry_env import stair_mode
    from pass_cache import PassCache
    import hashlib
    scope = scope or scope_setting()
    if scope not in SCOPES:
        raise ValueError('Stair walk scope must be one of %s, not %r' % (', '.join(SCOPES), scope))
    tasks = map_tasks(id1, models, only)
    # Development builds (and release builds with --allow-release-reuse) reuse rows for
    # unchanged map bytes (pass_cache.py).
    options = {'stair_mode': stair_mode(), 'models': hashlib.sha256(
        json.dumps(models or {}, sort_keys=True).encode()).hexdigest()}
    if scope != 'all':
        options['scope'] = scope
    cache = PassCache.open('stair-walk', options, __file__)
    rows = []
    try:
        # Largest maps first (their walks take longest; a big map dispatched last left most
        # workers idle at the end of the pass); rows still come back in map order.
        for name, found in ordered_map(check_map_cached, [(*task, cache, scope) for task in tasks],
                                       max(1, min(jobs, len(tasks) or 1)), cost=_map_cost):
            rows.extend(found)
    finally:
        cached = cache.summary() if cache is not None else None
    exempt = set(exempt)
    failures = [r for r in rows if _gating(r) and r['map'] not in exempt]
    exempted = [r for r in rows if _gating(r) and r['map'] in exempt]
    advisory = [r for r in rows if r['result'] == 'failed' and not _gating(r)]
    summary = {}
    for r in rows:
        kind = 'flight step' if r['kind'] == 'step' and r.get('flight') else r['kind']
        bucket = summary.setdefault(family(r['map']), {}).setdefault(kind, {})
        bucket[r['result']] = bucket.get(r['result'], 0) + 1
    report = dict(format=1, status='failed' if failures else 'passed', maps=len(tasks), step_height=STEP_HEIGHT,
                  walkable_normal_z=WALKABLE_Z, walkable_degrees=round(math.degrees(math.acos(WALKABLE_Z)), 2),
                  reference='Morrowind (OpenMW 0.51): step 8.5 (34 units), slope 46 degrees, authored collision',
                  gate='flights of stairs (3+ steps, 2+ vertical risers) the standing box cannot walk up and down',
                  summary=summary, failures=failures, exempt_failures=exempted, advisory_failures=advisory,
                  rows=rows)
    if scope != 'all':
        report['scope'] = ('flight steps only (release build): ramps and single steps are not walked; '
                           'their advisory findings come from a full walk (development or nightly build)')
    if cached is not None:
        report['pass_cache'] = cached
        print('Stair walk pass cache: %d maps reused, %d walked.' % (cached['hits'], cached['misses']), flush=True)
    return report


def accept_known(report, accepted):
    """Move failures on the placements of accepted known stair findings ({ref: tracker ID}, from
    chim.known.known_stair_findings; private -devN tests only, the caller checks the version) to
    accepted_known_findings, each with its ID. Nothing is dropped; every other failure still gates."""
    if not accepted:
        return report
    by_ref = {str(ref): fid for ref, fid in accepted.items()}
    report['accepted_known_findings'] = [dict(r, finding=by_ref[str(r['ref'])]) for r in report['failures']
                                         if str(r['ref']) in by_ref]
    report['failures'] = [r for r in report['failures'] if str(r['ref']) not in by_ref]
    report['accepted_ids'] = sorted(set(accepted.values()))
    if not report['failures'] and report['accepted_known_findings']:
        report['status'] = 'passed with accepted known findings'
    return report


def require(id1, output, jobs=1, only=None, models=None, exempt=(), accepted=None):
    """accepted: {placement ref: tracker ID} of known stair findings a private -devN test accepts
    (accept_known)."""
    report = accept_known(check(id1, jobs, only, models, exempt), accepted)
    Path(output).write_text(json.dumps(report, indent=1) + '\n', newline='\n')
    if report['failures']:
        first = report['failures'][0]
        raise ValueError('Stair walkability gate failed: %d flight steps cannot be walked (first %s ref %s at %s, rise %s); see %s'
                         % (len(report['failures']), first['map'], first['ref'], first['point'], first.get('rise'), output))
    return report


BLOCKING = ('blocked', 'start in solid', 'standing hull in solid', 'no floor ahead')


def _gating(row):
    """A failure that gates the build: a flight step the standing box cannot
    climb or descend (blocked, or collision solid where the visuals are open).
    Collision lower than the visuals ('did not rise') or missing under the
    approach ('no floor at start') is reported as advisory (a surface fidelity
    finding, COLLISION-CONVEX-LOSS-32), as are lone steps and ramps."""
    return (row['result'] == 'failed' and row['kind'] == 'step' and bool(row.get('flight'))
            and row['detail'].get('status') in BLOCKING)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('id1', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--maps', nargs='*')
    parser.add_argument('--jobs', type=int, default=1)
    parser.add_argument('--scope', choices=SCOPES, help="'all' (default, or AMIWIND_STAIR_WALK) or 'flights'")
    a = parser.parse_args()
    report = check(a.id1, a.jobs, a.maps, scope=a.scope)
    a.out.write_text(json.dumps(report, indent=1) + '\n', newline='\n')
    print(json.dumps(dict(status=report['status'], summary=report['summary'], failures=len(report['failures']))))
    return 1 if report['failures'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
