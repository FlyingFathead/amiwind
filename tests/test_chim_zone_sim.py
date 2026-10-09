# SPDX-License-Identifier: GPL-3.0-only
"""The CHIM zone walk gate (chim.zone_sim): the engine's own zone allocator, built for the host,
driven by the ring rules over walks through a CHIM world (CHIM-CHUNK-LOAD-FAIL-33).

Synthetic world (test_chim_format.fixture) and fixed ABI sizes (test_chim_heap.SIZES)."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import heap, zone_sim  # noqa: E402
from chim.validate import Failures, load_world  # noqa: E402
from test_chim_format import fixture  # noqa: E402
from test_chim_heap import SIZES  # noqa: E402

COMPILER = os.environ.get('CC') or shutil.which('cc') or shutil.which('gcc')


@unittest.skipIf(os.name == 'nt', 'the zone library is built and loaded on Linux, including the Docker gate')
@unittest.skipUnless(COMPILER, 'install a host C compiler')
class ChimZoneWalkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        fixture(Path(cls.tmp.name))
        fails = Failures()
        settings, files, disk, textures, models, frames = load_world(cls.tmp.name, fails)
        assert not fails, fails
        cls.world = {'settings': settings, 'textures': textures, 'models': models, 'frames': frames}
        cls.lib = zone_sim.build_library(Path(cls.tmp.name) / 'lib')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def walk(self, zone_kib, release=1, partial=1):
        blocks = zone_sim.block_sizes(self.world, SIZES)
        frame = self.world['frames'][0][1]
        memory = dict(heap.engine_memory(), zone_kib=zone_kib, pool_kib=16)
        route = [('lawnmower', 0, zone_sim.lawnmower(frame, spacing=frame['grain'], step=8.0, margin=frame['grain'] / 2))]
        return zone_sim.walk(self.lib, memory, self.world, blocks, route, release=release,
                             partial=partial)['lawnmower']

    def test_ample_zone_walks_without_holes_or_failures(self):
        r = self.walk(4096)
        self.assertGreater(r['steps'], 10)
        self.assertEqual((r['holes'], r['zone_fail'], r['data_fail'], r['released_ring']), (0, 0, 0, 0))
        self.assertGreater(r['chunk_loads'], 0)
        self.assertGreater(r['model_loads'], 0)

    def test_gate_writes_its_report_and_passes(self):
        report = zone_sim.require_zone_walk(self.tmp.name, sizes=SIZES, spacing=64.0, step=16.0)
        self.assertEqual(report['status'], 'passed')
        saved = json.loads((Path(self.tmp.name) / 'chim-zone-walk.json').read_text())
        self.assertTrue(saved['ok'])
        self.assertEqual(saved['zone_kib'], heap.engine_memory()['zone_kib'])
        self.assertIn('chim_zone.c', saved['method'])

    def test_gate_builds_its_library_under_the_output_folder_not_tmp(self):
        # CHIM-ZONE-TMP-NOEXEC-33 / BUILD-TMP-SCRATCH-33: /tmp may be mounted noexec (Docker --tmpfs); the
        # shared object is built and loaded under OUT/work (or the run's scratch) and removed afterwards.
        from unittest import mock
        seen = []
        real = zone_sim.build_library

        def spy(folder, *args, **kwargs):
            seen.append(Path(folder))
            return real(folder, *args, **kwargs)
        work = Path(self.tmp.name) / 'work'
        with mock.patch.dict(os.environ), mock.patch.object(zone_sim, 'build_library', side_effect=spy):
            os.environ.pop('AMIWIND_SCRATCH', None)
            zone_sim.require_zone_walk(self.tmp.name, sizes=SIZES, spacing=64.0, step=16.0)
        self.assertEqual(len(seen), 1)
        self.assertIn(work, seen[0].parents)
        self.assertEqual(list(work.rglob('amiwind-zone-*')), [])

    def test_gate_follows_the_run_scratch_folder(self):
        from unittest import mock
        seen = []
        real = zone_sim.build_library
        run_scratch = Path(self.tmp.name) / 'run-scratch'

        def spy(folder, *args, **kwargs):
            seen.append(Path(folder))
            return real(folder, *args, **kwargs)
        with mock.patch.dict(os.environ, {'AMIWIND_SCRATCH': str(run_scratch)}),                 mock.patch.object(zone_sim, 'build_library', side_effect=spy):
            zone_sim.require_zone_walk(self.tmp.name, sizes=SIZES, spacing=64.0, step=16.0)
        self.assertEqual([p.parent for p in seen], [run_scratch])

    def test_without_sizes_the_gate_says_it_did_not_run(self):
        self.assertIsNone(zone_sim.require_zone_walk(self.tmp.name)['ok'])

    def test_zone_library_is_the_engine_source(self):
        # One implementation: the gate compiles engine/aga/src/chim/chim_zone.c, never a copy.
        self.assertEqual(zone_sim.SRC, ROOT / 'engine/aga/src')
        self.assertTrue((zone_sim.SRC / 'chim/chim_zone.c').is_file())
        self.assertIn("'chim/chim_zone.c'", (ROOT / 'tools/chim/zone_sim.py').read_text())


if __name__ == '__main__':
    unittest.main()
