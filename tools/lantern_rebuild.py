# SPDX-License-Identifier: GPL-3.0-only
# Created by FlyingFathead a.k.a. Horstator. Thanks to ChaosWhisperer.
"""Method 2, kind "lantern_rings": a low-polygon lantern rebuilt from the user's own model, with baked side panels.

The body is six four-corner rings, capped top and bottom (base, metal bands, the panels, the roof as a truncated
square pyramid: four planar sides of two triangles each); the source handle's triangles are kept as they are. The
posts, braces, glass and candle behind each side are baked into one opaque picture per side (default), or replaced by
one procedural frosted picture for all four ("frosted": no game artwork, cheaper). Nothing of the game is in this file
or in the recipe (config/model-method-2.json: numbers only); the mesh and the pictures are made at build time from the
model and textures the builder exported from the user's own game files (tools/model_method2.py runs it as a unit).

Units, at every step:
  - the builder's mesh (the scenery export's geometry packet, our NIF reader): Morrowind units, Z up; a vertex's
    texture coordinate v counts down the picture (texel row = v x height), as the NIF stores it;
  - the recipe: Quake units (Morrowind x 0.25) and the OBJ convention (v' = 1 - v), as the checkpoint measured them;
  - to_recipe_frame converts the builder's mesh into the recipe's frame (positions rounded to 5 decimals and v' to 6,
    the checkpoint's export precision), from_recipe_frame converts the rebuilt mesh back (positions / 0.25, v = 1 - v').
The rebuilt lantern keeps the source's origin: its bounds are the source's within the recipe's tolerance.
"""
from collections import Counter
from pathlib import Path, PurePosixPath

import numpy as np

QUAKE_PER_MORROWIND = 0.25          # prepare_quake.SCALE
POSITION_DECIMALS = 5
UV_DECIMALS = 6
CORNERS = np.array([[-1, -1], [1, -1], [1, 1], [-1, 1]])
KIND = 'lantern_rings'
PANELS = ('baked', 'frosted')
PANEL_SIZES = (16, 32, 64)          # a static texture's size (prepare_mesh_bsp: 16, 32 or 64 texels per UV unit)


# ---------------------------------------------------------------- units

def to_recipe_frame(vertices):
    """(points N x 3 in Quake units, uvs N x 2 in the OBJ convention) of builder vertices (N x 9: Morrowind x, y, z,
    u, v, r, g, b, a)."""
    v = np.asarray(vertices, dtype=float)
    points = np.round(v[:, :3] * QUAKE_PER_MORROWIND, POSITION_DECIMALS)
    uvs = np.round(np.column_stack((v[:, 3], 1.0 - v[:, 4])), UV_DECIMALS)
    return points, uvs


def from_recipe_frame(points, uvs):
    """Builder positions (Morrowind units) and texture coordinates (the NIF's v) of recipe-frame points and uvs."""
    points = np.asarray(points, dtype=float) / QUAKE_PER_MORROWIND
    uvs = np.asarray(uvs, dtype=float)
    return points, np.column_stack((uvs[:, 0], 1.0 - uvs[:, 1]))


# ---------------------------------------------------------------- the source

def check_source(points, faces, recipe):
    """The source must be the model the recipe was measured on (Quake units): its triangle count, distinct
    positions and bounds."""
    expected = recipe['expected_source']
    if len(faces) != expected['triangles'] or len(np.unique(points, axis=0)) != expected['unique_positions']:
        raise ValueError('lantern_rings: the source does not match the recipe (%d triangles, %d positions; the recipe '
                         'expects %d and %d)' % (len(faces), len(np.unique(points, axis=0)), expected['triangles'],
                                                 expected['unique_positions']))
    for key, actual in (('min', points.min(0)), ('max', points.max(0))):
        if not np.allclose(actual, expected[key], atol=expected['bound_tolerance'], rtol=0):
            raise ValueError('lantern_rings: the source bounds (%s %s) are not the recipe\'s %s (Quake units)'
                             % (key, np.round(actual, 5).tolist(), expected[key]))


def source_faces(faces):
    """[(material, [a, b, c], [a, b, c])] of builder faces (M x 4): every corner has its own texture coordinate in the
    builder's mesh, so a corner's position and uv share its index."""
    return [(int(f[3]), [int(f[0]), int(f[1]), int(f[2])], [int(f[0]), int(f[1]), int(f[2])]) for f in faces]


# ---------------------------------------------------------------- the rebuilt mesh

class Model:
    """The rebuilt mesh in the recipe's frame: distinct positions (Quake units), a uv per face corner (OBJ
    convention), faces (material name, position ids, uv ids)."""

    def __init__(self):
        self.vertices, self.uvs, self.faces, self.index = [], [], [], {}

    def vertex(self, point):
        key = tuple(round(float(x), 6) for x in point)
        if key not in self.index:
            self.index[key] = len(self.vertices)
            self.vertices.append(key)
        return self.index[key]

    def tri(self, ids, uv, material):
        uv_ids = list(range(len(self.uvs), len(self.uvs) + 3))
        self.uvs.extend(uv)
        self.faces.append((material, ids, uv_ids))

    def quad(self, ids, uv, material):
        for order in ((0, 1, 2), (0, 2, 3)):
            self.tri([ids[i] for i in order], [uv[i] for i in order], material)


def reconstruct(points, uvs, faces, recipe):
    """The lantern of the recipe (Quake units): the rings' bands and caps, and the source handle copied as it is."""
    model = Model()
    cx, cy = recipe['center_xy']
    rings = [[model.vertex((cx + x * radius, cy + y * radius, z)) for x, y in CORNERS] for z, radius in recipe['rings']]
    uv_recipe = recipe['uv']
    for j, band in enumerate(recipe['ring_band_materials']):
        for i in range(4):
            k = (i + 1) % 4
            ids = [rings[j][i], rings[j][k], rings[j + 1][k], rings[j + 1][i]]
            material = band
            if band == 'panels':
                material, uv = 'side_%d' % i, [(0, 0), (1, 0), (1, 1), (0, 1)]
            elif band == 'base':
                a, b = uv_recipe['base']
                uv = [(i - .5, a), (i + .5, a), (i + .5, b), (i - .5, b)]
            elif band == 'metal':
                a, b = uv_recipe['metal']
                uv = [(0, a), (1, a), (1, b), (0, b)]
            elif band == 'roof':
                a, b = uv_recipe['roof_u']
                c, step = uv_recipe['roof_v_start'], uv_recipe['roof_v_step']
                uv = [(a, c - i * step), (a, c - (i + 1) * step), (b, c - (i + 1) * step), (b, c - i * step)]
            else:
                raise ValueError('lantern_rings: unknown band material ' + str(band))
            model.quad(ids, uv, material)
    square_uv = [(0, 0), (1, 0), (1, 1), (0, 1)]
    model.quad(list(reversed(rings[0])), square_uv, 'base')
    model.quad(rings[-1], square_uv, 'metal')
    handle = recipe['handle']
    selected = []
    for material, ids, uv_ids in faces:
        p = points[ids]
        if (material == handle['source_material'] and np.min(p[:, 2]) >= handle['min_z']
                and np.max(np.abs(p[:, 1])) < handle['max_abs_y']):
            selected.append((ids, uv_ids))
    positions = {tuple(p) for ids, _ in selected for p in points[ids]}
    if len(selected) != handle['expected_triangles'] or len(positions) != handle['expected_vertices']:
        raise ValueError('lantern_rings: the recipe did not find the source handle (%d triangles, %d positions; '
                         'expected %d and %d)' % (len(selected), len(positions), handle['expected_triangles'],
                                                  handle['expected_vertices']))
    for ids, uv_ids in selected:
        model.tri([model.vertex(p) for p in points[ids]], [tuple(p) for p in uvs[uv_ids]], 'metal')
    expected = recipe['expected_output']
    if len(model.vertices) != expected['vertices'] or len(model.faces) != expected['triangles']:
        raise ValueError('lantern_rings: the rebuilt mesh has %d positions and %d triangles, the recipe %d and %d'
                         % (len(model.vertices), len(model.faces), expected['vertices'], expected['triangles']))
    return model


def validate(model, recipe):
    """The rebuilt mesh's shape: counts, no degenerate triangle, the body closed and wound one way, only the handle
    ends open, the roof's four sides planar. Returns the report."""
    vertices = np.asarray(model.vertices, dtype=float)
    rings = 4 * len(recipe['rings'])
    edges, areas = Counter(), []
    for _, ids, _ in model.faces:
        p = vertices[ids]
        areas.append(float(np.linalg.norm(np.cross(p[1] - p[0], p[2] - p[0])) / 2))
        for i in range(3):
            edges[(ids[i], ids[(i + 1) % 3])] += 1
    if min(areas) <= 1e-8:
        raise ValueError('lantern_rings: a degenerate rebuilt triangle')
    for (a, b), count in edges.items():
        if max(a, b) < rings and (count != 1 or edges[(b, a)] != 1):
            raise ValueError('lantern_rings: the body is not closed and wound one way')
    undirected = Counter()
    for (a, b), count in edges.items():
        undirected[tuple(sorted((a, b)))] += count
    open_edges = sum(v == 1 for v in undirected.values())
    if max(undirected.values()) != 2 or open_edges != recipe['expected_output'].get('open_edges', open_edges):
        raise ValueError('lantern_rings: unexpected topology (%d open edges)' % open_edges)
    roof = [vertices[ids] for material, ids, _ in model.faces if material == 'roof']
    for i in range(0, len(roof) - 1, 2):
        normal = np.cross(roof[i][1] - roof[i][0], roof[i][2] - roof[i][0])
        normal /= np.linalg.norm(normal)
        if np.max(np.abs((roof[i + 1] - roof[i][0]) @ normal)) > 1e-5:
            raise ValueError('lantern_rings: a roof side is not planar')
    return {'positions': len(vertices), 'triangles': len(model.faces), 'open_edges': open_edges,
            'minimum_triangle_area': min(areas), 'closed_body': True, 'roof_triangles': len(roof),
            'min': vertices.min(0).tolist(), 'max': vertices.max(0).tolist()}


# ---------------------------------------------------------------- the panels

def bake_side(side, vertices, uvs, faces, textures, recipe, size, supersample):
    """One side panel (size x size RGB, uint8): an orthographic grid of rays into the side, the front-facing source
    triangles hit, their textures sampled (repeating) and alpha-composited front to back, a hit at the depth of the
    last one counted once (shared triangle edges and coincident glass do not double the opacity), the rest over the
    recipe's dark background, supersampled and reduced with Lanczos. Recipe frame (Quake units, OBJ uvs); TEXTURES:
    {material: RGBA float array in [0, 1], row 0 the top of the picture}."""
    from PIL import Image
    n = size * supersample
    lower, upper = recipe['panel_ring_pair']
    zlow, radius = recipe['rings'][lower]
    zhigh, upper_radius = recipe['rings'][upper]
    if abs(upper_radius - radius) > 1e-8:
        raise ValueError('lantern_rings: the panel baker needs parallel vertical side panels')
    center = np.array(recipe['center_xy'], dtype=float)
    a, b = CORNERS[side] * radius + center, CORNERS[(side + 1) % 4] * radius + center
    tangent = (b - a) / np.linalg.norm(b - a)
    outward = np.array([tangent[1], -tangent[0], 0.])
    direction = -outward
    color_pixels = np.empty((n * n, 3), dtype=np.uint8)
    for start in range(0, n * n, 4096):
        pixels_global = np.arange(start, min(start + 4096, n * n))
        u = (pixels_global % n + .5) / n
        v = 1 - (pixels_global // n + .5) / n
        xy = a + (b - a) * u[:, None]
        origins = np.column_stack([xy, zlow + (zhigh - zlow) * v]) + outward * recipe['bake']['ray_offset']
        distances = np.full((len(faces), len(origins)), np.inf, dtype=np.float32)
        colors = np.zeros((len(faces), len(origins), 4), dtype=np.float32)
        for fi, (material, ids, uv_ids) in enumerate(faces):
            tri = vertices[ids]
            e1, e2 = tri[1] - tri[0], tri[2] - tri[0]
            if np.dot(np.cross(e1, e2), direction) >= -1e-8:
                continue
            h = np.cross(direction, e2)
            determinant = np.dot(e1, h)
            if abs(determinant) < 1e-10:
                continue
            s = origins - tri[0]
            bu = (s @ h) / determinant
            q = np.cross(s, e1)
            bv, distance = (q @ direction) / determinant, (q @ e2) / determinant
            indexes = np.flatnonzero((bu >= -1e-7) & (bv >= -1e-7) & (bu + bv <= 1 + 1e-7) & (distance > 0))
            if not len(indexes):
                continue
            uv = uvs[uv_ids]
            coordinates = uv[0] + bu[indexes, None] * (uv[1] - uv[0]) + bv[indexes, None] * (uv[2] - uv[0])
            image = textures[material]
            height, width = image.shape[:2]
            x = np.floor((coordinates[:, 0] % 1) * width).astype(int) % width
            y = np.floor((1 - coordinates[:, 1] % 1) * height).astype(int) % height
            distances[fi, indexes] = distance[indexes]
            colors[fi, indexes] = image[y, x]
        order = np.argsort(distances, axis=0, kind='stable')
        pixels = np.arange(len(origins))
        accum, remaining, last = np.zeros((len(origins), 3)), np.ones(len(origins)), np.full(len(origins), -100.)
        for layer in range(len(faces)):
            indexes = order[layer]
            depth = distances[indexes, pixels]
            valid = np.isfinite(depth) & (remaining > 1e-5) & (np.abs(depth - last) > 1e-4)
            if not valid.any():
                continue
            rgba = colors[indexes, pixels]
            alpha = rgba[:, 3] * valid
            accum += remaining[:, None] * alpha[:, None] * rgba[:, :3]
            remaining *= 1 - alpha
            last[valid] = depth[valid]
        accum += remaining[:, None] * np.array(recipe['bake']['background_rgb'])
        color_pixels[pixels_global] = np.uint8(np.clip(accum, 0, 1) * 255)
    image = Image.fromarray(color_pixels.reshape(n, n, 3))
    return np.asarray(image.resize((size, size), Image.Resampling.LANCZOS), dtype=np.uint8)


FROSTED_RGB = (226, 170, 92)        # warm, lit paper and glass
FROSTED_FRAME_RGB = (58, 42, 30)    # the posts at the panel's edges


def frosted_panel(size):
    """One frosted side panel (size x size RGB, uint8), made from numbers only (no game artwork): a warm glow with a
    fixed fine grain and a dark frame of posts, the same for every side and every placement."""
    yy, xx = np.mgrid[:size, :size]
    grain = ((xx * 7 + yy * 13) % 5 - 2) * 3
    rgb = np.clip(np.array(FROSTED_RGB)[None, None, :] + grain[..., None], 0, 255)
    frame = max(1, size // 16)
    edge = (xx < frame) | (xx >= size - frame) | (yy < frame) | (yy >= size - frame)
    rgb[edge] = FROSTED_FRAME_RGB
    return rgb.astype(np.uint8)


# ---------------------------------------------------------------- the builder's mesh

def rebuild(vertices, faces, material_count, textures, recipe, panels='baked'):
    """The rebuilt lantern as the builder draws it: (visual vertices N x 9 in Morrowind units with the NIF's v,
    visual faces M x 4, the panel picture (RGB uint8), report). Materials: the source's own for the base, the metal
    bands and the handle and the roof (the recipe's "materials"), and MATERIAL_COUNT (the converter's baked-panel
    material: its picture is the returned one) for the four sides. Baked panels: one picture of the four sides side by
    side (side i at u in [i, i + 1]); frosted: one picture for every side (u in [0, 1]).
    VERTICES, FACES: the source mesh (the scenery export's packet); TEXTURES: {source material: RGBA uint8 array} of
    every material the bake can see."""
    if panels not in PANELS:
        raise ValueError('lantern_rings: panels must be one of %s, not %r' % (', '.join(PANELS), panels))
    points, uvs = to_recipe_frame(vertices)
    faces = source_faces(faces)
    check_source(points, faces, recipe)
    model = reconstruct(points, uvs, faces, recipe)
    report = validate(model, recipe)
    size = int(recipe['bake']['texture_size'])
    if size not in PANEL_SIZES:
        raise ValueError('lantern_rings: the panel size must be 16, 32 or 64 texels')
    if panels == 'baked':
        images = {m: np.asarray(t, dtype=float) / 255 for m, t in textures.items()}
        missing = sorted({m for m, _, _ in faces} - set(images))
        if missing:
            raise ValueError('lantern_rings: no texture for source materials %s' % missing)
        sides = [bake_side(i, points, uvs, faces, images, recipe, size, int(recipe['bake']['supersample']))
                 for i in range(4)]
        picture = np.concatenate(sides, axis=1)
    else:
        picture = frosted_panel(size)
    names = dict(recipe['materials'])
    out_v, out_f, corner = [], [], {}
    positions = np.asarray(model.vertices, dtype=float)
    corner_uvs = np.asarray(model.uvs, dtype=float)
    for material, ids, uv_ids in model.faces:
        if material.startswith('side_'):
            side = int(material[5:])
            target = material_count
            shift = side if panels == 'baked' else 0
        else:
            target, shift = int(names[material]), 0
        tri = []
        for pid, uid in zip(ids, uv_ids):
            p, uv = from_recipe_frame(positions[[pid]], corner_uvs[[uid]])
            row = (*(float(c) for c in p[0]), float(uv[0, 0]) + shift, float(uv[0, 1]), 255, 255, 255, 255)
            key = (row, target)
            if key not in corner:
                corner[key] = len(out_v)
                out_v.append(row)
            tri.append(corner[key])
        out_f.append([*tri, target])
    out_v, out_f = np.asarray(out_v, dtype=float), np.asarray(out_f, dtype=np.int64)
    source_points = np.asarray(vertices, dtype=float)[:, :3]
    report.update(kind=KIND, panels=panels, panel_size=size, picture=list(picture.shape[:2]),
                  source_triangles=len(faces), source_positions=int(len(np.unique(points, axis=0))),
                  bounds_morrowind=[out_v[:, :3].min(0).tolist(), out_v[:, :3].max(0).tolist()],
                  source_bounds_morrowind=[source_points.min(0).tolist(), source_points.max(0).tolist()],
                  corners=len(out_v))
    return out_v, out_f, picture, report


# ---------------------------------------------------------------- a private product for inspection

def inside(base, relative):
    """BASE / RELATIVE without leaving BASE (no absolute path, no '..', no drive)."""
    relative = str(relative).replace('\\', '/')
    p = PurePosixPath(relative)
    if p.is_absolute() or '..' in p.parts or ':' in relative:
        raise ValueError('Expected a path inside the output folder: ' + relative)
    path = (Path(base) / relative).resolve()
    if not path.is_relative_to(Path(base).resolve()):
        raise ValueError('A reference resolves outside the output folder')
    return path


def write_product(out, visual_v, visual_f, picture, material_count, source_name='lantern'):
    """The rebuilt mesh as OBJ + MTL + PNG in a NEW folder OUT (the Toolkit's Mesh Compare reads OBJ), Quake units
    (Morrowind x 0.25), Z up, OBJ texture convention. The picture is made from the user's game files: the folder is a
    private build product, never part of a package or the repository. Refuses an existing folder."""
    from PIL import Image
    out = Path(out)
    if out.exists():
        raise ValueError('Output already exists; choose a new private folder')
    out.mkdir(parents=True)
    Image.fromarray(picture).save(out / 'panels.png')
    lines = ['# AmiWind method 2 rebuild: Quake units (Morrowind x 0.25), Z up; private build product',
             'mtllib %s.mtl' % source_name]
    lines += ['v %.6f %.6f %.6f' % tuple(p * QUAKE_PER_MORROWIND) for p in visual_v[:, :3]]
    lines += ['vt %.6f %.6f' % (u, 1 - v) for u, v in visual_v[:, 3:5]]
    current = None
    for a, b, c, m in visual_f:
        if m != current:
            lines.append('usemtl %s' % ('panels' if m == material_count else 'm%d' % m))
            current = m
        lines.append('f %d/%d %d/%d %d/%d' % (a + 1, a + 1, b + 1, b + 1, c + 1, c + 1))
    (out / ('%s.obj' % source_name)).write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
    mtl = ['newmtl panels', 'map_Kd panels.png', '']
    (out / ('%s.mtl' % source_name)).write_text('\n'.join(mtl), encoding='utf-8', newline='\n')
    return out / ('%s.obj' % source_name)


def obj_index(text, count):
    value = int(text)
    index = value - 1 if value > 0 else count + value
    if value == 0 or not 0 <= index < count:
        raise ValueError('OBJ index is out of range')
    return index


def read_obj(path):
    """(positions, uvs, faces [(material, position ids, uv ids)], {material: texture path}) of an OBJ product;
    polygons as triangle fans; a face without texture coordinates is refused."""
    path = Path(path)
    vertices, uvs, faces, libraries, material = [], [], [], [], ''
    for number, line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
        parts = line.split('#', 1)[0].split()
        if not parts:
            continue
        kind = parts[0]
        if kind == 'v':
            vertices.append([float(c) for c in parts[1:4]])
        elif kind == 'vt':
            uvs.append([float(c) for c in parts[1:3]])
        elif kind == 'mtllib':
            libraries.append(inside(path.parent, ' '.join(parts[1:]).strip('"')))
        elif kind == 'usemtl':
            material = ' '.join(parts[1:])
        elif kind == 'f':
            corners = [part.split('/') for part in parts[1:]]
            if len(corners) < 3 or any(len(c) < 2 or not c[1] for c in corners):
                raise ValueError('Line %d: texture UVs are required' % number)
            indexes = [(obj_index(c[0], len(vertices)), obj_index(c[1], len(uvs))) for c in corners]
            for i in range(1, len(indexes) - 1):
                tri = [indexes[0], indexes[i], indexes[i + 1]]
                faces.append((material, [c[0] for c in tri], [c[1] for c in tri]))
    textures = {}
    for library in libraries:
        current = ''
        for line in library.read_text(encoding='utf-8-sig').splitlines():
            fields = line.split('#', 1)[0].strip().split(None, 1)
            if len(fields) == 2 and fields[0] == 'newmtl':
                current = fields[1]
            elif len(fields) == 2 and fields[0] == 'map_Kd':
                textures[current] = inside(library.parent, fields[1].strip('"'))
    return np.asarray(vertices, dtype=float), np.asarray(uvs, dtype=float), faces, textures


def load_recipe(row):
    """The recipe of a method-2 row of kind lantern_rings, checked for the fields the rebuild reads."""
    recipe = row['recipe']
    for key in ('expected_source', 'center_xy', 'rings', 'panel_ring_pair', 'ring_band_materials', 'handle',
                'materials', 'uv', 'bake', 'expected_output'):
        if key not in recipe:
            raise ValueError('lantern_rings recipe without ' + key)
    if len(recipe['ring_band_materials']) != len(recipe['rings']) - 1:
        raise ValueError('lantern_rings recipe: one band material between each two rings')
    return recipe


if __name__ == '__main__':
    raise SystemExit('tools/lantern_rebuild.py is run by the builder (tools/model_method2.py); see docs/chim/MESH_METHODS.md')
