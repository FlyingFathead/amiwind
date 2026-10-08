# SPDX-License-Identifier: GPL-3.0-only
"""tools/build.py must start on a bare system Python: CI and new users run it with no third-party packages
to install the tools (--autoinstall --install-dependencies). Any third-party import reached while parsing the
command line (e.g. numpy from an option helper) breaks the bootstrap (CI-BOOTSTRAP-NUMPY-32)."""
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BLOCKER = textwrap.dedent('''
    import importlib.abc, sys
    from pathlib import Path
    LOCAL = {p.stem for d in ("tools", "src") for p in (Path(%r) / d).glob("*.py")}
    LOCAL |= {p.name for d in ("tools", "src") for p in (Path(%r) / d).iterdir() if p.is_dir()}
    class Block(importlib.abc.MetaPathFinder):
        def find_spec(self, name, path=None, target=None):
            top = name.split(".")[0]
            if top in sys.stdlib_module_names or top in LOCAL or top in ("sitecustomize", "_distutils_hack"):
                return None
            raise ImportError("third-party module %%s imported before the tools exist" %% name)
    sys.meta_path.insert(0, Block())
''')


class BootstrapImportTests(unittest.TestCase):
    def run_bare(self, *args):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'sitecustomize.py').write_text(BLOCKER % (str(ROOT), str(ROOT)), encoding='utf-8')
            env = dict(os.environ, PYTHONPATH=tmp, PYTHONNOUSERSITE='1')
            return subprocess.run([sys.executable, str(ROOT / 'tools' / 'build.py'), *args], cwd=ROOT, env=env,
                                  capture_output=True, text=True, timeout=120)

    def test_help_needs_no_third_party_modules(self):
        r = self.run_bare('--help')
        self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])

    def test_dependency_plan_needs_no_third_party_modules(self):
        r = self.run_bare('--install-dependencies', '--plan')
        self.assertNotIn('before the tools exist', r.stdout + r.stderr)
        self.assertNotIn('Traceback', r.stderr)


if __name__ == '__main__':
    unittest.main()
