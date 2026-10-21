# SPDX-License-Identifier: GPL-3.0-only
"""--clean and --public-defaults (tools/clean_build.py, docs/BUILD_CACHE.md "Before a release").

Origin: a tester's public build stopped at world-scenery (BUILD-LAVA-TERRAIN-BUDGET-38) while the cached
builds with a cell list outside the source tree passed. --clean builds as a first-time user (no earlier run,
an empty workspace cache); --public-defaults refuses what a public user would not have. Both are off by
default and change no stage command or stage environment; the receipt records them when given.
"""
import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]

import build  # noqa: E402
import clean_build  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_guard  # noqa: E402

TOOLS = {name: '/tools/' + name for name in ('qbsp', 'vis', 'light', 'qcc', 'ffmpeg', 'xdftool', 'rdbtool')}
RUN = Path('/private/run')


class Stop(Exception):
    pass


def run_main(*argv):
    """build.main up to resolve_jobs (after both checks): (exit code or 'passed', stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), \
            patch('build.resolve_jobs', side_effect=Stop):
        try:
            build.main(list(argv))
            result = 0
        except SystemExit as exc:
            result = exc.code
        except Stop:
            result = 'passed'
    return result, out.getvalue(), err.getvalue()


def plan(workspace, *extra):
    args = build.parser().parse_args(['--workspace', str(workspace), *extra])
    args.data_files = Path('/owned/Data Files')
    args.sdk = Path('/sdk')
    with patch('build_jobs.auto_jobs', return_value=4):
        return build.commands(args, TOOLS, RUN)


@env_guard.isolated
class CleanBuild(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp.name) / 'ws'

    def tearDown(self):
        self.tmp.cleanup()

    def test_off_by_default(self):
        args = build.parser().parse_args([])
        self.assertFalse(args.clean)
        self.assertFalse(args.public_defaults)
        self.assertIsNone(clean_build.configure_clean(args))
        self.assertIsNone(clean_build.check_public_defaults(args, build.parser()))

    def test_stage_commands_are_unchanged(self):
        # Stage keys come from the commands and the stage environment: neither switch touches either.
        default = plan(self.workspace)
        self.assertEqual(plan(self.workspace, '--clean'), default)
        self.assertEqual(plan(self.workspace, '--public-defaults'), default)
        self.assertEqual(plan(self.workspace, '--clean', '--public-defaults'), default)

    def test_empty_or_absent_cache_passes_and_is_recorded(self):
        args = build.parser().parse_args(['--workspace', str(self.workspace), '--clean'])
        environ = {'AMIWIND_STORAGE_POOL': '/vol/pool', 'AMIWIND_PASS_CACHE': '/vol/passes', 'OTHER': 'kept'}
        record = clean_build.configure_clean(args, environ=environ)
        self.assertTrue(record['clean'])
        self.assertEqual(record['environment_ignored'], ['AMIWIND_PASS_CACHE', 'AMIWIND_STORAGE_POOL'])
        self.assertEqual(environ, {'OTHER': 'kept'})
        (self.workspace / 'cache').mkdir(parents=True)
        self.assertTrue(clean_build.configure_clean(args, environ={})['workspace_cache_empty_at_start'])

    def test_filled_cache_is_refused_and_kept(self):
        entry = self.workspace / 'cache' / 'chim-units' / 'unit.bin'
        entry.parent.mkdir(parents=True)
        entry.write_bytes(b'x')
        args = build.parser().parse_args(['--workspace', str(self.workspace), '--clean'])
        with self.assertRaisesRegex(ValueError, 'chim-units.*new --workspace'):
            clean_build.configure_clean(args, environ={})
        self.assertTrue(entry.is_file())  # never deleted

    def test_earlier_work_is_refused(self):
        for flag, extra in (('--reuse-from', ['--reuse-from', '/vol/build/run']),
                            ('--rebuild-stage', ['--reuse-from', '/vol/build/run', '--rebuild-stage', 'chim']),
                            ('--prerendered', ['--prerendered', '/vol/store']),
                            ('--storage-pool-dir', ['--storage-pool-dir', '/vol/pool']),
                            ('--rebuild-unit', ['--rebuild-unit', 'interior-room:x']),
                            ('--gallery-seed-run', ['--gallery-seed-run', '/vol/build/run']),
                            ('--allow-release-reuse', ['--allow-release-reuse'])):
            with self.subTest(flag=flag):
                args = build.parser().parse_args(['--workspace', str(self.workspace), '--clean', *extra])
                with self.assertRaisesRegex(ValueError, flag + ':'):
                    clean_build.configure_clean(args, environ={})
        args = build.parser().parse_args(['--workspace', str(self.workspace), '--clean'])
        with self.assertRaisesRegex(ValueError, 'storage_pool_dir'):
            clean_build.configure_clean(args, environ={}, config_pool='/vol/pool')

    def test_main_refuses_before_any_stage_and_prints_the_line(self):
        code, out, err = run_main('--workspace', str(self.workspace), '--clean', '--reuse-from', '/vol/build/r')
        self.assertEqual(code, 2)
        self.assertIn('--reuse-from: takes the stages of an earlier run', err)
        code, out, err = run_main('--workspace', str(self.workspace), '--clean')
        self.assertEqual(code, 'passed')
        self.assertIn('CLEAN BUILD (--clean)', out)

    def test_receipt_fields(self):
        args = build.parser().parse_args(['--workspace', str(self.workspace), '--clean', '--public-defaults'])
        args.data_files = Path('/owned/Data Files')
        args.clean_record = clean_build.configure_clean(args, environ={})
        args.public_defaults_record = clean_build.check_public_defaults(args, build.parser())
        receipt = build.provenance(args, {})
        self.assertIs(receipt['clean'], True)
        self.assertEqual(receipt['clean_build']['workspace_cache'], str((self.workspace / 'cache').absolute()))
        self.assertIs(receipt['public_defaults'], True)
        self.assertEqual(receipt['public_defaults_check']['refused'], [])
        default = build.parser().parse_args(['--workspace', str(self.workspace)])
        default.data_files = Path('/owned/Data Files')
        plain = build.provenance(default, {})
        for key in ('clean', 'clean_build', 'public_defaults', 'public_defaults_check'):
            self.assertNotIn(key, plain)


@env_guard.isolated
class PublicDefaults(unittest.TestCase):
    def check(self, *argv):
        args = build.parser().parse_args(list(argv) + ['--public-defaults'])
        return clean_build.check_public_defaults(args, build.parser())

    def test_default_build_passes(self):
        record = self.check()
        self.assertTrue(record['public_defaults'])
        self.assertEqual(record['refused'], [])

    def test_waivers_and_overrides_are_refused(self):
        for extra in (['--override', 'legacy-area'], ['--accept-entity-loss', 'reason'],
                      ['--allow-data-differences'], ['--allow-placeholder', 'x'],
                      ['--accept-known-stair-findings', 'ID'], ['--allow-release-reuse']):
            with self.subTest(extra=extra), self.assertRaisesRegex(ValueError, extra[0]):
                self.check(*extra)

    def test_private_cell_list_is_refused_and_a_tree_file_is_not(self):
        with self.assertRaisesRegex(ValueError, 'outside the source tree'):
            self.check('--chim-regions', '@/private/cells.json')
        with self.assertRaisesRegex(ValueError, 'chim-regions-status'):
            self.check('--chim-regions', 'coast', '--chim-regions-status', '/private/cell-progress.json')
        inside = ROOT / 'docs' / 'chim' / 'cell-progress-reference.json'
        self.assertEqual(self.check('--chim-regions', '@' + str(ROOT / 'config' / 'cells.json'),
                                    '--chim-regions-status', str(inside))['refused'], [])

    def test_default_cell_list_in_the_source_tree_passes(self):
        # BUILD-CHIM-CELLS-PRIVATE-LIST-47: the default cell list and tracker are in the source tree
        self.assertEqual(self.check('--chim-regions', '@' + str(build.CHIM_CELLS_DEFAULT),
                                    '--chim-regions-status', str(build.CHIM_CELLS_STATUS_DEFAULT))['refused'], [])
        self.assertEqual(self.check('--chim-regions', 'none')['refused'], [])

    def test_experimental_switches_are_refused_at_a_non_default_value(self):
        # --chim-crossing 0, --file-aliases off and the rest: the old methods since v0.0.47 made v0.0.47-dev2's
        # switches the default (decided for the project, 2026-10-21)
        for extra in (['--npc-lod', 'on'], ['--chim-crossing', '0'], ['--file-aliases', 'off'],
                      ['--shared-skins', 'off'], ['--chim-actor-table', 'off'], ['--chim-terrain-pack', 'bsp29'],
                      ['--chim-terrain-pack', 'compact'],
                      ['--engine-profile', 'upstream'], ['--stair-walk-cache', 'full']):
            with self.subTest(extra=extra), self.assertRaisesRegex(ValueError, extra[0]):
                self.check(*extra)
        # The documented default value given by hand, and a value the builder decides by itself, are fine.
        self.assertEqual(self.check('--npc-lod', 'off', '--stair-walk-cache', 'records')['refused'], [])
        # v0.0.47-dev2's five switches are the defaults now: given by hand they pass
        self.assertEqual(self.check('--chim-crossing', '1', '--chim-actor-table', 'on', '--chim-terrain-pack',
                                    'generate', '--file-aliases', 'on', '--shared-skins', 'on')['refused'], [])

    def test_every_refusal_is_listed(self):
        with self.assertRaises(ValueError) as caught:
            self.check('--npc-lod', 'on', '--accept-entity-loss', 'r', '--chim-regions', '@/private/c.json')
        self.assertIn('(3)', str(caught.exception))

    def test_the_experimental_page_is_read(self):
        found = clean_build.experimental_switches()
        parser_flags = {flag for action in build.parser()._actions for flag in action.option_strings}
        for flag in ('--npc-lod', '--chim-crossing', '--engine-profile', '--stair-walk-cache'):
            self.assertIn(flag, found)
            self.assertIn(flag, parser_flags)
        self.assertIn('full', found['--stair-walk-cache'])

    def test_main_lists_refusals(self):
        code, out, err = run_main('--public-defaults', '--override', 'legacy-area', '--legacy-area', 'balmora')
        self.assertEqual(code, 2)
        self.assertIn('--override legacy-area', err)
        self.assertIn('--legacy-area', err)


if __name__ == '__main__':
    unittest.main()
