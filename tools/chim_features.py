#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""CHIM feature tracker: docs/chim/features.json is the source, docs/chim/FEATURES.md is generated.

Usage:
  chim_features.py render   rewrite docs/chim/FEATURES.md from docs/chim/features.json
  chim_features.py check    validate features.json (schema, bug IDs, links and anchors) and
                            fail if FEATURES.md is stale

Every feature has an id, a name, a short summary of what it does, a status (shipped in a CHIM
version, in this release, in progress, planned or idea), the CHIM version it first appeared in,
the measured gains (figure, what was compared, how it was measured, when) or the statement that
nothing is measured yet, the visibility story (how Quake's visibility culling still works with
it), caveats, links to documents, the bug IDs and the commits it relates to.

Basis of a figure: build (builder output), count (exact engine counters), emulator (FS-UAE
timings, relative until a real Amiga has been measured), simulation (the engine's own code run
on the host), estimate, census (counts over the game's own data).
"""
import datetime
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'docs' / 'chim' / 'features.json'
OUT = ROOT / 'docs' / 'chim' / 'FEATURES.md'
BUGS = ROOT / 'docs' / 'bugs' / 'bugs.json'
SCHEMA = 'chim-features 1'
GENERATED = ('<!-- Generated whole by tools/chim_features.py render from docs/chim/features.json; '
             'do not edit by hand. -->')

STATUSES = ['shipped', 'in-release', 'in-progress', 'planned', 'idea']
STATUS_TITLES = {
    'shipped': 'Shipped in CHIM {v}',
    'in-release': 'In this release (CHIM {v})',
    'in-progress': 'In progress',
    'planned': 'Planned',
    'idea': 'Idea',
}
STATUS_SHORT = {'shipped': 'shipped', 'in-release': 'in this release', 'in-progress': 'in progress',
                'planned': 'planned', 'idea': 'ideas'}
STATUS_MEANING = {
    'shipped': 'in a published release',
    'in-release': 'in the line that becomes the next release; not yet published',
    'in-progress': 'being built or measured; not finished',
    'planned': 'decided; no finished design or code',
    'idea': 'written down, not decided',
}
AREAS = [
    ('world', 'World format and disk'),
    ('streaming', 'Streaming and memory'),
    ('rendering', 'Rendering and visibility'),
    ('characters', 'Characters'),
    ('engine', 'Engine'),
    ('builder', 'Builder and tools'),
    ('roadmap', 'Roadmap'),
]
BASES = {
    'build': 'builder output',
    'count': 'exact counts',
    'emulator': 'emulator, relative',
    'simulation': 'host simulation',
    'estimate': 'estimate',
    'census': 'census of the game data',
}
HOSTS = ['quiet', 'busy', 'mixed']
ID_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
COMMIT_RE = re.compile(r'^[0-9a-f]{7,12}$')
BUG_RE = re.compile(r'^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+$')
# Private paths and machine names never belong in the public feature page (built from parts so this
# source file itself stays clean for the release scan).
FORBIDDEN = ['c' + ':/', 'c' + ':' + chr(92), '/home/', 'users' + chr(92)]
FEATURE_KEYS = ['id', 'name', 'area', 'summary', 'status', 'version', 'gains', 'gain_short', 'gain_note',
                'caveats', 'vis', 'links', 'bugs', 'commits']
GAIN_KEYS = ['headline', 'text', 'compared', 'basis', 'host', 'date']
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September',
          'October', 'November', 'December']


def load(path=DATA):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def human_date(iso):
    d = datetime.date.fromisoformat(iso)
    return '%d %s %d' % (d.day, MONTHS[d.month - 1], d.year)


def anchor(heading):
    text = re.sub(r'[^\w\- ]', '', heading.strip().lower())
    return text.replace(' ', '-')


def anchors(path):
    seen, out, in_code = {}, set(), False
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        if line.startswith('```'):
            in_code = not in_code
        if in_code:
            continue
        m = re.match(r'#{1,6} (.+)$', line)
        if m:
            a = anchor(m.group(1))
            n = seen.get(a, 0)
            out.add(a if n == 0 else '%s-%d' % (a, n))
            seen[a] = n + 1
    return out


def bug_ids(root=ROOT):
    return {b['id'] for b in json.loads((root / 'docs' / 'bugs' / 'bugs.json').read_text(encoding='utf-8'))}


def chim_version(root=ROOT):
    return (root / 'CHIM_VERSION').read_text(encoding='utf-8').strip()


def _text(v):
    return isinstance(v, str) and v.strip() == v and v != ''


def _strings_ok(obj, where, problems):
    if isinstance(obj, dict):
        for k, v in obj.items():
            _strings_ok(v, '%s.%s' % (where, k), problems)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _strings_ok(v, '%s[%d]' % (where, i), problems)
    elif isinstance(obj, str):
        low = obj.lower()
        for bad in FORBIDDEN:
            if bad in low:
                problems.append('%s: contains %r, which must not appear in public docs' % (where, bad))
        if '\r' in obj or '\n' in obj:
            problems.append('%s: contains a line break' % where)
        if '|' in obj:
            problems.append('%s: contains "|", which breaks the tables' % where)


def problems_of(data, root=ROOT):
    """Every problem found in the data; an empty list means it is valid."""
    problems = []
    if data.get('schema') != SCHEMA:
        problems.append('schema must be %r' % SCHEMA)
    version = data.get('chim_version')
    if version != chim_version(root):
        problems.append('chim_version %r does not match CHIM_VERSION %r' % (version, chim_version(root)))
    try:
        datetime.date.fromisoformat(data.get('updated', ''))
    except ValueError:
        problems.append('updated must be an ISO date')
    feats = data.get('features')
    if not isinstance(feats, list) or not feats:
        return problems + ['features must be a non-empty list']
    bugs = bug_ids(root)
    ids, names, anchor_cache = set(), set(), {}
    for n, f in enumerate(feats):
        where = 'feature %s' % (f.get('id') if isinstance(f, dict) and f.get('id') else '#%d' % n)
        if not isinstance(f, dict):
            problems.append('%s: must be an object' % where)
            continue
        for k in f:
            if k not in FEATURE_KEYS:
                problems.append('%s: unknown field %r' % (where, k))
        for k in ('id', 'name', 'area', 'summary', 'status', 'vis'):
            if not _text(f.get(k)):
                problems.append('%s: %s must be a non-empty text' % (where, k))
        _strings_ok(f, where, problems)
        fid = f.get('id', '')
        if not ID_RE.match(fid) or len(fid) > 40:
            problems.append('%s: id must be lower-case words joined by hyphens, at most 40 characters' % where)
        if fid in ids:
            problems.append('%s: duplicate id' % where)
        ids.add(fid)
        name = f.get('name', '')
        if anchor(name) in names:
            problems.append('%s: name gives the same heading anchor as another feature' % where)
        names.add(anchor(name))
        if f.get('area') not in dict(AREAS):
            problems.append('%s: area must be one of %s' % (where, ', '.join(a for a, _ in AREAS)))
        if len(f.get('summary', '')) > 480:
            problems.append('%s: summary is longer than 480 characters' % where)
        status = f.get('status')
        if status not in STATUSES:
            problems.append('%s: status must be one of %s' % (where, ', '.join(STATUSES)))
        fv = f.get('version')
        if status in ('shipped', 'in-release'):
            if not _text(fv):
                problems.append('%s: a %s feature needs a version' % (where, status))
            elif status == 'in-release' and fv != version:
                problems.append('%s: an in-release feature has the current CHIM version %s' % (where, version))
        elif fv is not None:
            problems.append('%s: version must be null for %s' % (where, status))
        gains = f.get('gains')
        if not isinstance(gains, list):
            problems.append('%s: gains must be a list' % where)
            gains = []
        for i, g in enumerate(gains):
            gw = '%s gain %d' % (where, i + 1)
            if not isinstance(g, dict):
                problems.append('%s: must be an object' % gw)
                continue
            for k in g:
                if k not in GAIN_KEYS:
                    problems.append('%s: unknown field %r' % (gw, k))
            for k in ('text', 'compared'):
                if not _text(g.get(k)):
                    problems.append('%s: %s must be a non-empty text' % (gw, k))
            if g.get('basis') not in BASES:
                problems.append('%s: basis must be one of %s' % (gw, ', '.join(BASES)))
            if 'host' in g and g['host'] not in HOSTS:
                problems.append('%s: host must be one of %s' % (gw, ', '.join(HOSTS)))
            if g.get('basis') == 'emulator' and 'host' not in g:
                problems.append('%s: an emulator figure must say whether the host was quiet, busy or mixed' % gw)
            if 'headline' in g and not isinstance(g['headline'], bool):
                problems.append('%s: headline must be true or false' % gw)
            try:
                datetime.date.fromisoformat(g.get('date', ''))
            except ValueError:
                problems.append('%s: date must be an ISO date' % gw)
        if gains and not _text(f.get('gain_short')):
            problems.append('%s: gain_short (the figure for the status tables) is required when gains exist' % where)
        if not gains and not _text(f.get('gain_note')):
            problems.append('%s: a feature without measured gains needs a gain_note saying why' % where)
        if 'gain_short' in f and not gains:
            problems.append('%s: gain_short without gains' % where)
        if status in ('planned', 'idea') and any(g.get('headline') for g in gains if isinstance(g, dict)):
            problems.append('%s: a %s feature cannot have a headline figure' % (where, status))
        caveats = f.get('caveats')
        if not isinstance(caveats, list) or not all(_text(c) for c in caveats):
            problems.append('%s: caveats must be a list of texts' % where)
        for i, link in enumerate(f.get('links') or []):
            lw = '%s link %d' % (where, i + 1)
            if not isinstance(link, dict) or not _text(link.get('title')) or not _text(link.get('path')):
                problems.append('%s: needs a title and a path' % lw)
                continue
            rel, _, frag = link['path'].partition('#')
            target = root / rel
            if not target.is_file():
                problems.append('%s: %s does not exist' % (lw, rel))
            elif frag:
                if target.suffix != '.md':
                    problems.append('%s: only Markdown files have anchors' % lw)
                else:
                    if target not in anchor_cache:
                        anchor_cache[target] = anchors(target)
                    if frag not in anchor_cache[target]:
                        problems.append('%s: %s has no heading #%s' % (lw, rel, frag))
        if not f.get('links'):
            problems.append('%s: at least one link is required' % where)
        for b in f.get('bugs') or []:
            if not isinstance(b, str) or not BUG_RE.match(b):
                problems.append('%s: bad bug id %r' % (where, b))
            elif b not in bugs:
                problems.append('%s: bug %s is not in the bug register' % (where, b))
            elif not (root / 'docs' / 'bugs' / (b + '.md')).is_file():
                problems.append('%s: bug %s has no report page' % (where, b))
        for c in f.get('commits') or []:
            if not isinstance(c, str) or not COMMIT_RE.match(c):
                problems.append('%s: commit %r must be a short hash of 7 to 12 hex digits' % (where, c))
    return problems


def status_title(status, version):
    return STATUS_TITLES[status].format(v=version)


def figure_label(g):
    parts = [BASES[g['basis']]]
    if g.get('host'):
        parts.append('%s host' % g['host'])
    parts.append(human_date(g['date']))
    return ', '.join(parts)


def feature_link(f):
    return '[%s](#%s)' % (f['name'], anchor(f['name']))


def doc_path(path):
    """Link target of a repository-relative path, as seen from docs/chim/."""
    rel, _, frag = path.partition('#')
    target = os.path.relpath(rel, 'docs/chim').replace(os.sep, '/')
    return target + ('#' + frag if frag else '')


def render(data):
    feats = data['features']
    version = data['chim_version']
    lines = ['# CHIM feature tracker', '', GENERATED, '']
    lines += [
        'What the [CHIM engine](README.md) has done for AmiWind, feature by feature: what each feature does, '
        'where it stands, the gain that was measured (what was compared, how and when) and how Quake\'s '
        'visibility culling still works with it. Generated from [`features.json`](features.json); a test '
        'fails when this page is stale. Bugs are on the [CHIM bug tracker](../bugs/CHIM_TRACKER.md); '
        'ideas and held-back work are collected in [CHIM ideas](IDEAS.md). How far the open world has been '
        'converted, cell by cell, is on the [CHIM cell tracker](CELL_TRACKER.md).',
        '',
    ]
    counts = {s: sum(1 for f in feats if f['status'] == s) for s in STATUSES}
    parts = ['%d %s' % (counts[s], STATUS_SHORT[s]) for s in STATUSES if counts[s]]
    lines += ['CHIM version: %s. %d features: %s. Updated %s.' % (version, len(feats), ', '.join(parts),
                                                                   human_date(data['updated'])), '']
    lines += ['## What CHIM has done so far', '']
    heads = [(f, g) for f in feats for g in f['gains'] if g.get('headline')]
    lines += ['The headline measured gains. Each links to its feature, which says what was compared. '
              'Emulator figures are relative until a frame has been measured on a real accelerated Amiga.', '']
    for f, g in heads:
        lines.append('- **%s:** %s. *%s.* [Details](#%s)' % (f['name'], g['text'], figure_label(g),
                                                              anchor(f['name'])))
    lines += ['']
    lines += ['Several features also have a cost, listed under their caveats: CHIM leaves less of the Hunk free '
              'at the load peak, spends more time outside the 3D view and draws slightly more spans. '
              'CHIM 0.1.0 is not published yet; the features marked "in this release" are in the '
              'development line for AmiWind v0.0.33.', '']
    lines += ['## Features by status', '']
    lines += ['| Status | Meaning | Features |', '| --- | --- | --- |']
    for s in STATUSES:
        lines.append('| %s | %s | %d |' % (status_title(s, version), STATUS_MEANING[s], counts[s]))
    lines += ['']
    area_title = dict(AREAS)
    for s in STATUSES:
        group = [f for f in feats if f['status'] == s]
        if not group:
            continue
        lines += ['### %s' % status_title(s, version), '', '| Feature | Area | What it does | Measured gain |',
                  '| --- | --- | --- | --- |']
        for f in group:
            gain = f['gain_short'] if f['gains'] else 'not measured'
            lines.append('| %s | %s | %s | %s |' % (feature_link(f), area_title[f['area']], f['summary'], gain))
        lines += ['']
    lines += ['## Features', '']
    for key, title in AREAS:
        group = [f for f in feats if f['area'] == key]
        if not group:
            continue
        lines += ['### %s' % title, '']
        for f in group:
            lines += ['#### %s' % f['name'], '']
            lines += ['**Status:** %s. **ID:** `%s`.' % (status_title(f['status'], version), f['id']), '']
            lines += [f['summary'], '']
            if f['gains']:
                lines += ['**Measured gain:**', '']
                for g in f['gains']:
                    lines.append('- %s. Compared: %s. *%s.*' % (g['text'], g['compared'], figure_label(g)))
                lines += ['']
                if f.get('gain_note'):
                    lines += [f['gain_note'], '']
            else:
                note = f['gain_note']
                lead = '' if note.startswith('Not measured') else 'Not measured. '
                lines += ['**Measured gain:** %s%s' % (lead, note), '']
            lines += ['**Visibility:** %s' % f['vis'], '']
            if f['caveats']:
                lines += ['**Caveats:**', '']
                lines += ['- %s' % c for c in f['caveats']]
                lines += ['']
            links = ['[%s](%s)' % (l['title'], doc_path(l['path'])) for l in f['links']]
            lines += ['**Read more:** ' + '; '.join(links) + '.', '']
            if f['bugs']:
                lines += ['**Bugs:** ' + ', '.join('[%s](../bugs/%s.md)' % (b, b) for b in f['bugs']) + '.', '']
            if f['commits']:
                lines += ['**Commits:** ' + ', '.join('`%s`' % c for c in f['commits']) + '.', '']
    while lines and lines[-1] == '':
        lines.pop()
    return '\n'.join(lines) + '\n'


def write(path, text):
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)


def check(root=ROOT):
    data = load(root / 'docs' / 'chim' / 'features.json')
    problems = problems_of(data, root)
    if not problems:
        out = root / 'docs' / 'chim' / 'FEATURES.md'
        if not out.is_file() or out.read_bytes() != render(data).encode('utf-8'):
            problems.append('docs/chim/FEATURES.md is stale: run tools/chim_features.py render')
    return problems


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1 or argv[0] not in ('render', 'check'):
        print(__doc__)
        return 2
    if argv[0] == 'render':
        data = load()
        problems = problems_of(data)
        if problems:
            print('\n'.join(problems))
            return 1
        write(OUT, render(data))
        print('wrote %s (%d features)' % (OUT.relative_to(ROOT), len(data['features'])))
        return 0
    problems = check()
    if problems:
        print('\n'.join(problems))
        return 1
    print('CHIM feature tracker is valid and up to date')
    return 0


if __name__ == '__main__':
    sys.exit(main())
