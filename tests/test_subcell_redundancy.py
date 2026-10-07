# SPDX-License-Identifier: GPL-3.0-only
"""Fictional BSP29 maps only: cross-map face redundancy and density output."""
from pathlib import Path
import json
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from analyze_subcell_redundancy import analyze, main, placed_faces


def bsp(squares, entities=b''):
    """Build a minimal BSP29: each square is one world-model face (x0, y0, size)."""
    verts, edges, surfedges, faces = [], [(0, 0)], [], []
    for x0, y0, size in squares:
        base = len(verts)
        verts += [(x0, y0, 0), (x0 + size, y0, 0), (x0 + size, y0 + size, 0), (x0, y0 + size, 0)]
        first = len(surfedges)
        for i in range(4):
            edges.append((base + i, base + (i + 1) % 4)); surfedges.append(len(edges) - 1)
        faces.append(struct.pack('<HhiHh4Bi', 0, 0, first, 4, 0, 0, 255, 255, 255, -1))
    model = struct.pack('<9f4i3i', -1e3, -1e3, -1e3, 1e3, 1e3, 1e3, 0, 0, 0, 0, 0, 0, 0, 0, 0, len(faces))
    lumps = {0: entities or b'{\n"classname" "worldspawn"\n}\n',
             3: b''.join(struct.pack('<3f', *v) for v in verts),
             7: b''.join(faces), 12: b''.join(struct.pack('<2H', *e) for e in edges),
             13: b''.join(struct.pack('<i', s) for s in surfedges), 14: model}
    out = bytearray(4 + 15 * 8); struct.pack_into('<i', out, 0, 29)
    for i in range(15):
        data = lumps.get(i, b'')
        struct.pack_into('<ii', out, 4 + 8 * i, len(out), len(data)); out += data
    return bytes(out)


class SubcellRedundancyTests(unittest.TestCase):
    def test_shared_faces_count_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / 'zz000.bsp').write_bytes(bsp([(0, 0, 64), (100, 0, 64)]))
            (tmp / 'zz001.bsp').write_bytes(bsp([(100, 0, 64), (200, 0, 64)]))
            summary, per_map, points = analyze(sorted(tmp.glob('zz*.bsp')))
        self.assertEqual(summary['distinct_faces_union'], 3)
        self.assertEqual(summary['faces_summed_over_maps'], 4)
        self.assertEqual(summary['redundancy_factor'], 1.33)
        self.assertEqual(per_map['zz000']['shared_with_other_maps_percent'], 50.0)
        self.assertEqual(len(points), 3)

    def test_rejects_non_bsp29(self):
        with self.assertRaises(ValueError):
            list(placed_faces(b'\0' * 200))

    def test_cli_writes_aggregates_and_image_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / 'zz000.bsp').write_bytes(bsp([(0, 0, 64)]))
            (tmp / 'zz001.bsp').write_bytes(bsp([(0, 0, 64)]))
            regions = tmp / 'regions.json'
            regions.write_text(json.dumps({'regions': [{'name': 'zz000', 'core': [[0, 0], [64, 64]]}]}))
            main(['--maps', str(tmp), '--prefix', 'zz', '--regions', str(regions),
                  '--json', str(tmp / 'out.json'), '--image', str(tmp / 'out.png')])
            report = json.loads((tmp / 'out.json').read_text())
            self.assertEqual(report['summary']['redundancy_factor'], 2.0)
            self.assertTrue((tmp / 'out.png').read_bytes().startswith(b'\x89PNG'))
            self.assertNotIn('vert', json.dumps(report).lower())


if __name__ == '__main__':
    unittest.main()
