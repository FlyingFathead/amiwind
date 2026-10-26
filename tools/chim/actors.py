# SPDX-License-Identifier: GPL-3.0-only
"""The CHIM actor table (EXPERIMENTAL, build option --chim-actor-table on, default off): every exterior NPC and
creature reference of the game data in one island-wide table outside the frames, for the type 1 window's actors
(engine aw_actors.c with "chim actors table 1"; docs/chim/WORLD_FORMAT.md "Actor table (experimental)").

Until now an exterior actor existed only as an entity of a town frame map (the resident stage places a town's
residents); the region frames place none (CHIM-EXTERIOR-ACTORS-MISSING-46: 93 of 566 exterior NPC references,
0 of 5,415 creature references). The table lists them all, keyed by the game's reference number:

- a record per reference (24 bytes, big-endian): u32 key (the reference number & 0xFFFFFF: the save key rule of the
  template, a large-model cut index never reaches an actor), u16 base, u16 flags, f32 origin x, y, z in the local
  units of the reference's own cell (Quake units, the cell centre at 0, 0: the frame-local units of that cell's
  region frame, so a region frame joining the window places it as its own frame map would), f32 yaw in degrees
  (Quake angles[1]). Flags: bit 0 the origin is the builder's baked ground point (the engine sets aw_ground_baked
  to it and aw_ground_valid 1, as a frame map row says), bit 1 the record comes from a built actor row (its
  position and base as the frame map places it), else from the game data (position of the reference);
- a base per base record (12 bytes): u32 offset of its entity text in the text block, u16 text bytes (0: no actor
  model in this build, so the engine cannot spawn it), u16 kind (0 NPC, 1 creature, 2 levelled creature list,
  3 a dead resident: aw_corpse), u32 FNV-1a of the base record's id (lower case);
- a cell directory (16 bytes per exterior cell with actors, cells in order of their 4 x 4-cell page, then x, y):
  i16 cell x, i16 cell y, u32 first record, u32 records, u32 0; a cell's records are contiguous;
- the base entity text: the key/value pairs of the built actor row without the per-placement fields (origin,
  angles, aw_ref, aw_ground_baked, aw_ground_valid, aw_authored_origin, aw_authored_z), ASCII, each base's text
  ending in a newline; the engine parses it with ED_ParseEdict and sets the per-placement fields from the record.

Header (48 bytes): 'ACT1', u16 0, u16 1 (table version), u32 48, u32 cells, u32 cells offset, u32 records,
u32 records offset, u32 bases, u32 bases offset, u32 text offset, u32 file bytes, u32 0.

Version 3 (what write_table writes when an exterior reference has an instance scale, as the game data has: 5) is
version 2 plus a scale section after the lists (build_table SCALES).

Version 2 (what write_table writes since v0.0.47; build_table without LISTS still writes version 1 byte for byte)
adds the levelled creature lists, so the engine resolves a levelled reference when its cell joins, with the game's
rules (levelled_pick below; behaviour read from OpenMW 0.51 apps/openmw/mwmechanics/levelledlist.cpp and
mwclass/creaturelevlist.cpp, own implementation): the header's last u32 is the offset of the list section; a
levelled reference's base (kind 2) has no text and its u32 offset is the index of its list; every creature a used
list can give (at any level) has a creature base (kind 1) of its own. List section: u32 lists, then per list 8 bytes
(u32 first entry, u16 entries, u8 chance none 0-100, u8 flags: bit 0 "calculate from all levels <= the player's"),
then the entries, 4 bytes each in the record's order (u16 level, u16 target: a base index, or 0x8000 | list index
for a list inside a list). A creature base has text when a creature model library names its model
(tools/creature_library.py, LIBRARY {creature id: base text}); without one, a levelled reference resolves to a
creature the engine counts as "without a model".

What it does not do: only actors whose model a build made (the resident stage: today the town residents; with a
creature library, the creatures it baked) have base text; every other NPC is in the table without a model, and the
engine counts it as not spawnable. Nothing here is reached by a default build.
"""
import re
import struct
from pathlib import Path

MAGIC = b'ACT1'
VERSION = 1                      # build_table without levelled lists
VERSION_LISTS = 2                # with them
VERSION_SCALES = 3               # with them and the instance scales (write_table when a reference is scaled)
SCALE = struct.Struct('>If')                    # 8 bytes: record index, scale
HEADER = struct.Struct('>4sHHIIIIIIIIII')       # 48 bytes
CELL = struct.Struct('>hhIII')                  # 16 bytes
RECORD = struct.Struct('>IHHffff')              # 24 bytes
BASE = struct.Struct('>IHHI')                   # 12 bytes
LIST = struct.Struct('>IHBB')                   # 8 bytes
ENTRY = struct.Struct('>HH')                    # 4 bytes
NESTED = 0x8000                                 # entry target: a list, not a base
ALL_LEVELS = 1                                  # creature list flag: calculate from all levels <= the player's
FLAG_BAKED, FLAG_BUILT = 1, 2
FLAG_SCALED_MODEL = 4            # the base's model is baked at the record's scale: the engine draws it at 1
KINDS = {'NPC_': 0, 'CREA': 1, 'LEVC': 2, 'corpse': 3}
KEY_MASK = 0xFFFFFF
CELL_UNITS = 8192.0              # Morrowind units per exterior cell
LOCAL = 0.25                     # Quake units per Morrowind unit
PAGE = 4                         # cells per page side (the file's order)
SETTING = 'chim_actor_table'
MODES = ('off', 'on')
INSTANCE_FIELDS = ('origin', 'angles', 'aw_ref', 'aw_ground_baked', 'aw_ground_valid', 'aw_authored_origin',
                   'aw_authored_z')
ACTOR_CLASSES = ('aw_npc', 'aw_corpse')
ENTITY = re.compile(rb'\{([^{}]*)\}')
FIELD = re.compile(rb'"([^"]*)"\s+"([^"]*)"')
FILE_NAME = 'chim-actors.cca'    # in maps/, beside the frame maps


def fnv(text):
    h = 2166136261
    for b in text.lower().encode('cp1252', 'replace'):
        h = ((h ^ b) * 16777619) & 0xFFFFFFFF
    return h


def F32(x):
    return struct.unpack('>f', struct.pack('>f', float(x)))[0]


def cell_centre(cell):
    return ((cell[0] + 0.5) * CELL_UNITS, (cell[1] + 0.5) * CELL_UNITS)


# ---------------------------------------------------------------- game data

def exterior_actors(master):
    """[(number, base id, record type, cell (x, y), position, rotation)] of every non-deleted NPC_, CREA and LEVC
    reference placed in an exterior cell of the master's bytes (the entity tracker's census rule)."""
    from mwad.audit import cell_data, records, string, subrecords
    types, cells = {}, []
    for tag, flags, payload in records(master):
        if flags & 0x20:
            continue
        if tag == 'CELL':
            cells.append(cell_data(list(subrecords(payload))))
        elif tag in ('NPC_', 'CREA', 'LEVC'):
            fields = dict(subrecords(payload))
            if 'NAME' in fields and 'DELE' not in fields:
                types[string(fields['NAME']).casefold()] = tag
    out = []
    for cell in cells:
        if cell['flags'] & 1:
            continue
        for ref in cell['refs']:
            tag = types.get(ref.get('id', '').casefold())
            if ref.get('deleted') or tag is None or 'position' not in ref:
                continue
            out.append((ref['number'], ref['id'], tag, (cell['x'], cell['y']), tuple(ref['position']),
                        tuple(ref.get('rotation_radians', (0.0, 0.0, 0.0)))))
    return out


# ---------------------------------------------------------------- levelled creature lists

def levelled_lists(master):
    """{list id (lower case): (flags, chance none, [(entry id lower case, level)])} of every non-deleted LEVC record of
    the master's bytes, entries in the record's order (CNAM, INTV pairs)."""
    from mwad.audit import records, string, subrecords
    out = {}
    for tag, flags, payload in records(master):
        if tag != 'LEVC' or flags & 0x20:
            continue
        fields = list(subrecords(payload))
        names = [d for t, d in fields if t == 'NAME']
        if not names or any(t == 'DELE' for t, _ in fields):
            continue
        data = next((d for t, d in fields if t == 'DATA'), b'\0\0\0\0')
        chance = next((d for t, d in fields if t == 'NNAM'), b'\0')
        entries, pending = [], None
        for t, d in fields:
            if t == 'CNAM':
                pending = string(d, errors='replace').casefold()
            elif t == 'INTV' and pending is not None:
                entries.append((pending, struct.unpack('<H', d[:2])[0]))
                pending = None
        out[string(names[0], errors='replace').casefold()] = (struct.unpack('<I', data[:4])[0], min(chance[0], 100),
                                                              entries)
    return out


def creature_ids(master):
    """The ids (lower case) of every non-deleted CREA record of the master's bytes."""
    from mwad.audit import records, string, subrecords
    out = set()
    for tag, flags, payload in records(master):
        if tag == 'CREA' and not flags & 0x20:
            fields = list(subrecords(payload))
            name = next((d for t, d in fields if t == 'NAME'), None)
            if name is not None and not any(t == 'DELE' for t, _ in fields):
                out.add(string(name, errors='replace').casefold())
    return out


def used_lists(lists, roots):
    """The lists ROOTS reach, themselves and every list inside them, sorted (the table's list order)."""
    seen, todo = set(), [r for r in roots if r in lists]
    while todo:
        lid = todo.pop()
        if lid in seen:
            continue
        seen.add(lid)
        todo.extend(e for e, _ in lists[lid][2] if e in lists and e not in seen)
    return sorted(seen)


def rng_seed(key, seed=0):
    """The roll state of a reference (the engine's ChimActors_RollSeed): its key and the session seed."""
    x = ((key ^ seed) * 2654435761) & 0xFFFFFFFF
    return x or 0x9E3779B9


def rng_next(state):
    """xorshift32 (the engine's ChimActors_Rand): (new state, value)."""
    x = state
    x ^= (x << 13) & 0xFFFFFFFF
    x ^= x >> 17
    x ^= (x << 5) & 0xFFFFFFFF
    return x, x


PICK_NONE = -1
MAX_DEPTH = 8


def levelled_pick(table_lists, index, level, state, depth=0):
    """(base index or PICK_NONE, new state): one roll of list INDEX of a table's list section (read_lists) at player
    LEVEL, as the engine's ChimActors_LevelledPick does. The rule (read from OpenMW 0.51 getLevelledItem, our own
    implementation): chance none first (a roll 0-99 below it gives nothing); the candidates are every entry at or
    below the level when the list calculates from all levels, else only the entries at the highest level at or
    below it; none = nothing; one candidate picked uniformly; a list picked is rolled again at the same level
    (at most MAX_DEPTH deep); an entry naming no record gives nothing."""
    chance, flags, entries = table_lists[index]
    state, v = rng_next(state)
    if v % 100 < chance:
        return PICK_NONE, state
    if flags & ALL_LEVELS:
        cands = [t for lv, t in entries if lv <= level]
    else:
        top = max((lv for lv, _ in entries if lv <= level), default=None)
        cands = [t for lv, t in entries if lv == top]
    if not cands:
        return PICK_NONE, state
    state, v = rng_next(state)
    target = cands[v % len(cands)]
    if target == 0xFFFF:
        return PICK_NONE, state
    if target & NESTED:
        if depth + 1 >= MAX_DEPTH:
            return PICK_NONE, state
        return levelled_pick(table_lists, target & 0x7FFF, level, state, depth + 1)
    return target, state


def levelled_distribution(table_lists, index, level, p=1.0, out=None, depth=0):
    """{base index or PICK_NONE: probability} of one roll (the exact form of levelled_pick)."""
    out = {} if out is None else out
    chance, flags, entries = table_lists[index]
    if flags & ALL_LEVELS:
        cands = [t for lv, t in entries if lv <= level]
    else:
        top = max((lv for lv, _ in entries if lv <= level), default=None)
        cands = [t for lv, t in entries if lv == top]
    some = p * (100 - chance) / 100.0 if cands else 0.0
    out[PICK_NONE] = out.get(PICK_NONE, 0.0) + p - some
    for t in cands:
        q = some / len(cands)
        if t == 0xFFFF or (t & NESTED and depth + 1 >= MAX_DEPTH):
            out[PICK_NONE] += q
        elif t & NESTED:
            levelled_distribution(table_lists, t & 0x7FFF, level, q, out, depth + 1)
        else:
            out[t] = out.get(t, 0.0) + q
    return out


# ---------------------------------------------------------------- built rows

def entity_rows(text):
    """[{key: value}] of a map's entity text (bytes)."""
    return [{k.decode('latin1'): v.decode('latin1') for k, v in FIELD.findall(m)} for m in ENTITY.findall(text)]


def map_entities(path):
    """Entity rows of a BSP29 or .chim frame map file (lump 0)."""
    data = Path(path).read_bytes()
    offset, length = struct.unpack_from('<ii', data, 4)
    return entity_rows(data[offset:offset + length])


def built_actors(maps, frame_centres):
    """{reference number: (base id, base text, cell, cell-local origin, yaw, baked, kind)} of every actor row
    (aw_npc, aw_corpse) of the frame maps under MAPS whose worldspawn names a CHIM frame (_chim_frame). The row's
    frame-local origin is moved to its cell's local units: + (frame centre - cell centre) x 0.25.
    frame_centres: {frame cell: frame centre in Morrowind units} (the CHIM world's frame files). Intro roles are
    left out (the opening's own actors, not world state)."""
    out = {}
    from map_files import frame_maps
    # the frame maps by their key, whatever their extension; a CHIM room map (an interior: its residents are not
    # exterior actors) is not one (IMAGE-ROOM-MAPS-LATE-PASSES-48 sweep)
    for path in frame_maps(maps):
        rows = map_entities(path)
        world = next((r for r in rows if r.get('classname') == 'worldspawn'), {})
        if '_chim_frame' not in world:
            continue
        fcell = tuple(int(v) for v in world['_chim_frame'].split())
        centre = frame_centres.get(fcell, cell_centre(fcell))
        for r in rows:
            if r.get('classname') not in ACTOR_CLASSES or not r.get('aw_ref') or \
                    float(r.get('aw_intro_role', 0) or 0):
                continue
            number = int(float(r['aw_ref']))
            o = [float(v) for v in r['origin'].split()]
            world_xy = (centre[0] + o[0] / LOCAL, centre[1] + o[1] / LOCAL)
            cell = (int(world_xy[0] // CELL_UNITS), int(world_xy[1] // CELL_UNITS))
            cc = cell_centre(cell)
            shift = ((centre[0] - cc[0]) * LOCAL, (centre[1] - cc[1]) * LOCAL)
            local = (F32(o[0] + shift[0]), F32(o[1] + shift[1]), F32(o[2]))
            baked = r.get('aw_ground_valid') == '1' and 'aw_ground_baked' in r and \
                [float(v) for v in r['aw_ground_baked'].split()] == o
            yaw = float(r.get('angles', '0 0 0').split()[1]) if 'angles' in r else float(r.get('angle', 0) or 0)
            text = ''.join('"%s" "%s"\n' % (k, v) for k, v in r.items() if k not in INSTANCE_FIELDS)
            out[number] = (r.get('aw_source_id', ''), text, cell, local, F32(yaw), baked,
                           'corpse' if r['classname'] == 'aw_corpse' else None)
    return out


# ---------------------------------------------------------------- the table

def scale_key(ident, scale):
    """The library key of a creature at an instance scale ('id' at 1, else 'id@S' with S to 4 decimals)."""
    return ident if abs(scale - 1.0) < 1e-4 else '%s@%.4f' % (ident, scale)


def build_table(refs, built=None, lists=None, creatures=None, library=None, scales=None):
    """(table bytes, report) from exterior_actors' rows and built_actors' rows (keyed by reference number).

    Without LISTS: version 1, as before. With LISTS (levelled_lists of the master) and CREATURES (creature_ids):
    version 2 with the levelled creature lists the exterior uses; LIBRARY {record id: base text} gives the creature
    and NPC bases (direct references without a built row and the creatures the lists can give) their entity text
    (the actor library stage: tools/actor_library.py install).
    SCALES {reference number: instance scale} (exterior_scales; version 2 only): when a reference has a scale other
    than 1 the table is version 3: a scale section after the lists (u32 count, then per scaled record u32 record
    index and f32 scale, by record index); a scaled creature reference takes its library text at that scale (key
    'id@S', scale_key) when the library has it, and a scaled levelled reference a copy of its list whose creatures
    take their texts at that scale (the original scales the creature a list gives by the list reference's scale:
    OpenMW mwclass/creaturelevlist.cpp)."""
    built = built or {}
    library = {k.casefold(): v for k, v in (library or {}).items()}
    v2 = lists is not None
    creatures = set(creatures or ())
    scaled = {n: round(float(sc), 4) for n, sc in (scales or {}).items() if v2 and abs(sc - 1.0) > 1e-5}
    order = used_lists(lists, {b.casefold() for _, b, t, *_ in refs if t == 'LEVC'}) if v2 else []
    list_index = {lid: i for i, lid in enumerate(order)}
    # a scale the library has baked models for (keys 'id@S'): those references name the baked models (and say so
    # in their flags); without them the engine draws the model at the record's scale (AWU_SCALE)
    baked_scales = {k.rpartition('@')[2] for k in library if '@' in k}
    copies = sorted({(lid, scaled[n]) for n, b, t, *_ in refs if t == 'LEVC' and n in scaled
                     and '%.4f' % scaled[n] in baked_scales for lid in used_lists(lists, {b.casefold()})})
    for lid, sc in copies:
        list_index[(lid, sc)] = len(list_index)
    bases, base_index, texts = [], {}, bytearray()
    records = []
    kinds_seen = {}

    def text_at(ident, sc):
        return library.get(scale_key(ident, sc), library.get(ident, '')) if sc != 1.0 else library.get(ident, '')

    def base_of(base_id, kind, text, at=None):
        key = ((base_id.casefold(), kind, text) if at is None else (base_id.casefold(), kind, text, at)) if v2 \
            else (base_id.casefold(), text)
        if key not in base_index:
            raw = text.encode('latin1')
            if len(raw) > 0xFFFF:
                raise ValueError('Actor base text of %s is too long' % base_id)
            base_index[key] = len(bases)
            bases.append((len(texts) if at is None else at, len(raw), kind, fnv(base_id)))
            texts.extend(raw)
        return base_index[key]

    for number, base_id, tag, cell, position, rotation in refs:
        row = built.get(number)
        kind = KINDS[row[6]] if row and row[6] else KINDS[tag]
        sc = scaled.get(number, 1.0)
        own_scale = sc != 1.0 and '%.4f' % sc in baked_scales
        if v2 and tag == 'LEVC' and not row:
            lid = base_id.casefold()
            index = base_of(base_id, kind, '', at=list_index[(lid, sc) if own_scale else lid])
        else:
            text = row[1] if row else ((text_at(base_id.casefold(), sc) if own_scale else
                                        library.get(base_id.casefold(), '')) if v2 and tag in ('CREA', 'NPC_') else '')
            own_scale = own_scale and not row and scale_key(base_id.casefold(), sc) in library
            index = base_of(base_id, kind, text)
        flags = FLAG_SCALED_MODEL if own_scale else 0
        if row:
            _, _, cell, origin, yaw, baked, _ = row
            flags |= FLAG_BUILT | (FLAG_BAKED if baked else 0)
        else:
            cc = cell_centre(cell)
            origin = (F32((position[0] - cc[0]) * LOCAL), F32((position[1] - cc[1]) * LOCAL), F32(position[2] * LOCAL))
            # TES3 z rotation (radians, clockwise seen from above) as the Quake yaw (chim.models.yaw_degrees' rule)
            yaw = F32(-rotation[2] * 180.0 / 3.141592653589793)
        records.append((cell, number & KEY_MASK, index, flags, origin, yaw, sc))
        kinds_seen[kind] = kinds_seen.get(kind, 0) + 1
    # the lists' entries: a creature the list can give gets a creature base (its library text, or none)
    table_lists, missing = [], []
    for lid, sc in [(lid, 1.0) for lid in order] + copies:
        flags, chance, entries = lists[lid]
        out_entries = []
        for entry, level in entries:
            if entry in list_index:
                target = NESTED | list_index[(entry, sc) if sc != 1.0 else entry]
            elif entry in creatures:
                target = base_of(entry, KINDS['CREA'], text_at(entry, sc))
            else:
                target = 0xFFFF          # names no creature or list: gives nothing (OpenMW ignores it the same way)
                missing.append((lid, entry))
            out_entries.append((min(level, 0xFFFF), target))
        table_lists.append((chance, flags & 0xFF, out_entries))
    if len(bases) > (0x7FFF if v2 else 0xFFFF):
        raise ValueError('Too many actor bases')
    records.sort(key=lambda r: ((r[0][0] // PAGE, r[0][1] // PAGE), r[0], r[1]))
    cells = []
    for i, r in enumerate(records):
        if not cells or cells[-1][0] != r[0]:
            cells.append([r[0], i, 0])
        cells[-1][2] += 1
    at = HEADER.size
    cells_at = at
    records_at = cells_at + len(cells) * CELL.size
    bases_at = records_at + len(records) * RECORD.size
    text_at = bases_at + len(bases) * BASE.size
    total = text_at + len(texts)
    total += (-total) % 4
    lists_at = 0
    lists_raw = bytearray()
    if v2:
        lists_at = total
        lists_raw += struct.pack('>I', len(table_lists))
        first = 0
        for chance, flags, entries in table_lists:
            lists_raw += LIST.pack(first, len(entries), chance, flags)
            first += len(entries)
        for chance, flags, entries in table_lists:
            for level, target in entries:
                lists_raw += ENTRY.pack(level, target)
        if scaled:
            rows = [(i, r[6]) for i, r in enumerate(records) if r[6] != 1.0]
            lists_raw += struct.pack('>I', len(rows))
            for i, sc in rows:
                lists_raw += SCALE.pack(i, sc)
        total = lists_at + len(lists_raw)
    version = (VERSION_SCALES if scaled else VERSION_LISTS) if v2 else VERSION
    out = bytearray(HEADER.pack(MAGIC, 0, version, HEADER.size, len(cells), cells_at,
                                len(records), records_at, len(bases), bases_at, text_at, total, lists_at))
    for cell, first, n in cells:
        out += CELL.pack(cell[0], cell[1], first, n, 0)
    for cell, key, base, flags, origin, yaw, _sc in records:
        out += RECORD.pack(key, base, flags, *origin, yaw)
    for offset, n, kind, h in bases:
        out += BASE.pack(offset, n, kind, h)
    out += texts
    out += bytes((lists_at or total) - len(out))
    out += lists_raw
    spawnable = sum(1 for r in records if bases[r[2]][1])
    report = {'records': len(records), 'cells': len(cells), 'bases': len(bases), 'bytes': len(out),
              'text_bytes': len(texts), 'spawnable_records': spawnable,
              'by_kind': {k: kinds_seen.get(v, 0) for k, v in KINDS.items()},
              'built_rows_used': sum(1 for r in records if r[3] & FLAG_BUILT),
              'built_rows_not_in_game_data': sorted(set(built) - {n for n, *_ in refs})}
    if v2:
        targets = {t for _, _, e in table_lists for _, t in e if not t & NESTED and t != 0xFFFF}
        report['levelled'] = {'lists': len(table_lists), 'entries': sum(len(e) for _, _, e in table_lists),
                              'list_bytes': len(lists_raw), 'creature_bases': len(targets),
                              'creature_bases_with_model': sum(1 for t in targets if bases[t][1]),
                              'entries_naming_nothing': len(missing), 'scaled_list_copies': len(copies)}
        report['scaled_records'] = sum(1 for r in records if r[6] != 1.0)
    return bytes(out), report


def read_table(data):
    """(header dict, cells [(cell, first, n)], records [dict], bases [dict], text bytes) of a table (version 1 or 2;
    a version 2 table's lists: read_lists)."""
    v = HEADER.unpack_from(data)
    if v[0] != MAGIC or v[2] not in (VERSION, VERSION_LISTS, VERSION_SCALES) or v[3] != HEADER.size or \
            v[11] != len(data):
        raise ValueError('Not a CHIM actor table')
    n_cells, cells_at, n_rec, rec_at, n_base, base_at, text_at = v[4:11]
    end = v[12] if v[2] != VERSION else len(data)
    cells = [CELL.unpack_from(data, cells_at + k * CELL.size) for k in range(n_cells)]
    records = []
    for k in range(n_rec):
        key, base, flags, x, y, z, yaw = RECORD.unpack_from(data, rec_at + k * RECORD.size)
        records.append({'key': key, 'base': base, 'flags': flags, 'origin': (x, y, z), 'yaw': yaw})
    bases = []
    for k in range(n_base):
        o, n, kind, h = BASE.unpack_from(data, base_at + k * BASE.size)
        bases.append({'text': data[text_at + o:text_at + o + n].decode('latin1') if n else '', 'kind': kind, 'hash': h,
                      **({'list': o} if kind == KINDS['LEVC'] and v[2] != VERSION else {})})
    return ({'cells': n_cells, 'records': n_rec, 'bases': n_base, 'version': v[2]},
            [((c[0], c[1]), c[2], c[3]) for c in cells], records, bases, data[text_at:end])


def read_lists(data):
    """[(chance none, flags, [(level, target)])] of a version 2 or 3 table's list section (None for version 1)."""
    v = HEADER.unpack_from(data)
    if v[2] == VERSION:
        return None
    at = v[12]
    n = struct.unpack_from('>I', data, at)[0]
    heads = [LIST.unpack_from(data, at + 4 + k * LIST.size) for k in range(n)]
    entries_at = at + 4 + n * LIST.size
    out = []
    for first, count, chance, flags in heads:
        out.append((chance, flags, [ENTRY.unpack_from(data, entries_at + (first + k) * ENTRY.size)
                                    for k in range(count)]))
    return out


def read_scales(data):
    """{record index: scale} of a version 3 table (empty for versions 1 and 2)."""
    v = HEADER.unpack_from(data)
    if v[2] != VERSION_SCALES:
        return {}
    at = v[12]
    n = struct.unpack_from('>I', data, at)[0]
    heads = [LIST.unpack_from(data, at + 4 + k * LIST.size) for k in range(n)]
    at += 4 + n * LIST.size + sum(c for _, c, _, _ in heads) * ENTRY.size
    count = struct.unpack_from('>I', data, at)[0]
    return dict(SCALE.unpack_from(data, at + 4 + k * SCALE.size) for k in range(count))


def exterior_scales(master):
    """{reference number: instance scale} of the exterior NPC, creature and levelled creature references whose
    scale is not 1 (exterior_actors' census rule)."""
    numbers = {n for n, *_ in exterior_actors(master)}
    from mwad.audit import cell_data, records, subrecords
    out = {}
    for tag, flags, payload in records(master):
        if tag != 'CELL' or flags & 0x20:
            continue
        cell = cell_data(list(subrecords(payload)))
        if cell['flags'] & 1:
            continue
        for ref in cell['refs']:
            if ref['number'] in numbers and abs(ref.get('scale', 1.0) - 1.0) > 1e-5:
                out[ref['number']] = float(ref['scale'])
    return out


def frame_centres(chim_root):
    """{frame cell: frame centre (Morrowind units)} of a CHIM world's frame files."""
    from chim import format as F
    from chim import reach  # noqa: F401 (world formats 0.8 and 0.9)
    root = Path(chim_root)
    _, files, _, _ = F.read_index((root / 'world.cwi').read_bytes())
    out = {}
    for f in files:
        if f['kind'] == b'FRAM':
            frame, _, _ = F.read_frame((root / f['path']).read_bytes())
            out[tuple(frame['cell'])] = tuple(frame['centre'])
    return out


def master_tables(master_path):
    """What the table takes from the master alone: (exterior actors, levelled lists, creature ids, exterior scales).
    About 5 s on one core; the image step works it out beside its finalize checks and hands it to write_table
    (BUILD-IMAGE-FINALIZE-UNDERUSED-48)."""
    master = Path(master_path).read_bytes()
    return exterior_actors(master), levelled_lists(master), creature_ids(master), exterior_scales(master)


def write_table(path, master_path, maps, chim_root=None, library=None, tables=None):
    """Write the table for an image (version 2, or 3 with instance scales): the game data's exterior actors, the built rows of the frame maps in
    MAPS (positions and bases as placed there) and the levelled creature lists the exterior uses; LIBRARY (a creature
    library manifest, tools/creature_library.py, or {record id: base text}: tools/actor_library.py install) gives
    creature and NPC bases their model. TABLES: master_tables(MASTER_PATH), when worked out already. Returns the
    report."""
    refs, levelled, creatures, scales = master_tables(master_path) if tables is None else tables
    built = built_actors(maps, frame_centres(chim_root) if chim_root else {})
    if library is not None and not isinstance(library, dict):
        from creature_library import base_texts
        library = base_texts(library)
    data, report = build_table(refs, built, levelled, creatures, library, scales)
    Path(path).write_bytes(data)
    return report


def main(argv=None):
    import argparse
    import json
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--master', required=True)
    p.add_argument('--maps', required=True, help='folder of the frame maps (.chim) whose actor rows are used')
    p.add_argument('--chim', help='the CHIM world folder (chim/) for the frame centres')
    p.add_argument('--library', help='a creature library manifest (tools/creature_library.py) for the creature bases')
    p.add_argument('--out', required=True)
    a = p.parse_args(argv)
    print(json.dumps(write_table(a.out, a.master, a.maps, a.chim, a.library), indent=1, sort_keys=True))


if __name__ == '__main__':
    main()
