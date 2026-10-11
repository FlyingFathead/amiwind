#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Reference models: named meshes rebuilt by a fixed recipe from your own game data and checked by SHA-256.

A reference model is not a file we ship: it is mathematics. config/reference-models.json names, for each
one, the source mesh in the game's data (its path and the SHA-256 of its bytes as the GOTY edition holds
them), the converter profile and reduction method with their exact parameters, and the SHA-256 the
builder must get at every step from that source. Anyone with their own copy of the game rebuilds the
same model and gets the same hashes. docs/chim/REFERENCE_MODELS.md describes each model in words.

Steps (each hashed over a canonical encoding, so the same mesh gives the same hash on any machine):

  source    the mesh file's bytes as read from the data files (loose file or BSA)
  geometry  the decoded mesh: vertices (position, texture coordinates) and triangles with materials
            (prepare_scenery.model_geometry, as the scenery export and the seam audit read it)
  visible   the triangles the converter draws (exterior_visibility.apply_exterior_selection)
  reduced   the profile's reduction (static_lod.reduce_for_profile)
  faces     the converter's faces: coplanar polygons and the 240-texel extent split
            (mesh_geometry.surface_polygons, split_surface), vertices rounded to 1e-4 units

The check never fails a build: a mismatch is a loud warning naming the first step that differs (a
different source file, a changed decoder, reducer or polygon step).

    reference_models.py check --data-files DIR [--json REPORT]
    reference_models.py compute --data-files DIR      (print the hashes, e.g. to record a new model)
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

CONFIG = ROOT / 'config/reference-models.json'
STEPS = ('source', 'geometry', 'visible', 'reduced', 'faces')


def _sha(*arrays):
    h = hashlib.sha256()
    for a in arrays:
        h.update(a)
    return h.hexdigest()


def mesh_hash(vertices, faces):
    """SHA-256 of a triangle mesh: positions and texture coordinates rounded to 1e-6, triangles (int32)."""
    import numpy as np
    v = np.round(np.asarray(vertices, dtype=float), 6) + 0.0      # + 0.0: no negative zero
    return _sha(v.astype('<f8').tobytes(), np.asarray(faces, dtype='<i4').tobytes())


def faces_hash(polys):
    """SHA-256 of converter faces (patch, material, axes, offset, normal): points rounded to 1e-4 units,
    texture axes and offsets to 1e-6, in the converter's order."""
    import numpy as np
    h = hashlib.sha256()
    for patch, material, axes, offset, normal in polys:
        h.update(np.int32(material).tobytes())
        h.update((np.round(np.asarray(patch, dtype=float), 4) + 0.0).astype('<f8').tobytes())
        h.update((np.round(np.asarray(axes, dtype=float), 6) + 0.0).astype('<f8').tobytes())
        h.update((np.round(np.asarray(offset, dtype=float), 6) + 0.0).astype('<f8').tobytes())
    return h.hexdigest()


def load(path=CONFIG):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def profile_of(row):
    """The converter profile of a reference model: its scenery group's visual profile (config/scenery_groups.json),
    which every converter path reads (town_regions.visual_profile shares it)."""
    from scenery_selection import load_groups
    group = load_groups()[row['group']]
    return dict(group['visual_profiles'][row['source']])


def compute(source, row):
    """{step: sha256, counts...} of one reference model from a mesh source (world_estimate_data.MeshSource)."""
    import numpy as np
    from exterior_visibility import apply_exterior_selection
    from mesh_geometry import split_surface, surface_polygons
    from mwad.scene import unpack_geometry
    from prepare_scenery import model_geometry, nif_reader
    from static_lod import reduce_for_profile
    profile = profile_of(row)
    out = {'profile': profile}
    raw, where = source.read(row['source'])
    out['source'] = hashlib.sha256(raw).hexdigest()
    out['found_in'] = where
    packet, materials, _, _ = model_geometry(raw, nif_reader(), repair_uv=True)
    vv, ff, _ = unpack_geometry(packet)
    v, f = np.array(vv, float), np.array(ff, int)
    out['geometry'] = mesh_hash(v, f)
    visible = apply_exterior_selection(f, {'materials': materials, **row.get('model_record', {})})
    out['visible'] = mesh_hash(v, visible)
    rv, rf, _ = reduce_for_profile(v, visible, profile, materials, row['source'])
    out['reduced'] = mesh_hash(rv, rf)
    texsize = profile.get('texture_size', 64)
    polys = [(patch, mat, ax, off, normal) for poly, mat, ax, off, normal in surface_polygons(rv, rf)
             for patch in split_surface(poly, np.column_stack((ax.T * texsize, off * texsize)))]
    out['faces'] = faces_hash(polys)
    out['counts'] = {'source_triangles': int(len(f)), 'visible_triangles': int(len(visible)),
                     'reduced_triangles': int(len(rf)), 'faces': len(polys)}
    return out


def check(data_files, path=CONFIG, warn=print):
    """Rebuild every reference model from data_files and compare each step with its recorded SHA-256.
    Returns the report; warnings name the model and the first step that differs."""
    from world_estimate_data import MeshSource
    source = MeshSource(data_files)
    report = {'format': 'amiwind-reference-models-check-1', 'models': []}
    for row in load(path)['models']:
        entry = {'name': row['name'], 'source': row['source']}
        try:
            got = compute(source, row)
        except FileNotFoundError:
            entry['status'] = 'source not in the data files'
            warn('WARNING: reference model %s: %s is not in your data files' % (row['name'], row['source']))
            report['models'].append(entry)
            continue
        expected = row['expected']
        first = next((s for s in STEPS if got[s] != expected['sha256'][s]), None)
        entry.update(status='ok' if first is None else 'differs at %s' % first,
                     sha256={s: got[s] for s in STEPS}, counts=got['counts'])
        if first is not None:
            warn('WARNING: REFERENCE MODEL %s DIFFERS AT STEP "%s": expected SHA-256 %s, got %s (%s)' % (
                row['name'], first, expected['sha256'][first], got[first], STEP_MEANING[first]))
        report['models'].append(entry)
    return report


STEP_MEANING = {
    'source': 'your data holds another file under this name: another edition, a patch or a replacer mod',
    'geometry': 'the mesh decoder reads the same file differently',
    'visible': 'the exterior visibility rules select other triangles',
    'reduced': 'the reducer or its parameters give another mesh',
    'faces': 'the polygon step (coplanar merge or texture extent split) gives other faces',
}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    for name in ('check', 'compute'):
        a = sub.add_parser(name)
        a.add_argument('--data-files', type=Path, required=True)
        a.add_argument('--config', type=Path, default=CONFIG)
        a.add_argument('--json', type=Path)
    a = p.parse_args(argv)
    if a.cmd == 'compute':
        from world_estimate_data import MeshSource
        source = MeshSource(a.data_files)
        out = {row['name']: compute(source, row) for row in load(a.config)['models']}
        text = json.dumps(out, indent=1, sort_keys=True)
        print(text)
        if a.json:
            a.json.write_text(text + '\n', encoding='utf-8', newline='\n')
        return 0
    report = check(a.data_files, a.config)
    if a.json:
        a.json.write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8', newline='\n')
    for m in report['models']:
        print('reference model %s: %s' % (m['name'], m['status']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
