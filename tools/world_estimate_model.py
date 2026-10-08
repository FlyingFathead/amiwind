# SPDX-License-Identifier: GPL-3.0-only
"""World estimate, model side: per-map lump/heap prediction and calibration.

A map's BSP lumps are predicted from sums over its placement variants of the
per-mesh costs that world_estimate_data.mesh_costs computes with the
converter's own functions (S_* = once per converter variant, I_* = once per
instance; interiors bake light per instance so every interior instance is its
own submodel), plus terrain terms. Each lump is a non-negative linear fit of
those sums; the heap is a non-negative linear fit of the lumps to the
repository's own heap model (check_world_map_heap). The coefficients are plain
numbers (config/world-estimate-model.json); `estimate-calibrate` refits them
from maps the user converted (world_estimate.py --sample-convert).
"""
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = ROOT / 'config/world-estimate-model.json'
MODEL_FORMAT = 'aw-world-estimate-model-1'
COST_KEYS = ('faces', 'texinfo', 'luxels', 'nodes', 'clipnodes')
TARGETS = ('faces', 'texinfo', 'nodes', 'clipnodes', 'marksurfaces', 'vertexes', 'edges', 'surfedges', 'planes',
           'lighting_bytes', 'texture_bytes', 'entity_bytes', 'leafs', 'models', 'bsp_bytes')
HEAP_LUMPS = ('faces', 'texinfo', 'nodes', 'clipnodes', 'marksurfaces', 'vertexes', 'edges', 'surfedges', 'planes',
              'lighting_bytes', 'texture_bytes', 'entity_bytes', 'leafs', 'models')
XCOLS = {
    'faces': ('S_faces', 'I_faces', 'land', 'cov'), 'texinfo': ('S_texinfo', 'I_texinfo', 'land', 'cov'),
    'nodes': ('S_nodes', 'I_nodes', 'land'), 'clipnodes': ('S_clip', 'I_clip', 'land', 'cov'),
    'marksurfaces': ('S_faces', 'I_faces', 'land', 'cov'), 'vertexes': ('S_faces', 'I_faces', 'land', 'cov'),
    'edges': ('S_faces', 'I_faces', 'land', 'cov'), 'surfedges': ('S_faces', 'I_faces', 'land', 'cov'),
    'planes': ('S_faces', 'I_faces', 'S_nodes', 'I_nodes', 'S_clip', 'land'),
    'lighting_bytes': ('S_luxels', 'I_luxels', 'land', 'cov'), 'texture_bytes': ('n_tex', 'land'),
    'entity_bytes': ('n_inst', 'flames'), 'leafs': ('land', 'cov', 'n_inst'), 'models': ('n_var', 'n_inst'),
    'bsp_bytes': ('S_faces', 'I_faces', 'S_luxels', 'I_luxels', 'S_clip', 'I_clip', 'n_tex', 'land'),
}
SPACES = ('interior', 'exterior')


def fallback_ratios(meshes):
    """Per-space cost per visible triangle over the meshes scanned in this run
    (used only for a mesh whose cost pass failed)."""
    out = {}
    for space in SPACES:
        tot = collections.Counter()
        for m in meshes.values():
            c = (m.get('costs') or {}).get(space)
            if m.get('status') != 'ok' or not c or 'error' in c:
                continue
            tot['tris'] += m['tris']
            for k in COST_KEYS:
                tot[k] += c[k]
        out[space] = {k: tot[k] / tot['tris'] if tot['tris'] else 0.0 for k in COST_KEYS}
    return out


def variant_cost(meshes, ratios, space, model):
    m = meshes.get(model) or {}
    c = (m.get('costs') or {}).get(space)
    if c and 'error' not in c:
        return [c[k] for k in COST_KEYS], c.get('max_extent_target', c.get('max_extent', 0.0)), 'computed'
    tris = m.get('tris', 0)
    return [ratios[space][k] * tris for k in COST_KEYS], 0.0, 'fallback'


def map_sums(meshes, ratios, row, scen):
    """Feature sums of one map row (world_estimate_data feature dict) and scenario."""
    S = [0.0] * 5
    I = [0.0] * 5
    src = collections.Counter()
    nvar = ninst = 0
    maxext = 0.0
    for model, n in row[scen + '_variants']:
        v, ext, how = variant_cost(meshes, ratios, row['space'], model)
        for k in range(5):
            S[k] += v[k]
            I[k] += v[k] * n
        src[how] += 1
        nvar += 1
        ninst += n
        maxext = max(maxext, ext)
    return {'S_faces': S[0], 'S_texinfo': S[1], 'S_luxels': S[2], 'S_nodes': S[3], 'S_clip': S[4],
            'I_faces': I[0], 'I_texinfo': I[1], 'I_luxels': I[2], 'I_nodes': I[3], 'I_clip': I[4],
            'n_var': nvar, 'n_inst': ninst, 'n_tex': row[scen + '_textures'], 'flames': row[scen + '_flames'],
            'land': row.get('cov_area', 0) * row.get('land_frac_cov', 0) / 1e6, 'cov': row.get('cov_area', 0) / 1e6,
            'src': dict(src), 'known_maxext': maxext}


def xrow(sums, cols):
    return [1.0] + [float(sums[c]) for c in cols]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def load_model(path=None):
    path = Path(path) if path else DEFAULT_MODEL
    model = json.loads(path.read_text(encoding='utf-8'))
    if model.get('format') != MODEL_FORMAT:
        raise ValueError('Unsupported estimate model: ' + str(path))
    for space in SPACES:
        coeff = model['coefficients'][space]
        for t in TARGETS:
            if len(coeff[t]) != len(XCOLS[t]) + 1:
                raise ValueError('Model %s/%s has the wrong number of coefficients' % (space, t))
        for t in ('heap_raw', 'heap_final'):
            if len(coeff[t]) != len(HEAP_LUMPS) + 1:
                raise ValueError('Model %s/%s has the wrong number of coefficients' % (space, t))
    return model


def predict(model, meshes, ratios, row, scen):
    """Predicted lumps, heap (raw and optimized), final BSP bytes and compile seconds."""
    s = map_sums(meshes, ratios, row, scen)
    c = model['coefficients'][row['space']]
    p = {t: max(0.0, dot(xrow(s, XCOLS[t]), c[t])) for t in TARGETS}
    hx = [1.0] + [p[k] for k in HEAP_LUMPS]
    p['heap_raw'] = dot(hx, c['heap_raw'])
    p['heap_final'] = dot(hx, c['heap_final'])
    p['final_bytes'] = dot([1.0, p['bsp_bytes'], p['lighting_bytes']], c['final_bytes'])
    p['seconds'] = dot([1.0, p['faces'], p['clipnodes']], c['seconds'])
    return p, s


# ---------------------------------------------------------------- fitting

def _nnls(X, y):
    import numpy as np
    from scipy.optimize import nnls
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    # Column scaling keeps NNLS well conditioned; coefficients are unscaled after.
    scale = np.maximum(np.abs(X).max(axis=0), 1e-12)
    return (nnls(X / scale, y)[0] / scale).tolist()


def fit(pairs, meshes, ratios):
    """pairs: [(feature_row, measured)] with measured = {'bsp': lumps, 'heap_raw', 'heap_final'?,
    'final_bsp_bytes'?, 'seconds'?}. Returns the coefficient dict per space.
    The fit uses the 'cur' scenario (what the converters actually converted)."""
    out = {}
    for space in SPACES:
        rows = [(f, m) for f, m in pairs if f['space'] == space]
        if len(rows) < 3:
            raise ValueError('Calibration needs at least 3 measured %s maps (have %d)' % (space, len(rows)))
        sums = [map_sums(meshes, ratios, f, 'cur') for f, m in rows]
        c = {}
        for t in TARGETS:
            c[t] = _nnls([xrow(s, XCOLS[t]) for s in sums], [m['bsp'][t] for f, m in rows])
        X = [[1.0] + [m['bsp'][k] for k in HEAP_LUMPS] for f, m in rows]
        c['heap_raw'] = _nnls(X, [m['heap_raw'] for f, m in rows])
        fin = [(f, m) for f, m in rows if m.get('heap_final')]
        if len(fin) >= 3:
            c['heap_final'] = _nnls([[1.0] + [m['bsp'][k] for k in HEAP_LUMPS] for f, m in fin],
                                    [m['heap_final'] for f, m in fin])
            c['final_bytes'] = _nnls([[1.0, m['bsp']['bsp_bytes'], m['bsp']['lighting_bytes']] for f, m in fin],
                                     [m.get('final_bsp_bytes') or m['bsp']['bsp_bytes'] for f, m in fin])
        else:  # no optimized maps: the optimizer's effect is unknown, assume none
            c['heap_final'] = list(c['heap_raw'])
            c['final_bytes'] = [0.0, 1.0, 0.0]
        tm = [(f, m) for f, m in rows if m.get('seconds')]
        c['seconds'] = (_nnls([[1.0, m['bsp']['faces'], m['bsp']['clipnodes']] for f, m in tm],
                              [m['seconds'] for f, m in tm]) if len(tm) >= 3 else [0.0, 0.0, 0.0])
        out[space] = c
    return out


def err_stats(pred, true):
    import numpy as np
    pred, true = np.asarray(pred, float), np.asarray(true, float)
    ok = true > 0
    if not ok.any():
        return None
    rel = (pred[ok] - true[ok]) / true[ok]
    ss = float(((true - true.mean()) ** 2).sum())
    return {'n': int(ok.sum()), 'median_abs_pct': round(float(np.median(np.abs(rel)) * 100), 2),
            'p90_abs_pct': round(float(np.percentile(np.abs(rel), 90) * 100), 2),
            'max_abs_pct': round(float(np.abs(rel).max() * 100), 2),
            'bias_pct': round(float(np.median(rel) * 100), 2),
            'r2': round(1 - float(((pred - true) ** 2).sum()) / ss, 4) if ss > 0 else None}


def fold_of(f, folds=5):
    group = f.get('frame') or f['map']
    return int(hashlib.sha256(group.encode()).hexdigest(), 16) % folds


def cross_validate(pairs, meshes, ratios, folds=5):
    """Grouped k-fold CV (groups: exterior frame or interior map). Per-space
    error statistics for every target and the heap the gates use."""
    acc = collections.defaultdict(lambda: collections.defaultdict(lambda: ([], [])))
    rows = []
    for k in range(folds):
        test = [(f, m) for f, m in pairs if fold_of(f, folds) == k]
        train = [(f, m) for f, m in pairs if fold_of(f, folds) != k]
        if not test:
            continue
        coeff = fit(train, meshes, ratios)
        model = {'coefficients': coeff}
        for f, m in test:
            p, _ = predict(model, meshes, ratios, f, 'cur')
            heap_true = m.get('heap_final') or m['heap_raw']
            heap_pred = p['heap_final'] if m.get('heap_final') else p['heap_raw']
            for t in TARGETS:
                acc[f['space']][t][0].append(p[t])
                acc[f['space']][t][1].append(m['bsp'][t])
            acc[f['space']]['heap'][0].append(heap_pred)
            acc[f['space']]['heap'][1].append(heap_true)
            rows.append({'map': f['map'], 'space': f['space'], 'heap_true': heap_true, 'heap_pred': round(heap_pred)})
    return {sp: {t: err_stats(*v) for t, v in d.items()} for sp, d in acc.items()}, rows


def model_document(coefficients, calibration):
    return {'format': MODEL_FORMAT,
            'about': 'Generic numeric coefficients of the world estimate (tools/world_estimate_model.py). '
                     'Lumps = coefficients . [1, sums of per-mesh converter costs, terrain terms]; '
                     'heap = coefficients . [1, lumps]. No game data.',
            'xcols': {t: list(c) for t, c in XCOLS.items()}, 'heap_lumps': list(HEAP_LUMPS),
            'coefficients': coefficients, 'calibration': calibration}
