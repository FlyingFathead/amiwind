# SPDX-License-Identifier: GPL-3.0-only
"""READY-MAGIC-SHOWS-WEAPON-65 (v0.0.66): readied magic shows open hands and the bare hands fists, checked on the data
an image ships (tools/ready_hands.py; the image step runs it, tools/build_aga.py finalize_image). The measures and their
refusals on small built tables and models: a table whose spell stances hold the fists of hand to hand (the stand-in
v0.0.65 shipped) or whose fists are open is refused, as is a baked spell model that reaches no further than the fists."""
import math
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))

FIST_TURN = 68.0     # per joint: 8 joints, 544 degrees, the original's idlehh (545)
OPEN_TURN = 13.0     # per joint: 104 degrees, the original's idlespell (103 to 130)


def bones_and_parents():
    bones, parents = ['bip01'], [-1]
    for side in ('r', 'l'):
        bones.append('bip01 %s hand' % side)
        parents.append(0)
        hand = len(bones) - 1
        for n in (1, 2, 3, 4):
            bones.append('bip01 %s finger%d' % (side, n))
            parents.append(hand)
            knuckle = len(bones) - 1
            for j in (1, 2):
                bones.append('bip01 %s finger%d%d' % (side, n, j))
                parents.append(knuckle if j == 1 else len(bones) - 2)
    return bones, parents


def table(turns):
    """A first-person table in the engine's format (skeletal_actor.write_table): per group in the order of TURNS
    ({group: degrees per curl joint}) 28 frames, every finger's middle and end joint turned so about z."""
    import numpy as np
    import skeletal_actor as sa
    bones, parents = bones_and_parents()
    groups, rot, pos = {}, [], []
    for group, degrees in turns.items():
        groups[group] = (len(rot), len(rot) + 27)
        for _ in range(28):
            frame = np.zeros((len(bones), 4))
            frame[:, 0] = 1.0
            for b, name in enumerate(bones):
                if name[-2:].isdigit() and 'finger' in name:
                    a = math.radians(degrees) / 2
                    frame[b] = (math.cos(a), 0.0, 0.0, math.sin(a))
            rot.append(frame)
            pos.append(np.full((len(bones), 3), 1.5))
    q, p, scale = sa.quantise_table(np.array(rot), np.array(pos))
    return sa.write_table(parents, groups, q, p, scale), bones


class TableCheck(unittest.TestCase):
    def test_fists_and_open_spell_hands_pass(self):
        import ready_hands as rh
        data, bones = table({'hh': FIST_TURN, 'sps': OPEN_TURN, 'spt': OPEN_TURN, 'sp': OPEN_TURN})
        summary = rh.table_check(data, bones)
        self.assertAlmostEqual(summary['hh'][0], 8 * FIST_TURN, delta=2)
        for s in rh.SPELL_STANCES:
            self.assertAlmostEqual(summary[s][1], 8 * OPEN_TURN, delta=2)

    def test_spell_stance_with_the_fists_is_refused(self):
        # the magic stance holding the hand-to-hand fists (v0.0.65's stand-in): R and F would look alike
        import ready_hands as rh
        data, bones = table({'hh': FIST_TURN, 'sps': OPEN_TURN, 'spt': OPEN_TURN, 'sp': FIST_TURN})
        with self.assertRaisesRegex(ValueError, 'Readied-magic hands not open: spell stance sp'):
            rh.table_check(data, bones)

    def test_open_fists_are_refused(self):
        import ready_hands as rh
        data, bones = table({'hh': OPEN_TURN, 'sps': OPEN_TURN, 'spt': OPEN_TURN, 'sp': OPEN_TURN})
        with self.assertRaisesRegex(ValueError, 'First-person fists not closed'):
            rh.table_check(data, bones)

    def test_a_table_without_the_spell_stances_is_refused(self):
        import ready_hands as rh
        data, bones = table({'hh': FIST_TURN})
        with self.assertRaisesRegex(ValueError, 'no group sps'):
            rh.table_check(data, bones)

    def test_the_measure_is_the_turn(self):
        import numpy as np
        import ready_hands as rh
        a = math.radians(30)
        m = np.array([[math.cos(a), math.sin(a), 0], [-math.sin(a), math.cos(a), 0], [0, 0, 1]])
        self.assertAlmostEqual(rh.turn_degrees(m), 30.0, places=6)
        self.assertAlmostEqual(rh.hand_curl(lambda name: m, 'r'), 240.0, places=4)


def alias_model(points):
    """A one-frame vertex alias model (Quake mdl, one 8 x 8 skin, one triangle) holding POINTS."""
    import numpy as np
    points = np.asarray(points, float)
    origin, scale = np.array([-20.0, -20.0, -20.0]), np.array([.2, .2, .2])
    nv = len(points)
    head = struct.pack('<4si3f3ff3f8if', b'IDPO', 6, *scale, *origin, 10.0, 0, 0, 0, 1, 8, 8, nv, 1, 1, 0, 0, 0.0)
    assert len(head) == 84
    body = struct.pack('<i', 0) + bytes(64) + bytes(nv * 12) + struct.pack('<4i', 1, 0, 1, 2)
    verts = np.clip(np.round((points - origin) / scale), 0, 255).astype(np.uint8)
    frame = struct.pack('<i', 0) + bytes(8) + b'idle'.ljust(16, b'\0') + \
        b''.join(bytes((int(v[0]), int(v[1]), int(v[2]), 0)) for v in verts)
    return head + body + frame


JOINTS = {('r', 'hand'): (10.0, -5.0, 0.0), ('r', 'forearm'): (5.0, -5.0, 0.0),
          ('l', 'hand'): (10.0, 5.0, 0.0), ('l', 'forearm'): (5.0, 5.0, 0.0)}


def hands(reach):
    """Both hands' vertices: 24 each in front of the hand joint, out to REACH."""
    import numpy as np
    out = []
    for side in ('r', 'l'):
        x, y, z = JOINTS[(side, 'hand')]
        for i in range(24):
            t = (i % 6 + 1) / 6.0
            out.append((x + reach * t, y + (i // 6 - 1.5) * .3, z + ((i % 3) - 1) * .3))
    return np.array(out)


class BakedCheck(unittest.TestCase):
    def setUp(self):
        import numpy as np
        import ready_hands as rh
        self.rh = rh
        self.saved = rh.view_joints
        rh.view_joints = lambda skeleton, stance, frame=0: {k: np.array(v) for k, v in JOINTS.items()}

    def tearDown(self):
        self.rh.view_joints = self.saved

    def stage(self, tmp, spell_reach):
        from prepare_hand_catalog import model_paths, pack_catalog
        id1 = Path(tmp)
        (id1 / 'gfx').mkdir()
        (id1 / 'progs/hands').mkdir(parents=True)
        hand, torch = model_paths('nord', False)
        (id1 / 'gfx/hand-models.awh').write_bytes(pack_catalog([{'race': 'nord', 'female': False, 'hand_model': hand,
                                                                  'torch_model': torch}]))
        (id1 / hand).write_bytes(alias_model(hands(2.1)))
        (id1 / (hand[:-4] + '_sp.mdl')).write_bytes(alias_model(hands(spell_reach)))
        return id1

    def test_open_spell_arms_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self.rh.baked_check(None, self.stage(tmp, 3.2))
        (model, ratios), = out.items()
        self.assertEqual(model, 'progs/hands/nord_m_sp.mdl')
        self.assertGreater(min(ratios), self.rh.OPEN_MIN_REACH)

    def test_spell_arms_with_the_fists_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'Readied-magic hands not open in progs/hands/nord_m_sp.mdl'):
                self.rh.baked_check(None, self.stage(tmp, 2.1))

    def test_model_frame_reads_the_points(self):
        import numpy as np
        points = hands(3.0)
        got = self.rh.model_frame(alias_model(points), 0)
        self.assertTrue(np.allclose(got, points, atol=.11))


class ImageStep(unittest.TestCase):
    def test_the_image_step_runs_the_check(self):
        source = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        tail = source[source.index('def finalize_image(args):'):]
        self.assertIn("from ready_hands import image_check as ready_hands_check", tail)
        self.assertIn("ready_hands_check(args.data_files,boot/'id1')", tail)
        # after the hand catalogue is installed (both first-person paths are in the image then)
        self.assertLess(tail.index('install_hand_catalog(args.hand_catalog'), tail.index('ready_hands_check(args'))


if __name__ == '__main__':
    unittest.main()
