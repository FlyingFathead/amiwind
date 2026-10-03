"""Run real allocator regressions; no game assets or Amiga SDK are required."""
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
class HeapWatcherNativeTests(unittest.TestCase):
    def test_hunk_lifecycle_cache_eviction_and_zone_fragmentation(self):
        with tempfile.TemporaryDirectory(prefix='amiwind-heap-watcher-') as temp:
            executable = Path(temp) / ('heap-check.exe' if os.name == 'nt' else 'heap-check')
            command = [COMPILER, '-std=gnu89', '-O2', '-fwhole-program',
                       '-ffunction-sections', '-fdata-sections', '-Wl,--gc-sections',
                       '-I' + str(ROOT / 'engine/aga/src'),
                       str(ROOT / 'tests/aga_heap_watcher_test.c'), '-o', str(executable)]
            # MSYS GCC invoked from native Windows Python requires forward slashes.
            command = [part.replace('\\', '/') for part in command]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([str(executable)], cwd=temp, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
