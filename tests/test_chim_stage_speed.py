# SPDX-License-Identifier: GPL-3.0-only
"""The chim stage's checks on the shared worker pool and the hashed pool (BUILD-CHIM-STAGE-SERIAL-TAIL-36,
CHIM-STAIR-GATE-WORLD-RELOAD-36): the same results with 1 worker and with several, a frame read from its own files
equal to the whole-world read, and a rerun with nothing changed recomputes no unit. Synthetic data only."""
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim.validate import Failures, load_frame, load_world, validate  # noqa: E402
from chim.world import build_frames  # noqa: E402
from test_chim_frames import frame_specs  # noqa: E402


def digest(value):
    """SHA-256 of a validation result (numpy arrays as lists), for byte-level comparison."""
    def plain(v):
        if hasattr(v, 'tolist'):
            return v.tolist()
        if isinstance(v, dict):
            return {str(k): plain(x) for k, x in v.items()}
        if isinstance(v, (list, tuple, set)):
            items = [plain(x) for x in v]
            return sorted(items, key=repr) if isinstance(v, set) else items
        if isinstance(v, (bytes, bytearray)):
            return hashlib.sha256(v).hexdigest()
        return v
    return hashlib.sha256(json.dumps(plain(value), sort_keys=True, default=str).encode()).hexdigest()


class ChimStageSpeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        a, b, sections = frame_specs(cls.tmp.name)
        cls.spec, cls.section = a, sections[0]
        cls.out = Path(cls.tmp.name) / 'two'
        build_frames(cls.out, [a, b], {'grain': 256, 'sector_chunks': 2})
        cls.source = {'areas': ['west', 'east'], 'frames': sections}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_a_frame_read_from_its_own_files_equals_the_whole_world_read(self):
        _, _, _, _, models, frames = load_world(self.out, Failures())
        self.assertEqual(len(frames), 2)
        for fi, row in enumerate(frames):
            own, own_models = load_frame(self.out, fi)
            self.assertEqual(own[0], row[0])
            self.assertEqual(own[1], row[1])
            self.assertEqual(own[2], row[2])
            used = {r['model'] for c in row[2] for r in c['owned'] + c['reach']}
            self.assertEqual(set(own_models), used)
            for i in used:
                self.assertEqual(own_models[i], models[i])

    def test_validation_with_several_workers_equals_one_worker(self):
        with patch.dict(os.environ, {'AMIWIND_PASS_CACHE': 'off'}):
            serial = validate(self.out, self.source, jobs=1)
            pooled = validate(self.out, self.source, jobs=3)
        self.assertEqual(list(serial[0]), [])
        self.assertEqual(list(serial[0]), list(pooled[0]))
        self.assertEqual(digest(serial[1]), digest(pooled[1]))

    def test_a_rerun_with_nothing_changed_recomputes_no_validation_unit(self):
        from pass_cache import PassCache
        with tempfile.TemporaryDirectory() as cache, patch.dict(os.environ, {'AMIWIND_PASS_CACHE': cache}):
            first = validate(self.out, self.source, jobs=2)
            counts = []
            real = PassCache.summary

            def summary(self):
                counts.append(real(self))
                return counts[-1]
            with patch.object(PassCache, 'summary', summary):
                again = validate(self.out, self.source, jobs=2)
        self.assertEqual(counts[-1]['misses'], 0, counts)
        self.assertGreater(counts[-1]['hits'], 0, counts)
        self.assertEqual(list(first[0]), list(again[0]))
        self.assertEqual(digest(first[1]), digest(again[1]))

    def test_stair_gate_with_several_workers_equals_one_worker(self):
        from chim.collision import stair_gate
        _, _, _, _, models, frames = load_world(self.out, Failures())
        with patch.dict(os.environ, {'AMIWIND_PASS_CACHE': 'off'}):
            one = stair_gate(self.out, frames, 1, models=models)
            two = stair_gate(self.out, frames, 2, models=models)
        self.assertEqual(json.dumps(one, sort_keys=True, default=str), json.dumps(two, sort_keys=True, default=str))

    def test_stair_workers_never_read_the_whole_world(self):
        import chim.collision as collision
        import stair_progress
        frames = load_world(self.out, Failures())[5]
        collision._STAIR_CACHE.clear()
        with patch('chim.validate.load_world', side_effect=AssertionError('whole world read in a worker')):
            for task in collision.stair_tasks(self.out, frames)[:3]:
                collision.stair_task(task)
            stair_progress.chim_count_task((str(self.out), 0, [collision.stair_tasks(self.out, frames)[0][2]]))
        collision._STAIR_CACHE.clear()

    def test_zone_walk_on_the_pool_and_reused_by_hash(self):
        from chim import zone_sim
        from pass_cache import PassCache
        from test_chim_heap import SIZES
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'AMIWIND_PASS_CACHE': 'off'}):
            serial = zone_sim.require_zone_walk(self.out, sizes=SIZES, spacing=64.0, step=16.0,
                                                report_path=Path(tmp) / 'a.json')
            pooled = zone_sim.require_zone_walk(self.out, sizes=SIZES, spacing=64.0, step=16.0, jobs=2,
                                                report_path=Path(tmp) / 'b.json')
            self.assertEqual((Path(tmp) / 'a.json').read_bytes(), (Path(tmp) / 'b.json').read_bytes())
            self.assertEqual(serial['ok'], pooled['ok'])
        with tempfile.TemporaryDirectory() as cache, tempfile.TemporaryDirectory() as tmp,                 patch.dict(os.environ, {'AMIWIND_PASS_CACHE': cache}):
            zone_sim.require_zone_walk(self.out, sizes=SIZES, spacing=64.0, step=16.0, jobs=2,
                                       report_path=Path(tmp) / 'c.json')
            counts = []
            real = PassCache.summary

            def summary(self):
                counts.append(real(self))
                return counts[-1]
            with patch.object(PassCache, 'summary', summary):
                zone_sim.require_zone_walk(self.out, sizes=SIZES, spacing=64.0, step=16.0, jobs=2,
                                           report_path=Path(tmp) / 'd.json')
            self.assertEqual(counts[-1]['misses'], 0, counts)
            self.assertEqual(counts[-1]['hits'], 2, counts)
            self.assertEqual((Path(tmp) / 'c.json').read_bytes(), (Path(tmp) / 'd.json').read_bytes())

    def test_early_frame_checks_are_reused_by_hash(self):
        import chim.validate as V
        with tempfile.TemporaryDirectory() as cache, patch.dict(os.environ, {'AMIWIND_PASS_CACHE': cache}):
            first = V.early_frame_failures(self.spec, self.section, 'west', 1)
            with patch.object(V, '_early_chunks', side_effect=AssertionError('checked again')):
                again = V.early_frame_failures(self.spec, self.section, 'west', 1)
            changed = dict(self.section, water_level=self.section['water_level'] + 1)
            with patch.object(V, '_early_chunks', side_effect=RuntimeError('ran')):
                with self.assertRaises(RuntimeError):
                    V.early_frame_failures(self.spec, changed, 'west', 1)
        self.assertEqual(first, again)

    def test_the_heap_gate_runs_on_the_shared_pool(self):
        source = (ROOT / 'tools' / 'chim' / 'heap.py').read_text(encoding='utf-8')
        self.assertNotIn('ProcessPoolExecutor', source)
        self.assertIn('ordered_map', source)

    def test_the_stage_passes_its_workers_to_the_validation(self):
        source = (ROOT / 'tools' / 'chim_build.py').read_text(encoding='utf-8')
        self.assertIn('report_world(', source)
        self.assertEqual(source.count('jobs=resolve_jobs(a.jobs)'), 3)


if __name__ == '__main__':
    unittest.main()
