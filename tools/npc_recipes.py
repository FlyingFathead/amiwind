#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Residents drawn from parts at run time (docs/MODULAR_NPCS.md "Stage: residents from parts"; NPC-PARTS-RUNTIME-59).

The player's body is assembled by the engine from the parts library (tools/prepare_player_parts.py: one shared
skeletal model per part mesh, the recipe view/parts.txt). Here each resident gets its own recipe line, the same
choices the fused bake makes (mwad.npc.outfit: the race and sex, the record's head and hair, the worn clothing and
armour after its levelled lists), and the engine assembles its body from the same library by the same rule
(engine/aga/src/aw_player_parts.c AW_PartsAssemble, aw_npc_parts.c). The fused model stays in the image: it is the
resident's server model (collision, animation, carried items) and the drawing fallback (aw_npc_parts 0).
(tools/npc_parts.py is the earlier build-time parts library of the gallery, a different thing.)

  id1/view/npc_parts/<key>.awnb  one small binary table per place (BUILD-NPC-RECIPES-PER-CELL-59; the format below
                           at RECORD): key c<x>_<y> for an exterior cell (grid numbers), the map name for a room,
                           each with its own few names. Each table is made from the AWNP1 text recipe of
                           its residents (the reference form, recipe_text):
                           N <npc id> <race> <0|1> <head|-> <hair|-> <worn item> ...
                           ids with a space written '|' (as in view/parts.txt)

Only residents the engine can draw so get a line: a skeletal actor (--npc-anim-type 2) on the shared humanoid table
of the parts (a woman of a human race has her own female table, which the parts do not use yet), alive at the start
and without its own animation file. The rest keep their fused model."""
import math
import re
import struct
from pathlib import Path

RECIPE_FORMAT = 'AWNP1'
RECIPE_PATH = 'view/npc_parts.txt'
ITEMS_MAX = 16          # aw_player_parts.h AW_PARTS_ITEMS
WORD_MAX = 63           # AW_PARTS_ID - 1


def word(identifier):
    """An id as a recipe word (prepare_player_parts.recipe_text's rule); ValueError when it cannot be one."""
    text = str(identifier)
    if not text or any(c in text for c in '\t\n=,|') or not text.isascii() or len(text) > WORD_MAX:
        raise ValueError('Recipe id not a plain ASCII word: %r' % text)
    return text.replace(' ', '|')


def eligible(appearance):
    """(True, '') when the engine can draw this resident from parts, else (False, why)."""
    if appearance.get('initially_dead'):
        return False, 'dead at the start (one baked pose)'
    if appearance.get('animation'):
        return False, 'its own animation file (its own table view)'
    if appearance.get('female') and appearance.get('skeleton') == 'meshes/base_anim.nif':
        return False, 'the female table (the parts are on the shared humanoid table)'
    if appearance.get('skeleton') not in ('meshes/base_anim.nif', 'meshes/base_animkna.nif'):
        return False, 'not a humanoid skeleton'
    return True, ''


def recipe_line(appearance):
    """The resident's recipe line (no newline). The head and hair are the body ids the outfit chose for slots 0 and 1
    ('-' when none shows: the engine then takes the race's first, which a helmet covers anyway); the worn items are
    those the outfit put on, in its order, at most ITEMS_MAX."""
    by_slot = {p['slot']: p['id'] for p in appearance.get('parts', ()) if p.get('slot') in (0, 1)}
    items = [e['item'] for e in appearance.get('equipment', ()) if e.get('item')]
    if len(items) > ITEMS_MAX:
        raise ValueError('%s wears %d items, over %d' % (appearance['id'], len(items), ITEMS_MAX))
    words = ['N', word(appearance['id']), word(appearance['race']), '1' if appearance.get('female') else '0',
             word(by_slot[0]) if by_slot.get(0) else '-', word(by_slot[1]) if by_slot.get(1) else '-']
    return ' '.join(words + [word(i) for i in items])


def recipe_text(appearances):
    """(text, report): the recipe of every eligible resident, by id; report = {'lines', 'left': {id: why}}."""
    lines, left, seen = [RECIPE_FORMAT], {}, set()
    for appearance in sorted(appearances, key=lambda a: a['id'].casefold()):
        key = appearance['id'].casefold()
        if key in seen:
            continue
        seen.add(key)
        ok, why = eligible(appearance)
        if ok:
            try:
                lines.append(recipe_line(appearance))
                continue
            except ValueError as error:
                why = str(error)
        left[appearance['id']] = why
    return '\n'.join(lines) + '\n', {'lines': len(lines) - 1, 'left': left}


def parse_lines(text, label):
    """{id casefold: line} of a recipe file's text; ValueError naming LABEL when it is not AWNP1."""
    lines = text.splitlines()
    if not lines or lines[0] != RECIPE_FORMAT:
        raise ValueError('%s from %s is not an %s recipe file' % (RECIPE_PATH, label, RECIPE_FORMAT))
    found = {}
    for line in lines[1:]:
        if not line.strip():
            continue
        words = line.split(' ')
        if len(words) < 6 or words[0] != 'N':
            raise ValueError('%s from %s: not a recipe line: %r' % (RECIPE_PATH, label, line))
        key = words[1].casefold()
        if key in found and found[key] != line:
            raise ValueError('%s from %s: resident %s listed twice with other lines' % (RECIPE_PATH, label, words[1]))
        found[key] = line
    return found


def merge_texts(sources):
    """One recipe file from SOURCES [(label, text)]: the union of their lines, sorted by NPC id (casefold, as
    recipe_text), the header once. The same NPC in two sources must have the identical line, else ValueError naming
    both sources (BUILD-NPC-RECIPES-COLLIDE-59: every stage that prepares residents writes its own file)."""
    merged, owner = {}, {}
    for label, text in sources:
        for key, line in parse_lines(text, label).items():
            if key in merged and merged[key] != line:
                raise ValueError('%s: resident %s has other recipes in %s and %s: %r / %r'
                                 % (RECIPE_PATH, line.split(' ')[1], owner[key], label, merged[key], line))
            merged.setdefault(key, line)
            owner.setdefault(key, label)
    return '\n'.join([RECIPE_FORMAT] + [merged[k] for k in sorted(merged)]) + '\n'


# Which stage put each line into an image's recipe file (by the file's path), for the conflict message.
_INSTALLED = {}


def merge_into(target, source, label):
    """The bytes of the image's recipe file TARGET merged with a stage's SOURCE (LABEL names the stage); nothing is
    written. ValueError on a conflicting line, naming both stages."""
    target, source = Path(target), Path(source)
    stages = _INSTALLED.setdefault(str(target), ['the scene the image starts from (area stage)'])
    before = 'the image (staged by %s)' % ' + '.join(stages)
    text = merge_texts([(before, target.read_text(encoding='ascii')), (label, source.read_text(encoding='ascii'))])
    stages.append(label)
    return text.encode('ascii')


# Image files that several stages each write for their own part and the image install merges instead of refusing
# as a collision (tools/chim_rooms.py install, tools/room_batches.py install): published path -> merge function
# merge(target, source, label) -> bytes.
MERGEABLE = {RECIPE_PATH: merge_into}


# One table per place (BUILD-NPC-RECIPES-PER-CELL-59): the engine holds only the tables of the places loaded now, the
# way it loads the residents themselves (aw_npc_parts.c, aw_actors.c): an exterior cell's table comes in when the
# streamer's window joins that cell's frame (prefetched frames included) and goes when it leaves, a room's table comes
# in when the room is entered and goes with its map. The one island-wide file (RECIPE_PATH) is no longer written;
# MERGEABLE above stays for an image staged from an older stage output and matches nothing the stages write now.
TABLE_DIR = 'view/npc_parts'
KEY_MAX = 40            # aw_npc_parts.c table_read: "view/npc_parts/%.40s.awnb" in MAX_QPATH (64)


def cell_key(x, y):
    """The table key of exterior cell X Y (the game's cell grid numbers; aw_player_parts.c AW_NpcTableCellKey)."""
    return 'c%d_%d' % (int(x), int(y))


def cell_of(position, cell_units=8192):
    """The exterior cell grid numbers (x, y) of a game position."""
    return math.floor(position[0] / cell_units), math.floor(position[1] / cell_units)


def table_path(key):
    """The image path of a place's table; ValueError when KEY cannot name one."""
    if not key or len(key) > KEY_MAX or not key.isascii() or any(c in key for c in '/\\ \t\n.'):
        raise ValueError('Not a recipe table key: %r' % key)
    return '%s/%s.awnb' % (TABLE_DIR, key)


def tables(appearances, placements):
    """({key: text}, report): the recipe table of every place in PLACEMENTS [(key, npc id)] that has a resident drawn
    from parts, each with the lines of its own residents (recipe_text's lines, so a resident has the same line in every
    table it is in); report = {'lines', 'left', 'tables', 'bytes', 'largest': (key, bytes)}."""
    by_id = {a['id'].casefold(): a for a in appearances}
    _, report = recipe_text(appearances)
    places = {}
    report['places_left'] = []
    for key, identifier in placements:
        try:
            table_path(key)
        except ValueError:      # a room map name too long for a table path: its residents keep their fused models
            if key not in report['places_left']:
                report['places_left'].append(key)
            continue
        appearance = by_id.get(identifier.casefold())
        if appearance is not None and appearance['id'] not in report['left']:
            places.setdefault(key, {})[appearance['id'].casefold()] = appearance
    texts = {key: recipe_text(list(found.values()))[0] for key, found in sorted(places.items())}
    sizes = {key: len(text) for key, text in texts.items()}
    report.update(tables=len(texts), bytes=sum(sizes.values()),
                  largest=max(sizes.items(), key=lambda kv: (kv[1], kv[0])) if sizes else ('', 0))
    return texts, report


# The image's form of the tables (the maintainer's design, 3 November 2026: per cell or interior, packed): compact
# binary, big-endian (the 68k's own order), searched by aw_player_parts.c without parsing any text. Each place's file
# is whole on its own: its residents' records and the few names they use (its own small vocabulary), so it is read
# with one read, nothing island-wide is held, and no two stages ever write the same file.
#   view/npc_parts/<key>.awnb   AWNB: u8 version 2, u8 record size, u16 residents, u16 names, u16 0, then one record
#                              per resident sorted by its id hash: u32 FNV-1a of the id (recipe word, lower case),
#                              u8 race name index * 2 + female, u8 items worn, u16 head, u16 hair, ITEMS_MAX x u16
#                              worn items (name indices; NONE unused); then u16 offset per name (from the names'
#                              start) and the names (recipe words as written, NUL-ended): the races first, then the
#                              parts, each sorted.
RECORD = 4 + 1 + 1 + 2 + 2 + 2 * ITEMS_MAX
HEADER = 12
NONE = 0xFFFF


def id_hash(identifier):
    """FNV-1a 32 of the recipe word of IDENTIFIER, lower case (aw_player_parts.c AW_NpcIdHash)."""
    h = 0x811C9DC5
    for byte in word(identifier).lower().encode('ascii'):
        h = ((h ^ byte) * 0x01000193) & 0xFFFFFFFF
    return h


def table_bytes(text):
    """The AWNB table of an AWNP1 TEXT (one place's residents), with its own names; ValueError on two ids with one
    hash or a table too large for its fields."""
    rows = [line.split(' ') for line in text.splitlines()[1:] if line.strip()]
    races = sorted({w[2] for w in rows})
    parts = sorted({n for w in rows for n in w[4:] if n != '-'} - set(races))
    names = races + parts
    if len(races) > 127 or len(names) >= NONE:
        raise ValueError('Recipe table too large: %d races, %d names' % (len(races), len(names)))
    at = {n: i for i, n in enumerate(races)}
    at.update({n: len(races) + i for i, n in enumerate(parts)})
    def index(name):
        return NONE if name == '-' else at[name]
    records = {}
    for w in rows:
        items = [index(i) for i in w[6:]]
        h = id_hash(w[1].replace('|', ' '))
        if h in records:
            raise ValueError('Residents %s and another share the id hash %08x in one table' % (w[1], h))
        records[h] = struct.pack('>IBBHH', h, at[w[2]] * 2 + (w[3] == '1'), len(items), index(w[4]),
                                 index(w[5])) + struct.pack('>%dH' % ITEMS_MAX, *(items + [NONE] * (ITEMS_MAX - len(items))))
    offsets, blob = [], b''
    for name in names:
        offsets.append(len(blob))
        blob += name.encode('ascii') + b'\0'
    if len(blob) > 0xFFFF:
        raise ValueError('Recipe table names over 64 KiB')
    return (b'AWNB' + struct.pack('>BBHHH', 2, RECORD, len(records), len(names), 0) +
            b''.join(records[h] for h in sorted(records)) + struct.pack('>%dH' % len(names), *offsets) + blob)


# Where the tables are stored (the maintainer, 3 November 2026: no file per cell, an Amiga open and directory search
# each): every exterior cell's table in ONE pack, view/npc_parts/cells.awnp, with its index at its head (held in
# memory once read: one seek and one read per cell after that):
#   AWNP, u16 cells, u16 0, then per cell sorted by (x, y): i16 x, i16 y, u32 offset (from the file's start), u32 size;
#   then the tables. Only the stage with the exterior (the area stage) writes it.
# A room's table stays its own file, view/npc_parts/<map>.awnb: read once on entering the room, beside the room's own
# map load (one open among the many of a map load), and no two room stages ever write the same one.
PACK_PATH = TABLE_DIR + '/cells.awnp'
PACK_ENTRY = 12
CELL_KEY = re.compile(r'^c(-?\d+)_(-?\d+)$')


def pack_bytes(cells):
    """The cells pack of CELLS {(x, y): table bytes}."""
    order = sorted(cells)
    at = 8 + PACK_ENTRY * len(order)
    head, body = [b'AWNP', struct.pack('>HH', len(order), 0)], []
    for xy in order:
        head.append(struct.pack('>hhII', xy[0], xy[1], at, len(cells[xy])))
        body.append(cells[xy])
        at += len(cells[xy])
    return b''.join(head + body)


def pack_tables(data):
    """{(x, y): table bytes} of a cells pack (the reader the tests compare with)."""
    if data[:4] != b'AWNP':
        raise ValueError('not a cells pack')
    count, = struct.unpack_from('>H', data, 4)
    out = {}
    for i in range(count):
        x, y, at, size = struct.unpack_from('>hhII', data, 8 + PACK_ENTRY * i)
        out[(x, y)] = data[at:at + size]
    return out


# The resident directory (the maintainer, 3 November 2026: a local table that also works globally): id hash -> the
# place whose table holds the resident, 6 bytes a resident plus the place names, so a lookup outside the places loaded
# now reads only that one table (aw_npc_parts.c narrow_find). Each stage writes its own residents; the image install
# merges them (MERGEABLE), the first place per hash kept.
#   AWND, u16 places, u16 0, u32 residents; per resident sorted by hash: u32 hash, u16 place; u16 offset per place
#   name (from the names' start); the names (NUL-ended, sorted).
DIR_PATH = TABLE_DIR + '/dir.awnd'


def dir_bytes(entries):
    """The directory of ENTRIES {id hash: place key}."""
    names = sorted(set(entries.values()))
    at = {n: i for i, n in enumerate(names)}
    offsets, blob = [], b''
    for name in names:
        offsets.append(len(blob))
        blob += name.encode('ascii') + b'\0'
    if len(names) > 0xFFFF or len(blob) > 0xFFFF:
        raise ValueError('Resident directory too large: %d places' % len(names))
    return (b'AWND' + struct.pack('>HHI', len(names), 0, len(entries)) +
            b''.join(struct.pack('>IH', h, at[entries[h]]) for h in sorted(entries)) +
            struct.pack('>%dH' % len(names), *offsets) + blob)


def parse_dir(data, label='the directory'):
    """{id hash: place key} of a directory."""
    if data[:4] != b'AWND':
        raise ValueError('%s from %s is not a resident directory' % (DIR_PATH, label))
    places, _, count = struct.unpack_from('>HHI', data, 4)
    base = 12 + 6 * count
    offsets = struct.unpack_from('>%dH' % places, data, base)
    names_at = base + 2 * places
    names = [data[names_at + o:data.index(b'\0', names_at + o)].decode('ascii') for o in offsets]
    return {h: names[p] for h, p in (struct.unpack_from('>IH', data, 12 + 6 * i) for i in range(count))}


def merge_dir(target, source, label):
    """The image's directory TARGET with a stage's SOURCE: the union (a resident placed by two stages keeps the
    image's place: either table holds its one recipe)."""
    merged = parse_dir(Path(source).read_bytes(), label)
    merged.update(parse_dir(Path(target).read_bytes(), 'the image'))
    return dir_bytes(merged)


MERGEABLE[DIR_PATH] = merge_dir


def write_tables(id1, appearances, placements, log=print):
    """Write the binary tables into ID1 for APPEARANCES placed at PLACEMENTS [(key, npc id)]: the exterior cells' in
    view/npc_parts/cells.awnp, each room's in view/npc_parts/<map>.awnb. Returns the report, with the sizes: per place
    typical (median) and largest, names per table, the pack's bytes."""
    texts, report = tables(appearances, placements)
    folder = Path(id1) / TABLE_DIR
    folder.mkdir(parents=True, exist_ok=True)
    sizes, names, cells = {}, {}, {}
    for key, text in texts.items():
        data = table_bytes(text)
        cell = CELL_KEY.match(key)
        if cell:
            cells[(int(cell.group(1)), int(cell.group(2)))] = data
        else:
            (Path(id1) / table_path(key)).write_bytes(data)
        sizes[key] = len(data)
        names[key] = struct.unpack_from('>H', data, 8)[0]
    if cells:
        pack = pack_bytes(cells)
        (Path(id1) / PACK_PATH).write_bytes(pack)
        report['pack_bytes'], report['pack_index_bytes'] = len(pack), 8 + PACK_ENTRY * len(cells)
    entries = {}
    for key, text in sorted(texts.items()):
        for line in text.splitlines()[1:]:
            entries.setdefault(id_hash(line.split(' ')[1].replace('|', ' ')), key)
    if entries:
        directory = dir_bytes(entries)
        (Path(id1) / DIR_PATH).write_bytes(directory)
        report['dir_bytes'] = len(directory)
    per = sorted(sizes.values())
    report.update(tables=len(sizes), bytes=sum(per), typical=per[len(per) // 2] if per else 0,
                  largest=max(sizes.items(), key=lambda kv: (kv[1], kv[0])) if sizes else ('', 0), record=RECORD,
                  names_largest=max(names.values()) if names else 0)
    log('Residents from parts: %d recipes in %d place tables (%d bytes in all; typical %d, largest %s %d; %d bytes a '
        'resident record, at most %d names in a table; cells pack %d bytes, its index %d; resident directory %d bytes); %d keep their fused model; places without a table (name too long): %s' % (
            report['lines'], report['tables'], report['bytes'], report['typical'], report['largest'][0],
            report['largest'][1], RECORD, report['names_largest'], report.get('pack_bytes', 0),
            report.get('pack_index_bytes', 0), report.get('dir_bytes', 0), len(report['left']),
            ', '.join(report['places_left']) or 'none'), flush=True)
    return report
