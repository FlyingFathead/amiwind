# SPDX-License-Identifier: GPL-3.0-only
"""Drawn faces at every collision piece of a converted model (PRISON-SHIP-FLOOR-STUCK-67).

A model's visual reduction changes only what is drawn: its collision comes from the source (the authored
RootCollisionNode, or the source mesh). When the reduction takes a shape away and its collision stays, the player
walks into something he cannot see. Origin: the prison ship's hold, v0.0.67-dev1: the shell's mast ('Tri mast', a
five-sided column of 30 faces) was reduced to 4 faces by the hold's visual profile while its collision column stayed,
so only the tile at its foot showed and the player stopped at an invisible post.

The check, for one prepared model record (prepare_mesh_bsp._prepare_model: v, f, polys, pieces, lod): every
collision piece's surface is sampled every SPACING map units, and each sample is looked up against the drawn
surface, sampled the same way, within TOLERANCE map units:
- in the source mesh as the original draws it (the record's v, f; SOURCE_SCALE from source to map units), and
- in the converted polygons (the record's polys, as the map draws them).
A piece of at least MIN_SIZE map units whose surface the source draws (SOURCE_SHARE or more of its samples) and the
converted polygons draw much less (under KEPT_SHARE of the share the source draws) is LOST: an invisible piece made by
the conversion. Collision the original does not draw either (authored invisible blockers) is not a finding. A lost
piece taller than the engine's step height (player_hull.STEP_HEIGHT) is STANDING: the player cannot step over it,
an invisible post or wall. The hold's stage (tools/prepare_interior.py) refuses a standing lost piece and reports the
low ones.

Measured on the v0.0.67-dev2 hold (docs/SHIP_INTERIOR.md "Drawn where it collides"): of the shell's 1,205 collision
pieces, 1,000 are drawn by the source; 62 were lost, 40 of them standing (the two masts' 8 among them); with the
listed shapes drawn (tools/room_map_shapes.py) 1 is lost, under a step. Standard numpy and scipy only.
"""
import numpy as np

from player_hull import STEP_HEIGHT

SOURCE_SCALE = .25    # source (game) units to map units, as prepare_mesh_bsp's pieces and polygons are
SPACING = 1.0         # map units between the samples on a surface
TOLERANCE = 2.0       # map units within which a drawn sample counts a collision sample as drawn
MIN_SIZE = 2.0        # map units: a piece whose box is smaller on its longest side is not looked at
SOURCE_SHARE = .5     # share of a piece's samples the source must draw for the piece to count as drawn
KEPT_SHARE = .5       # share of the source's drawn share the converted polygons must keep
MAX_SAMPLES = 4096    # the most samples one triangle gives (needle triangles)


def sample_triangles(tris, spacing=SPACING, max_samples=MAX_SAMPLES):
    """Points on the triangles tris (n x 3 x 3) every SPACING units along the two edges at the corner opposite the
    longest edge, corners and centre included: (points, owner index of each point)."""
    tris = np.asarray(tris, float).reshape(-1, 3, 3)
    pts, owner = [], []
    for k, t in enumerate(tris):
        edges = [np.linalg.norm(t[(i + 1) % 3] - t[i]) for i in range(3)]
        far = int(np.argmax(edges))          # the edge from corner far to corner far+1 is the longest
        a = t[(far + 2) % 3]
        e1, e2 = t[far] - a, t[(far + 1) % 3] - a
        n1 = max(1, int(np.ceil(np.linalg.norm(e1) / spacing)))
        n2 = max(1, int(np.ceil(np.linalg.norm(e2) / spacing)))
        while (n1 + 1) * (n2 + 1) // 2 > max_samples:
            n1, n2 = max(1, n1 // 2), max(1, n2 // 2)
        i, j = np.meshgrid(np.arange(n1 + 1) / n1, np.arange(n2 + 1) / n2, indexing='ij')
        keep = (i + j) <= 1 + 1e-9
        p = a + i[keep][:, None] * e1 + j[keep][:, None] * e2
        p = np.vstack((p, t.mean(axis=0)))
        pts.append(p)
        owner.append(np.full(len(p), k))
    if not pts:
        return np.zeros((0, 3)), np.zeros(0, int)
    return np.concatenate(pts), np.concatenate(owner)


def polygon_triangles(points):
    """A convex polygon's corners as a fan of triangles."""
    p = np.asarray(points, float)
    return [np.array([p[0], p[i], p[i + 1]]) for i in range(1, len(p) - 1)]


def piece_triangles(points):
    """The surface of a convex collision piece (its points) as triangles; a flat piece as the fan of its outline."""
    from scipy.spatial import ConvexHull, QhullError
    p = np.unique(np.round(np.asarray(points, float), 6), axis=0)
    if len(p) < 3:
        return np.zeros((0, 3, 3))
    try:
        return p[ConvexHull(p).simplices]
    except (QhullError, ValueError):
        # a flat piece: its hull in its own plane
        c = p.mean(axis=0)
        _, _, axes = np.linalg.svd(p - c)
        flat = (p - c) @ axes[:2].T
        try:
            order = ConvexHull(flat).vertices
        except (QhullError, ValueError):
            return np.zeros((0, 3, 3))
        return np.array(polygon_triangles(p[order]))


def _drawn_tree(points):
    from scipy.spatial import cKDTree
    return cKDTree(points) if len(points) else None


def _drawn_share(tree, samples, tolerance):
    if tree is None or not len(samples):
        return np.zeros(len(samples), bool)
    distance, _ = tree.query(samples, distance_upper_bound=tolerance)
    return np.isfinite(distance)


def lost_pieces(record, materials=None, spacing=SPACING, tolerance=TOLERANCE, min_size=MIN_SIZE,
                source_share=SOURCE_SHARE, kept_share=KEPT_SHARE, source_scale=SOURCE_SCALE, step=STEP_HEIGHT):
    """The collision pieces of one prepared model record that the source draws and the converted polygons do not.

    record: (v, f, polys, pieces, lod) as prepare_mesh_bsp._prepare_model returns it. materials: the model's
    material list (scenery index), for the names of the source shapes drawn at a lost piece. Returns a receipt:
    {'pieces', 'looked_at', 'source_drawn', 'standing', 'lost': [{'piece', 'low', 'high', 'standing',
    'source_share', 'drawn_share', 'shapes'}...]} with boxes in model-local map units; standing = taller than
    STEP."""
    v, f, polys, pieces, lod = record
    receipt = {'pieces': len(pieces or ()), 'looked_at': 0, 'source_drawn': 0, 'standing': 0, 'lost': [],
               'rule': 'drawn_collision: a collision piece the source draws keeps drawn faces',
               'tolerance_units': tolerance, 'spacing_units': spacing, 'step_units': step}
    if not pieces or (lod or {}).get('representation') == 'collision_only':
        return receipt
    v = np.asarray(v, float)
    f = np.asarray(f)
    source_tris = v[f[:, :3], :3] * source_scale
    source_points, source_owner = sample_triangles(source_tris, spacing)
    drawn_tris = [t for poly in polys for t in polygon_triangles(poly[0])]
    drawn_points, _ = sample_triangles(np.array(drawn_tris) if drawn_tris else np.zeros((0, 3, 3)), spacing)
    source_tree, drawn_tree = _drawn_tree(source_points), _drawn_tree(drawn_points)
    face_material = f[:, 3] if f.shape[1] > 3 else np.zeros(len(f), int)
    for k, piece in enumerate(pieces):
        points = np.asarray(piece[0], float)
        low, high = points.min(axis=0), points.max(axis=0)
        if float((high - low).max()) < min_size:
            continue
        samples, _ = sample_triangles(piece_triangles(points), spacing)
        if not len(samples):
            continue
        receipt['looked_at'] += 1
        in_source = _drawn_share(source_tree, samples, tolerance)
        share_source = float(in_source.mean())
        if share_source < source_share:
            continue
        receipt['source_drawn'] += 1
        share_drawn = float(_drawn_share(drawn_tree, samples, tolerance).mean())
        if share_drawn >= kept_share * share_source:
            continue
        shapes = {}
        if materials is not None and source_tree is not None:
            _, nearest = source_tree.query(samples[in_source])
            for mat in face_material[source_owner[nearest]]:
                name = materials[int(mat)].get('source_shape', '?') if int(mat) < len(materials) else '?'
                shapes[name] = shapes.get(name, 0) + 1
        standing = bool(high[2] - low[2] > step)
        receipt['standing'] += standing
        receipt['lost'].append({'piece': k, 'low': low.round(2).tolist(), 'high': high.round(2).tolist(),
                                'standing': standing,
                                'source_share': round(share_source, 3), 'drawn_share': round(share_drawn, 3),
                                'shapes': dict(sorted(shapes.items(), key=lambda kv: -kv[1])[:4])})
    return receipt


def check_room(models, index, scale=SOURCE_SCALE):
    """The check over every prepared model of a room map (room_map_collision.prepare_room_models: {model index:
    record} of the scenery index INDEX): (receipt, message). The receipt counts the pieces over all models and keeps
    lost_pieces' receipt of every model with a lost piece ('by_model'); the message holds lost_message's lines of the
    models with a standing lost piece, boxes in map units at the model's first placement ('' when there is none)."""
    first = {}
    for ref in index.get('references', ()):
        first.setdefault(ref.get('model_index'), ref)
    total = {'models': 0, 'pieces': 0, 'looked_at': 0, 'source_drawn': 0, 'lost': 0, 'standing': 0, 'by_model': {}}
    lines = []
    for mi in sorted(models):
        model = index['models'][mi]
        receipt = lost_pieces(models[mi], model.get('materials'))
        total['models'] += 1
        for key in ('pieces', 'looked_at', 'source_drawn', 'standing'):
            total[key] += receipt[key]
        total['lost'] += len(receipt['lost'])
        if receipt['lost']:
            total['by_model'][model['source']] = receipt
        if receipt['standing']:
            offset = np.asarray(first.get(mi, {}).get('position', (0, 0, 0)), float) * scale
            lines.append(lost_message(model['source'], receipt, offset))
    return total, '\n'.join(lines)


def lost_message(model, receipt, offset=(0, 0, 0), standing_only=False):
    """One line per lost piece of a model (only the standing ones with STANDING_ONLY), its box in map units plus
    OFFSET (the model's place in the map) and the source shapes drawn there."""
    off = np.asarray(offset, float)
    rows = [row for row in receipt['lost'] if row['standing'] or not standing_only]
    lines = ['%s: %d of the %d collision pieces the original draws have no drawn faces at their place, %d of them '
             'standing (an invisible post or wall; draw their shapes as the original does, room_map_shapes):'
             % (model, len(receipt['lost']), receipt['source_drawn'], receipt['standing'])]
    for row in rows:
        lines.append('  %s piece %d at %s .. %s: source draws %.0f %%, the map %.0f %%; shapes %s' % (
            'standing' if row['standing'] else 'low', row['piece'], (np.asarray(row['low']) + off).round(1).tolist(),
            (np.asarray(row['high']) + off).round(1).tolist(), 100 * row['source_share'], 100 * row['drawn_share'],
            ', '.join(row['shapes']) or '?'))
    return '\n'.join(lines)
