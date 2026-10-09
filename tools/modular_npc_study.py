#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Modular NPC study (docs/MODULAR_NPCS.md): part census and composition prototype.

census   every humanoid appearance of the gallery resolver -> unique parts,
         uses, source faces/texture bytes and the quota each part gets in
         each whole-appearance bake; library quota-tier estimates.
compose  N residents: whole-actor bake (the resident stage's method) versus
         parts baked once and concatenated; faces, bytes, time, flat previews.

Host-only measurement. Reads the owner's data; writes JSON (and private
preview PNGs) to --out. Nothing here enters a game image.
"""
import argparse
import hashlib
import json
import statistics
import struct
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mwad.audit import BSA, normpath
from mwad.npc import load_master, outfit
from mwad.paths import child_ci
from build_parallel import ordered_map
from npc_geometry import Assets, Skeleton, assemble, bake, bake_quotas, animated_mdl

RESIDENT_BUDGETS = (480, 384, 320, 256, 192)


def part_key(appearance, part):
    """A library part: one mesh, its shape filter and attachment on one skeleton.

    The same NIF is several parts (a shirt covers chest and both arms) and a
    rigid mesh on a Left bone is mirrored, so the NIF path alone is not a key.
    """
    return '|'.join((appearance['skeleton'], normpath(part['mesh']), part['filter'].casefold(),
                     part['attach'].casefold(), str(part['slot'])))


def appearances(data):
    kinds, cells, _ = load_master(child_ci(data, 'Morrowind.esm'))
    specs = {}; records = 0; errors = 0; record_uses = 0
    for identifier in sorted(kinds['NPC_']):
        records += 1
        for equipped in (True, False):
            try:
                app = outfit(kinds, identifier, equipped=equipped)
            except (ValueError, KeyError):
                errors += 1; continue
            spec = {k: app[k] for k in ('parts', 'skeleton', 'height', 'weight')}
            record_uses += len(spec['parts'])
            key = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()[:16]
            specs[key] = spec
    return kinds, cells, specs, {'records': records, 'resolver_errors': errors,
                                 'record_part_uses': record_uses}


_ctx = {}


def context(data):
    if 'assets' not in _ctx:
        _ctx['assets'] = Assets(Path(data), BSA(child_ci(Path(data), 'Morrowind.bsa')))
        _ctx['skeletons'] = {}
    return _ctx['assets'], _ctx['skeletons']


def skeleton_for(data, source):
    assets, skeletons = context(data)
    if source not in skeletons:
        skeletons[source] = Skeleton(assets, source)
    return assets, skeletons[source]


def part_census(task):
    data, key, skeleton_source, part = task
    assets, skeleton = skeleton_for(data, skeleton_source)
    start = time.perf_counter()
    times, _ = skeleton.idle_times(8)
    shapes, materials, textures = assemble(assets, {'parts': [part], 'weight': 1., 'height': 1.}, skeleton, times)
    seconds = time.perf_counter() - start
    return {'key': key, 'shapes': [{'name': s['name'], 'faces': int(len(s['faces'])),
                                    'vertices': int(s['positions'].shape[1])} for s in shapes],
            'source_faces': int(sum(len(s['faces']) for s in shapes)),
            'textures': sorted(t for t in textures if t),
            'texture_rgba_bytes': int(sum(t.nbytes for t in textures.values() if t is not None)),
            'assemble_8_frames_seconds': round(seconds, 4)}


def whole_quotas(spec, census):
    """Replicate the whole-appearance quota split without baking (bake_quotas)."""
    shapes = []; owners = []
    for part in spec['parts']:
        row = census[part_key(spec, part)]
        for s in row['shapes']:
            shapes.append({'name': s['name'], 'part': part['slot'], 'faces': np.zeros((s['faces'], 3), int),
                           'positions': np.zeros((8, 1, 3))})
            owners.append(part_key(spec, part))
    for budget in RESIDENT_BUDGETS:
        try:
            quotas = bake_quotas(shapes, budget)
        except ValueError:
            continue
        output = [min(int(q), len(s['faces'])) for q, s in zip(quotas, shapes)]
        if sum(output) < 666:
            per_part = {}
            for owner, value in zip(owners, output):
                per_part[owner] = per_part.get(owner, 0) + value
            return budget, per_part
    raise ValueError('No resident budget fits')


def census_main(args):
    kinds, cells, specs, counts = appearances(args.data_files)
    parts = {}; uses = {}
    for spec in specs.values():
        for part in spec['parts']:
            key = part_key(spec, part)
            parts.setdefault(key, (spec['skeleton'], part)); uses[key] = uses.get(key, 0) + 1
    meshes = {normpath(p['mesh']) for _, p in parts.values()}
    tasks = [(str(args.data_files), key, sk, part) for key, (sk, part) in sorted(parts.items())]
    started = time.perf_counter(); census = {}
    for row in ordered_map(part_census, tasks, args.jobs):
        census[row['key']] = row
    census_seconds = time.perf_counter() - started
    # Per appearance: the quota each part shape gets in today's whole bake.
    per_part_quotas = {}; whole_faces = []; budgets = {}
    for spec in specs.values():
        budget, per_part = whole_quotas(spec, census)
        budgets[budget] = budgets.get(budget, 0) + 1; whole_faces.append(sum(per_part.values()))
        for owner, quota in per_part.items():
            per_part_quotas.setdefault(owner, []).append(quota)
    # Library tiers: per part, the distinct quota levels needed (quantiles).
    tiers = {}
    for key, values in per_part_quotas.items():
        faces = census[key]['source_faces']
        qs = sorted(values)
        pick = lambda f: qs[min(len(qs) - 1, int(f * (len(qs) - 1) + .5))]
        tiers[key] = {'source_faces': faces, 'uses': len(qs), 'min': qs[0], 'median': pick(.5),
                      'max': qs[-1], 'p10': pick(.1), 'p90': pick(.9), 'distinct': len(set(qs))}
    textures = {}
    for row in census.values():
        for t in row['textures']:
            textures[t] = True
    report = {
        'format': 'AmiWind modular NPC census 1',
        'counts': {**counts, 'appearances': len(specs), 'part_uses': sum(uses.values()),
                   'unique_parts': len(parts), 'unique_meshes': len(meshes),
                   'unique_textures': len(textures),
                   'reuse_factor': round(sum(uses.values()) / len(parts), 2)},
        'source_faces': {
            'whole_appearances_sum': int(sum(sum(census[part_key(s, p)]['source_faces'] for p in s['parts'])
                                             for s in specs.values())),
            'unique_parts_sum': int(sum(r['source_faces'] for r in census.values()))},
        'whole_bake_output_faces': {'sum': int(sum(whole_faces)), 'mean': round(statistics.mean(whole_faces), 1),
                                    'max': max(whole_faces), 'budget_histogram': budgets},
        'library_output_faces': {
            'one_tier_median_sum': int(sum(t['median'] for t in tiers.values())),
            'one_tier_max_sum': int(sum(t['max'] for t in tiers.values())),
            'three_tier_sum': int(sum(sum({t['p10'], t['median'], t['p90']}) for t in tiers.values())),
            'all_distinct_quotas_sum': int(sum(sum(set(per_part_quotas[k])) for k in tiers))},
        'census_seconds': round(census_seconds, 1), 'jobs': args.jobs,
        'assemble_seconds_sum': round(sum(r['assemble_8_frames_seconds'] for r in census.values()), 1),
        'parts': census, 'tiers': tiers}
    # Composition with the one-tier (median) library: faces per appearance.
    composed = [sum(tiers[part_key(s, p)]['median'] for p in s['parts']) for s in specs.values()]
    report['one_tier_composed_faces'] = {'mean': round(statistics.mean(composed), 1), 'max': max(composed),
                                         'over_480': sum(c > 480 for c in composed),
                                         'over_666': sum(c > 666 for c in composed)}
    Path(args.out).mkdir(parents=True, exist_ok=True)
    (Path(args.out) / 'census.json').write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('parts', 'tiers')}, indent=1))


def bake_resident(assets, skeleton, appearance, times):
    shapes, materials, textures = assemble(assets, appearance, skeleton, times)
    for budget in RESIDENT_BUDGETS:
        try:
            return bake(shapes, materials, textures, _ctx['palette'], budget=budget), shapes
        except ValueError as error:
            if str(error) != 'Alias vertex budget exceeded' or budget == RESIDENT_BUDGETS[-1]:
                raise


def library_bytes(frames, faces, uv, skin, tile=16):
    """Stored size of one baked part: tiles + st/tri records + frame vertices."""
    nf, nv, _ = frames.shape
    return len(faces) * tile * tile + nv * 12 + len(faces) * 16 + nf * (24 + nv * 4)


def compose(parts, scale):
    """Concatenate part bakes: frames (scaled), faces (offset), tiles (repacked)."""
    from PIL import Image
    frames = []; faces = []; uv = []; tiles = []; base = 0
    for frames_p, faces_p, uv_p, skin_p in parts:
        frames.append(frames_p * scale)
        faces.append(faces_p + base); base += frames_p.shape[1]
        for i in range(len(faces_p)):
            tiles.append(skin_p.crop((i % 32 * 16, i // 32 * 16, i % 32 * 16 + 16, i // 32 * 16 + 16)))
    count = len(tiles); height = max(256, ((count + 31) // 32) * 16)
    skin = Image.new('P', (512, height)); skin.putpalette(parts[0][3].getpalette())
    for i, tile in enumerate(tiles):
        tx, ty = i % 32 * 16, i // 32 * 16; skin.paste(tile, (tx, ty)); uv.extend([(tx, ty), (tx + 15, ty), (tx, ty + 15)])
    return np.concatenate(frames, axis=1), np.concatenate(faces), np.array(uv), skin


def preview(frames, faces, uv, skin, size=200):
    """Flat front view: each face filled with its tile's mean colour (not in-game)."""
    from PIL import Image, ImageDraw
    pal = np.array(skin.getpalette()[:768]).reshape(256, 3); pix = np.array(skin)
    p = frames[0]; lo = p.min(0); hi = p.max(0); s = (size - 10) / max(hi[2] - lo[2], 1e-3)
    image = Image.new('RGB', (size // 2 + 20, size), (40, 40, 48)); draw = ImageDraw.Draw(image)
    tris = p[faces]
    order = np.argsort(tris[:, :, 0].mean(1))[::-1]  # painter's order along x
    cx = (lo[1] + hi[1]) / 2
    for fi in order:
        t = tris[fi]; u = uv[faces[fi][0]]
        colour = pal[pix[int(u[1]):int(u[1]) + 16, int(u[0]):int(u[0]) + 16]].reshape(-1, 3).mean(0)
        pts = [((v[1] - cx) * s + image.width / 2, size - 5 - (v[2] - lo[2]) * s) for v in t]
        draw.polygon(pts, fill=tuple(int(c) for c in colour))
    return image


def compose_main(args):
    from PIL import Image, ImageDraw
    kinds, cells, _ = load_master(child_ci(args.data_files, 'Morrowind.esm'))
    _ctx['palette'] = args.palette.read_bytes()
    ids = sorted({r['id'].casefold() for c in cells if c['name'].startswith(args.cell_prefix)
                  for r in c['refs'] if not r.get('deleted') and r['id'].casefold() in kinds['NPC_']})
    scene_uses = 0; scene_parts = set()
    for identifier in ids:
        app = outfit(kinds, identifier); scene_uses += len(app['parts'])
        scene_parts.update(part_key(app, part) for part in app['parts'])
    scene = {'actors': len(ids), 'part_uses': scene_uses, 'unique_parts': len(scene_parts)}
    if len(ids) > args.count:
        ids = [ids[round(i * (len(ids) - 1) / (args.count - 1))] for i in range(args.count)]
    census = json.loads(Path(args.census).read_text()) if args.census else None
    if args.policy == 'tier3' and not census:
        raise SystemExit('--policy tier3 needs --census')
    assets, _ = context(str(args.data_files)); part_cache = {}; rows = []; previews = []
    for identifier in ids:
        app = outfit(kinds, identifier)
        assets, skeleton = skeleton_for(str(args.data_files), app['skeleton'])
        times, _ = skeleton.idle_times(8)
        t0 = time.perf_counter()
        (frames, faces, uv, skin), shapes = bake_resident(assets, skeleton, app, times)
        whole = animated_mdl(frames, faces, uv, skin); whole_s = time.perf_counter() - t0
        frame0 = np.concatenate([s['positions'][0] for s in shapes])
        reference_height = float(np.ptp(frame0[:, 2])) / app['height']
        offsets = []; at = 0
        for part in app['parts']:
            n = len(assemble(assets, {'parts': [part], 'weight': 1., 'height': 1.}, skeleton, times[:1])[0])
            offsets.append((at, at + n)); at += n
        new_parts = 0; part_seconds = 0.
        # The resident stage retries lower budgets when 480 overflows the alias
        # limit; a recipe does the same with its parts' quotas.
        for budget in RESIDENT_BUDGETS:
            whole_q = bake_quotas(shapes, budget); parts = []
            for part, (a, b) in zip(app['parts'], offsets):
                key = part_key(app, part); q = [int(x) for x in whole_q[a:b]]
                if args.policy == 'tier3':
                    t = census['tiers'][key]; want = sum(min(x, s['faces']) for x, s in zip(q, census['parts'][key]['shapes']))
                    tier = min(sorted({t['p10'], t['median'], t['p90']}), key=lambda l: (abs(l - want), l))
                    q = [max(1, round(tier * s['faces'] / census['parts'][key]['source_faces'])) for s in census['parts'][key]['shapes']]
                ck = key + '|' + ','.join(map(str, q))
                if ck not in part_cache:
                    p0 = time.perf_counter()
                    ps, pm, pt = assemble(assets, {'parts': [part], 'weight': 1., 'height': 1.}, skeleton, times)
                    part_cache[ck] = bake(ps, pm, pt, _ctx['palette'], quotas=q, shell_height=reference_height)
                    part_seconds += time.perf_counter() - p0; new_parts += 1
                parts.append(part_cache[ck])
            if sum(len(x[1]) for x in parts) < 666 or args.policy == 'tier3':
                break
        merge0 = time.perf_counter()
        cf, cfa, cuv, cskin = compose(parts, np.array([app['weight'], app['weight'], app['height']]))
        merge_s = time.perf_counter() - merge0
        composed = animated_mdl(cf, cfa, cuv, cskin, vertex_limit=3072 if len(cfa) > 666 else 1999)
        delta = np.abs(cf.min((0, 1)) - frames.min((0, 1))).max(), np.abs(cf.max((0, 1)) - frames.max((0, 1))).max()
        rows.append({'id': identifier, 'parts': len(app['parts']), 'whole_faces': int(len(faces)),
                     'whole_bytes': len(whole), 'whole_seconds': round(whole_s, 3),
                     'composed_faces': int(len(cfa)), 'composed_bytes': len(composed),
                     'new_parts_baked': new_parts, 'part_bake_seconds': round(part_seconds, 3),
                     'host_merge_seconds': round(merge_s, 4),
                     'bounds_delta_units': [round(float(d), 3) for d in delta]})
        print(json.dumps(rows[-1]), flush=True)
        if args.previews:
            a = preview(frames, faces, uv, skin); b = preview(cf, cfa, cuv, cskin)
            pair = Image.new('RGB', (a.width + b.width, a.height + 14), (20, 20, 24)); pair.paste(a, (0, 14)); pair.paste(b, (a.width, 14))
            ImageDraw.Draw(pair).text((2, 1), identifier[:22], fill=(230, 230, 230)); previews.append(pair)
    unique_bytes = sum(library_bytes(*p) for p in part_cache.values())
    summary = {'format': 'AmiWind modular NPC compose 1', 'policy': args.policy, 'cell_prefix': args.cell_prefix,
               'scene_reuse': scene,
               'actors': len(rows), 'unique_part_bakes': len(part_cache),
               'whole_faces': sum(r['whole_faces'] for r in rows), 'composed_faces': sum(r['composed_faces'] for r in rows),
               'whole_bytes': sum(r['whole_bytes'] for r in rows), 'composed_bytes': sum(r['composed_bytes'] for r in rows),
               'parts_library_bytes_as_mdls': unique_bytes,
               'whole_seconds': round(sum(r['whole_seconds'] for r in rows), 2),
               'part_bake_seconds': round(sum(r['part_bake_seconds'] for r in rows), 2),
               'host_merge_seconds': round(sum(r['host_merge_seconds'] for r in rows), 3), 'rows': rows}
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    (out / f'compose-{args.policy}.json').write_text(json.dumps(summary, indent=1) + '\n', encoding='utf-8', newline='\n')
    if previews:
        cols = 5; w, h = previews[0].size; sheet = Image.new('RGB', (cols * w, ((len(previews) + cols - 1) // cols) * h), (0, 0, 0))
        for i, p in enumerate(previews):
            sheet.paste(p, (i % cols * w, i // cols * h))
        sheet = sheet.resize((sheet.width * 2, sheet.height * 2), Image.Resampling.NEAREST)
        sheet.save(out / f'compose-{args.policy}.png')
    print(json.dumps({k: v for k, v in summary.items() if k != 'rows'}, indent=1))


def policies_main(args):
    """Library quota policies from a census: size, faces per appearance, quality deficit."""
    census = json.loads(Path(args.census).read_text())
    kinds, cells, specs, counts = appearances(args.data_files)
    today = {}; exact = set(); exact_scaled = set()
    for key, spec in specs.items():
        budget, per_part = whole_quotas(spec, census['parts'])
        today[key] = per_part
        for part in spec['parts']:
            k = part_key(spec, part); exact.add((k, per_part[k]))
            exact_scaled.add((k, per_part[k], round(spec['height'], 4), round(spec['weight'], 4)))
    def ladder(values, count):
        qs = sorted(values)
        return sorted({qs[min(len(qs) - 1, int(i * (len(qs) - 1) / max(1, count - 1) + .5))] for i in range(count)})
    per_part = {}
    for per in today.values():
        for k, q in per.items():
            per_part.setdefault(k, []).append(q)
    result = {'exact_library': {'bakes': len(exact), 'faces': int(sum(q for _, q in exact))},
              'exact_library_per_race_scale': {'bakes': len(exact_scaled), 'faces': int(sum(q for _, q, _, _ in exact_scaled))}}
    for tiers in (1, 2, 3, 4, 6):
        levels = {k: ladder(v, tiers) for k, v in per_part.items()}
        if tiers == 1:
            levels = {k: [census['tiers'][k]['median']] for k in per_part}
        down = []; near = []; deficit = []
        for key, per in today.items():
            d = sum(max([l for l in levels[k] if l <= q] or [min(levels[k])]) for k, q in per.items())
            n = sum(min(levels[k], key=lambda l: (abs(l - q), l)) for k, q in per.items())
            down.append(d); near.append(n); deficit.append(sum(per.values()) - d)
        faces = int(sum(sum(v) for v in levels.values()))
        result[f'tiers_{tiers}'] = {
            'bakes': int(sum(len(v) for v in levels.values())), 'faces': faces,
            'round_down_mean_faces': round(statistics.mean(down), 1), 'round_down_min': min(down),
            'round_down_mean_deficit_vs_today': round(statistics.mean(deficit), 1),
            'nearest_mean_faces': round(statistics.mean(near), 1), 'nearest_max': max(near),
            'nearest_over_480': sum(n > 480 for n in near), 'nearest_over_666': sum(n > 666 for n in near)}
    result['today_mean_faces'] = round(statistics.mean(sum(v.values()) for v in today.values()), 1)
    Path(args.out).mkdir(parents=True, exist_ok=True)
    (Path(args.out) / 'policies.json').write_text(json.dumps(result, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(result, indent=1))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    for name in ('census', 'compose', 'policies'):
        s = sub.add_parser(name)
        s.add_argument('--data-files', type=Path, required=True)
        s.add_argument('--out', type=Path, required=True)
        s.add_argument('--jobs', type=int, default=1)
    c = sub.choices['compose']
    c.add_argument('--palette', type=Path, required=True)
    c.add_argument('--cell-prefix', default='Balmora')
    c.add_argument('--count', type=int, default=20)
    c.add_argument('--policy', choices=('outfit', 'tier3'), default='outfit')
    c.add_argument('--census', type=Path)
    c.add_argument('--previews', action='store_true')
    sub.choices['policies'].add_argument('--census', type=Path, required=True)
    args = p.parse_args()
    {'census': census_main, 'compose': compose_main, 'policies': policies_main}[args.command](args)


if __name__ == '__main__':
    main()
