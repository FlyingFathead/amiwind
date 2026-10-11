# SPDX-License-Identifier: GPL-3.0-only
"""CONSOLE-COMMAND-SHADOWED-BY-CVAR-36: Quake's Cmd_AddCommand refuses a command whose name is already a
cvar ("already defined as a var"), and Cmd_ExecuteString runs the cvar instead. So no engine command may share
its name with a cvar (the dbg combat and dbg animkit handlers did, so their options never ran)."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'


def names():
    cvars, commands = set(), set()
    for path in SRC.glob('*.c'):
        text = path.read_text(encoding='latin-1')
        for decl in re.findall(r'cvar_t\s[^;]*;', text):
            cvars.update(re.findall(r'\{\s*"([^"]+)"', decl))
        commands.update(re.findall(r'Cmd_AddCommand\s*\(\s*"([^"]+)"', text))
    return cvars, commands


class ConsoleCommandNames(unittest.TestCase):
    def test_no_command_shares_its_name_with_a_cvar(self):
        cvars, commands = names()
        self.assertTrue(cvars and commands)
        self.assertEqual(sorted(cvars & commands), [])


if __name__ == '__main__':
    unittest.main()
