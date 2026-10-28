# SPDX-License-Identifier: GPL-3.0-only
"""Build recipes (tools/build_recipe.py, tools/build.py --recipe / --save-recipe, docs/BUILD_RECIPES.md).

The recipe schema and its rules, the round trip save -> load -> the same options, versions (same: quiet; a newer
builder warns and lists the changed options; an older builder refuses and names the options it does not know),
retired options (refused in developer mode, only --override lets one through), command-line precedence and its
record, input SHA-256s, the unverified warning, the receipts, the MiniWind presets as recipes (every preset gives
the options its earlier table row gave), the master builder's --recipe, the example recipes and the option-change
table.
"""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools'), str(ROOT / 'tests')]
import build  # noqa: E402
import build_recipe as br  # noqa: E402
import miniwind_presets as mp  # noqa: E402

DEV = '0.0.36-dev3'

# The MiniWind preset table as it was before the presets became recipes (config/miniwind-presets.json, format 1).
OLD_PRESETS = [
    {'name': 'balmora', 'description': 'Balmora: exterior and interiors', 'scope': 'full', 'start': None,
     'exclude': [], 'unreferenced': 'voice,npcs', 'character': None, 'skip_census': None, 'boot_commands': []},
    {'name': 'balmora-exterior', 'description': 'Balmora exterior (map only)', 'scope': 'exterior', 'start': None,
     'exclude': [], 'unreferenced': 'voice,npcs', 'character': None, 'skip_census': None, 'boot_commands': []},
    {'name': 'vivec-arena-pit', 'description': 'Vivec Arena Pit: combat test', 'scope': 'full',
     'start': 'interior:Vivec, Arena Pit', 'exclude': ['npc-gallery'], 'unreferenced': 'voice,npcs',
     'character': None, 'skip_census': None, 'boot_commands': []},
    # project decision 2026-10-11 09:55: the Arena preset starts in the whole-city frame
    {'name': 'vivec-arena-chim', 'description': 'Vivec on CHIM (whole city) from the Arena arrival', 'scope': 'full',
     'start': 'vivec_city', 'exclude': ['npc-gallery'], 'unreferenced': 'voice,npcs', 'character': None,
     'skip_census': None, 'boot_commands': []},
    # added with the recipes (Vivec stage B, 2026-10-11): all of Vivec in one CHIM frame
    {'name': 'vivec-city-chim', 'description': 'All of Vivec on CHIM, one frame: cantons, Temple, frame edge',
     'scope': 'full', 'start': 'vivec_city', 'exclude': ['npc-gallery'], 'unreferenced': 'voice,npcs', 'character': None,
     'skip_census': None, 'boot_commands': []},
    {'name': 'opening-ship', 'description': 'Opening ship: lantern and ship lighting check', 'scope': 'exterior',
     'start': 'interior:Imperial Prison Ship', 'exclude': ['npc-gallery'], 'unreferenced': 'voice,npcs',
     'character': None, 'skip_census': False, 'boot_commands': []},
    {'name': 'animkit', 'description': 'Animation kit: walk and run with a companion and hostiles',
     'scope': 'exterior', 'start': 'balmora', 'exclude': [], 'unreferenced': 'voice,npcs', 'character': None,
     'skip_census': None, 'boot_commands': ['dbg companion test', 'dbg combat on']},
]


def recipe(options=None, inputs=(), written=None, checked=None, name='test'):
    return {'schema': br.SCHEMA, 'name': name, 'description': 'a test recipe', 'options': dict(options or {}),
            'inputs': list(inputs), 'written_with': written, 'checked_with': checked,
            'status': 'verified' if checked else 'unverified'}


def builder_ref(version, run=None):
    record = {'amiwind_version': version, 'chim_version': '0.1.0', 'builder_commit': 'abc1234',
              'date': '2026-10-10 22:00:00 +0300'}
    if run is not None:
        record.update(run=run, result_sha256='c' * 64)
    return record


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        cwd = os.getcwd()
        os.chdir(self.dir)  # relative input paths resolve here
        self.addCleanup(os.chdir, cwd)

    def write(self, document, name='recipe.json'):
        path = self.dir / name
        path.write_text(json.dumps(document, indent=2) + '\n', encoding='utf-8', newline='\n')
        return path

    def load(self, path, *argv, version=DEV, check_files=True):
        argv = ['--recipe', str(path), *argv]
        args = build.parser().parse_args(argv)
        out = io.StringIO()
        record = br.configure(build.parser, args, argv, version, out=out, check_files=check_files)
        args.build_recipe_record = record
        return args, record, out.getvalue()

    def inputs(self):
        cells = self.dir / 'cells.csv'
        cells.write_text('x,y\n-7,2\n', encoding='utf-8', newline='\n')
        status = self.dir / 'progress.json'
        status.write_text('{"format": 1}\n', encoding='utf-8', newline='\n')
        return cells, status


class Schema(Base):
    def test_well_formed_recipes_pass(self):
        self.assertEqual(br.document_errors(recipe({'chim_terrain_hull': 'routed'})), [])
        self.assertEqual(br.document_errors(recipe(written=builder_ref(DEV), checked=builder_ref(DEV, 'run'))), [])

    def test_malformed_recipes_are_refused(self):
        cases = [
            (dict(recipe(), schema='build-recipe-2'), 'expected'),
            ({k: v for k, v in recipe().items() if k != 'options'}, "missing 'options'"),
            (dict(recipe(), name='Bad Name'), 'does not match'),
            (recipe({'workspace': '/x'}), 'not part of a recipe'),
            (recipe({'override': ['legacy-area']}), 'not part of a recipe'),
            (recipe({'Chim-Hull': 1}), 'not an option name'),
            (dict(recipe(), status='verified'), 'status'),
            (recipe({}, [{'option': 'chim_regions_status', 'role': 'x', 'path': 'p', 'sha256': 'a' * 64}]),
             'does not set'),
            (recipe({'a': 1}, [{'option': 'a', 'role': 'x', 'path': 'p', 'sha256': 'short'}]), 'does not match'),
            (dict(recipe(), extra=1), "unexpected 'extra'"),
        ]
        for document, text in cases:
            with self.subTest(text=text):
                errors = br.document_errors(document)
                self.assertTrue(errors)
                self.assertIn(text, ' '.join(errors))

    def test_reading_a_bad_file_is_a_refusal(self):
        path = self.dir / 'bad.json'
        path.write_text('{nope', encoding='utf-8')
        with self.assertRaises(br.RecipeError):
            br.read(path)

    def test_not_in_recipe_names_real_options(self):
        dests = {action.dest for action in build.parser()._actions}
        self.assertEqual(sorted(br.NOT_IN_RECIPE - dests), [])

    def test_version_order(self):
        order = ['0.0.35', '0.0.36-dev1', '0.0.36-dev3', '0.0.36-dev10', '0.0.36-rc1', '0.0.36', '0.1.0-dev1']
        self.assertEqual(sorted(reversed(order), key=br.version_key), order)
        self.assertEqual(br.compare_versions('v0.0.36-dev3', '0.0.36-dev3'), 0)
        with self.assertRaises(br.RecipeError):
            br.version_key('0.0.36-beta')


class RoundTrip(Base):
    def test_save_load_gives_the_same_options(self):
        cells, status = self.inputs()
        libs = self.dir / 'libs'
        libs.mkdir()
        (libs / '68040.library').write_bytes(b'not a real library')
        argv = ['--chim-area', 'balmora', '--chim-area', 'seyda', '--extra-town', 'bcoast_x7y2', '--no-npc-gallery',
                '--chim-regions', '@cells.csv', '--chim-regions', 'seabed', '--chim-regions-status', 'progress.json',
                '--chim-terrain-hull', 'routed', '--chim-terrain-refs', 'on', '--stair-walk', 'all', '--live-logs',
                '--heap-mb', '12', '--no-follow-original-stair-rules', '--skip-census', '--exclude-video',
                '--amiga-libs', 'libs', '--chim-cut-models-over', '512.5']
        args = build.parser().parse_args(argv)
        options = br.effective_options(build.parser, args)
        document = br.effective_document(build.parser, options, DEV, '0.1.0', 'abc1234', 'round-trip', base=self.dir)
        roles = {row['role']: row for row in document['inputs']}
        self.assertEqual(sorted(roles), ['amiga-libs', 'chim-regions-cells', 'chim-regions-status'])
        self.assertEqual(roles['chim-regions-cells']['sha256'], hashlib.sha256(cells.read_bytes()).hexdigest())
        self.assertEqual(roles['amiga-libs']['kind'], 'folder')
        self.assertEqual(document['status'], 'unverified')
        self.assertIsNone(document['checked_with'])
        path = self.dir / 'saved.json'
        br.write(path, document)
        loaded, record, out = self.load(path)
        self.assertEqual(br.effective_options(build.parser, loaded), options)
        self.assertEqual(record['relation'], 'same')
        self.assertEqual([row['status'] for row in record['inputs']], ['ok'] * 3)
        again = br.effective_document(build.parser, br.effective_options(build.parser, loaded), DEV, '0.1.0',
                                      'abc1234', 'round-trip', base=self.dir)
        self.assertEqual(again['options'], document['options'])
        self.assertEqual(br.effective_sha256(again['options'], again['inputs']),
                         br.effective_sha256(document['options'], document['inputs']))

    def test_every_option_default_survives_the_trip(self):
        args = build.parser().parse_args([])
        options = br.effective_options(build.parser, args)
        path = self.write(recipe(options))
        loaded, _, _ = self.load(path)
        self.assertEqual(br.effective_options(build.parser, loaded), options)
        self.assertEqual(options['chim_frame_ext'], 'chim')  # CHIM frame maps are .chim; bsp is the old method

    def test_from_flags_command_prints_a_recipe(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(br.main(['from-flags', '--name', 'cli', '--', '--chim-terrain-hull', 'compiled']), 0)
        document = json.loads(out.getvalue())
        self.assertEqual(br.document_errors(document), [])
        self.assertEqual(document['options']['chim_terrain_hull'], 'compiled')


class Versions(Base):
    def test_same_version_builds_quietly(self):
        path = self.write(recipe({'chim_terrain_hull': 'routed'}, written=builder_ref(DEV),
                                 checked=builder_ref(DEV, '2026_10_10_v0.0.36-dev3_full_abc1234')))
        args, record, out = self.load(path)
        self.assertNotIn('WARNING', out)
        self.assertEqual((record['relation'], record['status']), ('same', 'verified'))
        self.assertEqual(args.chim_terrain_hull, 'routed')

    def test_newer_builder_warns_and_lists_changed_options(self):
        path = self.write(recipe({'chim_native_towns': 'on', 'seyda_recorded': None},
                                 written=builder_ref('0.0.36-dev1'), checked=builder_ref('0.0.36-dev1', 'r')))
        args, record, out = self.load(path)
        self.assertIn('WARNING: recipe test checked with v0.0.36-dev1, this builder is v%s' % DEV, out)
        for flag in ('--chim-native-towns', '--legacy-area', '--seyda-recorded', '--chim-terrain-hull',
                     '--chim-frame-ext'):
            self.assertIn(flag, out)
        self.assertIn('[this recipe sets it: "on"]', out)
        self.assertNotIn('--world-map', out)  # changed in v0.0.36-dev1 itself, not since
        self.assertEqual(record['relation'], 'newer-builder')
        self.assertEqual({row['option'] for row in record['changed_options']} >= {'chim_native_towns',
                                                                                  'seyda_recorded'}, True)

    def test_newer_builder_with_nothing_changed_says_so(self):
        changes = {'format': 1, 'changes': []}
        with mock.patch.object(br, 'load_changes', return_value=changes):
            path = self.write(recipe({}, written=builder_ref('0.0.36-dev2')))
            _, record, out = self.load(path)
        self.assertIn('No option changed its meaning or default since v0.0.36-dev2', out)
        self.assertEqual(record['changed_options'], [])

    def test_older_builder_refuses_and_names_unknown_options(self):
        path = self.write(recipe({'chim_terrain_hull': 'routed', 'tide_tables': 'on', 'moon_phase': 2},
                                 written=builder_ref('0.0.37-dev1')))
        with self.assertRaises(br.RecipeError) as error:
            self.load(path)
        text = str(error.exception)
        self.assertIn('this recipe needs a newer builder (v0.0.37-dev1); this builder is v' + DEV, text)
        self.assertIn('moon_phase, tide_tables', text)
        path = self.write(recipe({}, written=builder_ref('0.0.36-rc1')))
        with self.assertRaisesRegex(br.RecipeError, 'needs a newer builder'):
            self.load(path)

    def test_unknown_option_at_the_same_version_is_refused(self):
        path = self.write(recipe({'tide_tables': 'on'}, written=builder_ref(DEV)))
        with self.assertRaisesRegex(br.RecipeError, 'does not know: tide_tables'):
            self.load(path)

    def test_a_bad_value_is_refused_by_the_options_own_parser(self):
        path = self.write(recipe({'chim_terrain_hull': 'woven'}))
        with self.assertRaisesRegex(br.RecipeError, 'invalid choice'):
            self.load(path)


def run_main(argv, version=DEV, **patches):
    out, err = io.StringIO(), io.StringIO()
    with mock.patch.dict(os.environ), mock.patch.object(build, 'VERSION', version), \
            mock.patch.object(build, 'setup_plan', return_value={}), \
            mock.patch.object(build, 'prerequisites') as setup, \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = build.main(argv)
        except SystemExit as stop:
            code = stop.code
    return code, out.getvalue(), err.getvalue(), setup


class Retired(Base):
    def test_retired_option_in_a_recipe_is_refused_in_developer_mode(self):
        path = self.write(recipe({'legacy_areas': ['balmora']}))
        code, out, err, setup = run_main(['--recipe', str(path), '--developer-mode', '--host-plan'])
        self.assertEqual(code, 2)
        self.assertIn('--legacy-area has been disabled since', err)
        self.assertIn('--override legacy-area', err)
        setup.assert_not_called()

    def test_only_override_on_the_command_line_lets_it_through(self):
        path = self.write(recipe({'legacy_areas': ['balmora']}))
        code, out, err, _ = run_main(['--recipe', str(path), '--developer-mode', '--override', 'legacy-area',
                                      '--host-plan'])
        self.assertNotIn('has been disabled since', err)
        self.assertIn('DO NOT USE --legacy-area', err)
        self.assertIn('(overridden)', err)
        path = self.write(recipe({'legacy_areas': ['balmora'], 'override': ['legacy-area']}))
        code, out, err, _ = run_main(['--recipe', str(path), '--developer-mode', '--host-plan'])
        self.assertEqual(code, 1)
        self.assertIn('override is not part of a recipe', err)

    def test_outside_developer_mode_a_retired_option_warns(self):
        path = self.write(recipe({'chim_native_towns': 'off'}))
        code, out, err, _ = run_main(['--recipe', str(path), '--host-plan'])
        self.assertIn('DO NOT USE --chim-native-towns off', err)


class Precedence(Base):
    def test_command_line_wins_and_is_recorded(self):
        path = self.write(recipe({'chim_terrain_hull': 'routed', 'stair_walk': 'all', 'live_logs': True}))
        args, record, out = self.load(path, '--chim-terrain-hull', 'compiled', '--stair-walk', 'all')
        self.assertEqual(args.chim_terrain_hull, 'compiled')
        self.assertTrue(args.live_logs)
        self.assertIn('recipe says --chim-terrain-hull routed, command line says --chim-terrain-hull compiled', out)
        self.assertEqual(record['overrides'], [{'option': 'chim_terrain_hull', 'flag': '--chim-terrain-hull',
                                                'recipe': 'routed', 'command_line': 'compiled'}])
        metadata = build.recipe_metadata(args)
        self.assertEqual(metadata['recipe']['overrides'][0]['command_line'], 'compiled')

    def test_switches_and_lists(self):
        path = self.write(recipe({'follow_original_stair_rules': False, 'extra_town': ['bcoast_x7y2'],
                                  'skip_census': True}))
        args, record, out = self.load(path, '--follow-original-stair-rules')
        self.assertIs(args.follow_original_stair_rules, True)
        self.assertEqual(args.extra_town, ['bcoast_x7y2'])
        self.assertIs(args.skip_census, True)
        self.assertIn('recipe says --no-follow-original-stair-rules, command line says '
                      '--follow-original-stair-rules', out)

    def test_exclusions_add_up(self):
        path = self.write(recipe({'exclude': ['npc-gallery']}))
        args, record, out = self.load(path, '--exclude-video')
        self.assertEqual(args.exclude, ['video', 'npc-gallery'])
        self.assertEqual(record['overrides'], [])
        self.assertEqual(record['added'][0]['option'], 'exclude')

    def test_one_recipe_at_a_time(self):
        path = self.write(recipe({}))
        argv = ['--recipe', str(path), '--miniwind-balmora']
        with self.assertRaisesRegex(br.RecipeError, 'give one recipe'):
            br.configure(build.parser, build.parser().parse_args(argv), argv, DEV, out=io.StringIO())


class Inputs(Base):
    def pinned(self, cells_sha=None):
        cells, status = self.inputs()
        sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()  # noqa: E731
        return recipe({'chim_regions': ['@cells.csv'], 'chim_regions_status': 'progress.json'},
                      [{'option': 'chim_regions', 'role': 'cells', 'path': 'cells.csv',
                        'sha256': cells_sha or sha(cells)},
                       {'option': 'chim_regions_status', 'role': 'status', 'path': 'progress.json',
                        'sha256': sha(status)}])

    def test_matching_inputs_build(self):
        args, record, _ = self.load(self.write(self.pinned()))
        self.assertEqual([row['status'] for row in record['inputs']], ['ok', 'ok'])
        self.assertEqual(args.chim_regions, ['@cells.csv'])

    def test_sha256_mismatch_is_refused(self):
        with self.assertRaisesRegex(br.RecipeError, r"input cells \(cells.csv\): SHA-256 [0-9a-f]{64} is not"):
            self.load(self.write(self.pinned('0' * 64)))

    def test_missing_input_is_refused(self):
        document = self.pinned()
        (self.dir / 'cells.csv').unlink()
        with self.assertRaisesRegex(br.RecipeError, 'input cells: cells.csv not found'):
            self.load(self.write(document))

    def test_a_file_option_without_a_pin_is_refused(self):
        self.inputs()
        path = self.write(recipe({'chim_regions_status': 'progress.json'}))
        with self.assertRaisesRegex(br.RecipeError, 'files with no SHA-256'):
            self.load(path)

    def test_recipe_input_remaps_a_role_and_still_checks_it(self):
        document = self.pinned()
        other = self.dir / 'elsewhere'
        other.mkdir()
        (other / 'mine.csv').write_bytes((self.dir / 'cells.csv').read_bytes())
        path = self.write(document)
        (self.dir / 'cells.csv').unlink()
        args, record, _ = self.load(path, '--recipe-input', 'cells=elsewhere/mine.csv')
        self.assertEqual(args.chim_regions, ['@elsewhere/mine.csv'])
        self.assertEqual(record['inputs'][0]['recipe_path'], 'cells.csv')
        (other / 'mine.csv').write_text('x,y\n0,0\n', encoding='utf-8')
        with self.assertRaisesRegex(br.RecipeError, 'is not the recipe'):
            self.load(path, '--recipe-input', 'cells=elsewhere/mine.csv')

    def test_command_line_replaces_an_input(self):
        args, record, _ = self.load(self.write(self.pinned()), '--chim-regions-status', 'other.json')
        self.assertEqual(record['inputs'][1]['status'], 'replaced by the command line')
        self.assertEqual(str(args.chim_regions_status), 'other.json')


class Receipts(Base):
    def test_unverified_recipe_warns(self):
        _, record, out = self.load(self.write(recipe({})))
        self.assertIn('WARNING: recipe test is unverified (checked_with: null)', out)
        self.assertEqual(record['status'], 'unverified')

    def test_build_state_summary_image_and_saved_recipe(self):
        path = self.write(recipe({'live_logs': True}, written=builder_ref(DEV)))
        workspace = self.dir / 'ws'
        saved = self.dir / 'saved-recipe.json'
        seen = {}
        import setup_build

        def execute(steps, run, metadata):
            seen['metadata'] = metadata
            seen['env'] = os.environ.get(br.ENV)
            image = run / 'image' / ('AmiWind-v%s-dry-run.hdf' % DEV)
            image.parent.mkdir(parents=True)
            image.write_bytes(b'synthetic image')

        with mock.patch.object(setup_build, 'use_environment'), \
                mock.patch.object(build, 'dry_run_prerequisites', return_value={}), \
                mock.patch.object(build, 'dry_run_commands', return_value=[]), \
                mock.patch.object(build, 'provenance', return_value={}), \
                mock.patch.object(build, 'execute', side_effect=execute):
            code, out, err, _ = run_main(['--recipe', str(path), '--dry-run', '--workspace', str(workspace),
                                          '--name', 'fixture', '--any-run-name', '--save-recipe', str(saved),
                                          '--builder', 'legacy'])
        self.assertEqual(code, 0, err)
        file_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        state = seen['metadata']['build_recipe']
        self.assertEqual(state['recipe']['sha256'], file_sha)
        self.assertRegex(state['effective_sha256'], '^[0-9a-f]{64}$')
        image = json.loads(seen['env'])
        self.assertEqual((image['sha256'], image['run'], image['status']), (file_sha, 'fixture', 'unverified'))
        summary = json.loads((workspace / 'build/fixture/build-summary.json').read_text(encoding='utf-8'))
        self.assertEqual(summary['build_recipe']['recipe']['sha256'], file_sha)
        document, _ = br.read(saved)
        self.assertEqual((document['status'], document['checked_with']), ('unverified', None))
        self.assertEqual((document['written_with']['run'], document['written_with']['result']), ('fixture', 'passed'))
        self.assertTrue(document['options']['live_logs'])
        self.assertIn('Recipe saved: ', out)

    def test_image_step_records_the_recipe_without_keying_it(self):
        import build_cache
        self.assertIn(br.ENV, build_cache.IGNORED_ENV)
        source = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        self.assertIn("os.environ.get('%s')" % br.ENV, source)
        self.assertIn("build_json['build_recipe']", source)

    def test_mark_checked_fills_checked_with(self):
        document = br.effective_document(build.parser, br.effective_options(build.parser, build.parser().parse_args(
            [])), DEV, '0.1.0', 'abc1234', 'x')
        checked = br.mark_checked(document, DEV, '0.1.0', 'abc1234', 'run-1', 'd' * 64)
        self.assertEqual(br.document_errors(checked), [])
        self.assertEqual((checked['status'], checked['checked_with']['result_sha256']), ('verified', 'd' * 64))


class Presets(Base):
    def test_every_preset_is_its_recipe(self):
        # every old table row is a recipe; seyda-chim, lava-pools, vivec-palace, vivec-city-exterior and redmountain
        # came later, and anim-stage (v0.0.52, SKEL-ANIM-STAGE-52), halloween (v0.0.53), combat-playground (v0.0.54)
        # and demowind (v0.0.55, docs/DEMOWIND.md)
        self.assertEqual(sorted(row['name'] for row in mp.presets()
                                if row['name'] not in ('seyda-chim', 'lava-pools', 'vivec-palace', 'vivec-city-exterior',
                                                       'redmountain', 'anim-stage', 'halloween', 'magic',
                                                       'combat-playground', 'demowind')),
                         sorted(row['name'] for row in OLD_PRESETS))
        # vivec-arena-pit moved to the interior scope (MINIWIND-NO-INTERIOR-SCOPE-42): its room only
        self.assertEqual(mp.find('vivec-arena-pit')['scope'], 'interior')
        for row in OLD_PRESETS:
            if row['name'] == 'vivec-arena-pit':
                row = dict(row, scope='interior')
            with self.subTest(preset=row['name']):
                self.assertEqual(mp.find(row['name']), row)
                document, _ = br.read(br.preset_path(row['name']))
                self.assertEqual(mp.recipe_of(row), document)
                self.assertEqual(mp.row_of(document), row)

    def test_every_preset_gives_the_options_its_table_row_gave(self):
        extra = (['--miniwind-description', 'Mine', '--exclude-video', '--no-skip-census'], [])
        for row in OLD_PRESETS:
            if row['name'] == 'vivec-arena-pit':
                row = dict(row, scope='interior')  # moved to the interior scope (MINIWIND-NO-INTERIOR-SCOPE-42)
            for more in extra:
                with self.subTest(preset=row['name'], more=more):
                    argv = ['--miniwind-preset', row['name'], *more]
                    old = build.parser().parse_args(argv)
                    mp.apply_row(old, row)
                    new = build.parser().parse_args(argv)
                    record = br.configure(build.parser, new, argv, DEV, out=io.StringIO())
                    self.assertEqual(record['preset'], row['name'])
                    mine = {key: value for key, value in vars(new).items() if key != 'build_recipe_record'}
                    self.assertEqual(mine, vars(old))

    def test_preset_through_build_main(self):
        code, out, err, setup = run_main(['--miniwind-animkit', '--host-plan'])
        self.assertEqual(code, 0, err)
        self.assertIn('Recipe: animkit (', err)

    def test_a_preset_recipe_holds_only_preset_options(self):
        document = mp.recipe_of(OLD_PRESETS[0])
        document['options']['chim_terrain_hull'] = 'routed'
        with self.assertRaisesRegex(ValueError, 'only'):
            mp.row_of(document)


class Examples(Base):
    def files(self):
        return sorted((ROOT / 'config/recipes').rglob('*.json'))

    def test_examples_are_well_formed_and_named_by_their_files(self):
        names = [path.stem for path in self.files()]
        for want in ('release', 'full-coast-dev', 'miniwind-spot'):
            self.assertIn(want, names)
        for path in self.files():
            with self.subTest(recipe=path.name):
                document, _ = br.read(path)
                self.assertEqual(document['name'], path.stem)
                self.assertIsNone(document['written_with'])  # kept with this source tree

    def test_examples_load_into_this_builder(self):
        for path in self.files():
            with self.subTest(recipe=path.name):
                argv = ['--recipe', str(path)]
                br.configure(build.parser, build.parser().parse_args(argv), argv, DEV, out=io.StringIO(),
                             check_files=False)

    def test_examples_pass_the_builders_option_checks(self):
        for name in ('release', 'miniwind-spot'):
            with self.subTest(recipe=name):
                code, out, err, setup = run_main(['--recipe', str(ROOT / 'config/recipes' / (name + '.json')),
                                                  '--host-plan'])
                self.assertEqual(code, 0, err)
                setup.assert_not_called()

    def test_full_coast_inputs_say_how_to_make_them(self):
        document, _ = br.read(ROOT / 'config/recipes/full-coast-dev.json')
        self.assertEqual(sorted(row['role'] for row in document['inputs']),
                         ['chim-regions-cells', 'chim-regions-status'])
        for row in document['inputs']:
            self.assertIn('tools/', row['how'])
            self.assertFalse(Path(row['path']).is_absolute())

    def test_frame_maps_default_to_chim_in_the_examples(self):
        for name in ('release', 'full-coast-dev', 'miniwind-spot'):
            document, _ = br.read(ROOT / 'config/recipes' / (name + '.json'))
            self.assertEqual(document['options']['chim_frame_ext'], 'chim')


class OptionChanges(unittest.TestCase):
    def setUp(self):
        self.changes = br.load_changes()
        self.parser = build.parser()
        self.dests = {action.dest for action in self.parser._actions}

    def test_current_defaults_are_recorded(self):
        current = br.snapshot(build.parser)
        for key in ('options', 'build_defaults'):
            missing = sorted(set(current[key]) - set(self.changes['current'][key]))
            gone = sorted(set(self.changes['current'][key]) - set(current[key]))
            changed = sorted(k for k in set(current[key]) & set(self.changes['current'][key])
                             if current[key][k] != self.changes['current'][key][k])
            self.assertEqual((missing, gone, changed), ([], [], []),
                             'a builder option was added, removed or changed its default: record it in '
                             'config/option-changes.json "changes" (version = VERSION) and update "current" '
                             '(python tools/build_recipe.py snapshot)')

    def test_each_options_last_change_matches_the_builder(self):
        current = br.snapshot(build.parser)
        last = {}
        for row in sorted(self.changes['changes'], key=lambda row: br.version_key(row['version'])):
            if row['change'] in ('added', 'default'):
                last[row['option']] = row['to']
        for option, value in last.items():
            with self.subTest(option=option):
                now = current['build_defaults'].get(option, current['options'].get(option))
                self.assertEqual(now, value)
        for key in current['build_defaults']:
            self.assertIn(key, last, 'every build-defaults key has its history')

    def test_rows_are_well_formed(self):
        import retired_flags
        retired = {row['dest'] for row in retired_flags.RETIRED}
        for row in self.changes['changes']:
            with self.subTest(row=row):
                br.version_key(row['version'])
                self.assertIn(row['change'], ('added', 'default', 'meaning', 'retired', 'removed'))
                if row['change'] == 'retired':
                    self.assertIn(row['option'], retired)
                elif row['change'] != 'removed':
                    self.assertIn(row['option'], self.dests)

    def test_changes_between_is_half_open(self):
        rows = br.changes_between('0.0.36-dev1', '0.0.36-dev2', self.changes)
        self.assertTrue(rows)
        self.assertTrue(all(row['version'] == '0.0.36-dev2' for row in rows))


class MasterBuilder(unittest.TestCase):
    """tools/aw.py request --recipe (the request service's part; docker and git replaced by fakes)."""

    def setUp(self):
        import test_aw_service as t
        self.t = t
        self.case = t.ServiceTests('test_build_runs_and_writes_its_result_and_trial')
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.case.recipes = True
        original = self.case.git

        def git(repo, *args):
            if args[0] == 'cat-file':
                return '' if self.case.recipes else None
            return original(repo, *args)
        patcher = mock.patch.object(t.aw_service, 'git_text', git)
        patcher.start()
        self.addCleanup(patcher.stop)

    def runner(self, saved=None):
        runner = self.t.FakeRunner()
        summary = dict(runner.summary, recipe=saved)
        runner.summary = summary
        runner.fed = []

        def feed(command, data):
            runner.ran.append(runner.name(command))
            runner.fed.append(data)
            path = command[-1].split('P="$D/')[1].split('"')[0]
            return 0, '%s  /vol/src/recipes/%s\n' % (hashlib.sha256(data).hexdigest(), path), ''
        runner.feed = feed
        return runner

    def recipe_option(self, document):
        text = json.dumps(document, indent=2) + '\n'
        return {'name': document['name'], 'sha256': hashlib.sha256(text.encode()).hexdigest(), 'text': text}

    def test_recipe_is_staged_and_given_with_the_flags_winning(self):
        document = recipe({'chim_terrain_hull': 'routed'}, name='coast')
        saved = recipe({'chim_terrain_hull': 'compiled'}, name='coast', written=builder_ref(DEV))
        options = {'flags': ['--chim-terrain-hull', 'compiled'], 'recipe': self.recipe_option(document)}
        runner = self.runner(saved)
        code, result, runner = self.case.submit(self.case.request(options=options), runner)
        self.assertEqual(code, 0, result['notes'])
        build_line = [c for c in result['commands'] if 'tools/build.py' in c and ' --check' not in c][0]
        check_line = [c for c in result['commands'] if ' --check' in c][0]
        self.assertLess(build_line.index('--recipe /vol/src/recipes/'), build_line.index('--chim-terrain-hull'))
        self.assertIn('--save-recipe /vol/ws8/build/', build_line)
        self.assertNotIn('--save-recipe', check_line)  # a check never makes the run folder
        self.assertEqual(runner.fed, [options['recipe']['text'].encode('utf-8')])
        self.assertEqual(result['recipe']['requested']['sha256'], options['recipe']['sha256'])
        verified, _ = br.read(result['recipe']['path'])
        result_file = [a for a in result['artifacts'] if a.endswith('.json')][0]
        self.assertEqual(verified['checked_with']['result_sha256'], br.file_sha256(result_file))
        self.assertEqual((verified['status'], verified['checked_with']['run']), ('verified', result['run_name']))
        self.assertEqual(verified['checked_with']['amiwind_version'], DEV)

    def test_every_passed_build_checks_in_its_recipe(self):
        saved = recipe({'live_logs': True}, name='full', written=builder_ref(DEV))
        code, result, _ = self.case.submit(self.case.request(), self.runner(saved))
        self.assertEqual(code, 0, result['notes'])
        self.assertIsNone(result['recipe']['requested'])
        self.assertTrue(Path(result['recipe']['path']).name.endswith('.recipe.json'))

    def test_failed_builds_check_in_nothing(self):
        runner = self.runner(recipe({}, name='full'))
        runner.build_exit = 1
        runner.summary.update(status='failed', failed_stage='image')
        code, result, _ = self.case.submit(self.case.request(), runner)
        self.assertEqual(code, 1)
        self.assertIsNone(result.get('recipe'))

    def test_a_failed_build_from_a_requested_recipe_writes_a_valid_result(self):
        # AW-RESULT-RECIPE-SAVED-36: the internal 'saved' field stayed in a failed build's recipe block and the
        # result did not validate (the first Vivec stage A run lost its result document)
        raw = (ROOT / 'config/recipes/miniwind/vivec-arena-pit.json').read_bytes()
        runner = self.runner(recipe({}, name='vivec-arena-pit'))
        runner.build_exit = 1
        runner.summary.update(status='failed', failed_stage='image')
        with mock.patch.object(self.t.aw_service, 'git_blob', return_value=raw):
            request = self.case.request(kind='miniwind', purpose='miniwind', options={'preset': 'vivec-arena-pit'})
            code, result, _ = self.case.submit(request, runner)
        self.assertEqual(code, 1)
        self.assertEqual(set(result['recipe']), {'requested'})
        self.assertEqual(result['recipe']['requested']['name'], 'vivec-arena-pit')

    def test_retired_options_in_a_recipe_are_refused(self):
        options = {'recipe': self.recipe_option(recipe({'legacy_areas': ['balmora']}))}
        result = self.case.assertRefused(self.case.request(options=options), 'retired flag --legacy-area',
                                         self.runner())
        self.assertIn('recipe option legacy_areas', ' '.join(result['refusals']))

    def test_relative_inputs_and_old_builders_are_refused(self):
        document = recipe({'chim_regions_status': 'p.json'},
                          [{'option': 'chim_regions_status', 'role': 's', 'path': 'p.json', 'sha256': 'a' * 64}])
        self.case.assertRefused(self.case.request(options={'recipe': self.recipe_option(document)}),
                                'relative paths', self.runner())
        self.case.recipes = False
        self.case.assertRefused(self.case.request(options={'recipe': self.recipe_option(recipe({}))}),
                                'has no build recipes', self.runner())

    def test_miniwind_kind_builds_from_the_preset_recipe_and_records_it(self):
        raw = (ROOT / 'config/recipes/miniwind/vivec-arena-pit.json').read_bytes()
        with mock.patch.object(self.t.aw_service, 'git_blob', return_value=raw):
            request = self.case.request(kind='miniwind', purpose='miniwind', options={'preset': 'vivec-arena-pit'})
            code, result, _ = self.case.submit(request, self.runner(recipe({}, name='vivec-arena-pit')))
        self.assertEqual(code, 0, result['notes'])
        build_line = [c for c in result['commands'] if 'tools/build.py' in c and ' --check' not in c][0]
        self.assertIn('--miniwind-preset vivec-arena-pit', build_line)
        self.assertEqual(result['recipe']['requested'], {'name': 'vivec-arena-pit',
                                                         'sha256': hashlib.sha256(raw).hexdigest(),
                                                         'file': 'config/recipes/miniwind/vivec-arena-pit.json'})

    def test_a_changed_text_is_a_malformed_request(self):
        option = self.recipe_option(recipe({}))
        option['text'] = option['text'].replace('test', 'tost')
        errors = self.t.aw_service.request_errors(self.case.request(options={'recipe': option}))
        self.assertIn("text's SHA-256", ' '.join(errors))

    def test_request_command_reads_the_recipe_and_its_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'r.json'
            document = recipe({'chim_regions_status': '/vol/in/p.json'},
                              [{'option': 'chim_regions_status', 'role': 'status', 'path': '/vol/in/p.json',
                                'sha256': 'a' * 64}])
            path.write_text(json.dumps(document), encoding='utf-8', newline='\n')
            import aw
            args = aw.parser().parse_args(['request', '--kind', 'build', '--repo', tmp, '--commit', 'abc1234',
                                           '--purpose', 'full', '--version', 'v' + DEV, '--recipe', str(path),
                                           '--flags=--live-logs', '--requester', 'w'])
            request = self.t.aw_service.make_request(args)
            self.assertEqual(request['options']['recipe']['sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(self.t.aw_service.request_errors(request), [])
        self.assertEqual(request['options']['inputs'], [{'path': '/vol/in/p.json', 'sha256': 'a' * 64,
                                                         'role': 'status'}])
        self.assertEqual(request['options']['flags'], ['--live-logs'])


class PublicFiles(unittest.TestCase):
    def test_new_files_are_release_files_and_documented(self):
        files = json.loads((ROOT / 'tools/release-files.json').read_text(encoding='utf-8'))
        listed = files if isinstance(files, list) else sum((v for v in files.values() if isinstance(v, list)), [])
        wanted = ['tools/build_recipe.py', 'config/schemas/build-recipe-1.json', 'config/option-changes.json',
                  'docs/BUILD_RECIPES.md', 'tests/test_build_recipe.py']
        wanted += [path.relative_to(ROOT).as_posix() for path in sorted((ROOT / 'config/recipes').rglob('*.json'))]
        self.assertEqual([path for path in wanted if path not in listed], [])
        page = (ROOT / 'docs/BUILD_RECIPES.md').read_text(encoding='utf-8')
        for word in ('--recipe', '--save-recipe', '--recipe-input', 'checked_with', 'config/option-changes.json',
                     'config/recipes/miniwind', 'aw.py request', '.chim'):
            self.assertIn(word, page)
        for doc in ('docs/AW.md', 'docs/BUILD_CACHE.md'):
            self.assertIn('BUILD_RECIPES.md', (ROOT / doc).read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
