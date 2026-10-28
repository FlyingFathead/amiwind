# SPDX-License-Identifier: GPL-3.0-only
"""Creature animation tables (tools/creature_tables.py, CREATURE-TABLES): every creature mesh on a table of its own
files, the engine's groups on its frames, and the creature library's 'skeletal' method beside 'kf'.

Synthetic data only (the model and keyframe files of tests/test_creature_pose.py). Checked: the table carries the
bones the keys move and the scene root (a shape no key moves rides it); every group of the creature's own file is in
it, and a two-legged creature's own groups play over the shared file's (OpenMW's source order); the layout puts each
engine group on the table's frames (a group the creature lacks stands on the idle; a 'hold' group ends on its stop
frame); table and model names fit the engine (AW_SKEL_TABLE_NAME); records of a later master replace an earlier
one's; the library keeps 'kf' as its default and refuses no method it lists.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'src', ROOT / 'tools', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


class TableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from test_creature_pose import FILES, model, kf
        cls.files = dict(FILES)
        cls.files['meshes/r/xbeast.nif'] = model()
        cls.files['meshes/r/xbeast.kf'] = kf(
            [(0.0, 'idle: start'), (1.0, 'idle: stop'), (1.0, 'death1: start'), (2.0, 'death1: stop')],
            [(b'Bone', (1, [(0.0, (0, 0, 0)), (2.0, (8, 0, 0))])), (b'Dummy', (1, [(0.0, (0, 0, 50)), (2.0, (0, 0, 50))]))])
        cls.files['meshes/xbase_anim.kf'] = kf(
            [(0.0, 'idle: start'), (4.0, 'idle: stop'), (4.0, 'walkforward: loop start'),
             (6.0, 'walkforward: loop stop')], [(b'Bone', (1, [(0.0, (0, 0, 0)), (4.0, (0, 40, 0))]))])

    def rig(self, biped=False):
        import creature_tables as T
        from prepare_scenery import nif_reader
        from test_creature_pose import reader
        return T.open_rig(nif_reader(), reader(self.files), 'r/beast.nif', biped)

    def test_bones_the_keys_move_and_the_root(self):
        import creature_tables as T
        self.assertEqual(T.animated_bones(self.rig()), ['root', 'bone', 'dummy'])

    def test_every_group_of_its_own_file(self):
        import creature_tables as T
        data, rep = T.table(self.rig())
        self.assertEqual(rep['names'], ['idle', 'death1'])
        self.assertEqual(rep['sources'], ['meshes/r/xbeast.kf'])
        self.assertFalse(rep['layered'])
        self.assertEqual(rep['scaled'], {})
        # 'dummy' holds still against the root over every key: merged (no drift); 'bone' moves 8 units: kept
        self.assertEqual(rep['bone_names'], ['root', 'bone'])
        self.assertEqual([(b, a) for b, a, _ in rep['bones_left_out']], [('dummy', 'root')])
        self.assertEqual((rep['bones_before'], rep['max_drift']), (3, 0.0))

    def test_two_legged_own_groups_over_the_shared_file(self):
        """xbase_anim.kf first, the creature's own file over it: its idle replaces the shared idle, the shared
        walk stays (OpenMW mwrender/creatureanimation.cpp: a later source wins for every group it has)."""
        import creature_tables as T
        import skeletal_actor
        rig = self.rig(biped=True)
        data, rep = T.table(rig)
        self.assertTrue(rep['layered'])
        self.assertEqual(sorted(rep['names']), ['death1', 'idle', 'walkforward'])
        t = skeletal_actor.read_table(data)
        # the idle is the own file's: 1 s at the table rate (the shared one is 4 s)
        a, b = t['groups']['idle']
        self.assertEqual(b - a, int(round(1.0 * skeletal_actor.TABLE_RATE)))

    def test_engine_groups_on_the_table_frames(self):
        import creature_tables as T
        import skeletal_actor
        rig = self.rig()
        data, rep = T.table(rig)
        groups = {g['name']: g for g in T.kit(rig, data, rep['times'])}
        t = skeletal_actor.read_table(data)
        self.assertEqual([g for g in T.KIT], list(groups))
        idle = t['groups']['idle']
        self.assertEqual((groups['idle']['base'], groups['idle']['count']), (idle[0], idle[1] - idle[0]))
        death = t['groups']['death1']
        # a 'hold' group ends on its stop frame
        self.assertEqual((groups['death']['base'], groups['death']['count']), (death[0], death[1] - death[0] + 1))
        for name in ('walk', 'run', 'attack', 'hit'):        # not in its files: the idle's first frame
            self.assertEqual((groups[name]['source'], groups[name]['base'], groups[name]['count']),
                             ('idle', idle[0], 1))
        self.assertAlmostEqual(groups['idle']['step'], 1 / skeletal_actor.TABLE_RATE, places=4)
        self.assertTrue(T.layout(list(groups.values())).startswith('idle:%d:%d:' % (idle[0], idle[1] - idle[0])))

    def test_two_legged_walk_from_the_shared_file(self):
        import creature_tables as T
        rig = self.rig(biped=True)
        data, rep = T.table(rig)
        groups = {g['name']: g for g in T.kit(rig, data, rep['times'])}
        self.assertEqual(groups['walk']['source'], 'table')
        self.assertEqual(groups['walk']['count'], 2 * 8)        # 2 s loop at 8 frames a second, stop frame left out
        self.assertNotIn('speed', groups['walk'])               # no accumulation root (bip01 / root bone) to measure

    def test_a_missing_attachment_bone_rides_its_parent(self):
        """An appended table needs every bone of the humanoid table: a weapon or shield bone the creature lacks is
        added riding its hand with no offset (no part of the creature hangs on it)."""
        import numpy as np
        import creature_tables as T
        from halloween_cast import RigSkeleton
        sk = T._WithAttachments(RigSkeleton(self.rig(), 0), {'weapon bone': 'bone'})
        self.assertEqual(sk.parents['weapon bone'], 'bone')
        np.testing.assert_allclose(sk.local('weapon bone', 0.5), np.eye(4))
        np.testing.assert_allclose(sk.pose(0.5)('weapon bone'), sk.pose(0.5)('bone'))

    def test_kit_takes_a_missing_group_from_the_base_after_the_own_frames(self):
        import creature_tables as T
        import skeletal_actor
        rig = self.rig(biped=True)
        data, rep = T.table(rig)
        own, _ = T.table(self.rig())                     # its own file only: idle and death1
        groups = {g['name']: g for g in T.kit(self.rig(), own, T.table(self.rig())[1]['times'], base=data)}
        own_frames = skeletal_actor.read_table(own)['frames']
        walk = skeletal_actor.read_table(data)['groups']['walkforward']
        self.assertEqual((groups['walk']['source'], groups['walk']['base']), ('base', walk[0] + own_frames))
        self.assertEqual(groups['idle']['source'], 'table')

    def test_names_fit_the_engine(self):
        import creature_tables as T
        for mesh in ('r/dagothr.nif', 'r/heart_akulakhan.nif', 'r/LordVivec.NIF'):
            self.assertLess(len(T.table_path(mesh)), 32)            # aw_skel.h AW_SKEL_TABLE_NAME
            self.assertTrue(T.table_path(mesh).startswith('progs/k_') and T.table_path(mesh).endswith('.awsk'))
            self.assertTrue(T.model_path(mesh).startswith('progs/c_') and T.model_path(mesh).endswith('_k.mdl'))
        self.assertEqual(T.table_path('r/LordVivec.NIF'), T.table_path('r/lordvivec.nif'))

    def test_drift_measured_and_the_limit_forces_more_merges(self):
        """A merge under the drift limit is free; past AW_SKEL_MAX_BONES the least drifting bone goes next and its
        drift is named (the 8-unit move of 'bone'); the scene root stays; when only the roots are left and it is still
        too many, the table is refused."""
        import creature_tables as T
        rig = self.rig()
        kept, merged = T.merge_plan(rig, T.animated_bones(rig), limit=3, drift_limit=0.5)
        self.assertEqual(kept, ['root', 'bone'])
        old = T.MAX_BONES
        try:
            T.MAX_BONES = 1
            data, rep = T.table(rig)
            self.assertEqual(rep['bone_names'], ['root'])
            self.assertEqual([b for b, _, _ in rep['bones_left_out']], ['dummy', 'bone'])
            self.assertAlmostEqual(rep['max_drift'], 8.0, places=2)
            T.MAX_BONES = 0
            with self.assertRaisesRegex(ValueError, 'AW_SKEL_MAX_BONES'):
                T.table(rig)
        finally:
            T.MAX_BONES = old


@unittest.skipIf(__import__('os').name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(__import__('shutil').which('cc'), 'a Linux C compiler is required')
class AppendedTableTests(unittest.TestCase):
    """CREATURE-APPENDED-TABLE-54: a creature's own groups in a small appended table (version 3) on the shared base
    table's bones; the engine (aw_skel.c, aw_skel_load.c) plays the own groups first, every other group from the
    base, frames after the own ones; refusals for other parents or a base that is itself appended."""

    def tables(self):
        import numpy as np
        import skeletal_actor as S
        from test_skeletal_actor import Chain
        chain = Chain()
        bones = S.bone_order(Chain.parents, ['fore'])
        parents = [-1 if Chain.parents[b] is None else bones.index(Chain.parents[b]) for b in bones]
        times = S.table_frames(0.0, 2.0, rate=10.0)
        rot, pos = S.sample_table(chain, bones, times)
        q, p, scale = S.quantise_table(rot, pos)
        base = S.write_table(parents, {'idle': (0, 10), 'walkforward': (11, 20)}, q, p, scale,
                             keys=[('start', 0, 0), ('stop', 0, 10), ('start', 1, 11), ('stop', 1, 20)])
        # the creature's own idle (its own motion: the chain's frames reversed) and a group of its own
        own = S.write_table(parents, {'idle': (0, 6), 'idle9': (7, 12)}, np.ascontiguousarray(q[::-1][:13]),
                            np.ascontiguousarray(p[::-1][:13]), scale,
                            keys=[('start', 0, 0), ('stop', 0, 6), ('start', 1, 7), ('stop', 1, 12)])
        return base, own

    def test_round_trip_and_the_engine_plays_both(self):
        import subprocess
        import tempfile
        import creature_tables as T
        base, own = self.tables()
        appended = T.to_appended(own, 'progs/humanoid.awsk')
        self.assertEqual(T.from_appended(appended), (own, 'progs/humanoid.awsk'))
        with self.assertRaises(ValueError):
            T.to_appended(appended, 'progs/humanoid.awsk')        # already appended
        with self.assertRaises(ValueError):
            T.to_appended(own, 'progs/humanoid.awsk|f')           # a view is no base
        src = ROOT / 'engine/aga/src'
        with tempfile.TemporaryDirectory() as scratch:
            scratch = Path(scratch)
            (scratch / 'base.bin').write_bytes(base)
            (scratch / 'own.bin').write_bytes(appended)
            exe = scratch / 'skel-check'
            compiled = subprocess.run(['cc', '-std=gnu89', '-O1', '-fsanitize=undefined', '-fno-sanitize-recover=all',
                                       '-I' + str(src), str(ROOT / 'tests/aga_skel_test.c'), str(src / 'aw_skel.c'),
                                       '-lm', '-o', str(exe)], capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            result = subprocess.run([str(exe), 'append', str(scratch / 'base.bin'), str(scratch / 'own.bin')],
                                    capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        # own: 2 groups, 13 frames; base: 2 groups, 21 frames
        self.assertEqual(result.stdout.split(), ['append', '4', '34', '2', '13', 'progs/humanoid.awsk'])


class RecordTests(unittest.TestCase):
    def test_a_later_master_replaces_the_record(self):
        import creature_tables as T
        from test_chim_levelled import MASTER
        one = T.records([('Morrowind.esm', MASTER)])
        two = T.records([('Morrowind.esm', MASTER), ('Tribunal.esm', MASTER)])
        self.assertTrue(one)
        self.assertEqual(set(one), set(two))
        self.assertEqual({r['master'] for r in two.values()}, {'Tribunal.esm'})
        per, remaining = T.record_count([('Morrowind.esm', MASTER), ('Tribunal.esm', MASTER)])
        self.assertEqual(per, {'Morrowind.esm': len(one), 'Tribunal.esm': len(one)})
        self.assertEqual(remaining, len(one))
        meshes = T.meshes(two)
        self.assertEqual(sum(len(m['ids']) for m in meshes.values()), sum(1 for r in two.values() if r['mesh']))


class LibraryTests(unittest.TestCase):
    def test_skeletal_beside_kf_default_unchanged(self):
        import creature_library as L
        self.assertEqual(L.DEFAULT_METHOD, 'kf')
        self.assertEqual(L.METHODS, ('kf', 'resident', 'skeletal'))
        with self.assertRaises(ValueError):
            L.bake('.', b'', {}, '.', method='baked')

    def test_actor_library_option(self):
        text = (ROOT / 'tools/actor_library.py').read_text(encoding='utf-8')
        self.assertIn("'--creature-method', choices=('kf', 'skeletal'), default='kf'", text)


if __name__ == '__main__':
    unittest.main()
