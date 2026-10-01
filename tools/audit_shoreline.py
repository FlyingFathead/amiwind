#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Compare emitted terrain triangles with every surveyed LAND height sample."""
import argparse
import json
from pathlib import Path
import time

import numpy as np
from prepare_world_regions import Terrain, terrain_triangles, SCALE, STEP


def surface(triangles, points):
    heights = np.full(len(points), np.nan)
    for tri in triangles:
        a, b, c = np.asarray(tri, dtype=float)
        denominator = (b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if denominator <= 0:
            raise ValueError('Degenerate or reversed terrain triangle')
        u = ((b[1]-c[1])*(points[:, 0]-c[0])+(c[0]-b[0])*(points[:, 1]-c[1]))/denominator
        v = ((c[1]-a[1])*(points[:, 0]-c[0])+(a[0]-c[0])*(points[:, 1]-c[1]))/denominator
        covered = (u >= -1e-8) & (v >= -1e-8) & (u+v <= 1+1e-8)
        values = u*a[2]+v*b[2]+(1-u-v)*c[2]
        overlap = covered & np.isfinite(heights)
        if np.any(np.abs(heights[overlap]-values[overlap]) > 1e-5):
            raise ValueError('Overlapping triangles disagree')
        heights[covered] = values[covered]
    if not np.isfinite(heights).all():
        raise ValueError('Uncovered source sample')
    return heights


def audit(survey):
    started = time.monotonic()
    terrain = Terrain(Path(survey))
    offsets = np.array([(x, y) for y in range(0, STEP+1, 32) for x in range(0, STEP+1, 32)])
    u, v = offsets[:, 0]/STEP, offsets[:, 1]/STEP
    result = dict(tiles=0, refined_tiles=0, sample_comparisons=0,
                  coarse_dry_samples_drowned=0, coarse_wet_samples_raised=0,
                  rebuilt_wet_dry_mismatches=0, shared_edges_checked=0, failures=[])
    for cx, cy in sorted(terrain.cells):
        for dy in range(0, 2048, STEP):
            for dx in range(0, 2048, STEP):
                x, y = cx*2048+dx, cy*2048+dy
                points = offsets + [x, y]
                actual = np.array([terrain.sample(px, py)[0] for px, py in points])
                a, b, c, d = actual[[0, 4, 24, 20]]
                coarse = np.where(v <= u, a+(b-a)*u+(c-b)*v, a+(c-d)*u+(d-a)*v)
                dry = actual >= 0
                result['coarse_dry_samples_drowned'] += int(np.sum(dry & (coarse < 0)))
                result['coarse_wet_samples_raised'] += int(np.sum(~dry & (coarse >= 0)))
                refined = terrain.shoreline_detail(x, y)
                if refined:
                    triangles = list(terrain_triangles(terrain, x, y))
                    rebuilt = surface(triangles, points)
                    # Check both directions: a neighbour need not be refined.
                    for axis, edge, nx, ny in ((0, x+STEP, x+STEP, y), (1, y+STEP, x, y+STEP)):
                        adjacent = list(terrain_triangles(terrain, nx, ny))
                        boundary = lambda ts: {tuple(p) for tri in ts for p in tri if p[axis] == edge}
                        if boundary(triangles) != boundary(adjacent):
                            raise ValueError(f'Shared edge mismatch at {x},{y}, axis {axis}')
                        result['shared_edges_checked'] += 1
                else:
                    rebuilt = coarse
                bad = dry != (rebuilt >= -1e-7)
                result['rebuilt_wet_dry_mismatches'] += int(np.sum(bad))
                if bad.any() and len(result['failures']) < 20:
                    result['failures'].append(dict(tile=[x, y], samples=points[bad].tolist()))
                result['tiles'] += 1
                result['refined_tiles'] += int(refined)
                result['sample_comparisons'] += len(points)
    result['seconds'] = round(time.monotonic()-started, 3)
    result['status'] = 'passed' if result['rebuilt_wet_dry_mismatches'] == 0 else 'failed'
    result['water_policy'] = 'Surveyed exterior CELL water levels must all be zero; other levels fail conversion.'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--survey', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.survey)
    with args.out.open('x') as out:
        out.write(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
