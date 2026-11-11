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

    def test_switch_builds_both_tree_methods_and_hands_the_image_the_alternative(self):
        args = SimpleNamespace(chim_sol_test='-23,20:l', data_files='/data', workspace=Path('/ws'), sdk='/sdk',
                               chim_terrain_hull='compiled', chim_sol_tree_copies='switch')
        try:
            steps = build.chim_sol_test_commands(args, self.steps(), tool, Path('/run'), {'qbsp': '/q'}, 4)
        except AttributeError as missing:
            self.skipTest('build settings: %s' % missing)
        commands = dict(steps)
        self.assertEqual([n for n, _ in steps], ['chim', 'chim-sol-data', 'chim-sol-trees', 'chim-sol', 'chim-sol-star',
                                                 'image'])
        self.assertIn('chim_build.py', ' '.join(commands['chim-sol']))
        self.assertIn('chim_tree_star.py', ' '.join(commands['chim-sol-star']))
        self.assertEqual(commands['image'][-4:], ['--chim-sol-world', str(Path('/run') / 'chim-sol'),
                                                  '--chim-sol-alt', '1=' + str(Path('/run') / 'chim-sol-star')])

    def test_layer_data_finds_the_mwad_package_when_run_as_a_script(self):
        # BUILD-LAYER-DATA-MWAD-SHADOWED-64: run as a script, tools/ (with tools/mwad.py) is first on the path
        import subprocess
        # the stage's path: the script folder first, src and tools later (from PYTHONPATH)
        code = ("import runpy, sys; sys.path.insert(0, %r); sys.path += [%r, %r]; runpy.run_path(%r, run_name='probe'); "
                "import mwad; print(hasattr(mwad, '__path__'))"
                % (str(ROOT / 'tools'), str(ROOT / 'src'), str(ROOT / 'tools'), str(ROOT / 'tools/chim_layer_data.py')))
        out = subprocess.run([sys.executable, '-B', '-c', code], capture_output=True, text=True, cwd=str(ROOT / 'tools'),
                             env={'PATH': '/usr/bin:/bin'})
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), 'True')

    def test_map_names(self):
        # the open-world map form (aw_maps.h AW_TerrainId "slNNNN"), by the frame's index in the ownership table
        self.assertEqual(map_name(0), 'sl0000')
        self.assertEqual(map_name(12), 'sl0012')
        with self.assertRaises(ValueError):
            map_name(4096)


if __name__ == '__main__':
    unittest.main()
