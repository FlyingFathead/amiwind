#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Variant audit: every baked model variant of a CHIM world derives from its mesh's base.

CHIM stores a model once per variant: the placement's scale and tilt are baked into the record
(`x/ex_hlaalu_b_01@s1`, `r/siltstrider@s0.89`; docs/chim/WORLD_FORMAT.md "Model records"). Every
variant of a mesh comes from the same prepared mesh (one reduction, prepare_mesh_bsp._prepare_model),
transformed by chim.models.variant_unit, so a variant must be the base record scaled (and turned):

- shape: the same faces in the same order, each face the base face scaled by the variant's scale
  (per-face edge lengths; independent of tilt and yaw);
- topology: the same shared vertices and the same open edges (edges used by one face). A scaled
  variant with more open edges than its base has seams the base does not have
  (CHIM-STRIDER-SCALED-SEAMS-36: vertices shared at scale 1 split at scale 0.89).

The base of a mesh is its `@s1` record without tilt, flattening or visual offset, else its
smallest-scale plain record. Records with another face count come from another reduction (a
different converter profile, e.g. a CHIM region frame's open-world profile against a town's): they
are listed, not compared. Reference models (config/reference-models.json) must have one reduction:
any variant of theirs that is not the base transformed is a failure. The seam audit
(tools/seam_audit.py) measures each base reduction against the source mesh; a variant that passes
this audit has the base's seams exactly.

    python3 tools/chim/variant_audit.py OUT [--json REPORT] [--strict]
      OUT: a CHIM world (holds chim/world.cwi). Exit 1 on a failure (--strict: also on any topology
      difference of a derived variant).
"""
import argparse
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import format as F  # noqa: E402

REFERENCE_MODELS = ROOT / 'config/reference-models.json'
# a vertex pair this close is one point of the mesh stored twice (an unshared seam)
NEAR = 1e-4
# per-face edge length match: relative (single-precision storage) plus absolute
REL_TOL = 1e-4
ABS_TOL = 2e-3
NAME = re.compile(r'^(?P<stem>[^@#]+)@s(?P<scale>[0-9.e+-]+)(?P<rest>[^#]*)(?:#(?P<dup>\d+))?$')


def parse_name(name):
    """(stem, scale, plain, flattened, duplicate number) of a variant name (chim.build.variant_name)."""
    m = NAME.match(name)
    if not m:
        return name, 1.0, False, False, 0
    rest = m.group('rest')
    return (m.group('stem'), float(m.group('scale')), rest == '', '@f' in rest, int(m.group('dup') or 0))


def decode(image):
    """(vertices, faces) of a brush image: positions (n, 3) and each face's vertex indices in order."""
    import numpy as np
    lumps = F.read_brush_image(image)
    verts = np.frombuffer(lumps[3], '<f4').reshape(-1, 3).astype(float)
    edges = np.frombuffer(lumps[12], '<u2').reshape(-1, 2)
    surf = np.frombuffer(lumps[13], '<i4')
    faces = []
    for k in range(len(lumps[7]) // 20):
        _, _, first, count, _ = struct.unpack_from('<HhihH', lumps[7], 20 * k)
        faces.append([int(edges[e][0]) if e >= 0 else int(edges[-e][1]) for e in surf[first:first + count]])
    return verts, faces


def topology(verts, faces):
    """Shared vertices, open edges (used by one face) and vertex pairs closer than NEAR."""
    from collections import Counter
    from scipy.spatial import cKDTree
    use = Counter()
    for f in faces:
        for a, b in zip(f, f[1:] + f[:1]):
            use[(min(a, b), max(a, b))] += 1
    near = len(cKDTree(verts).query_pairs(NEAR, p=float('inf'))) if len(verts) > 1 else 0
    return {'vertices': int(len(verts)), 'open_edges': sum(1 for n in use.values() if n == 1),
            'near_pairs': int(near)}


def face_lengths(verts, faces):
    import numpy as np
    return [np.linalg.norm(verts[f] - verts[f[1:] + f[:1]], axis=1) for f in faces]


def congruent(base, variant, ratio):
    """Largest per-face edge length mismatch of variant against base x ratio (None: faces differ)."""
    import numpy as np
    if len(base) != len(variant):
        return None
    worst = 0.0
    for a, b in zip(base, variant):
        if len(a) != len(b):
            return None
        d = np.abs(a * ratio - b) - REL_TOL * np.maximum(a * ratio, b)
        worst = max(worst, float(d.max()))
    return worst


def reference_stems(path=REFERENCE_MODELS):
    """Mesh stems (`r/siltstrider`) of the reference models: one reduction for every variant."""
    path = Path(path)
    if not path.is_file():
        return set()
    data = json.loads(path.read_text(encoding='utf-8'))
    out = set()
    for row in data.get('models', []):
        src = row['source'].replace('\\', '/').lower()
        src = src[len('meshes/'):] if src.startswith('meshes/') else src
        out.add(src[:-4] if src.endswith('.nif') else src)
    return out


def audit_models(models, references=None):
    """models: [{'name', 'image'}] of a world. Returns the report (see module text)."""
    from collections import defaultdict
    references = reference_stems() if references is None else set(references)
    groups = defaultdict(list)
    for i, m in enumerate(models):
        stem, scale, plain, flat, dup = parse_name(m['name'])
        groups[stem].append({'id': i, 'name': m['name'], 'scale': scale, 'plain': plain, 'flattened': flat,
                             'dup': dup, 'image': m['image']})
    report = {'format': 'amiwind-variant-audit-1', 'meshes': len(groups), 'variants': len(models),
              'compared': 0, 'derived': 0, 'other_reductions': [], 'topology_differences': [], 'failures': [],
              'references': sorted(references)}
    for stem in sorted(groups):
        rows = groups[stem]
        plain = [r for r in rows if r['plain'] and not r['dup']]
        base = next((r for r in plain if r['scale'] == 1.0), None)
        if base is None:
            base = min(plain or rows, key=lambda r: (r['scale'], r['dup'], r['name']))
        bv, bf = decode(base['image'])
        blen = face_lengths(bv, bf)
        btop = topology(bv, bf)
        for r in rows:
            if r is base:
                continue
            report['compared'] += 1
            v, f = decode(r['image'])
            worst = congruent(blen, face_lengths(v, f), r['scale'] / base['scale'])
            row = {'mesh': stem, 'base': base['name'], 'variant': r['name'], 'base_faces': len(bf), 'faces': len(f)}
            if worst is None or worst > ABS_TOL:
                row['shape_mismatch'] = None if worst is None else round(worst, 6)
                if stem in references:
                    report['failures'].append(dict(row, reason='reference model variant is not its base '
                                                               'transformed (another reduction or a stale record)'))
                else:
                    report['other_reductions'].append(row)
                continue
            report['derived'] += 1
            if r['flattened']:
                continue                    # flattening moves faces apart on purpose: shape only
            top = topology(v, f)
            if top['vertices'] != btop['vertices'] or top['open_edges'] != btop['open_edges']:
                report['topology_differences'].append(dict(row, base_topology=btop, topology=top))
    return report


def audit_world(out, references=None):
    """The report of the CHIM world in OUT (OUT/chim/world.cwi and its sector files)."""
    root = Path(out) / 'chim'
    _, files, mdir, _ = F.read_index((root / 'world.cwi').read_bytes())
    models = []
    for m in mdir:
        with (root / files[m['file']]['path']).open('rb') as fh:
            fh.seek(m['offset'])
            models.append({'name': m['name'], 'image': fh.read(m['bytes'])})
    return audit_models(models, references)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('out', type=Path)
    p.add_argument('--json', type=Path)
    p.add_argument('--references', type=Path, default=REFERENCE_MODELS)
    p.add_argument('--strict', action='store_true')
    a = p.parse_args(argv)
    report = audit_world(a.out, reference_stems(a.references))
    if a.json:
        a.json.write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8', newline='\n')
    print('Variant audit: %d meshes, %d variants, %d compared with their base, %d derived exactly, '
          '%d from another reduction, %d with another topology, %d failure(s)'
          % (report['meshes'], report['variants'], report['compared'], report['derived'],
             len(report['other_reductions']), len(report['topology_differences']), len(report['failures'])))
    for row in report['topology_differences'][:20]:
        print('  TOPOLOGY %s vs %s: open edges %d -> %d, vertices %d -> %d' % (
            row['variant'], row['base'], row['base_topology']['open_edges'], row['topology']['open_edges'],
            row['base_topology']['vertices'], row['topology']['vertices']))
    for row in report['failures']:
        print('  FAIL %s vs %s: %s' % (row['variant'], row['base'], row['reason']))
    bad = report['failures'] or (a.strict and report['topology_differences'])
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
