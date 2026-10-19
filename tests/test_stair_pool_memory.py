# SPDX-License-Identifier: GPL-3.0-only
"""The stair gate's workers fit the container (CHIM-STAIR-GATE-POOL-BROKEN-42).

Two Vivec palace MiniWind runs died in the CHIM stair gate with a bare BrokenProcessPool: each walk worker reads the
whole Vivec frame (about 2.6 GiB), 11 workers were asked, and in the step's 24-worker stage pool 22 walks ran at once.
Now (1) a map in a larger shared pool keeps to the tasks it asked for (build_parallel.completed_map), (2) the gate
sizes its workers by the container's own memory as well as by cores (chim.stair_pool), and a worker lets go of the
frames it keeps built so it never holds more than the largest frame it walks, and (3) a killed worker stops the gate
with the units, frames and memory named. None of this is part of the walker's key."""
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import collision, stair_pool  # noqa: E402

GIB = 1 << 30


def _sleep_and_count(task):
    """Worker: record that it runs (a file per running task) and how many ran at once."""
    folder, i = task
    me = Path(folder) / ('run-%d' % i)
    me.write_text('x')
    time.sleep(.4)
    running = len(list(Path(folder).glob('run-*')))
    me.unlink()
    return running


class Sizing(unittest.TestCase):
    def test_memory_bounds_the_workers(self):
        n, note = stair_pool.memory_workers(11, 2650., room=(12 * GIB, 'test 12 GiB'))
        self.assertEqual(n, 3)                     # 12 GiB x 0.8 / 2.65 GiB
        self.assertIn('by memory', note)
        n, note = stair_pool.memory_workers(11, 300., room=(12 * GIB, 'test'))
        self.assertEqual(n, 11)
        self.assertIn('by cores', note)
        self.assertEqual(stair_pool.memory_workers(8, 99999., room=(GIB, 'test'))[0], 1)
        self.assertEqual(stair_pool.memory_workers(8, 500., room=(None, 'unknown'))[0], 8)

    def test_the_estimate_follows_the_placed_bytes(self):
        image = b'x' * (1 << 20)
        row = ('p', {}, [{'image': image, 'owned': [{'model': 0}, {'model': 0}, {'model': 1}]}])
        models = [{'image': image}, {'image': b''}]
        self.assertAlmostEqual(stair_pool.frame_walk_mib(row, models),
                               stair_pool.WORKER_BASE_MIB + 3 * stair_pool.WORKER_MIB_PER_PLACED_MIB)
        # measured: whole-city Vivec, 150 MiB placed, a worker peaked at 2,643 MiB
        self.assertGreater(stair_pool.WORKER_BASE_MIB + 150 * stair_pool.WORKER_MIB_PER_PLACED_MIB, 2643)

    def test_the_container_limit_is_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'max').write_text('%d\n' % (16 * GIB))
            (Path(tmp) / 'cur').write_text('%d\n' % (4 * GIB))
            real = stair_pool._read_int
            paths = {'/sys/fs/cgroup/memory.max': str(Path(tmp) / 'max'),
                     '/sys/fs/cgroup/memory.current': str(Path(tmp) / 'cur')}
            with patch.object(stair_pool, '_read_int', lambda p: real(paths.get(p, p))), \
                    patch.object(stair_pool, '_inactive_file', lambda p: 0):
                free, note = stair_pool.memory_room()
            self.assertEqual(free, 12 * GIB)
            self.assertIn('cgroup v2', note)

    def test_a_worker_keeps_no_more_than_its_share(self):
        collision._STAIR_CACHE.clear()
        stair_pool._CACHE_MIB.clear()
        collision._STAIR_CACHE.update({('w', 1): 'a', ('w', 2): 'b'})
        stair_pool._CACHE_MIB.update({('w', 1): 900., ('w', 2): 900.})
        with patch('chim.collision.stair_unit', side_effect=lambda unit: (unit[3], [])):
            uid, rows, peak = stair_pool.stair_unit_sized((('w', 3, [], 7), 2000., 2650.))
        self.assertEqual((uid, rows), (7, []))
        self.assertEqual(list(collision._STAIR_CACHE), [])     # both let go: 900 + 900 + 2000 > 2650
        collision._STAIR_CACHE.clear()
        stair_pool._CACHE_MIB.clear()

    def test_the_pool_code_is_not_in_the_walk_key(self):
        self.assertNotIn('tools/chim/stair_pool.py', collision.STAIR_WALK_CODE)
        self.assertNotIn('tools/build_parallel.py', collision.STAIR_WALK_CODE)


class SharedPoolWindow(unittest.TestCase):
    def test_a_map_keeps_to_its_workers_in_a_larger_stage_pool(self):
        from build_parallel import completed_map, stage_pool
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop(__import__('build_parallel').ALLOWANCE_ENV, None)
                with stage_pool(6, 'test'):
                    seen = list(completed_map(_sleep_and_count, [(tmp, i) for i in range(8)], 2))
        self.assertLessEqual(max(seen), 2, seen)       # 2 asked: never 4 at once in the 6-worker pool


class NamedFailure(unittest.TestCase):
    def test_a_killed_worker_names_its_units(self):
        from concurrent.futures.process import BrokenProcessPool
        from chim.validate import Failures, load_world
        from test_chim_stairs import world_of

        import build_parallel
        real = build_parallel.completed_map

        def broken(function, items, jobs=None):
            if function is not stair_pool.stair_unit_sized:
                yield from real(function, items, 1)
                return
            raise BrokenProcessPool('A process in the process pool was terminated abruptly')
        with tempfile.TemporaryDirectory() as tmp:
            world_of(tmp, False)
            world = load_world(tmp, Failures())
            collision._STAIR_CACHE.clear()
            with patch.dict(os.environ, {'AMIWIND_STAIR_WALK_CACHE': 'full'}), \
                    patch('build_parallel.completed_map', side_effect=broken):
                with self.assertRaisesRegex(ValueError, 'walk worker was killed .* units unfinished, first frames/'):
                    collision.stair_gate(tmp, world[5], 2, models=world[4])


if __name__ == '__main__':
    unittest.main()
