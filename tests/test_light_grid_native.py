"""Actor light grid and warm lightstyle in the real r_light.c (NPC-LIGHT-COHERENCE-32,
OPENING-JIUB-LANTERN-32)."""
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
class LightGridNativeTests(unittest.TestCase):
    def test_grid_parse_sample_fallbacks_and_warm_style(self):
        with tempfile.TemporaryDirectory() as scratch:
            executable = Path(scratch) / 'light-grid-check'
            command = ['cc', '-std=gnu89', '-fsanitize=address,undefined,float-cast-overflow',
                       '-fno-sanitize=alignment', '-fno-sanitize-recover=all', '-ffunction-sections', '-fdata-sections',
                       '-Wl,--gc-sections', '-I'+str(SOURCE),
                       str(ROOT/'tests/aga_light_grid_test.c'),
                       *[str(SOURCE/name) for name in ('r_light.c', 'mathlib.c', 'aw_format.c')],
                       '-lm', '-o', str(executable)]
            compiled = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stdout+compiled.stderr)
            result = subprocess.run([str(executable)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            self.assertIn('light grid: trilinear', result.stdout)


if __name__ == '__main__':
    unittest.main()
