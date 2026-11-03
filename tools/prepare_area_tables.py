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
    return rooms, owners, containers, refs


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


def area(rows, owners, containers, refs, extras, items, icons):
    """One area's AWB1 record and its counts."""
    refs_here = [u32(r, 4) for r in rows]
    used = set()
    for r in rows:
        if r[0] == ord('I'):
            ident = r[64:96].split(b'\0', 1)[0].decode('ascii').lower()
            if ident in items:
                used.add(ident)
    conts = sorted(ref for ref in refs_here if ref in containers)
    for ref in conts:
        used.update(i.lower() for i, _ in containers[ref][1] if i.lower() in items)
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
        flags &= 7
        if extras.get(str(ref), (0, ''))[0]:
            flags |= CONT_TRAPPED
        if refs.get(ref, 0) & 1:
            flags |= CONT_RESPAWN
        kept = [(index[i.lower()], n) for i, n in entries if i.lower() in index]
        cont_rows.append(struct.pack('<IHHBBH', ref, len(content_rows), len(kept), flags, min(lock_of.get(ref, 0), 100), 0))
        content_rows.extend(struct.pack('<HHi', k, 0, n) for k, n in kept)
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
    return record, {'rows': len(rows), 'containers': len(cont_rows), 'items': len(order),
                    'pictures': sum(1 for p in pictures if p), 'bytes': len(record), 'item_ids': order,
                    'container_refs': conts}


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
    rooms, owners, containers, refs = read_focus((id1 / 'focus.awf').read_bytes())
    items = read_items((id1 / 'inventory' / 'items.awi').read_bytes())
    icons = {}
    if (id1 / 'gfx' / 'icons.awl').is_file() and (id1 / 'gfx' / 'icons.awp').is_file():
        icons = read_icons((id1 / 'gfx' / 'icons.awl').read_bytes(), (id1 / 'gfx' / 'icons.awp').read_bytes())
    extras = json.loads(Path(extras_path).read_text(encoding='utf-8')) if extras_path and Path(extras_path).is_file() else {}
    keys = sorted(rooms)
    records, stats = [], []
    for done, key in enumerate(keys, 1):
        record, s = area(rooms[key], owners, containers, refs, extras, items, icons)
        records.append(record); s['key'] = key; stats.append(s)
        if done % 500 == 0 or done == len(keys):
            print('[areas] %d / %d areas' % (done, len(keys)), flush=True)
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
    index = []
    for key, record in zip(keys, records):
        index.append(struct.pack('<III', key, at, len(record))); at += len(record)
    payload = (b'AWA1' + struct.pack('<IIIII', len(keys), item_at, len(item_dir), cont_at, len(cont_dir)) +
               b''.join(index) + b''.join(struct.pack('<IHH', h, n, 0) for h, n in item_dir) +
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
              'item_picture_bytes': sum(len(p) for p in icons.values())}
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


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--id1', required=True, type=Path)
    p.add_argument('--extras', type=Path)
    a = p.parse_args()
    print(json.dumps(install(a.id1, a.extras), indent=2))


if __name__ == '__main__':
    main()
