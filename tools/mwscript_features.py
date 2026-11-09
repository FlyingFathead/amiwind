#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""MWScript feature tracker (MWSCRIPT-COVERAGE-62): docs/mwscript-features.json is the source, docs/MWSCRIPT_FEATURES.md
is generated. The game parity tracker's twin (tools/game_features.py), one row per script record of the game.

Usage:
  mwscript_features.py measure --data-files DIR   read the masters and compile them as the builder does
                                                  (tools/mwscript), write docs/mwscript-features.json, render the page
  mwscript_features.py render                     recompute every row's state against the interpreter's current
                                                  function table (tools/mwscript/functions.py), rewrite the JSON's
                                                  states and docs/MWSCRIPT_FEATURES.md
  mwscript_features.py check                      validate the JSON and fail if a state or the page is stale

measure needs the game data (run it in the builder container: the masters are read there and nothing of their text
is written; the JSON keeps record ids, counts and function names only). render and check need only the repository.

One row per script record (the winning record of each id over Morrowind, Tribunal and Bloodmoon): its master, its
area (the region of its placed references; an interior takes the region its doors lead out to), what names it
(the records that carry it and their placed references per master, levelled lists, the start scripts, StartScript in
other scripts and in dialogue results), every function it calls and every function its conditions test, and our
state:
  runs               compiles whole, and the build attaches or starts it; or it calls no function at all, so it only
                     sets its own locals, which the dialogue keeps on the speaker without it (MWSCRIPT-COMPLETE-LANDMARK)
  missing-function   calls a function the interpreter does not carry out yet (it compiles; those calls read 0)
  attached-not-run   the game attaches it, but the build does not run it: a hand-written rule carries it
                     (config/mwscript.json), or nothing it does is seen yet (left out of the file)
  not-attached       compiles whole, but nothing in the build attaches or starts it
  not-in-image       its records are placed (or made by the scripts) only in an add-on's world (Mournhold, Solstheim),
                     not in the image yet
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

DATA = ROOT / 'docs' / 'mwscript-features.json'
OUT = ROOT / 'docs' / 'MWSCRIPT_FEATURES.md'
SCHEMA = 'mwscript-features 1'
STATES = ('runs', 'missing-function', 'attached-not-run', 'not-attached', 'not-in-image', 'inert', 'not-converted')
LABELS = {'runs': 'runs', 'missing-function': 'uses a function the interpreter lacks',
          'attached-not-run': 'attached, not run', 'not-attached': 'compiled, not attached',
          'not-in-image': 'only in an add-on world', 'inert': 'named by nothing', 'not-converted': 'not converted'}
SHORT = {'runs': 'Runs', 'missing-function': 'Function missing', 'attached-not-run': 'Attached, not run',
         'not-attached': 'Not attached', 'not-in-image': 'Add-on world', 'inert': 'Named by nothing',
         'not-converted': 'Not converted'}
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


def state_of(row):
    """(state, why) of one script row."""
    if row['error']:
        return 'not-converted', 'does not compile'
    if row['handwritten']:
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
    if row['inert'] and (started or game['placed'].get('Morrowind.esm')):
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
    if placed_addon:
        return 'not-in-image', 'placed only in an add-on world, not in the image yet'
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


def measure(data_files):
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
    binds = bindings(program, compiled)
    # MWSCRIPT-INVENTORY-HITONME-62: the rows of items placed containers and actors hold count apart (held)
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
    for p in placed:
        script = base_of.get(p['id'])
        if not script:
            continue
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
                'date': time.strftime('%Y-%m-%d'), 'bindings': len(binds),
                'start_scripts': len(data.start_scripts), 'placed_scripted': len([p for p in placed
                                                                                  if base_of.get(p['id'])])}
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
    if doc['dialogue'] != dialogue_counts(doc['dialogue_results']):
        out.append('dialogue counts are stale: run tools/mwscript_features.py render')
    for n in list(doc['dialogue_results']['functions']) + [n for g in doc['dialogue_results']['gaps']
                                                          for n in g['notyet']]:
        if n not in FUNCTIONS:
            out.append('dialogue results: function %s is not in tools/mwscript/functions.py' % n)
    if not doc['scripts']:
        out.append('no scripts')
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
        if r['state'] == 'runs':
            continue
        why = 'calls a function the interpreter does not carry out yet' if r['state'] == 'missing-function' \
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


def render(doc):
    import doc_toc
    use(doc)
    rows = doc['scripts']
    st = Counter(r['state'] for r in rows)
    meas = doc['measured']
    lines = ['# MWScript features', '',
             '_Last updated with AmiWind v%s (%s)._' % (doc['version'], long_date(doc['updated'])), '',
             GENERATED, '', doc['intro'], '',
             '**%s of %s scripts run**; %s use a function the interpreter lacks, %s are attached but not run, %s are '
             'compiled but not attached, %s belong to an add-on world not in the image yet, %s are named by nothing '
             '(they never run in the original either), %s are not converted.' % (
                 _n(st['runs']), _n(len(rows)), _n(st['missing-function']), _n(st['attached-not-run']),
                 _n(st['not-attached']), _n(st['not-in-image']), _n(st['inert']), _n(st['not-converted'])), '',
             '| State | Scripts | What it means |', '| --- | ---: | --- |']
    meaning = {'runs': 'compiles whole, and the build attaches it to its objects or starts it (a record that is never '
                       'placed: while the player carries its item, on the actor a levelled list gives, or on the '
                       'object a script places; a script with no function, whose own locals the dialogue keeps on the '
                       'speaker without it, counts as running)',
               'not-in-image': 'compiles whole, but its records are placed (or made by scripts) only in Mournhold or '
                               'Solstheim, which are not in the image yet',
               'inert': 'compiles whole, but no record, start, StartScript or dialogue result names it, or the records '
                        'that name it are never placed and nothing makes them: it never runs in the original either',
               'missing-function': 'compiles, but calls at least one function the interpreter does not carry out yet '
                                   '(those calls do nothing and read 0)',
               'attached-not-run': 'the game attaches it, but the build does not run it: a hand-written rule carries '
                                   'it, or nothing it does is seen yet',
               'not-attached': 'compiles whole, but nothing in the build attaches or starts it: its records are never '
                               'placed, and nothing makes them at run time yet',
               'not-converted': 'does not compile'}
    for s in STATES:
        lines.append('| %s | %s | %s |' % (LABELS[s], _n(st[s]), meaning[s]))
    d = doc['dialogue']
    lines += ['| **All script records** | **%s** | |' % _n(len(rows)), '',
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
                 'startcombat-actor': 'a fight between two actors: not carried out (the combat layer fights the '
                                      'player only)',
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
    lines += why_not_run(rows)
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
              '(the player\'s PositionCell to a known room, a Cast of a cure) and the others are not.', '',
              '| Function | Group | Carried out | Scripts | Uses | In conditions | Missing in | Only gap | Dialogue '
              '| Dialogue missing |',
              '| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for n, c in sorted(table.items(), key=lambda kv: (-(kv[1]['missing_in'] + kv[1]['dialogue_missing']),
                                                      -kv[1]['scripts'], kv[0])):
        fn = FUNCTIONS[n]
        gaps = c['missing_in'] + c['dialogue_missing']
        carried = 'host' if n in HOST else ('yes' if fn.run else 'no')
        if carried == 'no' and c['scripts'] + c['dialogue'] > gaps:
            carried = 'in part'          # some calls compile to their own form (the player's PositionCell)
        elif carried == 'host' and gaps:
            carried = 'host, in part'
        lines.append('| %s | %s | %s | %d | %d | %d | %d | %d | %d | %d |' % (
            n, fn.group, carried, c['scripts'], c['uses'], c['conditions'], c['missing_in'], c['only_gap'],
            c['dialogue'], c['dialogue_missing']))
    unused = sorted(n for n in FUNCTIONS if n not in table)
    lines += ['', '%d functions of the compiler\'s table are called by no script of the game.' % len(unused), '']
    # every script
    lines += ['## Every script', '',
              'Referenced by: the records that carry the script and their placed references per master, levelled '
              'lists, the start scripts, StartScript in other scripts and in dialogue results. Conditions: the number '
              'of if, elseif and while tests and what they read.', '']
    for master in MASTERS:
        mine = [r for r in rows if r['master'] == master]
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
         'dry, the scripting work is taken from here row by row.')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('command', choices=('measure', 'render', 'check'))
    p.add_argument('--data-files')
    p.add_argument('--version', help='the AmiWind version the page names (measure; default: the JSON\'s or VERSION)')
    p.add_argument('--updated', help='the date the page names, YYYY-MM-DD (default: today)')
    a = p.parse_args(argv)
    if a.command == 'measure':
        if not a.data_files:
            p.error('measure needs --data-files')
        measured, rows, results = measure(a.data_files)
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
