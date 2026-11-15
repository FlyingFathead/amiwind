# SPDX-License-Identifier: GPL-2.0-or-later
"""The engine's object track reader (engine/aga/src/aw_track.c, ENDGAME-CHAMBER-COLLAPSE-63) against the builder's
writer (tools/object_movers.py pack): the same movers, the same transforms at the frames and between them, the last
frame held, the sound keys in their windows, and a damaged record refused. Synthetic tracks only, no game data."""
import math
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'engine/aga/src'
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

import object_movers as M  # noqa: E402


def quarter(axis_turn):
    """(w, x, y, z) of a turn of AXIS_TURN radians about z."""
    return (math.cos(axis_turn / 2), 0.0, 0.0, math.sin(axis_turn / 2))


@unittest.skipUnless(shutil.which('cc'), 'no C compiler')
class TrackNative(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        scratch = Path(cls.tmp.name)
        cls.exe = scratch / 'track-check'
        compiled = subprocess.run(['cc', '-std=gnu89', '-O1', '-fsanitize=undefined', '-fno-sanitize-recover=all',
                                   '-I' + str(SOURCE), str(ROOT / 'tests/aga_track_test.c'), str(SOURCE / 'aw_track.c'),
                                   '-lm', '-o', str(cls.exe)], capture_output=True, text=True)
        assert compiled.returncode == 0, compiled.stdout + compiled.stderr
        # mover 7 slides 80 units along x over 2 s; mover 9 turns a half turn about z
        frames = 17
        slide = [(80.0 * i / (frames - 1), 0.0, 4.0) + (1.0, 0.0, 0.0, 0.0) for i in range(frames)]
        turn = [(0.0, 0.0, 0.0) + quarter(math.pi * i / (frames - 1)) for i in range(frames)]
        cls.data = M.pack({7: 'lknee', 9: 'waist'}, {7: slide, 9: turn}, sounds=[(4, 'endboom1'), (12, 'endboom2')])
        cls.record = scratch / 'track.bin'
        cls.record.write_bytes(cls.data)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_check(self, *args, record=None):
        return subprocess.run([str(self.exe), str(record or self.record), *map(str, args)], capture_output=True, text=True)

    def test_info(self):
        r = self.run_check('info')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.splitlines(), ['movers 2 frames 17 rate 8 seconds 2', 'mover 7 lknee', 'mover 9 waist'])

    def sample(self, m, seconds):
        r = self.run_check('sample', m, seconds)
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = r.stdout.split('\n')
        return [float(v) for v in lines[0].split()], [[float(v) for v in l.split()] for l in lines[1:4]]

    def test_slide_at_and_between_frames_and_held(self):
        for seconds, x in ((0, 0.0), (0.5, 20.0), (0.5625, 22.5), (2.0, 80.0), (5.0, 80.0), (-1, 0.0)):
            v, _ = self.sample(0, seconds)
            self.assertAlmostEqual(v[0], x, delta=0.01)
            self.assertAlmostEqual(v[2], 4.0, delta=0.01)

    def test_turn_matches_the_builder_quaternion(self):
        v, m = self.sample(1, 1.0)                       # a quarter turn about z
        self.assertAlmostEqual(v[3], math.cos(math.pi / 4), places=3)
        self.assertAlmostEqual(v[6], math.sin(math.pi / 4), places=3)
        # the row-vector matrix the builder's quaternion() reads back as the same turn
        back = M.quaternion(m)
        for a, b in zip(back, v[3:]):
            self.assertAlmostEqual(a, b, places=3)
        # +x turns to +y
        self.assertAlmostEqual(m[0][1], 1.0, places=3)

    def test_sounds_in_their_windows(self):
        self.assertEqual(self.run_check('sounds', -1, 0.5).stdout.split(), ['endboom1'])
        self.assertEqual(self.run_check('sounds', 0.5, 1.5).stdout.split(), ['endboom2'])
        self.assertEqual(self.run_check('sounds', 1.5, 2.0).stdout.split(), [])

    def test_damaged_records_refused(self):
        bad = Path(self.tmp.name) / 'bad.bin'
        for raw in (b'XXXX' + self.data[4:], self.data[:-1], self.data + b'\0',
                    self.data[:4] + bytes([0, 2]) + self.data[6:]):
            bad.write_bytes(raw)
            self.assertEqual(self.run_check('info', record=bad).returncode, 2)


if __name__ == '__main__':
    unittest.main()
