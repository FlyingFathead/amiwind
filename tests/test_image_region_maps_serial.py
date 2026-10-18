# SPDX-License-Identifier: GPL-3.0-only
"""BUILD-IMAGE-REGION-MAPS-SERIAL-43: the image step's CHIM frame-map phases off one core.

The CHIM world is read once for the whole image step (the entity tracker's placements, the frame maps and the
frame-map heap gate share it), the region frame maps' door bank rows are made on the worker pool beside the maps,
and the region pass cache is keyed by the code of BOTH row methods (game data and legacy). Synthetic data."""
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


class WorldReadOnce(unittest.TestCase):
    def test_chim_world_once_reads_the_world_once(self):
        import build_aga
        calls = []
        world = {'frames': [], 'models': []}
        with mock.patch('chim.frame_map.load', side_effect=lambda path: calls.append(path) or world):
            held = {}
            self.assertIs(build_aga.chim_world_once('w', held), world)
            self.assertIs(build_aga.chim_world_once('w', held), world)
            self.assertIsNone(build_aga.chim_world_once(None, {}))
        self.assertEqual(calls, ['w'])

    def test_the_placements_take_the_world_given(self):
        import build_aga
        world = {'frames': [], 'models': []}
        args = SimpleNamespace(chim_world='w', chim_town=None)
        with mock.patch('chim.frame_map.load', side_effect=AssertionError('read again')), \
                mock.patch('chim.frame_map.region_map_names', return_value={'vf0001': (1, 2)}):
            with tempfile.TemporaryDirectory() as tmp:
                self.assertEqual(build_aga.chim_region_placements(args, Path(tmp), world=world), {'vf0001': set()})

    def test_the_heap_gate_takes_the_world_given(self):
        from chim import heap
        world = {'settings': {}, 'textures': [], 'models': [], 'frames': []}
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'maps').mkdir()
            with mock.patch('chim.validate.load_world', side_effect=AssertionError('read again')), \
                    mock.patch('engine_limits.chim_memory', return_value={'heap_mb': 24}):
                self.assertEqual(heap.frame_map_heap('w', tmp, {'hunk': 16}, world=world), {})

    def test_the_image_step_reads_the_world_once_and_hands_it_on(self):
        source = (ROOT / 'tools' / 'build_aga.py').read_text(encoding='utf-8')
        start = source.index("chim_world_data = chim_world_once(getattr(args, 'chim_world', None), chim_world_held)")
        self.assertLess(start, source.index('entity_tracker = entity_gate('))
        for call in ("chim_town_placements(args, boot/'id1', world=chim_world_data)",
                     "chim_region_placements(args, boot/'id1', world=chim_world_data)"):
            self.assertIn(call, source)
        frames = source.index("chim_frames = chim_frame_maps(args.chim_world, boot/'id1'")
        heap = source.index('frame_heap = require_frame_map_heap(')
        self.assertIn('world=chim_world_data', source[frames:source.index(')', source.index('keep_catalogues', frames)) + 40])
        self.assertIn('world=chim_world_data', source[heap:source.index('for name, m in sorted(frame_heap', heap)])


class RegionPool(unittest.TestCase):
    def test_the_pool_worker_makes_the_door_rows(self):
        from chim import frame_map as FM
        task = {'world_dir': '/w', 'frame': {'id': 'f'}, 'placed': [5]}
        with mock.patch.object(FM, 'region_map', return_value=(b'map', {'r': 1}, False)), \
                mock.patch.object(FM, 'region_door_rows', side_effect=lambda w, f, rooms, placed:
                                  [(w, f['id'], rooms, placed)]) as rows:
            self.assertEqual(FM.region_unit(task), (b'map', {'r': 1}, False, [('/w', 'f', None, [5])]))
            self.assertEqual(FM.region_unit(dict(task, rooms={'x': 1}))[3], [('/w', 'f', {'x': 1}, [5])])
        self.assertEqual(rows.call_count, 2)

    def test_the_region_cache_key_reaches_both_row_methods(self):
        # until v0.0.43-dev2 it named _region_map (legacy rows) only: an edit of the default game-data method
        # kept stale frame maps in the pass cache
        import pass_cache
        from build_cache import SourceIndex
        from chim import frame_map as FM
        opened = []
        with mock.patch.object(pass_cache.PassCache, 'open', side_effect=lambda *a: opened.append(a)):
            FM.region_cache()
        script = Path(FM.__file__).resolve()
        self.assertEqual(opened, [(FM.REGION_CACHE, {}, (FM.__file__, '_region_frame_map'))])
        index = SourceIndex(ROOT, top_format=pass_cache.PASS_KEY_FORM)
        index.entry_digest(script, '_region_frame_map', pass_cache.PASS_KEY_NEUTRAL)
        reached = index._reached.get('%s::%s' % (script, '_region_frame_map'))
        if reached is None:
            self.skipTest('source index scope without units')
        units = set(reached['tools/chim/frame_map.py'])
        for unit in ('_region_map', '_region_map_game_data', 'static_check', 'native_activated_check',
                     'stream_statics', 'hunk_rest'):
            self.assertIn(unit, units)


if __name__ == '__main__':
    unittest.main()
