"""Windows launcher contract and shared-pipeline parity (no SDK/game inputs)."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import build
import build_windows
from install_dependencies import PYTHON_PACKAGES


class WindowsBuildTests(unittest.TestCase):
    def test_adapter_preserves_shared_arguments_and_defaults(self):
        shared = ['--dry-run', '--jobs', '3', '--workspace', 'output with spaces',
                  '--sdk', 'sdk folder', '--name', 'windows-check']
        windows, options, forwarded = build_windows.arguments(['--msys2', 'msys folder', *shared])
        self.assertEqual(forwarded, shared)
        self.assertEqual(vars(options), vars(build.parser().parse_args(shared)))
        self.assertEqual(windows.msys2, Path('msys folder'))

    def test_inventory_does_not_require_msys_or_create_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            tools = Path(directory) / 'missing tools'
            with patch.object(build_windows.sys, 'platform', 'win32'), \
                 patch.object(build_windows.sysconfig, 'get_platform', return_value='win-amd64'), \
                 patch.object(build_windows.subprocess, 'run', return_value=subprocess.CompletedProcess([], 7)) as run:
                self.assertEqual(build_windows.main(['--host-plan', '--tools-dir', str(tools)]), 7)
            command = run.call_args.args[0]
            self.assertEqual(command[-3:], ['--host-plan', '--tools-dir', str(tools)])
            self.assertIn(str(build_windows.ROOT / 'tools/build.py'), command)
            self.assertFalse(tools.exists())

    def test_setup_preview_uses_linux_requirements_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            tools = Path(directory) / 'new tools'
            args = build.parser().parse_args(['--tools-dir', str(tools), '--plan'])
            output = io.StringIO()
            with patch.object(build_windows.subprocess, 'run', side_effect=AssertionError('preview executed')), \
                 contextlib.redirect_stdout(output):
                self.assertEqual(build_windows.setup_python(args, {}), 0)
            for package in PYTHON_PACKAGES:
                self.assertIn(package, output.getvalue())
            self.assertFalse(tools.exists())

    def test_setup_failure_stops_before_pip(self):
        with tempfile.TemporaryDirectory() as directory:
            args = build.parser().parse_args(['--tools-dir', directory])
            with patch.object(build_windows.subprocess, 'run', side_effect=subprocess.CalledProcessError(23, ['venv'])) as run, \
                 contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(subprocess.CalledProcessError):
                    build_windows.setup_python(args, {})
            self.assertEqual(run.call_count, 1)

    def test_rejects_linux_downloads_and_incompatible_python(self):
        for platform, flag in [('win-amd64', '--autoinstall'), ('mingw_x86_64', '--host-plan')]:
            with self.subTest(platform=platform), \
                 patch.object(build_windows.sys, 'platform', 'win32'), \
                 patch.object(build_windows.sysconfig, 'get_platform', return_value=platform), \
                 patch.object(build_windows.subprocess, 'run', side_effect=AssertionError('must not execute')), \
                 contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(build_windows.main([flag]), 1)

    def test_environment_does_not_mutate_parent(self):
        original = {'PATH': 'previous', 'PYTHONHOME': 'other-python', 'PYTHONPATH': 'other-modules'}
        args = build.parser().parse_args([])
        env = build_windows.environment(args, Path('msys'), original)
        self.assertEqual(original['PATH'], 'previous')
        self.assertNotIn('PYTHONHOME', env)
        self.assertNotIn('PYTHONPATH', env)
        self.assertEqual(env['PYTHONUTF8'], '1')
        self.assertTrue(env['PATH'].endswith(os.pathsep + 'previous'))

    @unittest.skipUnless(sys.platform == 'win32', 'real Windows launcher integration')
    def test_cmd_and_ps1_preserve_arguments_and_exit_status(self):
        # Use the real launchers with a tiny recording target, no installed SDK.
        with tempfile.TemporaryDirectory(prefix='amiwind launcher ') as directory:
            root = Path(directory)
            (root / 'tools').mkdir()
            for name in ('build.cmd', 'build.ps1'):
                shutil.copyfile(build_windows.ROOT / name, root / name)
            (root / 'tools/build_windows.py').write_text(
                'import json, sys\nprint(json.dumps(sys.argv[1:]))\nsys.exit(19)\n', encoding='utf-8')
            env = dict(os.environ, AMIWIND_PYTHON=sys.executable)
            expected = ['--data-files', 'C:\\Example Games\\Morrowind',
                        '--name', 'literal-$value', '--jobs', '3']
            ps = ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(root / 'build.ps1')]
            commands = [ps + expected,
                        'cmd.exe /d /s /c "' + subprocess.list2cmdline([str(root / 'build.cmd'), *expected]) + '"']
            for command in commands:
                with self.subTest(command=command):
                    result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=30)
                    self.assertEqual(result.returncode, 19, result.stderr + result.stdout)
                    self.assertEqual(json.loads(result.stdout), expected)

    @unittest.skipUnless(os.name == 'posix', 'real Linux/POSIX launcher integration')
    def test_shell_launcher_preserves_arguments_and_exit_status(self):
        with tempfile.TemporaryDirectory(prefix='amiwind launcher ') as directory:
            root = Path(directory)
            (root / 'tools').mkdir()
            shutil.copyfile(build_windows.ROOT / 'build.sh', root / 'build.sh')
            (root / 'tools/build.py').write_text(
                'import json, sys\nprint(json.dumps(sys.argv[1:]))\nsys.exit(19)\n', encoding='utf-8')
            expected = ['--data-files', '/games/GOG Games/Morrowind', '--name', 'literal-$value']
            result = subprocess.run(['sh', str(root / 'build.sh'), *expected],
                                    env=dict(os.environ, AMIWIND_PYTHON=sys.executable),
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 19, result.stderr + result.stdout)
            self.assertEqual(json.loads(result.stdout), expected)


if __name__ == '__main__':
    unittest.main()
