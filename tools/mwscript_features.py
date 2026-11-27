#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""MWScript feature tracker (MWSCRIPT-COVERAGE-62): docs/mwscript-features.json is the source, docs/MWSCRIPT_FEATURES.md
is generated. The game parity tracker's twin (tools/game_features.py), one row per script record of the game.

Usage:
  mwscript_features.py measure --data-files DIR [--image-build RUN]
                                                  read the masters and compile them as the builder does
                                                  (tools/mwscript), write docs/mwscript-features.json, render the page;
                                                  RUN = the build whose image's add-on districts and rooms count
  mwscript_features.py render                     recompute every row's state against the interpreter's current
                                                  function table (tools/mwscript/functions.py), rewrite the JSON's
                                                  states and docs/MWSCRIPT_FEATURES.md
  mwscript_features.py check                      validate the JSON and fail if a state or the page is stale, or if a
                                                  function the scripts call has no effect class
                                                  (config/mwscript-effects.json: full, part or none in play, with
                                                  what is missing, how it is known: source, test or play, and what
                                                  was seen in play), if an effect row is stale against the register
                                                  (docs/bugs/bugs.json: an entry about the function that the row
                                                  does not name, or a fix step newer than the one the row was
                                                  checked against), or if a script listed as not used can run

measure needs the game data (run it in the builder container: the masters are read there and nothing of their text
is written; the JSON keeps record ids, counts and function names only). render and check need only the repository.

One row per script record (the winning record of each id over Morrowind, Tribunal and Bloodmoon): its master, its
area (the region of its placed references; an interior takes the region its doors lead out to), what names it
(the records that carry it and their placed references per master, levelled lists, the start scripts, StartScript in
other scripts and in dialogue results), every function it calls and every function its conditions test, and our
state:
  runs               compiles whole, and the build attaches or starts it; or it calls no function at all, so it only
                     sets its own locals, which the dialogue keeps on the speaker without it (MWSCRIPT-COMPLETE-LANDMARK)
  carried            an AmiWind adaptation: AmiWind's own code does the script's work, feature complete, every step
                     of the script carried out (config/mwscript-counterparts.json, each step "same")
  adaptation-gap     AmiWind's own code does it, but a step of the script is missing or different: a gap, never
                     counted as an adaptation (MWSCRIPT-EFFECT-PARITY-69)
  missing-function   calls a function the interpreter does not carry out yet (it compiles; those calls read 0)
  attached-not-run   the game attaches it, but the build does not run it: a hand-written rule carries it
                     (config/mwscript.json), or nothing it does is seen yet (left out of the file)
  not-attached       compiles whole, but nothing in the build attaches or starts it
  not-in-image       its records are placed (or made by the scripts) only in cells of an add-on's world (Mournhold,
                     Solstheim) that the image does not carry; the districts, rooms and add-on exterior cells (its
                     stores' frames) the measured build's image holds count as carried (measure --image-build,
                     TRACKERS-MOURNHOLD-NOT-COUNTED-67, EXPANSION-SCRIPTS-NOT-ATTACHED-66)
  inert              nothing names it (no record, no start, no StartScript, no dialogue), or its records are never
                     placed in any world and nothing makes them (refs made_by: the masters of the scripts whose Place
                     call names one): it never runs in the original either
  not-converted      does not compile
A script whose records are never placed runs when the build attaches it at run time (MWSCRIPT-UNPLACED-ATTACH-62, as
OpenMW 0.51 does): an item's script while the player carries one, an actor's script on the actor a levelled list gives,
an object's script on the object a script places (PlaceAtPC, PlaceAtMe, PlaceItem, PlaceItemCell).
"""
import argparse
from collections import Counter
import json
import re
import struct
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'src', ROOT / 'tools'):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from mwscript.functions import FUNCTIONS, HOST  # noqa: E402
from mwscript import dialogue_combat  # noqa: E402
from mwscript import gamedata  # noqa: E402

DATA = ROOT / 'docs' / 'mwscript-features.json'
OUT = ROOT / 'docs' / 'MWSCRIPT_FEATURES.md'
SCHEMA = 'mwscript-features 1'
# 'carried' is the AmiWind adaptation (the key is kept: older data and other tools read it): AmiWind's own code does
# the script's work and every step of the script is carried out. 'adaptation-gap': own code does it, but a step of the
# script is missing or different, so it is a gap, not an adaptation (MWSCRIPT-EFFECT-PARITY-69).
STATES = ('runs', 'carried', 'adaptation-gap', 'missing-function', 'attached-not-run', 'not-attached', 'not-in-image',
          'inert', 'not-converted')
LABELS = {'runs': 'runs', 'carried': 'AmiWind adaptation',
          'adaptation-gap': 'AmiWind\'s own code, steps open',
          'missing-function': 'uses a function the interpreter lacks',
          'attached-not-run': 'attached, not run', 'not-attached': 'compiled, not attached',
          'not-in-image': 'only in an add-on world', 'inert': 'named by nothing', 'not-converted': 'not converted'}
SHORT = {'runs': 'Runs', 'carried': 'Adaptation', 'adaptation-gap': 'Own code, steps open',
         'missing-function': 'Function missing', 'attached-not-run': 'Attached, not run',
         'not-attached': 'Not attached', 'not-in-image': 'Add-on world', 'inert': 'Named by nothing',
         'not-converted': 'Not converted'}
# the states that count as done: the script's work happens in the game as the original's does
DONE_STATES = ('runs', 'carried')
# the record types the player can carry (tools/mwscript/awms.py CARRIED: their scripts run while carried, PADD rows)
CARRIED = ('ALCH', 'APPA', 'ARMO', 'BOOK', 'CLOT', 'INGR', 'LIGH', 'LOCK', 'MISC', 'PROB', 'REPA', 'WEAP')
MASTERS = ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm')
ADDON_AREA = {'Tribunal.esm': 'mournhold (tribunal)', 'Bloodmoon.esm': 'solstheim (bloodmoon)'}
GLOBAL_AREA, DIALOGUE_AREA, UNPLACED_AREA, NOBODY_AREA = ('global scripts', 'dialogue only', 'records not placed',
                                                          'named by nothing')
REF_KINDS = ('ACTI', 'ALCH', 'APPA', 'ARMO', 'BOOK', 'CLOT', 'CONT', 'CREA', 'DOOR', 'INGR', 'LIGH', 'LOCK', 'MISC',
             'NPC_', 'PROB', 'REPA', 'WEAP', 'STAT')
KIND_NAMES = {'ACTI': 'activator', 'ALCH': 'potion', 'APPA': 'apparatus', 'ARMO': 'armour', 'BOOK': 'book',
              'CLOT': 'clothing', 'CONT': 'container', 'CREA': 'creature', 'DOOR': 'door', 'INGR': 'ingredient',
              'LIGH': 'light', 'LOCK': 'lockpick', 'MISC': 'item', 'NPC_': 'NPC', 'PROB': 'probe', 'REPA': 'repair tool',
              'STAT': 'static'}
GENERATED = ('<!-- Generated whole by tools/mwscript_features.py render from docs/mwscript-features.json; '
             'do not edit by hand. -->')
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
          'November', 'December']
CELL = 8192.0


def load(path=DATA):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def long_date(iso):
    y, m, d = (int(x) for x in iso.split('-'))
    return '%d %s %d' % (d, MONTHS[m - 1], y)


# --- the state of one row, from what was measured and the interpreter's function table of today ---

_HOST_THEN = set(HOST)    # the host functions when the data was measured (use(doc) sets it from the JSON)


def use(doc):
    """Read the measurement's own list of host functions (the JSON's measured.host) before any state is worked out."""
    global _HOST_THEN
    _HOST_THEN = set(doc['measured'].get('host', HOST))
    return doc


def missing_now(names):
    """The measured not-yet calls that are still not carried out: a function the table runs now drops out. A function
    that was already a host function when measured stays: its call was not handed to the host then (a Cast of a spell
    the host does not carry), so that use is not covered until the next measurement."""
    out = []
    for n in names:
        fn = FUNCTIONS.get(n)
        if fn is None or not fn.run or (n in HOST and n in _HOST_THEN):
            out.append(n)
    return sorted(set(out))


COUNTERPARTS = ROOT / 'config' / 'mwscript-counterparts.json'
VERDICTS = ('same', 'partial', 'different')
_counterparts = None


def counterparts(path=None):
    """{folded script id: entry} of config/mwscript-counterparts.json (v0.0.63): the scripts AmiWind's own code
    carries, with the counterpart and the parity check; {} when the file is missing."""
    global _counterparts
    if path is not None or _counterparts is None:
        p = Path(path) if path else COUNTERPARTS
        doc = json.loads(p.read_text(encoding='utf-8')) if p.exists() else {'entries': []}
        found = {e['script'].casefold(): e for e in doc.get('entries', [])}
        if path is not None:
            return found
        _counterparts = found
    return _counterparts


def open_steps(entry):
    """The steps of a counterpart entry that are not the same as the script's (partial or different): with one, the
    script is no AmiWind adaptation but a gap."""
    return [s for s in (entry or {}).get('steps') or () if s.get('verdict') != 'same']


def is_adaptation(entry):
    """An AmiWind adaptation: own code does the script's work, with every step of the script carried out."""
    return bool(entry) and bool(entry.get('steps')) and not open_steps(entry) and entry.get('verdict') == 'same'


def counterpart_problems(doc):
    """What the counterparts tracker refuses: an entry without a counterpart file and function, a verdict outside
    VERDICTS, a step without its four fields, an in-game check left empty, and an entry called the same as its script
    while one of its steps is not (an adaptation has no open step)."""
    out = []
    for e in doc.get('entries', []):
        if e.get('verdict') == 'same' and open_steps(e):
            out.append('%s: called the same as the script, but %d of its steps are not: an AmiWind adaptation has no '
                       'open step' % (e.get('script') or '?', len(open_steps(e))))
        if e.get('verdict') in VERDICTS and e.get('verdict') != 'same' and e.get('steps') and not open_steps(e):
            out.append('%s: every step is the same, but the entry is not called the same' % (e.get('script') or '?'))
    if doc.get('schema') != 'mwscript-counterparts 1':
        out.append('schema is not mwscript-counterparts 1')
    for e in doc.get('entries', []):
        sid = e.get('script') or '?'
        cp = e.get('counterpart') or {}
        if not cp.get('file') or not cp.get('function'):
            out.append('%s: no counterpart file and function' % sid)
        if e.get('verdict') not in VERDICTS:
            out.append('%s: verdict must be one of %s' % (sid, ', '.join(VERDICTS)))
        if not e.get('what') or not e.get('ingame'):
            out.append('%s: what it does and the in-game check are needed' % sid)
        for s in e.get('steps') or [None]:
            if not s or any(not s.get(k) for k in ('step', 'original', 'amiwind', 'verdict')) or \
                    s.get('verdict') not in VERDICTS:
                out.append('%s: every step needs step, original, amiwind and a verdict' % sid)
                break
        if not isinstance(e.get('register'), list):
            out.append('%s: register is a list' % sid)
    for e in doc.get('functions', []):
        names = ', '.join(e.get('functions') or ['?'])
        cp = e.get('counterpart') or {}
        if not e.get('functions') or not cp.get('file') or not cp.get('function') or e.get('verdict') not in VERDICTS \
                or not e.get('what') or not e.get('ingame') or not isinstance(e.get('register'), list):
            out.append('functions %s: functions, what, counterpart file and function, a verdict, the in-game check '
                       'and register are needed' % names)
    return out


def counterpart_functions():
    """The functions AmiWind's own code carries (config/mwscript-counterparts.json "functions", v0.0.63)."""
    p = COUNTERPARTS
    return json.loads(p.read_text(encoding='utf-8')).get('functions', []) if p.exists() else []


def counterparts_section():
    """The "AmiWind adaptations" section: per script its counterpart, whether it is an adaptation (every step the
    same) or own code with open steps, the in-game check, register IDs and the step table."""
    entries = sorted(counterparts().values(), key=lambda e: e['script'].casefold())
    if not entries:
        return []
    out = ['## AmiWind adaptations', '',
           'The game scripts whose work AmiWind\'s own code does instead of running them, each with the code that '
           'does it and a step-by-step comparison with the script (the tracker of these is '
           'config/mwscript-counterparts.json, checked by its test). A script is an **AmiWind adaptation** only when '
           'it is feature complete: every step the original\'s script does is carried out. With a step that is '
           'missing or different it is not an adaptation but a gap, counted as "%s", and its open steps are listed '
           'under its name below. Of the %d scripts here, %d are adaptations and %d have open steps. Decided for the '
           'project: the opening from the prison ship to the census office is AmiWind\'s own implementation.' % (
               LABELS['adaptation-gap'], len(entries), sum(1 for e in entries if is_adaptation(e)),
               sum(1 for e in entries if not is_adaptation(e))), '',
           '| Script | What it does | AmiWind counterpart | State | Open steps | Seen in play | Register |',
           '| --- | --- | --- | --- | ---: | --- | --- |']
    for e in entries:
        out.append('| %s | %s | %s %s | %s | %d | %s | %s |' % (
            e['script'], _cell(e['what']), e['counterpart']['file'], _cell(e['counterpart']['function']),
            LABELS['carried'] if is_adaptation(e) else LABELS['adaptation-gap'], len(open_steps(e)),
            _cell(e['ingame']), ', '.join(e['register']) or '-'))
    out.append('')
    funcs = counterpart_functions()
    if funcs:
        out += ['Functions whose work AmiWind\'s own code does (the script calls into it):', '',
                '| Functions | What | AmiWind counterpart | Parity | Note | In game |',
                '| --- | --- | --- | --- | --- | --- |']
        out += ['| %s | %s | %s %s | %s | %s | %s |' % (', '.join(e['functions']), _cell(e['what']),
                                                        e['counterpart']['file'], _cell(e['counterpart']['function']),
                                                        e['verdict'], _cell(e.get('note', '')), _cell(e['ingame']))
                for e in funcs]
        out.append('')
    console = json.loads(COUNTERPARTS.read_text(encoding='utf-8')).get('console', []) if COUNTERPARTS.exists() else []
    cfile = ROOT / 'config' / 'mwscript-console.json'
    if console and cfile.exists():   # MW-CONSOLE-COMMANDS-62: the original's console commands (v0.0.63)
        rows = json.loads(cfile.read_text(encoding='utf-8'))['commands']
        n = {s: sum(1 for r in rows if r['state'] == s) for s in ('alias', 'vm', 'collision', 'planned', 'not applicable')}
        out += ['The original game\'s console commands (docs/CONSOLE_COMMANDS_MORROWIND.md): %d in all; %d run AmiWind\'s '
                'own command, %d run through the script interpreter\'s host, %d are AmiWind\'s own names (kept), %d '
                'planned, %d not applicable. The aliases:' % (len(rows), n['alias'], n['vm'], n['collision'],
                                                             n['planned'], n['not applicable']), '',
                '| Original | AmiWind | Parity | Note |', '| --- | --- | --- | --- |']
        out += ['| %s | %s | %s | %s |' % (', '.join(c['original']), _cell(c['amiwind']), c['verdict'], _cell(c['note']))
                for c in console]
        out.append('')
    for e in entries:
        out += ['### %s' % e['script'], '', '| Step | Original | AmiWind | Same? |', '| --- | --- | --- | --- |']
        out += ['| %s | %s | %s | %s |' % (_cell(s['step']), _cell(s['original']), _cell(s['amiwind']), s['verdict'])
                for s in e['steps']]
        out.append('')
    return out


def state_of(row):
    """(state, why) of one script row."""
    if row['error']:
        return 'not-converted', 'does not compile'
    main = row.get('id', '').casefold() == gamedata.MAIN_SCRIPT
    if row['handwritten'] or main:
        c = counterparts().get(row.get('id', '').casefold())
        if c:
            where = '%s %s' % (c['counterpart']['file'], c['counterpart']['function'])
            if main:
                where += ' (the game always runs it, OpenMW GlobalScripts::addStartup)'
            if is_adaptation(c):
                return 'carried', 'an AmiWind adaptation: %s does every step of the script' % where
            gaps = open_steps(c)
            return 'adaptation-gap', '%s does it, but %d of its %d steps %s not as the script: %s' % (
                where, len(gaps), len(c.get('steps') or ()), 'is' if len(gaps) == 1 else 'are',
                '; '.join(s['step'] for s in gaps))
        if main:
            return 'adaptation-gap', ('the game always runs it (OpenMW GlobalScripts::addStartup); AmiWind\'s own '
                                      'code does part of it, and no step-by-step comparison is recorded')
        return 'attached-not-run', 'a hand-written rule carries it'
    game = row['refs']
    started = row['start'] or row['started_by'] or game['dialogue_starts']
    if not (started or row['bound'] or row.get('held') or game['records']):
        # named by nothing: it never runs in the original either, so a function it lacks keeps nothing from running
        return 'inert', 'nothing names it: it never runs in the original either'
    made = game.get('made_by')
    if made is not None and not (started or row['bound'] or row.get('held') or game['levelled'] or made or
                                 any(game['placed'].values()) or set(game['records']) & set(CARRIED)):
        # MWSCRIPT-COMPLETE-LANDMARK: its records are never placed in any world, no list gives them, nothing holds them
        # and no script or dialogue result places one: they never exist in the original either
        return 'inert', 'its records are never placed and nothing makes them: it never runs in the original either'
    missing = missing_now(row['notyet'])
    if missing:
        return 'missing-function', '%d not carried out: %s' % (len(missing), ', '.join(missing))
    # MWSCRIPT-EFFECT-PARITY-69: the placements in cells the image carries, bound or not (measure, placed_in_image). A
    # script the build leaves out of the file (nothing to run) has no binding, so its add-on placements were read as
    # "only in an add-on world" although their cells are in the image (two scripts with no function: an add-on
    # merchant's and the fort soldiers'). Data measured before the count has only the base game's placements.
    in_image = game.get('placed_in_image')
    here = bool(game['placed'].get('Morrowind.esm')) if in_image is None else bool(sum(in_image.values()))
    if row['inert'] and (started or here):
        if row.get('functions') == {}:
            # MWSCRIPT-COMPLETE-LANDMARK: no function at all, so it can only set its own locals, and nothing reads
            # them but the dialogue, which keeps them on the speaker without the script (the parked locals: a result
            # sets them, a filter reads them); running it would change nothing seen
            return 'runs', 'nothing to run but its own locals, which the dialogue keeps on the speaker'
        return 'attached-not-run', 'nothing it does is seen yet: left out of the file'
    if row['bound'] or started:
        return 'runs', ''
    if row.get('held') and not row['inert']:
        return 'runs', 'runs on the items placed containers and actors hold, while their area is loaded'
    placed_addon = any(game['placed'].get(m) for m in MASTERS[1:])
    if placed_addon and in_image is not None and any(in_image.get(m) for m in MASTERS[1:]):
        # its cells are in the image and the build attaches nothing: a fault of the build, not a missing world
        return 'not-attached', 'placed in cells the image carries, but the build does not attach it there'
    if placed_addon:
        return 'not-in-image', 'placed only in cells of an add-on world that the image does not carry'
    runtime = runtime_attach(row)
    if runtime and row['inert']:
        return 'attached-not-run', 'nothing it does is seen yet: left out of the file'
    if runtime:
        return 'runs', runtime
    if made and all(m in MASTERS[1:] for m in made):
        return 'not-in-image', 'made only by a script of an add-on world, not in the image yet'
    return 'not-attached', 'its records are never placed, and nothing makes them at run time yet'


def runtime_attach(row):
    """How the build attaches the script of a record that is never placed (MWSCRIPT-UNPLACED-ATTACH-62), '' none."""
    game = row['refs']
    kinds = set(game['records'])
    if kinds & set(CARRIED):
        return 'runs while the player carries one of its items'
    if game['levelled'] and kinds & {'CREA', 'NPC_'}:
        return 'runs on the actor a levelled list gives'
    if game.get('placed_by_scripts'):
        return 'runs on the object a script places'
    return ''


def dialogue_state(row):
    if row['error']:
        return 'not-converted'
    return 'missing-function' if missing_now(row['notyet']) else 'runs'


# --- measure: the masters and the compiler, in the builder container ---

def _cells(raw, master, out):
    """Every placed reference of one master: (master, interior, cell name, grid, base id, door target)."""
    from mwad.esm import records, subrecords, string
    for tag, flags, payload in records(raw):
        if tag != 'CELL':
            continue
        parts = list(subrecords(payload))
        head, refs, ref, moved = {}, [], None, False
        for t, data in parts:
            if t == 'MVRF':
                moved, ref = True, None
                continue
            if t == 'FRMR':
                moved = False
                ref = {}
                refs.append(ref)
                continue
            if ref is None:
                head.setdefault(t, data)
                continue
            if t == 'NAME':
                ref['id'] = string(data, errors='replace').casefold()
            elif t == 'DODT' and len(data) >= 12:
                ref['door'] = struct.unpack_from('<3f', data)
            elif t == 'DNAM':
                ref['dest'] = string(data, errors='replace').casefold()
            elif t == 'DELE':
                ref['deleted'] = True
        cflags, gx, gy = struct.unpack('<Iii', head['DATA']) if len(head.get('DATA', b'')) == 12 else (0, 0, 0)
        interior = bool(cflags & 1)
        name = string(head.get('NAME', b''), errors='replace').casefold()
        for r in refs:
            if r.get('deleted') or 'id' not in r:
                continue
            out.append({'master': master, 'interior': interior, 'cell': name if interior else (gx, gy),
                        'id': r['id'], 'door': r.get('door'), 'dest': r.get('dest')})


def _levelled(raw, out):
    from mwad.esm import records, subrecords, string
    for tag, flags, payload in records(raw):
        if tag in ('LEVC', 'LEVI'):
            for t, data in subrecords(payload):
                if t in ('CNAM', 'INAM'):
                    out[string(data, errors='replace').casefold()] += 1


def interior_regions(placed, exteriors):
    """{interior cell: region id}: the region of the exterior its doors lead out to, through other interiors when it
    has no such door (breadth first). An interior with no way out keeps no region."""
    direct, links = {}, {}
    for p in placed:
        if not p['interior'] or p['door'] is None:
            continue
        cell = p['cell']
        if p['dest']:
            links.setdefault(cell, set()).add(p['dest'])
        else:
            grid = (int(p['door'][0] // CELL), int(p['door'][1] // CELL))
            region = (exteriors.get(grid) or ('', ''))[1] or 'wilderness'
            direct.setdefault(cell, Counter())[region] += 1
    out = {c: n.most_common(1)[0][0] for c, n in direct.items()}
    frontier = list(out)
    while frontier:
        nxt = []
        for cell, dests in links.items():
            if cell in out:
                continue
            got = [out[d] for d in dests if d in out]
            if got:
                out[cell] = Counter(got).most_common(1)[0][0]
                nxt.append(cell)
        frontier = nxt
    return out


# Where OpenMW 0.51 deliberately differs from the original engine in what a script does; AmiWind follows OpenMW, not
# the original's bugs. Facts from OpenMW 0.51's own source notes (cited per row), never guessed. 'match' says which
# calls of a script hit the row: (function names, the explicit reference or None for any, the first string argument or
# None for any).
OPENMW_FIXES = (
    {'id': 'dagoth-ur-remote-change', 'match': (('modhealth', 'modmagicka', 'modfatigue'), 'dagoth_ur_1', None),
     'original': 'The endgame scripts change dagoth_ur_1\'s health, magicka or fatigue from afar, after he is gone.',
     'openmw': 'Such a change on dagoth_ur_1 through an explicit reference that finds no loaded actor is ignored, '
               'as a workaround for those broken scripts (apps/openmw/mwscript/statsextensions.cpp OpModDynamic).',
     'amiwind': 'follows: a change on dagoth_ur_1 with no entity is ignored (engine/aga/src/aw_mwhost.c)'},
    {'id': 'showmap-empty-name', 'match': (('showmap',), None, ''),
     'original': 'ShowMap with an empty name errors out or ends the game.',
     'openmw': 'ShowMap with an empty name stops the script with an error (apps/openmw/mwscript/guiextensions.cpp '
               'OpShowMap).',
     'amiwind': 'safe, not the same: nothing is revealed and the script goes on (engine/aga/src/aw_mwhost.c)'},
    {'id': 'dontsaveobject-ignored', 'match': (('dontsaveobject',), None, None),
     'original': 'DontSaveObject keeps its object out of the saved game.',
     'openmw': 'DontSaveObject does nothing, a deliberate and marginal difference '
               '(apps/openmw/mwscript/miscextensions.cpp OpDontSaveObject).',
     'amiwind': 'follows: compiled to no code (tools/mwscript/codegen.py)'},
    {'id': 'repairedonme-zero', 'match': (('repairedonme',), None, None),
     'original': 'RepairedOnMe does not work.',
     'openmw': 'RepairedOnMe always reads 0, deliberately (apps/openmw/mwscript/miscextensions.cpp OpRepairedOnMe).',
     'amiwind': 'not in the compiler\'s table: no script of the three masters calls it'},
)


def calls(tree):
    """Every call of a parsed script: [(explicit reference or None, function name, args)]."""
    out = []

    def expr(node):
        if not isinstance(node, tuple) or not node:
            return
        if node[0] == 'call':
            out.append((node[1], node[2], node[3] or []))
            for a in node[3] or ():
                expr(a)
        elif node[0] in ('bin', 'cmp'):
            expr(node[2]); expr(node[3])
        elif node[0] == 'neg':
            expr(node[1])

    def block(stmts):
        for s in stmts or ():
            if not isinstance(s, tuple) or not s:
                continue
            if s[0] == 'if':
                for cond, body in s[2]:
                    expr(cond); block(body)
                block(s[3])
            elif s[0] == 'while':
                expr(s[2]); block(s[3])
            elif s[0] == 'set':
                expr(s[3])
            elif s[0] == 'do':
                expr(s[2])
    if tree is not None:
        block(tree[2])
    return out


def openmw_fixes(tree):
    """The ids of OPENMW_FIXES a parsed script hits."""
    hit = set()
    for ref, name, args in calls(tree):
        for fix in OPENMW_FIXES:
            names, want_ref, want_arg = fix['match']
            if name not in names:
                continue
            if want_ref is not None and (ref or '').casefold() != want_ref:
                continue
            first = next((a[1] for a in args if a[0] == 'str'), None)
            if want_arg is not None and (first or '') != want_arg:
                continue
            hit.add(fix['id'])
    return sorted(hit)


def conditions(tree):
    """(number of if/elseif/while tests, sorted list of what the tests read: function names, 'local', 'global',
    'other script')."""
    tests, reads = [0], set()

    def expr(node):
        if not isinstance(node, tuple) or not node:
            return
        kind = node[0]
        if kind == 'call':
            reads.add(node[2])
            for a in node[3] or ():
                expr(a)
        elif kind == 'local':
            reads.add('local')
        elif kind == 'global':
            reads.add('global')
        elif kind == 'member':
            reads.add('other script')
        elif kind in ('bin', 'cmp'):
            expr(node[2]); expr(node[3])
        elif kind == 'neg':
            expr(node[1])

    def block(stmts):
        for s in stmts or ():
            if not isinstance(s, tuple) or not s:
                continue
            if s[0] == 'if':
                for cond, body in s[2]:
                    tests[0] += 1
                    expr(cond)
                    block(body)
                block(s[3])
            elif s[0] == 'while':
                tests[0] += 1
                expr(s[2])
                block(s[3])
    if tree is not None:
        block(tree[2])
    return tests[0], sorted(reads)


def image_world(build):
    """What a build's image carries of the add-on worlds, read from the build's own run folder (never typed here;
    TRACKERS-MOURNHOLD-NOT-COUNTED-67): {'build', 'addons': the add-on masters the scripts stage bound, 'districts':
    the outdoor districts the image presents (the module tribunal-mournhold's cells), 'rooms': the rooms the image's
    interior store holds, 'interiors': every interior cell (folded name) of those two}. The sources: the scripts
    stage's receipt (mwscript/mwscript-receipt.json: bound_addons, presented) and the room store's receipt
    (chim-interiors/chim-rooms-receipt.json "rooms": the cell of every room the store holds). A missing file leaves its part empty, so a build
    without the module or the rooms counts none of them."""
    build = Path(build)

    def read(*parts):
        p = build.joinpath(*parts)
        return json.loads(p.read_text(encoding='utf-8')) if p.is_file() else {}
    inputs = read('mwscript', 'mwscript-receipt.json').get('inputs') or {}
    districts = sorted(k.casefold() for k in (inputs.get('presented') or {}))
    store = read('chim-interiors', 'chim-rooms-receipt.json')
    rooms = sorted({r['cell'].casefold() for r in store.get('rooms', ()) if r.get('cell')})
    named = re.search(r'v\d+\.\d+\.\d+(?:-(?:dev|rc)\d+)?', build.name)       # the version, not the folder's name
    # EXPANSION-SCRIPTS-NOT-ATTACHED-66 (v0.0.68): the add-on worlds' exterior cells the image carries, the frames of
    # its stores (image/chim-layer-stores.json, tools/chim/layer_stores.py: Solstheim's frames since v0.0.68-dev3;
    # Mournhold's district frames are the districts above, bound by their interior cell)
    layers = build / 'image' / 'chim-layer-stores.json'
    stores = json.loads(layers.read_text(encoding='utf-8')) if layers.is_file() else []
    blocks = set().union(*_district_blocks(inputs))
    exteriors = sorted({tuple(m['cell']) for s in stores if isinstance(s, dict)
                        for m in s.get('maps') or () if m.get('cell') is not None} - blocks)
    return {'build': named.group(0) if named else build.name, 'addons': list(inputs.get('bound_addons') or ()),
            'districts': districts,
            'rooms': rooms, 'interiors': sorted(set(districts) | set(rooms)), 'exteriors': exteriors}


def _district_blocks(inputs):
    """The grid cells of each presented district's block (the scripts stage's receipt 'presented'): those frames are
    the districts', counted by their interior cell, not as an add-on exterior."""
    out = []
    for place in (inputs.get('presented') or {}).values():
        size = place.get('size') or (1, 1)
        out.append({(place['block'][0] + dx, place['block'][1] + dy) for dx in range(size[0]) for dy in range(size[1])})
    return out


def bound_in_image(binds, image, interior_names, masters=MASTERS):
    """The bindings the image attaches in cells it carries. A Morrowind.esm binding stays as it is; an add-on's own
    binding counts when its cell is one of the image's interior cells (the room store's rooms and the presented
    districts) or, since v0.0.68 (EXPANSION-SCRIPTS-NOT-ATTACHED-66), one of the add-on exterior cells its stores'
    frames carry (image_world 'exteriors': Solstheim's). Until then an add-on's exterior was never counted, so the
    Solstheim scripts the image runs (the Skaal village's and Raven Rock's doors among them) read "only in an add-on
    world". IMAGE None (no build given): the add-ons' bindings are all dropped, as before. interior_names: {interior
    number: folded cell name}."""
    from mwscript.gamedata import ADDON_KEY_STRIDE
    carried = set((image or {}).get('interiors') or ())
    outdoors = {tuple(c) for c in (image or {}).get('exteriors') or ()}
    out = []
    for b in binds:
        owner = (b['reference'] & 0xFFFFFF) // ADDON_KEY_STRIDE
        if owner == 0:
            out.append(b)
        elif owner < len(masters) and isinstance(b['cell'], int) and interior_names.get(b['cell'], '') in carried:
            out.append(b)
        elif owner < len(masters) and isinstance(b['cell'], tuple) and tuple(b['cell']) in outdoors:
            out.append(b)
    return out


def measure(data_files, image_build=None):
    from mwscript.gamedata import GameData
    from mwscript.compiler import compile_program, bindings, handwritten_patterns
    from mwscript.codegen import SCRIPT_HANDWRITTEN, SCRIPT_INERT, SCRIPT_DIALOGUE, SCRIPT_START
    from mwscript.awms import decode
    from mwscript.parser import Parser
    from mwscript.ident import compiler_identity
    from mwad.paths import child_ci
    started = time.time()
    print('=== PHASE 1/4: the masters (scripts, records, globals) ===', flush=True)
    data = GameData().load(data_files)
    print('  %d scripts, %d scripted records, %d start scripts, %d dialogue result texts (%.1f s)'
          % (len(data.scripts), sum(1 for b in data.bases.values() if b[1]), len(data.start_scripts),
             len(data.results), time.time() - started), flush=True)
    print('=== PHASE 2/4: placed references, levelled lists, doors of every master ===', flush=True)
    placed, levelled = [], Counter()
    for name in MASTERS:
        path = child_ci(Path(data_files), name, required=False)
        if path is None:
            continue
        raw = path.read_bytes()
        _cells(raw, name, placed)
        _levelled(raw, levelled)
        print('  %s: %d placed references so far (%.1f s)' % (name, len(placed), time.time() - started), flush=True)
    inner = interior_regions(placed, data.exteriors)
    print('=== PHASE 3/4: the compiler, as the builder runs it ===', flush=True)
    program, compiled = compile_program(data, None, handwritten=handwritten_patterns())
    # TRACKERS-MOURNHOLD-NOT-COUNTED-67: with a build given, the add-on worlds its image carries are bound as the
    # scripts stage binds them (its bound_addons); only the bindings in cells the image holds count as attached
    image = image_world(image_build) if image_build else None
    binds = bindings(program, compiled, addons=tuple((image or {}).get('addons') or ()))
    in_file = len(binds)
    addon_in_file = sum(1 for b in binds if (b['reference'] & 0xFFFFFF) // gamedata.ADDON_KEY_STRIDE)
    names ={number: name for name, number in data.interior_numbers.items()}
    binds = bound_in_image(binds, image, names)
    if image:
        image['bound_in_image'] = {m: sum(1 for b in binds if (b['reference'] & 0xFFFFFF) // gamedata.ADDON_KEY_STRIDE ==
                                          MASTERS.index(m)) for m in image['addons']}
        print('  image %s: add-ons %s, %d districts, %d rooms, %d add-on exterior cells; bindings attached there %s (%d '
              'bound in the file, %d kept)' % (image['build'], ', '.join(image['addons']) or 'none',
                                               len(image['districts']), len(image['rooms']),
                                               len(image.get('exteriors') or ()), image['bound_in_image'], in_file,
                                               len(binds)), flush=True)    # MWSCRIPT-INVENTORY-HITONME-62: the rows of items placed containers and actors hold count apart (held)
    from mwscript.compiler import BIND_HELD
    bound = Counter(b['script'] for b in binds if not b['flags'] & BIND_HELD)
    held = Counter(b['script'] for b in binds if b['flags'] & BIND_HELD)
    # MWSCRIPT-UNPLACED-ATTACH-62: the records a script's Place call can make (PLAC rows the engine can make), by script
    from mwscript.codegen import PLACE_ROWS_MAX
    from mwscript.opcodes import NONE
    place_made = Counter(r['script'] for k, r in enumerate(program.place_rows())
                         if r['carried'] and r['script'] != NONE and k < PLACE_ROWS_MAX)
    # MWSCRIPT-COMPLETE-LANDMARK: who makes each record at run time, whether the engine can or not: the masters of the
    # scripts whose Place call names it ('dialogue' for a dialogue result)
    from mwscript.codegen import PLACE_CALL
    makers = {}
    for maker, texts in ([(s.master, [s.text]) for s in data.scripts.values()] +
                         [('dialogue', [t for (_speaker, t) in data.results])]):
        for text in texts:
            for line in (text or '').splitlines():
                for m in PLACE_CALL.finditer(line.split(';', 1)[0]):
                    if m.group(1).casefold() != 'drop':
                        makers.setdefault(m.group(2).strip('"').casefold(), set()).add(maker)
    names = [row['name'] for row in program.scripts.rows]
    started_by = {}
    for i, c in enumerate(compiled):
        if c.error is not None:
            continue
        for _, op, args in decode(c.code):
            if op == 'STARTSCRIPT':
                started_by.setdefault(args[0], set()).add(i)
    print('  %d compiled (%d dialogue results), %d bindings (%.1f s)'
          % (len(compiled), sum(1 for c in compiled if c.flags & SCRIPT_DIALOGUE), len(binds), time.time() - started),
          flush=True)
    print('=== PHASE 4/4: one row per script ===', flush=True)
    by_script = {}
    for base, (tag, script) in data.bases.items():
        if script:
            by_script.setdefault(script, []).append((tag, base))
    base_of = {base: script for base, (tag, script) in data.bases.items() if script}
    placed_by = {}
    # MWSCRIPT-EFFECT-PARITY-69: the placements in cells the image carries, whether the build binds them or not (a
    # script with nothing to run is left out of the file and has no binding): the base game's all, an add-on's in the
    # image's interior cells (the rooms of its store and the presented districts) and add-on exterior cells
    image_inside = set((image or {}).get('interiors') or ())
    image_outside = {tuple(c) for c in (image or {}).get('exteriors') or ()}
    in_image = {}
    for p in placed:
        script = base_of.get(p['id'])
        if not script:
            continue
        if p['master'] == MASTERS[0] or (p['cell'] in image_inside if p['interior'] else
                                         tuple(p['cell']) in image_outside):
            in_image.setdefault(script, Counter())[p['master']] += 1
        if p['interior']:
            area = inner.get(p['cell']) or ADDON_AREA.get(p['master']) or 'interior with no way out'
        else:
            area = (data.exteriors.get(tuple(p['cell'])) or ('', ''))[1] or 'wilderness'
            if p['master'] != 'Morrowind.esm' and area == 'wilderness':
                area = ADDON_AREA[p['master']]
        placed_by.setdefault(script, []).append((p['master'], data.bases[p['id']][0], area))
    globals_ = {k: v[0] for k, v in data.globals.items()}
    speakers = Counter()
    for (speaker, _text) in data.results:
        script = data.bases.get(speaker, (None, ''))[1] if speaker else ''
        if script:
            speakers[script] += 1
    rows, results = [], []
    for i, (row, c) in enumerate(zip(program.scripts.rows, compiled)):
        if c.flags & SCRIPT_DIALOGUE:
            try:
                rtree = Parser(row['script'].text, globals_).script()
            except Exception:   # noqa: BLE001 (a result that does not parse: counted as not converted)
                rtree = None
            results.append({'error': c.error is not None, 'notyet': sorted(set(c.notyet)),
                            'functions': sorted(set(c.calls)), 'openmw': openmw_fixes(rtree),
                            'fight': dialogue_combat.calls(row['script'].text)})
            continue
        ident = c.ident
        s = row['script']
        try:
            tree = Parser(s.text, globals_).script()
        except Exception:   # noqa: BLE001 (a script that does not parse: no conditions to list)
            tree = None
        tests, reads = conditions(tree)
        here = placed_by.get(ident, [])
        per_master = {}
        for m, tag, _ in here:
            per_master.setdefault(m, Counter())[tag] += 1
        areas = Counter(a for _, _, a in here)
        starters = started_by.get(i, set())
        from_scripts = sorted(names[j] for j in starters if not compiled[j].flags & SCRIPT_DIALOGUE)
        from_dialogue = sum(1 for j in starters if compiled[j].flags & SCRIPT_DIALOGUE)
        if areas:
            area = sorted(areas.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        elif c.flags & SCRIPT_START or from_scripts:
            area = GLOBAL_AREA
        elif from_dialogue:
            area = DIALOGUE_AREA
        elif ident in by_script:
            area = UNPLACED_AREA
        else:
            area = NOBODY_AREA
        records_ = {}
        for tag, base in sorted(by_script.get(ident, [])):
            records_.setdefault(tag, []).append(base)
        rows.append({
            'id': s.id, 'master': s.master,
            'defined_in': [m for m in MASTERS if any(x.id.casefold() == ident for x in data.scripts_by_master[m])],
            'area': area, 'areas': dict(sorted(areas.items())),
            'refs': {'records': records_,
                     'placed': {m: dict(sorted(n.items())) for m, n in per_master.items()},
                     'placed_in_image': {m: in_image[ident][m] for m in MASTERS if in_image.get(ident, {}).get(m)},
                     'levelled': sum(levelled.get(b, 0) for _, b in by_script.get(ident, [])),
                     'dialogue_starts': from_dialogue, 'dialogue_speaker': speakers.get(ident, 0),
                     'placed_by_scripts': place_made.get(i, 0),
                     'made_by': sorted({m for _, base in by_script.get(ident, []) for m in makers.get(base, ())})},
            'start': bool(c.flags & SCRIPT_START), 'started_by': from_scripts,
            'bound': bound.get(i, 0), 'held': held.get(i, 0),
            'handwritten': bool(c.flags & SCRIPT_HANDWRITTEN), 'inert': bool(c.flags & SCRIPT_INERT),
            'error': c.error is not None,
            'functions': dict(sorted(Counter(c.calls).items())),
            'tests': tests, 'conditions': reads, 'openmw': openmw_fixes(tree),
            'notyet': sorted(set(c.notyet)),
        })
    rows.sort(key=lambda r: r['id'].casefold())
    # the dialogue results kept small: the total, how many call each function, and only the results with a call not
    # carried out or a compile error (the rest run whole whatever the table says)
    results = {'total': len(results),
               'functions': dict(sorted(Counter(n for r in results for n in r['functions']).items())),
               'openmw': dict(sorted(Counter(f for r in results for f in r['openmw']).items())),
               'gaps': sorted(({'error': r['error'], 'notyet': r['notyet']} for r in results
                               if r['error'] or r['notyet']), key=lambda g: (g['error'], g['notyet'])),
               # DIALOGUE-AGGRO-62: every answer that starts or changes a fight, its calls (no text) and whether it
               # compiles; its engine path is worked out from them (combat_paths), so a function carried out later
               # moves it
               'fight': sorted(({'calls': r['fight'], 'error': r['error'], 'notyet': r['notyet']} for r in results
                                if r['fight']), key=lambda f: json.dumps(f, sort_keys=True))}
    print('  %d script rows, %d dialogue results (%.1f s)' % (len(rows), results['total'], time.time() - started),
          flush=True)
    measured = {'masters': {m: data.master_sha256.get(m) for m in MASTERS}, 'compiler': compiler_identity(),
                'host': sorted(HOST),
                'date': time.strftime('%Y-%m-%d'), 'bindings': in_file,
                'start_scripts': len(data.start_scripts), 'placed_scripted': len([p for p in placed
                                                                                  if base_of.get(p['id'])])}
    if image:
        # the image's own add-on worlds, counted from the build: names of cells are not kept, only how many
        measured['image'] = {'build': image['build'], 'addons': image['addons'], 'districts': len(image['districts']),
                             'rooms': len(image['rooms']), 'exteriors': len(image.get('exteriors') or ()),
                             'bound_in_image': image['bound_in_image'], 'addon_in_file': addon_in_file}
    return measured, rows, results


# --- the JSON and the page ---

def dialogue_counts(results):
    d = Counter(dialogue_state(r) for r in results['gaps'])
    return {'runs': results['total'] - d['missing-function'] - d['not-converted'],
            'missing-function': d['missing-function'], 'not-converted': d['not-converted']}


def combat_paths(results):
    """DIALOGUE-AGGRO-62: how many fight-starting answers go down each engine path (tools/mwscript/dialogue_combat.py),
    with the functions not carried out now (a function carried out later moves its answers to their path)."""
    out = Counter()
    for f in results.get('fight', ()):
        out[dialogue_combat.path(f['calls'], runs=not f['error'] and not missing_now(f['notyet']))] += 1
    return dict(sorted(out.items()))


def apply_states(doc):
    use(doc)
    for row in doc['scripts']:
        row['state'], row['why'] = state_of(row)
    doc['dialogue'] = dialogue_counts(doc['dialogue_results'])
    return doc


def problems(doc):
    out = []
    if doc.get('schema') != SCHEMA:
        out.append('schema must be %r' % SCHEMA)
    for key in ('updated', 'version', 'intro', 'measured', 'scripts', 'dialogue_results', 'dialogue'):
        if key not in doc:
            out.append('missing key %s' % key)
    if out:
        return out
    use(doc)
    if not re.match(r'^\d{4}-\d\d-\d\d$', str(doc['updated'])):
        out.append('updated must be YYYY-MM-DD')
    if not re.match(r'^\d+\.\d+\.\d+(?:-[a-z]+\d+)?$', str(doc['version'])):
        out.append('version must be like 0.0.62-dev1')
    seen = set()
    for row in doc['scripts']:
        rid = row.get('id', '?')
        if rid.casefold() in seen:
            out.append('%s: twice' % rid)
        seen.add(rid.casefold())
        if row.get('state') not in STATES:
            out.append('%s: state must be one of %s' % (rid, STATES))
            continue
        want = state_of(row)
        if (row['state'], row.get('why')) != want:
            out.append('%s: state %s is stale (now %s): run tools/mwscript_features.py render' % (rid, row['state'],
                                                                                                  want[0]))
        for f in row.get('openmw', ()):
            if f not in {x['id'] for x in OPENMW_FIXES}:
                out.append('%s: unknown OpenMW fix %s' % (rid, f))
        for n in list(row['functions']) + row['notyet']:
            if n not in FUNCTIONS:
                out.append('%s: function %s is not in tools/mwscript/functions.py' % (rid, n))
        if row['state'] == 'inert' and reachable(row):
            out.append('%s: listed as not used in the original game, but it can run there (%s)'
                       % (rid, ', '.join(reachable(row))))
    if doc['dialogue'] != dialogue_counts(doc['dialogue_results']):
        out.append('dialogue counts are stale: run tools/mwscript_features.py render')
    for n in list(doc['dialogue_results']['functions']) + [n for g in doc['dialogue_results']['gaps']
                                                          for n in g['notyet']]:
        if n not in FUNCTIONS:
            out.append('dialogue results: function %s is not in tools/mwscript/functions.py' % n)
    if not doc['scripts']:
        out.append('no scripts')
    if not out:
        out += effect_problems(doc)    # every called function has its effect class (config/mwscript-effects.json)
    return out


def _n(x):
    return '{:,}'.format(x)


def _cell(text):
    return str(text).replace('|', '/').replace('\n', ' ')


def _refs(row):
    r = row['refs']
    parts = []
    kinds = Counter()
    for tag, ids in r['records'].items():
        kinds[tag] += len(ids)
    if kinds:
        parts.append(', '.join('%d %s' % (n, KIND_NAMES.get(t, t)) for t, n in sorted(kinds.items())))
    placed = sum(sum(v.values()) for v in r['placed'].values())
    if placed:
        parts.append('placed %d (%s)' % (placed, ', '.join('%s %d' % (m.split('.')[0], sum(v.values()))
                                                          for m, v in r['placed'].items())))
    if r['levelled']:
        parts.append('levelled lists %d' % r['levelled'])
    if row.get('held'):
        parts.append('held by placed containers and actors %d' % row['held'])
    if r.get('placed_by_scripts'):
        parts.append('placed by scripts (%d records)' % r['placed_by_scripts'])
    elif r.get('made_by'):
        parts.append('placed by scripts of %s (not made yet)' % ', '.join(m.replace('.esm', '') for m in r['made_by']))
    if row['start']:
        parts.append('start script')
    if row['started_by']:
        parts.append('started by ' + ', '.join(row['started_by']))
    if r['dialogue_starts']:
        parts.append('started by %d dialogue results' % r['dialogue_starts'])
    if r['dialogue_speaker']:
        parts.append('speaker of %d dialogue results' % r['dialogue_speaker'])
    return '; '.join(parts) or '-'


def _records(row):
    ids = [i for tag in sorted(row['refs']['records']) for i in row['refs']['records'][tag]]
    if len(ids) > 6:
        return ', '.join(ids[:6]) + ' and %d more' % (len(ids) - 6)
    return ', '.join(ids) or '-'


def function_table(doc):
    """{function: {...}} over the script rows and the dialogue results."""
    out = {}
    for row in doc['scripts']:
        conds = set(row['conditions'])
        missing = missing_now(row['notyet'])
        for n, k in row['functions'].items():
            f = out.setdefault(n, Counter())
            f['scripts'] += 1
            f['uses'] += k
            f['conditions'] += n in conds
            f['missing_in'] += n in missing
            f['only_gap'] += missing == [n]
    for n, k in doc['dialogue_results']['functions'].items():
        out.setdefault(n, Counter())['dialogue'] += k
    for g in doc['dialogue_results']['gaps']:
        for n in missing_now(g['notyet']):
            out.setdefault(n, Counter())['dialogue_missing'] += 1
    return out


# --- the effect in play of each function (MWSCRIPT-IN-PLAY-PARITY-68) ---
# "Carried out" above is static: the call compiles and the engine executes it. config/mwscript-effects.json says, per
# function the game's scripts call, whether what the engine then does is the original's effect: full, part (with the
# line of what is missing) or none (accepted, nothing of the effect happens), and how that is known (basis).
EFFECTS = ROOT / 'config' / 'mwscript-effects.json'
EFFECTS_SCHEMA = 'mwscript-effects 1'
EFFECT_CLASSES = ('full', 'part', 'none')
EFFECT_LABELS = {'full': 'full', 'part': 'in part', 'none': 'none'}
EFFECT_BASES = ('source', 'test', 'play')
_effects = None


def effects(path=None):
    """{function: {effect, missing, register, basis}} of config/mwscript-effects.json; {} when the file is missing."""
    global _effects
    if path is not None or _effects is None:
        p = Path(path) if path else EFFECTS
        found = json.loads(p.read_text(encoding='utf-8')) if p.exists() else {'schema': EFFECTS_SCHEMA, 'functions': {}}
        if path is not None:
            return found
        _effects = found
    return _effects


REGISTER = ROOT / 'docs' / 'bugs' / 'bugs.json'
# a register id's first word that is an everyday word as well as a function's name: such an entry is about a function
# only when its id begins with MWSCRIPT
EVERYDAY = frozenset(('journal', 'random', 'cast', 'drop', 'fall', 'face', 'move', 'choice', 'position', 'activate',
                      'enable', 'disable', 'lock', 'unlock', 'say', 'show', 'help', 'equip', 'rotate', 'goodbye'))


def register_entries(path=None):
    """{id: entry} of the bug register (docs/bugs/bugs.json); {} when the file is missing."""
    p = Path(path) if path else REGISTER
    if not p.is_file():
        return {}
    found = json.loads(p.read_text(encoding='utf-8'))
    return {b['id']: b for b in (found.get('bugs', ()) if isinstance(found, dict) else found)}


def fix_mark(entry):
    """The newest fix step of a register entry, as the effect rows record it under "checked": its last closure step
    (stage and where), else its fixed state; '' while nothing is fixed. A row is checked against that step; a newer
    step (shipped, confirmed in play) asks for the row to be checked again."""
    steps = entry.get('closure') or []
    if isinstance(steps, list) and steps:
        return '%s: %s' % (steps[-1].get('stage'), steps[-1].get('where'))
    if entry.get('state') in ('fixed', 'closed'):
        return 'fixed: %s' % (entry.get('fixed_in') or 'closed')
    return ''


def entries_about(name, register):
    """The register entries whose id says they are about the function NAME: an id that begins with MWSCRIPT and has
    the name as one of its words, or an id whose first word is the name (unless it is an everyday word)."""
    out = []
    for rid in register:
        words = rid.casefold().split('-')
        if (words[0] == 'mwscript' and name in words[1:]) or (words[0] == name and name not in EVERYDAY):
            out.append(rid)
    return sorted(out)


def stale_effect_rows(rows, register):
    """MWSCRIPT-TRACKER-EFFECT-ROWS-STALE-69: the effect rows that must be looked at again. A row names the register
    entries about its function; when one of them has a fix step (fixed in source, shipped, confirmed, or the fixed
    state), the row records that step under "checked" once it was read against the fix. A row is stale when an entry
    about its function has a fix step and is not named, when a named entry is not in the register, or when a named
    entry's newest fix step is not the one the row was checked against."""
    out = []
    for n, e in sorted(rows.items()):
        named = e.get('register') if isinstance(e.get('register'), list) else []
        checked = e.get('checked') or {}
        for rid in entries_about(n, register):
            # an open entry may be filed anywhere, at any time, without touching this file; once it has a fix step
            # the row must name it, which makes the row checked against that fix (the next loop)
            if rid not in named and fix_mark(register[rid]):
                out.append('effects: %s: the register entry %s is about this function and has the fix step "%s", '
                           'and the row does not name it' % (n, rid, fix_mark(register[rid])))
        for rid in named:
            if rid not in register:
                out.append('effects: %s names %s, which is not in the register' % (n, rid))
                continue
            mark = fix_mark(register[rid])
            if mark and checked.get(rid) != mark:
                out.append('effects: %s names %s, which has the fix step "%s": check the row against the fix '
                           '(its class, its line and what was seen in play) and record the step under "checked"'
                           % (n, rid, mark))
        for rid in checked:
            if rid not in named:
                out.append('effects: %s: checked names %s, which the row\'s register does not' % (n, rid))
    return out


def effect_problems(doc, table=None, register=None):
    """What the effects file is refused for: a function the game's scripts call without a class (DOC = the features
    data), a class or basis outside the lists, a part or none row without its line of what is missing, a full row
    with one, a name that is no function, a register field that is no list, a basis of play without what was seen in
    play, an in-play note without its three fields, and a row that is stale against the register
    (stale_effect_rows). REGISTER: {id: entry}, None for the repository's (no register file: that check is left)."""
    eff = table if table is not None else effects()
    reg = register if register is not None else register_entries()
    out = []
    if eff.get('schema') != EFFECTS_SCHEMA:
        out.append('config/mwscript-effects.json: schema must be %r' % EFFECTS_SCHEMA)
    rows = eff.get('functions', {})
    for n, e in sorted(rows.items()):
        if n not in FUNCTIONS:
            out.append('effects: %s is not in tools/mwscript/functions.py' % n)
        if e.get('effect') not in EFFECT_CLASSES:
            out.append('effects: %s: effect must be one of %s' % (n, ', '.join(EFFECT_CLASSES)))
            continue
        if e.get('basis') not in EFFECT_BASES:
            out.append('effects: %s: basis must be one of %s' % (n, ', '.join(EFFECT_BASES)))
        if e['effect'] != 'full' and not str(e.get('missing') or '').strip():
            out.append('effects: %s: a %s effect needs its line of what is missing' % (n, e['effect']))
        if e['effect'] == 'full' and e.get('missing'):
            out.append('effects: %s: a full effect has nothing missing' % n)
        if not isinstance(e.get('register'), list):
            out.append('effects: %s: register is a list' % n)
        seen = e.get('in_play', [])
        if not isinstance(seen, list) or any(not isinstance(s, dict) or not all(
                str(s.get(k) or '').strip() for k in ('what', 'version', 'date')) or
                not re.match(r'^\d{4}-\d\d-\d\d$', str(s.get('date'))) for s in seen):
            out.append('effects: %s: in_play is a list of notes, each with what was seen, the version and the date '
                       '(YYYY-MM-DD)' % n)
        elif e.get('basis') == 'play' and not seen:
            out.append('effects: %s: a class known from play needs its in_play note' % n)
    if reg:
        out += stale_effect_rows(rows, reg)
    for n in sorted(function_table(doc)):
        if n not in rows:
            out.append('effects: %s is called by the game\'s scripts and has no effect class in '
                       'config/mwscript-effects.json' % n)
    return out


def effects_section(table):
    """The lines under the "By function" table: the counts by class and, per function whose effect is not full, what
    is missing, by the number of scripts that call it."""
    rows = effects().get('functions', {})
    called = [n for n in table if n in rows]
    c = effect_counts(table)
    out = ['### Effect in play', '',
           'Carried out says that a call is executed; Effect in play says whether what the engine then does is what '
           'the original game does. Of the %d functions the game\'s scripts call, %d have the original\'s effect in '
           'full, %d in part and %d have none yet (the call is accepted and nothing of its effect happens). How each '
           'class is known: %d read from the source against the original\'s rules, %d kept by a test, %d checked in '
           'play. A class read from the source is not yet proven in play. Seen in play: what of a function\'s effect '
           'a play session has shown, with its build and date; %d functions have such a note, and a note covers only '
           'what it says, not the whole function. The rows were last checked against the source and the register '
           'for AmiWind v%s (%s).' % (
               c['called'], c['full'], c['part'], c['none'], c['source'], c['test'], c['play'], c['seen_in_play'],
               (effects().get('measured') or {}).get('version', '?'),
               long_date((effects().get('measured') or {}).get('date', '1970-01-01'))), '']
    gaps = [n for n in called if rows[n]['effect'] != 'full']
    if gaps:
        out += ['| Function | Effect | Scripts | Dialogue | What is missing | Known from | Seen in play | Register |',
                '| --- | --- | ---: | ---: | --- | --- | --- | --- |']
        for n in sorted(gaps, key=lambda n: (-table[n]['scripts'], -table[n]['dialogue'], n)):
            e = rows[n]
            out.append('| %s | %s | %d | %d | %s | %s | %s | %s |' % (
                n, EFFECT_LABELS[e['effect']], table[n]['scripts'], table[n]['dialogue'], _cell(e['missing']),
                e['basis'], _cell(_seen(e)), ', '.join(e['register']) or '-'))
        out.append('')
    whole = [n for n in called if rows[n]['effect'] == 'full' and rows[n].get('in_play')]
    if whole:
        out += ['Functions with the original\'s effect in full and a note of what was seen in play:', '',
                '| Function | Seen in play | Known from | Register |', '| --- | --- | --- | --- |']
        out += ['| %s | %s | %s | %s |' % (n, _cell(_seen(rows[n])), rows[n]['basis'],
                                          ', '.join(rows[n]['register']) or '-') for n in sorted(whole)]
        out.append('')
    return out


def _seen(e):
    """The in-play notes of one effect row as a cell: what was seen (version, date), or "not yet"."""
    return '; '.join('%s (v%s, %s)' % (s['what'], s['version'], long_date(s['date']))
                     for s in e.get('in_play') or ()) or 'not yet'


def effect_counts(table=None, doc=None):
    """The counts of the effect classes over the functions the game's scripts call: called, full, part, none, how
    the classes are known (source, test, play) and how many functions have something seen in play. TABLE:
    function_table(DOC), or DOC itself."""
    rows = effects().get('functions', {})
    table = table if table is not None else function_table(doc)
    called = [n for n in table if n in rows]
    count = Counter(rows[n]['effect'] for n in called)
    known = Counter(rows[n]['basis'] for n in called)
    return {'called': len(called), 'full': count['full'], 'part': count['part'], 'none': count['none'],
            'source': known['source'], 'test': known['test'], 'play': known['play'],
            'seen_in_play': sum(1 for n in called if rows[n].get('in_play'))}


# The Solstheim regions (Bloodmoon's exteriors): a script whose area is one of them belongs to an add-on world
ADDON_REGIONS = ('hirstaang forest region', 'isinfier plains region', 'felsaad coast region',
                 'moesring mountains region', 'thirsk region', 'brodir grove region', 'solstheim (bloodmoon)',
                 'mournhold (tribunal)')


def why_not_run(rows):
    """The section that counts the scripts that do not run by their reason (v0.0.63, MWSCRIPT-GAPS-63): the reason is
    the row's own "why" (a missing function counted as one reason, the functions are in By function), split by where
    the script's area is: Vvardenfell (the image's world, a start script, dialogue or no place) or an add-on world."""
    reasons = Counter()
    for r in rows:
        if r['state'] in ('runs', 'carried'):
            continue
        why ='calls a function the interpreter does not carry out yet' if r['state'] == 'missing-function' \
            else r['why']
        reasons[(LABELS[r['state']], why, r['area'] in ADDON_REGIONS)] += 1
    table = {}
    for (label, why, addon), n in reasons.items():
        table.setdefault((label, why), [0, 0])[1 if addon else 0] += n
    out = ['## Why the others do not run', '',
           'Each script that does not run, by its reason, and where its area is: Vvardenfell (the world in the image, '
           'including the start scripts, the dialogue-only ones and records with no place) or an add-on world '
           '(Mournhold, Solstheim). A missing function is one reason here; By function names the functions.', '',
           '| State | Reason | Vvardenfell | Add-on world | All |', '| --- | --- | ---: | ---: | ---: |']
    for (label, why), (v, a) in sorted(table.items(), key=lambda kv: -sum(kv[1])):
        out.append('| %s | %s | %s | %s | %s |' % (label, _cell(why), _n(v), _n(a), _n(v + a)))
    out.append('')
    return out


GAMES = {'Morrowind.esm': 'Morrowind (base game)', 'Tribunal.esm': 'Tribunal', 'Bloodmoon.esm': 'Bloodmoon'}


def script_summary(doc):
    """The counts the progress pages draw (MWSCRIPT-EFFECT-PARITY-69, TOOLKIT-PROGRESS-MWSCRIPT-MASTERS-69): per
    master and over all, the scripts used in the original, run, AmiWind adaptations (feature complete only), not yet
    (every other state), and those not used in the original, which never count toward completion; and the functions'
    effect in play (effect_counts). Every row's state is worked out again from the function table of today."""
    use(doc)

    def count(rows):
        st = Counter(state_of(r)[0] for r in rows)
        used = len(rows) - st['inert']
        done = st['runs'] + st['carried']
        return {'used': used, 'run': st['runs'], 'adaptation': st['carried'], 'not_yet': used - done,
                'unused': st['inert'], 'done': done,
                'percent': round(100.0 * done / used, 1) if used else 0.0}
    masters = [dict(count([r for r in doc['scripts'] if r.get('master') == m]), master=m, game=GAMES[m])
               for m in MASTERS]
    return {'source': 'docs/mwscript-features.json', 'version': doc.get('version'),
            'measured': (doc.get('measured') or {}).get('date'), 'masters': masters, 'all': count(doc['scripts']),
            'dialogue_results': {'total': doc['dialogue_results']['total'],
                                 'run': dialogue_counts(doc['dialogue_results'])['runs']},
            'functions': effect_counts(doc=doc)}


def reachable(row):
    """What could bring a script into the game at run time, from the row's measured references: [] for a script the
    original never runs. The "not used" list holds only rows with none (the check refuses another)."""
    game = row['refs']
    out = []
    if row.get('start'):
        out.append('a start record')
    if row.get('started_by') or game.get('dialogue_starts'):
        out.append('StartScript')
    if any(game.get('placed', {}).values()):
        out.append('a placed record')
    if game.get('levelled'):
        out.append('a levelled list')
    if game.get('made_by') or game.get('placed_by_scripts'):
        out.append('a script or dialogue result that makes its record')
    if row.get('bound') or row.get('held'):
        out.append('a binding of the build')
    if set(game.get('records') or ()) & set(CARRIED):
        out.append('an item a script could hand out')
    return out


def unused_note(rows):
    """One sentence of counts for the Not used section, from the rows' own data."""
    mine = [r for r in rows if r['state'] == 'inert']
    bare = sum(1 for r in mine if not r['refs']['records'])
    kinds = Counter(k for r in mine for k in r['refs']['records'])
    held = ', '.join('%d on %s records' % (n, KIND_NAMES.get(k, k)) for k, n in sorted(kinds.items()))
    return ('Of the %s scripts here, %s are carried by no record at all and %s by records that exist nowhere in the '
            'game%s.' % (_n(len(mine)), _n(bare), _n(len(mine) - bare), ' (%s)' % held if held else ''))


def render(doc):
    import doc_toc
    use(doc)
    rows = doc['scripts']
    st = Counter(r['state'] for r in rows)
    meas = doc['measured']
    lines = ['# MWScript features', '',
             '_Last updated with AmiWind v%s (%s)._' % (doc['version'], long_date(doc['updated'])), '',
             GENERATED, '', doc['intro'], '',
             'Of the %s scripts the original game uses, **%s run** as scripts and **%s are AmiWind adaptations** '
             '(AmiWind\'s own code does every step of the script). The rest, by state: done by AmiWind\'s own code '
             'with steps still open %s, using a function the interpreter lacks %s, attached but not run %s, '
             'compiled but not attached %s, placed only in add-on cells the image does not carry %s, not converted %s. '
             'A script that runs is not yet a script that plays as the original: Effect in play, under By function, '
             'says for each function the scripts call how much of the original\'s effect the engine has. '
             'The %s scripts not used in the original game (they never run there either: test and example scripts, '
             'replaced versions, cut content) are not counted toward completion and are listed apart under Not used '
             'in the original game.' % (
                 _n(len(rows) - st['inert']), _n(st['runs']), _n(st['carried']), _n(st['adaptation-gap']),
                 _n(st['missing-function']),
                 _n(st['attached-not-run']), _n(st['not-attached']), _n(st['not-in-image']), _n(st['not-converted']),
                 _n(st['inert'])), '',
             '| State | Scripts | What it means |', '| --- | ---: | --- |']
    meaning = {'runs': 'compiles whole, and the build attaches it to its objects or starts it (a record that is never '
                       'placed: while the player carries its item, on the actor a levelled list gives, or on the '
                       'object a script places; a script with no function, whose own locals the dialogue keeps on the '
                       'speaker without it, counts as running)',
               'not-in-image': 'compiles whole, but its records are placed (or made by scripts) only in cells of '
                               'Mournhold or Solstheim that the image does not carry (the image\'s own districts and '
                               'rooms count as carried: the measurement reads them from the build)',
               'inert': 'compiles whole, but no record, start, StartScript or dialogue result names it, or the records '
                        'that name it are never placed and nothing makes them: it never runs in the original either',
               'missing-function': 'compiles, but calls at least one function the interpreter does not carry out yet '
                                   '(those calls do nothing and read 0)',
               'attached-not-run': 'the game attaches it, but the build does not run it: a hand-written rule carries '
                                   'it, or nothing it does is seen yet',
               'not-attached': 'compiles whole, but nothing in the build attaches or starts it: its records are never '
                               'placed, and nothing makes them at run time yet',
               'not-converted': 'does not compile',
               'carried': 'not run as a script because AmiWind\'s own code does what it does, feature complete: every '
                          'step the original\'s script does is carried out (the section AmiWind adaptations names '
                          'the code and compares it step by step)',
               'adaptation-gap': 'not run as a script; AmiWind\'s own code does part of what it does, and at least '
                                 'one step of the script is missing or different: a gap, not an adaptation (its '
                                 'open steps are in the section AmiWind adaptations)'}
    for s in STATES:
        if s != 'inert':
            lines.append('| %s | %s | %s |' % (LABELS[s], _n(st[s]), meaning[s]))
    d = doc['dialogue']
    lines += ['| **Used in the original game** | **%s** | |' % _n(len(rows) - st['inert']),
              '| Not used in the original game (never runs there either; not counted toward completion) | %s | %s |'
              % (_n(st['inert']), meaning['inert']),
              '| **All script records** | **%s** | |' % _n(len(rows)), '',
              '| Game file | All | Used in the original | ' + ' | '.join(SHORT[s] for s in STATES if s != 'inert') +
              ' | Not used |',
              '| --- | ---: | ---: | ' + ' | '.join('---:' for s in STATES if s != 'inert') + ' | ---: |']
    for master in MASTERS:
        mc = Counter(r['state'] for r in rows if r['master'] == master)
        if sum(mc.values()):
            lines.append('| %s | %s | %s | ' % (master, _n(sum(mc.values())), _n(sum(mc.values()) - mc['inert'])) +
                         ' | '.join(_n(mc[s]) for s in STATES if s != 'inert') + ' | %s |' % _n(mc['inert']))
    lines += ['',
              'Dialogue result scripts (the lines a topic answer runs) are compiled as scripts of their own: '
              '%s results, %s run whole, %s use a function the interpreter lacks, %s are not converted.'
              % (_n(doc['dialogue_results']['total']), _n(d['runs']), _n(d['missing-function']),
                 _n(d['not-converted'])), '']
    fight = combat_paths(doc['dialogue_results'])
    if fight:
        # DIALOGUE-AGGRO-62: the answers that start or change a fight, by the engine path that carries them out
        names = {'speaker-startcombat': 'the speaker attacks (StartCombat): found by the answer\'s reference',
                 'other-startcombat': 'another actor attacks (StartCombat on a reference)',
                 'speaker-fight': 'the speaker\'s Fight changes: weighed when the talk ends',
                 'other-fight': 'another actor\'s Fight changes: weighed by that actor\'s next aggression check',
                 'startcombat-actor': 'a fight between two actors: both are set against each other (since v0.0.63)',
                 'not-run': 'the answer does not run whole'}
        lines += ['Dialogue answers that start or change a fight (StartCombat, SetFight, ModFight): %s.' %
                  _n(sum(fight.values())), '', '| Engine path | Answers |', '| --- | ---: |']
        lines += ['| %s | %s |' % (names.get(k, k), _n(v)) for k, v in fight.items()]
    lines += ['',
              'Measured on %s from the three masters (Morrowind, Tribunal, Bloodmoon) with the builder\'s own compiler '
              '(tools/mwscript), %s placed scripted references, %s bindings in the compiled file, %s start scripts. '
              'The states are worked out again from the interpreter\'s function table '
              '(tools/mwscript/functions.py) whenever the page is rendered, so a function carried out later moves its '
              'scripts without a new measurement.' % (long_date(meas['date']), _n(meas['placed_scripted']),
                                                       _n(meas['bindings']), _n(meas['start_scripts'])), '']
    img = meas.get('image')
    if img:
        # TRACKERS-MOURNHOLD-NOT-COUNTED-67: what the measured image carries of the add-on worlds, read from the build
        lines += ['The image measured: build %s. Its scripts stage bound the own placements of %s; the image carries %s '
                  'outdoor districts, %s rooms of the interior store and %s add-on exterior cells, and %s of the %s '
                  'add-on bindings in the file sit in those cells (%s). A script placed only in add-on cells outside '
                  'them is "%s".' % (
                      img['build'], ', '.join(a.replace('.esm', '') for a in img['addons']) or 'no add-on',
                      _n(img['districts']), _n(img['rooms']), _n(img.get('exteriors', 0)),
                      _n(sum(img['bound_in_image'].values())), _n(img['addon_in_file']),
                      ', '.join('%s %s' % (m.replace('.esm', ''), _n(n)) for m, n in img['bound_in_image'].items()),
                      LABELS['not-in-image']), '']
    lines += why_not_run(rows)
    lines += counterparts_section()
    # where OpenMW deliberately differs from the original engine
    hits = Counter(f for r in rows for f in r.get('openmw', ()))
    dhits = doc['dialogue_results'].get('openmw', {})
    lines += ['## Follows OpenMW\'s fix', '',
              'Where OpenMW 0.51 deliberately differs from the original engine in what a script does, AmiWind follows '
              'OpenMW, not the original\'s bug. Each fix names the original\'s behaviour and OpenMW\'s, taken from '
              'OpenMW\'s own source notes; Scripts and Dialogue count the script records and dialogue results whose '
              'calls hit it, and the rows of those scripts name it in their own column.', '',
              '| Fix | Original | OpenMW 0.51 | AmiWind | Scripts | Dialogue |', '| --- | --- | --- | --- | ---: | ---: |']
    for fix in OPENMW_FIXES:
        lines.append('| %s | %s | %s | %s | %d | %d |' % (fix['id'], _cell(fix['original']), _cell(fix['openmw']),
                                                         _cell(fix['amiwind']), hits.get(fix['id'], 0),
                                                         dhits.get(fix['id'], 0)))
    lines.append('')
    # per area
    lines += ['## By area', '',
              'The area of a script is where most of its placed references stand: the region for the exteriors, the '
              'region its doors lead out to for an interior. Scripts with no placed reference are grouped by what '
              'starts them.', '',
              '| Area | Scripts | ' + ' | '.join(SHORT[s] for s in STATES) + ' |',
              '| --- | ---: | ' + ' | '.join('---:' for _ in STATES) + ' |']
    areas = {}
    for r in rows:
        areas.setdefault(r['area'], Counter())[r['state']] += 1
    for area, c in sorted(areas.items(), key=lambda kv: (-sum(kv[1].values()), kv[0])):
        lines.append('| %s | %d | ' % (_cell(area), sum(c.values())) + ' | '.join('%d' % c[s] for s in STATES) + ' |')
    lines.append('| **All** | **%d** | ' % len(rows) + ' | '.join('**%d**' % st[s] for s in STATES) + ' |')
    # per function
    table = function_table(doc)
    lines += ['', '## By function', '',
              'Every function the game\'s scripts call. Scripts: the script records that call it; In conditions: of '
              'those, the ones whose if or while tests read it; Missing in: the scripts where the call is not carried '
              'out; Only gap: the scripts it alone keeps from running whole; Dialogue: the result scripts that call '
              'it, and of those the ones where the call is not carried out. Carried out "host" means the engine '
              'carries the call out through the import route; "in part" means some of its calls are carried out '
              '(the player\'s PositionCell to a known room, a Cast of a cure) and the others are not. Effect in play: '
              'whether what the engine does for the call is the original\'s effect, in full, in part or none (the '
              'list under the table says what is missing).', '',
              '| Function | Group | Carried out | Effect in play | Scripts | Uses | In conditions | Missing in | Only gap '
              '| Dialogue | Dialogue missing |',
              '| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    eff = effects().get('functions', {})
    for n, c in sorted(table.items(), key=lambda kv: (-(kv[1]['missing_in'] + kv[1]['dialogue_missing']),
                                                      -kv[1]['scripts'], kv[0])):
        fn = FUNCTIONS[n]
        gaps = c['missing_in'] + c['dialogue_missing']
        carried = 'host' if n in HOST else ('yes' if fn.run else 'no')
        if carried == 'no' and c['scripts'] + c['dialogue'] > gaps:
            carried = 'in part'          # some calls compile to their own form (the player's PositionCell)
        elif carried == 'host' and gaps:
            carried = 'host, in part'
        lines.append('| %s | %s | %s | %s | %d | %d | %d | %d | %d | %d | %d |' % (
            n, fn.group, carried, EFFECT_LABELS.get((eff.get(n) or {}).get('effect'), 'not classed'), c['scripts'],
            c['uses'], c['conditions'], c['missing_in'], c['only_gap'], c['dialogue'], c['dialogue_missing']))
    unused = sorted(n for n in FUNCTIONS if n not in table)
    lines += ['', '%d functions of the compiler\'s table are called by no script of the game.' % len(unused), '']
    lines += effects_section(table)
    # every script
    lines += ['## Every script', '',
              'Referenced by: the records that carry the script and their placed references per master, levelled '
              'lists, the start scripts, StartScript in other scripts and in dialogue results. Conditions: the number '
              'of if, elseif and while tests and what they read.', '']
    for master in MASTERS:
        mine = [r for r in rows if r['master'] == master and r['state'] != 'inert']
        if not mine:
            continue
        lines += ['### %s' % master.split('.')[0], '',
                  '| Script | Area | State | Referenced by | Records | Functions | Conditions | Follows OpenMW\'s fix '
                  '| Why |',
                  '| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
        for r in sorted(mine, key=lambda r: (r['area'], r['id'].casefold())):
            conds = ('%d: %s' % (r['tests'], ', '.join(r['conditions']))) if r['tests'] else '-'
            cells = [r['id'], r['area'], LABELS[r['state']], _refs(r), _records(r),
                     ', '.join(r['functions']) or '-', conds, ', '.join(r.get('openmw', ())) or '-', r['why'] or '-']
            lines.append('| ' + ' | '.join(_cell(x) for x in cells) + ' |')
        lines.append('')
    lines += ['## Not used in the original game', '',
              'Scripts that no object, character, item, dialogue line, start record or other script ever names or '
              'starts, so they never ran in the original game either: the developers\' test and example scripts, '
              'earlier versions replaced by others, and cut content. They stay in the game as they are; the counts '
              'above count only the scripts the original uses, and the data file keeps every script with its state. '
              'The rule, checked for every script here: no record carries the script and no start record, StartScript '
              'or dialogue result names it; or the records that carry it are placed in no cell of the three masters, '
              'no levelled list gives them, no script or dialogue result makes one (PlaceAtPC, PlaceAtMe, PlaceItem, '
              'PlaceItemCell), no container or character holds one, and they are not items a script could hand out '
              '(a script on an item always counts as used). %s' % unused_note(rows), '']
    for master in MASTERS:
        mine = [r for r in rows if r['master'] == master and r['state'] == 'inert']
        if not mine:
            continue
        lines += ['### %s (%s)' % (master.split('.')[0], _n(len(mine))), '', '| Script | Why |', '| --- | --- |']
        for r in sorted(mine, key=lambda r: r['id'].casefold()):
            lines.append('| %s | %s |' % (_cell(r['id']), _cell(r['why'] or '-')))
        lines.append('')
    return doc_toc.render('\n'.join(lines).rstrip('\n') + '\n')


def dumps(doc):
    """The JSON with one script row per line: small enough for the release's text limit (1 MiB) and still a
    readable diff when a row changes."""
    head = {k: v for k, v in doc.items() if k != 'scripts'}
    text = json.dumps(head, indent=1, ensure_ascii=False)
    rows = ',\n'.join('  ' + json.dumps(r, ensure_ascii=False, separators=(',', ':')) for r in doc['scripts'])
    return text[:-2] + ',\n "scripts": [\n' + rows + '\n ]\n}\n'


def write(doc):
    DATA.write_text(dumps(doc), encoding='utf-8', newline='\n')
    OUT.write_text(render(doc), encoding='utf-8', newline='\n')


INTRO = ('One row per script record of the game: what names it, where it stands, which functions it calls and what '
         'its conditions test, and what state AmiWind has it in. The data is measured from the game\'s masters with '
         'the builder\'s own compiler; the page lists record ids, counts and states only. When the work list runs '
         'dry, the scripting work is taken from here row by row, toward the next landmark: every game script playing '
         'as in the original.')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('command', choices=('measure', 'render', 'check'))
    p.add_argument('--data-files')
    p.add_argument('--image-build', help='measure: the run folder of the build whose image is measured; its add-on '
                   'worlds (the presented districts, the rooms of the interior store, the add-ons the scripts stage '
                   'bound) count as in the image. Without it the add-on worlds are not in the image.')
    p.add_argument('--version', help='the AmiWind version the page names (measure; default: the JSON\'s or VERSION)')
    p.add_argument('--updated', help='the date the page names, YYYY-MM-DD (default: today)')
    a = p.parse_args(argv)
    if a.command == 'measure':
        if not a.data_files:
            p.error('measure needs --data-files')
        measured, rows, results = measure(a.data_files, a.image_build)
        old = load() if DATA.is_file() else {}
        doc = {'schema': SCHEMA, 'updated': a.updated or time.strftime('%Y-%m-%d'),
               'version': a.version or old.get('version') or (ROOT / 'VERSION').read_text(encoding='utf-8').strip(),
               'intro': old.get('intro', INTRO), 'measured': measured, 'scripts': rows, 'dialogue_results': results}
        apply_states(doc)
        write(doc)
        st = Counter(r['state'] for r in rows)
        print('wrote %s and %s: %d scripts, %s' % (DATA.relative_to(ROOT), OUT.relative_to(ROOT), len(rows),
                                                  ', '.join('%s %d' % (s, st[s]) for s in STATES)))
        return 0
    doc = load()
    if a.command == 'render':
        if a.updated:
            doc['updated'] = a.updated
        if a.version:
            doc['version'] = a.version
        apply_states(doc)
        bad = problems(doc)
        if bad:
            print('\n'.join('mwscript features: ' + b for b in bad))
            return 1
        write(doc)
        print('wrote %s and %s' % (DATA.relative_to(ROOT), OUT.relative_to(ROOT)))
        return 0
    bad = problems(doc)
    if bad:
        print('\n'.join('mwscript features: ' + b for b in bad[:40]))
        return 1
    if not OUT.is_file() or OUT.read_text(encoding='utf-8') != render(doc):
        print('mwscript features: docs/MWSCRIPT_FEATURES.md is stale: run tools/mwscript_features.py render')
        return 1
    print('mwscript features ok: %d scripts' % len(doc['scripts']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
