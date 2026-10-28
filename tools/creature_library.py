# SPDX-License-Identifier: GPL-3.0-only
"""Creature model library (EXPERIMENTAL, not part of any default build; CHIM-EXTERIOR-ACTORS-MISSING-46).

A creature record (CREA) is drawn with its own NIF (its MODL), its own skeleton and its own keyframes; the record's
other fields (name, stats, behaviour, sounds) do not change the model. So one baked model per creature MESH serves every
creature record that uses it: the exterior of Vvardenfell has 81 creature bases (49 placed directly, 49 reachable
through its levelled lists at player levels 1 to 30) but only 39 distinct creature meshes (measured on the
maintainer's Morrowind.esm, 21 October 2026). The resident stage bakes a model per creature RECORD
(tools/prepare_area.py, a_<sha of the id>.mdl); this library keys it by the mesh (c_<sha of the mesh>.mdl).

- plan(master): every creature record's mesh, display name and support state, grouped by mesh;
- bake(...): the models of each mesh, in parallel, one unit per mesh (and instance scale): method 'kf' (default
  since v0.0.47) poses the creature's animated model with its keyframe files as the original reads them
  (tools/creature_pose.py: a standing model and a mover model with walk, run, attack, hit and death frames;
  CREATURE-BAKE-NIF-UNSUPPORTED-47); method 'resident' is the resident stage's own creature bake
  (creature_residents.bake_task: 8 frames of its idle group; the previous method);
- base_texts(manifest): the entity text of each creature base for the CHIM actor table (tools/chim/actors.py
  version 2): the fields a resident row has, without the per-placement ones.

Support state (aw_ground_mode): the grounding policy's class when config/actor_grounding.json names the creature,
else the creature record's movement flags (OpenMW 0.51 components/esm3/loadcrea.hpp: Swims 0x10, Flies 0x20, Walks
0x40): a creature that flies or swims and does not walk is not put on the ground. Authored-dead creatures (health
0: 'dead rat', 'netch_bull_dead', the dead guar of a mudcrab nest) get a corpse model per mesh: one frame, the last
key of the creature's own death group (creature_pose.CORPSE), drawn as an aw_corpse lying at its authored spot
(ACTOR-LIBRARY-LEFT-OUT-48; before v0.0.48 they got none and were dropped without a reason). A dead variant whose
record names its own mesh gets that mesh's corpse; one whose creature has no death group is left out with that reason.

What it does not do: creature sounds on the animation frames (footsteps, roars) are not converted; a scaled
reference needs its own model (bake SCALES); not wired into a build stage (the maintainer's go is needed for a build); its sizes were measured with a read-only
run on the real data, the models kept in a scratch folder only.
"""
import hashlib
import json
import struct
from pathlib import Path

FORMAT = 'AmiWind creature library 1'
SWIMS, FLIES, WALKS = 0x10, 0x20, 0x40


def model_path(mesh):
    return 'progs/c_%s.mdl' % hashlib.sha256(mesh.casefold().encode('utf-8')).hexdigest()[:12]


def plan(master):
    """{'bases': {id: {mesh, name, flags, ground_mode, dead}}, 'meshes': {mesh: [ids]}} of every creature record
    of the master's bytes."""
    from mwad.audit import normpath, records, string, subrecords
    bases = {}
    for tag, flags, payload in records(master):
        if tag != 'CREA' or flags & 0x20:
            continue
        fields = list(subrecords(payload))
        get = lambda name: next((d for t, d in fields if t == name), None)  # noqa: E731
        if get('NAME') is None or get('DELE') is not None:
            continue
        ident = string(get('NAME'), errors='replace').casefold()
        npdt = get('NPDT') or b''
        cflags = struct.unpack('<I', get('FLAG'))[0] if get('FLAG') else 0
        bases[ident] = {'mesh': normpath(string(get('MODL') or b'', errors='replace')),
                        'name': string(get('FNAM') or get('NAME'), errors='replace'),
                        'flags': cflags, 'ground_mode': ground_mode(ident, cflags),
                        'dead': len(npdt) == 96 and struct.unpack_from('<i', npdt, 40)[0] <= 0}
    meshes, corpses = {}, {}
    for ident in sorted(bases):
        if bases[ident]['mesh']:
            (corpses if bases[ident]['dead'] else meshes).setdefault(bases[ident]['mesh'], []).append(ident)
    return {'bases': bases, 'meshes': meshes, 'corpses': corpses}


CORPSE_KEY = '#dead'


def corpse_key(mesh):
    """The library key of a mesh's corpse model (an authored-dead creature: its death pose, one frame)."""
    return mesh + CORPSE_KEY


def corpse_path(mesh):
    return model_path(mesh)[:-4] + '_d.mdl'


def ground_mode(ident, flags):
    """1 (not put on the ground) or 0: the grounding policy's class when it names IDENT, else the record's flags."""
    try:
        from actor_grounding import initial_state
        return int(initial_state(ident) != 'ground')
    except ValueError:
        return int(bool(flags & (SWIMS | FLIES)) and not flags & WALKS)


# 'skeletal' (CREATURE-TABLES, v0.0.54): the creature's own animation table (tools/creature_tables.py: every group of
# its own files, OpenMW's source order) and one skeletal model on it; selectable, not the default until the
# in-game A/B against 'kf' is recorded (a new method is added beside the old, never in place of it).
METHODS = ('kf', 'resident', 'skeletal')
DEFAULT_METHOD = 'kf'


def variant_key(mesh, scale=1.0):
    """The library key of a model: the mesh, plus '@scale' for an instance scale other than 1."""
    return mesh if abs(scale - 1.0) < 1e-4 else '%s@%.4f' % (mesh, scale)


def variant_path(mesh, scale=1.0, mover=False):
    base = model_path(mesh)[:-4]
    if abs(scale - 1.0) >= 1e-4:
        base += '_s%03d' % int(round(scale * 100))
    return base + ('_m' if mover else '') + '.mdl'


def bake(data, palette, meshes, out_id1, jobs=1, method=DEFAULT_METHOD, bipedal=None, scales=None, corpses=None):
    """Bake every mesh in MESHES ({mesh: [creature ids]}, plan()['meshes']) into OUT_ID1/progs.

    method 'kf' (default): the creature's animated model and keyframe files as the original reads them
    (tools/creature_pose.py): a standing model (idle 8, hit 3, death 5 frames) and a mover model (idle, walk, run,
    attack, hit, death: 38 frames), each with its layout written beside it (<model>.anm, the NPC animation kit's
    format; the standing layout names the mover with '>'). method 'resident': the resident stage's creature bake
    (creature_residents.bake_task: 8 idle frames; kept, the previous method). BIPEDAL: {mesh: True} for meshes of
    two-legged creatures (they also take the shared xbase_anim.kf). SCALES: {mesh: [instance scales]} to bake
    besides 1 ('kf' only). CORPSES: {mesh: [creature ids]} of authored-dead creatures (plan()['corpses']): one
    corpse model per mesh, the last key of the creature's own death group (key corpse_key(mesh), 'kf' only).
    Returns {variant key: record} and {variant key: error} (left out with the reason)."""
    from build_parallel import ordered_map
    if method not in METHODS:
        raise ValueError('Unknown creature library method: ' + str(method))
    tasks = []
    for mesh, ids in sorted(meshes.items()):
        app = {'id': ids[0], 'kind': 'CREA', 'name': ids[0], 'mesh': mesh}
        for scale in [1.0] + sorted(set((scales or {}).get(mesh, ())) - {1.0}):
            if method in ('resident', 'skeletal') and scale != 1.0:
                continue        # 'skeletal': the engine scales a live actor (AWU_SCALE); one model per mesh
            tasks.append((method, data, palette, app, bool((bipedal or {}).get(mesh)), scale))
    for mesh, ids in sorted((corpses or {}).items()):
        app = {'id': ids[0], 'kind': 'CREA', 'name': ids[0], 'mesh': mesh}
        tasks.append(('corpse', data, palette, app, bool((bipedal or {}).get(mesh)), 1.0))
    done, failed = {}, {}
    for key, out, seconds, error in ordered_map(_unit, tasks, jobs=max(1, jobs)):
        if out is None:
            failed[key] = error
            print('Creature library: %s left out (%s)' % (key, error), flush=True)
            continue
        record = out['record']
        for role, raw, path in out['files']:
            target = Path(out_id1) / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        done[key] = dict(record, seconds=round(seconds, 2))
        print('Creature library: %s -> %s (%s, %.1f s)' % (key, record['model'], ', '.join(
            '%s %d bytes %d frames' % (r, record[r + '_bytes'], record[r + '_frames']) for r in record['roles']),
            seconds), flush=True)
    return done, failed


def _unit(task):
    """Worker (module level for the process pool): one mesh at one scale."""
    import time
    method, data, palette, app, bipedal, scale = task
    key = corpse_key(app['mesh']) if method == 'corpse' else variant_key(app['mesh'], scale)
    t0 = time.time()
    try:
        if method == 'corpse':
            out = bake_kf(data, palette, app, bipedal, corpse=True)
        elif method == 'skeletal':
            out = bake_skeletal(data, palette, app, bipedal)
        elif method == 'resident':
            import creature_residents
            _, raw, record = creature_residents.bake_task((data, palette, app))
            path = variant_path(app['mesh'])
            out = {'files': [('standing', raw, path)],
                   'record': {'model': path, 'roles': ['standing'], 'standing_bytes': len(raw),
                              'standing_frames': record['frames'], 'triangles': record['triangles'],
                              'step': record['step'], 'idle': record['idle']['group'], 'method': method,
                              'sha256': hashlib.sha256(raw).hexdigest()}}
        else:
            out = bake_kf(data, palette, app, bipedal, scale)
        return key, out, time.time() - t0, None
    except Exception as error:  # noqa: BLE001 (each failure is reported with its mesh)
        return key, None, time.time() - t0, '%s: %s' % (type(error).__name__, error)


_assets = {}


def bake_skeletal(data, palette, app, bipedal):
    """{'files': [(role, bytes, path)], 'record': {...}} of one mesh with the 'skeletal' method: its own table, one
    skeletal model on it and that model's layout (every engine group on the table's frames; tools/creature_tables.py).
    One model plays every group, so there is no separate mover (the layout names none)."""
    import creature_tables
    mesh, out, error = creature_tables.unit((app['mesh'], data, palette, bipedal, False))
    if out is None:
        raise ValueError(error)
    rep = out['report']
    files = [('table', out['table'], rep['table']), ('standing', out['model'], rep['model']),
             ('standing_layout', (out['layout'] + '\n').encode('ascii'), rep['model'][:-4] + '.anm')]
    idle_step = next((float(w.split(':')[3]) for w in out['layout'].split() if w.startswith('idle:')), 0.125)
    record = {'model': rep['model'], 'roles': ['standing'], 'method': 'skeletal', 'scale': 1.0,
              'animated_model': rep['animated_model'], 'sources': rep['sources'], 'table': rep['table'],
              'table_bytes': rep['table_bytes'], 'table_frames': rep['frames'], 'table_groups': len(rep['groups']),
              'standing_bytes': rep['model_bytes'], 'standing_frames': rep['frames'], 'triangles': rep['faces'],
              'vertices': rep['vertices'], 'step': idle_step, 'idle': 'idle', 'kit': rep['kit'],
              'scaled_bones': rep['scaled_bones'], 'repeated_node_names': rep['repeated_node_names'],
              'sha256': rep['model_sha256'], 'table_sha256': rep['table_sha256']}
    return {'files': files, 'record': record}


def bake_kf(data, palette, app, bipedal, scale=1.0, profile=None, corpse=False):
    """{'files': [(role, bytes, path)], 'record': {...}} of one mesh with the 'kf' method. corpse: the one-frame
    model of an authored-dead creature (creature_pose.CORPSE: the last key of its own death group)."""
    import numpy as np
    from mwad.audit import BSA, normpath
    from mwad.paths import child_ci
    from mwad.scene import unpack_geometry
    from npc_geometry import Assets, bake as bake_model, animated_mdl
    from prepare_scenery import model_geometry, nif_reader
    from prepare_gallery import quality_profiles
    import creature_pose
    import creature_residents
    root = str(Path(data).resolve())
    if root not in _assets:
        _assets[root] = Assets(Path(data), BSA(child_ci(Path(data), 'Morrowind.bsa')))
    assets = _assets[root]
    reader = nif_reader()
    rig = creature_pose.CreatureRig(reader, assets.read, app['mesh'], bipedal)
    samples, groups = rig.plan(creature_pose.CORPSE if corpse else (profile or creature_pose.MOVER))
    per_frame = []
    for source, time, fixed in samples:
        packet, materials, _bounds, _skipped = model_geometry(rig.raw, reader, repair_uv=True,
                                                              pose_world=rig.pose_world(source, time, fixed))
        vertices, faces, _ = unpack_geometry(packet)
        per_frame.append((np.array(vertices), np.array(faces, dtype=int), materials))
    v0, f0, materials = per_frame[0]
    for v, f, _ in per_frame[1:]:
        if v.shape != v0.shape or not np.array_equal(f, f0):
            raise ValueError('posed frames do not share one topology')
    shapes, textures = [], {}
    for i, material in enumerate(materials):
        selected = f0[f0[:, 3] == i, :3]
        if not len(selected):
            continue
        source = material.pop('texture_source')
        material['texture_index'] = source
        if source and source not in textures:
            textures[source] = assets.texture(source)
        used, remap = np.unique(selected, return_inverse=True)
        # Morrowind units to Quake units (0.25) times the instance scale; the source origin is kept.
        positions = np.stack([v[used, :3] * (.25 * scale) for v, _, _ in per_frame])
        shapes.append(dict(name=material['source_shape'], part=-1, positions=positions,
                           faces=remap.reshape(-1, 3), uv=v0[used, 3:5], colours=v0[used, 5:9] / 255, material=i))
    if not shapes:
        raise ValueError('no visible geometry')
    if corpse:
        # one frame: the creature's own death pose (its last key); a creature without a death group would stand,
        # so it is left out with that reason instead
        if any(g.get('source') == 'idle' for g in groups):
            raise ValueError('no death group in %s: no corpse pose to take' % ', '.join(s['name'] for s in rig.sources))
        profile = quality_profiles().get(normpath(app['mesh']))
        budgets = (profile['budget'],) if profile else creature_residents.BUDGETS
        for budget in budgets:
            try:
                frames, faces, uv, skin = bake_model(shapes, materials, textures, palette, budget=budget,
                                                     minimum_faces=(profile or {}).get('minimum_faces') or None)
                break
            except ValueError as error:
                if 'Alias' not in str(error) or budget == budgets[-1]:
                    raise
        raw = animated_mdl(frames, faces, uv, skin)
        path = corpse_path(app['mesh'])
        record = {'model': path, 'roles': ['corpse'], 'method': 'kf', 'scale': scale, 'corpse': True,
                  'animated_model': rig.model, 'sources': [s['name'] for s in rig.sources],
                  'corpse_bytes': len(raw), 'corpse_frames': int(frames.shape[0]), 'triangles': int(len(faces)),
                  'vertices': int(frames.shape[1]), 'skin': list(skin.size), 'step': 0.0, 'idle': 'death',
                  'pose': 'death group, last key (%s)' % groups[0]['source'],
                  'repeated_node_names': rig.duplicates, 'sha256': hashlib.sha256(raw).hexdigest()}
        return {'files': [('corpse', raw, path)], 'record': record}
    profile = quality_profiles().get(normpath(app['mesh']))
    budgets = (profile['budget'],) if profile else creature_residents.BUDGETS
    for budget in budgets:
        try:
            frames, faces, uv, skin = bake_model(shapes, materials, textures, palette, budget=budget,
                                                 minimum_faces=(profile or {}).get('minimum_faces') or None)
            mover = animated_mdl(frames, faces, uv, skin)
            break
        except ValueError as error:
            if 'Alias' not in str(error) or budget == budgets[-1]:
                raise
    # the standing model: the mover's idle, hit and death frames (the same topology, skin and texture coordinates)
    keep = {name for name, _ in creature_pose.STANDING}
    index, standing_groups = [], []
    for g in groups:
        if g['name'] in keep:
            standing_groups.append(dict(g, base=len(index)))
            index.extend(range(g['base'], g['base'] + g['count']))
    standing = animated_mdl(frames[index], faces, uv, skin)
    stand_path = variant_path(app['mesh'], scale)
    mover_path = variant_path(app['mesh'], scale, mover=True)
    files = [('standing', standing, stand_path), ('mover', mover, mover_path),
             ('standing_layout', (creature_pose.layout(standing_groups) + ' >' + mover_path + '\n').encode('ascii'),
              stand_path[:-4] + '.anm'),
             ('mover_layout', (creature_pose.layout(groups) + '\n').encode('ascii'), mover_path[:-4] + '.anm')]
    record = {'model': stand_path, 'mover': mover_path, 'roles': ['standing', 'mover'], 'method': 'kf',
              'scale': scale, 'animated_model': rig.model, 'sources': [s['name'] for s in rig.sources],
              'standing_bytes': len(standing), 'standing_frames': len(index), 'mover_bytes': len(mover),
              'mover_frames': int(frames.shape[0]), 'triangles': int(len(faces)), 'vertices': int(frames.shape[1]),
              'skin': list(skin.size), 'step': float(groups[0]['step']), 'idle': 'idle',
              'groups': [{k: g[k] for k in ('name', 'count', 'source') if k in g} for g in groups],
              'groups_from_idle': [g['name'] for g in groups if g.get('source') == 'idle'],
              'repeated_node_names': rig.duplicates,
              'sha256': hashlib.sha256(standing).hexdigest(), 'mover_sha256': hashlib.sha256(mover).hexdigest()}
    return {'files': files, 'record': record}


def manifest(planned, models):
    """The library manifest: the models and every base that has one (an authored-dead base: its mesh's corpse
    model, 'dead' true)."""
    bases = {}
    for i, b in planned['bases'].items():
        if b['dead'] and corpse_key(b['mesh']) in models:
            bases[i] = dict({k: b[k] for k in ('mesh', 'name', 'ground_mode')}, dead=True)
        elif not b['dead'] and b['mesh'] in models:
            bases[i] = {k: b[k] for k in ('mesh', 'name', 'ground_mode')}
    return {'format': FORMAT, 'models': models, 'bases': bases}


def entity_text(ident, base, model):
    """A creature base's entity text: a resident row's fields without the per-placement ones (origin, angles,
    aw_ref, aw_ground_baked/valid, aw_authored_*), in the order prepare_area writes them; no greeting (hello 0).
    An authored-dead base is an aw_corpse (its death pose, frame 0) kept at its authored spot (ground mode 1), as
    the NPC corpses (npc_library.entity_text)."""
    def clean(text):
        return ''.join(c for c in text if c not in '"\n\r\0')
    dead = bool(base.get('dead'))
    fields = [('aw_source_id', ident), ('aw_ground_mode', '1' if dead else str(base['ground_mode'])),
              ('classname', 'aw_corpse' if dead else 'aw_npc'),
              ('model', model['model']), ('netname', clean(base['name'])), ('aw_voice', ''), ('aw_line', ''),
              ('aw_idle_step', repr(float(model['step']))), ('aw_hello_distance', '0'), ('aw_hello_reset', '0'),
              ('aw_greet_duration', '0')]
    return ''.join('"%s" "%s"\n' % kv for kv in fields)


def base_texts(source):
    """{creature id: entity text} of a library manifest (a dict or a JSON file)."""
    m = source if isinstance(source, dict) else json.loads(Path(source).read_text(encoding='utf-8'))
    if m.get('format') != FORMAT:
        raise ValueError('Not a creature library manifest')
    out = {}
    for key, model in m['models'].items():
        if key.endswith(CORPSE_KEY):
            for i, b in m['bases'].items():
                if b.get('dead') and corpse_key(b['mesh']) == key:
                    out[i] = entity_text(i, b, model)
            continue
        mesh, _, scale = key.partition('@')
        for i, b in m['bases'].items():
            if b['mesh'] == mesh and not b.get('dead'):
                out[i if not scale else '%s@%s' % (i, scale)] = entity_text(i, b, model)
    return out


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--data-files', type=Path, required=True)
    p.add_argument('--palette', type=Path, required=True, help='the Quake palette (gfx/palette.lmp)')
    p.add_argument('--out', type=Path, required=True, help='an id1 folder: models go to OUT/progs, the manifest beside')
    p.add_argument('--only', help='comma-separated creature ids: bake only their meshes')
    p.add_argument('--jobs', type=int, default=1)
    p.add_argument('--method', choices=METHODS, default=DEFAULT_METHOD)
    a = p.parse_args(argv)
    from mwad.paths import child_ci
    planned = plan(child_ci(a.data_files, 'Morrowind.esm').read_bytes())
    meshes, corpses = planned['meshes'], planned['corpses']
    if a.only:
        want = {i.strip().casefold() for i in a.only.split(',')}
        meshes = {m: ids for m, ids in meshes.items() if want & set(ids)}
        corpses = {m: ids for m, ids in corpses.items() if want & set(ids)}
    print('Creature library: %d meshes for %d creature records, %d corpse meshes, %d jobs' % (
        len(meshes), sum(len(v) for v in meshes.values()), len(corpses), a.jobs), flush=True)
    bipedal = {m: any(planned['bases'][i]['flags'] & 1 for i in ids)
               for m, ids in list(meshes.items()) + list(corpses.items())}
    models, failed = bake(a.data_files, a.palette.read_bytes(), meshes, a.out, a.jobs, a.method, bipedal,
                          corpses=corpses if a.method in ('kf', 'skeletal') else None)
    out = manifest(planned, models)
    out['left_out'] = failed
    (a.out / 'creature-library.json').write_text(json.dumps(out, indent=1, sort_keys=True) + '\n', encoding='utf-8',
                                                newline='\n')


if __name__ == '__main__':
    main()
