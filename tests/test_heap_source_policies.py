"""The CHIM heap audit's source policies on this tree (BUILD-EDGE-PIN-SHARED-SHAPES-63).

tools/check_world_map_heap.py reads the engine's allocation policies (packed edges, alias streaming, sprite loader,
efrag pool, BSP slices, compact harvest) from the engine source and stops the CHIM stage when one is not recognized,
for example when engine/aga/src/model.c changed without its pin in tools/edge_cache_heap.py. This test runs the
same readers on the tree, so a missing pin fails in the gate instead of hours into a build.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

import alias_stream_heap  # noqa: E402
import check_world_map_heap  # noqa: E402
import compact_harvest_heap  # noqa: E402
import edge_cache_heap  # noqa: E402
import sprite_heap  # noqa: E402

SRC = ROOT / 'engine/aga/src'


class HeapSourcePolicies(unittest.TestCase):
    def test_edge_policy_is_recognized(self):
        self.assertIn(edge_cache_heap.runtime_policy(SRC)['mode'], ('embedded', 'world_prefix'))

    def test_alias_policy_is_recognized(self):
        self.assertIn('alias_streaming', alias_stream_heap.runtime_policy(SRC))

    def test_sprite_and_efrag_policies_are_recognized(self):
        model_c = (SRC / 'model.c').read_text(encoding='utf-8')
        self.assertIn('sprite_streaming', sprite_heap.sprite_loader_profile(model_c))
        sprite_heap.efrag_pool_policy(SRC)

    def test_bsp_slice_policy_is_recognized(self):
        policy = check_world_map_heap.bsp_slice_policy((SRC / 'model.c').read_text(encoding='utf-8'))
        self.assertIn('slice_bytes', policy)
        self.assertIn('record_prefix_bytes', policy)

    def test_compact_harvest_policy_is_recognized(self):
        self.assertIn('mode', compact_harvest_heap.runtime_policy(ROOT / 'engine/aga'))


if __name__ == '__main__':
    unittest.main()
