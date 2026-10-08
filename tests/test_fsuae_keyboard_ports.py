# SPDX-License-Identifier: GPL-3.0-only
"""Every FS-UAE configuration AmiWind ships or writes keeps the cursor keys for the game.

FS-UAE's default for joystick port 1 is "auto", which falls back to keyboard joystick emulation
(cursor keys + Right Ctrl) when no gamepad is connected; the game would then never see the arrows
(console history, menus, movement). CONSOLE-HISTORY-ARROWS-32.
"""
import importlib.util
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

KEYBOARD_PORT = re.compile(r'^\s*joystick_port_[0-3]\s*=\s*keyboard', re.M | re.I)


def version():
    return (ROOT / 'VERSION').read_text(encoding='utf-8').strip()


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

    def test_playtesting_doc_example(self):
        self.assert_ports((ROOT / 'docs/FS-UAE-PLAYTESTING.md').read_text(encoding='utf-8'), 'FS-UAE-PLAYTESTING.md')


if __name__ == '__main__':
    unittest.main()
