#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The item model table (ITEM-WORLD-MODELS-58): every carriable item's world model, one alias model per distinct
original mesh, keyed by the mesh path.

A build stage of its own (builder step item-models, after the census for its palette). Every item record the
inventory catalogues (tools/prepare_inventory.py source_items: weapons, armour, clothing, potions, ingredients,
books, misc items, keys, gold, tools, carried lights) names a mesh; each distinct mesh is converted once
(npc_items.item_model) on every core, and the converted file is squeezed: the skin is cut to the rows and
columns its texture coordinates reach (the model's only large part). The output is

  id1/progs/items/m<16 hex>.mdl   one per mesh (the name is the SHA-256 of the mesh key)
  id1/progs/items/models.awt      the table: "AWT1 <rows>" then one "<mesh key>\t<payload path>" line per mesh
  item-models-receipt.json        per mesh: path, SHA-256, bytes before and after the squeeze

The models are disk-only: the engine loads one when an item lies on the ground (aw_inventory.c inv_model) and
nothing is resident before that. The same table serves the items placed in the game's cells
(WORLD-OBJECT-PLACEMENT-59): the stage also writes

  id1/progs/items/placed.awp      per room and exterior cell, every placed takeable item: its reference, its row in
                                  models.awt, position, rotation and scale (placement_list below)

so an item in a room or outdoors is drawn by reference to the one shared model of its mesh, never a copy. The
engine draws the rows the map does not draw itself (aw_inventory.c placed_load); the aim box and the activate
key use the same reference (focus.awf). Each room, and each exterior cell with its eight neighbours (what the
engine holds at once outdoors), may name at most PLACED_MODELS distinct models (the engine's AW_PLACED_MODELS):
the stage refuses a key over it here, never in the image or the game.
Each mesh's result is kept in the image pass cache (pass_cache.PassCache 'item-models', AMIWIND_PASS_CACHE),
keyed by the game data, the mesh, the palette and the conversion code: a mesh that did not change is not
converted again. Meshes that do not convert (no geometry) are listed in the receipt and have no row."""
import argparse
import hashlib
import json
import math
import struct
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))          # ahead of tools/ (tools/mwad.py is a command, src/mwad the package)
from ref_identity import stable_ref  # noqa: E402

TABLE ='progs/items/models.awt'
PLACED = 'progs/items/placed.awp'
# The engine's per-level room for placed item models (aw_inventory.h AW_PLACED_MODELS; tests/test_item_models.py
# keeps the two equal; the engine source is not read here, so an engine edit does not re-key this stage).
PLACED_MODELS = 96
PLACED_ROW = 48
PLACED_ROWS = 1024          # per key: the engine's focus table (aw_inventory.c FOCUS_ROWS)
SCALE_ONE = 1 << 12         # u16 scale in twelve fraction bits (TES3 XSCL is 0.5 to 2.0)
_STATE = {}


def model_path(key):
    """The payload path of a mesh key's model (64-byte catalogue field safe)."""
    return 'progs/items/m%s.mdl' % hashlib.sha256(key.encode('utf-8')).hexdigest()[:16]


def squeeze(raw):
    """The alias model with its skin cut to what its texture coordinates reach (+1 texel, width a multiple of 4).
    One skin, single (group 0) skins only; anything else is returned unchanged. Lossless for the drawn model."""
    if raw[:4] != b'IDPO' or struct.unpack_from('<i', raw, 4)[0] != 6:
        return raw
    numskins, w, h, nv, nt, nf = struct.unpack_from('<6i', raw, 48)
    if numskins != 1 or struct.unpack_from('<i', raw, 84)[0] != 0:
        return raw
    skin_at = 88
    uv_at = skin_at + w * h
    us = vs = 0
    for i in range(nv):
        _, u, v = struct.unpack_from('<3i', raw, uv_at + 12 * i)
        us, vs = max(us, u), max(vs, v)
    nw = min(w, (us + 2 + 3) // 4 * 4)
    nh = min(h, vs + 2)
    if (nw, nh) == (w, h):
        return raw
    skin = raw[skin_at:uv_at]
    cut = b''.join(skin[row * w:row * w + nw] for row in range(nh))
    head = bytearray(raw[:skin_at])
    struct.pack_into('<2i', head, 52, nw, nh)
    return bytes(head) + cut + raw[uv_at:]


def _convert(task):
    """Pool worker: (key, raw squeezed model or None, size before, error)."""
    data, key, mesh, palette = task
    if _STATE.get('data') != data:
        from npc_geometry import Assets
        from mwad.audit import BSA
        from mwad.paths import child_ci
        from prepare_scenery import nif_reader
        _STATE.clear()
        _STATE.update(data=data, nif=nif_reader(), assets=Assets(Path(data), BSA(child_ci(Path(data), 'Morrowind.bsa'))))
    from npc_items import item_model
    try:
        raw = item_model(_STATE['assets'], {'slot': 25, 'id': key, 'mesh': mesh, 'attach': '', 'filter': ''},
                         palette, _STATE['nif'])
    except (ValueError, KeyError, OSError, IndexError) as error:
        return key, None, 0, str(error)[:200]
    return key, squeeze(raw), len(raw), None


def meshes(data):
    """{mesh key: original mesh path} of every item the inventory catalogues."""
    from prepare_inventory import source_items, mesh_key
    items = source_items(data)[0]
    out = {}
    for identifier in sorted(items):
        mesh = items[identifier]['source_model']
        if mesh:
            out.setdefault(mesh_key(mesh), mesh)
    return out


def build(data_files, palette, out, jobs=None):
    from mwad.paths import resolve_data_files
    from build_parallel import in_order_map
    import pass_cache
    data = resolve_data_files(Path(data_files))
    palette = bytes(palette)
    if len(palette) != 768:
        raise ValueError('Expected the 256-colour game palette')
    out = Path(out)
    wanted = meshes(data)
    game = pass_cache.game_data_digest()
    cache = pass_cache.PassCache.open('item-models', {'palette': hashlib.sha256(palette).hexdigest(), 'form': 1},
                                      (str(Path(__file__).resolve()), '_convert')) if game else None
    results, tasks = {}, []
    for key, mesh in sorted(wanted.items()):
        found = cache.load(pass_cache.input_digest([game, key])) if cache else None
        if found is not None and found[1] is not None:
            results[key] = (found[1], found[0].get('before', len(found[1])), None)
        else:
            tasks.append((str(data), key, mesh, palette))
    start = time.time()
    print('[item-models] %d meshes: %d from the cache, %d to convert on %s workers' % (
        len(wanted), len(results), len(tasks), jobs or 'all'), flush=True)
    for done, (key, raw, before, error) in enumerate(in_order_map(_convert, tasks, jobs), 1):
        if done % 100 == 0 or done == len(tasks):
            print('[item-models] converted %d/%d (%.0f s)' % (done, len(tasks), time.time() - start), flush=True)
        results[key] = (raw, before, error)
        if cache and raw is not None:
            cache.store(pass_cache.input_digest([game, key]), {'before': before}, raw)
    folder = out / 'id1/progs/items'
    folder.mkdir(parents=True, exist_ok=True)
    rows, receipt = [], {'models': {}, 'held': {}}
    for key in sorted(results):
        raw, before, error = results[key]
        if raw is None:
            receipt['held'][key] = error
            continue
        path = model_path(key)
        (out / 'id1' / path).write_bytes(raw)
        rows.append('%s\t%s' % (key, path))
        receipt['models'][key] = {'path': path, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
                                  'bytes_before_squeeze': before}
    table = ('AWT1 %d\n' % len(rows) + ''.join(r + '\n' for r in rows)).encode('utf-8')
    (out / 'id1' / TABLE).write_bytes(table)
    # the items placed in the cells, by reference to the table's models (WORLD-OBJECT-PLACEMENT-59)
    placed, receipt['placed'] = build_placed(data, read_table(table))
    (out / 'id1' / PLACED).write_bytes(placed)
    print('[item-models] placed items: %d in %d rooms and %d exterior cells, %d distinct models; at most %d models in '
          'a room, %d around an exterior cell (limit %d)' % (
              receipt['placed']['rows'], receipt['placed']['rooms'], receipt['placed']['exterior_cells'],
              receipt['placed']['distinct_models'], receipt['placed']['most_models_room'],
              receipt['placed']['most_models_outdoors'], PLACED_MODELS), flush=True)
    receipt.update(meshes=len(wanted), converted=len(rows), table=TABLE,
                   palette_sha256=hashlib.sha256(palette).hexdigest(),
                   table_sha256=hashlib.sha256(table).hexdigest(),
                   bytes=sum(m['bytes'] for m in receipt['models'].values()),
                   bytes_before_squeeze=sum(m['bytes_before_squeeze'] for m in receipt['models'].values()),
                   converted_now=len(tasks), cache=cache.summary() if cache else None,
                   seconds=round(time.time() - start, 1))
    (out / 'item-models-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8', newline='\n')
    return receipt


def read_table(raw):
    """{mesh key: payload path} of a models.awt table; ValueError when it is malformed."""
    lines = raw.decode('utf-8').split('\n')
    head = lines[0].split()
    if len(head) != 2 or head[0] != 'AWT1' or lines[-1] != '':
        raise ValueError('Not an item model table')
    rows = [line.split('\t') for line in lines[1:-1]]
    if len(rows) != int(head[1]) or any(len(r) != 2 or not r[0] or not r[1].endswith('.mdl') for r in rows):
        raise ValueError('Damaged item model table')
    return dict(rows)


# ---------------------------------------------------------------- placed items (WORLD-OBJECT-PLACEMENT-59)

def alias_angles(rotation):
    """(pitch, yaw, roll) in degrees for an alias entity whose drawn rotation is the TES3 placement ROTATION
    (radians, prepare_scenery.reference_rotation: Z then Y then X, clockwise). The alias renderer turns a model
    by AngleVectors(-pitch, yaw, roll) with the columns forward, -right, up (r_alias.c R_AliasSetUpTransform);
    the stored pitch carries that sign. A yaw-only placement gets yaw = -z exactly (the actors' rule)."""
    x, y, z = [-a for a in rotation]
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    # model to world: Rx(x) Ry(y) Rz(z) on column vectors
    rz = ((cz, -sz, 0.0), (sz, cz, 0.0), (0.0, 0.0, 1.0))
    ry = ((cy, 0.0, sy), (0.0, 1.0, 0.0), (-sy, 0.0, cy))
    rx = ((1.0, 0.0, 0.0), (0.0, cx, -sx), (0.0, sx, cx))
    m = _mul(rx, _mul(ry, rz))
    if not any(abs(math.sin(a)) > 1e-7 or math.cos(a) < 0 for a in rotation[:2]):
        return 0.0, -math.degrees(rotation[2]), 0.0
    p = math.asin(max(-1.0, min(1.0, -m[2][0])))
    if abs(math.cos(p)) > 1e-6:
        yaw, roll = math.atan2(m[1][0], m[0][0]), math.atan2(m[2][1], m[2][2])
    else:
        yaw, roll = math.atan2(-m[0][1], m[1][1]), 0.0
    angles = (-math.degrees(p), math.degrees(yaw), math.degrees(roll))
    error = max(abs(a - b) for ra, rb in zip(alias_matrix(angles), m) for a, b in zip(ra, rb))
    if error > 1e-4:
        raise ValueError('Placed item rotation %r: alias angles %r are %.3g from it' % (rotation, angles, error))
    return angles


def _mul(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def alias_matrix(angles):
    """Model to world of an alias entity with ANGLES (the engine's own rule, see alias_angles): rows of the matrix
    whose columns are forward, -right, up of AngleVectors(-pitch, yaw, roll)."""
    p, yw, r = math.radians(-angles[0]), math.radians(angles[1]), math.radians(angles[2])
    sp, cp, sy, cy, sr, cr = math.sin(p), math.cos(p), math.sin(yw), math.cos(yw), math.sin(r), math.cos(r)
    forward = (cp * cy, cp * sy, -sp)
    right = (-sr * sp * cy + cr * sy, -sr * sp * sy - cr * cy, -sr * cp)
    up = (cr * sp * cy + sr * sy, cr * sp * sy - sr * cy, cr * cp)
    return tuple((forward[i], -right[i], up[i]) for i in range(3))


def placement_list(raw, items, table, numbers):
    """{key: [row]} of every placed takeable item of the master RAW whose mesh has a model in TABLE ({mesh key:
    payload path}, models.awt order = TABLE's insertion order), keyed as focus.awf keys its rooms (NUMBERS: folded
    interior cell name -> room number; exteriors by prepare_focus.exterior_key). A row: (reference, model row,
    model path, x, y, z, pitch, yaw, roll, scale). Carried lights are left to the maps' own light path (a lamp on a
    table is drawn and lit there); every other item the catalogue (ITEMS: prepare_inventory.source_items) knows."""
    from prepare_focus import cells_of, exterior_key, GRID_BIAS
    from prepare_inventory import mesh_key
    index = {key: i for i, key in enumerate(table)}
    out, missing = {}, {}
    for cell, interior, grid, _, refs in cells_of(raw):
        if interior:
            if not cell or cell.casefold() not in numbers:
                continue
            key = numbers[cell.casefold()]
        elif not all(abs(g) < GRID_BIAS for g in grid) or not refs:
            continue
        else:
            key = exterior_key(*grid)
        for ref in refs:
            if 'DELE' in ref or 'NAME' not in ref or len(ref.get('DATA', b'')) != 24:
                continue
            ident = ref['NAME'].split(b'\0')[0].decode('cp1252', 'replace').casefold()
            item = items.get(ident)
            if not item or item.get('light') or not item.get('source_model'):
                continue
            mesh = mesh_key(item['source_model'])
            if mesh not in index:
                missing[mesh] = missing.get(mesh, 0) + 1
                continue
            x, y, z, rx, ry, rz = struct.unpack('<6f', ref['DATA'])
            scale = struct.unpack('<f', ref['XSCL'])[0] if len(ref.get('XSCL', b'')) == 4 else 1.0
            if not all(math.isfinite(v) for v in (x, y, z, rx, ry, rz, scale)) or not 0 < scale <= 15:
                continue
            # the stable reference id (tools/ref_identity.py, CELL-CHANGES-59), the same key as focus.awf's rows
            out.setdefault(key, []).append((stable_ref('Morrowind.esm', ref['number']), index[mesh], table[mesh], x, y, z,
                                            *alias_angles((rx, ry, rz)), scale))
    return out, missing


def neighbourhoods(rows):
    """{exterior key: distinct model rows of the cell and its eight neighbours}: what the engine holds at once
    outdoors (aw_inventory.c focus_load reads the 3 x 3 cells around the player)."""
    from prepare_focus import GRID_BIAS
    out = {}
    for key in rows:
        if not key & 0x80000000:
            continue
        gx, gy = (key >> 12 & 0xFFF) - GRID_BIAS, (key & 0xFFF) - GRID_BIAS
        near = set()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                other = 0x80000000 | ((gx + dx + GRID_BIAS) & 0xFFF) << 12 | ((gy + dy + GRID_BIAS) & 0xFFF)
                near |= {r[1] for r in rows.get(other, ())}
        out[key] = near
    return out


def check_placed(rows, limit=PLACED_MODELS):
    """Refuse (ValueError naming every key) a room, or an exterior cell with its neighbours, that names more than
    LIMIT distinct item models, or a key with more rows than the engine's table; returns the per-key counts."""
    problems, counts = [], {}
    near = neighbourhoods(rows)
    for key, items in sorted(rows.items()):
        models = len(near[key]) if key in near else len({r[1] for r in items})
        counts[key] = {'rows': len(items), 'models': models}
        if models > limit:
            problems.append('%s %#x: %d item models (the engine holds %d per level: AW_PLACED_MODELS)' % (
                'exterior cell' if key in near else 'room', key, models, limit))
        if len(items) > PLACED_ROWS:
            problems.append('key %#x: %d placed items (the engine reads %d)' % (key, len(items), PLACED_ROWS))
    if problems:
        raise ValueError('Placed items over the engine limits (WORLD-OBJECT-PLACEMENT-59):\n  ' + '\n  '.join(problems))
    return counts


def pack_placed(rows):
    """The AWP1 file (little-endian):
      "AWP1" u32 keys
      keys x { u32 key, u32 first row, u32 rows, u32 distinct models }   ascending key (focus.awf's keys)
      rows x 48 bytes { u32 reference, u16 model row (models.awt), u16 scale (12 fraction bits), f32 x, y, z (game units),
                        f32 pitch, yaw, roll (alias degrees), char model[16] (the 16 hex of progs/items/m<hex>.mdl) }
    rows of a key ascending by reference."""
    index, body = [], []
    for key in sorted(rows):
        items = sorted(rows[key])
        index.append(struct.pack('<IIII', key, len(body), len(items), len({r[1] for r in items})))
        for reference, row, path, x, y, z, pitch, yaw, roll, scale in items:
            stem = path[len('progs/items/m'):-len('.mdl')]
            if len(stem) != 16 or not all(c in '0123456789abcdef' for c in stem):
                raise ValueError('Placed item model outside the item model table: ' + path)
            body.append(struct.pack('<IHH6f', reference, row, max(1, min(0xFFFF, round(scale * SCALE_ONE))),
                                    x, y, z, pitch, yaw, roll) + stem.encode('ascii'))
    assert all(len(r) == PLACED_ROW for r in body)
    return b'AWP1' + struct.pack('<I', len(index)) + b''.join(index) + b''.join(body)


def read_placed(raw):
    """{key: [(reference, model row, scale, (x, y, z), (pitch, yaw, roll), model path)]} of an AWP1 file;
    ValueError when it is malformed (the engine refuses the same: aw_inventory.c placed_load)."""
    if raw[:4] != b'AWP1' or len(raw) < 8:
        raise ValueError('Not a placed item list')
    keys = struct.unpack_from('<I', raw, 4)[0]
    base = 8 + keys * 16
    if keys > 65535 or base > len(raw) or (len(raw) - base) % PLACED_ROW:
        raise ValueError('Damaged placed item list')
    total = (len(raw) - base) // PLACED_ROW
    out, last = {}, -1
    for i in range(keys):
        key, first, count, _ = struct.unpack_from('<IIII', raw, 8 + 16 * i)
        if key <= last or first + count > total or count > PLACED_ROWS:
            raise ValueError('Damaged placed item list')
        last = key
        rows = out[key] = []
        for j in range(first, first + count):
            at = base + j * PLACED_ROW
            reference, model, scale = struct.unpack_from('<IHH', raw, at)
            values = struct.unpack_from('<6f', raw, at + 8)
            rows.append((reference, model, scale / SCALE_ONE, values[:3], values[3:],
                         'progs/items/m%s.mdl' % raw[at + 32:at + 48].decode('ascii')))
    return out


def install_placed(stage, id1, receipt, table):
    """The image step's part (build_aga.install_item_models): the stage's placed item list into id1, checked against
    its receipt and the installed TABLE (every row names one of its models); {} for a stage run without one."""
    placed = receipt.get('placed')
    if not placed:
        return {}
    raw = (Path(stage) / 'id1' / placed['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != placed['sha256']:
        raise ValueError('Placed item list differs from its stage receipt')
    paths = set(table.values())
    if any(row[5] not in paths for rows in read_placed(raw).values() for row in rows):
        raise ValueError('Placed item list names a model outside the item model table')
    (Path(id1) / placed['path']).write_bytes(raw)
    return {'placed': 'id1/' + placed['path'], 'placed_rows': placed['rows'], 'placed_keys': placed['keys'],
            'placed_sha256': placed['sha256']}


def build_placed(data, table):
    """(payload, receipt part) of the placed item list for the item model TABLE ({mesh key: path}, file order)."""
    from cell_numbers import load_table
    from mwad.paths import child_ci
    from prepare_inventory import source_items
    numbers = {row['cell'].casefold(): row['number'] for row in load_table(data)[0] if row['master'] == 'Morrowind.esm'}
    rows, missing = placement_list(child_ci(data, 'Morrowind.esm').read_bytes(), source_items(data)[0], table, numbers)
    counts = check_placed(rows)
    payload = pack_placed(rows)
    rooms = {k: v for k, v in counts.items() if not k & 0x80000000}
    outdoors = {k: v for k, v in counts.items() if k & 0x80000000}
    part = {'path': PLACED, 'sha256': hashlib.sha256(payload).hexdigest(), 'bytes': len(payload),
            'keys': len(rows), 'rooms': len(rooms), 'exterior_cells': len(outdoors),
            'rows': sum(len(v) for v in rows.values()), 'model_limit': PLACED_MODELS,
            'distinct_models': len({r[1] for v in rows.values() for r in v}),
            'most_models_room': max((v['models'] for v in rooms.values()), default=0),
            'most_models_outdoors': max((v['models'] for v in outdoors.values()), default=0),
            'per_key': {'%d' % k: v for k, v in sorted(counts.items())},
            'no_model': dict(sorted(missing.items()))}
    return payload, part


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--data-files', required=True, type=Path)
    p.add_argument('--palette', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    from build_jobs import add_jobs
    add_jobs(p)
    a = p.parse_args()
    # the palette the image step ends with (the hand catalogue's rule): the installed models need no remap
    from prepare_hand_catalog import runtime_palette
    receipt = build(a.data_files, runtime_palette(a.data_files, a.palette), a.out, a.jobs)
    print('[item-models] %d meshes, %d converted (%d now), %d held; %d bytes (%d before the squeeze), %.1f s' % (
        receipt['meshes'], receipt['converted'], receipt['converted_now'], len(receipt['held']), receipt['bytes'],
        receipt['bytes_before_squeeze'], receipt['seconds']), flush=True)


if __name__ == '__main__':
    main()
