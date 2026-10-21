# SPDX-License-Identifier: GPL-3.0-only
"""The actor library stage (EXPERIMENTAL; a build has this stage only with --chim-actor-table on; the image step
installs its models and gives the actor table their base texts; CHIM-EXTERIOR-ACTORS-MISSING-46).

Models for the exterior actors the town residents do not cover:
- every creature the exterior can show (its creature references and every creature its levelled lists can give):
  one standing and one mover model per creature mesh (tools/creature_library.py, method kf);
- every exterior NPC record that is not a resident of a CHIM town of this run (their models come from the town
  stages): one standing model per appearance (tools/npc_library.py).

Output: OUT/id1/progs (c_*.mdl, n_*.mdl and their .anm layouts), OUT/id1/sound (footstep sounds of the layouts),
OUT/creature-library.json, OUT/npc-library.json and OUT/actor-library.json (counts, bytes, left out with reasons).
Scaled references are drawn at their scale by the engine (U_AW_SCALE); --scaled-variants also bakes models at the
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
    out = set()
    for path in sorted(Path(run).glob('chim-town-*/residents.json')):
        out |= {k.casefold() for k in json.loads(path.read_text(encoding='utf-8')).get('models', {})}
    return out


def plan(master, residents=()):
    """(creature meshes {mesh: [ids]}, two-legged {mesh: bool}, scales {mesh: [scale]}, NPC ids) of the exterior."""
    from chim import actors as A
    import creature_library as L
    refs = A.exterior_actors(master)
    lists, creatures = A.levelled_lists(master), A.creature_ids(master)
    used = A.used_lists(lists, {b.casefold() for _, b, t, *_ in refs if t == 'LEVC'})
    want = {b.casefold() for _, b, t, *_ in refs if t == 'CREA'}
    for lid in used:
        want |= {e for e, _ in lists[lid][2] if e in creatures}
    planned = L.plan(master)
    meshes, bipedal = {}, {}
    for ident in sorted(want):
        b = planned['bases'].get(ident)
        if b and not b['dead'] and b['mesh']:
            meshes.setdefault(b['mesh'], []).append(ident)
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
    npcs = sorted({b.casefold() for _, b, t, *_ in refs if t == 'NPC_'} - set(residents))
    return meshes, bipedal, {m: sorted(v) for m, v in scales.items()}, npcs, planned


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--data-files', type=Path, required=True)
    p.add_argument('--palette', type=Path, required=True, help='the runtime palette (gfx/palette.lmp)')
    p.add_argument('--run', type=Path, help='the build run: its CHIM town stages name the residents to leave out')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--jobs', type=int, default=1)
    p.add_argument('--scaled-variants', action='store_true',
                   help='also bake creature models at the instance scales the exterior uses (the previous method)')
    a = p.parse_args(argv)
    path = list(sys.path)
    import creature_library as L
    import npc_library as NL
    sys.path[:] = path   # keep src/mwad ahead of tools/mwad.py whatever those imports did
    from mwad.paths import child_ci
    t0 = time.time()
    master = child_ci(a.data_files, 'Morrowind.esm').read_bytes()
    residents = town_residents(a.run) if a.run else set()
    meshes, bipedal, scales, npcs, planned = plan(master, residents)
    print('Actor library: %d creature meshes, %d NPC records (%d town residents left to the town stages), '
          '%d jobs' % (len(meshes), len(npcs), len(residents), a.jobs), flush=True)
    id1 = a.out / 'id1'
    id1.mkdir(parents=True, exist_ok=True)
    palette = a.palette.read_bytes()
    t1 = time.time()
    models, failed = L.bake(a.data_files, palette, meshes, id1, a.jobs, 'kf', bipedal,
                            scales if a.scaled_variants else None)
    creature_manifest = dict(L.manifest(planned, models), left_out=failed)
    (a.out / 'creature-library.json').write_text(json.dumps(creature_manifest, indent=1, sort_keys=True) + '\n',
                                                 encoding='utf-8', newline='\n')
    print('Actor library: creatures done - took %.1fs, %d models, %d left out' % (time.time() - t1, len(models),
                                                                                  len(failed)), flush=True)
    t2 = time.time()
    npc_manifest = NL.build(a.data_files, palette, npcs, id1, a.jobs)
    (a.out / 'npc-library.json').write_text(json.dumps(npc_manifest, indent=1, sort_keys=True) + '\n',
                                            encoding='utf-8', newline='\n')
    print('Actor library: NPCs done - took %.1fs, %d appearances, %d left out' % (
        time.time() - t2, len(npc_manifest['models']), len(npc_manifest['left_out'])), flush=True)
    summary = {'creature_meshes': len(meshes), 'creature_models': len(models), 'creature_left_out': failed,
               'creature_bytes': sum(m.get('standing_bytes', 0) + m.get('mover_bytes', 0) for m in models.values()),
               'npc_records': len(npcs), 'npc_appearances': len(npc_manifest['models']),
               'npc_left_out': npc_manifest['left_out'],
               'npc_bytes': sum(m['bytes'] for m in npc_manifest['models'].values()),
               'scaled_variants': bool(a.scaled_variants), 'town_residents_left_to_towns': len(residents),
               'seconds': round(time.time() - t0, 1)}
    (a.out / 'actor-library.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n', encoding='utf-8',
                                              newline='\n')
    print('Actor library: done - took %.1fs' % summary['seconds'], flush=True)


def install(library, id1):
    """Copy an actor library stage's models, layouts and sounds into an image's id1; returns the base texts
    {record id (or 'id@S'): entity text} of its creatures and NPCs for the actor table."""
    import shutil
    import creature_library as L
    import npc_library as NL
    library, id1 = Path(library), Path(id1)
    copied = 0
    for src in sorted((library / 'id1').rglob('*')):
        if src.is_file():
            dst = id1 / src.relative_to(library / 'id1')
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            copied += 1
    texts = L.base_texts(library / 'creature-library.json')
    texts.update(NL.base_texts(library / 'npc-library.json'))
    return texts, copied


if __name__ == '__main__':
    main()
