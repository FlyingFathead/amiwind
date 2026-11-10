#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Tree type 2 copies of an expansion layer's tree models (TREES-DEPTH-56, docs/WORLD_TREE_SPRITES.md).

For every tree model of the layer (config/tree-copies.json) this bakes, from the original model:
- the billboard: one camera-facing sprite (the shared tree sprite bake, tools/prepare_tree_sprites.py);
- the star: four oriented sprites (SPR_ORIENTED) at 0, 45, 90 and 135 degrees around the trunk, each the whole tree
  seen across its panel, so that together they make eight half-panels seen from above.

Both copies are sprites, because CHIM model faces have no transparent texels (CHIM-MODEL-FENCE-FACES-64) while the
engine's sprite spans skip palette index 255. The manifest tree-copies.json names both copies per model (the model
path as the CHIM world names it), with the hashes, sizes and pixel bytes, for the engine's per-placement level choice.
TEST BUILDS ONLY: the stage chim-sol-trees of tools/build.py --chim-sol-test runs it; no base stage reads it.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from build_jobs import add_jobs, resolve_jobs
from build_parallel import ordered_map

CONFIG = Path(__file__).resolve().parents[1] / 'config' / 'tree-copies.json'
SCALE = .25
SPR_VP_PARALLEL = 2        # the billboard of the shared bake (prepare_quake._preview_model)
SPR_ORIENTED = 3           # a sprite with its own angle in the world (engine/aga/src/r_sprite.c)
FORMAT = 'AmiWind tree copies 1'


def load_config(path=CONFIG, layer='bloodmoon'):
    doc = json.loads(Path(path).read_text(encoding='utf-8'))
    if doc.get('schema') != 'aw-tree-copies-1':
        raise ValueError('Unknown tree copies schema')
    angles = doc['star_angles_degrees']
    if (not isinstance(angles, list) or len(angles) < 2 or len(set(angles)) != len(angles)
            or any(not isinstance(a, int) or not 0 <= a < 180 for a in angles)):
        raise ValueError('Star angles must be distinct whole degrees in [0, 180)')
    rule = doc['layers'][layer]
    patterns = rule['model_stem_contains']
    if not patterns or any(not isinstance(p, str) or not p for p in patterns):
        raise ValueError('A layer needs model stem patterns')
    points = doc.get('outline_points', 16)
    if not isinstance(points, int) or not 3 <= points <= 64:
        raise ValueError('outline_points must be a whole number in [3, 64]')
    return angles, [p.casefold() for p in patterns], points


def layer_tree_models(master, patterns):
    """The tree models of the layered master whose file stem holds one of PATTERNS (sorted, normalized)."""
    from world_flora import inventory
    from prepare_tree_sprites import normalized_model
    census = inventory(master, ('tree',))
    found = set()
    for ref in census['references']:
        model = normalized_model(ref['model'])
        stem = model.rsplit('/', 1)[-1]
        if any(p in stem for p in patterns):
            found.add(model)
    if not found:
        raise ValueError('No tree model of the layer matches ' + ', '.join(patterns))
    return sorted(found)


def sprite_bytes(pix, kind, radius, width, height, top):
    raw = struct.pack('<4siifiiifi', b'IDSP', 1, kind, radius * SCALE, width, height, 1, 0., 0)
    return raw + struct.pack('<5i', 0, -width // 2, top, width, height) + pix.tobytes()


def bake_view(task):
    """One oriented panel image of a model: the tree seen across the panel at ANGLE degrees (as the billboard bake,
    prepare_quake._preview_model, with the view turned)."""
    import numpy as np
    from PIL import Image
    from mwad.scene import unpack_geometry
    from preview_scenery import render
    key, angle, packet, materials, textures, palette, points = task
    pal = Image.new('P', (1, 1)); pal.putpalette(palette)
    vv, ff, _ = unpack_geometry(packet); v = np.array(vv); f = np.array(ff, int)
    centre = (v[:, :2].min(axis=0) + v[:, :2].max(axis=0)) / 2; v[:, :2] -= centre
    radius = float(np.linalg.norm(v[:, :2], axis=1).max()); bottom = v[:, 2].min(); top = v[:, 2].max()
    w = max(1, math.ceil(radius * 2 * SCALE)); h = max(1, math.ceil((top - bottom) * SCALE))
    rgba = render(v, f, materials, textures, math.radians(angle), (w, h), (-radius, radius, bottom, top))
    pix = np.array(rgba.convert('RGB').quantize(palette=pal, dither=Image.Dither.NONE))
    alpha = np.array(rgba)[:, :, 3]
    pix[alpha < 128] = 255
    raw = sprite_bytes(pix, SPR_ORIENTED, radius, w, h, round(top * SCALE))
    outline = silhouette(alpha >= 128, points)
    return key, angle, raw, {'covered_pixels': int((alpha >= 128).sum()), 'centre': centre.tolist(),
                             'outline': outline}


def polygon_area(poly):
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))) / 2


def silhouette(mask, points):
    """The panel's outline as one simple polygon of at most POINTS corners, in sprite pixels (x right, y down from the
    top row): the covered extent of every row (left edge down, right edge up), then the corner whose removal changes
    the area least is dropped until POINTS remain (Visvalingam). For the opaque cut-out panels (route C) without a
    second bake; covered_share = covered pixels / polygon area (1.0 = the cut-out covers no empty pixel)."""
    import numpy as np
    rows = [y for y in range(mask.shape[0]) if mask[y].any()]
    if not rows:
        raise ValueError('Empty panel view')
    left = [(int(np.argmax(mask[y])), y) for y in rows]
    right = [(int(mask.shape[1] - np.argmax(mask[y][::-1])), y + 1) for y in reversed(rows)]
    poly = [left[0]] + [(x, y + 1) for x, y in left] + right
    dedup = []
    for p in poly:
        if not dedup or dedup[-1] != p:
            dedup.append(p)
    poly = dedup
    while len(poly) > max(3, points):
        costs = [polygon_area([poly[i - 1], poly[i], poly[(i + 1) % len(poly)]]) for i in range(len(poly))]
        del poly[costs.index(min(costs))]
    area = polygon_area(poly)
    return {'points': [list(p) for p in poly], 'corners': len(poly), 'triangles_per_side': len(poly) - 2,
            'area_pixels': area, 'covered_share': round(float(mask.sum()) / area, 4) if area else None}


def validate_star(raw):
    """The oriented sprite's header against its pixels (as prepare_tree_sprites.validate_sprite for the billboard)."""
    magic, version, kind, radius, width, height, frames, _, _ = struct.unpack_from('<4siifiiifi', raw)
    frame_type, _, _, fw, fh = struct.unpack_from('<5i', raw, 36)
    if (magic != b'IDSP' or version != 1 or kind != SPR_ORIENTED or frames != 1 or frame_type != 0
            or width <= 0 or height <= 0 or (width, height) != (fw, fh) or len(raw) != 56 + width * height
            or not math.isfinite(radius) or radius <= 0):
        raise ValueError('Invalid star sprite')


def star_name(billboard_name, angle):
    return billboard_name[:-len('.spr')] + '_star%03d.spr' % angle


def prepare(data_files, palette_path, out, jobs=None, layer='bloodmoon', config=CONFIG):
    import numpy as np
    from mwad.paths import child_ci, ensure_external, resolve_data_files
    from mwad.scene import read_asset
    import prepare_tree_sprites
    angles, patterns, outline_points = load_config(config, layer)
    data = resolve_data_files(Path(data_files))
    out = ensure_external(Path(out), 'private tree copies output')
    if out.exists():
        raise ValueError('Tree copies output exists: ' + str(out))
    budget = resolve_jobs(jobs)
    print('=== PHASE 1/3: the layer\'s tree models ===', flush=True)
    models = layer_tree_models(child_ci(data, 'Morrowind.esm').read_bytes(), patterns)
    print('tree models:', len(models), flush=True)
    print('=== PHASE 2/3: billboards (shared tree sprite bake) ===', flush=True)
    billboard = prepare_tree_sprites.prepare(data, None, palette_path, out / 'billboard', budget, models)
    palette = list(Path(palette_path).read_bytes())
    source = out / 'billboard' / 'source'
    index = json.loads((source / 'scenery-index.json').read_text(encoding='utf-8'))
    by_source = {m['source'].removeprefix('meshes/'): m for m in index['models']}
    print('=== PHASE 3/3: stars (%d oriented sprites per model) ===' % len(angles), flush=True)
    with (source / 'scenery.mwpak').open('rb') as archive:
        textures = {}
        for ti, texture in enumerate(index['textures']):
            raw = read_asset(archive, texture)
            _, width, height = struct.unpack_from('>4sHH', raw)
            textures[ti] = np.frombuffer(raw[8:], np.uint8).reshape(height, width, 4)
        tasks = []
        for asset in billboard['assets']:
            m = by_source[asset['model']]
            used = {x['texture_index'] for x in m['materials'] if x['texture_index'] is not None}
            packet = read_asset(archive, m)
            for angle in angles:
                tasks.append((asset['model'], angle, packet, m['materials'], {i: textures[i] for i in used}, palette,
                              outline_points))
    stars = {}
    done = 0
    for model, angle, raw, report in ordered_map(bake_view, tasks, min(budget, max(1, len(tasks))),
                                                     cost=lambda t: len(t[2])):   # a view's work follows its mesh size
        validate_star(raw)
        stars.setdefault(model, []).append((angle, raw, report))
        done += 1
        print('STAR %d / %d %s %d' % (done, len(tasks), model, angle), flush=True)
    rows = []
    for asset in billboard['assets']:
        name = asset['sprite_asset_name']
        panels = []
        for angle, raw, report in sorted(stars[asset['model']], key=lambda s: s[0]):
            path = star_name(name, angle)
            (out / 'billboard' / path).parent.mkdir(parents=True, exist_ok=True)
            (out / 'billboard' / path).write_bytes(raw)
            _, _, _, _, w, h, *_ = struct.unpack_from('<4siifiiifi', raw)
            panels.append({'angle_degrees': angle, 'sprite': path, 'sha256': hashlib.sha256(raw).hexdigest(),
                           'bytes': len(raw), 'pixel_bytes': w * h, 'covered_pixels': report['covered_pixels'],
                           'outline': report['outline']})
        rows.append({'model': 'meshes/' + asset['model'],
                     'billboard': {'sprite': name, 'sha256': asset['sha256'], 'bytes': asset['bytes'],
                                   'pixel_bytes': asset['pixel_bytes'], 'pixel_dimensions': asset['pixel_dimensions']},
                     'star': panels,
                     'star_pixel_bytes': sum(p['pixel_bytes'] for p in panels),
                     'bake_centre': asset['source_xy_bake_center'],
                     'original_instances': asset['original_instances']})
    manifest = {'format': FORMAT, 'layer': layer, 'star_angles_degrees': angles, 'outline_points': outline_points,
                'sprite_types': {'billboard': SPR_VP_PARALLEL, 'star': SPR_ORIENTED},
                'why_sprites': 'CHIM model faces have no transparent texels (CHIM-MODEL-FENCE-FACES-64)',
                'runtime_activation': False, 'models': rows,
                'pixel_bytes': {'billboards': sum(r['billboard']['pixel_bytes'] for r in rows),
                                'stars': sum(r['star_pixel_bytes'] for r in rows)},
                'billboard_receipt_sha256': hashlib.sha256(
                    (out / 'billboard' / 'tree-sprites.json').read_bytes()).hexdigest()}
    (out / 'tree-copies.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('TREE COPIES %d models; pixel bytes: billboards %d, stars %d' % (
        len(rows), manifest['pixel_bytes']['billboards'], manifest['pixel_bytes']['stars']), flush=True)
    return manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--data-files', type=Path, required=True, help='The layered test data (tools/chim_layer_data.py)')
    ap.add_argument('--palette', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--layer', default='bloodmoon')
    add_jobs(ap)
    a = ap.parse_args()
    prepare(a.data_files, a.palette, a.out, a.jobs, a.layer)


if __name__ == '__main__':
    main()
