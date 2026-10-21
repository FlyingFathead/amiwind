# SPDX-License-Identifier: GPL-3.0-only
"""NPC standing models for the outdoor NPCs outside the towns (EXPERIMENTAL; the actor library stage, only with
--chim-actor-table on; CHIM-EXTERIOR-ACTORS-MISSING-46).

The resident stage bakes models for the town residents only. The actor table also lists the exterior NPC
references of the rest of the island; this module gives them a model, one per APPEARANCE (the outfit's parts,
skeleton, height, weight, sex, attack stance and whether the NPC starts dead: everything the bake reads), so two
records that look the same share one model. The bake is the resident stage's own (tools/prepare_area.py
build_resident, the animation kit branch, the standing model only), repeated here step by step because that
module's stage key must not change; tests and the measurement compare its bytes with build_resident's on the same
appearance.

What it does not do: no mover model (the moving frames; the standing model's layout names none), no carried items
(weapons, shields: npc_items), no greeting voice or dialogue lines (aw_voice and aw_line empty, hello distance 0), no
near/far levels of detail. The support state is the grounding policy's when it names the NPC, else on the ground.
"""
import hashlib
import json
from pathlib import Path

FORMAT = 'AmiWind NPC standing library 1'
_assets, _rigs, _sounds = {}, {}, {}


def appearance_key(appearance, profile):
    """SHA-256 (16 hex) of everything the standing bake reads of an appearance, the root rule and the profile."""
    from npc_geometry import get_root_rule
    from mesh_geometry_env import npc_head_detail, npc_head_reducer
    spec = {k: appearance.get(k) for k in ('parts', 'skeleton', 'height', 'weight', 'female', 'attack_stance',
                                            'initially_dead')}
    # the build's head settings reach the bake through the environment (tools/build.py exports them)
    spec.update(root_rule=appearance.get('root_rule') or get_root_rule(), profile=profile,
                head_detail=npc_head_detail(), head_reducer=npc_head_reducer())
    return hashlib.sha256(json.dumps(spec, sort_keys=True, default=str).encode()).hexdigest()[:16]


def model_path(key):
    return 'progs/n_%s.mdl' % key


def standing_profile():
    """The build's animation profile (AMIWIND_NPC_ANIM, e.g. 'react+full'): the standing model is baked as the
    resident stage bakes it under that profile (with a mover profile, the standing frames are a subset of the
    mover's bake, as the town residents' are), and only the standing model is kept."""
    import npc_anim
    name, _ = npc_anim.selected_profile()
    npc_anim.split_profile(name)
    return name


def appearances(kinds, ids):
    """{npc id: appearance} as the resident stage makes them (prepare_area populate: outfit, carried items' stance,
    initially dead, foot class). An NPC whose outfit does not resolve is left out with the reason."""
    import struct
    import npc_items
    from mwad.npc import outfit, first
    from npc_anim import foot_class
    out, left = {}, {}
    for identifier in sorted(ids):
        try:
            app = npc_items.attach_items(kinds, identifier, outfit(kinds, identifier))
        except (ValueError, KeyError) as error:
            left[identifier] = str(error)
            continue
        stats = first(kinds['NPC_'][identifier], 'NPDT')
        app['initially_dead'] = len(stats) == 52 and struct.unpack_from('<h', stats, 38)[0] <= 0
        app['foot'] = foot_class(kinds, app)
        out[identifier] = app
    return out, left


def bake_standing(task):
    """(model bytes, layout, sounds {name: bytes}, facts) of one appearance: build_resident's animation kit branch
    with profile PROFILE ('react+full', 'react', ...; 'idle' = its idle-only branch), the standing model only."""
    import numpy as np
    import npc_anim
    from mwad.audit import BSA
    from mwad.paths import child_ci
    from npc_geometry import Assets, Skeleton, assemble, bake, animated_mdl
    data, palette, appearance, profile_name = task
    data = Path(data)
    key = str(data.resolve())
    if key not in _assets:
        _assets[key] = Assets(data, BSA(child_ci(data, 'Morrowind.bsa')))
    assets = _assets[key]
    rig = (key, appearance['skeleton'])
    if rig not in _rigs:
        _rigs[rig] = Skeleton(assets, appearance['skeleton'])
    skeleton = _rigs[rig]
    dead = appearance.get('initially_dead', False)
    kit = None
    if dead:
        times, step = np.array([skeleton.events['death1: stop']]), 0.
    elif profile_name == 'idle':
        times, step = skeleton.idle_times(8)
    else:
        female = None
        if appearance.get('female') and appearance['skeleton'] == 'meshes/base_anim.nif':
            rig = (key, npc_anim.FEMALE_SKELETON)
            if rig not in _rigs:
                _rigs[rig] = Skeleton(assets, npc_anim.FEMALE_SKELETON)
            female = _rigs[rig]
        kit, groups = npc_anim.plan(skeleton, npc_anim.plan_profile(profile_name), female,
                                    appearance.get('weight', 1.), attack_stance=appearance.get('attack_stance'))
        times = npc_anim.idle_compatible_times(groups)
        step = groups[0]['step']
    shapes, materials, textures = assemble(assets, appearance, kit or skeleton, times)
    for budget in (480, 384, 320, 256, 192):
        try:
            frames, faces, uv, skin = bake(shapes, materials, textures, palette, budget=budget,
                                           reference_frames=8 if kit else None,
                                           full_frame_budget=npc_anim.ALIAS_BYTE_BUDGET if kit else None)
            break
        except ValueError as error:
            if str(error) not in ('Alias vertex budget exceeded', 'Alias byte budget exceeded with full samples') \
                    or budget == 192:
                raise ValueError(appearance['id'] + ': ' + str(error)) from error
    layout, sounds = '', {}
    if kit:
        nv, nt, (sw, sh) = frames.shape[1], len(faces), skin.size
        standing_name, mover_name = npc_anim.split_profile(profile_name)
        if mover_name:
            keep = {g['name']: g['count'] for g in groups if g['name'] in dict(npc_anim.profiles()[standing_name])}
            standing_groups, standing_index = npc_anim.select(groups, keep)
        else:
            standing_groups, standing_index = npc_anim.fit(groups, nv, nt, sw, sh)
        names = [g['name'] + '%02d' % i for g in standing_groups for i in range(g['count'])]
        raw = animated_mdl(frames[standing_index], faces, uv, skin, names=names)
        foot = appearance.get('foot', 'bare')
        if key not in _sounds:
            _sounds[key] = npc_anim.soun_records(child_ci(data, 'Morrowind.esm'))
        layout = npc_anim.layout(standing_groups, foot)
        sounds = npc_anim.sound_payload(assets, _sounds[key], npc_anim.needed_sounds(standing_groups, foot))
        nframes = len(standing_index)
    else:
        raw = animated_mdl(frames, faces, uv, skin)
        nframes = len(frames)
    facts = {'bytes': len(raw), 'frames': nframes, 'triangles': int(len(faces)), 'vertices': int(frames.shape[1]),
             'skin': list(skin.size), 'step': float(step), 'sha256': hashlib.sha256(raw).hexdigest()}
    return raw, layout, sounds, facts


def _unit(task):
    """Worker: one appearance (key, ids, appearance) -> (key, result or None, seconds, error)."""
    import time
    key, data, palette, appearance, profile = task
    t0 = time.time()
    try:
        return key, bake_standing((data, palette, appearance, profile)), time.time() - t0, None
    except Exception as error:  # noqa: BLE001 (each failure is reported with its appearance)
        return key, None, time.time() - t0, '%s: %s' % (type(error).__name__, error)


def build(data, palette, ids, out_id1, jobs=1, kinds=None):
    """Bake the standing models of the NPC records IDS into OUT_ID1 (progs/n_<key>.mdl + .anm, sound/...); returns
    the manifest {'format', 'profile', 'models': {key: facts + model}, 'npcs': {id: {key, name, dead}},
    'left_out': {id or key: reason}}."""
    from build_parallel import ordered_map
    from mwad.npc import load_master, text
    from mwad.paths import child_ci
    data = Path(data)
    if kinds is None:
        kinds, _, _ = load_master(child_ci(data, 'Morrowind.esm'))
    profile = standing_profile()
    apps, left = appearances(kinds, ids)
    groups = {}
    for identifier, app in apps.items():
        groups.setdefault(appearance_key(app, profile), []).append(identifier)
    tasks = [(k, data, palette, apps[v[0]], profile) for k, v in sorted(groups.items())]
    print('NPC library: %d NPC records, %d appearances, profile %s, %d jobs' % (
        len(apps), len(tasks), profile, jobs), flush=True)
    models = {}
    for key, result, seconds, error in ordered_map(_unit, tasks, jobs=max(1, jobs)):
        if result is None:
            left[key] = error
            print('NPC library: appearance %s (%s) left out: %s' % (key, groups[key][0], error), flush=True)
            continue
        raw, layout, sounds, facts = result
        path = model_path(key)
        target = Path(out_id1) / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        if layout:
            target.with_suffix('.anm').write_text(layout + '\n', encoding='ascii', newline='\n')
        for name, sound in sorted(sounds.items()):
            s = Path(out_id1) / 'sound' / name
            s.parent.mkdir(parents=True, exist_ok=True)
            if not s.exists() or s.read_bytes() != sound:
                s.write_bytes(sound)
        models[key] = dict(facts, model=path, seconds=round(seconds, 2))
        print('NPC library: %s -> %s (%d bytes, %d frames, %.1f s)' % (groups[key][0], path, facts['bytes'],
                                                                         facts['frames'], seconds), flush=True)
    npcs = {}
    for key, idents in groups.items():
        if key in models:
            for i in idents:
                npcs[i] = {'key': key, 'name': text(kinds['NPC_'][i], 'FNAM') or i,
                           'dead': bool(apps[i].get('initially_dead'))}
    return {'format': FORMAT, 'profile': profile, 'models': models, 'npcs': npcs, 'left_out': left}


def entity_text(ident, npc, model):
    """An NPC base's entity text: the resident row's fields (prepare_area populate) without the per-placement ones
    and without voice, greeting and dialogue (not made here)."""
    try:
        from actor_grounding import fields as grounding_fields
        ground = grounding_fields(ident)
    except ValueError:
        ground = {'aw_source_id': ident, 'aw_ground_mode': 0}

    def clean(t):
        return ''.join(c for c in t if c not in '"\n\r\0')
    fields = [('aw_source_id', ground['aw_source_id']), ('aw_ground_mode', str(ground['aw_ground_mode'])),
              ('classname', 'aw_corpse' if npc['dead'] else 'aw_npc'), ('model', model['model']),
              ('netname', clean(npc['name'])), ('aw_voice', ''), ('aw_line', ''),
              ('aw_idle_step', repr(float(model['step']))), ('aw_hello_distance', '0'), ('aw_hello_reset', '0'),
              ('aw_greet_duration', '0')]
    return ''.join('"%s" "%s"\n' % kv for kv in fields)


def base_texts(source):
    """{npc id: entity text} of a manifest (a dict or a JSON file)."""
    m = source if isinstance(source, dict) else json.loads(Path(source).read_text(encoding='utf-8'))
    if m.get('format') != FORMAT:
        raise ValueError('Not an NPC standing library manifest')
    return {i: entity_text(i, n, m['models'][n['key']]) for i, n in m['npcs'].items() if n['key'] in m['models']}
