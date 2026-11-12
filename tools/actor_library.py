# SPDX-License-Identifier: GPL-3.0-only
"""The actor library stage (EXPERIMENTAL; a build has this stage only with --chim-actor-table on; the image step
installs its models and gives the actor table their base texts; CHIM-EXTERIOR-ACTORS-MISSING-46).

Models for the exterior actors the town residents do not cover:
- every creature the exterior can show (its creature references and every creature its levelled lists can give)
  and every creature the rooms can show (their levelled lists and their placed creatures, TOMB-NO-CREATURES-61):
  one standing and one mover model per creature mesh (tools/creature_library.py, method kf; a mesh only the rooms
  reach: one skeletal model on its own table, room_only_meshes); an authored-dead
  creature placed outdoors: one corpse model per mesh, its own death pose (ACTOR-LIBRARY-LEFT-OUT-48);
- every exterior NPC record with a reference the CHIM towns of this run do not place (a record only the towns place
  has its model from the town stages): one standing model per appearance (tools/npc_library.py).

Output: OUT/id1/progs (c_*.mdl, n_*.mdl and their .anm layouts), OUT/id1/sound (footstep sounds of the layouts),
OUT/creature-library.json, OUT/npc-library.json and OUT/actor-library.json (counts, bytes, left out with reasons).
Scaled references are drawn at their scale by the engine (AWU_SCALE); --scaled-variants also bakes models at the
scales the exterior uses (the method before the engine could scale a live actor).
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Run as a script, Python puts tools/ first, and tools/mwad.py would hide the src/mwad package
# (BUILD-ACTOR-LIBRARY-MWAD-PATH-47): src/ goes ahead of tools/, as in chim_build.py.
for _p in (ROOT / 'tools', ROOT / 'src'):
    while str(_p) in sys.path:
        sys.path.remove(str(_p))
    sys.path.insert(0, str(_p))


# The opening's own actors (tools/prepare_intro.py INTRO_ACTORS, the placed roles): the opening stage bakes their
# progs/np_<stem>.mdl with its 21 talk, blink and walk frames only (idle 0-7, walk 13-20), so a fight showed no
# attack, hit or death (CENSUS-NPC-NO-ATTACK-ANIM-65). Their appearances are baked here too, and np_<stem>.anm names
# that full-kit model as the mover the engine wears in a fight (aw_combat.c AW_CombatEngage). The list is kept equal
# to INTRO_ACTORS by tests/test_actor_library.py; prepare_intro.py itself is not changed (its stage key stays).
OPENING_ACTORS = (('chargen name', 'jiub'), ('chargen boat guard 2', 'escort'), ('chargen boat guard 3', 'upper'),
                  ('chargen boat guard 1', 'deck'), ('chargen dock guard', 'dock'), ('chargen class', 'census'),
                  ('chargen captain', 'captain'), ('chargen door guard', 'hall'))


def opening_layout(key):
    """np_<stem>.anm of an opening actor: its own idle and walk frames (AW_AnimDefault's 21-frame layout) and the
    library model of its appearance (KEY) as its full-kit mover."""
    import npc_library as NL
    return 'idle:0:8:0.1500 walk:13:8:0.1250 >%s\n' % NL.model_path(key)


def write_opening_layouts(npc_manifest, id1):
    """Write id1/progs/np_<stem>.anm for every opening actor the NPC library baked; {stem: library model}."""
    out = {}
    for ident, stem in OPENING_ACTORS:
        npc = npc_manifest.get('npcs', {}).get(ident)
        if not npc:
            continue
        (Path(id1) / 'progs').mkdir(parents=True, exist_ok=True)
        (Path(id1) / 'progs' / ('np_%s.anm' % stem)).write_text(opening_layout(npc['key']), encoding='ascii',
                                                                 newline='\n')
        out[stem] = 'progs/n_%s.mdl' % npc['key']
    return out


def _layout_groups(id1, model):
    """(group names, mover model or None) of MODEL's .anm in ID1; None when it has none."""
    path = Path(id1) / (model[:-4] + '.anm')
    if not path.is_file():
        return None
    words = path.read_text(encoding='cp1252').split()
    groups = {w.split(':')[0] for w in words if w[:1] not in '@!~>'}
    movers = [w[1:] for w in words if w.startswith('>')]
    return groups, (movers[0] if movers else None)


COVERAGE_GROUPS = ('idle', 'walk', 'run', 'attack', 'hit', 'death')
# Placed actors a fight can never reach, by record id: {id: reason with the script line}. Empty: every placed actor
# is checked (the opening's eight are all linked to their full kit, which also covers a console teleport).
COVERAGE_EXCEPTIONS = {}
# The opening actors' lifecycle, from the original scripts (Morrowind.esm SCPT text; line numbers of that text):
# CharGenClassNPC state 0 (lines 31-51, the clerk's script on the player's first frame in the census office)
# disables "CharGen Boat", "CharGen Boat Guard 1", "CharGen Boat Guard 2", "CharGen Dock Guard" and the ship's props
# and cabin door; nothing disables Jiub or Boat Guard 3, who stay in the ship's hold, which is out of reach once the
# cabin door is gone. The engine does the same: aw_opening.c AW_OpeningSpawn sets ship_disabled in the census
# office and hides roles 4 and 5 and the ship in Seyda Neen; aw_scene.c leaves out the link back to the ship.
# No script disables the three census people: they can be met and attacked for the rest of the game.
_SHIP = 'until the census office; the ship is out of reach after CharGenClassNPC state 0 disables its cabin door'
OPENING_LIFECYCLE = {
    'chargen name': ('ship hold (prison.bsp), the opening', 'never disabled; ' + _SHIP, False),
    'chargen boat guard 3': ('ship hold (prison.bsp), the opening', 'never disabled; ' + _SHIP, False),
    'chargen boat guard 2': ('ship (prison.bsp), the opening',
                             'disabled by CharGenClassNPC state 0 (line 38)', False),
    'chargen boat guard 1': ('ship deck, Seyda Neen dock', 'disabled by CharGenClassNPC state 0 (line 37)', False),
    'chargen dock guard': ('Seyda Neen dock', 'disabled by CharGenClassNPC state 0 (line 39)', False),
    'chargen class': ('census office (census.bsp)', 'never disabled', True),
    'chargen captain': ('census office (census.bsp)', 'never disabled', True),
    'chargen door guard': ('census hall (census.bsp)', 'never disabled', True),
}


def _record_tables(id1):
    """What an actor's record reaches in ID1 (OPENING-ACTORS-FULL-RECORD-65): the combat sheets {record: row cells}
    (combat/actors.txt), focus.awf's reference identities {reference: record hash}, the area pack's records
    {room key: bytes} (areas.awa) and the ambient rows' references (npc-ambient.lut). A missing file gives empty."""
    import struct
    id1 = Path(id1)
    sheets, refs, areas, ambient = {}, {}, {}, set()
    path = id1 / 'combat/actors.txt'
    if path.is_file():
        for line in path.read_text(encoding='ascii', errors='replace').splitlines():
            cols = line.split('\t')
            if len(cols) > 6:
                sheets[cols[0]] = cols
    if (id1 / 'focus.awf').is_file():
        import prepare_area_tables as PAT
        refs = PAT.reference_hashes((id1 / 'focus.awf').read_bytes())
    if (id1 / 'areas.awa').is_file():
        raw = (id1 / 'areas.awa').read_bytes()
        for i in range(struct.unpack_from('<I', raw, 4)[0]):
            key, off, size = struct.unpack_from('<III', raw, 24 + 12 * i)
            areas[key] = raw[off:off + size]
    if (id1 / 'npc-ambient.lut').is_file():
        import ambient_lut
        ambient = {r['ref'] & 0xFFFFFF for r in ambient_lut.read_table((id1 / 'npc-ambient.lut').read_bytes())[1]}
    return sheets, refs, areas, ambient


def record_binding(f, room, tables):
    """How a placed actor (entity fields F, its map's room key ROOM) reaches its own record: the combat sheet, the
    reference identity, the stat entry in its room's area record (stats, behaviour, faction, spells, gold) and an ambient
    row; 'missing' lists what it lacks (an ambient row is only needed by a wanderer, so it is not required)."""
    import struct
    import prepare_area_tables as PAT
    sheets, refs, areas, ambient = tables
    ident = f.get('aw_source_id', '').casefold()
    try:
        ref = int(float(f.get('aw_ref', '0'))) & 0xFFFFFF
    except ValueError:
        ref = 0
    h = PAT.name_hash(ident) if ident else 0
    sheet = sheets.get(ident)
    out = {'record': ident, 'reference': ref,
           'sheet': {'level': int(sheet[2]), 'attributes': sheet[3], 'skills': sheet[4],
                     'health_magicka_fatigue': sheet[5], 'fight_flee': sheet[6]} if sheet else None,
           'reference_is_record': bool(ref) and refs.get(ref) == h,
           'room': room, 'stat_entry_in_room': bool(room in areas and h and struct.pack('>I', h) in areas[room]),
           'ambient_row': ref in ambient}
    out['missing'] = [k for k, ok in (('record id', bool(ident)), ('combat sheet', bool(sheet)),
                                      ('reference identity', out['reference_is_record']),
                                      ('stat entry in its room', out['stat_entry_in_room'])) if not ok]
    return out


def coverage_rows(id1):
    """The actor animation coverage table of ID1 (actor-anim-coverage.json, CENSUS-NPC-NO-ATTACK-ANIM-65): one row
    per aw_npc placed in its .bsp maps: record id, map, name, model, the groups its fight can play (its own layout's
    or its full-kit mover's), the mover, can_be_hostile, exception and ok (an attack group, or a named exception)."""
    import re
    import struct
    rows = []
    tables = _record_tables(id1)
    checked = bool(tables[0])      # an image with its record tables (a bare test image has none)
    for path in sorted((Path(id1) / 'maps').glob('*.bsp')):
        raw = path.read_bytes()
        if len(raw) < 12:
            continue
        off, size = struct.unpack_from('<ii', raw, 4)
        text = raw[off:off + size].decode('cp1252', 'replace')
        blocks = re.findall(r'\{[^{}]*\}', text)
        world = dict(re.findall(r'"([^"]+)"\s+"([^"]*)"', blocks[0])) if blocks else {}
        room = int(world['_aw_cell_int']) if world.get('_aw_cell_int', '').isdigit() else None
        for block in blocks:
            f = dict(re.findall(r'"([^"]+)"\s+"([^"]*)"', block))
            model = f.get('model', '')
            if f.get('classname') != 'aw_npc' or not model.endswith('.mdl'):
                continue
            own = _layout_groups(id1, model)
            groups = set(own[0]) if own else set()
            link = own[1] if own else None
            if link:
                mover = _layout_groups(id1, link) if (Path(id1) / link).is_file() else None
                if mover:
                    groups |= mover[0]
                else:
                    link = None      # a link to a model or layout the image lacks plays nothing
            ident = f.get('aw_source_id', '').casefold()
            exception = COVERAGE_EXCEPTIONS.get(ident)
            present = {g: g in groups for g in COVERAGE_GROUPS}
            life = OPENING_LIFECYCLE.get(ident)
            lifecycle = {'placed_by': 'map entity (%s)' % path.name + ('; ' + life[0] if life else ''),
                         'removed_by': life[1] if life else 'not read yet (only the opening actors are)'}
            rows.append({'record': ident, 'map': path.name, 'name': f.get('netname', ''), 'model': model,
                         'layout': own is not None, 'groups': present, 'full_kit': link, 'lifecycle': lifecycle,
                         # attacked in the opening's own window or later; unknown lifecycles count as attackable
                         'can_be_met_and_attacked': life[2] if life else True,
                         'can_be_hostile': True, 'exception': exception,
                         # OPENING-ACTORS-FULL-RECORD-65: its stats, inventory, behaviour and faction through its own record
                         'record_binding': record_binding(f, room, tables) if checked else None,
                         'ok': present['attack'] or bool(exception)})
            b = rows[-1]['record_binding']
            if b and b['missing'] and not exception:
                rows[-1]['ok'] = False
    return rows


def fight_layout_failures(id1):
    """Every aw_npc of ID1's .bsp maps that would fight with no attack group, or (an image with its record tables)
    does not reach its own record (a coverage row not ok): [(map, name, model and what is missing)]."""
    out = []
    for r in coverage_rows(id1):
        if r['ok']:
            continue
        why = ([] if r['groups']['attack'] else ['attack group']) + \
            (r['record_binding']['missing'] if r['record_binding'] else [])
        out.append((r['map'], r['name'], '%s; %s: %s' % (r['model'], r['record'] or '?', ', '.join(why))))
    return out


def write_coverage(id1, out):
    """Write OUT/actor-anim-coverage.json from ID1 and return its rows."""
    rows = coverage_rows(id1)
    doc = {'format': 'AmiWind actor animation coverage 1', 'groups': list(COVERAGE_GROUPS),
           'actors': len(rows), 'failing': sum(1 for r in rows if not r['ok']), 'rows': rows}
    Path(out).mkdir(parents=True, exist_ok=True)
    (Path(out) / 'actor-anim-coverage.json').write_text(json.dumps(doc, indent=1, sort_keys=True) + '\n',
                                                         encoding='utf-8', newline='\n')
    return rows


def town_residents(run):
    """The NPC and creature record ids the CHIM town stages of RUN made models for (their residents.json)."""
    return town_cast(run)[0]


def town_cast(run):
    """(record ids, reference numbers) the CHIM town stages of RUN place (their residents.json models and cast)."""
    ids, refs = set(), set()
    for path in sorted(Path(run).glob('chim-town-*/residents.json')):
        doc = json.loads(path.read_text(encoding='utf-8'))
        ids |= {k.casefold() for k in doc.get('models', {})}
        refs |= {int(c['number']) for c in doc.get('cast', []) if 'number' in c}
    return ids, refs


def opening_ids(master):
    """The OPENING_ACTORS record ids MASTER has (a test master without them adds none)."""
    low = master.lower()
    return {i for i, _ in OPENING_ACTORS if i.encode('cp1252') + b'\0' in low}


def plan(master, residents=(), town_refs=None):
    """(creature meshes {mesh: [ids]}, two-legged {mesh: bool}, scales {mesh: [scale]}, NPC ids, the creature plan,
    corpse meshes {mesh: [ids]}) of the exterior.

    An NPC record a CHIM town places (RESIDENTS) still gets a library model when it has an exterior reference the
    towns do not place (TOWN_REFS: their cast's reference numbers): 'hlaalu guard_outside' and 'ordinator wander'
    stand in Balmora or Vivec and on the roads around them, and the region frames need them too
    (ACTOR-LIBRARY-LEFT-OUT-48). TOWN_REFS None: every exterior reference of a resident counts as the towns' (the
    rule before v0.0.48). An authored-dead creature placed outdoors gets its mesh's corpse model (corpses)."""
    from chim import actors as A
    import creature_library as L
    refs = A.exterior_actors(master)
    lists, creatures = A.levelled_lists(master), A.creature_ids(master)
    # the rooms' levelled lists too (chim.actors.table_list_order): the table rolls a room's 'aw_levelled' entity
    # from the same lists, so every creature they can give needs its model here (CREATURE-ROOM-LEVELLED-54); and the
    # creatures placed in rooms, each on a list of one (TOMB-NO-CREATURES-61)
    rooms = A.room_references(master)
    placed = A.room_placed_creatures(master, references=rooms)
    used = A.table_list_order(lists, refs, rooms['LEVC'], placed)
    lists = A.with_placed(lists, placed)
    want = {b.casefold() for _, b, t, *_ in refs if t == 'CREA'}
    # v0.0.62 (MWSCRIPT-GAP-FUNCTIONS-62): every actor a script places, placed in the world or not
    by_script = A.script_placed_actors(master)
    want |= set(by_script['CREA'])
    for lid in used:
        want |= {e for e, _ in lists[lid][2] if e in creatures}
    planned = L.plan(master)
    meshes, bipedal, corpses = {}, {}, {}
    for ident in sorted(want):
        b = planned['bases'].get(ident)
        if b and b['mesh']:
            (corpses if b['dead'] else meshes).setdefault(b['mesh'], []).append(ident)
            bipedal[b['mesh']] = bipedal.get(b['mesh'], False) or bool(b['flags'] & 1)
    scales = {}
    numbers = A.exterior_scales(master)
    by_number = {n: (b.casefold(), t) for n, b, t, *_ in refs}
    for number, scale in numbers.items():
        ident, tag = by_number[number]
        ids = [ident] if tag == 'CREA' else [e for lid in A.used_lists(lists, {ident}) for e, _ in lists[lid][2]
                                             if e in creatures]
        for i in ids:
            b = planned['bases'].get(i)
            if b and b['mesh'] in meshes:
                scales.setdefault(b['mesh'], set()).add(round(float(scale), 4))
    residents = {r.casefold() for r in residents}
    npcs = sorted({b.casefold() for n, b, t, *_ in refs if t == 'NPC_' and
                   (b.casefold() not in residents or (town_refs is not None and n not in town_refs))} |
                  set(by_script['NPC_']) | opening_ids(master))
    return meshes, bipedal, {m: sorted(v) for m, v in scales.items()}, npcs, planned, corpses


def room_only_meshes(master, meshes):
    """The meshes of MESHES (plan's) that only the rooms reach (their levelled lists or their placed creatures; no
    exterior reference or exterior list gives them): they are baked with the skeletal method (one rest frame on the creature's own table, about a
    third of a kf model's bytes), sized for the 32 MB rooms."""
    from chim import actors as A
    import creature_library as L
    refs = A.exterior_actors(master)
    lists, creatures = A.levelled_lists(master), A.creature_ids(master)
    ext = {b.casefold() for _, b, t, *_ in refs if t == 'CREA'}
    for lid in A.used_lists(lists, {b.casefold() for _, b, t, *_ in refs if t == 'LEVC'}):
        ext |= {e for e, _ in lists[lid][2] if e in creatures}
    bases = L.plan(master)['bases']
    ext_meshes = {bases[i]['mesh'] for i in ext if i in bases}
    return {m: ids for m, ids in meshes.items() if m not in ext_meshes}


def pool_sizes(jobs):
    """(creature workers, NPC pool size) of the stage (BUILD-ACTOR-LIBRARY-UNDERUSED-54). The launch --jobs is only
    the scheduler's share when the stage started (12 of 24 beside other stages); a split of it below the stage's
    assigned workers fixed both pools for the whole stage, so about 8 ran while 192 NPC units waited once the other
    stages had finished. Now: the creatures (about 50 models) take a quarter of the share they have at the start; the
    NPC pool is sized for the stage's ceiling (build_parallel.stage_ceiling: the build budget under the scheduler), so
    its ordered_map follows the live allowance and grows to every allowed core when the stage runs alone. While the
    creatures run, the NPC pool follows NpcAllowance (the allowance minus the creature workers), so the two together
    never hold more than the stage's allowance. Outside the scheduler: the creatures a quarter of JOBS, the NPCs the rest, as before."""
    from build_parallel import live_jobs, stage_ceiling, ALLOWANCE_ENV
    share = max(1, live_jobs(jobs))
    creature_jobs = max(1, share // 4) if share > 1 else 1
    if os.environ.get(ALLOWANCE_ENV):
        return creature_jobs, max(1, stage_ceiling(jobs))
    return creature_jobs, (max(1, jobs - creature_jobs) if jobs > 1 else 1)


class NpcAllowance:
    """The NPC pool's own allowance file while the creatures bake beside it: the stage's live allowance minus the
    creature workers still running, rewritten every half second, so the two pools together never hold more than the
    stage is allowed (the resource plan sizes memory by it; BUILD-CHIM-MAIN-MEMORY-46's family) and the NPC pool grows
    to the whole allowance once the creatures are done. Under the scheduler only (ALLOWANCE_ENV set); a no-op
    outside it. Use: with NpcAllowance(creature_jobs) as share: ... share.creatures_done() ..."""

    def __init__(self, creature_jobs):
        from build_parallel import ALLOWANCE_ENV
        self.env, self.source = ALLOWANCE_ENV, os.environ.get(ALLOWANCE_ENV)
        self.creature_jobs, self.done, self.path, self.thread = creature_jobs, False, None, None

    def value(self):
        """What the NPC pool may hold now."""
        try:
            live = max(1, int(Path(self.source).read_text().strip()))
        except (OSError, ValueError, TypeError):
            return None
        return max(1, live - (0 if self.done else self.creature_jobs))

    def write(self):
        v = self.value()
        if v is not None:
            tmp = self.path.with_suffix('.tmp')
            tmp.write_text(str(v), encoding='ascii', newline='\n')
            os.replace(tmp, self.path)

    def creatures_done(self):
        self.done = True
        if self.path:
            self.write()

    def __enter__(self):
        if not self.source:
            return self
        import threading
        # beside the scheduler's own allowance file (no system temp: build_scratch's rule)
        self.path = Path(self.source).with_name(Path(self.source).name + '.actor-npc')
        self.write()
        os.environ[self.env] = str(self.path)
        self.stop = threading.Event()

        def loop():
            while not self.stop.wait(.5):
                self.write()
        self.thread = threading.Thread(target=loop, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *exc):
        if self.thread:
            self.stop.set()
            self.thread.join()
            os.environ[self.env] = self.source
            for p in (self.path, self.path.with_suffix('.tmp')):
                try:
                    p.unlink()
                except OSError:
                    pass
        return False


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--data-files', type=Path, required=True)
    p.add_argument('--palette', type=Path, required=True, help='the runtime palette (gfx/palette.lmp)')
    p.add_argument('--run', type=Path, help='the build run: its CHIM town stages name the residents to leave out')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--jobs', type=int, default=1)
    p.add_argument('--scaled-variants', action='store_true',
                   help='also bake creature models at the instance scales the exterior uses (the previous method)')
    p.add_argument('--creature-method', choices=('kf', 'skeletal'), default='kf',
                   help='kf (default): the baked standing and mover models; skeletal: each creature mesh on its own '
                        'animation table, every group of its own files (tools/creature_tables.py, CREATURE-TABLES)')
    a = p.parse_args(argv)
    path = list(sys.path)
    import creature_library as L
    import npc_library as NL
    sys.path[:] = path   # keep src/mwad ahead of tools/mwad.py whatever those imports did
    from mwad.paths import child_ci
    t0 = time.time()
    master = child_ci(a.data_files, 'Morrowind.esm').read_bytes()
    residents, town_refs = town_cast(a.run) if a.run else (set(), set())
    meshes, bipedal, scales, npcs, planned, corpses = plan(master, residents, town_refs)
    print('Actor library: %d creature meshes, %d corpse meshes, %d NPC records (%d town residents: those placed '
          'only by the towns are left to the town stages), %d jobs' % (len(meshes), len(corpses), len(npcs),
                                                                       len(residents), a.jobs), flush=True)
    id1 = a.out / 'id1'
    id1.mkdir(parents=True, exist_ok=True)
    palette = a.palette.read_bytes()
    t1 = time.time()
    rooms_only = room_only_meshes(master, meshes)
    # The creatures (about 50 models) and the NPCs (about 400 appearances) are baked side by side: one after the
    # other, the NPCs' 400 units waited for the creatures' last few (BUILD-ACTOR-LIBRARY-UNDERUSED-54: 45 s at about
    # 2 cores in the v0.0.57-dev5 full build). The creatures take a quarter of the jobs, the NPCs the rest; they
    # write different files (progs/c_* and progs/n_*, the NPCs' sounds), each into id1 as before.
    from concurrent.futures import ThreadPoolExecutor
    creature_jobs, npc_jobs = pool_sizes(a.jobs)
    print('Actor library: %d creature workers beside an NPC pool of up to %d (the build\'s live share)' % (
        creature_jobs, npc_jobs), flush=True)
    side = ThreadPoolExecutor(max_workers=1)
    with NpcAllowance(creature_jobs) as share:
        creature_future = side.submit(L.bake, a.data_files, palette,
                                      {m: v for m, v in meshes.items() if m not in rooms_only}, id1, creature_jobs,
                                      a.creature_method, bipedal, scales if a.scaled_variants else None,
                                      corpses=corpses)
        creature_future.add_done_callback(lambda _f: share.creatures_done())
        t2 = time.time()
        npc_manifest = NL.build(a.data_files, palette, npcs, id1, npc_jobs)
        npc_seconds = time.time() - t2
        models, failed = creature_future.result()
    side.shutdown(wait=True)
    if rooms_only:
        print('Actor library: %d creature meshes only the rooms\' levelled lists give: skeletal (%s)' % (
            len(rooms_only), ', '.join(sorted(rooms_only))), flush=True)
        more, more_failed = L.bake(a.data_files, palette, rooms_only, id1, a.jobs, 'skeletal', bipedal)
        models.update(more)
        failed.update(more_failed)
    creature_manifest = dict(L.manifest(planned, models), left_out=failed)
    (a.out / 'creature-library.json').write_text(json.dumps(creature_manifest, indent=1, sort_keys=True) + '\n',
                                                 encoding='utf-8', newline='\n')
    print('Actor library: creatures done - took %.1fs, %d models, %d left out' % (time.time() - t1, len(models),
                                                                                  len(failed)), flush=True)
    (a.out / 'npc-library.json').write_text(json.dumps(npc_manifest, indent=1, sort_keys=True) + '\n',
                                            encoding='utf-8', newline='\n')
    opening = write_opening_layouts(npc_manifest, id1)
    print('Actor library: %d of %d opening actors linked to their full-kit model (%s)' % (
        len(opening), len(OPENING_ACTORS), ', '.join('%s=%s' % kv for kv in sorted(opening.items()))), flush=True)
    print('Actor library: NPCs done - took %.1fs, %d appearances, %d left out' % (
        npc_seconds, len(npc_manifest['models']), len(npc_manifest['left_out'])), flush=True)
    summary = {'creature_meshes': len(meshes), 'corpse_meshes': len(corpses),
               'corpse_models': sum(1 for k in models if k.endswith(L.CORPSE_KEY)),
               'creature_models': len(models), 'creature_left_out': failed,
               'creature_bytes': sum(m.get('standing_bytes', 0) + m.get('mover_bytes', 0) for m in models.values()),
               'npc_records': len(npcs), 'npc_appearances': len(npc_manifest['models']),
               'npc_left_out': npc_manifest['left_out'],
               # appearances baked at a smaller animation level (alias byte budget; RESIDENT-ANIM-BYTE-BUDGET-48)
               'npc_anim_fallback': {key: {'level': f['level'], 'npcs': f['npcs']}
                                     for key, f in npc_manifest.get('anim_fallback', {}).items()},
               'npc_bytes': sum(m['bytes'] for m in npc_manifest['models'].values()),
               'opening_links': opening,
               'scaled_variants': bool(a.scaled_variants), 'town_residents_left_to_towns': len(residents),
               'seconds': round(time.time() - t0, 1)}
    (a.out / 'actor-library.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n', encoding='utf-8',
                                              newline='\n')
    print('Actor library: done - took %.1fs' % summary['seconds'], flush=True)


def install(library, id1, jobs=1):
    """Copy an actor library stage's models, layouts and sounds into an image's id1; returns the base texts
    {record id (or 'id@S'): entity text} of its creatures and NPCs for the actor table."""
    import shutil
    import creature_library as L
    import npc_library as NL
    from concurrent.futures import ThreadPoolExecutor
    library, id1 = Path(library), Path(id1)
    pairs = [(src, id1 / src.relative_to(library / 'id1')) for src in sorted((library / 'id1').rglob('*'))
             if src.is_file()]
    for folder in sorted({dst.parent for _, dst in pairs}):
        folder.mkdir(parents=True, exist_ok=True)
    # about a thousand small files: side by side (copying releases the interpreter lock), each to its own name, so
    # the installed files are the same as one by one (BUILD-IMAGE-FINALIZE-UNDERUSED-48)
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        list(pool.map(lambda pair: shutil.copyfile(*pair), pairs))
    copied = len(pairs)
    # every aw_npc of the image's maps fights with attack frames (its own or its mover's; CENSUS-NPC-NO-ATTACK-ANIM-65)
    bad = fight_layout_failures(id1)
    if bad:
        raise ValueError('Actors without attack frames (no attack group in their layout or mover): ' +
                         ', '.join('%s %s (%s)' % b for b in bad))
    texts = L.base_texts(library / 'creature-library.json')
    texts.update(NL.base_texts(library / 'npc-library.json'))
    return texts, copied


if __name__ == '__main__':
    main()
