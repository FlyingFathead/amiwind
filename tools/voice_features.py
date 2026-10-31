#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Voices and sounds tracker: docs/voice-features.json is the source, docs/VOICE_FEATURES.md is generated.

Usage:
  voice_features.py render   rewrite docs/VOICE_FEATURES.md from docs/voice-features.json
  voice_features.py check    validate the json (schema, states, bug IDs in the register) and fail if the page is
                             stale

One row per moment kind (VOICE-COVERAGE-58): what the build maps, whether it has been heard, the proof, the bugs.
"""
import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'docs' / 'voice-features.json'
OUT = ROOT / 'docs' / 'VOICE_FEATURES.md'
SCHEMA = 'voice-features 1'
GENERATED = ('<!-- Generated whole by tools/voice_features.py render from docs/voice-features.json; '
             'do not edit by hand. -->')
STATES = {
    'heard': 'heard in a build, with its proof',
    'mapped': 'mapped and wired in the engine; not yet heard in a build',
    'in-source': 'new in source on this line; not yet in a build',
    'silent': 'the original plays it; nothing plays it here yet',
    'not-built': 'the system that plays it is not built yet',
    'silent-by-design': 'silent in the original too, with the reason',
    'out-of-scope': 'not in this release, with the reason',
}
FIELDS = ('id', 'part', 'moment', 'state', 'mapped', 'proof', 'bugs')


def register_ids():
    """Every bug ID of the register and its archives."""
    ids = set()
    for path in [ROOT / 'docs/bugs/bugs.json'] + sorted((ROOT / 'docs/bugs/archive').glob('*.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        rows = data if isinstance(data, list) else data.get('bugs', [])
        ids.update(r['id'] for r in rows if isinstance(r, dict) and 'id' in r)
    return ids


def load():
    return json.loads(DATA.read_text(encoding='utf-8'))


def problems(doc, known=None):
    """The schema's complaints, one line each."""
    out = []
    if doc.get('schema') != SCHEMA:
        out.append('schema must be %r' % SCHEMA)
    seen = set()
    known = register_ids() if known is None else known
    for n, row in enumerate(doc.get('rows', [])):
        where = 'row %d (%s)' % (n, row.get('id'))
        if sorted(row) != sorted(FIELDS):
            out.append('%s: fields must be %s' % (where, ', '.join(FIELDS)))
            continue
        if row['id'] in seen:
            out.append('%s: id used twice' % where)
        seen.add(row['id'])
        if row['state'] not in STATES:
            out.append('%s: state %r is not one of %s' % (where, row['state'], ', '.join(STATES)))
        if row['state'] == 'heard' and not row['proof']:
            out.append('%s: a heard row needs its proof' % where)
        for bug in row['bugs']:
            if bug not in known:
                out.append('%s: %s is not in the register' % (where, bug))
    return out


def render(doc, version=None, today=None):
    version = version or (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
    today = today or datetime.date.today()
    rows = doc['rows']
    counts = {s: sum(1 for r in rows if r['state'] == s) for s in STATES}
    lines = ['# Voices and sounds', '',
             '_Last updated with AmiWind v%s (%d %s %d)._' % (version, today.day, today.strftime('%B'), today.year), '',
             GENERATED, '', doc['intro'], '',
             '**%d rows:** %s.' % (len(rows), ', '.join('%d %s' % (counts[s], s) for s in STATES if counts[s])), '',
             '## Measured on the game data', '', doc['measured'], '', '## States', '']
    lines += ['- `%s`: %s' % (s, m) for s, m in STATES.items()]
    part = None
    for row in rows:
        if row['part'] != part:
            part = row['part']
            lines += ['', '## ' + part, '', '| Moment | State | Mapped | Proof | Bugs |', '| --- | --- | --- | --- | --- |']
        cells = [row['moment'], '`%s`' % row['state'], row['mapped'], row['proof'] or '-',
                 ', '.join('[%s](bugs/%s.md)' % (b, b) if (ROOT / 'docs/bugs' / (b + '.md')).exists() else b
                           for b in row['bugs']) or '-']
        lines.append('| ' + ' | '.join(c.replace('|', '/') for c in cells) + ' |')
    return '\n'.join(lines) + '\n'


def stale(doc):
    """True when the page's body (all but its Last-updated line) differs from a fresh render."""
    if not OUT.exists():
        return True
    body = lambda text: [l for l in text.splitlines() if not l.startswith('_Last updated with')]
    return body(OUT.read_text(encoding='utf-8')) != body(render(doc))


def main(argv):
    if len(argv) != 2 or argv[1] not in ('render', 'check'):
        print(__doc__)
        return 2
    doc = load()
    bad = problems(doc)
    if bad:
        print('\n'.join(bad))
        return 1
    if argv[1] == 'render':
        if stale(doc):
            OUT.write_text(render(doc), encoding='utf-8', newline='\n')
            print('wrote docs/VOICE_FEATURES.md')
        return 0
    if stale(doc):
        print('docs/VOICE_FEATURES.md stale: run tools/voice_features.py render')
        return 1
    print('voice features ok: %d rows' % len(doc['rows']))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
