#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The focus table (FOCUS-BOX-58): what the framed box shows when you aim at a placed thing in a room.

For every interior cell of the base master (numbered as tools/cell_numbers.py numbers them, the room map's
_aw_cell_int) and every exterior cell (by its grid), each placed item, actor and door: its kind, reference number, position (game units), and for items
the weight, value and whether taking it would be theft (an owner or owning faction on the placement, OpenMW 0.51
mwworld/cellref and mechanicsmanagerimp isAllowedToUse); for doors the destination cell's name, or for a door
leading outside the exterior cell's name, else its region's name. Names are the records'
own display names. The output is private game data: id1/focus.awf, one file with a per-room index.

Format AWF3 (little-endian; AWF1 was the rows without the record id, 64 bytes each; AWF2 the rows below without the
owner list; the engine reads all three):
  "AWF3" u32 rooms
  rooms x { u32 key, u32 first row, u32 rows }   ascending key: a room's cell number, or for an exterior cell
          0x80000000 | (grid x + 2048) << 12 | (grid y + 2048) (exterior_key)
  rows x 96 bytes { u8 kind ('I' item, 'A' actor, 'D' door), u8 owned, u8 action code (STEAL-PROMPT-58: bits 0-1
                    0 none / 1 take / 2 read / 3 talk, bit 2 owned, bit 3 magic scroll; 0 in older files; a container
                    'C': 1 opens (CONTAINER-WINDOW-59), 0 an organic one, flora, harvested), u8 a container's lock
                    level in the data (FLTV 0..100; 0 for everything else and in older files),
                    u32 reference,
                    i32 x, i32 y, i32 z (game units), f32 weight, i32 value, char name[36] (NUL-ended cp1252),
                    char id[32] (an item's record id, folded, NUL-padded; empty for actors and doors) }
  then the owners list (CELL-CHANGES-59 slice 2): "AWO1" u32 n,
  n x { u32 reference, u16 offset of its owner id in the pool, u8 flags (bit 0: a faction owns it), u8 0 }
          ascending reference: every owned item row whose owner id fits (OWNER_ID bytes, printable)
  u32 pool bytes, the pool: each owner id once, folded, NUL-ended
  then the containers' contents (CELL-CHANGES-59 slice 3; an engine of slice 2 stops reading before it):
  "AWC1" u32 n, n x { u32 reference, u32 first item, u16 items, u8 flags (bit 0: an entry restocks, bit 1: a levelled
          list left as the data has it, bit 2: organic), u8 0 }   ascending reference: every placed container ('C' rows, a container
          is owned like an item: its owner in the owners list)
  u32 items, items x { char id[32] (folded, NUL-padded), i32 count }   the record's NPCO list (a restocking entry's
          count made positive); levelled lists (LEVI) are left out (resolved by a later slice)
  then the reference identity table (CELL-CHANGES-59 slice 7; an engine of slice 6 stops reading before it): "AWI1"
          u8 files, files x { u8 index (tools/ref_identity.py), u8 length, the name, u32 references, 8 bytes of the
          file's SHA-256 }, i32 iMonthsToRespawn, f32 fCorpseRespawnDelay, f32 fCorpseClearDelay (the master's GMSTs),
          u32 rows, u32 step, u32 blocks, blocks x u32 the first key of each block of STEP rows,
          rows x { u32 key | flags << 24, u32 record hash }   ascending key: every live placed reference of the master
          by its stable id; flags 1 its record is flagged Respawn (CONT 2, CREA 2, NPC_ 4), 2 a levelled creature list;
          the record hash is FNV-1a over the record id folded to lower case (0 becomes 1; the engine's
          AW_LedgerNameHash). A saved game keeps each changed reference's hash, so a build of other game data can tell
          a reference that is gone or now names another record (engine aw_ledger.h AW_LedgerMigrate), and the respawn
          rules read the flags (OpenMW 0.51 CellStore::respawn).
The record id is what the engine adds to the inventory when the player takes a placed item (PICKUP-PLACED-58); the
owner is whom it is stolen from (the reference's owner ANAM, else its owning faction CNAM; the rule of OpenMW 0.51
mwmechanics/mechanicsmanagerimp.cpp itemTaken), kept by the engine's world change list as (item, owner).
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
OWNER_ID = 32           # the longest owner id the engine keeps (aw_ledger.h AW_LEDGER_STOLEN_ID)
OWNER_POOL = 65536      # the pool offsets are 16 bits
MAX_ROWS = 1024        # per room: the engine's table (aw_focus.c FOCUS_ROWS)
LIGHT_CARRY = 2         # LHDT flags: can be carried
CELL = 8192             # game units per exterior cell
GRID_BIAS = 2048        # exterior keys: grid offset into 12 bits
# The action code (STEAL-PROMPT-58), byte 2 of a row: what the activate key does and how the prompt reads.
ACT_NONE, ACT_TAKE, ACT_READ, ACT_TALK = 0, 1, 2, 3      # bits 0-1
ACT_OWNED = 4                                            # bit 2: taking it is theft
ACT_MAGIC_SCROLL = 8                                     # bit 3: a BOOK with an enchantment (taken, never read)
CONT_ORGANIC = 1        # CONT FLAG bit 0: organic (flora: harvested, never opened)
CFLAG_ORGANIC = 4       # the contents list's flag for it (bit 2)


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


def container_items(fields, items):
    """A CONT record's NPCO list: [(folded id, count)] of the entries ITEMS (the item records) knows, restocking
    counts made positive; and the flags (1: an entry restocks, 2: a levelled list was left out)."""
    out, flags = [], 0
    for key, value in fields:
        if key != 'NPCO' or len(value) < 36:
            continue
        count = struct.unpack_from('<i', value)[0]
        ident = value[4:36].split(b'\0', 1)[0].decode('ascii', 'replace').casefold()
        if count < 0:
            flags |= 1; count = -count
        if ident not in items:
            flags |= 2 if ident else 0
            continue
        if count and len(ident.encode('ascii', 'replace')) <= IDENT:
            out.append((ident, count))
    return out, flags


def objects_of(raw):
    """Folded record id -> (kind, name, weight, value, action[, contents, flags]) of every placeable item, actor,
    door and container (kind 'C': its contents and their flags, container_items)."""
    out = {}
    conts = []
    for tag, flags, payload in records(raw):
        if tag not in ITEM_DATA and tag not in ACTORS and tag not in ('DOOR', 'CONT'):
            continue
        fields = list(subrecords(payload))
        if flags & 0x20 or any(k == 'DELE' for k, _ in fields):
            continue
        ident = string(first(fields, 'NAME'), 'NAME', errors='replace').casefold()
        name = string(first(fields, 'FNAM'), 'FNAM', errors='replace')
        if tag == 'CONT':
            if name:
                flag = first(fields, 'FLAG')
                organic = len(flag) >= 4 and bool(struct.unpack_from('<I', flag)[0] & CONT_ORGANIC)
                conts.append((ident, name, fields, organic))
            continue
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
    items = {k for k, v in out.items() if v[0] == 'I'}
    for ident, name, fields, organic in conts:
        contents, cflags = container_items(fields, items)
        # CONTAINER-WINDOW-59: a container opens (ACT_TAKE: E opens its strip); an organic one (flora) is harvested,
        # never opened (action none, flag 4)
        out[ident] = ('C', name, 0.0, 0, ACT_NONE if organic else ACT_TAKE, contents,
                      cflags | (CFLAG_ORGANIC if organic else 0))
    return out


def lock_level(ref):
    """CONTAINER-WINDOW-59: a placed container's lock level in the data (FLTV, 0 unlocked, at most 100)."""
    raw = ref.get('FLTV', b'')
    if len(raw) < 4:
        return 0
    return max(0, min(100, struct.unpack_from('<i', raw)[0]))


def contents_list(containers):
    """The contents list after the owners list: CONTAINERS maps reference -> (contents, flags)."""
    index, body = [], []
    for reference in sorted(containers):
        contents, flags = containers[reference]
        index.append(struct.pack('<IIHBB', reference, len(body), len(contents), flags & 7, 0))
        for ident, count in contents:
            body.append(record_id(ident) + struct.pack('<i', count))
    return (b'AWC1' + struct.pack('<I', len(index)) + b''.join(index) + struct.pack('<I', len(body)) + b''.join(body))


RESPAWN_GMSTS = ('iMonthsToRespawn', 'fCorpseRespawnDelay', 'fCorpseClearDelay')
RESPAWN_DEFAULT = (4, 72.0, 72.0)     # Morrowind.esm's own values (OpenMW 0.51 reads the same GMSTs)
RESPAWN_FLAG = {'CONT': 2, 'CREA': 2, 'NPC_': 4}   # the record's Respawn flag (OpenMW esm3 loadcont/loadcrea/loadnpc)
REFS_STEP = 256
REFS_RESPAWN = 1
REFS_LEVELLED = 2


def name_hash(ident):
    """FNV-1a over the id's bytes with A-Z folded to lower case; 0 becomes 1 (engine aw_ledger.c AW_LedgerNameHash)."""
    h = 2166136261
    for c in ident.encode('cp1252', 'replace'):
        if 65 <= c <= 90:
            c += 32
        h = ((h ^ c) * 16777619) & 0xFFFFFFFF
    return h or 1


def respawn_settings(raw):
    """(iMonthsToRespawn, fCorpseRespawnDelay, fCorpseClearDelay) from the master's GMSTs, the defaults where absent."""
    found = dict(zip(RESPAWN_GMSTS, RESPAWN_DEFAULT))
    for tag, flags, payload in records(raw):
        if tag != 'GMST' or flags & 0x20:
            continue
        fields = list(subrecords(payload))
        name = string(first(fields, 'NAME'), 'NAME', errors='replace')
        if name not in found:
            continue
        for key, value in fields:
            if key == 'INTV' and len(value) >= 4 and name.startswith('i'):
                found[name] = struct.unpack_from('<i', value)[0]
            elif key == 'FLTV' and len(value) >= 4 and name.startswith('f'):
                found[name] = struct.unpack_from('<f', value)[0]
    return tuple(found[n] for n in RESPAWN_GMSTS)


def reference_flags(raw):
    """Folded record id -> table flags (REFS_RESPAWN, REFS_LEVELLED) of the records that have any."""
    out = {}
    for tag, flags, payload in records(raw):
        if tag not in RESPAWN_FLAG and tag != 'LEVC':
            continue
        fields = list(subrecords(payload))
        if flags & 0x20 or any(k == 'DELE' for k, _ in fields):
            continue
        ident = string(first(fields, 'NAME'), 'NAME', errors='replace').casefold()
        if tag == 'LEVC':
            out[ident] = REFS_LEVELLED
            continue
        value = first(fields, 'FLAG')
        if len(value) >= 4 and struct.unpack_from('<I', value)[0] & RESPAWN_FLAG[tag]:
            out[ident] = REFS_RESPAWN
    return out


def reference_table(raw, digest=None, name=MASTER):
    """The AWI1 section: every live placed reference of the master by its stable id, with its record hash and flags."""
    from ref_identity import RefIdentityError, file_index
    flags = reference_flags(raw)
    rows = {}
    for _cell, _interior, _grid, _region, refs in cells_of(raw):
        for ref in refs:
            if 'DELE' in ref or 'NAME' not in ref:
                continue
            try:
                key = stable_ref(name, ref['number'])
            except RefIdentityError:
                continue
            ident = string(ref['NAME'], 'NAME', errors='replace').casefold()
            rows.setdefault(key, (name_hash(ident), flags.get(ident, 0)))
    keys = sorted(rows)
    months, respawn_delay, clear_delay = respawn_settings(raw)
    raw_name = name.encode('ascii')
    files = struct.pack('<BBB', 1, file_index(name), len(raw_name)) + raw_name + struct.pack('<I', len(keys)) + \
        (bytes.fromhex(digest)[:8] if digest else bytes(8))
    blocks = [keys[i] for i in range(0, len(keys), REFS_STEP)]
    body = b''.join(struct.pack('<II', k | rows[k][1] << 24, rows[k][0]) for k in keys)
    return (b'AWI1' + files + struct.pack('<iffIII', months, respawn_delay, clear_delay, len(keys), REFS_STEP,
                                          len(blocks)) +
            b''.join(struct.pack('<I', k) for k in blocks) + body), len(keys), (months, respawn_delay, clear_delay)


def action_code(kind_action, owned):
    """The row's action code (byte 2): the kind in bits 0-1, owned in bit 2, a magic scroll in bit 3. The engine
    indexes its prompt table by it (aw_inventory.c AW_ItemPrompt); nothing is looked up per frame."""
    return (kind_action & (3 | ACT_MAGIC_SCROLL)) | (ACT_OWNED if owned else 0)


def owner_of(ref):
    """Whom taking the placed thing REF steals from (OpenMW 0.51 itemTaken): (owner id, 0) for its owner (ANAM), else
    (faction id, 1) for its owning faction (CNAM); None when neither is set or the id does not fit the engine's list
    (printable, at most OWNER_ID bytes)."""
    for key, faction in (('ANAM', 0), ('CNAM', 1)):
        if ref.get(key):
            ident = string(ref[key], key, errors='replace').strip().casefold()
            raw = ident.encode('ascii', 'replace')
            if not raw or len(raw) > OWNER_ID or any(b < 32 or b > 126 for b in raw):
                return None
            return ident, faction
    return None


def owner_list(owners):
    """The owners list after the rows: OWNERS maps reference -> (owner id, faction flag)."""
    pool, offsets, entries = bytearray(), {}, []
    for reference in sorted(owners):
        ident, faction = owners[reference]
        if ident not in offsets:
            offsets[ident] = len(pool)
            pool += ident.encode('ascii') + b'\0'
            if len(pool) > OWNER_POOL:
                raise SystemExit('[focus] the pool of owner ids is over %d bytes' % OWNER_POOL)
        entries.append(struct.pack('<IHBB', reference, offsets[ident], faction & 1, 0))
    return b'AWO1' + struct.pack('<I', len(entries)) + b''.join(entries) + struct.pack('<I', len(pool)) + bytes(pool)


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


def placements(raw, objects, numbers, extras=None):
    """Table key -> rows: interior cells of this master by their room number, exterior cells by exterior_key.
    EXTRAS (a dict, optional; AREA-TABLES-59): reference -> (trapped, key item id) of every placed container and door
    that has a trap (TNAM) or a key (KNAM), for the per-area tables (tools/prepare_area_tables.py)."""
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
            kind, name, weight, value, action = record[:5]
            x, y, z = struct.unpack_from('<fff', ref['DATA'])
            owned = int(kind in ('I', 'C') and bool(ref.get('ANAM') or ref.get('CNAM')))
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
            if extras is not None and kind in ('C', 'D') and (ref.get('TNAM') or ref.get('KNAM')):
                key_id = string(ref['KNAM'], 'KNAM', errors='replace').strip().casefold() if ref.get('KNAM') else ''
                extras[stable_ref(MASTER, ref['number'])] = (bool(ref.get('TNAM')), key_id)
            rows.append((kind, owned, stable_ref(MASTER, ref['number']), x, y, z, weight, value, name,
                         ident if kind in ('I', 'C') else '',
                         action_code(action, owned), owner_of(ref) if owned else None,
                         record[5:7] if kind == 'C' else None, lock_level(ref) if kind == 'C' else 0))
    return rooms


def build(data_files):
    from cell_numbers import load_table
    data = resolve_data_files(Path(data_files))
    raw = child_ci(data, 'Morrowind.esm').read_bytes()
    table, hashes = load_table(data)
    numbers = {row['cell'].casefold(): row['number'] for row in table if row['master'] == 'Morrowind.esm'}
    extras = {}
    rooms = placements(raw, objects_of(raw), numbers, extras)
    index, body, held, owners, containers = [], [], {}, {}, {}
    for number in sorted(rooms):
        rows = sorted(rooms[number], key=lambda r: r[2])
        if len(rows) > MAX_ROWS:
            held[number] = len(rows) - MAX_ROWS; rows = rows[:MAX_ROWS]
        index.append(struct.pack('<III', number, len(body), len(rows)))
        for kind, owned, reference, x, y, z, weight, value, name, ident, action, owner, contents, lock in rows:
            if contents is not None:
                containers[reference] = contents
            name = clean(name)
            body.append(struct.pack('<BBBBIiiifi', ord(kind), owned, action, lock, reference, int(round(x)), int(round(y)),
                                    int(round(z)), weight, value) + name + b'\0' * (NAME - len(name)) +
                        record_id(ident))
            if owner:
                owners[reference] = owner
    identities, references, respawn = reference_table(raw, hashes.get('Morrowind.esm'))
    payload = (b'AWF3' + struct.pack('<I', len(index)) + b''.join(index) + b''.join(body) + owner_list(owners) +
               contents_list(containers) + identities)
    assert all(len(r) == ROW for r in body)
    report = {'format': 'AWF3', 'rooms': len(index), 'rows': len(body), 'owners': len(owners),
              'containers': len(containers), 'references': references,
              'respawn': dict(zip(RESPAWN_GMSTS, respawn)), 'bytes': len(payload),
              'sha256': hashlib.sha256(payload).hexdigest(), 'master_sha256': hashes.get('Morrowind.esm'),
              'held_rows': held}
    # AREA-TABLES-59: traps and keys of placed containers and doors (not in focus.awf; read by
    # tools/prepare_area_tables.py from the stage's focus-extras.json)
    report['extras'] = {str(k): [int(t), key] for k, (t, key) in sorted(extras.items())}
    return payload, report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-files', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    a = p.parse_args()
    payload, report = build(a.data_files)
    (a.out / 'id1').mkdir(parents=True, exist_ok=True)
    (a.out / 'id1/focus.awf').write_bytes(payload)
    extras = report.pop('extras')
    (a.out / 'focus-extras.json').write_text(json.dumps(extras, indent=0) + '\n', encoding='utf-8', newline='\n')
    (a.out / 'focus-receipt.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('[focus] %d rooms, %d placed things, %d owned things with their owner, %d containers with contents, '
          '%d references in the identity table, %d bytes'
          % (report['rooms'], report['rows'], report['owners'], report['containers'], report['references'],
             report['bytes']), flush=True)


if __name__ == '__main__':
    main()
