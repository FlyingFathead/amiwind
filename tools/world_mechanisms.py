#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The census of the game's world mechanisms (TRAPS-WHEN-OPENED-63, WORLD-BUTTONS-62), counted from the masters' records.

1. MECHANISMS: every activator (ACTI) whose script moves, turns, enables, disables, locks, unlocks or activates
   ANOTHER object it names ("ex_gg_portcullis_01"->MoveWorld z 70): the Ghostgate switches, the steam valves of the
   Red Mountain strongholds, levers, wheels, buttons. Each row: the master, the activator's id and name, its script,
   whether the player works it (the script reads OnActivate), the cells it is placed in, what it acts on, and the
   script's state in the MWScript tracker (docs/mwscript-features.json: runs, or what keeps it from running).
2. TRAPS: every placed door and container that names a trap spell (the reference's TNAM), counted by master, by kind
   (load door, hinged door, container) and by spell.

The script text is read only for the calls; nothing of it is written out (ids, counts and states only).

  world_mechanisms.py --data-files DIR [--features docs/mwscript-features.json] [--json OUT] [--markdown OUT]
"""
import argparse
import json
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mwad.esm import records, subrecords, string, is_deleted  # noqa: E402

MASTERS = ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm')
# what a call does to the object it names (OpenMW 0.53 mwscript transformationextensions.cpp, miscextensions.cpp)
VERBS = {'moveworld': 'moves', 'move': 'moves', 'setpos': 'moves', 'setatstart': 'moves', 'positioncell': 'moves',
         'rotate': 'turns', 'rotateworld': 'turns', 'setangle': 'turns',
         'enable': 'enables', 'disable': 'disables', 'lock': 'locks', 'unlock': 'unlocks',
         'activate': 'activates', 'playgroup': 'animates', 'loopgroup': 'animates'}
_CALL = re.compile(r'(?:"([^"]+)"|\b([A-Za-z0-9_\-]+))\s*->\s*(%s)\b' % '|'.join(sorted(VERBS, key=len, reverse=True)),
                   re.I)
_ONACTIVATE = re.compile(r'\bonactivate\b', re.I)
PLACED_SHOWN = 4          # cells named per row; the rest counted


def _text(data):
    return string(data, errors='replace')


def calls(text):
    """[(verb, target)] of a script's text: the calls on a named object, in order, each pair once (comments
    dropped). TARGET folded."""
    out = []
    for line in text.splitlines():
        line = line.split(';', 1)[0]
        for m in _CALL.finditer(line):
            pair = (VERBS[m.group(3).casefold()], (m.group(1) or m.group(2)).casefold())
            if pair not in out:
                out.append(pair)
    return out


def cell_label(head):
    """A CELL's label: the interior's name, or the exterior's name (or region) with its grid."""
    data = head.get('DATA', b'')
    flags, gx, gy = struct.unpack('<Iii', data) if len(data) == 12 else (0, 0, 0)
    name = _text(head.get('NAME', b''))
    if flags & 1:
        return name
    return '%s (%d, %d)' % (name or _text(head.get('RGNN', b'')) or 'Wilderness', gx, gy)


def read_master(raw, master):
    """One master's records: {'bases': {folded id: (tag, id, name, folded script)}, 'scripts': {folded id: (id, text)},
    'refs': [{'master', 'number', 'id' (folded), 'cell', 'trap', 'door' (1 load door)}]}."""
    bases, scripts, refs, deleted = {}, {}, [], set()
    for tag, flags, payload in records(raw):
        if tag == 'SCPT':
            parts = list(subrecords(payload)); s = dict(parts)
            ident = _text(s.get('SCHD', b'')[:32])
            if is_deleted(flags, parts):
                deleted.add(('SCPT', ident.casefold())); continue
            scripts[ident.casefold()] = (ident, (s.get('SCTX') or b'').decode('cp1252', 'replace'))
        elif tag in ('ACTI', 'DOOR', 'CONT'):
            parts = list(subrecords(payload)); s = dict(parts)
            ident = _text(s.get('NAME', b''))
            if is_deleted(flags, parts):
                deleted.add(('BASE', ident.casefold())); continue
            bases[ident.casefold()] = (tag, ident, _text(s.get('FNAM', b'')), _text(s.get('SCRI', b'')).casefold())
        elif tag == 'CELL':
            parts = list(subrecords(payload))
            if is_deleted(flags, parts, header_only=True):
                continue
            head, ref = {}, None
            for t, data in parts:
                if t == 'FRMR':
                    ref = {'master': master, 'number': struct.unpack('<I', data)[0], 'id': '', 'trap': '', 'door': 0}
                    refs.append(ref)
                elif t == 'MVRF':
                    ref = None
                elif ref is None:
                    head.setdefault(t, data)
                elif t == 'NAME':
                    ref['id'] = _text(data).casefold()
                elif t == 'TNAM':
                    ref['trap'] = _text(data)
                elif t == 'DODT':
                    ref['door'] = 1
                elif t == 'DELE':
                    ref['deleted'] = True
            label = cell_label(head)
            for r in refs:
                r.setdefault('cell', label)
    return {'bases': bases, 'scripts': scripts, 'refs': [r for r in refs if not r.get('deleted')], 'deleted': deleted}


def merge(masters):
    """The masters in load order (MASTERS: [(name, read_master result)]): the last master's record of an id wins;
    every master's placements kept."""
    bases, scripts, owner, refs = {}, {}, {}, []
    for name, m in masters:
        for kind, ident in m['deleted']:
            (scripts if kind == 'SCPT' else bases).pop(ident, None)
        for k, v in m['bases'].items():
            bases[k] = v; owner[('BASE', k)] = name
        for k, v in m['scripts'].items():
            scripts[k] = v; owner[('SCPT', k)] = name
        refs.extend(m['refs'])
    return bases, scripts, owner, refs


def feature_states(path):
    """{folded script id: state} of the MWScript tracker (docs/mwscript-features.json); {} without it."""
    if not path or not Path(path).is_file():
        return {}
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    rows = data.get('scripts') or data.get('rows') or []
    out = {}
    for row in rows:
        if isinstance(row, dict) and row.get('id'):
            out[row['id'].casefold()] = (row.get('state') or '') + (': ' + row['why'] if row.get('why') else '')
    return out


def census(masters, states=None):
    """The report of MASTERS ([(name, read_master result)]) with the tracker's STATES."""
    states = states or {}
    bases, scripts, owner, refs = merge(masters)
    placed = {}
    for r in refs:
        placed.setdefault(r['id'], []).append(r['cell'])
    rows = []
    for key in sorted(bases):
        tag, ident, name, script = bases[key]
        if tag != 'ACTI' or not script or script not in scripts:
            continue
        sid, text = scripts[script]
        acts = [(v, t) for v, t in calls(text) if t != key]
        if not any(v != 'animates' for v, _ in acts):
            continue
        cells = sorted(set(placed.get(key, [])))
        state = states.get(script, 'not in the tracker')
        rows.append({'master': owner[('BASE', key)], 'id': ident, 'name': name, 'script': sid,
                     'player': bool(_ONACTIVATE.search(text)), 'placed': len(placed.get(key, [])), 'cells': cells,
                     'acts': ['%s %s' % (v, t) for v, t in acts], 'state': state,
                     'runs': state.split(':', 1)[0] == 'runs'})
    traps = {'references': 0, 'by_master': {}, 'by_kind': {}, 'by_spell': {}}
    for r in refs:
        if not r['trap']:
            continue
        base = bases.get(r['id'])
        if not base or base[0] not in ('DOOR', 'CONT'):
            continue
        kind = 'container' if base[0] == 'CONT' else 'load door' if r['door'] else 'hinged door'
        traps['references'] += 1
        for field, value in (('by_master', r['master']), ('by_kind', kind), ('by_spell', r['trap'].casefold())):
            traps[field][value] = traps[field].get(value, 0) + 1
    summary = {}
    for row in rows:
        s = summary.setdefault(row['master'], {'activators': 0, 'player_worked': 0, 'runs': 0})
        s['activators'] += 1; s['player_worked'] += row['player']; s['runs'] += row['runs']
    return {'schema': 'world-mechanisms 1', 'masters': [n for n, _ in masters], 'summary': summary,
            'mechanisms': rows, 'traps': traps}


def load(data_files, masters=MASTERS):
    out = []
    for name in masters:
        path = next((p for p in Path(data_files).iterdir() if p.name.casefold() == name.casefold()), None)
        if path is not None:
            out.append((name, read_master(path.read_bytes(), name)))
    return out


def _cell(text):
    return text.replace('|', '/')


ACTS_SHOWN = 6            # objects named per row in the page; the rest counted


def acts_text(acts):
    """'what it does to whom' of a row's ACTS ('verb target'), grouped by object: "door_a (turns), wall (disables,
    moves)", at most ACTS_SHOWN objects named."""
    order, verbs = [], {}
    for a in acts:
        verb, target = a.split(' ', 1)
        if target not in verbs:
            order.append(target); verbs[target] = []
        if verb not in verbs[target]:
            verbs[target].append(verb)
    text = ', '.join('%s (%s)' % (t, ', '.join(verbs[t])) for t in order[:ACTS_SHOWN])
    if len(order) > ACTS_SHOWN:
        text += ' and %d more' % (len(order) - ACTS_SHOWN)
    return text


def markdown(report, version='', date=''):
    """docs/WORLD_MECHANISMS.md from REPORT (plain: ids, counts, states)."""
    lines = ['# World mechanisms', '']
    if version:
        lines += ['_Last updated with AmiWind v%s (%s)._' % (version, date), '']
    lines += ['The objects in the world that the player works to change something else: switches, levers, wheels, '
              'valves and buttons whose script moves, turns, enables, disables, locks, unlocks or activates another '
              'object, and the doors and containers that carry a trap spell. Counted from the game\'s masters by '
              '`tools/world_mechanisms.py`; the state of each script is the MWScript tracker\'s '
              '(docs/mwscript-features.json, docs/MWSCRIPT_FEATURES.md). An object that only animates itself, or sets '
              'a global that another object\'s script reads, is not counted here.', '',
              'Masters read: ' + ', '.join(report['masters']) + '.', '', '## Summary', '',
              '| Master | Activators acting on another object | Worked by the player (OnActivate) | Scripts that run |',
              '|---|---:|---:|---:|']
    for m in report['masters']:
        s = report['summary'].get(m, {'activators': 0, 'player_worked': 0, 'runs': 0})
        lines.append('| %s | %d | %d | %d |' % (m, s['activators'], s['player_worked'], s['runs']))
    t = report['traps']
    lines += ['', '## Traps', '',
              'A door or container with a trap spell casts it on the one who opens it without disarming it first; the '
              'trap is used up when it is sprung, and the door\'s or container\'s key disarms it (the rule OpenMW '
              'follows). Trapped references: %d.' % t['references'], '',
              '| Kind | References |', '|---|---:|']
    lines += ['| %s | %d |' % (k, n) for k, n in sorted(t['by_kind'].items())]
    lines += ['', '| Master | References |', '|---|---:|']
    lines += ['| %s | %d |' % (k, n) for k, n in sorted(t['by_master'].items())]
    lines += ['', '| Trap spell | References |', '|---|---:|']
    lines += ['| %s | %d |' % (_cell(k), n) for k, n in sorted(t['by_spell'].items(), key=lambda kv: (-kv[1], kv[0]))]
    for m in report['masters']:
        rows = [r for r in report['mechanisms'] if r['master'] == m]
        if not rows:
            continue
        lines += ['', '## %s' % m, '',
                  '| Activator | Name | Script | Player | Placed in | Acts on | State |', '|---|---|---|---|---|---|---|']
        for r in rows:
            cells = ', '.join(_cell(c) for c in r['cells'][:PLACED_SHOWN])
            if len(r['cells']) > PLACED_SHOWN:
                cells += ' and %d more' % (len(r['cells']) - PLACED_SHOWN)
            lines.append('| %s | %s | %s | %s | %s | %s | %s |' % (
                _cell(r['id']), _cell(r['name']) or '-', _cell(r['script']), 'yes' if r['player'] else 'no',
                cells or 'not placed', _cell(acts_text(r['acts'])), _cell(r['state'])))
    return '\n'.join(lines) + '\n'


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--data-files', type=Path, required=True)
    p.add_argument('--features', type=Path, default=Path(__file__).resolve().parents[1] / 'docs/mwscript-features.json')
    p.add_argument('--json', type=Path)
    p.add_argument('--markdown', type=Path)
    p.add_argument('--version', default='')
    p.add_argument('--date', default='')
    a = p.parse_args(argv)
    print('=== PHASE 1/2: reading the masters ===', flush=True)
    masters = load(a.data_files)
    print('=== PHASE 2/2: the census ===', flush=True)
    report = census(masters, feature_states(a.features))
    if a.json:
        a.json.write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8', newline='\n')
    if a.markdown:
        a.markdown.write_text(markdown(report, a.version, a.date), encoding='utf-8', newline='\n')
    print('mechanisms: %d activators; traps: %d references %s' % (
        len(report['mechanisms']), report['traps']['references'], json.dumps(report['traps']['by_kind'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
