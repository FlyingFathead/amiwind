import importlib.util
import os
from pathlib import Path
import struct
import sys
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import prepare_hand_normals as normal


def model():
    # Outward clockwise tetrahedron in MDL's winding convention.
    vertices = np.array([[0, 0, 0], [10, 0, 0], [0, 10, 0], [0, 0, 10]], np.uint8)
    faces = [(0, 1, 2), (0, 3, 1), (0, 2, 3), (1, 3, 2)]
    raw = bytearray(struct.pack('<4si3f3ff3f8if', b'IDPO', 6, 1, 1, 1, 0, 0, 0, 18, 0, 0, 0, 1, 4, 4, 4, 4, 8, 0, 0, 1))
    raw += struct.pack('<i', 0) + bytes([1] * 16)
    raw += struct.pack('<12i', *([0] * 12))
    for face in faces:
        raw += struct.pack('<4i', 1, *face)
    for frame in range(8):
        raw += struct.pack('<i4B4B16s', 0, 0, 0, 0, 0, 10, 10, 10, 0, b'idle')
        raw += np.column_stack((vertices, np.zeros(4, np.uint8))).astype(np.uint8).tobytes()
    return bytes(raw)


class NormalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path(os.environ.get('AMIWIND_SOURCE', ROOT))
        cls.table = normal.normal_table(source / 'engine/aga/src/anorms.h')

    def test_outward_winding_and_only_normal_bytes(self):
        old = model()
        raw, report = normal.rewrite(old, self.table)
        points, faces, offsets = normal.decode(raw)
        self.assertEqual(len(raw), len(old))
        self.assertTrue(report['geometry_texture_animation_byte_identical'])
        changed = set(np.flatnonzero(np.frombuffer(raw, np.uint8) != np.frombuffer(old, np.uint8)))
        self.assertTrue(changed and changed <= set(offsets.ravel()))
        normals = self.table[np.frombuffer(raw, np.uint8)[offsets[0]]]
        # All four faces of the tetrahedron must point away from its center.
        self.assertTrue(np.all(np.einsum('ij,ij->i', normals, points[0] - points[0].mean(0)) > 0))
        self.assertEqual(raw, normal.rewrite(raw, self.table)[0])

    def test_collapsed_vertices_are_explicit(self):
        frames = np.zeros((8, 3, 3))
        indices, fallback = normal.surface_indices(frames, np.array([[0, 2, 1]]), self.table)
        self.assertEqual(fallback, 24)
        self.assertFalse(indices.any())

    def test_complete_trajectory_key_does_not_weld_animation(self):
        points = np.array([[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 0], [0, 0, 1], [1, 0, 0]]], float)
        points = np.repeat(points, 8, axis=0)
        points[4, 3] = [.2, .2, .2]
        before = points.copy()
        indices, _ = normal.surface_indices(points, np.array([[0, 2, 1], [3, 5, 4]]), self.table)
        self.assertTrue(np.array_equal(points, before))
        self.assertNotEqual(indices[0, 0], indices[0, 3])

    def test_bounds_and_truncation(self):
        for data in (model()[:-1], model() + b'x', b'bad', model()[:90]):
            with self.assertRaises(ValueError):
                normal.rewrite(data, self.table)

    def test_grouped_frame_and_bad_indices_rejected(self):
        original = model()
        _, _, offsets = normal.decode(original)
        for at, replacement in ((int(offsets[0, 0]) - 31, struct.pack('<i', 1)),
                                (int(offsets[0, 0]), bytes([255])),
                                (88 + 16 + 4 * 12 + 4, struct.pack('<i', 4))):
            raw = bytearray(original)
            raw[at:at + len(replacement)] = replacement
            with self.assertRaises(ValueError):
                normal.rewrite(bytes(raw), self.table)

    def test_nonfinite_and_invalid_scale(self):
        for value in (float('nan'), float('inf'), 0, -1):
            raw = bytearray(model())
            struct.pack_into('<f', raw, 8, value)
            with self.assertRaises(ValueError):
                normal.rewrite(bytes(raw), self.table)


if __name__ == '__main__':
    unittest.main()
