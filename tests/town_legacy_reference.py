# SPDX-License-Identifier: GPL-3.0-only
"""Frozen Balmora converter functions from v0.0.31-dev5 (before generic towns).

Verbatim copies of tools/balmora_regions.py and tools/prepare_balmora.py as
they stood before the town converter became generic. test_town_import.py runs
them next to the generic code on synthetic inputs to prove Balmora's
config-derived outputs are byte-identical. Never edit these bodies.
"""
import math
import shutil
import struct

from player_hull import lumps, pack_lumps
from prepare_area import entity
from prepare_quake import box, brush


def regions(settings):
    size = settings['core_size']
    low, high = settings['bounds']
    if size <= 0 or any((high[i] - low[i]) % size for i in range(2)):
        raise ValueError('Sub-cell bounds must contain complete cores')
    if settings['overlap'] < math.sqrt(2) * settings['draw_distance'] + settings['hysteresis'] + 32:
        raise ValueError('Overlap must cover visibility, hysteresis and collision margin')
    out = []
    for y in range(low[1], high[1], size):
        for x in range(low[0], high[0], size):
            name = f'bm{len(out):03d}'
            core = settings.get('region_core_overrides', {}).get(name, [[x, y], [x + size, y + size]])
            margin = settings['overlap']
            coverage = [[max(low[i], core[0][i] - margin) for i in range(2)],
                        [min(high[i], core[1][i] + margin) for i in range(2)]]
            out.append({'name': f'bm{len(out):03d}', 'core': core, 'coverage': coverage})
    if len(out) > 64:
        raise ValueError('Region directory exceeds native capacity')
    validate_partition(out, settings)
    return out


def validate_partition(entries, settings):
    """Exact rectangular tiling: no holes, overlap, invalid names or hidden slots."""
    low, high = settings['bounds']
    names = {e['name'] for e in entries}
    if set(settings.get('region_core_overrides', {})) - names:
        raise ValueError('Unknown region override')
    area = 0
    for i, entry in enumerate(entries):
        a, b = entry['core']
        if any(type(v) is not int for v in (*a, *b)) or any(
                not low[k] <= a[k] < b[k] <= high[k] for k in range(2)):
            raise ValueError('Invalid region core bounds')
        if any((v-low[k]) % settings['terrain_step'] for point in (a,b) for k,v in enumerate(point)):
            raise ValueError('Region core must align with terrain grid')
        area += (b[0]-a[0])*(b[1]-a[1])
        for other in entries[:i]:
            c,d=other['core']
            if all(max(a[k],c[k]) < min(b[k],d[k]) for k in range(2)):
                raise ValueError('Region cores overlap')
    if area != (high[0]-low[0])*(high[1]-low[1]):
        raise ValueError('Region core coverage has a hole')


def owner(point, entries, current=None, hysteresis=0):
    if not all(math.isfinite(v) for v in point[:2]):
        raise ValueError('Nonfinite region position')
    if current is not None:
        a, b = entries[current]['core']
        if all(a[i] - hysteresis <= point[i] <= b[i] + hysteresis for i in range(2)):
            return current
    for i, entry in enumerate(entries):
        a, b = entry['core']
        if all(a[k] <= point[k] < b[k] for k in range(2)):
            return i
    # The outermost east/north edge belongs to its final core.
    for i, entry in enumerate(entries):
        a, b = entry['core']
        if all(a[k] <= point[k] <= b[k] for k in range(2)):
            return i
    return None


def terrain_sample(grids, settings, x, y):
    wx, wy = [settings['centre'][i] + v / settings['scale'] for i, v in enumerate((x, y))]
    cx, cy = math.floor(wx / 8192), math.floor(wy / 8192)
    if (cx, cy) not in grids:
        # The last vertex is also the previous source cell's east/north edge.
        if (cx - 1, cy) in grids and wx == cx * 8192: cx -= 1
        if (cx, cy - 1) in grids and wy == cy * 8192: cy -= 1
        if (cx, cy) not in grids and (cx - 1, cy - 1) in grids and wx == cx * 8192 and wy == cy * 8192:
            cx -= 1; cy -= 1
    grid = grids[cx, cy]
    ix, iy = (wx - cx * 8192) / 128, (wy - cy * 8192) / 128
    return grid, cx, cy, ix, iy


def terrain_material(grids, settings, x, y):
    grid, cx, cy, ix, iy = terrain_sample(grids, settings, x, y)
    tx, ty = min(15, math.floor(ix/4)), min(15, math.floor(iy/4))
    material = grid['materials'][ty][tx]
    for repair in settings.get('terrain_material_repairs', []):
        if repair['cell'] == [cx, cy] and repair['tile'] == [tx, ty]:
            if material != repair['source_material']:
                raise ValueError('Terrain repair no longer matches its source tile')
            material = repair['material']
    return material


def terrain_at(grids, settings, x, y):
    grid, cx, cy, ix, iy = terrain_sample(grids, settings, x, y)
    return grid['heights'][round(iy)][round(ix)] * settings['scale'], terrain_material(grids, settings, x, y)


def terrain_map(entry, grids, settings, spawn, timings):
    low, high = entry['coverage']; step = settings['terrain_step']; brushes = []
    for y in range(low[1], high[1], step):
        for x in range(low[0], high[0], step):
            corners = []
            # A terrain tile owns its area, not the northern neighbour sampled
            # at the final height corner. Sample material inside the quad.
            material = terrain_material(grids, settings, x+step/2, y+step/2)
            for dx, dy in ((0, 0), (step, 0), (step, step), (0, step)):
                z, _ = terrain_at(grids, settings, x + dx, y + dy)
                corners.append([x + dx, y + dy, z])
            for ids in ((0, 1, 2), (0, 2, 3)):
                tri = [corners[i] for i in ids]
                pts = tri + [[p[0], p[1], -1024] for p in tri]
                brushes.append(brush(pts, [(0, 1, 2), (3, 4, 5), (0, 1, 4), (1, 2, 5), (2, 0, 3)], f'g{material}'))
    x0, y0 = low; x1, y1 = high
    brushes += [box([x0, y0, -1000], [x1, y1, 0], '*water'),
                box([x0 - 32, y0 - 32, -1056], [x1 + 32, y1 + 32, -1024], 'stone'),
                box([x0 - 32, y0 - 32, 2048], [x1 + 32, y1 + 32, 2080], 'sky'),
                box([x0 - 32, y0 - 32, -1024], [x0, y1 + 32, 2048], 'sky'),
                box([x1, y0 - 32, -1024], [x1 + 32, y1 + 32, 2048], 'sky'),
                box([x0, y0 - 32, -1024], [x1, y0, 2048], 'sky'),
                box([x0, y1, -1024], [x1, y1 + 32, 2048], 'sky')]
    return ('{\n"classname" "worldspawn"\n"wad" "terrain.wad"\n"message" "Balmora"\n'
            + timings + '\n' + '\n'.join(brushes) + '\n}\n'
            + entity({'classname': 'info_player_start', 'origin': ' '.join(map(str, spawn)), 'angle': 90}) + '\n')


def travel_point(kinds, identifier, settings):
    candidates = []
    for tag, raw in kinds['NPC_'][identifier]:
        if tag != 'DODT': continue
        values = struct.unpack('<6f', raw)
        point = [(values[i] - (settings['centre'][i] if i < 2 else 0)) * settings['scale'] for i in range(3)]
        if all(settings['bounds'][0][i] <= point[i] <= settings['bounds'][1][i] for i in range(2)):
            point[2] += 16.875
            candidates.append((point, (90 - math.degrees(values[5])) % 360))
    if len(candidates) != 1: raise ValueError('Travel destination must resolve uniquely: ' + identifier)
    return candidates[0]


def publish(scene, out, settings, entries, references, index, npc_entities, arrival, yaw, returning, return_yaw):
    # Every region seeds all stable actor IDs. The runtime restores their latest
    # state and deactivates residents outside this region's coverage.
    for entry in entries:
        payload = lumps((out / entry['name'] / 'scene.bsp').read_bytes())
        text = payload[0].decode('cp1252').rstrip('\0\n')
        payload[0] = (text + '\n' + '\n'.join(npc_entities) + '\n\0').encode('cp1252')
        (scene / 'id1/maps' / (entry['name'] + '.bsp')).write_bytes(pack_lumps(payload))
    shutil.copyfile(scene / 'id1/maps' / (entries[owner(arrival, entries)]['name'] + '.bsp'), scene / 'id1/maps/balmora.bsp')
    rows = ['AWBR1 ' + ' '.join(map(str, [len(entries), settings['hysteresis'], settings['draw_distance'], *arrival, yaw, *returning, return_yaw]))]
    for entry in entries:
        rows.append(entry['name'] + ' ' + ' '.join(map(str, [*entry['core'][0], *entry['core'][1], *entry['coverage'][0], *entry['coverage'][1]])))
    (scene / 'id1/balmora-regions.txt').write_text('\n'.join(rows) + '\n')
    converted = {r['number']: r for r in index['references']}
    doors = ['AWD3']
    for ref in references:
        if ref['type'] != 'DOOR' or not ref.get('destination') or ref['number'] not in converted: continue
        bounds = [[(v - (settings['centre'][i] if i < 2 else 0)) * settings['scale'] for i, v in enumerate(p)] for p in converted[ref['number']]['bounds']]
        label = ref.get('destination_cell') or 'Exterior world'
        if any(c in label for c in '\r\n'): raise ValueError('Invalid door label')
        doors.append('balmora - ' + str(ref['number']) + ' ' + ' '.join(map(str, [*bounds[0], *bounds[1], 0, 0, 0, 0])) + ' ' + label)
    (scene / 'id1/scene-doors-balmora.txt').write_text('\n'.join(doors) + '\n', encoding='cp1252')
