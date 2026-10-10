"""The animation kit (docs/ANIMKIT.md): the builder switch, the dbg animkit command, the MiniWind preset."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools'), str(Path(__file__).resolve().parent)]
import build  # noqa: E402
import test_aga_native_source as native  # noqa: E402

SRC = ROOT / 'engine' / 'aga' / 'src'
UBSAN = ['-fsanitize=undefined', '-fno-sanitize-recover=all']


def resolved(argv):
    """npc_anim after build.main's resolution, without running a build."""
    args = build.parser().parse_args(argv)
    if args.npc_anim is None:
        args.npc_anim = build.ANIM_KIT_PROFILES[args.anim_kit]
    return args.npc_anim


class BuilderSwitch(unittest.TestCase):
    def test_kit_is_on_by_default_and_off_is_the_previous_method(self):
        self.assertEqual(build.parser().parse_args([]).anim_kit, 'on')
        self.assertEqual(resolved([]), 'react+full')
        self.assertEqual(resolved(['--anim-kit', 'off']), 'idle')
        self.assertEqual(resolved(['--anim-kit', 'off', '--npc-anim', 'move']), 'move')  # --npc-anim wins
        text = (ROOT / 'tools/build.py').read_text(encoding='utf-8')
        self.assertIn('args.npc_anim = ANIM_KIT_PROFILES[getattr(args, "anim_kit", "on")]', text)


class Console(unittest.TestCase):
    def test_parser_table_and_kit_switch(self):
        native.NativeSourceTests().compile_run('aga_animkit_test.c', [SRC / 'aw_animkit_rules.c', SRC / 'aw_anim.c'],
                                               defines=['AW_ANIM_HOST_TEST'], cflags=UBSAN)

    def test_compiled_out_kit_plays_idle(self):
        # -DAW_ANIMKIT=0: the build-time switch beside the cvar (docs/ANIMKIT.md).
        native.NativeSourceTests().compile_run('aga_animkit_test.c', [SRC / 'aw_animkit_rules.c', SRC / 'aw_anim.c'],
                                               defines=['AW_ANIM_HOST_TEST', 'AW_ANIMKIT=0'], cflags=UBSAN)
        source = (SRC / 'aw_animkit.c').read_text(encoding='utf-8')
        self.assertIn('#if !AW_ANIMKIT', source)
        self.assertIn('if(!AW_ANIMKIT || !aw_anim_kit_enabled)return AW_ANIM_IDLE;',
                      (SRC / 'aw_anim.c').read_text(encoding='utf-8'))

    def test_command_is_registered_catalogued_and_ticked(self):
        catalogue = (ROOT / 'config/debug-commands.txt').read_text(encoding='utf-8')
        self.assertRegex(catalogue, r'(?m)^PLAYTESTING\|animkit\|aw_animkit\|\[on/off / list / play <group> / stop')
        self.assertIn('Cmd_AddCommand("aw_animkit",command);', (SRC / 'aw_animkit.c').read_text(encoding='utf-8'))
        self.assertIn('AW_AnimKitInit();', (SRC / 'aw_debug.c').read_text(encoding='utf-8'))
        self.assertIn('AW_AnimKitTick();', (SRC / 'host.c').read_text(encoding='utf-8'))
        makefile = (ROOT / 'engine/aga/Makefile').read_text(encoding='utf-8')
        self.assertIn('aw_anim.c aw_animkit_rules.c aw_animkit.c', makefile)


class Preset(unittest.TestCase):
    def test_animkit_sandbox_row(self):
        rows = json.loads((ROOT / 'config/miniwind-presets.json').read_text(encoding='utf-8'))['presets']
        row = next(r for r in rows if r['name'] == 'animkit')
        self.assertEqual(row['scope'], 'exterior')
        self.assertEqual(row['start'], 'balmora')
        args = build.parser().parse_args(['--miniwind-animkit'])
        self.assertEqual(args.miniwind_preset, 'animkit')
        # The sandbox sets itself up on arrival: a companion and fighting NPCs (miniwind.txt "boot").
        self.assertEqual(row['boot_commands'], ['dbg companion test', 'dbg combat on'])
        import miniwind
        line = miniwind.boot_line(row['boot_commands'])
        data = miniwind.data_file('FEATURES ONLY: Balmora exterior (CHIM)', boot=line).decode('ascii')
        self.assertIn('\nboot dbg companion test;dbg combat on\n', data)
        for bad in (['map seyda'], ['dbg x;quit'], ['dbg "x"']):
            with self.assertRaises(ValueError):
                miniwind.boot_line(bad)
        header = (SRC / 'aw_miniwind.h').read_text(encoding='utf-8')
        self.assertIn('#define AW_MINIWIND_BOOT %d' % (miniwind.BOOT_CHARS + 1), header)


class Docs(unittest.TestCase):
    def test_page_lists_the_flag_commands_preset_and_sources(self):
        page = (ROOT / 'docs/ANIMKIT.md').read_text(encoding='utf-8')
        for item in ('--anim-kit', 'aw_animkit', 'dbg animkit list', 'dbg animkit play', 'dbg animkit speed',
                     '--miniwind-animkit', 'aifollow.cpp', 'aicombat.cpp', 'fBaseRunMultiplier'):
            self.assertIn(item, page)
        self.assertIn('docs/ANIMKIT.md', json.loads((ROOT / 'tools/release-files.json').read_text(encoding='utf-8')))


if __name__ == '__main__':
    unittest.main()
