"""Exercise the real alias transform, clipper and depth projection with synthetic data."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('cc'), 'C compiler required')
class FistNearClipTests(unittest.TestCase):
    def test_near_geometry_and_legacy_depth(self):
        source = ROOT / 'engine/aga/src'
        with tempfile.TemporaryDirectory() as work:
            exe = Path(work) / 'fist-near'
            args = ['cc', '-std=gnu89', '-fsanitize=undefined,float-cast-overflow',
                    '-fno-sanitize=alignment', '-fno-sanitize-recover=all',
                    '-ffunction-sections', '-fdata-sections', '-Wl,--gc-sections',
                    '-I' + str(source), str(ROOT / 'tests/aga_fist_near_clip_test.c'),
                    *(str(source / name) for name in ('r_alias.c', 'r_aclip.c', 'mathlib.c')),
                    '-lm', '-o', str(exe)]
            subprocess.run(args, check=True, capture_output=True, text=True)
            result = subprocess.run([str(exe)], check=True, capture_output=True, text=True)
            self.assertIn('exclusions passed', result.stdout)


if __name__ == '__main__':
    unittest.main()
