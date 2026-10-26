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

    def test_placed_model_bound_omits_only_unallocated_renderer_nodes(self):
        from chim import format as F
        lumps = F.read_brush_image(self.world['models'][0]['image'])
        nodes = len(lumps[5]) // SIZES['dnode']
        self.assertGreater(nodes, 0)
        terrain = heap.image_bytes(lumps, SIZES)
        model = heap.image_bytes(lumps, SIZES, point_hull_only=True)
        self.assertEqual(terrain-model, heap._a16(nodes*SIZES['mnode']))
        self.assertGreater(model, heap.collision_bytes(lumps, SIZES))

    def test_gate_is_strict_and_names_the_frame(self):
        # a ring over the zone even with the 32 MB minimum's cache bank holding its models and textures fails
        r = heap.ring_peak(self.world, SIZES)
        f = r['frames'][0]
        rest_kib = (f['peak_bytes'] - sum(f['peak_breakdown'].get(k, 0) for k in heap.BANKED)) // 1024
        with self.assertRaisesRegex(ValueError, 'heap gate failed'):
            heap.require_heap(self.tmp.name, sizes=SIZES, zone_kib=rest_kib + 2 * r['pool_kib'] - 1)
        report = json.loads((Path(self.tmp.name) / 'chim-heap.json').read_text())
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['frames'][0]['fast_mb'], 0)
        self.assertEqual(heap.require_heap(self.tmp.name, sizes=SIZES)['status'], 'passed')

    def test_over_or_near_the_16mb_budget_is_built_and_marked_for_32mb(self):
        """CHIM-FRAME-16MB-REFUSAL-48 (the maintainer's rule: over the budget, mark it as needing 32 MB): a frame over
        the 16 MB baseline's zone, or within FRAME_NEAR_BYTES of it, that fits the 32 MB minimum (the same zone and
        the automatic cache bank for its models and textures) passes, marked; the receipt fields count it."""
        r = heap.ring_peak(self.world, SIZES)
        f = r['frames'][0]
        need_kib = f['peak_bytes'] // 1024
        over = heap.require_heap(self.tmp.name, sizes=SIZES, zone_kib=need_kib + 2 * r['pool_kib'] - 1)
        self.assertEqual(over['status'], 'passed')
        self.assertLess(over['frames'][0]['headroom_bytes'], 0)
        self.assertEqual(over['frames'][0]['fast_mb'], 32)
        self.assertEqual(over['marked_32mb'], [f['frame']])
        self.assertEqual({k: over['fast_ram_32mb'][k] for k in ('frames', 'over_16mb', 'near_bytes')},
                         {'frames': 1, 'over_16mb': 1, 'near_bytes': heap.FRAME_NEAR_BYTES})
        self.assertEqual(over['fast_ram_32mb']['frame_records'], [f['frame']])
        near = heap.require_heap(self.tmp.name, sizes=SIZES, zone_kib=need_kib + 2 * r['pool_kib'] + 2)
        self.assertGreater(near['frames'][0]['headroom_bytes'], 0)
        self.assertLess(near['frames'][0]['headroom_bytes'], heap.FRAME_NEAR_BYTES)
        self.assertEqual((near['marked_32mb'], near['fast_ram_32mb']['over_16mb']), ([f['frame']], 0))
        roomy = heap.require_heap(self.tmp.name, sizes=SIZES)
        self.assertEqual((roomy['marked_32mb'], roomy['frames'][0]['fast_mb']), ([], 16))
        # the efrag limit is not Fast RAM: a frame over it still fails, marked or not
        from unittest import mock
        import engine_limits
        with mock.patch.object(engine_limits, 'chim_efrag_budget', return_value=0), \
                self.assertRaisesRegex(ValueError, 'efrag links'):
            heap.require_heap(self.tmp.name, sizes=SIZES, zone_kib=need_kib + 2 * r['pool_kib'] - 1)

    def test_frame_cells_and_marked_frame_maps(self):
        from chim import format as F
        from chim.frame_map import entities, entity_text
        self.assertEqual(heap.frame_cells(['frames/x-07/y-04/frame.ccf', 'frames/x+17/y+04/frame.ccf', 'other']),
                         {(-7, -4), (17, 4)})
        with tempfile.TemporaryDirectory() as tmp:
            maps = Path(tmp, 'maps')
            maps.mkdir()
            hands = {'aw_hand_%02d' % i: '0.%d' % i for i in range(80)}     # a long worldspawn, as frame maps have
            for name, cell in (('vf0001', '-7 -4'), ('vf0002', '-6 -4')):
                lumps = [b''] * 15
                lumps[0] = entity_text([dict({'classname': 'worldspawn', '_chim_frame': cell}, **hands),
                                        {'classname': 'info_player_start'}])
                (maps / (name + '.chim')).write_bytes(F.brush_image(lumps)[0])
            before = (maps / 'vf0002.chim').read_bytes()
            self.assertEqual(heap.mark_frame_maps(tmp, {(-7, -4)}), ['vf0001'])
            rows = entities((maps / 'vf0001.chim').read_bytes())
            self.assertEqual(list(rows[0])[:2], ['classname', heap.FRAME_FAST_KEY])   # first: the engine reads 1 KiB
            self.assertEqual(rows[0][heap.FRAME_FAST_KEY], '32')
            self.assertEqual({k: v for k, v in rows[0].items() if k != heap.FRAME_FAST_KEY},
                             dict({'classname': 'worldspawn', '_chim_frame': '-7 -4'}, **hands))
            self.assertEqual(rows[1], {'classname': 'info_player_start'})
            self.assertEqual((maps / 'vf0002.chim').read_bytes(), before)
            once = (maps / 'vf0001.chim').read_bytes()
            self.assertEqual(heap.mark_frame_maps(tmp, {(-7, -4)}, maps=['vf0001.chim']), ['vf0001'])
            self.assertEqual((maps / 'vf0001.chim').read_bytes(), once)                # marking twice: same bytes
            import struct
            at = struct.unpack_from('<i', once, 4)[0]                                    # the entity lump
            text = once[at:at + 1023].decode('latin-1')
            self.assertNotIn('}', text)                       # this worldspawn is longer than what the engine reads
            self.assertIn('"%s" "32"' % heap.FRAME_FAST_KEY, text)

    def test_ring_placements_are_gated_on_the_engine_efrag_budget(self):
        # CHIM-EFRAG-UNCAPPED-35: one source for the limit (engine_limits reads client.h and chim_local.h)
        from unittest import mock
        import engine_limits
        self.assertEqual(engine_limits.chim_efrag_budget(),
                         engine_limits.limits()['efrag_limit'] - engine_limits.limits()['chim_efrag_reserve'])
        f = heap.ring_peak(self.world, SIZES)['frames'][0]
        self.assertTrue(f['efrags']['ok'])
        self.assertGreater(f['efrags']['ring_placements_peak'], 0)
        self.assertEqual(f['efrags']['budget_links'], engine_limits.chim_efrag_budget())
        with mock.patch.object(engine_limits, 'chim_efrag_budget', return_value=0):
            self.assertFalse(heap.ring_peak(self.world, SIZES)['ok'])
            with self.assertRaisesRegex(ValueError, 'efrag links CHIM may use'):
                heap.require_heap(self.tmp.name, sizes=SIZES)
        self.assertEqual(heap.require_heap(self.tmp.name, sizes=SIZES)['status'], 'passed')

    def test_without_sizes_the_gate_says_it_did_not_run(self):
        self.assertIsNone(heap.require_heap(self.tmp.name)['ok'])



class OverBudgetTextTests(unittest.TestCase):
    """The gate names how far over budget each frame is (owner 2026-10-16)."""

    def test_amount_over_in_bytes_kib_and_percent(self):
        text = heap.over_budget_text({'frame': 'frames/x+17/y+05/frame.ccf', 'peak_bytes': 7463936,
                                      'budget_bytes': 6242304, 'peak_position': [1.0, 2.0]})
        self.assertIn('over by 1221632 bytes (1193 KiB, 19.6 %)', text)
        self.assertTrue(text.startswith('frames/x+17/y+05/frame.ccf needs 7463936 bytes'))


class PerFrameAuditTests(unittest.TestCase):
    """CHIM-WORLD-AUDIT-SCALING-33: ring_peak audits each frame on what it uses (its own model and texture
    numbering), in parallel and cached by content, with the same report as the whole-world form."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        fixture(Path(cls.tmp.name))
        fails, world = validate(cls.tmp.name)
        assert not fails, fails
        path, frame, chunks = world['frames'][0]
        # a second frame with half the chunks (another model set), and unused models in the world's list
        half = [c for c in chunks if (c['cx'] + c['cy']) % 2 == 0]
        second = ('frames/x+01/y+00/frame.ccf', dict(frame, cell=(1, 0)), half)
        cls.world = dict(world, frames=[world['frames'][0], second], models=world['models'] + world['models'])
        cls.cells = [(0, 0), (1, 0)]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def options(self):
        _, frame, chunks = self.world['frames'][0]
        g, (lx, ly) = frame['grain'], frame['low']
        some = [c['index'] for c in chunks[:3]]
        return {'points': [('cam', lx + g * 1.5, ly + g * 1.5), ('far', lx + g * 3.5, ly + g * 0.5)],
                'chunk_extra': {(0, 0): {some[0]: 5000}},
                'chunk_models': {(1, 0): {some[1]: {'progs/a.mdl': 7000}, some[2]: {'progs/a.mdl': 7000}}},
                'zone_bytes': {(1, 0): 5000 * 1024}}

    def test_same_report_as_the_whole_world_audit(self):
        for opts in ({}, self.options()):
            with self.subTest(options=sorted(opts)):
                whole = heap.ring_peak_whole(self.world, SIZES, **opts)
                per = heap.ring_peak(self.world, SIZES, **opts)
                # the whole-world form leaves numpy booleans in its point rows; compare as JSON
                plain = lambda r: json.loads(json.dumps(r, default=lambda o: o.item()))
                self.assertEqual(plain(per), plain(whole))
                self.assertEqual(len(per['frames']), 2)
                for f in per['frames']:
                    # what fills the worst position adds up to the peak (CHIM-TOWN-HEAP-ROUTED-HULL-36)
                    self.assertEqual(sum(f['peak_breakdown'].values()), f['peak_bytes'])

    def test_parallel_and_cached_runs_give_the_same_report(self):
        opts = self.options()
        serial = heap.ring_peak(self.world, SIZES, **opts)
        self.assertEqual(heap.ring_peak(self.world, SIZES, jobs=2, **opts), serial)
        with tempfile.TemporaryDirectory() as cache:
            first = heap.ring_peak(self.world, SIZES, cache_dir=cache, **opts)
            self.assertEqual(len(list(Path(cache).glob('*.json'))), 2)
            again = heap.ring_peak(self.world, SIZES, cache_dir=cache, **opts)
            self.assertEqual(json.loads(json.dumps(first)), json.loads(json.dumps(serial)))
            self.assertEqual(json.loads(json.dumps(again)), json.loads(json.dumps(serial)))
            # another frame setting is another key: no stale result
            other = heap.ring_peak(self.world, dict(SIZES, scenery=SIZES['scenery'] + 1000), cache_dir=cache, **opts)
            self.assertEqual(len(list(Path(cache).glob('*.json'))), 4)
            self.assertGreater(other['frames'][0]['peak_bytes'], serial['frames'][0]['peak_bytes'])

    def test_a_big_frame_split_over_the_pool_gives_the_same_report(self):
        # maintainer order 2026-10-11 10:08 (max parallelization): a big frame scans its positions in slices over the
        # shared pool; with the threshold lowered here every frame of this small world is "big": same report
        from unittest.mock import patch
        opts = self.options()
        serial = heap.ring_peak(self.world, SIZES, **opts)
        plain = lambda r: json.loads(json.dumps(r, default=lambda o: o.item()))
        with patch.object(heap, 'BIG_FRAME_POSITIONS', 1), patch.object(heap, 'SCAN_BATCH', 7):
            split = heap.ring_peak(self.world, SIZES, jobs=3, **opts)
            whole = heap.ring_peak(self.world, SIZES, jobs=1, **opts)
        self.assertEqual(plain(split), plain(serial))
        self.assertEqual(plain(whole), plain(serial))
        # slices merged in order keep the first worst position (ties included)
        task = None
        with patch.object(heap, 'SCAN_BATCH', 7):
            import numpy as np
            calls = []
            real = heap._scan

            def scan(work):
                calls.append(work[1:])
                return real(work)
            with patch.object(heap, '_scan', scan), patch.object(heap, 'BIG_FRAME_POSITIONS', 1), \
                    patch('build_parallel.ordered_map', lambda f, items, *a, **k: (f(i) for i in items)):
                task = plain(heap.ring_peak(self.world, SIZES, jobs=4, **opts))
        self.assertGreater(len(calls), 2)
        self.assertEqual(task, plain(serial))

    def test_an_unwritable_cache_never_fails_the_gate(self):
        # BUILD-CACHE-OWNER-FAILS-STAGE-34 (persisting, 2026-10-11): a read-only unit cache failed the whole-city
        # Vivec heap gate after the world was built; the gate computes and goes on, with a warning
        from unittest.mock import patch
        opts = self.options()
        serial = heap.ring_peak(self.world, SIZES, **opts)
        with tempfile.TemporaryDirectory() as cache, \
                patch.object(Path, 'write_text', side_effect=OSError(30, 'Read-only file system')), \
                patch.object(Path, 'mkdir', side_effect=OSError(30, 'Read-only file system')), \
                patch('sys.stdout'):
            again = heap.ring_peak(self.world, SIZES, cache_dir=Path(cache) / 'heap', **opts)
        self.assertEqual(json.loads(json.dumps(again)), json.loads(json.dumps(serial)))

    def test_a_frame_audit_does_not_grow_with_the_world(self):
        # the per-frame task holds only what the frame uses, however many models the world lists
        big = dict(self.world, models=self.world['models'] * 20)
        self.assertEqual(heap.ring_peak(big, SIZES), heap.ring_peak(self.world, SIZES))


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


class ImageGateMarksTests(unittest.TestCase):
    """BUILD-CHIM-HEAP-GATE-LATE-36: the image step's exact frame-map check marks a frame map over the 16 MB budget that
    fits the 32 MB minimum (as the CHIM stage marks such frames), and stops the build only for one that fits neither."""

    def frame(self, name, ok):
        return {'map': name + '.chim', 'frame': 'frames/x+01/y+02/frame.ccf', 'ok': ok, 'peak_bytes': 6251840,
                'budget_bytes': 6242304, 'gated_ring': 'active', 'load_ring': {'peak_bytes': 6251840},
                'zone_bytes': 7028736, 'heap_mb': 11, 'efrags': {'ok': True}}

    def test_over_16mb_that_fits_32mb_is_marked_not_refused(self):
        from unittest import mock
        maps = {'vf0147': self.frame('vf0147', False), 'vf0002': self.frame('vf0002', True)}
        marked = []
        with mock.patch.object(heap, 'frame_map_heap', return_value=maps), \
                mock.patch.object(heap, 'frame_fast_ram', return_value=heap.SAFE_FAST_MB), \
                mock.patch.object(heap, 'mark_frame_maps', side_effect=lambda id1, cells, maps: marked.append(
                    (sorted(cells), maps)) or ['vf0147']):
            report = heap.require_frame_map_heap('world', 'id1', sizes=SIZES, heap_mb=11)
        self.assertTrue(report['ok'])
        self.assertEqual(report['marked_32mb_late'], ['vf0147'])
        self.assertEqual(marked, [([(1, 2)], ['vf0147.chim'])])
        self.assertEqual((maps['vf0147']['fast_mb'], maps['vf0147']['marked_by_image_gate']), (heap.SAFE_FAST_MB, True))

    def test_a_frame_that_fits_neither_still_stops_the_build(self):
        from unittest import mock
        maps = {'vf0147': self.frame('vf0147', False)}
        with mock.patch.object(heap, 'frame_map_heap', return_value=maps), \
                mock.patch.object(heap, 'frame_fast_ram', return_value=0), \
                mock.patch.object(heap, 'mark_frame_maps') as mark:
            with self.assertRaisesRegex(ValueError, 'vf0147.chim needs 6251840 bytes'):
                heap.require_frame_map_heap('world', 'id1', sizes=SIZES, heap_mb=11)
        mark.assert_not_called()


if __name__ == '__main__':
    unittest.main()
