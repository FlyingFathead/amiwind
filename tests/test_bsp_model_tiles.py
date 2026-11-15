# SPDX-License-Identifier: GPL-3.0-only
"""Draw tiles of a large room-map brush model (tools/bsp_model_tiles.py, PRISON-SHIP-POLY-COLLISION-65)."""
import re
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import bsp_model_tiles as T  # noqa: E402


def synthetic_map(quads=10, mark_face=None, node_faces=None):
    """A BSP29 with the world (model 0, no faces) and model *1: QUADS unit quads in a row along x, placed by one
    func_wall with an aw_ref. Leaf 0 solid, leaf 1 empty. Model 1's hulls: a point node, clipnode 0."""
    planes = struct.pack('<4fi', 0.0, 0.0, 1.0, 0.0, 2)
    verts = b''
    edges = struct.pack('<HH', 0, 0)
    surfedges = b''
    faces = b''
    for q in range(quads):
        base = len(verts) // 12
        for x, y in ((0, 0), (1, 0), (1, 1), (0, 1)):
            verts += struct.pack('<3f', q * 10.0 + x, float(y), 0.0)
        first = len(surfedges) // 4
        for k in range(4):
            e = len(edges) // 4
            edges += struct.pack('<HH', base + k, base + (k + 1) % 4)
            surfedges += struct.pack('<i', e)
        faces += T.FACE.pack(0, 0, first, 4, 0, 0, 255, 255, 255, -1)
    nf0, nn0 = (node_faces if node_faces else (0, 0))
    nodes = T.NODE.pack(0, -2, -2, -64, -64, -64, 64, 64, 64, nf0, nn0)     # children: leaf 1 (empty)
    leafs = struct.pack('<ii6hHH4B', -2, -1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)  # solid
    leafs += struct.pack('<ii6hHH4B', -1, -1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)  # empty
    marks = struct.pack('<H', mark_face) if mark_face is not None else b''
    clip = struct.pack('<ihh', 0, -1, -2)
    models = T.MODEL.pack(-64, -64, -64, 64, 64, 64, 0, 0, 0, 0, -1, -1, -1, 0, 0, 0)
    models += T.MODEL.pack(0, 0, 0, quads * 10.0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, quads)
    ents = ('{\n"classname" "worldspawn"\n}\n{\n"classname" "func_wall"\n"aw_ref" "77"\n"model" "*1"\n'
            '"origin" "1 2 3"\n"angles" "0 -0.0 0"\n}\n\0').encode()
    lumps = [ents, planes, struct.pack('<i', 0), verts, b'', nodes, struct.pack('<8fii', *[0.0] * 8, 0, 0), faces,
             b'', clip, leafs, marks, edges, surfedges, models]
    return T._pack([bytearray(x) for x in lumps])


def parsed(raw):
    L = T._lumps(raw)
    models = [T.MODEL.unpack_from(L[14], k * 64) for k in range(len(L[14]) // 64)]
    faces = [bytes(L[7][i * 20:(i + 1) * 20]) for i in range(len(L[7]) // 20)]
    text = bytes(L[0]).rstrip(b'\0').decode()
    ents = [dict(re.findall(r'"([^"]*)"\s+"([^"]*)"', b)) for b in re.findall(r'\{[^{}]*\}', text)]
    return L, models, faces, ents


class DrawTiles(unittest.TestCase):
    def test_faces_moved_not_changed(self):
        raw = synthetic_map(10)
        out, rec = T.tile_model(raw, 1, 3)
        L0, m0, f0, _ = parsed(raw)
        L1, m1, f1, ents = parsed(out)
        self.assertEqual(sorted(f0), sorted(f1))            # the same face records, only reordered
        self.assertEqual(len(f0), len(f1))
        self.assertEqual(rec['tiles'], 4)                    # 10 faces at most 3 a tile: 3, 2, 3, 2 by medians
        self.assertTrue(all(n <= 3 for n in rec['faces_per_tile']))
        self.assertEqual(sum(rec['faces_per_tile']), 10)
        # the shell keeps its box and hulls and draws nothing
        self.assertEqual(m1[1][:6], m0[1][:6])
        self.assertEqual(m1[1][9:13], m0[1][9:13])
        self.assertEqual(m1[1][15], 0)
        # the tiles partition the shell's range and their boxes hold their faces
        at = m0[1][14]
        for number in rec['tile_models']:
            t = m1[number]
            self.assertEqual(t[14], at)
            at += t[15]
            self.assertEqual(t[10:13], (-1, -1, -1))
            node = T.NODE.unpack_from(L1[5], t[9] * T.NODE.size)
            self.assertEqual(node[1:3], (-2, -2))          # both children the empty leaf (leaf 1)
            for i in range(t[14], t[14] + t[15]):
                p = T.face_points(L1, i)
                self.assertTrue((p >= t[0:3]).all() and (p <= t[3:6]).all())
        self.assertEqual(at, m0[1][14] + 10)
        tiles = [e for e in ents if e.get('aw_tile_of') == '77']
        self.assertEqual(len(tiles), 4)
        for e in tiles:
            self.assertEqual((e['classname'], e['origin'], e['angles']), ('func_wall', '1 2 3', '0 -0.0 0'))
            self.assertNotIn('aw_ref', e)
        self.assertEqual(sum(1 for e in ents if e.get('aw_ref') == '77'), 1)

    def test_tiles_are_spatial(self):
        out, rec = T.tile_model(synthetic_map(8), 1, 2)
        L, models, _, _ = parsed(out)
        spans = sorted((models[n][0], models[n][3]) for n in rec['tile_models'])
        for (lo_a, hi_a), (lo_b, hi_b) in zip(spans, spans[1:]):
            self.assertLessEqual(hi_a, lo_b + 2)            # neighbours along the row, no tile spans the row

    def test_deterministic(self):
        raw = synthetic_map(12)
        self.assertEqual(T.tile_model(raw, 1, 5)[0], T.tile_model(raw, 1, 5)[0])

    def test_small_model_unchanged(self):
        raw = synthetic_map(4)
        out, rec = T.tile_model(raw, 1, 4)
        self.assertEqual(out, raw)
        self.assertEqual(rec['tiles'], 0)

    def test_refuses_shared_faces(self):
        with self.assertRaises(ValueError):
            T.tile_model(synthetic_map(10, mark_face=3), 1, 3)
        with self.assertRaises(ValueError):
            T.tile_model(synthetic_map(10, node_faces=(2, 2)), 1, 3)
        with self.assertRaises(ValueError):
            T.tile_model(synthetic_map(10), 0, 3)

    def test_model_by_ref(self):
        self.assertEqual(T.model_by_ref(synthetic_map(3), 77), 1)
        with self.assertRaises(ValueError):
            T.model_by_ref(synthetic_map(3), 78)


if __name__ == '__main__':
    unittest.main()
