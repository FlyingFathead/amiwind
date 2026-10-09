# SPDX-License-Identifier: GPL-3.0-only
"""Every FS-UAE configuration AmiWind ships or writes keeps the cursor keys for the game.

FS-UAE's default for joystick port 1 is "auto", which falls back to keyboard joystick emulation
(cursor keys + Right Ctrl) when no gamepad is connected; the game would then never see the arrows
(console history, menus, movement). CONSOLE-HISTORY-ARROWS-32.
"""
import configparser
import importlib.util
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

KEYBOARD_PORT = re.compile(r'^\s*joystick_port_[0-3]\s*=\s*keyboard', re.M | re.I)
SLOW_PRESET = ROOT / 'resources/emulators/AmiWind-SlowAccelerator-FS-UAE.fs-uae'
# The only lines in which the slow accelerator preset may differ from the normal preset
# (besides the disk lines: it also names the world disk).
SPEED_KEYS = {'jit_compiler', 'uae_cpu_speed', 'uae_cpu_cycle_exact', 'uae_cpu_multiplier'}


def version():
    return (ROOT / 'VERSION').read_text(encoding='utf-8').strip()


def settings(path):
    parser = configparser.ConfigParser(interpolation=None, delimiters=('=',), strict=True)
    parser.read_string(path.read_text(encoding='utf-8'))
    return dict(parser['config'])


def launcher():
    spec = importlib.util.spec_from_file_location('fsuae_launcher', ROOT / 'tools/AmiWind-FS-UAE-launcher.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FsUaeKeyboardPortTests(unittest.TestCase):
    def assert_ports(self, text, where):
        self.assertRegex(text, r'(?m)^\s*joystick_port_1\s*=\s*none\s*$', where + ': joystick_port_1 = none missing')
        self.assertIsNone(KEYBOARD_PORT.search(text), where + ': a joystick port uses the keyboard')

    def test_current_version_template(self):
        path = ROOT / 'resources/emulators' / ('AmiWind-v%s-FS-UAE.fs-uae' % version())
        self.assert_ports(path.read_text(encoding='utf-8'), path.name)

    def test_helper_launcher_profile_and_preset(self):
        module = launcher()
        self.assertEqual(module.PROFILE_VALUES.get('joystick_port_1'), 'none')
        self.assert_ports(module.PRESET, 'AmiWind-FS-UAE-launcher.py PRESET')

    def test_home_and_end_reach_the_game(self):
        """FS-UAE sends PC Home/End as keypad ( and Help; the presets send them as the unused
        keys 0x6a/0x6c, which the engine reads as Home/End (KEYS-AMIGA-EDIT-32)."""
        path = ROOT / 'resources/emulators' / ('AmiWind-v%s-FS-UAE.fs-uae' % version())
        text = path.read_text(encoding='utf-8')
        self.assertRegex(text, r'(?m)^keyboard_key_home = action_key_6a$')
        self.assertRegex(text, r'(?m)^keyboard_key_end = action_key_6c$')
        module = launcher()
        self.assertEqual(module.PROFILE_VALUES.get('keyboard_key_home'), 'action_key_6a')
        self.assertEqual(module.PROFILE_VALUES.get('keyboard_key_end'), 'action_key_6c')
        keys = (ROOT / 'engine/aga/src/keys.c').read_text(encoding='utf-8')
        self.assertIn('if(raw==0x6a)return K_HOME;', keys)
        self.assertIn('if(raw==0x6c)return K_END;', keys)

    def test_slow_accelerator_preset(self):
        """The slow accelerator preset keeps the game's keys and the normal preset's machine;
        only the CPU speed lines differ: interpreted 68040 with FPU, cycle-exact, clock set by
        uae_cpu_multiplier (uae_cpu_frequency is ignored in cycle-exact mode)."""
        text = SLOW_PRESET.read_text(encoding='utf-8')
        self.assert_ports(text, SLOW_PRESET.name)
        self.assertRegex(text, r'(?m)^keyboard_key_home = action_key_6a$')
        self.assertRegex(text, r'(?m)^keyboard_key_end = action_key_6c$')
        slow = settings(SLOW_PRESET)
        self.assertEqual((slow['cpu'], slow['fpu']), ('68040-NOMMU', '68040'))
        self.assertEqual(slow['jit_compiler'], '0')
        self.assertEqual(slow['uae_cpu_cycle_exact'], 'true')
        self.assertGreaterEqual(int(slow['uae_cpu_multiplier']), 1)
        self.assertNotIn('uae_cpu_frequency', slow)
        self.assertNotIn('uae_cpu_speed', slow)
        normal = settings(ROOT / 'resources/emulators' / ('AmiWind-v%s-FS-UAE.fs-uae' % version()))
        def machine(values):
            return {k: v for k, v in values.items() if k not in SPEED_KEYS and not k.startswith('hard_drive_')}
        self.assertEqual(machine(slow), machine(normal))
        self.assertEqual(slow['hard_drive_0_type'], 'hdf')

    def test_playtesting_doc_example(self):
        self.assert_ports((ROOT / 'docs/FS-UAE-PLAYTESTING.md').read_text(encoding='utf-8'), 'FS-UAE-PLAYTESTING.md')


if __name__ == '__main__':
    unittest.main()
