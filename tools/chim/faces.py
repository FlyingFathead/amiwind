# SPDX-License-Identifier: GPL-3.0-only
"""The faces of a CHIM brush image as polygons (moved here from chim/validate.py, which still offers it).

A module of its own because the stair walk reads it (chim.collision.frame_polys): the walk's key holds the code it
runs (chim.collision.STAIR_WALK_CODE), and chim/validate.py also holds the world loader and the validation, whose
edits never change a walk's rows (BUILD-REUSE-SCHEDULER-TOP-45 part 2).
"""
import struct


def face_polygons(lumps):
    """[(points, normal, texinfo flags, lit)] of a brush image's faces."""
    import numpy as np
    verts = np.array(list(struct.iter_unpack('<3f', lumps[3]))) if lumps[3] else np.zeros((0, 3))
    planes = list(struct.iter_unpack('<4fi', lumps[1]))
    texinfo = list(struct.iter_unpack('<8fii', lumps[6]))
    edges = list(struct.iter_unpack('<HH', lumps[12]))
    surfedges = [v[0] for v in struct.iter_unpack('<i', lumps[13])]
    out = []
    for f in struct.iter_unpack('<HhihH4Bi', lumps[7]):
        ids = [edges[e][0] if e >= 0 else edges[-e][1] for e in surfedges[f[2]:f[2] + f[3]]]
        n = np.array(planes[f[0]][:3]) * (-1 if f[1] else 1)
        out.append((verts[ids], n, texinfo[f[4]][9], f[9] >= 0))
    return out
