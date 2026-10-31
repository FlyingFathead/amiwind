#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The dialogue table (AWDL1, id1/dialogue.lut): every NPC record's conversation topics, their answers in the
original's order with the run-time conditions as the voice table's 8-byte condition records, the answers' result
scripts and hyperlinks, and every quest's journal entries (DIALOGUE-57; docs/DIALOGUE_DESIGN.md).

The method is the voice table's (tools/greeting_lut.py): for every NPC record and every Topic and Persuasion INFO of
Morrowind.esm, the tests that read only the speaker's record are decided here (mwad.dialogue.Context.compile, the rule
of OpenMW's mwdialogue/filter.cpp, with Choice left for run time); what can change while the game runs becomes
condition records with the voice table's opcodes, so greetings, voice lines and topics share one evaluator
(engine/aga/src/aw_glut.c AW_GlutCond). An entry is one INFO with the run-time conditions some NPCs see; its audience
is the set of those NPCs. The entries of a topic with the same audience form one list, in the original's order, cut
after its first entry without a run-time condition (first match, OpenMW Filter::search); an NPC's candidates for a
topic are the merge of the few lists whose audience holds it (a list set). An NPC row lists its topics with their
list sets; equal rows, list sets, texts and scripts are stored once.

Only a small index stays in memory on the Amiga (the resident part: topic rows, NPC row offsets, the fixture,
globals and names); the rows, lists, entries, conditions, links, journal, topic names, scripts and texts are read
from the file per conversation (docs/DIALOGUE_DESIGN.md "Plan").

  python3 tools/dialogue_lut.py --data-files DIR --out dialogue.lut [--report report.json] [--jobs N]
"""
import argparse
import hashlib
import json
import re
import struct
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tools', ROOT / 'src'):
    while str(_p) in sys.path:
        sys.path.remove(str(_p))
    sys.path.insert(0, str(_p))

import greeting_lut as G  # noqa: E402  (the voice table: NPC order, condition opcodes, strings)

MAGIC = b'AWDL'
VERSION = 1
NAME = 'dialogue.lut'
HEADER = 96
# after the magic: version, functions; then the counts of topics, npcs, row bytes, list sets, list set items, lists,
# list items, entries, conditions, globals, names, links, quests, journal entries, string bytes, topic string
# bytes, script bytes, text bytes; then the SHA-256 prefix of the NPC order (the voice table's rows), the topic
# "Info Refusal" (NONE16 none) and three zeros
HEADER_FORMAT = '>HH18I8sHHHH'
INFO_REFUSAL = 'info refusal'
LOCAL_FLOAT = 0x4000             # a Local / NotLocal operand: the slot in the speaker's script, this bit for a float
# The game settings the engine's disposition reads (engine/aga/src/aw_dial.h AW_DIAL_SET_*, in this order; the rule
# of OpenMW's MechanicsManager::getDerivedDisposition, our own code), from the master's GMST records (0 when absent,
# listed in the report)
SETTINGS = ('fDispRaceMod', 'fDispPersonalityMult', 'fDispPersonalityBase', 'fDispFactionRankMult',
            'fDispFactionRankBase', 'fDispFactionMod', 'fDispCrimeMod', 'fDispDiseaseMod', 'fDispWeaponDrawn')
FACTION_ID = 32                  # a faction row: its folded id, NUL padded


def settings_of(kinds):
    """([float] in SETTINGS order, [missing names]) from the GMST records."""
    from mwad.esm import first
    values, missing = [], []
    for name in SETTINGS:
        raw = first(kinds.get('GMST', {}).get(name.casefold(), []), 'FLTV')
        if len(raw) == 4:
            values.append(struct.unpack('<f', raw)[0])
        else:
            values.append(0.0)
            missing.append(name)
    return values, missing


def factions_of(kinds):
    """([folded faction id] sorted by bytes, [(faction, other, reaction)]) of the FACT records (their ANAM/INTV
    reaction pairs; a faction absent from another's list reacts 0)."""
    from mwad.esm import string
    ids = sorted(kinds.get('FACT', {}), key=lambda k: k.encode('cp1252', 'replace'))
    ids = [i for i in ids if len(i.encode('cp1252', 'replace')) < FACTION_ID]
    index = {k: n for n, k in enumerate(ids)}
    reactions = []
    for n, k in enumerate(ids):
        other = None
        for tag, data in kinds['FACT'][k]:
            if tag == 'ANAM':
                other = string(data, 'ANAM', errors='replace').casefold()
            elif tag == 'INTV' and other is not None and len(data) == 4:
                if other in index:
                    reactions.append((n, index[other], max(-32768, min(32767, struct.unpack('<i', data)[0]))))
                other = None
    return ids, sorted(reactions)


RANKS = 10                       # a faction's rank names (the original has at most ten)


def rank_names(kinds, ids):
    """[[RANKS names]] of the factions IDS (FACT RNAM in order, '' past the last)."""
    from mwad.esm import string
    out = []
    for k in ids:
        names = [string(d, 'RNAM', errors='replace') for tag, d in kinds['FACT'][k] if tag == 'RNAM'][:RANKS]
        out.append(names + [''] * (RANKS - len(names)))
    return out
# The topics a new character knows: the ones the census captain's answers add (their result scripts' AddTopic; the
# original's character generation, which every new game passes; Morrowind.esm: Caius Cosades, South Wall, latest
# rumors, little advice, little secret, my trade, services, someone in particular, specific place). Read from the
# data, never listed by hand.
START_SPEAKER = 'chargen captain'
ADD_TOPIC = re.compile(r'(?im)^[ \t]*addtopic[ \t,]*"([^"\r\n]+)"')


def start_topics(topics, names):
    """[table topic index] the start speaker's result scripts add, in table order."""
    from mwad.esm import text
    found = set()
    for infos in topics.values():
        for fields in infos:
            if text(fields, 'ONAM').casefold() == START_SPEAKER:
                found.update(m.group(1).strip().casefold() for m in ADD_TOPIC.finditer(text(fields, 'BNAM')))
    return sorted(names.index(n) for n in found if n in names)
TOPIC_ROW = '>IBBH'              # topic name offset (topic strings), name length, kind, 0
ENTRY_ROW = '>IIIIHBB'           # text, first condition, script, first link (NONE32 none), links, conditions, flags
LIST_ROW = '>IHH'                # first item, items, 0 (list sets and lists)
QUEST_ROW = '>IIHH'              # quest id (topic strings), first journal entry, entries, 0
JOURNAL_ROW = '>HBBI'            # index, flags, 0, text offset
KIND_TOPIC, KIND_PERSUASION = 0, 3
DIAL_TYPES = (KIND_TOPIC, KIND_PERSUASION)
DIAL_JOURNAL = 4
QUEST_NAME, QUEST_FINISHED, QUEST_RESTART = 1, 2, 4
ENTRY_LAST = G.ENTRY_LAST
NONE16, NONE32 = G.NONE16, G.NONE32
NO_CELL = G.NO_CELL


# ---- the game data

def dial_names(path):
    """{folded topic: (display name, DIAL type)} of a master, in file order (the topics' own spelling)."""
    from mwad.esm import first, records, subrecords, text
    out = {}
    for tag, _flags, raw in records(Path(path).read_bytes()):
        if tag == 'DIAL':
            fields = list(subrecords(raw))
            name = text(fields, 'NAME')
            kind = first(fields, 'DATA')
            out.setdefault(name.casefold(), (name, kind[0] if kind else None))
    return out


def table_topics(dials):
    """The table's topics: Topic and Persuasion DIALs, sorted by the folded name's bytes (OpenMW lists topics by name
    without case; the engine's topic list is this order)."""
    return sorted((k for k, (_n, kind) in dials.items() if kind in DIAL_TYPES),
                  key=lambda k: k.encode('cp1252', 'replace'))


from mwad.dialogue import Context as _Context, RUNTIME as _RUNTIME  # noqa: E402


class TopicContext(_Context):
    """mwad.dialogue.Context for a conversation topic: Choice is decided while the game runs (the greeting's
    context fixes it to 'no choice open')."""

    def __init__(self, kinds, ident, cell):
        _Context.__init__(self, kinds, ident, cell=cell)

    def static(self, function, variable, op, value):
        if function == 'Choice':
            return _RUNTIME
        return _Context.static(self, function, variable, op, value)


def info_index(topics, names):
    """[(generic [(i, fields)], {actor: [(i, fields)]})] per table topic: the INFOs that name one actor kept apart,
    so an NPC compiles only its own and the generic ones (11,594 of 13,082 Topic INFOs name one actor)."""
    from mwad.esm import text
    out = []
    for name in names:
        generic, by_actor = [], {}
        for i, fields in enumerate(topics.get(name, ())):
            actor = text(fields, 'ONAM').casefold()
            (by_actor.setdefault(actor, []) if actor else generic).append((i, fields))
        out.append((generic, by_actor))
    return out


def script_slots(kinds, ident):
    """{folded local name: (type letter, slot)} of the speaker's script, by the script compiler's own declaration
    reader (tools/mwscript: the interpreter's slots); {} without a script."""
    from mwad.esm import text
    from mwad.dialogue import speaker
    from mwscript.lexer import tokenize
    from mwscript.parser import declarations
    script = speaker(kinds, ident)['script']
    source = text(kinds.get('SCPT', {}).get(script, []), 'SCTX') if script else ''
    return declarations(tokenize(source, [])) if source else {}


def with_slots(runtime, slots):
    """The run-time conditions with each Local / NotLocal variable named by its slot in the speaker's script
    ('name#slot', '#f' for a float local), so the engine reads the speaker's script locals without names."""
    out = []
    for c in runtime:
        if c[0] in ('Local', 'NotLocal') and c[1] in slots:
            letter, slot = slots[c[1]]
            c = (c[0], '%s#%d%s' % (c[1], slot, 'f' if letter == 'f' else ''), c[2], c[3])
        out.append(tuple(c))
    return tuple(out)


def speaker_entries(kinds, index, ident, home):
    """[(topic index, INFO index, run-time conditions)] of one NPC: every table INFO it can ever say."""
    context = TopicContext(kinds, ident, home or NO_CELL)
    slots = script_slots(kinds, ident) if context.locals else {}
    out = []
    for t, (generic, by_actor) in enumerate(index):
        own = by_actor.get(ident)
        candidates = sorted(generic + own, key=lambda x: x[0]) if own else generic
        for i, fields in candidates:
            runtime = context.compile(fields)
            if runtime is not None:
                out.append((t, i, with_slots(runtime, slots)))
    return out


_INDEX = {}


def _chunk(task):
    """Worker: (master path, home cells, topic names, NPC bit index, ids) -> ({entry key: mask}, {id: reason})."""
    path, homes, names, bits, ids = task
    kinds, topics = G.load(path)
    key = (str(path), tuple(names))
    if key not in _INDEX:
        _INDEX.clear()
        _INDEX[key] = info_index(topics, names)
    index = _INDEX[key]
    out, left = {}, {}
    for ident in ids:
        try:
            entries = speaker_entries(kinds, index, ident, homes.get(ident))
        except (ValueError, KeyError, struct.error) as error:
            left[ident] = str(error)
            continue
        bit = 1 << bits[ident]
        for k in entries:
            out[k] = out.get(k, 0) | bit
    return out, left


# ---- hyperlinks and the journal

def link_finder(display):
    """A function text -> [topic index] of the topic names a text names (case-insensitive, longest first, not inside a
    word, each topic once, in the order they appear); DISPLAY: the Topic kind's names by table index (None for the
    others). The rule of OpenMW's keyword search over the known topics (mwdialogue/keywordsearch.hpp), our own code."""
    names = sorted(((n.casefold(), t) for t, n in enumerate(display) if n), key=lambda x: -len(x[0]))
    if not names:
        return lambda line: []
    by = dict(names)
    pattern = re.compile(r'(?<![0-9a-z])(?:%s)(?![0-9a-z])' % '|'.join(re.escape(n) for n, _ in names))

    def find(line):
        seen, out = set(), []
        for m in pattern.finditer(line.casefold()):
            t = by[m.group(0)]
            if t not in seen:
                seen.add(t)
                out.append(t)
        return out
    return find


def journal(topics, dials):
    """[(quest id, [(index, flags, text)])] of the Journal DIALs, quests sorted by the folded id's bytes, entries
    sorted by index (flags: QUEST_NAME, QUEST_FINISHED, QUEST_RESTART)."""
    from mwad.esm import first, text
    out = []
    for key in sorted((k for k, (_n, kind) in dials.items() if kind == DIAL_JOURNAL),
                      key=lambda k: k.encode('cp1252', 'replace')):
        rows = []
        for fields in topics.get(key, ()):
            raw = first(fields, 'DATA')
            index = struct.unpack_from('<i', raw, 4)[0] if len(raw) >= 8 else 0
            flags = (QUEST_NAME if first(fields, 'QSTN') else 0) | (QUEST_FINISHED if first(fields, 'QSTF') else 0) \
                | (QUEST_RESTART if first(fields, 'QSTR') else 0)
            rows.append((max(0, min(NONE16, index)), flags, text(fields, 'NAME')))
        rows.sort(key=lambda r: (r[0], not r[1] & QUEST_NAME))
        out.append((dials[key][0], rows))
    return out


# ---- the table

def tables(kinds, topics, dials, names, masks, order):
    """The deduplicated tables of masks {(topic, info, runtime): audience mask over ORDER}."""
    from mwad.dialogue import FUNCTIONS, globals_of
    from mwad.esm import text
    strings, tstrings, scripts, texts = G.Strings(), G.Strings(), G.Strings(), G.Strings()
    name_ids, globals_, conds = {}, {}, []
    glob_values = kinds.get('_globals') or globals_of(kinds)
    display = [dials[n][0] if dials[n][1] == KIND_TOPIC else None for n in names]
    links_of = link_finder(display)

    def name_index(value):
        if value not in name_ids:
            name_ids[value] = len(name_ids)
            strings.add(value)
        return name_ids[value]

    def condition(function, variable, op, value):
        if function == 'Global' and variable == 'random100':
            code, operand = G.OP_RANDOM100, 0
        elif function == 'Global':
            if variable not in globals_:
                globals_[variable] = len(globals_)
                strings.add(variable)
            code, operand = G.OP_GLOBAL, globals_[variable]
        elif function in ('Local', 'NotLocal') and '#' in variable:
            # the speaker's script local by its slot (with_slots); LOCAL_FLOAT marks a float local
            code = G.OPCODES[function]
            slot = variable.split('#', 1)[1]
            operand = int(slot.rstrip('f')) | (LOCAL_FLOAT if slot.endswith('f') else 0)
        elif function in G.OPCODES:
            code = G.OPCODES[function]
            operand = name_index(variable) if code in G.NAMED and variable else NONE16 if code in G.NAMED else 0
            if function == 'Cell':
                value, op = 1, '0'
            elif function == 'NotCell':
                value, op = 0, '0'
        elif function in FUNCTIONS:
            code, operand = G.OP_FUNC, FUNCTIONS.index(function)
        else:
            raise ValueError('No run-time opcode for condition ' + function)
        is_float = isinstance(value, float)
        raw = struct.pack('>f', value) if is_float else struct.pack('>i', int(value))
        return struct.pack('>BBH', code, int(op) | (G.FLOAT if is_float else 0), operand) + raw

    topic_rows = []
    for n in names:
        shown, kind = dials[n]
        raw = shown.encode('cp1252', 'replace')
        if len(raw) > 255:
            raise ValueError('Topic name past 255 bytes: ' + shown)
        topic_rows.append(struct.pack(TOPIC_ROW, tstrings.add(shown), len(raw), kind, 0))

    def sort_key(key):
        return (key[0], key[1], repr(key[2]))
    grouped = {}
    for key in sorted(masks, key=sort_key):
        grouped.setdefault((key[0], masks[key]), []).append(key)
    kept = {}
    for group, keys in grouped.items():
        cut = next((n for n, k in enumerate(keys) if not k[2]), len(keys) - 1)
        kept[group] = keys[:cut + 1]
    entry_keys = sorted({k for keys in kept.values() for k in keys}, key=sort_key)
    entry_index = {k: n for n, k in enumerate(entry_keys)}
    entries, links = [], []
    for t, i, runtime in entry_keys:
        fields = topics[names[t]][i]
        line, script = text(fields, 'NAME'), text(fields, 'BNAM')
        if len(runtime) > 255:
            raise ValueError('More than 255 run-time conditions in one INFO')
        first = len(conds)
        conds += [condition(*c) for c in runtime]
        found = links_of(line) if line else []
        entries.append(struct.pack(ENTRY_ROW, texts.add(line) if line else NONE32, first,
                                   scripts.add(script) if script.strip() else NONE32,
                                   len(links) if found else NONE32, len(found), len(runtime),
                                   0 if runtime else ENTRY_LAST))
        links += found
    list_rows, list_items, list_of = [], [], {}
    for group in sorted(kept, key=lambda g: (g[0], entry_index[kept[g][0]], g[1])):
        list_of[group] = len(list_rows)
        list_rows.append(struct.pack(LIST_ROW, len(list_items), len(kept[group]), 0))
        list_items += [entry_index[k] for k in kept[group]]
    per_npc = [{} for _ in order]
    for (t, mask), number in list_of.items():
        bit = 0
        while mask:
            if mask & 1:
                per_npc[bit].setdefault(t, []).append(number)
            mask >>= 1
            bit += 1
    listsets_of, listset_rows, listset_items = {}, [], []
    rows_of, rows, offsets = {}, bytearray(), []
    for n in range(len(order)):
        pairs = []
        for t in sorted(per_npc[n]):
            numbers = tuple(sorted(per_npc[n][t]))
            if numbers not in listsets_of:
                if len(numbers) > NONE16:
                    raise ValueError('List set past 16 bits')
                listsets_of[numbers] = len(listset_rows)
                listset_rows.append(struct.pack(LIST_ROW, len(listset_items), len(numbers), 0))
                listset_items += numbers
            pairs.append((t, listsets_of[numbers]))
        if not pairs:
            offsets.append(NONE32)
            continue
        if len(listset_rows) >= NONE16:
            raise ValueError('Dialogue table list sets past 16 bits')
        row = struct.pack('>HH', len(pairs), 0) + b''.join(struct.pack('>HH', t, s) for t, s in pairs)
        if row not in rows_of:
            rows_of[row] = len(rows)
            rows += row
        offsets.append(rows_of[row])
    quests, journal_rows = [], []
    for quest, items in journal(topics, dials):
        quests.append(struct.pack(QUEST_ROW, tstrings.add(quest), len(journal_rows), len(items), 0))
        journal_rows += [struct.pack(JOURNAL_ROW, index, flags, 0, texts.add(line) if line else NONE32)
                         for index, flags, line in items]
    return {'topics': topic_rows, 'offsets': offsets, 'rows': bytes(rows), 'listsets': listset_rows,
            'listset_items': listset_items, 'lists': list_rows, 'list_items': list_items, 'entries': entries,
            'conds': conds, 'links': links, 'quests': quests, 'journal': journal_rows,
            'globals': [struct.pack('>If', strings.add(g), float(glob_values.get(g, 0.)))
                        for g in sorted(globals_, key=globals_.get)],
            'names': [struct.pack('>I', strings.add(v)) for v in sorted(name_ids, key=name_ids.get)],
            'strings': bytes(strings.data), 'tstrings': bytes(tstrings.data), 'scripts': bytes(scripts.data),
            'texts': bytes(texts.data), 'functions': len(FUNCTIONS), 'fixture': G.fixture_values(kinds),
            'order_sha': hashlib.sha256('\n'.join(order).encode('cp1252', 'replace')).digest()[:8],
            'info_refusal': names.index(INFO_REFUSAL) if INFO_REFUSAL in names else NONE16,
            'start': start_topics(topics, names),
            'settings': settings_of(kinds)[0], 'settings_missing': settings_of(kinds)[1],
            'faction_ids': factions_of(kinds)[0], 'reactions': factions_of(kinds)[1],
            'rank_names': rank_names(kinds, factions_of(kinds)[0])}


def _pad(raw):
    return raw + bytes(-len(raw) % 4)


RESIDENT, CONVERSATION, ON_DISK = 'resident', 'conversation', 'disk'
# The session-long memory the table may take on the 32 MB Fast machine (docs/DIALOGUE_DESIGN.md: about 30 KB); the
# image step refuses a table past it (measured on Morrowind.esm, 30 October 2026: 24.8 KB resident, 25.0 KB per
# conversation)
RESIDENT_BUDGET = 32768
CONVERSATION_BUDGET = 40960
# the whole buffer of one open conversation (engine/aga/src/aw_dial.h AW_DIAL_BUFFER; measured: 53.6 KB at most,
# Eno Hlaalu's 747 candidate answers, 34.5 KB the median), allocated when it opens and freed when it ends
BUFFER_BUDGET = 81920


def sections(t):
    """[(name, bytes, where)] in file order: RESIDENT (kept in memory for the session), CONVERSATION (read once when a
    conversation opens, freed when it ends: what the condition records name), ON_DISK (read as needed)."""
    count = t['functions']
    bits = bytearray((count + 7) // 8)
    for i in t['fixture']:
        bits[i >> 3] |= 1 << (i & 7)
    return [
        ('topics', b''.join(t['topics']), RESIDENT),
        ('npc_offsets', b''.join(struct.pack('>I', o) for o in t['offsets']), RESIDENT),
        ('fixture', b''.join(struct.pack('>i', t['fixture'].get(i, 0)) for i in range(count)) + _pad(bytes(bits)),
         RESIDENT),
        ('start_topics', _pad(b''.join(struct.pack('>H', x) for x in t['start'])), RESIDENT),
        ('settings', b''.join(struct.pack('>f', v) for v in t['settings']), RESIDENT),
        ('factions', b''.join(f.encode('cp1252', 'replace').ljust(FACTION_ID, b'\0') for f in t['faction_ids']) +
         b''.join(struct.pack('>BBh', a, b, r) for a, b, r in t['reactions']), RESIDENT),
        ('globals', b''.join(t['globals']), CONVERSATION),
        ('names', b''.join(t['names']), CONVERSATION),
        ('strings', _pad(t['strings']), CONVERSATION),
        ('rows', t['rows'], ON_DISK),
        ('listsets', b''.join(t['listsets']) + b''.join(struct.pack('>I', x) for x in t['listset_items']), ON_DISK),
        ('lists', b''.join(t['lists']) + b''.join(struct.pack('>I', x) for x in t['list_items']), ON_DISK),
        ('entries', b''.join(t['entries']), ON_DISK),
        ('conds', b''.join(t['conds']), ON_DISK),
        ('links', _pad(b''.join(struct.pack('>H', x) for x in t['links'])), ON_DISK),
        ('quests', b''.join(t['quests']), ON_DISK),
        ('journal', b''.join(t['journal']), ON_DISK),
        ('rank_names', b''.join(n.encode('cp1252', 'replace')[:FACTION_ID - 1].ljust(FACTION_ID, b'\0')
                                for names in t['rank_names'] for n in names), ON_DISK),
        ('topic_strings', _pad(t['tstrings']), ON_DISK),
        ('scripts', _pad(t['scripts']), ON_DISK),
        ('texts', t['texts'], ON_DISK)]


def pack(t):
    """The AWDL1 file of tables(): big-endian, every section 4-byte aligned."""
    head = MAGIC + struct.pack(HEADER_FORMAT, VERSION, t['functions'], len(t['topics']), len(t['offsets']),
                               len(t['rows']), len(t['listsets']), len(t['listset_items']), len(t['lists']),
                               len(t['list_items']), len(t['entries']), len(t['conds']), len(t['globals']),
                               len(t['names']), len(t['links']), len(t['quests']), len(t['journal']),
                               len(_pad(t['strings'])), len(_pad(t['tstrings'])), len(_pad(t['scripts'])),
                               len(t['texts']), t['order_sha'], t['info_refusal'], len(t['start']), len(t['faction_ids']),
                               len(t['reactions']))
    return head + bytes(HEADER - len(head)) + b''.join(raw for _n, raw, _r in sections(t))


def read(raw):
    """The tables of an AWDL1 file as Python values (tests, the measurement)."""
    if raw[:4] != MAGIC:
        raise ValueError('Not an AWDL file')
    (version, functions, topics, npcs, row_bytes, listsets, listset_items, lists, list_items, entries, conds,
     globals_, names, links, quests, journal_n, string_bytes, tstring_bytes, script_bytes, text_bytes,
     order_sha, info_refusal, starts, nfactions, nreactions) = struct.unpack_from(HEADER_FORMAT, raw, 4)
    if version != VERSION:
        raise ValueError('AWDL version %d' % version)
    at = HEADER

    def take(size):
        nonlocal at
        value = raw[at:at + size]
        at += size
        return value
    topic_raw, offset_raw = take(8 * topics), take(4 * npcs)
    fixture_raw = take(4 * functions)
    bits = take(len(_pad(bytes((functions + 7) // 8))))
    start = list(struct.unpack('>%dH' % starts, take(len(_pad(bytes(2 * starts))))[:2 * starts]))
    settings = dict(zip(SETTINGS, struct.unpack('>%df' % len(SETTINGS), take(4 * len(SETTINGS)))))
    faction_ids = [take(FACTION_ID).rstrip(b'\0').decode('cp1252') for _ in range(nfactions)]
    reactions = [struct.unpack('>BBh', take(4)) for _ in range(nreactions)]
    resident = at
    global_raw, name_raw, strings = take(8 * globals_), take(4 * names), take(string_bytes)
    conversation = at - resident
    rows = take(row_bytes)
    listset_raw, listset_item_raw = take(8 * listsets), take(4 * listset_items)
    list_raw, list_item_raw = take(8 * lists), take(4 * list_items)
    entry_raw, cond_raw = take(20 * entries), take(8 * conds)
    link_raw = take(len(_pad(bytes(2 * links))))
    quest_raw, journal_raw = take(12 * quests), take(8 * journal_n)
    rank_raw = take(FACTION_ID * RANKS * nfactions)
    tstrings, scripts, texts = take(tstring_bytes), take(script_bytes), take(text_bytes)
    if at != len(raw):
        raise ValueError('AWDL size mismatch')

    def s(offset, block):
        return None if offset == NONE32 else block[offset:block.index(b'\0', offset)].decode('cp1252')
    out = {'resident_bytes': resident, 'conversation_bytes': conversation, 'bytes': len(raw), 'order_sha': order_sha,
           'info_refusal': None if info_refusal == NONE16 else info_refusal, 'start': start,
           'settings': settings, 'factions': faction_ids, 'reactions': reactions,
           'rank_names': [[rank_raw[(f * RANKS + r) * FACTION_ID:(f * RANKS + r + 1) * FACTION_ID].rstrip(b'\0')
                           .decode('cp1252') for r in range(RANKS)] for f in range(nfactions)],
           'fixture': {i: v for i, v in enumerate(struct.unpack('>%di' % functions, fixture_raw))
                       if bits[i >> 3] >> (i & 7) & 1},
           'globals': [(s(o, strings), v) for o, v in struct.iter_unpack('>If', global_raw)],
           'names': [s(o, strings) for (o,) in struct.iter_unpack('>I', name_raw)],
           'listsets': [struct.unpack_from('>IH', listset_raw, i) for i in range(0, len(listset_raw), 8)],
           'listset_items': list(struct.unpack('>%dI' % listset_items, listset_item_raw)),
           'lists': [struct.unpack_from('>IH', list_raw, i) for i in range(0, len(list_raw), 8)],
           'list_items': list(struct.unpack('>%dI' % list_items, list_item_raw)),
           'entries': list(struct.iter_unpack(ENTRY_ROW, entry_raw)),
           'conds': [struct.unpack_from('>BBHi', cond_raw, i) for i in range(0, len(cond_raw), 8)],
           'links': list(struct.unpack('>%dH' % links, link_raw[:2 * links])),
           'text': lambda o: s(o, texts), 'script': lambda o: s(o, scripts)}
    out['topics'] = [(s(o, tstrings), kind) for o, _n, kind, _z in struct.iter_unpack(TOPIC_ROW, topic_raw)]
    out['quests'] = []
    for o, first, n, _z in struct.iter_unpack(QUEST_ROW, quest_raw):
        items = [struct.unpack_from(JOURNAL_ROW, journal_raw, 8 * k) for k in range(first, first + n)]
        out['quests'].append((s(o, tstrings), [(i, f, s(x, texts)) for i, f, _z, x in items]))
    out['rows'] = []
    for (o,) in struct.iter_unpack('>I', offset_raw):
        if o == NONE32:
            out['rows'].append({})
            continue
        count = struct.unpack_from('>H', rows, o)[0]
        out['rows'].append(dict(struct.unpack_from('>HH', rows, o + 4 + 4 * k) for k in range(count)))
    return out


def derived_disposition(table, base, same_race, personality, bounty, faction, ranks, diseased=False,
                        weapon_drawn=False, clamp=True):
    """The NPC's disposition toward the player as the engine works it out (aw_dial.c AW_DialDisposition; the rule of
    OpenMW's MechanicsManager::getDerivedDisposition, our own code): RANKS {folded faction: (rank, expelled)} of the
    player; FACTION the speaker's folded faction id or None."""
    s = table['settings']
    ids = table['factions']

    def f32(v):                      # the engine's single-precision arithmetic, step by step
        return struct.unpack('<f', struct.pack('<f', v))[0]
    react = {(a, b): r for a, b, r in table['reactions']}
    x = float(base)
    if same_race:
        x = f32(x + s['fDispRaceMod'])
    x = f32(x + f32(s['fDispPersonalityMult'] * f32(personality - s['fDispPersonalityBase'])))
    reaction, rank = 0.0, 0
    own = ids.index(faction) if faction in ids else None
    if faction and faction in ranks:
        if not ranks[faction][1] and own is not None:
            reaction, rank = float(react.get((own, own), 0)), ranks[faction][0]
    elif faction:
        first = True
        for name, (r, expelled) in sorted(ranks.items()):
            if expelled or r < 0 or name not in ids:      # the engine knows the factions of the table only
                continue
            value = react.get((own, ids.index(name)), 0) if own is not None else 0
            if first or value < reaction:
                reaction, rank, first = float(value), r, False
    x = f32(x + f32(f32(f32(f32(s['fDispFactionRankMult'] * rank) + s['fDispFactionRankBase']) * s['fDispFactionMod']) * reaction))
    x = f32(x - f32(s['fDispCrimeMod'] * bounty))
    if diseased:
        x = f32(x + s['fDispDiseaseMod'])
    if weapon_drawn:
        x = f32(x + s['fDispWeaponDrawn'])
    x = int(x)                       # toward zero, as a C cast
    return max(0, min(100, x)) if clamp else x


def candidates(table, npc, topic):
    """The entry indices an NPC row walks for a table topic, in the original's order, up to and including the first
    entry without a run-time condition."""
    listset = table['rows'][npc].get(topic)
    if listset is None:
        return []
    first, count = table['listsets'][listset]
    merged = sorted(e for number in table['listset_items'][first:first + count]
                    for e in table['list_items'][table['lists'][number][0]:
                                                 table['lists'][number][0] + table['lists'][number][1]])
    out = []
    for e in merged:
        out.append(e)
        if table['entries'][e][6] & ENTRY_LAST:
            break
    return out


def answers(table, npc, topic):
    """[(text, script, [link topic], [(op, cmp, operand, value)])] an NPC row walks for a topic."""
    out = []
    for e in candidates(table, npc, topic):
        text, first, script, link, nlinks, n, _flags = table['entries'][e]
        out.append((table['text'](text), table['script'](script),
                    table['links'][link:link + nlinks] if link != NONE32 else [], table['conds'][first:first + n]))
    return out


def report_of(t, raw, order, left, names, dials):
    secs = sections(t)
    resident = HEADER + sum(len(r) for _n, r, where in secs if where == RESIDENT)
    conversation = sum(len(r) for _n, r, where in secs if where == CONVERSATION)
    sizes = {n: len(r) for n, r, _k in secs}
    rows_per_npc = [0 if o == NONE32 else struct.unpack_from('>H', t['rows'], o)[0] for o in t['offsets']]
    return {'format': 'AWDL%d' % VERSION, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'resident_bytes': resident, 'resident_budget': RESIDENT_BUDGET, 'conversation_bytes': conversation,
            'disk_bytes': len(raw) - resident - conversation, 'section_bytes': sizes,
            'topics': len(names), 'topic_kinds': {str(k): sum(1 for n in names if dials[n][1] == k)
                                                  for k in DIAL_TYPES},
            'npcs': len(order), 'npcs_with_topics': sum(1 for o in t['offsets'] if o != NONE32),
            'distinct_rows': len({o for o in t['offsets'] if o != NONE32}),
            'topics_per_npc_max': max(rows_per_npc or [0]),
            'topics_per_npc_mean': round(sum(rows_per_npc) / max(1, len(rows_per_npc)), 1),
            'list_sets': len(t['listsets']), 'lists': len(t['lists']), 'entries': len(t['entries']),
            'conditions': len(t['conds']), 'links': len(t['links']), 'globals': len(t['globals']),
            'names': len(t['names']), 'quests': len(t['quests']), 'journal_entries': len(t['journal']),
            'settings_missing': t['settings_missing'], 'factions': len(t['faction_ids']),
            'faction_reactions': len(t['reactions']),
            'left_out': left}


def build(kinds, topics, dials, homes=None, masks=None, left=None):
    """(AWDL1 bytes, report) from loaded records (kinds with the dialogue records, topics, dial_names())."""
    homes = homes or {}
    names = table_topics(dials)
    order, _facts, early = G.plan_npcs(kinds, homes)
    left = dict(early, **(left or {}))
    bits = {i: n for n, i in enumerate(order)}
    if masks is None:
        masks, gone = _chunk_local(kinds, topics, names, homes, bits, order)
        left.update(gone)
    keep = [i for i in order if i not in left]
    if len(keep) != len(order):
        remap = {bits[i]: n for n, i in enumerate(keep)}
        masks = {k: sum(1 << remap[b] for b in range(len(order)) if m >> b & 1 and b in remap)
                 for k, m in masks.items()}
        masks = {k: m for k, m in masks.items() if m}
    t = tables(kinds, topics, dials, names, masks, keep)
    raw = pack(t)
    report = report_of(t, raw, keep, left, names, dials)
    report.update(conversation_buffer(read(raw), keep))
    return raw, report


AMIGA_ANSWER = 24                # sizeof(aw_dial_answer_t) on the 68k (engine/aga/src/aw_dial.h), 8-byte pieces


def conversation_buffer(table, order):
    """The buffer one conversation takes on the Amiga (aw_dial.c AW_DialConverse: the globals and names, the row's
    pairs, every candidate answer and its conditions, each piece 8-byte aligned): the largest and the median."""
    def p8(n):
        return (n + 7) & ~7
    sizes = []
    for npc, row in enumerate(table['rows']):
        size = p8(table['conversation_bytes']) + p8(4 * len(row))
        for topic in row:
            for e in candidates(table, npc, topic):
                size += AMIGA_ANSWER + p8(8 * table['entries'][e][5]) * (table['entries'][e][5] > 0)
        sizes.append((size, order[npc] if npc < len(order) else ''))
    sizes.sort()
    if not sizes:
        return {'conversation_buffer_max': 0, 'conversation_buffer_median': 0, 'conversation_buffer_npc': ''}
    return {'conversation_buffer_max': sizes[-1][0], 'conversation_buffer_npc': sizes[-1][1],
            'conversation_buffer_median': sizes[len(sizes) // 2][0]}


def _chunk_local(kinds, topics, names, homes, bits, ids):
    index = info_index(topics, names)
    out, left = {}, {}
    for ident in ids:
        try:
            entries = speaker_entries(kinds, index, ident, homes.get(ident))
        except (ValueError, KeyError, struct.error) as error:
            left[ident] = str(error)
            continue
        for k in entries:
            out[k] = out.get(k, 0) | 1 << bits[ident]
    return out, left


def build_master(path, jobs=1):
    """(AWDL1 bytes, report) of a master file, the NPC records compiled in chunks on JOBS processes."""
    from build_parallel import ordered_map
    t0 = time.time()
    print('=== PHASE 1/3: Dialogue table: reading the master ===', flush=True)
    kinds, topics = G.load(path)
    dials = dial_names(path)
    homes = G.home_cells(path, kinds)
    names = table_topics(dials)
    order, _facts, _left = G.plan_npcs(kinds, homes)
    bits = {i: n for n, i in enumerate(order)}
    size = max(16, len(order) // max(1, jobs * 4))
    chunks = [order[i:i + size] for i in range(0, len(order), size)]
    print('=== PHASE 2/3: Dialogue table: %d NPC records x %d topics, %d units on %d jobs ===' % (
        len(order), len(names), len(chunks), jobs), flush=True)
    masks, left, done, t1 = {}, {}, 0, time.time()
    for out, gone in ordered_map(_chunk, [(str(path), homes, names, bits, c) for c in chunks], jobs=max(1, jobs),
                                 cost=lambda task: len(task[4])):
        for key, mask in out.items():
            masks[key] = masks.get(key, 0) | mask
        left.update(gone)
        done += 1
        rate = done / max(0.1, time.time() - t1)
        print('Dialogue table: %d/%d units (%.1f/s, ETA %.0f s)' % (done, len(chunks), rate,
                                                                   (len(chunks) - done) / max(rate, 1e-6)),
              flush=True)
    print('=== PHASE 3/3: Dialogue table: tables and packing ===', flush=True)
    raw, report = build(kinds, topics, dials, homes, masks, left)
    report['home_cells'] = len(homes)
    report['seconds'] = round(time.time() - t0, 1)
    print('Dialogue table: %d topics, %d NPCs (%d rows), %d entries, %d conditions, %d quests; %d bytes, %d resident '
          '(%.1f s)' % (report['topics'], report['npcs'], report['distinct_rows'], report['entries'],
                        report['conditions'], report['quests'], report['bytes'], report['resident_bytes'],
                        report['seconds']), flush=True)
    return raw, report


def image_step(data, id1, out=None, jobs=1):
    """The image step: id1/dialogue.lut from DATA's Morrowind.esm, through the unit cache (keyed by the master's
    SHA-256 and this module's sources); the report beside it in OUT (dialogue-table.json). Returns the report."""
    from build_scratch import scratch_dir
    from mwad.esm import sha256_file
    from mwad.paths import child_ci
    from pass_cache import UnitCache
    master = child_ci(Path(data), 'Morrowind.esm')
    inputs = {'master_sha256': sha256_file(master)}
    import mwad.dialogue
    cache = UnitCache.open('dialogue-table', {'format': 'AWDL%d' % VERSION}, __file__, G.__file__,
                           mwad.dialogue.__file__)
    target = Path(id1) / NAME
    t0 = time.time()
    print('Dialogue table: start (1 unit cache lookup, then %d jobs if built)' % jobs, flush=True)
    with scratch_dir(prefix='dialogue-table-', near=out if out is not None else Path(id1).parent,
                     keep_on_failure=False) as tmp:
        folder = Path(tmp) / 'unit'
        row = cache.restore_unit(inputs, folder) if cache else None
        if row is not None:
            report = json.loads((folder / 'report.json').read_text(encoding='utf-8'))
            raw = (folder / NAME).read_bytes()
            report['reused'] = True
        else:
            raw, report = build_master(master, jobs)
            folder.mkdir(parents=True)
            (folder / NAME).write_bytes(raw)
            (folder / 'report.json').write_text(json.dumps(report, indent=1, sort_keys=True) + '\n',
                                                encoding='utf-8', newline='\n')
            if cache:
                cache.store_unit(inputs, {'bytes': len(raw)}, folder)
            report['reused'] = False
    if hashlib.sha256(raw).hexdigest() != report['sha256']:
        raise ValueError('Dialogue table: SHA-256 differs from its report')
    if report['resident_bytes'] > RESIDENT_BUDGET or report['conversation_bytes'] > CONVERSATION_BUDGET or \
            report['conversation_buffer_max'] > BUFFER_BUDGET:
        raise ValueError('Dialogue table: %d resident / %d names / %d conversation buffer bytes, past the budget '
                         '%d / %d / %d' % (report['resident_bytes'], report['conversation_bytes'],
                                           report['conversation_buffer_max'], RESIDENT_BUDGET, CONVERSATION_BUDGET,
                                           BUFFER_BUDGET))
    voices = Path(id1) / G.NAME
    if voices.is_file():
        # the NPC rows are the voice table's: the engine finds the row by the voice table's lookup
        order = list(G.read(voices.read_bytes())['npcs'])
        if hashlib.sha256('\n'.join(order).encode('cp1252', 'replace')).digest()[:8] != read(raw)['order_sha']:
            raise ValueError('Dialogue table: NPC rows differ from the voice table (%s)' % voices)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    if out is not None:
        Path(out).mkdir(parents=True, exist_ok=True)
        (Path(out) / 'dialogue-table.json').write_text(json.dumps(report, indent=1, sort_keys=True) + '\n',
                                                       encoding='utf-8', newline='\n')
    print('Dialogue table: %s %s, %d bytes, %d resident (took %.1f s, %s)' % (
        'reused' if report['reused'] else 'built', NAME, len(raw), report['resident_bytes'], time.time() - t0,
        '1 core' if report['reused'] else '%d jobs' % jobs), flush=True)
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--data-files', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True, help='the AWDL1 file to write')
    p.add_argument('--report', type=Path)
    p.add_argument('--jobs', type=int, default=1)
    a = p.parse_args(argv)
    from mwad.paths import child_ci
    raw, report = build_master(child_ci(a.data_files, 'Morrowind.esm'), a.jobs)
    a.out.write_bytes(raw)
    if a.report:
        a.report.write_text(json.dumps(report, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
