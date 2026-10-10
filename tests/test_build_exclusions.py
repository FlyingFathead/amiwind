# SPDX-License-Identifier: GPL-3.0-only
"""Quick test builds: --exclude GROUP and its aliases (tools/build_exclusions.py).

One table says what each group skips. These tests fail when an alias stops
meaning the same as the general form, when a default build leaves anything
out, when a group is added without its alias or table row, when the stage
cache key ignores the exclusion set, when a release candidate or final accepts
an exclusion, or when a group would remove dressing, flora or anything else
with collision that NPCs or the player walk into (owner rule).
"""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]

import build  # noqa: E402
import build_exclusions as ex  # noqa: E402
from build_parallel import stage_dependencies  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))  # tests/ (env_guard) when run as a file
import env_guard  # noqa: E402

TOOLS = {name: '/tools/' + name for name in ('qbsp', 'vis', 'light', 'qcc', 'ffmpeg', 'xdftool', 'rdbtool')}
RUN = Path('/private/run')
FULL_BUILD_GROUPS = [name for name, row in ex.GROUPS.items() if not row.get('area_builds')]


def steps(*extra):
    args = build.parser().parse_args(list(extra))
    args.data_files = Path('/owned/Data Files')
    args.sdk = Path('/sdk')
    with patch('build_jobs.auto_jobs', return_value=4):
        return build.commands(args, TOOLS, RUN)


def option(command, flag):
    return command[command.index(flag) + 1] if flag in command else None


class GroupTable(unittest.TestCase):
    def test_every_group_has_one_alias_and_a_complete_row(self):
        flags = {action.option_strings[0]: action for action in build.parser()._actions
                 if action.dest in ('exclude', 'exclude_unreferenced')}
        self.assertIn('--exclude', flags)
        for name, row in ex.GROUPS.items():
            with self.subTest(group=name):
                for key in ('label', 'notice', 'alias', 'skip', 'options', 'placements', 'in_game', 'saves'):
                    self.assertIn(key, row)
                self.assertEqual(row['alias'], '--exclude-' + name)
                self.assertIn(row['alias'], flags)
                # --exclude-unreferenced takes an optional group list (all when none is given).
                self.assertEqual(flags[row['alias']].const, 'all' if name == 'unreferenced' else name)
                self.assertTrue(flags[row['alias']].help.startswith('DEBUGGING ONLY'))
        # Every alias flag belongs to a group: no stray --exclude-* option.
        self.assertEqual(sorted(f for f in flags if f != '--exclude'), sorted(ex.alias_flags()))

    def test_requested_aliases(self):
        for flag in ('--exclude-video', '--exclude-music', '--exclude-voice', '--exclude-npc-gallery',
                     '--exclude-interiors', '--exclude-harvest', '--exclude-unreferenced'):
            self.assertIn(flag, ex.alias_flags())

    def test_table_stages_exist_in_the_default_plan(self):
        names = {name for name, _ in steps()}
        for name, row in ex.GROUPS.items():
            for stage in (*row['skip'], *row['options']):
                with self.subTest(group=name, stage=stage):
                    self.assertIn(stage, names)
        for stage in ex.COLLISION_STAGES:
            self.assertIn(stage, names)

    def test_no_group_removes_collision_content(self):
        """Owner rule: dressing, clutter, props, flora and other collision content stay in."""
        for name, row in ex.GROUPS.items():
            with self.subTest(group=name):
                self.assertNotIn(name, ex.REFUSED)
                touched = set(row['skip']) | set(row['options'])
                self.assertFalse(touched & set(ex.COLLISION_STAGES), touched)
                for stage_options in row['options'].values():
                    self.assertFalse(set(stage_options) & set(ex.COLLISION_OPTIONS))
                for word in ('dressing', 'clutter', 'prop', 'flora', 'tree', 'grass', 'scenery', 'collision'):
                    self.assertNotIn(word, name)
        for name in ('dressing', 'clutter', 'props', 'flora'):
            self.assertIn(name, ex.REFUSED)

    def test_refused_and_unknown_groups_stop_with_the_reason(self):
        for name in ex.REFUSED:
            with self.subTest(group=name), self.assertRaises(ValueError) as error:
                ex.parse([name])
            self.assertIn('refused', str(error.exception))
        with self.assertRaises(ValueError) as error:
            ex.parse(['videos'])
        self.assertIn('unknown group', str(error.exception))
        with self.assertRaises(ValueError) as error:
            ex.parse(['flora'])
        self.assertIn('--no-tree-sprites', str(error.exception))
        with self.assertRaises(ValueError) as error:
            ex.parse(['dressing'])
        self.assertIn('--skip-dressing', str(error.exception))

    def test_marker_text_fits_the_engine(self):
        text = ex.marker_text(list(ex.GROUPS))
        lines = text.splitlines()
        self.assertEqual(lines[0], ex.MARKER_MAGIC)
        self.assertTrue(text.endswith('\n') and '\r' not in text)
        self.assertLessEqual(len(ex.GROUPS), ex.MAX_GROUPS)
        for line, (name, row) in zip(lines[1:], ex.GROUPS.items()):
            self.assertEqual(line, name + ' ' + row['notice'])
            self.assertLessEqual(len(name), ex.NAME_CHARS)
            self.assertLessEqual(len(row['notice']), ex.NOTICE_CHARS)
        # The engine's buffers (aw_excluded.c) match the table's limits.
        source = (ROOT / 'engine/aga/src/aw_excluded.c').read_text(encoding='utf-8')
        self.assertIn(f'#define EXCLUDED_MAX {ex.MAX_GROUPS}', source)
        self.assertIn(f'#define EXCLUDED_NAME {ex.NAME_CHARS + 1}', source)
        self.assertIn(f'#define EXCLUDED_NOTICE {ex.NOTICE_CHARS + 1}', source)
        self.assertIn('"AWX1\\n"', source)
        self.assertIn('"excluded-content.txt"', source)
        self.assertEqual(ex.MARKER, 'excluded-content.txt')


class Plans(unittest.TestCase):
    def test_default_build_excludes_nothing(self):
        default = steps()
        image = dict(default)['image']
        self.assertNotIn('--exclude', image)
        self.assertEqual(option(image, '--music'), str(RUN / 'music'))
        for _, command in default:
            for flag in ('--no-videos', '--no-voices', '--no-movie', '--no-rooms', '--reference-closure'):
                self.assertNotIn(flag, command)
        args = build.parser().parse_args([])
        self.assertEqual(ex.fold(args), [])
        self.assertEqual(ex.record([])['summary'], 'complete (nothing excluded)')

    def test_alias_equals_the_general_form(self):
        for name in FULL_BUILD_GROUPS:
            with self.subTest(group=name):
                self.assertEqual(steps(ex.GROUPS[name]['alias']), steps('--exclude', name))
        combined = steps('--exclude', 'music,video', '--exclude-voice')
        self.assertEqual(combined, steps('--exclude-video', '--exclude-music', '--exclude-voice'))
        self.assertEqual(option(dict(combined)['image'], '--exclude'), 'video,music,voice')  # table order

    def test_older_switches_are_the_same_groups(self):
        self.assertEqual(steps('--exclude', 'npc-gallery'), steps('--no-npc-gallery'))
        self.assertEqual(steps('--exclude-harvest'), steps('--no-harvest'))
        args = build.parser().parse_args(['--no-npc-gallery', '--no-harvest'])
        self.assertEqual(ex.fold(args), ['npc-gallery', 'harvest'])

    def test_each_group_skips_exactly_its_table_row(self):
        default = dict(steps())
        for name in FULL_BUILD_GROUPS:
            row = ex.GROUPS[name]
            with self.subTest(group=name):
                plan = steps('--exclude', name)
                quick = dict(plan)
                self.assertEqual(set(default) - set(quick), set(row['skip']))
                self.assertEqual(set(quick) - set(default), set())
                for stage, extra in row['options'].items():
                    self.assertEqual(quick[stage][-len(extra):], extra)
                    self.assertEqual(quick[stage][:-len(extra)], default[stage])
                self.assertEqual(option(quick['image'], '--exclude'), name)
                # The scheduler accepts the plan: no stage waits for a skipped one.
                dependencies = stage_dependencies(plan, ex.skipped_stages([name]))
                if name == 'music':  # without the plan's skipped set the scheduler refuses the gap
                    with self.assertRaises(ValueError):
                        stage_dependencies(plan)
                for stage, deps in dependencies.items():
                    self.assertFalse(set(deps) & set(row['skip']), (stage, deps))

    def test_music_leaves_the_image_without_a_soundtrack(self):
        image = dict(steps('--exclude-music'))['image']
        self.assertNotIn('--music', image)
        self.assertNotIn('music', stage_dependencies(steps('--exclude-music'), {'music'})['image'])
        from build_parallel import plan_skipped
        self.assertEqual(plan_skipped({'excluded_content': ex.record(['music', 'video'])}), {'music'})
        self.assertEqual(plan_skipped({}), set())

    def test_placement_groups_record_the_loss_with_the_quick_test_reason(self):
        image = dict(steps('--exclude', 'interiors'))['image']
        if '--entity-baseline' in image:
            self.assertEqual(option(image, '--accept-entity-loss'), 'quick test build, excluded: interiors')
        image = dict(steps('--exclude', 'video'))['image']
        self.assertNotIn('--accept-entity-loss', image)
        image = dict(steps('--exclude', 'interiors', '--accept-entity-loss', 'my reason'))['image']
        self.assertEqual(image.count('--accept-entity-loss'), 1)  # the owner's own reason wins
        self.assertEqual(option(image, '--accept-entity-loss'), 'my reason')

    def test_labels(self):
        groups = ['video', 'music']
        self.assertEqual(ex.summary(groups), 'quick test build, excluded: video, music')
        self.assertEqual(ex.folder_tag(groups), 'quick-test-video-music')
        record = ex.record(groups)
        self.assertEqual(record['groups'], groups)
        self.assertEqual(record['marker'], 'id1/excluded-content.txt')
        self.assertEqual(record['details']['music']['skipped_stages'], ['music'])


@env_guard.isolated  # build.main exports AMIWIND_* switches (TEST-ENV-LEAK-HULL-33)
class Refusals(unittest.TestCase):
    def resolve(self, version, *extra):
        return ex.resolve(build.parser().parse_args(list(extra)), version)

    def test_release_candidates_and_finals_refuse_every_exclusion(self):
        for version in ('0.0.33', '0.0.33-rc1'):
            for extra in (['--exclude', 'video'], ['--exclude-music'], ['--no-npc-gallery'], ['--no-harvest']):
                with self.subTest(version=version, extra=extra), self.assertRaises(ValueError) as error:
                    self.resolve(version, *extra)
                self.assertIn('release candidate or final', str(error.exception))
        self.assertEqual(self.resolve('0.0.33-dev1', '--exclude', 'video,music'), ['video', 'music'])
        self.assertEqual(self.resolve('0.0.33'), [])

    def test_area_groups_need_an_area_build(self):
        with self.assertRaises(ValueError) as error:
            self.resolve('0.0.33-dev1', '--exclude-unreferenced')
        self.assertIn('needs an area build', str(error.exception))
        args = build.parser().parse_args(['--exclude-unreferenced'])
        self.assertEqual(ex.resolve(args, '0.0.33-dev1', area_build=True), ['unreferenced'])

    def test_main_refuses_before_any_work(self):
        with patch.object(build, 'VERSION', '0.0.33'), contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()) as err, self.assertRaises(SystemExit) as stop:
            build.main(['--exclude-video', '--host-plan'])
        self.assertEqual(stop.exception.code, 1)
        self.assertIn('release candidate or final', err.getvalue())
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err, \
                self.assertRaises(SystemExit):
            build.main(['--exclude', 'flora', '--host-plan'])
        self.assertIn('refused', err.getvalue())

    def test_image_step_refuses_exclusions_for_releases(self):
        import build_aga
        from types import SimpleNamespace
        args = SimpleNamespace(exclude='video,music')
        self.assertEqual(build_aga.excluded_groups(args), ['video', 'music'])
        self.assertIn('--exclude video,music', build_aga.image_waivers(args))
        self.assertEqual(build_aga.image_waivers(SimpleNamespace()), [])
        from project_version import require_private_test_version
        with self.assertRaises(ValueError):
            require_private_test_version('0.0.33', build_aga.image_waivers(args))


class CacheKey(unittest.TestCase):
    def fingerprints(self, groups):
        import build_cache
        plan = steps(*(['--exclude', ','.join(groups)] if groups else []))
        metadata = {'tools': TOOLS, 'excluded_content': ex.record(groups)}
        index = build_cache.SourceIndex()
        return build_cache.fingerprint_steps(plan, RUN, metadata, index)

    def test_the_stage_key_changes_with_the_exclusions_it_follows(self):
        plain, plain_parts, _, _ = self.fingerprints([])
        quick, quick_parts, _, _ = self.fingerprints(['video', 'voice'])
        for stage in ('media', 'intro', 'image'):
            self.assertNotEqual(plain[stage], quick[stage], stage)
            self.assertIn('excluded_content', quick_parts[stage])
        # A stage no group touches keeps its key (development reuse still works for it)...
        for stage in ('setup', 'terrain', 'world-survey', 'engine', 'music'):
            self.assertEqual(plain[stage], quick[stage], stage)
            self.assertNotIn('excluded_content', quick_parts[stage])
        # ...and a complete build's keys carry no exclusion component at all.
        for stage, parts in plain_parts.items():
            self.assertNotIn('excluded_content', parts, stage)
        other, _, _, _ = self.fingerprints(['video'])
        self.assertNotEqual(other['media'], quick['media'])


class Media(unittest.TestCase):
    def fake_data(self, root):
        data = root / 'Data Files'
        for relative in ('Sound/Vo/d/m/hlo_a.mp3', 'Sound/Vo/d/m/hlo_b.mp3', 'Sound/Fx/door.wav', 'Video/bm_frost.bik',
                         'Music/Explore/a.mp3'):
            path = data / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'x' * 10)
        return data  # no archives: loose files only (masters are not read: lookups is patched)

    def run_prepare(self, **options):
        import prepare_media_assets as media
        converted = []

        def convert(task):
            record, output, ffmpeg = task[:3]     # (+ the per-file cache, None here)
            converted.append(record['source'])
            return {'source': record['source'], 'category': 'voices' if media.is_voice(record['source']) else 'effects',
                    'status': 'included', 'path': media.sound_output(record['source']), 'sha256': '0', 'bytes': 1}, 'off'
        with tempfile.TemporaryDirectory() as tmp:
            data = self.fake_data(Path(tmp))
            with patch.object(media, 'convert_sound_cached', side_effect=convert), \
                    patch.object(media, 'lookups', return_value={'sounds': [], 'voiced_dialogue': []}), \
                    patch.object(media, 'resolve_data_files', side_effect=lambda p: Path(p)), \
                    contextlib.redirect_stdout(io.StringIO()):
                report = media.prepare(data, Path(tmp) / 'media', jobs=1, **options)
        return sorted(converted), report

    def test_voices_and_videos_can_be_left_out(self):
        everything, report = self.run_prepare(videos=False)
        self.assertEqual(everything, ['sound/fx/door.wav', 'sound/vo/d/m/hlo_a.mp3', 'sound/vo/d/m/hlo_b.mp3'])
        self.assertEqual(report['excluded'], ['videos'])
        self.assertFalse([r for r in report['entries'] if r['category'] == 'videos'])
        effects, report = self.run_prepare(videos=False, voices=False)
        self.assertEqual(effects, ['sound/fx/door.wav'])
        self.assertEqual(report['excluded'], ['videos', 'voices'])
        self.assertEqual(report['left_out']['voices'], 2)

    def test_reference_closure_keeps_only_listed_voices(self):
        closure = {'groups': ['voice'], 'cells': ['Balmora'], 'voice_files': ['vo/d/m/hlo_a.mp3']}
        kept, report = self.run_prepare(videos=False, closure=closure)
        self.assertEqual(kept, ['sound/fx/door.wav', 'sound/vo/d/m/hlo_a.mp3'])
        self.assertEqual(report['left_out']['voices'], 1)
        self.assertEqual(report['reference_closure']['groups'], ['voice'])

    def test_staged_catalogue_without_music_passes_the_media_gate(self):
        import prepare_media_assets as media
        import build_aga
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'media/id1').mkdir(parents=True)
            report = {'format': 'AWMEDIA1', 'excluded': ['videos', 'voices'], 'entries': [],
                      'lookups': {'sounds': [], 'voiced_dialogue': []}, 'categories': {}}
            (root / 'media/media-coverage.json').write_text(json.dumps(report))
            (root / 'media/source-inventory.json').write_text(json.dumps({'assets': {'music/explore/a.mp3': {'file': 'x'}}}))
            (root / 'id1').mkdir()
            with contextlib.redirect_stdout(io.StringIO()):
                staged = media.stage_catalogue(root / 'media', root / 'id1', {'tracks': []}, excluded=['music'])
            self.assertEqual(staged['excluded'], ['music', 'videos', 'voices'])
            self.assertTrue(build_aga.require_complete_media_outputs(staged))
            with contextlib.redirect_stdout(io.StringIO()):
                complete = media.stage_catalogue(root / 'media', root / 'id1', {'tracks': []})
            with self.assertRaises(ValueError):  # a soundtrack the image should have had
                build_aga.require_complete_media_outputs(complete)


class AlwaysIncluded(unittest.TestCase):
    """The shared sky, palette, fonts and menus survive every exclusion (owner rule)."""

    def test_no_group_or_combination_skips_a_protected_stage(self):
        import itertools
        names = FULL_BUILD_GROUPS
        default = {name for name, _ in steps()}
        for size in range(1, len(names) + 1):
            for combo in itertools.combinations(names, size):
                with self.subTest(groups=combo):
                    plan = {name for name, _ in steps('--exclude', ','.join(combo))}
                    for stage in ex.PROTECTED_STAGES:
                        self.assertIn(stage, default)
                        self.assertIn(stage, plan)
        for name, row in ex.GROUPS.items():
            self.assertFalse(set(row['skip']) & set(ex.PROTECTED_STAGES), name)

    def fixture(self, root, drop=(), sky_bytes=ex.SHARED_SKY_BYTES):
        id1 = Path(root) / 'id1'
        for name in ex.ALWAYS_INCLUDED:
            if name in drop:
                continue
            path = id1 / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'\0' * (sky_bytes if name == ex.SHARED_SKY else 4))
        return id1

    def test_the_image_check_names_every_missing_asset(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1 = self.fixture(tmp)
            maps = {'vf0000': {'_aw_sky_mode': 'exterior', '_aw_sky_asset': 'gfx/aw_shared_sky.lmp'}}
            record = ex.check_always_included(id1, exterior=True, maps=maps)
            self.assertEqual(record['status'], 'passed')
            self.assertIn('gfx/aw_shared_sky.lmp', record['checked'])
            self.assertEqual(record['sky_assets_named_by_maps'], {'gfx/aw_shared_sky.lmp': 1})
        for drop in (['gfx/aw_shared_sky.lmp'], ['gfx/palette.lmp', 'gfx.wad'], ['gfx/magic16.awf']):
            with tempfile.TemporaryDirectory() as tmp, self.subTest(drop=drop):
                id1 = self.fixture(tmp, drop)
                with self.assertRaises(ValueError) as error:
                    ex.check_always_included(id1)
                for name in drop:
                    self.assertIn(name, str(error.exception))
        with tempfile.TemporaryDirectory() as tmp:
            id1 = self.fixture(tmp, ['gfx/aw_shared_sky.lmp'])
            # An interior-only build needs no sky ...
            self.assertEqual(ex.check_always_included(id1, exterior=False)['status'], 'passed')
            # ... unless a map names one.
            with self.assertRaises(ValueError) as error:
                ex.check_always_included(id1, exterior=False, maps={'bm000': {'_aw_sky_asset': 'gfx/aw_shared_sky.lmp'}})
            self.assertIn('named by 1 maps', str(error.exception))
        with tempfile.TemporaryDirectory() as tmp:
            id1 = self.fixture(tmp, sky_bytes=100)
            with self.assertRaises(ValueError) as error:
                ex.check_always_included(id1)
            self.assertIn('not 32768', str(error.exception))

    def test_worldspawn_sky_keys_are_read_from_the_maps(self):
        import struct
        with tempfile.TemporaryDirectory() as tmp:
            maps = Path(tmp)
            entities = b'{\n"classname" "worldspawn"\n"_aw_sky_mode" "exterior"\n"_aw_sky_asset" "gfx/aw_shared_sky.lmp"\n}\n'
            head = bytearray(124)
            struct.pack_into('<iii', head, 0, 29, 124, len(entities))
            (maps / 'vf0000.bsp').write_bytes(bytes(head) + entities)
            (maps / 'notbsp.bsp').write_bytes(b'xx')
            self.assertEqual(ex.worldspawn_sky_keys(maps),
                             {'vf0000': {'_aw_sky_mode': 'exterior', '_aw_sky_asset': 'gfx/aw_shared_sky.lmp'}})

    def test_the_closure_never_filters_them(self):
        import prepare_media_assets as media
        keep, _ = media.closure_filter({'groups': ['voice', 'sounds'], 'voice_files': [], 'sound_files_dropped': []})
        for name in ex.ALWAYS_INCLUDED:
            self.assertTrue(keep(name), name)  # not a media asset: never filtered
        from build_gallery import gallery_filter
        self.assertIsNone(gallery_filter({'groups': ['voice']}))


class MiniWindDefaults(unittest.TestCase):
    """A MiniWind build leaves the videos out and builds only the voices and NPC records Balmora
    references (owner decision after MiniWind #2 shipped all 17 videos and 6,447 voices). Music,
    the included NPCs' whole dialogue pool and the always-included assets stay."""

    def plan(self, *extra):
        import build_font_options as options
        args = build.parser().parse_args(['--miniwind', *extra])
        args.data_files, args.sdk, args.workspace = Path('/owned/Data Files'), Path('/sdk'), Path('/private/ws')
        with patch.object(build, 'VERSION', '0.0.33-dev1'), contextlib.redirect_stdout(io.StringIO()):
            build.configure_miniwind(args)
            ex.miniwind_defaults(args)
            ex.resolve(args, '0.0.33-dev1', area_build=True)
            build.configure_area_closure(args)
        args.builder_options = options.resolve_builder(args)
        with patch('build_jobs.auto_jobs', return_value=4):
            return dict(build.commands(args, TOOLS, RUN)), args

    def test_defaults(self):
        plan, args = self.plan()
        self.assertEqual(args.exclude_groups, ['video', 'unreferenced'])
        self.assertEqual(args.unreferenced_groups, ['npcs', 'voice'])
        self.assertEqual(option(plan['image'], '--exclude'), 'video,unreferenced')
        self.assertEqual(plan['media'][-3:-1], ['--no-videos', '--reference-closure'])
        self.assertIn('--no-movie', plan['intro'])
        closure = plan[ex.CLOSURE_STAGE]
        self.assertEqual(option(closure, '--groups'), 'npcs,voice')
        self.assertIn('cell:-3,-2', closure)
        self.assertIn("interior:Balmora, Caius Cosades' House", closure)
        # Music stays: its stage runs and the image takes the soundtrack.
        self.assertIn('music', plan)
        self.assertIn('--music', plan['image'])
        self.assertNotIn('--no-voices', plan['media'])  # the included NPCs' dialogue pool stays
        # The shared sky and the other always-included assets: no protected stage is skipped.
        for stage in ex.PROTECTED_STAGES:
            if stage in ('scene', 'intro', 'census', 'engine', 'image'):
                self.assertIn(stage, plan)

    def test_the_exterior_scope_closes_over_the_exterior_only(self):
        plan, args = self.plan('--miniwind-scope', 'exterior')
        self.assertTrue(all(cell.startswith('cell:') for cell in args.closure_cells))
        self.assertEqual(len(args.closure_cells), 9)

    def test_opt_outs(self):
        plan, args = self.plan('--with-video', '--exclude-unreferenced', 'none')
        self.assertEqual(args.exclude_groups, [])
        self.assertNotIn('--exclude', plan['image'])
        self.assertNotIn(ex.CLOSURE_STAGE, plan)
        plan, args = self.plan('--exclude-unreferenced', 'voice')
        self.assertEqual(args.unreferenced_groups, ['voice'])
        self.assertEqual(option(plan['image'], '--exclude'), 'video,unreferenced')

    def test_full_builds_are_unaffected(self):
        args = build.parser().parse_args([])
        self.assertEqual(ex.miniwind_defaults(args), [])
        self.assertIsNone(getattr(args, 'exclude', None))
        self.assertIsNone(args.exclude_unreferenced)


class ImageMarkers(unittest.TestCase):
    def test_markers_written_only_for_quick_test_builds(self):
        import build_aga
        with tempfile.TemporaryDirectory() as tmp:
            boot = Path(tmp)
            (boot / 'id1').mkdir()
            with contextlib.redirect_stdout(io.StringIO()):
                record = build_aga.stage_excluded_content(boot, ['video', 'interiors'])
            marker = boot / 'id1' / ex.MARKER
            self.assertEqual(marker.read_bytes(), b'AWX1\nvideo the intro movies\ninteriors the interiors\n')
            self.assertIn('quick test build, excluded: video, interiors',
                          (boot / ex.ROOT_MARKER).read_text(encoding='ascii'))
            self.assertEqual(record['groups'], ['video', 'interiors'])
            record = build_aga.stage_excluded_content(boot, [])  # a stale marker from the scene goes
            self.assertFalse(marker.exists() or (boot / ex.ROOT_MARKER).exists())
            self.assertEqual(record['groups'], [])

    def test_engine_lists_the_marker_source(self):
        makefile = (ROOT / 'engine/aga/Makefile').read_text(encoding='utf-8')
        self.assertIn('aw_excluded.c', makefile)
        files = json.loads((ROOT / 'tools/release-files.json').read_text(encoding='utf-8'))
        for path in ('engine/aga/src/aw_excluded.c', 'tools/build_exclusions.py', 'tests/aga_excluded_test.c',
                     'tests/test_build_exclusions.py'):
            self.assertIn(path, files)

    def test_stage_options_reach_the_stage_parsers(self):
        for script, flags in (('prepare_media_assets.py', ('--no-videos', '--no-voices', '--reference-closure')),
                              ('prepare_intro.py', ('--no-movie',)),
                              ('prepare_area.py', ('--no-rooms',)),
                              ('prepare_balmora_interiors.py', ('--no-rooms',))):
            source = (ROOT / 'tools' / script).read_text(encoding='utf-8')
            for flag in flags:
                with self.subTest(script=script, flag=flag):
                    self.assertIn(f"'{flag}'", source)
        for name, row in ex.GROUPS.items():
            for stage, extra in row['options'].items():
                script = Path(dict(steps())[stage][1]).name
                source = (ROOT / 'tools' / script).read_text(encoding='utf-8')
                for flag in extra:
                    self.assertIn(f"'{flag}'", source, (name, stage, flag))


if __name__ == '__main__':
    unittest.main()
