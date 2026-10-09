# SPDX-License-Identifier: GPL-3.0-only
"""The CHIM heap gate (chim.heap): every chunk's resident ring fits the engine's CHIM zone, strict.

Synthetic world and fixed ABI sizes (the gate itself probes them with the Amiga compiler)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import heap  # noqa: E402
from chim.validate import validate  # noqa: E402
from test_chim_format import fixture  # noqa: E402

# 68k sizes of the probed types (illustrative; the build probes the real ones)
SIZES = {'pointer': 4, 'short': 2, 'int': 4, 'hunk': 16, 'dvertex': 12, 'dedge': 4, 'dplane': 20, 'dnode': 24,
         'dclipnode': 8, 'clipnode': 8, 'dleaf': 28, 'texinfo': 40, 'dface': 20, 'dmodel': 64, 'mvertex': 12,
         'medge': 8, 'mplane': 20, 'mtexinfo': 52, 'msurface': 68, 'mnode': 40, 'mleaf': 48, 'texture': 100,
         'entity': 400, 'scenery': 120, 'model': 300}


class ChimHeapGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        fixture(Path(cls.tmp.name))
        fails, cls.world = validate(cls.tmp.name)
        assert not fails, fails

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_ring_peak_counts_chunks_models_textures_and_placements(self):
        r = heap.ring_peak(self.world, SIZES)
        f = r['frames'][0]
        self.assertTrue(r['ok'])
        self.assertGreater(f['peak_bytes'], 0)
        self.assertEqual(f['budget_bytes'], (r['zone_kib'] - 2 * r['pool_kib']) * 1024)
        # more placement cost, a larger peak: the catalogue entries are part of it
        bigger = heap.ring_peak(self.world, dict(SIZES, scenery=SIZES['scenery'] + 1000))['frames'][0]
        self.assertGreater(bigger['peak_bytes'], f['peak_bytes'])

    def test_gate_is_strict_and_names_the_frame(self):
        r = heap.ring_peak(self.world, SIZES)
        need_kib = r['frames'][0]['peak_bytes'] // 1024
        with self.assertRaisesRegex(ValueError, 'heap gate failed'):
            heap.require_heap(self.tmp.name, sizes=SIZES, zone_kib=need_kib + 2 * r['pool_kib'] - 1)
        report = json.loads((Path(self.tmp.name) / 'chim-heap.json').read_text())
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(heap.require_heap(self.tmp.name, sizes=SIZES)['status'], 'passed')

    def test_without_sizes_the_gate_says_it_did_not_run(self):
        self.assertIsNone(heap.require_heap(self.tmp.name)['ok'])



class StreamedStaticsHeapTests(unittest.TestCase):
    """Streamed statics' models in the rings (chunk_extra: each chunk its own copy; chunk_models: one
    copy per ring) and the zone the whole-map rule leaves (zone_bytes)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        fixture(Path(cls.tmp.name))
        cls.world = load(Path(cls.tmp.name))
        cls.base = heap.ring_peak(cls.world, SIZES)['frames'][0]
        frame = cls.world['frames'][0][1]
        cls.cell = tuple(frame['cell'])
        cls.chunks = [c['index'] for c in cls.world['frames'][0][2]]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_every_chunk_copy_counts(self):
        extra = {k: 1000 for k in self.chunks}
        f = heap.ring_peak(self.world, SIZES, chunk_extra={self.cell: extra})['frames'][0]
        self.assertEqual(f['peak_bytes'], self.base['peak_bytes'] + 1000 * f['ring_chunks'])
        self.assertEqual(f['streamed_bytes'], 1000 * len(self.chunks))

    def test_a_shared_model_counts_once_per_ring(self):
        shared = {k: {'progs/a.spr': 1000} for k in self.chunks}
        f = heap.ring_peak(self.world, SIZES, chunk_models={self.cell: shared})['frames'][0]
        self.assertEqual(f['peak_bytes'], self.base['peak_bytes'] + 1000)
        self.assertEqual(f['load_ring']['peak_bytes'], self.base['load_ring']['peak_bytes'] + 1000)

    def test_the_whole_map_zone_is_the_budget(self):
        r = heap.ring_peak(self.world, SIZES, zone_bytes={self.cell: 4096 * 1024})
        f = r['frames'][0]
        self.assertEqual(f['zone_bytes'], 4096 * 1024)
        self.assertEqual(f['budget_bytes'], 4096 * 1024 - heap.POOL_SLOTS * r['pool_kib'] * 1024)
        # never more than the zone the engine is built with
        big = heap.ring_peak(self.world, SIZES, zone_bytes={self.cell: 10 ** 9})
        self.assertEqual(big['frames'][0]['zone_bytes'], big['zone_kib'] * 1024)

    def test_streamed_models_per_chunk(self):
        root = Path(self.tmp.name) / 'id1'
        (root / 'progs').mkdir(parents=True, exist_ok=True)
        (root / 'progs/a.spr').write_bytes(bytes(100))
        (root / 'progs/b.spr').write_bytes(bytes(40))
        rows = [{'classname': 'worldspawn'},
                {'classname': 'aw_flora', 'model': 'progs/a.spr', '_chim_chunk': '3'},
                {'classname': 'aw_flora', 'model': 'progs/a.spr', '_chim_chunk': '3'},
                {'classname': 'aw_flora', 'model': 'progs/b.spr', '_chim_chunk': '3'},
                {'classname': 'aw_flora', 'model': 'progs/a.spr', '_chim_chunk': '5'},
                {'classname': 'aw_npc', 'model': 'progs/b.spr'}]
        self.assertEqual(heap.streamed_chunk_models(rows, root, SIZES),
                         {3: {'progs/a.spr': 128, 'progs/b.spr': 64}, 5: {'progs/a.spr': 128}})
        self.assertEqual(heap.streamed_chunk_bytes(rows, root, SIZES), {3: 192, 5: 128})


def load(path):
    from chim.validate import Failures, load_world
    fails = Failures()
    settings, files, disk, textures, models, frames = load_world(path, fails)
    assert not fails, fails
    return {'settings': settings, 'textures': textures, 'models': models, 'frames': frames}


class ZoneConstantTests(unittest.TestCase):
    def test_the_budget_is_the_engines_chunk_room(self):
        # one source: the engine's cvar defaults through tools/engine_limits.chim_memory
        from engine_limits import chim_memory
        memory = chim_memory()
        world = {'settings': {'draw_distance': 540.0, 'hysteresis': 96.0}, 'models': [], 'textures': [], 'frames': []}
        r = heap.ring_peak(world, SIZES)
        self.assertEqual((r['zone_kib'], r['pool_kib']), (memory['zone_kib'], memory['pool_kib']))
        self.assertEqual(memory['zone_kib'] - heap.POOL_SLOTS * memory['pool_kib'], memory['chunk_room_kib'])


class LoadRingTests(unittest.TestCase):
    """CHIM-CHUNK-LOAD-FAIL-33: chunks stay locked out to the load radius; the gate reports that ring and
    the largest single block, and gates on it when the engine states that policy."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        fixture(Path(cls.tmp.name))
        cls.fails, cls.world = validate(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_load_ring_holds_at_least_the_active_ring(self):
        f = heap.ring_peak(self.world, SIZES, zone_kib=6864, pool_kib=384)['frames'][0]
        self.assertGreaterEqual(f['load_ring']['peak_bytes'], f['peak_bytes'])
        self.assertGreater(f['largest_block_bytes'], 0)
        self.assertEqual(f['gated_ring'], 'active')

    def test_the_engines_stated_policy_decides_which_ring_is_gated(self):
        from unittest import mock
        f = heap.ring_peak(self.world, SIZES, zone_kib=6864, pool_kib=384)['frames'][0]
        zone = (f['load_ring']['peak_bytes'] + f['peak_bytes']) // 2 // 1024 + 2 * 384
        with mock.patch.object(heap, 'engine_memory', return_value={'zone_kib': zone, 'pool_kib': 384,
                                                                    'locked_ring': 'load'}):
            r = heap.ring_peak(self.world, SIZES)
        if f['load_ring']['peak_bytes'] > f['peak_bytes'] + 2048:
            self.assertFalse(r['ok'])
        self.assertEqual(r['gated_ring'], 'load')


if __name__ == '__main__':
    unittest.main()
