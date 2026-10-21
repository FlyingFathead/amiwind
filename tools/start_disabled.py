#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Actors the original's start scripts disable at a new game (NPC-STORY-DISABLED-AT-START-42).

What the original does (base master records): a new game sets CharGenState to 1; the global script
Main (the script the game always runs; rule from OpenMW apps/openmw/mwscript/globalscripts.cpp,
GlobalScripts::addStartup) then starts the scripts named by its StartScript lines. One of them,
Startup, is the run-once script whose `ID->Disable` lines take story characters (the Dreamers, the
Dreamer Prophet, quest characters) and creatures out of the world before the player arrives. A
disabled reference only leaves the scene: its own local script keeps running, which is how a
Dreamer's script enables it once the main quest's journal reaches its index (rule from OpenMW
apps/openmw/mwworld/worldimp.cpp, World::disable / World::enable).

This module reads that list FROM THE DATA (never a hand list):

- start_scripts(): the scripts Main starts (its StartScript lines);
- disable_lines(): the unconditional `ID->Disable` lines of a script (lines inside an if block are
  conditional and are reported, not applied);
- enable_rule(): how a disabled reference comes back: its own script when that script is the simple
  journal template (`Set v to GetJournalIndex J` ... `if ( v == N )` `Enable`), every other script or
  dialogue result that names `ID->Enable`, else nothing found; anything more complex is recorded as
  unknown (it needs the script compiler, docs/ROADMAP.md game logic);
- held(): the placement filter. Mode (--start-disabled, environment AMIWIND_START_DISABLED; part of
  the resident stages' cache keys): placed (default) = every actor placed, as before; original (off by
  default, for A/B) leaves the actors the start scripts disable out of a new game and lists them with
  their enable rule.

original is the faithful mode, but AmiWind does not run the main quest's journal yet, so nothing would
enable a held actor at run time (the Dreamer Prophet and the quest characters would be gone for good).
It stays off until the runtime enable exists (the world-state record's "disabled at start" flag); the
table each resident stage writes in that mode is its input. Objects the start scripts disable (scaffolding, notes, keys) are listed but not filtered here.
"""
import hashlib
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

ENV = 'AMIWIND_START_DISABLED'
MODES = ('original', 'placed')
DEFAULT_MODE = 'placed'
SCHEMA = 'start-disabled-1'
# The global script the game always runs (OpenMW GlobalScripts::addStartup adds it before the
# master's own start scripts); a new game's run-once scripts are the ones it starts.
MAIN_SCRIPT = 'main'
ACTOR_TYPES = ('NPC_', 'CREA')
OBJECT_TYPES = ('NPC_', 'CREA', 'STAT', 'ACTI', 'CONT', 'DOOR', 'LIGH', 'MISC', 'BOOK', 'ALCH', 'APPA',
                'ARMO', 'CLOT', 'INGR', 'LOCK', 'PROB', 'REPA', 'WEAP', 'LEVC', 'LEVI')
UNKNOWN = 'unknown, needs the script compiler'

_TARGET = r'(?:"([^"]+)"|([^\s"]+))'
DISABLE = re.compile(r'^' + _TARGET + r'\s*->\s*disable$', re.I)
ENABLE_CALL = re.compile(_TARGET + r'\s*->\s*enable\b', re.I)
START = re.compile(r'^startscript[\s,]+' + _TARGET + r'$', re.I)
SET_JOURNAL = re.compile(r'^set\s+([a-z_][a-z0-9_]*)\s+to\s+getjournalindex[\s,]+' + _TARGET + r'$', re.I)
COMPARE = re.compile(r'^if\s*\(\s*(.+?)\s*(==|!=|<=|>=|<|>)\s*(-?\d+)\s*\)$', re.I)
JOURNAL_CALL = re.compile(r'^getjournalindex[\s,]+' + _TARGET + r'$', re.I)
DECLARATION = re.compile(r'^(short|long|float)\s+[a-z_][a-z0-9_]*$', re.I)


def mode():
    value = os.environ.get(ENV, '').strip() or DEFAULT_MODE
    if value not in MODES:
        raise ValueError('%s takes %s, not %r' % (ENV, ', '.join(MODES), value))
    return value


def add_option(parser):
    parser.add_argument('--start-disabled', choices=MODES, default=None,
                        help='Actors the original disables at a new game (its Startup script; '
                             'NPC-STORY-DISABLED-AT-START-42): placed (default) = every actor placed, as before; '
                             'original (off by default, A/B) leaves them out and lists them with the condition '
                             'that enables them (nothing enables them during play yet). Not given = placed. Part of the resident '
                             'stages\' cache keys (AMIWIND_START_DISABLED)')
    return parser


def export_mode(value):
    """Export the resolved mode for every converter worker (the default removes the variable)."""
    if value not in MODES:
        raise ValueError('start-disabled must be one of %s, not %r' % (', '.join(MODES), value))
    if value == DEFAULT_MODE:
        os.environ.pop(ENV, None)
    else:
        os.environ[ENV] = value
    return value


def _lines(source):
    """(number, text) of the script's statements: comments cut, blanks dropped, spaces folded."""
    rows = []
    for number, line in enumerate(source.splitlines(), 1):
        line = re.sub(r'\s+', ' ', line.split(';', 1)[0]).strip()
        if line:
            rows.append((number, line))
    return rows


def _name(match, first=1):
    return (match.group(first) or match.group(first + 1)).strip()


def _opens(line):
    return re.match(r'^if\b', line, re.I) is not None


def _closes(line):
    return re.match(r'^endif\b', line, re.I) is not None


def disable_lines(source):
    """[{id, line, conditional}] for every `ID->Disable` line of a script, in order.

    conditional: the line sits inside an if block (applied only when its condition holds; never
    applied by the builder)."""
    rows, depth = [], 0
    for number, line in _lines(source):
        if _closes(line):
            depth = max(0, depth - 1)
            continue
        if _opens(line):
            depth += 1
            continue
        match = DISABLE.match(line)
        if match:
            rows.append({'id': _name(match), 'line': number, 'conditional': depth > 0})
    return rows


def started_scripts(source):
    """The script names a script starts with StartScript, in order (any depth)."""
    names = []
    for _, line in _lines(source):
        match = START.match(line)
        if match and _name(match).casefold() not in [n.casefold() for n in names]:
            names.append(_name(match))
    return names


def enable_rule(source):
    """How a reference's own script enables it: the simple journal template, or why it is unknown.

    {'status': 'journal', 'journal': J, 'operator': op, 'value': N} when every statement is a
    declaration, `Set v to GetJournalIndex J`, a `GetDisabled` guard that only returns, or one
    `Enable` under exactly one journal comparison; {'status': 'no enable'} when the script never
    enables; else {'status': UNKNOWN, 'reason': ...}."""
    rows = _lines(source)
    if not rows or not re.match(r'^begin\s+\S+$', rows[0][1], re.I) or not re.match(r'^end\b', rows[-1][1], re.I):
        return {'status': UNKNOWN, 'reason': 'no begin/end block'}
    journal_vars, stack, found = {}, [], []
    for number, line in rows[1:-1]:
        lowered = line.casefold()
        if DECLARATION.match(line):
            continue
        match = SET_JOURNAL.match(line)
        if match:
            journal_vars[match.group(1).casefold()] = _name(match, 2)
            continue
        if _opens(line):
            match = COMPARE.match(line)
            subject = match.group(1).strip() if match else ''
            if not match or not (subject.casefold() == 'getdisabled' or subject.casefold() in journal_vars
                                 or JOURNAL_CALL.match(subject)):
                return {'status': UNKNOWN, 'reason': 'line %d: %s' % (number, line)}
            stack.append((match.group(1).strip(), match.group(2), int(match.group(3))))
            continue
        if _closes(line):
            if not stack:
                return {'status': UNKNOWN, 'reason': 'line %d: endif without if' % number}
            stack.pop()
            continue
        if lowered == 'return':
            continue
        if lowered == 'enable':
            found.append((number, list(stack)))
            continue
        return {'status': UNKNOWN, 'reason': 'line %d: %s' % (number, line)}
    if stack:
        return {'status': UNKNOWN, 'reason': 'unclosed if block'}
    if not found:
        return {'status': 'no enable'}
    if len(found) != 1:
        return {'status': UNKNOWN, 'reason': 'more than one Enable'}
    number, conditions = found[0]
    # A GetDisabled guard above the Enable is allowed only as `if ( GetDisabled == 1 )`.
    conditions = [c for c in conditions if not (c[0].casefold() == 'getdisabled' and c[1] == '==' and c[2] == 1)]
    if len(conditions) != 1:
        return {'status': UNKNOWN, 'reason': 'line %d: Enable under %d conditions' % (number, len(conditions))}
    subject, operator, value = conditions[0]
    journal = journal_vars.get(subject.casefold())
    if journal is None:
        match = JOURNAL_CALL.match(subject)
        journal = _name(match) if match else None
    if journal is None:
        return {'status': UNKNOWN, 'reason': 'line %d: Enable under "%s"' % (number, subject)}
    return {'status': 'journal', 'journal': journal, 'operator': operator, 'value': value}


def enable_callers(texts, identifier):
    """Names (of scripts or dialogue results) whose text contains `identifier->Enable`."""
    key = identifier.casefold()
    found = []
    for name, source in texts:
        for match in ENABLE_CALL.finditer(source or ''):
            if _name(match).casefold() == key:
                if name not in found:
                    found.append(name)
                break
    return found


def read_master(raw):
    """(scripts, bases, placements, dialogue) of a base master:

    scripts {casefold name: (name, text)}; bases {casefold id: (type, script name)};
    placements {casefold id: [{'cell': name or [x, y], 'reference': number}]};
    dialogue [(\"topic: <topic>\", result text)]."""
    from mwad.esm import records, subrecords, string, text, first, is_deleted
    from mwad.audit import cell_data
    scripts, bases, placements, dialogue = {}, {}, {}, []
    topic = None
    for tag, flags, payload in records(raw):
        if tag == 'SCPT':
            fields = list(subrecords(payload))
            name = string(first(fields, 'SCHD')[:32])
            if not is_deleted(flags, fields):
                scripts[name.casefold()] = (name, text(fields, 'SCTX'))
        elif tag in OBJECT_TYPES:
            fields = list(subrecords(payload))
            if not is_deleted(flags, fields):
                bases[text(fields, 'NAME').casefold()] = (tag, text(fields, 'SCRI'))
        elif tag == 'CELL':
            fields = list(subrecords(payload))
            if is_deleted(flags, fields, header_only=True):
                continue
            cell = cell_data(fields)
            where = [cell['x'], cell['y']] if not cell['flags'] & 1 else cell['name']
            for ref in cell['refs']:
                if not ref.get('deleted') and 'id' in ref:
                    placements.setdefault(ref['id'].casefold(), []).append(
                        {'cell': where, 'reference': ref['number']})
        elif tag == 'DIAL':
            topic = text(list(subrecords(payload)), 'NAME')
        elif tag == 'INFO' and topic is not None:
            result = text(list(subrecords(payload)), 'BNAM')
            if result:
                dialogue.append(('topic: ' + topic, result))
    return scripts, bases, placements, dialogue


def table(raw):
    """The disabled-at-start table of a base master (schema start-disabled-1)."""
    scripts, bases, placements, dialogue = read_master(raw)
    main = scripts.get(MAIN_SCRIPT)
    if main is None:
        raise ValueError('The master has no global script Main: no start scripts to read')
    texts = [(name, source) for name, source in scripts.values()] + dialogue
    started = [n for n in started_scripts(main[1]) if n.casefold() in scripts]
    rows, conditional = [], []
    for script in started:
        name, source = scripts[script.casefold()]
        for line in disable_lines(source):
            entry = {'id': line['id'], 'script': name, 'line': line['line']}
            if line['conditional']:
                conditional.append(entry)
                continue
            key = line['id'].casefold()
            kind, own = bases.get(key, (None, ''))
            entry['type'] = kind
            entry['placements'] = placements.get(key, [])
            rule = {'own_script': own or None}
            if own:
                own_source = scripts.get(own.casefold())
                rule.update(enable_rule(own_source[1]) if own_source else {'status': 'missing script'})
            else:
                rule['status'] = 'no script'
            rule['enabled_by'] = [n for n in enable_callers(texts, line['id'])
                                  if not own or n.casefold() != own.casefold()]
            entry['enable'] = rule
            rows.append(entry)
    return {'schema': SCHEMA, 'master_sha256': hashlib.sha256(raw).hexdigest(),
            'main_script': main[0], 'start_scripts': [scripts[s.casefold()][0] for s in started],
            'rows': rows, 'conditional_not_applied': conditional,
            'scope': 'Read from the base master only. Actors (NPC_, CREA) are filtered by held(); other '
                     'objects are listed, not filtered. AmiWind does not enable a held actor at run time yet.'}


_TABLES = {}


def table_for(data):
    """The table of the Data Files' Morrowind.esm, once per file content in this process."""
    from mwad.paths import child_ci
    path = child_ci(Path(data), 'Morrowind.esm')
    stat = path.stat()
    key = (str(path), stat.st_size, stat.st_mtime_ns)
    if key not in _TABLES:
        _TABLES[key] = table(path.read_bytes())
    return _TABLES[key]


def actor_rows(document):
    """{casefold id: row} of the actors the start scripts disable."""
    return {row['id'].casefold(): row for row in document['rows'] if row.get('type') in ACTOR_TYPES}


def enable_text(row):
    rule = row['enable']
    if rule.get('status') == 'journal':
        own = 'its script %s: journal %s %s %d' % (rule['own_script'], rule['journal'], rule['operator'], rule['value'])
    elif rule.get('own_script'):
        own = 'its script %s: %s' % (rule['own_script'], rule.get('reason') and
                                     '%s (%s)' % (rule['status'], rule['reason']) or rule['status'])
    else:
        own = 'no script of its own'
    others = rule.get('enabled_by') or []
    return own + ('; enabled by ' + ', '.join(others) if others else '')


def held(references, document, where=None, active=None):
    """(kept, held): references minus the actors the start scripts disable (mode original).

    references: placements with 'id' (and 'number'); a reference counts by its object id, as the
    original's `ID->Disable` names it. held rows carry the map, reference, id, the start script and
    line, and the enable rule. active: override the mode (None = mode() == 'original')."""
    if active is None:
        active = mode() == 'original'
    if not active:
        return list(references), []
    actors = actor_rows(document)
    kept, out = [], []
    for ref in references:
        row = actors.get(str(ref.get('id', '')).casefold())
        if row is None:
            kept.append(ref)
            continue
        out.append({**({'map': where} if where else {}), 'reference': ref.get('number'), 'id': ref['id'],
                    'type': row['type'], 'disabled_by': '%s line %d' % (row['script'], row['line']),
                    'enable': row['enable'],
                    'reason': 'disabled at a new game by the start script %s (enable: %s)' % (row['script'], enable_text(row))})
    return kept, out


def held_ids(data):
    """The casefold ids held out of a new game (empty in mode placed)."""
    if mode() != 'original':
        return set()
    return set(actor_rows(table_for(data)))


def main(argv=None):
    import argparse, json
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--data-files', required=True, type=Path)
    parser.add_argument('--out', type=Path, help='write the table as JSON here')
    args = parser.parse_args(argv)
    document = table_for(args.data_files)
    if args.out:
        args.out.write_text(json.dumps(document, indent=2) + '\n', encoding='utf-8', newline='\n')
    actors = actor_rows(document)
    print('Start scripts: %s; %d disabled references, %d actors (%d NPC, %d creature), %d conditional not applied'
          % (', '.join(document['start_scripts']), len(document['rows']), len(actors),
             sum(r['type'] == 'NPC_' for r in actors.values()), sum(r['type'] == 'CREA' for r in actors.values()),
             len(document['conditional_not_applied'])), flush=True)
    for row in actors.values():
        print('  %-28s %-4s %d placement(s); %s' % (row['id'], row['type'], len(row['placements']), enable_text(row)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
