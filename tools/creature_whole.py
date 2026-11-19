# SPDX-License-Identifier: GPL-3.0-only
"""A creature kept whole on its own animation table: the skeletal method for a mesh whose gallery profile says
'whole' (CREATURE-RACER-HOLES-67).

The cliff racer has been baked whole since v0.0.58 (CREATURE-RACER-MESH-SPIKE-58: every reduction of its thin wing
membranes and tail left holes; config/gallery_model_quality.json 'whole'): all 965 source triangles on their 667
source vertices with the original textures in one skin atlas (npc_geometry.shared_vertex_mdl, the shared-vertex
encoding), on the 'kf' method. Since v0.0.66-dev3 the creature library bakes every creature with the 'skeletal'
method (its own animation table, creature_tables), whose model is the resident bake: reduced to the budget ladder (474
triangles), every triangle on three vertices of its own and its own baked texture tile. The profile's 'whole' was not
read there. Measured on the v0.0.67-dev2 library: 474 triangles on 1,422 vertices, none shared, 62 open edges, 474
texture tiles; 66 % of the whole model's surface within half a unit of it.

And the racer's accumulation root is 'root bone', not 'bip01': skeletal_actor.hold_in_place, which holds a moving
group's root in place as OpenMW does (the movement is the game's, animation.cpp accumulation), only knows 'bip01', so
the racer's own table kept the root's travel in its walk and run (up to 7,429 units forward). The pose box the engine
quantises every drawn vertex in covers every table pose, so it reached 8,069 units along the body: a byte step of 31.6
units, every vertex drawn up to 15.8 units off along the body in every frame.

This route bakes such a mesh on its own table with the rig's own accumulation root (creature_pose.ROOTS) held in
place in its moving groups, and its model whole: the source triangles on their source vertices and the original
textures (shared_vertex_mdl), carried onto the table's bones as skeletal_actor.skeletal_from_shapes carries a reduced
model (the same block, box and MDL writers). It is its own unit worker with its own code key (unit), so the other
creatures' models, the room residents and the shared skeletal code keep their keys. Standard numpy; the readers of
the builder.
"""
import hashlib

import numpy as np

# the library task's method on this route (creature_library.bake; actor_units.creature_inputs keys it apart)
METHOD = 'skeletal-whole'


def whole_meshes(meshes):
    """The meshes of MESHES whose gallery profile (config/gallery_model_quality.json) says 'whole'."""
    from mwad.audit import normpath
    from prepare_gallery import quality_profiles
    profiles = quality_profiles()
    return {m for m in meshes if (profiles.get(normpath(m)) or {}).get('whole')}


def moving_windows(keys):
    """{group: (start, stop)} of the moving groups (skeletal_actor.MOVING_GROUPS prefixes) in the text KEYS
    [(time, 'group: what')], from their 'start' and 'stop' keys (skeletal_actor.groups_of, the table's own ranges)."""
    import skeletal_actor
    names = {line.split(':', 1)[0].strip() for _, line in keys if ':' in line}
    wanted = [g for g in sorted(names) if g.casefold().startswith(skeletal_actor.MOVING_GROUPS)]
    return skeletal_actor.groups_of(keys, wanted)


class HeldRoot:
    """A kept skeleton (creature_tables._kept) whose ROOT holds its horizontal (x, y) place within each moving group
    at the group's first time, its height kept: skeletal_actor.hold_in_place for a root of any name (the cliff racer's
    'root bone'). The rest of the skeleton is the kept one's."""

    def __init__(self, kept, root):
        self.kept, self.root = kept, root
        self.keys, self.parents, self.nodes = kept.keys, kept.parents, kept.nodes
        self.scaled = getattr(kept, 'scaled', {})
        self.windows = moving_windows(kept.keys) if root in kept.parents else {}

    def pose(self, time):
        return self.kept.pose(time)

    def local(self, name, time):
        m = np.array(self.kept.local(name, time), float)
        if name == self.root:
            for start, stop in self.windows.values():
                if start <= time <= stop:
                    m[3, :2] = np.asarray(self.kept.local(name, start), float)[3, :2]
                    break
        return m


def table(rig):
    """(table bytes, report) of the rig's own table (creature_tables.table, path 'own') with the rig's accumulation root
    held in its moving groups (HeldRoot). A table that needs scale tracks or the humanoid table is refused (this route
    makes neither)."""
    import creature_tables as T
    import skeletal_actor
    keep = tuple(T.animated_bones(rig))
    if not keep:
        raise ValueError('%s: no bone moved by its keyframes' % rig.model)
    kept, dropped = T.merge_plan(rig, keep, T.MAX_BONES)
    if len(kept) > T.MAX_BONES:
        raise ValueError('%s: %d animated bones, the engine takes %d' % (rig.model, len(kept), T.MAX_BONES))
    root = rig.nodes[rig.root][4] if rig.root is not None else None
    base = HeldRoot(T._kept(rig, 0, tuple(kept)), root)
    over = HeldRoot(T._kept(rig, 1, tuple(kept)), root) if len(rig.sources) > 1 else None
    data, report = skeletal_actor.build_table(base, over=over, tolerance=skeletal_actor.POSITION_TOLERANCE)
    if report['missing']:
        raise ValueError('%s: groups without start or stop keys: %s' % (rig.model, report['missing']))
    if base.scaled or (over is not None and over.scaled):
        raise ValueError('%s: scale keys: the whole route makes no scale tracks' % rig.model)
    return data, dict(report, sources=[s['name'] for s in rig.sources], layered=over is not None,
                      bones_left_out=dropped, bones_before=len(keep),
                      max_drift=max([d for _, _, d in dropped], default=0.0), scaled={},
                      root_held={'root': root, 'groups': sorted(base.windows)})


def whole_model(shapes, materials, textures, palette, sources, rest_world, table_bytes, bone_names, table_path,
                parents, actor_scale=(.25, .25, .25)):
    """(MDL bytes, facts) of the whole model on its table: every source triangle on its source vertices and the
    original textures in one atlas (npc_geometry.shared_vertex_mdl), each vertex carried onto its table bones, the box
    over the table's poses and the MDL with its block, as skeletal_actor.skeletal_from_shapes writes them."""
    import skeletal_actor as S
    from npc_geometry import shared_vertex_mdl
    actor_scale = np.asarray(actor_scale, float)
    tagged = [{**s, 'positions': np.concatenate((s['positions'][:1],
                                                 (s['positions'][0] + [(k + 1) * S.SHAPE_TAG, 0, 0])[None]))}
              for k, s in enumerate(shapes)]
    frames, faces, uv, skin = shared_vertex_mdl(tagged, materials, textures, palette)
    rest_model = frames[0]
    if len(rest_model) > S.SKEL_VERTEX_LIMIT:
        raise ValueError('A whole skeletal creature takes at most %d vertices: %d' % (S.SKEL_VERTEX_LIMIT,
                                                                                     len(rest_model)))
    if len(faces) > S.SKEL_FACE_LIMIT:
        raise ValueError('A whole skeletal creature takes at most %d triangles: %d' % (S.SKEL_FACE_LIMIT, len(faces)))
    tag = frames[-1] - rest_model
    shape_of = np.rint(tag[:, 0] / S.SHAPE_TAG).astype(int) - 1
    if np.any(np.abs(tag[:, 0] - (shape_of + 1) * S.SHAPE_TAG) > 1e-3) or np.any(np.abs(tag[:, 1:]) > 1e-3) or \
            np.any(shape_of < 0) or np.any(shape_of >= len(shapes)):
        raise ValueError('A whole vertex lost its shape tag')
    index = {name: i for i, name in enumerate(bone_names)}
    carried = []
    for shape, src in zip(shapes, sources):
        src = S.onto_kept(src, parents, set(bone_names), rest_world)
        missing = [n for n in src['bones'] if n not in index]
        if missing:
            raise ValueError('Shape %s hangs on bones the table lacks: %s' % (src['name'], missing))
        carried.append({**src, 'points': shape['positions'][0], 'index': [index[n] for n in src['bones']]})
    bone, second, weight, rest, rest2, distance, _ = S.carry_bones(carried, rest_model, shape_of, rest_world,
                                                                  actor_scale)
    table = S.read_table(table_bytes)
    lo, hi = rest_model.min(axis=0), rest_model.max(axis=0)
    for f in S.box_frames(table):
        posed = S.skin_many(rest, bone, second, weight, rest2, S.table_world(table, f)) * actor_scale
        lo, hi = np.minimum(lo, posed.min(axis=0)), np.maximum(hi, posed.max(axis=0))
    lo, step = S.ground_grid(lo, hi, rest_model[:, 2].min())
    blob, rest_scale = S.write_verts(bone, second, weight, rest, rest2)
    block = S.write_block(table_path, blob, rest_scale, len(rest), table['frames'], lo / actor_scale,
                          step / actor_scale)
    model = S.skeletal_mdl(rest_model, faces, uv, skin, lo, step, block)
    return model, {'vertices': len(rest), 'faces': len(faces), 'bytes': len(model), 'budget': 'whole',
                   'skin': list(skin.size), 'box_step': step.tolist(), 'largest_move': float(distance.max()),
                   'source_faces': sum(len(s['faces']) for s in shapes),
                   'source_vertices': sum(s['positions'].shape[1] for s in shapes)}


def bake(mesh, data, palette, biped):
    """{'table', 'model', 'layout', 'report'} of one mesh on the whole route (creature_tables.unit's result form)."""
    import halloween_cast
    import creature_tables as T
    from prepare_scenery import nif_reader
    assets = T._open(data)
    N = nif_reader()
    rig = T.open_rig(N, assets.read, mesh, biped)
    if T.effect_shapes(N, rig.raw):
        raise ValueError('%s: effect shapes: the whole route draws every shape' % mesh)
    tdata, report = table(rig)
    groups = T.kit(rig, tdata, report['times'])
    idle = rig.window('idle')
    if idle is None:
        raise ValueError('%s: no idle group' % rig.model)
    source, start, _ = idle
    shapes, materials, textures, sources, parents, rest_world = halloween_cast.creature_shapes(
        N, rig.raw, halloween_cast.RigSkeleton(rig, source).pose, [start], assets)
    raw, facts = whole_model(shapes, materials, textures, palette, sources, rest_world, tdata,
                             report['bone_names'], T.table_path(mesh), parents)
    rep = {'mesh': mesh, 'animated_model': rig.model, 'sources': report['sources'], 'layered': report['layered'],
           'table': T.table_path(mesh), 'table_bytes': len(tdata), 'table_sha256': hashlib.sha256(tdata).hexdigest(),
           'bones': report['bones'], 'frames': report['frames'], 'groups': report['names'], 'keys': report['keys'],
           'kit': {g['name']: g['source'] for g in groups}, 'repeated_node_names': rig.duplicates,
           'scaled_bones': {}, 'bones_left_out': report['bones_left_out'], 'bones_before': report['bones_before'],
           'max_drift': report['max_drift'], 'path': 'own', 'path_reason': 'whole profile: its own table',
           'root_held': report['root_held'], 'model': T.model_path(mesh), 'model_bytes': len(raw),
           'model_sha256': hashlib.sha256(raw).hexdigest(), 'vertices': facts['vertices'], 'faces': facts['faces'],
           'budget': 'whole', 'skin': facts['skin'], 'box_step': facts['box_step'],
           'source_faces': facts['source_faces'], 'source_vertices': facts['source_vertices']}
    return {'table': tdata, 'model': raw, 'layout': T.layout(groups), 'report': rep}


def unit(task):
    """Worker (module level for the process pool; its own code key, creature_library.bake): one task of the creature
    library ('skeletal-whole', data, palette, app, bipedal, scale) -> (key, {'files', 'record'} or None, seconds,
    error), as creature_library._unit returns."""
    import time
    import creature_library as L
    _, data, palette, app, bipedal, _scale = task
    key = L.variant_key(app['mesh'])
    t0 = time.time()
    try:
        L.layered_assets(data)
        out = bake(app['mesh'], data, palette, bipedal)
        rep = out['report']
        files = [('table', out['table'], rep['table']), ('standing', out['model'], rep['model']),
                 ('standing_layout', (out['layout'] + '\n').encode('ascii'), rep['model'][:-4] + '.anm')]
        idle_step = next((float(w.split(':')[3]) for w in out['layout'].split() if w.startswith('idle:')), 0.125)
        record = {'model': rep['model'], 'roles': ['standing'], 'method': 'skeletal', 'scale': 1.0, 'whole': True,
                  'animated_model': rep['animated_model'], 'sources': rep['sources'], 'table': rep['table'],
                  'table_bytes': rep['table_bytes'], 'table_frames': rep['frames'], 'table_groups': len(rep['groups']),
                  'standing_bytes': rep['model_bytes'], 'standing_frames': rep['frames'], 'triangles': rep['faces'],
                  'vertices': rep['vertices'], 'skin': rep['skin'], 'step': idle_step, 'idle': 'idle',
                  'kit': rep['kit'], 'kept_whole': ['all'], 'root_held': rep['root_held'],
                  'box_step': rep['box_step'], 'source_triangles': rep['source_faces'],
                  'source_vertices': rep['source_vertices'], 'scaled_bones': {},
                  'repeated_node_names': rep['repeated_node_names'], 'sha256': rep['model_sha256'],
                  'table_sha256': rep['table_sha256']}
        return key, {'files': files, 'record': record}, time.time() - t0, None
    except Exception as error:  # noqa: BLE001 (the mesh is reported with its error, as creature_library._unit does)
        return key, None, time.time() - t0, '%s: %s' % (type(error).__name__, error)
