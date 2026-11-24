# SPDX-License-Identifier: GPL-3.0-only
"""A stage rebuilt from its stored units has the same outputs as the run it replaces (CHIM-REBUILD-NOT-IDENTICAL-68).

The v0.0.68-dev8 CHIM world, rebuilt from its stored units with unchanged inputs, wrote every game file byte for byte
as its source run did, but 110,543 compiled collision memos fewer (chim-world/work/AREA/collision-cache/*.pickle):
a stage writes such a content-addressed memo only for the units it computes, never for one taken from a unit cache.
Early cutoff counted them, called the outputs different and ran seven later stages again. The same on the Solstheim
module stage. Memos are left out of every comparison (build_cache.MEMO_FOLDERS, unit tree schema 2).

The stage below builds a small CHIM-like region the way the CHIM pool does: each area's frame from the unit store
when it holds it, else compiled through the collision memo of the area's work folder, then stored. It is run cold,
warm and half warm, each time in another unit order, recorded by the builder's own Recorder and compared by its own
early cutoff check.
"""
import hashlib
import json
from pathlib import Path
import random
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import build_cache  # noqa: E402
import unit_tree  # noqa: E402

STAGE = 'chim'
AREAS = {name: [[i, i + 1, i * 2 + 3], [i + 7, i % 3, 4]] for i, name in enumerate(
    ('rcm10_p4', 'rcm10_p5', 'rcm11_p4', 'rcp2_m1', 'seyda', 'balmora'))}


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def compile_hull(pieces, memo_folder):
    """A compiled hull through its content-addressed memo, as tools/collision_bsp.py keeps it: KEY.CHECK.pickle,
    KEY the SHA-256 of the compiler source; a memo found is read, else the hull is compiled and the memo written."""
    source = json.dumps(pieces, sort_keys=True).encode()
    memo = memo_folder / ('%s.%s.pickle' % (_sha(source), _sha(b'check 3')[:16]))
    if memo.is_file():
        return memo.read_bytes()
    hull = b'HULL' + hashlib.sha256(b'qbsp' + source).digest()
    memo_folder.mkdir(parents=True, exist_ok=True)
    memo.write_bytes(hull)
    return hull


def region_stage(run, store, order, noise=None):
    """Build the areas of AREAS into RUN/chim-world in ORDER, each frame from STORE (one file per unit key) when it
    holds it. NOISE: an area whose frame gets one byte more (a real difference). The cache hit counts go into a
    diagnostic, as chim-stats.json does."""
    world = run / 'chim-world'
    hits = 0
    for area in order:
        pieces = AREAS[area]
        key = _sha(json.dumps({'area': area, 'pieces': pieces}, sort_keys=True).encode())
        stored = store / key
        if stored.is_file():
            frame = stored.read_bytes()
            hits += 1
        else:
            frame = b'FRAME' + compile_hull(pieces, world / 'work' / area / 'collision-cache')
            store.mkdir(parents=True, exist_ok=True)
            stored.write_bytes(frame)
        if area == noise:
            frame += b'!'
        target = world / 'chim' / 'frames' / area / 'frame.ccf'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(frame)
        (world / 'work' / area).mkdir(parents=True, exist_ok=True)
        (world / 'work' / area / 'audit.json').write_text(json.dumps({'area': area, 'pieces': len(pieces)}))
    (world / 'chim-regions.json').write_text(json.dumps(sorted(AREAS)))
    (world / 'chim-stats.json').write_text(json.dumps({'unit_cache_hits': hits, 'order': list(order)}))


def recorded_run(folder, store, seed, noise=None):
    """One recorded run of the region stage: the unit order shuffled by SEED. Returns the run folder."""
    run = folder / ('run-%d' % seed)
    run.mkdir(parents=True)
    (run / 'build-state.json').write_text('{}')
    command = [sys.executable, 'tools/chim_world.py', '--out', str(run / 'chim-world')]
    recorder = build_cache.Recorder(run, [(STAGE, command)], {})
    recorder.before(STAGE, command)
    order = sorted(AREAS)
    random.Random(seed).shuffle(order)
    region_stage(run, store, order, noise)
    manifest = recorder.after(STAGE, {})
    assert manifest['reusable'], manifest['reasons']
    return run


def _in_memo_folder(path):
    return 'collision-cache' in path.split('/')


def memo_files(run):
    return sorted(path for path in build_cache.load_manifest(run, STAGE)['files'] if _in_memo_folder(path))


def compared_files(run):
    """{path: SHA-256} of the stage's recorded files without diagnostics and memos."""
    return {path: row['sha256'] for path, row in build_cache.load_manifest(run, STAGE)['files'].items()
            if not build_cache.diagnostic(path) and not _in_memo_folder(path)}


class MemoRuleTests(unittest.TestCase):
    def test_a_memo_is_a_file_in_or_the_folder_named_by_memo_folders(self):
        for path in ('chim-world/work/rcm13_p8/collision-cache/0c%s.4ee1aae8251e51b6.pickle' % ('a' * 62),
                     'chim-world/work/rcm13_p8/collision-cache', 'bloodmoon-solstheim/work/rcm24_p26/collision-cache',
                     'chim-interiors/work/collision-cache/x.pickle'):
            self.assertTrue(build_cache.memo(path), path)
            self.assertTrue(build_cache.uncompared(path), path)
        for path in ('chim-world/chim/frames/x+00/y+00/frame.ccf', 'chim-world/work/rcm13_p8/collision.json',
                     'chim-world/work/rcm13_p8/lava-pools.json', 'chim-world/chim-regions.json'):
            self.assertFalse(build_cache.memo(path), path)
            self.assertFalse(build_cache.uncompared(path), path)
        self.assertTrue(build_cache.uncompared('chim-world/chim-stats.json'))

    def test_every_memo_folder_the_builder_names_is_listed(self):
        """Every hyphenated '...-cache' folder name on a line of tools/ that passes a collision memo folder
        (collision_cache, the compile's cache argument) is in MEMO_FOLDERS: a renamed or new memo folder of a
        compile would otherwise count in the comparisons again."""
        named = set()
        for path in sorted((ROOT / 'tools').rglob('*.py')):
            for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
                if 'collision_cache' in line or 'collision-cache' in line:
                    named.update(re.findall(r"""['"]([\w.-]*-cache)['"]""", line))
        self.assertIn('collision-cache', named)
        self.assertEqual(named - build_cache.MEMO_FOLDERS, set())


class RebuildFromStoredUnitsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = self.root / 'unit-store'

    def tearDown(self):
        self.temp.cleanup()

    def test_cold_warm_and_half_warm_rebuilds_in_any_order_have_the_same_outputs(self):
        cold = recorded_run(self.root, self.store, 1)                 # every unit compiled: a memo per area
        warm = recorded_run(self.root, self.store, 2)                 # every unit from the store: no memo
        for stored in sorted(self.store.iterdir())[::2]:              # half the units leave the store
            stored.unlink()
        mixed = recorded_run(self.root, self.store, 3)
        # the builder's own early cutoff check: the same outputs, whatever the order and the unit store's hits
        for run, old in ((warm, cold), (mixed, cold), (cold, warm), (mixed, warm), (cold, mixed)):
            self.assertIs(build_cache.same_outputs(run, old, STAGE), True, (run.name, old.name))
            self.assertEqual(build_cache.output_differences(run, old, STAGE), [], (run.name, old.name))
        hashes = {build_cache.load_manifest(run, STAGE)['tree']['stage_hash'] for run in (cold, warm, mixed)}
        self.assertEqual(len(hashes), 1)
        # what the three runs really wrote: every other file byte for byte the same, the memos only where computed
        self.assertEqual(compared_files(warm), compared_files(cold))
        self.assertEqual(compared_files(mixed), compared_files(cold))
        self.assertEqual(len(memo_files(cold)), len(AREAS))
        self.assertEqual(memo_files(warm), [])
        self.assertEqual(len(memo_files(mixed)), len(AREAS) // 2)

    def test_a_real_difference_still_counts(self):
        cold = recorded_run(self.root, self.store, 1)
        noisy = recorded_run(self.root, self.store, 4, noise='rcm11_p4')
        self.assertIs(build_cache.same_outputs(noisy, cold, STAGE), False)
        found = build_cache.output_differences(noisy, cold, STAGE)
        self.assertTrue(found)
        self.assertTrue(all(unit != 'work' for _, unit, _ in found), found)

    def test_a_record_whose_stored_tree_counted_memos_is_compared_by_its_files(self):
        """A record of tree schema 1 stored a stage hash over its memos too: it is not used, the tree is made again
        from the record's files, so the rebuild still has the same outputs and the change of schema rebuilds
        nothing."""
        cold = recorded_run(self.root, self.store, 1)
        warm = recorded_run(self.root, self.store, 2)
        path = cold / 'profile' / 'manifests' / f'{STAGE}.json'
        record = json.loads(path.read_text())
        files = {name: row['sha256'] for name, row in record['files'].items() if not build_cache.diagnostic(name)}
        old_hash = _sha(json.dumps(sorted(files.items())).encode())
        record['tree'] = {'schema': 'AmiWind unit tree 1', 'stage_hash': old_hash, 'segments': {}}
        path.write_text(json.dumps(record))
        self.assertEqual(unit_tree.tree_of(record), unit_tree.of_manifest(record))
        self.assertIs(build_cache.same_outputs(warm, cold, STAGE), True)
        fresh = build_cache.load_manifest(warm, STAGE)
        self.assertEqual(fresh['tree']['schema'], unit_tree.SCHEMA)
        self.assertIs(unit_tree.tree_of(fresh), fresh['tree'])


if __name__ == '__main__':
    unittest.main()
