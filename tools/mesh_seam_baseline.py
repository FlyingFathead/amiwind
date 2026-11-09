#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The seam ratchet's baseline (MESH-SEAM-METHOD-62): config/mesh-seam-baseline.json, today's known seam failures.

The bake's seam stop (npc_geometry.seam_stop, AMIWIND_MESH_SEAM_STOP=ratchet, the default) fails a model that fails
the seam check (an uncovered new opening, or a limb under 0.5 of its width) unless the model is listed here and is
no worse than its line. This tool writes the file from a sweep, so it only ever shrinks:

    mesh_seam_baseline.py write --sweep SWEEP.json [--sweep MORE.json] --reason TEXT [--date YYYY-MM-DD] [--first]
        SWEEP: rows {"kind": "npc"|"creature", "model": id, "uncovered": n, "least_width": w|null}, or a build's
        NPC library manifest / creature library records (a build with AMIWIND_MESH_SEAM_STOP=warn is the whole-game
        sweep; --first with the earlier file merges, see below). Every failing
        row is listed; a passing row is left out (a model that starts passing drops out and can never fail again
        unnoticed). Against the existing file a model may only stay the same or get better: a new failing model or
        a worse line is refused (exit 1, each named) unless --first (the first baseline) is given.
    mesh_seam_baseline.py check     the file is valid (exit 0) and prints its counts
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
PATH = ROOT / 'config' / 'mesh-seam-baseline.json'
STOP_WIDTH = 0.5


def failing(row):
    w = row.get('least_width')
    return bool(row.get('uncovered')) or (w is not None and w < STOP_WIDTH)


def lines_from(rows):
    out = {}
    for r in rows:
        key = '%s:%s' % (r['kind'], str(r['model']).strip().lower())
        if failing(r):
            out[key] = {'uncovered': int(r.get('uncovered') or 0),
                        'least_width': round(float(r['least_width']), 3) if r.get('least_width') is not None else 1.0}
    return out


def manifest_rows(manifest):
    """Sweep rows from a build's own library manifest: the NPC library ({'models': {key: {'body': {'receipt'}}}}) or
    the creature library records ({mesh: {'seam_check': {...}}}), so a build run with AMIWIND_MESH_SEAM_STOP=warn is
    the whole-game sweep."""
    rows = []
    models = manifest.get('models') if isinstance(manifest.get('models'), dict) else None
    for key, m in (models or manifest).items():
        if not isinstance(m, dict):
            continue
        r = ((m.get('body') or {}).get('receipt') or {})
        if 'uncovered_openings' in r:
            rows.append({'kind': 'npc', 'model': r.get('seam_model') or key, 'uncovered': r['uncovered_openings'],
                         'least_width': r.get('least_width')})
        elif isinstance(m.get('seam_check'), dict):
            rows.append({'kind': 'creature', 'model': key, 'uncovered': m['seam_check'].get('new', 0),
                         'least_width': None})
    return rows


def ratchet(old, new):
    """[problem text] of NEW against OLD: a model not in OLD, or one with more uncovered openings or a thinner limb."""
    bad = []
    for key, line in sorted(new.items()):
        was = old.get(key)
        if was is None:
            bad.append('%s fails and is not in the baseline' % key)
        elif line['uncovered'] > was['uncovered'] or line['least_width'] < was.get('least_width', 1.0) - 0.005:
            bad.append('%s is worse than its baseline (%s -> %s)' % (key, was, line))
    return bad


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='command', required=True)
    w = sub.add_parser('write')
    w.add_argument('--sweep', action='append', type=Path, required=True)
    w.add_argument('--reason', required=True)
    w.add_argument('--date', default='')
    w.add_argument('--first', action='store_true')
    w.add_argument('--out', type=Path, default=PATH)
    c = sub.add_parser('check')
    c.add_argument('--file', type=Path, default=PATH)
    a = p.parse_args(argv)
    from model_face_overrides import load_seam_baseline
    if a.command == 'check':
        lines = load_seam_baseline(a.file)
        kinds = {}
        for k in lines:
            kinds[k.split(':', 1)[0]] = kinds.get(k.split(':', 1)[0], 0) + 1
        print('mesh-seam-baseline: %d models %s' % (len(lines), kinds))
        return 0
    rows = []
    for s in a.sweep:
        data = json.loads(s.read_text(encoding='utf-8'))
        rows.extend(data if isinstance(data, list) else manifest_rows(data))
    new = lines_from(rows)
    old = load_seam_baseline(a.out) if a.out.is_file() else {}
    left = sorted(k for k in old if k not in new)
    if not a.first:
        bad = ratchet(old, new)
        if bad:
            print('mesh-seam-baseline: refused:\n  ' + '\n  '.join(bad))
            return 1
    import datetime
    date = a.date or datetime.date.today().isoformat()
    doc = {'schema': 1, 'date': date, 'reason': a.reason,
           'about': 'Known seam failures (npc_geometry.seam_stop ratchet): a listed model may fail as far as its line, '
                    'never further; written by tools/mesh_seam_baseline.py from a sweep, never by hand.',
           'models': {k: new[k] for k in sorted(new)}}
    a.out.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
    print('mesh-seam-baseline: %d models listed, %d left the baseline (now passing or gone)%s' % (
        len(new), len(left), (': ' + ', '.join(left[:20])) if left else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
