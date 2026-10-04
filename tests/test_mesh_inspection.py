# SPDX-License-Identifier: GPL-3.0-or-later
"""Asset-free structural checks for the offline mesh inspection exporter."""
import importlib.util
import json
from pathlib import Path
import struct
import unittest

tool = Path(__file__).with_name('export_mesh_inspection.py')
if not tool.exists():
    tool = Path(__file__).resolve().parents[1] / 'tools' / 'export_mesh_inspection.py'
spec = importlib.util.spec_from_file_location('exporter', tool)
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


def synthetic_bsp(textured=False):
    # Two placements referencing the same square: model zero and a rotated brush.
    lumps = [b'' for _ in range(15)]
    lumps[0] = b'{"classname" "worldspawn"}\n{"classname" "func_wall" "model" "*1" "origin" "10 20 30" "angles" "0 90 0" "aw_ref" "synthetic"}\0'
    lumps[3] = b''.join(struct.pack('<3f', *p) for p in ((0, 0, 0), (2, 0, 0), (2, 2, 0), (0, 2, 0)))
    lumps[12] = b''.join(struct.pack('<HH', *p) for p in ((0, 1), (1, 2), (2, 3), (3, 0)))
    lumps[13] = struct.pack('<4i', 0, 1, 2, 3)
    lumps[7] = struct.pack('<Hhihh4Bi', 0, 0, 0, 4, 7, 0, 0, 0, 0, -1)
    model = struct.pack('<9f7i', *(0.0 for _ in range(9)), *(0 for _ in range(4)), 0, 0, 1)
    lumps[14] = model * 2
    if textured:
        pixels = bytes([0, 255] * 128)
        mip_header = struct.pack('<16s6I', b'synthetic_check', 16, 16, 40, 296, 360, 376)
        lumps[2] = struct.pack('<ii', 1, 8) + mip_header + pixels + bytes(64+16+4)
        info = struct.pack('<8fii', 2, 0, 0, 3, 0, 4, 0, 5, 0, 0)
        lumps[6] = info * 8
    offset = 124
    header = bytearray(struct.pack('<i', 29))
    for lump in lumps:
        header.extend(struct.pack('<ii', offset, len(lump)))
        offset += len(lump)
    return bytes(header) + b''.join(lumps)


class MeshInspectionTests(unittest.TestCase):
    def test_shared_model_rotation_and_origin(self):
        scene = exporter.extract(synthetic_bsp(), 'synthetic.bsp')
        self.assertEqual(len(scene['objects']), 2)
        world, placed = scene['objects']
        self.assertEqual(world['vertices'][1], [2, 0, 0])
        for actual, expected in zip(placed['vertices'][1], [10, 22, 30]):
            self.assertAlmostEqual(actual, expected)
        self.assertEqual(placed['faceCount'], 1)
        self.assertEqual(placed['materialCount'], 1)
        self.assertEqual(len(placed['edges']), 4)
        self.assertEqual(len(placed['triangles']), 2)
        self.assertEqual(placed['reference'], 'synthetic')

    def test_reject_truncated_lump(self):
        with self.assertRaisesRegex(ValueError, 'Invalid lump'):
            exporter.extract(synthetic_bsp()[:-1], 'broken')

    def test_reject_invalid_edge(self):
        raw = bytearray(synthetic_bsp())
        edge_offset = struct.unpack_from('<i', raw, 4 + 12 * 8)[0]
        struct.pack_into('<H', raw, edge_offset, 9999)
        with self.assertRaisesRegex(ValueError, 'Vertex outside'):
            exporter.extract(raw, 'broken')

    def test_reject_invalid_model(self):
        raw = synthetic_bsp().replace(b'"*1"', b'"*9"')
        with self.assertRaisesRegex(ValueError, 'Model index'):
            exporter.extract(raw, 'broken')

    def test_reject_wrong_format(self):
        with self.assertRaisesRegex(ValueError, 'version 29'):
            exporter.extract(b'not a BSP', 'broken')

    def test_reject_nonfinite_geometry(self):
        raw = bytearray(synthetic_bsp())
        vertex_offset = struct.unpack_from('<i', raw, 4 + 3 * 8)[0]
        struct.pack_into('<f', raw, vertex_offset, float('nan'))
        with self.assertRaisesRegex(ValueError, 'Non-finite'):
            exporter.extract(raw, 'broken')

    def test_reject_nonfinite_angles(self):
        raw = bytearray(synthetic_bsp().replace(b'"0 90 0"', b'"0 nan 0"'))
        # Update the entity lump and subsequent offsets for the one added byte.
        for i in range(15):
            offset, size = struct.unpack_from('<ii', raw, 4 + i * 8)
            struct.pack_into('<ii', raw, 4 + i * 8, offset + (1 if i else 0), size + (1 if i == 0 else 0))
        with self.assertRaisesRegex(ValueError, 'placement transform'):
            exporter.extract(raw, 'broken')

    def test_inline_script_labels_are_data(self):
        scene = {'source': '</script><script>evil()</script>', 'label': '<!--\u2028'}
        serialized = exporter.script_safe_json(scene)
        self.assertNotIn('<', serialized)
        self.assertEqual(json.loads(serialized), scene)

    def test_texture_pixels_and_local_uv_survive_rotation(self):
        scene = exporter.extract(synthetic_bsp(textured=True), 'synthetic.bsp')
        texture = scene['textures'][0]
        self.assertEqual((texture['width'], texture['height']), (16, 16))
        self.assertEqual(texture['pixels'][:4], [0, 255, 0, 255])
        world, rotated = scene['objects']
        self.assertEqual(world['polygons'][0]['uv'], [[3, 5], [7, 5], [7, 13], [3, 13]])
        self.assertEqual(world['polygons'][0]['uv'], rotated['polygons'][0]['uv'])
        self.assertEqual(rotated['polygons'][0]['texture'], 0)

    def test_reject_out_of_bounds_mip(self):
        raw = bytearray(synthetic_bsp(textured=True))
        base = struct.unpack_from('<i', raw, 4 + 2 * 8)[0]
        struct.pack_into('<I', raw, base + 8 + 24, 999999)
        with self.assertRaisesRegex(ValueError, 'mip outside'):
            exporter.extract(raw, 'broken')

    def test_missing_texture_table_entry(self):
        self.assertEqual(exporter.extract_textures(struct.pack('<ii', 1, -1)), [None])

    def test_reject_nonfinite_texinfo(self):
        raw = bytearray(synthetic_bsp(textured=True))
        base = struct.unpack_from('<i', raw, 4 + 6 * 8)[0]
        struct.pack_into('<f', raw, base, float('inf'))
        with self.assertRaisesRegex(ValueError, 'texinfo vectors'):
            exporter.extract(raw, 'broken')


if __name__ == '__main__':
    unittest.main()
