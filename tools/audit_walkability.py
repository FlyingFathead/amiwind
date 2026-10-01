#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Offline standing-hull floor/step scan of a converted BSP29 scene.

Reports candidate falls and reachable scan edges; it does not invent geometry
or certify visual closure. Coordinates and heights are native player origins.
Dynamic actors, opening barriers and script-driven door poses are not simulated.
"""
import argparse
from collections import Counter, deque
import hashlib
import json
import math
from pathlib import Path
import re
import struct
from player_hull import lumps, PROFILE, WALKABLE_Z


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def axes(angles):
    p, y, r = map(math.radians, angles)
    sp, cp, sy, cy, sr, cr = math.sin(p), math.cos(p), math.sin(y), math.cos(y), math.sin(r), math.cos(r)
    return ((cp*cy, cp*sy, -sp), (sr*sp*cy-cr*sy, sr*sp*sy+cr*cy, sr*cp),
            (cr*sp*cy+sr*sy, cr*sp*sy-sr*cy, cr*cp))


class Scene:
    def __init__(self, raw, hull=1):
        if hull not in (0,1): raise ValueError('Expected point or standing hull')
        data = lumps(raw)
        entities = [dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"', block))
                    for block in re.findall(r'\{[^{}]*\}', data[0].decode('cp1252'))]
        if not entities or entities[0].get('aw_hull') != PROFILE:
            raise ValueError('Scene must declare the converted humanoid standing hull')
        self.sha256 = hashlib.sha256(raw).hexdigest()
        self.planes = list(struct.iter_unpack('<4fi', data[1]))
        self.nodes = [(p,a+65536 if a < -15 else a,b+65536 if b < -15 else b)
                      for p,a,b in struct.iter_unpack('<ihh', data[9])]
        if hull==0:
            leaves=[r[0] for r in struct.iter_unpack('<ii6h2H4B',data[10])]
            def child(n): return n if n>=0 else leaves[-n-1]
            self.nodes=[(r[0],child(r[1]),child(r[2])) for r in struct.iter_unpack('<ihh6h2H',data[5])]
        models = list(struct.iter_unpack('<9f7i', data[14]))
        if not models:
            raise ValueError('Missing BSP models')
        # Validate every branch, then cycles while walking only visited paths.
        for plane, front, back in self.nodes:
            if not 0 <= plane < len(self.planes) or max(front, back) >= len(self.nodes):
                raise ValueError('Invalid collision node')
        self.brushes = []
        for e in [dict(model='*0', aw_ref='world'), *entities]:
            if not re.fullmatch(r'\*\d+', e.get('model', '')):
                continue
            if e['model'] != '*0' and e.get('classname') != 'func_wall':
                continue
            index = int(e['model'][1:])
            if index >= len(models):
                raise ValueError('Invalid brush model')
            origin = tuple(map(float, e.get('origin', '0 0 0').split()))
            angles = tuple(map(float, e.get('angles', '0 0 0').split()))
            if len(origin) != 3 or len(angles) != 3 or not all(map(math.isfinite, (*origin, *angles))):
                raise ValueError('Invalid brush transform')
            root = models[index][9+hull]  # point or expanded standing hull
            if root >= len(self.nodes):
                raise ValueError('Invalid hull root')
            self.brushes.append((root, origin, axes(angles), e.get('aw_ref', e['model'])))

    def _trace_brushes(self, start, end):
        return self.brushes

    def trace(self, start, end):
        """First solid interval on a segment through each rotated standing hull."""
        best = None
        for root, origin, basis, ref in self._trace_brushes(start, end):
            a = tuple(dot(tuple(start[i]-origin[i] for i in range(3)), axis) for axis in basis)
            b = tuple(dot(tuple(end[i]-origin[i] for i in range(3)), axis) for axis in basis)
            stack = [(root, 0., 1., None, False)]; visits = 0; states = {}
            while stack:
                node, lo, hi, normal, done = stack.pop()
                key = (node, lo, hi)
                if done:
                    states[key] = 2
                    continue
                if states.get(key) == 1:
                    raise ValueError('Cyclic collision tree')
                if states.get(key) == 2:
                    continue
                # A split exactly at an endpoint has no interval on one side.
                # Following that empty branch through shared convex tails can
                # multiply visits without adding any possible collision.
                if hi-lo <= 1e-10:
                    continue
                if best and lo >= best['fraction']:
                    continue
                states[key] = 1
                stack.append((node, lo, hi, normal, True))
                visits += 1
                if visits > max(4096,len(self.nodes)*32):
                    raise ValueError('Cyclic or excessive collision tree')
                if node < 0:
                    if node == -2:
                        world_normal = tuple(sum(normal[j]*basis[j][i] for j in range(3)) for i in range(3)) if normal else (0., 0., 0.)
                        best = dict(fraction=lo, normal=world_normal, reference=ref)
                    continue
                pi, front, back = self.nodes[node]; plane = self.planes[pi]
                da, db = dot(a, plane[:3])-plane[3], dot(b, plane[:3])-plane[3]
                dl, dh = da+(db-da)*lo, da+(db-da)*hi
                if dl >= 0 and dh >= 0:
                    stack.append((front, lo, hi, normal, False)); continue
                if dl < 0 and dh < 0:
                    stack.append((back, lo, hi, normal, False)); continue
                mid = min(hi, max(lo, -da/(db-da)))
                first, second = (front, back) if dl >= 0 else (back, front)
                entering = tuple(v*(1 if dl >= 0 else -1) for v in plane[:3])
                stack.append((second, mid, hi, entering, False))
                stack.append((first, lo, mid, normal, False))
        return best

    def floor(self, point, drop):
        hit = self.trace(point, (point[0], point[1], point[2]-drop))
        result = dict(point=list(point), status='unsupported')
        if hit:
            result.update(hit)
            result['height'] = point[2]-drop*hit['fraction']
            result['status'] = 'blocked' if hit['fraction'] == 0 else 'supported' if hit['normal'][2] >= WALKABLE_Z else 'steep'
        return result


def scan(scene, bounds, height, spacing=4., drop=16., seed=None, step=4.5):
    x0, y0, x1, y1 = bounds
    nx, ny = int((x1-x0)/spacing)+1, int((y1-y0)/spacing)+1
    if nx <= 0 or ny <= 0 or nx*ny > 100000:
        raise ValueError('Scan requires 1..100000 samples')
    cells = [scene.floor((x0+x*spacing, y0+y*spacing, height), drop) for y in range(ny) for x in range(nx)]
    reachable, falls, edges = set(), set(), set()
    if seed:
        sx, sy = round((seed[0]-x0)/spacing), round((seed[1]-y0)/spacing)
        if not (0 <= sx < nx and 0 <= sy < ny) or cells[sy*nx+sx]['status'] != 'supported':
            raise ValueError('Seed must be a supported sample in the scan bounds')
        queue = deque([sy*nx+sx]); reachable.add(sy*nx+sx)
        while queue:
            n = queue.popleft(); x, y = n % nx, n // nx; a = cells[n]
            pa = (*a['point'][:2], a['height']+.125)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                xx, yy = x+dx, y+dy
                if not (0 <= xx < nx and 0 <= yy < ny):
                    edges.add(n); continue
                j = yy*nx+xx; b = cells[j]
                if b['status'] == 'unsupported':
                    if not scene.trace(pa, (*b['point'][:2], pa[2])):
                        falls.add(j)
                elif b['status'] == 'supported' and j not in reachable and abs(b['height']-a['height']) <= step:
                    z = max(a['height'], b['height'])+.125
                    aa, bb = (*pa[:2], z), (*b['point'][:2], z)
                    if not scene.trace(pa, aa) and not scene.trace(aa, bb):
                        reachable.add(j); queue.append(j)
    return dict(bsp_sha256=scene.sha256, hull=PROFILE, bounds=list(bounds), height=height,
                spacing=spacing, drop=drop, shape=[nx, ny], summary=dict(Counter(c['status'] for c in cells)),
                reachable_count=len(reachable), reachable=sorted(reachable),
                possible_fall_samples=sorted(falls), reachable_scan_edges=sorted(edges), samples=cells,
                limitations='Static standing hulls; finite sampling can miss smaller gaps. Edge flags need inspection. Visual walls, actors, scripted poses and barriers require separate checks.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('bsp', type=Path); p.add_argument('--out', required=True, type=Path)
    p.add_argument('--bounds', nargs=4, type=float, required=True, metavar=('X0','Y0','X1','Y1'))
    p.add_argument('--height', type=float, required=True)
    p.add_argument('--spacing', type=float, default=4); p.add_argument('--drop', type=float, default=16)
    p.add_argument('--seed', nargs=2, type=float)
    p.add_argument('--probe', nargs=3, type=float, action='append', default=[])
    a = p.parse_args()
    if not all(math.isfinite(v) for v in [*a.bounds, a.height, a.spacing, a.drop, *(a.seed or []), *sum(a.probe, [])]) or a.spacing <= 0 or a.drop <= 0:
        p.error('Finite coordinates and positive spacing/drop required')
    scene = Scene(a.bsp.read_bytes()); report = scan(scene, a.bounds, a.height, a.spacing, a.drop, a.seed)
    report['probes'] = [scene.floor(point, a.drop) for point in a.probe]
    a.out.parent.mkdir(parents=True, exist_ok=True); a.out.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: report[k] for k in ('summary', 'reachable_count', 'probes')}))
    return 2 if any(p['status'] != 'supported' for p in report['probes']) else 0


if __name__ == '__main__':
    raise SystemExit(main())
