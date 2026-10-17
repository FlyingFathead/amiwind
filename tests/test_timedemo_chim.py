# SPDX-License-Identifier: GPL-3.0-only
"""Quake's demo benchmark on CHIM maps (fixlist E7, docs/HARDWARE-BENCHMARK.md "Timedemo").

record / playdemo / timedemo (cl_demo.c) play a recorded demo without a server. A CHIM frame map's world is
grafted on by SV_SpawnServer, so before this a demo of a CHIM map played an empty world (sky, the actors, no
terrain, buildings or statics: measured 2026-10-17 on Balmora's frame, dbg rcount bm 0 wf 0). Now the client starts
the same frame world from the map the demo names, and a timedemo sums the renderer counters over exactly the frames
Quake times, prints them and appends one line to saves/timedemo-results.txt; three timedemos of one demo gave the same
counters (fps differ with the host)."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'


def read(name):
    return (SRC / name).read_text(encoding='latin-1')


class DemoPlaybackStartsTheFrameWorld(unittest.TestCase):
    def test_the_client_starts_chim_for_a_demo(self):
        parse = read('cl_parse.c')
        info = parse[parse.index('cl_entities[0].model = cl.worldmodel = cl.model_precache[1];'):]
        hook = info.index('if (cls.demoplayback && !sv.active && aw_demo_map_begin)')
        self.assertLess(hook, info.index('R_NewMap ();'))          # grafted before the renderer sees the map
        self.assertIn('extern void (*aw_demo_map_begin)(void);', parse)
        self.assertIn('\nvoid (*aw_demo_map_begin)(void);', read('aw_scenery.c'))   # beside the other CHIM map hooks
        world = read('chim/chim_world.c')
        self.assertIn('aw_demo_map_begin = DemoMap;', world)
        demo = world[world.index('static void DemoMap (void)'):]
        self.assertIn('demo_map = 1;\n\tMapBegin (cl.worldmodel->entities);\n\tdemo_map = 0;', demo[:400])
        self.assertIn('return demo_map ? cl.worldmodel : sv.worldmodel;', world)
        begin = world[world.index('static void MapBegin (const char *entities)'):world.index('static void DemoMap (void)')]
        self.assertNotIn('sv.worldmodel', begin)                    # every map reference goes through MapModel ()
        self.assertIn('ChimGraft_Begin (MapModel ())', begin)


class TimedemoCounters(unittest.TestCase):
    def test_one_window_for_the_whole_demo(self):
        rc = read('aw_rcount.c')
        self.assertIn('int on = (aw_rcount_cvar.value > 0 || cls.timedemo) && cls.state == ca_connected;', rc)
        self.assertIn('(cls.timedemo && host_framecount <= cls.td_startframe + 1)', rc)
        self.assertIn('if (now - start < 1.0 || cls.timedemo)', rc)
        done = rc[rc.index('static void timedemo_done(const char *demo, int frames_counted, double seconds)\n{'):]
        self.assertIn('"AWTD1|%s|%d|%ld|%ld|%s\\n"', done)
        self.assertIn('"/timedemo-results.txt"', done)
        self.assertIn('aw_timedemo_done=timedemo_done;', rc)
        demo = read('cl_demo.c')
        finish = demo[demo.index('void CL_FinishTimeDemo (void)\n{'):]
        self.assertIn('if (aw_timedemo_done)\n\t\taw_timedemo_done (timedemo_name, frames, time);', finish)
        self.assertIn('Q_strcpy_bounded (timedemo_name, Cmd_Argv(1), sizeof(timedemo_name));', demo)

    def test_documented(self):
        bench = (ROOT / 'docs' / 'HARDWARE-BENCHMARK.md').read_text(encoding='utf-8')
        self.assertIn('## Timedemo', bench)
        self.assertIn('saves/timedemo-results.txt', bench)


if __name__ == '__main__':
    unittest.main()
