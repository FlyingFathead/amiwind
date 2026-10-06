#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Explicit offline lighting-normal pass for ordinary first-person MDL6 files.

Only the existing normal-index byte in each vertex changes. Geometry, authored
open ends, animation, materials and model allocation sizes remain untouched.
This approximates smooth surface normals from the encoded mesh; it does not
claim to preserve original NIF normals or repair the shape of a closed fist.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

import numpy as np


def normal_table(path):
    rows = re.findall(r'\{\s*([-+.\d]+),\s*([-+.\d]+),\s*([-+.\d]+)\s*\}', Path(path).read_text())
    table = np.asarray(rows, dtype=np.float64)
    if table.shape != (162, 3) or not np.isfinite(table).all() or not np.allclose(np.linalg.norm(table, axis=1), 1, atol=2e-6):
        raise ValueError('Expected the renderer 162-entry unit-normal table')
    return table


def decode(raw):
    if len(raw) < 88 or len(raw) > 512 * 1024 or raw[:8] != struct.pack('<4si', b'IDPO', 6):
        raise ValueError('Expected bounded ordinary MDL6')
    scale = np.asarray(struct.unpack_from('<3f', raw, 8), dtype=np.float64)
    origin = np.asarray(struct.unpack_from('<3f', raw, 20), dtype=np.float64)
    ns, w, h, nv, nt, nf = struct.unpack_from('<6i', raw, 48)
    if not np.isfinite(scale).all() or np.any(scale <= 0) or not np.isfinite(origin).all():
        raise ValueError('Invalid MDL quantization')
    if ns != 1 or w < 4 or w > 512 or w % 4 or not 1 <= h <= 480 or not 1 <= nv <= 1999 or not 1 <= nt <= 2048 or nf not in (8, 28):
        raise ValueError('Outside first-person single-skin/frame profile')
    if struct.unpack_from('<i', raw, 84)[0] != 0:
        raise ValueError('Grouped skin not supported')
    tri_start = 88 + w * h + nv * 12
    frame_start = tri_start + nt * 16
    if frame_start + nf * (28 + nv * 4) != len(raw):
        raise ValueError('Truncated, grouped or trailing MDL contents')
    tris = np.frombuffer(raw, '<i4', count=nt * 4, offset=tri_start).reshape(nt, 4)
    faces = tris[:, 1:].astype(np.int64)
    if np.any((tris[:, 0] != 0) & (tris[:, 0] != 1)) or faces.min() < 0 or faces.max() >= nv:
        raise ValueError('Invalid triangle record')
    offsets = []
    frames = []
    for i in range(nf):
        start = frame_start + i * (28 + nv * 4)
        if struct.unpack_from('<i', raw, start)[0] != 0:
            raise ValueError('Grouped frame not supported')
        encoded = np.frombuffer(raw, np.uint8, count=nv * 4, offset=start + 28).reshape(nv, 4)
        if np.any(encoded[:, 3] >= 162):
            raise ValueError('Invalid existing lighting normal')
        frames.append(encoded[:, :3].astype(np.float64) * scale)
        offsets.append(start + 28 + np.arange(nv) * 4 + 3)
    return np.asarray(frames), faces, np.asarray(offsets)


def surface_indices(frames, faces, table):
    """Area-weighted clockwise-MDL normals, smoothing only compatible copies.

    UV/tint copies can share lighting when their COMPLETE encoded animation
    trajectory is identical. Copies at a hard crease (>45 degrees between
    their own normals) remain split. No positional welding or face edits occur.
    """
    groups = {}
    for vertex in range(frames.shape[1]):
        groups.setdefault(frames[:, vertex].tobytes(), []).append(vertex)
    result = []
    fallback = 0
    for points in frames:
        # The exporters reverse NIF's counter-clockwise triangles for MDL.
        triangle = -np.cross(points[faces[:, 1]] - points[faces[:, 0]], points[faces[:, 2]] - points[faces[:, 0]])
        accum = np.zeros_like(points)
        for corner in range(3):
            np.add.at(accum, faces[:, corner], triangle)
        length = np.linalg.norm(accum, axis=1)
        own = np.divide(accum, length[:, None], out=np.zeros_like(accum), where=length[:, None] > 1e-12)
        smoothed = accum.copy()
        for ids in groups.values():
            if len(ids) < 2:
                continue
            for vertex in ids:
                compatible = np.asarray(ids)[own[ids] @ own[vertex] >= np.sqrt(.5)]
                if len(compatible):
                    smoothed[vertex] = accum[compatible].sum(axis=0)
        length = np.linalg.norm(smoothed, axis=1)
        valid = length > 1e-12
        normals = np.divide(smoothed, length[:, None], out=np.zeros_like(smoothed), where=valid[:, None])
        indices = np.argmax(normals @ table.T, axis=1).astype(np.uint8)
        indices[~valid] = 0  # authored isolated/collapsed vertices: deterministic legacy fallback
        fallback += int((~valid).sum())
        result.append(indices)
    return np.asarray(result), fallback


def rewrite(raw, table):
    frames, faces, offsets = decode(raw)
    indices, fallback = surface_indices(frames, faces, table)
    data = np.frombuffer(raw, np.uint8).copy()
    old = data[offsets].copy()
    data[offsets] = indices
    output = data.tobytes()
    changed = np.flatnonzero(np.frombuffer(raw, np.uint8) != data)
    if not set(changed).issubset(set(offsets.ravel().tolist())):
        raise AssertionError('Non-normal model byte changed')
    return output, {'input_sha256': hashlib.sha256(raw).hexdigest(), 'output_sha256': hashlib.sha256(output).hexdigest(),
                    'bytes': len(raw), 'vertices': frames.shape[1], 'triangles': len(faces), 'frames': len(frames),
                    'normal_bytes_changed': int(np.count_nonzero(old != indices)), 'unique_normal_indices': int(len(np.unique(indices))),
                    'degenerate_vertex_frames': fallback, 'geometry_texture_animation_byte_identical': True,
                    'file_size_delta': 0, 'decoded_cache_size_delta': 0, 'native_accepted': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--normal-table', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.input.resolve() == args.output.resolve():
        raise ValueError('Output must be a fresh path')
    raw, report = rewrite(args.input.read_bytes(), normal_table(args.normal_table))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('xb') as stream:
        stream.write(raw)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
