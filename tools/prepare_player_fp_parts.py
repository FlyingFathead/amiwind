#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The player's first-person arms assembled from parts by what is worn (docs/THIRD_PERSON.md "First-person arms";
PLAYER-GEAR-VISUAL-59, second slice).

The third-person body is assembled from parts (tools/prepare_player_parts.py); first person showed the baked bare
arms of the race and sex (tools/prepare_hand_catalog.py) whatever the hands wore. Here the same rule gives the arms:
the race's own hand, wrist, forearm and upper-arm parts (prepare_hands.appearance_parts: the first-person '.1st'
record first, then the third-person one, a woman then the man's, as the baked hands choose them), and over them the
parts the worn gloves, gauntlets, bracers, shirts and cuirasses give those slots, by the same ranks as the body.

Rules (read, not copied, from OpenMW 0.51 mwrender/npcanimation.cpp, which the baked hands follow too): first person
shows only the arm slots (hands, wrists, forearms, upper arms); for each part the record of the same id with '.1st'
appended is used when the game has one (the original's gauntlets and gloves have their own first-person meshes); the
first-person skeleton is meshes/base_anim.1st.nif. A robe shows its sleeves from its chest record's '.1st' (the
original's first-person robe mesh: chest shapes that hold only the sleeves, skinned to the arm bones) and covers the
forearms and upper arms under them; a robe without one leaves the arms as they are.

  id1/progs/humanoid_1st.awsk   the first-person table: the arms of base_anim.1st.nif (every finger joint: the hand
                                is seen close), 28 frames per stance in the baked hands' frame contract (prepare_hands
                                stance_clips: idle 8, draw 6, lower 4, punch 10) for the four stances in the engine's
                                order (bare hands, one-handed, two-handed close, two-handed wide; then bow, crossbow,
                                thrown and, last, the held light: the bare hands with the left arm on the original's
                                torch group, which a candle, candlestick or lantern takes). The root carries the
                                view: each stance's frames are taken from its first frame's Camera and turned to the
                                view axes, as prepare_hands bakes the arms, so a posed part is in view space and the
                                Weapon Bone tags of gfx/hand-weapons.aww place the weapon on it unchanged.
  id1/progs/parts/<2>/<10>.mdl  one skeletal model per (first-person skeleton, slot, mesh) (prepare_player_parts
                                part_path; the skeleton is in the key, so none is shared with the body's)
  id1/view/parts_1st.txt        the recipe (AWPP1, the body's format and reader, engine aw_player_parts.c): one
                                skeleton 'h' for every race (the baked hands use the one skeleton for all), the
                                races' skins, the items' first-person parts; '-/-' leaves the part under it showing.

Each part is a unit of the image unit cache ('player-fp-parts'). A part's triangles are capped by its slot (FP_CAP),
about the baked bare arms' own count, which keep the authored topology."""
import hashlib
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

FP_SKELETON = 'meshes/base_anim.1st.nif'
FP_TABLE = 'progs/humanoid_1st.awsk'
FP_RECIPE = 'view/parts_1st.txt'
UNIT_CACHE = 'player-fp-parts'
# the arm slots (mwad.npc.PART_NAMES): hands 6/7, wrists 8/9, forearms 11/12, upper arms 13/14
FP_SLOTS = (6, 7, 8, 9, 11, 12, 13, 14)
SLEEVES = (11, 12, 13, 14)
CHEST = 3
# the table's groups in the engine's stance order (aw_hand_models.c AW_HandStance + 1; 0 the bare hands)
STANCES = ('hh', '1h', '2c', '2w', 'bow', 'xb', '1t')     # the ranged three since v0.0.61 (FIRST-PERSON-WEAPONS-56)
# after them the held light (HELD-LIGHT-OWN-MODEL-61): the engine's stance 7 (aw_view.c HAND_PART_LIGHT)
LIGHT_STANCE = 'light'
FRAMES = 28
# triangles per part by slot: the baked bare arms of a man keep about 700 of the source's (authored topology)
FP_CAP = {3: 160, 6: 320, 7: 320, 8: 48, 9: 48, 11: 120, 12: 120, 13: 80, 14: 80}
ROBE_RANK = 24
# a part keeps its authored (shared) vertices up to this many times its slot's cap of triangles; past it, the reduction
SOURCE_FACES = 2
# the view axes the baked hands use (prepare_hands: x = y, y = -x, z = z of the skeleton): p @ VIEW_AXES
VIEW_AXES = ((0.0, -1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))


def fp_bones(skeleton):
    """The table's bones of the first-person skeleton (its parents {name: parent}): the root, the neck and every
    bone of both arms from the clavicle down (all finger joints, the shield and weapon bones); attachment nodes
    ('left hand') ride their bone (skeletal_actor.onto_kept)."""
    parents = skeleton.parents if hasattr(skeleton, 'parents') else skeleton
    keep = []
    for name in parents:
        n = name
        while n is not None and n not in ('bip01 l clavicle', 'bip01 r clavicle'):
            n = parents[n]
        if n is not None and (name.startswith('bip01 ') or name in ('shield bone', 'weapon bone')):
            keep.append(name)
    return tuple([n for n in ('bip01', 'bip01 neck') if n in parents and n not in keep] + keep)


def view_matrix(camera):
    """4 x 4 row-vector matrix: a skeleton point p to the view space of a camera at CAMERA (skeleton units):
    (p - camera) @ VIEW_AXES."""
    import numpy as np
    axes = np.array(VIEW_AXES)
    m = np.eye(4)
    m[:3, :3] = axes
    m[3, :3] = -np.asarray(camera, float) @ axes
    return m


def stance_times(skeleton):
    """[(stance, its 28 sample times)] in table order (prepare_hands.sample_clips: the baked hands' times)."""
    from prepare_hands import sample_clips
    return [(s, [float(t) for t in sample_clips(skeleton.events, s)[0]]) for s in STANCES]


def camera_at(skeleton, t):
    import numpy as np
    return np.asarray(skeleton.pose(float(t))('camera'), float)[3, :3]


def light_times(skeleton, count=FRAMES):
    """The left arm's sample times of the light stance (HELD-LIGHT-OWN-MODEL-61): the original's first-person torch
    group (base_anim.1st.nif 'torch: start'..'torch: stop', the hold prepare_torch bakes in 8 phases), its 8 phases in
    turn over the stance's 28 frames."""
    start, stop = skeleton.events.get('torch: start'), skeleton.events.get('torch: stop')
    if start is None or stop is None or not stop > start:
        raise ValueError('The first-person skeleton has no torch group')
    return [float(start + (i % 8) / 8.0 * (stop - start)) for i in range(count)]


def left_arm(parents, bones):
    """The indices of the table's bones from the left clavicle down (the arm the carried light takes)."""
    out = set()
    for i, name in enumerate(bones):
        n = name
        while n is not None and n != 'bip01 l clavicle':
            n = parents.get(n)
        if n is not None:
            out.add(i)
    return sorted(out)


def fp_table(skeleton):
    """(table bytes, bone names, the bare hands' view matrix, the table's sample times): the first-person table of
    the skeleton (npc_geometry.Skeleton of base_anim.1st.nif). After the weapon stances the light stance
    (LIGHT_STANCE, HELD-LIGHT-OWN-MODEL-61): the bare hands' 28 frames with the left arm on the torch group, as the
    original layers a carried light over the hands."""
    import numpy as np
    import skeletal_actor as sa
    keep = fp_bones(skeleton)
    kept = sa.KeptSkeleton(skeleton, keep)
    bones = list(kept.nodes)
    parents = [-1 if kept.parents[b] is None else bones.index(kept.parents[b]) for b in bones]
    times, groups, views = [], {}, []
    for stance, t in stance_times(skeleton):
        if len(t) != FRAMES:
            raise ValueError('First-person stance %s has %d frames, not %d' % (stance, len(t), FRAMES))
        groups[stance] = (len(times), len(times) + FRAMES - 1)
        views.extend([view_matrix(camera_at(skeleton, t[0]))] * FRAMES)
        times.extend(t)
    rot, pos = sa.sample_table(kept, bones, times)
    hands = stance_times(skeleton)[0][1]
    groups[LIGHT_STANCE] = (len(times), len(times) + FRAMES - 1)
    views.extend([view_matrix(camera_at(skeleton, hands[0]))] * FRAMES)
    times.extend(hands)
    lrot, lpos = sa.sample_table(kept, bones, hands)
    trot, tpos = sa.sample_table(kept, bones, light_times(skeleton))
    arm = left_arm(kept.parents, bones)
    lrot[:, arm], lpos[:, arm] = trot[:, arm], tpos[:, arm]
    rot, pos = np.concatenate((rot, lrot)), np.concatenate((pos, lpos))
    for f, view in enumerate(views):
        for b, parent in enumerate(parents):
            if parent < 0:
                m = sa.local_matrix(rot[f, b], pos[f, b]) @ view
                rot[f, b] = sa.matrix_to_quat(m[:3, :3])
                pos[f, b] = m[3, :3]
    for f in range(1, len(times)):          # the shorter way between neighbouring frames (build_table's rule)
        flip = np.einsum('bi,bi->b', rot[f], rot[f - 1]) < 0
        rot[f, flip] = -rot[f, flip]
    q, p, scale = sa.quantise_table(rot, pos)
    data = sa.write_table(parents, groups, q, p, scale, sa.TABLE_RATE, sa.POSITION_TOLERANCE)
    return data, bones, views[0], times


def first_person_id(bodies, body):
    """The record a part of BODY shows in first person: BODY + '.1st' when the game has it, else BODY (ids
    case-folded; None stays None). bodies: {case-folded id: id}."""
    if not body:
        return None
    return bodies.get(body.casefold() + '.1st') or bodies.get(body.casefold())


def fp_item_rows(kinds, items=None):
    """The worn items' first-person parts: per item its rank and per arm slot [male, female] body ids (their '.1st'
    records where the game has them). A robe whose chest record has a '.1st' shows it in the chest slot (CHEST: the
    original's first-person robe mesh holds only the sleeves, skinned to the arm bones) and covers the forearms and
    upper arms under them (None: nothing shows, the robe's cover of the body); an explicit arm part of its own first.
    Items without an arm part are left out (they leave the arms as they are)."""
    import prepare_player_parts as ppp
    bodies = {b.casefold(): b for b in kinds.get('BODY', {})}
    out = []
    for row in (items if items is not None else ppp.item_rows(kinds)):
        slots = {}
        for s, pair in sorted(row['slots'].items()):
            if s in FP_SLOTS and pair and (pair[0] or pair[1]):
                slots[s] = [first_person_id(bodies, pair[0]), first_person_id(bodies, pair[1])]
        if row['rank'] == ROBE_RANK and (row['slots'].get(CHEST) or [None])[0]:
            male, female = row['slots'][CHEST]
            sleeve = [bodies.get((b or '').casefold() + '.1st') for b in (male, female)]
            if sleeve[0] or sleeve[1]:
                slots[CHEST] = sleeve
                for s in SLEEVES:
                    slots.setdefault(s, None)
        if slots:
            out.append({'id': row['id'], 'kind': row['kind'], 'rank': row['rank'], 'slots': slots})
    return out


def race_skins(kinds):
    """Per playable race and sex its arm skin parts (prepare_hands.appearance_parts, the baked hands' choice):
    [{'race', 'female', 'skin': {slot: body id}, 'mesh': {body id: mesh}}]."""
    from prepare_hands import appearance_parts
    from prepare_player_view import playable_races
    rows = []
    for race in playable_races(kinds):
        for female in (False, True):
            parts = appearance_parts(kinds, race, female)
            rows.append({'race': race, 'female': female,
                         'skin': {p['slot']: p['id'] for p in parts if p['slot'] in FP_SLOTS},
                         'mesh': {p['id']: p['mesh'] for p in parts}})
    return rows


def recipe_text(races, items, models, bones):
    """The first-person recipe (AWPP1, the body's format: tools/prepare_player_parts.py recipe_text, read by the
    engine's aw_player_parts.c): one table 'h', no groups ('-'), every race at the unit scale, its skin per slot, the
    items' parts per slot as '<hex>/-' (no beast column), '-/-' where a part has no model (the one under it shows).
    models {(slot, body id): part path}; bones (weapon bone, shield bone) of the table."""
    from prepare_player_parts import part_hex

    def word(s):
        if any(c in s for c in '\t\n=,|') or not s.isascii():
            raise ValueError('Recipe id not plain ASCII: ' + s)
        return s.replace(' ', '|')
    lines = ['AWPP1', 'T h %s %d %d' % (FP_TABLE, bones[0], bones[1]), 'A h 0 -', 'A h 1 -']
    words = {}
    for item in items:
        if words.setdefault(word(item['id']), item['id']) != item['id']:
            raise ValueError('Two items share the recipe word %s' % word(item['id']))
    for r in races:
        race, f = word(r['race']), int(r['female'])
        lines.append('R %s %d h 1.0000 1.0000' % (race, f))
        for slot, body in sorted(r['skin'].items()):
            if (slot, body) in models:
                lines.append('S %s %d %d %s' % (race, f, slot, part_hex(models[(slot, body)])))
    for item in items:
        sides = []
        for slot, pair in sorted(item['slots'].items()):
            if pair is None:                              # covered: nothing shows (a robe over the arms)
                sides.append('%d=-,-' % slot)
                continue
            cols = []
            for body in (pair[0], pair[1] or pair[0]):    # a woman wears the man's part where none is hers
                path = models.get((slot, body)) if body else None
                cols.append('%s/-' % part_hex(path) if path else '-/-')
            sides.append('%d=%s' % (slot, ','.join(cols)))
        lines.append('I %s %d %s' % (word(item['id']), item['rank'], ' '.join(sides)))
    return '\n'.join(lines) + '\n'


# ---------------------------------------------------------------- one part (a pool unit)

_rig = {}


def _fp_rig(assets):
    """(skeleton, table bytes, bone names, the bare hands' view matrix, the bare hands' times), once per process."""
    if 'rig' not in _rig:
        from npc_geometry import Skeleton
        rig = Skeleton(assets, FP_SKELETON)
        table, bones, view, _ = fp_table(rig)
        _rig['rig'] = (rig, table, bones, view, stance_times(rig)[0][1])
    return _rig['rig']


def bake_part(task):
    """Worker: one first-person part model. task = (data, palette, part, cap). Returns (path, mdl bytes, report)."""
    import numpy as np
    import prepare_player_view as ppv
    import skeletal_actor as sa
    from npc_geometry import assemble
    from prepare_player_parts import part_path, quotas_for
    data, palette, part, cap = task
    kinds, assets, _ = ppv._sources(data)
    rig, table, bones, view, times = _fp_rig(assets)
    appearance = {'id': 'first-person part ' + part['id'], 'skeleton': FP_SKELETON, 'female': False, 'weight': 1.0,
                  'height': 1.0, 'parts': [part]}
    shapes, materials, textures = assemble(assets, appearance, rig, times)
    if not shapes:
        raise ValueError('Part %s (%s) has no drawn shape' % (part['id'], part['mesh']))
    # into the view space as the baked hands (prepare_hands: model units, the camera at the first frame)
    for shape in shapes:
        shape['positions'] = np.asarray(shape['positions'], float) @ view[:3, :3] + view[3, :3] * .25
    sources = sa.export_actor(assets, appearance, rig)
    rest = rig.pose(float(times[0]))

    def rest_world(name):
        return np.asarray(rest(name), float) @ view
    common = (shapes, materials, textures, palette, sources, rest_world, [.25, .25, .25], table, bones)
    try:
        # the authored vertices, shared (FP-ARMS-PARTS-COST-59): the baked arms keep the source topology too; the
        # face-tile reduction gave every triangle its own three vertices, about three times the baked arms' count
        raw, facts = sa.skeletal_from_shapes(*common, table_path=FP_TABLE, parents=rig.parents, topology='source')
        if facts['faces'] > SOURCE_FACES * cap:
            raise ValueError('source topology past %d x the slot cap' % SOURCE_FACES)
    except ValueError:
        # a part the shared encoding cannot take (past its bounds, translucent, or much past the slot's cap)
        raw, facts = sa.skeletal_from_shapes(*common, table_path=FP_TABLE, budgets=(cap,),
                                             quotas=quotas_for(shapes, cap), head_detail='budget',
                                             body_skin_rows=480, parents=rig.parents)
    out = part_path(FP_SKELETON, part)
    return out, raw, {'id': part['id'], 'slot': part['slot'], 'mesh': part['mesh'], 'skeleton': FP_SKELETON,
                      'model': out, 'bytes': len(raw), 'faces': facts['faces'], 'vertices': facts['vertices'],
                      'topology': facts['topology'],
                      'sha256': hashlib.sha256(raw).hexdigest()}


def _safe_bake(task):
    """bake_part; a part that cannot be baked is named and left out (the part under it shows)."""
    try:
        return bake_part(task)
    except Exception as error:  # noqa: BLE001  (named in the report; the slot falls back)
        return 'FAILED %s: %s: %s' % (unit_inputs(task)['entry']['name'], type(error).__name__, error)


def unit_inputs(task):
    data, palette, part, cap = task
    # a part's skin block names the table's frame count (aw_skel_load.c refuses a part whose count differs), so the
    # table's frames are part of the key: the light stance (v0.0.61) made every part again once
    return {'entry': {'name': 'first-person part %d %s' % (part['slot'], part['id'])}, 'skeleton': FP_SKELETON,
            'part': part, 'cap': cap, 'palette_sha256': hashlib.sha256(palette).hexdigest(),
            'table_frames': FRAMES * (len(STANCES) + 1)}


def _unit_cache():
    from pass_cache import UnitCache, game_data_digest
    game = game_data_digest()
    if game is None:
        return None
    import skeletal_actor
    import npc_geometry
    import prepare_hands
    return UnitCache.open(UNIT_CACHE, {'game_data': game}, __file__, skeletal_actor.__file__, npc_geometry.__file__,
                          prepare_hands.__file__)


# ---------------------------------------------------------------- the stage

def prepare(data, id1, palette, jobs=None, log=print):
    """Bake the first-person parts, the table and the recipe into ID1. Returns the report."""
    import prepare_player_view as ppv
    from build_parallel import stage_pool
    from mwad.npc import text
    from pass_cache import forced
    from prepare_player_parts import part_dict, part_path, write_same
    started = time.monotonic()
    kinds, assets, _ = ppv._sources(data)
    races = race_skins(kinds)
    items = fp_item_rows(kinds)
    need = set()
    for r in races:
        need.update(r['skin'].items())
    for item in items:
        for slot, pair in item['slots'].items():
            need.update((slot, b) for b in (pair or ()) if b)
    tasks = []
    for slot, body in sorted(need):
        record = kinds['BODY'].get(body)
        mesh = text(record, 'MODL') if record is not None else None
        if mesh:
            tasks.append((str(data), palette, part_dict(slot, body, mesh), FP_CAP.get(slot, 64)))
    unique = {}
    for t in tasks:
        unique.setdefault(part_path(FP_SKELETON, t[2]), t)
    log('=== PHASE 1/3: first-person parts: %d part uses, %d models to bake or reuse ===' % (len(tasks), len(unique)),
        flush=True)
    cache = _unit_cache()
    todo, results, failed = [], {}, []
    for path, t in unique.items():
        found = None
        if cache is not None and not forced(UNIT_CACHE, unit_inputs(t)['entry']['name']):
            found = cache.load_unit(unit_inputs(t))
        if found is not None:
            row, files = found
            results[path] = (files['0'], row['report'])
        else:
            todo.append(t)
    reused = len(results)
    if todo:
        import unit_store
        from build_jobs import resolve_jobs
        workers = max(1, min(resolve_jobs(jobs), len(todo)))
        names = [unit_inputs(t)['entry']['name'] for t in todo]
        log('first-person parts: %d to bake on %d workers' % (len(todo), workers), flush=True)

        def keep(index, result):
            # each part into the unit cache the moment it is back (UNIT-STORED-AT-MAP-END-62)
            if isinstance(result, str):
                failed.append(result)
                return
            path, raw, report = result
            results[path] = (raw, report)
            if cache is not None:
                cache.store_files(unit_inputs(todo[index]), {'report': report}, {'0': raw})
        with stage_pool(jobs, 'first-person parts'):
            failed.extend(unit_store.run_each('player-fp-parts', _safe_bake, list(enumerate(todo)), names, workers,
                                              keep, fallback=lambda name: 1.0, label='First-person parts',
                                              already=reused, log=log))
    log('=== PHASE 2/3: first-person parts: the table ===', flush=True)
    models = {}
    for path in unique:
        if path in results:
            write_same(Path(id1) / path, results[path][0])
    for t in tasks:
        path = part_path(FP_SKELETON, t[2])
        if path in results:
            models[(t[2]['slot'], t[2]['id'])] = path
    rig, table, bones, _, _ = _fp_rig(assets)
    write_same(Path(id1) / FP_TABLE, table)
    names = [b.casefold() for b in bones]
    item_bones = (names.index('weapon bone') if 'weapon bone' in names else -1,
                  names.index('shield bone') if 'shield bone' in names else -1)
    log('=== PHASE 3/3: first-person parts: the recipe ===', flush=True)
    recipe = recipe_text(races, items, models, item_bones)
    (Path(id1) / FP_RECIPE).parent.mkdir(parents=True, exist_ok=True)
    (Path(id1) / FP_RECIPE).write_text(recipe, encoding='ascii', newline='\n')
    sizes = [r[1]['bytes'] for r in results.values()]
    faces = [r[1]['faces'] for r in results.values()]
    report = {'models': len(results), 'reused': reused, 'made': len(results) - reused, 'failed': failed,
              'bytes': sum(sizes), 'faces_median': sorted(faces)[len(faces) // 2] if faces else 0,
              'vertices': sum(r[1]['vertices'] for r in results.values()),
              'source_topology': sum(r[1].get('topology') == 'source' for r in results.values()),
              'table': FP_TABLE, 'table_bytes': len(table), 'table_bones': len(bones),
              'recipe_sha256': hashlib.sha256(recipe.encode('ascii')).hexdigest(), 'items': len(items),
              'races': len(races), 'seconds': round(time.monotonic() - started, 1)}
    log('First-person parts: %d models (%d reused, %d made, %d failed), %.1f MB, %d items, table %d bytes, %.1f s' % (
        report['models'], reused, report['made'], len(failed), report['bytes'] / 1e6, len(items), len(table),
        report['seconds']), flush=True)
    return report


def image_step(data_files, id1, out, jobs=None):
    """The image step's phase (tools/build_aga.py, after the player view; not with --no-player-body): the arm parts
    on the palette the body's parts use (prepare_player_view.prepare_image), the report as OUT/player-fp-parts.json.
    The baked arms of the hand catalogue stay for aw_hand_parts 0, the carried torch and the shield guard."""
    import json
    import build_profile
    from mwad.paths import resolve_data_files
    print('Converting the first-person arm parts (gloves, gauntlets, bracers, sleeves)...', flush=True)
    with build_profile.phase('Image: first-person parts', detail='after the player view'):
        report = prepare(resolve_data_files(Path(data_files)), Path(id1),
                         (Path(id1) / 'gfx/palette.lmp').read_bytes(), jobs=jobs)
    (Path(out) / 'player-fp-parts.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8',
                                                     newline='\n')
    return report
