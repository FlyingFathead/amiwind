# SPDX-License-Identifier: GPL-3.0-only
"""Each flight walked once (BUILD-STAIR-WALK-BORDER-COPIES-41): a CHIM region frame's stair walk covers the cell the
frame owns plus the engine's map-switch margin (chim.collision.frame_walk_areas, from the build's ownership table
chim-regions.json); its border copies of the neighbouring cells are walked where they are owned. The rows of an area
walk are exactly the whole-frame walk's rows inside the area (same steps, flight marks and order), so an unchanged
whole-frame walk gives the area walk without walking. --stair-walk-area frame keeps the earlier whole-frame walk."""
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

from chim import collision  # noqa: E402

LEFT_OUT = (-200.0, -512.0, 512.0, 512.0)   # the fixture's ref 21 flight (x -300 .. -280) is outside


def strip(report):
    return {k: v for k, v in report.items() if k not in ('pass_cache', 'walk_area', 'walk_counts', 'tested', 'tasks')}


class StairWalkArea(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = dict(os.environ)
        for name in ('AMIWIND_STAIR_WALK_REUSE', 'AMIWIND_STAIR_WALK_AREA', 'AMIWIND_PASS_CACHE'):
            os.environ.pop(name, None)
        os.environ.update(AMIWIND_STAIR_WALK_CACHE='cached', AMIWIND_STAIR_WALK_SAMPLE='0',
                          AMIWIND_RUN_VERSION='0.0.42-dev1', AMIWIND_RUN_NAME='2026_10_16_v0.0.42-dev1_full_abc1234')

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.env)
        self.tmp.cleanup()

    def world(self, name, fill=False, core=None, margin=64):
        from test_chim_stairs import world_of
        out = Path(self.tmp.name) / name
        out.mkdir()
        world_of(out, fill)
        if core is not None:
            # the ownership table as tools/chim_regions.py writes it: frame-local core, origin = centre / 4
            table = {'format': 'aw-chim-ownership-1', 'leave_margin': margin, 'terrain_margin': 896,
                     'cell_map_units': 2048, 'frames': [{'cell': [0, 0], 'cells': [[0, 0]], 'core': core,
                                                         'origin': [1024.0, 1024.0, 0.0], 'id': 'rcp0_p0'}]}
            (out / 'chim-regions.json').write_text(json.dumps(table), encoding='utf-8')
        return out

    def gate(self, out, cache=None):
        from chim.validate import Failures, load_world
        if cache is not None:
            os.environ['AMIWIND_PASS_CACHE'] = str(cache)
        else:
            os.environ.pop('AMIWIND_PASS_CACHE', None)
        world = load_world(out, Failures())
        collision._STAIR_CACHE.clear()
        return collision.stair_gate(out, world[5], 1, models=world[4])

    @staticmethod
    def core_for(area, margin=64):
        m = margin + collision.MAXS[0]
        return [[area[0] + m, area[1] + m], [area[2] - m, area[3] - m]]

    def test_area_rows_are_the_whole_walk_rows_inside_it(self):
        whole = self.gate(self.world('whole', fill=True))
        part = self.gate(self.world('part', fill=True, core=self.core_for(LEFT_OUT)))
        rows = lambda r: r['failures'] + r['advisory_failures']  # noqa: E731
        self.assertEqual(whole['status'], 'failed')
        self.assertEqual(part['status'], 'passed')         # the failing flight is a border copy here
        self.assertEqual(part['walk_area']['frames'], 1)
        self.assertGreater(whole['tested'], part['tested'])
        self.assertEqual(json.dumps([r for r in rows(whole) if collision.in_walk_area(LEFT_OUT, r['point'])],
                                    sort_keys=True, default=str), json.dumps(rows(part), sort_keys=True, default=str))

    def test_a_failure_in_the_owned_cell_is_still_found(self):
        whole = self.gate(self.world('whole', fill=True))
        owned = self.gate(self.world('owned', fill=True, core=[[-512, -512], [-100, 512]]))
        self.assertEqual(owned['status'], 'failed')
        self.assertEqual(json.dumps(owned['failures'], sort_keys=True, default=str),
                         json.dumps(whole['failures'], sort_keys=True, default=str))

    def test_a_flight_within_the_switch_margin_is_walked(self):
        # the core ends 40 units before the flight; the map-switch margin (64) plus the box (16) reaches it
        owned = self.gate(self.world('margin', fill=True, core=[[-240, -512], [512, 512]]))
        self.assertEqual(owned['status'], 'failed')
        out = self.gate(self.world('beyond', fill=True, core=[[-240, -512], [512, 512]], margin=0))
        self.assertEqual(out['status'], 'passed')

    def test_frame_mode_is_the_earlier_whole_frame_walk(self):
        whole = self.gate(self.world('whole', fill=True))
        with patch.dict(os.environ, {'AMIWIND_STAIR_WALK_AREA': 'frame'}):
            framed = self.gate(self.world('framed', fill=True, core=self.core_for(LEFT_OUT)))
        self.assertEqual(json.dumps(strip(framed), sort_keys=True, default=str),
                         json.dumps(strip(whole), sort_keys=True, default=str))
        self.assertEqual((framed['walk_area']['frames'], framed['tested']), (0, whole['tested']))
        with patch.dict(os.environ, {'AMIWIND_STAIR_WALK_AREA': 'maybe'}):
            with self.assertRaises(ValueError):
                collision.walk_area_mode()

    def test_cores_outside_the_area_are_not_tasks(self):
        frames = [('p', {'grain': 256, 'low': (0.0, 0.0), 'nx': 16, 'ny': 4}, [])]     # 4 cores in a row
        whole = collision.stair_tasks('w', frames)
        self.assertEqual(len(whole), 4)
        inside = collision.stair_tasks('w', frames, {0: (0.0, 0.0, 1000.0, 1000.0)})
        self.assertEqual([t[2] for t in inside], [whole[0][2]])
        self.assertEqual([t[2] for t in collision.stair_tasks('w', frames, {0: (1000.0, 0.0, 2100.0, 10.0)})],
                         [t[2] for t in whole[:3]])

    def test_an_unchanged_whole_frame_walk_gives_the_area_walk_without_walking(self):
        cache = Path(self.tmp.name) / 'cache'
        with patch.dict(os.environ, {'AMIWIND_STAIR_WALK_AREA': 'frame'}):
            self.gate(self.world('a', fill=True, core=self.core_for(LEFT_OUT)), cache)      # failed: border copy
        fresh = self.gate(self.world('fresh', fill=True, core=self.core_for(LEFT_OUT)))    # no cache: walked
        with patch.object(collision, 'stair_task_in', side_effect=AssertionError('walked')):
            derived = self.gate(self.world('b', fill=True, core=self.core_for(LEFT_OUT)), cache)
        self.assertEqual(derived['walk_area']['derived'], 1)
        self.assertEqual(derived['status'], 'passed')
        self.assertTrue(list(derived['pass_cache']['frames'].values())[0].startswith('derived from its whole-frame'))
        self.assertEqual(json.dumps(strip(derived), sort_keys=True, default=str),
                         json.dumps(strip(fresh), sort_keys=True, default=str))
        # the derived walk is a record of its own: the next build reuses it as a pass
        records = [json.loads(p.read_text(encoding='utf-8'))['row']['record']
                   for p in (cache / 'stair-walk').rglob('*.json')]
        self.assertEqual(sorted(r['outcome'] for r in records), ['failed', 'passed'])
        self.assertEqual([bool(r.get('derived_from')) for r in records if r['outcome'] == 'passed'], [True])
        with patch.object(collision, 'stair_task_in', side_effect=AssertionError('walked')):
            again = self.gate(self.world('c', fill=True, core=self.core_for(LEFT_OUT)), cache)
        self.assertEqual((again['pass_cache']['reused_passes'], again['walk_area']['derived']), (1, 0))
        # a sampled derived frame is walked again and must match
        os.environ['AMIWIND_STAIR_WALK_SAMPLE'] = '1'
        sampled = self.gate(self.world('d', fill=True, core=self.core_for(LEFT_OUT)), cache)
        self.assertEqual(sampled['pass_cache']['walked'], 0)

    def test_a_failing_area_is_not_derived_from_an_unchecked_walk(self):
        cache = Path(self.tmp.name) / 'cache'
        core = [[-512, -512], [-100, 512]]
        with patch.dict(os.environ, {'AMIWIND_STAIR_WALK_AREA': 'frame'}):
            self.gate(self.world('a', fill=True, core=core), cache)
        again = self.gate(self.world('b', fill=True, core=core), cache)
        self.assertEqual((again['walk_area']['derived'], again['pass_cache']['walked'], again['status']),
                         (0, 1, 'failed'))

    def test_whole_frame_keys_do_not_change_and_area_keys_differ(self):
        self.assertNotEqual(collision.stair_area_key_sources(), collision.stair_key_sources())
        selected, uncertain = collision.stair_code_selection('stair_task')
        self.assertFalse(uncertain)
        area, _ = collision.stair_code_selection('stair_task_in')
        self.assertTrue(set(area) <= set(collision.STAIR_WALK_CODE))
        self.assertIn('tools/chim/collision.py', area)

    def test_a_misplaced_table_row_is_refused(self):
        out = self.world('w', core=[[-512, -512], [512, 512]])
        table = json.loads((out / 'chim-regions.json').read_text(encoding='utf-8'))
        table['frames'][0]['origin'] = [0.0, 0.0, 0.0]
        (out / 'chim-regions.json').write_text(json.dumps(table), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'not placed where the ownership table'):
            self.gate(out)

    def test_walk_counts_count_copies_once(self):
        frames = [('a', {'centre': (0.0, 0.0)}, []), ('b', {'centre': (8192.0, 0.0)}, [])]
        row = {'ref': 7, 'kind': 'step', 'point': [1500.0, 10.0, 5.0]}
        copy = dict(row, point=[1500.0 - 2048.0, 10.0, 5.0])
        counted = collision.walk_counts(frames, {0: [row], 1: [copy]})
        self.assertEqual((counted['rows'], counted['distinct'], counted['ratio']), (2, 1, 2.0))


class GateOrder(unittest.TestCase):
    """B15: tools/chim_build.py runs the stair gate first (right after the validation), before the statistics, the
    heap gate and the zone walk; --gate-order stairs-last keeps the order before v0.0.42."""

    def order(self, extra):
        import chim_build
        calls = []
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'out'
            palette = Path(tmp) / 'palette.lmp'
            palette.write_bytes(bytes(768))

            def world(*args, **kwargs):
                out.mkdir(parents=True, exist_ok=True)
                (out / 'chim-receipt.json').write_text('{}', encoding='utf-8')

            def step(name, result):
                def run(*args, **kwargs):
                    calls.append(name)
                    return result
                return run
            with patch('chim.build.build_areas', side_effect=world),                     patch('chim.validate.report_world', side_effect=lambda *a, **k: (
                        calls.append('validation') or {'ok': True, 'failure_count': 0, 'measured': {}}, None, None)),                     patch('chim.validate.report_text', return_value=''),                     patch('chim_build.write_stats', side_effect=step('stats', 0)),                     patch('chim.heap.require_heap', side_effect=step('heap', {'status': 'passed', 'frames': []})),                     patch('chim.zone_sim.require_zone_walk', side_effect=step('zone walk', {'status': 'passed',
                                                                                             'walks': []})),                     patch('chim.collision.require_stairs', side_effect=step('stairs', {'status': 'passed'})):
                code = chim_build.main(['--area', 'balmora', '--data-files', tmp, '--palette', str(palette), '--out',
                                        str(out), '--validate', '--stats', '--jobs', '1', '--pool', 'batch'] + extra)
        self.assertEqual(code, 0)
        return calls

    def test_stairs_first_by_default(self):
        self.assertEqual(self.order([]), ['validation', 'stairs', 'stats', 'heap', 'zone walk'])

    def test_stairs_last_is_the_earlier_order(self):
        self.assertEqual(self.order(['--gate-order', 'stairs-last']), ['validation', 'stats', 'heap', 'zone walk',
                                                                        'stairs'])


if __name__ == '__main__':
    unittest.main()
