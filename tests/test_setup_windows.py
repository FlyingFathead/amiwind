"""Windows provisioning safety and parity without network or game inputs."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import build
import build_versions
from fetch_native import QCC_FILES
from fetch_toolchain import SPEC
from install_dependencies import PYTHON_PACKAGES
import setup_windows


class WindowsSetupTests(unittest.TestCase):
    def test_windows_sdk_matches_linux_and_constraints_cover_shared_packages(self):
        spec = json.loads((setup_windows.ROOT / 'config/windows-toolchain.json').read_text())
        self.assertEqual(spec['sdk']['version'], SPEC['release'])
        names = lambda values: {v.split('=')[0].split('>')[0].lower().replace('_', '-') for v in values}
        self.assertEqual(names(spec['python_constraints']), names(PYTHON_PACKAGES))
        for value in spec['python_constraints']:
            self.assertIn('==', value)

    def test_cache_verifies_hash_and_offline_never_downloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            spec = {'filename': 'tool.zip', 'url': 'https://example.invalid/tool.zip', 'bytes': 3,
                    'sha256': hashlib.sha256(b'abc').hexdigest()}
            with patch.object(setup_windows, 'run', side_effect=AssertionError('network attempted')):
                with self.assertRaisesRegex(ValueError, 'Offline cache missing'):
                    setup_windows.cached_download(spec, cache, offline=True)
                (cache / 'tool.zip').write_bytes(b'abc')
                self.assertEqual(setup_windows.cached_download(spec, cache, offline=True), cache / 'tool.zip')
                (cache / 'tool.zip').write_bytes(b'bad')
                with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
                    setup_windows.cached_download(spec, cache, offline=True)

    def test_zip_rejects_traversal_and_windows_paths(self):
        for name in ('pkg/../escape', '/pkg/file', 'pkg/C:/file', 'pkg/a\\b', 'pkg/file.'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                archive = Path(tmp) / 'bad.zip'
                with zipfile.ZipFile(archive, 'w') as z:
                    entry = zipfile.ZipInfo()
                    entry.filename = name  # Bypass Windows writer normalization for the hostile fixture.
                    entry.orig_filename = name
                    z.writestr(entry, b'bad')
                with self.assertRaisesRegex(ValueError, 'Unsafe ZIP'):
                    setup_windows.install_zip(archive, Path(tmp) / 'out', 'pkg')
                self.assertFalse((Path(tmp) / 'out').exists())

    def test_zip_reuses_exact_files_and_preserves_local_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / 'good.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('pkg/bin/tool.exe', b'fixture')
            setup_windows.install_zip(archive, root / 'out', 'pkg')
            setup_windows.install_zip(archive, root / 'out', 'pkg')
            target = root / 'out/bin/tool.exe'
            target.write_bytes(b'local change')
            with self.assertRaisesRegex(ValueError, 'Existing tool differs'):
                setup_windows.install_zip(archive, root / 'out', 'pkg')
            self.assertEqual(target.read_bytes(), b'local change')

    def test_older_version_emits_explicit_warning(self):
        args = build.parser().parse_args([])
        output = io.StringIO()
        with patch.object(build_versions, 'host_name', return_value='windows'), \
             patch.object(build_versions.platform, 'python_version', return_value='3.10.0'), \
             patch.object(build_versions, 'probe', side_effect=lambda name, value, spec: {
                 'name': name, 'reference': spec['version'], 'detected': None, 'status': 'missing'}), \
             contextlib.redirect_stdout(output):
            rows = build_versions.report(args)
        self.assertEqual(rows[0]['status'], 'older')
        self.assertIn('WARNING: Python 3.10.0 is older than', output.getvalue())

    @unittest.skipUnless(sys.platform == 'win32', 'PowerShell setup preview')
    def test_plan_needs_no_python_installation_or_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Preview needs a valid MSYS2 path, independent of TEMP aliases/spaces.
            tools = Path(Path(tmp).anchor) / ('amiwind-plan-' + Path(tmp).name)
            self.assertFalse(tools.exists())
            result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                                     '-File', str(setup_windows.ROOT / 'setup-windows.ps1'), '-Plan',
                                     '-ToolsDir', str(tools)], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Preview only', result.stdout)
            self.assertFalse(tools.exists())


if __name__ == '__main__':
    unittest.main()
