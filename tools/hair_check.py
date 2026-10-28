#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The universal hair check (NPC-HAIR-BACK-MISSING-53): every hair and helmet of the island's NPCs, baked as the
game's skeletal residents are, against the original meshes.

The unit is the unique head + hair/helmet pairing (hair and heads are shared body parts: many NPCs wear the same
style); each pairing is baked once, from its first NPC (by record id), and every NPC wearing it gets that result.
Per pairing: the original hair or helmet (triangles, open edges after welding by position, pieces), ours (kept whole
or reduced, open edges), the head-through-hair count (directions from every side, front and hairline included, where
the original shows hair or helmet and ours shows head), the hair vertices inside the head, the model's faces,
vertices and resident bytes against the limits of the source being run (skeletal_actor.SKEL_VERTEX_LIMIT and
SKEL_FACE_LIMIT, which tests/test_skel_vertex_limit.py ties to the engine's defines).

Pass (verdict): no open edge the original does not have, and head through hair in at most PASS_HEAD_THROUGH of the
directions where the original shows hair (spike tips of a reduced spiky style; 0 is the target, a whole hair gives 0).

Outputs (private: they are made from the user's own game data): hair-check.json, hair-check.md (the ranked list),
hair-styles-sheet-N.png (every unique pairing, original against ours, back and top) and hair-worst-24.png.

    python3 tools/hair_check.py --data-files DIR --palette gfx/palette.lmp --out DIR [--jobs N] [--limit N]
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

PASS_HEAD_THROUGH = .01     # share of the original's hair directions where ours may show head (spike tips)
DIRECTIONS = 1500
CELL = 200
SHEET_COLUMNS = 4           # pairings per sheet row (each: original back, ours back, original top, ours top)
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


# ---- geometry (pure; tests/test_hair_check.py) ----
def open_edges(points, faces):
    """Edges used by one triangle only after welding the points by position (a closed shell has none)."""
    faces = np.asarray(faces)
    if not len(faces):
        return 0
    _, ix = np.unique(np.round(np.asarray(points, float), 4), axis=0, return_inverse=True)
    w = ix.reshape(-1)[faces]
    edges = np.sort(np.concatenate([w[:, [0, 1]], w[:, [1, 2]], w[:, [2, 0]]]), axis=1)
    _, counts = np.unique(edges, axis=0, return_counts=True)
    return int((counts == 1).sum())


def pieces(points, faces):
    """Connected pieces after welding by position."""
    faces = np.asarray(faces)
    if not len(faces):
        return 0
    _, ix = np.unique(np.round(np.asarray(points, float), 4), axis=0, return_inverse=True)
    w = ix.reshape(-1)[faces]
    parent = list(range(int(w.max()) + 1))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for a, b, c in w.tolist():
        for x, y in ((a, b), (b, c)):
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[rx] = ry
    return len({find(v) for v in np.unique(w)})


def sphere_dirs(n=DIRECTIONS):
    i = np.arange(n) + .5
    phi = np.arccos(1 - 2 * i / n)
    th = np.pi * (1 + 5 ** .5) * i
    return np.column_stack((np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)))


def outward_sign(points, faces):
    """+1 when most faces wind outward (normal away from the middle), else -1."""
    v = np.asarray(points)[np.asarray(faces)]
    n = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0])
    out = v.mean(1) - v.reshape(-1, 3).mean(0)
    return 1.0 if (np.einsum('ij,ij->i', n, out) > 0).mean() >= .5 else -1.0


def first_hits(points, faces, labels, centre, dirs, radius):
    """Label of the first front-facing face each ray from outside (centre + d*radius, towards the centre) meets; -1
    for none. Back faces are culled, as the alias renderer does."""
    points, faces, labels = np.asarray(points, float), np.asarray(faces), np.asarray(labels)
    a = points[faces[:, 0]]
    e1, e2 = points[faces[:, 1]] - a, points[faces[:, 2]] - a
    n = np.cross(e1, e2) * outward_sign(points, faces)
    out = np.full(len(dirs), -1)
    for i, d in enumerate(dirs):
        o, r = centre + d * radius, -d
        good = n @ r < 0
        q = np.cross(r, e2)
        det = np.einsum('ij,ij->i', e1, q)
        good &= np.abs(det) > 1e-12
        inv = np.where(good, 1 / np.where(good, det, 1), 0)
        s = o - a
        u = np.einsum('ij,ij->i', s, q) * inv
        w = np.cross(s, e1)
        v = (w @ r) * inv
        t = np.einsum('ij,ij->i', e2, w) * inv
        hit = good & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 0)
        if hit.any():
            out[i] = labels[np.flatnonzero(hit)[np.argmin(t[hit])]]
    return out


def head_through_hair(original, ours, dirs=None):
    """(directions where the original shows hair (1) and ours shows head (0), directions where the original shows
    hair). original/ours: (points, faces, labels) of the head (0) and hair (1) faces, in the same space."""
    dirs = sphere_dirs() if dirs is None else dirs
    p0, f0, l0 = original
    used = np.asarray(p0)[np.unique(np.asarray(f0))]
    centre = (used.min(0) + used.max(0)) / 2
    radius = 3 * float(np.ptp(used, axis=0).max())
    before = first_hits(p0, f0, l0, centre, dirs, radius)
    after = first_hits(*ours, centre, dirs, radius)
    return int(np.sum((before == 1) & (after == 0))), int(np.sum(before == 1))


def verdict(row):
    """'pass' or the reasons it fails (the gate test's rule, tests/test_hair_check.py)."""
    reasons = []
    if row.get('error'):
        return 'error: ' + row['error']
    if row['ours_open_edges'] > row['orig_open_edges']:
        reasons.append('open edges %d > %d' % (row['ours_open_edges'], row['orig_open_edges']))
    if row['hair_dirs'] and row['head_through_hair'] > PASS_HEAD_THROUGH * row['hair_dirs']:
        reasons.append('head through hair %d of %d' % (row['head_through_hair'], row['hair_dirs']))
    if row['model_vertices'] > row['vertex_limit']:
        reasons.append('model %d vertices > %d' % (row['model_vertices'], row['vertex_limit']))
    return 'pass' if not reasons else '; '.join(reasons)


def score(row):
    """Worst first: failing, then head through hair share, then open edges added."""
    if row.get('error'):
        return (2, 0, 0)
    share = row['head_through_hair'] / max(1, row['hair_dirs'])
    return (1 if row['verdict'] != 'pass' else 0, share, row['ours_open_edges'] - row['orig_open_edges'])


# ---- the bake ----
_capture = []


def _observe(real):
    def bake(shapes, *a, **k):
        parts = []
        k['face_parts'] = parts
        r = real(shapes, *a, **k)
        _capture.append({'shapes': shapes, 'r': r, 'parts': np.array(parts)})
        return r
    return bake


def pairing_key(app):
    head = [p['id'] for p in app['parts'] if p['slot'] == 0]
    cover = sorted(p['id'] for p in app['parts'] if p['slot'] == 1)
    return '%s|%s|%s|%s' % (app.get('race', ''), 'f' if app.get('female') else 'm', ','.join(head), ','.join(cover))


class Context:
    def __init__(self, data, palette):
        import npc_anim
        from halloween_cast import _assets
        from mwad.npc import load_master
        from mwad.paths import child_ci
        self.data = Path(data)
        self.palette = Path(palette).read_bytes()
        self.assets = _assets(self.data)
        self.kinds, _, _ = load_master(child_ci(self.data, 'Morrowind.esm'))
        self.profile = npc_anim.plan_profile('react+full')
        self.rigs = {}

    def appearance(self, ident):
        import npc_anim
        import npc_items
        from mwad.npc import outfit
        app = npc_items.attach_items(self.kinds, ident, outfit(self.kinds, ident))
        app['foot'] = npc_anim.foot_class(self.kinds, app)
        return app

    def rig(self, path):
        from npc_geometry import Skeleton
        if path not in self.rigs:
            self.rigs[path] = Skeleton(self.assets, path)
        return self.rigs[path]


_ctx = None


def _init(data, palette):
    global _ctx
    import npc_geometry
    os.environ.setdefault('AMIWIND_NPC_ANIM', 'react+full')
    os.environ.setdefault('AMIWIND_NPC_ANIM_TYPE', '2')
    if not getattr(npc_geometry.bake, '_hair_check', False):
        npc_geometry.bake = _observe(npc_geometry.bake)
        npc_geometry.bake._hair_check = True
    _ctx = Context(data, palette)


def meshes(call):
    """(original head+hair, ours head+hair): (points, faces, labels) each, frame 0 of the bake (the same space)."""
    pts, fcs, labs, off = [], [], [], 0
    for s in call['shapes']:
        if s['part'] not in (0, 1):
            continue
        pts.append(np.asarray(s['positions'][0]))
        fcs.append(np.asarray(s['faces']) + off)
        labs += [s['part']] * len(s['faces'])
        off += len(s['positions'][0])
    original = (np.concatenate(pts), np.concatenate(fcs), np.array(labs))
    frames, faces, _, _ = call['r']
    sel = np.isin(call['parts'], (0, 1))
    ours = (np.asarray(frames[0]), np.asarray(faces)[sel][:, [0, 2, 1]], call['parts'][sel])
    return original, ours


def check_pairing(job):
    """One pairing: bake its first NPC as the game's resident; the row of facts."""
    key, ident = job
    import skeletal_actor as sa
    row = {'pairing': key, 'npc': ident, 'vertex_limit': sa.SKEL_VERTEX_LIMIT, 'face_limit': sa.SKEL_FACE_LIMIT}
    try:
        app = _ctx.appearance(ident)
        _capture.clear()
        raw, _, skel, _, _ = sa.skeletal_resident(str(_ctx.data), _ctx.assets, app, _ctx.palette, _ctx.profile,
                                                  _ctx.rig)
        call = max(_capture, key=lambda c: len(c['r'][1]))
        original, ours = meshes(call)
        po, fo, lo = original
        pu, fu, lu = ours
        hair_o, hair_u = fo[lo == 1], fu[lu == 1]
        through, dirs = head_through_hair(original, ours)
        frames = call['r'][0]
        # hair vertices inside the original head (its ray from the head's centre leaves the head beyond the vertex)
        import npc_geometry
        head = npc_geometry._cover([{'part': 1, 'positions': po[None], 'faces': fo[lo == 0]}])
        inside = 0
        if head is not None and len(hair_u):
            centre = po[np.unique(fo[lo == 0])].mean(axis=0)
            _, inside = npc_geometry.keep_outside_surface(pu[np.unique(hair_u)], head, centre, margin=0)
        row.update(name=app.get('name'), orig_hair_tris=int(len(hair_o)), orig_head_tris=int((lo == 0).sum()),
                   orig_open_edges=open_edges(po, hair_o), orig_pieces=pieces(po, hair_o),
                   ours_hair_tris=int(len(hair_u)), ours_head_tris=int((lu == 0).sum()),
                   ours_open_edges=open_edges(pu, hair_u), whole=bool(len(hair_u) == len(hair_o)),
                   head_through_hair=through, hair_dirs=dirs, hair_verts_inside_head=int(inside),
                   model_faces=int(len(call['r'][1])), model_vertices=int(frames.shape[1]),
                   resident_bytes=len(raw), budget=skel['model'].get('budget'))
    except Exception as error:      # one pairing's failure is a row, never the end of the check
        row['error'] = '%s: %s' % (type(error).__name__, error)
    row['verdict'] = verdict(row)
    return row


# ---- pictures ----
def _font(size):
    from PIL import ImageFont
    try:
        return ImageFont.truetype(FONT, size)
    except OSError:
        return ImageFont.load_default()


def draw(points, faces, colours, yaw, pitch, centre, extent, size=CELL):
    """Faces (back faces culled) in COLOURS, a simple light, from YAW/PITCH degrees around CENTRE."""
    from PIL import Image, ImageDraw
    p = np.asarray(points, float) - centre
    a, b = np.radians(yaw), np.radians(pitch)
    rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    rx = np.array([[1, 0, 0], [0, np.cos(b), -np.sin(b)], [0, np.sin(b), np.cos(b)]])
    v = (p @ rz.T @ rx.T)[np.asarray(faces)]
    n = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0]) * outward_sign(points, faces)
    light = np.array([0.3, -0.7, 0.6]) / np.linalg.norm([0.3, -0.7, 0.6])
    shade = 0.45 + 0.55 * np.abs(n @ light) / np.maximum(np.linalg.norm(n, axis=1), 1e-9)
    img = Image.new('RGB', (size, size), (40, 44, 56))
    d = ImageDraw.Draw(img)
    zoom = size * .78 / extent
    for i in np.argsort(-v[:, :, 1].mean(1)):
        if n[i, 1] >= 0:
            continue
        d.polygon([(size / 2 + w[0] * zoom, size / 2 - w[2] * zoom) for w in v[i]],
                  fill=tuple(int(c) for c in np.clip(np.asarray(colours[i]) * shade[i], 0, 255)))
    return img


def pairing_pictures(job):
    """Four pictures of one pairing (original back, ours back, original top, ours top): head grey, hair brown,
    so a head showing through the hair is plain to see."""
    key, ident = job
    import skeletal_actor as sa
    app = _ctx.appearance(ident)
    _capture.clear()
    sa.skeletal_resident(str(_ctx.data), _ctx.assets, app, _ctx.palette, _ctx.profile, _ctx.rig)
    call = max(_capture, key=lambda c: len(c['r'][1]))
    original, ours = meshes(call)
    used = original[0][np.unique(original[1])]
    centre = (used.min(0) + used.max(0)) / 2
    extent = float(np.ptp(used, axis=0).max())
    out = []
    for yaw, pitch in ((0., 0.), (0., 80.)):
        for p, f, l in (original, ours):
            colours = np.where((l == 1)[:, None], [[120, 80, 50]], [[205, 190, 170]])
            out.append(np.asarray(draw(p, f, colours, yaw, pitch, centre, extent)))
    return key, out


def sheet(rows, pictures, title, path):
    from PIL import Image, ImageDraw
    big, small = _font(18), _font(14)
    width = SHEET_COLUMNS * 4 * CELL
    tiles = [(r, pictures[r['pairing']]) for r in rows if r['pairing'] in pictures]
    nrows = (len(tiles) + SHEET_COLUMNS - 1) // SHEET_COLUMNS
    img = Image.new('RGB', (width, 40 + nrows * (CELL + 44)), (0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((8, 8), title, fill=(255, 255, 255), font=big)
    for i, (r, pics) in enumerate(tiles):
        x0, y0 = (i % SHEET_COLUMNS) * 4 * CELL, 40 + (i // SHEET_COLUMNS) * (CELL + 44)
        for k, pic in enumerate(pics):
            img.paste(Image.fromarray(pic), (x0 + k * CELL, y0 + 22))
        race, sex, _, cover = r['pairing'].split('|')
        d.text((x0 + 4, y0 + 2), '%s %s %s  x%d' % (race, sex, cover or '(no hair)', r['npcs']),
               fill=(255, 255, 160), font=small)
        ok = r['verdict'] == 'pass'
        d.text((x0 + 4, y0 + CELL + 24), ('A back | ours | A top | ours   ' +
                                           ('%s, through %s' % ('whole' if r.get('whole') else 'reduced',
                                                                r.get('head_through_hair')) if not r.get('error')
                                            else 'ERROR')),
               fill=(160, 255, 160) if ok else (255, 120, 120), font=small)
    img.save(path)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    p.add_argument('--data-files', required=True)
    p.add_argument('--palette', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--jobs', type=int, default=os.cpu_count() or 1)
    p.add_argument('--limit', type=int, default=0, help='only the first N pairings (a quick look)')
    p.add_argument('--no-sheets', action='store_true')
    a = p.parse_args(argv)
    import multiprocessing as mp
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    _init(a.data_files, a.palette)
    groups = {}
    for ident in sorted(_ctx.kinds['NPC_']):
        try:
            app = _ctx.appearance(ident)
        except Exception:           # an NPC without a humanoid appearance (no head): not a hair check
            continue
        if not any(part['slot'] == 0 for part in app['parts']):
            continue
        groups.setdefault(pairing_key(app), []).append(ident)
    jobs = sorted((key, ids[0]) for key, ids in groups.items())
    if a.limit:
        jobs = jobs[:a.limit]
    styles = {k.split('|')[3] for k in groups if k.split('|')[3]}
    print('Hair check: %d NPCs, %d unique head + hair/helmet pairings, %d hair/helmet styles; %d to bake on %d '
          'workers' % (sum(len(v) for v in groups.values()), len(groups), len(styles), len(jobs), a.jobs), flush=True)
    rows = []
    with mp.Pool(a.jobs, initializer=_init, initargs=(a.data_files, a.palette)) as pool:
        for n, row in enumerate(pool.imap_unordered(check_pairing, jobs), 1):
            row['npcs'] = len(groups[row['pairing']])
            rows.append(row)
            if n % 25 == 0 or n == len(jobs):
                print('Hair check: %d/%d pairings, %.0f s' % (n, len(jobs), time.time() - t0), flush=True)
    rows.sort(key=score, reverse=True)
    ok = [r for r in rows if not r.get('error')]
    summary = {
        'npcs': sum(r['npcs'] for r in rows), 'pairings': len(rows), 'styles': len(styles),
        'pass': sum(r['verdict'] == 'pass' for r in rows), 'errors': sum(bool(r.get('error')) for r in rows),
        'whole': sum(r['whole'] for r in ok), 'whole_npcs': sum(r['npcs'] for r in ok if r['whole']),
        'head_through_hair_pairings': sum(r['head_through_hair'] > 0 for r in ok),
        'open_edges_added_pairings': sum(r['ours_open_edges'] > r['orig_open_edges'] for r in ok),
        'resident_bytes_npcs_total': sum(r['resident_bytes'] * r['npcs'] for r in ok),
        'resident_bytes_pairings_max': max((r['resident_bytes'] for r in ok), default=0),
        'limits': {'vertices': rows[0]['vertex_limit'] if rows else None,
                   'faces': rows[0]['face_limit'] if rows else None},
        'pass_rule': 'no open edge the original lacks; head through hair <= %.1f %% of the hair directions'
                     % (100 * PASS_HEAD_THROUGH),
        'seconds': round(time.time() - t0)}
    (out / 'hair-check.json').write_text(json.dumps({'summary': summary, 'rows': rows}, indent=1) + '\n',
                                         encoding='utf-8', newline='\n')
    lines = ['# Hair check', '', '```', json.dumps(summary, indent=1), '```', '',
             '| # | pairing | NPCs | verdict | hair orig/ours | whole | open edges orig/ours | head through hair | '
             'model faces/verts | bytes |', '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    for i, r in enumerate(rows, 1):
        if r.get('error'):
            lines.append('| %d | %s | %d | %s | | | | | | |' % (i, r['pairing'], r['npcs'], r['verdict']))
            continue
        lines.append('| %d | %s | %d | %s | %d/%d | %s | %d/%d | %d of %d | %d/%d | %d |' % (
            i, r['pairing'], r['npcs'], r['verdict'], r['orig_hair_tris'], r['ours_hair_tris'], r['whole'],
            r['orig_open_edges'], r['ours_open_edges'], r['head_through_hair'], r['hair_dirs'], r['model_faces'],
            r['model_vertices'], r['resident_bytes']))
    (out / 'hair-check.md').write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
    print('Hair check: %(pass)d of %(pairings)d pairings pass, %(errors)d errors, %(whole)d whole' % summary,
          flush=True)
    if a.no_sheets:
        return 0
    with_hair = [r for r in rows if r['pairing'].split('|')[3]]
    worst = [r for r in with_hair if not r.get('error')][:24]
    # the pictures of the worst 24 and of each style's worst pairing only
    wanted, seen = [], set()
    for r in [x for x in with_hair if not x.get('error')]:
        cover = r['pairing'].split('|')[3]
        if (r in worst or cover not in seen) and r['pairing'] not in {w[0] for w in wanted}:
            wanted.append((r['pairing'], r['npc']))
        seen.add(cover)
    pictures = {}
    with mp.Pool(a.jobs, initializer=_init, initargs=(a.data_files, a.palette)) as pool:
        for key, pics in pool.imap_unordered(pairing_pictures, wanted):
            pictures[key] = pics
    sheet(worst, pictures, 'The worst 24 head + hair pairings (original against ours, back and top)',
          out / 'hair-worst-24.png')
    # every unique hair or helmet style once: its worst pairing (rows are sorted worst first), labelled with the NPCs
    # of every pairing that wears it
    styles_rows = {}
    for r in [x for x in with_hair if not x.get('error')]:
        cover = r['pairing'].split('|')[3]
        if cover not in styles_rows:
            styles_rows[cover] = dict(r, npcs=sum(x['npcs'] for x in with_hair if x['pairing'].split('|')[3] == cover))
    by_style = sorted(styles_rows.values(), key=lambda r: r['pairing'].split('|')[3])
    per = SHEET_COLUMNS * 12
    for i in range(0, len(by_style), per):
        sheet(by_style[i:i + per], pictures, 'Every hair and helmet style, its worst pairing (%d-%d of %d)' % (
            i + 1, min(i + per, len(by_style)), len(by_style)), out / ('hair-styles-sheet-%d.png' % (i // per + 1)))
    print('Hair check: sheets written, %.0f s' % (time.time() - t0), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
