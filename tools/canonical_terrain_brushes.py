# SPDX-License-Identifier: GPL-3.0-only
"""Exact canonical LAND prisms shared by rendered and collision BSP compilation."""
import math
from collections import defaultdict
import numpy as np


def canonical_prisms(land, bounds, bottom=-512.0):
    """Return complete authored tiles; never sample water or invent missing LAND."""
    low, high = bounds
    aligned = [[math.floor(v / 32) * 32 for v in low],
               [math.ceil(v / 32) * 32 for v in high]]
    triangles = list(land.triangles(aligned))
    expected = int((aligned[1][0]-aligned[0][0]) * (aligned[1][1]-aligned[0][1]) / 512)
    if len(triangles) != expected:
        raise ValueError('Incomplete canonical LAND coverage')
    if not math.isfinite(bottom) or any(p[2] <= bottom for t in triangles for p in t):
        raise ValueError('Collision prism bottom must lie below every authored terrain vertex')
    groups = defaultdict(list)
    for tri in triangles:
        q = np.asarray(tri, dtype=float)
        sample = land.sample(*q.mean(axis=0)[:2])
        if sample is None:
            raise ValueError('Missing canonical material coverage')
        n = np.cross(q[1]-q[0], q[2]-q[0])
        dx, dy = -n[:2]/n[2]
        groups[(float(dx),float(dy),float(q[0,2]-dx*q[0,0]-dy*q[0,1]),sample['material'])].append(q)
    from terrain_visual_cull import merge_convex_parts
    result = []
    for key, parts in groups.items():
      for q in merge_convex_parts(parts):
        count = len(q)
        points = np.concatenate((q, np.column_stack((q[:, :2], np.full(count, bottom)))))
        center = points.mean(axis=0)
        lines = ['{']
        faces = [(0,1,2),(count,count+1,count+2)] + [(i,(i+1)%count,(i+1)%count+count) for i in range(count)]
        for ids in faces:
            a, b, c = points[list(ids)]
            if np.dot(np.cross(a-b, c-b), center-a) > 0:
                b, c = c, b
            positions = ' '.join('( '+' '.join(format(float(v), '.17g') for v in p)+' )' for p in (a,b,c))
            lines.append(positions+' g'+str(key[3])+' 0 0 0 1 1')
        result.append('\n'.join(lines+['}']))
    return result, {'canonical': land.metadata(), 'bounds': aligned,
                    'source_triangles': len(triangles), 'convex_prisms': len(result),
                    'coalescing': 'exact affine plane/material groups; shared edges; convex area-preserving union',
                    'render_and_collision_source': 'same exact canonical MAP planes',
                    'bottom_role': 'collision closure only; final canonical visual pass removes buried render closure'}
