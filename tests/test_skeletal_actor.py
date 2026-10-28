# SPDX-License-Identifier: GPL-3.0-only
"""Shared animation tables (tools/skeletal_actor.py, docs/MODULAR_NPCS.md method C) on synthetic skeletons: the
posed vertices from bone space equal today's baked skinning (tools/npc_geometry.py assemble), the table round trip,
joint blends and the group ranges. No game data."""
import math
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]     # src first: its mwad package, not tools/mwad.py
import skeletal_actor as S  # noqa: E402


def axis_quat(axis, degrees):
    a = np.asarray(axis, float) / np.linalg.norm(axis)
    h = math.radians(degrees) / 2
    return np.array([math.cos(h), *(a * math.sin(h))])


class Chain:
    """A three-bone chain: root at the origin, upper arm 10 units up, forearm 10 more; the arm bends with time."""
    parents = {'root': None, 'upper': 'root', 'fore': 'upper'}

    def local(self, name, time):
        if name == 'root':
            return S.local_matrix(axis_quat((0, 0, 1), 30 * time), (1.0, 2.0, 0.0))
        if name == 'upper':
            return S.local_matrix(axis_quat((1, 0, 0), 20 * time), (0.0, 0.0, 10.0))
        return S.local_matrix(axis_quat((0, 1, 0), 45 * time), (0.0, 0.0, 10.0))


class QuaternionTests(unittest.TestCase):
    def test_matrix_and_quaternion_round_trip(self):
        for axis, deg in (((0, 0, 1), 30), ((1, 1, 0), 170), ((1, -2, 3), 359), ((0, 1, 0), 0)):
            q = axis_quat(axis, deg)
            q = q if q[0] >= 0 else -q
            np.testing.assert_allclose(S.matrix_to_quat(S.quat_to_matrix(q)), q, atol=1e-9)

    def test_row_vector_rotation_matches_the_reader(self):
        # npc_geometry.quat_matrix: Rotation.from_quat(xyzw).as_matrix().T, a point turns as p @ R
        r = S.quat_to_matrix(axis_quat((0, 0, 1), 90))
        np.testing.assert_allclose(np.array([1.0, 0, 0]) @ r, [0, 1, 0], atol=1e-12)


class PoseTests(unittest.TestCase):
    def setUp(self):
        self.chain = Chain()
        self.bones = S.bone_order(Chain.parents, ['fore'])
        self.parents = [-1 if Chain.parents[b] is None else self.bones.index(Chain.parents[b]) for b in self.bones]

    def world_by_name(self, time):
        """npc_geometry.Skeleton.pose: world = local @ world(parent)."""
        out = {}

        def world(name):
            if name not in out:
                p = Chain.parents[name]
                out[name] = self.chain.local(name, time) @ (world(p) if p else np.eye(4))
            return out[name]
        return world

    def test_bones_are_parent_first(self):
        self.assertEqual(self.bones, ['root', 'upper', 'fore'])
        with self.assertRaises(ValueError):
            S.pose_matrices([1, -1], [np.eye(4), np.eye(4)])

    def test_bone_space_skinning_equals_the_baked_skinning(self):
        # a shape in bind pose (time 0): two vertices on the forearm, one on the upper arm, one joint vertex
        bind = self.world_by_name(0.0)
        inverse = {i: np.linalg.inv(bind(b)) for i, b in enumerate(self.bones)}
        vertices = np.array([[1.0, 2.0, 25.0], [1.5, 2.0, 28.0], [1.0, 2.5, 15.0], [1.0, 2.0, 20.0]])
        weights = {1: ([2, 3], [1.0, 0.4]), 2: ([0, 1, 3], [1.0, 1.0, 0.6])}
        bone, second, weight, rest, rest2 = S.bind_skinned(vertices, weights, inverse)
        self.assertEqual(list(bone), [2, 2, 1, 2])
        self.assertEqual(list(second), [-1, -1, -1, 1])
        self.assertAlmostEqual(weight[3], 0.4)
        for t in (0.0, 0.7, 2.0):
            pose = self.world_by_name(t)
            world = S.pose_matrices(self.parents, [self.chain.local(b, t) for b in self.bones])
            for i, b in enumerate(self.bones):
                np.testing.assert_allclose(world[i], pose(b), atol=1e-12)
            # the baked way (npc_geometry.assemble): sum over bones of hom @ inverse_bind @ pose(bone) x weight
            hom = np.column_stack((vertices, np.ones(len(vertices))))
            baked = np.zeros((len(vertices), 3))
            total = np.zeros(len(vertices))
            for bi, (ids, ws) in weights.items():
                for v, w in zip(ids, ws):
                    baked[v] += (hom[v] @ inverse[bi] @ pose(self.bones[bi]))[:3] * w
                    total[v] += w
            baked /= total[:, None]
            posed = S.skin(rest, bone, second, weight, world, rest2)
            np.testing.assert_allclose(posed, baked, atol=1e-9)

    def test_a_weak_second_bone_is_dropped(self):
        inverse = {0: np.eye(4), 1: np.eye(4)}
        bone, second, weight, _, _ = S.bind_skinned(np.zeros((1, 3)), {0: ([0], [0.9]), 1: ([0], [0.1])}, inverse)
        self.assertEqual((bone[0], second[0], weight[0]), (0, -1, 0.0))


class TableTests(unittest.TestCase):
    def test_sampled_table_round_trips_within_a_step(self):
        chain = Chain()
        bones = S.bone_order(Chain.parents, ['fore'])
        times = S.table_frames(0.0, 2.0)
        self.assertEqual(len(times), int(2 * S.TABLE_RATE) + 1)     # 8 a second (SKEL-TABLE-SIZE-52)
        rot, pos = S.sample_table(chain, bones, times)
        # neighbouring frames stay on the same side, so the engine's nlerp never takes the long way
        self.assertTrue(np.all(np.einsum('fbq,fbq->fb', rot[1:], rot[:-1]) >= 0))
        q, p, scale = S.quantise_table(rot, pos)
        self.assertEqual((q.dtype, p.dtype), (np.int16, np.int16))
        r2, p2 = S.dequantise_table(q, p, scale)
        # stored with w >= 0 (q and -q are one rotation), w rebuilt from x y z
        self.assertTrue(np.all(r2[..., 0] >= 0))
        np.testing.assert_allclose(r2, np.where(rot[..., :1] < 0, -rot, rot), atol=1e-3)
        np.testing.assert_allclose(p2, pos, atol=scale)

    def test_still_and_turning_bones_store_no_frames(self):
        """Version 2: a bone that never changes is stored once, one that only turns without its position; the table
        read back gives every bone at every frame as written."""
        rng = np.random.default_rng(3)
        frames = 6
        rot = rng.normal(size=(frames, 3, 4))
        rot /= np.linalg.norm(rot, axis=-1, keepdims=True)
        rot[:, 0] = rot[0, 0]                   # bone 0 still
        pos = rng.uniform(-20, 20, size=(frames, 3, 3))
        pos[:, 0] = pos[0, 0]
        pos[:, 1] = pos[0, 1]                   # bone 1 turns only; bone 2 moves
        q, p, scale = S.quantise_table(rot, pos)
        self.assertEqual(S.bone_kinds(q, p), [S.STILL, S.TURNS, S.MOVES])
        data = S.write_table([-1, 0, 1], {'idle': (0, frames - 1)}, q, p, scale)
        head = 24 + 8 + 4 + 32 + 3 * 12
        self.assertEqual(len(data), head + frames * (6 + 12))
        table = S.read_table(data)
        self.assertEqual(table['kinds'], [S.STILL, S.TURNS, S.MOVES])
        np.testing.assert_array_equal(table['p'], p)
        np.testing.assert_allclose(table['q'], S.stored_quats(q))
        r1, _ = S.dequantise_table(q, p, scale)
        r2, _ = S.dequantise_table(table['q'], table['p'], scale)
        np.testing.assert_allclose(r1, r2)

    def test_a_scaled_bone_is_refused(self):
        class Scaled(Chain):
            def local(self, name, time):
                m = Chain.local(self, name, time)
                m[:3, :3] *= 1.5
                return m
        with self.assertRaises(ValueError):
            S.sample_table(Scaled(), ['root'], [0.0])

    def test_moving_groups_are_held_in_place(self):
        # the root's horizontal travel in walk/run/... is taken out (the game moves the actor); its height and every
        # other group stay as sampled
        pos = np.zeros((6, 2, 3))
        pos[:, 0] = [[0, 0, 5], [10, 1, 6], [20, 2, 5], [0, 0, 1], [3, 4, 2], [6, 8, 3]]
        pos[:, 1] = 7.0
        S.hold_in_place(pos, ['bip01', 'pelvis'], {'walkforward': (0, 2), 'death1': (3, 5)})
        np.testing.assert_array_equal(pos[0:3, 0], [[0, 0, 5], [0, 0, 6], [0, 0, 5]])
        np.testing.assert_array_equal(pos[3:6, 0], [[0, 0, 1], [3, 4, 2], [6, 8, 3]])
        self.assertTrue(np.all(pos[:, 1] == 7.0))

    def test_every_group_is_in_the_table_combat_and_poses_included(self):
        # the maintainer, 25 October 2026: if a humanoid can do it, it is in the table; attack groups name their
        # phases instead of start/stop, inventory poses have one key; sound keys are events, not groups
        keys = [(0.0, 'idle: start'), (1.0, 'idle: stop'), (1.5, 'soundgen: left'),
                (2.0, 'weapononehand: equip start'), (2.4, 'weapononehand: chop min attack'),
                (2.9, 'weapononehand: chop hit'), (3.5, 'weapononehand: unequip stop'),
                (4.0, 'inventoryhandtohand: start'), (5.0, 'sound: swishm')]
        names = S.all_groups(keys)
        self.assertEqual(names, ['idle', 'weapononehand', 'inventoryhandtohand'])
        self.assertEqual(S.group_spans(keys, names),
                         {'idle': (0.0, 1.0), 'weapononehand': (2.0, 3.5), 'inventoryhandtohand': (4.0, 4.0)})
        self.assertEqual(len(S.table_frames(4.0, 4.0)), 1)

    def test_text_keys_become_table_frames(self):
        # the phases a group is played between (OpenMW's character controller, MWScript's PlayGroup) and the sound
        # events, as frames of the span that holds them; a phased group's second place keeps its own phases
        keys = [(64.0, 'spellcast: equip start'), (64.5, 'spellcast: equip stop'), (259.5, 'spellcast: self start'),
                (260.5, 'spellcast: self release'), (261.5, 'spellcast: self stop'), (260.0, 'soundgen: left'),
                (400.0, 'idle: start')]
        names = S.all_groups(keys)
        ranges = S.group_spans(keys, names)
        groups = {'spellcast': (0, 4), 'spellcast_2': (5, 21)}
        rate = 8.0
        got = S.text_keys(keys, {g: ranges[g] for g in groups}, groups, rate)
        self.assertEqual(got, [('equip start', 0, 0), ('equip stop', 0, 4), ('self start', 1, 5),
                               ('soundgen: left', 1, 9), ('self release', 1, 13), ('self stop', 1, 21)])

    def test_appended_groups_follow_under_their_prefix(self):
        """SKEL-TABLE-SHARED-FEMALE-52: the female groups live in the common table as 'f:<group>' after its own,
        with their own text keys; the same skeleton appended gives the same frames again."""
        sk = ChainSkeleton()
        data, report = S.build_table(sk)
        both, both_report = S.build_table(sk, over=ChainSkeleton(), append='f:')
        table, joined = S.read_table(data), S.read_table(both)
        self.assertEqual(both_report['names'][:2], ['idle', 'walkforward'])
        self.assertEqual(both_report['names'][2:4], ['f:idle', 'f:walkforward'])
        self.assertEqual(joined['frames'], 2 * table['frames'])
        first, last = joined['groups']['f:walkforward']
        own_first, own_last = joined['groups']['walkforward']
        self.assertEqual(last - first, own_last - own_first)
        names = list(joined['groups'])
        f_keys = sorted((t, f) for t, g, f in joined['keys'] if g == names.index('f:walkforward'))
        keys = sorted((t, f + table['frames']) for t, g, f in joined['keys'] if g == names.index('walkforward'))
        self.assertEqual(f_keys, keys)
        np.testing.assert_array_equal(joined['q'][first:last + 1], joined['q'][own_first:own_last + 1])

    def test_the_dodge_is_a_named_span_of_the_walk_loop(self):
        # the enhanced combat's dodge (docs/COMBAT.md): the walk-left/right loop, no frames of its own
        groups = {'idle': (0, 10), 'walkleft': (11, 30), 'walkright': (31, 50)}
        keys = [('start', 1, 11), ('loop start', 1, 13), ('loop stop', 1, 27), ('stop', 1, 30),
                ('loop start', 2, 33), ('loop stop', 2, 47)]
        self.assertEqual(S.extra_groups(groups, keys), {'dodgel': (13, 27), 'dodger': (33, 47)})
        self.assertEqual(S.extra_groups({'idle': (0, 10)}, []), {})

    def test_a_phased_group_in_two_places_is_two_spans(self):
        # SKEL-GROUP-SPAN-52: the beast skeleton's spellcast has its equip keys at 64 s and its casts at 260 s
        keys = [(64.0, 'spellcast: equip start'), (64.2, 'spellcast: equip stop'), (259.7, 'spellcast: self start'),
                (261.7, 'spellcast: self stop'), (300.0, 'idle2: start'), (301.0, 'idle2: stop')]
        spans = S.group_spans(keys, S.all_groups(keys))
        self.assertEqual(spans, {'idle2': (300.0, 301.0), 'spellcast': (64.0, 64.2), 'spellcast_2': (259.7, 261.7)})

    def test_groups_from_text_keys(self):
        keys = [(1.0, 'idle: start'), (3.0, 'idle: stop'), (4.0, 'walkforward: start'), (4.5, 'walkforward: loop start'),
                (6.0, 'walkforward: stop'), (7.0, 'soundgen: left'), (8.0, 'death1: start')]
        self.assertEqual(S.groups_of(keys, ['idle', 'walkforward', 'death1', 'runforward']),
                         {'idle': (1.0, 3.0), 'walkforward': (4.0, 6.0)})


class ChainSkeleton(Chain):
    """The chain as an npc_geometry.Skeleton: nodes, parents, text keys (two groups) and pose()."""
    nodes = {'root': None, 'upper': None, 'fore': None}
    keys = [(0.0, 'idle: start'), (2.0, 'idle: stop'), (2.5, 'walkforward: start'), (4.0, 'walkforward: stop')]

    def pose(self, time):
        out = {}

        def world(name):
            if name not in out:
                p = Chain.parents[name]
                out[name] = self.local(name, time) @ (world(p) if p else np.eye(4))
            return out[name]
        return world


def strip(width, height, x0, z0, y=1.0):
    """A flat grid in the x-z plane: vertices, faces, uv."""
    xs, zs = np.meshgrid(np.linspace(x0, x0 + 4, width + 1), np.linspace(z0, z0 + height, height + 1))
    points = np.column_stack((xs.ravel(), np.full(xs.size, y), zs.ravel()))
    faces = []
    for j in range(height):
        for i in range(width):
            a = j * (width + 1) + i
            faces += [(a, a + 1, a + width + 1), (a + 1, a + width + 2, a + width + 1)]
    uv = np.column_stack(((xs.ravel() - x0) / 4, (zs.ravel() - z0) / height))
    return points, np.array(faces), uv


class SkeletalModelTests(unittest.TestCase):
    """C3: one appearance as a skeletal model (S.skeletal_from_shapes): bake's reduction and atlas, one rest frame,
    the block; posed as the engine poses it, it matches the source shapes posed and scaled."""
    SCALE = np.array([1.1, 1.1, 0.9]) * .25

    def setUp(self):
        try:
            import fast_simplification  # noqa: F401
            import scipy  # noqa: F401
            from PIL import Image  # noqa: F401
        except ImportError:
            self.skipTest('Install optional NPC conversion dependencies')
        self.skeleton = ChainSkeleton()
        self.table, self.report = S.build_table(self.skeleton)
        self.times = np.linspace(0.0, 2.0, 8, endpoint=False)
        rest = self.skeleton.pose(0.0)
        # a skinned arm (upper, fore; joint vertices between z 10 and 14, second weights 0.25 to 0.75) and a rigid
        # plate on the forearm
        points, faces, uv = strip(6, 24, -2.0, 0.0)
        w_fore = np.clip((points[:, 2] - 10) / 4, 0, 1)
        weights = {}
        for b, w in ((0, 1 - w_fore), (1, w_fore)):
            ids = np.flatnonzero(w > 0)
            weights[b] = (ids, w[ids])
        inverse = {0: np.linalg.inv(rest('upper')), 1: np.linalg.inv(rest('fore'))}
        bone, second, weight, r, r2 = S.bind_skinned(points, weights, inverse)
        arm = {'name': 'tri chest', 'part': 3, 'bones': ['upper', 'fore'], 'bone': bone, 'second': second,
               'weight': weight, 'rest': r, 'rest2': r2, 'faces': faces, 'uv': uv, 'texture': None}
        points, faces, uv = strip(3, 3, 3.0, 24.0, y=-1.0)
        plate = {'name': 'tri hand', 'part': 6, 'bones': ['fore'], 'bone': np.zeros(len(points), int),
                 'second': np.full(len(points), -1), 'weight': np.zeros(len(points)),
                 'rest': (np.column_stack((points, np.ones(len(points)))) @ inverse[1])[:, :3],
                 'rest2': np.zeros((len(points), 3)), 'faces': faces, 'uv': uv, 'texture': None}
        self.sources = [arm, plate]
        self.shapes = []
        for src in self.sources:
            positions = np.array([S.posed_shape(src, self.skeleton.pose(t)) for t in self.times]) * self.SCALE
            self.shapes.append({'name': src['name'], 'part': src['part'], 'positions': positions,
                                'faces': src['faces'], 'uv': src['uv'], 'colours': np.ones((len(src['uv']), 4)),
                                'material': 0})
        materials = [{'texture_index': None, 'diffuse': [1., 1., 1.], 'alpha': 1.}]
        self.model, self.facts = S.skeletal_from_shapes(
            self.shapes, materials, {}, bytes(range(256)) * 3, self.sources, rest, self.SCALE, self.table,
            self.report['bone_names'], budgets=(192,))
        self.read = S.read_skeletal(self.model)

    def test_a_budget_too_small_for_the_head_floor_retries_with_the_idle_rule(self):
        """SKEL-BUDGET-SHAPES-52: dev1-try10 stopped on a Vivec resident: with every kit sample (more than 8 frames)
        each head shape takes up to 120 faces before the split and no budget of the ladder held them all; that
        budget is baked again with the 8-frame rule, the poses unchanged."""
        import npc_geometry
        from unittest.mock import patch
        times = np.linspace(0.0, 2.0, 12, endpoint=False)
        shapes = [dict(s, positions=np.array([S.posed_shape(src, self.skeleton.pose(t)) for t in times]) * self.SCALE)
                  for s, src in zip(self.shapes, self.sources)]
        real, seen = npc_geometry.bake, []

        def bake(*args, **kwargs):
            seen.append(kwargs.get('reference_frames'))
            if kwargs.get('reference_frames', 0) > 8:
                raise ValueError('Too many separate shapes for budget')
            return real(*args, **kwargs)
        materials = [{'texture_index': None, 'diffuse': [1., 1., 1.], 'alpha': 1.}]
        with patch.object(npc_geometry, 'bake', bake):
            model, _ = S.skeletal_from_shapes(shapes, materials, {}, bytes(range(256)) * 3, self.sources,
                                              self.skeleton.pose(0.0), self.SCALE, self.table,
                                              self.report['bone_names'], budgets=(192,))
        self.assertEqual(seen, [12, 8])
        self.assertEqual(S.read_skeletal(model)['frames'], 1)
        # any other refusal still stops the model
        with patch.object(npc_geometry, 'bake', side_effect=ValueError('Invalid protected shape budget')):
            with self.assertRaises(ValueError):
                S.skeletal_from_shapes(shapes, materials, {}, bytes(range(256)) * 3, self.sources,
                                       self.skeleton.pose(0.0), self.SCALE, self.table, self.report['bone_names'],
                                       budgets=(192,))

    def test_one_rest_frame_and_the_block_after_a_standard_mdl(self):
        m = self.read
        self.assertEqual(m['frames'], 1)
        self.assertLess(m['nt'], sum(len(s['faces']) for s in self.shapes))     # bake reduced it
        self.assertEqual(m['nv'], 3 * m['nt'])
        self.assertEqual(len(self.model), m['standard'] + S.BLOCK_HEAD + m['nv'] * S.VERT_BYTES)
        self.assertEqual(m['block_bytes'], S.BLOCK_HEAD + m['nv'] * S.VERT_BYTES)
        self.assertEqual((m['table'], m['table_frames']), (S.SKEL_TABLE_PATH, self.report['frames']))
        self.assertEqual(list(m['frame_box']), [0, 0, 0, 0, 255, 255, 255, 0])
        np.testing.assert_allclose(m['pose_origin'], m['origin'] / self.SCALE, rtol=1e-6)
        np.testing.assert_allclose(m['pose_step'], m['scale'] / self.SCALE, rtol=1e-6)
        self.assertEqual(self.facts['kept_vertices'] + self.facts['moved_vertices'], m['nv'])
        self.assertGreater(self.facts['moved_vertices'], 0, self.facts['largest_move'])
        self.assertGreater(self.facts['joint_vertices'], 0)

    def test_the_rest_frame_stands_on_its_true_soles(self):
        # SKEL-GROUND-SOLES-52 (dev1-try8: Hefadmir and Wusha found no spot on their sloped floors): the box over every
        # table frame is taller than the idle's, so its z grid is laid with the rest pose's lowest point on a step;
        # the soles the ground check reads are then the rest pose's own, not a step above them
        import check_actor_ground as C
        rest = self.facts['rest_model']
        frame = C.model_frames(self.model)
        self.assertTrue(frame.skeletal)
        lowest = min(p[2] for p in frame[0])
        self.assertAlmostEqual(lowest, float(rest[:, 2].min()), places=4)
        soles = C.contact_samples(frame, (0, 0, 0))
        self.assertTrue(all(lowest - 1e-6 <= z <= lowest + .5 for _, _, z in soles))
        # the grid still holds every pose
        lo, step = S.ground_grid([0, 0, -3.0], [10, 20, 40.0], 0.137)
        self.assertAlmostEqual((0.137 - lo[2]) / step[2], round((0.137 - lo[2]) / step[2]), places=9)
        self.assertLessEqual(lo[2], -3.0)
        self.assertGreaterEqual(lo[2] + 255 * step[2], 40.0 - 1e-9)
        np.testing.assert_allclose(step[:2], [10 / 255, 20 / 255])

    def test_a_skeletal_model_is_told_from_a_baked_one(self):
        # the image step's guard torches keep their baked registry for baked guards only (is_skeletal)
        self.assertTrue(S.is_skeletal(self.model))
        self.assertFalse(S.is_skeletal(self.model[:self.read['standard']]))
        self.assertFalse(S.is_skeletal(b'not a model'))

    def test_engine_pose_equals_the_source_posed_and_scaled(self):
        m = self.read
        table = S.read_table(self.table)
        times = self.report['times']
        shape_of = self.facts['shape_of']
        # every baked vertex starts where bake put it (the rest frame is bake's frame 0, quantised in the box)
        error = np.abs(m['rest_bytes'][:, :3] * m['scale'] + m['origin'] - self.facts['rest_model']) / m['scale']
        self.assertLess(error.max(), 0.51, (error.argmax(), self.facts['rest_model'].min(0),
                                            self.facts['rest_model'].max(0), m['origin'], m['scale']))
        # at the rest frame (the idle group's first table frame): every vertex, moved ones included
        idle = table['groups']['idle'][0]
        self.assertEqual(times[idle], 0.0)
        np.testing.assert_array_less(np.abs(S.engine_pose(m, table, idle) - m['rest_bytes'][:, :3]), 1.01)
        for frame in (0, 7, 19, table['groups']['walkforward'][0] + 5, table['frames'] - 1):
            posed = S.engine_pose(m, table, frame)
            pose = self.skeleton.pose(times[frame])
            checked = 0
            for k, src in enumerate(self.sources):
                ids = np.flatnonzero(shape_of == k)
                kept = self.facts['distance'][ids] < 1e-4         # a vertex the reduction kept on an original one
                expected = S.posed_shape(src, pose)[self.facts['nearest'][ids]] * self.SCALE
                expected = (expected - m['origin']) / m['scale']
                np.testing.assert_array_less(np.abs(posed[ids][kept] - expected[kept]), 1.01)
                checked += int(kept.sum())
            self.assertGreater(checked, 0)

    def test_a_moved_vertex_keeps_its_offset_in_bone_space(self):
        rest = self.skeleton.pose(0.0)
        src = {**self.sources[1], 'points': self.shapes[1]['positions'][0], 'index': [2]}
        offset = np.array([0.03, -0.02, 0.01])     # well inside the plate's vertex spacing (about 0.37)
        point = src['points'][4] + offset
        bone, second, weight, r, _, distance, _ = S.carry_bones([src], point[None], np.array([0]), rest, self.SCALE)
        self.assertEqual((bone[0], second[0]), (2, -1))
        self.assertAlmostEqual(distance[0], np.linalg.norm(offset))
        np.testing.assert_allclose((np.append(r[0], 1) @ rest('fore'))[:3] * self.SCALE, point, atol=1e-9)

    def test_vectorised_skin_and_table_reader(self):
        table = S.read_table(self.table)
        self.assertEqual(table['parents'], [-1, 0, 1])
        self.assertEqual(list(table['groups']), self.report['names'])
        src = self.sources[0]
        world = S.table_world(table, 10)
        np.testing.assert_allclose(S.skin_many(src['rest'], src['bone'] + 1, np.where(src['second'] >= 0,
                                                                                         src['second'] + 1, -1),
                                               src['weight'], src['rest2'], world),
                                   S.skin(src['rest'], src['bone'] + 1, np.where(src['second'] >= 0,
                                                                                 src['second'] + 1, -1),
                                          src['weight'], list(world), src['rest2']), atol=1e-12)


class StickFigureTests(unittest.TestCase):
    """The stick figure (STICK_BONES): a left-out bone's motion is kept in its kept child's local transform, and a
    part on a left-out bone rides its nearest kept ancestor, exactly at rest."""

    def test_kept_bones_keep_their_world_motion(self):
        sk = ChainSkeleton()
        kept = S.KeptSkeleton(sk, ('root', 'fore'))
        self.assertEqual(kept.parents, {'root': None, 'fore': 'root'})
        for t in (0.0, 0.7, 3.1):
            world = S.pose_matrices([-1, 0], [kept.local('root', t), kept.local('fore', t)])
            np.testing.assert_allclose(world[1], sk.pose(t)('fore'), atol=1e-12)

    def test_a_part_on_a_left_out_bone_rides_its_kept_ancestor(self):
        sk = ChainSkeleton()
        rest = sk.pose(0.5)
        point = np.array([[0.5, 0.2, 14.0], [0.0, 1.0, 22.0]])
        inv = {n: np.linalg.inv(rest(n)) for n in ('upper', 'fore')}
        src = {'name': 'arm', 'bones': ['upper', 'fore'], 'bone': np.array([0, 1]), 'second': np.array([1, -1]),
               'weight': np.array([0.5, 0.0]),
               'rest': np.array([(np.append(point[0], 1) @ inv['upper'])[:3],
                                 (np.append(point[1], 1) @ inv['fore'])[:3]]),
               'rest2': np.array([(np.append(point[0], 1) @ inv['fore'])[:3], [0, 0, 0]])}
        out = S.onto_kept(src, Chain.parents, {'root', 'fore'}, rest)
        self.assertEqual(out['bones'], ['root', 'fore'])
        world = [rest('root'), rest('fore')]
        np.testing.assert_allclose(S.skin(out['rest'], out['bone'], out['second'], out['weight'], world, out['rest2']),
                                   point, atol=1e-9)
        # two bones landing on one keep one
        both = S.onto_kept({**src, 'second': np.array([0, -1])}, Chain.parents, {'root'}, rest)
        self.assertEqual(list(both['second']), [-1, -1])

    def test_the_hand_keeps_a_thumb_and_one_finger_unit(self):
        parents = {'bip01 l hand': None, 'bip01 l finger1': 'bip01 l hand', 'bip01 l finger11': 'bip01 l finger1',
                   'bip01 l finger2': 'bip01 l hand', 'bip01 l finger21': 'bip01 l finger2'}
        keep = set(S.STICK_BONES)
        self.assertEqual(S.kept_ancestor(parents, keep, 'bip01 l finger2'), 'bip01 l finger1')
        self.assertEqual(S.kept_ancestor(parents, keep, 'bip01 l finger21'), 'bip01 l finger11')
        self.assertEqual(S.kept_ancestor(parents, keep, 'bip01 l finger11'), 'bip01 l finger11')


class SkeletalModelReadersTests(unittest.TestCase):
    """The builder's other readers of actor models take a skeletal one (dev1-try5 stopped in chim-town-seyda: the
    ground check refused the block after the rest frame; the stream heap estimate called it unstreamable)."""

    def setUp(self):
        fixture = SkeletalModelTests('test_one_rest_frame_and_the_block_after_a_standard_mdl')
        fixture.setUp()
        self.model = fixture.model
        self.nv = fixture.read['nv']

    def test_the_ground_check_reads_the_rest_frame(self):
        import check_actor_ground
        frames = check_actor_ground.model_frames(self.model)
        self.assertEqual((len(frames), len(frames[0])), (1, self.nv))
        with self.assertRaises(ValueError):
            check_actor_ground.model_frames(self.model + b'\0')           # a block of the wrong size
        with self.assertRaises(ValueError):
            broken = bytearray(self.model)
            broken[len(self.model) - S.BLOCK_HEAD - self.nv * S.VERT_BYTES] = ord('X')   # not a block
            check_actor_ground.model_frames(bytes(broken))

    def test_a_refused_model_is_named_with_its_counts(self):
        # ACTOR-MODEL-ERROR-UNNAMED-48 (persisting on 2026-10-27: chim-town-vivec_city stopped with "Unsupported actor
        # model" and no name): the refusal names the model and the header counts the limits judge
        import check_actor_ground
        self.assertEqual(len(check_actor_ground.named_model_frames(self.model, 'progs/ok.mdl')), 1)
        broken = bytearray(self.model)
        broken[4:8] = (7).to_bytes(4, 'little')                           # a version the check refuses
        with self.assertRaises(ValueError) as caught:
            check_actor_ground.named_model_frames(bytes(broken), 'progs/npc_vilamon.mdl')
        text = str(caught.exception)
        self.assertIn('progs/npc_vilamon.mdl', text)
        self.assertIn('version 7', text)
        self.assertIn('%d vertices' % self.nv, text)
        with self.assertRaises(ValueError) as caught:
            check_actor_ground.named_model_frames(b'IDPO', 'progs/short.mdl')
        self.assertIn('progs/short.mdl', str(caught.exception))
        self.assertIn('shorter than the 84-byte header', str(caught.exception))

    def test_the_ground_check_grounds_the_rest_frame_whatever_the_layout(self):
        # SKEL-GROUND-LAYOUT-TABLE-52: the layout names table frames (idle:0:21, walk:1102:8 ...), not model frames;
        # the stage-build stop in chim-town-balmora ("Animation kit idle group outside the model frames")
        import check_actor_ground
        frames = check_actor_ground.model_frames(self.model)
        layout = 'idle:0:21:0.1270 walk:1102:8:0.1333:38.52'
        samples = check_actor_ground.contact_samples(frames, (0, 0, 0), layout=layout)
        self.assertEqual(samples, check_actor_ground.contact_samples(frames, (0, 0, 0)))
        self.assertTrue(samples)
        self.assertEqual(check_actor_ground.idle_poses(frames, layout), list(frames))

    def test_the_payload_check_reads_the_table_frames(self):
        # the payload preflight's actor-frames check: a skeletal actor's layout and AWTS1 tags index its table
        import actor_frames
        table = S.read_skeletal(self.model)['table_frames']
        self.assertEqual(actor_frames.skeletal_frames(self.model), table)
        self.assertEqual(actor_frames.layout_frames(self.model), table)
        self.assertIsNone(actor_frames.skeletal_frames(self.model[:len(self.model) - 1]))
        self.assertEqual(actor_frames.of_model(2730, 'idle:0:21:0.127 walk:1102:8:0.133', skeletal=True).idle, (0, 21))
        with self.assertRaises(ValueError):
            actor_frames.of_model(2730, 'idle:0:21:0.127')                 # past an ordinary model's 256 frames
        self.assertEqual(actor_frames.tag_frames('AWTS1 2730\nweapon -\n', skeletal=True), 2730)
        with self.assertRaises(ValueError):
            actor_frames.tag_frames('AWTS1 2730\n')                          # an ordinary model's tag is AWTG1

    def test_the_stream_estimate_streams_it(self):
        from alias_stream_heap import eligible
        self.assertTrue(eligible(self.model, len(self.model)))
        self.assertFalse(eligible(self.model + b'\0', len(self.model)))


class PreviewTests(unittest.TestCase):
    def test_the_preview_draws_every_frame_of_a_group(self):
        try:
            import PIL  # noqa: F401
        except ImportError:
            self.skipTest('Pillow is not installed')
        import skeleton_preview as P
        table, report = S.build_table(ChainSkeleton())
        report['bone_names'] = ['bip01', 'upper', 'fore']       # the preview centres on bip01
        t = S.read_table(table)
        frames, starts = P.render([('chain', t, report)], ['idle'], S.TABLE_RATE)
        first, last = t['groups']['idle']
        self.assertEqual((len(frames), starts), (last - first + 1, [(0, last - first + 1)]))
        self.assertEqual(P.contact_sheet(frames, starts).size, (P.W, P.H // 2))

    def test_the_character_preview_draws_the_engine_pose(self):
        try:
            import PIL  # noqa: F401
        except ImportError:
            self.skipTest('Pillow is not installed')
        import skeleton_preview as P
        model = SkeletalModelTests('test_one_rest_frame_and_the_block_after_a_standard_mdl')
        model.setUp()
        table = S.read_table(model.table)
        tris, colour = P.model_faces(model.model, bytes(range(256)) * 3)
        self.assertEqual((len(tris), colour.shape), (model.read['nt'], (model.read['nt'], 3)))
        frames = P.render_body(model.model, bytes(range(256)) * 3, table, ['idle'], 'test', size=(64, 80))
        first, last = table['groups']['idle']
        self.assertEqual(len(frames), last - first + 1)
        self.assertGreater(len(set(frames[0].getdata())), 2)        # something was drawn


if __name__ == '__main__':
    unittest.main()
