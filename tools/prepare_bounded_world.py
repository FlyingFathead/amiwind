#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Compile a bounded LAND world and retain intersecting original scenery.

Offline candidate builder: it does not update region tables or install images.
The input MAP must be the generated prepare_quake LAND map in the same coordinate
system as both BSPs. Its g<number> triangle brushes and final BSP miptex pixels
are preserved. Unknown world geometry is rejected rather than silently lost.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

from prepare_quake import box, wad
from player_hull import lumps, rebuild_world_hull
from replace_bsp_world import replace_world, texture_blobs, verify_collision, rows
from compact_bsp import compact
from prepare_seyda_regions import select
from deduplicate_bsp import deduplicate
from check_world_map_heap import compile_target_sizes, estimate_bsp

MIB = 1024 * 1024


def world_contents(data, point, hull):
    node_id = data[14][0][9+hull]
    index = 5 if hull == 0 else 9
    visited = set()
    while node_id >= 0 and (index == 5 or node_id < 65520):
        if node_id in visited or node_id >= len(data[index]):
            raise ValueError('Invalid world collision tree')
        visited.add(node_id)
        node = data[index][node_id]
        plane = data[1][node[0]]
        distance = sum(point[i]*plane[i] for i in range(3))-plane[3]
        node_id = node[1 if distance >= 0 else 2]
    return (data[10][-node_id-1][0] if hull == 0 else
            node_id-65536 if node_id >= 65520 else node_id)


def audit_world_samples(source_raw, candidate_raw, coverage):
    """A deterministic regression sample, not a proof for every world point."""
    a, b = rows(lumps(source_raw)), rows(lumps(candidate_raw))
    low, high = checked_bounds(coverage)
    count = 0
    mismatches = []
    for hull in (0, 1):
        for ix in range(17):
            for iy in range(17):
                # Stay just inside the required rectangle, away from enclosure.
                x = low[0]+(high[0]-low[0])*(0.0001+ix*0.9998/16)
                y = low[1]+(high[1]-low[1])*(0.0001+iy*0.9998/16)
                for z in (-480, -250, -32, -1, 1, 16, 32, 64, 96, 128, 192, 256, 384, 512):
                    point = (x, y, z)
                    old, new = world_contents(a, point, hull), world_contents(b, point, hull)
                    count += 1
                    if old != new and len(mismatches) < 20:
                        mismatches.append({'hull': hull, 'point': point, 'source': old, 'candidate': new})
    if mismatches:
        raise ValueError('World collision sample mismatch: '+json.dumps(mismatches))
    return {'samples': count, 'mismatches': 0, 'hulls': [0, 1],
            'scope': 'finite deterministic contents samples; not exhaustive terrain or playtest proof'}


def checked_bounds(bounds):
    if len(bounds) != 2 or any(len(row) != 2 for row in bounds):
        raise ValueError('Bounds require two XY corners')
    result = [[float(v) for v in row] for row in bounds]
    if not all(math.isfinite(v) for row in result for v in row):
        raise ValueError('Bounds must be finite')
    if any(result[0][i] >= result[1][i] for i in range(2)):
        raise ValueError('Bounds must have positive area')
    return result


def terrain_brushes(text):
    """Extract original complete triangle prisms, rejecting unknown materials."""
    ground = []
    excluded = {'clip': 0, 'enclosure_or_water': 0}
    for block in re.findall(r'\{[^{}]*\}', text):
        names = re.findall(r'(?:\([^)]*\)\s*){3}(\S+)', block)
        if not names:
            continue
        if any(name == 'clip' for name in names):
            # Approximated architecture boxes must not enter the terrain world.
            # Architecture collision is retained through original inline models.
            excluded['clip'] += 1
            continue
        if not all(re.fullmatch(r'g\d+', name) for name in names):
            if set(names) <= {'sky', 'stone', '*water'}:
                excluded['enclosure_or_water'] += 1
                continue
            raise ValueError('Unsupported non-LAND brush materials: '+repr(names))
        points = [tuple(map(float, p.split()))
                  for p in re.findall(r'\(\s*([^)]*)\)', block)]
        if any(len(p) != 3 or not all(math.isfinite(v) for v in p) for p in points):
            raise ValueError('Invalid LAND brush plane coordinates')
        if len(names) != 5 or len(points) != 15:
            raise ValueError('Expected an original five-plane LAND triangle prism')
        ground.append((block, points, set(names)))
    if not ground:
        raise ValueError('No generated LAND triangle brushes found')
    return ground, excluded


def prepare_inputs(source_text, texture_raw, coverage):
    coverage = checked_bounds(coverage)
    ground, excluded = terrain_brushes(source_text)
    low, high = coverage
    selected = [(block, points, names) for block, points, names in ground
                if all(max(p[i] for p in points) >= low[i] and
                       min(p[i] for p in points) <= high[i] for i in range(2))]
    if not selected:
        raise ValueError('Coverage does not intersect any LAND triangles')
    original_low = [min(p[i] for _, points, _ in ground for p in points) for i in range(2)]
    original_high = [max(p[i] for _, points, _ in ground for p in points) for i in range(2)]
    sky_top = max(512, max(p[2] for _, points, _ in ground for p in points)+256)
    sea_extent = certified_sea_extent(source_text, sky_top)
    permitted = sea_extent if sea_extent is not None else [original_low, original_high]
    if any(low[i] < permitted[0][i] or high[i] > permitted[1][i] for i in range(2)):
        raise ValueError('Required coverage extends beyond source LAND or certified sea extent')
    selected_low = [min(low[i], min(p[i] for _, points, _ in selected for p in points))-32 for i in range(2)]
    selected_high = [max(high[i], max(p[i] for _, points, _ in selected for p in points))+32 for i in range(2)]
    xmin, ymin = selected_low
    xmax, ymax = selected_high
    brushes = [block for block, _, _ in selected]
    brushes += [box([xmin, ymin, -500], [xmax, ymax, 0], '*water'),
                box([xmin-32, ymin-32, -544], [xmax+32, ymax+32, -512], 'stone'),
                box([xmin-32, ymin-32, sky_top], [xmax+32, ymax+32, sky_top+32], 'sky'),
                box([xmin-32, ymin-32, -512], [xmin, ymax+32, sky_top], 'sky'),
                box([xmax, ymin-32, -512], [xmax+32, ymax+32, sky_top], 'sky'),
                box([xmin, ymin-32, -512], [xmax, ymin, sky_top], 'sky'),
                box([xmin, ymax, -512], [xmax, ymax+32, sky_top], 'sky')]
    textures = {}
    for blob in texture_blobs(lumps(texture_raw)[2]):
        if blob is None:
            continue
        name = blob[:16].split(b'\0', 1)[0].decode('ascii')
        if name in textures and textures[name] != blob:
            raise ValueError('Conflicting texture pixels for '+name)
        textures[name] = blob
    names = set().union(*(names for _, _, names in selected)) | {'*water', 'stone', 'sky'}
    missing = names - textures.keys()
    if missing:
        raise ValueError('Final BSP lacks required textures: '+repr(sorted(missing)))
    text = '{\n"classname" "worldspawn"\n"wad" "terrain.wad"\n'
    text += '"message" "Bounded LAND candidate"\n'+'\n'.join(brushes)+'\n}\n'
    text += ('{\n"classname" "info_player_start"\n"origin" "%g %g %g"\n}\n' %
             ((low[0]+high[0])/2, (low[1]+high[1])/2, sky_top-128))
    report = {'coverage': coverage, 'source_land_extent': [original_low, original_high],
              'certified_source_sea_extent': sea_extent,
              'enclosure': [selected_low, selected_high], 'sky_top': sky_top,
              'original_ground_brushes': len(ground), 'selected_ground_brushes': len(selected),
              'excluded_brushes': excluded, 'whole_intersecting_triangles_preserved': True,
              'texture_names': sorted(names)}
    return text, wad([(name, 68, textures[name]) for name in sorted(names)]), report


def certified_sea_extent(text, sky_top):
    """Recognize the exact generated water/bottom/sky shell, never infer ocean."""
    blocks = []
    water = []
    for block in re.findall(r'\{[^{}]*\}', text):
        names = re.findall(r'(?:\([^)]*\)\s*){3}(\S+)', block)
        if not names or not set(names) <= {'sky', 'stone', '*water'}:
            continue
        blocks.append(block)
        if set(names) == {'*water'}:
            water.append(block)
    if not blocks:
        return None
    if len(water) != 1:
        raise ValueError('Expected one generated water enclosure')
    points = [tuple(map(float, p.split())) for p in re.findall(r'\(\s*([^)]*)\)', water[0])]
    if any(len(p) != 3 or not all(math.isfinite(v) for v in p) for p in points):
        raise ValueError('Invalid source water enclosure')
    low = [min(p[i] for p in points) for i in range(3)]
    high = [max(p[i] for p in points) for i in range(3)]
    xmin, ymin, _ = low
    xmax, ymax, _ = high
    expected = [box([xmin, ymin, -500], [xmax, ymax, 0], '*water'),
                box([xmin-32, ymin-32, -544], [xmax+32, ymax+32, -512], 'stone'),
                box([xmin-32, ymin-32, sky_top], [xmax+32, ymax+32, sky_top+32], 'sky'),
                box([xmin-32, ymin-32, -512], [xmin, ymax+32, sky_top], 'sky'),
                box([xmax, ymin-32, -512], [xmax+32, ymax+32, sky_top], 'sky'),
                box([xmin, ymin-32, -512], [xmax, ymin, sky_top], 'sky'),
                box([xmin, ymax, -512], [xmax, ymax+32, sky_top], 'sky')]
    canonical = lambda s: ' '.join(s.split())
    if sorted(map(canonical, blocks)) != sorted(map(canonical, expected)):
        raise ValueError('Source water/sky shell does not match generated enclosure contract')
    # Keep required points safely inside the original standing collision wall.
    return [[xmin+32, ymin+32], [xmax-32, ymax-32]]


def build_candidate(source_map, texture_bsp, source_bsp, palette, coverage, out_dir,
                    ericw_bin, target_sizes, *, core=None, threads=1):
    """Return report; estimate when supplied ABI sizes, otherwise require the final build gate.

    Source BSP should be the full town when evaluating different cores, so a
    previously selected derivative cannot silently omit required scenery.
    The caller owns core coverage, adjacency, runtime region count and acceptance.
    """
    if threads < 1:
        raise ValueError('Compiler thread count must be positive')
    paths = {name: Path(value).resolve() for name, value in
             [('source_map', source_map), ('texture_bsp', texture_bsp),
              ('source_bsp', source_bsp), ('palette', palette)]}
    raw = {name: path.read_bytes() for name, path in paths.items()}
    if len(raw['palette']) != 768:
        raise ValueError('Palette must contain exactly 768 bytes')
    coverage = checked_bounds(coverage)
    if core is not None:
        core = checked_bounds(core)
        if any(core[0][i] < coverage[0][i] or core[1][i] > coverage[1][i] for i in range(2)):
            raise ValueError('Core must be contained by required coverage')
    text, wad_raw, provenance = prepare_inputs(raw['source_map'].decode('utf-8'), raw['texture_bsp'], coverage)
    out = Path(out_dir).resolve()
    if out.exists():
        raise ValueError('Candidate output directory must be new: '+str(out))
    out.mkdir(parents=True)
    (out/'base.map').write_text(text, encoding='ascii', newline='\n')
    (out/'terrain.wad').write_bytes(wad_raw)
    binary = Path(ericw_bin)
    def executable(name):
        path = binary/name
        return path if path.is_file() else binary/(name+'.exe')
    for name, args in [('qbsp', ['-nopercent', 'base.map']),
                       ('vis', ['-fast', '-threads', str(threads), 'base.bsp']),
                       ('light', ['-minlight', '100', '-threads', str(threads), 'base.bsp'])]:
        with (out/(name+'.log')).open('w', encoding='utf-8') as log:
            subprocess.run([str(executable(name)), *args], cwd=out,
                           stdout=log, stderr=subprocess.STDOUT, check=True)
    rebuild_world_hull(out/'base.bsp', out/'base.map', executable('qbsp'), discard_stock_hulls=True)
    composed, composition = replace_world(raw['source_bsp'], (out/'base.bsp').read_bytes(),
                                          raw['palette'], raw['palette'])
    selected, selection = compact(composed, select(composed, coverage), visual_bounds=coverage)
    candidate, deduplication = deduplicate(selected)
    source_lumps, candidate_lumps = lumps(composed), lumps(candidate)
    parsed = rows(source_lumps), rows(candidate_lumps)
    for new_id, old_id in enumerate(selection['retained_models']):
        for hull in (0, 1, 2, 3):
            verify_collision(source_lumps, candidate_lumps, old_id, new_id, hull, parsed)
    terrain_samples = audit_world_samples(raw['source_bsp'], candidate, coverage)
    (out/'candidate.bsp').write_bytes(candidate)
    estimate = None
    if target_sizes is not None:
        estimate = estimate_bsp(out/'candidate.bsp', target_sizes)
        estimate['reserve_bytes'] = 5*MIB
        estimate['hunk_bytes'] = 11*MIB
        estimate['clearance_bytes'] = 6*MIB-estimate['peak_loader_bytes']
        estimate['gate'] = 'pass' if estimate['clearance_bytes'] >= 0 else 'fail'
    report = {'status': 'offline candidate; target lifecycle and coverage acceptance pending',
              'inputs': {name: {'path': str(paths[name]), 'sha256': hashlib.sha256(value).hexdigest()}
                         for name, value in raw.items()},
              'candidate_sha256': hashlib.sha256(candidate).hexdigest(),
              'candidate_path': str(out/'candidate.bsp'), 'core': core,
              'coverage_provenance': provenance, 'composition': composition,
              'selection': selection, 'deduplication': deduplication,
              'retained_hull_trees_verified': len(selection['retained_models'])*4,
              'world_collision_samples': terrain_samples,
              'heap_estimate': estimate,
              'limits': ['Source BSP must include all scenery needed by coverage.',
                         'Source MAP and BSP coordinate/palette provenance is a caller contract.',
                         'Static allocator estimate is not target runtime clearance.',
                         'No runtime region tables or HDFs were changed.']}
    (out/'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source-map', 'texture-bsp', 'source-bsp', 'palette', 'out', 'ericw-bin', 'sdk'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--coverage', type=float, nargs=4, required=True, metavar=('X0', 'Y0', 'X1', 'Y1'))
    parser.add_argument('--core', type=float, nargs=4)
    parser.add_argument('--threads', type=int, default=1)
    args = parser.parse_args()
    sizes, _ = compile_target_sizes(args.sdk)
    report = build_candidate(args.source_map, args.texture_bsp, args.source_bsp, args.palette,
                             [args.coverage[:2], args.coverage[2:]], args.out, args.ericw_bin,
                             sizes, core=[args.core[:2], args.core[2:]] if args.core else None,
                             threads=args.threads)
    print(json.dumps(report['heap_estimate'], indent=2))
    return 0 if report['heap_estimate']['gate'] == 'pass' else 2


if __name__ == '__main__':
    raise SystemExit(main())
