"""Horizon draw method defaults (HORIZON-FLORA-SPRITES-32).

The land-outline horizon is the shipped default (aw_skyline_fill 0 in the game
config the builder installs, and a one-time migration for saved configs). The
object silhouetting method (aw_skyline_fill 1) is tested but subpar results and
is kept for future improvement: it must stay registered and selectable. Its
rendering is checked natively in tests/aga_horizon_test.c.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def commands(path):
    return [line.split() for line in path.read_text(encoding='utf-8').splitlines()
            if line.strip() and not line.lstrip().startswith('//')]


class HorizonMethodTests(unittest.TestCase):
    def test_game_config_selects_the_land_outline_horizon(self):
        values = [c[1] for c in commands(ROOT / 'config/game.cfg') if c[0] == 'aw_skyline_fill']
        self.assertEqual(values, ['0'])

    def test_saved_configs_migrate_once_after_config_cfg(self):
        source = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        rc = re.search(r"\(boot/'id1/quake\.rc'\)\.write_text\('([^']*)'", source).group(1).split('\\n')
        self.assertLess(rc.index('exec config.cfg'), rc.index('aw_horizon_migrate'))
        self.assertLess(rc.index('exec default-game.cfg'), rc.index('exec config.cfg'))
        fog = (ROOT / 'engine/aga/src/aw_fog.c').read_text(encoding='utf-8')
        self.assertIn('Cmd_AddCommand("aw_horizon_migrate",horizon_migrate)', fog)
        self.assertIn('static cvar_t aw_horizon_defaults={"aw_horizon_defaults","0",true};', fog)

    def test_object_silhouetting_is_kept_selectable_and_documented(self):
        fog = (ROOT / 'engine/aga/src/aw_fog.c').read_text(encoding='utf-8')
        self.assertIn('Cvar_RegisterVariable(&aw_skyline_fill)', fog)
        self.assertIn('if(fill && skyline[x])pixels[x]=ramp[(15<<8)+pixels[x]];', fog)
        catalogue = (ROOT / 'config/debug-commands.txt').read_text(encoding='utf-8')
        rows = [line for line in catalogue.splitlines() if '|aw_skyline_fill|' in line]
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertIn('tested but subpar results', row)
            self.assertIn('experimental and buggy', row)
        config = (ROOT / 'config/game.cfg').read_text(encoding='utf-8').lower()
        self.assertIn('tested but subpar results', config)
        self.assertIn('experimental and buggy', config)


if __name__ == '__main__':
    unittest.main()
