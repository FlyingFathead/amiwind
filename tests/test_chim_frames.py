# SPDX-License-Identifier: GPL-3.0-only
"""CHIM worlds of several frames (one per area): layout, shared storage, validation. Synthetic data only."""
import copy
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

from chim import format as F  # noqa: E402
from chim.validate import measure, validate  # noqa: E402
from chim.world import build_frames, frame_order  # noqa: E402
from test_chim_format import CENTRE, ROWS, chim_files, fixture  # noqa: E402

OFFSET = 8192.0                  # the second frame's centre, east of the first (frames 4096 units wide)


def frame_specs(tmp):
    """Two frame inputs from the fixture's units: the fixture frame at cell (0, 0) and a copy at
    cell (2, 0), 8192 units east, holding other references."""
    captured = []

    def capture(out, specs, *a, **kw):
        captured.append(specs[0])
        return {}
    with patch('chim.build.build_frames', side_effect=capture):
        _, source_a = fixture(Path(tmp) / 'a')
        _, source_b = fixture(Path(tmp) / 'b', placements=[dict(r, ref=r['ref'] + 100) for r in ROWS])
    a, b = captured
    b = dict(b, frame=dict(b['frame'], cell=(2, 0), centre=(CENTRE[0] + OFFSET, CENTRE[1])))
    sections = [dict(source_a, town='west', cell=[0, 0]), dict(source_b, town='east', cell=[2, 0])]
    return a, b, sections


class MultiFrameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.a, cls.b, cls.sections = frame_specs(cls.tmp.name)
        cls.out = Path(cls.tmp.name) / 'two'
        cls.receipt = build_frames(cls.out, [cls.a, cls.b], {'grain': 256, 'sector_chunks': 2})
        cls.source = {'areas': ['west', 'east'], 'frames': cls.sections}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_two_frame_world_validates(self):
        fails, world = validate(self.out, self.source)
        self.assertEqual(list(fails), [])
        self.assertEqual(len(world['frames']), 2)
        self.assertEqual(world['settings']['frames'], 2)
        self.assertEqual(self.receipt['placements'], 2 * len(ROWS))
        self.assertEqual([f['frame']['cell'] for f in self.receipt['frames']], [[0, 0], [2, 0]])
        self.assertGreater(world['seam_samples'], 0)

    def test_same_key_other_content_is_stored_under_its_own_name(self):
        # each area has its own ground materials under the same keys ('ground', 'g1')
        b = copy.copy(self.b)
        b['textures'] = dict(b['textures'])
        key = ('ground', 'g1')
        mip = bytearray(b['textures'][key]['miptex'])
        mip[40:] = bytes(v ^ 0x55 for v in mip[40:])
        b['textures'][key] = dict(b['textures'][key], miptex=bytes(mip))
        with tempfile.TemporaryDirectory() as tmp:
            receipt = build_frames(Path(tmp), [self.a, b], {'grain': 256, 'sector_chunks': 2})
            fails, world = validate(tmp, self.source)
        self.assertEqual(list(fails), [])
        self.assertEqual(receipt['textures'], self.receipt['textures'] + 1)
        names = [t['name'] for t in world['textures']]
        self.assertIn('ground|g1', names)
        self.assertIn('ground|g1#2', names)

    def test_identical_models_are_stored_once_across_frames(self):
        with tempfile.TemporaryDirectory() as tmp:
            one = build_frames(Path(tmp) / 'one', [self.a], {'grain': 256, 'sector_chunks': 2})
        self.assertEqual(self.receipt['models'], one['models'])
        self.assertEqual(self.receipt['textures'], one['textures'])
        self.assertEqual(self.receipt['model_variants'], 2 * one['model_variants'])

    def test_input_order_does_not_change_the_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            build_frames(Path(tmp), [self.b, self.a], {'grain': 256, 'sector_chunks': 2})
            self.assertEqual(chim_files(tmp), chim_files(self.out))

    def test_file_table_and_placement_ids(self):
        _, files, _, _ = F.read_index((self.out / 'chim/world.cwi').read_bytes())
        kinds = [(f['kind'], tuple(f['cell'])) for f in files]
        self.assertEqual(kinds[0], (b'FRAM', (0, 0)))
        second = kinds.index((b'FRAM', (2, 0)))
        self.assertTrue(all(k == (b'SECT', (0, 0)) for k in kinds[1:second]))
        self.assertTrue(all(k == (b'SECT', (2, 0)) for k in kinds[second + 1:]))
        fails, world = validate(self.out, self.source)
        pids = sorted(r['pid'] for c in world['chunks'] for r in c['owned'])
        self.assertEqual(pids, list(range(2 * len(ROWS))))

    def test_walks_and_cameras_per_frame(self):
        fails, world = validate(self.out, self.source)
        m = measure(world, self.source, cameras=[('west', CENTRE[0], CENTRE[1]),
                                                 ('east', CENTRE[0] + OFFSET, CENTRE[1]),
                                                 ('nowhere', CENTRE[0] - OFFSET, CENTRE[1])])
        self.assertEqual(sorted(m['walks']), ['0,0', '2,0'])
        frames = [c.get('frame') for c in m['cameras']]
        self.assertEqual(frames, [[0, 0], [2, 0], None])

    def test_stats_split_disk_by_area(self):
        from chim.stats import chim_stats
        fails, world = validate(self.out, self.source)
        m = measure(world, self.source)
        m['walk'].pop('_replay', None)
        s = chim_stats(world, m, dict(self.receipt, areas=['west', 'east']), ['west', 'east'], source=self.source)
        areas = s['disk']['areas']
        self.assertEqual(sum(a['chim_bytes'] for a in areas.values()) + s['disk']['index_bytes'], s['disk']['bytes'])
        self.assertEqual(areas['west']['chim_files'], areas['east']['chim_files'])

    def test_overlapping_or_duplicate_frames_are_refused(self):
        near = dict(self.b, frame=dict(self.b['frame'], centre=(CENTRE[0] + 1000, CENTRE[1])))
        with self.assertRaisesRegex(ValueError, 'overlap'):
            frame_order([self.a, near])
        same = dict(self.b, frame=dict(self.b['frame'], cell=(0, 0)))
        with self.assertRaisesRegex(ValueError, 'share the cell'):
            frame_order([self.a, same])

    def test_validator_needs_a_section_per_frame(self):
        one = {'frames': self.sections[:1]}
        fails, _ = validate(self.out, one)
        self.assertTrue(any('frame sections' in f for f in fails), list(fails))

    def test_frame_order_is_hilbert_over_cells(self):
        specs = []
        for cell in ((3, 3), (0, 0), (1, 0), (0, 1)):
            specs.append({'frame': {'cell': cell, 'centre': (cell[0] * 8192.0, cell[1] * 8192.0),
                                    'low': (-512.0, -512.0), 'span': (1024, 1024)}})
        cells = [specs[k]['frame']['cell'] for k in frame_order(specs)]
        lo = (0, 0)
        expected = sorted([s['frame']['cell'] for s in specs],
                          key=lambda c: (F.hilbert_index(4, c[0] - lo[0], c[1] - lo[1]), c))
        self.assertEqual(cells, expected)
        self.assertEqual(cells[0], (0, 0))



class ScriptPathTests(unittest.TestCase):
    def test_chim_build_finds_the_mwad_package_first(self):
        # The script's own folder (tools/, holding mwad.py) comes first on sys.path; the src/mwad
        # package must win, or the build stops on "No module named 'mwad.cli'".
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            out = subprocess.run([sys.executable, str(ROOT / 'tools/chim_build.py'), '--area', 'balmora',
                                  '--data-files', str(Path(tmp) / 'missing'), '--palette', str(Path(tmp) / 'p.lmp'),
                                  '--out', str(Path(tmp) / 'out')],
                                 capture_output=True, text=True,
                                 # as in the build container: src already on the path, before tools
                                 env={'PYTHONPATH': str(ROOT / 'src') + os.pathsep + str(ROOT / 'tools')})
        self.assertEqual(out.returncode, 1)
        self.assertNotIn('Traceback', out.stderr)
        self.assertIn('Error:', out.stderr)


if __name__ == '__main__':
    unittest.main()
