"""Independent source/data oracle: no compiler, subprocess or native binary."""
import struct
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from check_geometry_render_inputs import BSP, compare_render_inputs
from share_bsp_geometry import share_geometry
from player_hull import lumps, pack_lumps
from test_share_bsp_geometry import repeated_geometry


class RenderInputOracleTests(unittest.TestCase):
    def test_exact_sharing_matches_both_input_paths(self):
        raw = repeated_geometry()
        candidate, _ = share_geometry(raw)
        report = compare_render_inputs(raw, candidate)
        self.assertEqual(report['faces_verified'], 3)
        self.assertEqual(len(report['edge_zero_paths']), 2)
        self.assertIn('not performed', report['native_execution'])

    def test_uv_winding_light_plane_flags_and_texture_changes_rejected(self):
        raw = repeated_geometry()
        mutations = ((6, 12, '<f', 3.0), (13, 0, '<i', -1),
                     (8, 0, '<B', 99), (1, 12, '<f', 1.0),
                     (7, 2, '<h', 1), (7, 12, '<B', 1),
                     (2, 48, '<B', 99), (14, 0, '<f', -17.0))
        for lump, offset, fmt, value in mutations:
            with self.subTest(lump=lump, offset=offset):
                data = lumps(raw)
                struct.pack_into(fmt, data[lump], offset, value)
                with self.assertRaises(ValueError):
                    compare_render_inputs(raw, pack_lumps(data))

    def test_reserved_zero_checks_renderer_endpoint_separately(self):
        data = lumps(repeated_geometry())
        struct.pack_into('<HH', data[12], 0, 0, 1)
        struct.pack_into('<i', data[13], 0, 0)
        raw = pack_lumps(data)
        face = BSP(raw).face_inputs(0)
        self.assertNotEqual(face[0][0][0], face[0][1][0])
        changed = lumps(raw)
        # Extent endpoint v0 unchanged; only renderer's edge-zero v1 changes.
        struct.pack_into('<H', changed[12], 2, 2)
        self.assertEqual(BSP(raw).face_inputs(0)[0][0],
                         BSP(pack_lumps(changed)).face_inputs(0)[0][0])
        with self.assertRaisesRegex(ValueError, 'Rendered face'):
            compare_render_inputs(raw, pack_lumps(changed))
        optimized, _ = share_geometry(raw)
        compare_render_inputs(raw, optimized)

    def test_constant_uv_keeps_minimum_extent_and_samples(self):
        data = lumps(repeated_geometry())
        struct.pack_into('<8f', data[6], 0, *([0.0]*8))
        face = BSP(pack_lumps(data)).face_inputs(0)
        self.assertEqual(face[6], (16, 16))
        self.assertEqual(len(face[-1]), 4)

    def test_serialized_uv_boundary_requires_the_larger_lightmap(self):
        data = lumps(repeated_geometry())
        # Asset-free example: in decimal arithmetic 1.2*21.7+165.96=192.
        # Stored binary32 values project above 192 under BOTH policies, so
        # the renderer needs four U samples rather than the producer's three.
        points = ((1.2, 0, 0), (0, 0, 0), (0, 16, 0))
        for index in range(len(data[3])//12):
            struct.pack_into('<3f', data[3], index*12, *points[index % 3])
        struct.pack_into('<8f', data[6], 0, 21.7, 0, 0, 165.96, 0, 1, 0, 0)
        for index in range(len(data[7])//20):
            struct.pack_into('<i', data[7], index*20+16, 0)
        data[8] = bytearray([80]*6)
        parsed = BSP(pack_lumps(data))
        # The engine rule's span must lie inside the lump; the binary32 rule
        # (engines before it) is compared on the bytes that exist.
        with self.assertRaisesRegex(ValueError, 'face 0.*need 8 bytes, available 6'):
            parsed.face_inputs(0, True)
        self.assertEqual(parsed.face_inputs(0, False)[-1], bytes([80]*6))
        with self.assertRaisesRegex(ValueError, 'face 0.*need 8 bytes, available 6'):
            compare_render_inputs(pack_lumps(data), pack_lumps(data))
        # A correctly baked complete grid is accepted, without weakening bounds.
        data[8] = bytearray([80]*8)
        parsed = BSP(pack_lumps(data))
        for wide in (False, True):
            face = parsed.face_inputs(0, wide)
            self.assertEqual(face[5:7], ((160, 0), (48, 16)))
            self.assertEqual(face[-1], bytes([80]*8))

    def test_malformed_indices_ranges_and_nonfinite_are_rejected(self):
        raw = repeated_geometry()
        mutations = ((7, 4, '<i', -1), (7, 8, '<h', 0),
                     (7, 10, '<h', 999), (7, 16, '<i', 9999),
                     (12, 0, '<H', 65535), (13, 0, '<i', -999),
                     (6, 0, '<f', float('nan')), (3, 0, '<f', float('inf')),
                     (14, 60, '<i', 999), (10, 20, '<H', 999),
                     (2, 4, '<i', 999999), (2, 32, '<I', 999999))
        for lump, offset, fmt, value in mutations:
            with self.subTest(lump=lump, offset=offset):
                data = lumps(raw)
                struct.pack_into(fmt, data[lump], offset, value)
                with self.assertRaises(ValueError):
                    compare_render_inputs(pack_lumps(data), pack_lumps(data))
        for offset, value in ((4, -1), (8, len(raw)+1), (4+8, 124)):
            bad = bytearray(raw)
            struct.pack_into('<i', bad, offset, value)
            with self.assertRaises(ValueError):
                BSP(bad)


if __name__ == '__main__':
    unittest.main()
