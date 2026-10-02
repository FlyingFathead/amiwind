"""Host boundaries: simulated Windows choices and real POSIX make invocation."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import build
import build_host
import build_versions


class BuildHostTests(unittest.TestCase):
    def assertSamePath(self, actual, expected):
        """Discovery returns canonical paths; fixture paths may use 8.3 aliases."""
        self.assertEqual(Path(actual).resolve(), Path(expected).resolve())

    def test_windows_explicit_tool_and_sdk_discovery(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ('sdk/bin/m68k-amigaos-gcc.exe', 'sdk/bin/vasmm68k_mot.exe',
                         'sdk/m68k-amigaos/ndk-include/exec/exec_lib.i',
                         'ericw/bin/qbsp.exe', 'ericw/bin/vis.exe', 'ericw/bin/light.exe',
                         'Quake-Tools/qcc-host.exe'):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch(); path.chmod(0o755)
            args = build.parser().parse_args(['--tools-dir', temp])
            with patch.object(build_host, 'host_name', return_value='windows'):
                self.assertSamePath(build.detected_sdk(args), root/'sdk')
                self.assertSamePath(build_versions.find_quake_tools(args), root/'ericw/bin')
                self.assertSamePath(build_versions.find_qcc(args), root/'Quake-Tools/qcc-host.exe')
            with patch.object(build_host, 'host_name', return_value='linux'):
                self.assertIsNone(build.detected_sdk(args))

    @unittest.skipUnless(sys.platform == 'win32', 'Windows 8.3 path alias regression')
    def test_discovery_with_short_temp_alias(self):
        import ctypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        short_path = kernel.GetShortPathNameW
        short_path.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32]
        short_path.restype = ctypes.c_uint32
        with tempfile.TemporaryDirectory(prefix='amiwind-long-temp-path-') as directory:
            output = ctypes.create_unicode_buffer(32768)
            size = short_path(directory, output, len(output))
            if not size:
                raise ctypes.WinError(ctypes.get_last_error())
            self.assertLess(size, len(output))
            if Path(output.value) == Path(directory).resolve():
                self.skipTest('This volume does not provide a distinct 8.3 alias')
            # Keep the aliased input: exercise real font/SDK/map/QCC discovery.
            with patch.object(tempfile, 'tempdir', output.value):
                self.test_managed_font_and_explicit_missing_font()
                self.test_windows_explicit_tool_and_sdk_discovery()

    def test_python_distribution_selects_venv_layout(self):
        for host, platform, expected in (('windows', 'win-amd64', 'Scripts/python.exe'),
                                         ('windows', 'mingw_x86_64', 'bin/python.exe'),
                                         ('linux', 'linux-x86_64', 'bin/python')):
            with self.subTest(host=host, platform=platform), \
                 patch.object(build_host, 'host_name', return_value=host), \
                 patch.object(build_host.sysconfig, 'get_platform', return_value=platform):
                self.assertEqual(build_host.venv_python(Path('venv')), Path('venv')/expected)

    def test_managed_font_and_explicit_missing_font(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); font = root/'fonts/DejaVuSansMono.ttf'
            font.parent.mkdir(); font.touch()
            self.assertSamePath(build_host.fallback_font(tools_dir=root), font)
            with self.assertRaisesRegex(ValueError, 'not found'):
                build_host.fallback_font(root/'missing.ttf', root)

    def test_font_path_is_forwarded_as_one_stage_argument(self):
        args = build.parser().parse_args(['--data-files', '/game', '--sdk', '/sdk',
                                         '--fallback-font', '/fonts with spaces/DejaVuSansMono.ttf'])
        tools = {name: '/tools/'+name for name in ('qbsp', 'vis', 'light', 'qcc', 'ffmpeg', 'xdftool', 'rdbtool')}
        command = dict(build.commands(args, tools, Path('/run')))['scene']
        self.assertEqual(command[command.index('--fallback-font')+1], str(args.fallback_font))

    def test_host_plan_has_no_execution_or_installation(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp)/'absent tools'
            output = io.StringIO()
            with patch.object(build_host, 'host_name', return_value='windows'), \
                 patch.object(subprocess, 'run', side_effect=AssertionError('must not run tools')), \
                 patch.object(build, 'prerequisites', side_effect=AssertionError('must not read game data')), \
                 contextlib.redirect_stdout(output):
                self.assertEqual(build.main(['--host-plan', '--tools-dir', str(destination)]), 0)
            result = json.loads(output.getvalue())
            self.assertEqual(result['host'], 'windows')
            self.assertIn('untested', result['validation'])
            self.assertFalse(destination.exists())

    def test_host_plan_rejects_install_mode(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                build.main(['--host-plan', '--autoinstall'])
        self.assertEqual(error.exception.code, 1)

    def test_cygpath_translates_one_argument_without_shell_expansion(self):
        value = r"C:\Ami Wind\source $(literal) 'quoted'"
        with patch.object(build_host, 'find_executable', return_value='/msys/usr/bin/cygpath.exe'), \
             patch.object(subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '/c/Ami Wind/source\r\n')) as run:
            self.assertEqual(build_host.translate_path(value), '/c/Ami Wind/source')
        self.assertEqual(run.call_args.args[0], ['/msys/usr/bin/cygpath.exe', '-u', '--', value])
        self.assertFalse(run.call_args.kwargs.get('shell', False))

    def test_cygpath_rejects_missing_tool_bad_output_and_failure(self):
        with patch.object(build_host, 'find_executable', return_value=None):
            with self.assertRaisesRegex(ValueError, 'not found'):
                build_host.translate_path('file')
        with patch.object(build_host, 'find_executable', return_value='cygpath'):
            for output in ('', 'a\nb', 'a\0b'):
                with patch.object(subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, output)):
                    with self.assertRaises(ValueError): build_host.translate_path('file')
            with patch.object(subprocess, 'run', side_effect=subprocess.CalledProcessError(1, ['cygpath'])):
                with self.assertRaises(subprocess.CalledProcessError): build_host.translate_path('file')

    @unittest.skipUnless(os.name == 'posix', 'requires a POSIX make shell')
    def test_make_uses_selected_interpreter_with_spaces_quotes_and_dollars(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); interpreter = root/"Python space 'quote' $literal"
            interpreter.symlink_to(sys.executable)
            (root/'Makefile').write_text('all:\n\t$(PYTHON) -c "from pathlib import Path; Path(\'result\').write_text(\'ran\')"\n')
            subprocess.run(['make', '-s', build_host.make_python_assignment(interpreter)],
                           cwd=root, check=True, capture_output=True, text=True)
            self.assertEqual((root/'result').read_text(), 'ran')


if __name__ == '__main__':
    unittest.main()
