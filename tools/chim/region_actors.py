# SPDX-License-Identifier: GPL-3.0-only
"""The actors of the CHIM region frames (EXPERIMENTAL, build option --chim-region-actors on, default off;
CHIM-EXTERIOR-ACTORS-MISSING-46).

Until now only the town frames placed actors (their resident stage, tools/chim_town.py); a region frame map held
the ground, the objects and the player start and no NPC or creature. With this option every exterior NPC and
creature reference of a region frame's cells becomes an actor row of its frame map, the way a town frame carries
its residents: the same aw_npc / aw_corpse rows (the actor library stage's models and base texts,
tools/actor_library.py), the same instance fields, put on the frame's own collision by the frame map's own
height refit (chim.frame_map.refit_height: actor_grounding's contact interval) and checked by the frame map's
contact check (chim.frame_map.contact).

Actors start where the game puts them (the maintainer, 22 October 2026). Every actor is placed at its reference's
position and rotation from the game data, never moved elsewhere:

- an actor whose reference stands within OFF_GROUND units of the ground (or of the water surface under it) gets the
  ordinary ground contact, x and y kept: its height is the contact interval of its soles on the collision under
  it (every sole within -0.5..1.0, nearest the support point), else the support point itself (support + 0.25, the
  engine's own snap); the result is baked (aw_ground_baked) and each sole's gap recorded. The towns' sideways
  search (actor_grounding's offsets, up to 48 units) is not used: it would move the actor off its authored spot;
- an actor authored well above the ground or the water under it (more than OFF_GROUND, which is also the bound of
  the engine's own runtime floor snap, aw_scene.c AW_NPCFloor) keeps its authored spot with aw_ground_mode 1, so
  neither the builder nor the engine snaps it; it is listed as "authored off the ground" with its height and its
  script (the base record's SCRI) when it has one: the falling wizard near Seyda Neen is the known example, his
  script makes him fall. A swimming creature authored in the water well above the sea floor is listed the same way;
- an actor the grounding policy classifies as not standing (config/actor_grounding.json: scripted airborne,
  flying, levitating, swimming, authored dead) keeps its authored spot as in the towns.

Levelled creature references (LEVC) are not placed in a frame map: the game rolls the list at the player's level
when the cell loads, and a frame map row carries one fixed creature, so a pick made by the builder would fix a level
the game decides at run time (the interiors' rule, tools/creature_residents.py: no invented roll). They are listed
per frame as deferred with that reason; the actor table (tools/chim/actors.py, version 2) rolls them when a cell
joins the type 1 window. A reference without a model in the actor library, one a town frame places, and one the
start scripts hold out of a new game (--start-disabled original) is listed with its reason too: nothing is dropped
silently.

Memory: actor models go to Quake's Cache, not the CHIM zone (chim.heap.actor_cache). Each frame's record says how
many bytes its actors' standing models take and whether they fit the Cache room of the 16 MB baseline (the built
heap: the Hunk gap, chim_reserve_kib) and of the largest heap the engine takes on its own with more RAM
(AW_HEAP_AUTO_MAX_MB); past the room the engine evicts least recently used models (slower, not fatal), so a frame
over it is reported, not refused. A frame map must also fit the engine's per-map tables (edicts, model and sound
precaches: tools/map_engine_limits.py): actors past them are left out with that reason, farthest from the frame
centre first, and the frame is reported.

Units: one per region frame with actors, on the shared worker pool (chim.frame_map.build_regions), each keyed by
the SHA-256 of what it reads (its frame's collision, its references, the base texts and model files it uses) in the
pass cache 'chim-region-actors'. A frame without actors has no unit and its frame map is the same bytes as without
the option.
"""
import collections
import hashlib
import json
import math
import os
import struct
from pathlib import Path

SETTING = 'chim_region_actors'
MODES = ('off', 'on')
DEFAULT = 'off'
ENV = 'AMIWIND_CHIM_REGION_ACTORS'
CACHE = 'chim-region-actors'
FORMAT = 'AmiWind CHIM region actors 1'
LOCAL = 0.25                     # Quake units per Morrowind unit
CELL_UNITS = 8192.0              # Morrowind units per exterior cell
WATER_LEVEL = 0.0                # the exterior water surface, Morrowind units
OFF_GROUND = 32.0                # local units: an actor farther than this above its support keeps its authored spot
ACTOR_TYPES = ('NPC_', 'CREA')
DEFERRED_REASON = ('levelled creature list: the game rolls it at the player\'s level when the cell loads; a frame '
                   'map row holds one fixed creature, so the builder does not pick one (no invented roll); the actor '
                   'table rolls it when the cell joins the type 1 window')
NO_MODEL_REASON = 'no model in the actor library stage (its left-out list names why)'
TOWN_REASON = 'placed by a town frame (its resident stage)'


def mode(value=None):
    """'on' or 'off' (an explicit VALUE wins over the environment, AMIWIND_CHIM_REGION_ACTORS)."""
    if value is None:
        value = os.environ.get(ENV, '').strip() or DEFAULT
    if value not in MODES:
        raise ValueError('%s takes %s, not %r' % (ENV, ' or '.join(MODES), value))
    return value


def export_mode(value):
    os.environ[ENV] = mode(value)


# ---------------------------------------------------------------- the game data

def census(master):
    """Every non-deleted NPC_, CREA and LEVC reference placed in an exterior cell of the master's bytes (the census
    rule of chim.actors.exterior_actors), as dicts: number, id, type, cell [x, y], position (Morrowind units),
    rotation (radians), scale, script (the base record's SCRI, '' without one) and region (the cell's RGNN)."""
    from mwad.audit import cell_data, records, string, subrecords
    types, scripts, cells = {}, {}, []
    for tag, flags, payload in records(master):
        if flags & 0x20:
            continue
        if tag == 'CELL':
            cells.append(cell_data(list(subrecords(payload))))
        elif tag in ('NPC_', 'CREA', 'LEVC'):
            fields = dict(subrecords(payload))
            if 'NAME' in fields and 'DELE' not in fields:
                ident = string(fields['NAME'], errors='replace').casefold()
                types[ident] = tag
                if 'SCRI' in fields:
                    scripts[ident] = string(fields['SCRI'], errors='replace')
    out = []
    for cell in cells:
        if cell['flags'] & 1:
            continue
        for ref in cell['refs']:
            key = ref.get('id', '').casefold()
            tag = types.get(key)
            if ref.get('deleted') or tag is None or 'position' not in ref:
                continue
            out.append({'number': ref['number'], 'id': ref['id'], 'type': tag, 'cell': [cell['x'], cell['y']],
                        'position': [float(v) for v in ref['position']],
                        'rotation': [float(v) for v in ref.get('rotation_radians', (0.0, 0.0, 0.0))],
                        'scale': float(ref.get('scale', 1.0)), 'script': scripts.get(key, ''),
                        'region': cell.get('region') or ''})
    return out


def census_file(master_path):
    """census of a master file (a picklable call for a Background worker)."""
    return census(Path(master_path).read_bytes())


def by_cell(refs):
    """{(x, y): [refs]} in reference number order."""
    out = collections.defaultdict(list)
    for r in sorted(refs, key=lambda r: r['number']):
        out[tuple(r['cell'])].append(r)
    return dict(out)


def library_texts(library):
    """{record id (lower case): base entity text} of an actor library stage's manifests (tools/actor_library.py),
    read without installing anything; {} when the stage is missing."""
    import creature_library as L
    import npc_library as NL
    library = Path(library)
    out = {}
    if (library / 'creature-library.json').is_file():
        out.update(L.base_texts(library / 'creature-library.json'))
    if (library / 'npc-library.json').is_file():
        out.update(NL.base_texts(library / 'npc-library.json'))
    return {k.casefold(): v for k, v in out.items() if '@' not in k}


def plan_frame(frame, refs, texts, town_refs=(), held=None):
    """(place, deferred, left_out) of one region frame: its cells' references split by what happens to them.
    place: NPC and creature references with a library text ([ref, text]); deferred: levelled references with the
    reason; left_out: the others with theirs. held: {reference number: reason} of the start scripts (mode
    original); town_refs: reference numbers a town frame places."""
    held = held or {}
    town_refs = set(town_refs)
    place, deferred, left = [], [], []
    for cell in frame.get('cells') or [frame['cell']]:
        for r in refs.get(tuple(cell), ()):
            row = {'reference': r['number'], 'id': r['id'], 'type': r['type']}
            if r['number'] in town_refs:
                left.append(dict(row, reason=TOWN_REASON))
            elif r['number'] in held:
                left.append(dict(row, reason=held[r['number']]))
            elif r['type'] == 'LEVC':
                deferred.append(dict(row, reason=DEFERRED_REASON))
            elif r['id'].casefold() not in texts:
                left.append(dict(row, reason=NO_MODEL_REASON))
            else:
                place.append([r, texts[r['id'].casefold()]])
    return place, deferred, left


# ---------------------------------------------------------------- rows

def parse_text(text):
    import re
    return dict(re.findall(r'"([^"\n]*)"\s+"([^"\n]*)"', text))


def authored_point(ref, frame):
    """The reference's position in the frame's local units ((Morrowind - frame centre) x 0.25, z less the frame
    origin's), as the frame's door bank and its placements are."""
    origin = frame['origin']
    return tuple(round(ref['position'][k] * LOCAL - origin[k], 5) for k in range(3))


def yaw_degrees(ref):
    """The Quake yaw of a reference's z rotation (the resident rule, import_town.resident_entities)."""
    return -math.degrees(ref['rotation'][2])


def actor_row(ref, text, frame):
    """The frame map row of one placed reference: the library's base text, then the instance fields (aw_ref,
    origin at the authored spot, angles, and aw_scale for a scaled reference: the engine draws a live actor at it)."""
    row = parse_text(text)
    point = authored_point(ref, frame)
    row['aw_ref'] = str(ref['number'])
    row['origin'] = '%.5f %.5f %.5f' % point
    row['angles'] = '0 %.5f 0' % yaw_degrees(ref)
    if abs(ref['scale'] - 1.0) > 1e-5:
        row['aw_scale'] = '%.4f' % ref['scale']
    return row


# ---------------------------------------------------------------- the unit

def support(scene, point, bottom, water):
    """(ground height or None, in water, height above the support or None): the first collision under the point on
    the frame's point hull, and the water surface when the ground under it is lower."""
    from chim.frame_map import ground_trace
    ground = ground_trace(scene, point[:2], point[2] + 8.0, bottom)
    if ground is None:
        return None, False, None
    if ground < water:
        if point[2] < water:
            return ground, True, point[2] - ground          # in the water: what counts is the sea floor
        return ground, False, point[2] - water              # over the water: the surface counts
    return ground, False, point[2] - ground


def soles(library_id1, e, angles, models):
    """The actor's sole samples at its yaw and instance scale, as the frame map's contact check reads them
    (check_actor_ground: the lowest rendered vertices of the initial idle poses); () without the model file."""
    from check_actor_ground import contact_samples, layout_of, named_model_frames
    path = Path(library_id1) / e.get('model', '')
    if not e.get('model') or not path.is_file():
        return ()
    if e['model'] not in models:
        models[e['model']] = (named_model_frames(path.read_bytes(), e['model']), layout_of(path))
    frames, layout = models[e['model']]
    scale = float(e.get('aw_scale', 1.0))
    return tuple(tuple(v * scale for v in s) for s in contact_samples(frames, angles, False, layout))


def frame_actors(task):
    """Pool worker: (rows, record) of one region frame's actors on its own collision. task: 'frame' (the region
    table row), 'subworld' (chim.frame_map.frame_subworld of its frame), 'place' ([[ref, text]]), 'library_id1'
    (the actor library's id1: the models' soles), 'deferred', 'left_out'."""
    from chim.collision import FrameScene
    from chim.frame_map import FLOOR_MARGIN, contact, refit_height
    from actor_grounding import initial_state
    frame = task['frame']
    world = task['subworld']
    scene = FrameScene(world, 0, hull=0)
    bottom = min(c['zmin'] for c in world['frames'][0][2]) - FLOOR_MARGIN
    water = WATER_LEVEL * LOCAL - frame['origin'][2]
    models = {}
    rows, placed = [], []
    for ref, text in task['place']:
        e = actor_row(ref, text, frame)
        authored = [float(v) for v in e['origin'].split()]
        angles = tuple(float(v) for v in e['angles'].split())
        ground, wet, height = support(scene, authored, bottom, water)
        status = {'reference': ref['number'], 'id': ref['id'], 'type': ref['type'], 'region': ref['region'],
                  'authored': authored, 'height_above_support': None if height is None else round(height, 3),
                  'in_water': wet, **({'script': ref['script']} if ref['script'] else {})}
        policy = None
        try:
            policy = initial_state(ref['id'])
        except (ValueError, KeyError):
            policy = None                    # not classified: decided by its authored height below
        e['aw_authored_origin'] = e['origin']
        e['aw_authored_z'] = '%.5f' % authored[2]
        if e.get('classname') == 'aw_corpse' or (policy not in (None, 'ground')) or \
                (policy is None and e.get('aw_ground_mode') == '1'):
            e['aw_ground_mode'] = '1'
            status['status'] = 'policy: ' + (policy or ('authored dead' if e.get('classname') == 'aw_corpse'
                                                        else 'not standing'))
        elif height is None or height > OFF_GROUND or height < -OFF_GROUND:
            # authored off the ground (or in the water well above the sea floor, or under the ground): the
            # authored spot stays, neither the builder nor the engine (AW_NPCFloor) snaps it
            e['aw_ground_mode'] = '1'
            status['status'] = ('authored in the water' if wet else 'authored under the ground'
                                if height is not None and height < 0 else 'authored off the ground')
        else:
            # the ordinary ground contact, x and y kept (no relocation): the towns' contact interval on the frame
            # (chim.frame_map.refit_height: every sole within -0.5..1.0 of the collision under it, the height
            # nearest the support point), else the support point itself (the engine's own snap: support + 0.25)
            e['aw_ground_mode'] = '0'
            samples = soles(task['library_id1'], e, angles, models)
            base = (authored[0], authored[1], round(ground + 0.25, 5))
            z = refit_height(scene, base, samples) if samples else None
            placed_at = (authored[0], authored[1], round(base[2] if z is None else z, 5))
            text3 = '%.5f %.5f %.5f' % placed_at
            e['origin'] = text3
            e['aw_ground_valid'] = '1'
            e['aw_ground_baked'] = text3
            gaps, failures = contact(scene, placed_at, samples) if samples else ([], [{'support': 'no model soles'}])
            status.update(status='grounded' if not failures else 'grounded at the reference, soles not all in contact',
                          dz=round(placed_at[2] - authored[2], 3),
                          minimum_gap=round(min(gaps), 3) if gaps else None,
                          maximum_gap=round(max(gaps), 3) if gaps else None)
            if failures:
                status['failures'] = failures[:4]
        rows.append(e)
        placed.append(status)
    by = collections.Counter(p['status'] for p in placed)
    record = {'format': FORMAT, 'frame': frame['id'], 'cells': [list(c) for c in frame.get('cells') or [frame['cell']]],
              'placed': len(rows), 'by_type': dict(collections.Counter(r['type'] for r, _ in task['place'])),
              'by_status': dict(sorted(by.items())), 'actors': placed,
              'deferred': list(task.get('deferred', [])), 'left_out': list(task.get('left_out', [])),
              'off_ground_limit': OFF_GROUND}
    return rows, record


def _canonical(value, h):
    """Feed a CHIM world part (dicts, lists, bytes, numbers, numpy arrays) into hash h in one fixed form."""
    if isinstance(value, dict):
        h.update(b'{')
        for k in sorted(value, key=str):
            h.update(repr(str(k)).encode())
            _canonical(value[k], h)
        h.update(b'}')
    elif isinstance(value, (list, tuple)):
        h.update(b'[%d' % len(value))
        for v in value:
            _canonical(v, h)
        h.update(b']')
    elif isinstance(value, (bytes, bytearray, memoryview)):
        raw = bytes(value)
        h.update(b'b%d:' % len(raw) + raw)
    elif value is None or isinstance(value, (bool, int, float, str)):
        h.update(repr(value).encode())
    elif hasattr(value, 'tobytes') and hasattr(value, 'dtype'):
        h.update(('a%s%s:' % (value.dtype.str, tuple(value.shape))).encode() + value.tobytes())
    else:
        h.update(repr(value).encode())


def world_digest(subworld):
    """SHA-256 of a frame's subworld (what FrameScene reads: the frame's chunks and its placements' models)."""
    h = hashlib.sha256()
    _canonical({'frames': subworld['frames'], 'models': subworld['models']}, h)
    return h.hexdigest()


def unit_inputs(task):
    """SHA-256 of everything frame_actors reads: the frame row, its collision, its references with their base texts,
    the model files those texts name (and their layouts), the grounding policy, the deferred and left-out rows."""
    from pass_cache import input_digest
    lib = Path(task['library_id1'])
    models = {}
    for _, text in task['place']:
        model = parse_text(text).get('model', '')
        for path in (model, model[:-4] + '.anm') if model.endswith('.mdl') else ():
            if path not in models:
                models[path] = (hashlib.sha256((lib / path).read_bytes()).hexdigest()
                                if (lib / path).is_file() else None)
    policy = Path(__file__).resolve().parents[2] / 'config/actor_grounding.json'
    return input_digest({'format': FORMAT, 'frame': task['frame'], 'world': task.get('world_sha256')
                         or world_digest(task['subworld']), 'place': task['place'], 'models': models,
                         'policy': hashlib.sha256(policy.read_bytes()).hexdigest(),
                         'deferred': task.get('deferred', []), 'left_out': task.get('left_out', [])})


def cache():
    """The region actors' share of the image pass cache (tools/pass_cache.py), keyed by the code frame_actors
    reaches; None when the cache is off."""
    from pass_cache import PassCache
    return PassCache.open(CACHE, {}, (__file__, 'frame_actors'))


def unit(task):
    """(rows, record, reused) of one frame: from the pass cache when unit_inputs is unchanged, else frame_actors."""
    store = task.get('actor_cache')
    key = unit_inputs(task) if store is not None else None
    if store is not None:
        found = store.load(key)
        if found is not None and isinstance(found[0], dict) and found[0].get('format') == FORMAT:
            return found[0]['rows'], found[0]['record'], True
    rows, record = frame_actors(task)
    if store is not None:
        store.store(key, json.loads(json.dumps({'format': FORMAT, 'rows': rows, 'record': record})))
    return rows, record, False


# ---------------------------------------------------------------- the frame map

def overlay(data, rows):
    """A frame map's bytes with ROWS added after its entities (the entity lump only; every other lump the same)."""
    from chim import format as F
    from chim.frame_map import entities, entity_text
    lumps = [bytes(v) for v in F.read_brush_image(data)]
    lumps[0] = entity_text(entities(data) + [dict(r) for r in rows])
    return F.brush_image(lumps)[0]


def table_limits(data, rows, library_id1, name='region frame'):
    """(rows kept, rows left out with the reason, counts): ROWS within the engine's per-map tables for the frame map
    DATA (tools/map_engine_limits.check, with the library's layouts and item tags); the farthest from the frame
    centre leave first."""
    from map_engine_limits import check
    order = sorted(range(len(rows)), key=lambda i: (-math.hypot(*[float(v) for v in rows[i]['origin'].split()[:2]]),
                                                     rows[i]['aw_ref']))
    kept = list(rows)
    left = []
    while True:
        refused, counts = check(overlay(data, kept), name, scenery=False, id1=library_id1)
        if not refused or not kept:
            return kept, left, dict(counts, refused=refused)
        drop = next(i for i in order if rows[i] in kept)
        kept.remove(rows[drop])
        left.append({'reference': int(rows[drop]['aw_ref']), 'id': rows[drop].get('aw_source_id', ''),
                     'reason': 'over the engine\'s per-map tables: ' + refused[0]})


def memory(data, rows, library_id1, hunk_header=None, heap_mb=None):
    """The Cache bytes of a frame map's actors (chim.heap.actor_cache's rule: each distinct standing model once,
    a 16-byte aligned block with its Hunk header, plus the two largest mover models) and the Cache room the map
    leaves: at the built heap (the 16 MB baseline: the Hunk gap) and at the largest heap the engine takes with more
    RAM (AW_HEAP_AUTO_MAX_MB). hunk_header: the target's Hunk block header (chim.heap sizes['hunk']; 16 when not
    probed)."""
    from engine_limits import MEASURED_HUNK, chim_memory, define, whole_map_zone
    from chim.frame_map import HUNK_KEY, entities
    from chim.heap import MOVERS_AT_ONCE
    header = 16 if hunk_header is None else hunk_header
    lib = Path(library_id1)

    def block(n):
        return (n + header + 15) & ~15
    models = sorted({r['model'] for r in rows if r.get('model') and (lib / r['model']).is_file()})
    standing = sum(block((lib / m).stat().st_size) for m in models)
    movers = sorted((block((lib / (m[:-4] + '_m.mdl')).stat().st_size) for m in models
                     if (lib / (m[:-4] + '_m.mdl')).is_file()), reverse=True)
    peak = standing + sum(movers[:MOVERS_AT_ONCE])
    after = int(entities(data)[0].get(HUNK_KEY, MEASURED_HUNK['client_per_map_bytes']))
    before = MEASURED_HUNK['before_map_bytes'] + block(len(data))
    out = {'actor_models': len(models), 'standing_bytes': standing, 'mover_bytes_at_once': sum(movers[:MOVERS_AT_ONCE]),
           'peak_bytes': peak}
    for label, mb in (('baseline', heap_mb), ('more_ram', define('aw_heapsize.h', 'AW_HEAP_AUTO_MAX_MB'))):
        m = chim_memory(heap_mb=mb)
        zone = min(m['zone_kib'] * 1024, whole_map_zone(before, after, m))
        room = max(0, m['hunk_bytes'] - before - zone - after - 64)
        out[label] = {'heap_mb': m['heap_mb'], 'cache_room_bytes': room, 'fits': peak <= room,
                      'over_bytes': max(0, peak - room)}
    return out


def apply(data, rows, record, library_id1, name, hunk_header=None, heap_mb=None):
    """(frame map bytes, record) of a region frame map with its actors: the rows that fit the engine's tables
    (table_limits), the memory record, and the frame's budget status."""
    kept, left, counts = table_limits(data, rows, library_id1, name)
    out = overlay(data, kept) if kept else data
    record = dict(record, placed=len(kept), left_out=list(record.get('left_out', [])) + left,
                  engine_tables={k: counts[k] for k in ('edicts_peak', 'models', 'sounds')},
                  memory=memory(out, kept, library_id1, hunk_header, heap_mb))
    over = [label for label in ('baseline', 'more_ram') if not record['memory'][label]['fits']]
    record['over_budget'] = over + (['engine tables'] if left else [])
    return out, record


def summary(records):
    """Island-wide counts of the region frames' actor records."""
    placed = collections.Counter()
    by_region = collections.defaultdict(collections.Counter)
    statuses = collections.Counter()
    off = []
    deferred = collections.Counter()
    left = collections.Counter()
    over = {'baseline': [], 'more_ram': [], 'engine tables': []}
    for rec in records:
        for a in rec['actors']:
            if any(a['reference'] == x['reference'] for x in rec['left_out']):
                continue
            placed[a['type']] += 1
            by_region[a['region'] or '(no region)'][a['type']] += 1
            statuses[a['status']] += 1
            if a['status'].startswith('authored') or (a['status'].startswith('policy') and
                                                      (a['height_above_support'] or 0) > OFF_GROUND):
                off.append({k: a.get(k) for k in ('reference', 'id', 'status', 'height_above_support', 'script')}
                           | {'frame': rec['frame']})
        for d in rec['deferred']:
            deferred[d['type']] += 1
        for x in rec['left_out']:
            left[x['reason'].split(':')[0]] += 1
        for label in rec.get('over_budget', ()):
            over[label].append({'frame': rec['frame'], **({'over_bytes': rec['memory'][label]['over_bytes'],
                                                           'peak_bytes': rec['memory']['peak_bytes']}
                                                          if label in rec.get('memory', {}) else {})})
    return {'frames_with_actors': len(records), 'placed': dict(placed), 'placed_total': sum(placed.values()),
            'by_region': {k: dict(v) for k, v in sorted(by_region.items())}, 'by_status': dict(sorted(statuses.items())),
            'off_the_ground': len(off), 'off_the_ground_with_script': [o for o in off if o.get('script')],
            'off_the_ground_rows': off, 'deferred': dict(deferred), 'left_out': dict(left), 'over_budget': over}
