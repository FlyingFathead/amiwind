# SPDX-License-Identifier: GPL-3.0-only
"""The project's reference progress file: what a release publishes so you can compare your own build with it.

`cell_progress.py publish` writes docs/chim/cell-progress-reference.json from the tracker data: per cell its ID, name (as in
the public docs), status, lighting state, ring, release and each audit's result, plus a few size figures. Nothing else:
no assets, textures, meshes, audit detail text, bug text, build or machine names, paths or notes. The World Map loads it
next to your own progress (Compare layer: same / better / worse per cell). `check-reference` scans the file.
"""
import json
import re

REFERENCE_FORMAT = 'aw-cell-reference-1'
# Built from parts on purpose: the build cache reads every path-like string of a stage's modules as an input, and the CHIM
# stage reaches this module through cell_progress; a published reference file is not an input of any build stage.
REFERENCE_PATH = '/'.join(('docs', 'chim', 'cell-progress-reference.json'))
CELL_KEYS = ('name', 'status', 'lighting', 'ring', 'island', 'release', 'audits', 'stats')
STAT_KEYS = ('records.refs_total', 'faces.chim_placed', 'bytes.chim', 'chunks.count')
# Status order for the compare layer (higher = further along). Empty sea is as good as it gets.
RANK = {'not_started': 0, 'not_converted': 1, 'converted_failing': 2, 'hull_policy_pending': 3, 'converted_unmeasured': 3,
        'audits_passed': 4, 'playtested': 4, 'approved': 4, 'terrain_complete_unlit': 5, 'terrain_complete': 6,
        'complete_unlit': 6, 'complete': 7, 'empty_sea': 7}
PRIVATE = (re.compile(r'\b[A-Za-z]:[\\/]'), re.compile(r'(^|[\s"(`])/(vol|src|out|owned|trk|met|perf|work|input)\b'),
           re.compile(r'amiwind-[a-z0-9-]*-\d{3}'), re.compile(r'@[a-z0-9.-]+\.[a-z]{2,}', re.I))


def dotted(d, name):
    for part in name.split('.'):
        if not isinstance(d, dict) or part not in d:
            return None
        d = d[part]
    return d


def build(doc):
    cells = {}
    for k, c in sorted(doc['cells'].items()):
        if c.get('island') is None or not (c['land'] or c['chim']['bucket'] == 'empty_sea'):
            continue
        row = {'name': c.get('name') or c.get('region'), 'status': c['chim']['bucket'], 'ring': c.get('ring'), 'island': c['island'],
               'lighting': (c.get('lighting') or {}).get('status'), 'release': (c.get('release') or {}).get('name')}
        if c['chim']['converted']:
            row['audits'] = {m: a['status'] for m, a in sorted(c['audits'].items()) if a['status'] != 'not_measured'}   # absent = not measured
            row['stats'] = {s: dotted(c.get('stats') or {}, s) for s in STAT_KEYS if dotted(c.get('stats') or {}, s) is not None}
        cells[k] = row
    return {'format': REFERENCE_FORMAT, 'generated': doc.get('generated'), 'headline': {
                i['name']: {'cells': i['cells'], 'done': i['done']} for i in doc['headline'].get('islands', [])},
            'rank': RANK, 'cells': cells}


def dumps(ref):
    """JSON with one cell per line (readable diffs, small file)."""
    one = lambda v: json.dumps(v, sort_keys=True, separators=(',', ':'))
    head = ['%s: %s' % (one(k), one(v)) for k, v in sorted(ref.items()) if k != 'cells']
    cells = ['%s: %s' % (one(k), one(v)) for k, v in sorted(ref['cells'].items())]
    return '{\n' + ',\n'.join(head + ['"cells": {\n' + ',\n'.join(cells) + '\n}']) + '\n}\n'


def check(text):
    """Problems of a reference file: wrong format, a key outside the allow-list, private-looking content."""
    problems = []
    try:
        ref = json.loads(text)
    except ValueError as e:
        return ['not JSON: %s' % e]
    if ref.get('format') != REFERENCE_FORMAT:
        problems.append('format is not %s' % REFERENCE_FORMAT)
    for k, c in ref.get('cells', {}).items():
        extra = set(c) - set(CELL_KEYS)
        if extra:
            problems.append('cell %s has keys outside the allow-list: %s' % (k, sorted(extra)))
            break
    for i, ln in enumerate(text.splitlines(), 1):
        if any(p.search(ln) for p in PRIVATE):
            problems.append('line %d looks private: %s' % (i, ln.strip()[:80]))
            break
    return problems


def compare(mine, ref):
    """{cell: 'same'|'better'|'worse'|'new'|'missing'} for two documents' cells (mine: tracker cells, ref: reference cells)."""
    out = {}
    for k, r in ref['cells'].items():
        m = mine.get(k)
        if m is None:
            out[k] = 'missing'
            continue
        a, b = RANK.get(m['chim']['bucket'], 0), RANK.get(r['status'], 0)
        out[k] = 'same' if a == b else 'better' if a > b else 'worse'
    return out
