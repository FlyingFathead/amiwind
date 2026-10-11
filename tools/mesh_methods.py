# SPDX-License-Identifier: GPL-3.0-only
"""CHIM mesh methods: how the CHIM builder turns each mesh into Quake faces (docs/chim/MESH_METHODS.md).

Methods (DON'T DELETE ANY METHOD: every one stays selectable):

  converter       the converter's own polygon step and the profile's reducer (the method before v0.0.36-dev3)
  merge           the same reduction, then planar merge (tools/planar_merge.py): lossless, never more faces
  meshopt+merge   meshoptimizer's simplifier with locked borders (tools/meshopt.py, vendored, MIT) in place
                  of the profile's reducer, then planar merge; only meshes the profile reduces (ratio < 1)

config/mesh-methods.json names the default method and the meshes that get another one, each with the
measurement that chose it (tools/mesh_methods.py sweep applies the rule in that file island-wide). The
build setting `mesh_method` (chim_build.py --mesh-method, tools/build.py --chim-mesh-method) is `table`
(default: the file) or one method for every mesh (an override, e.g. `converter` for the earlier output).

Only the CHIM builder's profiles carry these keys (chim.build.prepare_area, chim.seyda); the legacy
converters are unchanged.

    python3 tools/mesh_methods.py sweep --data-files DIR --world CHIM_WORLD_DIR --out REPORT.json [--jobs N]
        measure every reduced hard-surface mesh of a CHIM world's areas both ways and print the table rows
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'config/mesh-methods.json'
METHODS = {'converter': {}, 'merge': {'faces': 'merge'}, 'meshopt+merge': {'reducer': 'meshopt', 'faces': 'merge'}}
MODES = ('table',) + tuple(METHODS)


def load(path=CONFIG):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if data.get('format') != 'amiwind-mesh-methods-1':
        raise ValueError('Not a mesh method table: %s' % path)
    if data['default'] not in METHODS:
        raise ValueError('Unknown default mesh method: %s' % data['default'])
    for source, row in data.get('meshes', {}).items():
        if row['method'] not in METHODS:
            raise ValueError('Unknown mesh method for %s: %s' % (source, row['method']))
        if source != source.lower().replace('\\', '/'):
            raise ValueError('Mesh method rows name lower-case sources with /: %s' % source)
    return data


def method_of(source, settings=None, table=None):
    """The method of one mesh under the build setting mesh_method ('table' or a method for every mesh)."""
    mode = (settings or {}).get('mesh_method', 'table')
    if mode not in MODES:
        raise ValueError('Unknown mesh method mode: %s' % mode)
    if mode != 'table':
        return mode
    table = table or load()
    row = table.get('meshes', {}).get(source.lower().replace('\\', '/'))
    return row['method'] if row else table['default']


def apply(profile, source, settings=None, table=None):
    """The profile with the mesh's method keys (a new dict; the converter method adds nothing)."""
    method = method_of(source, settings, table)
    out = {k: v for k, v in profile.items() if k not in ('reducer', 'faces', 'method_version')}
    out.update(METHODS[method])
    if method == 'meshopt+merge' and not (out.get('ratio') and out['ratio'] < 1):
        out.pop('reducer')                  # nothing to reduce: planar merge only
    if method != 'converter':
        # part of the mesh unit key (chim.build.mesh_fingerprint hashes the profile): a changed merge step or
        # meshoptimizer source gives new units, the converter's units keep their keys
        out['method_version'] = MERGE_VERSION + ('|meshopt-' + meshopt_sha()[:16] if 'reducer' in out else '')
    return out


MERGE_VERSION = 'planar-merge-1'


def meshopt_sha():
    from meshopt import source_sha256
    return source_sha256()


# ------------------------------------------------------------------ the island-wide sweep (rule in the table file)

def hard_surface(source):
    """Architecture and objects (meshes/x, d, o, i, l), not flora, creatures or rocks (meshes/f, r, and the
    flora_ and terrain_ meshes kept under the object folders)."""
    s = source.lower().replace('\\', '/')
    name = s.rsplit('/', 1)[-1]
    return (s.startswith(('meshes/x/', 'meshes/d/', 'meshes/o/', 'meshes/i/', 'meshes/l/'))
            and not name.startswith(('flora_', 'terrain_')))


def measure(task):
    """One mesh both ways: faces, render bytes, seam audit, shape error (sampled both ways)."""
    import numpy as np
    from prepare_scenery import model_geometry, nif_reader
    from mwad.scene import unpack_geometry
    from seam_audit import _point_triangle_distance, measure as seams
    from static_lod import reduce_for_profile
    from world_estimate_data import MeshSource
    from planar_merge import converter_polygons, merged_polygons
    data_files, source, profile = task
    raw, _ = MeshSource(data_files).read(source)
    packet, materials, _, _ = model_geometry(raw, nif_reader(), repair_uv=True)
    vv, ff, _ = unpack_geometry(packet)
    v, f = np.array(vv, float), np.array(ff, int)
    tex = profile.get('texture_size', 64)
    row = {'source': source, 'triangles': int(len(f)), 'ratio': profile.get('ratio')}
    for name, prof, merge in (('converter', profile, False), ('meshopt+merge', dict(profile, reducer='meshopt'), True)):
        rv, rf, _ = reduce_for_profile(v, f, prof, materials, source)
        polys = merged_polygons(rv, rf, tex) if merge else converter_polygons(rv, rf, tex)
        if merge:
            base = converter_polygons(rv, rf, tex)
            polys = polys if len(polys) < len(base) else base
        s = seams(v, f, rv, rf)
        rng = np.random.default_rng(1)

        def sample(vx, fx, n=8000):
            t = vx[fx[:, :3], :3]
            a = np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1)
            pick = rng.choice(len(t), size=n, p=a / a.sum())
            r1, r2 = rng.random(n), rng.random(n)
            q = np.sqrt(r1)
            t = t[pick]
            return t[:, 0] * (1 - q)[:, None] + t[:, 1] * (q * (1 - r2))[:, None] + t[:, 2] * (q * r2)[:, None]
        d1 = _point_triangle_distance(sample(v, f), rv[rf[:, :3], :3], 0.05)
        d2 = _point_triangle_distance(sample(rv, rf), v[f[:, :3], :3], 0.05)
        row[name] = {'faces': len(polys), 'triangles': int(len(rf)), 'seam_torn': s['seam']['torn_share'],
                     'rim_torn': s['rim']['torn_share'], 'hausdorff': round(float(max(d1.max(), d2.max())), 3),
                     'mean_error': round(float(d1.mean()), 4)}
    return row


def chooses_meshopt(row, rule):
    """The table rule: hard surface, at least min_faces faces now, and meshopt+merge no worse on seams and
    shape error and fewer faces."""
    a, b = row['converter'], row['meshopt+merge']
    return (row['hard_surface'] and a['faces'] >= rule['min_faces'] and b['faces'] < a['faces']
            and b['seam_torn'] <= a['seam_torn'] and b['rim_torn'] <= a['rim_torn']
            and b['hausdorff'] <= a['hausdorff'] * (1 + rule['hausdorff_slack']))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('sweep')
    s.add_argument('--data-files', required=True)
    s.add_argument('--profiles', type=Path, required=True,
                   help='JSON {mesh source: converter profile} of the meshes to measure (every CHIM area)')
    s.add_argument('--out', type=Path, required=True)
    s.add_argument('--jobs', type=int)
    a = p.parse_args(argv)
    sys.path.insert(0, str(ROOT / 'src'))
    from build_jobs import resolve_jobs
    from build_parallel import ordered_map
    profiles = json.loads(a.profiles.read_text(encoding='utf-8'))
    rule = load()['rule']
    tasks = [(a.data_files, src, prof) for src, prof in sorted(profiles.items())
             if prof.get('ratio') and prof['ratio'] < 1]
    rows = []
    for row in ordered_map(measure, tasks, resolve_jobs(a.jobs)):
        row['hard_surface'] = hard_surface(row['source'])
        row['meshopt'] = chooses_meshopt(row, rule)
        rows.append(row)
        print(json.dumps(row), flush=True)
    a.out.write_text(json.dumps(rows, indent=1) + '\n', encoding='utf-8', newline='\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
