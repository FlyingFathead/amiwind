# SPDX-License-Identifier: GPL-3.0-only
"""Builder code never compiles, loads or stores large files in the system temp directory
(BUILD-TMP-SCRATCH-33, related to CHIM-ZONE-TMP-NOEXEC-33).

In the build container /tmp is a size-limited, RAM-backed, noexec tmpfs. Builder code that needs scratch
space uses tools/build_scratch.py (the run's scratch folder). This test is the static guard: a tempfile
call without dir=, or a /tmp string, in the tool sources fails unless it is one of the audited small
transient uses below, with its reason."""
import ast
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

import build_scratch  # noqa: E402

TEMP_CALLS = {'gettempdir', 'TemporaryDirectory', 'mkdtemp', 'mkstemp', 'NamedTemporaryFile',
              'TemporaryFile', 'SpooledTemporaryFile'}

# Audited class (c) uses: small files (a few KiB), nothing executed from them, removed with the block.
# file -> (allowed count, reason). A new use must go through build_scratch, or be argued for here.
SMALL_TRANSIENT = {
    'tools/build_aga.py': (1, 'QuakeC compile check: copies three source files, the compiler is run from its own path'),
    'tools/build_versions.py': (1, 'cwd for a tool version probe (--version output only)'),
    'tools/check_world_map_heap.py': (1, 'target ABI probe: one C file compiled to assembly (-S), nothing is run'),
    'tools/collision_bsp.py': (1, 'one tiny .map compiled by qbsp (the compiler is run from its own path)'),
    'tools/prepare_area.py': (1, 'one greeting mp3/wav (under 1 MB) converted by ffmpeg'),
    'tools/prepare_intro.py': (1, 'one sound file converted by ffmpeg'),
    'tools/prepare_media_assets.py': (1, 'one archived sound at a time, per worker (the video ones use dir=)'),
    'tools/prepare_npcs.py': (1, 'one greeting mp3 converted by ffmpeg'),
    'tools/run_tests.py': (1, 'the test runner scratch: plan, event and log files of test workers'),
}
# Files that may name /tmp literally.
TMP_PATH_STRINGS = {
    'tools/fsuae_headless_probe.py': 'container diagnostic: the probe works in its own throwaway worker container',
}
SCRIPT_SUFFIXES = {'.sh', '.cmd', '.ps1', '.bat'}


def python_sources():
    for folder in ('tools', 'src'):
        for path in sorted((ROOT / folder).rglob('*.py')):
            if '__pycache__' not in path.parts:
                yield path


def temp_call_name(node):
    func = node.func
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == 'tempfile':
        return func.attr
    return None


def system_temp_uses():
    """{relative path: [(line, call)]} of tempfile calls that land in the system temp directory."""
    found = {}
    for path in python_sources():
        relative = path.relative_to(ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=relative)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = temp_call_name(node)
                if name in TEMP_CALLS and (name == 'gettempdir' or not any(k.arg == 'dir' for k in node.keywords)):
                    found.setdefault(relative, []).append((node.lineno, name))
    return found


class BuildScratchHelperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)

    def env(self, **values):
        env = {k: v for k, v in os.environ.items() if k != build_scratch.ENV}
        env.update(values)
        return mock.patch.dict(os.environ, env, clear=True)

    def test_root_prefers_the_environment_then_the_caller_then_the_checkout(self):
        with self.env(**{build_scratch.ENV: str(self.base / 'run')}):
            self.assertEqual(build_scratch.scratch_root(self.base / 'near'), self.base / 'run')
        with self.env():
            self.assertEqual(build_scratch.scratch_root(self.base / 'near'), self.base / 'near' / '.scratch')
            self.assertEqual(build_scratch.scratch_root(), ROOT / 'out' / 'scratch')

    def test_folder_is_removed_after_success(self):
        with self.env(**{build_scratch.ENV: str(self.base / 'run')}):
            with build_scratch.scratch_dir('ok-') as folder:
                (folder / 'file').write_bytes(b'x')
                self.assertTrue(folder.is_dir())
                self.assertEqual(folder.parent, self.base / 'run')
                self.assertTrue(folder.name.startswith('ok-'))
        self.assertFalse(folder.exists())

    def test_folder_is_kept_after_a_failure_for_inspection(self):
        with self.env(**{build_scratch.ENV: str(self.base / 'run')}):
            with self.assertRaises(RuntimeError):
                with build_scratch.scratch_dir('bad-') as folder:
                    (folder / 'file').write_bytes(b'x')
                    raise RuntimeError('stage failed')
        self.assertTrue((folder / 'file').is_file())

    def test_many_small_folders_can_opt_out_of_keeping(self):
        with self.env(**{build_scratch.ENV: str(self.base / 'run')}):
            with self.assertRaises(RuntimeError):
                with build_scratch.scratch_dir('item-', keep_on_failure=False) as folder:
                    raise RuntimeError('item failed')
        self.assertFalse(folder.exists())

    @unittest.skipIf(os.name == 'nt', 'POSIX shell script')
    def test_scratch_can_run_a_program_it_wrote(self):
        # The point of the helper: what a stage builds in scratch can be executed (no noexec tmpfs).
        import subprocess
        with self.env(**{build_scratch.ENV: str(self.base / 'run')}):
            with build_scratch.scratch_dir('exec-') as folder:
                script = folder / 'probe.sh'
                script.write_text('#!/bin/sh\necho ok\n', newline='\n')
                script.chmod(0o755)
                self.assertEqual(subprocess.run([str(script)], capture_output=True, text=True).stdout.strip(), 'ok')

    def test_the_builder_points_every_stage_at_the_run_scratch(self):
        run = self.base / 'run-1'
        with self.env():
            self.assertEqual(build_scratch.stage_environment(run), {build_scratch.ENV: str(run / 'scratch')})
        with self.env(**{build_scratch.ENV: str(self.base / 'big-volume')}):
            self.assertEqual(build_scratch.stage_environment(run), {})

    def test_both_stage_launchers_pass_the_scratch_environment(self):
        for name in ('tools/build.py', 'tools/build_parallel.py'):
            self.assertIn('stage_environment(run)', (ROOT / name).read_text(encoding='utf-8'), name)


class NoSystemTempTests(unittest.TestCase):
    def test_tool_sources_use_no_unreviewed_system_temp(self):
        problems = []
        for relative, uses in sorted(system_temp_uses().items()):
            allowed = SMALL_TRANSIENT.get(relative, (0, ''))[0]
            if len(uses) > allowed:
                problems.append('%s: %d system-temp use(s) at %s, %d audited; use build_scratch.scratch_dir() '
                                '(or dir=) so nothing is built or stored in /tmp'
                                % (relative, len(uses), ', '.join('line %d %s' % u for u in uses), allowed))
        self.assertEqual(problems, [])

    def test_the_audited_list_is_exact(self):
        # A fixed or removed use must leave the list too, so it cannot hide a new one later.
        counts = {k: len(v) for k, v in system_temp_uses().items()}
        self.assertEqual({k: v[0] for k, v in SMALL_TRANSIENT.items()}, counts)

    def test_no_tool_source_names_tmp(self):
        problems = []
        for path in python_sources():
            relative = path.relative_to(ROOT).as_posix()
            if relative in TMP_PATH_STRINGS:
                continue
            tree = ast.parse(path.read_text(encoding='utf-8'), filename=relative)
            for node in ast.walk(tree):
                if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                        and '\n' not in node.value and node.value.startswith('/tmp')):
                    problems.append('%s:%d names /tmp' % (relative, node.lineno))
        self.assertEqual(problems, [])

    def test_shell_scripts_use_no_tmp_or_mktemp(self):
        problems = []
        candidates = [ROOT / name for name in ('build.sh', 'build.cmd', 'build.ps1', 'setup-windows.cmd',
                                               'setup-windows.ps1')]
        candidates += [p for p in (ROOT / 'tools').rglob('*') if p.suffix in SCRIPT_SUFFIXES]
        for path in candidates:
            if not path.is_file():
                continue
            text = path.read_text(encoding='utf-8', errors='replace')
            for token in ('/tmp', 'mktemp', 'TMPDIR', '$env:TEMP', '%TEMP%', '$TEMP'):
                if token in text:
                    problems.append('%s uses %s' % (path.relative_to(ROOT).as_posix(), token))
        self.assertEqual(problems, [])

    def test_audited_reasons_are_given(self):
        for name, (count, reason) in SMALL_TRANSIENT.items():
            self.assertGreater(count, 0, name)
            self.assertGreater(len(reason), 20, name)
            self.assertTrue((ROOT / name).is_file(), name)

    def test_zone_walk_gate_has_no_system_temp_left(self):
        text = (ROOT / 'tools/chim/zone_sim.py').read_text(encoding='utf-8')
        self.assertNotIn('tempfile', text)
        self.assertNotIn('library_in_temp', text)

    def test_large_scratch_stages_use_the_helper(self):
        # Raw movie frames (up to ~3 GB) and the terrain survey are class (b): never the system temp.
        for name in ('tools/prepare_video.py', 'tools/prepare_world_ui.py'):
            self.assertIn('scratch_dir(', (ROOT / name).read_text(encoding='utf-8'), name)
        uses = system_temp_uses()
        for name in ('tools/prepare_video.py', 'tools/prepare_world_ui.py', 'tools/chim/zone_sim.py'):
            self.assertNotIn(name, uses)


if __name__ == '__main__':
    unittest.main()
