"""tools/crossing_route.py: the route data, the log parsers and the crossing table (CHIM-CROSSING-SLUGGISH-43)."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

import crossing_route as cr  # noqa: E402

CONSOLE = """Memory: 113 MiB Fast RAM free of 128 MiB; CHIM cache 95 MiB in 1 bank (automatic); look-ahead x3
seg ai-e1
Loading AmiWind v0.0.44: rcp2_m6...
CHIM: map frame 2 -6: 9 chunks, 40 files, 120 models, 60 textures, zone 6144 KiB
CHIM: prime at 100 200
CHIM: primed: 9 active, 9 loaded, 120 models, 60 textures, 1000 KiB in 50 reads, 300 ms
Scene ready: rcp2_m6, 500 ms, 9000000 hunk bytes, arrival checked
flight ai-e1 start
Loading AmiWind v0.0.44: rcp3_m6...
CHIM: map frame 3 -6: 9 chunks, 41 files, 130 models, 61 textures, zone 6144 KiB
CHIM: primed: 9 active, 9 loaded, 140 models, 70 textures, 1400 KiB in 70 reads, 210 ms
Scene ready: rcp3_m6, 450 ms, 9100000 hunk bytes, arrival checked
flight ai-e1 end
"""
CELL_LOAD = ("maps/rcp2_m6.chim\t1\t200000\t20\t0.050000\t0.020000\t0.080000\t0.010000\t0.120000\t0\t0\t0\t0\t0\t0\t0\t1.5\n"
             "maps/rcp3_m6.chim\t1\t300000\t30\t0.060000\t0.030000\t0.100000\t0.020000\t0.150000\t0\t0\t0\t0\t0\t0\t0\t1.5\n")
VISIBLE = "maps/rcp2_m6.chim\t1\t0.600000\t131072\t1.50\nmaps/rcp3_m6.chim\t1\t0.520000\t131072\t1.50\n"
STALLS = "time_ms,frame,frame_us\n1000,5,600000\n5000,105,480000\n5500,108,150000\n9000,200,120000\n"
WALK = ("frame,elapsed_ms,frame_us,x100,y100,z100,yaw100,hunk_bytes,distance,world_us,map,server_us,surface_order\n"
        "90,0,1,0,0,0,0,0,0,0,maps/rcp2_m6.chim,0,0\n100,0,1,0,0,0,0,0,0,0,maps/rcp2_m6.chim,0,0\n"
        "110,0,1,0,0,0,0,0,0,0,maps/rcp3_m6.chim,0,0\n")
RC = ('30 frames fps10 150 | bm 1/1/1/1/1 bf 1/1 cf 1 frag 1/1 lf 1 wf 1 | q 1/1/1 e 1/1/1 s 1 sp 1 | sc 1/1 scb 4/900 al 0'
      ' | us 1/1/1/1/1/1/1 pk 480000 | vd 0 ne 1/1 | at 0 ln 0/0/0 | ft 0/0/0 0/0/0/0 | chim 9/9/9 pl 1/1/1 hid 0 fz 0'
      ' rb 1 500/500 gr 0/0/0 0 cw 0 sm -1 ur 0/0 pool 100 zone 1/1 zl 1/1 ev 0 rd 64/3 op 0')


class CrossingRouteTest(unittest.TestCase):
    def test_route_is_fixed_data(self):
        legs = cr.ROUTE['legs']
        self.assertEqual(len({leg['name'] for leg in legs}), len(legs))
        self.assertGreaterEqual(sum(1 for leg in legs if leg['kind'] == 'edge'), 6)
        self.assertGreaterEqual(sum(1 for leg in legs if leg['kind'] == 'corner'), 4)
        self.assertEqual({leg['weight'] for leg in legs}, {'light', 'heavy'})
        # corners first (the first results asked for), then the edges
        kinds = [leg['kind'] for leg in cr.route_legs()]
        self.assertEqual(kinds, sorted(kinds, key=lambda k: k == 'edge'))
        self.assertEqual(cr.leg_base('ai-c1#3'), 'ai-c1')
        loops = [leg for leg in legs if leg.get('loop')]
        self.assertEqual({leg['weight'] for leg in loops}, {'light', 'heavy'})
        for leg in loops:
            # a square around a corner: back at the start after the four sides
            yaws = [t[0] for t in leg['turns']]
            self.assertEqual(yaws[0], leg['yaw'])
            self.assertEqual([(b - a) % 360 for a, b in zip(yaws, yaws[1:])], [90, 90, 90])
            # the square's middle is a cell corner
            side = 470 * leg['turns'][0][1]
            x, y = leg['start']
            cx = x + side / 2 * (cr.math.cos(cr.math.radians(yaws[0])) + cr.math.cos(cr.math.radians(yaws[1])))
            cy = y + side / 2 * (cr.math.sin(cr.math.radians(yaws[0])) + cr.math.sin(cr.math.radians(yaws[1])))
            self.assertLess(cr.corner_distance(cx, cy), 60, leg['name'])
            self.assertEqual(len({t[1] for t in leg['turns']}), 1)
            self.assertEqual(cr.leg_seconds(leg), sum(t[1] for t in leg['turns']))
        for leg in legs:
            if leg.get('loop'):
                continue
            x, y = leg['start']
            path = [(x + t * cr.math.cos(cr.math.radians(leg['yaw'])), y + t * cr.math.sin(cr.math.radians(leg['yaw'])))
                    for t in range(0, 4001, 16)]
            nearest = min(cr.corner_distance(*p) for p in path)
            if leg['kind'] == 'corner':
                # a corner leg flies diagonally through a cell corner
                self.assertLess(nearest, 16, leg['name'])
            else:
                # an edge leg stays far from every corner
                self.assertGreater(nearest, 2000, leg['name'])

    def test_model_names(self):
        self.assertTrue(cr.model_is('maps/vf1248.chim', 'vf1248'))
        self.assertTrue(cr.model_is('maps/balmora-chim.chim', 'balmora'))
        self.assertFalse(cr.model_is('maps/vf12480.chim', 'vf1248'))

    def test_corner_distance(self):
        self.assertEqual(cr.corner_distance(8192, -8192), 0)
        self.assertEqual(cr.corner_distance(8192 + 300, -8192 + 400), 500)

    def test_parse_console_marks_crossings(self):
        c = cr.parse_console(CONSOLE)
        self.assertTrue(c['memory'].startswith('Memory: 113 MiB'))
        self.assertEqual([ld['map'] for ld in c['loads']], ['rcp2_m6', 'rcp3_m6'])
        self.assertEqual([ld['crossing'] for ld in c['loads']], [False, True])
        self.assertEqual(c['loads'][1]['ready_ms'], 450)
        self.assertEqual(c['loads'][1]['prime_kib'], 400)
        self.assertEqual(c['loads'][1]['prime_reads'], 20)
        self.assertEqual(c['loads'][1]['frame']['x'], 3)

    def test_parse_rcount(self):
        f = cr.parse_rcount(RC)
        self.assertEqual(f['frames'], 30)
        self.assertEqual(f['pk_ms'], 480)
        self.assertEqual((f['scb_blocks'], f['scb_texels']), (4, 900))
        self.assertEqual((f['rd_kib'], f['rd_reads']), (64, 3))
        self.assertEqual(f['rb'], 1)

    def test_parse_session_and_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / 'run1'
            (d / 'awctl').mkdir(parents=True)
            (d / 'hdflogs').mkdir()
            (d / 'awctl' / 'console.log').write_text(CONSOLE)
            (d / 'hdflogs' / 'cell-load-profile.tsv').write_text(CELL_LOAD)
            (d / 'hdflogs' / 'cell-visible-profile.tsv').write_text(VISIBLE)
            (d / 'hdflogs' / 'frame-stalls.csv').write_text(STALLS)
            (d / 'hdflogs' / 'walk-profile.csv').write_text(WALK)
            (d / 'session.json').write_text(json.dumps({'fast_mb': 128}))
            samples = [
                {'t': 1.0, 'leg': 'ai-e1', 'flight': True, 'server': 'rcp2_m6', 'global': [24400, -45056, 2600], 'rcount': None},
                {'t': 1.5, 'leg': 'ai-e1', 'flight': True, 'server': 'rcp3_m6', 'global': [24700, -45056, 2600], 'rcount': RC},
                {'t': 3.0, 'leg': 'ai-e1', 'flight': True, 'server': 'rcp3_m6', 'global': [25200, -45056, 2600], 'rcount': RC},
            ]
            (d / 'samples.jsonl').write_text(''.join(json.dumps(s) + '\n' for s in samples))
            r = cr.parse_session(d)
            self.assertEqual(len(r['crossings']), 1)
            c = r['crossings'][0]
            self.assertEqual((c['from'], c['to'], c['kind'], c['weight']), ('rcp2_m6', 'rcp3_m6', 'edge', 'light'))
            self.assertEqual(c['stall']['frame_ms'], 480)
            self.assertEqual(c['stall']['window_ms'], 630)
            self.assertEqual(c['load']['disk_bytes'], 300000)
            self.assertEqual(c['split_ms']['map_read'], 60)
            self.assertEqual(c['split_ms']['map_parse'], 40)
            self.assertEqual(c['split_ms']['ring_prime'], 210)
            self.assertEqual(c['split_ms']['ready_to_visible'], 70)
            self.assertEqual(c['after_3s']['surface_blocks'], 120)
            self.assertEqual(c['after_3s']['chim_kib'], 64)
            self.assertEqual(c['at'], [24550, -45056])
            self.assertEqual(r['teleports'][0]['map'], 'rcp2_m6')
            md = cr.table([r])
            self.assertIn('| 128 MB | edge | all | 1 | 480 / 480 | 630 / 630 | 450 / 450 | 293 / 30 | 400 / 20 | 27 |', md)
            self.assertIn('| 128 MB | edge | light | 1 | 60 | 40 |', cr.split_table([r]))
            # without the engine's diagnostic logs: the stall from the rcount second, no section split
            for f in (d / 'hdflogs').iterdir():
                f.unlink()
            r2 = cr.parse_session(d)
            c2 = r2['crossings'][0]
            self.assertEqual(c2['stall'], {'frame_ms': 480, 'source': 'rcount'})
            self.assertNotIn('split_ms', c2)
            self.assertIn('| 480 / 480 | - / - |', cr.table([r2]))


if __name__ == '__main__':
    unittest.main()
