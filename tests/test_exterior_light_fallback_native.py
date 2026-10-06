"""Regression for empty versus unused exterior lighting lumps; real C renderer."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get('AMIWIND_RUNTIME_SOURCE', str(ROOT / 'engine/aga'))) / 'src'


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class ExteriorLightFallbackTests(unittest.TestCase):
    def test_empty_and_unused_lumps_match_pixels_and_actor_light(self):
        with tempfile.TemporaryDirectory() as scratch:
            executable = Path(scratch) / 'exterior-light-check'
            command = ['cc', '-std=gnu89', '-fsanitize=undefined,float-cast-overflow',
                       '-fno-sanitize-recover=all', '-ffunction-sections', '-fdata-sections',
                       '-Wl,--gc-sections', '-I'+str(SOURCE),
                       str(ROOT/'tests/aga_exterior_light_fallback_test.c'),
                       *[str(SOURCE/name) for name in ('r_surf.c', 'r_light.c', 'd_surf.c')],
                       '-lm', '-o', str(executable)]
            compiled = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stdout+compiled.stderr)
            result = subprocess.run([str(executable)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
