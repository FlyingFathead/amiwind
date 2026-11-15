#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Draw tiles for a large brush model of a room map (PRISON-SHIP-POLY-COLLISION-65).

The engine tests each brush model's box against the view frustum once (r_main.c R_BmodelCheckBBox) and then sends every
face of a model in view to the edge list, face by face: a model has no per-face frustum test and the converted meshes'
own nodes reference no faces (they are a point-trace chain, model.c AW_BrushFinish). A room shell made of one model
(the prison ship's hull, 7,997 faces, its box the whole room) is therefore in view from every heading, and all its
faces are tested every frame, although at most headings only a few hundred of them are on screen.

This pass splits such a model's faces into draw tiles: the faces are grouped by their centres (a k-d split at the
median of the longest axis until a group holds at most ``max_faces``), each group becomes a new brush model with its
own box and no collision (one node whose two children are the map's empty leaf, hull roots -1, as the converter writes
a nonsolid prop), and a func_wall entity per tile is added at the shell's placement. The shell's own model keeps its
box, its collision trees and its entity (aw_ref) and loses its faces (numfaces 0). No face is split, added or changed:
the face records are only reordered inside the shell's own range, so the drawn surface is exactly the same.

Refused (ValueError) when anything else references a face in the shell's range (a node or a leaf's mark surface).
"""
import argparse
import json
import re
import struct
from pathlib import Path

import numpy as np

# the switch (--room-draw-tiles, AMIWIND_ROOM_DRAW_TILES; 512 by default, 0 = one model) lives in room_map_env
from room_map_env import ROOM_DRAW_TILES_DEFAULT, ROOM_DRAW_TILES_VARIABLE, room_draw_tiles  # noqa: F401

FACE = struct.Struct('<HhihH4Bi')
MODEL = struct.Struct('<9f7i')
NODE = struct.Struct('<ihh6h2H')
LEAF = 28
CONTENTS_EMPTY = -1


def _lumps(raw):
    if len(raw) < 124 or struct.unpack_from('<i', raw)[0] != 29:
        raise ValueError('Expected BSP29')
    out = []
    for i in range(15):
        o, n = struct.unpack_from('<ii', raw, 4 + i * 8)
        if o < 124 or n < 0 or o + n > len(raw):
            raise ValueError('BSP lump bounds')
        out.append(bytearray(raw[o:o + n]))
    return out


def _pack(data):
    head = bytearray(struct.pack('<i', 29) + bytes(120))
    body = bytearray()
    for i, raw in enumerate(data):
        body += bytes(-len(body) % 4)
        struct.pack_into('<ii', head, 4 + i * 8, 124 + len(body), len(raw))
        body += raw
    return bytes(head + body)


def face_points(lumps, face_index):
    """The corners of one face (model space), in winding order."""
    _, _, firstedge, numedges, _, _, _, _, _, _ = FACE.unpack_from(lumps[7], face_index * FACE.size)
    pts = []
    for j in range(numedges):
        se = struct.unpack_from('<i', lumps[13], (firstedge + j) * 4)[0]
        a, b = struct.unpack_from('<HH', lumps[12], abs(se) * 4)
        v = a if se >= 0 else b
        pts.append(struct.unpack_from('<3f', lumps[3], v * 12))
    return np.array(pts, float)


def kd_groups(centres, max_faces):
    """Index groups of at most max_faces centres: split at the median of the longest axis (a stable order)."""
    if max_faces < 1:
        raise ValueError('max_faces must be at least 1')
    out = []
    stack = [np.arange(len(centres))]
    while stack:
        idx = stack.pop()
        if len(idx) <= max_faces:
            out.append(idx)
            continue
        c = centres[idx]
        axis = int(np.argmax(c.max(axis=0) - c.min(axis=0)))
        order = idx[np.argsort(c[:, axis], kind='stable')]
        half = len(order) // 2
        stack.append(order[half:])
        stack.append(order[:half])
    return out


def _model_entities(text, model_number):
    """The entity blocks (text spans) that place model *N."""
    out = []
    for m in re.finditer(r'\{[^{}]*\}', text):
        if re.search(r'"model"\s+"\*%d"' % model_number, m.group(0)):
            out.append(m.group(0))
    return out


def tile_model(raw, model_number, max_faces=512):
    """(new BSP bytes, receipt) with model *model_number's faces moved into draw tiles."""
    lumps = _lumps(raw)
    nmodels = len(lumps[14]) // MODEL.size
    if not 0 < model_number < nmodels:
        raise ValueError('Model %d is not a placed brush model of this map' % model_number)
    m = list(MODEL.unpack_from(lumps[14], model_number * MODEL.size))
    first, count = m[14], m[15]
    if count <= max_faces:
        return raw, {'model': model_number, 'faces': count, 'tiles': 0, 'note': 'not tiled: at most max_faces faces'}
    end = first + count
    # nothing else may name these faces: the nodes' face ranges and the leaves' mark surfaces
    for k in range(len(lumps[5]) // NODE.size):
        node = NODE.unpack_from(lumps[5], k * NODE.size)
        f0, nf = node[9], node[10]
        if nf and f0 < end and f0 + nf > first:
            raise ValueError('Node %d references faces of model %d' % (k, model_number))
    marks = struct.unpack('<%dH' % (len(lumps[11]) // 2), bytes(lumps[11]))
    if any(first <= s < end for s in marks):
        raise ValueError('A leaf marks a face of model %d' % model_number)
    for k in range(nmodels):
        if k == model_number:
            continue
        o = MODEL.unpack_from(lumps[14], k * MODEL.size)
        if o[15] and o[14] < end and o[14] + o[15] > first:
            raise ValueError('Model %d shares faces with model %d' % (k, model_number))
    text = bytes(lumps[0]).rstrip(b'\0').decode('latin-1')
    placements = _model_entities(text, model_number)
    if not placements:
        raise ValueError('No entity places model %d' % model_number)
    if nmodels + 1 > 256:
        raise ValueError('Model budget exceeded')
    points = [face_points(lumps, first + i) for i in range(count)]
    centres = np.array([p.mean(axis=0) for p in points])
    groups = kd_groups(centres, max_faces)
    if nmodels + len(groups) > 256:
        raise ValueError('Model budget exceeded: %d models and %d tiles, limit 256' % (nmodels, len(groups)))
    # the faces in tile order inside the shell's own range
    order = np.concatenate(groups)
    records = [bytes(lumps[7][(first + int(i)) * FACE.size:(first + int(i) + 1) * FACE.size]) for i in order]
    lumps[7][first * FACE.size:end * FACE.size] = b''.join(records)
    # one shared empty point node for the tiles (the converter's nonsolid node: both children the empty leaf)
    empty_leaf = next(i for i in range(len(lumps[10]) // LEAF) if struct.unpack_from('<i', lumps[10], i * LEAF)[0] == CONTENTS_EMPTY)
    plane = None
    for k in range(len(lumps[1]) // 20):
        nx, ny, nz, d, t = struct.unpack_from('<4fi', lumps[1], k * 20)
        if (nx, ny, nz, d) == (1.0, 0.0, 0.0, 0.0):
            plane = k
            break
    if plane is None:
        plane = len(lumps[1]) // 20
        lumps[1] += struct.pack('<4fi', 1.0, 0.0, 0.0, 0.0, 0)
    root = len(lumps[5]) // NODE.size
    if root > 32767:
        raise ValueError('Point node budget exceeded')
    leaf = -empty_leaf - 1
    lumps[5] += NODE.pack(plane, leaf, leaf, -32768, -32768, -32768, 32767, 32767, 32767, 0, 0)
    tiles = []
    at = first
    for g in groups:
        p = np.concatenate([points[int(i)] for i in g])
        lo = np.floor(p.min(axis=0)) - 1
        hi = np.ceil(p.max(axis=0)) + 1
        number = len(lumps[14]) // MODEL.size
        lumps[14] += MODEL.pack(*lo, *hi, 0, 0, 0, root, -1, -1, -1, 0, at, len(g))
        tiles.append({'model': number, 'faces': len(g), 'mins': lo.tolist(), 'maxs': hi.tolist()})
        at += len(g)
    m[15] = 0
    MODEL.pack_into(lumps[14], model_number * MODEL.size, *m)
    added = []
    for block in placements:
        kv = dict(re.findall(r'"([^"]*)"\s+"([^"]*)"', block))
        for t in tiles:
            fields = [('classname', 'func_wall'), ('model', '*%d' % t['model'])]
            for key in ('origin', 'angles', 'angle'):
                if key in kv:
                    fields.append((key, kv[key]))
            if 'aw_ref' in kv:
                fields.append(('aw_tile_of', kv['aw_ref']))
            added.append('{\n' + ''.join('"%s" "%s"\n' % f for f in fields) + '}')
    lumps[0] = bytearray((text.rstrip('\n') + '\n' + '\n'.join(added) + '\n').encode('latin-1') + b'\0')
    receipt = {'model': model_number, 'faces': count, 'max_faces': max_faces, 'tiles': len(tiles),
               'placements': len(placements), 'entities_added': len(added), 'models_after': len(lumps[14]) // MODEL.size,
               'faces_per_tile': [t['faces'] for t in tiles], 'tile_models': [t['model'] for t in tiles],
               'rule': 'faces reordered inside the model range by a k-d split of their centres; the model keeps its box and '
                       'collision with no faces; each tile is a nonsolid func_wall at the same placement'}
    return _pack(lumps), receipt


def model_by_ref(raw, aw_ref):
    """The model number the entity with this aw_ref places."""
    lumps = _lumps(raw)
    text = bytes(lumps[0]).rstrip(b'\0').decode('latin-1')
    for block in re.findall(r'\{[^{}]*\}', text):
        kv = dict(re.findall(r'"([^"]*)"\s+"([^"]*)"', block))
        if kv.get('aw_ref') == str(aw_ref) and kv.get('model', '').startswith('*'):
            return int(kv['model'][1:])
    raise ValueError('No brush entity with aw_ref %s' % aw_ref)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('bsp', type=Path)
    p.add_argument('--out', type=Path, required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--model', type=int)
    g.add_argument('--aw-ref')
    p.add_argument('--max-faces', type=int, default=512)
    a = p.parse_args(argv)
    raw = a.bsp.read_bytes()
    number = a.model if a.model is not None else model_by_ref(raw, a.aw_ref)
    out, receipt = tile_model(raw, number, a.max_faces)
    a.out.write_bytes(out)
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
