# SPDX-License-Identifier: GPL-3.0-only
"""tools/chim_inclusion.py: the world map's inclusion ledger is written from a build's records, never by hand."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import chim_inclusion as I  # noqa: E402


class InclusionLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        frames = [{'cell': [1, 2], 'town': 'rcm1_p2'}, {'cell': [-3, -9], 'town': 'seyda'},
                  {'cell': [0, -11], 'town': 'rcm0_m11'}, {'cell': [5, -2], 'town': 'rcp5_m2'}]
        (self.tmp / 'source.json').write_text(json.dumps({'frames': frames}))
        (self.tmp / 'cells.json').write_text(json.dumps({'format': 'aw-chim-cells-1',
                                                         'cells': [[1, 2], [0, -11], [-1, -11]]}))

    def test_entry_lists_region_cells_towns_and_overlaps(self):
        e = I.entry('v9.9.9-dev1', 'packaged', 'abc', self.tmp / 'source.json', self.tmp / 'cells.json',
                    'a' * 64, 'b' * 64, 'readback', now='2026-10-16T00:00:00+00:00')
        self.assertEqual(e['cells'], {'0,-11': {'state': 'included', 'frame': 'rcm0_m11'},
                                      '1,2': {'state': 'included', 'frame': 'rcm1_p2'},
                                      '5,-2': {'state': 'included', 'frame': 'rcp5_m2'}})
        self.assertEqual(e['town_frames'], ['seyda'])
        self.assertEqual(e['partial_town_overlap_cells'], ['-1,-11'])
        self.assertFalse(e['owner_accepted'])

    def test_town_frame_cells_are_included_with_their_town(self):
        frames = [{'cell': [1, 2], 'town': 'rcm1_p2'},
                  {'cell': [3, -10], 'town': 'vivec_city',
                   'frame_ownership': {'core': [8192.0, -90112.0, 24576.0, -73728.0]}}]
        (self.tmp / 'towns.json').write_text(json.dumps({'frames': frames}))
        e = I.entry('v9', 'packaged', 'abc', self.tmp / 'towns.json', self.tmp / 'cells.json', 'a' * 64, 'b' * 64,
                    'x', now='2026-10-16T00:00:00+00:00')
        self.assertEqual({k: v['frame'] for k, v in e['cells'].items()},
                         {'1,2': 'rcm1_p2', '1,-11': 'vivec_city', '1,-10': 'vivec_city',
                          '2,-11': 'vivec_city', '2,-10': 'vivec_city'})
        self.assertEqual(e['town_frames'], ['vivec_city'])

    def test_write_replaces_the_same_version_and_keeps_newest_first(self):
        old = {'version': 'v1', 'state': 'released', 'cells': {}, 'generated': '2026-01-01'}
        (self.tmp / 'chim-inclusion.json').write_text(json.dumps({'format': I.FORMAT, 'builds': [old]}))
        new = I.entry('v2', 'packaged', 'abc', self.tmp / 'source.json', self.tmp / 'cells.json', 'a' * 64,
                      'b' * 64, 'x', now='2026-10-16T00:00:00+00:00')
        doc = I.write(self.tmp, new)
        doc = I.write(self.tmp, dict(new, evidence='y'))
        self.assertEqual([b['version'] for b in doc['builds']], ['v2', 'v1'])
        self.assertEqual(doc['builds'][0]['evidence'], 'y')
        js = (self.tmp / 'chim-inclusion.js').read_text(encoding='utf-8')
        self.assertTrue(js.startswith('window.ChimInclusionMetadata = {') and js.endswith('};\n'))
        self.assertEqual(json.loads(js[len('window.ChimInclusionMetadata = '):-2]), doc)


if __name__ == '__main__':
    unittest.main()
