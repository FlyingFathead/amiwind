# SPDX-License-Identifier: GPL-3.0-only
"""The CHIM actor table (EXPERIMENTAL, --chim-actor-table on; tools/chim/actors.py, engine chim/chim_actor_table.c
and aw_actors.c "chim actors table 1"): every exterior NPC and creature reference of the game data in one table
outside the frames.

A synthetic master (NPC, creature and levelled creature references in exterior and interior cells, one deleted) and
a synthetic frame map with built actor rows (a resident, an intro role, a dead resident) are turned into a table;
checked: which references it holds and with which flags, the built rows' positions moved to their own cell's local
units, the base text the engine parses (the frame map row's fields without the per-placement ones, which the record
gives back: like for like with the frame map row), the engine's decoders reading the same table (native), and that
no unit kind and no stair code reaches the module. Synthetic data only.
"""
import os
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'src', ROOT / 'tools', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
SRC = ROOT / 'engine/aga/src'

from test_entity_tracker import base, cell, record, sub, z  # noqa: E402


def ref(number, ident, pos=(0.0, 0.0, 0.0), rot_z=0.0, deleted=False):
    out = sub('FRMR', struct.pack('<I', number)) + sub('NAME', z(ident))
    out += sub('DATA', struct.pack('<6f', *pos, 0.0, 0.0, rot_z))
    return out + (sub('DELE', b'\0\0\0\0') if deleted else b'')


MASTER = b''.join([
    base('NPC_', 'villager'), base('NPC_', 'guard'), base('CREA', 'mudcrab', 'r\\mudcrab.nif'), base('LEVC', 'random_crab'),
    base('STAT', 'rock', 'x\\rock.nif'),
    cell('', False, 0, 0, ref(101, 'villager', (5000.0, 4000.0, 100.0), 1.0) + ref(102, 'mudcrab', (1000.0, 2000.0, 8.0))
         + ref(103, 'rock') + ref(104, 'guard', (3000.0, 3000.0, 40.0), deleted=True)),
    cell('', False, 1, 0, ref(201, 'guard', (8192.0 + 4196.0, 4100.0, 60.0)) + ref(202, 'random_crab', (9000.0, 100.0, 0.0))),
    cell('Some Inn', True, refs=ref(301, 'villager')),
])

# a frame map whose frame is cell 0,0 (centre 4096, 4096): the guard of cell 1,0 stands in it at local x 2075
ROWS = [
    {'classname': 'worldspawn', '_chim_frame': '0 0'},
    {'classname': 'aw_npc', 'aw_ref': '201', 'model': 'progs/a_guard.mdl', 'origin': '2075.00000 1.00000 15.00000',
     'angles': '0 30.5 0', 'netname': 'Guard', 'aw_voice': 'npc/g.wav', 'aw_source_id': 'guard', 'aw_ground_mode': '0',
     'aw_ground_valid': '1', 'aw_ground_baked': '2075.00000 1.00000 15.00000', 'aw_authored_origin': '2075 1 16',
     'aw_authored_z': '16'},
    {'classname': 'aw_npc', 'aw_ref': '101', 'model': 'progs/a_vil.mdl', 'origin': '226.0 -24.0 25.0',
     'angles': '0 -57.29578 0', 'aw_source_id': 'villager', 'aw_intro_role': '1'},
    {'classname': 'aw_corpse', 'aw_ref': '102', 'model': 'progs/a_crab.mdl', 'origin': '-774 -524 2',
     'angles': '0 0 0', 'aw_source_id': 'mudcrab'},
]


def frame_map(path, rows):
    text = ''.join('{\n' + ''.join('"%s" "%s"\n' % kv for kv in r.items()) + '}\n' for r in rows).encode('ascii')
    header = struct.pack('<i', 29) + struct.pack('<ii', 4 + 15 * 8, len(text)) + b'\0' * (14 * 8)
    Path(path).write_bytes(header + text)


class ActorTableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from chim import actors as A
        cls.tmp = tempfile.TemporaryDirectory(prefix='amiwind-actor-table-')
        maps = Path(cls.tmp.name) / 'maps'
        maps.mkdir()
        frame_map(maps / 'town-chim.chim', ROWS)
        frame_map(maps / 'plain.bsp', ROWS)          # not a .chim frame map: never read
        cls.refs = A.exterior_actors(MASTER)
        cls.built = A.built_actors(maps, {})
        cls.data, cls.report = A.build_table(cls.refs, cls.built)
        cls.table = A.read_table(cls.data)
        cls.path = Path(cls.tmp.name) / 'chim-actors.cca'
        cls.path.write_bytes(cls.data)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_game_data_references(self):
        """Every exterior NPC, creature and levelled creature reference; no interior, deleted or static one."""
        self.assertEqual(sorted((n, t, c) for n, _, t, c, *_ in self.refs),
                         [(101, 'NPC_', (0, 0)), (102, 'CREA', (0, 0)), (201, 'NPC_', (1, 0)), (202, 'LEVC', (1, 0))])
        head, cells, records, bases, _ = self.table
        self.assertEqual(head['records'], 4)
        self.assertEqual([c for c, *_ in cells], [(0, 0), (1, 0)])
        self.assertEqual(self.report['by_kind'], {'NPC_': 2, 'CREA': 0, 'LEVC': 1, 'corpse': 1})

    def test_built_rows(self):
        """The resident row (not the intro role) gives the base text and its exact position in its own cell's
        local units; the dead resident is kept as a corpse (not spawned by the engine's actor join)."""
        from chim import actors as A
        self.assertEqual(set(self.built), {201, 102})
        head, cells, records, bases, _ = self.table
        guard = next(r for r in records if r['key'] == 201)
        self.assertEqual(guard['flags'], A.FLAG_BUILT | A.FLAG_BAKED)
        # frame cell 0,0 -> cell 1,0: x - 2048 (8192 Morrowind units x 0.25)
        self.assertEqual(guard['origin'], (27.0, 1.0, 15.0))
        self.assertEqual(guard['yaw'], 30.5)
        villager = next(r for r in records if r['key'] == 101)
        self.assertEqual(villager['flags'], 0)            # the intro role is not world state: game data only
        self.assertEqual(bases[villager['base']]['text'], '')
        self.assertEqual(villager['origin'], (226.0, -24.0, 25.0))      # (5000 - 4096) x 0.25 ...
        crab = next(r for r in records if r['key'] == 102)
        self.assertEqual(bases[crab['base']]['kind'], A.KINDS['corpse'])
        self.assertEqual(self.report['spawnable_records'], 2)

    def test_like_for_like_with_the_frame_map_row(self):
        """The fields the engine gets (the base text parsed, then the record's origin, angles, reference and baked
        ground) are the frame map row's, its position moved to the cell's local units; only the authored-height
        diagnostics are left out."""
        from chim import actors as A
        head, cells, records, bases, _ = self.table
        guard = next(r for r in records if r['key'] == 201)
        got = {k.decode(): v.decode() for k, v in A.FIELD.findall(bases[guard['base']]['text'].encode())}
        got.update(origin='%g %g %g' % guard['origin'], angles='0 %g 0' % guard['yaw'], aw_ref=str(guard['key']),
                   aw_ground_valid='1', aw_ground_baked='%g %g %g' % guard['origin'])
        want = dict(ROWS[1])
        for k in ('aw_authored_origin', 'aw_authored_z'):
            want.pop(k)
        want.update(origin='27 1 15', aw_ground_baked='27 1 15', angles='0 30.5 0')
        self.assertEqual(got, want)

    def test_refusals(self):
        from chim import actors as A
        with self.assertRaises(ValueError):
            A.read_table(self.data[:-4])
        bad = bytearray(self.data)
        bad[0:4] = b'ACT0'
        with self.assertRaises(ValueError):
            A.read_table(bytes(bad))

    @unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
    @unittest.skipUnless(shutil.which('cc'), 'a C compiler is required')
    def test_engine_decoders_read_the_same_table(self):
        from test_aga_native_source import NativeSourceTests
        from test_chim_engine_native import WARN
        head, cells, records, bases, text = self.table
        with tempfile.TemporaryDirectory(prefix='amiwind-actor-table-c-') as tmp:
            out = Path(tmp) / 'out.txt'
            NativeSourceTests.compile_run(self, 'aga_chim_actor_table_test.c',
                                          [SRC / 'chim/chim_format.c', SRC / 'chim/chim_actor_table.c'],
                                          cflags=[*WARN, '-O1'], arguments=[str(self.path), str(out)])
            lines = out.read_text(encoding='ascii').splitlines()
        want = ['head %d %d %d' % (head['cells'], head['records'], head['bases'])]
        want += ['cell %d %d %d %d' % (c[0], c[1], first, n) for c, first, n in cells]
        want += ['rec %d %d %d %.9g %.9g %.9g %.9g' % (r['key'], r['base'], r['flags'], *r['origin'], r['yaw'])
                 for r in records]
        want += ['base %d %d %d %s' % (b['kind'], b['hash'], len(b['text']), b['text'].encode('latin1').hex())
                 for b in bases]
        self.assertEqual(lines, want)


class ActorTableKeyTests(unittest.TestCase):
    def test_no_unit_kind_or_stair_code_reaches_the_module(self):
        from chim import units
        from chim import collision
        for kind in units.CODE_ENTRIES:
            self.assertNotIn('tools/chim/actors.py', units.TOOLS.get(kind, []), kind)
            key = units.unit_code_key(kind)
            self.assertFalse(any('chim/actors.py' in str(u) for u in key.get('units', key.get('reach', []))), kind)
        self.assertFalse(any('chim/actors.py' in f for f in collision.stair_code_selection()[0]))

    def test_on_ships_a_config_that_turns_the_table_on(self):
        # The engine reads the table only with "chim actors table 1" (aw_actors.c table_on, off by default, not saved):
        # v0.0.47-dev2 shipped maps/chim-actors.cca without it and spawned no outdoor actors. A build with the table
        # (the default since v0.0.47) ends default-game.cfg with that line; off writes nothing.
        import tempfile
        import types
        import build_aga
        shipped = (ROOT / 'config' / 'game.cfg').read_bytes()
        self.assertNotIn(b'chim actors table', shipped)
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / 'default-game.cfg'
            cfg.write_bytes(shipped)
            for value in (None, 'off'):
                self.assertIsNone(build_aga.stage_chim_actor_table_config(
                    types.SimpleNamespace(chim_actor_table=value), tmp))
                self.assertEqual(cfg.read_bytes(), shipped)
            rec = build_aga.stage_chim_actor_table_config(types.SimpleNamespace(chim_actor_table='on'), tmp)
            self.assertEqual(rec, {'on': True, 'config': 'id1/default-game.cfg', 'line': 'chim actors table 1'})
            raw = cfg.read_bytes()
            self.assertTrue(raw.startswith(shipped))
            self.assertTrue(raw.endswith(b'\nchim actors table 1\n'))
            added = raw[len(shipped):].decode('ascii').splitlines()
            self.assertTrue(all(line.startswith('//') for line in added[:-1]) and len(added) > 1, added)
            self.assertNotIn(b'\r', raw)
        # the image step stages it with the game config and records it; the default plan passes the table on
        image = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        self.assertIn("args.image_chim_actor_table_config=stage_chim_actor_table_config(args, boot/'id1')", image)
        self.assertIn("build_json['chim_actor_table_config'] = args.image_chim_actor_table_config", image)
        # the engine side: the line the config writes is the command that turns the table on
        engine = (SRC / 'aw_actors.c').read_text(encoding='utf-8')
        self.assertIn('!strcmp (a, "table")', engine)
        self.assertIn('table_on = atoi (Cmd_Argv (3)) != 0;', engine)
        from test_build_defaults import steps
        default = [str(part) for part in dict(steps())['image']]
        self.assertEqual(default[default.index('--chim-actor-table') + 1], 'on')

    def test_options_defaults(self):
        import build
        # build.py: on by default since v0.0.47 (decided for the project, 2026-10-21); off stays selectable
        self.assertEqual(build.parser().parse_args([]).chim_actor_table, 'on')
        self.assertEqual(build.parser().parse_args(['--chim-actor-table', 'off']).chim_actor_table, 'off')
        # the image step's option (build_aga.py main builds its parser inline): off unless build.py passes on, and the
        # table is written only when it is on
        text = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        self.assertIn("i.add_argument('--chim-actor-table', choices=('off', 'on'), default='off',", text)
        self.assertIn("if getattr(args, 'chim_actor_table', 'off') == 'on':", text)


if __name__ == '__main__':
    unittest.main()
