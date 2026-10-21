# SPDX-License-Identifier: GPL-3.0-only
"""Creature posing for the creature model library (tools/creature_pose.py, EXPERIMENTAL, no default build uses it;
CREATURE-BAKE-NIF-UNSUPPORTED-47) and the actor table's instance scales (tools/chim/actors.py version 3, engine
chim/chim_actor_table.c).

Synthetic data only: a model with a moved bone and a repeated node name and its keyframe file built in the test.
Checked: the animated model and keyframe file are picked as the original picks them (the "x" version when its .kf
exists); a group is read from the newest source that has it (a two-legged creature's own file over the shared
one); keyframes bind to the first node of a name and a later node of the same name keeps its own transform; the
key types (linear, quadratic with tangents, TCB with tangents made from tension, continuity and bias, constant,
quaternions slerped) by hand; the pose handed to prepare_scenery.model_geometry by position; the layout string;
the table's version 3 scale section (builder and engine read the same scales; a broken section refused) and
version 2 unchanged without scales; and that no unit kind, stair code or NPC/gallery/resident bake reaches the
modules.
"""
import io
import os
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'src', ROOT / 'tools', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
SRC = ROOT / 'engine/aga/src'


def box(N, name, offset):
    shape = N.NiTriShape()
    shape.name = name
    data = N.NiTriShapeData()
    V = [(0, 0, 0), (8, 0, 0), (8, 8, 0), (0, 8, 0)]
    data.num_vertices = 4
    data.has_vertices = True
    data.vertices.update_size()
    for v, p in zip(data.vertices, V):
        v.x, v.y, v.z = p[0] + offset, p[1], p[2]
    data.num_uv_sets = 1
    data.has_uv = True
    data.uv_sets.update_size()
    for uv, p in zip(data.uv_sets[0], V):
        uv.u, uv.v = p[0] / 8, p[1] / 8
    data.num_triangles = 2
    data.num_triangle_points = 6
    data.has_triangles = True
    data.triangles.update_size()
    for t, p in zip(data.triangles, [(0, 1, 2), (0, 2, 3)]):
        t.v_1, t.v_2, t.v_3 = p
    shape.data = data
    return shape


def node(N, name, children, z=0.0):
    n = N.NiNode()
    n.name = name
    n.translation.z = z
    n.num_children = len(children)
    n.children.update_size()
    for i, c in enumerate(children):
        n.children[i] = c
    return n


def model():
    """Root -> Bone (a box) and two nodes named Dummy (boxes), the second one 100 units up."""
    from prepare_scenery import nif_reader
    N = nif_reader()
    d = N.Data(version=0x04000002)
    root = node(N, b'Root', [node(N, b'Bone', [box(N, b'Tri Bone', 0)]), node(N, b'Dummy', [box(N, b'Tri D1', 20)]),
                             node(N, b'Dummy', [box(N, b'Tri D2', 40)], z=100.0)])
    d.roots = [root]
    s = io.BytesIO()
    d.write(s)
    return s.getvalue()


def kf(keys, bones):
    """A keyframe file: text keys [(time, text)] and per bone a position channel (interpolation, [(time, xyz)])."""
    from prepare_scenery import nif_reader
    N = nif_reader()
    d = N.Data(version=0x04000002)
    seq = N.NiSequenceStreamHelper()
    text = N.NiTextKeyExtraData()
    text.num_text_keys = len(keys)
    text.text_keys.update_size()
    for k, (t, v) in zip(text.text_keys, keys):
        k.time = t
        k.value = v.encode('ascii')
    extras, ctrls = [text], []
    for bone, (kind, values) in bones:
        e = N.NiStringExtraData()
        e.string_data = bone
        extras.append(e)
        c = N.NiKeyframeController()
        data = N.NiKeyframeData()
        data.translations.num_keys = len(values)
        data.translations.interpolation = kind
        data.translations.keys.update_size()
        for key, (t, xyz) in zip(data.translations.keys, values):
            key.time = t
            key.value.x, key.value.y, key.value.z = xyz
        c.data = data
        ctrls.append(c)
    for a, b in zip(extras, extras[1:]):
        a.next_extra_data = b
    for a, b in zip(ctrls, ctrls[1:]):
        a.next_controller = b
    seq.extra_data = extras[0]
    seq.controller = ctrls[0] if ctrls else None
    d.roots = [seq]
    s = io.BytesIO()
    d.write(s)
    return s.getvalue()


FILES = {
    'meshes/r/beast.nif': b'plain',
    'meshes/r/xbeast.nif': None,      # filled in setUpClass
    'meshes/r/xbeast.kf': None,
    'meshes/xbase_anim.kf': None,
}


def reader(files):
    def read(name):
        if files.get(name) is None:
            raise KeyError(name)
        return files[name]
    return read


class SamplerTests(unittest.TestCase):
    def test_keys_by_hand(self):
        import creature_pose as P
        lin = {'times': [0.0, 2.0], 'values': np.array([[0.0, 0, 0], [8.0, 0, 0]]), 'type': 1, 'quaternion': False,
               'tangents': None}
        self.assertEqual(P.sample(lin, 0.5).tolist(), [2.0, 0, 0])
        self.assertEqual(P.sample(lin, -1).tolist(), [0.0, 0, 0])          # before the first key: the first value
        self.assertEqual(P.sample(lin, 9).tolist(), [8.0, 0, 0])           # after the last: the last
        const = dict(lin, type=5)
        self.assertEqual(P.sample(const, 0.9).tolist(), [0.0, 0, 0])
        self.assertEqual(P.sample(const, 1.1).tolist(), [8.0, 0, 0])
        quad = dict(lin, type=2, tangents=[(np.zeros(3), np.zeros(3)), (np.zeros(3), np.zeros(3))])
        # Hermite with zero tangents at the middle: 0.5
        self.assertAlmostEqual(P.sample(quad, 1.0)[0], 4.0)
        self.assertAlmostEqual(P.sample(quad, 0.5)[0], 8 * (-2 * .25 ** 3 + 3 * .25 ** 2))

    def test_tcb_tangents(self):
        """OpenMW's generateTCBTangents: with tension, continuity and bias 0 the inner tangent is the average of
        the neighbouring steps weighted by the time spans (a Catmull-Rom curve), the ends take half their step."""
        import creature_pose as P
        times, values = [0.0, 1.0, 3.0], [np.array(0.0), np.array(2.0), np.array(4.0)]
        t = P.tcb_tangents(times, values, [(0, 0, 0)] * 3)
        self.assertAlmostEqual(float(t[0][1]), 2.0)                          # (C + D) / 2 = 1, x the step 2
        self.assertAlmostEqual(float(t[1][0]), (2 + 2) * (1 / 3))           # (prev + next) x (1 / 3)
        self.assertAlmostEqual(float(t[1][1]), (2 + 2) * (2 / 3))
        t = P.tcb_tangents(times, values, [(1, 0, 0)] * 3)                  # tension 1: flat
        self.assertEqual([float(a) for a, _ in t], [0.0, 0.0, 0.0])

    def test_quaternions_slerp(self):
        import creature_pose as P
        h = np.sqrt(.5)
        rot = {'times': [0.0, 1.0], 'values': np.array([[1.0, 0, 0, 0], [h, 0, 0, h]]), 'type': 3,
               'quaternion': True}
        q = P.sample(rot, .5)
        self.assertAlmostEqual(float(q[0]), np.cos(np.pi / 8), places=6)
        self.assertAlmostEqual(float(q[3]), np.sin(np.pi / 8), places=6)


class RigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = dict(FILES)
        cls.files['meshes/r/xbeast.nif'] = model()
        cls.files['meshes/r/xbeast.kf'] = kf(
            [(0.0, 'idle: start'), (1.0, 'idle: stop'), (1.0, 'death1: start'), (2.0, 'death1: stop')],
            [(b'Bone', (1, [(0.0, (0, 0, 0)), (2.0, (8, 0, 0))])), (b'Dummy', (1, [(0.0, (0, 0, 50)), (2.0, (0, 0, 50))]))])
        cls.files['meshes/xbase_anim.kf'] = kf(
            [(0.0, 'idle: start'), (4.0, 'idle: stop'), (4.0, 'walkforward: loop start'),
             (6.0, 'walkforward: loop stop')], [(b'Bone', (1, [(0.0, (0, 0, 0)), (4.0, (0, 40, 0))]))])

    def rig(self, bipedal=False):
        import creature_pose as P
        from prepare_scenery import nif_reader
        return P.CreatureRig(nif_reader(), reader(self.files), 'r/Beast.NIF', bipedal)

    def test_files_as_the_original_picks_them(self):
        import creature_pose as P
        read = reader(self.files)
        self.assertEqual(P.actor_files(read, 'r/Beast.NIF'), ('meshes/r/xbeast.nif', 'meshes/r/xbeast.kf'))
        files = dict(self.files, **{'meshes/r/xbeast.kf': None})
        self.assertEqual(P.actor_files(reader(files), 'r/beast.nif'), ('meshes/r/beast.nif', None))

    def test_groups_from_the_newest_source(self):
        r = self.rig(bipedal=True)
        self.assertEqual([s['name'] for s in r.sources], ['meshes/xbase_anim.kf', 'meshes/r/xbeast.kf'])
        self.assertEqual(r.window('idle'), (1, 0.0, 1.0))                  # the creature's own file wins
        self.assertEqual(r.window('walk'), (0, 4.0, 6.0))                  # only the shared file has it
        self.assertIsNone(self.rig().window('walk'))
        samples, groups = self.rig().plan()
        self.assertEqual([g['name'] for g in groups if g.get('source') == 'idle'], ['walk', 'run', 'attack', 'hit'])

    def test_repeated_names_and_the_pose(self):
        """The keys move the first Dummy only; the second keeps its own transform (100 up); the pose reaches the
        shapes through model_geometry by position."""
        from prepare_scenery import model_geometry, nif_reader
        from mwad.scene import unpack_geometry
        r = self.rig()
        self.assertEqual(r.duplicates, ['dummy'])
        w = r.worlds(0, 0.5)
        names = [n[0] for n in r.nodes]
        self.assertEqual(names, ['root', 'bone', 'dummy', 'dummy'])
        self.assertEqual(w[1][3, :3].tolist(), [2.0, 0.0, 0.0])
        self.assertEqual(w[2][3, :3].tolist(), [0.0, 0.0, 50.0])
        self.assertEqual(w[3][3, :3].tolist(), [0.0, 0.0, 100.0])
        packet, materials, _, _ = model_geometry(r.raw, nif_reader(), repair_uv=True, pose_world=r.pose_world(0, .5))
        v, f, _ = unpack_geometry(packet)
        v = np.array(v)
        self.assertEqual(sorted({tuple(np.round(x[:3], 3)) for x in v[:4]})[0], (2.0, 0.0, 0.0))
        self.assertEqual(v[4:8, 2].tolist(), [50.0] * 4)
        self.assertEqual(v[8:12, 2].tolist(), [100.0] * 4)

    def test_idle_loop_markers_first(self):
        """A looping idle with loop markers is sampled between them (the loop the original repeats), as the
        resident bake samples it (creature_residents.idle_range); without them from start to stop."""
        import creature_pose as P
        from prepare_scenery import nif_reader
        files = dict(self.files)
        files['meshes/r/xbeast.kf'] = kf(
            [(0.0, 'idle: start'), (0.5, 'idle: loop start'), (1.5, 'idle: loop stop'), (2.0, 'idle: stop')],
            [(b'Bone', (1, [(0.0, (0, 0, 0)), (2.0, (8, 0, 0))]))])
        rig = P.CreatureRig(nif_reader(), reader(files), 'r/beast.nif', False)
        self.assertEqual(rig.window('idle'), (0, 0.5, 1.5))
        self.assertEqual(self.rig().window('idle'), (0, 0.0, 1.0))

    def test_layout(self):
        import creature_pose as P
        samples, groups = self.rig().plan()
        self.assertEqual(len(samples), sum(c for _, c in P.MOVER))
        self.assertTrue(P.layout(groups).startswith('idle:0:8:0.1250 walk:8:8:0.1250'))


class ScaleTableTests(unittest.TestCase):
    def setUp(self):
        from test_chim_levelled import MASTER, LIBRARY
        from chim import actors as A
        self.A, self.master, self.library = A, MASTER, LIBRARY

    def tables(self):
        A, m = self.A, self.master
        refs = A.exterior_actors(m)
        lib = dict(self.library, **{'crab@0.8000': '"classname" "aw_npc"\n"model" "progs/c_crab_s080.mdl"\n',
                                    'rat@2.0000': '"classname" "aw_npc"\n"model" "progs/c_rat_s200.mdl"\n'})
        plain, _ = A.build_table(refs, {}, A.levelled_lists(m), A.creature_ids(m), lib)
        scaled, rep = A.build_table(refs, {}, A.levelled_lists(m), A.creature_ids(m), lib, {14: 0.8, 11: 2.0})
        return plain, scaled, rep

    def test_version_3(self):
        A = self.A
        plain, scaled, rep = self.tables()
        self.assertEqual(A.read_table(plain)[0]['version'], 2)
        head, cells, records, bases, _ = A.read_table(scaled)
        self.assertEqual(head['version'], 3)
        sc = A.read_scales(scaled)
        self.assertEqual({records[i]['key']: round(s, 4) for i, s in sc.items()}, {14: 0.8, 11: 2.0})
        crab = next(r for r in records if r['key'] == 14)
        self.assertIn('c_crab_s080', bases[crab['base']]['text'])
        lists = A.read_lists(scaled)
        lev = bases[next(r for r in records if r['key'] == 11)['base']]
        # the scaled list copy gives the rat at its scale
        targets = [bases[t]['text'] for _, t in lists[lev['list']][2] if t != 0xFFFF and not t & A.NESTED]
        self.assertIn('"model" "progs/c_rat_s200.mdl"\n', targets[0])
        self.assertEqual(rep['levelled']['scaled_list_copies'], 1)
        self.assertEqual(rep['scaled_records'], 2)

    def test_version_2_unchanged_without_scales(self):
        """No scale: the table is the dev line's version 2, byte for byte (SHA-256 of the same synthetic case)."""
        import hashlib
        from test_chim_levelled import table
        data, _ = table()
        self.assertEqual(hashlib.sha256(data).hexdigest(), V2_SHA256)

    @unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
    @unittest.skipUnless(shutil.which('cc'), 'a C compiler is required')
    def test_engine_reads_the_same_scales(self):
        from test_aga_native_source import NativeSourceTests
        from test_chim_engine_native import WARN
        A = self.A
        _, scaled, _ = self.tables()
        head, cells, records, bases, _ = A.read_table(scaled)
        want = ['scale %d %.6g' % (i, A.read_scales(scaled).get(i, 1.0)) for i in range(len(records))]
        with tempfile.TemporaryDirectory(prefix='amiwind-actor-scales-') as tmp:
            path = Path(tmp) / 'chim-actors.cca'
            path.write_bytes(scaled)
            out = Path(tmp) / 'out.txt'
            NativeSourceTests.compile_run(self, 'aga_chim_scales_test.c',
                                          [SRC / 'chim/chim_format.c', SRC / 'chim/chim_actor_table.c'],
                                          cflags=[*WARN, '-O1'], arguments=[str(path), str(out)])
            lines = out.read_text(encoding='ascii').splitlines()
        self.assertEqual(lines[:3], ['refused order', 'refused count', 'valid'])
        self.assertEqual(lines[3:], want)


V2_SHA256 = '3c6a879c5895e3eac5241774bd0f6523f22ce7319bdbd37a47630f43d8f7f973'   # the dev line 48353e8d's output


class KeyTests(unittest.TestCase):
    def test_no_default_bake_reaches_the_new_module(self):
        """The NPC, gallery and resident bakes keep their own code: none imports creature_pose or creature_library,
        and no unit kind or the stair code lists them."""
        from chim import units
        from chim import collision
        for f in ('tools/npc_geometry.py', 'tools/creature_residents.py', 'tools/prepare_area.py',
                  'tools/prepare_gallery.py', 'tools/build_gallery.py', 'tools/npc_anim.py', 'tools/prepare_scenery.py'):
            text = (ROOT / f).read_text(encoding='utf-8')
            self.assertNotIn('creature_pose', text, f)
            self.assertNotIn('creature_library', text, f)
        for kind in units.CODE_ENTRIES:
            for module in ('tools/creature_pose.py', 'tools/creature_library.py'):
                self.assertNotIn(module, units.TOOLS.get(kind, []), kind)
        self.assertFalse(any('creature_' in f for f in collision.stair_code_selection()[0]))


if __name__ == '__main__':
    unittest.main()
