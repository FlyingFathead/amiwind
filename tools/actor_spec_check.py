#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The actor spec check (BUILD-ACTOR-SPEC-CHECK-66, docs/ACTOR_RECORDS.md "The build's actor spec check"): a build
verdict that stops a build whose people and creatures are fewer than the original's or out of spec.

Part 1, placement, per area kind and actor kind, the original counted from the game data (the cells of the merged
master of the selected masters, mwad.masters: every NPC_, CREA and LEVC reference, deleted references left out)
against what the build places, both sides from the same master and its reference numbers (like for like):

  interior          the references the image's maps place (image/entity-tracker.json placed_refs, the rooms' cells),
                    each under its own record's kind (a levelled point is a LEVC reference, of any master)
  exterior-region   the region frames' cells (tools/chim/actor_census_check.py: the actor table joins there)
  exterior-town     the town maps' cells (actor_census_check: the town stages place the NPCs, the engine's town
                    join the creatures and levelled points)
  water             the exterior references of swim-only creatures (CREA FLAG swims, neither walks nor flies) and of
                    levelled lists that give only such creatures (a subset of the two exterior kinds)

An exterior row counts as placed only when the engine can spawn it (engine_places, OUTDOOR-CREATURES-REGRESSION-66):
a person or creature with a model in this build, a levelled point whose list can give such a creature, with the
actor table and the creatures switched on by the image's own default-game.cfg (engine_settings); a row the engine
would skip ("without a model", a list of unmodelled creatures, the table or the creatures left off) is missing.
A kind whose placed count falls short of the original by more than config/actor_census_allowlist.json allows
("area/kind": {"missing": n, "register": ID, "why": ...}) fails. With the expansions selected, the places the build
sets aside on purpose leave both sides and are listed by name, each with its register entry (the same file's
"set_aside"): the rooms the room batch stage records as not made (RUN/chim-room-batches/room-batches.json, each
group by the stage's own list: its exterior-like cells and refused rooms, the places the world door table holds the
doors back for, and the cells the game data leaves empty, which no door leads into) and the exterior
cells the exterior plan does not plan (RUN/world-terrain, exterior_plan.planned_cells: Solstheim's cells, which no
map holds yet). Only a reference of an expansion master is set aside: a base game reference there still counts as
missing. With the base game alone nothing is set aside and the expansions' skip is printed by name
(BUILD-ACTOR-SPEC-EXPANSIONS-66: with Tribunal and Bloodmoon selected the check compared the three masters'
interior references with the base game's levelled points alone and stopped the image step).

Part 2, records: the actor record audit (tools/actor_record_audit.py) over the build's actor data, every field
(level, attributes, skills, health, magicka, fatigue, hello/fight/flee/alarm, flags, spells, inventory, the
carried weapon and ranged weapon, packages, animations) against config/actor-record-gaps.json: a field with more
missing or different records than listed fails.

Both parts read stored outputs only (no build, no emulator): about 35 s. The image step runs it right after the
creature census (build_aga.py finalize_image); by hand, in the shell container:
  python3 tools/actor_spec_check.py RUN_DIR --data-files DIR [--town-join on|off] [--no-records] [--json OUT]
                                    [--room-batches DIR] [--exterior-terrain DIR]
(the selected masters: AMIWIND_MASTERS, as the build sets it; the two stage folders default to the run's own)
"""
import argparse
import json
import re
import struct
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tools' / 'chim', ROOT / 'tools', ROOT / 'src'):
    while str(_p) in sys.path:
        sys.path.remove(str(_p))
    sys.path.insert(0, str(_p))

ALLOWLIST = ROOT / 'config' / 'actor_census_allowlist.json'
GAPS = ROOT / 'config' / 'actor-record-gaps.json'
REPORT = 'actor-spec-check.json'
KINDS = ('NPC_', 'CREA', 'LEVC')
SWIMS, FLIES, WALKS = 0x10, 0x20, 0x40          # CREA FLAG (OpenMW components/esm3/loadcrea.hpp)
EXPANSION_SKIP = ('Tribunal.esm and Bloodmoon.esm cells: not selected for this build (the base game alone); their '
                  'creatures are counted by the creature census (CREATURE-EXPANSION-62)')
ADDON_KEY_STRIDE = 1 << 22      # mwad.masters: a merged reference number is its owner's place x the stride + the low bits
ROOM_RECORD = 'room-batches.json'      # tools/room_batches.py RECORD, the room batch stage's record


def _text(d):
    return d.split(b'\0', 1)[0].decode('cp1252', 'replace')


def read_original(master_bytes, numbers=False):
    """({id: tag}, {id: CREA flags}, {list id: [creature or list ids]}, refs) of a master. refs: [(interior, cell xy
    or None, id)]; with NUMBERS [(interior, cell xy or None, id, reference number, cell name)]."""
    from mwad.esm import records, subrecords
    tags, flags, lists, refs = {}, {}, {}, []

    def ref(interior, xy, cur, cell):
        return (interior, xy, cur[0], cur[2], cell) if numbers else (interior, xy, cur[0])
    for tag, rflags, payload in records(master_bytes):
        parts = list(subrecords(payload))
        if tag == 'CELL':
            data = next((d for t, d in parts if t == 'DATA'), b'')
            interior = bool(len(data) >= 4 and struct.unpack_from('<I', data)[0] & 1)
            xy = struct.unpack_from('<ii', data, 4) if not interior and len(data) >= 12 else None
            cell = _text(next((d for t, d in parts if t == 'NAME'), b''))    # the header's NAME comes first
            cur = None
            for key, value in parts:
                if key == 'FRMR':
                    if cur is not None and not cur[1]:
                        refs.append(ref(interior, xy, cur, cell))
                    cur = [None, False, struct.unpack_from('<I', value)[0] if len(value) >= 4 else None]
                elif cur is not None and key == 'NAME' and cur[0] is None:
                    cur[0] = _text(value).casefold()
                elif cur is not None and key == 'DELE':
                    cur[1] = True
            if cur is not None and not cur[1]:
                refs.append(ref(interior, xy, cur, cell))
            continue
        if tag not in KINDS or rflags & 0x20:
            continue
        ident = _text(next((d for t, d in parts if t == 'NAME'), b'')).casefold()
        if not ident:
            continue
        tags[ident] = tag
        if tag == 'CREA':
            f = next((d for t, d in parts if t == 'FLAG'), b'\0\0\0\0')
            flags[ident] = struct.unpack_from('<I', f)[0]
        elif tag == 'LEVC':
            lists[ident] = [_text(d).casefold() for t, d in parts if t == 'CNAM']
    return tags, flags, lists, refs


def water_ids(tags, flags, lists):
    """The swim-only creatures and the levelled lists that give only them (every entry, nested lists included)."""
    def swim_only(ident, seen):
        if tags.get(ident) == 'CREA':
            f = flags.get(ident, 0)
            return bool(f & SWIMS) and not f & (WALKS | FLIES)
        if tags.get(ident) == 'LEVC' and ident not in seen:
            seen = seen | {ident}
            entries = [e for e in lists.get(ident, []) if e]
            return bool(entries) and all(swim_only(e, seen) for e in entries)
        return False
    return {i for i in tags if tags[i] in ('CREA', 'LEVC') and swim_only(i, frozenset())}


def master_of(number):
    """The game master that owns a reference number of the merged master (mwad.masters: the base game's numbers are
    its own, an expansion's are its place in GAME_MASTERS x ADDON_KEY_STRIDE + the low bits)."""
    from mwad.esm import GAME_MASTERS
    k = (number or 0) // ADDON_KEY_STRIDE
    return GAME_MASTERS[k] if k < len(GAME_MASTERS) else 'master %d' % k


def set_aside_rooms(room_batches):
    """{room cell casefold: (group, reason)} of the rooms the room batch stage output ROOM_BATCHES records as not made,
    each under the stage's own list: its exterior-like cells (group 'exterior_like', waiting for their exterior work),
    the rooms it refused (group 'refused', with its error), and the cells the game data leaves empty (group 'empty',
    tools/chim_room_batches.py empty_rooms: no placement the room converter keeps, with what the cell holds and how
    many doors lead in; ROOM-EMPTY-CELL-66). {} without it. BUILD-ACTOR-SPEC-EMPTY-ROOMS-66: the stage moved those
    cells from 'refused' to 'empty' and this read only the first two, so the one NPC of Mournhold, Royal Palace
    counted as missing and the v0.0.66-dev3 image step stopped."""
    path = Path(room_batches) / ROOM_RECORD if room_batches else None
    if path is None or not path.is_file():
        return {}
    record = json.loads(path.read_text(encoding='utf-8'))
    made = {r['room'].casefold() for r in record.get('rooms') or ()}
    out = {}
    for row in record.get('exterior_like') or ():
        out[row['cell'].casefold()] = ('exterior_like', row.get('state') or 'an exterior-like cell')
    for cell, why in sorted((record.get('refused') or {}).items()):
        out.setdefault(cell.casefold(), ('refused', str(why)))
    for cell, why in sorted((record.get('empty') or {}).items()):
        out.setdefault(cell.casefold(), ('empty', str(why)))
    return {c: v for c, v in out.items() if c not in made}


def interior_placed(tracker):
    """The reference numbers the image's maps place in the rooms' cells (entity-tracker.json placed_refs, its npc and
    creature lists: the creatures and the levelled points together, told apart by the original's record)."""
    if 'placed_refs' not in tracker:
        raise ValueError('actor spec check: entity-tracker.json has no placed_refs (the image step writes them)')
    out = set()
    for key, cats in tracker['placed_refs'].items():
        if key.startswith('interior:'):
            for cat in ('npc', 'creature'):
                out.update(cats.get(cat, ()))
    return out


def sort_refs(tags, refs, placed_inside, rooms_aside, planned):
    """The original's references REFS (read_original with numbers) sorted like for like: ({kind: {'original',
    'placed'}} of the rooms, [(cell xy, id, kind)] of the exterior references counted, {(area, room cell or None,
    master, group): {kind: n}} set aside). A room reference is placed when the image's maps place its number
    (PLACED_INSIDE); an expansion's reference that is not placed, in a room ROOMS_ASIDE names (set_aside_rooms), is set
    aside under its group; an expansion's exterior reference in a cell PLANNED does not hold (None: every cell planned)
    is set aside as 'unplanned_exterior'. A base game reference is never set aside."""
    base = master_of(0)
    inside = defaultdict(lambda: {'original': 0, 'placed': 0})
    outside, aside = [], {}
    for interior, xy, ident, number, cell in refs:
        kind = tags.get(ident)
        if kind not in KINDS:
            continue
        master = master_of(number)
        if interior:
            if number in placed_inside:
                inside[kind]['original'] += 1
                inside[kind]['placed'] += 1
            elif master != base and cell.casefold() in rooms_aside:
                key = ('interior', cell, master, rooms_aside[cell.casefold()][0])
                aside.setdefault(key, defaultdict(int))[kind] += 1
            else:
                inside[kind]['original'] += 1
        elif planned is not None and tuple(xy) not in planned and master != base:
            aside.setdefault(('exterior', None, master, 'unplanned_exterior'), defaultdict(int))[kind] += 1
        else:
            outside.append((xy, ident, kind))
    return ({k: dict(v) for k, v in inside.items()}, outside,
            {k: dict(sorted(v.items())) for k, v in aside.items()})


CONFIG = 'default-game.cfg'      # the image's shipped settings (tools/build_aga.py writes it into id1)


def engine_settings(id1):
    """{'table': the engine joins the exterior's actors from the actor table, 'creatures': it spawns creatures} as the
    image's shipped default-game.cfg leaves them (aw_actors.c: table_on is 0 and creatures_on 1 until a settings line
    says otherwise, the last line winning). Without "chim actors table 1" a joining cell reads its frame map, which
    holds no levelled point (CHIM-EXTERIOR-ACTORS-MISSING-46: v0.0.47-dev2 shipped the table without the line);
    "chim actors creatures 0" (dbg creatures off) spawns no creature at all."""
    out = {'table': False, 'creatures': True}
    path = Path(id1) / CONFIG
    text = path.read_text(encoding='latin-1') if path.is_file() else ''
    for line in text.splitlines():
        words = line.split('//', 1)[0].split()
        if words[:3] == ['chim', 'actors', 'table'] and len(words) == 4:
            digits = re.match(r'[+-]?\d+', words[3])          # the engine reads it with atoi: "on" is 0
            out['table'] = bool(digits and int(digits.group(0)))
        elif (words[:3] == ['chim', 'actors', 'creatures'] and len(words) == 4) or \
                (words[:2] == ['dbg', 'creatures'] and len(words) == 3):
            word = words[-1].lower()
            if word in ('on', 'true', '1', 'off', 'false', '0'):        # anything else: the usage line, no change
                out['creatures'] = word in ('on', 'true', '1')
    return out


def list_gives_model(lists, index, bases, seen=frozenset()):
    """Whether levelled list INDEX of the table's list section (actors.read_lists) can give, at some level, a creature
    whose base has a model in this build (nested lists followed; an entry naming nothing gives nothing)."""
    import actors
    if lists is None or index in seen or index >= len(lists):
        return False
    for _level, target in lists[index][2]:
        if target == 0xFFFF:
            continue
        if target & actors.NESTED:
            if list_gives_model(lists, target & 0x7FFF, bases, seen | {index}):
                return True
        elif target < len(bases) and bases[target]['text']:
            return True
    return False


def engine_places(base, bases, lists, settings):
    """Whether the engine can spawn a row of BASE when its cell joins (aw_actors.c TableJoinKinds and SpawnOne, as the
    image's SETTINGS leave them): a person or creature only with a model in this build (an empty base text is "without
    a model": never spawned), a levelled point only when its list can give such a creature, no creature with the
    creatures switched off. A corpse row: the frame map holding its cell places it (the region frames' authored dead,
    the town stages' dead). Without the table, a joining cell reads its frame map: its people and placed creatures,
    never a levelled point (tools/chim/region_actors.py defers them to the table)."""
    import actors
    kind = base['kind']
    if kind == actors.KINDS['corpse']:
        return bool(base['text'])
    if kind == actors.KINDS['LEVC']:
        return settings['table'] and settings['creatures'] and list_gives_model(lists, base.get('list', -1), bases)
    if not base['text']:
        return False
    return kind == actors.KINDS['NPC_'] or settings['creatures']


def placement(run, master_bytes, town_join=True, room_batches=None, exterior_terrain=None, groups=None):
    """({area: {kind: {'original', 'placed', 'source'}}}, [set-aside rows]) of build run RUN (the selected masters'
    world). ROOM_BATCHES, EXTERIOR_TERRAIN: the room batch and world terrain stage outputs (default: the run's own);
    GROUPS: the allowlist file's "set_aside" {group: {register, why}}."""
    import actor_census_check as acc
    import actors
    from exterior_plan import planned_cells
    run = Path(run)
    image = run / 'image'
    id1 = image / 'boot' / 'id1'
    groups = groups or {}
    tags, flags, lists, refs = read_original(master_bytes, numbers=True)
    water = water_ids(tags, flags, lists)
    rooms_aside = set_aside_rooms(room_batches if room_batches is not None else run / 'chim-room-batches')
    planned = planned_cells(exterior_terrain if exterior_terrain is not None else run / 'world-terrain')
    tracker = json.loads((image / 'entity-tracker.json').read_text(encoding='utf-8'))
    placed_inside = interior_placed(tracker)
    with open(id1 / 'world' / 'regions.awr', 'rb') as fh:
        cores = acc.town_cores(fh.read())
    out = defaultdict(lambda: defaultdict(lambda: {'original': 0, 'placed': 0, 'source': ''}))
    inside, outside, aside = sort_refs(tags, refs, placed_inside, rooms_aside, planned)
    for kind, row in inside.items():
        out['interior'][kind].update(row, source='entity-tracker.json placed_refs (rooms), kind by the reference\'s '
                                                 'record')
    for xy, ident, kind in outside:
        area = acc.area_of(xy, cores)
        out[area][kind]['original'] += 1
        if ident in water:
            out['water'][kind]['original'] += 1
    # the build: the exterior from the actor table, each row under its record's own kind (a corpse row is an NPC_ or
    # CREA reference of the original), placed by actor_census_check's rule: a region cell joins the table; a town
    # map's stage places its NPCs and corpses, the engine's town join its creatures and levelled points. A row in an
    # exterior cell the plan does not plan is in no map: it leaves the count with its original (set aside above).
    by_hash = {actors.fnv(i): i for i in tags}
    table_bytes = (id1 / 'maps' / 'chim-actors.cca').read_bytes()
    _head, cells, recs, bases, _text_bytes = actors.read_table(table_bytes)
    lists = actors.read_lists(table_bytes)
    settings = engine_settings(id1)
    kind_names = {v: k for k, v in actors.KINDS.items()}
    # OUTDOOR-CREATURES-REGRESSION-66: a row counts as placed only when the engine can spawn it (engine_places: its
    # model, a levelled list that can give a modelled creature, the shipped settings); the check before counted every
    # row of the table, so a build whose creatures had lost their models, or whose config left the table off, passed
    source = 'maps/chim-actors.cca (town join %s; table %s, creatures %s in %s)' % (
        'on' if town_join else 'off', 'on' if settings['table'] else 'OFF', 'on' if settings['creatures'] else 'OFF',
        CONFIG)
    table_aside = 0
    for cell, first, n in cells:
        if planned is not None and tuple(cell) not in planned:
            table_aside += n
            continue
        area = acc.area_of(cell, cores)
        for r in recs[first:first + n]:
            b = bases[r['base']]
            ident = by_hash.get(b['hash'])
            kind = tags.get(ident) or kind_names.get(b['kind'])
            if kind not in KINDS:
                continue
            # a town's people and dead: its resident stage places them; everything else: the engine's join (a town
            # map's creatures and levelled points only with its town join)
            town_stage = area == 'exterior-town' and kind_names.get(b['kind']) in acc.TOWN_STAGE_KINDS
            joined = area == 'exterior-region' or town_join
            if town_stage or (joined and engine_places(b, bases, lists, settings)):
                out[area][kind]['placed'] += 1
                if ident in water:
                    out['water'][kind]['placed'] += 1
            out[area][kind]['source'] = source
            if ident in water:
                out['water'][kind]['source'] = source + ', swim-only bases'
    places = []
    for (area, cell, master, group), kinds in sorted(aside.items(), key=lambda kv: (kv[0][0], kv[0][1] or '',
                                                                                      kv[0][2], kv[0][3])):
        row = {'area': area, 'master': master, 'group': group, 'kinds': dict(sorted(kinds.items())),
               'register': groups.get(group, {}).get('register'), 'why': groups.get(group, {}).get('why')}
        if cell is not None:
            row['cell'] = cell
            row['stage_reason'] = rooms_aside[cell.casefold()][1]
        places.append(row)
    totals = defaultdict(lambda: defaultdict(int))
    for row in places:
        for kind, n in row['kinds'].items():
            totals[row['area']][kind] += n
    set_aside = {'places': places, 'totals': {a: dict(sorted(k.items())) for a, k in sorted(totals.items())},
                 # the actor table's rows in the exterior cells the plan does not plan, left out with their originals
                 'exterior_table_rows': table_aside,
                 'exterior_plan': 'not found: every exterior cell counts' if planned is None else
                 '%d exterior cells planned' % len(planned)}
    return {a: {k: dict(v) for k, v in kinds.items()} for a, kinds in out.items()}, set_aside


def placement_verdict(counts, allowlist):
    """[failure lines]: every area and kind short of the original by more than its allowlisted number."""
    bad = []
    for area in sorted(counts):
        for kind in sorted(counts[area]):
            row = counts[area][kind]
            missing = row['original'] - row['placed']
            allowed = allowlist.get('%s/%s' % (area, kind), {}).get('missing', 0)
            if missing > allowed:
                bad.append('placement %s %s: %d of %d placed, %d missing (allowed %d)' % (
                    area, kind, row['placed'], row['original'], missing, allowed))
    return bad


def record_verdict(fields, gaps):
    """[failure lines]: every audit field with more missing or different records than config/actor-record-gaps.json
    lists (FIELDS: {field: {state: {'records': n, 'examples': [...]}}})."""
    bad = []
    for field in sorted(fields):
        for state in ('missing', 'different'):
            n = fields[field][state]['records']
            allowed = gaps.get(field, {}).get(state, 0)
            if n > allowed:
                bad.append('record %s: %d records %s, %d allowed (e.g. %s)' % (
                    field, n, state, allowed, ', '.join(fields[field][state].get('examples', [])[:4]) or '-'))
    return bad


def records_report(run, data_files):
    """The actor record audit's whole report over build RUN (its field table and its rows)."""
    import actor_record_audit as ara
    records, refs = ara.read_masters(data_files)
    build = ara.read_build(run)
    missing = [k for k, v in build['files'].items() if v is None]
    if missing:
        raise ValueError('actor spec check: the build has no %s to compare' % ', '.join(missing))
    build['anim'] = ara.read_anim_build(run)
    return ara.audit(records, refs, build, original=ara.OriginalGroups(ara.game_reader(data_files)))


def records_audit(run, data_files):
    """The actor record audit's field table over build RUN."""
    return records_report(run, data_files)['fields']


def set_aside_lines(set_aside):
    """The printed lines of the set-aside places: per area the counts, then each room by name."""
    lines = []
    for area, kinds in set_aside['totals'].items():
        lines.append('  set aside %-8s %s' % (area, ', '.join('%s %d' % kv for kv in kinds.items())))
    for row in set_aside['places']:
        where = row.get('cell') or 'the exterior cells the exterior plan does not plan (%d actor table rows)' % \
            set_aside['exterior_table_rows']
        lines.append('    %-44s %-14s %s [%s]' % (where, row['master'], ', '.join('%s %d' % kv for kv in row['kinds'].items()),
                                                 row.get('register') or 'no register entry'))
    return lines


def check(run, data_files, town_join=True, records=True, allowlist=ALLOWLIST, gaps=GAPS, room_batches=None,
          exterior_terrain=None):
    """The report dict ({'placement', 'set_aside', 'records', 'failures', 'skipped'}) of build run RUN.
    ROOM_BATCHES, EXTERIOR_TERRAIN: the stage outputs that say what the build sets aside (default: the run's own)."""
    from mwad.masters import is_base_only, master_path, selected_masters
    t0 = time.time()
    print('=== PHASE 1/2: placement per area kind ===', flush=True)
    doc = json.loads(Path(allowlist).read_text(encoding='utf-8'))
    allow, groups = doc['allow'], doc.get('set_aside', {})
    masters = selected_masters()
    counts, set_aside = placement(run, master_path(Path(data_files)).read_bytes(), town_join, room_batches,
                                  exterior_terrain, groups)
    print('  masters: %s' % ', '.join(masters), flush=True)
    settings = engine_settings(Path(run) / 'image' / 'boot' / 'id1')
    print('  the engine\'s shipped settings (%s): actor table %s, creatures %s' % (
        CONFIG, 'on' if settings['table'] else 'OFF', 'on' if settings['creatures'] else 'OFF'), flush=True)
    for area in sorted(counts):
        for kind in sorted(counts[area]):
            r = counts[area][kind]
            print('  %-16s %-5s original %5d placed %5d  (%s)' % (area, kind, r['original'], r['placed'], r['source']),
                  flush=True)
    bad = placement_verdict(counts, allow)
    unnamed = sorted({row['group'] for row in set_aside['places'] if not row.get('register')})
    bad += ['set-aside group %s has no register entry in config/actor_census_allowlist.json set_aside' % g
            for g in unnamed]
    for line in set_aside_lines(set_aside):
        print(line, flush=True)
    skipped = [EXPANSION_SKIP] if is_base_only(masters) else []
    for line in skipped:
        print('  skipped: %s' % line, flush=True)
    print('  placement: %.1f s' % (time.time() - t0), flush=True)
    fields = audit = expansion = None
    if records:
        print('=== PHASE 2/2: the actor records (actor_record_audit) ===', flush=True)
        audit = records_report(Path(run), data_files)
        fields = audit['fields']
        bad += record_verdict(fields, json.loads(Path(gaps).read_text(encoding='utf-8'))['gaps'])
        print('  %d fields compared (%.1f s)' % (len(fields), time.time() - t0), flush=True)
    if audit is not None and not is_base_only(masters):
        # part 3, the expansions' actors and stages per land (tools/expansion_actor_check.py, config/expansion-stages.json):
        # counts at milestone 1, a stop per incomplete actor from milestone 2; with the base game alone it does not run
        # and the report has no such key
        print("=== PHASE 3: the expansions' actors and stages (expansion_actor_check) ===", flush=True)
        import expansion_actor_check as eac
        expansion = eac.check(Path(run), data_files, list(masters), audit)
        for land, c in expansion['lands'].items():
            print('  %-24s stage 2: %s of %s actor placements placed, %s complete; failing %s' % (
                land, c['stage 2 actors placed'], c['stage 2 actor placements'], c['stage 2 actors complete'],
                c['stage 2 failing columns'] or '-'), flush=True)
        bad += expansion['failures']
    report = {'placement': counts, 'set_aside': set_aside, 'masters': list(masters), 'allowlist': allow,
              'skipped': skipped, 'town_join': town_join, 'engine_settings': settings,
              'records': {f: {s: v[s]['records'] for s in ('missing', 'different')} for f, v in (fields or {}).items()},
              'failures': bad, 'seconds': round(time.time() - t0, 1)}
    if expansion is not None:
        report['expansion_actors'] = {k: expansion[k] for k in ('setting', 'lands', 'failures')}
        report['_expansion_rows'] = expansion['rows']
    return report


def stage(run, data_files, out):
    """The image step's verdict: writes OUT/actor-spec-check.json and stops (ValueError) on any failure. The set-aside
    places come from the run's own stage outputs (RUN/chim-room-batches, RUN/world-terrain: tools/build.py's names)."""
    report = check(run, data_files)
    rows = report.pop('_expansion_rows', None)
    if rows is not None:   # every expansion actor placement, one row each (only with an expansion selected)
        (Path(out) / 'expansion-actors.json').write_text(json.dumps(rows, indent=1, default=str) + '\n',
                                                         encoding='utf-8', newline='\n')
    (Path(out) / REPORT).write_text(json.dumps(report, indent=1, sort_keys=True) + '\n', encoding='utf-8',
                                    newline='\n')
    if report['failures']:
        raise ValueError('Actor spec check failed (BUILD-ACTOR-SPEC-CHECK-66): %d problem(s): %s'
                         % (len(report['failures']), '; '.join(report['failures'][:8])))
    print('Actor spec check passed: every area kind placed, every actor record within its tracked gaps (%.1f s).'
          % report['seconds'], flush=True)
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('run', type=Path)
    ap.add_argument('--data-files', type=Path, required=True)
    ap.add_argument('--town-join', choices=('on', 'off'), default='on')
    ap.add_argument('--no-records', action='store_true', help='placement only (seconds)')
    ap.add_argument('--json', type=Path)
    ap.add_argument('--room-batches', type=Path, help='the room batch stage output (default RUN/chim-room-batches)')
    ap.add_argument('--exterior-terrain', type=Path, help='the world terrain stage output (default RUN/world-terrain)')
    a = ap.parse_args(argv)
    report = check(a.run, a.data_files, a.town_join == 'on', not a.no_records, room_batches=a.room_batches,
                   exterior_terrain=a.exterior_terrain)
    report.pop('_expansion_rows', None)
    if a.json:
        a.json.write_text(json.dumps(report, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    for line in report['failures']:
        print('FAIL ' + line)
    print('actor spec check: %s' % ('FAIL' if report['failures'] else 'PASS'))
    return 1 if report['failures'] else 0


if __name__ == '__main__':
    sys.exit(main())
