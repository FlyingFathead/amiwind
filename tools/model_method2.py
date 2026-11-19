# SPDX-License-Identifier: GPL-3.0-only
"""Method 2: hand-made reductions of one model each (config/model-method-2.json; MODEL-REPLACEMENT-OBJ-67).

Method 1 is the conversion every model gets (the converter's profile reduction, planar merge or meshopt+merge by
config/mesh-methods.json, the rows of config/visual-recipes.json). A model with a method-2 row is drawn by its
hand-made mesh wherever it is placed, in every CHIM frame and every CHIM room, keyed by its model path and the SHA-256
of its NIF file, so only that model type changes. Its collision, light and flames stay the original's (the mesh step
keeps the source mesh for collision, as for a visual primitive). Method 1 stays selectable: per model ("method": 1 in
its row) and for the whole build (AMIWIND_MODEL_METHOD=1), so every A/B runs both ways.

The mesh and its pictures are made at build time from the scenery export of the user's own game files: a unit of its
own kind ('mesh-method2', chim.units), so the default mesh units' keys never reach this code and only the method-2
models' units are made again when it changes.
"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / 'config' / 'model-method-2.json'
METHOD_VARIABLE = 'AMIWIND_MODEL_METHOD'    # 1: method 1 for every model (the method before); 2 (default): method 2
PANELS_VARIABLE = 'AMIWIND_METHOD2_PANELS'  # baked | frosted: every method-2 row's panels for an A/B (else the row's)
UNIT_KIND = 'mesh-method2'
# lantern_rings: tools/lantern_rebuild.py; the kinds of the hand-made batches 001-004: tools/hand_made_kinds.py
KINDS = ('lantern_rings', 'conservative', 'profile_shell', 'dunmer_lantern', 'common_lantern')
# the recipe keys of method 1 a method-2 mesh does not use (its drawn mesh is the hand-made one)
METHOD1_VISUAL_KEYS = ('ratio', 'meshopt_error_share', 'lod_preserve_border', 'visual_triangle_target',
                       'visual_primitive', 'visual_panel', 'flatten', 'visual_recipe')


def load_table(path=None):
    data = json.loads(Path(path or TABLE).read_text(encoding='utf-8'))
    if data.get('format') != 1:
        raise ValueError('config/model-method-2.json: unknown format')
    for source, row in data['models'].items():
        if source != source.replace('\\', '/').lower() or not source.startswith('meshes/'):
            raise ValueError('config/model-method-2.json: model paths are lower-case meshes/... (%s)' % source)
        if len(row.get('source_sha256', '')) != 64:
            raise ValueError('config/model-method-2.json %s: source_sha256 (the NIF file) is required' % source)
        if row.get('kind') not in KINDS:
            raise ValueError('config/model-method-2.json %s: unknown kind %r' % (source, row.get('kind')))
        if row.get('method') not in (1, 2):
            raise ValueError('config/model-method-2.json %s: method must be 1 or 2' % source)
        if row.get('panels', 'baked') not in ('baked', 'frosted'):
            raise ValueError('config/model-method-2.json %s: panels must be baked or frosted' % source)
        for key in ('source', 'counts', 'ab'):
            if key not in row:
                raise ValueError('config/model-method-2.json %s: every row records its %s' % (source, key))
    return data


def method_setting():
    """The build's method setting: 2 (default: method 2 wherever a model has a row) or 1 (method 1 for every
    model)."""
    value = os.environ.get(METHOD_VARIABLE, '').strip() or '2'
    if value not in ('1', '2'):
        raise ValueError('%s must be 1 or 2, not %r' % (METHOD_VARIABLE, value))
    return int(value)


def panels_setting(row):
    value = os.environ.get(PANELS_VARIABLE, '').strip() or row.get('panels', 'baked')
    if value not in ('baked', 'frosted'):
        raise ValueError('%s must be baked or frosted, not %r' % (PANELS_VARIABLE, value))
    return value


def row_for(model, table):
    """The method-2 row of a scenery-index model, or None: its path and its NIF file's SHA-256 must both match."""
    source = model['source'].replace('\\', '/').lower()
    row = table['models'].get(source)
    if row is None or model.get('source_sha256') != row['source_sha256']:
        return None
    return row


def apply_method2(profile, model, table=None):
    """PROFILE (method 1, as the stage made it) with the model's method-2 mesh, when the build and the model's row
    use method 2; else PROFILE unchanged. The method-2 profile keeps the stage's own settings (collision, faces
    method, stair and hull rules) and drops method 1's visual recipe keys."""
    table = load_table() if table is None else table
    row = row_for(model, table)
    if row is None or row['method'] != 2 or method_setting() != 2:
        return profile
    out = {k: v for k, v in profile.items() if k not in METHOD1_VISUAL_KEYS}
    out['visual_method2'] = {'kind': row['kind'], 'panels': panels_setting(row), 'recipe': row['recipe']}
    out['visual_recipe'] = {'name': 'method-2', 'sha256': row['source_sha256']}
    return out


def is_method2(profile):
    return 'visual_method2' in (profile or {})


def unit_kind(profile, default='mesh'):
    """The unit kind of a mesh with this profile: UNIT_KIND for a method-2 mesh, else DEFAULT."""
    return UNIT_KIND if is_method2(profile) else default


def run_mesh_units(items, worker, jobs, cache, kind='mesh'):
    """run_units for mesh items [(fp, (mi, model, profile, archive, textures))] in their order: the method-2 meshes
    on their own unit kind and worker (mesh_unit_method2), every other mesh on KIND with WORKER, as before."""
    from chim.units import run_units
    plain = [i for i, (_, task) in enumerate(items) if not is_method2(task[2])]
    hand = [i for i, (_, task) in enumerate(items) if is_method2(task[2])]
    out = [None] * len(items)
    for i, result in zip(plain, run_units(kind, [items[i] for i in plain], worker, jobs, cache)):
        out[i] = result
    if hand:
        for i, result in zip(hand, run_units(UNIT_KIND, [items[i] for i in hand], mesh_unit_method2, jobs, cache)):
            out[i] = result
        print('[method 2] %d hand-made meshes: %s' % (len(hand), ', '.join(
            sorted({items[i][1][1]['source'] for i in hand}))), flush=True)
    return out


def _source(task):
    """(vertices, faces, material count, {material: RGBA uint8 array}) of a mesh task's source model."""
    import struct
    import numpy as np
    from mwad.scene import read_asset, unpack_geometry
    _, model, _, archive_path, *extras = task
    texture_records = extras[0] if extras else []
    with Path(archive_path).open('rb') as archive:
        v, f, count = unpack_geometry(read_asset(archive, model))
        textures = {}
        for material, mat in enumerate(model['materials']):
            ti = mat.get('texture_index')
            if ti is None:
                continue
            raw = read_asset(archive, texture_records[ti])
            _, w, h = struct.unpack_from('>4sHH', raw)
            textures[material] = np.frombuffer(raw[8:], np.uint8).reshape(h, w, 4)
    return np.asarray(v, dtype=float), np.asarray(f, dtype=np.int64), count, textures


def mesh_unit_method2(task):
    """The prepared mesh (prepare_mesh_bsp._prepare_model's result) of a method-2 model: its hand-made drawn mesh
    (lantern_rebuild.rebuild), its panel picture as the converter's baked-panel material (lod '_flat_rgb', material =
    the material count), the collision of its source mesh, every other step the converter's own."""
    import numpy as np
    import prepare_mesh_bsp
    import visual_primitives
    mi, model, profile, archive_path, *extras = task
    spec = profile['visual_method2']
    if spec['kind'] not in KINDS:
        raise ValueError('method 2: unknown kind %r (%s)' % (spec['kind'], model['source']))
    vertices, faces, count, textures = _source(task)
    if spec['kind'] == 'lantern_rings':
        from lantern_rebuild import load_recipe, rebuild
        visual_v, visual_f, picture, report = rebuild(vertices, faces, count, textures, load_recipe(spec),
                                                      spec['panels'])
    else:
        # the hand-made batches' kinds (tools/hand_made_kinds.py); "conservative" keeps the source's textures
        from hand_made_kinds import rebuild as rebuild_kind
        visual_v, visual_f, picture, report = rebuild_kind(vertices, faces, count, textures, spec, model['materials'])
    # the converter draws the visual a primitive names (prepare_mesh_bsp: visual_primitive); this unit's primitive is
    # the hand-made mesh, its panel faces on a source material no other drawn face uses for that step (a primitive's
    # materials are the source's) and moved to the baked-panel material after it
    panel = visual_f[:, 3] == count
    free = sorted(set(range(count)) - {int(m) for m in visual_f[~panel, 3]})
    if panel.any() and not free:
        raise ValueError('method 2: %s has no source material left for the panel faces' % model['source'])
    placeholder = free[0] if panel.any() else None
    drawn_f = visual_f.copy()
    if placeholder is not None:
        drawn_f[panel, 3] = placeholder
    original = visual_primitives.make_visual

    def make_visual(settings):
        if settings.get('kind') == 'method2':
            return visual_v, drawn_f
        return original(settings)
    clean = {k: v for k, v in profile.items() if k != 'visual_method2'}
    visual_primitives.make_visual = make_visual
    try:
        _, (v, f, polys, pieces, lod) = prepare_mesh_bsp._prepare_model(
            (mi, model, dict(clean, visual_primitive={'kind': 'method2'}), archive_path, *extras))
    finally:
        visual_primitives.make_visual = original
    # the panel faces back on the baked-panel material (index = the material count, its picture in lod['_flat_rgb'])
    if placeholder is not None:
        polys = [(poly, count if mat == placeholder else mat, ax, off, normal) for poly, mat, ax, off, normal in polys]
    lod = dict(lod, visual_primitive='method2', visual_method2=dict(report, kind=spec['kind']))
    if picture is not None:
        lod['_flat_rgb'] = np.ascontiguousarray(picture)
    # the prepared mesh alone, as chim.build.mesh_unit returns it
    return v, f, polys, pieces, lod
