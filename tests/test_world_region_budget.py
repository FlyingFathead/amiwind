# SPDX-License-Identifier: GPL-3.0-only
"""BUILD-LAVA-TERRAIN-BUDGET-38: every region a public default build makes fits its world-scenery limits.

The project's own builds put the dense lava and Molag Mar cells on CHIM, so their BSP29 regions are only built by a
default build from the public repository. The recorded scan (config/world-region-budget-scan.json, written by
tools/world_budget_scan.py from such a build) must be measured with the current refinement table and show no
region over a limit.
"""
from pathlib import Path
import json
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import world_budget_scan as scan


class WorldRegionBudgetScanTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads(scan.RECORD.read_text(encoding='utf-8'))

    def test_scan_was_measured_with_the_current_refinement_table(self):
        # A changed table lays out other regions: measure again (tools/world_budget_scan.py record).
        self.assertEqual(self.record['refinements_sha256'], scan.refinements_sha256(),
                         'config/world-region-refinements.json changed since the region budget scan; rerun the '
                         'world-terrain and world-scenery stages of a default build and record the scan')

    def test_no_region_of_the_default_build_is_over_a_limit(self):
        self.assertEqual(self.record['limits'], scan.LIMITS)
        self.assertEqual(self.record['regions_over'], [])
        self.assertGreater(self.record['regions_measured'], 2000)
        largest = self.record['largest']
        self.assertTrue(largest)
        self.assertEqual([r['bytes'] for r in largest], sorted((r['bytes'] for r in largest), reverse=True))
        for row in largest:
            for key, limit in scan.LIMITS.items():
                self.assertLessEqual(row[key], limit, '%s %s' % (row['name'], key))

    def test_limits_are_the_world_scenery_stage_limits(self):
        source = (ROOT / 'tools/prepare_world_scenery.py').read_text(encoding='utf-8')
        self.assertIn("report['faces'] > 30000 or report['clipnodes'] > 32767 or report['bytes'] > 4 * 1024 * 1024",
                      source)
        self.assertEqual(scan.LIMITS, {'bytes': 4 * 1024 * 1024, 'faces': 30000, 'clipnodes': 32767})

    def test_scan_reads_every_made_region_and_skips_chim_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            terrain, scenery = root / 'terrain', root / 'scenery'
            terrain.mkdir()
            regions = [dict(name='vf0000', cell=[0, 0], divisions=1, subcell=[0, 0], converted=dict(bytes=10)),
                       dict(name='vf0001', cell=[1, 0], divisions=1, subcell=[0, 0], chim_region=True),
                       dict(name='vf0002', cell=[2, 0], divisions=2, subcell=[1, 0], converted=dict(bytes=20))]
            (terrain / 'world-regions.json').write_text(json.dumps(dict(regions=regions)))
            for name, faces, clipnodes, pad in (('vf0000', 3, 5, 100), ('vf0002', 7, 2, 300)):
                header = bytearray(4 + 8 * 15)
                struct.pack_into('<i', header, 0, 29)
                struct.pack_into('<ii', header, 4 + 8 * 7, 0, faces * 20)
                struct.pack_into('<ii', header, 4 + 8 * 9, 0, clipnodes * 8)
                (scenery / name).mkdir(parents=True)
                (scenery / name / 'scene.bsp').write_bytes(bytes(header) + bytes(pad))
            _, rows = scan.scan(terrain, scenery)
            self.assertEqual([(r['name'], r['faces'], r['clipnodes'], r['terrain_bytes']) for r in rows],
                             [('vf0002', 7, 2, 20), ('vf0000', 3, 5, 10)])
            (scenery / 'vf0000' / 'scene.bsp').unlink()
            with self.assertRaisesRegex(ValueError, 'without a scenery map'):
                scan.scan(terrain, scenery)


if __name__ == '__main__':
    unittest.main()
