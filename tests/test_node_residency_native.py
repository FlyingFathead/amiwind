"""Exercise actual loader functions with synthetic collision/render trees."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPILER = os.environ.get('CC') or shutil.which('cc') or shutil.which('gcc')


@unittest.skipIf(os.name == 'nt', 'Owner workflow: no generated Windows test executables; run this native oracle on Linux')
@unittest.skipUnless(COMPILER, 'install a host C compiler or set CC')
class NodeResidencyTests(unittest.TestCase):
    def test_render_prefix_hull_identity_fallback_and_malformed_bounds(self):
        with tempfile.TemporaryDirectory(prefix='amiwind-node-residency-') as temp:
            exe = Path(temp)/('nodes.exe' if os.name == 'nt' else 'nodes')
            command = [COMPILER, '-std=gnu89', '-O2', '-fwhole-program',
                       '-ffunction-sections', '-fdata-sections', '-Wl,--gc-sections',
                       '-I'+str(ROOT/'engine/aga/src'),
                       str(ROOT/'tests/aga_node_residency_test.c'), '-o', str(exe)]
            result = subprocess.run([s.replace('\\', '/') for s in command], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            result = subprocess.run([str(exe)], cwd=temp, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)


if __name__ == '__main__':
    unittest.main()
