# SPDX-License-Identifier: GPL-3.0-only
"""Compile every script of the game data into one program (codegen.Program + per-script code)."""
from collections import Counter

from .codegen import (Program, ScriptCompiler, CompileError, SCRIPT_BROKEN, SCRIPT_START, SCRIPT_GLOBAL,
                      SCRIPT_HANDWRITTEN, SCRIPT_INERT, SCRIPT_DIALOGUE, EFFECT_OPS, effect_op)  # noqa: F401 (EFFECT_OPS: callers)
from .awms import CARRIED
from .functions import lookup
from .lexer import LexError
from .parser import Parser, ParseError

BIND_INTERIOR = 1        # the reference stands in an interior cell (cell = interior name string)
BIND_ACTOR = 2           # an NPC or creature: found in game by its aw_ref edict
BIND_EDICT = 4           # another kind the maps keep as an edict (doors, containers, activators with aw_ref)
# MWSCRIPT-INVENTORY-HITONME-62: an item held by a placed container, NPC or creature (OpenMW 0.51 mwworld/
# localscripts.cpp addCell: the scripts of the items in the active cells' containers and actors run, each on its item).
# Its row's reference is HELD_KEY(holder, n): bit 30 and the item's ordinal among the holder's scripted items in bits
# 24-29 above the holder's own reference, so the rows sort after every placed reference; the cell and position are
# the holder's. The engine attaches it while the holder's area is loaded and the holder still has the item.
BIND_HELD = 8
HELD_BIT = 0x40000000
HELD_PER_HOLDER = 64


def held_key(holder, n):
    if not 0 < holder <= 0xFFFFFF or not 0 <= n < HELD_PER_HOLDER:
        raise ValueError('held item key out of range: %r %r' % (holder, n))
    return HELD_BIT | (n << 24) | holder


class Compiled:
    __slots__ = ('ident', 'name', 'master', 'code', 'flags', 'nlocals', 'calls', 'warnings', 'error', 'max_depth',
                 'source_bytes', 'original_bytes', 'ops', 'loops', 'notyet')


def handwritten_patterns(config=None):
    """The script name patterns the engine carries by hand today (config/mwscript.json 'handwritten')."""
    import json
    from pathlib import Path
    path = Path(config) if config else Path(__file__).resolve().parents[2] / 'config' / 'mwscript.json'
    if not path.is_file():
        return ()
    return tuple(p.casefold() for p in json.loads(path.read_text(encoding='utf-8'))['handwritten']['patterns'])


def compile_program(data, media=None, scripts=None, handwritten=None, rooms=None):
    """(Program, [Compiled]) for every script of DATA (the winning record of each id), in table order.
    SCRIPTS: compile these records instead (one master's own records, for the per-master measurement).
    HANDWRITTEN: name patterns marked SCRIPT_HANDWRITTEN (None: config/mwscript.json).
    ROOMS: the room maps the player's PositionCell can load (rooms.room_table; None: the repo's own lists)."""
    from fnmatch import fnmatchcase
    from .rooms import room_table
    patterns = handwritten_patterns() if handwritten is None else tuple(p.casefold() for p in handwritten)
    program = Program(data, media, scripts)
    program.rooms = room_table() if rooms is None else rooms
    parsed = {}
    globals_ = {k: v[0] for k, v in data.globals.items()}
    if scripts is not None:
        # every script's locals, for member access into scripts outside this list
        for ident, s in data.scripts.items():
            program.script_locals[ident] = {n: v for n, v in Parser(s.text, globals_).locals.items()}
    # pass 1: parse everything, so member access can see every script's locals
    for ident, row in zip(program.scripts.index, program.scripts.rows):
        s = row['script']
        p = Parser(s.text, globals_)
        try:
            tree = p.script()
            parsed[ident] = (tree, p, None)
        except (ParseError, LexError) as error:
            parsed[ident] = (None, p, str(error))
        program.script_locals[ident] = {name: (letter, slot) for name, (letter, slot) in p.locals.items()}
    out = []
    starts = set(data.start_scripts)
    for index, (ident, row) in enumerate(zip(program.scripts.index, program.scripts.rows)):
        s = row['script']
        tree, p, error = parsed[ident]
        c = Compiled()
        c.ident, c.name, c.master = ident, s.id, s.master
        c.source_bytes, c.original_bytes = s.source_bytes, s.original_bytes
        c.warnings = list(p.warnings)
        c.nlocals = len(p.locals)
        c.error = error
        c.loops = 0
        if c.nlocals > 255:
            c.error = c.error or 'more than 255 locals'
        if c.error is None:
            sc = ScriptCompiler(program, ident, tree, program.script_locals[ident], c.warnings)
            try:
                c.code = sc.compile()
                c.flags, c.calls, c.max_depth, c.ops, c.loops = sc.flags, sc.calls, sc.e.max_depth, sc.e.ops, sc.loops
                c.notyet = sc.notyet_names
            except CompileError as e:
                c.error = str(e)
        if c.error is not None:
            c.code, c.flags, c.calls, c.max_depth, c.ops = b'\x00', SCRIPT_BROKEN, list(p.used), 0, [(0, 'END')]
            c.notyet = [n for n in p.used if not lookup(n).run]
        if row.get('dialogue'):
            c.flags |= SCRIPT_DIALOGUE
        if ident in starts:
            c.flags |= SCRIPT_START
        if any(fnmatchcase(ident, p) for p in patterns):
            c.flags |= SCRIPT_HANDWRITTEN
        out.append(c)
        row['compiled'] = c
    for row, c in zip(program.scripts.rows, out):
        if row.get('started'):
            c.flags |= SCRIPT_GLOBAL
    # inert scripts: no effect op, and no other script reads their values (GETM on an object or script running it)
    from .awms import decode
    read_by_others = set()
    for c in out:
        if c.error is not None:
            continue
        for _, name, args in decode(c.code):
            if name == 'GETM':
                obj = program.objects.rows[args[0]]
                if obj['script'] is not None:
                    read_by_others.add(obj['script'])
    dialogue_read = dialogue_read_slots(data, program)
    for index, c in enumerate(out):
        if c.error is None and index not in read_by_others and \
                not any(effect_op(name, args) or (name in ('SETL', 'SETLS') and args[0] in dialogue_read.get(c.ident, ()))
                        for _, name, args in decode(c.code)):
            c.flags |= SCRIPT_INERT
    return program, out


def dialogue_read_slots(data, program):
    """MWSCRIPT-INERT-SEEN-62: {script ident: {slot}} of the locals a dialogue filter reads (an INFO's Local or NotLocal
    condition, read from the speaker's attached script: engine aw_mwhost.c live_local), for the scripts an NPC or a
    creature record carries. A script that sets one is seen through what the speaker says (the Temple stewards'
    completedGraces, Baren Alen's land deed), so it is not inert."""
    names = getattr(data, 'dialogue_locals', None) or set()
    if not names:
        return {}
    speakers = {script for tag, script in data.bases.values() if tag in ('NPC_', 'CREA') and script}
    out = {}
    for ident in speakers:
        slots = {slot for name, (letter, slot) in program.script_locals.get(ident, {}).items()
                 if name.casefold() in names}
        if slots:
            out[ident] = slots
    return out


def bindings(program, compiled=None):
    """The placed references that carry a script, sorted by reference number:
    [{'reference', 'script' (index), 'flags', 'cell' (x, y) or interior string index, 'position' (source units)}].
    COMPILED: leave out the references whose script is inert today (dead weight; back when it is compiled again)."""
    rows = []
    for ref in program.data.references:
        key = ref['script']
        if key not in program.scripts.index:
            continue
        if compiled is not None and compiled[program.scripts.index[key]].flags & SCRIPT_INERT:
            continue
        flags = 0
        if ref['interior']:
            flags |= BIND_INTERIOR
        if ref['type'] in ('NPC_', 'CREA'):
            flags |= BIND_ACTOR
        elif ref['type'] in ('DOOR', 'CONT', 'ACTI'):
            flags |= BIND_EDICT
        rows.append({'reference': ref['reference'], 'script': program.scripts.index[key], 'flags': flags,
                     # an interior: its stable number, as the room map's worldspawn _aw_cell_int carries it
                     'cell': program.data.interior_numbers.get(ref['cell'].casefold(), 0) if ref['interior']
                     else tuple(ref['cell']),
                     'position': [int(round(v)) for v in ref['position']], 'id': ref['id'], 'type': ref['type']})
    rows.extend(held_bindings(program, compiled))
    rows.sort(key=lambda r: r['reference'])
    seen = set()
    unique = []
    for r in rows:
        if r['reference'] in seen:
            continue
        seen.add(r['reference'])
        unique.append(r)
    return unique


def held_bindings(program, compiled=None):
    """BIND_HELD rows (MWSCRIPT-INVENTORY-HITONME-62): one per placed Morrowind.esm container, NPC or creature and each
    distinct carryable item of its record (NPCO) whose record names a compiled script that is not inert, in the
    record's order; the holder's cell and position. A levelled item list in a holder names no item record: none."""
    data = program.data
    holdings = getattr(data, 'holdings', None) or {}
    rows = []
    for ref in getattr(data, 'holder_refs', None) or ():
        items, seen = [], set()
        for item in holdings.get(ref['id'], ()):
            tag, script = data.bases.get(item, (None, ''))
            if tag not in CARRIED or not script or script not in program.scripts.index or (item, script) in seen:
                continue
            index = program.scripts.index[script]
            if compiled is not None and compiled[index].flags & SCRIPT_INERT:
                continue
            seen.add((item, script))
            items.append((item, index))
        if not 0 < ref['reference'] <= 0xFFFFFF:
            continue
        for n, (item, index) in enumerate(items[:HELD_PER_HOLDER]):
            flags = BIND_HELD | (BIND_INTERIOR if ref['interior'] else 0) | \
                (BIND_ACTOR if ref['type'] in ('NPC_', 'CREA') else BIND_EDICT)
            rows.append({'reference': held_key(ref['reference'], n), 'script': index, 'flags': flags,
                         'cell': data.interior_numbers.get(ref['cell'].casefold(), 0) if ref['interior']
                         else tuple(ref['cell']),
                         'position': [int(round(v)) for v in ref['position']], 'id': item, 'type': 'HELD',
                         'holder': ref['reference']})
    return rows


def usage(compiled):
    """Counter of function names over every compiled script (each use counted)."""
    total = Counter()
    for c in compiled:
        total.update(c.calls)
    return total


def groups_of(c):
    return {lookup(name).group for name in set(c.calls)}
