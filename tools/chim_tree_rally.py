#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Tree type 2, the rally-game trees (SOLSTHEIM-TREES-THREE-LOD-68, docs/WORLD_TREE_SPRITES.md): each Solstheim tree
model drawn as its trunk in polygons and its crown as a few see-through picture planes, the way the 3D rally games of
the 1990s lined their tracks with forests.

Seen from above, the crown is cut into wedges by PLANES vertical planes through the trunk's axis (4 planes = 8 panes).
Each plane is ONE flat face per side (a mirrored copy behind it, so it is seen from both sides), cut to the convex
outline of what it shows, and carries a picture rendered offline from the ORIGINAL model's crown (its needle
textures and their see-through texels, its vertex colours and material tint: tools/preview_scenery.render, the
renderer of the tree sprite bake), with see-through texels where the crown is not. Two kinds of picture
(pane_texture):
- silhouette: the whole crown seen across the plane (the classic crossed billboard);
- slice: only the crown's triangles in that plane's own wedge (every needle in exactly one plane).
The trunk is the original model's bark triangles (trunk original) or a tapered bark prism of trunk_sides faces (trunk
prism). Collision stays the model's own.

The engine draws a face whose texture has see-through texels in its see-through pass (engine/aga/src/d_fence.c):
kept off the edge list and off the face-by-face clip down the terrain tree, z-tested per texel. That is why these
are model faces (bitmap planes) and not sprites: the engine draws them through the CHIM model path that already
carries the trees, with no entity per pane and no new format. All of one model's planes share one picture atlas, the
converter's baked-panel material (index = the material count, its picture in lod['_flat_rgb'], here RGBA); the
texture step makes it a see-through texture (chim.fence: palette index 255 where the picture is clear).

Use: tools/chim_tree_rally.py --tree-rally CONFIG [--pane-texture silhouette|slice] <tools/solstheim_test_world.py
arguments>. It installs the rally trees' mesh step (prepare_mesh_bsp._prepare_model, read by chim.build.mesh_unit at
call time; the mesh unit key carries the rally settings, so a unit cache never mixes methods) and the see-through
atlas texture unit, in this process and in the workers it starts (tools/tree_rally_site), then runs the Solstheim
test world runner (its master selection, unit pool and options) in this process. TEST BUILDS ONLY: the stages
chim-sol-rally / chim-sol-slice of tools/build.py --chim-sol-tree-copies rally-switch (alternative models 2 and 3 of
aw_tree_crowns) and chim-sol of --chim-sol-tree-copies rally; no base stage runs it, and chim_build.py, the
converters and the runner are unchanged, so no base key moves.
"""
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

CONFIG = Path(__file__).resolve().parents[1] / 'config' / 'tree-copies.json'
PANE_TEXTURES = ('silhouette', 'slice')
TRUNKS = ('original', 'prism')
SCALE = .25                  # source units to map units (prepare_mesh_bsp SCALE)
CLEAR_SHARE = 0.05           # a material whose texture has more see-through texels than this is crown (needles)
ALPHA_CUT = 128              # the original's alpha test (preview_scenery.render, chim.fence)
MAX_PANE_TEXELS = 208        # one face's texel span: the converter splits a face whose span, widened to the 16-texel
#                              grid at both ends, passes 240 (mesh_geometry.split_surface): 208 + 2 x 16 stays within
ATLAS_ALIGN = 16             # miptex sides are multiples of 16; panes start on 16 texels (no bleeding at mip 3)


def load_rally(path=CONFIG, layer='bloodmoon', pane_texture=None, trunk=None):
    """(settings, model stem patterns) of the config's 'rally' block; PANE_TEXTURE and TRUNK override its
    pane_texture and trunk."""
    doc = json.loads(Path(path).read_text(encoding='utf-8'))
    if doc.get('schema') != 'aw-tree-copies-1':
        raise ValueError('Unknown tree copies schema')
    s = {k: v for k, v in dict(doc['rally']).items() if k not in ('note', 'methods')}
    if pane_texture is not None:
        s['pane_texture'] = pane_texture
    if trunk is not None:
        s['trunk'] = trunk
    if not isinstance(s.get('planes'), int) or not 2 <= s['planes'] <= 8:
        raise ValueError('rally planes must be a whole number in [2, 8]')
    if s.get('pane_texture') not in PANE_TEXTURES:
        raise ValueError('rally pane_texture must be one of %s' % ', '.join(PANE_TEXTURES))
    if s.get('trunk') not in TRUNKS:
        raise ValueError('rally trunk must be one of %s' % ', '.join(TRUNKS))
    if not isinstance(s.get('trunk_sides'), int) or not 3 <= s['trunk_sides'] <= 16:
        raise ValueError('rally trunk_sides must be a whole number in [3, 16]')
    if not isinstance(s.get('outline_corners'), int) or not 3 <= s['outline_corners'] <= 16:
        raise ValueError('rally outline_corners must be a whole number in [3, 16]')
    if not isinstance(s.get('supersample'), int) or not 1 <= s['supersample'] <= 4:
        raise ValueError('rally supersample must be a whole number in [1, 4]')
    if not 0 < float(s.get('texels_per_unit', 0)) <= 4:
        raise ValueError('rally texels_per_unit must be in (0, 4]')
    if not 0 < float(s.get('coverage', 0)) <= 1:
        raise ValueError('rally coverage must be in (0, 1]')
    float(s.get('first_angle_degrees', 0))
    patterns = [p.casefold() for p in doc['layers'][layer]['model_stem_contains']]
    if not patterns:
        raise ValueError('A layer needs model stem patterns')
    return s, patterns


def rally_methods(path=CONFIG):
    """[(aw_tree_crowns value, pane texture, trunk)] of the config's rally 'methods' (the alternative models of a
    --chim-sol-tree-copies rally-switch test image), sorted by value."""
    doc = json.loads(Path(path).read_text(encoding='utf-8'))
    out = []
    for value, m in sorted(doc['rally']['methods'].items(), key=lambda kv: int(kv[0])):
        if not 2 <= int(value) <= 15 or m.get('pane_texture') not in PANE_TEXTURES or m.get('trunk') not in TRUNKS:
            raise ValueError('rally method %s: value 2-15, pane_texture %s, trunk %s' % (
                value, '/'.join(PANE_TEXTURES), '/'.join(TRUNKS)))
        out.append((int(value), m['pane_texture'], m['trunk']))
    return out


def is_rally_model(source, patterns):
    stem = source.replace('\\', '/').casefold().rsplit('/', 1)[-1]
    return stem.endswith('.nif') and any(p in stem for p in patterns)


def source_textures(archive, texture_records, materials):
    """{texture index: RGBA array} of the materials' textures (the exported MWT1 records, as prepare_mesh_bsp reads)."""
    import struct
    import numpy as np
    from mwad.scene import read_asset
    out = {}
    for mat in materials:
        ti = mat.get('texture_index')
        if ti is None or ti in out:
            continue
        raw = read_asset(archive, texture_records[ti])
        _, w, h = struct.unpack_from('>4sHH', raw)
        out[ti] = np.frombuffer(raw[8:], np.uint8).reshape(h, w, 4)
    return out


def tree_parts(vertices, faces, materials, textures):
    """The model's parts: {'centre': (x, y) of the trunk axis, 'crown': see-through textured materials (the needle
    cards), 'bark': the opaque textured material nearest the axis or None, 'trunk': every other material (bark,
    roots, anything opaque)}."""
    import numpy as np
    v = np.asarray(vertices, dtype=float)
    f = np.asarray(faces, dtype=int)
    used = sorted(set(f[:, 3].tolist()))
    p = v[np.unique(f[:, :3]), :3]
    box_centre = ((p[:, 0].min() + p[:, 0].max()) / 2, (p[:, 1].min() + p[:, 1].max()) / 2)

    def clear(mat):
        t = textures.get(materials[mat].get('texture_index'))
        return t is not None and float((np.asarray(t)[:, :, 3] < ALPHA_CUT).mean()) > CLEAR_SHARE
    crown = [m for m in used if clear(m)]
    if not crown:
        raise ValueError('No see-through (needle) material: not a rally tree')
    opaque = [m for m in used if m not in crown]

    def axis_distance(mat):
        q = v[np.unique(f[f[:, 3] == mat, :3]), :3]
        return float(np.median(np.hypot(q[:, 0] - box_centre[0], q[:, 1] - box_centre[1])))
    textured = [m for m in opaque if materials[m].get('texture_index') is not None]
    bark = min(textured, key=axis_distance) if textured else None
    if bark is not None:
        b = v[np.unique(f[f[:, 3] == bark, :3]), :3]
        centre = (float(b[:, 0].mean()), float(b[:, 1].mean()))
    else:
        centre = box_centre
    return {'centre': centre, 'crown': crown, 'bark': bark, 'trunk': opaque}


def plane_angles(settings):
    """The planes' angles in degrees: PLANES over half a turn (each plane holds two panes, one on each side of the
    trunk), from first_angle_degrees."""
    n = int(settings['planes'])
    a0 = float(settings.get('first_angle_degrees', 0))
    return [a0 + 180.0 * k / n for k in range(n)]


def slice_owner(xy, angles):
    """For points XY (n x 2, relative to the axis) the index of the plane whose line (both sides of the trunk) is
    nearest in angle. A plane at angle a lies along (cos a, -sin a) (preview_scenery.render's image x)."""
    import numpy as np
    psi = np.arctan2(xy[:, 1], xy[:, 0])
    dist = []
    for a in angles:
        d = (psi + math.radians(a)) % math.pi            # 0 or pi on the plane's line
        dist.append(np.minimum(d, math.pi - d))
    return np.argmin(np.stack(dist, axis=1), axis=1)


def render_pane(v, faces, materials, textures, angle, frame, size, supersample, coverage):
    """(RGBA uint8 array H x W, covered mask) of the crown triangles FACES seen across the plane at ANGLE (degrees),
    framed by FRAME (lo, hi, bottom, top in source units) at SIZE (W, H) texels: rendered SUPERSAMPLE times larger by
    preview_scenery.render (the original's textures, alpha test, vertex colours and tint), then each texel covered
    where at least COVERAGE of its samples are, its colour the mean of its covered samples."""
    import numpy as np
    from preview_scenery import render
    w, h = size
    k = int(supersample)
    if not len(faces):
        return np.zeros((h, w, 4), np.uint8), np.zeros((h, w), bool)
    big = np.asarray(render(v, faces, materials, textures, math.radians(angle), (w * k, h * k), frame))
    cov = (big[:, :, 3] >= ALPHA_CUT).reshape(h, k, w, k)
    rgb = big[:, :, :3].astype(float).reshape(h, k, w, k, 3)
    count = cov.sum(axis=(1, 3))
    colour = (rgb * cov[..., None]).sum(axis=(1, 3)) / np.maximum(count, 1)[..., None]
    covered = count >= max(1, math.ceil(coverage * k * k))
    out = np.zeros((h, w, 4), np.uint8)
    out[:, :, :3] = np.clip(np.rint(colour), 0, 255).astype(np.uint8)
    out[:, :, 3] = np.where(covered, 255, 0).astype(np.uint8)
    out[~covered, :3] = 0
    return out, covered


def _cross2(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _line_meet(p, d, q, e):
    den = d[0] * e[1] - d[1] * e[0]
    if abs(den) < 1e-12:
        return None
    t = ((q[0] - p[0]) * e[1] - (q[1] - p[1]) * e[0]) / den
    return (p[0] + t * d[0], p[1] + t * d[1])


def polygon_area(poly):
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))) / 2


def covering_polygon(points, corners):
    """A convex polygon (counter-clockwise) of at most CORNERS corners that holds every one of POINTS: their convex
    hull, then edges removed one at a time where extending the two neighbouring edges to meet adds the least area
    (the polygon only grows, so nothing the hull holds falls out)."""
    import numpy as np
    from scipy.spatial import ConvexHull
    pts = np.unique(np.asarray(points, float), axis=0)
    hull = ConvexHull(pts)
    poly = [tuple(map(float, pts[i])) for i in hull.vertices]          # counter-clockwise in 2D
    while len(poly) > corners:
        n = len(poly)
        best = None
        for i in range(n):
            a, b, c, d = poly[i - 1], poly[i], poly[(i + 1) % n], poly[(i + 2) % n]
            x = _line_meet(b, (b[0] - a[0], b[1] - a[1]), c, (c[0] - d[0], c[1] - d[1]))
            if x is None or _cross2(b, x, c) <= 0:                       # not outside the edge b-c: not removable
                continue
            # the meeting point must lie ahead of b along a->b and ahead of c along d->c
            if (x[0] - b[0]) * (b[0] - a[0]) + (x[1] - b[1]) * (b[1] - a[1]) < -1e-9:
                continue
            if (x[0] - c[0]) * (c[0] - d[0]) + (x[1] - c[1]) * (c[1] - d[1]) < -1e-9:
                continue
            added = polygon_area([b, x, c])
            if best is None or added < best[0]:
                best = (added, i, x)
        if best is None:
            break
        _, i, x = best
        j = (i + 1) % len(poly)
        if j == 0:
            poly = [x] + poly[1:i]
        else:
            poly = poly[:i] + [x] + poly[j + 1:]
    return poly


def clip_to_rect(poly, x0, y0, x1, y1):
    """POLY (convex, counter-clockwise) clipped to the rectangle (Sutherland-Hodgman)."""
    def clip(points, inside, meet):
        out = []
        for i, cur in enumerate(points):
            prev = points[i - 1]
            if inside(cur):
                if not inside(prev):
                    out.append(meet(prev, cur))
                out.append(cur)
            elif inside(prev):
                out.append(meet(prev, cur))
        return out

    def at_x(x):
        return lambda p, q: (x, p[1] + (q[1] - p[1]) * (x - p[0]) / (q[0] - p[0]))

    def at_y(y):
        return lambda p, q: (p[0] + (q[0] - p[0]) * (y - p[1]) / (q[1] - p[1]), y)
    for inside, meet in ((lambda p: p[0] >= x0, at_x(x0)), (lambda p: p[0] <= x1, at_x(x1)),
                         (lambda p: p[1] >= y0, at_y(y0)), (lambda p: p[1] <= y1, at_y(y1))):
        poly = clip(poly, inside, meet)
        if not poly:
            break
    out = []
    for p in poly:
        if not out or math.dist(out[-1], p) > 1e-6:
            out.append(p)
    if len(out) > 1 and math.dist(out[0], out[-1]) <= 1e-6:
        out.pop()
    return out


def open_edges(faces):
    """Edges used by exactly one triangle (by vertex index)."""
    from collections import Counter
    count = Counter()
    for a, b, c, *_ in faces:
        for e in ((a, b), (b, c), (c, a)):
            count[tuple(sorted(e))] += 1
    return sum(1 for n in count.values() if n == 1)


def rally_tree(vertices, faces, materials, textures, settings, texsize=64):
    """(vertices, triangles, atlas RGBA, report) of the rally tree of one model's source geometry (the visual
    primitive format: rows x y z u v r g b a; triangles a b c material). The pane triangles carry the material
    report['pane_material'] (one of the crown's own, a placeholder: the caller moves the converted pane faces onto the
    baked-panel material whose picture is the atlas); the trunk keeps the model's materials."""
    import numpy as np
    v = np.asarray(vertices, dtype=float)
    f = np.asarray(faces, dtype=int)
    parts = tree_parts(v, f, materials, textures)
    cx, cy = parts['centre']
    crown = f[np.isin(f[:, 3], parts['crown'])]
    trunk_f = f[np.isin(f[:, 3], parts['trunk'])]
    vc = v.copy()
    vc[:, 0] -= cx
    vc[:, 1] -= cy
    cp = vc[np.unique(crown[:, :3]), :3]
    radius = float(np.hypot(cp[:, 0], cp[:, 1]).max())
    bottom, top = float(cp[:, 2].min()), float(cp[:, 2].max())
    rho = float(settings['texels_per_unit']) * SCALE                  # texels per source unit
    w = max(1, math.ceil(2 * radius * rho))
    h = max(1, math.ceil((top - bottom) * rho))
    if w > MAX_PANE_TEXELS or h > MAX_PANE_TEXELS:
        # one face per pane: shrink the density to the converter's face extent rather than split the pane
        rho *= MAX_PANE_TEXELS / max(w, h)
        w = max(1, math.ceil(2 * radius * rho))
        h = max(1, math.ceil((top - bottom) * rho))
    lo = -radius
    frame = (lo, lo + w / rho, top - h / rho, top)                   # exactly w x h texels of 1 / rho units
    angles = plane_angles(settings)
    kind = settings['pane_texture']
    if kind == 'slice':
        centroids = vc[crown[:, :3], :2].mean(axis=1)
        owner = slice_owner(centroids, angles)
    panes, x0 = [], 0
    for k, a in enumerate(angles):
        tris = crown if kind == 'silhouette' else crown[owner == k]
        rgba, covered = render_pane(vc, tris, materials, textures, a, frame, (w, h), int(settings['supersample']),
                                    float(settings['coverage']))
        panes.append({'angle': a, 'rgba': rgba, 'covered': covered, 'x0': x0, 'triangles_shown': int(len(tris))})
        x0 += -(-(w + 8) // ATLAS_ALIGN) * ATLAS_ALIGN                   # a clear gutter of 8 texels or more
    aw = max(ATLAS_ALIGN, -(-x0 // ATLAS_ALIGN) * ATLAS_ALIGN)
    ah = max(ATLAS_ALIGN, -(-h // ATLAS_ALIGN) * ATLAS_ALIGN)
    atlas = np.zeros((ah, aw, 4), np.uint8)
    out_v, out_f = [], []
    pane_mat = int(parts['crown'][0])
    corners, polygon_texels, covered_texels = [], 0.0, 0
    for pane in panes:
        atlas[:h, pane['x0']:pane['x0'] + w] = pane['rgba']
        ys, xs = np.nonzero(pane['covered'])
        if not len(xs):
            corners.append(0)
            continue
        covered_texels += int(len(xs))
        # every covered texel's square, in texel coordinates (x right, y down from the crown's top)
        sq = np.concatenate([np.column_stack((xs + dx, ys + dy)) for dx in (0, 1) for dy in (0, 1)])
        # as (s, z) in source units, so counter-clockwise there is the face's front (normal along -depth)
        sz = np.column_stack((lo + sq[:, 0] / rho, top - sq[:, 1] / rho))
        poly = covering_polygon(sz, int(settings['outline_corners']))
        poly = clip_to_rect(poly, lo, top - h / rho, lo + w / rho, top)
        if len(poly) < 3:
            corners.append(0)
            continue
        corners.append(len(poly))
        polygon_texels += polygon_area(poly) * rho * rho
        a = math.radians(pane['angle'])
        side = (math.cos(a), -math.sin(a))
        start = len(out_v)
        for s_, z in poly:
            u = (pane['x0'] + (s_ - lo) * rho) / texsize
            t = (top - z) * rho / texsize
            out_v.append([cx + s_ * side[0], cy + s_ * side[1], z, u, t, 255, 255, 255, 255])
        for i in range(1, len(poly) - 1):
            out_f.append([start, start + i, start + i + 1, pane_mat])        # the front
            out_f.append([start, start + i + 1, start + i, pane_mat])        # the mirrored back
    pane_triangles = len(out_f)
    # the trunk
    if settings['trunk'] == 'original':
        ids = np.unique(trunk_f[:, :3])
        remap = {int(i): len(out_v) + n for n, i in enumerate(ids)}
        out_v.extend(v[ids].tolist())
        out_f.extend([[remap[int(a)], remap[int(b)], remap[int(c)], int(m)] for a, b, c, m in trunk_f])
        trunk_report = {'kind': 'original', 'triangles': int(len(trunk_f)), 'open_edges': open_edges(trunk_f.tolist())}
    else:
        trunk_report = _prism_trunk(v, f, parts, settings, out_v, out_f, texsize)
    report = {'kind': 'rally', 'pane_texture': kind, 'planes': len(angles), 'angles': angles,
              'source_triangles': int(len(f)), 'crown_triangles': int(len(crown)),
              'triangles': len(out_f), 'pane_triangles': pane_triangles, 'pane_material': pane_mat,
              'pane_corners': corners, 'pane_texels': [w, h], 'texels_per_source_unit': round(rho, 5),
              'atlas': [aw, ah], 'atlas_bytes_with_mips': aw * ah + (aw // 2) * (ah // 2) + (aw // 4) * (ah // 4)
              + (aw // 8) * (ah // 8),
              'covered_texels': covered_texels, 'pane_polygon_texels': round(polygon_texels),
              'crown': {'radius': round(radius, 3), 'bottom': round(bottom, 3), 'top': round(top, 3)},
              'centre': [round(cx, 3), round(cy, 3)], 'trunk': trunk_report,
              'triangles_shown': [p['triangles_shown'] for p in panes]}
    return np.asarray(out_v, dtype=float), np.asarray(out_f, dtype=np.int64), atlas, report


def bark_units(v, faces, fallback=128.0):
    """(source units per texture repeat across, along the height) of the bark triangles FACES: the median length of
    their texture axes (the converter's per-triangle mapping, mesh_geometry.surface_polygons), the larger one taken
    as the height's when the axes are not upright. FALLBACK for none."""
    import numpy as np
    across, along = [], []
    for a, b, c, *_ in faces:
        p, uv = v[[a, b, c], :3], v[[a, b, c], 3:5]
        n = np.cross(p[1] - p[0], p[2] - p[0])
        if np.linalg.norm(n) < 1e-6:
            continue
        A = np.vstack((p[1] - p[0], p[2] - p[0], n / np.linalg.norm(n)))
        axes = np.linalg.solve(A, np.vstack((uv[1] - uv[0], uv[2] - uv[0], [0, 0])))   # 3 x 2: d(u, v) / dxyz
        for col in range(2):
            g = axes[:, col]
            if np.linalg.norm(g) < 1e-9:
                continue
            (along if abs(g[2]) > np.linalg.norm(g[:2]) else across).append(1 / np.linalg.norm(g))
    s = float(np.median(across)) if across else fallback
    t = float(np.median(along)) if along else fallback
    return s, t


def _prism_trunk(v, f, parts, settings, out_v, out_f, texsize):
    """A tapered bark prism of trunk_sides faces (no caps: the ground hides its foot, it narrows to the bark's own
    top inside the crown), from the bark's own vertices: radius near the foot and near the top."""
    import numpy as np
    sides = int(settings['trunk_sides'])
    mat = parts['bark'] if parts['bark'] is not None else parts['trunk'][0] if parts['trunk'] else parts['crown'][0]
    cx, cy = parts['centre']
    pick = parts['trunk'] if parts['trunk'] else [mat]
    q = v[np.unique(f[np.isin(f[:, 3], pick), :3]), :3]
    r = np.hypot(q[:, 0] - cx, q[:, 1] - cy)
    z0, z1 = float(q[:, 2].min()), float(q[:, 2].max())
    band = 0.15 * (z1 - z0)
    r0 = float(np.median(r[q[:, 2] <= z0 + band])) if (q[:, 2] <= z0 + band).any() else float(np.median(r))
    r1 = float(np.median(r[q[:, 2] >= z1 - band])) if (q[:, 2] >= z1 - band).any() else r0
    r1 = min(r0, r1)
    unit_s, unit_t = bark_units(v, f[f[:, 3] == mat])  # the original bark's own texel density
    # one face per side: the height stays within the converter's face extent (a slightly longer bark repeat
    # instead of every side split in two)
    unit_t = max(unit_t, (z1 - z0) * texsize / MAX_PANE_TEXELS)
    before = len(out_f)
    for k in range(sides):
        a0, a1 = 2 * math.pi * k / sides, 2 * math.pi * (k + 1) / sides
        corners = [(cx + r0 * math.cos(a0), cy + r0 * math.sin(a0), z0), (cx + r0 * math.cos(a1), cy + r0 * math.sin(a1), z0),
                   (cx + r1 * math.cos(a1), cy + r1 * math.sin(a1), z1), (cx + r1 * math.cos(a0), cy + r1 * math.sin(a0), z1)]
        width = math.dist(corners[0][:2], corners[1][:2]) or 1.0
        ex, ey = (corners[1][0] - corners[0][0]) / width, (corners[1][1] - corners[0][1]) / width
        start = len(out_v)
        for p in corners:
            s = (p[0] - corners[0][0]) * ex + (p[1] - corners[0][1]) * ey
            out_v.append([*p, (k * width + s) / unit_s, (z1 - p[2]) / unit_t, 255, 255, 255, 255])
        out_f.append([start, start + 1, start + 2, mat])
        out_f.append([start, start + 2, start + 3, mat])
    return {'kind': 'prism', 'sides': sides, 'triangles': len(out_f) - before, 'radius_bottom': round(r0, 3),
            'radius_top': round(r1, 3), 'z': [round(z0, 3), round(z1, 3)],
            'bark_units_per_repeat': [round(unit_s, 2), round(unit_t, 2)]}


def pane_texture_unit(task):
    """The rally atlas (the baked-panel material with an RGBA picture) as a see-through miptex (chim.fence's
    format: colours quantized without palette index 255, 255 wherever the picture is clear)."""
    import numpy as np
    from PIL import Image
    from prepare_quake import miptex
    from chim.fence import FENCE_INDEX, engine_name
    rgba = np.asarray(task['flat_rgb'])
    pal = list(task['palette'][:768])
    pal += [0] * (768 - len(pal))
    pal[765:768] = pal[0:3]                          # a palette without index 255: its colour is index 0's
    no255 = Image.new('P', (1, 1))
    no255.putpalette(pal)
    pixels = np.array(Image.fromarray(np.ascontiguousarray(rgba[:, :, :3])).quantize(palette=no255,
                                                                                     dither=Image.Dither.NONE))
    pixels[pixels == FENCE_INDEX] = 0
    pixels[rgba[:, :, 3] < ALPHA_CUT] = FENCE_INDEX
    im = Image.fromarray(pixels.astype(np.uint8), 'P')
    return {'miptex': miptex(engine_name('fence', 0, 0), im), 'size': list(im.size), 'kind': 'fence', 'glow': 0}


def is_rally_atlas(task):
    import numpy as np
    rgba = task.get('flat_rgb')
    return task.get('kind') == 'flatten' and rgba is not None and np.asarray(rgba).ndim == 3 \
        and np.asarray(rgba).shape[2] == 4


_ORIGINAL = {}               # the functions install() replaced (the first ones: a second install keeps them)


def rally_texture_unit(task):
    """chim.models.texture_unit with the rally atlas made see-through; every other texture as before. Module level,
    so the CHIM pool pickles it by reference (chim_tree_rally.rally_texture_unit) for its workers."""
    if is_rally_atlas(task):
        return pane_texture_unit(task)
    return _ORIGINAL['texture_unit'](task)


def install(settings, patterns):
    """Replace the mesh step of the rally models and make their RGBA atlas a see-through texture (in this process;
    the workers it starts install the same at start-up, tools/tree_rally_site)."""
    import prepare_mesh_bsp
    import visual_primitives
    from chim import build as chim_build_mod
    from chim import models as chim_models
    from mwad.scene import read_asset, unpack_geometry
    if getattr(prepare_mesh_bsp, '_aw_rally_installed', None) == json.dumps(settings, sort_keys=True):
        return
    original_prepare = prepare_mesh_bsp._prepare_model
    original_visual = visual_primitives.make_visual
    original_fingerprint = chim_build_mod.mesh_fingerprint
    _ORIGINAL.setdefault('texture_unit', chim_models.texture_unit)
    tag = json.dumps(settings, sort_keys=True)

    def make_visual(s):
        if s.get('kind') == 'aw_rally_tree':
            return s['_v'], s['_f']
        return original_visual(s)

    def prepare(task):
        mi, m, profile, archive_path, *extras = task
        if not is_rally_model(m['source'], patterns):
            return original_prepare(task)
        if not extras:
            raise ValueError('rally trees need the source textures: ' + m['source'])
        with Path(archive_path).open('rb') as archive:
            vv, ff, _ = unpack_geometry(read_asset(archive, m))
            textures = source_textures(archive, extras[0], m['materials'])
        size = int(profile.get('texture_size', 64))
        rv, rf, atlas, report = rally_tree(vv, ff, m['materials'], textures, settings, size)
        clean = {k: v for k, v in profile.items() if k not in ('ratio', 'flatten', 'visual_panel')}
        prim = {'kind': 'aw_rally_tree', '_v': rv, '_f': rf}
        _, (v, f, polys, pieces, lod) = original_prepare((mi, m, dict(clean, visual_primitive=prim), archive_path,
                                                          *extras))
        flat = len(m['materials'])
        pane = report['pane_material']
        polys = [(poly, flat if mat == pane else mat, ax, off, normal) for poly, mat, ax, off, normal in polys]
        report['faces'] = {'panes': sum(1 for p in polys if p[1] == flat), 'trunk': sum(1 for p in polys if p[1] != flat)}
        lod['visual_primitive'] = 'aw_rally_tree'
        lod['_flat_rgb'] = atlas
        lod['rally_tree'] = report
        print('RALLY TREE %s: %s panes (%d planes, corners %s), %d pane faces + %d trunk faces (%s trunk) from %d '
              'source triangles; atlas %dx%d, %d texels covered of %d in the pane polygons' % (
                  m['source'], report['pane_texture'], report['planes'], report['pane_corners'],
                  report['faces']['panes'], report['faces']['trunk'], report['trunk']['kind'],
                  report['source_triangles'], report['atlas'][0], report['atlas'][1], report['covered_texels'],
                  report['pane_polygon_texels']), flush=True)
        return mi, (v, f, polys, pieces, lod)

    def fingerprint(model, profile, texture_records, kind='mesh'):
        key = original_fingerprint(model, profile, texture_records, kind)
        if is_rally_model(model['source'], patterns):
            import hashlib
            return hashlib.sha256((str(key) + '|aw_rally_tree|' + tag).encode()).hexdigest()
        return key

    prepare_mesh_bsp._prepare_model = prepare
    visual_primitives.make_visual = make_visual
    chim_build_mod.mesh_fingerprint = fingerprint
    chim_models.texture_unit = rally_texture_unit
    prepare_mesh_bsp._aw_rally_installed = tag


ENV = 'AMIWIND_TREE_RALLY'
ENV_PANES = 'AMIWIND_TREE_RALLY_PANES'
ENV_TRUNK = 'AMIWIND_TREE_RALLY_TRUNK'
USAGE = ('usage: chim_tree_rally.py --tree-rally CONFIG [--pane-texture silhouette|slice] [--trunk original|prism] '
         '<tools/solstheim_test_world.py arguments>')


def take_args(argv):
    """(config path, pane texture or None, trunk or None, the rest) of
    '--tree-rally CONFIG [--pane-texture KIND] [--trunk KIND] REST...'."""
    argv = list(argv)
    if len(argv) < 2 or argv[0] != '--tree-rally':
        raise SystemExit(USAGE)
    config, rest = argv[1], argv[2:]
    found = {'--pane-texture': (PANE_TEXTURES, None), '--trunk': (TRUNKS, None)}
    while rest[:1] and rest[0] in found and found[rest[0]][1] is None:
        choices = found[rest[0]][0]
        if len(rest) < 2 or rest[1] not in choices:
            raise SystemExit('%s takes one of %s' % (rest[0], ', '.join(choices)))
        found[rest[0]] = (choices, rest[1])
        rest = rest[2:]
    return config, found['--pane-texture'][1], found['--trunk'][1], rest


def main(argv=None):
    import os
    config, panes, trunk, rest = take_args(sys.argv[1:] if argv is None else argv)
    settings, patterns = load_rally(config, pane_texture=panes, trunk=trunk)
    print('TREE RALLY: %d planes (%d panes), %s pictures, %s trunk, %.2f texels per unit, models with %s' % (
        settings['planes'], 2 * settings['planes'], settings['pane_texture'], settings['trunk'],
        float(settings['texels_per_unit']), ', '.join(patterns)), flush=True)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    # installed from the importable module, not this script's __main__: the pool pickles the texture unit by name
    import chim_tree_rally
    chim_tree_rally.install(settings, patterns)
    # the worker pool spawns fresh interpreters: each installs the same steps at start-up (tree_rally_site)
    os.environ[ENV] = str(Path(config).resolve())
    os.environ[ENV_PANES] = settings['pane_texture']
    os.environ[ENV_TRUNK] = settings['trunk']
    site = str(Path(__file__).resolve().parent / 'tree_rally_site')
    os.environ['PYTHONPATH'] = os.pathsep.join([site, *filter(None, os.environ.get('PYTHONPATH', '').split(os.pathsep))])
    import solstheim_test_world
    return solstheim_test_world.main(rest)


if __name__ == '__main__':
    sys.exit(main())
