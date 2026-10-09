# SPDX-License-Identifier: GPL-3.0-only
"""Shared models and textures of the CHIM world: one brush image per variant.

The geometry comes from the legacy converter's own functions
(prepare_mesh_bsp._prepare_model and _prepare_placement: the same faces,
texture mappings and collision pieces a region map gets). This module only
writes them into a standalone brush image instead of appending them to a
region map. Its record rules (texture pixels, plane/texinfo/vertex/edge
records, the convex-piece hull chain) are the ones of
prepare_mesh_bsp._append_meshes, whose closures cannot be called from outside;
tests/test_chim_format.py compares both writers on the same model so they
cannot drift apart.

Model frame: a variant is stored with scale and tilt baked in and yaw left
for run time, exactly like a region map's func_wall submodel (entity origin
and "angles 0 yaw 0").
"""
import math
import struct
from types import SimpleNamespace

import numpy as np

from chim.format import texture_refs

SOLID_LEAF = struct.pack('<2i6h2H4B', -2, -1, *[0] * 6, 0, 0, 0, 0, 0, 0)
EMPTY_LEAF = struct.pack('<2i6h2H4B', -1, -1, *[0] * 6, 0, 0, 0, 0, 0, 0)
EMPTY_LEAF_INDEX = 1
# routed standing hull: pieces chained per part, and the piece count above which a placed model is
# routed instead of one chain (CHIM-HULL-CHAIN-COST-33); one implementation in tools/routed_hull.py
from routed_hull import HULL_LEAF_PIECES, CHIM_ROUTE_PIECES as MODEL_ROUTE_PIECES  # noqa: E402


# ---------------------------------------------------------------- textures

def material_texture_key(model, material, size, no_emissive):
    """prepare_mesh_bsp texture() identity: (texture, size, tint, glow) or the flattened panel."""
    if material == len(model['materials']):
        return ('flatten', model['source'], size)
    mat = model['materials'][material]
    glow = 0 if no_emissive else int(mat.get('emissive', 0))
    return (mat['texture_index'], size, tuple(round(x, 2) for x in mat['diffuse']), glow)


def material_texture_image(archive, index, model, material, size, palette_image, flat_rgb=None):
    """Quantized texture image: the converter's own function (prepare_mesh_bsp.material_image)."""
    from prepare_mesh_bsp import material_image
    return material_image(archive, index, model, material, size, palette_image, flat_rgb)


def engine_texture_name(kind, glow, texture_id):
    """Miptex name the engine sees: emitN_ (self-lit, r_surf.c R_EmissiveLevel), flatN, surfaceN."""
    if kind == 'flatten':
        return 'flat%d' % texture_id
    return ('emit%d_%d' % (glow, texture_id)) if glow else 'surface%d' % texture_id


# ---------------------------------------------------------------- lump writer

class BrushLumps:
    """Fresh BSP29 lumps for one brush image, with the converter's record rules."""

    def __init__(self):
        self.lumps = [bytearray() for _ in range(15)]
        self.lumps[10] += SOLID_LEAF + EMPTY_LEAF
        # Edge 0 is never used: a surfedge -0 could not name its reverse (qbsp reserves it too).
        self.lumps[12] += struct.pack('<HH', 0, 0)
        self.planes = {}
        self.texinfo = {}
        self.textures = []          # local index -> global texture id
        self.face_planes = []

    def plane(self, n, d):
        key = tuple(np.round([*n, d], 5))
        if key not in self.planes:
            self.planes[key] = len(self.lumps[1]) // 20
            self.lumps[1] += struct.pack('<4fi', *n, d, 3)
        return self.planes[key]

    def local_texture(self, global_id):
        if global_id not in self.textures:
            self.textures.append(global_id)
        return self.textures.index(global_id)

    def texinfo_index(self, ax, off, t, flags=0):
        key = (*np.round(ax.flatten(), 5), *np.round(off, 4), t, flags)
        if key not in self.texinfo:
            tx = len(self.lumps[6]) // 40
            if tx > 65535:
                raise ValueError('Texture mapping budget exceeded: %d mappings, limit 65,536' % (tx + 1))
            self.texinfo[key] = tx
            self.lumps[6] += struct.pack('<8fii', *ax[:, 0], off[0], *ax[:, 1], off[1], t, flags)
        return self.texinfo[key]

    def faces(self, surfaces, texture_of, flags_of=lambda s: 0, light_of=lambda s: None, plane_of=None):
        """Append faces; surfaces: (q, n, ax, off, material, ...) with q counter-clockwise about n.

        Vertices are shared within this call (rounded to 1e-5), as within one
        placement of a region map; faces store them clockwise (q reversed).
        Returns (firstface, numfaces)."""
        lumps = self.lumps
        first = len(lumps[7]) // 20
        vmap, emap = {}, {}

        def vertex(p):
            key = tuple(np.round(p, 5))
            if key not in vmap:
                vmap[key] = len(lumps[3]) // 12
                lumps[3] += struct.pack('<3f', *p)
            if vmap[key] >= 65536:
                raise ValueError('Vertex budget exceeded')
            return vmap[key]
        for s in surfaces:
            q, n, ax, off, material = s[:5]
            pi, side = self.plane(n, float(n @ q[0])), 0
            if plane_of is not None:
                # World faces lie on their node's plane; a face seen from the
                # plane's back side says so (qbsp: face side, SURF_PLANEBACK).
                pi, side = plane_of(s)
            t = self.local_texture(texture_of(material))
            tx = self.texinfo_index(ax, off, t, flags_of(s))
            verts = [vertex(p) for p in q[::-1]]
            firstedge = len(lumps[13]) // 4
            for a, c in zip(verts, verts[1:] + verts[:1]):
                if (a, c) in emap:
                    ed = emap[a, c]
                elif (c, a) in emap:
                    ed = -emap[c, a]
                else:
                    ed = len(lumps[12]) // 4
                    emap[a, c] = ed
                    lumps[12] += struct.pack('<HH', a, c)
                lumps[13] += struct.pack('<i', ed)
            light = light_of(s)
            styles, lightoffset = ((255, 255, 255, 255), -1) if light is None else ((0, 255, 255, 255), light)
            self.face_planes.append(pi)
            lumps[7] += struct.pack('<HhihH4Bi', 0, side, firstedge, len(verts), tx, *styles, lightoffset)
        return first, len(lumps[7]) // 20 - first

    def collider(self, pieces, exact=False, compiled=None, point_hull=True, standing=True):
        """Convex-piece union as chained clipnodes (standing hull) and nodes (point hull).

        prepare_mesh_bsp collider(): each piece is a run of planes, outside
        any plane goes on to the next piece, inside all is solid. compiled:
        the exact union from collision_bsp.compile_standing, used for the
        standing hull instead of the chain. Returns (point root, hull root)."""
        from prepare_mesh_bsp import standing_planes
        lumps = self.lumps
        if not pieces:
            return -EMPTY_LEAF_INDEX - 1, -1
        roots, noderoots = [], []
        for k, (points, hull, ids, error) in enumerate(pieces):
            point_eq = np.unique(np.round(hull.equations, 5), axis=0)
            # exact: True / False for every piece, or the set of piece positions with exact bevels
            piece_exact = exact if isinstance(exact, bool) else k in exact
            eq = standing_planes(points, point_eq, piece_exact) if compiled is None and standing else []
            root = len(lumps[9]) // 8
            noderoot = len(lumps[5]) // 24
            roots.append(root)
            noderoots.append(noderoot)
            count = len(eq)
            nxt = root + count if k + 1 < len(pieces) else -1
            low = np.floor(points.min(axis=0)).astype(int)
            high = np.ceil(points.max(axis=0)).astype(int)
            for j, e in enumerate(eq):
                pi = self.plane(e[:3], -e[3])
                inside = root + j + 1 if j + 1 < count else -2
                if max(nxt, inside) >= 65520:
                    raise ValueError('Clipnode budget exceeded')
                lumps[9] += struct.pack('<iHH', pi, nxt & 65535, inside & 65535)
            if not point_hull:
                continue
            nnxt = noderoot + len(point_eq) if k + 1 < len(pieces) else -EMPTY_LEAF_INDEX - 1
            for j, e in enumerate(point_eq):
                pn = self.plane(e[:3], -e[3])
                nin = noderoot + j + 1 if j + 1 < len(point_eq) else -1
                if max(nnxt, nin) > 32767:
                    raise ValueError('Point node budget exceeded')
                lumps[5] += struct.pack('<ihh6h2H', pn, nnxt, nin, *low, *high, 0, 0)
        if not standing:
            return noderoots[0], None
        if compiled is not None:
            nodes, croot = compiled
            start = len(lumps[9]) // 8
            if start + len(nodes) >= 65520:
                raise ValueError('Compiled collision node budget exceeded')
            for equation, front, back in nodes:
                pi = self.plane(equation[:3], equation[3])
                children = [start + c if c >= 0 else c & 65535 for c in (front, back)]
                lumps[9] += struct.pack('<iHH', pi, *children)
            return noderoots[0], start + croot if croot >= 0 else croot
        return noderoots[0], roots[0]

    def routed_hull(self, pieces, region, leaf_pieces=None, exact=True):
        """Standing hull of convex pieces with axial routing: returns the hull root (clipnode or contents).

        Each piece is expanded by the standing player box (prepare_mesh_bsp.standing_planes);
        axial clipnodes at the expanded pieces' xy edges split `region` (x0, y0, x1, y1) until
        a part meets at most `leaf_pieces` pieces or no split helps; each part then holds the
        chain of the pieces that reach it (outside every piece: empty, inside one: solid). The
        result classifies every point like the chain of all pieces, with short chains.
        Default HULL_LEAF_PIECES (8): Balmora's ground, measured (exact pieces): about as few
        clipnode visits per point test as format 0.3's own-tile chain (19.9 vs 19.5 mean, p95 30
        vs 38) at 5.1 KB of clipnodes per chunk; at most 2 per leaf costs 9.3 KB for 15.2 visits.
        Pieces are expanded exactly (the Minkowski sum with the box, edge bevels included, as
        Quake's ExpandBrush): without bevels a box rests above convex ridges
        (CHIM-TERRAIN-HULL-BEVELS-33: up to 8 units on Balmora's slopes)."""
        from routed_hull import expand, route
        eqs, boxes = expand(pieces, exact)
        self.hull_chains = []
        return route(self.lumps[9], self.plane, eqs, boxes, region,
                     HULL_LEAF_PIECES if leaf_pieces is None else leaf_pieces, self.hull_chains)

    def finish(self, lo, hi, nroot, croot, firstface, numfaces, entities=b'', lighting=b''):
        """dmodel, texture references, plane order (face planes first), surface check."""
        from prepare_mesh_bsp import order_face_planes
        from surface_grid import check_lumps
        lumps = self.lumps
        lumps[14] = bytearray(struct.pack('<9f7i', *lo, *hi, 0, 0, 0, nroot, croot, croot, croot, 0,
                                          firstface, numfaces))
        # Texture references: global ids when known; the assembly resolves texture keys later.
        known = all(isinstance(t, int) for t in self.textures)
        lumps[2] = bytearray(texture_refs(self.textures)) if known else bytearray()
        lumps[0] = bytearray(entities)
        lumps[8] = bytearray(lighting)
        order_face_planes(lumps, self.face_planes)
        check_lumps(lumps, 0)
        return lumps


def hull_pieces(parts):
    """Collision pieces with convex hulls (as _prepare_placement returns them)."""
    from scipy.spatial import ConvexHull
    return [(points, hull if hull is not None else SimpleNamespace(equations=ConvexHull(points).equations), ids, err)
            for points, hull, ids, err in parts]


def model_image_lumps(surfaces, parts, lo, hi, texture_of, exact=False, compiled=None, entities=b'',
                      hull=None):
    """Lumps of one shared model (faces, collision chain, dmodel) and its texture list.

    texture_of(material) gives a global texture id or a texture key; the
    returned list holds them in local texture order. hull: the standing hull's form when it is not
    compiled, a routed_hull mode (default: the build's, mesh_geometry_env.model_hull_mode): 'chain'
    (every piece in one chain, as the converters wrote it before), 'routed' / 'balanced' (axial routing
    over the model's box, routed_hull.routing: the same solid set, short chains) or 'auto' (routed for
    more than MODEL_ROUTE_PIECES pieces; the chain when the routing exceeds the clipnode budget). The
    variant unit compiles a large model's hull with qbsp when it can (variant_unit)."""
    w = BrushLumps()
    first, num = w.faces(surfaces, texture_of)
    pieces = hull_pieces(parts)
    from routed_hull import CHIM_ROUTE_PIECES, wants_route
    if hull is None:
        from mesh_geometry_env import model_hull_mode
        hull = model_hull_mode()
    if wants_route(len(pieces), hull, compiled is not None, CHIM_ROUTE_PIECES):
        try:
            return _routed_model(w, surfaces, pieces, exact, lo, hi, first, num, entities, hull)
        except ValueError as error:
            if 'budget' not in str(error) or hull in ('routed', 'balanced'):
                raise
            # too many parts for the routing: the chain, as the legacy converter writes it
            w = BrushLumps()
            first, num = w.faces(surfaces, texture_of)
            nroot, croot = w.collider(pieces, exact, compiled)
    else:
        nroot, croot = w.collider(pieces, exact, compiled)
    return w.finish(lo, hi, nroot, croot, first, num, entities), list(w.textures)


def _routed_model(w, surfaces, pieces, exact, lo, hi, first, num, entities, mode='auto'):
    """The routed standing hull over the model's box (point hull still the chain of pieces), by the
    mode's routing (routed_hull.routing, routed_standing)."""
    from routed_hull import routed_standing, routing
    nroot, _ = w.collider(pieces, exact, None, standing=False)
    # no copies unless asked for ('routed'): a CHIM model's bytes are in every ring that holds it, so by
    # default its hull takes no more than the chain plus one clipnode per cut (BUILD-CHIM-HULL-RING-33)
    croot, _, w.hull_chains = routed_standing(w.lumps, w.plane, w.planes, pieces, bool(exact),
                                              **routing(mode, shared_budget=mode != 'routed'))
    return w.finish(lo, hi, nroot, croot, first, num, entities), list(w.textures)


def variant_unit(task):
    """One shared model variant from its prepared mesh (a pool worker; see chim.units).

    task: ref, data (prepare_mesh_bsp._prepare_model result), texsize, centre,
    model (scenery index record), exact, hollow, qbsp, collision_cache."""
    from prepare_mesh_bsp import NO_EMISSIVE, _prepare_placement, flame_entities
    ref, model, centre, size = task['ref'], task['model'], task['centre'], task['texsize']
    surfaces, parts, lo, hi = _prepare_placement((ref, task['data'], size, centre, None, False))
    keys = {}
    for s in surfaces:
        keys[s[4]] = ('model',) + material_texture_key(model, s[4], size, NO_EMISSIVE)
    compiled = None
    fallback = None
    # A large model's standing hull is routed (model_image_lumps), not compiled by qbsp: a compiled union
    # takes more bytes than the chain, and every byte is in the ring (Balmora's south-west ring went
    # 136,160 B over the zone; BUILD-CHIM-HULL-RING-33). Mode 'compiled' keeps the qbsp union for large
    # models selectable; exact models are compiled as before.
    from mesh_geometry_env import model_hull_mode
    from routed_hull import CHIM_ROUTE_PIECES
    big = len(parts) > CHIM_ROUTE_PIECES and task.get('model_hull', model_hull_mode()) == 'compiled'
    if (task['exact'] or big) and task.get('qbsp') and parts:
        from collision_bsp import compile_standing
        try:
            compiled = compile_standing(hull_pieces(parts), task['qbsp'], task['collision_cache'])
        except ValueError as error:
            fallback = str(error)[-200:]
    local = dict(ref, position=[*centre, 0.0])
    flames = variant_flames(flame_entities(local, model, centre), local, centre)
    lumps, tkeys = model_image_lumps(surfaces, parts, lo, hi, lambda m: keys[m], task['exact'], compiled, flames)
    occluder_grid = None
    if task['hollow']:
        # hollow collision shells do not occlude; the closed render mesh does (CHIM-PVS-HOLLOW-33)
        from chim.occluders import solid_columns
        occluder_grid = solid_columns([s[0] for s in surfaces])
    return {'lumps': [bytes(x) for x in lumps], 'texture_keys': tkeys, 'lo': [float(v) for v in lo],
            'hi': [float(v) for v in hi], 'occluders': [] if task['hollow'] else [p for p, *_ in parts],
            'occluder_grid': occluder_grid,
            'materials': {k: m for m, k in keys.items()}, 'collision_fallback': fallback}


def texture_unit(task):
    """One shared texture as a miptex with a placeholder name (a pool worker).

    task: archive (scenery archive path or None), textures (scenery index
    texture records), model, material, size, palette (bytes), flat_rgb, kind, glow."""
    from PIL import Image
    from prepare_quake import miptex
    pal = Image.new('P', (1, 1))
    pal.putpalette(task['palette'])
    archive = open(task['archive'], 'rb') if task.get('archive') else None
    try:
        im = material_texture_image(archive, {'textures': task['textures']}, task['model'], task['material'],
                                    task['size'], pal, task.get('flat_rgb'))
    finally:
        if archive:
            archive.close()
    return {'miptex': miptex(engine_texture_name(task['kind'], task['glow'], 0), im), 'size': list(im.size),
            'kind': task['kind'], 'glow': task['glow']}


def variant_flames(flame_text, ref, centre):
    """aw_flame emitters of a placement moved into the variant (model) frame.

    flame_text: prepare_mesh_bsp.flame_entities of the placement; the model
    frame is _placement_frame's: origin at the placement, yaw removed."""
    import re
    from prepare_mesh_bsp import _placement_frame
    origin, rotation = _placement_frame(ref, centre)
    out = []
    for text in flame_text:
        m = re.search(r'"origin" "([^"]+)"', text)
        p = np.array([float(v) for v in m.group(1).split()])
        local = rotation.T @ (p - origin)
        out.append(text.replace(m.group(0), '"origin" "%.2f %.2f %.2f"' % tuple(local)))
    return ('\n'.join(out) + '\n\0').encode('ascii') if out else b''


def yaw_degrees(ref):
    """The entity yaw of a placement (prepare_mesh_bsp: -rotation z in degrees)."""
    return -ref['rotation_radians'][2] * 180 / math.pi
