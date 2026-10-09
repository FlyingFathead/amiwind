#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""CHIM memory predictor: the resident ring's bytes anywhere on the island, before anything is built.

The CHIM heap gate (chim.heap) measures a built world exactly. This predicts the same quantity from the
world survey's placement list (survey_vvardenfell.py: placed-geometry.json, one row per placed object with
its world bounds and source triangle count), so frame plans can be judged island-wide in seconds and
rejected before a build. The heap gate stays the final word.

Model, per player position (frame-local or world units, all in Morrowind units / 4 = local):

    ring bytes = sum over the distinct models of the placements in the ring (model_a * triangles + model_b)
               + ring chunks * terrain_bytes
               + placements in the ring * placement_bytes
               + distinct models in the ring * texture_bytes

A placement is in the ring when its box comes within the ring radius of the player (the engine's rule is
per chunk: a chunk is in the ring when its square is within the radius, and a placement belongs to every
chunk its box touches; the box distance plus half a chunk diagonal approximates that). The coefficients
are fitted on built worlds (fit): each model's decoded block against its mesh's source triangles, the
mean terrain block per chunk, the catalogue entry per placement and the texture bytes per model. A
coefficient file records which worlds it came from and the fit's error on them.

    predict.py fit WORLD --scenery INDEX [WORLD --scenery INDEX ...] --out coefficients.json
    predict.py map placed-geometry.json --coefficients coefficients.json --out ring.json [--png ring.png]
    predict.py check WORLD --scenery INDEX [WORLD --scenery INDEX ...] --survey placed-geometry.json --sdk SDK

check: the predictor's error on built worlds. For every world: the heap gate's active-ring peak
(chim.heap.ring_peak) against the predicted peak over the same frame and positions, with the
coefficients fitted on all the given worlds and, when there are several, on the others only
(leave-one-out: the error to expect on an area that was not built).
"""
import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

SCALE = 0.25          # Morrowind units to local units
FORMAT = 'chim-ring-predictor 1'


def placements_from_survey(rows):
    """[(model, triangles, (x0, y0, x1, y1) local units)] from placed-geometry.json rows."""
    out = []
    for r in rows:
        (x0, y0, _), (x1, y1, _) = r['bounds']
        out.append((r['model'].lower(), int(r['triangles']), (x0 * SCALE, y0 * SCALE, x1 * SCALE, y1 * SCALE)))
    return out


def ring_bytes(placements, coefficients, points, radius, grain=256.0):
    """Predicted ring bytes at each point (local units). placements: placements_from_survey rows."""
    import numpy as np
    c = coefficients
    if not placements:
        return np.zeros(len(points))
    boxes = np.array([b for _, _, b in placements], float)
    names = sorted({m for m, _, _ in placements})
    index = {m: i for i, m in enumerate(names)}
    tri = np.zeros(len(names))
    for m, t, _ in placements:
        tri[index[m]] = max(tri[index[m]], t)
    model_cost = c['model_a'] * tri + c['model_b'] + c['texture_bytes']
    which = np.array([index[m] for m, _, _ in placements])
    reach = radius + grain * math.sqrt(0.5)
    chunk_area = grain * grain
    out = np.zeros(len(points))
    for k, (px, py) in enumerate(points):
        dx = np.maximum(np.maximum(boxes[:, 0] - px, px - boxes[:, 2]), 0)
        dy = np.maximum(np.maximum(boxes[:, 1] - py, py - boxes[:, 3]), 0)
        inside = dx * dx + dy * dy <= reach * reach
        models = np.unique(which[inside])
        chunks = math.pi * (radius + grain / 2) ** 2 / chunk_area
        out[k] = (model_cost[models].sum() + inside.sum() * c['placement_bytes'] + chunks * c['terrain_bytes'])
    return out


def fit(worlds, sizes):
    """Coefficients from built worlds: [(world folder, scenery index)]; sizes: the target ABI sizes.
    model_a/model_b: least squares of each model's decoded block on its mesh's source triangles;
    terrain_bytes: mean chunk terrain block; placement_bytes: catalogue entry; texture_bytes: mean
    decoded texture bytes per model."""
    import numpy as np
    from chim import format as F
    from chim.heap import _a16, image_bytes, texture_bytes
    from chim.validate import Failures, load_world
    xs, ys, terrain, tex_per_model, sources = [], [], [], [], []
    for world_dir, index_path in worlds:
        settings, files, disk, textures, models, frames = load_world(world_dir, Failures())
        index = json.loads(Path(index_path).read_text(encoding='utf-8'))
        tris = {m['source'].lower().replace(chr(92), '/'): m['triangles'] for m in index['models']}
        for m in models:
            mesh = 'meshes/' + m['name'].split('@')[0] + '.nif'
            if mesh not in tris:
                continue
            lumps = F.read_brush_image(m['image'])
            xs.append(tris[mesh])
            ys.append(image_bytes(lumps, sizes))
            refs = F.read_texture_refs(lumps[2])
            tex_per_model.append(sum(texture_bytes(textures[t]['width'], textures[t]['height'], sizes)
                                     for t in refs) / max(1, len(refs)) * min(len(refs), 2))
        for _, _, chunks in frames:
            terrain += [image_bytes(F.read_brush_image(ch['image']), sizes) for ch in chunks]
        sources.append(str(world_dir))
    a, b = np.polyfit(np.array(xs, float), np.array(ys, float), 1)
    return {'format': FORMAT, 'model_a': float(a), 'model_b': float(b),
            'terrain_bytes': float(np.mean(terrain)),
            'placement_bytes': float(_a16(sizes.get('scenery', sizes['entity']) + sizes['pointer'])),
            'texture_bytes': float(np.mean(tex_per_model)) if tex_per_model else 0.0,
            'models_fitted': len(xs), 'worlds': sources}


def frame_placements(rows, centre, frame_lo, frame_hi, margin):
    """Survey placements whose box comes within margin of a frame, in frame-local units (centre: the
    frame's Morrowind-unit centre)."""
    out = []
    for m, t, (x0, y0, x1, y1) in rows:
        b = (x0 - centre[0] * SCALE, y0 - centre[1] * SCALE, x1 - centre[0] * SCALE, y1 - centre[1] * SCALE)
        if b[2] >= frame_lo[0] - margin and b[0] <= frame_hi[0] + margin and \
                b[3] >= frame_lo[1] - margin and b[1] <= frame_hi[1] + margin:
            out.append((m, t, b))
    return out


def check(worlds, survey_rows, sizes, sample=64.0):
    """[{world, frame, actual_peak, predicted_peak, error, ...}] (see the module text)."""
    import numpy as np
    from chim.heap import ring_peak
    from chim.validate import Failures, load_world
    fits = {'all': fit(worlds, sizes)}
    if len(worlds) > 1:
        for k, (w, _) in enumerate(worlds):
            fits['without ' + Path(w).name] = fit([x for j, x in enumerate(worlds) if j != k], sizes)
    out = []
    for world_dir, _ in worlds:
        settings, files, disk, textures, models, frames = load_world(world_dir, Failures())
        world = {'settings': settings, 'textures': textures, 'models': models, 'frames': frames}
        radius = float(settings['draw_distance'] + settings['hysteresis'])
        actual = ring_peak(world, sizes, sample=sample)
        for (path, frame, chunks), rep_ in zip(frames, actual['frames']):
            g, (lx, ly) = frame['grain'], frame['low']
            lo, hi = (lx, ly), (lx + frame['nx'] * g, ly + frame['ny'] * g)
            rows = frame_placements(survey_rows, frame['centre'], lo, hi, radius + g)
            xs = np.arange(lx + sample / 2, hi[0], sample)
            ys = np.arange(ly + sample / 2, hi[1], sample)
            points = [(x, y) for y in ys for x in xs]
            row = {'world': str(world_dir), 'frame': path, 'actual_peak': rep_['peak_bytes'],
                   'actual_position': rep_['peak_position'], 'placements_near': len(rows), 'radius': radius}
            for name, c in fits.items():
                if name.startswith('without ') and name == 'without ' + Path(world_dir).name or name == 'all':
                    v = ring_bytes(rows, c, points, radius, g)
                    k = int(np.argmax(v))
                    key = 'all' if name == 'all' else 'leave_one_out'
                    row[key] = {'predicted_peak': int(v[k]), 'position': [round(points[k][0], 1), round(points[k][1], 1)],
                                'error': round((v[k] - rep_['peak_bytes']) / rep_['peak_bytes'], 4)}
            out.append(row)
    return {'format': FORMAT, 'coefficients': fits, 'frames': out}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    f = sub.add_parser('fit')
    f.add_argument('worlds', nargs='+', type=Path)
    f.add_argument('--scenery', action='append', type=Path, required=True)
    f.add_argument('--sdk', type=Path, required=True)
    f.add_argument('--out', type=Path, required=True)
    c = sub.add_parser('check')
    c.add_argument('worlds', nargs='+', type=Path)
    c.add_argument('--scenery', action='append', type=Path, required=True)
    c.add_argument('--survey', type=Path, required=True)
    c.add_argument('--sdk', type=Path, required=True)
    c.add_argument('--out', type=Path)
    m = sub.add_parser('map')
    m.add_argument('survey', type=Path)
    m.add_argument('--coefficients', type=Path, required=True)
    m.add_argument('--radius', type=float, default=892.0, help='ring radius, local units (892: the load ring)')
    m.add_argument('--step', type=float, default=1024.0, help='sample spacing, local units')
    m.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(argv)
    if a.cmd == 'fit':
        from check_world_map_heap import compile_target_sizes
        if len(a.scenery) != len(a.worlds):
            ap.error('one --scenery per world')
        coeff = fit(list(zip(a.worlds, a.scenery)), compile_target_sizes(a.sdk)[0])
        a.out.write_text(json.dumps(coeff, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
        print(json.dumps(coeff))
        return 0
    if a.cmd == 'check':
        from check_world_map_heap import compile_target_sizes
        if len(a.scenery) != len(a.worlds):
            ap.error('one --scenery per world')
        rows = placements_from_survey(json.loads(a.survey.read_text(encoding='utf-8')))
        report = check(list(zip(a.worlds, a.scenery)), rows, compile_target_sizes(a.sdk)[0])
        if a.out:
            a.out.write_text(json.dumps(report, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
        for r in report['frames']:
            print(r['world'], r['frame'], 'actual', r['actual_peak'],
                  'predicted', r['all']['predicted_peak'], 'error %+.1f %%' % (100 * r['all']['error']),
                  *(['leave-one-out %+.1f %%' % (100 * r['leave_one_out']['error'])] if 'leave_one_out' in r else []))
        return 0
    coeff = json.loads(a.coefficients.read_text(encoding='utf-8'))
    rows = placements_from_survey(json.loads(a.survey.read_text(encoding='utf-8')))
    xs = [b[0] for _, _, b in rows] + [b[2] for _, _, b in rows]
    ys = [b[1] for _, _, b in rows] + [b[3] for _, _, b in rows]
    points = [(x, y) for y in frange(min(ys), max(ys), a.step) for x in frange(min(xs), max(xs), a.step)]
    values = ring_bytes(rows, coeff, points, a.radius)
    a.out.write_text(json.dumps({'format': FORMAT, 'radius': a.radius, 'step': a.step, 'coefficients': coeff,
                                 'points': [[round(x, 1), round(y, 1), int(v)] for (x, y), v in zip(points, values)]})
                     + '\n', encoding='utf-8', newline='\n')
    return 0


def frange(lo, hi, step):
    v = lo
    while v <= hi:
        yield v
        v += step


if __name__ == '__main__':
    raise SystemExit(main())
