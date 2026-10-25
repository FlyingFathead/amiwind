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

    def test_chunk_trees_cross_processes_packed_with_the_same_nodes(self):
        # BUILD-CHIM-STAGE-SERIAL-TAIL-36 (v0.0.51): a chunk tree goes between the processes as three arrays
        # (PackedNodes), not one array per node; it indexes, unpacks and answers box_leaves as world_tree's list
        import pickle
        from chim import format as F
        from chim.terrain import box_leaves, tree_depth
        from chim.validate import PackedNodes, _plain_tree, _tree_from_json, _tree_to_json, world_tree
        _, _, _, _, _, frames = load_world(self.out, Failures())
        trees = [world_tree(F.read_brush_image(c['image']), 'chunk', Failures()) for _, _, chunks in frames
                 for c in chunks]
        self.assertTrue(any(len(nodes) > 3 for nodes, _ in trees))
        for nodes, leaves in trees:
            packed = PackedNodes.of(nodes)
            self.assertEqual(len(packed), len(nodes))
            plain = _plain_tree((packed, leaves))[0]
            for a, b, c in zip(nodes, packed, plain):
                for x in (b, c):
                    self.assertEqual(x[0].dtype, a[0].dtype)
                    self.assertEqual(x[0].tolist(), a[0].tolist())
                    self.assertEqual(x[1:], a[1:])
            self.assertEqual(tree_depth(packed), tree_depth(nodes))
            for lo, hi in (((-4096, -4096, -4096), (4096, 4096, 4096)), ((0, 0, 0), (64, 64, 64))):
                self.assertEqual(box_leaves(packed, leaves, lo, hi), box_leaves(nodes, leaves, lo, hi))
            stored = _tree_from_json(json.loads(json.dumps(_tree_to_json((nodes, leaves)))))
            self.assertEqual(stored[0], packed)
            again = pickle.loads(pickle.dumps(packed, protocol=pickle.HIGHEST_PROTOCOL))
            self.assertEqual(again, packed)
        # smaller once a tree has more than a few nodes (the arrays' fixed header dominates a tiny one); the dev1
        # world's trees were 441 MB as per-node arrays
        nodes = max((n for n, _ in trees), key=len)
        size = lambda v: len(pickle.dumps(v, protocol=pickle.HIGHEST_PROTOCOL))   # noqa: E731
        self.assertLess(size(PackedNodes.of(nodes)), size(nodes), len(nodes))

    def test_ffs_rules_walk_equals_the_path_walk(self):
        # BUILD-CHIM-STAGE-SERIAL-TAIL-36 (v0.0.51): the os.scandir walk gives the sizes and failures (in order) of
        # the Path.rglob walk it replaced, on the fixture world and on a tree that breaks the rules
        from chim import format as F
        from chim.validate import ffs_rules

        def path_walk(root, fails):
            sizes = {}
            for d in [root, *[p for p in root.rglob('*') if p.is_dir()]]:
                entries = list(d.iterdir())
                fails.check(len(entries) <= F.FFS_MAX_DIRECTORY_ENTRIES, 'FFS: %s holds %d entries (limit %d)'
                            % (d.name, len(entries), F.FFS_MAX_DIRECTORY_ENTRIES))
                for e in entries:
                    fails.check(len(e.name) <= F.FFS_NAME_CHARS, 'FFS: name longer than 30 characters: ' + e.name)
                    fails.check(all(32 < ord(ch) < 127 and ch not in ':/' for ch in e.name), 'FFS: unsafe name '
                                + e.name)
                    if e.is_file():
                        sizes[e.relative_to(root).as_posix()] = e.stat().st_size
                        fails.check(e.stat().st_size <= F.FFS_MAX_PACK, 'FFS: %s larger than the 1 GiB pack limit'
                                    % e.name)
            return sizes
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp)
            for k in range(3):
                d = bad / ('d%d' % k) / 'inner'
                d.mkdir(parents=True)
                (d / ('f%d.bin' % k)).write_bytes(b'x' * k)
            (bad / 'd1' / ('long' * 10)).write_bytes(b'')
            (bad / 'd2' / 'odd name').write_bytes(b'12')
            with patch.object(F, 'FFS_MAX_DIRECTORY_ENTRIES', 2):
                for root in (self.out / 'chim', bad):
                    old, new = Failures(), Failures()
                    self.assertEqual(ffs_rules(root, new), path_walk(root, old))
                    self.assertEqual(list(new), list(old))
            self.assertTrue(list(old))                                 # the broken tree did fail

    def test_set_bits_equals_the_bit_by_bit_decode(self):
        # BUILD-CHIM-STAGE-SERIAL-TAIL-36 (v0.0.51): the set bits of a row as row_to_bits' True places, below n
        import random
        from chim.validate import set_bits
        from chim.visibility import row_to_bits
        rng = random.Random(51)
        for n in (0, 1, 7, 8, 9, 64, 333, 1351):
            for density in (0.0, 0.01, 0.3, 1.0):
                row = bytes(sum(1 << b for b in range(8) if rng.random() < density) for _ in range((n + 7) // 8))
                want = [k for k, b in enumerate(row_to_bits(row, n)) if b]
                self.assertEqual(set_bits(row, n), want, (n, density))
        self.assertEqual(set_bits(b'\xff', 3), [0, 1, 2])          # bits past n in the last byte are not counted

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

    def test_keyed_lookups_equal_lookups_in_the_task(self):
        # BUILD-CHIM-SERIAL-SECTIONS-44: the parent keys the units and the workers look them up; only misses get
        # their inputs. The same failures, world and hit/miss counts as each task looking itself up, on a cold cache
        # and on a warm one; on the warm one no task receives the chunk images
        import chim.validate as V
        from pass_cache import PassCache
        runs = {}
        for mode in ('in-task', 'keys'):
            counts = []
            real = PassCache.summary

            def summary(self):
                counts.append(real(self))
                return counts[-1]
            with tempfile.TemporaryDirectory() as cache, patch.dict(os.environ, {'AMIWIND_PASS_CACHE': cache,
                                                                                  V.VALIDATE_LOOKUP_ENV: mode}), \
                    patch.object(PassCache, 'summary', summary), patch.object(V, 'MODEL_GROUP', 1):
                cold = validate(self.out, self.source, jobs=2)
                sent = []
                real_map = V._pool_map

                def watched(function, tasks, jobs, cost):
                    sent.append(function.__name__)
                    return real_map(function, tasks, jobs, cost)
                with patch.object(V, '_pool_map', watched):
                    warm = validate(self.out, self.source, jobs=2)
            runs[mode] = (list(cold[0]), digest(cold[1]), list(warm[0]), digest(warm[1]),
                          [(c['hits'], c['misses']) for c in counts])
            if mode == 'keys':
                self.assertNotIn('_chunk_checks', sent)
                self.assertNotIn('_model_checks', sent)
        self.assertEqual(runs['keys'], runs['in-task'])

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
        # validation, heap gate, zone walk and (BUILD-CHIM-SERIAL-SECTIONS-44) the statistics
        self.assertEqual(source.count('jobs=resolve_jobs(a.jobs)'), 4)


if __name__ == '__main__':
    unittest.main()
