#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""What goes with a taken or disabled object: the effects tied to its placement (TAKEN-LIGHT-FLAME-61).

The rule, for the whole game, in two questions: can it be picked up (a light whose LIGH record has the can-carry
flag), and does it give light (a radius, or a flame emitter in its mesh)? If both are yes, every light-giving effect
at its spot goes with it when it is taken or disabled: its flame sprites, its night lamp light, and outdoors the
placement itself. A fixed light (no can-carry flag) keeps its effects.

Rooms (whole and batch) tie their flames in the map itself: every aw_flame row of a placement names it ("aw_ref",
tools/prepare_mesh_bsp.py flame_entities, tools/chim/interior.py). Outdoors the CHIM world and its frame maps are
left as they are (no world stage re-keyed): at image assembly each exterior cell's own record in id1/areas.awa
(tools/prepare_area_tables.py, loaded with the cell in the read that already happens and freed with it) gets a small
last section, the cell's effect links (small lookup tables per area, never one for the whole world):

  "AWE1" u16 rows u16 0, rows x 12 bytes { u8 kind, u8 0, u16 aux, u32 key, u32 reference }, ascending
         (kind, key, aux); then u32 the section's offset in the record, "AWE1" (the record's last 8 bytes)
    'P'  key = a CHIM placement id of the reference (every cut piece): hidden by reference (chim_chunks.c), so the
         light can be taken and stays taken after a load or a crossing
    'F'  key = the frame map name's hash (prepare_area_tables.name_hash of its stem), aux = the order of its aw_flame
         row among the map's aw_flame rows (aw_guard_torch.c)
    'L'  key = the row of world/lamps.awl (aw_lamps.c)

Keys are the area keys of focus.awf and the items index (prepare_focus.exterior_key of the light's own cell); the
references are the stable ids (tools/ref_identity.py) the world change list uses. The general hide by reference of
an exterior placement ('P' rows) is meant for every takeable or disableable object later (OUTDOOR-ITEMS-TAKE-61);
today it lists the carriable lights only.

check() is the build's keeper of the rule: it refuses an image where a carriable light's flame in any map, its night
lamp row or its exterior placement has no link to its reference (a flame cut by a map's flame cap is not drawn at
all and is only counted).
"""
import collections
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'src', ROOT / 'tools'):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

LAMPS = 'world/lamps.awl'
AREAS = 'areas.awa'
MAGIC = b'AWE1'
ROW = struct.Struct('<BBHII')
KIND_PLACE, KIND_FLAME, KIND_LAMP = ord('P'), ord('F'), ord('L')
MASTERS = ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm')
# LHDT flags (tools/light_sources.py): can be carried, negative (a darkener), off by default (an unlit prop)
CARRY, NEGATIVE, OFF_DEFAULT = 0x2, 0x4, 0x20
# engine/aga/src/aw_guard_torch.c STATIC_FLAME_MAX (tools/chim/flames.py)
FLAME_CAP = 128
# engine/aga/src/chim/chim_chunks.c CHIM_GONE_PIDS and aw_mwhost.c exterior_hide: placement ids of one reference
PIECES_MAX = 16


# ---------------------------------------------------------------- the game data: which placements the rule covers

def light_records(raw):
    """{folded id: {'model', 'radius', 'flags'}} of the live LIGH records of one master."""
    from mwad.audit import records, subrecords, string
    out = {}
    for tag, flags, payload in records(raw):
        if tag != 'LIGH' or flags & 0x20:
            continue
        s = dict(subrecords(payload))
        if len(s.get('LHDT', b'')) != 24 or 'NAME' not in s:
            continue
        out[string(s['NAME'], errors='replace').casefold()] = {
            'model': string(s.get('MODL', b''), errors='replace'),
            'radius': struct.unpack_from('<I', s['LHDT'], 12)[0],
            'flags': struct.unpack_from('<I', s['LHDT'], 20)[0]}
    return out


def gives_light(light, has_flame):
    """The second question of the rule: a light that gives light (not an unlit prop or a darkener)."""
    return bool(not light['flags'] & (OFF_DEFAULT | NEGATIVE) and (light['radius'] > 0 or has_flame))


def mesh_flame_reader(data_files):
    """flames(model) -> number of flame emitters of a LIGH mesh (prepare_scenery.model_flames, the converters'
    rule), read from the loose files or the archives once per mesh; None when the mesh is not found."""
    from mwad.audit import BSA
    from mwad.paths import child_ci
    from npc_geometry import bsa_read
    from prepare_scenery import model_flames, nif_reader
    data = Path(data_files)
    archives = [BSA(p) for p in (child_ci(data, n, required=False) for n in
                                 ('Bloodmoon.bsa', 'Tribunal.bsa', 'Morrowind.bsa')) if p is not None]
    meshes = child_ci(data, 'Meshes', required=False)
    loose = ({p.relative_to(data).as_posix().casefold(): p for p in meshes.rglob('*') if p.is_file()}
             if meshes is not None else {})
    N, seen = nif_reader(), {}

    def flames(model):
        key = ('meshes/' + model.replace('\\', '/')).casefold()
        if key not in seen:
            raw = loose[key].read_bytes() if key in loose else None
            for archive in archives if raw is None else ():
                try:
                    raw = bsa_read(archive, key)
                    break
                except (KeyError, ValueError):
                    continue
            seen[key] = None if raw is None else len(model_flames(raw, N, key))
        return seen[key]
    return flames


def carriable_lights(data_files, flames=None):
    """{stable reference: {'id', 'master', 'interior', 'cell', 'position', 'flames'}} of every placement of a light
    the rule covers (can-carry flag and gives light), in the three masters (a later master's record wins), read with
    the items index's own readers (prepare_focus.cells_of, ref_identity.stable_ref: the same keys). flames:
    mesh_flame_reader's function (made here when None)."""
    from mwad.paths import child_ci
    from prepare_focus import cells_of
    from ref_identity import stable_ref
    data = Path(data_files)
    raws = {m: p.read_bytes() for m, p in ((m, child_ci(data, m, required=False)) for m in MASTERS) if p is not None}
    lights = {}
    for m in MASTERS:
        if m in raws:
            lights.update(light_records(raws[m]))
    flames = mesh_flame_reader(data) if flames is None else flames
    covered = {}
    for ident, light in lights.items():
        if light['flags'] & CARRY and light['model']:
            n = flames(light['model']) or 0
            if gives_light(light, n > 0):
                covered[ident] = n > 0
    out = {}
    for m in MASTERS:
        for cell, interior, grid, _, refs in cells_of(raws[m]) if m in raws else ():
            for ref in refs:
                if 'DELE' in ref or 'NAME' not in ref or len(ref.get('DATA', b'')) != 24:
                    continue
                ident = ref['NAME'].split(b'\0')[0].decode('cp1252', 'replace').casefold()
                if ident not in covered:
                    continue
                out[stable_ref(m, ref['number'])] = {
                    'id': ident, 'master': m, 'interior': interior, 'cell': cell if interior else tuple(grid),
                    'position': struct.unpack_from('<3f', ref['DATA']), 'flames': covered[ident]}
    return out


def outdoor(lights):
    return {r: light for r, light in lights.items() if not light['interior']}


def area_key(light):
    from prepare_focus import exterior_key
    return exterior_key(int(light['cell'][0]), int(light['cell'][1]))


# ---------------------------------------------------------------- the links (image assembly)

def lamp_rows(raw):
    """[(cell x, cell y, x, y, z)] of an AWL1 lamp table, in file order (the engine's row numbers)."""
    if raw[:4] != b'AWL1' or len(raw) < 8:
        raise ValueError('Not a lamp table')
    count = struct.unpack_from('<I', raw, 4)[0]
    if len(raw) != 8 + 20 * count:
        raise ValueError('Damaged lamp table')
    return [struct.unpack_from('<hh3f', raw, 8 + 20 * i) for i in range(count)]


def _f32(v):
    return struct.unpack('<f', struct.pack('<f', v))[0]


def lamp_links(lamps, lights):
    """[(row, reference)] of the lamp rows standing at an exterior carriable light (the same cell and the same f32
    position: the lamp table is written from the same placement), ascending row."""
    at = {(int(l['cell'][0]), int(l['cell'][1])) + tuple(_f32(v) for v in l['position']): r
          for r, l in outdoor(lights).items()}
    return [(i, at[tuple(row)]) for i, row in enumerate(lamps) if tuple(row) in at]


def place_links(world, lights):
    """[(placement id, reference)] of every CHIM exterior placement (every cut piece) of a carriable light."""
    from chim.cut import source_ref
    out_refs = set(outdoor(lights))
    out = set()
    for _, _, chunks in world['frames']:
        for c in chunks:
            for r in c['owned']:
                if source_ref(r['ref']) in out_refs:
                    out.add((r['pid'], source_ref(r['ref'])))
    return sorted(out)


def map_entities(path):
    from chim.frame_map import entities
    return entities(Path(path).read_bytes())


_MODELS = {}


def _models(world):
    """The world's model list with each model's flame emitters read once (chim.flames._Models)."""
    from chim.flames import _Models
    if _MODELS.get('models') is not world['models']:
        _MODELS.clear()
        _MODELS.update(models=world['models'], table=_Models(world['models']))
    return _MODELS['table']


def frame_flame_links(rows, world, lights):
    """[(flame row, reference)] of one frame map (its entity rows): the aw_flame rows that the frame's carriable
    light placements give (chim.flames.frame_rows with refs, matched by their written origin), in map order."""
    from chim.flames import FLAME_CLASS, REF_KEY, frame_rows
    from chim.frame_map import frames_at
    cell = tuple(int(v) for v in rows[0]['_chim_frame'].split())
    found = frames_at(world['frames'], cell)
    if not found:
        return []
    _, (_, _, chunks) = found[0]
    expected, _ = frame_rows(chunks, _models(world), cap=None, refs=True)
    out_refs = set(outdoor(lights))
    by_origin = {e['origin']: int(e[REF_KEY]) for e in expected if int(e.get(REF_KEY, 0)) in out_refs}
    links, k = [], 0
    for e in rows:
        if e.get('classname') != FLAME_CLASS:
            continue
        if e['origin'] in by_origin and REF_KEY not in e:
            links.append((k, by_origin[e['origin']]))
        k += 1
    return links


def frame_maps(id1):
    """[(stem, entity rows)] of the CHIM exterior frame maps in id1/maps."""
    from map_files import map_files
    out = []
    for p in map_files(Path(id1) / 'maps'):
        rows = map_entities(p)
        if rows and '_chim_frame' in rows[0] and '_chim_room' not in rows[0]:
            out.append((p.stem, rows))
    return out


def area_rows(id1, world, lights):
    """{area key: sorted [(kind, aux, key, reference)]}: every effect link of the image, in the area (exterior
    cell) of the light it belongs to."""
    from prepare_area_tables import name_hash
    id1 = Path(id1)
    lit = outdoor(lights)
    rows = collections.defaultdict(set)
    if (id1 / LAMPS).is_file():
        for row, ref in lamp_links(lamp_rows((id1 / LAMPS).read_bytes()), lights):
            rows[area_key(lit[ref])].add((KIND_LAMP, 0, row, ref))
    if world is not None:
        pieces = collections.Counter()
        for pid, ref in place_links(world, lights):
            rows[area_key(lit[ref])].add((KIND_PLACE, 0, pid, ref))
            pieces[ref] += 1
        over = sorted(r for r, n in pieces.items() if n > PIECES_MAX)
        if over:
            raise ValueError('Carriable lights cut into more than %d pieces (the engine hides at most that many): %s'
                             % (PIECES_MAX, ', '.join(map(str, over))))
        for stem, entities in frame_maps(id1):
            for ordinal, ref in frame_flame_links(entities, world, lights):
                rows[area_key(lit[ref])].add((KIND_FLAME, ordinal, name_hash(stem), ref))
    return {k: sorted(v, key=lambda r: (r[0], r[2], r[1])) for k, v in rows.items()}


def section(rows):
    """An area's effect link section (without its trailer)."""
    if len(rows) > 0xFFFF:
        raise ValueError('An area holds more than 65535 effect links')
    return MAGIC + struct.pack('<HH', len(rows), 0) + b''.join(ROW.pack(k, 0, aux, key, ref) for k, aux, key, ref in rows)


def read_section(record):
    """[(kind, aux, key, reference)] of an area record's effect link section ([] without one)."""
    if len(record) < 16 or record[-4:] != MAGIC:
        return []
    at = struct.unpack_from('<I', record, len(record) - 8)[0]
    if record[at:at + 4] != MAGIC:
        raise ValueError('Damaged effect link section')
    n = struct.unpack_from('<H', record, at + 4)[0]
    if at + 8 + n * ROW.size != len(record) - 8:
        raise ValueError('Damaged effect link section')
    return [(k, aux, key, ref) for k, _, aux, key, ref in (ROW.unpack_from(record, at + 8 + i * ROW.size)
                                                           for i in range(n))]


def read_areas(raw):
    """(head 24 bytes, [(key, offset, bytes)], bytes between the index and the first record, {key: record})."""
    if raw[:4] != b'AWA1':
        raise ValueError('areas.awa is not AWA1')
    n = struct.unpack_from('<I', raw, 4)[0]
    index = [struct.unpack_from('<III', raw, 24 + 12 * i) for i in range(n)]
    first = min((o for _, o, _ in index), default=len(raw))
    return raw[:24], index, raw[24 + 12 * n:first], {k: raw[o:o + b] for k, o, b in index}


def patch_areas(raw, rows):
    """areas.awa with each area of ROWS ({key: rows}) given its effect link section (an earlier one replaced); the
    records stay in their order, the index follows the new offsets. KeyError naming keys the pack has no area of."""
    head, index, between, records = read_areas(raw)
    missing = sorted(set(rows) - set(records))
    if missing:
        raise KeyError('Effect links for areas the pack does not hold: ' + ', '.join('%#x' % k for k in missing))
    at = 24 + 12 * len(index) + len(between)
    out_index, body = [], []
    for key, _, _ in index:
        record = records[key]
        if record[-4:] == MAGIC:
            record = record[:struct.unpack_from('<I', record, len(record) - 8)[0]]
        if rows.get(key):
            record += section(rows[key]) + struct.pack('<I', len(record)) + MAGIC
        out_index.append(struct.pack('<III', key, at, len(record)))
        body.append(record)
        at += len(record)
    return head + b''.join(out_index) + between + b''.join(body)


def stage(id1, data_files, world, out=None):
    """The image step's part, after the frame maps and the night lamp table: every exterior cell's effect links into
    its own record of id1/areas.awa; the receipt (OUT/effect-links.json when OUT is given)."""
    import hashlib
    import json
    import time
    t0 = time.time()
    id1 = Path(id1)
    print('=== effect links: what a taken carriable light takes with it (TAKEN-LIGHT-FLAME-61) ===', flush=True)
    lights = carriable_lights(data_files)
    rows = area_rows(id1, world, lights)
    sizes = sorted(16 + ROW.size * len(v) for v in rows.values())
    receipt = {'carriable_light_placements': len(lights), 'outdoors': len(outdoor(lights)), 'areas': len(rows),
               'rows': {chr(k): sum(1 for v in rows.values() for r in v if r[0] == k)
                        for k in (KIND_PLACE, KIND_FLAME, KIND_LAMP)},
               'section_bytes_median': sizes[len(sizes) // 2] if sizes else 0,
               'section_bytes_largest': sizes[-1] if sizes else 0, 'section_bytes': sum(sizes)}
    path = id1 / AREAS
    if rows:
        if not path.is_file():
            raise ValueError('Effect links for %d exterior cells but the image has no %s' % (len(rows), AREAS))
        raw = patch_areas(path.read_bytes(), rows)
        path.write_bytes(raw)
        receipt['areas_sha256'] = hashlib.sha256(raw).hexdigest()
    # the rule kept: every flame, lamp row and placement of a carriable light outdoors (and in the rooms) linked
    receipt['check'] = check(id1, lights, world, links=rows)
    receipt['seconds'] = round(time.time() - t0, 1)
    print('[effect-links] %d carriable light placements (%d outdoors); %d exterior cells, rows %s; section median %d '
          'bytes, largest %d; %.1f s' % (len(lights), receipt['outdoors'], len(rows), receipt['rows'],
                                       receipt['section_bytes_median'], receipt['section_bytes_largest'],
                                       receipt['seconds']), flush=True)
    if out is not None:
        (Path(out) / 'effect-links.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8',
                                                     newline='\n')
    return receipt


# ---------------------------------------------------------------- the build check: the universal rule

def image_links(id1):
    """{area key: [(kind, aux, key, reference)]} of the effect link sections in id1/areas.awa."""
    path = Path(id1) / AREAS
    if not path.is_file():
        return {}
    return {k: v for k, v in ((k, read_section(r)) for k, r in read_areas(path.read_bytes())[3].items()) if v}


def check(id1, lights, world=None, limit=20, links=None):
    """Refuse (ValueError naming the misses) an image where a carriable light that gives light has an effect with no
    link to its reference: a flame of its placement in a room map without aw_ref; outdoors (WORLD: the CHIM world) a
    frame map flame, a lamp row or a CHIM placement missing from its cell's effect links (LINKS: {area key: rows},
    else read from id1/areas.awa). Returns the receipt (counts per path)."""
    from chim.flames import FLAME_CLASS, REF_KEY
    from chim.interior import installed_room_refs
    from prepare_area_tables import name_hash
    id1 = Path(id1)
    links = image_links(id1) if links is None else links
    have = {(k, aux, key, ref) for v in links.values() for k, aux, key, ref in v}
    flame_refs = {r for r, light in lights.items() if light['flames']}
    misses, counts = [], collections.Counter()
    from map_files import map_files
    for p in map_files(id1 / 'maps'):
        rows = map_entities(p)
        world_row = rows[0] if rows else {}
        if '_chim_frame' in world_row and '_chim_room' not in world_row:
            continue                                  # exterior frame maps: below, from the CHIM world
        flames = [e for e in rows if e.get('classname') == FLAME_CLASS]
        drawn = {int(e['aw_ref']) for e in rows if e.get('aw_ref', '').isdigit() and e.get('classname') != FLAME_CLASS}
        if '_chim_room' in world_row:
            drawn |= installed_room_refs(p)
        want = drawn & flame_refs
        if not want:
            continue
        tied = {int(e[REF_KEY]) for e in flames if e.get(REF_KEY, '').isdigit()}
        counts['room maps with carriable lights'] += 1
        counts['room placements'] += len(want)
        missing = sorted(want - tied)
        if missing and len(flames) >= FLAME_CAP:
            counts['room placements past the flame cap (no flame drawn)'] += len(missing)
            continue
        counts['room placements tied'] += len(want) - len(missing)
        misses += ['%s: the flame of reference %d (%s) names no placement' % (p.name, r, lights[r]['id'])
                   for r in missing]
    if world is not None:
        for pid, ref in place_links(world, lights):
            counts['exterior placements'] += 1
            if (KIND_PLACE, 0, pid, ref) not in have:
                misses.append('CHIM placement %d of reference %d (%s) has no effect link in its cell, so it cannot be '
                              'taken' % (pid, ref, lights[ref]['id']))
        maps = frame_maps(id1)
        for stem, rows in maps:
            for ordinal, ref in frame_flame_links(rows, world, lights):
                counts['exterior frame map flames'] += 1
                if (KIND_FLAME, ordinal, name_hash(stem), ref) not in have:
                    misses.append('%s.chim: flame row %d of reference %d (%s) has no effect link in its cell'
                                  % (stem, ordinal, ref, lights[ref]['id']))
        # TAKEN-LIGHT-OUTDOOR-EFFECTS-UNLINKED-61: a flame link is matched by the engine against the loaded frame map
        # file's stem (aw_inventory.c AW_AreaMapHash); a link naming no frame map of the image is never applied
        stems = {name_hash(stem) for stem, _ in maps}
        for k, aux, key, ref in sorted(have):
            if k == KIND_FLAME and key not in stems:
                misses.append('flame link %d of reference %d names map hash %#x, which is no frame map of the image'
                              % (aux, ref, key))
    if (id1 / LAMPS).is_file():
        for row, ref in lamp_links(lamp_rows((id1 / LAMPS).read_bytes()), lights):
            counts['lamp rows'] += 1
            if (KIND_LAMP, 0, row, ref) not in have:
                misses.append('%s row %d of reference %d (%s) has no effect link in its cell'
                              % (LAMPS, row, ref, lights[ref]['id']))
    if misses:
        raise ValueError('Effects of carriable lights not tied to their item (TAKEN-LIGHT-FLAME-61): %d\n  %s%s' % (
            len(misses), '\n  '.join(misses[:limit]), '\n  ...' if len(misses) > limit else ''))
    return dict(counts, rule='a can-carry LIGH that gives light: every flame, lamp row and exterior placement linked',
                carriable_light_placements=len(lights))


def check_image(id1, data_files, out=None, world=None):
    """The image step's check after the engine map limits; its receipt into OUT/effect-links-check.json."""
    import json
    receipt = check(id1, carriable_lights(data_files), world)
    print('[effect-links] check passed: %s' % ', '.join('%s %s' % (k, v) for k, v in sorted(receipt.items())
                                                       if isinstance(v, int)), flush=True)
    if out is not None:
        (Path(out) / 'effect-links-check.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8',
                                                           newline='\n')
    return receipt
