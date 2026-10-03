"""Validate actual direct clipnode loader without proprietary assets."""
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
class DirectClipLoadTests(unittest.TestCase):
    def test_in_place_endian_prefetch_pack_offset_and_invalid_data(self):
        with tempfile.TemporaryDirectory(prefix='amiwind-direct-clip-') as temp:
            exe = Path(temp)/('clip.exe' if os.name == 'nt' else 'clip')
            command = [COMPILER, '-std=gnu89', '-O2', '-fwhole-program',
                       '-ffunction-sections', '-fdata-sections', '-Wl,--gc-sections',
                       '-I'+str(ROOT/'engine/aga/src'),
                       str(ROOT/'tests/aga_direct_clip_load_test.c'), '-o', str(exe)]
            result = subprocess.run([s.replace('\\', '/') for s in command], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            result = subprocess.run([str(exe)], cwd=temp, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)


if __name__ == '__main__':
    unittest.main()
