#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The focus table (FOCUS-BOX-58): what the framed box shows when you aim at a placed thing in a room.

For every interior cell of the base master (numbered as tools/cell_numbers.py numbers them, the room map's
_aw_cell_int) and every exterior cell (by its grid), each placed item, actor and door: its kind, reference number, position (game units), and for items
the weight, value and whether taking it would be theft (an owner or owning faction on the placement, OpenMW 0.51
mwworld/cellref and mechanicsmanagerimp isAllowedToUse); for doors the destination cell's name, or for a door
leading outside the exterior cell's name, else its region's name. Names are the records'
own display names. The output is private game data: id1/focus.awf, one file with a per-room index.

Format AWF2 (little-endian; AWF1 was the same without the record id, rows of 64 bytes):
  "AWF2" u32 rooms
  rooms x { u32 key, u32 first row, u32 rows }   ascending key: a room's cell number, or for an exterior cell
          0x80000000 | (grid x + 2048) << 12 | (grid y + 2048) (exterior_key)
  rows x 96 bytes { u8 kind ('I' item, 'A' actor, 'D' door), u8 owned, u8 action code (STEAL-PROMPT-58: bits 0-1
                    0 none / 1 take / 2 read / 3 talk, bit 2 owned, bit 3 magic scroll; 0 in older files), u8 0,
                    u32 reference,
                    i32 x, i32 y, i32 z (game units), f32 weight, i32 value, char name[36] (NUL-ended cp1252),
                    char id[32] (an item's record id, folded, NUL-padded; empty for actors and doors) }
The record id is what the engine adds to the inventory when the player takes a placed item (PICKUP-PLACED-58).
A new stage of its own: no other stage's input or cache key changes.
"""
import argparse, hashlib, json, math, struct, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from mwad.esm import records, subrecords, string, first
from mwad.paths import resolve_data_files, child_ci
sys.path.insert(0, str(ROOT / 'tools'))
from ref_identity import stable_ref

MASTER = 'Morrowind.esm'   # the content file the lists read (its references' stable ids: tools/ref_identity.py)
ITEM_DATA = {   # record -> (data subrecord, struct of its weight and value, offset)
    'WEAP': ('WPDT', '<fi', 0), 'ARMO': ('AODT', '<xxxxfi', 0), 'CLOT': ('CTDT', '<xxxxfH', 0),
    'ALCH': ('ALDT', '<fi', 0), 'INGR': ('IRDT', '<fi', 0), 'BOOK': ('BKDT', '<fi', 0), 'MISC': ('MCDT', '<fi', 0),
    'LIGH': ('LHDT', '<fi', 0), 'APPA': ('AADT', '<xxxxxxxxfi', 0), 'LOCK': ('LKDT', '<fi', 0),
    'PROB': ('PBDT', '<fi', 0), 'REPA': ('RIDT', '<fi', 0)}
ACTORS = ('NPC_', 'CREA')
ROW = 96
NAME = 36
IDENT = 32
MAX_ROWS = 1024         # per room: the engine's table (aw_focus.c FOCUS_ROWS)
LIGHT_CARRY = 2         # LHDT flags: can be carried
CELL = 8192             # game units per exterior cell
GRID_BIAS = 2048        # exterior keys: grid offset into 12 bits
# The action code (STEAL-PROMPT-58), byte 2 of a row: what the activate key does and how the prompt reads.
ACT_NONE, ACT_TAKE, ACT_READ, ACT_TALK = 0, 1, 2, 3      # bits 0-1
ACT_OWNED = 4                                            # bit 2: taking it is theft
ACT_MAGIC_SCROLL = 8                                     # bit 3: a BOOK with an enchantment (taken, never read)


def clean(name):
    name = ''.join(c for c in name if ord(c) >= 32).strip()
    raw = name.encode('cp1252', 'replace')[:NAME - 1]
    return raw


def record_id(ident):
    """An item's record id as the row keeps it: printable ASCII, NUL-padded to IDENT bytes; empty when it would not
    fit whole (the engine then leaves the item where it is)."""
    raw = ident.encode('ascii', 'replace') if ident else b''
    if len(raw) > IDENT or any(b < 32 or b > 126 for b in raw):
        raw = b''
    return raw + b'\0' * (IDENT - len(raw))


def objects_of(raw):
    """Folded record id -> (kind, name, weight, value) of every placeable item, actor and door."""
    out = {}
    for tag, flags, payload in records(raw):
        if tag not in ITEM_DATA and tag not in ACTORS and tag != 'DOOR':
            continue
        fields = list(subrecords(payload))
        if flags & 0x20 or any(k == 'DELE' for k, _ in fields):
            continue
        ident = string(first(fields, 'NAME'), 'NAME', errors='replace').casefold()
        name = string(first(fields, 'FNAM'), 'FNAM', errors='replace')
        if tag in ITEM_DATA:
            sub, fmt, _ = ITEM_DATA[tag]
            data = first(fields, sub)
            if len(data) < struct.calcsize(fmt):
                continue
            weight, value = struct.unpack_from(fmt, data)
            if tag == 'LIGH' and (len(data) < 24 or not struct.unpack_from('<i', data, 20)[0] & LIGHT_CARRY):
                continue      # a fixed light is not an item
            if not math.isfinite(weight) or weight < 0 or value < 0 or not name:
                continue
            # STEAL-PROMPT-58: a BOOK without an enchantment is read; one with (a magic scroll) is taken like an item
            action = ACT_TAKE
            if tag == 'BOOK':
                action = ACT_TAKE | ACT_MAGIC_SCROLL if first(fields, 'ENAM') else ACT_READ
            out[ident] = ('I', name, float(weight), int(value), action)
        elif name:
            out[ident] = ('A' if tag in ACTORS else 'D', name, 0.0, 0, ACT_TALK if tag in ACTORS else ACT_NONE)
    return out


def action_code(kind_action, owned):
    """The row's action code (byte 2): the kind in bits 0-1, owned in bit 2, a magic scroll in bit 3. The engine
    indexes its prompt table by it (aw_inventory.c AW_ItemPrompt); nothing is looked up per frame."""
    return (kind_action & (3 | ACT_MAGIC_SCROLL)) | (ACT_OWNED if owned else 0)


def exterior_key(gx, gy):
    """The table key of an exterior cell: the top bit set (room numbers stay below it), then the grid x and y,
    each offset by 2048 into 12 bits. The engine computes the same from a game position (aw_inventory.c)."""
    return 0x80000000 | ((gx + GRID_BIAS) & 0xFFF) << 12 | ((gy + GRID_BIAS) & 0xFFF)


def cells_of(raw):
    """Every live CELL record: (name, interior, grid x, grid y, region id, its references)."""
    for tag, flags, payload in records(raw):
        if tag != 'CELL' or flags & 0x20:
            continue
        cell = None; interior = False; grid = (0, 0); region = ''; current = None; refs = []
        for key, value in subrecords(payload):
            if current is None and key == 'NAME' and cell is None:
                cell = string(value, 'NAME', errors='replace')
            elif current is None and key == 'DATA' and len(value) == 12:
                interior = bool(struct.unpack('<I', value[:4])[0] & 1)
                grid = struct.unpack_from('<ii', value, 4)
            elif current is None and key == 'RGNN':
                region = string(value, 'RGNN', errors='replace').casefold()
            elif key == 'FRMR':
                current = {'number': struct.unpack('<I', value)[0]}; refs.append(current)
            elif current is not None:
                current.setdefault(key, value)
        yield cell or '', interior, grid, region, refs


def place_names(raw):
    """Exterior grid -> the name the original shows for a door leading there: the cell's own name (a town, a
    ruin), else its region's name."""
    regions = {}
    for tag, flags, payload in records(raw):
        if tag == 'REGN' and not flags & 0x20:
            fields = list(subrecords(payload))
            regions[string(first(fields, 'NAME'), 'NAME', errors='replace').casefold()] = \
                string(first(fields, 'FNAM'), 'FNAM', errors='replace')
    out = {}
    for cell, interior, grid, region, _ in cells_of(raw):
        if not interior:
            out[grid] = cell.strip() or regions.get(region, '')
    return out


def placements(raw, objects, numbers):
    """Table key -> rows: interior cells of this master by their room number, exterior cells by exterior_key."""
    rooms = {}
    places = place_names(raw)
    for cell, interior, grid, region, refs in cells_of(raw):
        if interior:
            if not cell or cell.casefold() not in numbers:
                continue
            key = numbers[cell.casefold()]
        elif not all(abs(g) < GRID_BIAS for g in grid) or not refs:
            continue
        else:
            key = exterior_key(*grid)
        rows = rooms.setdefault(key, [])
        for ref in refs:
            if 'DELE' in ref or 'NAME' not in ref or len(ref.get('DATA', b'')) != 24:
                continue
            ident = string(ref['NAME'], 'NAME', errors='replace').casefold()
            record = objects.get(ident)
            if not record:
                continue
            kind, name, weight, value, action = record
            x, y, z = struct.unpack_from('<fff', ref['DATA'])
            owned = int(kind == 'I' and bool(ref.get('ANAM') or ref.get('CNAM')))
            if kind == 'D':
                if 'DNAM' in ref:
                    name = string(ref['DNAM'], 'DNAM', errors='replace')
                elif len(ref.get('DODT', b'')) >= 8:
                    # leads outside: the place there, as the original names it (cell name, else region)
                    dx, dy = struct.unpack_from('<ff', ref['DODT'])
                    if math.isfinite(dx) and math.isfinite(dy):
                        name = places.get((math.floor(dx / CELL), math.floor(dy / CELL))) or name
                else:
                    continue          # a door that only opens: the hinged doors say their own name
            # the stable reference id (tools/ref_identity.py, CELL-CHANGES-59): the list reads Morrowind.esm alone,
            # whose own numbers are their ids
            rows.append((kind, owned, stable_ref(MASTER, ref['number']), x, y, z, weight, value, name,
                         ident if kind == 'I' else '',
                         action_code(action, owned)))
    return rooms


def build(data_files):
    from cell_numbers import load_table
    data = resolve_data_files(Path(data_files))
    raw = child_ci(data, 'Morrowind.esm').read_bytes()
    table, hashes = load_table(data)
    numbers = {row['cell'].casefold(): row['number'] for row in table if row['master'] == 'Morrowind.esm'}
    rooms = placements(raw, objects_of(raw), numbers)
    index, body, held = [], [], {}
    for number in sorted(rooms):
        rows = sorted(rooms[number], key=lambda r: r[2])
        if len(rows) > MAX_ROWS:
            held[number] = len(rows) - MAX_ROWS; rows = rows[:MAX_ROWS]
        index.append(struct.pack('<III', number, len(body), len(rows)))
        for kind, owned, reference, x, y, z, weight, value, name, ident, action in rows:
            name = clean(name)
            body.append(struct.pack('<BBBBIiiifi', ord(kind), owned, action, 0, reference, int(round(x)), int(round(y)),
                                    int(round(z)), weight, value) + name + b'\0' * (NAME - len(name)) +
                        record_id(ident))
    payload = b'AWF2' + struct.pack('<I', len(index)) + b''.join(index) + b''.join(body)
    assert all(len(r) == ROW for r in body)
    report = {'format': 'AWF2', 'rooms': len(index), 'rows': len(body), 'bytes': len(payload),
              'sha256': hashlib.sha256(payload).hexdigest(), 'master_sha256': hashes.get('Morrowind.esm'),
              'held_rows': held}
    return payload, report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-files', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    a = p.parse_args()
    payload, report = build(a.data_files)
    (a.out / 'id1').mkdir(parents=True, exist_ok=True)
    (a.out / 'id1/focus.awf').write_bytes(payload)
    (a.out / 'focus-receipt.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('[focus] %d rooms, %d placed things, %d bytes' % (report['rooms'], report['rows'], report['bytes']), flush=True)


if __name__ == '__main__':
    main()
