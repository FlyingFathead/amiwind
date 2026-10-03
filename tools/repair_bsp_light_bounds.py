#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Rebake only proven BSP light-lump overruns from retained source lighting.

Geometry, entities, valid face records and every existing light byte are kept.
An affected face must have one light style, one inline entity, and matching
binary32/wide-intermediate grids. This does not repair other lighting issues.
No compiler, engine, external helper or game executable is run.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

import numpy as np

from check_geometry_render_inputs import BSP, project, project_wide, require
from compact_bsp import entities
from interior_lighting import bake_surface
from player_hull import lumps, pack_lumps


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def face_grid(bsp, index, projection):
    face = bsp.rows[7][index]
    vectors = np.asarray(bsp.rows[6][face[4]][:8]).reshape(2, 4)
    points = np.asarray([bsp.rows[3][bsp.rows[12][abs(edge)][0 if edge >= 0 else 1]]
                         for (edge,) in bsp.rows[13][face[2]:face[2]+face[3]]])
    uv = [[projection(point, vec) for vec in vectors] for point in points]
    low = tuple(math.floor(min(999999., *(v[a] for v in uv))/16)*16 for a in (0, 1))
    extent = tuple(max(16, math.ceil(max(-99999., *(v[a] for v in uv))/16)*16-low[a])
                   for a in (0, 1))
    require(max(extent) <= 256, 'Repair surface exceeds the runtime lightmap budget')
    return points, vectors, low, tuple((v >> 4)+1 for v in extent)


def repair_light_bounds(raw, lighting):
    bsp = BSP(raw)
    data = lumps(raw)
    placements = entities(bsp.parts[0])
    repairs = []
    for index, face in enumerate(bsp.rows[7]):
        if face[-1] < 0:
            continue
        grids = [face_grid(bsp, index, policy) for policy in (project, project_wide)]
        styles = next((i for i, style in enumerate(face[5:9]) if style == 255), 4)
        lengths = [grid[3][0]*grid[3][1]*styles for grid in grids]
        if face[-1]+max(lengths) <= len(bsp.parts[8]):
            continue
        require(face[5:9] == (0, 255, 255, 255), 'Repair requires one default light style')
        require(grids[0][2:] == grids[1][2:],
                f'Cannot repair face {index}: arithmetic policies require different grids')
        models = [i for i, model in enumerate(bsp.rows[14])
                  if model[14] <= index < model[14]+model[15]]
        require(len(models) == 1 and models[0] > 0, 'Repair requires unique inline face ownership')
        owners = [entity for entity in placements if entity.get('model') == '*'+str(models[0])]
        require(len(owners) == 1 and owners[0].get('classname') == 'func_wall',
                'Repair requires exactly one func_wall placement')
        owner = owners[0]
        origin = np.asarray([float(v) for v in owner.get('origin', '0 0 0').split()])
        angles = [float(v) for v in owner.get('angles', '0 0 0').split()]
        require(origin.shape == (3,) and len(angles) == 3 and angles[0] == angles[2] == 0,
                'Unsupported inline placement transform')
        require(np.all(np.isfinite(origin)) and all(math.isfinite(v) for v in angles),
                'Non-finite inline placement transform')
        angle = math.radians(angles[1])
        rotation = np.array([[math.cos(angle), -math.sin(angle), 0],
                             [math.sin(angle), math.cos(angle), 0], [0, 0, 1]])
        points, vectors, low, size = grids[0]
        samples = bake_surface(points, vectors[:, :3].T, vectors[:, 3], rotation,
                               origin, lighting, sample_grid=(low, size))
        require(len(samples) == lengths[0], 'Rebake returned an unexpected sample count')
        offset = len(data[8])
        data[8] += samples
        struct.pack_into('<i', data[7], index*20+16, offset)
        repairs.append({'face': index, 'model': models[0], 'reference': owner.get('aw_ref'),
                        'old_offset': face[-1], 'new_offset': offset,
                        'old_available_bytes': len(bsp.parts[8])-face[-1],
                        'sample_dimensions': size, 'texture_mins': low,
                        'sample_bytes': len(samples), 'sample_sha256': sha(samples),
                        'arithmetic_policies': 'binary32 and wide-intermediate grids agree'})
    require(repairs, 'No out-of-lump lightmap to repair')
    result = pack_lumps(data)
    checked = BSP(result)
    repaired_indices = {row['face'] for row in repairs}
    for index in range(15):
        if index not in (7, 8):
            require(checked.parts[index] == bsp.parts[index], f'Repair changed lump {index}')
    require(checked.parts[8].startswith(bsp.parts[8]), 'Repair changed original light bytes')
    for index, (before, after) in enumerate(zip(bsp.rows[7], checked.rows[7])):
        require(before[:-1] == after[:-1], 'Repair changed face geometry/style metadata')
        if index not in repaired_indices:
            require(before == after, 'Repair changed an unaffected face record')
        for wide in (False, True):
            rendered = checked.face_inputs(index, wide)
            if index not in repaired_indices:
                require(bsp.face_inputs(index, wide) == rendered, 'Repair changed a valid face input')
    return result, {'status': 'repaired and all faces independently checked under both policies',
                    'input_sha256': sha(raw), 'output_sha256': sha(result),
                    'input_bytes': len(raw), 'output_bytes': len(result),
                    'faces_verified': len(bsp.rows[7]), 'repairs': repairs,
                    'preserved': 'all other lumps, valid faces, and original light bytes',
                    'scope': 'confirmed lump overruns only; other precision differences unchanged'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--lighting-index', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    raw = args.source.read_bytes()
    index_bytes = args.lighting_index.read_bytes()
    result, report = repair_light_bounds(raw, json.loads(index_bytes)['lighting'])
    report.update(source=str(args.source.resolve()), output=str(args.output.resolve()),
                  lighting_index=str(args.lighting_index.resolve()),
                  lighting_index_sha256=sha(index_bytes),
                  tool_sha256=sha(Path(__file__).read_bytes()))
    args.output.write_bytes(result)
    args.report.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
