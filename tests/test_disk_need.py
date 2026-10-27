# SPDX-License-Identifier: GPL-3.0-only
"""The free space a build needs (BUILD-DISK-NEED-UNKNOWN-52, tools/disk_need.py).

A tester's public v0.0.50 build stopped halfway on a full disk: the only check asked a fixed 20 GiB once. The
maintainer (26 October 2026): among the very first steps of a build, failing fast; the minimum configurable in the
build defaults; compared with the last known good build, about 30 % over it; the game data copied into Docker too.
These tests fail when the check leaves the first steps (the entry script, the Docker image build, the game data
copy), when the minimum or the margin keys a stage, when a stage starts without its own last figure checked, when a
passing build writes no figure, and when the shipped figure is missing or older than the release."""
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_cache  # noqa: E402
import disk_need  # noqa: E402

GIB = 2 ** 30
FIGURE = {'schema': disk_need.SCHEMA, 'version': '0.0.52', 'build': 'b',
          'bytes': {'run': 10 * GIB, 'scratch': 2 * GIB, 'cache': 3 * GIB, 'pool': 5 * GIB, 'game_data': 2 * GIB,
                    'builder_image': 2 * GIB},
          'stages': {'chim': {'workspace': 4 * GIB}}}
NO_SWITCH = {disk_need.WATCH_ENV: '', disk_need.MIN_FREE_ENV: '', disk_need.MARGIN_ENV: ''}


def stage_scripts():
    text = (ROOT / 'tools' / 'build.py').read_text(encoding='utf-8')
    return sorted(set(re.findall(r"tool\(\s*'([A-Za-z0-9_]+\.py)'", text)))


class MachineSettingsKeyNothingTests(unittest.TestCase):
    """Changing the minimum or the margin re-keys no stage (config/build-defaults.json is read by stages)."""

    def selections(self, defaults=None):
        index = build_cache.SourceIndex(ROOT, top_format=build_cache.STAGE_TOP_FORMAT)
        if defaults is not None:
            index.files._paths[build_cache.MACHINE_SETTINGS_FILE] = defaults
        found = {}
        for script in stage_scripts():
            path = ROOT / 'tools' / script
            if path.is_file():
                found[script] = index.selection(path)[0]
        return found

    def changed(self, **values):
        text = json.loads((ROOT / 'config' / 'build-defaults.json').read_text(encoding='utf-8'))
        text.update(values)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'build-defaults.json'
            path.write_text(json.dumps(text, indent=2) + '\n', encoding='utf-8', newline='\n')
            return self.selections(path)

    @classmethod
    def setUpClass(cls):
        cls.base = None

    def baseline(self):
        if MachineSettingsKeyNothingTests.base is None:
            MachineSettingsKeyNothingTests.base = self.selections()
        return MachineSettingsKeyNothingTests.base

    def test_some_stage_reads_the_build_defaults(self):
        keyed = [s for s, sel in self.baseline().items() if build_cache.MACHINE_SETTINGS_FILE in sel]
        self.assertTrue(keyed, 'no stage keys config/build-defaults.json: this test would prove nothing')

    def test_changing_the_minimum_and_the_margin_rekeys_nothing(self):
        after = self.changed(min_free_gib=999, disk_margin_percent=77)
        self.assertEqual([s for s in after if after[s] != self.baseline()[s]], [])

    def test_changing_a_real_setting_still_rekeys(self):
        after = self.changed(lava='static')
        keyed = [s for s, sel in self.baseline().items() if build_cache.MACHINE_SETTINGS_FILE in sel]
        self.assertEqual(sorted(s for s in after if after[s] != self.baseline()[s]), sorted(keyed))

    def test_the_defaults_file_keeps_the_digest_it_had_before_the_settings(self):
        # the file is written as json indent 2, so without the machine settings it is the bytes it had before them:
        # no stage of an earlier build is re-keyed by their arrival
        path = ROOT / 'config' / 'build-defaults.json'
        text = path.read_text(encoding='utf-8')
        values = json.loads(text)
        self.assertEqual(text, json.dumps(values, indent=2) + '\n')
        self.assertTrue(disk_need.MACHINE_SETTINGS <= set(values))
        self.assertEqual(build_cache.MACHINE_SETTINGS, disk_need.MACHINE_SETTINGS)
        self.assertEqual(build_cache.MACHINE_SETTINGS_FILE, 'config/build-defaults.json')

    def test_the_settings_and_the_switch_in_the_environment_key_nothing(self):
        for name in (disk_need.MIN_FREE_ENV, disk_need.MARGIN_ENV, disk_need.WATCH_ENV):
            self.assertIn(name, build_cache.IGNORED_ENV)

    def test_the_figure_keys_nothing(self):
        # the shipped figure changes with every release: no stage may read it
        for script, selection in self.baseline().items():
            self.assertNotIn('config/disk-footprint.json', selection, script)


class SettingsTests(unittest.TestCase):
    def test_shipped_defaults(self):
        values = json.loads((ROOT / 'config' / 'build-defaults.json').read_text(encoding='utf-8'))
        self.assertEqual(values['min_free_gib'], 35)        # the v0.0.52 floor
        self.assertEqual(values['disk_margin_percent'], 30)  # the maintainer: about 30 % or more
        with patch.dict(os.environ, NO_SWITCH):
            self.assertEqual(disk_need.settings(), {'min_free_gib': 35, 'margin_percent': 30})

    def test_environment_overrides_and_bad_values(self):
        self.assertEqual(disk_need.settings({disk_need.MIN_FREE_ENV: '5', disk_need.MARGIN_ENV: '50'}),
                         {'min_free_gib': 5.0, 'margin_percent': 50.0})
        with self.assertRaises(ValueError):
            disk_need.settings({disk_need.MIN_FREE_ENV: 'lots'})
        with tempfile.TemporaryDirectory() as temp:
            bad = Path(temp) / 'defaults.json'
            bad.write_text('{"min_free_gib": -1}', encoding='utf-8')
            with self.assertRaises(ValueError):
                disk_need.settings({}, bad)


class ShippedFigureTests(unittest.TestCase):
    """The release ships the last known good figure; missing or older than the release fails the gate."""

    def test_the_figure_exists_and_is_valid(self):
        figure = disk_need.load(disk_need.FIGURE_FILE)
        self.assertGreater(figure['bytes']['run'], 10 * GIB)
        self.assertGreater(figure['bytes']['builder_image'], 0)
        self.assertTrue(figure.get('build'))

    def test_the_figure_is_not_older_than_the_release(self):
        figure = disk_need.load(disk_need.FIGURE_FILE)
        measured, _ = disk_need.release_version(figure['version'])
        version, kind = disk_need.release_version((ROOT / 'VERSION').read_text(encoding='utf-8'))
        if kind != 'dev':
            # a release candidate or final ships a figure of its own release's builds
            self.assertEqual(measured, version, 'ship a figure of this release: tools/disk_need.py ship RUN')
        else:
            pin = json.loads((ROOT / 'tools' / 'previous-release.json').read_text(encoding='utf-8'))
            previous, _ = disk_need.release_version(pin['version'])
            self.assertGreaterEqual(measured, previous, 'the figure is older than the previous release')
            self.assertLessEqual(measured, version)

    def test_the_figure_ships(self):
        files = json.loads((ROOT / 'tools' / 'release-files.json').read_text(encoding='utf-8'))
        for name in ('config/disk-footprint.json', 'tools/disk_need.py', 'tests/test_disk_need.py'):
            self.assertIn(name, files)


class NeedTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.workspace = Path(temp.name) / 'workspace'
        self.workspace.mkdir()
        self.config = {'min_free_gib': 0, 'margin_percent': 30}

    def rows(self, free, **kwargs):
        with patch.object(disk_need, 'free_bytes', return_value=free):
            return disk_need.plan(self.workspace, figure=kwargs.pop('figure', FIGURE), mine=None, config=self.config,
                                  **kwargs)

    def test_a_fresh_workspace_needs_the_figure_plus_the_margin(self):
        rows = self.rows(10 ** 15)
        self.assertEqual(len(rows), 1)                         # everything on one file system
        self.assertEqual(rows[0]['figure'], 20 * GIB)          # run, scratch, cache, pool (no Docker parts)
        self.assertEqual(rows[0]['need'], int(20 * GIB * 1.3))
        self.assertEqual(disk_need.problems(rows, self.config), [])
        short = self.rows(20 * GIB)
        self.assertEqual(len(disk_need.problems(short, self.config)), 1)
        self.assertIn('GiB needed', disk_need.problems(short, self.config)[0])

    def test_never_below_the_minimum(self):
        self.config['min_free_gib'] = 35
        self.assertEqual(self.rows(10 ** 15)[0]['need'], 35 * GIB)

    def test_a_workspace_with_a_passing_build_reuses_its_cache_and_pool(self):
        (self.workspace / 'cache' / 'asset-pool-v1').mkdir(parents=True)
        run = self.workspace / 'build' / 'old'
        run.mkdir(parents=True)
        (run / 'build-state.json').write_text('{"status": "failed"}', encoding='utf-8')
        self.assertEqual(self.rows(10 ** 15)[0]['present'], 0)
        (run / 'build-state.json').write_text('{"status": "passed"}', encoding='utf-8')
        row = self.rows(10 ** 15)[0]
        self.assertEqual(row['present'], 8 * GIB)
        self.assertEqual(row['need'], int(12 * GIB * 1.3))

    def test_the_docker_game_data_copy_counts(self):
        rows = self.rows(10 ** 15, adds={'game_data': 3 * GIB}, extra={'game_data': self.workspace})
        self.assertEqual(rows[0]['figure'], 23 * GIB)

    def test_the_figure_is_the_larger_of_shipped_and_local(self):
        shipped = Path(self.workspace) / 'shipped.json'
        shipped.write_text(json.dumps(FIGURE), encoding='utf-8')
        run = self.workspace / 'build' / 'mine'
        run.mkdir(parents=True)
        mine = dict(FIGURE, bytes=dict(FIGURE['bytes'], run=12 * GIB, pool=1 * GIB), stages={'chim': {'workspace': GIB}})
        (run / disk_need.RECORD).write_text(json.dumps(mine), encoding='utf-8')
        merged, local = disk_need.reference(self.workspace, shipped)
        self.assertEqual(local['bytes']['run'], 12 * GIB)
        self.assertEqual(merged['bytes']['run'], 12 * GIB)
        self.assertEqual(merged['bytes']['pool'], 5 * GIB)
        self.assertEqual(merged['stages']['chim']['workspace'], 4 * GIB)

    def test_docker_image_build_need(self):
        problems, need, free = disk_need.docker_problems(str(self.workspace), FIGURE, self.config, build=False)
        self.assertEqual(need, int(2 * GIB * 1.3))
        problems, need, free = disk_need.docker_problems(str(self.workspace), FIGURE, self.config, build=True)
        self.assertEqual(need, int(24 * GIB * 1.3))
        with patch.object(disk_need, 'free_bytes', return_value=GIB):
            self.assertEqual(len(disk_need.docker_problems(str(self.workspace), FIGURE, self.config)[0]), 1)
        self.assertEqual(disk_need.docker_problems(None, FIGURE, self.config)[2], None)   # not visible: no claim


class WatchTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.workspace = Path(temp.name) / 'workspace'
        self.run = self.workspace / 'build' / 'run-1'
        self.run.mkdir(parents=True)
        (self.workspace / 'cache' / 'asset-pool-v1').mkdir(parents=True)
        self.metadata = {'schema': 'amiwind-build-receipt-v1', 'stage': 'aga', 'runtime_version': '0.0.53-dev1',
                         'storage_pool_dir': str(self.workspace / 'cache' / 'asset-pool-v1'), 'data_files': None}

    def watch(self, figure=FIGURE):
        watch = disk_need.Watch(self.run, self.metadata, interval=0.05, config={'min_free_gib': 0, 'margin_percent': 30},
                                figure=figure)
        self.addCleanup(watch.stop.set)
        return watch

    def test_a_stage_with_too_little_room_for_its_last_figure_stops_before_it_starts(self):
        watch = self.watch()
        with patch.object(disk_need, 'free_bytes', return_value=4 * GIB):
            with self.assertRaises(disk_need.DiskShort) as caught:
                watch.before('chim')
            self.assertIn('chim', str(caught.exception))
            watch.before('terrain')            # no figure of its own: the entry check covered the build

    def test_a_passing_build_writes_its_figure(self):
        free = [100 * GIB]
        with patch.object(disk_need, 'free_bytes', side_effect=lambda path: free[0]):
            watch = disk_need.Watch(self.run, self.metadata, interval=3600,
                                    config={'min_free_gib': 0, 'margin_percent': 30}, figure=FIGURE)
            self.addCleanup(watch.stop.set)
            watch.before('terrain')
            (self.run / 'out.bin').write_bytes(b'x' * 100000)
            free[0] = 90 * GIB                   # the stage's scratch at its peak
            watch._sample()
            free[0] = 95 * GIB                   # what stays: run files, cache and pool entries
            watch.finished('terrain')
            run_bytes = disk_need.tree_bytes([self.run])
            figure = watch.close({'status': 'passed', 'runtime_version': '0.0.53-dev1'})
        written = disk_need.load(self.run / disk_need.RECORD)
        self.assertEqual(written, figure)
        self.assertEqual(written['bytes']['run'], run_bytes)
        self.assertGreaterEqual(run_bytes, 100000)
        self.assertEqual(written['bytes']['scratch'], 5 * GIB)
        self.assertEqual(written['bytes']['cache'], 5 * GIB - run_bytes)    # the growth less the run's new files
        self.assertEqual(written['stages']['terrain'], {'workspace': 10 * GIB})
        self.assertEqual(written['version'], '0.0.53-dev1')

    def test_a_failed_build_writes_none(self):
        watch = self.watch()
        self.assertIsNone(watch.close({'status': 'failed'}))
        self.assertFalse((self.run / disk_need.RECORD).exists())

    def test_the_profiling_session_carries_the_watch(self):
        import build_profile
        with patch.dict(os.environ, NO_SWITCH), patch.object(disk_need, 'Watch') as made:
            session = build_profile.start(self.run, [], dict(self.metadata, profile=False))
            self.assertIsInstance(session, disk_need.WatchedSession)
            made.return_value.before.side_effect = disk_need.DiskShort('short')
            with self.assertRaises(OSError):
                session.command(1, 'chim', ['true'], 1)
        with patch.dict(os.environ, NO_SWITCH):
            for other in ({'stage': 'terrain'}, {'npc_gallery': 'asset-free'}, {'schema': None}):
                plain = build_profile.start(self.run, [], dict(self.metadata, profile=False, **other))
                self.assertNotIsInstance(plain, disk_need.WatchedSession)

    def test_ship_copies_a_passing_figure(self):
        record = dict(FIGURE, bytes=dict(FIGURE['bytes'], builder_image=0))
        (self.run / disk_need.RECORD).write_text(json.dumps(record), encoding='utf-8')
        target = self.workspace / 'shipped.json'
        target.write_text(json.dumps(FIGURE), encoding='utf-8')
        shipped = disk_need.ship(self.run, target)
        self.assertEqual(shipped['bytes']['builder_image'], 2 * GIB)    # kept from the earlier figure
        self.assertEqual(disk_need.load(target)['build'], 'b')


class FirstStepTests(unittest.TestCase):
    """The check runs before anything a build does: the entry (build.sh, build.cmd, the build inside Docker), the
    builder image build and the game data copy."""

    def test_build_py_checks_right_after_reading_the_options(self):
        text = (ROOT / 'tools' / 'build.py').read_text(encoding='utf-8')
        at = text.index("__import__('disk_need').entry(args, p, storage_pool_dir)")
        self.assertLess(text.index('args = p.parse_args(argv)'), at)
        for later in ('retired_flags.check(args)', 'clean_build.configure_clean(',
                      'accepted = setup(args, argv, interactive=',
                      'require_previous_release(ROOT, VERSION)', 'build_preflight.run(args.workspace',
                      '            execute(steps, run, metadata)\n'):
            self.assertLess(at, text.index(later), later)

    def test_the_docker_image_build_checks_first(self):
        text = (ROOT / 'tools' / 'build_docker.py').read_text(encoding='utf-8')
        self.assertLess(text.index('disk_need.docker_problems('), text.index("['build', '--progress=plain'"))

    def test_the_game_data_copy_checks_first(self):
        text = (ROOT / 'tools' / 'run_docker.py').read_text(encoding='utf-8')
        self.assertIn('disk_need.docker_volume_check(', text)
        self.assertLess(text.index('check_space(disk_need.tree_bytes([data]))'), text.index('stage_inputs(\n'))
        self.assertLess(text.index('            check_space()\n'), text.index("['create', '--name'"))

    def test_entry_stops_a_short_build_and_skips_setup_modes(self):
        import argparse
        parser = argparse.ArgumentParser()
        with tempfile.TemporaryDirectory() as temp:
            args = argparse.Namespace(stage='aga', workspace=Path(temp), dry_run=False)
            with patch.dict(os.environ, NO_SWITCH), patch.object(disk_need, 'free_bytes', return_value=GIB), \
                    patch.object(disk_need, 'shipped', return_value=FIGURE):
                with self.assertRaises(SystemExit) as caught, patch('sys.stderr'), patch('sys.stdout'):
                    disk_need.entry(args, parser)
                self.assertEqual(caught.exception.code, 1)
                for mode in ('dry_run', 'plan', 'check', 'install_dependencies'):
                    disk_need.entry(argparse.Namespace(stage='aga', workspace=Path(temp), **{mode: True}), parser)
                disk_need.entry(argparse.Namespace(stage='terrain', workspace=Path(temp)), parser)

    def test_the_build_guides_state_the_need(self):
        for name in ('docs/LINUX_BUILD.md', 'docs/WINDOWS_BUILD.md', 'docs/DOCKER_BUILD.md',
                     'docs/DOCKER_BUILD_ROADMAP.md'):
            text = (ROOT / name).read_text(encoding='utf-8')
            self.assertIn('config/disk-footprint.json', text, name)
            self.assertIn('min_free_gib', text, name)


if __name__ == '__main__':
    unittest.main()
