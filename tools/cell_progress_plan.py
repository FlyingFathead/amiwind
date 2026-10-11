# SPDX-License-Identifier: GPL-3.0-only
"""CHIM Progress Tracker: the release plan of every cell (which release a cell is planned for, and whether it shipped).

The plan is a layer of its own: it never changes a cell's conversion or audit status, and conversion results, audits and
ingest never write it. It lives in OUT/plan.json (format aw-cell-plan-1, schema PLAN_SCHEMA) and is set only by
`cell_progress.py plan` and `cell_progress.py ship`. Every change is also one line in OUT/history.jsonl.

Per cell: {"release": "v0.0.36", "state": "planned|in_build|shipped", "since": <host time>, "source": <who/what set it>, ...}.
The record is open: any other key is kept, shown in the Toolkit's cell panel and exported to JSON, so new facts about a
plan (a district, a reason, a build name) need no code change. A plan file with a newer schema than this tool knows is
refused for writing (never silently downgraded) and read as far as it is understood.

"Upcoming" is data, not code: the next release is the lowest-numbered plan release that is not shipped. When it ships
(`ship`), the next one takes its place, so the gold colour always means "planned for the next release" and later planned
releases are drawn in a lighter gold. This is separate from releases.json (cell_progress_release.py), the owner's approval.
"""
import json
from pathlib import Path

import cell_progress_release as RL

PLAN_FORMAT = 'aw-cell-plan-1'
PLAN_SCHEMA = 1
PLAN_FILE = 'plan.json'
STATES = ('planned', 'in_build', 'shipped')
CORE_KEYS = ('release', 'state', 'since', 'source')


def version_key(v):
    return [int(x) if x.isdigit() else x for x in str(v).lstrip('v').replace('-', '.').split('.')]


def load(out):
    p = Path(out) / PLAN_FILE
    if p.is_file():
        d = json.loads(p.read_text(encoding='utf-8'))
        if d.get('format') == PLAN_FORMAT:
            d.setdefault('releases', {})
            d.setdefault('cells', {})
            d.setdefault('schema', 1)
            return d
    return {'format': PLAN_FORMAT, 'schema': PLAN_SCHEMA, 'releases': {}, 'cells': {}}


def next_release(doc):
    """The lowest-numbered plan release that has not shipped (None without a plan)."""
    open_ = [v for v, r in doc['releases'].items() if not r.get('shipped')]
    return sorted(open_, key=version_key)[0] if open_ else None


def tier(doc, release, state):
    if state == 'shipped' or (doc['releases'].get(release) or {}).get('shipped'):
        return 'shipped'
    return 'next' if release == next_release(doc) else 'later'


def resolve(cells, specs, eligible, area_cells=None, doc=None):
    """Cell keys for selectors: the release selectors of cell_progress_release plus area:NAME, build:RUN, plan:VERSION,
    state:STATE (of the plan), unplanned and @FILE (a file with whitespace-separated cell ids)."""
    out = set()
    rest = []
    plan_cells = (doc or {}).get('cells', {})
    for spec in specs:
        spec = spec.strip()
        if spec.startswith('area:'):
            found = set((area_cells or {}).get(spec[5:], ()))
            if not found:
                raise ValueError('%s: the tracker data has no cells for that area' % spec)
            out |= found
        elif spec.startswith('build:'):
            out |= {k for k, r in cells.items() if (r.get('provenance') or {}).get('build') == spec[6:]}
        elif spec.startswith('plan:'):
            out |= {k for k, e in plan_cells.items() if e.get('release') == spec[5:] and k in cells}
        elif spec.startswith('state:'):
            out |= {k for k, e in plan_cells.items() if e.get('state') == spec[6:] and k in cells}
        elif spec == 'unplanned':
            out |= {k for k, r in cells.items() if RL.usable(r) and k not in plan_cells}
        elif spec.startswith('@'):
            for item in Path(spec[1:]).read_text(encoding='utf-8').split():
                if item not in cells:
                    raise ValueError('%s: unknown cell %r' % (spec, item))
                out.add(item)
        elif spec:
            rest.append(spec)
    if rest:
        out |= set(RL.resolve(cells, rest, eligible, area_cells))
    return sorted(out)


def _write(out, doc, line):
    out = Path(out)
    doc['format'], doc['schema'] = PLAN_FORMAT, max(PLAN_SCHEMA, int(doc.get('schema', 1)))
    (out / PLAN_FILE).write_bytes((json.dumps(doc, indent=2, sort_keys=True) + '\n').encode('utf-8'))
    hist = out / 'history.jsonl'
    old = hist.read_text(encoding='utf-8') if hist.is_file() else ''
    hist.write_bytes((old + json.dumps(line, sort_keys=True, separators=(',', ':')) + '\n').encode('utf-8'))
    return out / PLAN_FILE


def _check_writable(doc):
    if int(doc.get('schema', 1)) > PLAN_SCHEMA:
        raise ValueError('plan.json has schema %s, newer than this tool (%s); update the tool' % (doc['schema'], PLAN_SCHEMA))


def record(out, release, keys, state='planned', who='owner', source=None, now=None, clear=False, extra=None,
           title=None, selector=''):
    """Plan (or with clear=True un-plan) the cells for `release`. `extra` keys are stored on each cell record, kept as given."""
    if not clear and state not in STATES:
        raise ValueError('state must be one of %s' % ', '.join(STATES))
    doc = load(out)
    _check_writable(doc)
    for k in keys:
        if clear:
            if (doc['cells'].get(k) or {}).get('release') == release:
                del doc['cells'][k]
            continue
        old = doc['cells'].get(k) or {}
        e = {x: v for x, v in old.items() if x not in CORE_KEYS}      # unknown keys survive a re-plan
        e.update(extra or {})
        same = old.get('state') == state and old.get('release') == release
        e.update({'release': release, 'state': state, 'since': old.get('since', now) if same else now, 'source': source or who})
        doc['cells'][k] = e
    rel = doc['releases'].setdefault(release, {'shipped': False})
    if title:
        rel['title'] = title
    line = {'type': 'plan', 'date': now, 'who': who, 'release': release, 'action': 'clear' if clear else 'plan',
            'state': state, 'selector': selector, 'cells': len(keys)}
    return _write(out, doc, line)


def ship(out, release, who='owner', now=None):
    """The release is published: every plan cell of it becomes shipped. Returns the number of cells flipped."""
    doc = load(out)
    _check_writable(doc)
    if release not in doc['releases']:
        raise ValueError('no plan for %s' % release)
    n = 0
    for e in doc['cells'].values():
        if e.get('release') == release and e.get('state') != 'shipped':
            e['state'], e['since'] = 'shipped', now
            n += 1
    doc['releases'][release]['shipped'] = True
    doc['releases'][release]['shipped_at'] = now
    _write(out, doc, {'type': 'plan', 'date': now, 'who': who, 'release': release, 'action': 'ship', 'cells': n})
    return n


def attach(cells, doc):
    """rec['plan'] = the record plus 'tier' (next | later | shipped), or None."""
    for k, rec in cells.items():
        e = doc['cells'].get(k)
        rec['plan'] = dict(e, tier=tier(doc, e.get('release'), e.get('state'))) if e else None


def summary(cells, doc):
    """One row per plan release (oldest first) and the unplanned rest: planned cells and how they stand today."""
    names = sorted(doc['releases'], key=version_key)
    nxt = next_release(doc)
    rows = []
    for name in names + [None]:
        mine = [r for r in cells.values() if RL.usable(r) and ((r.get('plan') or {}).get('release') == name)]
        b = [r['chim']['bucket'] for r in mine]
        row = {'release': name, 'shipped': bool(name and doc['releases'][name].get('shipped')), 'next': bool(name and name == nxt),
               'planned': len(mine), 'complete': sum(x in RL.COMPLETE_DONE for x in b),
               'awaiting_lighting': sum(x in RL.AWAITING for x in b), 'failing': sum(x in RL.FAILING for x in b),
               'hull_policy_pending': sum(x == 'hull_policy_pending' for x in b), 'not_started': sum(x == 'not_started' for x in b),
               'ocean': sum(x == 'ocean' for x in b),
               'states': {s: sum(1 for r in mine if r['plan']['state'] == s) for s in STATES} if name else {}}
        if name and doc['releases'][name].get('title'):
            row['title'] = doc['releases'][name]['title']
        rows.append(row)
    return rows
