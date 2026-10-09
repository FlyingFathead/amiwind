# SPDX-License-Identifier: GPL-3.0-only
"""chim-stats.json: polycounts, disk, memory, streaming and build figures of a CHIM world.

Every CHIM build writes this file next to chim/ (schema "chim-stats 1",
documented in docs/chim/STATS.md). It is made from the world files as the
validator reads them (chim.validate), the validator's measurements and the
builder receipt, so the numbers describe what is on disk, not what the builder
meant to write. Counts are the main currency; times are the builder's own wall
and CPU seconds and the read cost model's estimates (chim.readcost).

Usage: stats.py OUT [--legacy-maps DIR --legacy-regions FILE] [--camera NAME X Y]... [--json FILE]
"""
import argparse
import collections
import json
import statistics
import struct
import sys
from pathlib import Path

if __package__ in (None, ''):
    sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parents[2] / 'src')]

from chim import format as F  # noqa: E402

SCHEMA = 'chim-stats 1'
TOP = 20
FACE_BYTES = 20                     # BSP29 dface_t
FACES_LUMP = 7
# The developers' benchmark cameras (docs/HARDWARE-BENCHMARK.md, "Frame time in the game"):
# original Morrowind positions, by town id of config/towns.json.
BENCHMARK_CAMERAS = {
    'balmora': [('Balmora 1', -20088, -14638), ('Balmora 2', -20970, -16963), ('Balmora 3', -21800, -12300),
                ('Balmora 4', -19000, -11000), ('Balmora 5', -20500, -9500)],
    'seyda': [('Seyda Neen 1', -11264, -71680), ('Seyda Neen 2', -11548, -71200),
              ('Seyda Neen 3', -10474, -73437), ('Seyda Neen 4', -10920, -75120),
              ('Seyda Neen 5', -12200, -72500)],
}
# Figures copied from the validator's walk per cache size (bytes and estimated ms per crossing).
WALK_FIELDS = ('crossings', 'crossings_reading', 'bytes_read', 'per_crossing_p50', 'per_crossing_max',
               'seek_runs_p50', 'seek_runs_max', 'files_per_crossing_p50', 'estimated_ms_p50',
               'estimated_ms_max', 'estimated_ms_total', 'cold_bytes', 'cold_estimated_ms',
               'resident_p50', 'resident_max')


def pct(values, q):
    """Nearest-rank percentile, the same rule as the validator's reports."""
    v = sorted(values)
    return v[min(len(v) - 1, int(q * (len(v) - 1)))] if v else 0


def distribution(values):
    values = list(values)
    if not values:
        return {'count': 0, 'total': 0, 'min': 0, 'p50': 0, 'p95': 0, 'max': 0, 'mean': 0}
    return {'count': len(values), 'total': sum(values), 'min': min(values), 'p50': pct(values, .5),
            'p95': pct(values, .95), 'max': max(values), 'mean': round(statistics.mean(values), 2)}


def faces_of(image):
    return len(F.read_brush_image(image)[FACES_LUMP]) // FACE_BYTES


def bsp_faces(path):
    """Faces of a Quake BSP29 file from its lump directory (no decoding)."""
    with open(path, 'rb') as f:
        head = f.read(4 + 15 * 8)
    version, = struct.unpack_from('<i', head)
    if version != 29:
        raise ValueError('%s: not a BSP29 map' % path)
    _, size = struct.unpack_from('<ii', head, 4 + FACES_LUMP * 8)
    return size // FACE_BYTES


def legacy_summary(legacy_maps, legacy_regions):
    """Today's region maps of the same area: files, bytes and faces stored."""
    from world_chunk_estimate import read_regions
    regions = read_regions(Path(legacy_regions).read_text(encoding='utf-8'))
    paths = [Path(legacy_maps) / (n + '.bsp') for n in sorted(regions)]
    sizes = [p.stat().st_size for p in paths]
    faces = [bsp_faces(p) for p in paths]
    return {'regions': len(paths), 'files': len(paths), 'bytes': sum(sizes),
            'faces_stored': sum(faces), 'faces_per_region': distribution(faces),
            'bytes_per_region': distribution(sizes)}


def chunk_cell(frame, x, y):
    """The chunk of a Morrowind position (frame-local units are a quarter of Morrowind's)."""
    lxp, lyp = (x - frame['centre'][0]) * 0.25, (y - frame['centre'][1]) * 0.25
    g, (lx, ly) = frame['grain'], frame['low']
    return (min(frame['nx'] - 1, max(0, int((lxp - lx) // g))), min(frame['ny'] - 1, max(0, int((lyp - ly) // g))))


def resident_rings(world, model_tex):
    """Per chunk as the player's chunk: what its ring needs resident (file bytes; engine
    structures differ, the engine reports its own zone use): the ring's chunk records, the
    distinct models its placements use and the distinct textures of those and of the ground."""
    from asset_census import ring_offsets
    settings = world['settings']
    models, textures = world['models'], world['textures']
    rows = []
    for path, frame, _ in world['frames']:
        by_cell = {c['cell']: c for c in world['chunks'] if c['frame'] == path}
        offs = ring_offsets(frame['grain'], settings['draw_distance'] + settings['hysteresis'])
        for cell in sorted(by_cell):
            ring = [by_cell[k] for k in ((cell[0] + dx, cell[1] + dy) for dx, dy in offs) if k in by_cell]
            mids = sorted({r['model'] for c in ring for r in c['records']})
            tids = {t for c in ring for t in c['terrain_textures']} | {t for m in mids for t in model_tex[m]}
            chunk_bytes = sum(c['render'] + c['collision'] for c in ring)
            model_bytes = sum(models[m]['bytes'] for m in mids)
            model_render = sum(models[m]['render'] for m in mids)
            texture_bytes = sum(textures[t]['bytes'] for t in tids)
            rows.append({'cell': list(cell), 'chunks': len(ring), 'models': len(mids), 'textures': len(tids),
                         'chunk_bytes': chunk_bytes, 'model_bytes': model_bytes, 'model_render_bytes': model_render,
                         'texture_bytes': texture_bytes, 'total_bytes': chunk_bytes + model_bytes + texture_bytes})
    return rows


def chim_stats(world, measured, receipt=None, areas=None, legacy=None, cameras=(), top=TOP, source=None):
    """The chim-stats document (schema SCHEMA) from a validated world (chim.validate.validate),
    its measurements (chim.validate.measure), the builder receipt and today's region maps."""
    receipt = receipt or {}
    models, textures, chunks = world['models'], world['textures'], world['chunks']
    model_faces = [faces_of(m['image']) for m in models]
    model_tex = [F.read_texture_refs(F.read_brush_image(m['image'])[2]) for m in models]
    owned = [(c, r) for c in chunks for r in c['owned']]
    uses = collections.Counter(r['model'] for _, r in owned)
    # models
    per_model = [{'id': i, 'name': m['name'], 'faces': model_faces[i], 'render_bytes': m['render'],
                  'collision_bytes': m['bytes'] - m['render'], 'placements': uses[i],
                  'placed_faces': model_faces[i] * uses[i], 'file': m['file']} for i, m in enumerate(models)]

    def short(row):
        return {k: row[k] for k in ('id', 'name', 'faces', 'placements', 'placed_faces', 'render_bytes')}
    by_faces = sorted(per_model, key=lambda r: (-r['faces'], r['id']))
    by_placed = sorted(per_model, key=lambda r: (-r['placed_faces'], r['id']))
    # placements (owner records: each placement once)
    placement_rows = sorted([r['pid'], r['model'], model_faces[r['model']], r['leaves'], c['cell'][0], c['cell'][1]]
                            for c, r in owned)
    leaves = [row[3] for row in placement_rows]
    # chunks
    chunk_rows = []
    for c in sorted(chunks, key=lambda c: (c['frame'], c['cell'])):
        placed = sum(model_faces[r['model']] for r in c['owned'])
        reach = sum(model_faces[r['model']] for r in c['reach'])
        chunk_rows.append({'frame': c['frame'], 'cell': list(c['cell']), 'terrain_faces': c['faces'],
                           'owned': len(c['owned']), 'reach': len(c['reach']), 'placed_faces': placed,
                           'faces': c['faces'] + placed, 'faces_with_reach': c['faces'] + placed + reach,
                           'bytes': c['render'] + c['collision']})
    heavy_chunks = sorted(chunk_rows, key=lambda r: (-r['faces'], r['frame'], r['cell']))
    terrain_faces = sum(c['faces'] for c in chunks)
    faces = {'models_stored': sum(model_faces), 'terrain': terrain_faces,
             'stored': sum(model_faces) + terrain_faces,
             'placed': sum(row[2] for row in placement_rows) + terrain_faces}
    faces['placed_over_stored'] = round(faces['placed'] / faces['stored'], 2) if faces['stored'] else None
    # views: benchmark cameras (terrain of the potentially visible chunks + the placement list)
    views = {'cameras': [], 'all_chunks': measured.get('visibility', {})}
    by_name = {v['camera']: v for v in measured.get('cameras', [])}
    if world['visibility'] and cameras:
        from chim.validate import frame_of_point
        for name, x, y in cameras:
            k = frame_of_point(world, x, y)
            if k is None:                               # listed, not counted: no frame of the world holds it
                views['cameras'].append({'camera': name, 'position': [x, y], 'frame': None})
                continue
            path, frame, _ = world['frames'][k]
            vis = world['visibility'][k]
            by_cell = {c['cell']: c for c in chunks if c['frame'] == path}
            cell = chunk_cell(frame, x, y)
            row = dict(by_name.get(name, {}), camera=name, position=[x, y], chunk=list(cell))
            row['visible_chunks'] = len(vis['vis'].get(cell, ()))
            row['terrain_faces'] = sum(by_cell[b]['faces'] for b in vis['vis'].get(cell, ()))
            row['faces'] = row['terrain_faces'] + row.get('placement_list_faces', 0)
            views['cameras'].append(row)
        cams = [r for r in views['cameras'] if r.get('frame') is not None]
        if cams:
            views['camera_faces'] = {'p50': pct([r['faces'] for r in cams], .5), 'max': max(r['faces'] for r in cams)}
    views.setdefault('camera_faces', None)
    # disk
    files = [f for f in world['files']]
    sectors = [f for f in files if f['kind'] == b'SECT']
    per_file = collections.Counter(m['file'] for m in models)
    per_file_tex = collections.Counter(t['file'] for t in textures)
    paks = sorted(({'path': f['path'], 'bytes': f['bytes'], 'records': f['entries'], 'models': per_file[f['path']],
                    'textures': per_file_tex[f['path']]} for f in sectors), key=lambda r: (-r['bytes'], r['path']))
    chim_bytes = sum(world['sizes'].values())
    area_names = list(areas or [receipt.get('town', 'area')])
    disk = {'files': len(world['sizes']), 'bytes': chim_bytes, 'bytes_by_kind': measured.get('bytes_by_kind', {}),
            'paks': len(sectors), 'pak_bytes': distribution(f['bytes'] for f in sectors),
            'largest_paks': paks[:top],
            'stored_once': {'model_bytes': sum(m['bytes'] for m in models),
                            'model_bytes_if_each_placement_stored_its_own': sum(models[r['model']]['bytes']
                                                                                for _, r in owned)},
            'areas': {}}
    so = disk['stored_once']
    so['model_sharing_factor'] = round(so['model_bytes_if_each_placement_stored_its_own'] / so['model_bytes'], 2) \
        if so['model_bytes'] else None
    # A world of one area: every file. Several areas: each area's frame and sector files
    # (by the source sections' cells); the index is shared (index_bytes).
    cells = {s['town']: tuple(s['cell']) for s in (source or {}).get('frames', [])}
    disk['index_bytes'] = world['sizes'].get('world.cwi', 0)
    for name in area_names:
        own = ([f for f in files if tuple(f['cell']) == cells[name]] if len(area_names) > 1 and name in cells
               else None)
        row = {'chim_bytes': sum(f['bytes'] for f in own) if own is not None else chim_bytes,
               'chim_files': len(own) if own is not None else len(world['sizes']),
               'legacy_bytes': None, 'legacy_files': None, 'duplication_factor': None}
        if legacy and len(area_names) == 1:
            row.update(legacy_bytes=legacy['bytes'], legacy_files=legacy['files'],
                       duplication_factor=round(legacy['bytes'] / chim_bytes, 2) if chim_bytes else None)
        disk['areas'][name] = row
    # memory
    rings = resident_rings(world, model_tex)
    peak = max(rings, key=lambda r: (r['total_bytes'], r['cell'])) if rings else {}
    walk = measured.get('walk', {})
    memory = {'ring_chunks': walk.get('ring_chunks'),
              'resident_ring_bytes': distribution(r['total_bytes'] for r in rings),
              'resident_ring_peak': peak,
              'model_zone_bytes': distribution(r['model_bytes'] for r in rings),
              'model_zone_peak_bytes': max((r['model_bytes'] for r in rings), default=0),
              'walk_resident_max': walk.get('extra_0', {}).get('resident_max'),
              'basis': 'file bytes of the ring\'s chunk records, distinct models and textures; '
                       'decoded engine structures differ'}
    # streaming
    streaming = {'route_stops': walk.get('route_stops'), 'chunks_visited': walk.get('chunks_visited'),
                 'cache': {}, 'legacy': walk.get('legacy'), 'cost_model': walk.get('cost_model')}
    for key, value in sorted(walk.items()):
        if key.startswith('extra_') and isinstance(value, dict):
            streaming['cache'][key[len('extra_'):]] = {k: value[k] for k in WALK_FIELDS if k in value}
    timing = receipt.get('timing', {})
    build = {'wall_seconds': receipt.get('wall_seconds', timing.get('seconds')),
             'cpu_seconds': timing.get('cpu_seconds'), 'jobs': receipt.get('jobs'),
             'sections': timing.get('sections', []), 'units': receipt.get('units', {})}
    # pain points: the top 5 % by cost, and every placement the engine cannot cull (> MAX_ENT_LEAFS)
    pain = []
    cut = pct([r['placed_faces'] for r in per_model], .95)
    pain += [{'kind': 'model', 'id': r['id'], 'name': r['name'], 'value': r['placed_faces'],
              'rule': 'placed faces in the top 5 %'} for r in by_placed if r['placed_faces'] >= cut > 0][:top]
    cut = pct([r['faces'] for r in chunk_rows], .95)
    pain += [{'kind': 'chunk', 'cell': r['cell'], 'value': r['faces'], 'rule': 'chunk faces in the top 5 %'}
             for r in heavy_chunks if r['faces'] >= cut > 0][:top]
    over = sorted((row for row in placement_rows if row[3] > F.MAX_ENT_LEAFS), key=lambda r: (-r[3], r[0]))
    pain += [{'kind': 'placement', 'id': r[0], 'model': models[r[1]]['name'], 'value': r[3],
              'rule': 'over %d leaves: sent with every view of its chunks' % F.MAX_ENT_LEAFS} for r in over[:top]]
    out = {
        'schema': SCHEMA, 'builder': 'chim', 'chim_version': receipt.get('chim_version'),
        'world_format': receipt.get('world_format'), 'areas': area_names,
        'counts': {'models': len(models), 'textures': len(textures), 'chunks': len(chunks),
                   'placements': len(placement_rows), 'reach_copies': sum(len(c['reach']) for c in chunks),
                   'frames': len(world['frames']), 'paks': len(sectors)},
        'faces': faces,
        'models': {'faces': distribution(model_faces), 'top_by_faces': [short(r) for r in by_faces[:top]],
                   'top_by_placed_faces': [short(r) for r in by_placed[:top]], 'per_model': per_model},
        'placements': {'faces': distribution(row[2] for row in placement_rows), 'leaves': distribution(leaves),
                       'over_16_leaves': len(over),
                       'columns': ['pid', 'model', 'faces', 'leaves', 'chunk_x', 'chunk_y'],
                       'rows': placement_rows},
        'chunks': {'faces': distribution(r['faces'] for r in chunk_rows),
                   'faces_with_reach': distribution(r['faces_with_reach'] for r in chunk_rows),
                   'terrain_faces': distribution(r['terrain_faces'] for r in chunk_rows),
                   'top_by_faces': heavy_chunks[:top], 'per_chunk': chunk_rows},
        'views': views, 'disk': disk, 'memory': memory, 'streaming': streaming, 'build': build,
        'pain_points': pain,
    }
    # Without today's region maps the legacy fields are null (the schema keeps every field).
    out['legacy'] = legacy
    out['faces']['legacy_stored'] = out['faces']['legacy_over_chim_placed'] = None
    if legacy:
        out['faces']['legacy_stored'] = legacy['faces_stored']
        out['faces']['legacy_over_chim_placed'] = round(legacy['faces_stored'] / faces['placed'], 2) \
            if faces['placed'] else None
    return out


def dumps(stats):
    return json.dumps(stats, indent=1, sort_keys=True) + '\n'


def main(argv=None):
    from chim.validate import measure, validate
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('out', type=Path, help='builder output folder (holds chim/, chim-receipt.json)')
    ap.add_argument('--source', type=Path, help='source manifest (default OUT/chim-source.json if present)')
    ap.add_argument('--receipt', type=Path, help='builder receipt (default OUT/chim-receipt.json)')
    ap.add_argument('--legacy-maps', type=Path, help="folder with today's region maps of the same area")
    ap.add_argument('--legacy-regions', type=Path, help="today's region table of the same area")
    ap.add_argument('--camera', nargs=3, action='append', default=None, metavar=('NAME', 'X', 'Y'),
                    help='a view at this Morrowind position (repeatable; default: the area\'s benchmark cameras)')
    ap.add_argument('--json', type=Path, help='write here (default OUT/chim-stats.json)')
    a = ap.parse_args(argv)
    src = a.source or (a.out / 'chim-source.json')
    source = json.loads(src.read_text(encoding='utf-8')) if src.is_file() else None
    rec = a.receipt or (a.out / 'chim-receipt.json')
    receipt = json.loads(rec.read_text(encoding='utf-8')) if rec.is_file() else {}
    fails, world = validate(a.out, source)
    if fails:
        sys.stderr.write('CHIM world fails validation (%d); no stats written:\n  %s\n' % (len(fails), '\n  '.join(fails[:20])))
        return 1
    area_list = receipt.get('areas') or ([receipt['town']] if receipt.get('town') else [])
    cameras = [(n, float(x), float(y)) for n, x, y in a.camera] if a.camera is not None \
        else [(n, float(x), float(y)) for area in area_list for n, x, y in BENCHMARK_CAMERAS.get(area, [])]
    measured = measure(world, source, a.legacy_maps, a.legacy_regions, None, cameras)
    measured.get('walk', {}).pop('_replay', None)
    legacy = legacy_summary(a.legacy_maps, a.legacy_regions) if a.legacy_maps and a.legacy_regions else None
    stats = chim_stats(world, measured, receipt, area_list or None, legacy, cameras, source=source)
    target = a.json or (a.out / 'chim-stats.json')
    target.write_bytes(dumps(stats).encode('utf-8'))
    print('chim-stats: %s (%d models, %d placements, %d chunks)' % (target, len(world['models']),
                                                                     stats['counts']['placements'], len(world['chunks'])))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
