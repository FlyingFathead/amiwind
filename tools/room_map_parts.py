#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Small closed parts of a room map's props drawn as boxes (the prison ship's hammocks; PRISON-SHIP-POLY-COLLISION-65).

The hold's 14 hammocks (active_de_bed_30) are 536 faces each, 7,504 of the room's 26,628. The faces are in 19 closed
parts: ten rings and knots of 1 to 2.2 units (about 5 to 12 cm) carry 205 of them, two end knots of 4.75 units 120. The
mesh simplifier with locked borders keeps all of them (docs/chim/MESH_METHODS.md "Hot models": closed thin parts
have no border to lock, and simplified they stop spanning their own shape), so it saves nothing here.

This method replaces each closed part whose box is at most LIMIT units on its longest side by the six faces of that
box, in the part's own material and texture scale; the lightmaps are baked for the new faces as for any other. A box is
closed (no open edge the part did not have: the closed-edge rule) and spans its part exactly on every axis (the shape
guard of the simplifier); the parts are joined to nothing (a part is a set of faces sharing corners), so no seam moves.
The collision is untouched. A part of at most six faces stays as it is.

The models and limits are the table ROOM_MAP_SMALL_PARTS; --room-small-parts off keeps every part (the method before).
"""
import numpy as np

# the switch (--room-small-parts box|off, AMIWIND_ROOM_SMALL_PARTS; box by default) lives in room_map_env
from room_map_env import (ROOM_SMALL_PARTS_MODES, ROOM_SMALL_PARTS_VARIABLE,  # noqa: F401
                          export_room_small_parts, room_small_parts)

# model source -> the longest side (map units) up to which a closed part becomes its box
ROOM_MAP_SMALL_PARTS = {
    'meshes/f/active_de_bed_30.nif': 2.5,
}


def part_groups(polys, digits=4):
    """Index lists of the polygons joined by shared corners (positions rounded to DIGITS decimals)."""
    parent = {}

    def find(a):
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    keys = []
    for poly in polys:
        k = [tuple(np.round(np.asarray(p, float), digits)) for p in poly[0]]
        keys.append(k)
        for q in k[1:]:
            ra, rb = find(k[0]), find(q)
            if ra != rb:
                parent[rb] = ra
    groups = {}
    for i, k in enumerate(keys):
        groups.setdefault(find(k[0]), []).append(i)
    return list(groups.values())


def _winding(poly):
    """+1 when the polygon's corners turn counter-clockwise around its normal, else -1."""
    p = np.asarray(poly[0], float)
    n = np.asarray(poly[4], float)
    area = np.zeros(3)
    for i in range(len(p)):
        area += np.cross(p[i], p[(i + 1) % len(p)])
    return 1 if float(area @ n) >= 0 else -1


def box_polygons(lo, hi, material, scale, winding):
    """The six faces of the box lo..hi as converter polygons (points, material, axes, offset, normal): each face's
    texture axes along its two in-plane axes with the part's texture SCALE (texture repeats per unit)."""
    out = []
    for axis in range(3):
        for sign in (-1, 1):
            n = np.zeros(3)
            n[axis] = sign
            u, w = [a for a in range(3) if a != axis]
            c = hi[axis] if sign > 0 else lo[axis]
            quad = []
            for a, b in ((0, 0), (1, 0), (1, 1), (0, 1)):
                p = np.zeros(3)
                p[axis] = c
                p[u] = hi[u] if a else lo[u]
                p[w] = hi[w] if b else lo[w]
                quad.append(p)
            quad = np.array(quad)
            area = sum(np.cross(quad[i], quad[(i + 1) % 4]) for i in range(4))
            if (1 if float(area @ n) >= 0 else -1) != winding:
                quad = quad[::-1].copy()
            ax = np.zeros((3, 2))
            ax[u, 0] = scale
            ax[w, 1] = scale
            out.append((quad, material, ax, np.zeros(2), n))
    return out


def box_small_parts(prepared, limit, unit_scale):
    """Replace, in one prepared model record (v, f, polys, parts, lod), every closed part of at most LIMIT map units
    on its longest side (polygon units x UNIT_SCALE) and more than six faces by its box. Returns (record, receipt)."""
    v, f, polys, parts, lod = prepared
    keep, boxed, before = [], [], len(polys)
    winding = _winding(polys[0]) if polys else 1
    for group in part_groups(polys):
        pts = np.concatenate([np.asarray(polys[i][0], float) for i in group])
        lo, hi = pts.min(axis=0), pts.max(axis=0)
        if len(group) <= 6 or float((hi - lo).max()) * unit_scale > limit:
            keep.extend(group)
            continue
        if float((hi - lo).min()) <= 1e-6:
            keep.extend(group)          # a flat part: no box
            continue
        first = polys[group[0]]
        scale = float(np.mean([np.linalg.norm(np.asarray(polys[i][2], float), axis=0).mean() for i in group]))
        boxed.append((len(group), box_polygons(lo, hi, first[1], scale, winding)))
    new = [polys[i] for i in sorted(keep)] + [p for _, faces in boxed for p in faces]
    receipt = {'limit_units': limit, 'parts_boxed': len(boxed), 'faces_before': before, 'faces_after': len(new),
               'faces_of_boxed_parts': sum(n for n, _ in boxed)}
    lod = dict(lod, small_parts=receipt)
    return (v, f, new, parts, lod), receipt


def apply_room_small_parts(models, index):
    """Box the small parts of every model of ROOM_MAP_SMALL_PARTS in the prepared models of a room's scenery index
    (in place); returns {model source: receipt} ({} with --room-small-parts off)."""
    if room_small_parts() == 'off':
        return {}
    out = {}
    for mi, model in enumerate(index['models']):
        limit = ROOM_MAP_SMALL_PARTS.get(model['source'])
        if limit is None or mi not in models:
            continue
        # the prepared polygons are in map units already (prepare_mesh_bsp._prepare_model: the hammock's box is
        # 74.7 x 25.6 x 19.4, its size in the map)
        models[mi], out[model['source']] = box_small_parts(models[mi], limit, 1.0)
    return out
