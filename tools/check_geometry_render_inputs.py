#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Independent, interpreted BSP29 oracle for exact geometry sharing.

No optimizer/parser imports and no compiler/subprocess invocation. Compare the
ordered render inputs and CalcSurfaceExtents inputs separately: the engine uses
>0 for renderer edge orientation but >=0 for extent calculation. Binary32
arithmetic below is a specified source-level model, not execution of Amiga C;
compiler intermediate precision/FPU behavior and target playtesting stay pending.
Only vertices, edges, surfedges and face firstedge may change. Run against the
geometry-only output, before separate lighting/PVS deduplication.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct


FORMATS = {1: '<4fi', 3: '<3f', 5: '<i2h6h2H', 6: '<8f2i',
           7: '<Hhihh4Bi', 9: '<i2H', 10: '<ii6h2H4B',
           11: '<H', 12: '<2H', 13: '<i', 14: '<9f7i'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def f32(value):
    try:
        result = struct.unpack('<f', struct.pack('<f', value))[0]
    except (OverflowError, struct.error) as exc:
        raise ValueError('Non-finite binary32 arithmetic') from exc
    require(math.isfinite(result), 'Non-finite binary32 arithmetic')
    return result


def project(point, vec):
    # Explicit left-to-right rounded products/adds; both inputs must agree.
    return f32(f32(f32(f32(point[0]*vec[0]) + f32(point[1]*vec[1]))
                       + f32(point[2]*vec[2])) + vec[3])


def project_wide(point, vec):
    """Alternative: wide intermediate products/sums, rounded on float store."""
    return f32(point[0]*vec[0]+point[1]*vec[1]+point[2]*vec[2]+vec[3])


class BSP:
    def __init__(self, raw):
        require(len(raw) >= 124, 'Truncated BSP header')
        require(struct.unpack_from('<i', raw)[0] == 29, 'Expected BSP29')
        self.parts = []
        ranges = []
        for index in range(15):
            offset, size = struct.unpack_from('<ii', raw, 4+index*8)
            require(offset >= 0 and size >= 0 and offset+size <= len(raw),
                    'Invalid lump range '+str(index))
            if size:
                require(offset >= 124, 'Lump overlaps header')
                ranges.append((offset, offset+size))
            self.parts.append(raw[offset:offset+size])
        ranges.sort()
        require(all(a[1] <= b[0] for a, b in zip(ranges, ranges[1:])),
                'Overlapping lump ranges')
        self.rows = {}
        for index, fmt in FORMATS.items():
            require(len(self.parts[index]) % struct.calcsize(fmt) == 0,
                    'Invalid record length '+str(index))
            self.rows[index] = list(struct.iter_unpack(fmt, self.parts[index]))
        r = self.rows
        for index, count in ((1, 4), (3, 3), (6, 8), (14, 9)):
            require(all(math.isfinite(v) for row in r[index] for v in row[:count]),
                    'Non-finite source float '+str(index))
        require(r[14] and r[12], 'Missing world model or edge zero')
        self.textures = self.parse_textures()
        for row in r[6]:
            require(0 <= row[8] < len(self.textures), 'Invalid texture index')
        for a, b in r[12]:
            require(a < len(r[3]) and b < len(r[3]), 'Invalid edge vertex')
        for (edge,) in r[13]:
            require(abs(edge) < len(r[12]), 'Invalid surfedge index')
        for face in r[7]:
            require(face[0] < len(r[1]), 'Invalid face plane')
            require(0 <= face[4] < len(r[6]), 'Invalid face texinfo')
            require(face[2] >= 0 and face[3] >= 1 and
                    face[2]+face[3] <= len(r[13]), 'Invalid face edge range')
            require(face[9] >= -1, 'Invalid negative light offset')
        self.protected_faces = set()
        for index, model in enumerate(r[14]):
            self.face_range(model[14], model[15])
            if index == 0:
                self.protected_faces.update(range(model[14], model[14]+model[15]))
            root = model[9]
            require(root < len(r[5]) if root >= 0 else -1-root < len(r[10]),
                    'Invalid model point root')
            for root in model[10:13]:
                require(root < len(r[9]) if root >= 0 else root >= -15,
                        'Invalid model clip root')
        for node in r[5]:
            require(0 <= node[0] < len(r[1]), 'Invalid node plane')
            self.face_range(node[9], node[10])
            self.protected_faces.update(range(node[9], node[9]+node[10]))
            for child in node[1:3]:
                require(child < len(r[5]) if child >= 0 else -1-child < len(r[10]),
                        'Invalid node child')
        for node in r[9]:
            require(0 <= node[0] < len(r[1]), 'Invalid clip plane')
            require(all(child < len(r[9]) or child >= 65521 for child in node[1:]),
                    'Invalid clip child')
        for leaf in r[10]:
            require(leaf[8]+leaf[9] <= len(r[11]), 'Invalid leaf mark range')
        for (mark,) in r[11]:
            require(mark < len(r[7]), 'Invalid marksurface')
            self.protected_faces.add(mark)

    def face_range(self, first, count):
        require(first >= 0 and count >= 0 and first+count <= len(self.rows[7]),
                'Invalid model/node face range')

    def parse_textures(self):
        part = self.parts[2]
        require(len(part) >= 4, 'Missing texture table')
        count = struct.unpack_from('<i', part)[0]
        require(0 <= count <= (len(part)-4)//4, 'Invalid texture table count')
        result = []
        for i in range(count):
            start = struct.unpack_from('<i', part, 4+4*i)[0]
            if start == -1:
                result.append(None)
                continue
            require(start >= 4+4*count and start+40 <= len(part), 'Invalid miptex header')
            width, height, *offsets = struct.unpack_from('<6I', part, start+16)
            require(width > 0 and height > 0, 'Invalid miptex dimensions')
            pixels = []
            for level, offset in enumerate(offsets):
                size = (width >> level)*(height >> level)
                if offset == 0:
                    pixels.append(None)  # External/WAD reference, still identical.
                else:
                    require(offset >= 40 and start+offset+size <= len(part),
                            'Invalid miptex pixel range')
                    pixels.append(hashlib.sha256(part[start+offset:start+offset+size]).digest())
            result.append((part[start:start+16], width, height, tuple(pixels)))
        return result

    def face_inputs(self, index, wide_intermediates=False):
        r = self.rows
        face = r[7][index]
        texinfo = r[6][face[4]]
        texture = self.textures[texinfo[8]]
        require(texture is not None, 'Missing texture requires runtime fallback; unsupported')
        paths = []
        projection = project_wide if wide_intermediates else project
        for renderer in (False, True):
            points, uv = [], []
            for (edge,) in r[13][face[2]:face[2]+face[3]]:
                endpoint = 0 if (edge > 0 if renderer else edge >= 0) else 1
                vertex = r[12][abs(edge)][endpoint]
                points.append(self.parts[3][12*vertex:12*vertex+12])
                uv.append(tuple(projection(r[3][vertex], texinfo[4*axis:4*axis+4])
                                for axis in range(2)))
            paths.append((tuple(points), tuple(uv)))
        # Match original sentinel extrema and the minimum 16-unit extent.
        mins = tuple(math.floor(min(999999., *(uv[axis] for uv in paths[0][1]))/16)*16
                     for axis in range(2))
        extents = tuple(max(16, math.ceil(max(-99999., *(uv[axis] for uv in paths[0][1]))/16)*16-mins[axis])
                        for axis in range(2))
        require(texinfo[9] & 1 or max(extents) <= 256, 'Bad surface extents')
        require(all(-32768 <= v <= 32767 for v in mins+extents),
                'Surface short overflow unsupported')
        flags = 2 if face[1] else 0
        name = texture[0].split(b'\0', 1)[0]
        if name.startswith(b'sky'):
            flags |= 4 | 32
        elif name.startswith(b'*'):
            flags |= 16 | 32
        styles = face[5:9]
        active = next((i for i, v in enumerate(styles) if v == 255), 4)
        samples = None
        if face[9] != -1:
            size = ((extents[0] >> 4)+1)*((extents[1] >> 4)+1)*active
            require(face[9]+size <= len(self.parts[8]),
                    f'Light sample range outside lump: face {index}, '
                    f'{"wide" if wide_intermediates else "binary32"} extents {extents}, '
                    f'offset {face[9]}, need {size} bytes, '
                    f'available {len(self.parts[8])-face[9]}')
            samples = self.parts[8][face[9]:face[9]+size]
        runtime_mins, runtime_extents = ((-8192, -8192), (16384, 16384)) if flags & 16 else (mins, extents)
        return (tuple(paths), self.parts[1][20*face[0]:20*face[0]+20],
                self.parts[6][40*face[4]:40*face[4]+40], flags, texture,
                mins, extents, runtime_mins, runtime_extents, styles, samples)


def compare_render_inputs(before, after):
    a, b = BSP(before), BSP(after)
    require(len(a.rows[7]) == len(b.rows[7]), 'Face count changed')
    for index in range(len(a.rows[7])):
        require(a.face_inputs(index) == b.face_inputs(index),
                'Rendered face input changed at '+str(index))
        old, new = a.rows[7][index], b.rows[7][index]
        require(old[:2]+old[3:] == new[:2]+new[3:], 'Face metadata changed')
    for index in set(range(15))-{3, 7, 12, 13}:
        require(a.parts[index] == b.parts[index], 'Unchanged lump differs: '+str(index))
    # Preserve the equality/inequality relation of cached world edge identities.
    mapping = {0: 0}
    for index, (old, new) in enumerate(zip(a.rows[7], b.rows[7])):
        for j in range(old[3]):
            source = abs(a.rows[13][old[2]+j][0])
            target = abs(b.rows[13][new[2]+j][0])
            if index in a.protected_faces:
                require(mapping.setdefault(source, target) == target, 'World edge identity split')
    require(len(set(mapping.values())) == len(mapping), 'World edge identities merged')
    # Inline faces may originally share world edges; forbid only newly introduced sharing.
    protected_source = set(mapping)
    protected_target = set(mapping.values())
    for old, new in zip(a.rows[7], b.rows[7]):
        for j in range(old[3]):
            if abs(a.rows[13][old[2]+j][0]) not in protected_source:
                require(abs(b.rows[13][new[2]+j][0]) not in protected_target,
                        'Inline edge newly aliases world edge')
    return {'status': 'Python structural/render-input equivalence verified',
            'faces_verified': len(a.rows[7]), 'world_edge_identities_verified': len(mapping),
            'source_sha256': hashlib.sha256(before).hexdigest(),
            'output_sha256': hashlib.sha256(after).hexdigest(),
            'edge_zero_paths': ['CalcSurfaceExtents: >=0 selects v0', 'renderer: >0 selects v0'],
            'float_model': 'finite binary32 source values; rounded products and left-associated adds',
            'unchanged': 'models, all collision data, texinfo, textures, light bytes, entities, PVS',
            'native_execution': 'not performed; target/FPU/renderer execution and playtest remain pending'}


def decoded_pvs(part, offset, width):
    """Independent classic BSP29 zero-run decoder; no deduplicator imports."""
    if offset == -1:
        return None
    require(0 <= offset < len(part), 'Invalid PVS offset')
    result = bytearray()
    while len(result) < width:
        require(offset < len(part), 'Truncated PVS row')
        value = part[offset]
        offset += 1
        if value:
            result.append(value)
        else:
            require(offset < len(part) and part[offset] != 0, 'Invalid PVS zero run')
            result.extend(bytes(part[offset]))
            offset += 1
        require(len(result) <= width, 'PVS row overrun')
    return bytes(result)


def compare_sample_sharing(before, after):
    """Allow only face light offsets/leaf PVS offsets and their backing bytes."""
    a, b = BSP(before), BSP(after)
    for index in set(range(15))-{4, 7, 8, 10}:
        require(a.parts[index] == b.parts[index], 'Sample sharing modified lump '+str(index))
    require(len(a.rows[7]) == len(b.rows[7]), 'Sample sharing changed face count')
    for index, (old, new) in enumerate(zip(a.rows[7], b.rows[7])):
        require(old[:-1] == new[:-1], 'Sample sharing changed face metadata')
        for wide in (False, True):
            require(a.face_inputs(index, wide) == b.face_inputs(index, wide),
                    'Sample sharing changed referenced render inputs at '+str(index))
    require(len(a.rows[10]) == len(b.rows[10]), 'Sample sharing changed leaf count')
    count = a.rows[14][0][13]
    require(0 <= count < len(a.rows[10]), 'Invalid world visibility leaf count')
    width = (count+7)//8
    for index, (old, new) in enumerate(zip(a.rows[10], b.rows[10])):
        require(old[:1]+old[2:] == new[:1]+new[2:], 'Sample sharing changed leaf data')
        require(decoded_pvs(a.parts[4], old[1], width) ==
                decoded_pvs(b.parts[4], new[1], width),
                'Sample sharing changed decoded PVS at '+str(index))
    return {'faces_verified': len(a.rows[7]), 'pvs_leaves_verified': len(a.rows[10]),
            'light_samples': 'independently compared under per-operation binary32 and wide-intermediate extents',
            'pvs': 'independently decoded classic BSP29 rows; identical'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    result = compare_render_inputs(args.source.read_bytes(), args.candidate.read_bytes())
    text = json.dumps(result, indent=2)+'\n'
    if args.report:
        args.report.write_text(text, encoding='utf-8')
    print(text, end='')


if __name__ == '__main__':
    main()
