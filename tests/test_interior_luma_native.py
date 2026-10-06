"""Gameplay-interior light control using actual scene, renderer and config code."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import json

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get('AMIWIND_RUNTIME_SOURCE', str(ROOT / 'engine/aga'))) / 'src'


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class InteriorLumaTests(unittest.TestCase):
    def test_static_renderer_controls_and_archived_override(self):
        with tempfile.TemporaryDirectory() as scratch:
            from project_version import generate_native
            generate_native(ROOT/'VERSION', Path(scratch))
            executable = Path(scratch) / 'interior-luma-check'
            command = ['cc', '-std=gnu89', '-DAMIWIND_DEBUG_LUMA=1', '-Wl,--wrap=D_FlushCaches', '-fsanitize=undefined,float-cast-overflow',
                       '-fno-sanitize-recover=all', '-ffunction-sections', '-fdata-sections',
                       '-Wl,--gc-sections', '-I'+scratch, '-I'+str(SOURCE),
                       str(ROOT/'tests/aga_interior_luma_test.c'),
                       *[str(SOURCE/name) for name in ('r_surf.c', 'r_light.c', 'd_surf.c', 'cvar.c', 'common.c', 'aw_scene.c')],
                       '-lm', '-o', str(executable)]
            compiled = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stdout+compiled.stderr)
            scenes = {}
            for name in ('seyda_area.json', 'balmora_interiors.json'):
                scenes.update({row['map']: row for row in json.loads((ROOT/'config'/name).read_text())['scenes']})
            interiors = sorted(name for name, row in scenes.items() if row['interior'])
            self.assertTrue({'prison', 'addamasartus', 'tharystomb', 'bmtemple'} <= set(interiors))
            self.assertEqual(len(interiors), 58)
            result = subprocess.run([str(executable), *interiors, 'mi5b8154939f7aa', 'mi5b8154939f7ab'],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)

    def test_shipped_default_is_one_multiplicative_setting(self):
        commands = [line.split() for line in (ROOT/'config/game.cfg').read_text().splitlines()
                    if line.strip() and not line.lstrip().startswith('//')]
        self.assertEqual([row for row in commands if row[0] == 'aw_interiorluma'], [['aw_interiorluma', '1.2']])

    def test_disabled_objects_keep_only_explanatory_commands(self):
        with tempfile.TemporaryDirectory() as scratch:
            from project_version import generate_native
            generate_native(ROOT/'VERSION', Path(scratch))
            for debug in (False, True):
                symbols = ''
                for name in ('r_light.c', 'r_surf.c', 'r_main.c', 'r_misc.c'):
                    obj = Path(scratch)/f'{name}.{int(debug)}.o'
                    command = ['cc', '-std=gnu89', '-O1', '-I'+scratch, '-I'+str(SOURCE),
                               *(['-DAMIWIND_DEBUG_LUMA=1'] if debug else []),
                               '-c', str(SOURCE/name), '-o', str(obj)]
                    compiled = subprocess.run(command, capture_output=True, text=True)
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    symbols += subprocess.check_output(['nm', '-a', str(obj)], text=True)
                if debug:
                    self.assertIn('R_InteriorLumaUpdate', symbols)
                    self.assertIn('interior_luma_factor', symbols)
                else:
                    self.assertIn('R_InteriorLumaInit', symbols)
                    self.assertNotIn('R_InteriorLumaUpdate', symbols)
                    self.assertNotIn('luma_settings', symbols)
                    self.assertNotIn('R_Brightness', symbols)
                    self.assertNotIn('InteriorStaticLight', symbols)
                    self.assertNotIn('interior_luma', symbols)
