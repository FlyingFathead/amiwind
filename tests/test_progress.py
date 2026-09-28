"""Progress must be visible while work runs, with complete retained logs."""
import contextlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from mwad.progress import Progress, live_log, section, setup_step
from unittest.mock import patch
import os


class ProgressTests(unittest.TestCase):
    def test_heartbeat_while_operation_is_quiet(self):
        messages = []
        seen = threading.Event()
        def notify(message):
            messages.append(message)
            if 'still running' in message:
                seen.set()
        with Progress('Quiet tool', interval=0.02, notify=notify) as progress:
            progress.bytes(1048576, 2097152)
            self.assertTrue(seen.wait(2))
        self.assertTrue(any('50%' in line for line in messages))
        self.assertIn('done in', messages[-1])

    def test_output_visible_before_process_finishes_and_log_retained(self):
        seen = threading.Event()
        class Capture(io.StringIO):
            def write(self, text):
                result = super().write(text)
                if 'ready' in text:
                    seen.set()
                return result
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'stage.log'
            captured = Capture()
            with path.open('w') as output, contextlib.redirect_stdout(captured), live_log(path):
                process = subprocess.Popen([sys.executable, '-u', '-c',
                    "import sys; print('ready'); sys.stdin.readline(); print('finished')"],
                    stdin=subprocess.PIPE, stdout=output, stderr=subprocess.STDOUT, text=True)
                try:
                    self.assertTrue(seen.wait(3))
                    self.assertIsNone(process.poll())
                finally:
                    process.communicate('\n', timeout=3)
            self.assertEqual(captured.getvalue(), path.read_text())
            self.assertEqual(path.read_text(), 'ready\nfinished\n')

    def test_error_does_not_report_success(self):
        messages = []
        with self.assertRaisesRegex(ValueError, 'failure'):
            with Progress('Verify archive', notify=messages.append):
                raise ValueError('failure')
        self.assertIn('stopped in', messages[-1])

    def test_separator_uses_terminal_width(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch('mwad.progress.os.get_terminal_size', return_value=os.terminal_size((97, 24))):
            section('Step one')
        self.assertEqual(output.getvalue().splitlines(), ['', '-' * 97, 'Step one', '-' * 97])

    def test_apt_prompt_has_no_background_status_thread(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch('mwad.progress.threading.Thread') as thread:
            with setup_step(['sudo', 'apt-get', 'install', '--no-remove', 'libgmp10'], 2, 7):
                thread.assert_not_called()
        self.assertIn('Setup [2/7]: Install missing system packages', output.getvalue())
        self.assertNotIn('still running', output.getvalue())
