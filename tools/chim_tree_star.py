#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Tree type 2, route D (TREES-DEPTH-56, docs/WORLD_TREE_SPRITES.md): the Solstheim trees as star prisms.

Seen from above each tree is a four-pointed star (four long points with inner corners between them); the crown is a
closed opaque volume of 2-4 stacked tiers, each tier a star smaller than the one below, tapering upward like a spruce,
starting at the model's lowest needle vertex, on a hexagonal bark trunk without caps. Every face is an ordinary opaque
face, so the CHIM model path draws it as it is (no see-through texels: CHIM-MODEL-FENCE-FACES-64). The sizes come from
each model's own vertices: a tier's star reaches as far as the model's crown reaches in that tier's height band, the
trunk is as wide as the bark. The needle faces take an opaque texture baked from the model's side view (see-through
texels filled from their neighbours), the trunk the bark. Collision stays the model's own.

Use: tools/chim_tree_star.py --tree-star CONFIG <tools/chim_build.py arguments>. It runs tools/chim_build.py in this
process with the mesh step of the configured tree models replaced (prepare_mesh_bsp._prepare_model, read by
chim.build.mesh_unit at call time; the mesh unit key carries the star's settings, so a unit cache never mixes the
two). TEST BUILDS ONLY: the stage chim-sol runs it when tools/build.py --chim-sol-tree-copies star; the base CHIM stage
never does, and chim_build.py and the converters are unchanged, so no base key moves.
"""
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

CONFIG = Path(__file__).resolve().parents[1] / 'config' / 'tree-copies.json'


def load_star(path=CONFIG, layer='bloodmoon'):
    doc = json.loads(Path(path).read_text(encoding='utf-8'))
    if doc.get('schema') != 'aw-tree-copies-1':
        raise ValueError('Unknown tree copies schema')
    s = dict(doc['star_prism'])
    if not isinstance(s['tiers'], int) or not 2 <= s['tiers'] <= 4:
        raise ValueError('star_prism tiers must be 2, 3 or 4')
    for key in ('point_depth', 'crown_bottom_share', 'tier_overlap', 'trunk_half_width_share', 'inner_shade'):
        if not 0 <= float(s[key]) < 1:
            raise ValueError('star_prism %s must be in [0, 1)' % key)
    if not float(s['texture_units']) > 0:
        raise ValueError('star_prism texture_units must be positive')
    patterns = [p.casefold() for p in doc['layers'][layer]['model_stem_contains']]
    return s, patterns


def is_star_model(source, patterns):
    stem = source.replace('\\', '/').casefold().rsplit('/', 1)[-1]
    return stem.endswith('.nif') and any(p in stem for p in patterns)


def star_ring(cx, cy, z, outer, inner):
    """Eight corners of a four-pointed star at height Z: points at 0, 90, 180, 270 degrees, inner corners between."""
    out = []
    for k in range(8):
        a = math.radians(45 * k)
        r = outer if k % 2 == 0 else inner
        out.append((cx + r * math.cos(a), cy + r * math.sin(a), z))
    return out


def star_prism(vertices, faces, materials, settings, textures=None):
    """(vertices, triangles, report) of the star prism for one model's source geometry (the visual primitive format:
    rows x y z u v r g b a; triangles a b c material)."""
    import numpy as np
    v = np.asarray(vertices, dtype=float)
    f = np.asarray(faces, dtype=int)
    p = v[np.unique(f[:, :3]), :3]
    lo, hi = p.min(0), p.max(0)
    cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
    height = hi[2] - lo[2]
    if height <= 0:
        raise ValueError('Flat tree model')
    # the needles: the textured material with the largest area
    tri = v[f[:, :3], :3]
    area = np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1) / 2
    best, best_area = None, -1.0
    for mat in sorted(set(f[:, 3].tolist())):
        if materials[mat].get('texture_index') is None:
            continue
        a = float(area[f[:, 3] == mat].sum())
        if a > best_area:
            best, best_area = mat, a
    if best is None:
        best = int(f[0, 3])
    # the bark: the textured material nearest the trunk axis (its vertices' median distance), when the model has
    # more than one; every other material is the crown (the Solstheim spruces carry one material per branch)
    # With TEXTURES ({texture index: RGBA}) the crown is every material whose texture has see-through texels (the
    # needle cards) and the bark the opaque one nearest the axis (roots and other opaque parts are neither)
    textured = [mat for mat in sorted(set(f[:, 3].tolist())) if materials[mat].get('texture_index') is not None]
    bark = None

    def axis_distance(mat):
        q = v[np.unique(f[f[:, 3] == mat, :3]), :3]
        return float(np.median(np.hypot(q[:, 0] - cx, q[:, 1] - cy)))
    if textures is not None and len(textured) > 1:
        def clear(mat):
            t = textures.get(materials[mat]['texture_index'])
            return t is not None and float((np.asarray(t)[:, :, 3] < 128).mean()) > 0.05
        crown_mats = [mat for mat in textured if clear(mat)]
        opaque = [mat for mat in textured if not clear(mat)]
        if crown_mats and opaque:
            bark = min(opaque, key=axis_distance)
        else:
            crown_mats = []
    if bark is None and len(textured) > 1:
        bark = min(textured, key=axis_distance)
        crown_mats = [mat for mat in textured if mat != bark]
    if bark is not None:
        best = max(crown_mats, key=lambda mat: float(area[f[:, 3] == mat].sum()))
    else:
        crown_mats = [best]
    tiers = int(settings['tiers'])
    depth = float(settings['point_depth'])
    # the crown starts where the model's needles start (its lowest needle vertex), so the bare trunk shows below
    needle_z = v[np.unique(f[np.isin(f[:, 3], crown_mats), :3]), 2]
    bottom = float(needle_z.min()) if bark is not None and needle_z.size else \
        lo[2] + height * float(settings['crown_bottom_share'])
    span = (hi[2] - bottom) / tiers
    overlap = float(settings['tier_overlap'])
    radial = np.hypot(p[:, 0] - cx, p[:, 1] - cy)
    shade = int(round(255 * (1 - float(settings['inner_shade']))))
    unit = float(settings['texture_units'])
    out_v, out_f = [], []

    def quad(a, b, c, d, inner_ids=()):
        # one face of four corners (a b bottom, c d top), UV: along the bottom edge and up, in texture_units
        # s: the distance along the bottom edge for every corner, so both triangles share one affine mapping and
        # the converter keeps the quad one face (a trapezoid with s = width at its short top edge would split)
        width = math.dist(a[:2], b[:2]) or 1.0
        ex, ey = (b[0] - a[0]) / width, (b[1] - a[1]) / width
        corners = [(q, (q[0] - a[0]) * ex + (q[1] - a[1]) * ey, q[2]) for q in (a, b, c, d)]
        start = len(out_v)
        for k, (q, s, t) in enumerate(corners):
            g = shade if k in inner_ids else 255
            out_v.append([*q, s / unit, -t / unit, g, g, g, 255])
        out_f.append([start, start + 1, start + 2, best])
        out_f.append([start, start + 2, start + 3, best])

    rings = []
    for k in range(tiers):
        z0 = bottom + k * span - (span * overlap if k else 0)
        z1 = bottom + (k + 1) * span
        band = radial[(p[:, 2] >= z0) & (p[:, 2] <= z1)]
        outer = float(band.max()) if band.size else float(radial.max()) * (1 - k / tiers)
        top_outer = outer * (0.35 if k < tiers - 1 else 0.0)
        rings.append((star_ring(cx, cy, z0, outer, outer * (1 - depth)),
                      star_ring(cx, cy, z1, top_outer, top_outer * (1 - depth)), k == tiers - 1))
    for low, high, apex in rings:
        for k in range(8):
            j = (k + 1) % 8
            inner = tuple(i for i, n in ((0, k), (1, j), (2, j), (3, k)) if n % 2)
            if apex:                                     # the top tier closes on one point
                start = len(out_v)
                for i, q in enumerate((low[k], low[j], high[0])):
                    g = shade if (i == 0 and k % 2) or (i == 1 and j % 2) else 255
                    out_v.append([*q, (math.dist(low[k][:2], low[j][:2]) if i == 1 else 0) / unit, -q[2] / unit,
                                  g, g, g, 255])
                out_f.append([start, start + 1, start + 2, best])
            else:
                quad(low[k], low[j], high[j], high[k], inner)
        # the tier's underside: a fan from its centre (seen from below, walking under the lowest tier); off by
        # default (settings 'undersides'): the engine posts one face per fan polygon side it sees, 8 per tier
        if not settings.get('undersides', False):
            continue
        start = len(out_v)
        out_v.append([cx, cy, low[0][2], 0, 0, shade, shade, shade, 255])
        for q in low:
            out_v.append([*q, (q[0] - cx) / unit, (q[1] - cy) / unit, shade, shade, shade, 255])
        for k in range(8):
            out_f.append([start, start + 1 + (k + 1) % 8, start + 1 + k, best])
    # the trunk: a prism of trunk_sides faces (6, a hexagon) with the bark, no caps (the crown covers its top, the
    # ground its bottom); its radius from the bark vertices near the ground and just under the crown (a slight taper)
    sides = int(settings.get('trunk_sides', 6))
    trunk_mat = bark if bark is not None else best
    if bark is not None:
        bv = v[np.unique(f[f[:, 3] == bark, :3]), :3]
        br = np.hypot(bv[:, 0] - cx, bv[:, 1] - cy)
        zb0, zb1 = float(bv[:, 2].min()), float(bv[:, 2].max())
        low_band = br[bv[:, 2] <= zb0 + 0.15 * (zb1 - zb0)]
        high_band = br[(bv[:, 2] >= bottom - 0.15 * (zb1 - zb0)) & (bv[:, 2] <= bottom)]
        r0 = float(np.median(low_band)) if low_band.size else float(np.median(br))
        r1 = float(np.median(high_band)) if high_band.size else r0
        r1 = min(r0, r1) if r1 > 0 else r0                 # a taper upward, never a widening
    else:
        r0 = r1 = float(settings['trunk_half_width_share']) * float(radial.max())
    if r0 > 0 and sides >= 3:
        z0, z1 = lo[2], bottom + span * 0.5               # up into the lowest tier
        ring0 = [(cx + r0 * math.cos(2 * math.pi * k / sides), cy + r0 * math.sin(2 * math.pi * k / sides), z0)
                 for k in range(sides)]
        ring1 = [(cx + r1 * math.cos(2 * math.pi * k / sides), cy + r1 * math.sin(2 * math.pi * k / sides), z1)
                 for k in range(sides)]
        before = len(out_f)
        for k in range(sides):
            j = (k + 1) % sides
            width = math.dist(ring0[k][:2], ring0[j][:2]) or 1.0
            ex, ey = (ring0[j][0] - ring0[k][0]) / width, (ring0[j][1] - ring0[k][1]) / width
            start = len(out_v)
            for q in (ring0[k], ring0[j], ring1[j], ring1[k]):
                s = (q[0] - ring0[k][0]) * ex + (q[1] - ring0[k][1]) * ey
                out_v.append([*q, s / unit, -q[2] / unit, 255, 255, 255, 255])
            out_f.append([start, start + 1, start + 2, trunk_mat])
            out_f.append([start, start + 2, start + 3, trunk_mat])
        trunk_faces = (len(out_f) - before) // 2
    else:
        trunk_faces, r0, r1 = 0, 0.0, 0.0
    report = {'kind': 'star_prism', 'tiers': tiers, 'point_depth': depth, 'triangles': len(out_f),
              'source_triangles': int(len(f)), 'material': int(best),
              'bark_material': None if bark is None else int(bark), 'crown_materials': [int(x) for x in crown_mats],
              'crown_bottom': round(bottom, 3),
              'trunk': {'sides': trunk_faces, 'radius_bottom': round(r0, 3), 'radius_top': round(r1, 3)}}
    return np.asarray(out_v, dtype=float), np.asarray(out_f, dtype=np.int64), report


def needle_texture(vertices, faces, materials, textures, material, size=64):
    """An opaque size x size RGB needle texture for the star faces, baked from the model's own side view: the crown
    (the faces of MATERIAL) seen across, its see-through texels filled from the nearest covered texel (as
    surface_flatten.bake_panel fills its panels), so no texel of the star draws the black of a see-through needle."""
    import numpy as np
    from scipy.ndimage import distance_transform_edt
    from preview_scenery import render
    v = np.asarray(vertices, dtype=float)
    f = np.asarray(faces, dtype=int)
    crown = f[np.isin(f[:, 3], list(material) if isinstance(material, (list, tuple)) else [material])]
    if not len(crown):
        crown = f
    p = v[np.unique(crown[:, :3]), :3]
    cx, cy = (p[:, 0].min() + p[:, 0].max()) / 2, (p[:, 1].min() + p[:, 1].max()) / 2
    v = v.copy(); v[:, 0] -= cx; v[:, 1] -= cy
    radius = float(np.hypot(p[:, 0] - cx, p[:, 1] - cy).max()) or 1.0
    # the middle half of the crown's width and height: needles, not the sky around the outline
    lo_z, hi_z = float(p[:, 2].min()), float(p[:, 2].max())
    mid = (lo_z + hi_z) / 2
    rgba = np.array(render(v, crown, materials, textures, 0, (size, size),
                           (-radius / 2, radius / 2, mid - (hi_z - lo_z) / 4, mid + (hi_z - lo_z) / 4)))
    covered = rgba[:, :, 3] >= 128
    rgb = rgba[:, :, :3].copy()
    if not covered.any():
        raise ValueError('Needle bake has no covered texels')
    nearest = distance_transform_edt(~covered, return_distances=False, return_indices=True)
    rgb[~covered] = rgb[tuple(nearest[:, ~covered])]
    return rgb.astype(np.uint8), float(covered.mean())


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


def install(settings, patterns):
    """Replace the mesh step of the star models (in this process and the workers it forks)."""
    import prepare_mesh_bsp
    import visual_primitives
    from chim import build as chim_build_mod
    from mwad.scene import read_asset, unpack_geometry
    original_prepare = prepare_mesh_bsp._prepare_model
    original_visual = visual_primitives.make_visual
    original_fingerprint = chim_build_mod.mesh_fingerprint
    tag = json.dumps(settings, sort_keys=True)

    def make_visual(s):
        if s.get('kind') == 'aw_star_prism':
            v, f, _ = star_prism(s['_vertices'], s['_faces'], s['_materials'], settings, s.get('_textures'))
            return v, f
        return original_visual(s)

    def prepare(task):
        mi, m, profile, archive_path, *extras = task
        if not is_star_model(m['source'], patterns):
            return original_prepare(task)
        with Path(archive_path).open('rb') as archive:
            vv, ff, _ = unpack_geometry(read_asset(archive, m))
            textures = source_textures(archive, extras[0], m['materials']) if extras else None
        star = {'kind': 'aw_star_prism', '_vertices': vv, '_faces': ff, '_materials': m['materials'],
                '_textures': textures}
        clean = {k: v for k, v in profile.items() if k not in ('ratio', 'flatten', 'visual_panel')}
        out = original_prepare((mi, m, dict(clean, visual_primitive=star), archive_path, *extras))
        _, (v, f, polys, pieces, lod) = out
        report = star_prism(vv, ff, m['materials'], settings, textures)[2]
        lod['visual_primitive'] = 'aw_star_prism'
        if settings.get('needle_texture', 'baked') == 'baked' and textures is not None:
            # the star's needle faces take an opaque texture baked from the model's side view: the converter's
            # flattened-panel material (index = the material count, its image in lod['_flat_rgb'])
            size = int(profile.get('texture_size', 64))
            rgb, share = needle_texture(vv, ff, m['materials'], textures, report['crown_materials'], size)
            flat = len(m['materials'])
            polys = [(poly, flat if mat == report['material'] else mat, ax, off, normal)
                     for poly, mat, ax, off, normal in polys]
            lod['_flat_rgb'] = rgb
            report['needle_texture'] = {'size': size, 'covered_share_before_fill': round(share, 4)}
        lod['star_prism'] = report
        return mi, (v, f, polys, pieces, lod)

    def fingerprint(model, profile, texture_records, kind='mesh'):
        key = original_fingerprint(model, profile, texture_records, kind)
        if is_star_model(model['source'], patterns):
            import hashlib
            return hashlib.sha256((str(key) + '|aw_star_prism|' + tag).encode()).hexdigest()
        return key

    prepare_mesh_bsp._prepare_model = prepare
    visual_primitives.make_visual = make_visual
    chim_build_mod.mesh_fingerprint = fingerprint


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2 or argv[0] != '--tree-star':
        raise SystemExit('usage: chim_tree_star.py --tree-star CONFIG <chim_build.py arguments>')
    settings, patterns = load_star(argv[1])
    print('TREE STAR: tiers %d, point depth %.2f, models with %s' % (settings['tiers'], float(settings['point_depth']),
                                                                     ', '.join(patterns)), flush=True)
    install(settings, patterns)
    # the worker pool spawns fresh interpreters: each installs the same mesh step at start-up (tree_star_site)
    import os
    os.environ['AMIWIND_TREE_STAR'] = str(Path(argv[1]).resolve())
    site = str(Path(__file__).resolve().parent / 'tree_star_site')
    os.environ['PYTHONPATH'] = os.pathsep.join([site, *filter(None, os.environ.get('PYTHONPATH', '').split(os.pathsep))])
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import chim_build
    sys.argv = [str(Path(__file__).resolve().parent / 'chim_build.py'), *argv[2:]]
    return chim_build.main()


if __name__ == '__main__':
    sys.exit(main())
