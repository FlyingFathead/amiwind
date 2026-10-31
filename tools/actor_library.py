# SPDX-License-Identifier: GPL-3.0-only
"""The actor library stage (EXPERIMENTAL; a build has this stage only with --chim-actor-table on; the image step
installs its models and gives the actor table their base texts; CHIM-EXTERIOR-ACTORS-MISSING-46).

Models for the exterior actors the town residents do not cover:
- every creature the exterior can show (its creature references and every creature its levelled lists can give):
  one standing and one mover model per creature mesh (tools/creature_library.py, method kf); an authored-dead
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
    # from the same lists, so every creature they can give needs its model here (CREATURE-ROOM-LEVELLED-54)
    used = A.table_list_order(lists, refs, A.room_levelled_roots(master))
    want = {b.casefold() for _, b, t, *_ in refs if t == 'CREA'}
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
                   (b.casefold() not in residents or (town_refs is not None and n not in town_refs))})
    return meshes, bipedal, {m: sorted(v) for m, v in scales.items()}, npcs, planned, corpses


def room_only_meshes(master, meshes):
    """The meshes of MESHES (plan's) that only the rooms' levelled lists reach (no exterior reference or exterior
    list gives them): they are baked with the skeletal method (one rest frame on the creature's own table, about a
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
    creature_jobs = max(1, a.jobs // 4) if a.jobs > 1 else 1
    npc_jobs = max(1, a.jobs - creature_jobs) if a.jobs > 1 else 1
    side = ThreadPoolExecutor(max_workers=1)
    creature_future = side.submit(L.bake, a.data_files, palette,
                                  {m: v for m, v in meshes.items() if m not in rooms_only}, id1, creature_jobs,
                                  a.creature_method, bipedal, scales if a.scaled_variants else None, corpses=corpses)
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
    texts = L.base_texts(library / 'creature-library.json')
    texts.update(NL.base_texts(library / 'npc-library.json'))
    return texts, copied


if __name__ == '__main__':
    main()
