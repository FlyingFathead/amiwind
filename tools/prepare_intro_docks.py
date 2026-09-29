#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Derive a conservative intro-only exterior from an owned compiled BSP29.

Keep the route, nearby houses and port silhouette. Retain terrain collision and
all BSP indices; remove distant scenery entities and distant world-face leaf
references. The full Seyda Neen BSP is never overwritten. This first variant
reduces submitted geometry, not the resident BSP payload.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import struct
from player_hull import lumps, pack_lumps

# Local quarter-scale coordinates; margin around the ship-to-office route.
BOUNDS = (-240.0, -1100.0, 1120.0, 620.0)


def derive(raw, bounds=BOUNDS):
    if len(bounds) != 4 or not all(math.isfinite(v) for v in bounds):
        raise ValueError('Expected finite XY bounds')
    xmin, ymin, xmax, ymax = bounds
    if xmin >= xmax or ymin >= ymax:
        raise ValueError('Empty dock bounds')
    data = lumps(raw)
    entities = re.findall(r'\{[^{}]*\}', data[0].decode('ascii').rstrip('\0'))
    models = list(struct.iter_unpack('<9f7i', data[14]))
    kept = []
    counts = {'scenery_removed': 0, 'actors_removed': 0, 'world_faces_hidden': 0}
    def intersects(low, high):
        return low[0] <= xmax and high[0] >= xmin and low[1] <= ymax and high[1] >= ymin
    for block in entities:
        fields = dict(re.findall(r'"([^"\n]*)"\s+"([^"\n]*)"', block))
        kind = fields.get('classname', '')
        origin = [float(v) for v in fields.get('origin', '0 0 0').split()]
        if len(origin) != 3:
            raise ValueError('Bad entity origin')
        low = [v-96 for v in origin]; high = [v+96 for v in origin]
        model = fields.get('model', '')
        if model.startswith('*'):
            m = models[int(model[1:])]
            # Radius conservatively covers rotated brush bounds.
            radius = math.sqrt(sum(max(abs(m[i]), abs(m[i+3]))**2 for i in range(3)))
            low = [v-radius for v in origin]; high = [v+radius for v in origin]
        if kind in ('func_wall', 'aw_static', 'aw_npc') and not intersects(low, high):
            counts['actors_removed' if kind == 'aw_npc' else 'scenery_removed'] += 1
        else:
            kept.append(block)
    data[0] = ('\n'.join(kept)+'\n\0').encode('ascii')
    vertices = list(struct.iter_unpack('<3f', data[3]))
    edges = list(struct.iter_unpack('<HH', data[12]))
    surfedges = [v[0] for v in struct.iter_unpack('<i', data[13])]
    faces = list(struct.iter_unpack('<Hhihh4Bi', data[7]))
    start, count = models[0][14:16]
    hidden = set()
    for index in range(start, start+count):
        f = faces[index]; points = []
        for se in surfedges[f[2]:f[2]+f[3]]:
            points.append(vertices[edges[abs(se)][0 if se >= 0 else 1]])
        if points and not intersects([min(p[i] for p in points) for i in range(3)],
                                     [max(p[i] for p in points) for i in range(3)]):
            hidden.add(index)
    marks = [m[0] for m in struct.iter_unpack('<H', data[11])]
    newmarks = bytearray(); leaves = bytearray(data[10])
    for offset in range(0, len(leaves), 28):
        first, count = struct.unpack_from('<HH', leaves, offset+20)
        selected = [f for f in marks[first:first+count] if f not in hidden]
        struct.pack_into('<HH', leaves, offset+20, len(newmarks)//2, len(selected))
        for f in selected: newmarks.extend(struct.pack('<H', f))
    data[10] = leaves; data[11] = newmarks
    # Bound the standing hull to the fogged patch so an intro escape cannot
    # walk into the removed visible world. Preserve all authored inner hulls.
    root = struct.unpack_from('<i', data[14], 40)[0]
    nodes = list(struct.iter_unpack('<iHH', data[9]))
    if len(nodes)+4 >= 65520: raise ValueError('Dock boundary exceeds BSP29 clipnode budget')
    prefixed = bytearray()
    for i, (axis, distance, front_solid) in enumerate([
            (0, xmax-7.32, True), (0, xmin+7.32, False),
            (1, ymax-7.12, True), (1, ymin+7.12, False)]):
        normal = [0.0, 0.0, 0.0]; normal[axis] = 1.0
        plane = len(data[1])//20
        data[1].extend(struct.pack('<4fi', *normal, distance, axis))
        child = i+1 if i<3 else root+4
        prefixed.extend(struct.pack('<iHH', plane, 65534 if front_solid else child,
                                    child if front_solid else 65534))
    for plane, front, back in nodes:
        prefixed.extend(struct.pack('<iHH', plane,
                        front+4 if front < len(nodes) else front,
                        back+4 if back < len(nodes) else back))
    data[9] = prefixed
    for offset in range(0, len(data[14]), 64):
        for hull in range(1, 4):
            head = struct.unpack_from('<i', data[14], offset+36+hull*4)[0]
            if head >= 0: struct.pack_into('<i', data[14], offset+36+hull*4, head+4)
    struct.pack_into('<i', data[14], 40, 0)
    counts.update(world_faces_hidden=len(hidden), entities_before=len(entities),
                  entities_after=len(kept), bounds=list(bounds),
                  collision='authored hull plus four outer XY boundary planes', resident_geometry='unchanged',
                  source_sha256=hashlib.sha256(raw).hexdigest())
    return pack_lumps(data), counts


def convert(source, target):
    source, target = Path(source), Path(target)
    if source.resolve() == target.resolve():
        raise ValueError('Never replace the full exterior')
    result, report = derive(source.read_bytes())
    target.write_bytes(result)
    target.with_suffix('.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path); p.add_argument('target', type=Path)
    args = p.parse_args(); print(json.dumps(convert(args.source, args.target), indent=2))
