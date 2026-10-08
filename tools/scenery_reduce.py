# SPDX-License-Identifier: GPL-3.0-only
"""Measured scenery reductions for the mesh converter (both off by default).

--texinfo-snap TEXELS
    Edge-connected triangles of one material share one texture mapping (a
    Quake texinfo: a 3D affine map, so it may span several planes) while it
    reproduces every member's own texture coordinates within 3/4 of TEXELS
    at every vertex (modulo whole-texture repeats); coplanar members merge
    into larger convex faces. A face reuses an existing texinfo of the map
    that matches within the remaining 1/4 of TEXELS (modulo the texture
    size), so no face moves by more than TEXELS in total. A shared mapping that would change a face's engine
    mip factor is stored as the face's exactly equal in-plane mapping.
    TEXELS are texels of the converted (shipped) texture.
--scenery-reduce ERROR
    Visual meshes of scenery are simplified per UV chart with quadric edge
    collapse (fast-simplification). Chart borders (open edges, UV seams and
    material boundaries) are locked, so joins stay watertight and UVs stay
    continuous. A reduction is kept only if its two-sided surface distance
    stays within ERROR map units (model scale), its texture coordinates within
    the texel bound and no triangle turns over. Collision proxies always use
    the original mesh; meshes with their own LOD profile are left alone.

The options are read from AMIWIND_TEXINFO_SNAP / AMIWIND_SCENERY_REDUCE (and
AMIWIND_SCENERY_REDUCE_TEXELS, default 1/8) so converter worker processes see
them; add_options() puts them on a converter's command line.
"""
import os


class _LazyNumpy:
    """numpy is loaded on first use: tools/build.py imports this module's option helpers while it is
    still running on the system Python, before the tools environment (with numpy) exists."""
    def __getattr__(self, name):
        import numpy
        globals()['np'] = numpy
        return getattr(numpy, name)


np = _LazyNumpy()

DEFAULT_REDUCE_TEXELS = 1/8
# Share of the --texinfo-snap budget used when one texinfo of the map is
# reused for another placement; the rest bounds the per-mesh mapping fit, so
# a face never moves by more than the requested TEXELS in total.
MAP_SHARE_FRACTION = 0.25
MIN_CHART_TRIANGLES = 6


def _number(name):
    text = os.environ.get(name, '').strip()
    if not text:
        return None
    if '/' in text:
        a, b = text.split('/', 1)
        value = float(a)/float(b)
    else:
        value = float(text)
    if not value > 0:
        raise ValueError(f'{name} must be positive')
    return value


def texinfo_snap():
    """Snap tolerance in texels, or None (off)."""
    return _number('AMIWIND_TEXINFO_SNAP')


def snap_budget():
    """(per-mesh fit, map-level reuse) tolerances in texels, or None."""
    total = texinfo_snap()
    if total is None:
        return None
    return total*(1-MAP_SHARE_FRACTION), total*MAP_SHARE_FRACTION


def scenery_reduce():
    """(error in map units, texel bound) or None (off)."""
    error = _number('AMIWIND_SCENERY_REDUCE')
    if error is None:
        return None
    return error, _number('AMIWIND_SCENERY_REDUCE_TEXELS') or DEFAULT_REDUCE_TEXELS


def add_options(parser):
    parser.add_argument('--texinfo-snap', metavar='TEXELS',
                        help='Share texture mappings within TEXELS (e.g. 1/16); off by default')
    parser.add_argument('--scenery-reduce', metavar='ERROR',
                        help='Simplify scenery visual meshes within ERROR map units; off by default')
    parser.add_argument('--scenery-reduce-texels', metavar='TEXELS',
                        help='Texture-coordinate bound for --scenery-reduce (default 1/8)')


def apply_options(args):
    """Export parsed options to the environment (inherited by workers)."""
    for value, name in ((args.texinfo_snap, 'AMIWIND_TEXINFO_SNAP'),
                        (args.scenery_reduce, 'AMIWIND_SCENERY_REDUCE'),
                        (args.scenery_reduce_texels, 'AMIWIND_SCENERY_REDUCE_TEXELS')):
        if value is not None:
            os.environ[name] = str(value)
    texinfo_snap()
    scenery_reduce()


def eligible(profile):
    """Scenery meshes the reduction may touch: no own reducing LOD profile
    (ratio below 1), flattening or collision-only representation."""
    return not (profile.get('ratio', 1) < 1 or 'flatten' in profile or profile.get('collision_only'))


# ---------------------------------------------------------------- geometry

def closest_points(points, triangles):
    """Closest point on each triangle (t,3,3) for each point (p,3).

    Returns (distance (p,t), barycentric (p,t,3)); Ericson's region test.
    """
    a = triangles[None, :, 0]; b = triangles[None, :, 1]; c = triangles[None, :, 2]
    p = points[:, None, :]
    ab = b-a; ac = c-a; ap = p-a
    d1 = (ab*ap).sum(-1); d2 = (ac*ap).sum(-1)
    bp = p-b; d3 = (ab*bp).sum(-1); d4 = (ac*bp).sum(-1)
    cp = p-c; d5 = (ab*cp).sum(-1); d6 = (ac*cp).sum(-1)
    va = d3*d6-d5*d4; vb = d5*d2-d1*d6; vc = d1*d4-d3*d2
    shape = d1.shape
    w = np.zeros(shape+(3,))
    tiny = 1e-30
    # Interior first, then overwrite with edge/vertex regions.
    denom = va+vb+vc
    denom = np.where(abs(denom) < tiny, tiny, denom)
    v_ = vb/denom; w_ = vc/denom
    w[..., 0] = 1-v_-w_; w[..., 1] = v_; w[..., 2] = w_
    def put(mask, bary):
        for k in range(3):
            w[..., k] = np.where(mask, bary[k], w[..., k])
    # Edge BC.
    m = (va <= 0) & (d4-d3 >= 0) & (d5-d6 >= 0)
    t = (d4-d3)/np.where(abs((d4-d3)+(d5-d6)) < tiny, tiny, (d4-d3)+(d5-d6))
    put(m, (0, 1-t, t))
    # Edge AC.
    m = (vb <= 0) & (d2 >= 0) & (d6 <= 0)
    t = d2/np.where(abs(d2-d6) < tiny, tiny, d2-d6)
    put(m, (1-t, 0, t))
    # Edge AB.
    m = (vc <= 0) & (d1 >= 0) & (d3 <= 0)
    t = d1/np.where(abs(d1-d3) < tiny, tiny, d1-d3)
    put(m, (1-t, t, 0))
    # Vertices.
    put((d6 >= 0) & (d5 <= d6), (0, 0, 1))
    put((d3 >= 0) & (d4 <= d3), (0, 1, 0))
    put((d1 <= 0) & (d2 <= 0), (1, 0, 0))
    q = w[..., 0, None]*a+w[..., 1, None]*b+w[..., 2, None]*c
    return np.linalg.norm(p-q, axis=-1), w


def _samples(tri):
    """Vertices, edge midpoints and centroid of triangles (t,3,3) -> (t,7,3)."""
    a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
    return np.stack((a, b, c, (a+b)/2, (b+c)/2, (c+a)/2, (a+b+c)/3), axis=1)


def _nearest(points, tri):
    """Index, distance and barycentric of the nearest triangle per point."""
    chunk = max(16, 400000//max(1, len(tri)))
    best = np.empty(len(points), int); dist = np.empty(len(points)); bary = np.empty((len(points), 3))
    for s in range(0, len(points), chunk):
        d, w = closest_points(points[s:s+chunk], tri)
        i = np.argmin(d, axis=1); r = np.arange(len(i))
        best[s:s+chunk] = i; dist[s:s+chunk] = d[r, i]; bary[s:s+chunk] = w[r, i]
    return best, dist, bary


def _normals(tri):
    n = np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0])
    return n/np.maximum(np.linalg.norm(n, axis=1)[:, None], 1e-12)


def charts(v, f):
    """Triangle groups joined across edges with equal position, UV and
    material: one UV chart each. Returns welded vertex ids and chart lists."""
    keys = np.column_stack((np.round(v[f[:, :3].reshape(-1), :3], 4),
                            np.round(v[f[:, :3].reshape(-1), 3:5], 5),
                            np.repeat(f[:, 3], 3)))
    _, weld = np.unique(keys, axis=0, return_inverse=True)
    weld = weld.reshape(-1, 3)
    parent = list(range(len(f)))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    edge_owner = {}
    for t, (a, b, c) in enumerate(weld.tolist()):
        for e in ((a, b), (b, c), (c, a)):
            e = (min(e), max(e))
            if e in edge_owner:
                parent[find(t)] = find(edge_owner[e])
            else:
                edge_owner[e] = t
    groups = {}
    for t in range(len(f)):
        groups.setdefault(find(t), []).append(t)
    return weld, list(groups.values())


def _reduce_chart(points, tris, uv, error, uv_tolerance, simplify):
    """Smallest accepted simplification of one chart, or None.

    Tries the zero-error (lossless) collapse pass first, then a binary search
    on the triangle target; every candidate is measured, never assumed."""
    src = points[tris]
    src_uv = uv[tris]
    src_n = _normals(src)
    src_samples = _samples(src).reshape(-1, 3)

    def evaluate(p, t):
        t = np.asarray(t)
        if not 0 < len(t) < len(tris):
            return None
        tri = p[t]
        area = np.linalg.norm(np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]), axis=1)
        t = t[area > 1e-9]; tri = p[t]
        if not len(t):
            return None
        # Texture coordinates of the new vertices from the source surface.
        vi, _, vw = _nearest(p, src)
        new_uv = (vw[:, :, None]*src_uv[vi]).sum(axis=1)
        si, sd, sw = _nearest(_samples(tri).reshape(-1, 3), src)
        true_uv = (sw[:, :, None]*src_uv[si]).sum(axis=1).reshape(-1, 7, 2)
        tuv = new_uv[t]
        interp = np.stack((tuv[:, 0], tuv[:, 1], tuv[:, 2], (tuv[:, 0]+tuv[:, 1])/2,
                           (tuv[:, 1]+tuv[:, 2])/2, (tuv[:, 2]+tuv[:, 0])/2, tuv.mean(axis=1)), axis=1)
        uv_dev = float(np.abs(interp-true_uv).max())
        _, back, _ = _nearest(src_samples, tri)
        geo = max(float(sd.max()), float(back.max()))
        turned = float((_normals(tri)*src_n[si.reshape(-1, 7)[:, 6]]).sum(axis=1).min())
        if geo <= error and uv_dev <= uv_tolerance and turned > .5:
            return p, t, new_uv, geo, uv_dev
        return None

    best = None
    try:
        best = evaluate(*simplify(points, tris.astype(np.int32), target_count=1, lossless=True,
                                  preserve_border=True))
    except Exception:
        best = None
    lo, hi = max(1, len(tris)//20), (len(best[1]) if best else len(tris))-1
    while lo <= hi:
        target = (lo+hi)//2
        try:
            result = evaluate(*simplify(points, tris.astype(np.int32), target_count=target, preserve_border=True))
        except Exception:
            result = None
        if result is not None:
            best = result; hi = min(len(result[1]), target)-1
        else:
            lo = target+1
    return best


def reduce_scenery(v, f, error, uv_tolerance, simplify=None):
    """Chart-wise visual reduction; returns (v, f, details).

    v: (n, >=5) vertices (xyz in source units, uv); f: (m, 4) triangles with
    material. `error` is in map units (source units x 0.25) and `uv_tolerance`
    in texture units. Unreduced charts keep their source rows unchanged.
    """
    if simplify is None:
        import fast_simplification
        simplify = fast_simplification.simplify
    v = np.asarray(v, float); f = np.asarray(f)
    weld, groups = charts(v, f)
    out_v = [v]; out_f = []; extra = v.shape[1]-5
    reduced = 0; worst_geo = 0.; worst_uv = 0.; charts_reduced = 0
    for ids in groups:
        ids = np.array(ids)
        if len(ids) < MIN_CHART_TRIANGLES:
            out_f.append(f[ids]); continue
        local, inverse = np.unique(weld[ids].reshape(-1), return_inverse=True)
        tris = inverse.reshape(-1, 3)
        # Positions and UVs of the welded chart vertices (map units).
        corner = f[ids, :3].reshape(-1)
        first = np.zeros(len(local), int); first[inverse] = corner
        points = v[first, :3]*.25; uv = v[first, 3:5]
        result = _reduce_chart(points, tris, uv, error, uv_tolerance, simplify)
        if result is None:
            out_f.append(f[ids]); continue
        p, t, new_uv, geo, uv_dev = result
        base = sum(len(x) for x in out_v)
        pad = np.repeat(v[first, 5:].mean(axis=0, keepdims=True), len(p), axis=0) if extra else np.zeros((len(p), 0))
        out_v.append(np.column_stack((p/.25, new_uv, pad)))
        material = int(f[ids[0], 3])
        out_f.append(np.column_stack((t+base, np.full(len(t), material))))
        reduced += len(ids)-len(t); charts_reduced += 1
        worst_geo = max(worst_geo, geo); worst_uv = max(worst_uv, uv_dev)
    nv = np.concatenate(out_v); nf = np.concatenate(out_f).astype(f.dtype) if out_f else f[:0]
    return nv, nf, {'source_triangles': int(len(f)), 'reduced_triangles': int(len(nf)),
                    'charts': len(groups), 'charts_reduced': charts_reduced,
                    'error_bound': error, 'max_surface_distance': round(worst_geo, 5),
                    'uv_bound': uv_tolerance, 'max_uv_deviation': worst_uv,
                    'collision': 'original source geometry'}
