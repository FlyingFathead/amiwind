#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The outer-hull check of a reduced actor model against its original (MESH-SEAM-METHOD-62, MESH-REDUCTION-SEAMS-62,
ACTOR-PACK-GUAR-MESH-BROKEN-64, NPC-JOINT-GAPS-33, CREATURE-MESH-HOLES-62).

The rule, decided for the project on 20 November 2026: a reduced model keeps the ORIGINAL'S OUTER MEASURES. Its outer
hull has no gap, and its outer dimensions (the extent of the body, the girth of the arms, legs and other parts, the
surface it covers) stay those of the original. The verdict is these numbers, measured in the pose the bake draws, never
a picture (docs/MODEL_REDUCTION.md section 7):

- extent: per axis, the reduced model's box against the source's (1.0 = the same). Under EXTENT_KEEP on any axis or
  over 1/EXTENT_KEEP = a part pulled in, cut off or thrown out.
- girth: per part (an NPC body's arms, legs, neck and tail by the bone of its table that moves them; a creature's
  shapes; each connected piece of GIRTH_MIN_FACES or more faces and GIRTH_MIN_SHARE of the model's size on its own),
  the narrowest of the cuts at 25, 50 and 75 % of the part's length: the reduced surface near the part's own source
  surface against the source cut (girth_of; a flat plate's thickness is not a girth). Under GIRTH_KEEP = a limb
  thinned towards a stick.
- lost: a source piece (a claw, an antenna, a hand) the reduced surface no longer reaches (lost_pieces). Any = fails.
- hull: the share of the source's surface within TOL of the reduced model's surface (creature_surface.coverage).
  Under HULL_KEEP = a hole in the hull, a part torn away or a surface scattered.
- open: open edges of the welded reduced whole that lie farther than TOL from every open edge of the welded source
  whole (mesh_seam_check.open_edges: two parts that meet at a seam count as closed). Any = a new gap in the hull.
- seams: every join of the source that is not welded closed (a rim of one part resting on another without sharing its
  points: the neck on the chest, a wrist on a hand), its widest opening on the reduced model and the share of the
  joins' length left open (seam_joins: a point half a unit in from the rim farther than SEAM_TOL from the reduced
  model). Over SEAM_GAP_MAX or SEAM_OPEN_MAX = a head or a limb standing apart from the part it joins.
- tear (a skeletal model only, reported, not judged yet): over the posed frames of its animation table, the widest
  distance between the copies of one point (the vertices that coincide in the bake's rest pose); a finding only
  against the source posed the same way, since parts the original hangs on different bones part in it too.

Usage (in the shell container, the worktree's tools and src on PYTHONPATH):
  outer_hull.py creature --mesh r/guar.nif --model progs/c_..._k.mdl --data-files DIR [--table progs/k_....awsk]
  outer_hull.py library --run BUILD_RUN --data-files DIR [--creatures all|MESH,...] [--npcs ID,...] [--json OUT]
      every creature model of the run's creature library and the named residents' models (the room batches' and
      the NPC library's appearance records), each against its source posed as the bake posed it.
Exit 0 = every model passes, 1 = a model fails (its problems printed), 2 = a model could not be read.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

if __name__ == '__main__':
    # run as a command: src/ ahead of tools/ (tools/mwad.py is the command, src/mwad the package; the script's own
    # folder is sys.path[0] already); imported, the caller's path stands
    for _path in (str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parents[1] / 'src')):
        while _path in sys.path:
            sys.path.remove(_path)
        sys.path.insert(0, _path)

TOL = 1.0               # Quake units: the hull's tolerance (creature_surface.TOLERANCE; an alias step is 0.2 to 0.4)
EXTENT_KEEP = 0.97      # every axis of the box keeps at least this share of the source's (and at most its inverse)
GIRTH_KEEP = 0.8        # every part's narrowest cross-section keeps this share (npc_geometry.GIRTH_KEEP)
HULL_KEEP = 0.97        # this share of the source's surface lies within TOL of the reduced surface
TEAR_MAX = 0.5          # Quake units: copies of one rest point may part this far in a pose (two alias steps)
SEAM_GAP_MAX = 0.5      # Quake units: the widest opening a join of the source may show (npc_geometry.JOINT_MAX_GAP)
SEAM_OPEN_MAX = 0.05    # and at most this share of the joins' length open (npc_geometry.JOINT_OPEN_SHARE)
GIRTH_MIN_FACES = 24    # a creature shape this small is a detail (mesh_seam_check.THICK_MIN_FACES)
LIMITS = {'extent': EXTENT_KEEP, 'girth': GIRTH_KEEP, 'hull': HULL_KEEP, 'open': 0, 'seam_gap': SEAM_GAP_MAX,
          'seam_open': SEAM_OPEN_MAX, 'tear': TEAR_MAX, 'tol': TOL}


def _tris(points, faces):
    return np.asarray(points, float)[np.asarray(faces)[:, :3]]


def source_whole(shapes):
    """(points, faces) of the source shapes' first frame as one list (each shape's vertices after the previous ones)."""
    pts, fcs, off = [], [], 0
    for s in shapes:
        p = np.asarray(s['positions'][0], float)
        pts.append(p)
        fcs.append(np.asarray(s['faces'])[:, :3] + off)
        off += len(p)
    return np.concatenate(pts), np.concatenate(fcs)


def extent_ratios(src_points, src_faces, points, faces):
    """Per axis: the reduced surface's box against the source surface's (only the vertices the faces use)."""
    s = np.asarray(src_points, float)[np.unique(np.asarray(src_faces)[:, :3])]
    r = np.asarray(points, float)[np.unique(np.asarray(faces)[:, :3])] if len(faces) else np.zeros((1, 3))
    return [round(float(b / a), 3) if a > 1e-6 else 1.0 for a, b in zip(np.ptp(s, axis=0), np.ptp(r, axis=0))]


def new_open_edges(src_points, src_faces, points, faces, tol=TOL):
    """Midpoints of the reduced whole's open edges that lie farther than TOL from every open edge of the source
    whole (both welded: mesh_seam_check.open_edges)."""
    import mesh_seam_check as M
    rims = M.open_edges(points, faces)
    if not len(rims):
        return np.zeros((0, 3))
    source = M.open_edges(src_points, src_faces)
    return rims[M._far_from(rims, source, tol)].mean(axis=1)


GIRTH_TOL = 0.5        # Quake units: a reduced cut point this near a part's own source surface traces its outline
FLAT = 0.2              # a cut thinner than this share of its width across is a plate's thickness, not a girth
GIRTH_MIN_SHARE = 0.04  # a piece shorter than this share of the model's size is a detail, not a limb (no girth)
STATIONS = (25, 50, 75) # per cent along a part's long axis (mesh_seam_check.STATIONS)


def girth_of(src_points, src_faces, red_tris, stations=STATIONS, min_length=0.0):
    """The narrowest cross-section ratio of one part (SRC_FACES of the source) against the WHOLE reduced surface
    (RED_TRIS, n x 3 x 3), whatever reduced faces carry it: at 25, 50 and 75 % of the part's length the plane across
    its long axis cuts both; the reduced cut points within max(GIRTH_TOL, a fifth of the part's radius there) of the
    part's own source surface are its reduced outline, and their extent across the part's two narrow axes is compared
    with the source cut's (the smaller of the two ratios). A limb thinned to a stick lies inside its source surface
    and leaves no point near it (0.0); a lost part the same. None: the part is too small to cut, or shorter than
    MIN_LENGTH (a detail: a claw, a finger, an eye; lost_pieces reads whether it is still there)."""
    import mesh_seam_check as M
    from npc_seam_audit import point_triangle_distance
    src_faces = np.asarray(src_faces)[:, :3]
    src_tri = np.asarray(src_points, float)[src_faces]
    samples = M._samples(src_points, src_faces)
    if len(samples) < 8:
        return None
    centre = samples.mean(0)
    _, _, axes = np.linalg.svd(samples - centre, full_matrices=False)
    lo, hi = np.percentile((samples - centre) @ axes[0], [2, 98])
    length = max(hi - lo, 1e-6)
    if length < min_length:
        return None
    ratios = []
    for st in stations:
        at = float(centre @ axes[0] + lo + length * st / 100.0)
        s = M._slice(src_tri, axes[0], at)
        if len(s) < 3:
            continue
        sc = s.mean(0)
        radius = max(float(np.abs((s - sc) @ axis).max()) for axis in axes[1:])
        tol = max(GIRTH_TOL, 0.2 * radius)
        r = M._slice(np.asarray(red_tris, float), axes[0], at) if len(red_tris) else np.zeros((0, 3))
        if len(r):
            r = r[point_triangle_distance(r, src_tri, tol) <= tol]
        if len(r) < 2:
            ratios.append(0.0)
            continue
        # a flat part (a plate, a wing, a pack's cloth) has no girth across its thickness: an axis whose source cut
        # is under FLAT of the other's (or under GIRTH_TOL) is left out
        spans = [float(np.ptp(s @ axis)) for axis in axes[1:]]
        kept = [float(np.ptp(r @ axis)) / span for axis, span in zip(axes[1:], spans)
                if span >= max(GIRTH_TOL, FLAT * max(spans))]
        if kept:
            ratios.append(min(kept))
    return round(min(ratios), 3) if ratios else None


def pieces(points, faces):
    """Lists of face indices, one per connected piece of FACES (vertices welded by position, mesh_seam_check.WELD)."""
    import mesh_seam_check as M
    faces = np.asarray(faces)[:, :3]
    if not len(faces):
        return []
    _, inv = np.unique(np.round(np.asarray(points, float), M.WELD), axis=0, return_inverse=True)
    tri = np.asarray(inv).reshape(-1)[faces]
    parent = list(range(int(tri.max()) + 1))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b, c in tri:
        ra, rb, rc = find(int(a)), find(int(b)), find(int(c))
        parent[rb] = ra
        parent[find(rc)] = ra
    roots = np.array([find(int(t[0])) for t in tri])
    return [np.flatnonzero(roots == r) for r in dict.fromkeys(roots.tolist())]


def girth(src_points, src_faces, points, faces, groups):
    """{part: narrowest cross-section ratio} (girth_of) of every connected piece of GIRTH_MIN_FACES or more faces of
    every group (a shape that carries two legs is two limbs: 'name #2' for the second piece): GROUPS {name: source
    face indices into the source whole (source_whole's faces)}."""
    red = _tris(points, faces) if len(faces) else np.zeros((0, 3, 3))
    src_faces = np.asarray(src_faces)[:, :3]
    used = np.asarray(src_points, float)[np.unique(src_faces)]
    min_length = GIRTH_MIN_SHARE * float(np.ptp(used, axis=0).max()) if len(used) else 0.0
    out = {}
    for name, idx in groups.items():
        idx = np.asarray(idx, int)
        if len(idx) < GIRTH_MIN_FACES:
            continue
        parts = [idx[p] for p in pieces(src_points, src_faces[idx]) if len(p) >= GIRTH_MIN_FACES]
        for k, part in enumerate(sorted(parts, key=len, reverse=True)):
            g = girth_of(src_points, src_faces[part], red, min_length=min_length)
            if g is not None:
                out[str(name) if k == 0 else '%s #%d' % (name, k + 1)] = g
    return out


LOST_MIN_FACES = 8      # a source piece this large that the reduced surface no longer reaches is a lost part
LOST_COVER = 0.1        # ... under this share of its surface within TOL of the reduced surface


def lost_pieces(shapes, src_points, src_faces, points, faces):
    """['shape #k'] of the source's connected pieces (LOST_MIN_FACES or more faces) of which the reduced surface
    covers under LOST_COVER within TOL: a claw, an antenna, an ear, a hand gone from the model."""
    from creature_surface import coverage
    out = []
    for name, idx in shape_faces(shapes).items():
        idx = np.asarray(idx, int)
        for k, p in enumerate(sorted(pieces(src_points, np.asarray(src_faces)[idx]), key=len, reverse=True)):
            if len(p) < LOST_MIN_FACES:
                continue
            if coverage(_tris(src_points, np.asarray(src_faces)[idx[p]]), points, faces, TOL) < LOST_COVER:
                out.append(str(name) if k == 0 else '%s #%d' % (name, k + 1))
    return out


def _face_label(labels, faces):
    """Each face's label: the one at least two of its corners share, else its first corner's."""
    f = np.asarray(faces)[:, :3]
    a, b, c = labels[f[:, 0]], labels[f[:, 1]], labels[f[:, 2]]
    return np.where((b == c) & (a != b), b, a)


def shape_faces(shapes, names=None):
    """{group: source face indices into the source whole}: each shape (or NAMES {group: [shape indices]})."""
    off = np.cumsum([0] + [len(s['faces']) for s in shapes])
    if names is None:
        names = {s.get('name', '') or str(i): [i] for i, s in enumerate(shapes)}
    return {k: np.concatenate([np.arange(off[i], off[i + 1]) for i in v]) if v else np.zeros(0, int)
            for k, v in names.items()}


def bone_faces(shapes):
    """{bone: source face indices into the source whole}: the faces each bone carries (the label at least two of
    their corners share: the arms, legs, neck and tail as the engine moves them, whichever worn piece covers them).
    Shapes without 'bone_name' (NpcSource.shapes sets it): {}."""
    if not shapes or not all('bone_name' in s for s in shapes):
        return {}
    _, sf = source_whole(shapes)
    labels = _face_label(np.concatenate([np.asarray(s['bone_name'], dtype=object) for s in shapes]), sf)
    return {str(b): np.flatnonzero(labels == b) for b in sorted(set(labels.tolist())) if b}


SEAM_TOL = 0.25         # Quake units: a join's inset point this far from the reduced model is open (npc_seam_audit.TOL)


def seam_joins(shapes, src_points, src_faces, red_tris, tol=SEAM_TOL):
    """(widest opening, open share, 'part / part' of the widest) over the joins of the source that are NOT welded
    closed (a rim of one part lying on another part without sharing its points: an NPC's neck on its chest, a wrist
    on a hand; npc_seam_audit.joint_edges, rims still open in the welded source whole). A welded seam cannot open
    without a new open edge (counted by 'open'), so it is left to that measure."""
    import mesh_seam_check as M
    import npc_seam_audit as A
    src = [{'name': s.get('name', ''), 'points': np.asarray(s['positions'][0], float),
            'faces': np.asarray(s['faces'])[:, :3]} for s in shapes]
    whole_rims = M.open_edges(src_points, src_faces)
    total = opened = worst = 0.0
    where = ''
    for (a, b), (edges, inset) in sorted(A.joint_edges(src).items()):
        keep = ~M._far_from(edges, whole_rims, 1e-3) if len(whole_rims) else np.zeros(len(edges), bool)
        if not keep.any():
            continue
        e, p = edges[keep], inset[keep]
        length = np.linalg.norm(e[:, 1] - e[:, 0], axis=1)
        d = A.point_triangle_distance(p, red_tris, tol) if len(red_tris) else np.full(len(p), 1e3)
        total += float(length.sum())
        opened += float(length[d > tol].sum())
        gap = float(np.where(d > tol, np.minimum(d, 1e3), 0).max())
        if gap > worst:
            worst, where = gap, '%s / %s' % (src[a]['name'], src[b]['name'])
    return round(worst, 3), round(opened / total, 3) if total else 0.0, where


def creature_groups(shapes):
    """A creature's parts: each shape on its own (its limbs, plates and body), as source face indices."""
    return shape_faces(shapes)


def _src_first():
    """src/ ahead of tools/ on sys.path before importing a module that imports the mwad package (tools/mwad.py is the
    command, src/mwad the package): npc_seam_audit puts tools/ first when it is imported."""
    src = str(Path(__file__).resolve().parents[1] / 'src')
    if 'mwad' not in sys.modules:
        while src in sys.path:
            sys.path.remove(src)
        sys.path.insert(0, src)


def body_groups(shapes):
    """An NPC body's parts: the faces each bone of its table carries (bone_faces), else its limb slots
    (npc_geometry.LIMB_SLOTS, every shape that fills one), as source face indices."""
    by_bone = bone_faces(shapes)
    if by_bone:
        return by_bone
    _src_first()
    from npc_geometry import LIMB_SLOTS
    return shape_faces(shapes, {'slot %d' % slot: [i for i, s in enumerate(shapes) if s['part'] == slot]
                                for slot in sorted({s['part'] for s in shapes} & LIMB_SLOTS)})


TEAR_WELD = 0.05        # Quake units: vertices this close in the idle's first pose are copies of one point


def tear(model_raw, table_raw, every=4, weld=TEAR_WELD):
    """(widest separation in Quake units, the table frame it is at) of the copies of one point over the table's frames
    (every EVERY-th and each group's first and last), posed by the model's own block on the table as the engine poses
    it (skeletal_actor.skin_many, before the byte grid). The copies: vertices within WELD of each other in the idle's
    first frame (the bake's rest pose), so two parts that meet at a seam must still meet in every pose."""
    import skeletal_actor as S
    k = S.read_skeletal(model_raw)
    table = read_any_table(table_raw)
    actor = np.asarray(k['scale'], float) / np.maximum(np.asarray(k['pose_step'], float), 1e-12)
    second = np.where(k['weight'] > 0, k['second'], -1)

    def posed(f):
        return S.skin_many(k['rest'], k['bone'], second, k['weight'] / 255.0, k['rest2'], S.table_world(table, f)) * actor
    idle = table['groups'].get('idle', (0, 0))[0]
    _, group = np.unique(np.rint(posed(idle) / weld).astype(np.int64), axis=0, return_inverse=True)
    group = np.asarray(group).reshape(-1)
    shared = np.flatnonzero(np.bincount(group)[group] > 1)
    if not len(shared):
        return 0.0, 0
    order = shared[np.argsort(group[shared], kind='stable')]
    g = group[order]
    first = np.r_[0, np.flatnonzero(np.diff(g)) + 1]
    lead = np.repeat(order[first], np.diff(np.r_[first, len(order)]))
    worst, at = 0.0, 0
    for f in S.box_frames(table, every):
        p = posed(f)
        d = float(np.linalg.norm(p[order] - p[lead], axis=1).max())
        if d > worst:
            worst, at = d, int(f)
    return round(worst, 3), at


def measure(shapes, points, faces, groups=None):
    """The outer measures of a reduced model (POINTS, FACES: its rest frame, the pose the source SHAPES are in)
    against its source: {'triangles', 'source_triangles', 'vertices', 'extent' [x, y, z], 'girth' {part: ratio},
    'least_girth', 'lost' [pieces], 'hull', 'open' (new open edges), 'open_at' (the first positions), 'seam_gap',
    'seam_open', 'seam_gap_at'}. GROUPS: {part: source face indices} (creature_groups, body_groups; default: every
    shape)."""
    from creature_surface import coverage
    sp, sf = source_whole(shapes)
    points = np.asarray(points, float)
    faces = np.asarray(faces)[:, :3]
    g = girth(sp, sf, points, faces, groups if groups is not None else creature_groups(shapes))
    opened = new_open_edges(sp, sf, points, faces)
    gap, share, where = seam_joins(shapes, sp, sf, _tris(points, faces) if len(faces) else np.zeros((0, 3, 3)))
    return {'triangles': int(len(faces)), 'source_triangles': int(len(sf)), 'vertices': int(len(points)),
            'extent': extent_ratios(sp, sf, points, faces), 'girth': g,
            'least_girth': round(min(g.values()), 3) if g else 1.0,
            'lost': lost_pieces(shapes, sp, sf, points, faces) if len(faces) else ['all'],
            'hull': round(coverage(_tris(sp, sf), points, faces, TOL), 4),
            'open': int(len(opened)), 'open_at': [[round(float(x), 2) for x in p] for p in opened[:8]],
            'seam_gap': gap, 'seam_open': share, 'seam_gap_at': where}


def problems(row, limits=LIMITS):
    """The reasons a model fails the outer-hull check (empty: it keeps the original's outer measures)."""
    out = []
    for axis, r in zip('xyz', row.get('extent', ())):
        if r < limits['extent'] or r > 1.0 / limits['extent']:
            out.append('extent %s %.2f of the source' % (axis, r))
    thin = sorted((v, k) for k, v in row.get('girth', {}).items() if v < limits['girth'])
    if thin:
        out.append('girth under %.2f on %d part(s), least %.2f (%s)' % (limits['girth'], len(thin), thin[0][0],
                                                                        thin[0][1]))
    if row.get('lost'):
        out.append('%d part(s) lost (%s)' % (len(row['lost']), ', '.join(row['lost'][:4])))
    if row.get('hull', 1.0) < limits['hull']:
        out.append('hull %.1f %% of the source surface within %.1f units' % (100 * row['hull'], limits['tol']))
    if row.get('open', 0) > limits['open']:
        out.append('%d new open edge(s) in the hull' % row['open'])
    if row.get('seam_gap', 0.0) > limits['seam_gap'] or row.get('seam_open', 0.0) > limits['seam_open']:
        out.append('a seam open %.2f units (%s), %.0f %% of the seams\' length open' % (
            row.get('seam_gap', 0.0), row.get('seam_gap_at', ''), 100 * row.get('seam_open', 0.0)))
    # the tear is reported, not judged here: parts the source itself hangs on different bones part in motion in the
    # original too, so a tear is a finding only against the source posed the same way (not measured yet)
    return out


def read_model(raw):
    """(rest frame positions in model units, faces) of an alias model (a skeletal model's rest frame)."""
    from creature_surface import read_alias
    pos, faces, _, _ = read_alias(raw)
    return pos, faces


def check_creature(data, mesh, model_raw, table_raw=None, biped=False):
    """The row of one creature model against its source mesh posed at its idle's first time (the bake's rest pose)."""
    from creature_surface import source_shapes
    shapes = source_shapes(data, mesh, biped)
    pos, faces = read_model(model_raw)
    row = measure(shapes, pos, faces, creature_groups(shapes))
    if table_raw is not None:
        row['tear'], row['tear_frame'] = tear(model_raw, table_raw)
    row['problems'] = problems(row)
    return row


class NpcSource:
    """The source of a resident's model: its appearance assembled at the first sample of its skeletal bake's kit
    (skeletal_actor.skeletal_resident: npc_anim.plan on its table's skeleton, the first sample = the rest pose)."""

    def __init__(self, data):
        import npc_anim
        from halloween_cast import _assets
        self.data = str(data)
        self.assets = _assets(Path(data))
        self.profile = npc_anim.plan_profile('react+full')
        self.rigs = {}

    def rig(self, path):
        from npc_geometry import Skeleton
        if path not in self.rigs:
            self.rigs[path] = Skeleton(self.assets, path)
        return self.rigs[path]

    def appearance(self, ident):
        """An NPC record's appearance from the masters, as the builder makes it (tools/hair_check.Context)."""
        import npc_anim
        import npc_items
        from mwad.masters import master_path
        from mwad.npc import load_master, outfit
        if not hasattr(self, 'kinds'):
            self.kinds, _, _ = load_master(master_path(Path(self.data)))
        app = npc_items.attach_items(self.kinds, ident, outfit(self.kinds, ident))
        app['foot'] = npc_anim.foot_class(self.kinds, app)
        return app

    def shapes(self, appearance):
        """(the appearance's shapes in the bake's rest pose, each with 'bone_name': every vertex's bone on the
        table the engine poses it by (export_actor's bone carried onto the stick figure, skeletal_actor.onto_kept),
        the table's bone names)."""
        import npc_anim
        import skeletal_actor as S
        from npc_geometry import assemble
        _, report, _, _, skeleton, over = S.game_table(self.data, appearance, self.rig)
        poser, groups = npc_anim.plan(skeleton, self.profile, over, appearance.get('weight', 1.),
                                      attack_stance=appearance.get('attack_stance'))
        shapes, _, _ = assemble(self.assets, appearance, poser, np.array([0.0]))
        names = list(report['bone_names'])
        sources = S.export_actor(self.assets, appearance, skeleton)
        parents = getattr(skeleton, 'parents', None)
        if parents is not None and len(sources) == len(shapes) and all(
                s['positions'].shape[1] == len(src['rest']) for s, src in zip(shapes, sources)):
            keep = set(names)
            for s, src in zip(shapes, sources):
                kept = [S.kept_ancestor(parents, keep, n) for n in src['bones']]
                s['bone_name'] = np.array([kept[b] or '' for b in np.asarray(src['bone'], int)], dtype=object)
        return shapes, names


def check_npc(source, appearance, model_raw, table_raw=None):
    """The row of one resident's model against its appearance assembled in the bake's rest pose; its girth per bone
    of the table (body_groups)."""
    shapes, _ = source.shapes(appearance)
    pos, faces = read_model(model_raw)
    row = measure(shapes, pos, faces, body_groups(shapes))
    if table_raw is not None:
        row['tear'], row['tear_frame'] = tear(model_raw, table_raw)
    row['problems'] = problems(row)
    return row


def block_table(id1, model_raw):
    """The path of the animation table a skeletal model's block names (its view suffix '|...' left off), under ID1
    or the run's other stage folders; None for a model without a block or a table not found."""
    import skeletal_actor as S
    if not S.is_skeletal(model_raw):
        return None
    name = S.read_skeletal(model_raw)['table'].split(S.TABLE_VIEW)[0]
    for root in [Path(id1)] + sorted(Path(id1).parent.parent.glob('*/id1')):
        if (root / name).is_file():
            return root / name
    return None


def read_any_table(raw):
    """skeletal_actor.read_table of a table in any of its forms (plain, appended to the humanoid table, scaled)."""
    import skeletal_actor as S
    import creature_tables as T
    try:
        return S.read_table(raw)
    except ValueError:
        pass
    for convert in (T.from_scaled, T.from_appended):
        try:
            return S.read_table(convert(raw)[0])     # the scale tracks or the base name aside
        except ValueError:
            continue
    raise ValueError('Not an animation table in any form')


def two_legged(data):
    """{mesh: True when a creature record using it is two-legged} (creature_tables.meshes over the masters)."""
    import creature_tables as T
    return {m: v['biped'] for m, v in T.meshes(T.records(T.read_masters(data))).items()}


def _library_tasks(run, creatures, npcs, biped=None):
    """[(kind, key, payload)] of a build run's models: its creature library's standing models (all or the named
    meshes) and the named residents (room batches first, then the NPC library's appearances)."""
    run = Path(run)
    tasks = []
    lib = run / 'actor-library' / 'creature-library.json'
    biped = biped or {}
    if creatures and lib.is_file():
        manifest = json.loads(lib.read_text(encoding='utf-8'))
        for mesh, rec in sorted(manifest.get('models', {}).items()):
            if '#' in mesh or rec.get('corpse'):
                continue
            if creatures != 'all' and mesh not in creatures:
                continue
            model = run / 'actor-library' / 'id1' / rec['model']
            table = run / 'actor-library' / 'id1' / rec['table'] if rec.get('table') else None
            tasks.append(('creature', mesh, {'model': model, 'table': table, 'method': rec.get('method'),
                                             'biped': biped.get(mesh, False)}))
    for ident in npcs or ():
        found = None
        for path in sorted(run.glob('*/scene/*residents*.json')) + sorted(run.glob('*/*residents*.json')):
            try:
                models = json.loads(path.read_text(encoding='utf-8')).get('models', {})
            except (OSError, ValueError):
                continue
            rec = models.get(ident)
            if rec and rec.get('appearance') and rec.get('model'):
                for id1 in (path.parent.parent / 'id1', path.parent / 'id1'):
                    if (id1 / rec['model']).is_file():
                        found = {'model': id1 / rec['model'], 'appearance': rec['appearance'],
                                 'table': block_table(id1, (id1 / rec['model']).read_bytes()),
                                 'where': str(path.relative_to(run))}
                        break
            if found:
                break
        lib_npc = run / 'actor-library' / 'npc-library.json'
        if found is None and lib_npc.is_file():
            manifest = json.loads(lib_npc.read_text(encoding='utf-8'))
            entry = manifest.get('npcs', {}).get(ident)
            rec = manifest.get('models', {}).get((entry or {}).get('key', ''))
            id1 = run / 'actor-library' / 'id1'
            if rec and (id1 / rec['model']).is_file():
                # the NPC library keeps no appearance: it is made again from the masters (NpcSource.appearance)
                found = {'model': id1 / rec['model'], 'appearance': None, 'ident': ident,
                         'table': block_table(id1, (id1 / rec['model']).read_bytes()),
                         'where': 'actor-library/npc-library.json'}
        tasks.append(('npc', ident, found))
    return tasks


def library(run, data, creatures='all', npcs=(), log=print):
    """{'rows': {key: row}, 'unread': {key: why}, 'failing': [key]} over a build run's models (_library_tasks)."""
    out = {'run': str(run), 'limits': LIMITS, 'rows': {}, 'unread': {}, 'failing': []}
    source = None
    for kind, key, task in _library_tasks(run, creatures, npcs, two_legged(data) if creatures else None):
        try:
            if task is None:
                raise ValueError('no model record with an appearance in the run')
            raw = Path(task['model']).read_bytes()
            table = Path(task['table']).read_bytes() if task.get('table') else None
            if kind == 'creature':
                row = check_creature(data, key, raw, table, task['biped'])
                row['method'] = task.get('method')
            else:
                source = source or NpcSource(data)
                row = check_npc(source, task['appearance'] or source.appearance(task['ident']), raw, table)
                row['where'] = task['where']
            row['model'] = str(Path(task['model']).relative_to(run))
        except Exception as error:  # noqa: BLE001 (a model the check cannot read is listed with its reason)
            out['unread'][key] = '%s: %s' % (type(error).__name__, error)
            log('%-28s UNREAD %s' % (key, out['unread'][key]), flush=True)
            continue
        out['rows'][key] = row
        if row['problems']:
            out['failing'].append(key)
        log('%-24s %4d/%-5d tris  extent %s  girth %.2f  hull %5.1f %%  open %3d  seam %.2f/%2.0f%%  tear %s  %s' % (
            key, row['triangles'], row['source_triangles'], '/'.join('%.2f' % e for e in row['extent']),
            row['least_girth'], 100 * row['hull'], row['open'], row['seam_gap'], 100 * row['seam_open'],
            '-' if row.get('tear') is None else '%.2f' % row['tear'],
            'FAIL: ' + '; '.join(row['problems']) if row['problems'] else 'PASS'), flush=True)
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='command', required=True)
    c = sub.add_parser('creature', help='one creature mesh against a baked model')
    c.add_argument('--mesh', required=True)
    c.add_argument('--model', type=Path, required=True)
    c.add_argument('--table', type=Path)
    c.add_argument('--biped', action='store_true')
    c.add_argument('--data-files', type=Path, required=True)
    lib = sub.add_parser('library', help="a build run's creature library and named residents")
    lib.add_argument('--run', type=Path, required=True)
    lib.add_argument('--data-files', type=Path, required=True)
    lib.add_argument('--creatures', default='all', help="'all', 'none' or a comma list of meshes (r/guar.nif,...)")
    lib.add_argument('--npcs', default='', help='a comma list of NPC record ids')
    lib.add_argument('--json', type=Path)
    a = p.parse_args(argv)
    from mwad.paths import resolve_data_files
    data = resolve_data_files(a.data_files)
    if a.command == 'creature':
        row = check_creature(data, a.mesh, a.model.read_bytes(), a.table.read_bytes() if a.table else None,
                             a.biped)
        print(json.dumps(row, indent=1))
        return 1 if row['problems'] else 0
    creatures = None if a.creatures == 'none' else 'all' if a.creatures == 'all' else set(a.creatures.split(','))
    npcs = [n for n in a.npcs.split(',') if n]
    print('=== outer-hull check of %s: creatures %s, residents %d ===' % (a.run, a.creatures, len(npcs)), flush=True)
    out = library(a.run, data, creatures, npcs)
    print('=== %d models: %d pass, %d fail, %d unread ===' % (
        len(out['rows']), len(out['rows']) - len(out['failing']), len(out['failing']), len(out['unread'])))
    if a.json:
        a.json.write_text(json.dumps(out, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    return 2 if out['unread'] else 1 if out['failing'] else 0


if __name__ == '__main__':
    sys.exit(main())
