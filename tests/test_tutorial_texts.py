# SPDX-License-Identifier: GPL-3.0-only
"""The tutorial texts' keys (OPENING-TUTORIAL-KEYS-65): the table natively (every row resolves to a bound key, a rebound
key changes the text, a once row shows once), the table's rendering, the engine's wiring, and the key-hint check: no
new player-facing text in the engine names a fixed key letter (tests/key-hint-allowlist.json lists the ones left)."""
import json
import os
import re
import shutil
import sys
import unittest
from pathlib import Path

import test_aga_native_source as native

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'
UBSAN = ['-fsanitize=undefined', '-fno-sanitize-recover=all']
sys.path.insert(0, str(ROOT / 'tools'))
ALLOWLIST = ROOT / 'tests' / 'key-hint-allowlist.json'
# a string literal of the engine that names a fixed letter key: "Press E", "M: map", "(Q)", "P/Esc"
HINT = re.compile(r'\b[Pp]ress(?:ing)?\s+(?:the\s+)?[A-Z]\b|(?<![A-Za-z0-9])[A-Z]: ?[A-Za-z]|\((?:[A-Z])\)|'
                  r'(?<![A-Za-z])[A-Z]/(?:Esc|Enter)\b|\b[A-Z] to (?:open|close|take|use|read|talk|equip|drop)\b')


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8', errors='replace'), flags=re.S)


def key_hints():
    """{file: sorted list of the string literals holding a fixed letter key}"""
    found = {}
    for path in sorted(SRC.glob('*.c')):
        text = code(path.name)
        text = re.sub(r'//[^\n]*', '', text)
        for literal in re.findall(r'"((?:[^"\\\n]|\\.)*)"', text):
            if HINT.search(literal):
                found.setdefault(path.name, []).append(literal)
    return {k: sorted(set(v)) for k, v in found.items()}


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class TutorialNativeTests(unittest.TestCase):
    def test_every_row_names_the_bound_key(self):
        native.NativeSourceTests().compile_run('aga_tutorial_test.c', [SRC / 'aw_tutorial_rules.c'], cflags=UBSAN)


class TutorialTableTests(unittest.TestCase):
    def test_the_table_is_the_json_rendered(self):
        import tutorial_texts
        rows = tutorial_texts.load()
        self.assertEqual((SRC / 'aw_tutorial_table.inc').read_text(encoding='utf-8'), tutorial_texts.render(rows))
        self.assertGreaterEqual(len(rows), 16)
        self.assertEqual(tutorial_texts.text_hash('You now  have a MAP.'), tutorial_texts.text_hash('you now have a map.'))

    def test_no_box_shows_the_same_text_as_another(self):
        # TUTORIAL-BOX-SHOWN-TWICE-65 (v0.0.65-rc4 test on the Pi): the original's second box after the stats and the
        # inventory boxes ("right click to use your new menu") had our first box's text, so the same box came twice;
        # those rows hide their box, and the table refuses two shown rows with one text
        import tutorial_texts
        rows = tutorial_texts.load()
        kinds = {r['hash']: r['kind'] for r in rows}
        self.assertEqual(kinds['0x63f76653'], 'hide')
        self.assertEqual(kinds['0x0640f16d'], 'hide')
        shown = [r['text'] for r in rows if r['kind'] in ('replace', 'once') and not r.get('alternative_of')]
        self.assertEqual(len(shown), len(set(shown)))
        twice = [dict(r) for r in rows[:2]]
        twice[1]['hash'], twice[1]['kind'] = '0x00000001', 'replace'
        twice[1]['text'] = twice[0]['text']
        with self.assertRaises(ValueError):
            tutorial_texts.check_rows(twice)

    def test_every_box_goes_through_the_table_and_the_bound_keys(self):
        box = code('aw_msgbox.c')
        self.assertIn('if(aw_msgbox_tutorial && (row=aw_msgbox_tutorial(raw,keyed,sizeof(keyed)))<0)', box)
        self.assertIn('if(aw_msgbox_tutorial && row>0)raw=keyed;', box)
        textdef = code('aw_textdef.c')
        self.assertIn('return AW_TutorialApply(text, AW_TextBoundKeyForCommand, out, capacity);', textdef)
        self.assertIn('AW_ResetRegister("tutorial texts shown once", reset_tutorial, NULL);', textdef)
        self.assertIn('AW_TextDefineInit();', code('aw_debug.c'))
        self.assertIn('aw_tutorial_rules.c', (ROOT / 'engine' / 'aga' / 'Makefile').read_text(encoding='utf-8'))
        # the engine's own opening hints: the bound keys (the captain's box, the movement hint)
        self.assertIn('"Press ^ActionActivate to talk to the Captain.', code('aw_opening.c'))
        self.assertIn('"^ActionForward and ^ActionBack move forward and back. "', code('aw_intro.c'))
        # the key column: a tab in a line of the box pipeline
        ui = code('aw_ui.c')
        self.assertIn("if((tab=strchr(line,'\\t'))!=NULL){", ui)
        # the inventory's own keys, bindable and saved (use/equip E and Enter, drop D)
        worldui = code('aw_worldui.c')
        self.assertIn('cvar_t aw_key_inv_use={"aw_key_inv_use","E ENTER",true};', worldui)
        self.assertIn('cvar_t aw_key_inv_drop={"aw_key_inv_drop","D",true};', worldui)
        self.assertIn('if(win_key(aw_key_inv_use.string,key)){', worldui)
        self.assertIn('if(win_key(aw_key_inv_drop.string,key)){', worldui)


class KeyHintCheck(unittest.TestCase):
    """No new hard-coded key letter in a player-facing text: every hit must be in the allowlist (the rows left for
    v0.0.66, each named); a fixed hint removed must leave the allowlist too."""

    def test_no_new_fixed_key_letters(self):
        allowed = json.loads(ALLOWLIST.read_text(encoding='utf-8'))['files']
        found = key_hints()
        new = {f: [s for s in v if s not in allowed.get(f, [])] for f, v in found.items()}
        new = {f: v for f, v in new.items() if v}
        gone = {f: [s for s in v if s not in found.get(f, [])] for f, v in allowed.items()}
        gone = {f: v for f, v in gone.items() if v}
        self.assertEqual(new, {}, 'a player-facing text names a fixed key: use the bound key (aw_textdef.c '
                                  'AW_TextBoundKeyForCommand, the ^Action defines, config/tutorial-texts.json)')
        self.assertEqual(gone, {}, 'these allowlisted hints are gone: remove them from tests/key-hint-allowlist.json')


if __name__ == '__main__':
    if sys.argv[1:] == ['--allowlist']:
        hints = key_hints()
        print(json.dumps({'format': 'AmiWind key hint allowlist 1', 'count': sum(len(v) for v in hints.values()),
                          'files': hints}, indent=1))
    else:
        unittest.main()
