#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Game parity tracker (GAME-PARITY-TRACKER-60): docs/game-features.json is the source, docs/GAME_FEATURES.md is
generated. The dialogue tracker's twin (tools/dialogue_features.py), over the whole base game.

Usage:
  game_features.py render     rewrite docs/GAME_FEATURES.md from the JSON
  game_features.py check      validate the JSON (schema, states, proofs, register IDs) and fail if the page is stale

One row per system of the base game: its state (done, partial, missing), what it is, the reference that decides how
it should behave (OpenMW 0.51, or a page of the UESP mirror), the proof (a test file, a document or an in-game
session), what is missing, the work items that carry the rest and the register IDs. A done or partial row names its
proof, and every tests/, docs/ or tools/ path in a proof must exist. The sub-trackers (dialogue) are read from their
own JSON, so their numbers here cannot go stale.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'docs' / 'game-features.json'
OUT = ROOT / 'docs' / 'GAME_FEATURES.md'
BUGS = ROOT / 'docs' / 'bugs' / 'bugs.json'
DIALOGUE = ROOT / 'docs' / 'dialogue-features.json'
SCHEMA = 'game-features 1'
STATES = ('done', 'partial', 'missing')
AREAS = [('world', 'World and interiors'), ('actors', 'Actors and behaviour'), ('player', 'The player'),
         ('combat', 'Combat, death and the law'), ('magic', 'Magic'), ('items', 'Items, containers and trade'),
         ('story', 'Dialogue, voices, journal and factions'), ('scripts', 'MWScript'),
         ('sound-ui', 'Sound, music and the interface')]
KEYS = {'id', 'name', 'area', 'state', 'what', 'reference', 'proof', 'missing', 'bugs', 'todo'}
REQUIRED = {'id', 'name', 'area', 'state', 'what', 'reference', 'bugs', 'todo'}
ID_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
BUG_RE = re.compile(r'^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+$')
PATH_RE = re.compile(r'\b((?:tests|docs|tools)/[A-Za-z0-9_./-]*[A-Za-z0-9_])')
GENERATED = ('<!-- Generated whole by tools/game_features.py render from docs/game-features.json; '
             'do not edit by hand. -->')
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
          'November', 'December']
MW_INTS = ('table_functions', 'carried_out', 'used_by_game', 'scripts_total', 'scripts_compile', 'scripts_run_whole')


def load(path=DATA):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def version():
    return (ROOT / 'VERSION').read_text(encoding='utf-8').strip()


def long_date(iso):
    y, m, d = (int(x) for x in iso.split('-'))
    return '%d %s %d' % (d, MONTHS[m - 1], y)


def register_ids():
    data = json.loads(BUGS.read_text(encoding='utf-8'))
    rows = data if isinstance(data, list) else data.get('bugs', [])
    return {b['id'] for b in rows if isinstance(b, dict) and 'id' in b}


def problems(doc, bug_ids=None, root=ROOT):
    """Every reason the JSON is not valid, as one line each."""
    out = []
    if doc.get('schema') != SCHEMA:
        out.append('schema must be %r' % SCHEMA)
    if not re.match(r'^\d{4}-\d\d-\d\d$', str(doc.get('updated', ''))):
        out.append('updated must be YYYY-MM-DD')
    m = doc.get('mwscript') or {}
    if any(not isinstance(m.get(k), int) for k in MW_INTS):
        out.append('mwscript needs the whole numbers %s' % ', '.join(MW_INTS))
    elif m['carried_out'] > m['table_functions'] or m['scripts_run_whole'] > m['scripts_compile'] \
            or m['scripts_compile'] > m['scripts_total']:
        out.append('mwscript: counts are out of order')
    if m.get('used_and_carried_out') is not None and not isinstance(m.get('used_and_carried_out'), int):
        out.append('mwscript.used_and_carried_out is a whole number or null (pending)')
    seen, areas = set(), {k for k, _ in AREAS}
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
        for p in PATH_RE.findall(f.get('proof') or ''):
            if not (root / p).exists():
                out.append('%s: proof names %s, which does not exist' % (fid, p))
        for t in f.get('todo', []):
            if not BUG_RE.match(t):
                out.append('%s: bad work item ID %s' % (fid, t))
        for b in f.get('bugs', []):
            if not BUG_RE.match(b):
                out.append('%s: bad register ID %s' % (fid, b))
            elif bug_ids is not None and b not in bug_ids:
                out.append('%s: register ID %s is not in docs/bugs/bugs.json' % (fid, b))
    if not doc.get('features'):
        out.append('no features')
    return out


def tally(feats):
    return {s: sum(1 for f in feats if f['state'] == s) for s in STATES}


def render(doc):
    feats = doc['features']
    total = tally(feats)
    m = doc['mwscript']
    lines = ['# Game features', '', '_Last updated with AmiWind v%s (%s)._' % (version(), long_date(doc['updated'])),
             '', GENERATED, '', doc['intro'], '',
             '**%d of %d systems done**, %d partial, %d missing.' % (total['done'], len(feats), total['partial'],
                                                                     total['missing']), '',
             '| Area | Done | Partial | Missing | Systems |', '| --- | ---: | ---: | ---: | ---: |']
    for key, title in AREAS:
        rows = [f for f in feats if f['area'] == key]
        c = tally(rows)
        lines.append('| %s | %d | %d | %d | %d |' % (title, c['done'], c['partial'], c['missing'], len(rows)))
    lines.append('| **All** | **%d** | **%d** | **%d** | **%d** |' % (total['done'], total['partial'], total['missing'],
                                                                      len(feats)))
    lines += ['', 'A row counts the system, not its size: a done row can be small and a missing one large. '
              'The references are OpenMW 0.51 for behaviour (read for the rules, nothing copied) and the pages '
              'of the UESP mirror for the original\'s numbers.', '',
              '## Measured: MWScript', '',
              '%s.' % m['source'], '',
              '| | Count |', '| --- | ---: |',
              '| Functions and instructions in the compiler\'s table | %s |' % '{:,}'.format(m['table_functions']),
              '| Carried out by the interpreter and the host | %s (%.1f %%) |'
              % ('{:,}'.format(m['carried_out']), 100.0 * m['carried_out'] / m['table_functions']),
              '| Distinct functions the game\'s scripts use (%s) | %s |' % (m['used_measured'],
                                                                           '{:,}'.format(m['used_by_game'])),
              '| Of those, carried out | %s |' % ('{:,}'.format(m['used_and_carried_out'])
                                                  if m.get('used_and_carried_out') is not None else 'used: pending'),
              '| Scripts in the three masters | %s |' % '{:,}'.format(m['scripts_total']),
              '| Scripts that compile | %s |' % '{:,}'.format(m['scripts_compile']),
              '| Scripts that run whole (%s) | %s (%.1f %%) |' % (m['scripts_measured'],
                                                                 '{:,}'.format(m['scripts_run_whole']),
                                                                 100.0 * m['scripts_run_whole'] / m['scripts_total']),
              '', m['note'], '']
    lines += ['## Sub-trackers', '', 'Each has its own source file and its own check.', '',
              '| Tracker | Headline |', '| --- | --- |']
    if DIALOGUE.is_file():
        d = tally(json.loads(DIALOGUE.read_text(encoding='utf-8'))['features'])
        n = sum(d.values())
        lines.append('| [Dialogue features](DIALOGUE_FEATURES.md) | %d of %d done, %d partial, %d missing |'
                     % (d['done'], n, d['partial'], d['missing']))
    lines += ['| [Voices and sounds](VOICE_FEATURES.md) | per kind of line, with its proof |',
              '| [CHIM features](chim/FEATURES.md) | engine features with measured gains |',
              '| [World, cell by cell](chim/CELL_TRACKER.md) | every cell converted and audited |',
              '| [CHIM progress](chim/PROGRESS_TRACKER.md) | the island by region |',
              '| [Asset coverage](ASSET_COVERAGE.md) | what of the original\'s assets is integrated |',
              '| [Older trackers](trackers/README.md) | world progress, entities and points of interest, first versions |',
              '']
    lines += ['## The systems', '']
    for key, title in AREAS:
        rows = [f for f in feats if f['area'] == key]
        lines += ['### ' + title, '', '| System | State | What | Reference | Proof | Missing | Work items | Register |',
                  '| --- | --- | --- | --- | --- | --- | --- | --- |']
        for f in rows:
            bugs = ', '.join('[%s](bugs/%s.md)' % (b, b) if (ROOT / 'docs' / 'bugs' / ('%s.md' % b)).is_file()
                             else b for b in f['bugs']) or '-'
            cells = [f['name'], f['state'], f['what'], f['reference'], f.get('proof') or '-',
                     f.get('missing') or '-', ', '.join(f['todo']) or '-', bugs]
            lines.append('| ' + ' | '.join(x.replace('|', '/').replace('\n', ' ') for x in cells) + ' |')
        lines.append('')
    return '\n'.join(lines).rstrip('\n') + '\n'


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] not in ('render', 'check'):
        print(__doc__)
        return 2
    doc = load()
    bad = problems(doc, register_ids())
    if bad:
        print('\n'.join('game features: ' + b for b in bad))
        return 1
    if argv[0] == 'render':
        OUT.write_text(render(doc), encoding='utf-8', newline='\n')
        print('wrote %s' % OUT.relative_to(ROOT))
        return 0
    if not OUT.is_file() or OUT.read_text(encoding='utf-8') != render(doc):
        print('game features: docs/GAME_FEATURES.md is stale: run tools/game_features.py render')
        return 1
    print('game features ok: %d rows' % len(doc['features']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
