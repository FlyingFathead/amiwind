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
it lists the carriable lights and, since OUTDOOR-DISABLE-NOT-HIDDEN-68, every outdoor placement a script of the masters
can Disable or Enable (scripted_placements: the strongholds' building stages, the colony's, Mournhold's trees), in
the base world and in every store of frames the image installs (Solstheim's, Mournhold's districts at their presented
cells: placed_outdoors).

check() is the build's keeper of the rule: it refuses an image where a carriable light's flame in any map, its night
lamp row or its exterior placement, or a scripted placement's exterior piece, has no link to its reference (a flame
cut by a map's flame cap is not drawn at all and is only counted); a scripted target with no CHIM piece and no entity
of a frame map is named in the receipt (a finding: nothing hides it).
"""
import collections
import re
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
# CHIM-GONE-LIST-64-CAP-68: the engine hides every piece a reference's 'P' rows name (aw_inventory.c
# AW_AreaEffectHide, a bit per placement of the loaded frame in chim/chim_chunks.c): no limit per reference any more
# (16 pieces before, refused here)


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


# OUTDOOR-DISABLE-NOT-HIDDEN-68: a script's Disable / Enable (OpenMW apps/openmw/mwscript/miscextensions.cpp OpEnable,
# OpDisable: the reference the line names by id->, else the script's own object), as the masters write it
SCRIPT_TOGGLE = re.compile(r'(?i)(?:("?)([^"\s,;>\-][^"\->]*?)\1\s*->\s*)?\b(disable|enable)\b(?!\w)')
ACTOR_TAGS = ('NPC_', 'CREA', 'LEVC')     # an actor has an edict: its Disable hides the edict (aw_mwhost.c object_hide)


def script_targets(raws):
    """(ids, scripts, kinds, scripted): the folded ids a script line or a dialogue result switches by "X->Disable" /
    "X->Enable", the folded names of the scripts with a bare Disable or Enable (their own objects), {folded id: record
    tag} of every record and {folded id: folded script} of every record that names a script, a later master's record
    winning; from the masters RAWS ({master: bytes}) in load order."""
    from mwad.audit import records, string, subrecords
    ids, scripts, kinds, scripted = set(), set(), {}, {}

    def read(text, script):
        for line in (text or '').splitlines():
            for m in SCRIPT_TOGGLE.finditer(line.split(';', 1)[0]):
                if m.group(2):
                    ids.add(m.group(2).strip().casefold())
                elif script:
                    scripts.add(script)
    for m in MASTERS:
        if m not in raws:
            continue
        for tag, flags, payload in records(raws[m]):
            if flags & 0x20:
                continue
            if tag == 'SCPT':
                s = dict(subrecords(payload))
                head = s.get('SCHD', b'')
                read(string(s.get('SCTX', b''), errors='replace'), string(head[:32], errors='replace').casefold())
            elif tag == 'INFO':
                for t, d in subrecords(payload):
                    if t == 'BNAM':
                        read(string(d, errors='replace'), None)
            elif tag not in ('CELL', 'LAND', 'PGRD', 'DIAL', 'TES3'):
                s = {}
                for t, d in subrecords(payload):
                    s.setdefault(t, d)                    # the record's own NAME and SCRI, its first of each
                if 'NAME' not in s:
                    continue
                ident = string(s['NAME'], errors='replace').casefold()
                kinds[ident] = tag
                if 'SCRI' in s:
                    scripted[ident] = string(s['SCRI'], errors='replace').casefold()
                else:
                    scripted.pop(ident, None)
    return ids, scripts, kinds, scripted


def scripted_placements(data_files):
    """{stable reference: {'id', 'master', 'interior', 'cell', 'position', 'flames'}} of every placement a script of
    the masters can Disable or Enable (script_targets: every placement of an id a line names, every placement of a
    record whose script has a bare Disable or Enable), actors left out (their edicts are hidden), read as
    carriable_lights reads its placements (the same keys). OUTDOOR-DISABLE-NOT-HIDDEN-68."""
    from mwad.paths import child_ci
    from prepare_focus import cells_of
    from ref_identity import stable_ref
    data = Path(data_files)
    raws = {m: p.read_bytes() for m, p in ((m, child_ci(data, m, required=False)) for m in MASTERS) if p is not None}
    ids, scripts, kinds, scripted = script_targets(raws)
    out = {}
    for m in MASTERS:
        for cell, interior, grid, _, refs in cells_of(raws[m]) if m in raws else ():
            for ref in refs:
                if 'DELE' in ref or 'NAME' not in ref or len(ref.get('DATA', b'')) != 24:
                    continue
                ident = ref['NAME'].split(b'\0')[0].decode('cp1252', 'replace').casefold()
                if kinds.get(ident) in ACTOR_TAGS or (ident not in ids and scripted.get(ident) not in scripts):
                    continue
                out[stable_ref(m, ref['number'])] = {
                    'id': ident, 'master': m, 'interior': interior, 'cell': cell if interior else tuple(grid),
                    'position': struct.unpack_from('<3f', ref['DATA']), 'flames': False}
    return out


def outdoor(lights):
    return {r: light for r, light in lights.items() if not light['interior']}


def placed_outdoors(entries, places=None):
    """ENTRIES ({reference: entry}) that stand outdoors in AmiWind: an exterior cell's as they are, a presented
    district's (MOURNHOLD-EXTERIOR-CELLS-66; PLACES: presented_exterior.build_places) at the cell of its presented
    block (present_position, the move the presented master gave it); every other room's left out."""
    out = {}
    for r, e in entries.items():
        if not e['interior']:
            out[r] = e
        elif places:
            from presented_exterior import is_presented, present_position
            if is_presented(places, e['cell']):
                grid, _ = present_position(places, e['cell'], e['position'])
                out[r] = dict(e, interior=False, cell=(int(grid[0]), int(grid[1])))
    return out


def hideable(lights, scripted=None, places=None):
    """{reference: entry} of every outdoor placement a 'P' row hides: the carriable lights and the scripted ones."""
    both = dict(scripted or {})
    both.update(lights)
    return placed_outdoors(both, places)


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


def placement_ref(number):
    """The stable reference id (tools/ref_identity.py) of a CHIM placement's source reference NUMBER (chim.cut
    source_ref). A store of frames (Solstheim's, Mournhold's districts) numbers an expansion's reference as the merged
    master does, master index x 2**22 + its own number; the scripted placements and the carriable lights are keyed by
    the stable id, master index x 2**20 + the number (REF-IDENTITY-MERGED-MASTER-66, as chim/chim_room.c RoomRefIs
    reads both). The base game's numbers are both forms. Before, the merged number was compared with the stable id,
    so no piece of an expansion's store of frames ever got a row: a script's Disable of Bloodmoon's ice covers in
    front of Stahlman's Gorge and the Caves of Fjalding left them drawn and solid (EXPANSION-STORE-DISABLE-NOT-HIDDEN-68)."""
    from ref_identity import RefIdentityError, stable_ref
    try:
        return stable_ref('Morrowind.esm', number)
    except RefIdentityError:
        return number


def place_links(world, lights, places=None):
    """[(placement id, reference)] of every CHIM exterior placement (every cut piece) of WORLD that LIGHTS ({reference:
    entry}: carriable lights, scripted placements: hideable) holds outdoors; a placement matched by its stable id
    (placement_ref), the row naming that id."""
    from chim.cut import source_ref
    out_refs = set(placed_outdoors(lights, places))
    out = set()
    for _, _, chunks in world['frames']:
        for c in chunks:
            for r in c['owned']:
                ref = placement_ref(source_ref(r['ref']))
                if ref in out_refs:
                    out.add((r['pid'], ref))
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


def area_rows(id1, world, lights, scripted=None, layers=(), places=None):
    """{area key: sorted [(kind, aux, key, reference)]}: every effect link of the image, in the area (exterior
    cell) of the light it belongs to. 'P' rows (OUTDOOR-DISABLE-NOT-HIDDEN-68): the pieces of the carriable lights
    and of SCRIPTED (scripted_placements) in WORLD and in every world of LAYERS (the stores of frames the image
    installs: Solstheim's, Mournhold's districts at their presented cells, PLACES)."""
    from prepare_area_tables import name_hash
    id1 = Path(id1)
    lit = outdoor(lights)
    hide = hideable(lights, scripted, places)
    rows = collections.defaultdict(set)
    if (id1 / LAMPS).is_file():
        for row, ref in lamp_links(lamp_rows((id1 / LAMPS).read_bytes()), lights):
            rows[area_key(lit[ref])].add((KIND_LAMP, 0, row, ref))
    for w in [world] + list(layers):
        if w is not None:
            for pid, ref in place_links(w, hide):
                rows[area_key(hide[ref])].add((KIND_PLACE, 0, pid, ref))
    if world is not None:
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


def stage(id1, data_files, world, out=None, layers=(), places=None):
    """The image step's part, after the frame maps and the night lamp table: every exterior cell's effect links into
    its own record of id1/areas.awa; the receipt (OUT/effect-links.json when OUT is given). LAYERS: the world folders
    of the stores of frames the image installs (Solstheim's, Mournhold's districts), read here (chim.frame_map.load);
    PLACES: the presented districts (tools/build_aga.py presented_places)."""
    import hashlib
    import json
    import time
    t0 = time.time()
    id1 = Path(id1)
    print('=== effect links: what a taken carriable light or a script\'s Disable takes with it (TAKEN-LIGHT-FLAME-61, '
          'OUTDOOR-DISABLE-NOT-HIDDEN-68) ===', flush=True)
    lights = carriable_lights(data_files)
    scripted = scripted_placements(data_files)
    if layers:
        from chim.frame_map import load
        layers = [load(path) for path in layers]
    rows = area_rows(id1, world, lights, scripted, layers, places)
    sizes = sorted(16 + ROW.size * len(v) for v in rows.values())
    receipt = {'carriable_light_placements': len(lights), 'outdoors': len(outdoor(lights)), 'areas': len(rows),
               'scripted_placements': len(scripted), 'scripted_outdoors': len(placed_outdoors(scripted, places)),
               'layer_worlds': len(layers),
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
    # the rule kept: every flame, lamp row and placement of a carriable light outdoors (and in the rooms) linked, and
    # every exterior piece of a scripted placement
    receipt['check'] = check(id1, lights, world, links=rows, scripted=scripted, layers=layers, places=places)
    receipt['seconds'] = round(time.time() - t0, 1)
    print('[effect-links] %d carriable light placements (%d outdoors), %d scripted (%d outdoors); %d exterior cells, '
          'rows %s; section median %d bytes, largest %d; %d scripted targets with no piece and no entity; %.1f s'
          % (len(lights), receipt['outdoors'], len(scripted), receipt['scripted_outdoors'], len(rows), receipt['rows'],
             receipt['section_bytes_median'], receipt['section_bytes_largest'],
             len(receipt['check'].get('scripted targets with no CHIM piece and no entity', ())), receipt['seconds']),
          flush=True)
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


def check(id1, lights, world=None, limit=20, links=None, scripted=None, layers=(), places=None):
    """Refuse (ValueError naming the misses) an image where a carriable light that gives light has an effect with no
    link to its reference: a flame of its placement in a room map without aw_ref; outdoors (WORLD: the CHIM world) a
    frame map flame, a lamp row or a CHIM placement missing from its cell's effect links (LINKS: {area key: rows},
    else read from id1/areas.awa). OUTDOOR-DISABLE-NOT-HIDDEN-68: every exterior piece of a placement a script can
    Disable or Enable (SCRIPTED, in WORLD and LAYERS) linked too; a scripted target outdoors with no piece in any of
    those worlds and no entity of a frame map (whose edict the Disable hides) is named in the receipt, a finding.
    Returns the receipt (counts per path)."""
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
    hide, reached, unreached = hideable(lights, scripted, places), set(), []
    for w in [world] + list(layers):
        if w is None:
            continue
        for pid, ref in place_links(w, hide):
            counts['exterior placements' if ref in lights else 'scripted exterior placements'] += 1
            reached.add(ref)
            if (KIND_PLACE, 0, pid, ref) not in have:
                misses.append('CHIM placement %d of reference %d (%s) has no effect link in its cell, so it cannot be '
                              '%s' % (pid, ref, hide[ref]['id'], 'taken' if ref in lights else 'switched off'))
    if scripted and (world is not None or layers):
        # a scripted target with no CHIM piece: an entity of a frame map (its edict is hidden), else nothing hides it
        entity_refs = {placement_ref(int(e['aw_ref'])) for _, rows in frame_maps(id1) for e in rows
                       if str(e.get('aw_ref', '')).isdigit()}
        for ref, e in sorted(placed_outdoors(scripted, places).items()):
            if ref in reached:
                continue
            if ref in entity_refs:
                counts['scripted placements drawn as entities (hidden by their edict)'] += 1
            else:
                unreached.append('%d %s %s' % (ref, e['id'], tuple(e['cell']) if not isinstance(e['cell'], str)
                                               else e['cell']))
    if world is not None:
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
        raise ValueError('Effects of carriable lights not tied to their item (TAKEN-LIGHT-FLAME-61), or scripted '
                         'placements not hidden by their switch (OUTDOOR-DISABLE-NOT-HIDDEN-68): %d\n  %s%s' % (
                             len(misses), '\n  '.join(misses[:limit]), '\n  ...' if len(misses) > limit else ''))
    out = dict(counts, rule='a can-carry LIGH that gives light: every flame, lamp row and exterior placement linked; a '
                            'placement a script can Disable or Enable: every exterior piece linked',
               carriable_light_placements=len(lights))
    if scripted:
        out['scripted targets with no CHIM piece and no entity'] = unreached
    return out


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
