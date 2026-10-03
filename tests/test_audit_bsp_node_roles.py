import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from audit_bsp_node_roles import audit
from player_hull import lumps, pack_lumps
from test_replace_bsp_world import fixture


def collision_fixture():
    data = lumps(fixture(inline=True))
    struct.pack_into('<H', data[5], 24+22, 0)
    return data


class NodeRoleTests(unittest.TestCase):
    def test_separate_collision_tree_and_zero_face_world_nodes(self):
        data = collision_fixture()
        struct.pack_into('<H', data[5], 22, 0)
        report = audit(pack_lumps(data))
        self.assertEqual(report['world_render_zero_face_nodes'], 1)
        self.assertEqual(report['eligible_collision_only_zero_face_nodes'], 1)
        self.assertEqual(report['avoidable_expanded_resident_bytes_before_bookkeeping'], 40)
        self.assertTrue(report['safe_prefix_candidate'])

    def test_shared_world_root_is_never_counted_as_disposable(self):
        data = collision_fixture()
        struct.pack_into('<i', data[14], 64+36, 0)
        report = audit(pack_lumps(data))
        self.assertEqual(report['eligible_collision_only_zero_face_nodes'], 0)
        self.assertEqual(report['shared_world_inline_nodes'], 1)
        self.assertEqual(report['unreferenced_nodes'], 1)
        self.assertFalse(report['safe_prefix_candidate'])

    def test_negative_inline_root_and_nonzero_faces_need_separate_review(self):
        report = audit(fixture(inline=True))
        self.assertEqual(report['inline_only_nodes_with_faces_require_review'], 1)
        self.assertFalse(report['safe_prefix_candidate'])
        data = collision_fixture()
        struct.pack_into('<i', data[14], 64+36, -2)
        report = audit(pack_lumps(data))
        self.assertEqual(report['inline_negative_leaf_roots'], 1)
        self.assertEqual(report['eligible_collision_only_zero_face_nodes'], 0)

    def test_noncontiguous_world_tree_is_reported(self):
        data = collision_fixture()
        data[5] += data[5][:24]
        struct.pack_into('<h', data[5], 4, 2)
        report = audit(pack_lumps(data))
        self.assertEqual(report['world_render_nodes'], 2)
        self.assertEqual(report['eligible_collision_only_zero_face_nodes'], 1)
        self.assertFalse(report['world_nodes_are_contiguous_prefix'])

    def test_cycles_bad_planes_children_and_roots_rejected(self):
        for lump, offset, fmt, value in ((5, 4, '<h', 0), (5, 0, '<i', 99),
                                        (5, 4, '<h', -99), (14, 36, '<i', 1),
                                        (14, 100, '<i', -99)):
            data = collision_fixture()
            struct.pack_into(fmt, data[lump], offset, value)
            with self.assertRaises(ValueError):
                audit(pack_lumps(data))


if __name__ == '__main__':
    unittest.main()
