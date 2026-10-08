# SPDX-License-Identifier: GPL-3.0-only
"""Surface extents and lightmap grids exactly as the engine computes them.

The engine (`engine/aga/src/model.c`, `CalcSurfaceExtents`) projects every
vertex of a face with its texture axes in IEEE double precision after each
product and sum, in source order ((x*s0 + y*s1) + z*s2) + s3, from the
single-precision values stored in the map. It floors the minimum and ceils the
maximum to the 16-texel grid; extents below 16 become 16 and extents above 256
stop the load. The lightmap holds ((extent >> 4) + 1) samples per axis and
light style. ericw light computes the same coordinates in (at least) double
precision, so world faces agree with this rule too.

The grid must be computed from the stored values: authored texture
coordinates often sit exactly on a 16-texel line, and storing the placed
vertices and axes as single precision moves them by a few millionths of a
texel to either side (LIGHTMAP-TAIL-31, LIGHTMAP-GRID-31).

`target_extents` is the conservative check: the largest extents any plausible
FPU rule gives for the stored values (the engine rule, single precision after
every operation as GCC emits for the 68040 without the engine's rounding
helper, and 68040 extended intermediates kept unrounded), so a face passes
only if it fits whatever the arithmetic (MESH-EXTENT-GRID-31).
"""
import math
import struct

import numpy as np

# Margin (texels) by which split_surface widens a face's span before rounding
# to the grid: drift from placement and single-precision storage is far below
# it, so a span that sits exactly on grid lines is split, not left at the limit.
GRID_GUARD = 1/16
MAX_EXTENT = 256


def stored(values):
    """Values as written to the map: single precision, widened back exactly."""
    return np.asarray(values, dtype=np.float32).astype(np.float64)


def engine_uv(points, vecs):
    """(n, 2) texture coordinates by the engine rule; inputs as stored."""
    p = stored(points).reshape(-1, 3)
    v = stored(vecs).reshape(2, 4)
    return np.column_stack([((p[:, 0]*v[j, 0] + p[:, 1]*v[j, 1]) + p[:, 2]*v[j, 2]) + v[j, 3]
                            for j in range(2)])


def binary32_uv(points, vecs):
    """Single precision after every product and sum (GCC -m68040 fsmul/fsadd)."""
    p = np.asarray(points, dtype=np.float32).reshape(-1, 3)
    v = np.asarray(vecs, dtype=np.float32).reshape(2, 4)
    return np.column_stack([(((p[:, 0]*v[j, 0]) + (p[:, 1]*v[j, 1])) + (p[:, 2]*v[j, 2])) + v[j, 3]
                            for j in range(2)]).astype(np.float64)


def extended_uv(points, vecs):
    """68040 extended intermediates (64-bit mantissa), not rounded on store.

    numpy's longdouble is x87 extended on Linux x86; elsewhere it falls back to
    double, which still bounds the exact value as closely as the engine rule.
    """
    p = stored(points).reshape(-1, 3).astype(np.longdouble)
    v = stored(vecs).reshape(2, 4).astype(np.longdouble)
    return np.column_stack([((p[:, 0]*v[j, 0] + p[:, 1]*v[j, 1]) + p[:, 2]*v[j, 2]) + v[j, 3]
                            for j in range(2)])


def grid(uv):
    """(texturemins, extents) per axis from projected coordinates."""
    mins, extents = [], []
    for axis in range(2):
        # Round in the coordinates' own precision (extended stays extended).
        low = int(np.floor(np.minimum(999999., np.min(uv[:, axis]))/16))
        high = int(np.ceil(np.maximum(-99999., np.max(uv[:, axis]))/16))
        mins.append(low*16)
        extents.append(max(16, (high-low)*16))
    return tuple(mins), tuple(extents)


def engine_grid(points, vecs):
    """Engine (texturemins, extents); plain Python floats are IEEE doubles."""
    p = stored(points).reshape(-1, 3).tolist()
    v = stored(vecs).reshape(2, 4).tolist()
    mins, extents = [], []
    for s0, s1, s2, s3 in v:
        values = [((x*s0 + y*s1) + z*s2) + s3 for x, y, z in p]
        low = math.floor(min(999999., *values)/16)
        high = math.ceil(max(-99999., *values)/16)
        mins.append(low*16)
        extents.append(max(16, (high-low)*16))
    return tuple(mins), tuple(extents)


def target_extents(points, vecs):
    """Largest extents over the engine, binary32 and extended rules."""
    result = [0, 0]
    for rule in (engine_uv, binary32_uv, extended_uv):
        _, extents = grid(rule(points, vecs))
        result = [max(a, b) for a, b in zip(result, extents)]
    return tuple(result)


def sample_dimensions(extents):
    return tuple((e >> 4)+1 for e in extents)


def lightmap_grid(points, vecs):
    """(texturemins, sample dimensions) of the engine's lightmap for a face."""
    mins, extents = engine_grid(points, vecs)
    return mins, sample_dimensions(extents)


def check_face(points, vecs, special=False, label='face'):
    """Engine grid of a face; ValueError if any rule exceeds the 256-texel limit."""
    mins, extents = engine_grid(points, vecs)
    if not special:
        worst = target_extents(points, vecs)
        if max(worst) > MAX_EXTENT:
            raise ValueError(f'Bad surface extents on the target: {label} extents {worst} '
                             f'(engine rule {extents}) exceed {MAX_EXTENT}')
    return mins, extents


def face_points(vertex_lump, vertex_indices):
    """Stored vertex positions for a face, in its vertex order."""
    return np.array([struct.unpack_from('<3f', vertex_lump, 12*i) for i in vertex_indices],
                    dtype=np.float64)


def texinfo_vecs(texinfo_lump, index):
    return np.array(struct.unpack_from('<8f', texinfo_lump, 40*index),
                    dtype=np.float64).reshape(2, 4)


def check_lumps(lumps, first_face=0, last_face=None):
    """Vectorised target check of faces [first_face, last_face) of BSP29 lumps.

    Returns the number of faces checked; ValueError names the first faces whose
    extents exceed 256 texels under any rule. Faces with special texinfo flags
    (sky, water) are exempt, as in the engine.
    """
    raw_faces = bytes(lumps[7][first_face*20:None if last_face is None else last_face*20])
    if not raw_faces:
        return 0
    faces = np.frombuffer(raw_faces, dtype=np.dtype([
        ('plane', '<u2'), ('side', '<i2'), ('firstedge', '<i4'), ('numedges', '<i2'),
        ('texinfo', '<u2'), ('styles', 'u1', 4), ('lightofs', '<i4')]))
    infos = np.frombuffer(bytes(lumps[6]), dtype=np.dtype([('vecs', '<f4', (2, 4)), ('miptex', '<i4'),
                                                          ('flags', '<i4')]))
    if np.any(faces['texinfo'] >= len(infos)):
        raise ValueError('Face texinfo index outside texinfo lump')
    counts = faces['numedges'].astype(np.int64)
    if np.any(counts < 1):
        raise ValueError('Face without edges')
    starts = np.r_[0, np.cumsum(counts)[:-1]]
    surfedges = np.frombuffer(bytes(lumps[13]), '<i4')
    edges = np.frombuffer(bytes(lumps[12]), '<u2').reshape(-1, 2)
    vertices = np.frombuffer(bytes(lumps[3]), '<f4').reshape(-1, 3)
    index = np.concatenate([np.arange(f, f+n) for f, n in zip(faces['firstedge'], counts)])
    selected = surfedges[index]
    points32 = vertices[edges[np.abs(selected), (selected < 0).astype(int)]]
    vecs32 = np.repeat(infos['vecs'][faces['texinfo']], counts, axis=0)
    p64, v64 = points32.astype(np.float64), vecs32.astype(np.float64)
    pe, ve = p64.astype(np.longdouble), v64.astype(np.longdouble)
    rules = {
        'engine': [((p64[:, 0]*v64[:, j, 0] + p64[:, 1]*v64[:, j, 1]) + p64[:, 2]*v64[:, j, 2]) + v64[:, j, 3]
                   for j in range(2)],
        'binary32': [(((points32[:, 0]*vecs32[:, j, 0]) + (points32[:, 1]*vecs32[:, j, 1]))
                      + (points32[:, 2]*vecs32[:, j, 2])) + vecs32[:, j, 3] for j in range(2)],
        'extended': [((pe[:, 0]*ve[:, j, 0] + pe[:, 1]*ve[:, j, 1]) + pe[:, 2]*ve[:, j, 2]) + ve[:, j, 3]
                     for j in range(2)],
    }
    worst = np.zeros((len(faces), 2), dtype=np.int64)
    for uv in rules.values():
        for j in range(2):
            low = np.floor(np.minimum(999999., np.minimum.reduceat(uv[j], starts))/16)
            high = np.ceil(np.maximum(-99999., np.maximum.reduceat(uv[j], starts))/16)
            worst[:, j] = np.maximum(worst[:, j], np.maximum(16, (high-low)*16).astype(np.int64))
    special = (infos['flags'][faces['texinfo']] & 1) != 0
    bad = np.flatnonzero((worst.max(axis=1) > MAX_EXTENT) & ~special)
    if len(bad):
        rows = ', '.join(f'face {first_face+int(i)} extents {tuple(int(x) for x in worst[i])}'
                         for i in bad[:5])
        raise ValueError(f'Bad surface extents on the target ({len(bad)} faces): {rows}')
    return len(faces)
