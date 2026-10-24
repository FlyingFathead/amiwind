# SPDX-License-Identifier: GPL-3.0-only
"""BUILD-SUMMARY-INTERIOR-COUNTS-48: the build summary and the CHIM inclusion ledger say how many interiors a build
includes (tools/interior_counts.py), from the run's room batches record, CHIM interiors receipt, image room heap report
and the room stages' residents reports."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import interior_counts as C  # noqa: E402


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


KIT = {'appearance': {}, 'anim': {'profile': 'react+full'}}


class InteriorCounts(unittest.TestCase):
    def setUp(self):
        self.run = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.run, True)
        write(self.run / C.BATCH_RECORD, {
            'selection': '1-40', 'rooms': [{'room': 'A'}, {'room': 'B'}, {'room': 'C'}],
            'held': {'Balmora, X': 'balmora-interiors', 'Vivec, Y': 'chim-rooms-vivec_city', 'Seyda Neen, Z': 'area'},
            'refused': {'D': 'no placement to convert'}})
        write(self.run / C.RECEIPT, {
            'rooms': [{'room': r, 'placements': 10} for r in ('a', 'b', 'c', 'x')],
            'kept_room_maps': [{'room': 'y', 'reason': 'water: the room map has 2 water brushes'}],
            'failed_rooms': [{'room': 'z', 'reason': 'ValueError: boom'}]})
        (self.run / 'intro-scene/id1/maps').mkdir(parents=True)
        (self.run / 'intro-scene/id1/maps/prison.bsp').write_bytes(b'x')
        write(self.run / 'chim-room-batches/scene/room-batches-residents.json', {
            'models': {'a': KIT, 'b': dict(KIT, anim_fallback={'level': 'standing'}),
                       'dead': {'appearance': {'initially_dead': True}}, 'rat': {'idle': {}}},
            'cast': [{'map': 'ra', 'id': 'a'}, {'map': 'rb', 'id': 'a'}, {'map': 'ra', 'id': 'B'},
                     {'map': 'ra', 'id': 'dead'}, {'map': 'ra', 'id': 'rat'}]})
        # the area report's exterior residents (map seyda) are not room residents
        write(self.run / 'intro-scene/area-report.json', {
            'models': {'c': KIT, 'out': KIT}, 'cast': [{'map': 'seyda', 'id': 'out'}, {'map': 'room', 'id': 'c'}]})
        write(self.run / 'chim-rooms-vivec_city/scene/vivec_city-interiors.json', {
            'models': {'v': dict(KIT, anim_fallback={'level': 'idle'})}, 'cast': [{'map': 'vx', 'id': 'v'}]})

    def test_counts_from_the_records(self):
        record = C.counts(self.run)
        self.assertEqual(record['plan']['rooms'], 7)          # 3 converted + 3 held + 1 refused
        self.assertEqual(record['plan']['by_stage'], {'area': 1, 'balmora-interiors': 1, 'chim-room-batches': 3,
                                                      'chim-rooms-vivec_city': 1})
        self.assertEqual(record['chim'], {'rooms': 4, 'placements': 40})
        reasons = {c['room']: c['reason'] for c in record['classic']}
        self.assertEqual(sorted(reasons), ['D', 'prison', 'y', 'z'])
        self.assertIn('water', reasons['y'])
        self.assertIn('not made', reasons['z'])
        self.assertIn('refused', reasons['D'])
        self.assertIsNone(record['fast_32mb'])                # no image room heap report yet
        res = record['residents']
        self.assertEqual(res['models'], {'kit': 2, 'standing': 1, 'corpse': 1, 'creature': 1, 'idle': 1})
        self.assertEqual(res['placed'], {'kit': 3, 'standing': 1, 'corpse': 1, 'creature': 1, 'idle': 1})
        self.assertEqual(res['profile'], 'react+full')

    def test_the_image_marks_and_the_lines(self):
        write(self.run / C.HEAP_REPORT, {'marked_32mb': ['vhi003', 'bmguild']})
        write(self.run / C.INSTALL_RECORD, {'rooms': [{}] * 4, 'not_in_image': [], 'shell_maps_removed': []})
        lines = C.summary_lines(C.counts(self.run))
        text = '\n'.join(lines)
        self.assertIn('Interiors in the plan: 7 rooms', text)
        self.assertIn('Interiors converted to CHIM rooms: 4 (40 placements); in the image: 4', text)
        self.assertIn('Interiors kept as classic maps: 4', text)
        self.assertIn('Interiors that need 32 MB of Fast RAM (_chim_room_fast_mb): 2: bmguild, vhi003', text)
        self.assertIn('Room residents by animation level (kit = react+full): models kit 2, standing 1, idle 1, '
                      'corpse 1, creature 1', text)
        compact = C.ledger_record(C.counts(self.run))
        self.assertEqual((compact['plan'], compact['chim'], compact['fast_32mb']), (7, 4, 2))

    def test_no_records_no_counts(self):
        self.assertIsNone(C.counts(self.run / 'nothing'))
        self.assertEqual(C.summary_lines(None), [])

    def test_the_build_summary_prints_them(self):
        import build_summary
        with contextlib.redirect_stdout(io.StringIO()) as out:
            result = build_summary.BuildSummary(self.run, 'test', 'AGA image').finish('failed')
        self.assertEqual(result['interior_counts']['chim']['rooms'], 4)
        self.assertIn('Interiors converted to CHIM rooms: 4', out.getvalue())

    def test_the_inclusion_ledger_keeps_them(self):
        import chim_inclusion as I
        write(self.run / 'chim-world/chim-source.json', {'frames': [{'cell': [1, 2], 'town': 'rcp1_p2'}]})
        repo = self.run / 'repo'
        repo.mkdir()
        log = []
        e = I.build_step(self.run, '0.0.48', 'abc', ledger=repo, log=log.append)
        self.assertEqual(e['interiors']['chim'], 4)
        self.assertEqual(I.run_entry(I.load(self.run / 'toolkit'), self.run.name)['interiors']['plan'], 7)
        self.assertTrue(any('Interiors in the plan: 7' in line for line in log))
        # a new image report changes the counts: the entry is made again, not reused
        write(self.run / C.HEAP_REPORT, {'marked_32mb': ['r']})
        e = I.build_step(self.run, '0.0.48', 'abc', ledger=repo, log=log.append)
        self.assertEqual(e['interiors']['fast_32mb'], 1)


if __name__ == '__main__':
    unittest.main()
