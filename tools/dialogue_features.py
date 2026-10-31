#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Dialogue feature tracker (DIALOGUE-COMPLETE-58): docs/dialogue-features.json is the source,
docs/DIALOGUE_FEATURES.md is generated. The CHIM feature tracker's twin (tools/chim_features.py).

Usage:
  dialogue_features.py render              rewrite docs/DIALOGUE_FEATURES.md from the JSON
  dialogue_features.py check               validate the JSON (schema, states, register IDs) and fail if the page is stale
  dialogue_features.py measure REPORT      take the measured counts from a dialogue table report (tools/dialogue_lut.py
                                           --report, or the image step's dialogue-table.json: its coverage block)
  dialogue_features.py blocking            list the rows that are not done and carry no written deferral (the release
                                           guard's question); exit 1 when there are any

One row per part of the original's dialogue: its state (done, partial, missing), what it is, the proof (a test, a
gate, an in-game still), what is missing, its register IDs and, when the maintainer deferred it, the deferral in
his words with its date.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'docs' / 'dialogue-features.json'
OUT = ROOT / 'docs' / 'DIALOGUE_FEATURES.md'
BUGS = ROOT / 'docs' / 'bugs' / 'bugs.json'
SCHEMA = 'dialogue-features 1'
STATES = ('done', 'partial', 'missing')
AREAS = [('conversation', 'The conversation'), ('conditions', 'Conditions'), ('disposition', 'Disposition'),
         ('window', 'The window'), ('scripts', 'Result scripts'), ('journal', 'The journal'),
         ('persuasion', 'Persuasion and Fight'), ('services', 'Services'), ('speakers', 'Speakers and add-ons'),
         ('voice', 'Voice'), ('verification', 'Verification')]
KEYS = {'id', 'name', 'area', 'state', 'what', 'proof', 'missing', 'bugs', 'deferral'}
REQUIRED = {'id', 'name', 'area', 'state', 'what', 'bugs'}
ID_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
BUG_RE = re.compile(r'^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+$')
GENERATED = ('<!-- Generated whole by tools/dialogue_features.py render from docs/dialogue-features.json; '
             'do not edit by hand. -->')
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
          'November', 'December']


def load(path=DATA):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def version():
    return (ROOT / 'VERSION').read_text(encoding='utf-8').strip()


def long_date(iso):
    y, m, d = (int(x) for x in iso.split('-'))
    return '%d %s %d' % (d, MONTHS[m - 1], y)


def problems(doc, bug_ids=None):
    """Every reason the JSON is not valid, as one line each."""
    out = []
    if doc.get('schema') != SCHEMA:
        out.append('schema must be %r' % SCHEMA)
    if not re.match(r'^\d{4}-\d\d-\d\d$', str(doc.get('updated', ''))):
        out.append('updated must be YYYY-MM-DD')
    m = doc.get('measured') or {}
    for block, keys in (('conditions', ('total', 'live', 'start_value', 'never')),
                        ('answers', ('total', 'unconditional', 'reachable', 'unreachable'))):
        b = m.get(block) or {}
        if any(not isinstance(b.get(k), int) for k in keys):
            out.append('measured.%s needs the whole numbers %s' % (block, ', '.join(keys)))
    c, a = m.get('conditions') or {}, m.get('answers') or {}
    if all(isinstance(c.get(k), int) for k in ('total', 'live', 'start_value', 'never')) and \
            c['live'] + c['start_value'] + c['never'] != c['total']:
        out.append('measured.conditions: live + start_value + never != total')
    if all(isinstance(a.get(k), int) for k in ('total', 'reachable', 'unreachable')) and \
            a['reachable'] + a['unreachable'] != a['total']:
        out.append('measured.answers: reachable + unreachable != total')
    seen = set()
    areas = {k for k, _ in AREAS}
    for f in doc.get('features', []):
        fid = f.get('id', '?')
        if set(f) - KEYS:
            out.append('%s: unknown keys %s' % (fid, sorted(set(f) - KEYS)))
        if REQUIRED - set(f):
            out.append('%s: missing keys %s' % (fid, sorted(REQUIRED - set(f))))
        if not ID_RE.match(fid) or fid in seen:
            out.append('%s: id must be lower-case words with dashes, once' % fid)
        seen.add(fid)
        if f.get('area') not in areas:
            out.append('%s: area must be one of %s' % (fid, sorted(areas)))
        if f.get('state') not in STATES:
            out.append('%s: state must be one of %s' % (fid, STATES))
        if f.get('state') in ('done', 'partial') and not f.get('proof'):
            out.append('%s: a done or partial row names its proof' % fid)
        if f.get('state') == 'partial' and not f.get('missing'):
            out.append('%s: a partial row says what is missing' % fid)
        if f.get('state') == 'done' and f.get('missing'):
            out.append('%s: a done row has nothing missing' % fid)
        d = f.get('deferral')
        if d is not None and (not isinstance(d, dict) or not d.get('words') or
                              not re.match(r'^\d{4}-\d\d-\d\d$', str(d.get('date', '')))):
            out.append('%s: a deferral holds the maintainer\'s words and its date' % fid)
        for b in f.get('bugs', []):
            if not BUG_RE.match(b):
                out.append('%s: bad register ID %s' % (fid, b))
            elif bug_ids is not None and b not in bug_ids:
                out.append('%s: register ID %s is not in docs/bugs/bugs.json' % (fid, b))
    if not doc.get('features'):
        out.append('no features')
    return out


def register_ids():
    data = json.loads(BUGS.read_text(encoding='utf-8'))
    rows = data if isinstance(data, list) else data.get('bugs', [])
    return {b['id'] for b in rows if isinstance(b, dict) and 'id' in b}


def render(doc):
    feats = doc['features']
    count = {s: sum(1 for f in feats if f['state'] == s) for s in STATES}
    m = doc['measured']
    c, a = m['conditions'], m['answers']
    lines = ['# Dialogue features', '', '_Last updated with AmiWind v%s (%s)._' % (version(), long_date(doc['updated'])),
             '', GENERATED, '',
             'What of the original\'s dialogue AmiWind does, row by row, against the original and OpenMW 0.51. '
             + doc['requirement'], '',
             '**%d of %d done**, %d partial, %d missing.' % (count['done'], len(feats), count['partial'],
                                                             count['missing']), '',
             '## Measured on the game data', '',
             '%s.' % m['source'], '',
             '| | Count | Share |', '| --- | ---: | ---: |']
    for label, value, total in (('Run-time conditions read live', c['live'], c['total']),
                                ('read their start-of-game value', c['start_value'], c['total']),
                                ('that never pass', c['never'], c['total']),
                                ('Answers that can be said', a['reachable'], a['total']),
                                ('that can never be said', a['unreachable'], a['total']),
                                ('with no run-time condition', a['unconditional'], a['total'])):
        lines.append('| %s | %s | %.1f %% |' % (label, '{:,}'.format(value), 100.0 * value / max(1, total)))
    for title, key in (('Never pass', 'functions_never'), ('Start value', 'functions_start_value')):
        if m.get(key):
            lines += ['', '%s: %s.' % (title, ', '.join('%s %s' % (k, '{:,}'.format(v)) for k, v in m[key].items()))]
    lines += ['', '## The parts', '']
    for key, title in AREAS:
        rows = [f for f in feats if f['area'] == key]
        if not rows:
            continue
        lines += ['### ' + title, '', '| Part | State | What | Proof | Missing | Register |',
                  '| --- | --- | --- | --- | --- | --- |']
        for f in rows:
            state = f['state'] + (' (deferred %s: %s)' % (long_date(f['deferral']['date']), f['deferral']['words'])
                                  if f.get('deferral') else '')
            bugs = ', '.join('[%s](bugs/%s.md)' % (b, b) if (ROOT / 'docs' / 'bugs' / ('%s.md' % b)).is_file()
                             else b for b in f['bugs']) or '-'
            cells = [f['name'], state, f['what'], f.get('proof') or '-', f.get('missing') or '-', bugs]
            lines.append('| ' + ' | '.join(x.replace('|', '/').replace('\n', ' ') for x in cells) + ' |')
        lines.append('')
    return '\n'.join(lines).rstrip('\n') + '\n'


def blocking(doc):
    return [f['id'] for f in doc['features'] if f['state'] != 'done' and not f.get('deferral')]


def measure(doc, report_path):
    cov = json.loads(Path(report_path).read_text(encoding='utf-8'))['coverage']
    c, a = cov['conditions'], cov['answers']
    doc['measured'].update({
        'conditions': {'total': c['live'] + c['start_value'] + c['never'], 'live': c['live'],
                       'start_value': c['start_value'], 'never': c['never']},
        'answers': {k: a[k] for k in ('total', 'unconditional', 'reachable', 'unreachable')},
        'functions_never': cov['functions_never'], 'functions_start_value': cov['functions_start_value']})
    return doc


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] not in ('render', 'check', 'measure', 'blocking'):
        print(__doc__)
        return 2
    doc = load()
    if argv[0] == 'measure':
        if len(argv) != 2:
            print('measure REPORT')
            return 2
        doc = measure(doc, argv[1])
        DATA.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
        argv = ['render']
    bad = problems(doc, register_ids())
    if bad:
        print('\n'.join('dialogue features: ' + b for b in bad))
        return 1
    if argv[0] == 'render':
        OUT.write_text(render(doc), encoding='utf-8', newline='\n')
        print('wrote %s' % OUT.relative_to(ROOT))
        return 0
    if argv[0] == 'blocking':
        rows = blocking(doc)
        print('\n'.join(rows) if rows else 'none')
        return 1 if rows else 0
    if not OUT.is_file() or OUT.read_text(encoding='utf-8') != render(doc):
        print('dialogue features: docs/DIALOGUE_FEATURES.md is stale: run tools/dialogue_features.py render')
        return 1
    print('dialogue features ok: %d rows' % len(doc['features']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
