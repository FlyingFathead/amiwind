#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The NPC voice and greeting table (AWGL1, id1/npc-voices.lut): every NPC record's voice lines and conversation
greeting, resolved at build time as far as the game's rules are static, for the engine to look up by record
(NPC-GREETINGS-LIBRARY-MUTE-48; docs/NPC_VOICE_TABLE.md).

For every NPC record of Morrowind.esm and every Voice topic of the data (Hello, Idle, Intruder, Thief, Hit, Attack,
Flee, and any other) plus the conversation greeting (the Greeting 0-9 topics in OpenMW's order), each INFO record
is compiled for each NPC with the filter the town residents' conversation greeting uses (mwad.dialogue.Context,
the rule of OpenMW's mwdialogue/filter.cpp): the tests that only read the speaker's record (actor id, race, class,
faction and rank, sex, NotId/NotRace/NotClass/NotFaction, level, reputation, Hello/Fight/Flee/Alarm settings, script locals declared or
not, the cell when the NPC is placed in one cell only) are decided here; an INFO that fails one is never a
candidate for that NPC. What can change while the game runs (globals, journal, items, the dead, the player's state
and faction, the speaker's health and disposition, Random100, the cell otherwise) is compiled into fixed 8-byte
condition records the engine evaluates at greet time (engine/aga/src/aw_glut.c).

Sharing (an inverted index): an entry is one INFO as some NPCs see it (its text with the speaker's defines filled,
its sound, its run-time conditions); its audience is the set of NPCs that see it so. The entries of a topic with
the same audience form one list, in the original's order, cut after its first entry without a run-time condition
(nothing after it can ever be said: first match, OpenMW Filter::search). An NPC's candidates for a topic are the
merge, in the original's order, of the few lists whose audience holds it (a list set); the engine walks that merge
and stops at the first entry whose conditions hold. Equal list sets, topic vectors (an NPC row's set), texts and
sounds are stored once. A sound is the converted voice file's pool name, sound/pool/a<16 hex>.wav, the media
catalogue's own (tools/prepare_media_assets.py sound_output): no voice is converted or stored again.

  python3 tools/greeting_lut.py --data-files DIR --out npc-voices.lut [--report report.json] [--jobs N]
"""
import argparse
import hashlib
import json
import struct
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tools', ROOT / 'src'):
    while str(_p) in sys.path:
        sys.path.remove(str(_p))
    sys.path.insert(0, str(_p))

MAGIC = b'AWGL'
VERSION = 1
NAME = 'npc-voices.lut'
HEADER = 72
# after the magic: version, topics, then the counts of npcs, sets, list sets, list set items, lists, list items,
# entries, conditions, sounds, globals, names, string bytes, text bytes; reset distance, greet seconds, functions
HEADER_FORMAT = '>HH13IHHHH'
NONE16 = 0xFFFF
NONE32 = 0xFFFFFFFF
# The Voice topics the engine knows by name first (engine/aga/src/aw_glut.h AW_GLUT_*), then any other in ID order;
# the conversation greeting (Greeting 0-9) is the last topic, named GREETING.
KNOWN_VOICE_TOPICS = ('hello', 'idle', 'intruder', 'thief', 'hit', 'attack', 'flee')
GREETING = 'greeting'
SCALE = 0.25                     # original units to Quake units (tools/prepare_quake.py SCALE)
NO_CELL = '\0'                   # the cell of an NPC with no single home cell: no cell name starts with it
# Opcodes of a condition record (docs/NPC_VOICE_TABLE.md "Condition records"; operand classes shared with the
# compiled scripts of the roadmap's MWScript step: a global by its index in the globals table, a journal, item,
# dead, local, cell or faction by its index in the names table, a function by the original's SCVR function number).
OP_FUNC, OP_GLOBAL, OP_LOCAL, OP_NOTLOCAL, OP_JOURNAL, OP_ITEM, OP_DEAD, OP_CELL, OP_DISP, OP_PCFACTION, \
    OP_RANDOM100 = range(1, 12)
OPCODES = {'Global': OP_GLOBAL, 'Local': OP_LOCAL, 'NotLocal': OP_NOTLOCAL, 'Journal': OP_JOURNAL, 'Item': OP_ITEM,
           'Dead': OP_DEAD, 'Cell': OP_CELL, 'NotCell': OP_CELL, 'Disposition': OP_DISP, 'PcFaction': OP_PCFACTION}
NAMED = (OP_LOCAL, OP_NOTLOCAL, OP_JOURNAL, OP_ITEM, OP_DEAD, OP_CELL, OP_PCFACTION)
FLOAT = 0x80                     # comparison byte: the value is an IEEE single (FLTV), else a 32-bit integer
ENTRY_LAST = 1                   # entry flags: no run-time condition (its list ends here)
# The functions the engine reads live (aw_glut.c value()); the rest take the fixture value or fail when unknown.
LIVE_FUNCTIONS = ('Health_Percent', 'PcHealthPercent', 'PcHealth', 'TalkedToPc', 'FactionRankDifference')


# ---- the game data

def topic_names(kinds, topics):
    """The topics of the table: the Voice topics (DIAL type 1) present, the engine's known ones first, then GREETING."""
    types = kinds.get('DIAL', {})
    voice = [t for t in topics if types.get(t) == 1]
    return ([t for t in KNOWN_VOICE_TOPICS if t in voice] + sorted(t for t in voice if t not in KNOWN_VOICE_TOPICS)
            + [GREETING])


def topic_infos(kinds, topics, name):
    """The INFO records of a table topic in the original's order (GREETING: Greeting 0 .. 9 in turn)."""
    if name != GREETING:
        return list(topics.get(name, ()))
    from mwad.dialogue import greeting_topics
    return [fields for t in greeting_topics(topics, kinds.get('DIAL')) for fields in topics[t]]


def home_cells(path, kinds):
    """{npc id: cell name} for NPC records placed in exactly one cell (the name the cell filter sees: an interior's
    name; an exterior cell's own name, else its region's name); NPCs placed in several cells or nowhere are absent."""
    from mwad.audit import cell_data
    from mwad.esm import records, subrecords, text
    seen = {}
    npcs = kinds['NPC_']
    for tag, _flags, raw in records(Path(path).read_bytes()):
        if tag != 'CELL':
            continue
        cell = cell_data(list(subrecords(raw)))
        name = cell['name']
        if not cell['flags'] & 1 and not name and cell.get('region'):
            region = kinds.get('REGN', {}).get(cell['region'].casefold(), [])
            name = text(region, 'FNAM') or cell['region']
        for ref in cell['refs']:
            ident = ref.get('id', '').casefold()
            if ident in npcs and not ref.get('deleted'):
                seen.setdefault(ident, {}).setdefault(name.casefold(), name)
    return {i: next(iter(names.values())) for i, names in seen.items()
            if len(names) == 1 and next(iter(names.values()))}


def greet_settings(kinds):
    """(iGreetDistanceMultiplier, reset distance in Quake units, greet duration in seconds) from the GMSTs."""
    from mwad.esm import first

    def value(name, tag, fmt, default):
        raw = first(kinds.get('GMST', {}).get(name.casefold(), []), tag)
        return struct.unpack(fmt, raw)[0] if len(raw) == 4 else default
    return (value('iGreetDistanceMultiplier', 'INTV', '<i', 6), value('fGreetDistanceReset', 'FLTV', '<f', 512.) * SCALE,
            value('iGreetDuration', 'INTV', '<i', 4))


def sound_resolver(data):
    """(resolve, sources, missing): resolve(SNAM) = the pool name ('pool/a<16 hex>.wav' under sound/) of the file the
    media stage converts for it (prepare_media_assets resolve_sound and sound_output: a requested .wav found only as
    .mp3 is that .mp3); sources = the sound sources DATA has (None without DATA: the requested name,
    npc_anim.voice_pool_name); missing collects the SNAMs with no source."""
    import prepare_media_assets as M
    from npc_anim import voice_pool_name
    missing = set()
    if data is None:
        return voice_pool_name, None, missing
    from mwad.audit import BSA
    from mwad.paths import child_ci
    data = Path(data)
    assets = {}
    for name in M.MASTERS:
        archive = child_ci(data, Path(name).with_suffix('.bsa').name, required=False)
        if archive is not None:
            for entry in BSA(archive).entries:
                path = M.key(entry)
                if path.startswith('sound/') and Path(path).suffix in M.AUDIO_SUFFIXES:
                    assets[path] = True
    folder = child_ci(data, 'Sound', required=False)
    if folder is not None:
        for source in folder.rglob('*'):
            if source.is_file() and source.suffix.casefold() in M.AUDIO_SUFFIXES:
                assets[M.key(source.relative_to(data).as_posix())] = True

    def resolve(sound):
        found = M.resolve_sound(sound, assets)
        if not found:
            missing.add(sound.replace(chr(92), '/').casefold())
        return M.sound_output(found)[len('sound/'):] if found else voice_pool_name(sound)
    return resolve, set(assets), missing


# ---- per NPC (the worker unit: a chunk of NPC records)

_MASTER = {}


def load(path):
    """(kinds with the dialogue records, topics) of a master, once per process."""
    key = str(Path(path).resolve())
    if key not in _MASTER:
        from mwad.npc import load_master
        from mwad.dialogue import dialogue_records
        kinds, _cells, topics = load_master(Path(path))
        _MASTER.clear()
        _MASTER[key] = (dialogue_records(Path(path), kinds), topics)
    return _MASTER[key]


def speaker_entries(kinds, infos, ident, home):
    """[(topic index, INFO index, text, SNAM, run-time conditions)] of one NPC: every INFO of every table topic
    (infos: [[fields]] per topic) it can ever say. The cell test is decided here against the NPC's home cell
    (HOME, home_cells()); an NPC placed in several cells or in none has no cell a test could name (NO_CELL: Cell
    fails, NotCell passes). A text keeps its defines for the engine (the speaker's from the NPC row, the player's
    from the game), '' when one of them cannot be filled for this speaker (mwad.dialogue.fill_defines: the line
    is then said without text), so NPCs share entries."""
    from mwad.dialogue import Context, fill_defines
    from mwad.esm import text
    context = Context(kinds, ident, cell=home or NO_CELL)
    out = []
    for t, fields_list in enumerate(infos):
        for i, fields in enumerate(fields_list):
            runtime = context.compile(fields)
            if runtime is None:
                continue
            line = text(fields, 'NAME')
            if '%' in line and fill_defines(kinds, ident, line, home) is None:
                line = ''
            out.append((t, i, line, text(fields, 'SNAM'), tuple(tuple(c) for c in runtime)))
    return out


def audiences(kinds, topics, names, homes, ids, index):
    """{entry key: audience bit mask over the NPC indices INDEX ({id: bit})} of the NPCs IDS, and {id: reason}
    for those left out."""
    infos = [topic_infos(kinds, topics, n) for n in names]
    out, left = {}, {}
    for ident in ids:
        try:
            entries = speaker_entries(kinds, infos, ident, homes.get(ident))
        except (ValueError, KeyError, struct.error) as error:
            left[ident] = str(error)
            continue
        bit = 1 << index[ident]
        for key in entries:
            out[key] = out.get(key, 0) | bit
    return out, left


def _chunk(task):
    """Worker: (master path, home cells, topic names, NPC index, ids) -> audiences()."""
    path, homes, names, index, ids = task
    kinds, topics = load(path)
    return audiences(kinds, topics, names, homes, ids, index)


# ---- the table

DEFINE_FIELDS = ('class', 'race', 'faction', 'rank', 'cell')     # the NPC row's define names, in row order
# NPC row (24 bytes): id string, hello distance, disposition, rank, set, the defines' names, two reserved
NPC_ROW = '>IHBbH5H2H'
NPC_ROW_BYTES = struct.calcsize(NPC_ROW)


def npc_facts(kinds, ident, multiplier, home=None):
    """(hello distance in Quake units, base disposition 0..100, faction rank or -1, {define: display text}) of an
    NPC record: the speaker's text defines as mwad.dialogue.fill_defines fills them (%Name is the entity's name),
    the home cell (HOME, also what the cell test reads) or ''."""
    from mwad.dialogue import speaker, _display, _rank_name
    from mwad.esm import first
    npc = speaker(kinds, ident)
    stats = first(kinds['NPC_'][ident], 'NPDT')
    disposition = stats[44] if len(stats) == 52 else stats[2] if len(stats) == 12 else 50
    hello = min(NONE16 - 1, int(round(npc['ai']['Hello'] * multiplier * SCALE)))
    defines = {'class': _display(kinds, 'CLAS', npc['class']), 'race': _display(kinds, 'RACE', npc['race']),
               'faction': _display(kinds, 'FACT', npc['faction']),
               'rank': _rank_name(kinds, npc['faction'], npc['rank']), 'cell': home or ''}
    return hello, max(0, min(100, disposition)), npc['rank'] if npc['faction'] else -1, defines


def fixture_values(kinds):
    """{function number: value} of the functions whose start-of-game value is known (mwad.dialogue FIXTURE plus
    the starting clothing value); the engine reads the live value of LIVE_FUNCTIONS and these for the rest."""
    from mwad.dialogue import FIXTURE, FUNCTIONS, starting_clothing_value
    values = {FUNCTIONS.index(name): int(value) for name, value in FIXTURE.items() if name in FUNCTIONS}
    values[FUNCTIONS.index('PcClothingModifier')] = starting_clothing_value(kinds)
    return values


class Strings:
    def __init__(self):
        self.data, self.at = bytearray(), {}

    def add(self, value):
        raw = value.encode('cp1252', errors='replace')
        if raw not in self.at:
            self.at[raw] = len(self.data)
            self.data += raw + b'\0'
        return self.at[raw]


def _sort_key(key):
    t, i, line, sound, runtime = key
    return (t, i, line, sound, repr(runtime))


def tables(kinds, names, masks, order, facts, resolve, settings):
    """The deduplicated tables: masks {entry key: audience mask}, order [npc id] (bit i = order[i]),
    facts {id: npc_facts()}."""
    from mwad.dialogue import FUNCTIONS, globals_of
    strings, texts, name_ids, globals_ = Strings(), Strings(), {}, {}
    glob_values = kinds.get('_globals') or globals_of(kinds)
    sounds, conds = {}, []
    topic_offsets = [strings.add(n) for n in names]

    def name_index(value):
        if value not in name_ids:
            name_ids[value] = len(name_ids)
            strings.add(value)
        return name_ids[value]

    def condition(function, variable, op, value):
        if function == 'Global' and variable == 'random100':
            code, operand = OP_RANDOM100, 0
        elif function == 'Global':
            if variable not in globals_:
                globals_[variable] = len(globals_)
                strings.add(variable)
            code, operand = OP_GLOBAL, globals_[variable]
        elif function in OPCODES:
            code = OPCODES[function]
            operand = name_index(variable) if code in NAMED and variable else NONE16 if code in NAMED else 0
            if function == 'Cell':
                value, op = 1, '0'
            elif function == 'NotCell':
                value, op = 0, '0'
        elif function in FUNCTIONS:
            code, operand = OP_FUNC, FUNCTIONS.index(function)
        else:
            raise ValueError('No run-time opcode for condition ' + function)
        is_float = isinstance(value, float)
        raw = struct.pack('>f', value) if is_float else struct.pack('>i', int(value))
        return struct.pack('>BBH', code, int(op) | (FLOAT if is_float else 0), operand) + raw

    # lists: one per (topic, audience), its keys in the original's order, cut after the first unconditional one
    grouped = {}
    for key in sorted(masks, key=_sort_key):
        grouped.setdefault((key[0], masks[key]), []).append(key)
    kept = {}
    for group, keys in grouped.items():
        cut = next((n for n, k in enumerate(keys) if not k[4]), len(keys) - 1)
        kept[group] = keys[:cut + 1]
    entry_keys = sorted({k for keys in kept.values() for k in keys}, key=_sort_key)
    entry_index = {k: n for n, k in enumerate(entry_keys)}
    if len(entry_keys) >= NONE16:
        raise ValueError('Voice table entries past 16 bits')
    entries = []
    for line, sound, runtime in ((k[2], k[3], k[4]) for k in entry_keys):
        first = len(conds)
        if len(runtime) > 255:
            raise ValueError('More than 255 run-time conditions in one INFO')
        for c in runtime:
            conds.append(condition(*c))
        s = NONE16
        if sound:
            pool = resolve(sound)
            s = sounds.setdefault(pool, len(sounds))
        entries.append(struct.pack('>IIHBB', texts.add(line) if line else NONE32, first, s, len(runtime),
                                   0 if runtime else ENTRY_LAST))
    list_rows, list_items, list_of = [], [], {}
    for group in sorted(kept, key=lambda g: (g[0], entry_index[kept[g][0]], g[1])):
        list_of[group] = len(list_rows)
        list_rows.append(struct.pack('>IHH', len(list_items), len(kept[group]), 0))
        list_items += [entry_index[k] for k in kept[group]]
    if len(list_rows) >= NONE16:
        raise ValueError('Voice table lists past 16 bits')
    # list sets: per NPC and topic, the lists whose audience holds it
    per_npc = [[[] for _ in names] for _ in order]
    for (t, mask), number in list_of.items():
        bit = 0
        while mask:
            if mask & 1:
                per_npc[bit][t].append(number)
            mask >>= 1
            bit += 1
    sets_of, set_rows, listsets_of, listset_rows, listset_items = {}, [], {}, [], []
    rows = []
    for n, ident in enumerate(order):
        vector = []
        for t in range(len(names)):
            numbers = tuple(sorted(per_npc[n][t]))
            if not numbers:
                vector.append(NONE16)
                continue
            if numbers not in listsets_of:
                listsets_of[numbers] = len(listset_rows)
                listset_rows.append(struct.pack('>IHH', len(listset_items), len(numbers), 0))
                listset_items += numbers
            vector.append(listsets_of[numbers])
        vector = tuple(vector)
        if vector not in sets_of:
            sets_of[vector] = len(set_rows)
            set_rows.append(struct.pack('>%dH' % len(vector), *vector))
        hello, disposition, rank, defines = facts[ident]
        rows.append(struct.pack(NPC_ROW, strings.add(ident), hello, disposition, rank, sets_of[vector],
                                *(name_index(defines[k]) if defines[k] else NONE16 for k in DEFINE_FIELDS), 0, 0))
    if len(set_rows) >= NONE16 or len(listset_rows) >= NONE16 or len(sounds) >= NONE16:
        raise ValueError('Voice table index past 16 bits')
    return {'topics': topic_offsets, 'npcs': rows, 'sets': set_rows, 'listsets': listset_rows,
            'listset_items': listset_items, 'lists': list_rows, 'list_items': list_items, 'entries': entries,
            'conds': conds, 'sounds': [bytes.fromhex(p[6:22]) for p in sorted(sounds, key=sounds.get)],
            'sound_names': sorted(sounds, key=sounds.get),
            'globals': [struct.pack('>If', strings.add(g), float(glob_values.get(g, 0.)))
                        for g in sorted(globals_, key=globals_.get)],
            'names': [struct.pack('>I', strings.add(n)) for n in sorted(name_ids, key=name_ids.get)],
            'strings': bytes(strings.data), 'texts': bytes(texts.data), 'functions': len(FUNCTIONS),
            'fixture': fixture_values(kinds),
            'settings': settings}


def _u16s(values):
    raw = struct.pack('>%dH' % len(values), *values)
    return raw + bytes(-len(raw) % 4)


def pack(t):
    """The AWGL1 file of tables(): big-endian, every table 4-byte aligned (docs/NPC_VOICE_TABLE.md)."""
    _mult, reset, duration = t['settings']
    count = t['functions']
    strings = t['strings'] + bytes(-len(t['strings']) % 4)
    head = MAGIC + struct.pack(HEADER_FORMAT, VERSION, len(t['topics']), len(t['npcs']), len(t['sets']),
                               len(t['listsets']), len(t['listset_items']), len(t['lists']), len(t['list_items']),
                               len(t['entries']), len(t['conds']), len(t['sounds']), len(t['globals']),
                               len(t['names']), len(strings), len(t['texts']), min(NONE16, int(round(reset))),
                               duration, count, 0)
    head += bytes(HEADER - len(head))
    body = bytearray(head)
    body += b''.join(struct.pack('>I', o) for o in t['topics'])
    body += b''.join(struct.pack('>i', t['fixture'].get(i, 0)) for i in range(count))
    bits = bytearray((count + 7) // 8)
    for i in t['fixture']:
        bits[i >> 3] |= 1 << (i & 7)
    body += bits + bytes(-len(bits) % 4)
    body += b''.join(t['npcs'])
    sets = b''.join(t['sets'])
    body += sets + bytes(-len(sets) % 4)
    body += b''.join(t['listsets']) + _u16s(t['listset_items'])
    body += b''.join(t['lists']) + _u16s(t['list_items'])
    for name in ('entries', 'conds', 'sounds', 'globals', 'names'):
        body += b''.join(t[name])
    body += strings
    body += t['texts']        # last: the engine keeps everything before it in memory and reads a text when said
    return bytes(body)


def read(raw):
    """The tables of an AWGL1 file as Python values (tests, the measurement)."""
    if raw[:4] != MAGIC:
        raise ValueError('Not an AWGL file')
    (version, topics, npcs, sets, listsets, listset_items, lists, list_items, entries, conds, sounds, globals_, names,
     string_bytes, text_bytes, reset, duration, functions, _) = struct.unpack_from(HEADER_FORMAT, raw, 4)
    if version != VERSION:
        raise ValueError('AWGL version %d' % version)
    at = HEADER

    def take(size, align=False):
        nonlocal at
        value = raw[at:at + size]
        at += size + (-size % 4 if align else 0)
        return value
    topic_offsets = struct.unpack('>%dI' % topics, take(4 * topics))
    fixture_raw = struct.unpack('>%di' % functions, take(4 * functions))
    bits = take((functions + 7) // 8, True)
    npc_raw = take(NPC_ROW_BYTES * npcs)
    set_raw = take(2 * topics * sets, True)
    listset_raw, listset_item_raw = take(8 * listsets), take(2 * listset_items, True)
    list_raw, list_item_raw = take(8 * lists), take(2 * list_items, True)
    entry_raw, cond_raw = take(12 * entries), take(8 * conds)
    sound_raw, global_raw, name_raw = take(8 * sounds), take(8 * globals_), take(4 * names)
    strings = take(string_bytes)
    texts = take(text_bytes)
    if at != len(raw):
        raise ValueError('AWGL size mismatch')

    def s(offset, block=strings):
        return None if offset == NONE32 else block[offset:block.index(b'\0', offset)].decode('cp1252')

    def u16(data):
        return list(struct.unpack('>%dH' % (len(data) // 2), data))
    out = {'topics': [s(o) for o in topic_offsets], 'reset': reset, 'duration': duration,
           'fixture': {i: v for i, v in enumerate(fixture_raw) if bits[i >> 3] >> (i & 7) & 1},
           'sounds': [sound_raw[i:i + 8].hex() for i in range(0, len(sound_raw), 8)],
           'globals': [(s(o), v) for o, v in struct.iter_unpack('>If', global_raw)],
           'names': [s(o) for (o,) in struct.iter_unpack('>I', name_raw)], 'bytes': len(raw),
           'listsets': [struct.unpack_from('>IH', listset_raw, i) for i in range(0, len(listset_raw), 8)],
           'listset_items': u16(listset_item_raw),
           'lists': [struct.unpack_from('>IH', list_raw, i) for i in range(0, len(list_raw), 8)],
           'list_items': u16(list_item_raw),
           'entries': [struct.unpack_from('>IIHBB', entry_raw, i) for i in range(0, len(entry_raw), 12)],
           'conds': [struct.unpack_from('>BBHi', cond_raw, i) for i in range(0, len(cond_raw), 8)],
           'sets': [struct.unpack_from('>%dH' % topics, set_raw, i) for i in range(0, len(set_raw), 2 * topics)]}
    out['npcs'] = {}
    for i in range(0, len(npc_raw), NPC_ROW_BYTES):
        ident, hello, disposition, rank, vset, *rest = struct.unpack_from(NPC_ROW, npc_raw, i)
        out['npcs'][s(ident)] = {'hello': hello, 'disposition': disposition, 'rank': rank, 'set': vset,
                                 'defines': {k: None if n == NONE16 else out['names'][n]
                                             for k, n in zip(DEFINE_FIELDS, rest)}}
    out['string'] = s
    out['text'] = lambda offset: s(offset, texts)
    out['resident_bytes'] = len(raw) - text_bytes
    return out


def candidates(table, ident, topic):
    """The entry indices an NPC's topic walks, in the original's order (the merge of its list set, as the engine
    walks it), up to and including the first entry without a run-time condition."""
    npc = table['npcs'][ident]
    listset = table['sets'][npc['set']][table['topics'].index(topic)]
    if listset == NONE16:
        return []
    first, count = table['listsets'][listset]
    merged = sorted(e for number in table['listset_items'][first:first + count]
                    for e in table['list_items'][table['lists'][number][0]:
                                                 table['lists'][number][0] + table['lists'][number][1]])
    out = []
    for e in merged:
        out.append(e)
        if table['entries'][e][4] & ENTRY_LAST:
            break
    return out


def lines(table, ident, topic):
    """[(text, sound hex or None, [(op, cmp, operand, value)])] an NPC's topic walks (candidates())."""
    out = []
    for e in candidates(table, ident, topic):
        text, cond, sound, n, _ = table['entries'][e]
        out.append((table['text'](text), None if sound == NONE16 else table['sounds'][sound],
                    table['conds'][cond:cond + n]))
    return out


def plan_npcs(kinds, homes=None):
    """([NPC id] in table order (by the id's bytes), {id: npc_facts()}, {id: reason left out})."""
    multiplier = greet_settings(kinds)[0]
    homes = homes or {}
    order, facts, left = [], {}, {}
    for ident in sorted(kinds['NPC_'], key=lambda i: i.encode('cp1252', errors='replace')):
        try:
            if not ident.isascii():
                raise ValueError('non-ASCII record id')
            facts[ident] = npc_facts(kinds, ident, multiplier, homes.get(ident))
            order.append(ident)
        except (ValueError, KeyError, struct.error, IndexError) as error:
            left[ident] = str(error)
    return order, facts, left


def build(kinds, topics, homes=None, resolve=None, masks=None, left=None):
    """(AWGL1 bytes, report) from loaded records (kinds with the dialogue records, topics); masks: the audiences
    already made (the worker pool's, with left), else made here."""
    from npc_anim import voice_pool_name
    resolve = resolve or voice_pool_name
    homes = homes or {}
    names = topic_names(kinds, topics)
    settings = greet_settings(kinds)
    order, facts, early = plan_npcs(kinds, homes)
    left = dict(early, **(left or {}))
    index = {i: n for n, i in enumerate(order)}
    if masks is None:
        masks, gone = audiences(kinds, topics, names, homes, order, index)
        left.update(gone)
    keep = [i for i in order if i not in left]
    if len(keep) != len(order):
        # renumber the audiences onto the NPCs kept
        remap = {index[i]: n for n, i in enumerate(keep)}
        masks = {k: sum(1 << remap[b] for b in range(len(order)) if m >> b & 1 and b in remap)
                 for k, m in masks.items()}
        masks = {k: m for k, m in masks.items() if m}
    t = tables(kinds, names, masks, keep, facts, resolve, settings)
    raw = pack(t)
    report = {'format': 'AWGL1', 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
              'npcs': len(t['npcs']), 'sets': len(t['sets']), 'list_sets': len(t['listsets']),
              'lists': len(t['lists']), 'entries': len(t['entries']), 'conditions': len(t['conds']),
              'sounds': len(t['sounds']), 'globals': len(t['globals']), 'names': len(t['names']),
              'string_bytes': len(t['strings']), 'text_bytes': len(t['texts']),
              'resident_bytes': len(raw) - len(t['texts']),
              'topics': names, 'sound_names': t['sound_names'], 'left_out': left,
              'table_bytes': {k: sum(len(r) for r in t[k]) for k in ('npcs', 'sets', 'listsets', 'lists', 'entries',
                                                                      'conds', 'sounds', 'globals', 'names')}}
    report['table_bytes'].update(listset_items=2 * len(t['listset_items']), list_items=2 * len(t['list_items']),
                                 strings=len(t['strings']), texts=len(t['texts']))
    return raw, report


def build_master(path, data=None, jobs=1, resolver=None):
    """(AWGL1 bytes, report) of a master file, the NPC records compiled in chunks on JOBS processes; resolver:
    sound_resolver(data), when already made."""
    from build_parallel import ordered_map
    t0 = time.time()
    kinds, topics = load(path)
    homes = home_cells(path, kinds)
    names = topic_names(kinds, topics)
    order, _facts, _left = plan_npcs(kinds, homes)
    index = {i: n for n, i in enumerate(order)}
    size = max(16, len(order) // max(1, jobs * 4))
    chunks = [order[i:i + size] for i in range(0, len(order), size)]
    print('Voice table: %d NPC records, %d topics (%s), %d units on %d jobs' % (
        len(order), len(names), ', '.join(names), len(chunks), jobs), flush=True)
    masks, left, done = {}, {}, 0
    for out, gone in ordered_map(_chunk, [(str(path), homes, names, index, c) for c in chunks], jobs=max(1, jobs),
                                 cost=lambda task: len(task[4])):
        for key, mask in out.items():
            masks[key] = masks.get(key, 0) | mask
        left.update(gone)
        done += 1
        if done % max(1, len(chunks) // 8) == 0 or done == len(chunks):
            print('Voice table: %d/%d units' % (done, len(chunks)), flush=True)
    resolve, available, missing = resolver or sound_resolver(data)
    raw, report = build(kinds, topics, homes, resolve, masks, left)
    report['home_cells'] = len(homes)
    # sounds named whose source file the data does not have: the engine shows the line and stays quiet
    report['missing_sources'] = sorted(missing) if available is not None else None
    report['seconds'] = round(time.time() - t0, 1)
    print('Voice table: %d NPCs, %d sets, %d list sets, %d lists, %d entries, %d conditions, %d sounds, %d bytes '
          '(%.1f s)' % (report['npcs'], report['sets'], report['list_sets'], report['lists'], report['entries'],
                        report['conditions'], report['sounds'], report['bytes'], report['seconds']), flush=True)
    return raw, report


def image_step(data, id1, out=None, jobs=1):
    """The image step: id1/npc-voices.lut from DATA's Morrowind.esm, through the unit cache (pass_cache.UnitCache,
    keyed by the master's SHA-256, the sound sources the data offers and this module's sources); the report beside
    it in OUT (npc-voice-table.json). Returns the report."""
    from build_scratch import scratch_dir
    from mwad.esm import sha256_file
    from mwad.paths import child_ci
    from pass_cache import UnitCache
    master = child_ci(Path(data), 'Morrowind.esm')
    resolver = sound_resolver(data)
    inputs = {'master_sha256': sha256_file(master),
              'sound_sources_sha256': hashlib.sha256('\n'.join(sorted(resolver[1] or ())).encode()).hexdigest()}
    cache = UnitCache.open('npc-voice-table', {'format': 'AWGL1'}, __file__)
    target = Path(id1) / NAME
    t0 = time.time()
    print('Voice table: start (1 unit cache lookup, then %d jobs if built)' % jobs, flush=True)
    with scratch_dir(prefix='voice-table-', near=out if out is not None else Path(id1).parent,
                     keep_on_failure=False) as tmp:
        folder = Path(tmp) / 'unit'
        row = cache.restore_unit(inputs, folder) if cache else None
        if row is not None:
            report = json.loads((folder / 'report.json').read_text(encoding='utf-8'))
            raw = (folder / NAME).read_bytes()
            report['reused'] = True
        else:
            raw, report = build_master(master, data, jobs, resolver)
            folder.mkdir(parents=True)
            (folder / NAME).write_bytes(raw)
            (folder / 'report.json').write_text(json.dumps(report, indent=1, sort_keys=True) + '\n', encoding='utf-8',
                                                newline='\n')
            if cache:
                cache.store_unit(inputs, {'bytes': len(raw)}, folder)
            report['reused'] = False
    if hashlib.sha256(raw).hexdigest() != report['sha256']:
        raise ValueError('Voice table: SHA-256 differs from its report')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    if out is not None:
        Path(out).mkdir(parents=True, exist_ok=True)
        (Path(out) / 'npc-voice-table.json').write_text(json.dumps(report, indent=1, sort_keys=True) + '\n',
                                                        encoding='utf-8', newline='\n')
    print('Voice table: %s %s, %d bytes, %d NPCs (took %.1f s, %s)' % (
        'reused' if report['reused'] else 'built', NAME, len(raw), report['npcs'], time.time() - t0,
        '1 core' if report['reused'] else '%d jobs' % jobs), flush=True)
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--data-files', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True, help='the AWGL1 file to write')
    p.add_argument('--report', type=Path)
    p.add_argument('--jobs', type=int, default=1)
    a = p.parse_args(argv)
    from mwad.paths import child_ci
    raw, report = build_master(child_ci(a.data_files, 'Morrowind.esm'), a.data_files, a.jobs)
    a.out.write_bytes(raw)
    if a.report:
        a.report.write_text(json.dumps(report, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
