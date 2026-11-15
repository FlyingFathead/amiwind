# SPDX-License-Identifier: GPL-3.0-only
"""Per-node movers of animated world objects (tools/object_movers.py, ENDGAME-CHAMBER-COLLAPSE-63, DOOR-MOVERS-56).

Synthetic data only (the model and keyframe files of tests/test_creature_pose.py): a group that moves one node is
found with how far it moves, the still nodes are not movers, the track record round-trips within its steps, sound
keys land on their frames, and a bad record is refused."""
import math
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# src/ ahead of tools/: tools/mwad.py would hide the src/mwad package (BUILD-ACTOR-LIBRARY-MWAD-PATH-47)
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools'), str(ROOT / 'tests')]

import object_movers as M  # noqa: E402


class Rig(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from test_creature_pose import FILES, model, kf, reader
        import creature_pose
        from prepare_scenery import nif_reader
        files = dict(FILES)
        files['meshes/i/xthing.nif'] = model()
        files['meshes/i/xthing.kf'] = kf(
            [(0.0, 'idle: start'), (0.0, 'idle: stop'), (0.0, 'death1: start'), (0.5, 'sound: endboom1'),
             (2.0, 'death1: stop')],
            [(b'Bone', (1, [(0.0, (0, 0, 0)), (2.0, (80, 0, 0))]))])
        files['meshes/i/thing.nif'] = b'plain'
        cls.rig = creature_pose.CreatureRig(nif_reader(), reader(files), 'meshes/i/thing.nif', False)

    def test_window(self):
        self.assertEqual(M.group_window(self.rig, 'death1')[1:], (0.0, 2.0))
        with self.assertRaises(ValueError):
            M.group_window(self.rig, 'death2')

    def test_only_the_keyed_node_moves(self):
        nodes = M.moved_nodes(self.rig, 'death1')
        self.assertEqual([n['name'] for n in nodes], ['bone'])
        self.assertAlmostEqual(nodes[0]['move'], 80.0, places=1)
        self.assertLess(nodes[0]['turn'], 0.5)

    def test_track_and_record_round_trip(self):
        nodes = M.moved_nodes(self.rig, 'death1')
        track = M.tracks(self.rig, 'death1', nodes)
        n = nodes[0]['node']
        self.assertEqual(len(track[n]), 17)                     # 2 s at 8 frames a second, both ends
        self.assertAlmostEqual(track[n][-1][0] - track[n][0][0], 80.0, places=3)
        sounds = M.sound_keys(self.rig, 'death1')
        self.assertEqual(sounds, [(4, 'endboom1')])
        data = M.pack({n: 'bone'}, track, sounds=sounds)
        back = M.unpack(data)
        self.assertEqual((back['names'], back['sounds'], back['rate']), ({n: 'bone'}, sounds, 8.0))
        for a, b in zip(track[n], back['track'][n]):
            for x, y in zip(a[:3], b[:3]):
                self.assertLessEqual(abs(x - y), back['unit'])
            for x, y in zip(a[3:], b[3:]):
                self.assertLessEqual(abs(x - y), 1.0 / M.Q)
        sheet = M.budget(data, nodes)
        self.assertEqual((sheet['movers'], sheet['frames'], sheet['seconds']), (1, 17, 2.0))
        self.assertEqual(sheet['record_bytes'], len(data))


class Riders(unittest.TestCase):
    """A geometry node fixed on a moving limb rides the limb (one track); a node turning on it stays a mover."""

    def rig(self, child_turns):
        import numpy as np

        class Fake:
            model = 'fake'
            nodes = [('root', -1), ('limb', 0), ('piece', 1)]
            sources = [{'events': {'death1: start': 0.0, 'death1: stop': 1.0}, 'keys': []}]

            def worlds(self, si, t):
                def m(angle, x):
                    c, s = math.cos(angle), math.sin(angle)
                    out = np.eye(4)
                    out[:3, :3] = [[c, s, 0], [-s, c, 0], [0, 0, 1]]
                    out[3, :3] = [x, 0, 0]
                    return out
                limb = m(0.0, 100.0 * t)
                piece = m(child_turns * t, 0.0) @ limb
                return [np.eye(4), limb, piece]
        return Fake()

    def test_fixed_piece_rides(self):
        riders = []
        movers = M.moved_nodes(self.rig(0.0), 'death1', riders=riders)
        self.assertEqual([n['name'] for n in movers], ['limb'])
        self.assertEqual([(n['name'], n['rides']) for n in riders], [('piece', 'limb')])

    def test_turning_piece_is_a_mover(self):
        movers = M.moved_nodes(self.rig(1.0), 'death1')
        self.assertEqual([n['name'] for n in movers], ['limb', 'piece'])

    def test_ride_off_keeps_every_moved_node(self):
        self.assertEqual(len(M.moved_nodes(self.rig(0.0), 'death1', ride=False)), 2)


class Format(unittest.TestCase):
    def test_quaternion_of_a_quarter_turn(self):
        c, s = math.cos(math.pi / 2), math.sin(math.pi / 2)
        row = [[c, s, 0], [-s, c, 0], [0, 0, 1]]                # p @ row turns +x to +y: 90 degrees about z
        q = M.quaternion(row)
        self.assertAlmostEqual(q[0], math.sqrt(.5), places=6)
        self.assertAlmostEqual(q[3], math.sqrt(.5), places=6)

    def test_bad_records_refused(self):
        with self.assertRaises(ValueError):
            M.pack({}, {})
        with self.assertRaises(ValueError):
            M.pack({1: 'a', 2: 'b'}, {1: [(0,) * 7] * 3, 2: [(0,) * 7] * 4})
        good = M.pack({1: 'a'}, {1: [(1, 2, 3, 1, 0, 0, 0)] * 2})
        with self.assertRaises(ValueError):
            M.unpack(b'XXXX' + good[4:])
        with self.assertRaises(ValueError):
            M.unpack(good + b'\0')
        with self.assertRaises(ValueError):
            M.unpack(good[:4] + struct.pack('>H', 9) + good[6:])

    def test_record_size(self):
        data = M.pack({1: 'a'}, {1: [(0, 0, 0, 1, 0, 0, 0)] * 214}, sounds=[(0, 'endboom1')])
        self.assertEqual(len(data), 20 + 36 + 32 + 214 * 14)


if __name__ == '__main__':
    unittest.main()
