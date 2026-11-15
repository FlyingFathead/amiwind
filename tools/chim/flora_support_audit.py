#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""World-wide audit of the plants that grow on another object (FLORA-SUPPORT, HARVEST-HYPHA-FACIA-FLOATING-65,
FUNGI-FLOATING-62): every bracket fungus of the base master (models named *shelffungus*), the object it sits on in
the original (its support: the nearest placed model by surface distance, a tree trunk, a log or a rock) and how
far it is from that support in the original and in the built CHIM world.

For each plant:

- original gap: the smallest distance from the plant's own vertices (its reference transform) to the triangles of
  the placed models near it, all read from your own game files as the converter reads them
  (tools/mesh_export.load_mesh), in Quake units (Morrowind units x 0.25);
- built gap: the same distance to the triangles the CHIM world draws in the plant's own frame (every placement's
  model image, at its origin and yaw), the plant itself and other bracket fungi left out;
- support gap: the distance to the built placement of the original support (by its reference number), or
  "missing" when the frame does not place it.

A plant is FLOATING when its built gap is over the tolerance while its original gap is within it (the original
seats it on something the build lost or moved). Prints one line per floating plant, counts by model and region,
and the cause per plant (support missing; support placed but reduced away from the plant; support moved), and
exits 1 when more than --max-floating plants float. Read only; frames run on a process pool (--jobs).

    python3 tools/chim/flora_support_audit.py CHIM_WORLD_DIR --data-files DIR [--json OUT] [--jobs N]
        [--tolerance 2.0] [--max-floating 0]
"""
import argparse
import json
import math
import os
import re
import struct
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT / 'tools', ROOT / 'src'):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

QUAKE = 0.25
CELL = 8192.0
TOLERANCE = 2.0              # Quake units (8 original units): a seated plant touches its support
NEAR = 64.0                  # original units: supports are looked for within this of the plant's box
SUPPORTED = re.compile(r'(^|/)flora_[a-z]+_shelffungus_\d+\.nif$')
MAX_PLANT_POINTS = 96

_STATE = {}


def is_supported_plant(model):
    """A model that grows on another object (the bracket fungi on tree trunks and logs)."""
    return bool(SUPPORTED.search(str(model).replace('\\', '/').lower()))


def mesh_source(model):
    return 'meshes/' + str(model).replace('\\', '/').lower()


# ---------------------------------------------------------------- geometry


def rotation(rot):
    """The reference rotation as the converter applies it (prepare_scenery.reference_rotation)."""
    import numpy as np
    x, y, z = [-a for a in rot]
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return rx @ ry @ rz


def place(points, ref):
    import numpy as np
    return np.asarray(points, float) @ rotation(ref['rotation_radians']).T * ref.get('scale', 1.0) \
        + np.asarray(ref['position'], float)


def brush_triangles(image):
    """Triangles (n x 3 x 3) of every face of a CHIM brush image (fan per face)."""
    import numpy as np
    from chim import format as F
    lumps = F.read_brush_image(image)
    verts = np.array(list(struct.iter_unpack('<3f', lumps[3])), float).reshape(-1, 3)
    edges = list(struct.iter_unpack('<HH', lumps[12]))
    surf = [v[0] for v in struct.iter_unpack('<i', lumps[13])]
    tris = []
    for f in struct.iter_unpack('<HhihH4Bi', lumps[7]):
        try:
            idx = [edges[e][0] if e >= 0 else edges[-e][1] for e in surf[f[2]:f[2] + f[3]]]
        except IndexError:
            continue
        for k in range(1, len(idx) - 1):
            tris.append((idx[0], idx[k], idx[k + 1]))
    if not tris or not len(verts):
        return np.zeros((0, 3, 3))
    t = np.array(tris, int)
    t = t[(t < len(verts)).all(axis=1)]
    return verts[t]


def placed_triangles(tris, origin, yaw):
    """A CHIM placement's triangles in frame-local units: the model image turned by yaw (degrees, about z) and
    moved to the origin (the engine's entity angles: pitch and roll are baked into the model variant)."""
    import numpy as np
    a = math.radians(yaw)
    c, s = math.cos(a), math.sin(a)
    r = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    return tris @ r.T + np.asarray(origin, float)


def point_triangle_distance(points, tris):
    """Smallest distance from any of points (p x 3) to any triangle (t x 3 x 3); inf when there are none."""
    import numpy as np
    if not len(points) or not len(tris):
        return (math.inf, None, None)
    p = np.asarray(points, float)[:, None, :]
    a, b, c = (tris[None, :, k, :] for k in range(3))
    ab, ac, ap = b - a, c - a, p - a
    d1 = (ab * ap).sum(-1); d2 = (ac * ap).sum(-1)
    bp = p - b; d3 = (ab * bp).sum(-1); d4 = (ac * bp).sum(-1)
    cp = p - c; d5 = (ab * cp).sum(-1); d6 = (ac * cp).sum(-1)
    va = d3 * d6 - d5 * d4; vb = d5 * d2 - d1 * d6; vc = d1 * d4 - d3 * d2
    denom = va + vb + vc
    denom = np.where(np.abs(denom) < 1e-12, 1e-12, denom)
    v = vb / denom; w = vc / denom
    closest = a + ab * v[..., None] + ac * w[..., None]            # inside the face
    # edges and corners where the projection falls outside
    def seg(p0, p1):
        d = p1 - p0
        t = np.clip(((p - p0) * d).sum(-1) / np.maximum((d * d).sum(-1), 1e-12), 0, 1)
        return p0 + d * t[..., None]
    inside = (va >= 0) & (vb >= 0) & (vc >= 0)
    cands = [np.where(inside[..., None], closest, np.inf)]
    for p0, p1 in ((a, b), (b, c), (c, a)):
        cands.append(seg(np.broadcast_to(p0, closest.shape), np.broadcast_to(p1, closest.shape)))
    best = (math.inf, None, None)
    for q in cands:
        d = np.sqrt(((p - q) ** 2).sum(-1))
        d = np.where(np.isfinite(d), d, np.inf)
        i = np.unravel_index(int(np.argmin(d)), d.shape)
        if float(d[i]) < best[0]:
            best = (float(d[i]), np.asarray(points, float)[i[0]], q[i].copy())
    return best


def point_triangle_closest(points, tris, step=2048):
    """(distance, plant point, support point) of the closest pair; (inf, None, None) when there are no triangles."""
    best = (math.inf, None, None)
    for i in range(0, len(tris), step):
        found = point_triangle_distance(points, tris[i:i + step])
        if isinstance(found, tuple) and found[0] < best[0]:
            best = found
    return best


def chunked_distance(points, tris, step=2048):
    return point_triangle_closest(points, tris, step)[0]


def box_of(points):
    import numpy as np
    p = np.asarray(points, float)
    return p.min(axis=0), p.max(axis=0)


def boxes_near(a, b, margin):
    return all(a[0][k] - margin <= b[1][k] and b[0][k] - margin <= a[1][k] for k in range(3))


# ---------------------------------------------------------------- original data


def read_master(data_files):
    """(objects {id: (type, model)}, exterior references [ref + cell, region]) of the base master."""
    from mwad.audit import cell_data, normpath, records, string, subrecords
    from mwad.masters import master_path
    from mwad.paths import resolve_data_files
    master = master_path(resolve_data_files(data_files), ['Morrowind.esm']).read_bytes()
    objects, refs = {}, []
    for tag, flags, payload in records(master):
        if tag == 'CELL':
            cell = cell_data(list(subrecords(payload)))
            if cell['flags'] & 1:
                continue
            for r in cell['refs']:
                if r.get('deleted') or 'position' not in r:
                    continue
                refs.append(dict(r, cell=[cell['x'], cell['y']], region=cell['region']))
        elif tag in ('STAT', 'CONT', 'ACTI', 'DOOR', 'LIGH', 'MISC'):
            fields = dict(subrecords(payload))
            if 'NAME' in fields and 'MODL' in fields and 'DELE' not in fields:
                objects[string(fields['NAME']).lower()] = (tag, normpath(string(fields['MODL'])))
    out = []
    for r in refs:
        obj = objects.get(r.get('id', '').lower())
        if obj:
            out.append(dict(r, type=obj[0], model=obj[1]))
    return out


def mesh_points(data_files, model, cache):
    """(vertices m x 3, triangles t x 3 x 3) of an original model in its own space (Morrowind units)."""
    if model not in cache:
        import numpy as np
        try:
            # mesh_export.load_mesh's own steps, with one archive reader for the whole run
            from prepare_scenery import model_geometry, nif_reader
            from mwad.scene import unpack_geometry
            from world_estimate_data import MeshSource
            if 'source' not in _STATE:
                _STATE['source'], _STATE['nif'] = MeshSource(data_files), nif_reader()
            raw, _ = _STATE['source'].read(mesh_source(model))
            packet, _, _, _ = model_geometry(raw, _STATE['nif'], repair_uv=True)
            v, f, _ = unpack_geometry(packet)
            v = np.asarray(v, float)[:, :3]
            f = np.asarray(f, int)[:, :3] if len(f) else np.zeros((0, 3), int)
            cache[model] = (v, v[f] if len(f) else np.zeros((0, 3, 3)))
        except Exception as e:          # a model the converter cannot read draws nothing in the build either
            cache[model] = (np.zeros((0, 3)), np.zeros((0, 3, 3)), str(e)[:120])
    return cache[model][:2]


# ---------------------------------------------------------------- per frame


def _init(world, data_files):
    from chim import format as F
    from chim import reach  # noqa: F401  (format 0.8+ headers)
    root = Path(world) / 'chim'
    _, files, mdir, _ = F.read_index((root / 'world.cwi').read_bytes())
    from flora_support import seats
    _STATE.update(world=str(world), data_files=data_files, mdir=mdir, meshes={}, images={}, seats=seats(),
                  frames={tuple(f['cell']): i for i, f in enumerate(x for x in files if x['kind'] == b'FRAM')})


def audit_cell(task):
    """Rows for the supported plants of one cell, measured in that cell's frame."""
    import numpy as np
    from chim.validate import load_frame
    cell, plants, near = task
    st = _STATE
    rows = []
    fi = st['frames'].get(tuple(cell))
    built = None
    if fi is not None:
        (_, frame, chunks), models = load_frame(st['world'], fi)
        centre = np.array(list(frame['centre']) + [0.0]) * QUAKE
        built = []
        for c in chunks:
            for r in c['owned'] + c['reach']:
                name = st['mdir'][r['model']]['name'] if r['model'] < len(st['mdir']) else '?'
                built.append((r, name, models.get(r['model'])))
    for p in plants:
        pv, _ = mesh_points(st['data_files'], p['model'], st['meshes'])
        if not len(pv):
            rows.append(dict(number=p['number'], id=p['id'], cell=cell, region=p['region'], status='unreadable'))
            continue
        step = max(1, len(pv) // MAX_PLANT_POINTS)
        pw = place(pv[::step], p)
        pbox = box_of(pw)
        # original support: the nearest placed model by surface distance
        best = (math.inf, None)
        for q in near:
            if q['number'] == p['number'] or is_supported_plant(q['model']):
                continue
            if max(abs(q['position'][k] - p['position'][k]) for k in range(2)) > 3 * CELL / 8:
                continue
            qv, qt = mesh_points(st['data_files'], q['model'], st['meshes'])
            if not len(qt):
                continue
            qw = place(qv, q)
            if not boxes_near(box_of(qw), pbox, NEAR):
                continue
            tw = qt @ rotation(q['rotation_radians']).T * q.get('scale', 1.0) + np.asarray(q['position'], float)
            d = chunked_distance(pw, tw) * QUAKE
            if d < best[0]:
                best = (d, q)
        orig_gap, host = best
        row = dict(number=p['number'], id=p['id'], model=p['model'], cell=cell, region=p['region'],
                   position=[round(v, 1) for v in p['position']], original_gap=round(orig_gap, 2),
                   support=(dict(number=host['number'], id=host['id'], model=host['model']) if host else None))
        if built is None:
            row.update(status='no-frame')
            rows.append(row)
            continue
        # where the build draws the plant: the original pose plus its seat (config/flora-support.json), Quake units
        seat = np.asarray(st['seats'].get(p['number'], (0.0, 0.0, 0.0)), float)
        local = pw * QUAKE - centre + seat * QUAKE
        lbox = box_of(local)
        bgap, sgap, sname, smoved, spair = math.inf, None, None, None, None
        for r, name, m in built:
            if r['ref'] == p['number'] or 'shelffungus' in name or m is None:
                continue
            if not boxes_near((r['box'][0], r['box'][1]), lbox, NEAR * QUAKE):
                if not (host and r['ref'] == host['number']):
                    continue
            key = r['model']
            if key not in st['images']:
                try:
                    st['images'][key] = brush_triangles(m['image'])
                except ValueError:
                    st['images'][key] = np.zeros((0, 3, 3))
            tw = placed_triangles(st['images'][key], r['origin'], r['yaw'])
            d, pp, qq = point_triangle_closest(local, tw)
            bgap = min(bgap, d)
            if host and r['ref'] == host['number']:
                want = np.asarray(host['position'], float) * QUAKE - centre
                moved = float(np.linalg.norm(np.asarray(r['origin'], float) - want))
                if sgap is None or d < sgap:
                    sgap, sname, smoved = d, name, moved
                    spair = (pp, qq) if pp is not None else None
        # the seat that puts the plant's nearest point on the drawn support (original units, added to any seat)
        need = None
        if spair is not None and math.isfinite(sgap) and sgap > 0.5:
            step_q = (spair[1] - spair[0]) * (1.0 - 0.25 / sgap)          # stop a quarter unit short of the surface
            need = [round(float(v), 2) for v in seat + step_q / QUAKE]
        row.update(built_gap=round(bgap, 2) if math.isfinite(bgap) else None,
                   support_gap=round(sgap, 2) if sgap is not None and math.isfinite(sgap) else None,
                   support_built=sname, support_moved=round(smoved, 2) if smoved is not None else None,
                   seat=[round(float(v), 2) for v in seat] if seat.any() else None, seat_needed=need)
        rows.append(row)
    return rows


def _progress(results, total, t0):
    done, last = 0, time.monotonic()
    for out in results:
        done += 1
        if time.monotonic() - last > 5 or done == total:
            last = time.monotonic()
            print('  %d / %d cells, %.0f s' % (done, total, last - t0), flush=True)
        yield out


def classify(row, tol):
    if row.get('status') in ('unreadable', 'no-frame'):
        return row['status']
    og, bg = row['original_gap'], row.get('built_gap')
    if og > tol:
        return 'unsupported-in-original'
    if bg is not None and bg <= tol:
        return 'seated'
    if '#collision_only' in (row.get('support_built') or ''):
        return 'floating: support drawn as a sprite'
    if row['support_gap'] is None:
        return 'floating: support not placed'
    if (row.get('support_moved') or 0) > tol:
        return 'floating: support moved'
    return 'floating: support reduced away'


def write_config(path, rows):
    """The table the builder reads (tools/flora_support.py): every kept seat, every newly measured one, and the trees
    drawn as a sprite that carry a plant (they become meshes). Rows are sorted by reference: byte-stable output."""
    seats, hosts = {}, {}
    for r in rows:
        if r.get('seat_needed') and r['verdict'].startswith('floating') and 'sprite' not in r['verdict']:
            seats[r['number']] = dict(reference=r['number'], id=r['id'], cell=r['cell'], shift=r['seat_needed'],
                                      support=r['support']['number'], gap=r.get('support_gap'))
        elif r.get('seat'):
            seats[r['number']] = dict(reference=r['number'], id=r['id'], cell=r['cell'], shift=r['seat'],
                                      support=(r.get('support') or {}).get('number'), gap=r.get('original_gap'))
        if r['verdict'] == 'floating: support drawn as a sprite' or (
                r.get('support') and '#collision_only' in (r.get('support_built') or '')):
            s = r['support']
            hosts[s['number']] = dict(reference=s['number'], id=s['id'], cell=r['cell'], plant=r['number'])
    data = {'format': 'AmiWind flora support 1',
            'about': 'Plants that grow on another object: seats (original units) put a bracket fungus on the trunk its '
                     'tree is drawn with; mesh_hosts are trees drawn as a mesh because a plant grows on them. Measured '
                     'and checked by tools/chim/flora_support_audit.py.',
            'seats': [seats[k] for k in sorted(seats)], 'mesh_hosts': [hosts[k] for k in sorted(hosts)]}
    if path.is_file():          # kept as written: each known plant carries its reason
        old = json.loads(path.read_text(encoding='utf-8'))
        data['mesh_hosts'] = sorted({h['reference']: h for h in old.get('mesh_hosts', []) + data['mesh_hosts']}.values(),
                                    key=lambda h: h['reference'])
        if old.get('known_floating'):
            data['known_floating'] = old['known_floating']
    path.write_text(json.dumps(data, indent=1) + '\n', encoding='utf-8', newline='\n')
    print('wrote %s: %d seats, %d mesh hosts' % (path, len(seats), len(hosts)), flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('world', help='the CHIM world stage folder (holds chim/world.cwi)')
    ap.add_argument('--data-files', required=True)
    ap.add_argument('--json')
    ap.add_argument('--jobs', type=int, default=os.cpu_count() or 1)
    ap.add_argument('--tolerance', type=float, default=TOLERANCE)
    ap.add_argument('--max-floating', type=int, default=0)
    ap.add_argument('--cells', help='only these cells, "x,y;x,y"')
    ap.add_argument('--known-from-config', action='store_true',
                    help='do not fail on the plants config/flora-support.json lists under known_floating (reported)')
    ap.add_argument('--write-config', help='write the measured seats and mesh hosts (config/flora-support.json)')
    a = ap.parse_args(argv)
    t0 = time.monotonic()
    print('=== PHASE 1/3: original references ===', flush=True)
    refs = read_master(a.data_files)
    plants = [r for r in refs if is_supported_plant(r['model'])]
    by_cell = defaultdict(list)
    for r in refs:
        by_cell[tuple(r['cell'])].append(r)
    cells = defaultdict(list)
    for p in plants:
        cells[tuple(p['cell'])].append(p)
    if a.cells:
        keep = {tuple(int(v) for v in c.split(',')) for c in a.cells.split(';')}
        cells = {c: v for c, v in cells.items() if c in keep}
    print('%d references, %d supported plants in %d cells (%.1f s)' % (len(refs), sum(map(len, cells.values())),
                                                                     len(cells), time.monotonic() - t0), flush=True)
    tasks = []
    for c, ps in sorted(cells.items()):
        near = [q for dx in (-1, 0, 1) for dy in (-1, 0, 1) for q in by_cell.get((c[0] + dx, c[1] + dy), ())]
        tasks.append((list(c), ps, near))
    print('=== PHASE 2/3: measure %d cells on %d workers ===' % (len(tasks), a.jobs), flush=True)
    rows = []
    import multiprocessing
    done, last = 0, time.monotonic()
    # largest cells first so the long ones do not finish last on a few workers
    tasks.sort(key=lambda t: -len(t[1]) * len(t[2]))
    with multiprocessing.get_context('fork').Pool(max(1, min(a.jobs, len(tasks) or 1)), initializer=_init,
                                                  initargs=(a.world, a.data_files)) as pool:
        results = list(_progress(pool.imap_unordered(audit_cell, tasks), len(tasks), t0))
    for out in results:
        rows += out
    rows.sort(key=lambda r: (r['cell'], r['number']))
    print('=== PHASE 3/3: report ===', flush=True)
    for r in rows:
        r['verdict'] = classify(r, a.tolerance)
    known = {}
    if a.known_from_config:
        from flora_support import known_floating
        known = known_floating()
    for r in rows:
        if r['verdict'].startswith('floating') and r['number'] in known:
            r['known'] = known[r['number']]
    floating = [r for r in rows if r['verdict'].startswith('floating') and 'known' not in r]
    listed = [r for r in rows if 'known' in r]
    for r in listed:
        print('KNOWN %s ref %s cell %s,%s %s: %s' % (r['id'], r['number'], r['cell'][0], r['cell'][1], r['verdict'],
                                                  r['known']))
    by_verdict = Counter(r['verdict'] for r in rows)
    by_model = Counter((r.get('id'), r['verdict']) for r in floating)
    by_region = Counter((r['region'], r['verdict']) for r in floating)
    for r in sorted(floating, key=lambda r: -(r.get('built_gap') or 0)):
        print('FLOATING %s ref %s cell %s,%s gap %.1f (original %.1f) support %s built %s -> %s' % (
            r['id'], r['number'], r['cell'][0], r['cell'][1], r.get('built_gap') or -1, r['original_gap'],
            (r['support'] or {}).get('id'), r.get('support_built'), r['verdict']))
    print('verdicts:', dict(by_verdict))
    print('floating by model:', dict(by_model))
    print('floating by region:', dict(by_region))
    report = dict(format='AmiWind flora support audit 1', tolerance=a.tolerance, plants=len(rows),
                  verdicts=dict(by_verdict), floating=len(floating),
                  by_model=[[k[0], k[1], v] for k, v in sorted(by_model.items())],
                  by_region=[[k[0], k[1], v] for k, v in sorted(by_region.items())], rows=rows,
                  seconds=round(time.monotonic() - t0, 1))
    if a.json:
        Path(a.json).write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8', newline='\n')
    if a.write_config:
        write_config(Path(a.write_config), rows)
    ok = len(floating) <= a.max_floating
    print('FLORA SUPPORT %s: %d of %d plants floating (allowed %d), %.1f s' % (
        'PASS' if ok else 'FAIL', len(floating), len(rows), a.max_floating, time.monotonic() - t0), flush=True)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
