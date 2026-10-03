import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from share_bsp_geometry import share_geometry, parse, face_vertices
from player_hull import lumps, pack_lumps
from test_replace_bsp_world import fixture


def repeated_geometry():
    data = lumps(fixture(inline=True))
    struct.pack_into('<H', data[5], 24+22, 0)  # Inline root is collision-only.
    data[3][36:72] = data[3][:36]
    data[3] += data[3][36:72]
    data[12] += b''.join(struct.pack('<HH', b, a) for a, b in ((6, 7), (7, 8), (8, 6)))
    data[13] += b''.join(struct.pack('<i', i) for i in (-7, -8, -9))
    face = bytearray(data[7][20:40]);struct.pack_into('<i', face, 4, 6);data[7] += face
    model = bytearray(data[14][64:128]);struct.pack_into('<i', model, 56, 2);data[14] += model
    # Native CalcSurfaceExtents yields six samples for these UVs. The minimal
    # structural fixture's four bytes per face were not intended for rendering.
    data[8] = bytearray(range(32))
    return pack_lumps(data)


class GeometrySharingTests(unittest.TestCase):
    def test_repeated_inline_metadata_keeps_world_cache_ownership(self):
        raw = repeated_geometry();result, report = share_geometry(raw)
        a, ar, protected = parse(raw);b, br, new_protected = parse(result)
        self.assertEqual(report['vertices_before'], 9)
        self.assertEqual(report['vertices_after'], 3)
        self.assertEqual(report['edges_after'], 7)  # Four protected + three inline.
        self.assertEqual(report['surfedges_after'], 6)
        self.assertEqual(len(new_protected), 4)
        world_ids = {abs(r[0]) for r in br[13][br[7][0][2]:br[7][0][2]+3]}
        inline_ids = {abs(r[0]) for r in br[13][br[7][1][2]:br[7][1][2]+3]}
        self.assertFalse(world_ids & inline_ids)
        self.assertEqual(br[7][1][2], br[7][2][2])
        for old, new in zip(ar[7], br[7]):
            self.assertEqual(face_vertices(a, ar, old), face_vertices(b, br, new))
        for i in set(range(15))-{3, 7, 12, 13}:
            self.assertEqual(a[i], b[i])
        repeated, _ = share_geometry(result)
        self.assertEqual(result, repeated)

    def test_world_duplicate_edges_remain_distinct(self):
        data = lumps(repeated_geometry())
        struct.pack_into('<i', data[14], 60, 3)  # All three faces belong to world.
        result, report = share_geometry(pack_lumps(data))
        self.assertEqual(report['edges_after'], report['edges_before'])

    def test_malformed_ranges_and_indices_rejected(self):
        cases = ((7, 4, '<i', -1), (7, 8, '<h', 0), (12, 4, '<H', 65535),
                 (13, 0, '<i', -999), (11, 0, '<H', 999), (14, 60, '<i', 999))
        for lump, offset, fmt, value in cases:
            data = lumps(repeated_geometry());struct.pack_into(fmt, data[lump], offset, value)
            with self.assertRaises(ValueError):
                share_geometry(pack_lumps(data))
        data = lumps(repeated_geometry());data[3] += b'x'
        with self.assertRaisesRegex(ValueError, 'record length'):
            share_geometry(pack_lumps(data))


if __name__ == '__main__':
    unittest.main()
