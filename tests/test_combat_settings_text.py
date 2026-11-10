"""RESIST-NORMAL-WEAPONS-61: combat/settings.txt carries the game setting sMagicTargetResistsWeapons as a text line
(tools/prepare_combat.py gmst_text). The first MiniWind with it stopped in the image step: a local variable named
`text` in the stage shadowed the module's text() helper (TypeError: 'str' object is not callable)."""
import ast
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import prepare_combat as pc  # noqa: E402


class CombatSettingsText(unittest.TestCase):
    def test_gmst_text(self):
        kinds = {'GMST': {'smagictargetresistsweapons': [('NAME', b'sMagicTargetResistsWeapons\0'),
                                                          ('STRV', b'Your weapon has no effect.')],
                          'sbad': [('STRV', b'caf\xe9')], 'slong': [('STRV', b'x' * 91)]}}
        self.assertEqual(pc.gmst_text(kinds, 'sMagicTargetResistsWeapons'), 'Your weapon has no effect.')
        self.assertEqual(pc.gmst_text(kinds, 'sBad'), '')          # not plain ASCII: the console line only
        self.assertEqual(pc.gmst_text(kinds, 'sLong'), '')         # past the engine's line
        self.assertEqual(pc.gmst_text(kinds, 'sMissing'), '')
        self.assertIn('sMagicTargetResistsWeapons', pc.TEXT_SETTINGS)
        self.assertEqual(struct.calcsize('<i'), 4)

    def test_expelled_message(self):
        """FACTION-EXPEL-MESSAGE-64: the expulsion shows sExpelledMessage + the faction (OpenMW NpcStats::expell);
        the image carries the setting and the engine reads its line and shows it beside the console line."""
        self.assertIn('sExpelledMessage', pc.TEXT_SETTINGS)
        self.assertLessEqual(len('text sExpelledMessage ') + 90, 127)
        c = (ROOT / 'engine/aga/src/aw_crime.c').read_text(encoding='utf-8')
        self.assertIn('"text sExpelledMessage ",22', c)
        expel = c.index('AW_StandingSetExpelled(f,1)')
        self.assertIn('AW_MsgBoxShow(text,NULL,0)', c[expel:expel + 800])

    def test_no_function_shadows_the_text_helper(self):
        tree = ast.parse((ROOT / 'tools/prepare_combat.py').read_text(encoding='utf-8'))
        for fn in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
            if fn.name == 'text':
                continue
            names = {t.id for n in ast.walk(fn) if isinstance(n, (ast.Assign, ast.For))
                     for t in ast.walk(n.targets[0] if isinstance(n, ast.Assign) else n.target)
                     if isinstance(t, ast.Name)}
            calls = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'text'
                        for n in ast.walk(fn))
            # a function that calls the text() helper must not also make a local of that name
            self.assertFalse(calls and 'text' in names, 'prepare_combat.%s shadows text()' % fn.name)


if __name__ == '__main__':
    unittest.main()
