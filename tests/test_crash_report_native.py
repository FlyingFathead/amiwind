"""Exercise the actual Amiga fatal handler with synthetic DOS operations."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipIf(os.name == 'nt', 'Native helper fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'A host C compiler is required')
class CrashReportTests(unittest.TestCase):
    def test_fatal_report_visibility_and_verified_log_failures(self):
        from project_version import generate_native
        source = (ROOT/'engine/aga/src/sys_amiga.c').read_text()
        fatal = source[source.index('void Sys_Error ('):source.index('void Sys_SendKeyEvents(')]
        with tempfile.TemporaryDirectory(prefix='amiwind-fatal-report-') as temp:
            directory = Path(temp)
            generate_native(ROOT/'VERSION', directory)
            (directory/'actual_sys_error.inc').write_text(fatal)
            executable = directory/'check'
            result = subprocess.run(['cc', '-std=gnu89', '-fsanitize=undefined',
                '-fno-sanitize-recover=all', '-I'+temp,
                str(ROOT/'tests/aga_crash_report_test.c'), '-o', str(executable)],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            result = subprocess.run([str(executable)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)


if __name__ == '__main__':
    unittest.main()
