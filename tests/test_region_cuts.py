# SPDX-License-Identifier: GPL-3.0-only
"""Sub-cell cut overlays from synthetic town configs and section plans."""
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import region_cuts  # noqa: E402

# Balmora-style settings: a 4x4 grid of 512-unit cores, one override.
TOWN = {'bounds': [[-1024, -1024], [1024, 1024]], 'core_size': 512, 'overlap': 300,
        'hysteresis': 10, 'draw_distance': 100, 'terrain_step': 128,
        'region_core_overrides': {}}
LAYOUT = {'regions': [
    {'name': 'sn000', 'core': [[-200, -200], [0, 200]], 'coverage': [[-400, -400], [200, 400]]},
    {'name': 'sn001', 'core': [[0, -200], [200, 200]], 'coverage': [[-200, -400], [400, 400]]},
    {'name': 'sn002', 'core': [[200, -200], [900, 200]], 'coverage': [[0, -400], [1100, 400]]}]}


def plan():
    sections = [dict(name='rooma', physical_id=8252, references=[1, 3], coverage=[[-100, -50, 0], [40, 50, 128]],
                     spawn=[-50, 0, 24], yaw=0),
                dict(name='roomb', physical_id=8253, references=[2, 3], coverage=[[-40, -50, 0], [100, 50, 128]],
                     spawn=[50, 0, 24], yaw=180)]
    portals = [{'from': 'rooma', 'to': 'roomb', 'axis': 0, 'split': 0, 'margin': 24,
                'bounds': [[-40, -30, 0], [40, 30, 96]]}]
    return dict(cell='Room', logical_map='room', sections=sections, portals=portals)


class RegionCutTests(unittest.TestCase):
    def test_town_settings_give_the_map_core_coverage_and_neighbour_cores(self):
        doc = region_cuts.from_town(TOWN, 'bm005', z=[0, 512])
        self.assertEqual(doc['format'], 'aw-cuts-1')
        self.assertEqual(doc['space'], 'map-local')
        self.assertEqual(doc['z'], [0, 512])
        focus = doc['regions'][0]
        # bm005 is row 1, column 1 of the 4x4 grid.
        self.assertEqual(focus['name'], 'bm005')
        self.assertEqual(focus['core'], [[-512, -512], [0, 0]])
        self.assertEqual(focus['coverage'], [[-812, -812], [300, 300]])
        names = [r['name'] for r in doc['regions']]
        # Neighbours: every core overlapping the coverage, i.e. the 3x3 block around bm005.
        self.assertEqual(sorted(names[1:]), ['bm000', 'bm001', 'bm002', 'bm004', 'bm006',
                                             'bm008', 'bm009', 'bm010'])
        self.assertTrue(all('coverage' not in r for r in doc['regions'][1:]))
        self.assertNotIn(focus['colour'], [r['colour'] for r in doc['regions'][1:]])
        self.assertEqual(doc['planes'], [])

    def test_border_planes_follow_core_lines_inside_the_coverage(self):
        doc = region_cuts.from_town(TOWN, 'bm005', border_planes=True)
        lines = {(p['axis'], p['at']): (p['from'], p['to']) for p in doc['planes']}
        self.assertEqual(set(lines), {('x', -512), ('x', 0), ('y', -512), ('y', 0)})
        self.assertEqual(lines[('x', 0)], (-812, 300))
        self.assertTrue(all(p['kind'] == 'region-border' for p in doc['planes']))

    def test_all_regions_and_explicit_layouts(self):
        doc = region_cuts.from_town(TOWN, all_regions=True)
        self.assertEqual(len(doc['regions']), 16)
        self.assertTrue(all('coverage' in r for r in doc['regions']))
        doc = region_cuts.from_town(LAYOUT, 'sn001')
        self.assertEqual([r['name'] for r in doc['regions']], ['sn001', 'sn000', 'sn002'])
        self.assertEqual(doc['regions'][0]['coverage'], [[-200, -400], [400, 400]])
        with self.assertRaisesRegex(ValueError, 'Unknown region map'):
            region_cuts.from_town(LAYOUT, 'sn009')

    def test_repository_balmora_config_places_bm019(self):
        settings = json.loads((ROOT / 'config/balmora.json').read_text(encoding='utf-8'))
        doc = region_cuts.from_town(settings, 'bm019')
        self.assertEqual(doc['regions'][0]['core'], [[-768, -1536], [0, -768]])
        self.assertEqual(doc['regions'][0]['coverage'], [[-1664, -2432], [896, 128]])
        # The split bm027/bm001 override is visible as two neighbour cores.
        cores = {r['name']: r['core'] for r in doc['regions']}
        self.assertEqual(cores['bm027'], [[-768, -768], [0, -640]])
        self.assertEqual(cores['bm001'], [[-768, -640], [0, 0]])

    def test_section_plan_becomes_coverage_boxes_and_portal_planes(self):
        doc = region_cuts.from_plan(plan())
        self.assertEqual(doc['map'], 'room')
        self.assertEqual([(r['name'], r['coverage'], r['z']) for r in doc['regions']],
                         [('rooma', [[-100, -50], [40, 50]], [0, 128]), ('roomb', [[-40, -50], [100, 50]], [0, 128])])
        portal = doc['planes'][0]
        self.assertEqual((portal['axis'], portal['at'], portal['from'], portal['to'], portal['z'], portal['margin']),
                         ('x', 0, -30, 30, [0, 96], 24))
        horizontal = plan()
        horizontal['portals'][0].update(axis=2, split=64, bounds=[[-40, -30, 32], [40, 30, 96]])
        plane = region_cuts.from_plan(horizontal)['planes'][0]
        self.assertEqual((plane['axis'], plane['at'], plane['x'], plane['y']), ('z', 64, [-40, 40], [-30, 30]))

    def test_plan_geometry_is_checked_by_the_section_tool(self):
        self.assertEqual(region_cuts.check_plan(plan()).splitlines()[0], b'AWIS1 2 1')
        bad = plan()
        bad['portals'][0]['margin'] = 45
        with self.assertRaises(ValueError):
            region_cuts.from_plan(bad)
        self.assertEqual(len(region_cuts.from_plan(bad, check=False)['planes']), 1)

    def test_overlay_validation_refuses_malformed_input(self):
        good = region_cuts.from_plan(plan())
        for mutate in (lambda d: d.update(format='aw-cuts-2'), lambda d: d.update(space='source'),
                       lambda d: d['regions'][0].pop('coverage'),
                       lambda d: d['regions'][0].update(core=[[1, 0], [0, 1]]),
                       lambda d: d['planes'][0].update(axis='w'),
                       lambda d: d['planes'][0].update(at=float('inf')),
                       lambda d: d['planes'][0].update(colour='red'),
                       lambda d: d['planes'][0].update(margin=0)):
            doc = json.loads(json.dumps(good))
            mutate(doc)
            with self.subTest(doc=doc), self.assertRaises(ValueError):
                region_cuts.validate_overlay(doc)

    def test_cli_writes_lf_json_and_checks_it(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'town.json').write_text(json.dumps(TOWN), encoding='utf-8')
            (root / 'plan.json').write_text(json.dumps(plan()), encoding='utf-8')
            self.assertEqual(region_cuts.main(['town', '--config', str(root / 'town.json'), '--map', 'bm000',
                                               '--out', str(root / 'town-cuts.json')]), 0)
            raw = (root / 'town-cuts.json').read_bytes()
            self.assertNotIn(b'\r', raw)
            self.assertTrue(raw.endswith(b'\n'))
            self.assertEqual(json.loads(raw)['regions'][0]['name'], 'bm000')
            self.assertEqual(region_cuts.main(['plan', '--plan', str(root / 'plan.json'),
                                               '--out', str(root / 'plan-cuts.json')]), 0)
            out = io.StringIO()
            with redirect_stdout(out):
                region_cuts.main(['check', '--overlay', str(root / 'plan-cuts.json')])
                region_cuts.main(['check', '--plan', str(root / 'plan.json')])
            self.assertIn('ok: room: 2 regions, 1 planes', out.getvalue())
            self.assertIn('ok: AWIS1 2 1', out.getvalue())


if __name__ == '__main__':
    unittest.main()
