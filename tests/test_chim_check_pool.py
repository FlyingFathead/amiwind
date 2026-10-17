# SPDX-License-Identifier: GPL-3.0-only
"""The CHIM final checks on one worker pool (BUILD-CHIM-STAGE-SERIAL-TAIL-36, fixlist B1-B4): validation (its
whole-world cross-checks split into frame units), the heap gate (big-frame slices and small frames in one map,
largest first) and the zone walk give byte for byte the reports of the previous method (one process, or a pool
per map), and every frame gets its progress line. Synthetic data only (test_chim_frames' two-frame world)."""
import contextlib
import copy
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import build_parallel  # noqa: E402
from build_parallel import stage_pool  # noqa: E402
from chim import heap, variant_audit, zone_sim  # noqa: E402
from chim.validate import Failures, load_world, report_text, report_world, validate  # noqa: E402
from chim.world import build_frames  # noqa: E402
from test_chim_frames import frame_specs  # noqa: E402
from test_chim_heap import SIZES  # noqa: E402

COMPILER = os.environ.get('CC') or shutil.which('cc') or shutil.which('gcc')


def plain(value):
    """value as JSON-able data: tuple keys as text, sets sorted, numpy scalars as numbers."""
    if isinstance(value, dict):
        return {repr(k) if not isinstance(k, str) else k: plain(v) for k, v in value.items()}
    if isinstance(value, (set, frozenset)):
        return sorted(plain(v) for v in value)
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    return value.item() if hasattr(value, 'item') else value


def sha(value):
    return hashlib.sha256(json.dumps(plain(value), sort_keys=True).encode()).hexdigest()


def quiet():
    return contextlib.redirect_stdout(io.StringIO())


class CheckPoolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        a, b, sections = frame_specs(cls.tmp.name)
        cls.out = Path(cls.tmp.name) / 'two'
        with quiet():
            build_frames(cls.out, [a, b], {'grain': 256, 'sector_chunks': 2})
        cls.source = {'areas': ['west', 'east'], 'frames': sections}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def both_ways(self, source):
        """(serial report text, pool report text, serial world, pool world, pool stderr)."""
        serial, sworld, _ = report_world(self.out, source, jobs=1, cross_checks='serial')
        err = io.StringIO()
        with quiet(), contextlib.redirect_stderr(err), stage_pool(2, 'test'):
            pooled, pworld, _ = report_world(self.out, source, jobs=2, cross_checks='pool')
        return report_text(serial), report_text(pooled), sworld, pworld, err.getvalue()

    def test_validation_report_is_byte_identical(self):
        serial, pooled, sworld, pworld, err = self.both_ways(self.source)
        self.assertEqual(hashlib.sha256(serial.encode()).hexdigest(), hashlib.sha256(pooled.encode()).hexdigest())
        self.assertTrue(json.loads(serial)['ok'])
        for key in ('leaf_counts', 'chunk_counts', 'seam_samples', 'variant_audit'):
            self.assertEqual(sha(sworld[key]), sha(pworld[key]), key)
        self.assertEqual(sha([{k: v for k, v in f.items() if k != 'trees'} for f in sworld['visibility']]),
                         sha([{k: v for k, v in f.items() if k != 'trees'} for f in pworld['visibility']]))
        # one progress line per frame (fixlist B2): [done/total frames] CHIM validation: <frame file>: N failures
        lines = [x for x in err.splitlines() if 'CHIM validation:' in x]
        self.assertEqual(len(lines), 2)
        self.assertRegex(lines[0], r'^\[1/2 frames\] CHIM validation: frames/[^:]+/frame\.ccf: 0 failures$')
        self.assertTrue(lines[1].startswith('[2/2 frames] CHIM validation: '))

    def test_chim_build_offers_both_pool_methods(self):
        # the step's pool option: stage (default) and batch (the previous method); the script must run at all
        import subprocess
        out = subprocess.run([sys.executable, str(ROOT / 'tools/chim_build.py'), '--help'], capture_output=True,
                             text=True, env=dict(os.environ, PYTHONPATH=str(ROOT / 'src') + os.pathsep + str(ROOT / 'tools')))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn('--pool {stage,batch}', out.stdout)

    def test_big_frames_split_into_chunk_runs_give_the_same_report(self):
        import chim.validate as V
        serial, _, _ = report_world(self.out, self.source, jobs=1, cross_checks='serial')
        with patch.object(V, 'CHUNK_GROUP', 3), quiet(), contextlib.redirect_stderr(io.StringIO()), \
                stage_pool(2, 'test') as pool:
            pooled, _, _ = report_world(self.out, self.source, jobs=2, cross_checks='pool')
            tasks = pool.summary()['tasks']
        self.assertEqual(report_text(pooled), report_text(serial))
        self.assertGreater(tasks, 10)          # the frames' chunks went out in runs of three

    def test_failures_keep_their_order_and_frame_names(self):
        # a source whose story-hidden list and placements disagree with the files: the cross-checks fail in both
        # frames, and the failure list (order, frame names) is the same both ways
        source = copy.deepcopy(self.source)
        for s in source['frames']:
            s['story_hidden'] = [r['ref'] for r in s['placements'][:2]]
        source['frames'][1]['placements'] = source['frames'][1]['placements'][1:]
        fails_serial, _ = validate(self.out, source, jobs=1, cross_checks='serial')
        with quiet(), contextlib.redirect_stderr(io.StringIO()), stage_pool(2, 'test'):
            fails_pool, _ = validate(self.out, source, jobs=2, cross_checks='pool')
        self.assertGreater(len(fails_serial), 3)
        self.assertEqual(list(fails_pool), list(fails_serial))
        self.assertTrue(any('story-hidden' in f and 'area east' in f for f in fails_serial))
        self.assertTrue(any('story-hidden' in f and 'area west' in f for f in fails_serial))
        with self.assertRaises(ValueError):
            validate(self.out, source, cross_checks='other')

    def test_variant_audit_in_runs_is_the_same_report(self):
        fails = Failures()
        models = load_world(self.out, fails)[4]
        rows = [{'name': m['name'], 'image': m['image']} for m in models]
        whole = variant_audit.audit_models(rows, set())
        with patch.object(variant_audit, 'AUDIT_GROUP_BYTES', 1), quiet(), stage_pool(2, 'test'):
            runs = variant_audit.audit_models(rows, set(), jobs=2)
        self.assertEqual(sha(runs), sha(whole))

    def heap_world(self):
        fails = Failures()
        settings, _, _, textures, models, frames = load_world(self.out, fails)
        return {'settings': settings, 'textures': textures, 'models': models, 'frames': frames}

    def test_heap_gate_one_map_largest_first_same_report(self):
        world = self.heap_world()
        serial = heap.ring_peak(world, SIZES)
        batch = heap.ring_peak(world, SIZES, jobs=2)
        out = io.StringIO()
        with patch.object(heap, 'BIG_FRAME_POSITIONS', 40), patch.object(heap, 'SCAN_BATCH', 7):
            with contextlib.redirect_stdout(out), stage_pool(3, 'test'):
                pooled = heap.ring_peak(world, SIZES, jobs=3)
        self.assertEqual(sha(pooled), sha(serial))
        self.assertEqual(sha(batch), sha(serial))
        lines = [x for x in out.getvalue().splitlines() if 'CHIM heap gate:' in x]
        self.assertEqual(len(lines), 2)                   # one per frame, as it is done
        self.assertRegex(lines[-1], r'^\[2/2 frames\] CHIM heap gate: frames/.+: active ring peak \d+ of \d+ bytes$')

    def test_heap_units_are_submitted_largest_first(self):
        world = self.heap_world()
        seen = []

        def recording(function, items, jobs=None):
            items = list(items)
            seen.extend(items)
            return map(function, items)
        with patch.object(heap, 'BIG_FRAME_POSITIONS', 40), patch.object(heap, 'SCAN_BATCH', 7), \
                patch.object(build_parallel, 'active_stage_pool', return_value=object()), \
                patch.object(build_parallel, 'completed_map', side_effect=recording), quiet():
            heap.ring_peak(world, SIZES, jobs=3)

        def cost(u):
            if u[0] == 'slice':
                return (u[3][2] - u[3][1]) * max(1, len(u[3][0]['own']))
            return heap._frame_positions(u[3]) * max(1, len(u[3]['chunks']))
        self.assertGreater(len(seen), 2)
        costs = [cost(u) for u in seen]
        self.assertEqual(costs, sorted(costs, reverse=True))

    def test_gates_on_the_validated_world_write_the_same_reports(self):
        # the heap gate and the stair gate read the world the validation read instead of the files again
        from chim.collision import require_stairs
        fails, world = validate(self.out, self.source)
        self.assertEqual(list(fails), [])
        with tempfile.TemporaryDirectory() as tmp:
            reports = {}
            for name, shared in (('files', None), ('validated', world)):
                with quiet():
                    heap.require_heap(self.out, sizes=SIZES, report_path=Path(tmp) / ('heap-' + name), world=shared)
                    require_stairs(self.out, report_path=Path(tmp) / ('stairs-' + name), world=shared)
                reports[name] = [hashlib.sha256((Path(tmp) / (k + '-' + name)).read_bytes()).hexdigest()
                                 for k in ('heap', 'stairs')]
        self.assertEqual(reports['validated'], reports['files'])

    @unittest.skipIf(os.name == 'nt', 'the zone library is built and loaded on Linux, including the Docker gate')
    @unittest.skipUnless(COMPILER, 'install a host C compiler')
    def test_zone_walk_same_report_with_progress_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            first, second = Path(tmp) / 'serial.json', Path(tmp) / 'pool.json'
            with quiet():
                zone_sim.require_zone_walk(self.out, sizes=SIZES, report_path=first, spacing=64.0, step=16.0)
            out = io.StringIO()
            fails, world = validate(self.out, self.source)
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()), stage_pool(2, 'test'):
                zone_sim.require_zone_walk(self.out, sizes=SIZES, report_path=second, spacing=64.0, step=16.0,
                                           jobs=2, world=world)
            self.assertEqual(hashlib.sha256(first.read_bytes()).hexdigest(),
                             hashlib.sha256(second.read_bytes()).hexdigest())
        lines = [x for x in out.getvalue().splitlines() if 'CHIM zone walk gate:' in x]
        self.assertEqual(len(lines), 2)
        self.assertRegex(lines[0], r'^\[1/2 frames\] CHIM zone walk gate: frames/.+ lawnmower: \d+ steps, 0 without '
                                   r'ground$')


if __name__ == '__main__':
    unittest.main()
