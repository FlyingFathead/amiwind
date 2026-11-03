# SPDX-License-Identifier: GPL-3.0-only
"""The CHIM world pack learns where sector records land from their sizes (format.sector_layout) and writes each
placement record once per frame (BUILD-CHIM-STAGE-SERIAL-TAIL-36). Both give the same files as the method before:
build every sector file, parse it again for the offsets (and build it a second time with terrain references), and
write each placement row again for every chunk it reaches. Synthetic data only."""
import hashlib
import random
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import format as F  # noqa: E402
from chim import world as W  # noqa: E402


def old_layout(records):
    """The method before: the sector file built and parsed again."""
    blob = F.sector_file(records)
    return {(r['kind'], r['id']): r['offset'] for r in F.read_sector(blob)}, len(blob)


def tree_hashes(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(Path(root).rglob('*')) if p.is_file()}


class SectorLayout(unittest.TestCase):
    def test_layout_is_where_the_sector_file_puts_each_record(self):
        rng = random.Random(36)
        kinds = [b'CHNK', b'TERR', b'MODL', b'TEXR']
        for n in (0, 1, 2, 7, 40):
            records = [(kinds[i % 4], i, bytes(rng.randrange(256) for _ in range(rng.randrange(0, 70))))
                       for i in range(n)]
            self.assertEqual(F.sector_layout(records), old_layout(records))


class PackSameFiles(unittest.TestCase):
    def build(self, specs, settings, out, method):
        if method == 'old':
            with patch.object(W.F, 'sector_layout', old_layout), patch.object(W, 'PACK_RECORD_REUSE', False):
                receipt = W.build_frames(out, specs, settings)
        else:
            receipt = W.build_frames(out, specs, settings)
        return receipt, tree_hashes(out)

    def same(self, specs, settings):
        with tempfile.TemporaryDirectory() as t:
            old = self.build(specs, settings, Path(t) / 'old', 'old')
            new = self.build(specs, settings, Path(t) / 'new', 'new')
        self.assertEqual(new[1], old[1])
        self.assertTrue(new[1])
        drop = ('files_rewritten',)
        self.assertEqual({k: v for k, v in new[0].items() if k not in drop},
                         {k: v for k, v in old[0].items() if k not in drop})

    def test_two_frames_with_reach_copies(self):
        from test_chim_frames import frame_specs
        with tempfile.TemporaryDirectory() as t:
            a, b, _ = frame_specs(t)
        self.same([a, b], {'grain': 256, 'sector_chunks': 2})

    def test_terrain_references_across_frames(self):
        from test_chim_format import fixture
        from test_chim_terrain_refs import grid_task
        from chim.terrain import terrain_unit
        specs = []

        def capture(out, frames, *a, **kw):
            specs.extend(frames)
            return {}
        with tempfile.TemporaryDirectory() as t, patch('chim.build.build_frames', side_effect=capture):
            fixture(Path(t), placements=[], settings={'grain': 256, 'sector_chunks': 2}, same_ground=True,
                    heights_of=lambda x, y: -512)
            fixture(Path(t), placements=[], settings={'grain': 256, 'sector_chunks': 2, 'terrain_refs': 'on'},
                    same_ground=True, heights_of=lambda x, y: -512)
        second = specs[1]
        second['frame'] = dict(second['frame'], cell=(-19, 14), centre=(-151552, 118784))
        task = grid_task(0, 0, lambda x, y: -512)
        task['materials'] = [[1, 1], [1, 1]]
        template = terrain_unit(task)
        second['terrain'] = {c: dict(template, offset=u['offset']) for c, u in second['terrain'].items()}
        self.same(specs, {'grain': 256, 'sector_chunks': 2})


class PackImagesSameFiles(unittest.TestCase):
    """The texture ids handed out first and the brush images made ahead of the walk (in this process and on the
    worker pool) give the files and receipt of the walk that makes each image where it meets it."""

    def build(self, specs, settings, out, mode, jobs=1):
        with patch.dict('os.environ', {W.PACK_IMAGES_ENV: mode}):
            receipt = W.build_frames(out, specs, settings, jobs=jobs)
        return receipt, tree_hashes(out)

    def same(self, specs, settings):
        drop = ('files_rewritten',)
        with tempfile.TemporaryDirectory() as t:
            serial = self.build(specs, settings, Path(t) / 'serial', 'serial')
            here = self.build(specs, settings, Path(t) / 'here', 'here')
            pool = self.build(specs, settings, Path(t) / 'pool', 'workers', jobs=2)
        self.assertTrue(serial[1])
        for other in (here, pool):
            self.assertEqual(other[1], serial[1])
            self.assertEqual({k: v for k, v in other[0].items() if k not in drop},
                             {k: v for k, v in serial[0].items() if k not in drop})

    def test_three_frames_with_reach_copies(self):
        import copy
        from test_chim_frames import frame_specs
        with tempfile.TemporaryDirectory() as t:
            a, b, _ = frame_specs(t)
        # a third frame two cells further east, as frame_specs places the second (same units again: the models
        # and textures it meets are stored once, ids and homes from the walk)
        c = copy.deepcopy(b)
        step = b['frame']['centre'][0] - a['frame']['centre'][0]
        c['frame'] = dict(c['frame'], cell=(4, 0), centre=(b['frame']['centre'][0] + step, b['frame']['centre'][1]))
        self.same([a, b, c], {'grain': 256, 'sector_chunks': 2})

    def test_terrain_references_across_frames(self):
        specs = []
        PackSameFiles.test_terrain_references_across_frames(
            type('Capture', (), {'same': lambda _self, s, settings: specs.append((s, settings))})())
        self.same(*specs[0])


if __name__ == '__main__':
    unittest.main()
