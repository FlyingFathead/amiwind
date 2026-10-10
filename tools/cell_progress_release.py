# SPDX-License-Identifier: GPL-3.0-only
"""CHIM Progress Tracker: which cells are approved for which release (owner-set, per cell).

The release of a cell ("v0.0.33", "v0.0.34") is set by the owner through `cell_progress.py release` only and lives in
OUT/releases.json. Conversion results, audits and ingest never write it, and an ingest never loses it. Every change is
also one line in OUT/history.jsonl with the date (host clock) and who made it.
"""
import json
from pathlib import Path

RELEASE_FORMAT = 'aw-cell-release-1'
RELEASE_FILE = 'releases.json'
SHIPPED_RELEASE = 'v0.0.33'              # the release that shipped the CHIM towns
SHIPPED_AREAS = ('balmora', 'seyda')     # the CHIM towns of that release (area names of the CHIM receipt / town table)
COMPLETE_DONE = ('complete', 'terrain_complete')
AWAITING = ('complete_unlit', 'terrain_complete_unlit')
FAILING = ('converted_failing', 'not_converted')
SELECTORS = ('x,y', 'ring:N', 'status:BUCKET', 'eligible', 'unassigned', 'release:VERSION', 'shipped-towns', 'all')


def load(out):
    p = Path(out) / RELEASE_FILE
    if p.is_file():
        d = json.loads(p.read_text(encoding='utf-8'))
        if d.get('format') == RELEASE_FORMAT:
            return d
    return {'format': RELEASE_FORMAT, 'releases': {}, 'cells': {}}


def usable(rec):
    return rec.get('island') is not None and (rec['land'] or rec['chim']['bucket'] == 'empty_sea')


def resolve(cells, specs, eligible, area_cells=None):
    """Cell keys for a list of selectors (see SELECTORS) over the tracker's cells; ValueError for anything unknown."""
    out = set()
    for spec in specs:
        spec = spec.strip()
        if not spec:
            continue
        if spec in cells:
            out.add(spec)
        elif spec == 'all':
            out |= {k for k, r in cells.items() if usable(r)}
        elif spec == 'eligible':
            out |= {k for k, r in cells.items() if usable(r) and r['chim']['bucket'] in eligible}
        elif spec == 'unassigned':
            out |= {k for k, r in cells.items() if usable(r) and not r.get('release')}
        elif spec == 'shipped-towns':
            found = {k for a in SHIPPED_AREAS for k in (area_cells or {}).get(a, ())}
            if not found:
                raise ValueError('shipped-towns: the tracker data has no cells for %s (ingest the CHIM runs first)' % ', '.join(SHIPPED_AREAS))
            out |= found
        elif spec.startswith('ring:'):
            ring = int(spec[5:])
            out |= {k for k, r in cells.items() if r.get('ring') == ring and usable(r)}
        elif spec.startswith('status:'):
            out |= {k for k, r in cells.items() if r['chim']['bucket'] == spec[7:]}
        elif spec.startswith('release:'):
            out |= {k for k, r in cells.items() if (r.get('release') or {}).get('name') == spec[8:]}
        else:
            raise ValueError('unknown cell or selector %r (selectors: %s)' % (spec, ', '.join(SELECTORS)))
    return sorted(out)


def record(out, version, keys, who='owner', date=None, shipped=False, clear=False, selector=''):
    """Assign (or with clear=True remove) `version` for the cells; appends the history line. Returns the file path."""
    out = Path(out)
    doc = load(out)
    for k in keys:
        if clear:
            if (doc['cells'].get(k) or {}).get('release') == version:
                del doc['cells'][k]
        else:
            doc['cells'][k] = {'release': version, 'date': date[:10], 'who': who, 'shipped': bool(shipped)}
    rel = doc['releases'].setdefault(version, {'shipped': False})
    if shipped:
        rel['shipped'] = True
    path = out / RELEASE_FILE
    path.write_bytes((json.dumps(doc, indent=2, sort_keys=True) + '\n').encode('utf-8'))
    line = {'type': 'release', 'date': date, 'who': who, 'release': version, 'action': 'clear' if clear else 'assign',
            'selector': selector, 'cells': len(keys), 'shipped': bool(shipped)}
    hist = out / 'history.jsonl'
    old = hist.read_text(encoding='utf-8') if hist.is_file() else ''
    hist.write_bytes((old + json.dumps(line, sort_keys=True, separators=(',', ':')) + '\n').encode('utf-8'))
    return path


def attach(cells, doc):
    """rec['release'] = {name, date, who, shipped} or None, from the owner's file."""
    for k, rec in cells.items():
        e = doc['cells'].get(k)
        rec['release'] = {'name': e['release'], 'date': e.get('date'), 'who': e.get('who'), 'shipped': bool(e.get('shipped'))} if e else None


def summary(cells, doc):
    """One row per release (and the unassigned cells): approved, complete, awaiting lighting, lit, failing, pending."""
    names = sorted(doc['releases'], key=lambda v: [int(x) if x.isdigit() else x for x in v.lstrip('v').split('.')])
    rows = []
    for name in names + [None]:
        mine = [r for r in cells.values() if usable(r) and ((r.get('release') or {}).get('name') == name)]
        b = [r['chim']['bucket'] for r in mine]
        rows.append({'release': name, 'shipped': bool(name and doc['releases'][name].get('shipped')), 'approved': len(mine),
                     'complete': sum(x in COMPLETE_DONE for x in b), 'awaiting_lighting': sum(x in AWAITING for x in b),
                     'lit': sum(1 for r in mine if (r.get('lighting') or {}).get('status') == 'lit'),
                     'empty_sea': sum(x == 'empty_sea' for x in b), 'failing': sum(x in FAILING for x in b),
                     'hull_policy_pending': sum(x == 'hull_policy_pending' for x in b)})
    return rows
