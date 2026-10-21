# SPDX-License-Identifier: GPL-3.0-only
"""--chim-crossing 0|1 (tools/chim_crossing.py): the cell crossing method an image starts with.

Default 0 (type 0) writes nothing: the image step's command, every stage key and the game settings are the same as
before the option existed. 1 adds the image step's --chim-crossing 1, which ends default-game.cfg with
"chim crossing 1" (docs/chim/CELL_CROSSINGS.md). The engine side: the "chim" command is registered before
quake.rc runs and its "crossing" subcommand needs no loaded world.
"""
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]
sys.path.insert(0, str(Path(__file__).resolve().parent))  # tests/ when run as a file

import chim_crossing as cc  # noqa: E402

SRC = ROOT / 'engine' / 'aga' / 'src'


def code(name):
    return (SRC / name).read_text(encoding='utf-8')


def function(text, head):
    start = text.index(head)
    return text[start:text.index('\n}\n', start) + 3]


class OptionTests(unittest.TestCase):
    def test_default_is_type_1(self):
        # decided for the project, 2026-10-21 (v0.0.47 = v0.0.47-dev2's content, built with --chim-crossing 1)
        self.assertEqual(cc.DEFAULT, '1')
        for value in (None, '1'):
            rec = cc.configure(types.SimpleNamespace(chim_crossing=value))
            self.assertEqual(rec, {'type': 1, 'source': 'default'})
            self.assertEqual(cc.image_arguments(rec), ['--chim-crossing', '1'])

    def test_legacy_builder_gets_type_0(self):
        # a legacy-builder image has no CHIM world: type 0, nothing written (its image step as before)
        rec = cc.configure(types.SimpleNamespace(chim_crossing='1'), 'legacy')
        self.assertEqual(rec['type'], 0)
        self.assertEqual(cc.image_arguments(rec), [])
        self.assertEqual(cc.configure(types.SimpleNamespace(chim_crossing=None), 'chim')['type'], 1)

    def test_type_0_adds_nothing(self):
        zero = cc.configure(types.SimpleNamespace(chim_crossing='0'))
        self.assertEqual(zero, {'type': 0, 'source': '--chim-crossing 0'})
        self.assertEqual(cc.image_arguments(zero), [])
        self.assertEqual(cc.image_arguments(None), [])

    def test_parser_choices_and_default(self):
        import build
        args = build.parser().parse_args([])
        self.assertEqual(args.chim_crossing, '1')
        self.assertEqual(build.parser().parse_args(['--chim-crossing', '1']).chim_crossing, '1')
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            build.parser().parse_args(['--chim-crossing', '2'])


class ImageStepTests(unittest.TestCase):
    def test_type_0_writes_nothing_type_1_writes_the_line(self):
        import build_aga
        shipped = (ROOT / 'config' / 'game.cfg').read_bytes()
        self.assertNotIn(b'chim crossing', shipped)                       # 0 == the game as before
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / 'default-game.cfg'
            cfg.write_bytes(shipped)
            for value in (None, '0'):
                self.assertIsNone(build_aga.stage_chim_crossing(types.SimpleNamespace(chim_crossing=value), tmp))
                self.assertEqual(cfg.read_bytes(), shipped)
            rec = build_aga.stage_chim_crossing(types.SimpleNamespace(chim_crossing='1'), tmp)
            self.assertEqual(rec, {'type': 1, 'config': 'id1/default-game.cfg', 'line': 'chim crossing 1'})
            raw = cfg.read_bytes()
            self.assertTrue(raw.startswith(shipped))
            self.assertTrue(raw.endswith(b'\nchim crossing 1\n'))
            added = raw[len(shipped):].decode('ascii').splitlines()
            self.assertTrue(all(line.startswith('//') for line in added[:-1]) and len(added) > 1, added)
            self.assertNotIn(b'\r', raw)

    def test_quake_rc_runs_default_game_cfg_before_any_map(self):
        image = (ROOT / 'tools' / 'build_aga.py').read_text(encoding='utf-8')
        rc = image[image.index("(boot/'id1/quake.rc').write_text("):]
        rc = rc[:rc.index('\n')]
        self.assertIn('exec default.cfg\\nexec default-game.cfg\\nexec config.cfg', rc)
        self.assertNotIn('map ', rc)

    def test_receipt_and_wiring(self):
        build = (ROOT / 'tools' / 'build.py').read_text(encoding='utf-8')
        self.assertIn('add_chim_crossing_option(p)', build)
        self.assertIn("args.chim_crossing_record = __import__('chim_crossing').configure(args, resolve_builder(args)"
                      "['builder'])", build)
        self.assertIn('"chim_crossing": getattr(args, \'chim_crossing_record\', None)', build)   # the build receipt
        image = (ROOT / 'tools' / 'build_aga.py').read_text(encoding='utf-8')
        self.assertIn("i.add_argument('--chim-crossing',choices=('0','1'),default='0'", image)
        self.assertIn("args.image_chim_crossing_record=stage_chim_crossing(args, boot/'id1')", image)
        self.assertIn("build_json['chim_crossing'] = args.image_chim_crossing_record", image)   # the image receipt


class PlanTests(unittest.TestCase):
    """The option belongs to the image step only; type 0 (--chim-crossing 0) gives the image step and its key
    as before the option existed."""

    @staticmethod
    def plan(*extra):
        from test_build_defaults import steps
        return steps(*extra)

    def test_type_0_writes_nothing_and_1_reaches_only_the_image_step(self):
        zero = self.plan('--chim-crossing', '0')
        self.assertEqual(self.plan(), self.plan('--chim-crossing', '1'))
        for name, command in zero:
            self.assertNotIn('--chim-crossing', [str(part) for part in command], name)
        one = dict(self.plan())
        image = [str(part) for part in one['image']]
        at = image.index('--chim-crossing')
        self.assertEqual(image[at + 1], '1')
        self.assertEqual(image[:at] + image[at + 2:], [str(part) for part in dict(zero)['image']])
        for name, command in zero:
            if name != 'image':
                self.assertEqual(one[name], command, name)

    def test_stage_keys_default_unchanged_type_1_rekeys_only_the_image(self):
        import build_cache
        from test_build_defaults import TOOLS, RUN

        def keys(*extra):
            index = build_cache.SourceIndex()
            return build_cache.fingerprint_steps(self.plan(*extra), RUN, {'tools': TOOLS}, index)[0]

        default, zero, one = keys(), keys('--chim-crossing', '0'), keys('--chim-crossing', '1')
        self.assertEqual(default, one)
        self.assertEqual({name for name in zero if zero[name] != one[name]}, {'image'})


class EngineTests(unittest.TestCase):
    """A config line before any map really selects type 1: the command exists by then and needs no world."""

    def test_crossing_subcommand_sets_window_wanted_without_a_world(self):
        world = code('chim/chim_world.c')
        status = function(world, 'static void Status (void)')
        self.assertTrue(status.split('{', 1)[1].split('ChimZone_Stats', 1)[0].count('if (Subcommand ())'))
        sub = function(world, 'static int Subcommand (void)')
        crossing = sub[sub.index('if (!strcmp (argv[0], "crossing"))'):]
        self.assertIn('ChimChunks_WindowOn (atoi (argv[1]));', crossing)
        before = sub[:sub.index('if (!strcmp (argv[0], "crossing"))')]
        self.assertNotIn('active', before)                    # nothing before it asks for a loaded world
        chunks = code('chim/chim_chunks.c')
        self.assertEqual(chunks.count('window_wanted = '), 1)  # only the command sets it; never reset by a map
        self.assertIn('window_wanted = on != 0;', function(chunks, 'int ChimChunks_WindowOn (int on)'))

    def test_command_registered_before_quake_rc(self):
        self.assertIn('Cmd_AddCommand ("chim", Status);', function(code('chim/chim_world.c'), 'void Chim_Init (void)'))
        self.assertIn('Chim_Init();', code('aw_debug.c'))
        self.assertIn('AW_DebugInit();', function(code('host_cmd.c'), 'void Host_InitCommands (void)'))
        host = code('host.c')
        self.assertLess(host.index('Host_InitCommands ();'), host.index('Cbuf_InsertText ("exec quake.rc\\n");'))


if __name__ == '__main__':
    unittest.main()
