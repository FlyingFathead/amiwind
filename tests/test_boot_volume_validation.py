"""BOOT-VOLUME-NOT-VALIDATED-33: the engine waits for AmigaOS to finish validating the boot volume
before its first write, and the optional DEBUG.TXT log can never stop the game."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'engine/aga/src/sys_amiga.c'


def section(text, start, end):
    return text[text.index(start):text.index(end)]


class SourceOrderTests(unittest.TestCase):
    def setUp(self):
        self.text = SOURCE.read_text(encoding='utf-8')

    def test_wait_runs_before_the_first_write(self):
        main = section(self.text, 'int main(int argc', 'RunGameLoop();')
        self.assertIn('AW_WaitBootVolumeValidated();', main)
        self.assertLess(main.index('AW_WaitBootVolumeValidated();'), main.index('Sys_Init('))
        self.assertLess(main.index('AW_WaitBootVolumeValidated();'), main.index('Host_Init('))

    def test_wait_checks_the_disk_state_and_keeps_the_old_start_selectable(self):
        wait = section(self.text, '/* aw_validate_wait begin */', '/* aw_validate_wait end */')
        self.assertIn('ID_VALIDATING', wait)
        self.assertIn('"PROGDIR:"', wait)
        self.assertIn('GVF_LOCAL_ONLY', wait)  # never asks for ENV:, which the boot disk lacks
        self.assertIn('"AmiWindValidateWait"', wait)
        self.assertRegex(wait, r'#define AW_VALIDATE_WAIT_LIMIT 900\b')
        # The wait itself must not write to the volume it waits for.
        for call in ('fopen', 'Open(', 'Write(', 'CreateDir'):
            self.assertNotIn(call, wait)

    def test_debug_log_failure_does_not_stop_the_game(self):
        printf = section(self.text, 'void Sys_Printf (char *message', '#endif')
        self.assertNotIn('Sys_FileOpenWrite', printf)  # it called Sys_Error on failure
        self.assertNotIn('Sys_Error', printf)
        self.assertIn('AW_LogWrite(AW_LOG_DEBUG, text);', printf)
        # aw_log.c: a live file that cannot be created is skipped and not retried per line
        # (tests/aga_log_test.c runs it).
        log = (ROOT / 'engine/aga/src/aw_log.c').read_text(encoding='utf-8')
        opener = section(log, 'static FILE *awlog_open_live(', 'static void awlog_live_stream(')
        self.assertIn('if (l->failed) return NULL;', opener)
        self.assertIn('if (!f) l->failed = 1;', opener)

@unittest.skipIf(os.name == 'nt', 'Native helper fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'A host C compiler is required')
class WaitBehaviourTests(unittest.TestCase):
    def run_harness(self, *defines):
        text = SOURCE.read_text(encoding='utf-8')
        wait = section(text, '/* aw_validate_wait begin */', '/* aw_validate_wait end */')
        with tempfile.TemporaryDirectory(prefix='amiwind-validate-wait-') as temp:
            (Path(temp) / 'actual_validate_wait.inc').write_text(wait, encoding='utf-8')
            executable = Path(temp) / 'check'
            result = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-fsanitize=undefined',
                                     '-fno-sanitize-recover=all', '-I' + temp, *defines,
                                     str(ROOT / 'tests/aga_validate_wait_test.c'), '-o', str(executable)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([str(executable)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('validate wait ok', result.stdout)

    def test_waits_reports_gives_up_and_opt_out(self):
        self.run_harness('-DAW_VALIDATE_WAIT_LIMIT=7')

    def test_default_limit(self):
        self.run_harness()


if __name__ == '__main__':
    unittest.main()
