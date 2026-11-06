#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Every being's stats, squeezed (ACTOR-STATS-ALL-61): one small entry per NPC and creature record of the masters,
holding exactly what its record type holds and nothing else, written per area into id1/areas.awa (the area's AWS1
section, tools/prepare_area_tables.py), read by the engine with the area (engine aw_stats.c).

The record types (the masters' own layouts; read rules from OpenMW 0.51 components/esm3/loadnpc.cpp, loadcrea.cpp,
aipackage.hpp, written independently):
  NPC with stored stats (52-byte NPDT): level, 8 attributes, 27 skills, health, magicka, fatigue, disposition,
      reputation, rank, gold;
  NPC with auto-calculated stats (12-byte NPDT): level, disposition, reputation, rank, gold; the attributes, skills,
      health, magicka and fatigue are derived from race, class and level when the actor is made (engine aw_stats.c,
      the rule of tools/prepare_combat.py autocalc);
  creature (96-byte NPDT): type, level, 8 attributes, health, magicka, fatigue, soul, combat, magic, stealth, 6 attack
      values, gold;
  every actor: FLAG (its flags and blood type), AIDT (hello, fight, flee, alarm, services; an NPC without one reads
      OpenMW's defaults hello, fight and flee 30), its NPCS spells and abilities (as ASPT rows of the image's
      id1/mwscript.awm, the form the magic code reads); NPCs: race, class, faction.

Entry (big-endian, the 68k's order):
  u8 kind (KIND_STORED, KIND_AUTO, KIND_CREATURE), u16 present mask, then the fields of each set bit in bit order:
  P_BASE      always: stored NPC  level u16, attributes 8 x u8, skills 27 x u8, health u16, magicka u16, fatigue u16,
                                  disposition u8, reputation u8
                      auto NPC    level u16, disposition u8, reputation u8
                      creature    type u8, level u16, attributes 8 x u8, health u16, magicka u16, fatigue u16, soul u16,
                                  combat u8, magic u8, stealth u8, attacks 6 x u16 (chop, slash, thrust: min, max)
  P_FLAGS     always: flags u8 (FLAG's low byte, the record's own bits), blood u8 (FLAG >> 10)
  P_AI        the record has an AIDT: hello u16, fight u8, flee u8, alarm u8
  P_SERVICES  AIDT's services are not 0: u32
  P_FACTION   an NPC with a faction: u32 FNV-1a of its id (folded), rank i8
  P_RACE      an NPC: race u8, class u8 (indexes of the section's race and class rows)
  P_SPELLS    the record lists spells: u8 n, n x u16 ASPT row (0xFFFF: no row; the image has no such spell)
  P_GOLD      gold is not 0: u32
A field the mask leaves out reads 0 (the gold, the services) or, for AIDT, the record default above; which stats a
kind has at all is the kind's (engine AW_StatHas), never the mask's: the mask is a storage form only.

The area's section (prepare_area_tables.stats_section), big-endian:
  "AWS1" u16 entries, u8 races, u8 classes, f32 fNPCbaseMagickaMult, u8 skills[27] x { governing attribute,
  specialization } (54 bytes), entries x { u32 id hash (the ledger's AW_LedgerNameHash), u16 offset from the
  section's start } ascending hash, races x RACE_ROW, classes x CLASS_ROW, then the entries.
  RACE_ROW: u32 id hash, 8 x u8 male attributes, 8 x u8 female attributes, 7 x { i8 skill, u8 bonus }, u8 n spells,
            n x u16 ASPT row (the race's powers and abilities, which OpenMW gives every NPC of the race)
  CLASS_ROW: u32 id hash, u8 favoured attribute x 2, u8 specialization, 5 x { u8 minor skill, u8 major skill }
"""
import struct

KIND_STORED, KIND_AUTO, KIND_CREATURE = 0, 1, 2
P_BASE, P_FLAGS, P_AI, P_SERVICES, P_FACTION, P_RACE, P_SPELLS, P_GOLD = (1 << i for i in range(8))
NO_SPELL = 0xFFFF
AI_DEFAULT_NPC = (30, 30, 30, 0)          # OpenMW loadnpc.cpp: mHello = mFight = mFlee = 30 before AIDT is read
AI_DEFAULT_CREATURE = (0, 0, 0, 0)        # loadcrea.cpp: mAiData.blank()
MAGIC = b'AWS1'
FILE_MAGIC = b'AWT1'                       # the focus stage's vocabulary file (write_vocabulary)
FILE_NAME = 'actor-stats.awt'


def name_hash(ident):
    """FNV-1a over the id with A-Z folded; 0 becomes 1 (engine AW_LedgerNameHash, prepare_focus.name_hash)."""
    h = 2166136261
    for c in ident.encode('cp1252', 'replace'):
        if 65 <= c <= 90:
            c += 32
        h = ((h ^ c) * 16777619) & 0xFFFFFFFF
    return h or 1


def _first(fields, tag, default=b''):
    for t, d in fields:
        if t == tag:
            return d
    return default


def _text(d):
    return d.split(b'\0', 1)[0].decode('cp1252', 'replace')


def _fit(value, lo, hi, what, ident):
    if not lo <= value <= hi:
        raise ValueError('%s: %s %d does not fit %d..%d' % (ident, what, value, lo, hi))
    return value


def actor(tag, fields, spell_row):
    """The entry of one NPC_ or CREA record (FIELDS its subrecords) as a dict with 'kind', 'mask', the values and
    'race'/'class' ids (folded) for the section to index; None for a record without a known NPDT. SPELL_ROW: folded
    spell id -> ASPT row (or None: NO_SPELL)."""
    ident = _text(_first(fields, 'NAME'))
    npdt = _first(fields, 'NPDT')
    flag = struct.unpack('<I', _first(fields, 'FLAG', b'\0\0\0\0')[:4].ljust(4, b'\0'))[0]
    e = {'id': ident, 'flags': flag & 0xFF, 'blood': _fit(flag >> 10, 0, 255, 'blood', ident), 'mask': P_BASE | P_FLAGS}
    if tag == 'NPC_':
        if len(npdt) == 52:
            e['kind'] = KIND_STORED
            e['level'] = _fit(struct.unpack_from('<h', npdt)[0], 0, 0xFFFF, 'level', ident)
            e['attributes'] = list(npdt[2:10])
            e['skills'] = list(npdt[10:37])
            e['dynamic'] = list(struct.unpack_from('<3H', npdt, 38))
            e['disposition'], e['reputation'] = npdt[44], npdt[45]
            e['rank'] = struct.unpack_from('<b', npdt, 46)[0]
            e['gold'] = struct.unpack_from('<i', npdt, 48)[0]
        elif len(npdt) == 12:
            e['kind'] = KIND_AUTO
            e['level'] = _fit(struct.unpack_from('<h', npdt)[0], 0, 0xFFFF, 'level', ident)
            e['disposition'], e['reputation'] = npdt[2], npdt[3]
            e['rank'] = struct.unpack_from('<b', npdt, 4)[0]
            e['gold'] = struct.unpack_from('<i', npdt, 8)[0]
        else:
            return None
        e['race'] = _text(_first(fields, 'RNAM')).casefold()
        e['class'] = _text(_first(fields, 'CNAM')).casefold()
        e['mask'] |= P_RACE
        faction = _text(_first(fields, 'ANAM'))
        if faction:
            e['faction'] = name_hash(faction)
            e['mask'] |= P_FACTION
    elif tag == 'CREA':
        if len(npdt) != 96:
            return None
        v = struct.unpack('<24i', npdt)
        e['kind'] = KIND_CREATURE
        e['type'] = _fit(v[0], 0, 255, 'type', ident)
        e['level'] = _fit(v[1], 0, 0xFFFF, 'level', ident)
        e['attributes'] = [_fit(a, 0, 255, 'attribute', ident) for a in v[2:10]]
        e['dynamic'] = [_fit(x, 0, 0xFFFF, 'dynamic', ident) for x in v[10:13]]
        e['soul'] = _fit(v[13], 0, 0xFFFF, 'soul', ident)
        e['cms'] = [_fit(x, 0, 255, 'combat/magic/stealth', ident) for x in v[14:17]]
        e['attacks'] = [_fit(x, 0, 0xFFFF, 'attack', ident) for x in v[17:23]]
        e['gold'] = v[23]
    else:
        return None
    aidt = _first(fields, 'AIDT')
    if len(aidt) >= 5:
        e['ai'] = (struct.unpack_from('<H', aidt)[0], aidt[2], aidt[3], aidt[4])
        e['mask'] |= P_AI
        services = struct.unpack_from('<I', aidt, 8)[0] if len(aidt) >= 12 else 0
        if services:
            e['services'] = services
            e['mask'] |= P_SERVICES
    spells = [_text(d) for t, d in fields if t == 'NPCS']
    if spells:
        if len(spells) > 255:
            raise ValueError('%s: %d spells' % (ident, len(spells)))
        rows = [spell_row.get(s.casefold()) for s in spells]
        e['spells'] = [NO_SPELL if r is None else r for r in rows]
        e['mask'] |= P_SPELLS
    if e['gold']:
        e['gold'] = _fit(e['gold'], 0, 0xFFFFFFFF, 'gold', ident)
        e['mask'] |= P_GOLD
    return e


def encode(e, race_index=None, class_index=None):
    """The entry bytes of E (actor); RACE_INDEX/CLASS_INDEX: the section's row of its race and class."""
    k, m = e['kind'], e['mask']
    out = bytearray(struct.pack('>BH', k, m))
    if k == KIND_STORED:
        out += struct.pack('>H8B27B3HBB', e['level'], *e['attributes'], *e['skills'], *e['dynamic'], e['disposition'],
                           e['reputation'])
    elif k == KIND_AUTO:
        out += struct.pack('>HBB', e['level'], e['disposition'], e['reputation'])
    else:
        out += struct.pack('>BH8B3HH3B6H', e['type'], e['level'], *e['attributes'], *e['dynamic'], e['soul'], *e['cms'],
                           *e['attacks'])
    out += struct.pack('>BB', e['flags'], e['blood'])
    if m & P_AI:
        out += struct.pack('>HBBB', *e['ai'])
    if m & P_SERVICES:
        out += struct.pack('>I', e['services'])
    if m & P_FACTION:
        out += struct.pack('>Ib', e['faction'], max(-128, min(127, e['rank'])))
    if m & P_RACE:
        out += struct.pack('>BB', race_index, class_index)
    if m & P_SPELLS:
        out += struct.pack('>B%dH' % len(e['spells']), len(e['spells']), *e['spells'])
    if m & P_GOLD:
        out += struct.pack('>I', e['gold'])
    return bytes(out)


def decode(raw, at=0):
    """encode's inverse (the tests; the engine's aw_stats.c reads the same): (dict, bytes used)."""
    k, m = struct.unpack_from('>BH', raw, at)
    p = at + 3
    e = {'kind': k, 'mask': m}
    if k == KIND_STORED:
        v = struct.unpack_from('>H8B27B3HBB', raw, p); p += 2 + 8 + 27 + 6 + 2
        e.update(level=v[0], attributes=list(v[1:9]), skills=list(v[9:36]), dynamic=list(v[36:39]),
                 disposition=v[39], reputation=v[40])
    elif k == KIND_AUTO:
        e['level'], e['disposition'], e['reputation'] = struct.unpack_from('>HBB', raw, p); p += 4
    elif k == KIND_CREATURE:
        v = struct.unpack_from('>BH8B3HH3B6H', raw, p); p += 1 + 2 + 8 + 6 + 2 + 3 + 12
        e.update(type=v[0], level=v[1], attributes=list(v[2:10]), dynamic=list(v[10:13]), soul=v[13], cms=list(v[14:17]),
                 attacks=list(v[17:23]))
    else:
        raise ValueError('unknown stat entry kind %d' % k)
    e['flags'], e['blood'] = raw[p], raw[p + 1]; p += 2
    if m & P_AI:
        e['ai'] = struct.unpack_from('>HBBB', raw, p); p += 5
    if m & P_SERVICES:
        e['services'] = struct.unpack_from('>I', raw, p)[0]; p += 4
    if m & P_FACTION:
        e['faction'], e['rank'] = struct.unpack_from('>Ib', raw, p); p += 5
    if m & P_RACE:
        e['race_index'], e['class_index'] = raw[p], raw[p + 1]; p += 2
    if m & P_SPELLS:
        n = raw[p]; e['spells'] = list(struct.unpack_from('>%dH' % n, raw, p + 1)); p += 1 + 2 * n
    if m & P_GOLD:
        e['gold'] = struct.unpack_from('>I', raw, p)[0]; p += 4
    return e, p - at


def race_row(ident, fields, spell_row):
    """RACE_ROW of a RACE record."""
    radt = _first(fields, 'RADT')
    bonus = [struct.unpack_from('<2i', radt, 8 * i) for i in range(7)]
    attrs = [struct.unpack_from('<2i', radt, 56 + 8 * i) for i in range(8)]
    spells = [spell_row.get(_text(d).casefold()) for t, d in fields if t == 'NPCS']
    spells = [NO_SPELL if r is None else r for r in spells]
    out = struct.pack('>I', name_hash(ident))
    out += bytes(_fit(a[0], 0, 255, 'race attribute', ident) for a in attrs)
    out += bytes(_fit(a[1], 0, 255, 'race attribute', ident) for a in attrs)
    out += b''.join(struct.pack('>bB', s if 0 <= s < 27 else -1, _fit(b, 0, 255, 'race bonus', ident) if 0 <= s < 27
                                else 0) for s, b in bonus)
    return out + struct.pack('>B%dH' % len(spells), len(spells), *spells)


RACE_FIXED = 4 + 16 + 14 + 1
CLASS_ROW = 4 + 2 + 1 + 10


def class_row(ident, fields):
    cldt = _first(fields, 'CLDT')
    favoured = struct.unpack_from('<2i', cldt, 0)
    spec = struct.unpack_from('<i', cldt, 8)[0]
    pairs = [struct.unpack_from('<2i', cldt, 12 + 8 * i) for i in range(5)]
    return (struct.pack('>I', name_hash(ident)) + bytes(a & 0xFF for a in favoured) + bytes([spec & 0xFF]) +
            b''.join(bytes([mi & 0xFF, ma & 0xFF]) for mi, ma in pairs))


def skill_table(records):
    """27 x (governing attribute, specialization) from SKIL (SKDT), 0xFF when missing."""
    out = bytearray()
    for i in range(27):
        sk = _first(records['SKIL'].get(i, []), 'SKDT')
        gov, spec = struct.unpack_from('<2i', sk) if len(sk) >= 8 else (255, 255)
        out += bytes([gov & 0xFF, spec & 0xFF])
    return bytes(out)


def spell_rows(awm_raw):
    """{folded spell id: ASPT row} of an image's id1/mwscript.awm ({} without an actor table)."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from mwscript import awms
    f = awms.read(awm_raw)
    if 'ASPT' not in f:
        return {}
    names = awms.strings(f)
    out = {}
    for i in range(f['ASPT_rows']):
        sid = struct.unpack_from('>H', f['ASPT'], 4 * i)[0]
        out.setdefault(names[sid].casefold(), i)
    return out


# ---------------------------------------------------------------- the focus stage's vocabulary file
#
# focus/actor-stats.awt (the focus stage reads the masters already; the image step keys each area's section from it):
#   "AWT1" u32 actors, u32 races, u32 classes, f32 fNPCbaseMagickaMult, 54 bytes the skill table, then
#   actors x { u32 hash, u8 tag (0 NPC_, 1 CREA), u16 bytes, the record's subrecords NPDT FLAG AIDT NPCS RNAM CNAM ANAM
#              NAME as { 4s tag, u16 size, data } }, races x { the same for RADT NPCS NAME }, classes x { CLDT NAME }
# The spells stay ids here: their ASPT rows are the image's (spell_rows), known only at image assembly.
KEEP = {'NPC_': ('NAME', 'NPDT', 'FLAG', 'AIDT', 'NPCS', 'RNAM', 'CNAM', 'ANAM'), 'CREA': ('NAME', 'NPDT', 'FLAG',
        'AIDT', 'NPCS'), 'RACE': ('NAME', 'RADT', 'NPCS'), 'CLAS': ('NAME', 'CLDT'), 'BSGN': ('NAME', 'NPCS')}


def _pack_fields(tag, fields):
    return b''.join(struct.pack('>4sH', t.encode('ascii'), len(d)) + d for t, d in fields if t in KEEP[tag])


def levelled_by_area(raw, numbers):
    """{area key: [LEVC id hash]} of the levelled creature references of Morrowind.esm (RAW) by area (an interior by
    its room NUMBERS, an exterior cell by its grid key, as focus.awf): a levelled reference has no actor row, so its
    area's stats section names the creatures its list can give from these."""
    from prepare_focus import cells_of, exterior_key, GRID_BIAS
    from mwad.esm import string
    levc = set()
    from mwad.esm import records, subrecords
    for tag, flags, payload in records(raw):
        if tag == 'LEVC' and not flags & 0x20:
            ident = _text(dict(subrecords(payload)).get('NAME', b''))
            if ident:
                levc.add(ident.casefold())
    out = {}
    for cell, interior, grid, _region, refs in cells_of(raw):
        if interior:
            if not cell or cell.casefold() not in numbers:
                continue
            key = numbers[cell.casefold()]
        elif not all(abs(g) < GRID_BIAS for g in grid):
            continue
        else:
            key = exterior_key(*grid)
        for ref in refs:
            if 'DELE' in ref or 'NAME' not in ref:
                continue
            ident = string(ref['NAME'], 'NAME', errors='replace').casefold()
            if ident in levc:
                out.setdefault(key, []).append(name_hash(ident))
    return out


def write_vocabulary(records, gmst, levelled_areas=None):
    """The AWT1 bytes from the masters' records (mwscript GameData.records: last master wins) and float GMSTs;
    LEVELLED_AREAS: levelled_by_area's table (written after the lists)."""
    actors = []
    for tag, flag in (('NPC_', 0), ('CREA', 1)):
        for key in sorted(records[tag]):
            body = _pack_fields(tag, records[tag][key])
            actors.append(struct.pack('>IBH', name_hash(key), flag, len(body)) + body)
    races = [_pack_fields('RACE', records['RACE'][k]) for k in sorted(records['RACE'])]
    classes = [_pack_fields('CLAS', records['CLAS'][k]) for k in sorted(records['CLAS'])]
    head = FILE_MAGIC + struct.pack('>IIIf', len(actors), len(races), len(classes),
                                    gmst.get('fnpcbasemagickamult', 2.0)) + skill_table(records)
    births = [_pack_fields('BSGN', records['BSGN'][k]) for k in sorted(records.get('BSGN', {}))]
    lists = []
    for key in sorted(records.get('LEVC', {})):
        names = [name_hash(_text(d)) for t, d in records['LEVC'][key] if t == 'CNAM']
        lists.append(struct.pack('>IH%dI' % len(names), name_hash(key), len(names), *names))
    return (head + b''.join(actors) + b''.join(struct.pack('>H', len(r)) + r for r in races) +
            b''.join(struct.pack('>H', len(c)) + c for c in classes) + struct.pack('>I', len(lists)) +
            b''.join(lists) + struct.pack('>I', len(levelled_areas or {})) +
            b''.join(struct.pack('>IH%dI' % len(v), k, len(v), *v) for k, v in sorted((levelled_areas or {}).items())) +
            struct.pack('>I', len(births)) + b''.join(struct.pack('>H', len(b)) + b for b in births))


MASTERS = ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm')


def master_records(data_files):
    """({tag: {folded id: [(sub, data)]}} for NPC_, CREA, RACE, CLAS and SKIL (by INDX), {folded float GMSTs}) of the
    masters present, the last master's record of an id winning and a deleted record removing the earlier one (the
    rule tools/mwscript/gamedata.py keeps)."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
    from mwad.esm import records, subrecords
    from mwad.paths import child_ci, resolve_data_files
    try:
        data = resolve_data_files(Path(data_files))
    except ValueError:
        data = Path(data_files)        # a folder of masters alone (the tests; mwscript GameData reads it so too)
    out = {t: {} for t in ('NPC_', 'CREA', 'RACE', 'CLAS', 'SKIL', 'LEVC', 'BSGN')}
    gmst = {}
    for name in MASTERS:
        path = child_ci(data, name, required=False)
        if path is None:
            continue
        for tag, flags, payload in records(path.read_bytes()):
            if tag == 'GMST':
                f = dict(subrecords(payload))
                if len(f.get('FLTV', b'')) == 4:
                    gmst[_text(f.get('NAME', b'')).casefold()] = struct.unpack('<f', f['FLTV'])[0]
                continue
            if tag not in out:
                continue
            parts = list(subrecords(payload))
            if tag == 'SKIL':
                index = dict(parts).get('INDX', b'')
                if len(index) == 4:
                    out[tag][struct.unpack('<i', index)[0]] = parts
                continue
            ident = _text(dict(parts).get('NAME', b'')).casefold()
            if flags & 0x20 or 'DELE' in dict(parts):
                out[tag].pop(ident, None)
            elif ident:
                out[tag][ident] = parts
    return out, gmst


def _unpack_fields(body):
    out, p = [], 0
    while p < len(body):
        t, n = struct.unpack_from('>4sH', body, p)
        out.append((t.decode('ascii'), body[p + 6:p + 6 + n])); p += 6 + n
    return out


def read_vocabulary(raw):
    """AWT1 -> {'actors': {hash: (tag, fields)}, 'races': {folded id: fields}, 'classes': {...}, 'magicka_mult',
    'skills'}."""
    if raw[:4] != FILE_MAGIC:
        raise ValueError('not an AWT1 actor stats file')
    n, nr, nc, mult = struct.unpack_from('>IIIf', raw, 4)
    skills = raw[20:74]
    p = 74
    actors = {}
    for _ in range(n):
        h, flag, size = struct.unpack_from('>IBH', raw, p)
        actors.setdefault(h, ('CREA' if flag else 'NPC_', _unpack_fields(raw[p + 7:p + 7 + size]))); p += 7 + size
    races, classes = {}, {}
    for target, count in ((races, nr), (classes, nc)):
        for _ in range(count):
            size = struct.unpack_from('>H', raw, p)[0]
            fields = _unpack_fields(raw[p + 2:p + 2 + size]); p += 2 + size
            target[_text(_first(fields, 'NAME')).casefold()] = fields
    levelled = {}
    if p + 4 <= len(raw):
        count = struct.unpack_from('>I', raw, p)[0]; p += 4
        for _ in range(count):
            h, k = struct.unpack_from('>IH', raw, p)
            levelled[h] = list(struct.unpack_from('>%dI' % k, raw, p + 6)); p += 6 + 4 * k
    areas = {}
    if p + 4 <= len(raw):
        count = struct.unpack_from('>I', raw, p)[0]; p += 4
        for _ in range(count):
            key, k = struct.unpack_from('>IH', raw, p)
            areas[key] = list(struct.unpack_from('>%dI' % k, raw, p + 6)); p += 6 + 4 * k
    births = {}
    if p + 4 <= len(raw):
        count = struct.unpack_from('>I', raw, p)[0]; p += 4
        for _ in range(count):
            size = struct.unpack_from('>H', raw, p)[0]
            fields = _unpack_fields(raw[p + 2:p + 2 + size]); p += 2 + size
            births[_text(_first(fields, 'NAME')).casefold()] = fields
    return {'actors': actors, 'races': races, 'classes': classes, 'magicka_mult': mult, 'skills': skills,
            'levelled': levelled, 'levelled_areas': areas, 'births': births}


def expand(hashes, vocabulary):
    """HASHES with every levelled creature list among them replaced by every creature it (and its lists) can give."""
    out, todo, seen = set(), list(hashes), set()
    lists = vocabulary.get('levelled', {})
    while todo:
        h = todo.pop()
        if h in lists:
            if h not in seen:
                seen.add(h); todo.extend(lists[h])
        else:
            out.add(h)
    return out


MAGIC_SLIM = b'AWS2'
SLIM_HEAD = 8


def shared_tables(vocabulary):
    """DRY (the maintainer, 5 November 2026: no repeated blocks): the race and class rows every NPC uses, kept once in
    the shared stats record (STATS_KEY) instead of in every area: {'races': [ids], 'classes': [ids]} sorted."""
    races, classes = set(), set()
    for tag, fields in vocabulary['actors'].values():
        if tag != 'NPC_':
            continue
        r, c = _text(_first(fields, 'RNAM')).casefold(), _text(_first(fields, 'CNAM')).casefold()
        if r in vocabulary['races']:
            races.add(r)
        if c in vocabulary['classes']:
            classes.add(c)
    return {'races': sorted(races), 'classes': sorted(classes)}


def shared_section(hashes, vocabulary, spell_row, shared):
    """The shared stats record's AWS1 section: every race and class row of SHARED in its order (the slim sections'
    indexes) and the entries of HASHES (the creatures the exteriors' levelled lists can give, kept once); then the
    birthsign rows the player's spells come from at character creation (OpenMW 0.51 mechanicsmanagerimp.cpp: the
    birthsign's spells, as the race's powers come from the race rows): births x { u32 id hash, u8 n, n x u16 ASPT row },
    named by the section's last 8 bytes, "BSG1" u16 births u16 the rows' offset in the section."""
    block, report = section(hashes, vocabulary, spell_row, seed=shared)
    rows = []
    for ident in sorted(vocabulary.get('births', {})):
        spells = [spell_row.get(_text(d).casefold()) for t, d in vocabulary['births'][ident] if t == 'NPCS']
        spells = [NO_SPELL if r is None else r for r in spells][:255]
        rows.append(struct.pack('>IB%dH' % len(spells), name_hash(ident), len(spells), *spells))
    if rows and len(block) <= 0xFFFF:
        at = len(block)
        block += b''.join(rows) + b'BSG1' + struct.pack('>HH', len(rows), at)
        report['births'] = len(rows)
        report['bytes'] = len(block)
    return block, report


def section(hashes, vocabulary, spell_row, shared=None, expand_lists=True, seed=None):
    """An area's stats section for the actor id HASHES placed there (an unknown hash is left out); (bytes, stats).
    Without SHARED: a whole AWS1 section (its own race and class rows and skill table). With SHARED (shared_tables):
    the slim AWS2 form, "AWS2" u16 entries u16 0, the index and the entries, whose race and class indexes name the
    shared record's rows (the area holds only its entries). EXPAND_LISTS 0: levelled list hashes are left out."""
    entries, races, classes = [], [], []
    if shared is not None or seed is not None:
        races, classes = list((shared or seed)['races']), list((shared or seed)['classes'])
    wanted = expand(hashes, vocabulary) if expand_lists else set(hashes) - set(vocabulary.get('levelled', {}))
    for h in sorted(wanted):
        got = vocabulary['actors'].get(h)
        if not got:
            continue
        e = actor(got[0], got[1], spell_row)
        if e is None:
            continue
        ri = ci = None
        if e['mask'] & P_RACE:
            if shared is None and e['race'] in vocabulary['races'] and e['race'] not in races:
                races.append(e['race'])
            if shared is None and e['class'] in vocabulary['classes'] and e['class'] not in classes:
                classes.append(e['class'])
            ri = races.index(e['race']) if e['race'] in races else 0xFF
            ci = classes.index(e['class']) if e['class'] in classes else 0xFF
        entries.append((h, encode(e, ri, ci), e['kind']))
    if not entries and seed is None:
        return b'', {'entries': 0}
    if len(races) > 254 or len(classes) > 254:
        raise ValueError('an area names over 254 races or classes')
    if shared is not None:
        race_bytes, class_bytes = [], []
        head = MAGIC_SLIM + struct.pack('>HH', len(entries), 0)
    else:
        race_bytes = [race_row(r, vocabulary['races'][r], spell_row) for r in races]
        class_bytes = [class_row(c, vocabulary['classes'][c]) for c in classes]
        head = MAGIC + struct.pack('>HBBf', len(entries), len(races), len(classes), vocabulary['magicka_mult']) + \
            vocabulary['skills']
    at = len(head) + 6 * len(entries) + sum(len(r) for r in race_bytes) + CLASS_ROW * len(class_bytes)
    index, bodies = [], []
    for h, body, _ in entries:
        if at > 0xFFFF:
            raise ValueError('an area stats section over 64 KiB')
        index.append(struct.pack('>IH', h, at)); bodies.append(body); at += len(body)
    out = head + b''.join(index) + b''.join(race_bytes) + b''.join(class_bytes) + b''.join(bodies)
    kinds = [k for _, _, k in entries]
    offsets = {h: struct.unpack_from('>H', i, 4)[0] for (h, _, _), i in zip(entries, index)}
    return out, {'entries': len(entries), 'bytes': len(out), 'stored': kinds.count(KIND_STORED),
                 'auto': kinds.count(KIND_AUTO), 'creatures': kinds.count(KIND_CREATURE), 'races': len(races),
                 'classes': len(classes), 'offsets': offsets}


# The placed actor's own row in its area (ACTOR-STATS-ALL-61, the direct lookup): an actor row ('A') of the area record
# has an empty 32-byte id (bytes 64..95); the builder writes ROW_MARK at byte ROW_AT and the actor's entry offset in the
# section (u16, big-endian) after it, so the engine jumps to the entry from the row it reads at the area load, with no
# search. The id's first byte stays 0 (an empty id, as before).
ROW_AT, ROW_MARK = 92, b'S\0'
# and the actor's row in the island-wide actor table of id1/mwscript.awm (ACTB, its inventory and spell lists, read
# only when asked), so the live record is made at the area load with no search: "R", 0, u16 row at ACTB_AT
ACTB_AT, ACTB_MARK = 88, b'R\0'


def mark_row(row, offset, actb=None):
    """ROW (96 bytes, an actor row) with the entry OFFSET (and the ACTB row) written; unchanged for offset 0."""
    if not offset or row[0] != ord('A') or any(row[64:96]):
        return row
    out = row[:ROW_AT] + ROW_MARK + struct.pack('>H', offset) + row[ROW_AT + 4:]
    if actb is not None and 0 <= actb < 0xFFFF:
        out = out[:ACTB_AT] + ACTB_MARK + struct.pack('>H', actb) + out[ACTB_AT + 4:]
    return out


def row_actb(row):
    """The ACTB row an actor row carries, None none."""
    return struct.unpack_from('>H', row, ACTB_AT + 2)[0] if row[ACTB_AT:ACTB_AT + 2] == ACTB_MARK else None


def actor_rows(awm_raw):
    """{id hash: ACTB row} of an image's id1/mwscript.awm ({} without an actor table)."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from mwscript import awms
    f = awms.read(awm_raw)
    if 'ACTB' not in f:
        return {}
    names = awms.strings(f)
    return {name_hash(names[struct.unpack_from('>H', f['ACTB'], 96 * i)[0]]): i for i in range(f['ACTB_rows'])}


def row_offset(row):
    """The entry offset an actor row carries, 0 none."""
    return struct.unpack_from('>H', row, ROW_AT + 2)[0] if row[ROW_AT:ROW_AT + 2] == ROW_MARK else 0
