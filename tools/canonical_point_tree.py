# SPDX-License-Identifier: GPL-3.0-only
"""Compact point hull for authored canonical LAND; not a standing-hull builder.

XY coverage is half open. Positive roof equality selects EMPTY; points below the
roof and at/above the collision bottom select SOLID. This canonical contract
does not reproduce qbsp's arbitrary float32 CSG equality choices at shared edges.
The caller must preserve separately compiled standing hulls and water contents.
"""
import heapq
import math
import struct

import numpy as np

EMPTY = -1
SOLID = -2
SPACING = 32
TRACE_EPSILON = 0.03125


def build_point_tree(land, bounds, bottom=-512.0):
    """Return (planes, nodes, root, audit), with logical negative contents.

    Nodes have (plane, front, back); all positive child indices follow parents.
    A BSP writer must translate EMPTY/SOLID into its real leaf indices. No
    existing collision/render/PVS records are modified by this function.
    """
    try:
        low, high = [list(map(float, v)) for v in bounds]
        origin = list(map(float, land.origin))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError('Explicit finite aligned bounds and LAND origin required') from exc
    if (len(low) != 2 or len(high) != 2 or len(origin) != 3
            or not all(math.isfinite(v) for v in (*low, *high, *origin, bottom))
            or any(low[k] >= high[k] for k in (0, 1))
            or any(v % SPACING for v in (*low, *high, *origin[:2]))):
        raise ValueError('Finite nonempty 32-aligned bounds and origin lattice required')
    x0, y0 = [int(v / SPACING) for v in low]
    x1, y1 = [int(v / SPACING) for v in high]
    triangles = {}
    corners = {}
    for triangle in land.triangles(bounds):
        q = np.asarray(triangle, dtype=float)
        if q.shape != (3, 3) or not np.isfinite(q).all():
            raise ValueError('Finite canonical triangle required')
        if any(float(v) % SPACING for v in q[:, :2].flat):
            raise ValueError('Canonical triangle corners must follow the origin lattice')
        key = tuple(math.floor(float(v) / SPACING) for v in q[:, :2].mean(axis=0))
        if not (x0 <= key[0] < x1 and y0 <= key[1] < y1):
            raise ValueError('Canonical triangle outside requested coverage')
        for x, y, z in q:
            xy = (float(x), float(y))
            if xy in corners and corners[xy] != z:
                raise ValueError('Discontinuous canonical shared grid corner')
            corners[xy] = float(z)
        if float(q[:, 2].min()) <= bottom:
            raise ValueError('Collision bottom must be below every canonical vertex')
        triangles.setdefault(key, []).append(q)
    if (len(triangles) != (x1-x0)*(y1-y0)
            or any(len(v) != 2 for v in triangles.values())):
        raise ValueError('Incomplete canonical tile coverage')

    planes, nodes, plane_ids, node_ids = [], [], {}, {}
    rounding_bound = native_bound = 0.0
    gamma = 7 * 2**-24 / (1 - 7 * 2**-24)

    def plane(normal, distance, kind=3):
        n = np.asarray(normal, dtype=float)
        length = float(np.linalg.norm(n))
        if not math.isfinite(length) or length == 0:
            raise ValueError('Finite nonzero plane required')
        raw = struct.pack('<4fi', *(n/length), distance/length, kind)
        if raw not in plane_ids:
            plane_ids[raw] = len(planes)
            planes.append(tuple(struct.unpack('<4fi', raw)))
        return plane_ids[raw]

    def node(index, front, back):
        if front == back:
            return front
        key = (index, front, back)
        if key not in node_ids:
            node_ids[key] = len(nodes)
            nodes.append(key)
        return node_ids[key]

    def tile(x, y):
        nonlocal rounding_bound, native_bound
        a = np.array([x*32, y*32])
        b, c, d = a+[32, 0], a+[32, 32], a+[0, 32]
        wanted = [set(map(tuple, [a, b, c])), set(map(tuple, [a, c, d]))]
        parts = []
        for expected in wanted:
            found = [q for q in triangles[x, y] if set(map(tuple, q[:, :2])) == expected]
            if len(found) != 1:
                raise ValueError('Canonical diagonal must be (0,1,2)/(0,2,3)')
            parts.append(found[0])
        indices, gradients, errors, native_errors = [], [], [], []
        for q in parts:
            normal = np.cross(q[1]-q[0], q[2]-q[0])
            if normal[2] < 0:
                normal = -normal
            if normal[2] <= 0:
                raise ValueError('Canonical roof must have positive Z normal')
            index = plane(normal, float(normal@q[0]))
            p = np.asarray(planes[index][:4])
            gradients.append(-normal[:2]/normal[2])
            square = np.asarray([a, b, c, d], dtype=float)
            extrapolated = q[0, 2]+(square-q[0, :2])@gradients[-1]
            domain = np.column_stack((square, extrapolated))
            error = float(np.abs(domain@p[:3]-p[3]).max()/p[2])
            arithmetic = gamma * float((np.abs(domain*p[:3]).sum(axis=1)+abs(p[3])).max())/p[2]
            errors.append(error)
            native_errors.append(error+arithmetic)
            indices.append(index)
        # The two affine roofs agree on the authored diagonal. On either side,
        # the intended height is their min (ridge) or max (valley), so no rounded
        # XY diagonal plane is needed in the collision representation.
        extrapolated_b = parts[1][0, 2]+float((b-parts[1][0, :2])@gradients[1])
        use_max = corners[tuple(b)] > extrapolated_b
        rounding_bound = max(rounding_bound, max(errors))
        native_bound = max(native_bound, max(native_errors))
        second = node(indices[1], EMPTY, SOLID)
        if indices[0] == indices[1]:
            return second
        return node(indices[0], second, SOLID) if use_max else node(indices[0], EMPTY, second)

    def partition(ax, ay, bx, by):
        if bx-ax == by-ay == 1:
            return tile(ax, ay)
        if bx-ax >= by-ay:
            mid = (ax+bx)//2
            return node(plane([1, 0, 0], mid*32, 0),
                        partition(mid, ay, bx, by), partition(ax, ay, mid, by))
        mid = (ay+by)//2
        return node(plane([0, 1, 0], mid*32, 1),
                    partition(ax, mid, bx, by), partition(ax, ay, bx, mid))

    root = partition(x0, y0, x1, y1)
    for axis in (0, 1):
        normal = [0, 0, 0]
        normal[axis] = 1
        root = node(plane(normal, low[axis], axis), root, EMPTY)
        root = node(plane(normal, high[axis], axis), EMPTY, root)
    root = node(plane([0, 0, 1], bottom, 2), root, EMPTY)
    if not math.isfinite(native_bound) or native_bound >= TRACE_EPSILON:
        raise ValueError('Canonical point precision exceeds existing native trace epsilon')
    if len(nodes) > 32767:
        raise ValueError('Canonical point DAG exceeds BSP29 node index limit')
    indegree = [0]*len(nodes)
    for _, front, back in nodes:
        for child in (front, back):
            if child >= 0:
                indegree[child] += 1
    pending = [i for i, degree in enumerate(indegree) if degree == 0]
    heapq.heapify(pending)
    order = []
    while pending:
        old = heapq.heappop(pending)
        order.append(old)
        for child in nodes[old][1:]:
            if child >= 0:
                indegree[child] -= 1
                if indegree[child] == 0:
                    heapq.heappush(pending, child)
    if len(order) != len(nodes):
        raise ValueError('Canonical point DAG cycle')
    remap = {old: new for new, old in enumerate(order)}
    output = [(pi, *(remap[c] if c >= 0 else c for c in (front, back)))
              for pi, front, back in (nodes[old] for old in order)]
    audit = {'tiles': len(triangles), 'source_triangles': len(triangles)*2,
             'nodes': len(output), 'planes': len(planes), 'bounds': [low, high],
             'bottom': bottom, 'maximum_plane_vertical_error_bound': rounding_bound,
             'maximum_native_float32_vertical_error_bound': native_bound,
             'existing_native_trace_epsilon': TRACE_EPSILON,
             'error_bound_domain': 'both affine roofs over all four tile corners; min/max is 1-Lipschitz',
             'contract': 'half-open XY; roof min/max with positive roof equality EMPTY; bottom equality SOLID',
             'qbsp_exact_equality': 'changed semantics; not byte/equality equivalent',
             'standing_and_water': 'separate; caller must preserve and validate'}
    return planes, output, remap[root], audit
