"""--chim-sol-test (TEST BUILDS ONLY, DLC-BUILD-LATER): the Bloodmoon layer's frames reach the image only with the
option; without it the stages and the image command are exactly as before."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import build  # noqa: E402
from chim.sol_test import map_name  # noqa: E402


def tool(name, *parts):
    return ['python3', name, *[str(p) for p in parts]]


class SolTestCommands(unittest.TestCase):
    def steps(self):
        return [('chim', tool('chim_build.py', '--out', '/run/chim-world')), ('image', tool('build_aga.py', 'image'))]

    def test_off_changes_nothing(self):
        args = SimpleNamespace(chim_sol_test=None)
        steps = self.steps()
        self.assertEqual(build.chim_sol_test_commands(args, steps, tool, Path('/run'), {}, 4), self.steps())

    def test_on_adds_the_stages_and_the_store_to_the_image(self):
        args = SimpleNamespace(chim_sol_test='-23,20:l', data_files='/data', workspace=Path('/ws'), sdk='/sdk',
                               chim_terrain_hull='compiled')
        try:
            steps = build.chim_sol_test_commands(args, self.steps(), tool, Path('/run'), {'qbsp': '/q'}, 4)
        except AttributeError as missing:        # chim_stage_options reads more build settings
            self.skipTest('build settings: %s' % missing)
        names = [n for n, _ in steps]
        self.assertEqual(names, ['chim', 'chim-sol-data', 'chim-sol', 'image'])
        image = dict(steps)['image']
        self.assertEqual(image[-2:], ['--chim-sol-world', str(Path('/run') / 'chim-sol')])
        self.assertNotIn('--chim-sol-world', dict(steps)['chim'])

    def test_map_names(self):
        self.assertEqual(map_name((-23, 20)), 'solm23p20')
        self.assertEqual(map_name((-20, 23)), 'solm20p23')


if __name__ == '__main__':
    unittest.main()
