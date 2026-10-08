#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Measure how much geometry neighbouring sub-cell BSP29 maps duplicate.

Reads the user's own built maps. Every placed face (world model and brush
entities, moved by their origin and yaw) gets a world-space key, so faces that
several sub-cells carry can be counted once. Writes aggregate statistics and an
optional density image of face centroids with the configured cores drawn on
top. No asset geometry, texture or vertex data is exported.

Example:
  analyze_subcell_redundancy.py --maps build/id1/maps --prefix sn \
      --regions config/seyda-bounded-regions.json \
      --json seyda-redundancy.json --image seyda-cells.png
"""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import re
import struct
import sys

import numpy as np

LUMP_ENTITIES, LUMP_VERTEXES, LUMP_FACES = 0, 3, 7
LUMP_EDGES, LUMP_SURFEDGES, LUMP_MODELS = 12, 13, 14
FACE = np.dtype([('plane', '<u2'), ('side', '<i2'), ('firstedge', '<i4'), ('numedges', '<i2'),
                 ('texinfo', '<u2'), ('styles', 'u1', 4), ('lightofs', '<i4')])
MODEL = np.dtype([('mins', '<f4', 3), ('maxs', '<f4', 3), ('origin', '<f4', 3), ('headnode', '<i4', 4),
                  ('visleafs', '<i4'), ('firstface', '<i4'), ('numfaces', '<i4')])


def placed_faces(raw, quantum=0.5):
    """Yield (world-space face key, entity class, centroid xy) for every placed face."""
    if len(raw) < 124 or struct.unpack_from('<i', raw, 0)[0] != 29:
        raise ValueError('Not a BSP29 map')
    lumps = [struct.unpack_from('<ii', raw, 4 + 8 * i) for i in range(15)]
    lump = lambda i: raw[lumps[i][0]:lumps[i][0] + lumps[i][1]]
    verts = np.frombuffer(lump(LUMP_VERTEXES), '<f4').reshape(-1, 3).astype(np.float64)
    edges = np.frombuffer(lump(LUMP_EDGES), '<u2').reshape(-1, 2)
    surfedges = np.frombuffer(lump(LUMP_SURFEDGES), '<i4')
    faces = np.frombuffer(lump(LUMP_FACES), FACE)
    models = np.frombuffer(lump(LUMP_MODELS), MODEL)
    text = lump(LUMP_ENTITIES).decode('latin-1')
    placements = [(0, np.zeros(3), 0.0, 'world')]
    for block in re.findall(r'\{[^}]*\}', text):
        entity = dict(re.findall(r'"([^"]*)" "([^"]*)"', block))
        if not entity.get('model', '').startswith('*'):
            continue
        angles = entity.get('angles', '0 %s 0' % entity.get('angle', '0')).split()
        origin = np.array([float(v) for v in entity.get('origin', '0 0 0').split()])
        placements.append((int(entity['model'][1:]), origin, float(angles[1]), entity.get('classname', '?')))
    for index, origin, yaw, classname in placements:
        if index >= len(models):
            continue
        r = math.radians(yaw)
        rotation = np.array([[math.cos(r), -math.sin(r), 0], [math.sin(r), math.cos(r), 0], [0, 0, 1]])
        model = models[index]
        for face in faces[model['firstface']:model['firstface'] + model['numfaces']]:
            ids = [edges[s][0] if s >= 0 else edges[-s][1]
                   for s in surfedges[face['firstedge']:face['firstedge'] + face['numedges']]]
            points = verts[ids] @ rotation.T + origin
            key = tuple(sorted(map(tuple, np.round(points / quantum) * quantum)))
            yield key, classname, points[:, :2].mean(axis=0)


def analyze(paths):
    copies, centroids, per_map = Counter(), {}, {}
    for path in paths:
        raw = Path(path).read_bytes()
        keys, classes = set(), Counter()
        for key, classname, xy in placed_faces(raw):
            keys.add(key); classes[classname] += 1
            centroids.setdefault(key, xy)
        copies.update(keys)
        per_map[Path(path).stem] = {'bytes': len(raw), 'faces': sum(classes.values()),
                                    'distinct_faces': len(keys), 'faces_by_class': dict(classes), '_keys': keys}
    for row in per_map.values():
        keys = row.pop('_keys')
        row['shared_with_other_maps_percent'] = round(100 * sum(copies[k] > 1 for k in keys) / max(1, len(keys)), 1)
        row['median_copies_per_face'] = float(np.median([copies[k] for k in keys])) if keys else 0.0
    total = sum(copies.values())
    summary = {'maps': len(per_map), 'bytes': sum(r['bytes'] for r in per_map.values()),
               'distinct_faces_union': len(copies), 'faces_summed_over_maps': total,
               'redundancy_factor': round(total / max(1, len(copies)), 2),
               'median_copies_per_face': float(np.median(list(copies.values()))) if copies else 0.0}
    return summary, per_map, np.array(list(centroids.values())) if centroids else np.zeros((0, 2))


def density_image(points, regions, output, cell=32, scale=4):
    from PIL import Image, ImageDraw
    low, high = points.min(axis=0) - 2 * cell, points.max(axis=0) + 2 * cell
    width, height = int((high[0] - low[0]) // cell) + 1, int((high[1] - low[1]) // cell) + 1
    grid = np.zeros((height, width))
    for x, y in points:
        grid[int((high[1] - y) // cell), int((x - low[0]) // cell)] += 1
    level = np.log1p(grid) / max(1e-9, np.log1p(grid).max())
    rgb = np.stack([np.clip(level * 3, 0, 1), np.clip(level * 3 - 1, 0, 1), np.clip(level * 3 - 2, 0, 1)], -1)
    image = Image.fromarray((rgb * 255).astype(np.uint8)).resize((width * scale, height * scale), Image.NEAREST)
    draw = ImageDraw.Draw(image)
    for region in regions:
        (x0, y0), (x1, y1) = region['core']
        box = [(x0 - low[0]) / cell * scale, (high[1] - y1) / cell * scale,
               (x1 - low[0]) / cell * scale, (high[1] - y0) / cell * scale]
        draw.rectangle(box, outline=(80, 200, 255))
        draw.text((box[0] + 2, box[1] + 2), str(region.get('name', '')), fill=(80, 200, 255))
    image.save(output)
    return {'image': str(output), 'cell_units': cell, 'peak_faces_per_cell': int(grid.max())}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--maps', type=Path, required=True, help='Directory with the built .bsp maps')
    parser.add_argument('--prefix', required=True, help='Sub-cell name prefix, e.g. sn or bm')
    parser.add_argument('--regions', type=Path, help='Optional region JSON with core rectangles to draw')
    parser.add_argument('--json', type=Path, help='Aggregate statistics output')
    parser.add_argument('--image', type=Path, help='Density image output (PNG); keep real-map images private')
    args = parser.parse_args(argv)
    paths = sorted(p for p in args.maps.glob(args.prefix + '*.bsp')
                   if re.fullmatch(re.escape(args.prefix) + r'\d+', p.stem))
    if not paths:
        parser.error('no %s<number>.bsp maps found in %s' % (args.prefix, args.maps))
    summary, per_map, points = analyze(paths)
    if args.image:
        regions = json.loads(args.regions.read_text())['regions'] if args.regions else []
        summary['density'] = density_image(points, regions, args.image)
    if args.json:
        args.json.write_text(json.dumps({'summary': summary, 'maps': per_map}, indent=2) + '\n')
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
