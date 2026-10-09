#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Seam-tear audit: does a mesh reduction pull apart parts the source joins?

Static meshes are reduced per material component (static_lod.reduce_for_profile). A reducer that
moves a component's rim opens the seam where it met its neighbour, and the sky shows through a model
that is closed in the original (MESH-LOD-OPEN-SEAMS-33: the Silt Strider's shell plates; GEO-01: the
giant mushroom caps). This tool measures that for every mesh the converter reduces, island-wide,
offline and in parallel, and is the gate that keeps it from coming back.

Metric (geometric, no rendering): the source mesh is welded by position; every edge that bounds a
material component (used by one triangle of that component) is a rim edge, and a rim edge that two
or more components share is a seam edge. Each such edge is sampled; a sample is torn when it lies
farther than the tolerance (max(1 unit, 0.5 % of the model diagonal)) from the reduced surface. The
result is the torn share of seam length and of free-rim length. Unreduced meshes tear nothing.

Usage:
  seam_audit.py gate --data-files DIR --out REPORT.json [--jobs N]   (builder stage: audit, then check)
  seam_audit.py audit --data-files DIR --out REPORT.json [--jobs N] [--limit N]
  seam_audit.py check --report REPORT.json [--known config/seam-audit-known.json] [--threshold 0.02]
    check exits 1 when a reduced mesh tears more seam length than the threshold and is not a known,
    registered finding (or tears more than recorded). Known findings name their bug ID.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

DEFAULT_THRESHOLD = 0.02
KNOWN = Path(__file__).resolve().parents[1] / 'config/seam-audit-known.json'
SAMPLES_PER_EDGE = 3


def _pair_distance(p, a, b, c):
    """Exact distance from points p to triangles (a, b, c); arrays broadcast over leading axes."""
    import numpy as np
    ab, ac = b - a, c - a
    ap, bp, cp = p - a, p - b, p - c
    d1, d2 = (ab * ap).sum(-1), (ac * ap).sum(-1)
    d3, d4 = (ab * bp).sum(-1), (ac * bp).sum(-1)
    d5, d6 = (ab * cp).sum(-1), (ac * cp).sum(-1)
    vc, vb, va = d1 * d4 - d3 * d2, d5 * d2 - d1 * d6, d3 * d6 - d5 * d4
    denom = va + vb + vc
    denom = np.where(np.abs(denom) < 1e-30, 1e-30, denom)
    q = a + ab * (vb / denom)[..., None] + ac * (vc / denom)[..., None]
    inside = (va >= 0) & (vb >= 0) & (vc >= 0)
    dist = np.where(inside, np.linalg.norm(p - q, axis=-1), np.inf)
    for s, e in ((a, b), (b, c), (c, a)):
        se = e - s
        t = np.clip(((p - s) * se).sum(-1) / np.maximum((se * se).sum(-1), 1e-30), 0, 1)
        dist = np.minimum(dist, np.linalg.norm(p - (s + se * t[..., None]), axis=-1))
    return dist


def _point_triangle_distance(points, tris, tol):
    """Distance from each point to the reduced surface, exact where it matters: the 16 triangles
    with the nearest centroids first, then every triangle for points still farther than tol."""
    import numpy as np
    from scipy.spatial import cKDTree
    k = min(16, len(tris))
    _, idx = cKDTree(tris.mean(axis=1)).query(points, k=k)
    idx = idx.reshape(len(points), k)
    near = tris[idx]
    best = _pair_distance(points[:, None, :], near[:, :, 0], near[:, :, 1], near[:, :, 2]).min(axis=1)
    far = np.flatnonzero(best > tol)
    for start in range(0, len(far), 128):
        sel = far[start:start + 128]
        d = _pair_distance(points[sel, None, :], tris[None, :, 0], tris[None, :, 1], tris[None, :, 2])
        best[sel] = np.minimum(best[sel], d.min(axis=1))
    return best


def rim_edges(vertices, faces):
    """(seam edges, free rim edges) of the welded source, as (n, 2, 3) position arrays."""
    import numpy as np
    from collections import Counter, defaultdict
    from mesh_geometry import connected_components
    points, inverse = np.unique(np.round(vertices[:, :3], 3), axis=0, return_inverse=True)
    inverse = inverse.reshape(-1)
    owners = defaultdict(set)
    for material in sorted(set(faces[:, 3])):
        mf = faces[faces[:, 3] == material]
        for k, ids in enumerate(connected_components(vertices, mf)):
            tri = inverse[mf[ids][:, :3]]
            count = Counter(tuple(sorted((int(t[i]), int(t[(i + 1) % 3])))) for t in tri for i in range(3))
            for edge, n in count.items():
                if n == 1:
                    owners[edge].add((int(material), k))
    seams = [e for e, o in owners.items() if len(o) > 1]
    free = [e for e, o in owners.items() if len(o) == 1]
    as_xyz = lambda edges: points[np.array(edges, int)] if edges else np.zeros((0, 2, 3))
    return as_xyz(seams), as_xyz(free)


def measure(vertices, faces, reduced_vertices, reduced_faces):
    """Torn share of seam and free-rim length of one reduction (see module text)."""
    import numpy as np
    vertices = np.asarray(vertices, float)
    faces = np.asarray(faces, int)
    seams, free = rim_edges(vertices, faces)
    lo, hi = vertices[:, :3].min(axis=0), vertices[:, :3].max(axis=0)
    tol = max(1.0, 0.005 * float(np.linalg.norm(hi - lo)))
    tris = np.asarray(reduced_vertices, float)[np.asarray(reduced_faces, int)[:, :3], :3]
    out = {'tolerance': round(tol, 3), 'reduced_triangles': int(len(reduced_faces)),
           'source_triangles': int(len(faces))}
    for label, edges in (('seam', seams), ('rim', free)):
        if not len(edges):
            out[label] = {'edges': 0, 'length': 0.0, 'torn_length': 0.0, 'torn_share': 0.0}
            continue
        t = (np.arange(SAMPLES_PER_EDGE) + .5) / SAMPLES_PER_EDGE
        samples = edges[:, None, 0, :] * (1 - t)[None, :, None] + edges[:, None, 1, :] * t[None, :, None]
        length = np.linalg.norm(edges[:, 1] - edges[:, 0], axis=1)
        dist = _point_triangle_distance(samples.reshape(-1, 3), tris, tol).reshape(len(edges), SAMPLES_PER_EDGE)
        torn = (dist > tol).mean(axis=1) * length
        out[label] = {'edges': int(len(edges)), 'length': round(float(length.sum()), 2),
                      'torn_length': round(float(torn.sum()), 2),
                      'torn_share': round(float(torn.sum() / max(length.sum(), 1e-9)), 5),
                      'max_gap': round(float(np.where(dist > tol, dist, 0).max()), 2)}  # exact above tol
    return out


STATIC_TYPES = ('STAT', 'ACTI', 'DOOR', 'CONT')


def space_placements(masters):
    """{mesh: {space: placements}}: where the static converters meet each mesh. Exterior statics,
    activators, doors and containers go through the town converter ('town', or 'group' when a named
    scenery group profiles them); the open-world scenery converter takes the formations of
    world_scenery.scenery_kind ('world'); interior statics go through the interior converter.
    Creatures, NPCs and items are not converted by the static reducer and are not counted."""
    from collections import defaultdict
    from world_estimate_data import MASTERS
    from world_scenery import scenery_kind
    out = defaultdict(lambda: defaultdict(int))
    objects = {}
    for name in MASTERS:
        if name not in masters:
            continue
        objects.update(masters[name]['objects'])
        for cell in masters[name]['cells']:
            for r in cell['refs']:
                o = objects.get(r['id'])
                if r.get('deleted') or not o or not o.get('model') or o['type'] not in STATIC_TYPES or o.get('deleted'):
                    continue
                if cell['interior']:
                    out[o['model']]['interior'] += 1
                    continue
                out[o['model']]['town'] += 1
                if scenery_kind(r['id'], {'type': o['type'], 'model': o['model']}):
                    out[o['model']]['world'] += 1
    return {k: dict(v) for k, v in out.items()}


def converter_profiles(model, triangles, spaces=None):
    """{space: profile} of every converter path that reduces this mesh (ratio < 1): the named
    scenery groups (config/scenery_groups.json), town regions (town_regions.visual_profile), the
    open-world scenery (prepare_world_scenery.visual_profiles) and interiors (world_estimate_data).
    spaces limits the result to the converters that place the mesh (space_placements)."""
    from scenery_selection import load_groups
    from town_regions import town_model_profile
    from prepare_world_scenery import visual_profiles
    from world_estimate_data import interior_profile
    out = {}
    for group in load_groups().values():
        profile = group.get('visual_profiles', {}).get(model)
        if profile:
            out['group'] = dict(profile)
    # The town converters (legacy import_town and the CHIM model builder) put visual_profile over the
    # group's profile (town_model_profile); the Seyda Neen scenery path reads the group profile alone.
    # Both are measured, so no converter path reduces a mesh the audit has not seen.
    out['town'] = town_model_profile(out.get('group', {}), model, triangles)
    if out['town'] == out.get('group'):
        del out['town']
    out['world'] = visual_profiles({'models': [{'source': model, 'triangles': triangles}]})[model]
    interior = interior_profile(model, triangles)
    if interior:
        out['interior'] = interior
    if spaces is not None:
        out = {k: v for k, v in out.items() if (spaces.get('town') if k == 'group' else spaces.get(k))}
    return {k: v for k, v in out.items() if v.get('ratio') and v['ratio'] < 1}


_SOURCE = {}


def _audit_worker(task):
    data_files, model, spaces = task
    import numpy as np
    from prepare_scenery import nif_reader, model_geometry
    from mwad.scene import unpack_geometry
    from static_lod import reduce_for_profile
    from world_estimate_data import MeshSource
    if data_files not in _SOURCE:
        _SOURCE.clear()
        _SOURCE[data_files] = MeshSource(data_files)
    row = {'model': model}
    try:
        raw, _ = _SOURCE[data_files].read(model)
        packet, materials, _, _ = model_geometry(raw, nif_reader(), repair_uv=True)
        vv, ff, _ = unpack_geometry(packet)
        v, f = np.array(vv, float), np.array(ff, int)
    except Exception as exc:  # noqa: BLE001 - a mesh the converter cannot read is reported, not audited
        row['status'] = 'unreadable: %s' % str(exc)[:120]
        return row
    row['triangles'] = int(len(f))
    row['spaces'] = {}
    for space, profile in converter_profiles(model, len(f), spaces).items():
        try:
            rv, rf, _ = reduce_for_profile(v, f, profile, materials, model)
            row['spaces'][space] = {'ratio': round(profile['ratio'], 4),
                                    'lock_boundaries': bool(profile.get('lock_boundaries')),
                                    **measure(v, f, rv, rf)}
        except Exception as exc:  # noqa: BLE001
            row['spaces'][space] = {'error': str(exc)[:160]}
    row['status'] = 'ok'
    return row


def audit(data_files, jobs=None, limit=None, progress=print):
    from build_jobs import resolve_jobs
    from build_parallel import ordered_map
    from world_estimate_data import MASTERS, parse_master
    from mwad.paths import child_ci
    masters = {}
    for name in MASTERS:
        path = child_ci(Path(data_files), name, required=False)
        if path is not None and path.is_file():
            masters[name] = parse_master(path)
    placed = space_placements(masters)
    names = sorted(m for m in placed if m.endswith('.nif'))
    if limit:
        names = names[:limit]
    rows = []
    tasks = [(str(data_files), n, placed[n]) for n in names]
    for i, row in enumerate(ordered_map(_audit_worker, tasks, resolve_jobs(jobs))):
        row['placements'] = placed[row['model']]
        rows.append(row)
        if progress and (i % 200 == 0 or i == len(names) - 1):
            progress('seam audit %d/%d' % (i + 1, len(names)))
    return summarise(rows)


def summarise(rows):
    torn = []
    for row in rows:
        for space, r in row.get('spaces', {}).items():
            if 'seam' in r:
                placements = row.get('placements', {})
                count = placements.get('town' if space == 'group' else space, 0) if isinstance(placements, dict) else placements
                torn.append({'model': row['model'], 'space': space, 'placements': count,
                             'seam_torn_share': r['seam']['torn_share'], 'seam_torn_length': r['seam']['torn_length'],
                             'rim_torn_share': r['rim']['torn_share'], 'ratio': r['ratio'],
                             'source_triangles': r['source_triangles'], 'reduced_triangles': r['reduced_triangles']})
    torn.sort(key=lambda t: (-t['seam_torn_share'], -t['placements'], t['model'], t['space']))
    return {'format': 'amiwind-seam-audit-1', 'meshes': len(rows),
            'reduced_mesh_spaces': len(torn), 'ranked': torn, 'rows': rows}


def check(report, known=None, threshold=DEFAULT_THRESHOLD, closed=()):
    """Failures: reduced meshes above threshold that are not known findings (or worse than recorded),
    and any torn seam or rim on a mesh that must stay closed (repaired bugs, e.g. the Silt Strider)."""
    known = known or {}
    failures = []
    closed = {row['model']: row for row in closed}
    for t in report['ranked']:
        if t['model'] in closed and (t['seam_torn_share'] > 0 or t['rim_torn_share'] > 0):
            failures.append(dict(t, reason='must stay closed (%s)' % closed[t['model']].get('bug', '?')))
            continue
        if t['seam_torn_share'] <= threshold:
            continue
        k = known.get(t['model'], {}).get(t['space'])
        if k is None:
            failures.append(dict(t, reason='new torn mesh'))
        elif t['seam_torn_share'] > k['seam_torn_share'] + 0.005:
            failures.append(dict(t, reason='tears more than recorded (%s)' % k.get('bug', '?')))
    return failures


def load_known(path=KNOWN):
    """({model: {space: known row}}, [closed rows]) from the known-findings file."""
    path = Path(path)
    if not path.is_file():
        return {}, []
    data = json.loads(path.read_text(encoding='utf-8'))
    out = {}
    for row in data.get('known', []):
        out.setdefault(row['model'], {})[row['space']] = row
    return out, data.get('closed', [])


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    for name in ('audit', 'gate'):
        a = sub.add_parser(name)
        a.add_argument('--data-files', type=Path, required=True)
        a.add_argument('--out', type=Path, required=True)
        a.add_argument('--jobs', type=int)
        a.add_argument('--limit', type=int)
        a.add_argument('--known', type=Path, default=KNOWN)
        a.add_argument('--threshold', type=float, default=DEFAULT_THRESHOLD)
    c = sub.add_parser('check')
    c.add_argument('--report', type=Path, required=True)
    c.add_argument('--known', type=Path, default=KNOWN)
    c.add_argument('--threshold', type=float, default=DEFAULT_THRESHOLD)
    args = p.parse_args(argv)
    if args.cmd in ('audit', 'gate'):
        report = audit(args.data_files, args.jobs, args.limit)
        args.out.write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8', newline='\n')
        top = report['ranked'][:20]
        print('Seam audit: %d meshes, %d reduced mesh/space pairs, %d above %.0f %% seam tear' % (
            report['meshes'], report['reduced_mesh_spaces'],
            sum(t['seam_torn_share'] > DEFAULT_THRESHOLD for t in report['ranked']), DEFAULT_THRESHOLD * 100))
        for t in top:
            print('  %-48s %-8s seam %5.1f %%  rim %5.1f %%  placements %d' % (
                t['model'], t['space'], t['seam_torn_share'] * 100, t['rim_torn_share'] * 100, t['placements']))
        if args.cmd == 'audit':
            return 0
    else:
        report = json.loads(args.report.read_text(encoding='utf-8'))
    known, closed = load_known(args.known)
    failures = check(report, known, args.threshold, closed)
    missing = sorted({row['model'] for row in closed} - {t['model'] for t in report['ranked']})
    if missing and not getattr(args, 'limit', None):
        for model in missing:
            failures.append({'model': model, 'space': '-', 'seam_torn_share': 0, 'placements': 0,
                             'reason': 'must stay closed, but the audit did not measure it'})
    for f in failures:
        print('SEAM TEAR: %s (%s) %.1f %% of seam length, %d placements: %s' % (
            f['model'], f['space'], f['seam_torn_share'] * 100, f['placements'], f['reason']))
    print('Seam audit check: %d failure(s) above %.1f %%' % (len(failures), args.threshold * 100))
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
