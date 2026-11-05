#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Per-area lookup tables (AREA-TABLES-59): what the engine looks up during play about the placed things of one exterior
cell or one interior, in one small binary record per area, loaded with the area and freed with it, so that opening a
container, taking from it, a placed item's take, its owner, the item names and the strip's pictures need no search of
the island-wide files (id1/focus.awf, inventory/items.awi, gfx/icons.awl) during play (engine aw_inventory.c
area_load). Built at image assembly from the staged files themselves (after the palette work), so every byte is the
shipped data's own; focus.awf, items.awi and the icon pack stay for everything else that reads them.

Layout: one pack, id1/areas.awa (one file: thousands of small files would cost an open and a directory search each on
the Amiga file system). Little-endian:
  "AWA1" u32 areas, u32 item directory offset, u32 items, u32 container directory offset, u32 containers,
  areas x { u32 key, u32 offset, u32 bytes }   ascending key (focus.awf's keys: a room number, or an
          exterior cell's 0x80000000 | (gx + 2048) << 12 | (gy + 2048)); the engine keeps this index in memory and
          reads an area with one seek and one read.
  the item directory, items x { u32 id hash (name_hash), u16 area index, u16 0 }   ascending hash: the smallest area
          that holds the item's record (held in memory: a carried item from elsewhere costs one narrow area load)
  the container directory, containers x { u32 reference, u16 area index, u16 0 }   ascending reference (read from
          the file a block at a time, its block heads in memory: a container no loaded area has), then
          u32 the first reference of every block of 256 entries
  an area, "AWB1" u16 rows, u16 owners, u16 owned, u16 containers, u16 contents, u16 items, then:
    rows       x 96 bytes   the area's focus.awf rows, as they are there
    owners     x 32 bytes   the owning NPC and faction ids the area uses (folded, NUL-padded)
    owned      x 8 bytes    { u32 reference, u8 owner index, u8 1 a faction, u16 0 }   ascending reference
    containers x 12 bytes   { u32 reference, u16 first content, u16 contents, u8 flags (focus.awf AWC1's bits 0-2,
                            8 trapped, 16 its record respawns), u8 lock (0..100), u16 0 }   ascending reference
    contents   x 8 bytes    { u16 item index, u16 0, i32 count }
    items      x 512 bytes  the items.awi rows of every item the area's containers hold, its placed items are, and
                            its doors' and containers' keys (ascending, as items.awi)
    pictures   items x { u32 offset in the area, u32 bytes } (0 0: no picture), then the AWI1 pictures of the strip
                            ("item:<id>" in gfx/icons.awl)
"""
import argparse, hashlib, json, struct, sys
from pathlib import Path

ROW, IDENT, OWNER, ITEM_ROW, ICON_ROW = 96, 32, 32, 512, 160
CONT_TRAPPED, CONT_RESPAWN = 8, 16
DIR_BLOCK = 256         # container directory entries per block (the engine keeps each block's first reference)


def u32(raw, at):
    return struct.unpack_from('<I', raw, at)[0]


def read_focus(raw):
    """focus.awf AWF3 -> (rooms {key: [row bytes]}, owners {ref: (id, faction)}, containers {ref: (flags, [(id, n)])},
    refs flags {ref: flags})."""
    if raw[:4] != b'AWF3':
        raise ValueError('focus.awf is not AWF3')
    n = u32(raw, 4)
    index = [struct.unpack_from('<III', raw, 8 + 12 * i) for i in range(n)]
    base = 8 + 12 * n
    rooms = {key: [raw[base + (first + i) * ROW: base + (first + i + 1) * ROW] for i in range(rows)]
             for key, first, rows in index}
    at = base + sum(r for _, _, r in index) * ROW
    if raw[at:at + 4] != b'AWO1':
        raise ValueError('focus.awf has no owners list')
    count = u32(raw, at + 4)
    entries = [struct.unpack_from('<IHBB', raw, at + 8 + 8 * i) for i in range(count)]
    pool_at = at + 8 + 8 * count
    pool = raw[pool_at + 4: pool_at + 4 + u32(raw, pool_at)]
    owners = {ref: (pool[off:pool.index(b'\0', off)].decode('ascii'), flags & 1) for ref, off, flags, _ in entries}
    at = pool_at + 4 + len(pool)
    if raw[at:at + 4] != b'AWC1':
        raise ValueError('focus.awf has no contents list')
    count = u32(raw, at + 4)
    heads = [struct.unpack_from('<IIHBB', raw, at + 8 + 12 * i) for i in range(count)]
    items_at = at + 8 + 12 * count
    total = u32(raw, items_at)
    body = items_at + 4
    containers = {}
    for ref, first, k, flags, _ in heads:
        rows = []
        for i in range(first, first + k):
            rec = raw[body + 36 * i: body + 36 * i + 36]
            rows.append((rec[:IDENT].split(b'\0', 1)[0].decode('ascii'), struct.unpack_from('<i', rec, IDENT)[0]))
        containers[ref] = (flags, rows)
    at = body + 36 * total
    refs = {}
    if raw[at:at + 4] == b'AWI1':
        p = at + 4
        files = raw[p]; p += 1
        for _ in range(files):
            p += 2 + raw[p + 1] + 12
        p += 12
        rows, _step, blocks = struct.unpack_from('<III', raw, p); p += 12 + 4 * blocks
        for i in range(rows):
            word, _ = struct.unpack_from('<II', raw, p + 8 * i)
            if word >> 24:
                refs[word & 0xFFFFFF] = word >> 24
        at = p + 8 * rows
    return rooms, owners, containers, refs, read_levelled(raw, at)


def read_levelled(raw, at):
    """focus.awf's AWL1 section (prepare_focus.levelled_section; CONTAINER-LEVELLED-CONTENTS-60) at AT ->
    {list id: (flags, chance none, [(entry id, level)])}; {} when the file has none."""
    out = {}
    if raw[at:at + 4] != b'AWL1':
        return out
    n = u32(raw, at + 4); p = at + 8
    for _ in range(n):
        ident = raw[p:p + IDENT].split(b'\0', 1)[0].decode('ascii')
        flags, chance, k = struct.unpack_from('<BBH', raw, p + IDENT); p += IDENT + 4
        entries = []
        for _ in range(k):
            entries.append((raw[p:p + IDENT].split(b'\0', 1)[0].decode('ascii'),
                            struct.unpack_from('<H', raw, p + IDENT)[0])); p += IDENT + 2
        out[ident] = (flags, chance, entries)
    return out


LEV_EACH, LEV_ALL_LEVELS = 1, 2          # LEVI DATA flags (OpenMW 0.51 esm3 ItemLevList Each, AllLevels)
LEV_NESTED, LEV_NOTHING = 0x8000, 0xFFFF
CONT_ACTOR = 32                          # an actor's inventory (focus.awf AWC1 bit 3, CORPSE-LOOT-60)
CONTENT_LEVELLED = 1                     # a content row's flags (its u16 after the index): the index is a list's


def list_closure(levelled, roots):
    """The levelled lists ROOTS reach (themselves and every list inside them), sorted."""
    seen, todo = set(), [r for r in roots if r in levelled]
    while todo:
        lid = todo.pop()
        if lid in seen:
            continue
        seen.add(lid)
        todo.extend(e for e, _ in levelled[lid][2] if e in levelled and e not in seen)
    return sorted(seen)


LEV_POOL = 0x4000          # an entry's target: LEV_POOL | the index of an id in the area's id pool


def levelled_block(lists, levelled, index, items):
    """An area's levelled lists in the CHIM actor table's list layout (big-endian, engine ChimActors_LevelledPick, so
    the engine rolls an item list with the same code and rule as a creature list): u32 lists, lists x { u32 first
    entry, u16 entries, u8 chance none, u8 flags (bit 0 all levels, bit 1 each) }, entries x { u16 level, u16 target:
    the area's item index, LEV_POOL | an id of the pool below, LEV_NESTED | a list index, or LEV_NOTHING for an id the
    game has no item of }; then the id pool: "AWN1" u16 ids, ids x { u8 length, the folded id }. An item a list can
    give is named by its id only (BUDGET: its record and picture are not copied into every area whose containers name
    the list; the strip reads them through the item directory, NARROW-LOAD, when a roll gives it). Returns the bytes
    and the pool's ids."""
    at = {lid: i for i, lid in enumerate(lists)}
    heads, entries, pool, pool_at = [], [], [], {}
    for lid in lists:
        flags, chance, rows = levelled[lid]
        heads.append(struct.pack('>IHBB', len(entries), len(rows), chance,
                                 (1 if flags & LEV_ALL_LEVELS else 0) | (2 if flags & LEV_EACH else 0)))
        for ident, level in rows:
            if ident in at:
                target = LEV_NESTED | at[ident]
            elif ident in index:
                target = index[ident]
            elif ident in items:
                if ident not in pool_at:
                    pool_at[ident] = len(pool); pool.append(ident)
                target = LEV_POOL | pool_at[ident]
            else:
                target = LEV_NOTHING
            entries.append(struct.pack('>HH', min(level, 0xFFFF), target))
    if len(pool) >= LEV_POOL:
        raise ValueError('an area names over %d levelled item ids' % LEV_POOL)
    names = b''.join(bytes([len(i.encode('ascii'))]) + i.encode('ascii') for i in pool)
    return (struct.pack('>I', len(lists)) + b''.join(heads) + b''.join(entries) + b'AWN1' +
            struct.pack('<H', len(pool)) + names), pool


def read_items(raw):
    """items.awi AWI2 -> {folded id: row bytes} in file order."""
    if raw[:4] != b'AWI2':
        raise ValueError('items.awi is not AWI2')
    n = u32(raw, 4)
    out = {}
    for i in range(n):
        row = raw[8 + i * ITEM_ROW: 8 + (i + 1) * ITEM_ROW]
        out[row[:64].split(b'\0', 1)[0].decode('cp1252').lower()] = row
    return out


def read_icons(table, pack):
    """gfx/icons.awl AWL2 + icons.awp -> {lowered key: AWI1 picture bytes}."""
    if table[:4] != b'AWL2':
        return {}
    out = {}
    for i in range(u32(table, 4)):
        row = table[8 + i * ICON_ROW: 8 + (i + 1) * ICON_ROW]
        key = row[:64].split(b'\0', 1)[0].decode('cp1252').lower()
        if key.startswith('item:'):
            off, size = u32(row, 120), u32(row, 124)
            out[key] = pack[off:off + size]
    return out


STRINGS = ((0, 64), (64, 96), (184, 64), (248, 64), (312, 64), (376, 64))   # id, name, model, icon, enchantment, script
NUMBERS = ((160, 184), (440, 512))                                         # the row's fixed numeric parts (96 bytes)


def compact_item(row):
    """An items.awi row without its padding: the 96 numeric bytes, then the six strings as u8 length + bytes (the engine
    expands it back into the 512-byte row and reads it with items.awi's own row reader, area_item_row)."""
    out = b''.join(row[a:b] for a, b in NUMBERS)
    for at, size in STRINGS:
        s = row[at:at + size].split(b'\0', 1)[0]
        out += bytes([len(s)]) + s
    return out


def expand_item(packed):
    """compact_item's inverse (the native test checks it against the engine's)."""
    row = bytearray(ITEM_ROW)
    p = 0
    for a, b in NUMBERS:
        row[a:b] = packed[p:p + b - a]; p += b - a
    for at, size in STRINGS:
        n = packed[p]; row[at:at + n] = packed[p + 1:p + 1 + n]; p += 1 + n
    return bytes(row)


def area(rows, owners, containers, refs, extras, items, icons, levelled=None, extra_items=()):
    """One area's AWB1 record and its counts (EXTRA_ITEMS: item records it holds besides its own, item_chunks)."""
    levelled = levelled or {}
    refs_here = [u32(r, 4) for r in rows]
    used = {k for k in extra_items if k in items}
    for r in rows:
        if r[0] == ord('I'):
            ident = r[64:96].split(b'\0', 1)[0].decode('ascii').lower()
            if ident in items:
                used.add(ident)
    conts = sorted(ref for ref in refs_here if ref in containers)
    for ref in conts:
        used.update(i.lower() for i, _ in containers[ref][1] if i.lower() in items)
    # CONTAINER-LEVELLED-CONTENTS-60: the lists the area's containers and actors name and every list inside them; the
    # items they can give are named by id (levelled_block), their records stay where the item directory finds them
    lists = list_closure(levelled, {i.lower() for ref in conts for i, _ in containers[ref][1]})
    list_at = {lid: i for i, lid in enumerate(lists)}
    for ref in refs_here:
        key = extras.get(str(ref), (0, ''))[1]
        if key and key in items:
            used.add(key)
    order = [k for k in items if k in used]         # items.awi order (ascending)
    index = {k: i for i, k in enumerate(order)}
    owner_ids, owned = [], []
    for ref in sorted(set(refs_here)):
        if ref in owners:
            ident, faction = owners[ref]
            if ident not in owner_ids:
                owner_ids.append(ident)
            owned.append(struct.pack('<IBBH', ref, owner_ids.index(ident), faction, 0))
    cont_rows, content_rows = [], []
    lock_of = {u32(r, 4): r[3] for r in rows if r[0] == ord('C')}
    for ref in conts:
        flags, entries = containers[ref]
        flags = (flags & 7) | (CONT_ACTOR if flags & 8 else 0)
        if extras.get(str(ref), (0, ''))[0]:
            flags |= CONT_TRAPPED
        if refs.get(ref, 0) & 1:
            flags |= CONT_RESPAWN
        kept = [(index[i.lower()], 0, n) if i.lower() in index else (list_at[i.lower()], CONTENT_LEVELLED, n)
                for i, n in entries if i.lower() in index or i.lower() in list_at]
        cont_rows.append(struct.pack('<IHHBBH', ref, len(content_rows), len(kept), flags, min(lock_of.get(ref, 0), 100), 0))
        content_rows.extend(struct.pack('<HHi', k, f, n) for k, f, n in kept)
    head = b'AWB1' + struct.pack('<HHHHHH', len(rows), len(owner_ids), len(owned), len(cont_rows), len(content_rows),
                                 len(order))
    body = (head + b''.join(rows) + b''.join(i.encode('ascii').ljust(OWNER, b'\0') for i in owner_ids) +
            b''.join(owned) + b''.join(cont_rows) + b''.join(content_rows))
    packed = [compact_item(items[k]) for k in order]
    at = len(body) + 4 * len(order)
    offsets = []
    for p in packed:
        offsets.append(struct.pack('<I', at)); at += len(p)
    body += b''.join(offsets) + b''.join(packed)
    pictures, table, at = [], [], len(body) + 8 * len(order)
    for k in order:
        pic = icons.get('item:' + k, b'')
        table.append(struct.pack('<II', at if pic else 0, len(pic)))
        pictures.append(pic); at += len(pic)
    record = body + b''.join(table) + b''.join(pictures)
    lev_bytes, pool = 0, []
    if lists:
        # the levelled section after the pictures, found from the record's last 8 bytes: u32 its offset, "AWL1"
        block, pool = levelled_block(lists, levelled, index, items)
        block = b'AWL1' + block
        lev_bytes = len(block) + 8
        record += block + struct.pack('<I', len(record)) + b'AWL1'     # the offset is the record's length before it
    return record, {'rows': len(rows), 'containers': len(cont_rows), 'items': len(order),
                    'pictures': sum(1 for p in pictures if p), 'bytes': len(record), 'item_ids': order,
                    'container_refs': conts, 'levelled_lists': len(lists), 'levelled_bytes': lev_bytes,
                    'levelled_ids': pool,
                    'actor_inventories': sum(1 for ref in conts if containers[ref][0] & 8)}


CHUNK_KEY = 0x7FFF0000     # the item chunks' keys (no room number reaches them; exterior keys have the top bit)
CHUNK_ITEMS = 16           # item records per chunk (with their pictures: about 20 KiB at most)


def item_chunks(ids, items, icons):
    """CONTAINER-LEVELLED-CONTENTS-60: item records no area holds that a levelled list can give, as small area
    records of their own (no rows, no containers: items and pictures only, CHUNK_ITEMS each), so the item directory
    answers them with one narrow load, never the island-wide items.awi: [(key, record, stats)]."""
    out = []
    ids = [k for k in items if k in ids]              # items.awi order (ascending)
    for n in range(0, len(ids), CHUNK_ITEMS):
        part = ids[n:n + CHUNK_ITEMS]
        record, s = area([], {}, {}, {}, {}, items, icons, extra_items=part)
        out.append((CHUNK_KEY + n // CHUNK_ITEMS, record, s))
    return out


def pack_index(entries, at):
    """THE SHARED PER-AREA LAYOUT (the project's rule of small binary tables per area; areas.awa, npc-ambient.awa and
    npc-parts.awa all use it): the index of a pack, ENTRIES [(area key, record bytes)] in ascending key, each
    { u32 key, u32 offset from the file's start, u32 bytes } little-endian, the records stored from AT on in the same
    order. The key is focus.awf's: a room's number, or an exterior cell's 0x80000000 | (gx + 2048) << 12 | (gy + 2048)
    (prepare_focus.exterior_key), so one place key names an area in every pack. Returns (index bytes, the offset
    after the last record)."""
    out = []
    last = None
    for key, record in entries:
        if last is not None and key <= last:
            raise ValueError('area pack keys not ascending: %d after %d' % (key, last))
        last = key
        out.append(struct.pack('<III', key, at, len(record))); at += len(record)
    return b''.join(out), at


def name_hash(ident):
    """FNV-1a over the id with A-Z folded; 0 becomes 1 (prepare_focus.name_hash, engine AW_LedgerNameHash)."""
    h = 2166136261
    for c in ident.encode('cp1252', 'replace'):
        if 65 <= c <= 90:
            c += 32
        h = ((h ^ c) * 16777619) & 0xFFFFFFFF
    return h or 1


def build(id1, extras_path=None):
    id1 = Path(id1)
    rooms, owners, containers, refs, levelled = read_focus((id1 / 'focus.awf').read_bytes())
    items = read_items((id1 / 'inventory' / 'items.awi').read_bytes())
    icons = {}
    if (id1 / 'gfx' / 'icons.awl').is_file() and (id1 / 'gfx' / 'icons.awp').is_file():
        icons = read_icons((id1 / 'gfx' / 'icons.awl').read_bytes(), (id1 / 'gfx' / 'icons.awp').read_bytes())
    extras = json.loads(Path(extras_path).read_text(encoding='utf-8')) if extras_path and Path(extras_path).is_file() else {}
    keys = sorted(rooms)
    records, stats = [], []
    for done, key in enumerate(keys, 1):
        record, s = area(rooms[key], owners, containers, refs, extras, items, icons, levelled)
        records.append(record); s['key'] = key; stats.append(s)
        if done % 500 == 0 or done == len(keys):
            print('[areas] %d / %d areas' % (done, len(keys)), flush=True)
    # CONTAINER-LEVELLED-CONTENTS-60: the items a list can give that no area holds, in chunks the directory names
    held = {k for s in stats for k in s['item_ids']}
    wanted = {k for s in stats for k in s['levelled_ids']} - held
    chunks = item_chunks(wanted, items, icons)
    for key, record, s in chunks:
        s['key'] = key; keys.append(key); records.append(record); stats.append(s)
    order = sorted(range(len(keys)), key=lambda i: keys[i])
    keys = [keys[i] for i in order]; records = [records[i] for i in order]; stats = [stats[i] for i in order]
    # the directory (NARROW-LOAD, ALSO FOR GLOBAL LOOKUPS): an item by its name hash -> the smallest area that holds
    # its record (one narrow load answers a carried item from elsewhere); a container by its reference -> its area
    item_area, cont_area = {}, {}
    for n, (key, record, s) in enumerate(zip(keys, records, stats)):
        for k in s.pop('item_ids'):
            if k not in item_area or len(records[item_area[k]]) > len(record):
                item_area[k] = n
        for ref in s.pop('container_refs'):
            cont_area.setdefault(ref, n)
    item_dir = sorted((name_hash(k), n) for k, n in item_area.items())
    cont_dir = sorted(cont_area.items())
    head = 24
    at = head + 12 * len(keys)
    item_at = at; at += 8 * len(item_dir)
    cont_at = at; at += 8 * len(cont_dir)
    heads = [cont_dir[i][0] for i in range(0, len(cont_dir), DIR_BLOCK)]
    at += 4 * len(heads)
    index, at = pack_index(zip(keys, records), at)
    payload = (b'AWA1' + struct.pack('<IIIII', len(keys), item_at, len(item_dir), cont_at, len(cont_dir)) +
               index + b''.join(struct.pack('<IHH', h, n, 0) for h, n in item_dir) +
               b''.join(struct.pack('<IHH', r, n, 0) for r, n in cont_dir) +
               b''.join(struct.pack('<I', h) for h in heads) + b''.join(records))
    sizes = sorted(s['bytes'] for s in stats)
    largest = max(stats, key=lambda s: s['bytes']) if stats else {}
    vocabulary = len({k for k in items})
    report = {'format': 'AWA1', 'areas': len(keys), 'bytes': len(payload), 'index_bytes': head + 12 * len(keys),
              'item_directory': len(item_dir), 'item_directory_bytes': 8 * len(item_dir),
              'container_directory': len(cont_dir), 'container_directory_bytes': 8 * len(cont_dir),
              'sha256': hashlib.sha256(payload).hexdigest(),
              'area_bytes_median': sizes[len(sizes) // 2] if sizes else 0,
              'area_bytes_p90': sizes[int(len(sizes) * .9)] if sizes else 0,
              'area_bytes_largest': largest.get('bytes', 0), 'largest_key': largest.get('key'),
              'item_vocabulary': vocabulary, 'item_pictures': len(icons),
              'item_picture_bytes': sum(len(p) for p in icons.values()),
              'levelled_item_lists': len(levelled),
              'areas_with_levelled': sum(1 for s in stats if s['levelled_lists']),
              'levelled_bytes': sum(s['levelled_bytes'] for s in stats),
              'levelled_bytes_largest': max((s['levelled_bytes'] for s in stats), default=0),
              'item_chunks': len(chunks), 'item_chunk_items': len(wanted),
              'item_chunk_bytes': sum(len(r) for _, r, _ in chunks),
              'actor_inventories': sum(s['actor_inventories'] for s in stats)}
    return payload, report


def install(id1, extras_path=None):
    """Write id1/areas.awa from the staged files; the staging report."""
    payload, report = build(id1, extras_path)
    (Path(id1) / 'areas.awa').write_bytes(payload)
    report['file'] = 'id1/areas.awa'
    print('[areas] %d areas, %d bytes (median area %d, largest %d), index %d bytes' % (
        report['areas'], report['bytes'], report['area_bytes_median'], report['area_bytes_largest'],
        report['index_bytes']), flush=True)
    return report


def stage(id1, focus_stage, out):
    """build_aga.py's step, after the focus table is installed and the palette work is done: id1/areas.awa from the
    staged files (when the image has an item catalogue), its report in OUT/areas-staging.json."""
    id1 = Path(id1)
    if not (id1 / 'inventory' / 'items.awi').is_file() or not (id1 / 'focus.awf').is_file():
        return None
    print('=== areas: per-area lookup tables ===', flush=True)
    report = install(id1, Path(focus_stage) / 'focus-extras.json')
    (Path(out) / 'areas-staging.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    return report


# ---------------------------------------------------------------- AMBIENT-WALK-PER-AREA-60: the Wander packages per area
#
# id1/npc-ambient.awa, little-endian like areas.awa:
#   "AWM1" u32 areas, u32 shared offset, u32 shared bytes,
#   areas x { u32 key, u32 offset, u32 bytes }   ascending key (focus.awf's keys; only areas with a package)
#   shared: one AWAM1 table (tools/ambient_lut.py layout, big-endian inside) of the levelled creatures' package rows
#           (reference 0), kept in memory by the engine (the picked creature can come from any list)
#   per area: one AWAM1 table of the rows whose reference is placed in that area (its cell, from ambient_lut's
#           report; a room by its number from tools/cell_numbers.py, as focus.awf's keys), with their
#           points, hops and idle profiles renumbered; the engine reads it with one seek and one read when the area
#           loads and searches it in memory (aw_ambient.c, cvar aw_ambient_areas).
AWAM_HEADER, AWAM_ROW, AWAM_POINT, AWAM_PROFILE = 32, 28, 8, 16


def read_awam(raw):
    """npc-ambient.lut AWAM1 -> (multiplier, [(row fields, points bytes, hops bytes)], [profile bytes])."""
    if raw[:4] != b'AWAM' or struct.unpack_from('>HH', raw, 4) != (1, AWAM_ROW):
        raise ValueError('npc-ambient.lut is not AWAM1')
    rows, points, hops, profiles = struct.unpack_from('>IIII', raw, 8)
    multiplier = struct.unpack_from('>H', raw, 24)[0]
    points_at = AWAM_HEADER + rows * AWAM_ROW
    hops_at = points_at + points * AWAM_POINT
    prof_at = hops_at + hops
    if prof_at + profiles * AWAM_PROFILE != len(raw):
        raise ValueError('npc-ambient.lut size mismatch')
    out = []
    for i in range(rows):
        f = list(struct.unpack_from('>IIHHBBBBIIHH', raw, AWAM_HEADER + i * AWAM_ROW))
        n, d = f[6], f[7]
        pts = raw[points_at + f[8] * AWAM_POINT: points_at + (f[8] + n) * AWAM_POINT]
        hop = raw[hops_at + f[9]: hops_at + f[9] + n * d]
        out.append((f, pts, hop))
    profs = [raw[prof_at + i * AWAM_PROFILE: prof_at + (i + 1) * AWAM_PROFILE] for i in range(profiles)]
    return multiplier, out, profs


def write_awam(multiplier, rows, profiles):
    """An AWAM1 table of ROWS (as read_awam gives them, in their sorted order) with its own points, hops and the
    idle profiles they use, renumbered."""
    used = sorted({f[10] for f, _, _ in rows})
    remap = {p: i for i, p in enumerate(used)}
    row_bytes, pts_bytes, hop_bytes = [], [], []
    npts = nhop = 0
    for f, pts, hop in rows:
        g = list(f)
        g[8], g[9], g[10], g[11] = npts, nhop, remap[f[10]], 0
        row_bytes.append(struct.pack('>IIHHBBBBIIHH', *g))
        pts_bytes.append(pts); npts += len(pts) // AWAM_POINT
        padded = hop + b'\0' * (-len(hop) % 4)
        hop_bytes.append(padded); nhop += len(padded)
    head = b'AWAM' + struct.pack('>HHIIIIHHI', 1, AWAM_ROW, len(rows), npts, nhop, len(used), multiplier, 0, 0)
    return head + b''.join(row_bytes) + b''.join(pts_bytes) + b''.join(hop_bytes) + b''.join(profiles[p] for p in used)


def area_keys(places, numbers):
    """{reference: area key} from ambient_lut's placements' cells (PLACES: {str ref: ['i', name] | ['e', x, y]}) and
    the room numbers (NUMBERS: {folded interior name: number}); a room without a number has no area (the engine's
    island-wide fallback answers there, counted)."""
    from prepare_focus import exterior_key
    out = {}
    for ref, place in places.items():
        if place[0] == 'e':
            out[int(ref)] = exterior_key(place[1], place[2])
        elif place[1] in numbers:
            out[int(ref)] = numbers[place[1]]
    return out


def build_ambient(keys_of, lut):
    """npc-ambient.awa from each placement's area key (KEYS_OF: {reference: key}) and npc-ambient.lut's bytes; the
    report."""
    multiplier, rows, profiles = read_awam(lut)
    shared = write_awam(multiplier, [r for r in rows if r[0][0] == 0], profiles)
    by_ref = {}
    for r in rows:
        if r[0][0]:
            by_ref.setdefault(r[0][0], []).append(r)
    by_key = {}
    for ref in sorted(by_ref):
        if ref in keys_of:
            by_key.setdefault(keys_of[ref], []).append(ref)
    tables, placed = [], set()
    for key in sorted(by_key):
        refs = by_key[key]
        mine = [r for ref in refs for r in by_ref[ref]]       # ascending ref, by_ref keeps the file's hash order
        tables.append((key, write_awam(multiplier, mine, profiles), len(mine)))
        placed.update(refs)
    at = 16 + 12 * len(tables)
    shared_at = at; at += len(shared)
    index, at = pack_index(((key, t) for key, t, _ in tables), at)
    payload = (b'AWM1' + struct.pack('<III', len(tables), shared_at, len(shared)) + index + shared +
               b''.join(t for _, t, _ in tables))
    sizes = sorted(len(t) for _, t, _ in tables)
    largest = max(tables, key=lambda t: len(t[1])) if tables else (None, b'', 0)
    report = {'format': 'AWM1', 'areas': len(tables), 'bytes': len(payload), 'index_bytes': 16 + 12 * len(tables),
              'shared_rows': sum(1 for r in rows if r[0][0] == 0), 'shared_bytes': len(shared),
              'rows': len(rows), 'rows_placed': sum(len(by_ref[r]) for r in placed),
              'refs_not_in_any_area': len(set(by_ref) - placed),
              'area_bytes_median': sizes[len(sizes) // 2] if sizes else 0,
              'area_bytes_p90': sizes[int(len(sizes) * .9)] if sizes else 0,
              'area_bytes_largest': len(largest[1]), 'largest_key': largest[0],
              'sha256': hashlib.sha256(payload).hexdigest()}
    return payload, report


def stage_ambient(id1, out, data_files, places):
    """build_aga.py's step after the ambient table: id1/npc-ambient.awa from id1/npc-ambient.lut and the placements'
    cells (PLACES, the ambient table step's report), the room numbers from DATA_FILES (tools/cell_numbers.py, as
    focus.awf's keys); its report in OUT/ambient-areas-staging.json."""
    id1 = Path(id1)
    if not (id1 / 'npc-ambient.lut').is_file() or not places:
        return None
    print('=== areas: the Wander packages per area ===', flush=True)
    import prepare_focus  # noqa: F401  (puts src/ on the path for mwad)
    from cell_numbers import load_table
    from mwad.paths import resolve_data_files
    table, _ = load_table(resolve_data_files(Path(data_files)))
    numbers = {row['cell'].casefold(): row['number'] for row in table if row['master'] == 'Morrowind.esm'}
    payload, report = build_ambient(area_keys(places, numbers), (id1 / 'npc-ambient.lut').read_bytes())
    (id1 / 'npc-ambient.awa').write_bytes(payload)
    report['file'] = 'id1/npc-ambient.awa'
    print('[areas] ambient: %d areas, %d bytes (median area %d, largest %d), shared %d bytes, %d actors in no area' % (
        report['areas'], report['bytes'], report['area_bytes_median'], report['area_bytes_largest'],
        report['shared_bytes'], report['refs_not_in_any_area']), flush=True)
    (Path(out) / 'ambient-areas-staging.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8',
                                                          newline='\n')
    # NPC-RECIPES-PER-AREA-59: the residents' recipe tables on the same layout (here: this step has the data files the
    # room numbers come from, and build_aga.py sits at its release size limit, BUILD-AGA-AT-TEXT-LIMIT-60)
    stage_recipes(id1, out, data_files)
    return report


# ---------------------------------------------------------------- NPC-RECIPES-PER-AREA-59: the residents' recipes per area
#
# id1/npc-parts.awa: the residents' recipe tables (tools/npc_recipes.py AWNB, unchanged inside) on the shared per-area
# layout, written at image assembly from the stages' own files (view/npc_parts/cells.awnp, view/npc_parts/<map>.awnb),
# which stay in the image as the previous method (engine cvar aw_npc_tables_areas 0). Little-endian like areas.awa:
#   "AWR1" u32 areas, u32 directory offset, u32 directory entries,
#   areas x { u32 key, u32 offset, u32 bytes }   pack_index: ascending key (focus.awf's keys: an exterior cell by its
#           grid, a room by the number its map carries in "_aw_cell_int", the very key the engine's place has)
#   the resident directory, entries x { u32 id hash (npc_recipes.id_hash, as the AWNB records), u16 area index, u16 0 }
#           ascending hash (NARROW-LOAD: a resident outside the loaded areas costs one seek and one read; the first
#           area by key keeps a resident placed in two)
#   the AWNB tables, one per area
# The engine (aw_npc_parts.c) holds the index and the directory, and reads an area's table with one seek and one read
# when the place changes (AW_AreaPlaceKeys: the room, or the 3 x 3 exterior cells) or a cell's residents arrive.
def room_number(id1, name, planned=None):
    """The room number of map NAME: the "_aw_cell_int" its world entity carries (the key engine aw_inventory.c
    focus_room reads), else PLANNED[NAME], the number tools/cell_numbers.py stamps there later in the image step
    (planned_numbers); None when neither names one."""
    from map_files import head_bytes, map_file, worldspawn
    value = worldspawn(head_bytes(map_file(Path(id1) / 'maps', name))).get('_aw_cell_int', '')
    if value.isdigit():
        return int(value)
    return (planned or {}).get(name)


def planned_numbers(names, data_files):
    """{map name: room number} as tools/cell_numbers.py stamp_staged_cells will stamp the maps NAMES (the same map
    cells and the same numbering of the masters in DATA_FILES)."""
    import prepare_focus  # noqa: F401  (puts src/ on the path for mwad, as stage_ambient)
    from cell_numbers import interior_map_cells, load_table
    from mwad.paths import resolve_data_files
    table, _ = load_table(resolve_data_files(Path(data_files)))
    numbers = {row['cell'].casefold(): row['number'] for row in table}
    return {name: numbers[cell.casefold()] for name, cell in interior_map_cells(names).items()
            if cell.casefold() in numbers}


def table_hashes(table):
    """The id hashes of an AWNB table's residents (npc_recipes.table_bytes: u16 residents at 6, records from 12)."""
    if table[:4] != b'AWNB':
        raise ValueError('not an AWNB table')
    count, size = struct.unpack_from('>H', table, 6)[0], table[5]
    return [struct.unpack_from('>I', table, 12 + i * size)[0] for i in range(count)]


def build_recipes(tables):
    """npc-parts.awa from TABLES {area key: AWNB bytes}; the report."""
    keys = sorted(tables)
    directory = {}
    for n, key in enumerate(keys):
        for h in table_hashes(tables[key]):
            directory.setdefault(h, n)
    entries = sorted(directory.items())
    at = 16 + 12 * len(keys)
    dir_at = at
    at += 8 * len(entries)
    index, _ = pack_index(((k, tables[k]) for k in keys), at)
    payload = (b'AWR1' + struct.pack('<III', len(keys), dir_at, len(entries)) + index +
               b''.join(struct.pack('<IHH', h, n, 0) for h, n in entries) + b''.join(tables[k] for k in keys))
    sizes = sorted(len(t) for t in tables.values())
    report = {'format': 'AWR1', 'areas': len(keys), 'bytes': len(payload), 'index_bytes': 16 + 12 * len(keys),
              'residents': len(entries), 'directory_bytes': 8 * len(entries),
              'area_bytes_median': sizes[len(sizes) // 2] if sizes else 0,
              'area_bytes_largest': sizes[-1] if sizes else 0,
              'sha256': hashlib.sha256(payload).hexdigest()}
    return payload, report


def stage_recipes(id1, out, data_files=None):
    """The image step's write of id1/npc-parts.awa from the stages' recipe tables (none: no file), run from the
    Wander tables' step (stage_ambient, which has the data files for the room numbers: the image step stamps them
    into the maps only later); a room with no number keeps only its old file (listed). Its report in
    OUT/npc-parts-staging.json."""
    from prepare_focus import exterior_key
    import npc_recipes
    id1 = Path(id1)
    folder = id1 / npc_recipes.TABLE_DIR
    if not folder.is_dir():
        return None
    print('=== areas: the residents\' recipes per area ===', flush=True)
    tables, left = {}, []
    pack = folder / 'cells.awnp'
    if pack.is_file():
        for (x, y), data in sorted(npc_recipes.pack_tables(pack.read_bytes()).items()):
            tables[exterior_key(x, y)] = data
    rooms = sorted(folder.glob('*.awnb'))
    planned = planned_numbers([p.stem for p in rooms], data_files) if rooms and data_files else {}
    for path in rooms:
        number = room_number(id1, path.stem, planned)
        if number is None or number in tables:
            left.append(path.stem)
            continue
        tables[number] = path.read_bytes()
    if not tables:
        return None
    payload, report = build_recipes(tables)
    (id1 / 'npc-parts.awa').write_bytes(payload)
    report.update(file='id1/npc-parts.awa', places_left=left)
    print('[areas] recipes: %d areas, %d residents, %d bytes (index %d, directory %d); rooms without a number: %s' % (
        report['areas'], report['residents'], report['bytes'], report['index_bytes'], report['directory_bytes'],
        ', '.join(left) or 'none'), flush=True)
    (Path(out) / 'npc-parts-staging.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8',
                                                      newline='\n')
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--id1', required=True, type=Path)
    p.add_argument('--extras', type=Path)
    a = p.parse_args()
    print(json.dumps(install(a.id1, a.extras), indent=2))


if __name__ == '__main__':
    main()
