"""Compare real loader/render inputs after exact metadata sharing."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from share_bsp_geometry import share_geometry
from test_share_bsp_geometry import repeated_geometry
COMPILER = os.environ.get('CC') or shutil.which('cc') or shutil.which('gcc')


@unittest.skipIf(os.name == 'nt', 'Owner workflow: no generated Windows test executables; run this native oracle on Linux')
@unittest.skipUnless(COMPILER, 'install a host C compiler or set CC')
class GeometryShareNativeTests(unittest.TestCase):
    def test_world_and_inline_face_winding_uv_and_light_samples_identical(self):
        with tempfile.TemporaryDirectory(prefix='amiwind-geometry-share-') as temp:
            temp = Path(temp);exe = temp/('geometry.exe' if os.name == 'nt' else 'geometry')
            command = [COMPILER, '-std=gnu89', '-O2', '-fwhole-program',
                       '-ffunction-sections', '-fdata-sections', '-Wl,--gc-sections',
                       '-I'+str(ROOT/'engine/aga/src'),
                       str(ROOT/'tests/aga_geometry_share_test.c'), '-lm', '-o', str(exe)]
            result = subprocess.run([s.replace('\\', '/') for s in command], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            before = repeated_geometry();after, _ = share_geometry(before)
            a, b = temp/'before.bsp', temp/'after.bsp';a.write_bytes(before);b.write_bytes(after)
            result = subprocess.run([str(exe), str(a), str(b)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            hashes = [line.split()[:2] for line in result.stdout.splitlines()]
            self.assertEqual(len(hashes), 2)
            self.assertEqual(hashes[0], hashes[1])


if __name__ == '__main__':
    unittest.main()
