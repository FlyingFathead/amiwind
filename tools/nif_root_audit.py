#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Island-wide audit of NIF root transforms (MESH-EBONHEART-DRAGON-PEDESTAL-42).

Lists every placed model whose root transform the game's rule (nif_common.scenery_root_local, rule from OpenMW
file components/nif/node.cpp: a root NiNode loses its whole transform, any other root keeps it) treats differently
from the converter's previous rule ('morrowind': rotation dropped, translation and scale kept), with the shift of
the model and its placements (exterior and interior) in the master. A model listed here was drawn moved (the
Ebonheart dragon statue 327 units up, off its plaza) by every build before the repair.

  nif_root_audit.py --data-files DIR [--out FILE.json]
"""
import argparse
import io
import json
import struct
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import numpy as np
from mwad.audit import BSA, normpath, records, string, subrecords
from mwad.paths import child_ci
from nif_common import first_record, root_local, scenery_root_local

PLACEABLE = ('ACTI', 'ALCH', 'APPA', 'ARMO', 'BOOK', 'CLOT', 'CONT', 'DOOR', 'INGR', 'LIGH', 'LOCK', 'MISC', 'PROB',
             'REPA', 'STAT', 'WEAP')


def root_change(raw, N):
    """None when the game's root rule and the previous rule give the same root transform, else
    {'root', 'type', 'translation', 'scale', 'rotation', 'shift'} (shift: the previous rule's origin minus the
    game's, in NIF units)."""
    data = N.Data()
    data.read(io.BytesIO(raw))
    if not data.roots or not isinstance(data.roots[0], N.NiAVObject):
        return None
    root = data.roots[0]
    local = np.array(root.get_transform().as_list(), dtype=float)
    game = scenery_root_local(local, root, N, first_record(data, root))
    before = root_local(local, 'morrowind')
    if np.allclose(game, before, atol=1e-4):
        return None
    scale = float(np.linalg.norm(local[0, :3]))
    return {'root': root.name.decode('cp1252', 'replace'), 'type': type(root).__name__,
            'translation': [round(float(v), 2) for v in local[3, :3]], 'scale': round(scale, 4),
            'rotation': not np.allclose(local[:3, :3] / (scale or 1), np.eye(3), atol=1e-4),
            'shift': [round(float(v), 2) for v in before[3, :3] - game[3, :3]]}


def placements(master):
    """{model path: Counter(exterior=n, interior=n)} of every placed reference whose object has a model."""
    models = {}
    for tag, flags, payload in records(master):
        if tag not in PLACEABLE:
            continue
        fields = {}
        for key, value in subrecords(payload):
            fields.setdefault(key, value)
        if 'NAME' in fields and 'MODL' in fields and string(fields['MODL']).strip():
            models[string(fields['NAME']).casefold()] = normpath('meshes/' + string(fields['MODL']))
    counts = {}
    for tag, flags, payload in records(master):
        if tag != 'CELL':
            continue
        interior = None
        in_ref = False
        for key, value in subrecords(payload):
            if key == 'DATA' and interior is None and len(value) == 12:
                interior = bool(struct.unpack_from('<I', value)[0] & 1)
            elif key == 'FRMR':
                in_ref = True
            elif key == 'NAME' and in_ref:
                in_ref = False
                model = models.get(string(value).casefold())
                if model:
                    counts.setdefault(model, Counter())['interior' if interior else 'exterior'] += 1
    return counts


def audit(data_files):
    from prepare_scenery import bsa_read, nif_reader
    N = nif_reader()
    data_files = Path(data_files)
    bsa = BSA(child_ci(data_files, 'Morrowind.bsa'))
    counts = placements(child_ci(data_files, 'Morrowind.esm').read_bytes())
    rows, unreadable = [], []
    for model in sorted(counts):
        try:
            change = root_change(bsa_read(bsa, model), N)
        except Exception as exc:  # a model the converter cannot read either; named, never silent
            unreadable.append({'model': model, 'error': str(exc)[:200]})
            continue
        if change:
            rows.append(dict(change, model=model, exterior=counts[model]['exterior'],
                             interior=counts[model]['interior']))
    rows.sort(key=lambda r: -max(abs(v) for v in r['shift']))
    return {'format': 'AmiWind NIF root audit 1', 'placed_models': len(counts), 'changed_models': len(rows),
            'changed_placements': {'exterior': sum(r['exterior'] for r in rows),
                                   'interior': sum(r['interior'] for r in rows)},
            'unreadable': unreadable, 'models': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--data-files', type=Path, required=True)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    report = audit(args.data_files)
    text = json.dumps(report, indent=1) + '\n'
    if args.out:
        args.out.write_text(text, encoding='utf-8', newline='\n')
    for r in report['models']:
        print('%-42s %-10s shift %s  exterior %d interior %d' % (r['model'], r['type'], r['shift'], r['exterior'],
                                                               r['interior']))
    print('%d of %d placed models change (%d exterior, %d interior placements); %d unreadable' % (
        report['changed_models'], report['placed_models'], report['changed_placements']['exterior'],
        report['changed_placements']['interior'], len(report['unreadable'])))


if __name__ == '__main__':
    main()
