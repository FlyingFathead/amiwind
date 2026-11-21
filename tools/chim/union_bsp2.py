# SPDX-License-Identifier: GPL-3.0-only
"""Collision unions the compiler refuses in its standard format, compiled in its BSP2 format: their own unit kinds
(CHIM-COLLISION-UNION-FALLBACK-41).

An exact model's standing hull is the union of its grown convex pieces compiled by qbsp
(collision_bsp.compile_standing_checked); when the compiler refuses it, the variant keeps the raw chain of its pieces.
For some models the refusal is the compiler's own file format: the union needs more nodes or leaves than a BSP29 file
numbers (32,767), "Map exceeds BSP29 node/leaf limit". Measured on Solstheim's iceberg shards
(bm_ex_iceberg_shard01): 33,965 to 37,011 nodes; such a copy keeps a chain of about 46,600 clipnodes, 1.79 MB, where
the union compiled with -bsp2 passes the standing check and the copy is about 0.95 MB. Here the same union is compiled
with -bsp2 (32-bit numbers), read and packed as collision_bsp packs it; the image's own budget (65,520 compiled nodes,
chim.models.BrushLumps) still applies.

Own unit kinds, so the default kinds' keys never reach this module (chim.units TOOLS and CODE_ENTRIES); chosen per mesh
by config/collision-union-bsp2.json in chim.build frame_input:
- 'variant-bsp2': a listed mesh's variant whose union fell back runs again: chim.models.variant_unit unchanged, with
  collision_bsp.compile_standing_checked replaced by compile_standing_bsp2 for that one call and restored after it,
  whatever happens; its result replaces the fallback only when it compiled.
- 'tiles-budget-union': a listed model over one image's budget ("tiles": true) cut into tiles exactly as
  chim.cut.tile_unit cuts them (chim.cut.model_tiles), each tile's standing hull the BSP2 union of its pieces, the
  tile's own chain where a union is refused.

COPIES, kept on purpose: the brush text and the packing walk of collision_bsp.compile_standing_checked_once and the
body of chim.cut.tile_unit. Changed there, they would re-key every model variant of the island for copies whose bytes
do not change; tests/test_union_bsp2.py holds the brush text and the packed hull to the originals, and a tracked work
item (UNION-BSP2-COPIES-ONE-FUNCTION-68) makes them one function again at the next change that re-keys those kinds.
"""
import hashlib
import json
import os
import pickle
import struct
import subprocess
import tempfile
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UNION_LIST = ROOT / 'config' / 'collision-union-bsp2.json'
LIST_FORMAT = 'aw-collision-union-bsp2-1'
COMPILER_TAIL_LINES = 40        # the compiler's last output lines kept whole in a refusal: the cause is there
CACHE_FORM = b'collision-union-bsp2-1\0'


def union_list(path=UNION_LIST):
    """{mesh stem: row} of config/collision-union-bsp2.json ({} without the file): meshes whose refused collision unions
    are compiled in BSP2; a row with "tiles": true is a model over one image's budget, compiled tile by tile."""
    path = Path(path)
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('format') != LIST_FORMAT or not isinstance(data.get('meshes'), dict):
        raise ValueError('%s: format %s with a meshes table expected' % (path, LIST_FORMAT))
    return {str(k).lower(): v for k, v in data['meshes'].items()}


def redo_indices(results, items, listed=None):
    """Indices of the variant RESULTS (with their ITEMS, (fingerprint, task)) to run again as 'variant-bsp2': the
    union fell back, the task has the compiler, and the mesh is listed (LISTED: union_list())."""
    from routed_hull import mesh_stem
    listed = union_list() if listed is None else listed
    if not listed:
        return []
    return [i for i, (res, (_, task)) in enumerate(zip(results, items))
            if res.get('collision_fallback') and task.get('qbsp')
            and mesh_stem(task['model']['source']) in listed and not listed[mesh_stem(task['model']['source'])].get('tiles')]


def tiles_listed(source, listed=None):
    """True when the model SOURCE is listed for unions tile by tile ("tiles": true)."""
    from routed_hull import mesh_stem
    listed = union_list() if listed is None else listed
    return bool((listed.get(mesh_stem(source)) or {}).get('tiles'))


def read_bsp2(raw):
    """(planes, nodes, leaves, hull-0 root) of a BSP2 file: planes (nx, ny, nz, dist, type); nodes (plane, front, back,
    ...) with 32-bit children; leaves (contents, ...)."""
    if raw[:4] != b'BSP2' or len(raw) < 124:
        raise ValueError('not a BSP2 file')
    parts = []
    for i in range(15):
        o, n = struct.unpack_from('<ii', raw, 4 + i * 8)
        if o < 124 or n < 0 or o + n > len(raw):
            raise ValueError('BSP2 lump bounds')
        parts.append(raw[o:o + n])
    planes = list(struct.iter_unpack('<4fi', parts[1]))
    nodes = list(struct.iter_unpack('<iii6f2I', parts[5]))
    leaves = list(struct.iter_unpack('<ii6f2I4B', parts[10]))
    return planes, nodes, leaves, struct.unpack_from('<i', parts[14], 36)[0]


def brush_source(pieces, grid=64, merge_coplanar=False):
    """The compiler's map text of the grown PIECES: collision_bsp.compile_standing_checked_once's brushes, its loop
    copied (see the module text)."""
    import numpy as np
    from scipy.spatial import ConvexHull
    import collision_bsp as CB
    corners = np.array(list(product(*zip(CB.MINS, CB.MAXS))))
    brushes = []
    for points, hull, ids, error in pieces:
        expanded = (points[:, None, :] - corners[None, :, :]).reshape(-1, 3)
        expanded = np.unique(np.round(expanded * grid) / grid, axis=0)
        convex = (ConvexHull(expanded, qhull_options=CB.MERGE_COPLANAR) if merge_coplanar else ConvexHull(expanded))
        seen = set()
        lines = ['{']
        for equation in convex.equations:
            n = equation[:3]
            d = -equation[3]
            key = (*np.round(n, 4), round(d, 3))
            if key in seen:
                continue
            seen.add(key)
            axis = np.eye(3)[np.argmin(abs(n))]
            u = np.cross(n, axis)
            u /= np.linalg.norm(u)
            v = np.cross(n, u)
            centre = n * d
            points3 = (centre + u * 256, centre, centre + v * 256)
            lines.append(' '.join('( ' + ' '.join(f'{x:.8f}' for x in point) + ' )' for point in points3)
                         + ' stone 0 0 0 1 1')
        brushes.append('\n'.join(lines + ['}']))
    return '{\n"classname" "worldspawn"\n' + '\n'.join(brushes) + '\n}\n'


def pack(planes, nodes, leaves, root):
    """collision_bsp's packing of a compiled tree, its walk copied: (packed nodes [(plane, front, back)], root), the
    nodes in pre-order from the root, a leaf as its contents (-1 empty, -2 solid)."""
    found, order, stack = set(), [], [root]
    while stack:
        n = stack.pop()
        if n < 0 or n in found:
            continue
        found.add(n)
        order.append(n)
        stack.extend(nodes[n][1:3])
    remap = {old: i for i, old in enumerate(order)}

    def child(n):
        if n >= 0:
            return remap[n]
        contents = leaves[-n - 1][0]
        if contents not in (-1, -2):
            raise ValueError('Unexpected collision contents')
        return contents
    packed = [(planes[nodes[n][0]][:4], child(nodes[n][1]), child(nodes[n][2])) for n in order]
    return packed, (remap[root] if root >= 0 else child(root))


def _refusal(code, text):
    tail = '\n'.join(line.rstrip() for line in text.splitlines()[-COMPILER_TAIL_LINES:])
    return ValueError('Collision compiler failed in BSP2 (exit %d%s); its last lines:\n%s'
                      % (code, ', signal %d' % -code if code < 0 else '', tail))


def compile_standing_bsp2_once(pieces, qbsp, cache, grid=64, check_box=None, patch=True, merge_coplanar=False):
    """The union of the grown PIECES compiled with -bsp2: (result, check) as collision_bsp.compile_standing_checked_once
    gives them (the same standing check and hole patches), cached in CACHE under this form's own key."""
    import collision_bsp as CB
    source = brush_source(pieces, grid, merge_coplanar)
    compiler = Path(qbsp).resolve()
    key = hashlib.sha256(CACHE_FORM + source.encode() + compiler.read_bytes()).hexdigest()
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    box = None if check_box is None else tuple(round(float(v), 6) for v in check_box)
    path = cache / ('%s.%s.pickle' % (key, hashlib.sha256(repr((CB.CHECK_VERSION, box, bool(patch))).encode()).hexdigest()[:16]))
    if path.is_file():
        return pickle.loads(path.read_bytes())
    with tempfile.TemporaryDirectory(prefix='aw-collision-bsp2-') as tmp:
        tmp = Path(tmp)
        (tmp / 'collision.map').write_text(source, encoding='utf-8', newline='\n')
        run = subprocess.run([str(compiler), '-noclip', '-nofill', '-nopercent', '-bsp2', 'collision.map'], cwd=tmp,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if run.returncode:
            raise _refusal(run.returncode, run.stdout.decode(errors='replace'))
        planes, nodes, leaves, root = read_bsp2((tmp / 'collision.bsp').read_bytes())
    packed, top = pack(planes, nodes, leaves, root)
    result = (packed, top)
    implicated = set()
    check = CB.standing_check(result, pieces, box, implicated=implicated)
    patched = 0
    while patch and check['short'] > 0 and check['over'] == 0 and implicated and patched < CB.PATCH_ROUNDS:
        patched += 1
        result = CB.patch_holes(result, pieces, implicated)
        more = set()
        check = CB.standing_check(result, pieces, box, implicated=more)
        implicated = more
    if patched:
        check = dict(check, patched_rounds=patched, patched_nodes=len(result[0]) - len(packed))
    partial = path.with_name(path.name + '.' + str(os.getpid()) + '.tmp')
    partial.write_bytes(pickle.dumps((result, check), protocol=4))
    os.replace(partial, path)
    return result, check


def compile_standing_bsp2(pieces, qbsp, cache, grid=64, check_box=None, patch=True):
    """compile_standing_bsp2_once; a non-convex face refusal is tried once more with coplanar facets merged, as
    collision_bsp.compile_standing_checked does. The signature of collision_bsp.compile_standing_checked."""
    try:
        return compile_standing_bsp2_once(pieces, qbsp, cache, grid, check_box, patch)
    except ValueError as error:
        if 'non-convex face' not in str(error):
            raise
        try:
            return compile_standing_bsp2_once(pieces, qbsp, cache, grid, check_box, patch, merge_coplanar=True)
        except ValueError as again:
            raise ValueError('%s\n| retried with coplanar facets merged: %s' % (error, again)) from again


def variant_unit_bsp2(task):
    """One model variant as chim.models.variant_unit makes it, its union compiled in BSP2 (a pool worker, unit kind
    'variant-bsp2'). collision_bsp.compile_standing_checked is this module's for the one call and the original object
    again after it, whatever happens: a pool process lives on, and its next unit may be a plain 'variant'. A refusal
    keeps the compiler's last lines whole in 'collision_compiler_tail' (the variant's own 'collision_fallback' is cut
    at 400 characters)."""
    import collision_bsp as CB
    from chim import models as M
    original = CB.compile_standing_checked
    refused = []

    def compile_standing_checked(pieces, qbsp, cache, grid=64, check_box=None, patch=True):
        try:
            return compile_standing_bsp2(pieces, qbsp, cache, grid, check_box, patch)
        except ValueError as error:
            refused.append(str(error))
            raise
    CB.compile_standing_checked = compile_standing_checked
    try:
        result = M.variant_unit(task)
    finally:
        CB.compile_standing_checked = original
    if refused and result.get('collision_fallback'):
        result = dict(result, collision_compiler_tail=refused[-1])
    return dict(result, collision_form='bsp2')


def tile_union_unit(task):
    """The tiles of one model variant as chim.cut.tile_unit makes them (its body copied: see the module text), each
    tile's standing hull the BSP2 union of its pieces, the tile's chain where the union is refused (a pool worker,
    reached through budget_tile_unit_union)."""
    import numpy as np
    from prepare_mesh_bsp import NO_EMISSIVE, _prepare_placement
    from chim.cut import model_tiles
    from chim.models import hull_pieces, material_texture_key, model_image_lumps
    ref, model, centre, size = task['ref'], task['model'], task['centre'], task['texsize']
    surfaces, parts, _, _ = _prepare_placement((ref, task['data'], size, centre, None, False))
    keys = {}
    for srf in surfaces:
        keys[srf[4]] = ('model',) + material_texture_key(model, srf[4], size, NO_EMISSIVE, task.get('texture_shas'),
                                                          task.get('uv_scroll', 'off'))
    tiles = model_tiles(surfaces, parts, task['grain'])
    out = []
    order = sorted(tiles)
    whole_grid = None
    if task['hollow'] and order:
        from chim.occluders import solid_columns
        first = tiles[order[0]][2]
        whole_grid = solid_columns([np.asarray(srf[0], float) - first for srf in surfaces])
    for n, t in enumerate(order):
        surfs, prts, c = tiles[t]
        allp = np.vstack([np.asarray(srf[0]) for srf in surfs] + [p for p, *_ in prts])
        lo, hi = allp.min(axis=0) - 1, allp.max(axis=0) + 1
        compiled, refusal = None, None
        pieces = hull_pieces(prts)
        if pieces and task.get('qbsp'):
            try:
                compiled, _ = compile_standing_bsp2(pieces, task['qbsp'], task['collision_cache'],
                                                    patch=bool(task.get('hull_patch', True)))
            except ValueError as error:
                refusal = str(error)
        lumps, tkeys = model_image_lumps(surfs, prts, lo, hi, lambda m: keys[m], task['exact'], compiled, b'')
        out.append({'tile': list(t), 'centre': [float(v) for v in c], 'lumps': [bytes(x) for x in lumps],
                    'texture_keys': tkeys, 'lo': [float(v) for v in lo], 'hi': [float(v) for v in hi],
                    'occluders': [] if task['hollow'] else [p for p, *_ in prts],
                    'occluder_grid': whole_grid if n == 0 else None,
                    'materials': {k: m for m, k in keys.items() if k in tkeys},
                    'collision_form': 'bsp2' if compiled is not None else 'chain',
                    **({'collision_compiler_tail': refusal} if refusal else {})})
    return out


def budget_tile_unit_union(task):
    """chim.budget_tiles.fit_tiles with tile_union_unit (a pool worker; unit kind 'tiles-budget-union')."""
    from chim.budget_tiles import fit_tiles
    return fit_tiles(task, tile_union_unit)
