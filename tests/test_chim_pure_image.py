# SPDX-License-Identifier: GPL-3.0-only
"""Pure CHIM images: a CHIM town's legacy exterior maps leave the image after its frame maps are
checked against them (chim.frame_map.remove_legacy_areas), the removal is recorded, the recorded
Seyda Neen check and the payload coverage accept it. Synthetic files only."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import frame_map as M  # noqa: E402

TABLE = ('AWBR1 2 96 540 100 100 0 0 0 0 0 0\n'
         'bm000 -512 -512 0 512 -600 -600 100 600\n'
         'bm001 0 -512 512 512 -100 -600 600 600\n')


def id1_with_balmora(root):
    id1 = Path(root) / 'id1'
    (id1 / 'maps').mkdir(parents=True)
    (id1 / 'balmora-regions.txt').write_text(TABLE, encoding='ascii')
    for name in ('bm000', 'bm001', 'balmora', 'census', 'balmora-chim'):
        (id1 / 'maps' / (name + '.bsp')).write_bytes(name.encode())
    return id1


class RemoveLegacyAreaTests(unittest.TestCase):
    def test_a_chim_towns_legacy_maps_leave_and_are_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1 = id1_with_balmora(tmp)
            self.assertEqual(M.legacy_area_maps(id1, 'balmora'), ['maps/bm000.bsp', 'maps/bm001.bsp', 'maps/balmora.bsp'])
            rows = M.remove_legacy_areas(id1, ['balmora'], 'the town runs on CHIM')
            self.assertEqual([r['file'] for r in rows], ['maps/bm000.bsp', 'maps/bm001.bsp', 'maps/balmora.bsp'])
            self.assertEqual(rows[0]['sha256'], hashlib.sha256(b'bm000').hexdigest())
            self.assertEqual({r['reason'] for r in rows}, {'the town runs on CHIM'})
            left = sorted(p.name for p in (id1 / 'maps').iterdir())
            self.assertEqual(left, ['balmora-chim.bsp', 'census.bsp'])           # frame map and interiors stay
            self.assertTrue((id1 / 'balmora-regions.txt').is_file())             # the harvest regions still use it

    def test_seyda_neen_includes_its_special_maps(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp) / 'id1'
            (id1 / 'maps').mkdir(parents=True)
            (id1 / 'seyda-regions.txt').write_text('AWBR1 1 96 540 0 0 64 90 0 0 64 90\nsn000 -1 -1 1 1 -2 -2 2 2\n',
                                                   encoding='ascii')
            for name in ('sn000', 'seyda', 'intro_docks', 'sncourt', 'census'):
                (id1 / 'maps' / (name + '.bsp')).write_bytes(b'x')
            self.assertEqual(M.legacy_area_maps(id1, 'seyda'),
                             ['maps/sn000.bsp', 'maps/seyda.bsp', 'maps/intro_docks.bsp', 'maps/sncourt.bsp'])


class RecordedStageTests(unittest.TestCase):
    def test_removed_recorded_files_are_not_a_change(self):
        import recorded_stage
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp) / 'id1'
            (id1 / 'maps').mkdir(parents=True)
            (id1 / 'maps/sn001.bsp').write_bytes(b'kept')
            work = Path(tmp) / 'work'
            work.mkdir()
            rows = [{'file': 'maps/sn000.bsp', 'sha256': hashlib.sha256(b'gone').hexdigest()},
                    {'file': 'maps/sn001.bsp', 'sha256': hashlib.sha256(b'kept').hexdigest()}]
            recorded_stage.receipt_path(work).write_text(json.dumps({'files': rows, 'checks': []}))
            with self.assertRaisesRegex(ValueError, 'sn000'):
                recorded_stage.check(id1, work, 'test')
            receipt = recorded_stage.check(id1, work, 'test', removed=['maps/sn000.bsp'])
            self.assertEqual(receipt['checks'][-1]['removed_for_chim'], 1)


class CoverageTests(unittest.TestCase):
    def test_a_chim_build_need_not_ship_the_legacy_town_maps(self):
        from payload_coverage import compare
        config = {'features': [{'id': 'balmora', 'replaced_by_chim': True,
                                'patterns': ['id1/maps/bm[0-9][0-9][0-9].bsp', 'id1/balmora-regions.txt']}],
                  'new_features': []}
        baseline = {'release': 'x', 'classes': {'id1/maps/bm#.bsp': 64, 'id1/balmora-regions.txt': 1}}
        paths = ['id1/balmora-regions.txt']
        self.assertIn('id1/maps/bm#.bsp', compare(paths, config, baseline, 'legacy')['missing_classes'])
        self.assertEqual(compare(paths, config, baseline, 'chim')['missing_classes'], [])


if __name__ == '__main__':
    unittest.main()
