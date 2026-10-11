# SPDX-License-Identifier: GPL-3.0-only
"""Counted progress lines read [done/total work | done/total containers] stage: unit: result (tools/progress_line.py),
and the stair walks count their real work: done reaches the total of steps and ramps."""
import contextlib
import io
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src'), str(ROOT / 'tests')]

import progress_line  # noqa: E402

LINE = re.compile(r'^\[(\d+)/(\d+) stairs \| (\d+)/(\d+) (frames|maps)\] (CHIM stair gate|Stair walk): ([^:]+): '
                  r'(\d+) steps and ramps, (\d+) failed \((.+)\)$')


class ProgressLineTests(unittest.TestCase):
    def test_the_counters_come_first(self):
        self.assertEqual(progress_line.line('CHIM stair gate', 'frames/x+21/y-08', '51 steps and ramps, 0 failed (walked)',
                                            (12034, 15415, 'stairs'), (246, 273, 'frames')),
                         '[12034/15415 stairs | 246/273 frames] CHIM stair gate: frames/x+21/y-08: '
                         '51 steps and ramps, 0 failed (walked)')
        self.assertEqual(progress_line.line('Mesh census', None, None, (251, 9000, 'meshes')),
                         '[251/9000 meshes] Mesh census')
        self.assertEqual(progress_line.line('Sound import', None, None, (100, 200)), '[100/200] Sound import')
        self.assertEqual(progress_line.line('Stage', 'unit', 'done'), 'Stage: unit: done')
        out = io.StringIO()
        progress_line.emit('Music', 'a.mp3', 'converted', (1, 2, 'tracks'), stream=out)
        self.assertEqual(out.getvalue(), '[1/2 tracks] Music: a.mp3: converted\n')

    def test_legacy_stair_walk_counts_its_steps_and_ramps(self):
        import pass_cache
        import stair_walk
        from test_stair_walk import build
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'maps').mkdir()
            (root / 'maps' / 'room.bsp').write_bytes(build(fill=True))
            (root / 'maps' / 'hall.bsp').write_bytes(build())
            out = io.StringIO()
            with patch.dict(os.environ, {pass_cache.ENV: 'off'}), contextlib.redirect_stdout(out):
                report = stair_walk.check(root, jobs=1)
        lines = [m.groups() for m in map(LINE.match, out.getvalue().splitlines()) if m]
        self.assertEqual([g[6] for g in lines], ['hall', 'room'])
        self.assertEqual([(g[2], g[3]) for g in lines], [('1', '2'), ('2', '2')])
        done, total = int(lines[-1][0]), int(lines[-1][1])
        self.assertEqual(done, total)                        # the count before the walk is the walk's own work
        rows = sum(int(g[7]) for g in lines)
        self.assertGreaterEqual(total, rows)                 # (a candidate under water gives no row)
        self.assertGreater(rows, 0)
        self.assertEqual(report['status'] in ('passed', 'failed'), True)

    def test_chim_stair_gate_prints_one_counted_line_per_frame(self):
        from test_chim_format import fixture
        from chim.collision import stair_gate
        from chim.validate import Failures, load_world
        with tempfile.TemporaryDirectory() as temp:
            world_dir = Path(temp) / 'w'
            fixture(world_dir)
            world = load_world(world_dir, Failures())
            out = io.StringIO()
            with patch.dict(os.environ, {'AMIWIND_PASS_CACHE': 'off'}), contextlib.redirect_stdout(out):
                stair_gate(world_dir, world[5], 1, models=world[4])
        lines = [m.groups() for m in map(LINE.match, out.getvalue().splitlines()) if m]
        self.assertEqual(len(lines), len(world[5]))
        self.assertEqual((lines[-1][0], lines[-1][2], lines[-1][3]), (lines[-1][1], str(len(world[5])),
                                                                       str(len(world[5]))))
        self.assertEqual(lines[-1][9], 'walked')


if __name__ == '__main__':
    unittest.main()
