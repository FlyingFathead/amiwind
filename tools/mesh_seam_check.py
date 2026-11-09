#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Open-edge check of a reduced model against its source (NPC-BODY-REGRESSION-62, CREATURE-MESH-HOLES-62).

An edge used by exactly one face is open (Blender's "Select Non-Manifold" idea, in our own code). Positions are
welded first (rounded to WELD decimals), per shape and across shapes, so two shapes that share a seam count it as
closed where their faces meet. A reduced open edge is NEW when the source has no open edge there: its midpoint lies
farther than TOL from every open edge of the source (of the same shape, and of the welded whole). The bake gate
(npc_geometry.body_audit, creature_library.checked_bake) and this tool use the same code.

Usage (in the shell container):
  mesh_seam_check.py check --mesh r/duskyalit.nif --model progs/c_..._m.mdl --data-files DIR [--png OUT.png]
                           [--json OUT.json]
      the original NIF's shapes (posed as the creature bake poses them) against a baked model's frame 0: the new
      openings, the join map (every seam: which parts meet, its length, how much stayed open, the widest gap) and
      each part's thickness at 25 / 50 / 75 % of its length (1.0 = the source). --json writes the receipt the
      Toolkit page amiwind-toolkit/seam-check.html shows; the NPC bake writes the same fields into its receipt.
Exit 0 = PASS (no new opening), 1 = FAIL (each new opening printed with its shape and position). The thickness is
printed for reading, not judged here: a creature's parts are plates, claws and chains.

The bake stop (npc_geometry.seam_stop, MESH-SEAM-METHOD-62): an NPC bake of the builder with an uncovered new
opening or a limb under 0.5 of its width, or a creature bake with a new opening, stops (BakeStop) unless the model
has an entry in config/model-face-overrides.json. AMIWIND_MESH_SEAM_STOP=warn prints instead.
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

import numpy as np

for _path in (str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parents[1] / 'src')):
    if _path not in sys.path:
        sys.path.insert(0, _path)      # src/ ahead of tools/ (tools/mwad.py is the command, src/mwad the package)

WELD = 4          # decimals: positions closer than this are the same vertex
TOL = 0.25        # Quake units: two 8-bit alias grid steps of a 32-unit actor (npc_seam_audit.TOL)


def open_edges(points, faces):
    """(n, 2, 3) open edges (used by one face) of a triangle list after welding the positions."""
    points = np.asarray(points, float)
    faces = np.asarray(faces)[:, :3]
    if not len(faces):
        return np.zeros((0, 2, 3))
    welded, inverse = np.unique(np.round(points, WELD), axis=0, return_inverse=True)
    tri = inverse.reshape(-1)[faces]
    uses = Counter()
    for t in tri:
        for i in range(3):
            a, b = int(t[i]), int(t[(i + 1) % 3])
            if a != b:
                uses[(min(a, b), max(a, b))] += 1
    rim = [e for e, n in uses.items() if n == 1]
    return welded[np.array(rim, int)] if rim else np.zeros((0, 2, 3))


def _far_from(edges, reference, tol):
    """Mask: edge midpoints farther than TOL from every reference edge (segment distance)."""
    if not len(edges):
        return np.zeros(0, bool)
    if not len(reference):
        return np.ones(len(edges), bool)
    mid = edges.mean(axis=1)
    a, b = reference[:, 0], reference[:, 1]
    best = np.full(len(mid), np.inf)
    for start in range(0, len(mid), 256):
        p = mid[start:start + 256, None, :]
        ab = b - a
        t = np.clip(((p - a) * ab).sum(-1) / np.maximum((ab * ab).sum(-1), 1e-12), 0, 1)
        d = np.linalg.norm(p - (a + ab * t[..., None]), axis=-1)
        best[start:start + 256] = d.min(axis=1)
    return best > tol


def new_openings(shapes, frame, faces, face_shapes, tol=TOL):
    """[(shape index, shape name, midpoint (x, y, z))] of the reduced model's open edges that the source lacks.

    SHAPES: the source shapes (positions [frames, n, 3], faces); FRAME/FACES: the reduced model's frame 0 and faces;
    FACE_SHAPES: each reduced face's shape index. An edge is new when it is open in the reduced shape AND in the
    reduced whole (another shape does not close it), and no open edge of the source shape or the source whole lies
    within TOL of it."""
    frame = np.asarray(frame, float)
    faces = np.asarray(faces)[:, :3]
    face_shapes = np.asarray(face_shapes)
    src_whole = np.concatenate([np.asarray(s['positions'][0], float) for s in shapes])
    offsets = np.cumsum([0] + [len(s['positions'][0]) for s in shapes])
    src_faces = np.concatenate([np.asarray(s['faces'])[:, :3] + offsets[i] for i, s in enumerate(shapes)])
    source_whole_rims = open_edges(src_whole, src_faces)
    reduced_whole_rims = open_edges(frame, faces)
    out = []
    for i, s in enumerate(shapes):
        mine = faces[face_shapes == i] if len(face_shapes) == len(faces) else faces[:0]
        if not len(mine):
            continue
        rims = open_edges(frame, mine)
        if not len(rims):
            continue
        source_rims = open_edges(s['positions'][0], s['faces'])
        # open in the shape, open in the whole too (not closed by a neighbour) and new against the source
        still_open = ~_far_from(rims, reduced_whole_rims, 1e-3) if len(reduced_whole_rims) else np.zeros(len(rims), bool)
        new = still_open & _far_from(rims, source_rims, tol) & _far_from(rims, source_whole_rims, tol)
        for edge in rims[new]:
            out.append((i, s.get('name', ''), tuple(round(float(x), 2) for x in edge.mean(axis=0))))
    return out


def classify(shapes, frame, faces, face_shapes, covered_tris=None, tol=TOL):
    """(covered, uncovered) new openings. An opening is COVERED only when it lies on a head patch the bake removed
    because the hair or helmet hides it from every side (COVERED_TRIS: those removed source triangles, the bake's own
    test, npc_geometry.cull_hidden_head) AND it is not at a join: no other part's surface lies within TOL of it (the
    neck to the head, the neck to the chest and every body seam are never excused). Everything else is uncovered."""
    found = new_openings(shapes, frame, faces, face_shapes, tol)
    if covered_tris is None or not len(covered_tris):
        return [], found
    from npc_seam_audit import point_triangle_distance
    covered_tris = np.asarray(covered_tris, float)
    covered, uncovered = [], []
    for item in found:
        i, _, pos = item
        p = np.array([pos], float)
        on_patch = shapes[i]['part'] == 0 and point_triangle_distance(p, covered_tris, tol)[0] <= tol
        at_join = False
        if on_patch:
            for j, s in enumerate(shapes):
                # the hair or helmet is the cover itself, not a joined part
                if j == i or s['part'] == 1 or not len(s['faces']):
                    continue
                tris = np.asarray(s['positions'][0], float)[np.asarray(s['faces'])[:, :3]]
                if point_triangle_distance(p, tris, tol)[0] <= tol:
                    at_join = True
                    break
        (covered if on_patch and not at_join else uncovered).append(item)
    return covered, uncovered


def counts(shapes, frame, faces, face_shapes):
    """{'source_open': n, 'reduced_open': n, 'new': n} of the whole model (welded across shapes)."""
    src_whole = np.concatenate([np.asarray(s['positions'][0], float) for s in shapes])
    offsets = np.cumsum([0] + [len(s['positions'][0]) for s in shapes])
    src_faces = np.concatenate([np.asarray(s['faces'])[:, :3] + offsets[i] for i, s in enumerate(shapes)])
    return {'source_open': int(len(open_edges(src_whole, src_faces))),
            'reduced_open': int(len(open_edges(frame, faces))),
            'new': len(new_openings(shapes, frame, faces, face_shapes))}


STATIONS = (25, 50, 75)   # per cent along a limb's long axis where its thickness is measured
BAND = 0.08               # half the slab (share of the limb's length) whose samples give one station's thickness


def join_map(shapes, frame, faces):
    """[{'a', 'b', 'length', 'open_length', 'max_gap'}] for EVERY join of the source (a rim of shape a lying on shape
    b, npc_seam_audit.joint_edges), closed ones too: which parts meet, how long the seam is, how much of it the
    reduced model left open and the widest opening (npc_seam_audit.measure, the same TOL)."""
    import npc_seam_audit as seams
    src = [{'name': s.get('name', ''), 'points': np.asarray(s['positions'][0], float), 'faces': np.asarray(s['faces'])[:, :3]}
           for s in shapes]
    reduced = np.asarray(frame, float)[np.asarray(faces)[:, :3]]
    out = []
    for (a, b), (edges, inset) in sorted(seams.joint_edges(src).items()):
        length = np.linalg.norm(edges[:, 1] - edges[:, 0], axis=1)
        dist = seams.point_triangle_distance(inset, reduced, seams.TOL) if len(reduced) else np.full(len(inset), np.inf)
        gap = float(np.where(dist > seams.TOL, np.minimum(dist, 1e3), 0).max()) if len(dist) else 0.0
        out.append({'a': src[a]['name'], 'b': src[b]['name'], 'length': round(float(length.sum()), 3),
                    'open_length': round(float(length[dist > seams.TOL].sum()), 3), 'max_gap': round(gap, 3)})
    return out


def _samples(points, faces):
    tri = np.asarray(points, float)[np.asarray(faces)[:, :3]]
    if not len(tri):
        return np.zeros((0, 3))
    w = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1], [1 / 3] * 3, [.5, .5, 0], [0, .5, .5], [.5, 0, .5]])
    return np.einsum('kj,njd->nkd', w, tri).reshape(-1, 3)


def _slice(tris, along, at):
    """The points where the triangles' edges cross the plane along . p == at ((n, 3) array)."""
    if not len(tris):
        return np.zeros((0, 3))
    d = tris @ along - at                                   # (n, 3) signed distances of the corners
    out = []
    for i, j in ((0, 1), (1, 2), (2, 0)):
        a, b = d[:, i], d[:, j]
        cross = (a * b) < 0
        if cross.any():
            t = (a[cross] / (a[cross] - b[cross]))[:, None]
            out.append(tris[cross, i] + (tris[cross, j] - tris[cross, i]) * t)
        on = np.abs(a) < 1e-9
        if on.any():
            out.append(tris[on, i])
    return np.concatenate(out) if out else np.zeros((0, 3))


def thickness_profile(source_points, source_faces, frame, faces, stations=STATIONS, band=BAND):
    """{station: ratio} of one limb: at each station (per cent along the source's long principal axis) the
    cross-section of the reduced surface against the source's (the plane through the station cuts both models'
    triangles; the extent of the cut across the two narrow axes, the smaller ratio). 1.0 keeps the thickness; a
    station the reduced surface does not reach is 0.0; a station the source has no cross-section at is left out.
    BAND is kept for callers; the cut is exact."""
    src_tri = np.asarray(source_points, float)[np.asarray(source_faces)[:, :3]]
    red_tri = np.asarray(frame, float)[np.asarray(faces)[:, :3]] if len(faces) else np.zeros((0, 3, 3))
    src = _samples(source_points, source_faces)
    if len(src) < 8:
        return {}
    centre = src.mean(0)
    _, _, axes = np.linalg.svd(src - centre, full_matrices=False)
    along_s = (src - centre) @ axes[0]
    lo, hi = np.percentile(along_s, [2, 98])
    length = max(hi - lo, 1e-6)
    out = {}
    for st in stations:
        at = float(centre @ axes[0] + lo + length * st / 100.0)
        s = _slice(src_tri, axes[0], at)
        r = _slice(red_tri, axes[0], at)
        if len(s) < 3:
            continue
        if len(r) < 2:
            out[st] = 0.0
            continue
        ratios = []
        for axis in axes[1:]:
            a = (s - centre) @ axis; b = (r - centre) @ axis
            ratios.append(float((b.max() - b.min()) / max(a.max() - a.min(), 1e-6)))
        out[st] = round(min(ratios), 3)
    return out


def limb_thickness(shapes, frame, faces, face_shapes, groups=None):
    """{group: {station: ratio}}: thickness_profile per limb. GROUPS maps a name to source shape indices (an NPC
    body: its limb slots); without it every shape is its own group (a creature's parts)."""
    frame = np.asarray(frame, float)
    faces = np.asarray(faces)[:, :3]
    face_shapes = np.asarray(face_shapes)
    if groups is None:
        groups = {s.get('name', '') or str(i): [i] for i, s in enumerate(shapes)}
    out = {}
    for name, idx in groups.items():
        pts, fcs, off = [], [], 0
        for i in idx:
            p = np.asarray(shapes[i]['positions'][0], float)
            pts.append(p); fcs.append(np.asarray(shapes[i]['faces'])[:, :3] + off); off += len(p)
        if not pts:
            continue
        mine = faces[np.isin(face_shapes, idx)] if len(face_shapes) == len(faces) else faces[:0]
        prof = thickness_profile(np.concatenate(pts), np.concatenate(fcs), frame, mine)
        if prof:
            out[str(name)] = prof
    return out


def least_thickness(profile):
    """The thinnest station of a limb_thickness result (1.0 when empty)."""
    return min((v for p in profile.values() for v in p.values()), default=1.0)


def assign_faces(shapes, frame, faces):
    """Each reduced face's source shape (the shape whose source face centre is nearest), for a model baked without
    the bake's own face-to-shape list."""
    from scipy.spatial import cKDTree
    frame = np.asarray(frame, float)
    faces = np.asarray(faces)[:, :3]
    centres = np.concatenate([np.asarray(s['positions'][0], float)[np.asarray(s['faces'])[:, :3]].mean(1) for s in shapes])
    owner = np.concatenate([[i] * len(s['faces']) for i, s in enumerate(shapes)])
    return owner[cKDTree(centres).query(frame[faces].mean(1))[1]]


THICK_MIN_FACES = 24      # a creature shape this small is a detail (a claw, a fin): measured, never a limb


def audit(shapes, frame, faces, face_shapes=None):
    """The seam check's receipt of one reduced model against its source shapes: open edges, new openings with their
    positions, the join map, and the thickness at 25 / 50 / 75 % of every shape of THICK_MIN_FACES or more faces."""
    if face_shapes is None or len(face_shapes) != len(faces):
        face_shapes = assign_faces(shapes, frame, faces)
    found = new_openings(shapes, frame, faces, face_shapes)
    groups = {s.get('name', '') or str(i): [i] for i, s in enumerate(shapes) if len(s['faces']) >= THICK_MIN_FACES}
    thick = limb_thickness(shapes, frame, faces, face_shapes, groups)
    out = dict(counts(shapes, frame, faces, face_shapes))
    out.update(new_at=[[n, list(p)] for _, n, p in found[:20]], joins=join_map(shapes, frame, faces),
               thickness=thick, least_thickness=round(least_thickness(thick), 3))
    return out


def picture(shapes, frame, faces, found, out, size=420):
    """A PNG of the reduced model (front, side, three-quarter) with every new opening marked in red."""
    from PIL import Image, ImageDraw
    frame = np.asarray(frame, float)
    faces = np.asarray(faces)[:, :3]
    views = (('front', 0.0), ('side', 90.0), ('3/4', 45.0))
    img = Image.new('RGB', (size * len(views), size + 24), (30, 40, 60))
    lo, hi = frame.min(0), frame.max(0)
    centre = (lo + hi) / 2
    span = float(np.max(hi - lo)) * 1.1 or 1.0
    marks = np.array([p for _, _, p in found], float).reshape(-1, 3)
    for k, (label, angle) in enumerate(views):
        a = np.radians(angle)
        rot = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
        v = (frame - centre) @ rot.T
        m = (marks - centre) @ rot.T if len(marks) else marks
        def xy(p):
            return (k * size + size / 2 + p[1] / span * size, size / 2 - p[2] / span * size + 24)
        d = ImageDraw.Draw(img)
        order = np.argsort(v[faces][:, :, 0].mean(1))
        for i in order:
            tri = v[faces[i]]
            n = np.cross(tri[1] - tri[0], tri[2] - tri[0])
            g = int(70 + 160 * abs(n[0]) / (np.linalg.norm(n) + 1e-9))
            d.polygon([xy(p) for p in tri], fill=(g, g, g))
        for p in m:
            x, y = xy(p)
            d.ellipse((x - 4, y - 4, x + 4, y + 4), outline=(255, 0, 0), width=2)
        d.text((k * size + 6, 4), '%s: %d new openings' % (label, len(marks)), fill=(255, 220, 0))
    img.save(out)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='command', required=True)
    c = sub.add_parser('check', help='a creature mesh against a baked model (frame 0)')
    c.add_argument('--mesh', required=True)
    c.add_argument('--model', type=Path, required=True)
    c.add_argument('--data-files', type=Path, required=True)
    c.add_argument('--png', type=Path)
    c.add_argument('--json', type=Path, help='the receipt for the Toolkit page amiwind-toolkit/seam-check.html')
    a = p.parse_args(argv)
    import struct
    from npc_geometry import Assets
    from mwad.audit import BSA
    from mwad.paths import child_ci
    from prepare_gallery import creature_shapes
    assets = Assets(a.data_files, BSA(child_ci(a.data_files, 'Morrowind.bsa')))
    shapes = creature_shapes(assets, a.mesh)[0]
    raw = a.model.read_bytes()
    h = struct.unpack_from('<4si3f3ff3f8if', raw)
    scale, origin = np.array(h[2:5]), np.array(h[5:8])
    sw, sh, nv, nt = h[13], h[14], h[15], h[16]
    off = 84 + 4 + sw * sh + nv * 12
    tris = np.frombuffer(raw, '<i4', nt * 4, off).reshape(-1, 4)[:, 1:]
    off += nt * 16 + 4 + 8 + 16
    frame = np.frombuffer(raw, np.uint8, nv * 4, off).reshape(-1, 4)[:, :3] * scale + origin
    # without the bake's face-to-shape list, every reduced face is given the shape whose source surface is nearest
    face_shapes = assign_faces(shapes, frame, tris)
    found = new_openings(shapes, frame, tris, face_shapes)
    rep = audit(shapes, frame, tris, face_shapes)
    print('source open edges %(source_open)d, reduced open edges %(reduced_open)d, new %(new)d' % rep)
    for i, name, pos in found:
        print('NEW OPENING: shape %d %s at %s' % (i, name, pos))
    print('JOIN MAP (part / part: seam length, open length, widest gap):')
    for j in rep['joins']:
        print('  %s / %s: %.2f, %.2f, %.2f' % (j['a'], j['b'], j['length'], j['open_length'], j['max_gap']))
    print('THICKNESS at %s %% of the length (1.0 = the source):' % ' / '.join(map(str, STATIONS)))
    for name, prof in rep['thickness'].items():
        print('  %s: %s' % (name, ' / '.join('%.2f' % prof[s] if s in prof else '-' for s in STATIONS)))
    # a creature's thickness is shown, not judged (its parts are plates and claws; the bake stop judges openings)
    thin = False
    if a.json:
        import json
        a.json.write_text(json.dumps(dict(rep, model=str(a.model), mesh=a.mesh, stations=list(STATIONS),
                                          verdict='PASS' if not found and not thin else 'FAIL'), indent=1) + '\n',
                          encoding='utf-8', newline='\n')
    if a.png:
        picture(shapes, frame, tris, found, a.png)
    print('PASS' if not found and not thin else 'FAIL')
    return 0 if not found and not thin else 1


if __name__ == '__main__':
    sys.exit(main())
