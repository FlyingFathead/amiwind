# SPDX-License-Identifier: GPL-3.0-only
# Created by FlyingFathead a.k.a. Horstator. Thanks to ChaosWhisperer.
"""Method 2 kinds from the hand-made reduction batches 001-004: "conservative" (an endpoint simplifier with locked
borders on chosen materials), "profile_shell" (a closed shell through rings read from the source, with the appearance
baked into one picture and chosen source parts kept whole) and "dunmer_lantern" / "common_lantern" (a four-corner ring
body with baked side panels and the source handle kept). The recipes are numbers only (config/model-method-2.json);
the mesh and the pictures are made at build time from the model and textures the builder exported from the user's own
game files (tools/model_method2.py runs them as a unit of their own kind).

Units, at every step: the builder's mesh (the scenery export's packet) is in Morrowind units, Z up, its texture v
counting down the picture (the NIF's own). The recipes were measured in Morrowind units too, with the OBJ texture
convention (v' = 1 - v): to_source turns the builder's mesh into that frame, to_builder turns the result back (and maps
the baked picture's texture coordinates to the converter's texels). Nothing is scaled: the engine's 0.25 is applied
once, later, by the converter.
"""
from collections import Counter, defaultdict

import numpy as np

CORNERS = np.array([[-1, -1], [1, -1], [1, 1], [-1, 1]])
KINDS = ('conservative', 'profile_shell', 'dunmer_lantern', 'common_lantern')
BAKED_KINDS = ('profile_shell', 'dunmer_lantern', 'common_lantern')


# ---------------------------------------------------------------- the mesh model of the recipes

class Model:
    """Distinct positions (rounded to 6 decimals, Morrowind units), a texture coordinate per face corner (OBJ
    convention), faces (material name, position ids, uv ids) and a group per face."""

    def __init__(self):
        self.v, self.uv, self.faces, self.groups, self.index = [], [], [], [], {}

    def vertex(self, p):
        key = tuple(round(float(x), 6) for x in p)
        if key not in self.index:
            self.index[key] = len(self.v)
            self.v.append(key)
        return self.index[key]

    def tri(self, points, uv, material, group):
        ids = [self.vertex(p) for p in points]
        u = list(range(len(self.uv), len(self.uv) + 3))
        self.uv.extend([[float(c) for c in t] for t in uv])
        self.faces.append((material, ids, u))
        self.groups.append(group)

    def quad(self, points, uv, material, group='shell'):
        for ids in ((0, 1, 2), (0, 2, 3)):
            self.tri([points[i] for i in ids], [uv[i] for i in ids], material, group)


def to_source(vertices, faces):
    """The recipes' source model of a builder mesh: materials 'm<index>', groups 'source_m<index>'."""
    v = np.asarray(vertices, dtype=float)
    points, uvs = v[:, :3], np.column_stack((v[:, 3], 1.0 - v[:, 4]))
    model = Model()
    for f in np.asarray(faces, dtype=np.int64):
        ids = [int(f[0]), int(f[1]), int(f[2])]
        model.tri(points[ids], uvs[ids], 'm%d' % int(f[3]), 'source_m%d' % int(f[3]))
    return model


def edge_audit(v, faces):
    p = np.array(v)
    idx, weld = {}, []
    for point in p:
        key = tuple(np.round(point, 5))
        if key not in idx:
            idx[key] = len(idx)
        weld.append(idx[key])
    edges, directions, deg = Counter(), Counter(), 0
    for ids in faces:
        a = p[ids]
        deg += bool(np.linalg.norm(np.cross(a[1] - a[0], a[2] - a[0])) < 1e-9)
        ii = [weld[i] for i in ids]
        for j in range(3):
            a, b = ii[j], ii[(j + 1) % 3]
            edges[tuple(sorted((a, b)))] += 1
            directions[(a, b)] += 1
    return dict(open_edges=sum(n == 1 for n in edges.values()), nonmanifold_edges=sum(n > 2 for n in edges.values()),
                same_direction_pairs=sum(n == 2 and (directions[(a, b)] == 2 or directions[(b, a)] == 2)
                                         for (a, b), n in edges.items()),
                degenerate_triangles=int(deg))


def boundary_edges(model, material=None):
    edges = Counter()
    for mat, ids, _ in model.faces:
        if material is not None and mat != material:
            continue
        points = [tuple(np.round(model.v[i], 5)) for i in ids]
        edges.update(tuple(sorted((points[j], points[(j + 1) % 3]))) for j in range(3))
    return {edge for edge, n in edges.items() if n == 1}


def check_retained_boundaries(source, retained, material):
    # counting all open edges could hide a new cut where unrelated holes disappear
    introduced = boundary_edges(retained) - boundary_edges(source, material)
    if introduced:
        raise ValueError('Retained component has %d new cut edges' % len(introduced))


def statistics(model):
    v = np.array(model.v)
    groups = {}
    for group in sorted(set(model.groups)):
        fs = [ids for (_, ids, _), g in zip(model.faces, model.groups) if g == group]
        groups[group] = dict(triangles=len(fs), **edge_audit(v, fs))
    return dict(triangles=len(model.faces), positions=len(v), bounds=[v.min(0).tolist(), v.max(0).tolist()],
                groups=groups, global_topology=edge_audit(v, [ids for _, ids, _ in model.faces]))


def check_pair(source, reduced, closed_groups=()):
    """The reduced model against its source: bounds within 1e-4 Morrowind units, fewer triangles, no degenerate
    triangle, no more open edges overall, closed groups closed and wound one way, kept groups no more open."""
    a, b = statistics(source), statistics(reduced)
    error = float(np.max(np.abs(np.array(a['bounds']) - np.array(b['bounds']))))
    if error > 1e-4:
        raise ValueError('Bounds changed by %g Morrowind units' % error)
    if b['triangles'] >= a['triangles']:
        raise ValueError('Candidate does not reduce triangles')
    if b['global_topology']['degenerate_triangles']:
        raise ValueError('Degenerate output triangle')
    if b['global_topology']['open_edges'] > a['global_topology']['open_edges']:
        raise ValueError('Increased global open-edge count')
    for group, stats in b['groups'].items():
        if group in closed_groups:
            if stats['open_edges'] or stats['nonmanifold_edges'] or stats['same_direction_pairs']:
                raise ValueError('Invalid closed shell: ' + group)
        elif group in a['groups']:
            before = a['groups'][group]
            for key in ('open_edges', 'nonmanifold_edges', 'same_direction_pairs'):
                if stats[key] > before[key]:
                    raise ValueError('%s: increased %s' % (group, key))
    return a, b, error


# ---------------------------------------------------------------- the simplifier (kind "conservative")

def simplify(v, uv, faces, target, max_error):
    """Endpoint quadric simplification of one material, borders, texture seams and the extremes locked."""
    vv, index, ff, tt = [], {}, [], []
    for ids, tex in faces:
        row = []
        for i in ids:
            key = tuple(np.round(v[i], 5))
            if key not in index:
                index[key] = len(vv)
                vv.append(v[i])
            row.append(index[key])
        ff.append(row)
        tt.append(uv[tex])
    p, f, t = np.asarray(vv), np.asarray(ff, dtype=int), np.asarray(tt)
    q = np.zeros((len(p), 4, 4))
    for ids in f:
        pts = p[ids]
        n = np.cross(pts[1] - pts[0], pts[2] - pts[0])
        area = np.linalg.norm(n)
        if area < 1e-10:
            continue
        n /= area
        plane = np.r_[n, -np.dot(n, pts[0])]
        for i in ids:
            q[i] += np.outer(plane, plane)
    pinned = set()
    for axis in range(3):
        pinned.add(int(np.argmin(p[:, axis])))
        pinned.add(int(np.argmax(p[:, axis])))

    def same_chart(values):
        a = np.asarray(sorted(values))
        d = a - a[0]
        return np.max(np.abs(d - np.round(d))) <= .002
    while len(f) > target:
        edges = Counter(tuple(sorted((a[i], a[(i + 1) % 3]))) for a in f for i in range(3))
        incident, neighbors, uvsets = defaultdict(list), defaultdict(set), defaultdict(set)
        for k, ids in enumerate(f):
            for c, a in enumerate(ids):
                incident[a].append(k)
                neighbors[a].update(set(ids) - {a})
                uvsets[a].add(tuple(np.round(t[k, c], 6)))
        locked = set(pinned)
        for (a, b), n in edges.items():
            if n != 2:
                locked.update((a, b))
        locked.update(i for i, values in uvsets.items() if not same_chart(values))
        candidates = []
        for (a, b), n in edges.items():
            if n != 2:
                continue
            common = neighbors[a] & neighbors[b]
            opposite = {c for k in set(incident[a]) & set(incident[b]) for c in f[k] if c not in (a, b)}
            if common != opposite:
                continue
            for remove, keep in ((a, b), (b, a)):
                if remove in locked or not same_chart(uvsets[keep]):
                    continue
                h = np.r_[p[keep], 1.]
                cost = max(0., float(h @ (q[a] + q[b]) @ h))
                if cost > max_error ** 2:
                    continue
                candidates.append((cost, float(np.linalg.norm(p[a] - p[b])), remove, keep))
        changed = False
        for cost, dist, a, b in sorted(candidates):
            affected = incident[a]
            ok = True
            for k in affected:
                if b in f[k]:
                    continue
                old = p[f[k]]
                new = p[np.where(f[k] == a, b, f[k])]
                n0 = np.cross(old[1] - old[0], old[2] - old[0])
                n1 = np.cross(new[1] - new[0], new[2] - new[0])
                if np.linalg.norm(n1) < 1e-9 or np.dot(n0, n1) < .5 * np.linalg.norm(n0) * np.linalg.norm(n1):
                    ok = False
                    break
            if not ok:
                continue
            other = {tuple(sorted(ids)) for k, ids in enumerate(f) if k not in affected}
            for k in affected:
                ids = np.where(f[k] == a, b, f[k])
                if len(set(ids)) < 3:
                    continue
                key = tuple(sorted(ids))
                if key in other:
                    ok = False
                    break
                other.add(key)
            if not ok:
                continue
            targets = np.asarray(sorted(uvsets[b]))
            for k, c in np.argwhere(f == a):
                choices = targets + np.round(t[k, c] - targets)
                t[k, c] = choices[np.argmin(np.linalg.norm(choices - t[k, c], axis=1))]
            f[f == a] = b
            valid = np.array([len(set(x)) == 3 for x in f])
            f, t = f[valid], t[valid]
            q[b] += q[a]
            changed = True
            break
        if not changed:
            break
    return p, f, t


def copy_faces(result, source, selector, group=None, material=None):
    v, uv, count = np.asarray(source.v), np.asarray(source.uv), 0
    for (m, ids, u), g in zip(source.faces, source.groups):
        if selector(m, v[ids]):
            result.tri(v[ids], uv[u], material or m, group or g)
            count += 1
    return count


def conservative(source, settings):
    result = Model()
    v, uv = np.asarray(source.v), np.asarray(source.uv)
    for mat in sorted({m for m, _, _ in source.faces}):
        selected = [(ids, u) for m, ids, u in source.faces if m == mat]
        conf = settings['shapes'].get(mat)
        if conf:
            p, faces, coordinates = simplify(v, uv, selected, conf['target'], conf['qem_error'])
            for ids, uu in zip(faces, coordinates):
                result.tri(p[ids], uu, mat, 'source_' + mat)
        else:
            copy_faces(result, source, lambda m, p, mat=mat: m == mat)
    return result


# ---------------------------------------------------------------- the bakes

def _composite(origins, direction, faces, vertices, coords, textures, background):
    """Front-to-back alpha composite of the source triangles a grid of rays hits (a hit at the depth of the last one
    counted once), over BACKGROUND; RGB uint8 per ray."""
    distances = np.full((len(faces), len(origins)), np.inf, dtype=np.float32)
    colors = np.zeros((len(faces), len(origins), 4), dtype=np.float32)
    for local, (material, ids, ui) in enumerate(faces):
        tri = vertices[ids]
        e1, e2 = tri[1] - tri[0], tri[2] - tri[0]
        if np.dot(np.cross(e1, e2), direction) >= -1e-8:
            continue
        h = np.cross(direction, e2)
        det = np.dot(e1, h)
        if abs(det) < 1e-10:
            continue
        s = origins - tri[0]
        bu = (s @ h) / det
        q = np.cross(s, e1)
        bv, depth = (q @ direction) / det, (q @ e2) / det
        take = np.flatnonzero((bu >= -1e-7) & (bv >= -1e-7) & (bu + bv <= 1 + 1e-7) & (depth > 0))
        if not len(take):
            continue
        uv = coords[ui]
        t = uv[0] + bu[take, None] * (uv[1] - uv[0]) + bv[take, None] * (uv[2] - uv[0])
        image = textures[material]
        height, width = image.shape[:2]
        x = np.floor((t[:, 0] % 1) * width).astype(int) % width
        y = np.floor((1 - t[:, 1] % 1) * height).astype(int) % height
        distances[local, take] = depth[take]
        colors[local, take] = image[y, x]
    covered = int(np.isfinite(distances).any(axis=0).sum())
    order = np.argsort(distances, axis=0, kind='stable')
    pixels = np.arange(len(origins))
    accum, remaining, last = np.zeros((len(origins), 3)), np.ones(len(origins)), np.full(len(origins), -100.)
    for layer in range(len(faces)):
        index = order[layer]
        depth = distances[index, pixels]
        valid = np.isfinite(depth) & (remaining > 1e-5) & (np.abs(depth - last) > 1e-4)
        if not valid.any():
            continue
        rgba = colors[index, pixels]
        alpha = rgba[:, 3] * valid
        accum += remaining[:, None] * alpha[:, None] * rgba[:, :3]
        remaining *= 1 - alpha
        last[valid] = depth[valid]
    accum += remaining[:, None] * np.array(background)
    return np.uint8(np.clip(accum, 0, 1) * 255), covered


def _reduce(pixels, n, size):
    from PIL import Image
    return np.asarray(Image.fromarray(pixels.reshape(n, n, 3)).resize((size, size), Image.Resampling.LANCZOS),
                      dtype=np.uint8)


def bake_side(side, vertices, uvs, faces, textures, recipe, size, supersample):
    """One side panel (size x size RGB) of a four-corner ring body, sampled on the tapered quad as the output's
    triangles map it."""
    n = size * supersample
    lower, upper = recipe['panel_ring_pair']
    zlow, radius = recipe['rings'][lower]
    zhigh, upper_radius = recipe['rings'][upper]
    center = np.array(recipe['center_xy'], dtype=float)
    a, b = CORNERS[side] * radius + center, CORNERS[(side + 1) % 4] * radius + center
    corners = np.array(recipe.get('panel_corners', [[[*xy, zlow] for xy in CORNERS * radius + center],
                                                    [[*xy, zhigh] for xy in CORNERS * upper_radius + center]]))
    if 'panel_corners' in recipe:
        a, b = corners[0, side, :2], corners[0, (side + 1) % 4, :2]
    tangent = (b - a) / np.linalg.norm(b - a)
    outward = np.array([tangent[1], -tangent[0], 0.])
    out = np.empty((n * n, 3), dtype=np.uint8)
    for start in range(0, n * n, 4096):
        g = np.arange(start, min(start + 4096, n * n))
        u = (g % n + .5) / n
        v = 1 - (g // n + .5) / n
        points = np.column_stack([a + (b - a) * u[:, None], zlow + (zhigh - zlow) * v])
        if abs(upper_radius - radius) > 1e-8 or 'panel_corners' in recipe:
            p0, p1 = corners[0, side], corners[0, (side + 1) % 4]
            p2, p3 = corners[1, (side + 1) % 4], corners[1, side]
            points = np.where((u >= v)[:, None], (1 - u[:, None]) * p0 + (u - v)[:, None] * p1 + v[:, None] * p2,
                              (1 - v[:, None]) * p0 + u[:, None] * p2 + (v - u)[:, None] * p3)
        origins = points + outward * recipe['bake']['ray_offset']
        out[g], _ = _composite(origins, -outward, faces, vertices, uvs, textures, recipe['bake']['background_rgb'])
    return _reduce(out, n, size)


def bake_quad(points, source, textures, face_ids, size=28, supersample=4, background=(.08, .07, .05)):
    """A quad's picture from the source, sampled as the output's two triangles map it; (RGB, uncovered share)."""
    points = np.asarray(points, float)
    n = size * supersample
    yy, xx = np.mgrid[0:n, 0:n]
    u, v = (xx.ravel() + .5) / n, 1 - (yy.ravel() + .5) / n
    p0, p1, p2, p3 = points
    sample = np.where((u >= v)[:, None], (1 - u[:, None]) * p0 + (u - v)[:, None] * p1 + v[:, None] * p2,
                      (1 - v[:, None]) * p0 + u[:, None] * p2 + (v - u)[:, None] * p3)
    normal = np.cross(p1 - p0, p2 - p0)
    normal /= np.linalg.norm(normal)
    vertices, coords = np.asarray(source.v), np.asarray(source.uv)
    offset = np.ptp(vertices, axis=0).max() * 3
    faces = [source.faces[fi] for fi in face_ids]
    out = np.empty((len(sample), 3), np.uint8)
    covered = 0
    for start in range(0, len(sample), 2048):
        origins = sample[start:start + 2048] + normal * offset
        out[start:start + len(origins)], c = _composite(origins, -normal, faces, vertices, coords, textures, background)
        covered += c
    return _reduce(out, n, size), 1 - covered / len(sample)


# ---------------------------------------------------------------- kind "profile_shell"

def components(source, material):
    selected = [i for i, (m, ids, u) in enumerate(source.faces) if m == material]
    neighbors = defaultdict(set)
    for fi in selected:
        for i in source.faces[fi][1]:
            neighbors[i].add(fi)
    remaining, out = set(selected), []
    while remaining:
        todo, part = [min(remaining)], set()
        while todo:
            fi = todo.pop()
            if fi in part:
                continue
            part.add(fi)
            for vi in source.faces[fi][1]:
                todo.extend(neighbors[vi] - part)
        remaining -= part
        out.append(sorted(part))
    return out


def ring(source, rule):
    from scipy.spatial import ConvexHull
    v = np.asarray(source.v)
    ids = sorted({i for mat, ii, _ in source.faces if mat in rule['materials'] for i in ii})
    p = v[ids]
    p = p[np.abs(p[:, 2] - rule['z']) < rule.get('tolerance', .0001)]
    if not len(p):
        raise ValueError('Missing source ring')
    if rule.get('outer_per_quadrant'):
        center, selected = p[:, :2].mean(0), []
        for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            q = p[((p[:, 0] - center[0]) * sx > 0) & ((p[:, 1] - center[1]) * sy > 0)]
            if len(q) != rule.get('points_per_quadrant', 3):
                raise ValueError('Post cross-section signature changed')
            selected.append(q[np.argmax(np.sum((q[:, :2] - center) ** 2, axis=1))])
        p = np.array(selected)
    else:
        p = p[ConvexHull(p[:, :2]).vertices]
    if len(p) != rule['corners']:
        raise ValueError('Source ring corner signature changed')
    c = p[:, :2].mean(0)
    angles = np.mod(np.arctan2(p[:, 1] - c[1], p[:, 0] - c[0]) + np.pi / len(p), 2 * np.pi)
    return p[np.argsort(angles)]


def align_rings(rings):
    rings = [np.array(r, float).copy() for r in rings]
    for j in range(1, len(rings)):
        a = rings[j - 1][:, :2] - rings[j - 1][:, :2].mean(0)
        b = rings[j][:, :2] - rings[j][:, :2].mean(0)
        a /= np.linalg.norm(a, axis=1)[:, None]
        b /= np.linalg.norm(b, axis=1)[:, None]
        shifts = [float(np.sum((a - np.roll(b, k, axis=0)) ** 2)) for k in range(len(b))]
        shift = int(np.argmin(shifts))
        rings[j] = np.roll(rings[j], shift, axis=0)
        if np.max(np.linalg.norm(a - np.roll(b, shift, axis=0), axis=1)) > .25:
            raise ValueError('Profile corners have incompatible radial directions')
    return rings


def profile_shell(source, textures, settings):
    """(result, atlas RGB, report): the closed shell through the source rings, its appearance baked per patch into
    one atlas, the retained components copied whole."""
    kept, result, retained = set(), Model(), []
    for item in settings['retain_components']:
        parts = components(source, item['material'])
        ids = parts[item['component']]
        if len(ids) != item['triangles']:
            raise ValueError('Retained component signature changed')
        reference = Model()
        for fi in ids:
            m, ii, u = source.faces[fi]
            points, uv = np.asarray(source.v)[ii], np.asarray(source.uv)[u]
            group = 'retained_%s_%d' % (item['material'], item['component'])
            result.tri(points, uv, m, group)
            reference.tri(points, uv, m, group)
        check_retained_boundaries(source, reference, item['material'])
        kept.update(ids)
        retained.append(reference)
    rings = [ring(source, r) for r in settings['rings']]
    if len({len(r) for r in rings}) != 1:
        raise ValueError('Profile ring sizes disagree')
    rings = align_rings(rings)
    patches, count, triangle_patches = [], len(rings[0]), set()
    for lower, upper in zip(rings, rings[1:]):
        for i in range(count):
            k = (i + 1) % count
            patches.append([lower[i], lower[k], upper[k], upper[i]])
    cap_records = []
    if settings.get('tips'):
        for end, poly in (('bottom', rings[0]), ('top', rings[-1])):
            rule = settings['tips'][end]
            v = np.asarray(source.v)
            ids = sorted({i for m, ii, _ in source.faces if m == rule['material'] for i in ii})
            q = v[ids]
            q = q[np.abs(q[:, 2] - rule['z']) < .0001]
            if len(q) != 1:
                raise ValueError('Source tip signature changed')
            tip = q[0]
            for i in range(count):
                k = (i + 1) % count
                a, b = (poly[k], poly[i]) if end == 'bottom' else (poly[i], poly[k])
                triangle_patches.add(len(patches))
                patches.append([a, b, tip, a + tip - b])
    for poly in (() if settings.get('tips') else (rings[0][::-1], rings[-1])):
        a, b = poly[:, :2].min(0), poly[:, :2].max(0)
        z = float(poly[:, 2].mean())
        quad = np.array([[a[0], a[1], z], [b[0], a[1], z], [b[0], b[1], z], [a[0], b[1], z]])
        if np.cross(poly[1] - poly[0], poly[2] - poly[0])[2] < 0:
            quad = quad[::-1]
        cap_records.append((len(patches), poly, quad))
        patches.append(quad)
    size = settings.get('tile_size', 28)
    slot, columns = size + 4, 1
    while columns * columns < len(patches):
        columns *= 2
    atlas = np.zeros((columns * slot, columns * slot, 3), np.uint8)
    uvs, coverage = [], []
    tex = dict(textures)
    for m in settings.get('frost_materials', []):
        tex[m] = tex[m].copy()
        tex[m][:, :, 3] = 1
    face_ids = [i for i, (m, _, _) in enumerate(source.faces)
                if i not in kept and m not in settings.get('bake_exclude_materials', [])]
    for i, quad in enumerate(patches):
        image, miss = bake_quad(quad, source, tex, face_ids, size, settings.get('supersample', 4))
        coverage.append(miss)
        row, col = divmod(i, columns)
        atlas[row * slot:(row + 1) * slot, col * slot:(col + 1) * slot] = np.pad(image, ((2, 2), (2, 2), (0, 0)),
                                                                                  mode='edge')
        a, b = (col * slot + 2) / len(atlas), (col * slot + size + 2) / len(atlas)
        c, d = 1 - (row * slot + size + 2) / len(atlas), 1 - (row * slot + 2) / len(atlas)
        uv = [(a, c), (b, c), (b, d), (a, d)]
        uvs.append(np.array(uv))
        if i in triangle_patches:
            result.tri(quad[:3], uv[:3], 'panels', 'shell')
        elif not any(index == i for index, poly, q in cap_records):
            result.quad(quad, uv, 'panels', 'shell')
    for index, poly, quad in cap_records:
        a = quad[0]
        e1, e2 = quad[1] - a, quad[3] - a
        u, v = (poly - a) @ e1 / (e1 @ e1), (poly - a) @ e2 / (e2 @ e2)
        uv = uvs[index][0] + u[:, None] * (uvs[index][1] - uvs[index][0]) + v[:, None] * (uvs[index][3] - uvs[index][0])
        for i in range(1, len(poly) - 1):
            ii = [0, i, i + 1]
            result.tri(poly[ii], uv[ii], 'panels', 'shell')
    return result, atlas, {'retained_components': len(retained), 'patches': len(patches),
                           'patch_uncovered_fraction_max': float(max(coverage) if coverage else 0.0)}


# ---------------------------------------------------------------- kinds "dunmer_lantern" / "common_lantern"

def source_post_rings(source, settings):
    """The four outer post corners at each source height (taper and asymmetry kept)."""
    config = settings['panel_rings_from_source']
    center, v = np.array(settings['center_xy']), np.asarray(source.v)
    used = sorted({i for m, ids, _ in source.faces if m == config['material'] for i in ids})
    rings = []
    for z in config['heights']:
        candidates = v[used]
        candidates = candidates[np.abs(candidates[:, 2] - z) < 1e-4]
        out = []
        for sx, sy in CORNERS:
            quadrant = candidates[((candidates[:, 0] - center[0]) * sx > 0) & ((candidates[:, 1] - center[1]) * sy > 0)]
            if len(quadrant) != 4:
                raise ValueError('Source post cross-section signature changed')
            out.append(quadrant[np.argmax(np.sum((quadrant[:, :2] - center) ** 2, axis=1))])
        rings.append(np.array(out))
    return rings


def tile_uv(side, size=28):
    slot = size + 4
    total = slot * 2
    row, col = divmod(side, 2)
    a, b = (col * slot + 2) / total, (col * slot + size + 2) / total
    c, d = 1 - (row * slot + size + 2) / total, 1 - (row * slot + 2) / total
    return [(a, c), (b, c), (b, d), (a, d)]


def lantern(source, textures, settings):
    """(result, atlas RGB, kept handle model) of a four-corner ring lantern with its four sides baked."""
    settings = dict(settings)
    result, center, rings = Model(), np.array(settings['center_xy']), []
    for z, radius in settings['rings']:
        rings.append([(*xy, z) for xy in CORNERS * radius + center])
    if 'panel_rings_from_source' in settings:
        settings['panel_corners'] = source_post_rings(source, settings)
        for index, r in zip(settings['panel_ring_pair'], settings['panel_corners']):
            rings[index] = r
    size = settings['bake'].get('texture_size', 28)
    slot = size + 4
    atlas = np.zeros((slot * 2, slot * 2, 3), dtype=np.uint8)
    tex = dict(textures)
    for material in settings.get('frost_materials', []):
        tex[material] = tex[material].copy()
        tex[material][:, :, 3] = 1.0
    for side in range(4):
        data = bake_side(side, np.asarray(source.v), np.asarray(source.uv), source.faces, tex, settings, size,
                         settings['bake'].get('supersample', 4))
        data = np.pad(data, ((2, 2), (2, 2), (0, 0)), mode='edge')
        row, col = divmod(side, 2)
        atlas[row * slot:row * slot + slot, col * slot:col * slot + slot] = data
    for j, material in enumerate(settings['bands']):
        for side in range(4):
            k = (side + 1) % 4
            points = [rings[j][side], rings[j][k], rings[j + 1][k], rings[j + 1][side]]
            if material == 'panels':
                uv = tile_uv(side, size)
            else:
                uv = [(0, 0), (1, 0), (1, 1), (0, 1)]
                if settings['kind'] == 'common_lantern':
                    if material == 'm7':
                        uv = [(side - .5, .1708), (side + .5, .1708), (side + .5, .9263), (side - .5, .9263)]
                    elif material == 'm4':
                        uv = [(0, .15), (1, .15), (1, .85), (0, .85)]
                    elif material == 'm6':
                        a, b, c, step = .489369, .885798, 1.002107, .25
                        uv = [(a, c - side * step), (a, c - (side + 1) * step), (b, c - (side + 1) * step),
                              (b, c - side * step)]
            result.quad(points, uv, material)
    cap = [(0, 0), (1, 0), (1, 1), (0, 1)]
    if 'bottom_tip' in settings:
        tip = (*center, settings['bottom_tip'])
        for side in range(4):
            result.tri([rings[0][(side + 1) % 4], rings[0][side], tip], [(1, 1), (0, 1), (.5, 0)], settings['frame'],
                       'shell')
    else:
        result.quad(list(reversed(rings[0])), cap, settings['bottom_material'])
    result.quad(rings[-1], cap, settings['frame'])
    handle = settings['handle']

    def selected(m, p):
        return m == handle['material'] and p[:, 2].min() >= handle['min_z'] and np.max(np.abs(p[:, 1])) < handle['max_abs_y']
    if copy_faces(result, source, selected, 'retained_handle') != handle['triangles']:
        raise ValueError('Source handle signature mismatch')
    reference = Model()
    copy_faces(reference, source, selected, 'retained_handle')
    check_retained_boundaries(source, reference, handle['material'])
    return result, atlas, reference


# ---------------------------------------------------------------- the builder's mesh

def to_builder(model, material_count, atlas=None, texsize=64):
    """(vertices N x 9, faces M x 4) of a recipe model: positions as they are (Morrowind units), the NIF's texture v
    (1 - v'), materials 'm<index>' to the source's own index and 'panels' to MATERIAL_COUNT (the converter's baked
    material, its picture ATLAS: its coordinates scaled so one picture texel is one converter texel)."""
    if atlas is not None:
        scale = np.array([atlas.shape[1] / float(texsize), atlas.shape[0] / float(texsize)])
    positions, uvs = np.asarray(model.v, dtype=float), np.asarray(model.uv, dtype=float)
    out_v, out_f, corner = [], [], {}
    for material, ids, uv_ids in model.faces:
        if material == 'panels':
            if atlas is None:
                raise ValueError('a panel face without its picture')
            target = material_count
        else:
            target = int(material[1:])
            if not 0 <= target < material_count:
                raise ValueError('material %s outside the source model' % material)
        tri = []
        for pid, uid in zip(ids, uv_ids):
            u, v = uvs[uid]
            if target == material_count:
                st = (u * scale[0], (1.0 - v) * scale[1])
            else:
                st = (u, 1.0 - v)
            row = (*(float(c) for c in positions[pid]), float(st[0]), float(st[1]), 255, 255, 255, 255)
            key = (row, target)
            if key not in corner:
                corner[key] = len(out_v)
                out_v.append(row)
            tri.append(corner[key])
        out_f.append([*tri, target])
    return np.asarray(out_v, dtype=float), np.asarray(out_f, dtype=np.int64)


def rebuild(vertices, faces, material_count, textures, row, materials=None):
    """The method-2 model of KIND row['kind'] from the builder's source mesh: (visual vertices, visual faces, the
    panel picture or None, report). TEXTURES: {source material index: RGBA uint8} (the bake kinds read them);
    MATERIALS: the source's material records (a baked material must have a neutral tint, as the recipe saw it)."""
    kind, settings = row['kind'], row['recipe']['settings']
    source = to_source(vertices, faces)
    if len(source.faces) != row['recipe']['source_triangles']:
        raise ValueError('%s: the source has %d triangles, the recipe %d' % (kind, len(source.faces),
                                                                           row['recipe']['source_triangles']))
    tex = {'m%d' % m: np.asarray(t, dtype=float) / 255 for m, t in (textures or {}).items()}
    atlas, closed = None, ()
    if kind == 'conservative':
        result = conservative(source, settings)
    elif kind == 'profile_shell':
        _check_tints(materials, settings)
        result, atlas, _ = profile_shell(source, tex, settings)
        closed = ('shell',)
    elif kind in ('dunmer_lantern', 'common_lantern'):
        _check_tints(materials, settings)
        result, atlas, handle = lantern(source, tex, settings)
        if statistics(result)['groups'].get('retained_handle') != statistics(handle)['groups']['retained_handle']:
            raise ValueError('Retained handle topology changed')
        closed = ('shell',)
    else:
        raise ValueError('unknown method-2 kind %r' % kind)
    before, after, error = check_pair(source, result, closed)
    expected = row['recipe'].get('expected_triangles')
    if expected is not None and after['triangles'] != expected:
        raise ValueError('%s: %d triangles, the recipe expects %d' % (kind, after['triangles'], expected))
    out_v, out_f = to_builder(result, material_count, atlas)
    report = {'kind': kind, 'source_triangles': before['triangles'], 'triangles': after['triangles'],
              'positions': after['positions'], 'bounds_error_mw': error,
              'open_edges': after['global_topology']['open_edges'],
              'source_open_edges': before['global_topology']['open_edges'],
              'picture': None if atlas is None else list(atlas.shape[:2])}
    return out_v, out_f, atlas, report


def _check_tints(materials, settings):
    for i, mat in enumerate(materials or ()):
        if ('m%d' % i) in settings.get('bake_exclude_materials', ()):
            continue
        if not np.allclose(mat.get('diffuse', [1, 1, 1]), [1, 1, 1]) or abs(float(mat.get('alpha', 1)) - 1) > 1e-6:
            raise ValueError('a baked source material with a tint or opacity needs its own recipe (m%d)' % i)
