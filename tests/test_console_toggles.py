# SPDX-License-Identifier: GPL-3.0-only
"""DBG-SUPERSPEED-62: every on/off debug command of the catalogue turns the other way when typed with no argument.
A plain switch entry (its help starts with on/off, true/false, 1/0 or 0/1 only, no other choice after them) must be
a route onto a setting (the translator gives it the other value), a command whose state the translator reads from a
setting (aw_console.c toggle_state), a handler that turns itself, or a named exception with its reason."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'
CATALOGUE = ROOT / 'config' / 'debug-commands.txt'
SWITCH = {'on/off', 'true/false', '1/0', '0/1', 'or'}

# handlers that turn their switch themselves when typed bare, with the source line that does it
SELF_TOGGLING = {
    'aw_godmode': ('aw_debug.c', None), 'aw_photomode': ('aw_photo.c', None), 'aw_crosshair': ('aw_crosshair.c', None),
    'aw_inventory': ('aw_inventory.c', 'if(!w)on=!AW_MoveNoBurdenOn();'),
    'superspeed': ('aw_move.c', 'Cmd_Argc()==2?on:!AW_MoveSuperspeed()'),
    'amiwind_show_debug': ('aw_hud.c', 'Cvar_SetValue(setting->name,setting->value==0);'),
    'amiwind_debug_compass': ('aw_hud.c', 'Cvar_SetValue(setting->name,setting->value==0);'),
    'amiwind_debug_coords': ('aw_hud.c', 'Cvar_SetValue(setting->name,setting->value==0);'),
    'amiwind_debug_fps': ('aw_hud.c', 'Cvar_SetValue(setting->name,setting->value==0);'),
    'amiwind_debug_sealevel': ('aw_hud.c', 'Cvar_SetValue(setting->name,setting->value==0);'),
    'amiwind_debug_showfps': ('aw_hud.c', 'static void debug_showfps(void) {debug_fps();}'),
    'amiwind_debug_showram': ('aw_hud.c', 'Cvar_SetValue(setting->name,setting->value==0);'),
    'aw_debug_hud': ('aw_inspect.c', 'if(Cmd_Argc()==1)s=enabled?"off":"on";'),
    'aw_daynight_set': ('aw_wait.c', 'if(Cmd_Argc()==1)on=daynight_hold?1:0;'),
    'aw_hinged_door': ('aw_hinged_door.c', 'else door_locks=!door_locks;'),
    'chim': ('aw_actors.c', 'creatures_on = !creatures_on;'),
    'aw_magicfx': ('aw_cast.c', 'else cast_on=!cast_on;'),
    'aw_cull': ('aw_console.c', 'if(argc==j)on=!(value&bit);'),
}
# plain switches whose bare form stays something else, by an earlier decision
EXCEPTIONS = {
    'mwscript': 'the bare form is the scripts\' about page (DBG-MWSCRIPT-SILENT-56); on/off still switch',
    'companiontest': 'not a switch of a state but a test NPC spawned and removed; bare prints the report',
}


def pure(args):
    a = args[1:] if args.startswith('[') else args
    words = 0
    for token in re.split(r'[ ,]+', re.split(r'[;\]]', a, 1)[0].strip()):
        if token in SWITCH:
            words += 1
            continue
        if token.startswith('/'):
            return False
        break
    return words > 0


def entries():
    for line in CATALOGUE.read_text(encoding='utf-8').splitlines()[1:]:
        if line and not line.startswith('#'):
            group, words, handler, args = line.split('|', 3)
            yield words, handler, args


class EveryToggleTurnsBare(unittest.TestCase):
    def test_every_plain_switch_turns_the_other_way(self):
        text = ''.join(p.read_text(encoding='latin-1') for p in SRC.rglob('*.c'))
        cvars = set()
        for decl in re.findall(r'cvar_t\s+([^;]+);', text):    # every declarator, "a={...},b={...}" too
            cvars.update(re.findall(r'\w+\s*=\s*\{\s*"([^"]+)"', decl))
        console = (SRC / 'aw_console.c').read_text(encoding='utf-8')
        table = dict(re.findall(r'\{"([a-z ]+)","(aw_[a-z_]+)"\}', console[console.index('toggle_state[][2]'):
                                                                         console.index('int AW_DebugPureToggle')]))
        missing, checked = [], 0
        for words, handler, args in entries():
            if not pure(args):
                continue
            checked += 1
            if handler in cvars or words in EXCEPTIONS:
                continue
            if words in table:
                self.assertIn(table[words], cvars, words)
                continue
            if handler in SELF_TOGGLING:
                name, line = SELF_TOGGLING[handler]
                if line:
                    self.assertIn(line, (SRC / name).read_text(encoding='latin-1'), handler)
                continue
            missing.append('dbg %s (%s)' % (words, handler))
        self.assertEqual(missing, [], 'plain on/off commands that do not turn the other way when typed bare')
        self.assertGreater(checked, 50)

    def test_help_says_toggles_not_status(self):
        for words, handler, args in entries():
            if pure(args) and words not in EXCEPTIONS:
                self.assertNotRegex(args, r'no argument[ =:]+(status|shows|prints|state)', words)

    def test_the_rule_matches_the_engine(self):
        self.assertTrue(pure('[on/off, true/false or 1/0; no argument toggles] x'))
        self.assertTrue(pure('1/0 places in id1'))
        self.assertFalse(pure('[on/off / list / groups]'))
        self.assertFalse(pure('[on/off/auto] all'))
        self.assertFalse(pure('[0/1/2/3/4] once'))


if __name__ == '__main__':
    unittest.main()
