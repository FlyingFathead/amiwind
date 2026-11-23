# SPDX-License-Identifier: GPL-3.0-only
"""The end pose of a script's animation group on a placed object (tools/chim/anim_poses.py, MWSCRIPT-PLAYGROUP-ACTORS-
ONLY-68): the Halls of Penumbra's ice wall shattered by its script's LoopGroup idle2, the Clockwork City's doors opened
by their levers' scripts.

Synthetic data only (no game files): a model built here with text keys, a keyframed piece, an effect hidden by its
visibility controller and a material faded by its alpha controller; a master built here with scripts, objects and a
dialogue result. Checked: the calls are read in every form the game's scripts write them (commas, quoted ids and groups,
a named target, comments); the objects a script plays a group on, its own and a named one, and never an actor; a
group's times from its text keys; the controllers' time rules (constant, cycle, reverse); the pose at the group's stop
key (the piece where its keys end, the effect hidden, the faded shape hidden) through the converter's own reading, and
a group whose end is the model as placed makes no model; the pose table's round trip and its kinds; and the stage's
store step: the end-pose model takes a store id after every room's own models (no other id moves), only that room's
record lists it, and a room without poses keeps its record byte for byte.
"""
import io
import struct
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
# src before tools: tools/mwad.py must not shadow the src/mwad package (TEST-WORKER-SYSPATH-32)
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


def _box(N, name, offset):
    shape = N.NiTriShape()
    shape.name = name
    data = N.NiTriShapeData()
    corners = [(0, 0, 0), (8, 0, 0), (8, 8, 0), (0, 8, 0)]
    data.num_vertices = 4
    data.has_vertices = True
    data.vertices.update_size()
    for v, c in zip(data.vertices, corners):
        v.x, v.y, v.z = c[0] + offset, c[1], c[2]
    data.num_triangles = 2
    data.num_triangle_points = 6
    data.has_triangles = True
    data.triangles.update_size()
    for t, c in zip(data.triangles, [(0, 1, 2), (0, 2, 3)]):
        t.v_1, t.v_2, t.v_3 = c
    shape.data = data
    return shape


def _node(N, name, children, x=0.0):
    n = N.NiNode()
    n.name = name
    n.translation.x = x
    n.num_children = len(children)
    n.children.update_size()
    for i, c in enumerate(children):
        n.children[i] = c
    return n


def _chain(owner, items, attr):
    for a, b in zip(items, items[1:]):
        setattr(a, 'next_' + attr, b)
    setattr(owner, attr, items[0] if items else None)


def model(fade=True):
    """Root (text keys: Idle 0-1, Idle2 1-3) -> Piece (a box; its keys move it from x 0 to x 100 between 1.5 and 2.5),
    Fx (a box shown, hidden at 2.0 by its visibility controller), Glow (a box whose material fades to 0 by 3.0)."""
    from prepare_scenery import nif_reader
    N = nif_reader()
    d = N.Data(version=0x04000002)
    piece = _node(N, b'Piece', [_box(N, b'Tri Piece', 0)])
    move = N.NiKeyframeController()
    move.flags, move.frequency, move.start_time, move.stop_time = 12, 1.0, 1.5, 2.5
    data = N.NiKeyframeData()
    data.translations.num_keys = 2
    data.translations.interpolation = 1
    data.translations.keys.update_size()
    for key, (t, x) in zip(data.translations.keys, [(1.5, 0.0), (2.5, 100.0)]):
        key.time = t
        key.value.x, key.value.y, key.value.z = x, 0.0, 0.0
    move.data = data
    _chain(piece, [move], 'controller')
    fx = _node(N, b'Fx', [_box(N, b'Tri Fx', 20)])
    vis = N.NiVisController()
    vis.flags, vis.frequency, vis.start_time, vis.stop_time = 12, 1.0, 1.0, 2.0
    vdata = N.NiVisData()
    vdata.num_keys = 2
    vdata.keys.update_size()
    for key, (t, v) in zip(vdata.keys, [(1.0, 1), (2.0, 0)]):
        key.time, key.value = t, v
    vis.data = vdata
    _chain(fx, [vis], 'controller')
    glow_shape = _box(N, b'Tri Glow', 40)
    material = N.NiMaterialProperty()
    material.alpha = 1.0
    if fade:
        alpha = N.NiAlphaController()
        alpha.flags, alpha.frequency, alpha.start_time, alpha.stop_time = 12, 1.0, 1.0, 3.0
        adata = N.NiFloatData()
        adata.data.num_keys = 2
        adata.data.interpolation = 1
        adata.data.keys.update_size()
        for key, (t, v) in zip(adata.data.keys, [(1.0, 1.0), (3.0, 0.0)]):
            key.time, key.value = t, v
        alpha.data = adata
        _chain(material, [alpha], 'controller')
    glow_shape.num_properties = 1
    glow_shape.properties.update_size()
    glow_shape.properties[0] = material
    glow = _node(N, b'Glow', [glow_shape])
    root = _node(N, b'Root', [piece, fx, glow])
    text = N.NiTextKeyExtraData()
    keys = [(0.0, 'Idle: Start'), (1.0, 'Idle: Stop\r\nIdle2: Start'), (3.0, 'Idle2: Stop')]
    text.num_text_keys = len(keys)
    text.text_keys.update_size()
    for k, (t, v) in zip(text.text_keys, keys):
        k.time, k.value = t, v.encode('ascii')
    _chain(root, [text], 'extra_data')
    d.roots = [root]
    s = io.BytesIO()
    d.write(s)
    return s.getvalue()


def record(tag, subs):
    payload = b''.join(t.encode('ascii') + struct.pack('<I', len(v)) + v for t, v in subs)
    return tag.encode('ascii') + struct.pack('<III', len(payload), 0, 0) + payload


def z(text, size=None):
    b = text.encode('cp1252') + b'\0'
    return b if size is None else b.ljust(size, b'\0')


def master():
    """A master with: the ice wall's script on its activator (PlayGroup idle, LoopGroup idle2 0 1); a lever script that
    plays its own group and a named door's ("act_door1"->playgroup "idle2"); a script on a creature (an actor); a
    dialogue result naming the door; and a comment that names a group."""
    wall = ('Begin icewallScript\nshort doOnce\nif ( doOnce == 0 )\n\tPlayGroup idle\nendif\n'
            'if ( button == 0 )\n\tLoopGroup idle2 0 1 ; the wall breaks\nendif\nEnd icewallScript\n')
    lever = ('begin LeverScript\n;playgroup "idle9" is only a comment\nif ( move == 1 )\n\tplaygroup "idle2"\n'
             '\t"act_door1"->playgroup "idle3"\nendif\nMessageBox "a ; inside quotes" \nend\n')
    beast = 'begin BeastScript\nPlayGroup, Idle2\nend\n'
    out = record('TES3', [('HEDR', b'\0' * 300)])
    for name, text in (('icewallScript', wall), ('LeverScript', lever), ('BeastScript', beast)):
        out += record('SCPT', [('SCHD', z(name, 52)), ('SCTX', text.encode('cp1252'))])
    out += record('ACTI', [('NAME', z('bm_ice_wall')), ('MODL', z('f\\BM_ice_wall.NIF')), ('SCRI', z('icewallScript'))])
    out += record('ACTI', [('NAME', z('act_lever1')), ('MODL', z('i\\lever.nif')), ('SCRI', z('LeverScript'))])
    out += record('ACTI', [('NAME', z('act_door1')), ('MODL', z('i\\door.nif'))])
    out += record('CREA', [('NAME', z('beast')), ('MODL', z('r\\beast.nif')), ('SCRI', z('BeastScript'))])
    out += record('INFO', [('INAM', z('123')), ('BNAM', b'"act_door1"->PlayGroup, Idle2')])
    return out


class CallTests(unittest.TestCase):
    def test_every_form_of_a_call(self):
        from chim.anim_poses import group_calls
        self.assertEqual(group_calls('PlayGroup, Idle2\nLoopGroup idle2 0 1\n"act_sotha_pre_door1"->playgroup "idle2"\n'
                                     ';PlayGroup idle9\nMessageBox "x ; y"\nact_x->LoopGroup Idle3, 5'),
                         [(None, 'playgroup', 'idle2'), (None, 'loopgroup', 'idle2'),
                          ('act_sotha_pre_door1', 'playgroup', 'idle2'), ('act_x', 'loopgroup', 'idle3')])

    def test_objects_from_the_scripts_and_dialogue(self):
        from chim.anim_poses import scripted_groups
        found = scripted_groups(master())
        self.assertEqual(found['objects'], {
            'act_door1': {'idle2': ['dialogue result 123'], 'idle3': ['LeverScript']},
            'act_lever1': {'idle2': ['LeverScript']},
            'bm_ice_wall': {'idle': ['icewallScript'], 'idle2': ['icewallScript']}})
        self.assertEqual(found['models']['bm_ice_wall'], 'f\\BM_ice_wall.NIF')
        self.assertEqual((found['calls'], found['actor_calls'], found['unknown_targets']), (6, 1, []))


class PoseTests(unittest.TestCase):
    def setUp(self):
        from prepare_scenery import nif_reader
        self.N = nif_reader()

    def test_group_times_and_end(self):
        from chim.anim_poses import group_end, group_times, read_nif
        times = group_times(read_nif(model(), self.N), self.N)
        self.assertEqual(sorted(times), ['idle', 'idle2'])
        self.assertEqual((times['idle2']['start'], times['idle2']['stop']), (1.0, 3.0))
        self.assertEqual(group_end(times['idle2']), (3.0, 2.0))
        self.assertEqual(group_end(times['idle2'], 2), (3.0, 6.0))      # no loop keys: two more plays of the whole

    def test_controller_time_rules(self):
        from chim.anim_poses import controller_time

        class C:
            frequency, phase, start_time, stop_time = 1.0, 0.0, 1.0, 3.0
        c = C()
        # constant (flags 12) clamps; cycle (8) starts again at the start; reverse (10) runs back on odd cycles
        for flags, t, want in ((12, 0.0, 1.0), (12, 9.0, 3.0), (8, 4.5, 2.5), (10, 4.5, 1.5), (12, 2.0, 2.0)):
            c.flags = flags
            self.assertAlmostEqual(controller_time(c, t), want, msg='flags %d t %s' % (flags, t))

    def test_end_pose_moves_hides_and_fades(self):
        from chim.anim_poses import converted, pose_same, posed_nif, read_nif, _blocks
        raw = model()
        posed, info = posed_nif(raw, self.N, 'idle2')
        self.assertIsNotNone(posed)
        self.assertEqual(info['moved'], ['Piece'])
        self.assertEqual(sorted(info['hidden']), ['Fx', 'Tri Glow'])
        self.assertEqual((info['end'], info['seconds']), (3.0, 2.0))
        piece = next(b for b in _blocks(read_nif(posed, self.N)) if getattr(b, 'name', b'') == b'Piece')
        self.assertAlmostEqual(piece.translation.x, 100.0)
        drawn, (source, collision) = converted(posed, self.N)
        base, _ = converted(raw, self.N)
        self.assertEqual((base[1], drawn[1]), (6, 2))           # three boxes as placed, the moved one alone at the end
        self.assertAlmostEqual(float(drawn[0][:, 0].min()), 100.0)
        self.assertEqual(source, 'visual')
        self.assertFalse(pose_same(raw, posed, self.N))

    def test_a_group_ending_as_placed_makes_no_model(self):
        from chim.anim_poses import posed_nif
        posed, info = posed_nif(model(), self.N, 'idle')
        self.assertIsNone(posed)
        self.assertEqual(info['reason'], 'its end pose is the model as placed')
        self.assertIsNone(posed_nif(model(), self.N, 'idle7')[0])

    def test_rotation_is_written_where_the_file_keeps_it(self):
        from chim.anim_poses import quaternion_matrix, read_nif, set_rotation, write_nif, _blocks
        data = read_nif(model(), self.N)
        piece = next(b for b in _blocks(data) if getattr(b, 'name', b'') == b'Piece')
        q = (0.846, 0.534, 0.0, 0.0)
        set_rotation(piece, quaternion_matrix(q))
        again = next(b for b in _blocks(read_nif(write_nif(data), self.N)) if getattr(b, 'name', b'') == b'Piece')
        self.assertTrue(np.allclose(np.array(again.rotation.as_list()), quaternion_matrix(q), atol=1e-5))


class TableTests(unittest.TestCase):
    def test_round_trip_and_kinds(self):
        from chim.anim_poses import read_pose_table, write_pose_table
        rows = [('rif61f4dc044', 8417459, 'idle2', 'M', 7900, 7.2, 7.2, ((220, 1600, -460), (540, 1950, -240))),
                ('rif61f4dc044', 8417459, 'idle', 'B', 7318, 2.6667, 2.6667, ((227, 1653, -453), (537, 1907, -247))),
                ('ri60b45e81e3', 4198001, 'idle2', 'H', -1, 0.9, 0.9, ((0, 0, 0), (1, 1, 1)))]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'poses.txt'
            write_pose_table(path, rows)
            text = path.read_text()
            self.assertTrue(text.startswith('AWPG1\nR ri60b45e81e3 4198001 idle2 H -1 0.9000 0.9000 0 0 0 1 1 1\n'))
            back = read_pose_table(path)
        self.assertEqual(back, sorted(rows, key=lambda t: (t[0], t[1], t[2])))


class StoreStepTests(unittest.TestCase):
    """chim.anim_poses.store_poses on the stage's own record writer (chim.interior.room_record): the end-pose model
    after every room's own models, listed only by its room."""

    def test_end_pose_models_after_all_rooms_own(self):
        from chim.anim_poses import read_pose_table, store_poses
        from chim.interior import STORE, room_record

        class FakeStore:
            def __init__(self):
                self.model_records, self.packs = [], []

            def close_pack(self):
                pass

            def model_id(self, variant, textures):
                for i, (name, image, _) in enumerate(self.model_records):
                    if image == variant['image']:
                        return i
                self.model_records.append((variant['name'], variant['image'], None))
                return len(self.model_records) - 1
        store = FakeStore()
        # two rooms' own models first (ids 0..2), as Store.add_room gives them in the room loop
        for name in ('wall', 'rock', 'chest'):
            store.model_id({'name': name, 'image': name.encode()}, {})
        records = [b'\x01' * 56, b'\x02' * 56]
        parts = {'rif61f4dc044': (((0, 0, 0), (9, 9, 9)), [0, 1], records,
                                  {8417459: (0, (390.0, 1776.0, -412.0), (0.0, -270.0, 0.0), ((227, 1653, -453),
                                                                                             (537, 1907, -247)))})}
        spec = {'placements': [{'ref': 1, 'variant': 0}], 'textures': {},
                'variants': [{'name': 'wall@idle2', 'image': b'posed', 'lo': (-10.0, -10.0, 0.0), 'hi': (10.0, 10.0, 5.0)}]}
        room = {'poses': [{'ref': 8417459, 'group': 'idle2', 'kind': 'model', 'pseudo': 0, 'seconds': 7.2, 'loop': 7.2,
                           'id': 'bm_ice_wall'},
                          {'ref': 8417459, 'group': 'idle', 'kind': 'base', 'seconds': 2.6667, 'loop': 2.6667,
                           'id': 'bm_ice_wall'},
                          {'ref': 123, 'group': 'idle2', 'kind': 'model', 'pseudo': 0, 'seconds': 1.0, 'loop': 1.0}],
                'pose_spec': spec}
        rows = {'rif61f4dc044': {'room': 'rif61f4dc044', 'models': 2}, 'other': {'room': 'other', 'models': 1}}
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / STORE / 'rooms').mkdir(parents=True)
            other = room_record(((0, 0, 0), (1, 1, 1)), [2], [b'\x03' * 56])
            (Path(tmp) / STORE / 'rooms' / 'other.crm').write_bytes(other)
            out = store_poses(store, tmp, [('rif61f4dc044', room)], rows, parts)
            data = (Path(tmp) / STORE / 'rooms' / 'rif61f4dc044.crm').read_bytes()
            table = read_pose_table(Path(tmp) / STORE / 'poses.txt')
            self.assertEqual((Path(tmp) / STORE / 'rooms' / 'other.crm').read_bytes(), other)   # untouched
        # the end pose is store model 3: after the three models the rooms placed (none of their ids moved)
        self.assertEqual([m[0] for m in store.model_records], ['wall', 'rock', 'chest', 'wall@idle2'])
        self.assertEqual(data, room_record(((0, 0, 0), (9, 9, 9)), [0, 1, 3], records))
        self.assertEqual(rows['rif61f4dc044']['models'], 3)
        self.assertEqual(rows['rif61f4dc044']['pose_models'], [3])
        self.assertEqual([(t[2], t[3], t[4]) for t in table], [('idle', 'B', 0), ('idle2', 'M', 3)])
        self.assertEqual(table[0][7], ((227, 1653, -453), (537, 1907, -247)))      # the placed box for the base pose
        self.assertEqual((out['rows'], out['models_added']), (2, 1))
        self.assertEqual([f['ref'] for f in out['failed']], [123])                 # no single placement: not made


class FitDropTests(unittest.TestCase):
    """chim.anim_poses._store_drop_tail on the stage's own Store: the end-pose models a room the 32 MB minimum cannot
    hold are taken out, the others renumbered after the rooms' own models; the rooms' packs untouched."""

    def test_tail_models_dropped_and_renumbered(self):
        import hashlib
        from chim.anim_poses import _store_drop_tail
        from chim.interior import Store
        store = Store()

        def add(name, image):
            mid = len(store.model_records)
            digest = hashlib.sha256(image).hexdigest()
            store.model_content[digest] = mid
            store.model_names[name] = digest
            store.model_records.append((name, image, None))
            store._homed(b'MODL', mid, image)
            return mid
        add('wall', b'W')
        add('rock', b'R')
        store.close_pack()
        room_pack = list(store.packs[0])
        first_model, first_pack = len(store.model_records), len(store.packs)
        for name in ('wall@idle2', 'akulakhan@death1', 'door@idle2'):
            add(name, name.encode())
        store._homed(b'TEXR', 7, b'texture')
        store.close_pack()
        _store_drop_tail(store, first_model, first_pack, {2: 2, 4: 3})
        self.assertEqual([r[0] for r in store.model_records], ['wall', 'rock', 'wall@idle2', 'door@idle2'])
        self.assertEqual(store.packs[0], room_pack)                       # the rooms' pack as it was
        self.assertEqual(store.packs[1], [(b'MODL', 2, b'wall@idle2'), (b'MODL', 3, b'door@idle2'),
                                          (b'TEXR', 7, b'texture')])
        self.assertEqual(store.model_content[hashlib.sha256(b'door@idle2').hexdigest()], 3)
        self.assertNotIn(hashlib.sha256(b'akulakhan@death1').hexdigest(), store.model_content)
        self.assertNotIn('akulakhan@death1', store.model_names)
        self.assertEqual(store.home[(b'MODL', 3)], 1)

    def test_record_models_drops_and_renumbers(self):
        from chim.anim_poses import record_models
        from chim.interior import room_record
        from chim.room_records import read_room_record
        records = [b'\x05' * 56]
        data = room_record(((0, 0, 0), (1, 1, 1)), [0, 1, 7, 9], records)
        self.assertEqual(read_room_record(record_models(data, drop={7}, mapping={9: 8}))['models'], [0, 1, 8])


if __name__ == '__main__':
    unittest.main()
