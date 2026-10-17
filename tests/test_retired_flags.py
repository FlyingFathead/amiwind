# SPDX-License-Identifier: GPL-3.0-only
"""Flags retired since CHIM v0.1.0 (tools/retired_flags.py, BUILD-LEGACY-CHAIN-DEFAULT-36).

CHIM-native areas are the default: every CHIM area is prepared through the CHIM pipeline. A retired flag (--legacy-area,
--chim-native-towns off) stops a developer-mode build before any stage unless named with
--override NAME; outside developer mode it is accepted with a loud warning. Every use is
recorded: build-state.json, build-summary.json, the end-of-build summary and image/build.json.
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]

import build  # noqa: E402
import retired_flags  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_guard  # noqa: E402

TOOLS = {name: '/tools/' + name for name in ('qbsp', 'vis', 'light', 'qcc', 'ffmpeg', 'xdftool', 'rdbtool')}
RUN = Path('/private/run')


class Stop(Exception):
    pass


def parse(*argv):
    return build.parser().parse_args(list(argv))


def run_main(*argv):
    """build.main up to the first step after the retired-flag check (resolve_jobs): (exit code or
    'passed', stdout, stderr)."""
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


@env_guard.isolated
class RetiredFlagTests(unittest.TestCase):
    def test_chim_native_areas_are_the_default(self):
        args = parse()
        self.assertEqual(args.chim_native_towns, 'on')
        self.assertEqual(args.legacy_areas, [])
        self.assertEqual(retired_flags.check(args), ([], [], []))
        self.assertEqual(build.chim_native_towns(args), ['balmora', 'seyda', 'vivec_city'])

    def test_default_plan_needs_no_legacy_balmora_input(self):
        # Legacy Balmora files are for regression tests only (BUILD-IMAGE-NATIVE-BALMORA-CACHE-36): no stage of
        # the default plan makes or reads the legacy Balmora chain's work folder or region maps.
        args = parse('--jobs', '4')
        args.data_files, args.sdk = Path('/owned/Data Files'), Path('/sdk')
        steps = build.commands(args, TOOLS, RUN)
        self.assertNotIn('balmora', dict(steps))
        for name, command in steps:
            text = ' '.join(str(part) for part in command)
            with self.subTest(stage=name):
                self.assertNotIn('balmora-work', text)
                self.assertNotIn('prepare_balmora.py', text)
                self.assertNotIn('--balmora-cache', text)
                self.assertNotIn('--balmora-scenery', text)

    def test_the_table(self):
        self.assertEqual(retired_flags.NAMES, ('legacy-area', 'chim-native-towns-off', 'vivec-districts', 'seyda-recorded',
                                                'seyda-scene-compiled'))
        for row in retired_flags.RETIRED:
            self.assertTrue(row['source'] and row['why'] and row['replacement'], row)

    def test_every_retired_flag_has_retired_help(self):
        actions = {action.dest: action for action in build.parser()._actions}
        for row in retired_flags.RETIRED:
            with self.subTest(flag=row['flag']):
                text = actions[row['dest']].help
                if row.get('contains'):  # retired values of live flags (the Vivec district areas)
                    for dest in row['dests']:
                        self.assertIn(retired_flags.HELP_PREFIX + ': the Vivec district areas', actions[dest].help)
                elif row['value'] is None:
                    self.assertTrue(text.startswith(retired_flags.HELP_PREFIX), text)
                else:  # a retired value of a live flag: its part of the help starts with the prefix
                    self.assertIn(retired_flags.HELP_PREFIX + ': ' + row['value'], text)
        self.assertEqual(retired_flags.HELP_PREFIX, 'RETIRED - DO NOT USE except for antiquated regression testing')

    def test_refused_in_developer_mode(self):
        for argv, flag, name in ((['--legacy-area', 'balmora'], '--legacy-area', 'legacy-area'),
                                 (['--chim-native-towns', 'off'], '--chim-native-towns off', 'chim-native-towns-off')):
            with self.subTest(flag=flag):
                code, out, err = run_main('--developer-mode', *argv)
                self.assertEqual(code, 2)
                self.assertIn('ERROR: ' + flag + ' has been disabled since CHIM v0.1.0 in development mode. '
                              'Override only if sure / for historical regression tests: --override ' + name, err)

    def test_override_lets_one_flag_through_and_is_recorded(self):
        code, out, _ = run_main('--developer-mode', '--legacy-area', 'balmora', '--override', 'legacy-area')
        self.assertEqual(code, 'passed')
        self.assertIn('WARNING: DO NOT USE --legacy-area EXCEPT FOR ANTIQUATED REGRESSION PURPOSES', out)
        self.assertIn('RETIRED FLAGS USED: --legacy-area balmora (overridden)', out)
        # The override names one flag only.
        code, _, err = run_main('--developer-mode', '--legacy-area', 'balmora', '--chim-native-towns', 'off',
                                '--override', 'legacy-area')
        self.assertEqual(code, 2)
        self.assertIn('--override chim-native-towns-off', err)
        record = retired_flags.check(parse('--developer-mode', '--legacy-area', 'balmora',
                                           '--override', 'legacy-area'))[0]
        self.assertEqual([(r['name'], r['given'], r['overridden'], r['developer_mode']) for r in record],
                         [('legacy-area', 'balmora', True, True)])

    def test_warning_outside_developer_mode(self):
        code, out, _ = run_main('--legacy-area', 'balmora')
        self.assertEqual(code, 'passed')
        self.assertIn('WARNING: DO NOT USE --legacy-area EXCEPT FOR ANTIQUATED REGRESSION PURPOSES '
                      '(retired since CHIM v0.1.0)', out)
        self.assertIn('RETIRED FLAGS USED: --legacy-area balmora', out)
        code, out, _ = run_main()
        self.assertEqual(code, 'passed')
        self.assertNotIn('RETIRED', out)

    def test_unknown_override_is_refused(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            parse('--override', 'night-lamp-lightmaps')

    def test_recorded_in_build_state_and_image(self):
        source = (ROOT / 'tools/build.py').read_text(encoding='utf-8')
        self.assertIn('"retired_flags_used": getattr(args, "retired_flags_record", None) or [],', source)
        args = parse('--jobs', '4', '--legacy-area', 'balmora')
        args.data_files, args.sdk = Path('/owned/Data Files'), Path('/sdk')
        args.retired_flags_record = retired_flags.check(args)[0]
        image = [str(part) for part in dict(build.commands(args, TOOLS, RUN))['image']]
        self.assertIn('--legacy-area balmora', image[image.index('--retired-flags-used') + 1])
        default = parse('--jobs', '4')
        default.data_files, default.sdk = Path('/owned/Data Files'), Path('/sdk')
        self.assertNotIn('--retired-flags-used', [str(p) for p in dict(build.commands(default, TOOLS, RUN))['image']])
        aga = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        self.assertIn("i.add_argument('--retired-flags-used'", aga)
        self.assertIn("build_json['retired_flags_used'] = {'flags': args.retired_flags_used,", aga)

    def test_recorded_in_the_build_summary(self):
        from build_summary import BuildSummary
        record = retired_flags.check(parse('--chim-native-towns', 'off'))[0]
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()) as out:
            summary = BuildSummary(Path(tmp), '0.0.0', 'test')
            summary.record_environment({'retired_flags_used': record})
            result = summary.finish('failed')
            saved = json.loads((Path(tmp) / 'build-summary.json').read_text(encoding='utf-8'))
        self.assertEqual(saved['retired_flags_used'], record)
        self.assertEqual(result['retired_flags_used'], record)
        self.assertGreaterEqual(out.getvalue().count('RETIRED FLAGS USED: --chim-native-towns off - WARNING: '
                                                     'DO NOT USE EXCEPT FOR ANTIQUATED REGRESSION PURPOSES'), 2)


if __name__ == '__main__':
    unittest.main()


class VivecDistrictsTests(unittest.TestCase):
    """Project decision 2026-10-11 09:55 +0300: all of Vivec in one CHIM frame (vivec_city) is the default; the district
    areas (the Arena-only frame of stage A and the other cantons) are retired legacy areas, refused in developer mode
    without --override vivec-districts, and by the master builder without override.allow retired-flags."""

    def test_the_default_plan_holds_the_whole_city(self):
        args = parse()
        self.assertIn('vivec_city', build.chim_native_towns(args))
        self.assertFalse(set(build.chim_native_towns(args)) & set(retired_flags.VIVEC_DISTRICTS))

    def test_a_district_area_is_refused_without_override(self):
        for argv in (['--chim-area', 'balmora', '--chim-area', 'vivec_arena'], ['--extra-town', 'vivec_foreign'],
                     ['--miniwind', '--miniwind-town', 'vivec_arena']):
            with self.subTest(argv=argv):
                args = parse(*argv, '--developer-mode')
                record, errors, _ = retired_flags.check(args)
                self.assertEqual([r['name'] for r in record], ['vivec-districts'])
                self.assertTrue(errors and '--override vivec-districts' in errors[0], errors)
                args = parse(*argv, '--developer-mode', '--override', 'vivec-districts')
                record, errors, warnings = retired_flags.check(args)
                self.assertEqual((errors, record[0]['overridden']), ([], True))
        args = parse('--chim-area', 'balmora', '--chim-area', 'vivec_city', '--developer-mode')
        self.assertEqual(retired_flags.check(args), ([], [], []))

    def test_the_master_builder_refuses_a_district_area(self):
        import aw_service
        self.assertTrue(aw_service.retired_hits(['--chim-area', 'vivec_arena']))
        self.assertTrue(aw_service.retired_hits(['--miniwind-town', 'vivec_temple']))
        self.assertEqual(aw_service.retired_hits(['--chim-area', 'vivec_city', '--miniwind-town', 'vivec_city']), [])
        hits = aw_service.recipe_retired_hits({'options': {'chim_areas': ['balmora', 'vivec_arena']}})
        self.assertTrue(hits and 'vivec_arena' in hits[0], hits)
        self.assertEqual(aw_service.recipe_retired_hits({'options': {'chim_areas': ['vivec_city']}}), [])


class VivecCityManifestTests(unittest.TestCase):
    """The world manifest of a default build: vivec_city is CHIM-native, no legacy map of it is made or shipped."""

    def test_default_manifest_has_no_legacy_vivec(self):
        import world_manifest
        args = parse()
        native = build.chim_native_towns(args)
        manifest = world_manifest.plan(['balmora', 'seyda', 'vivec_city'], native)
        row = next(r for r in manifest['rows'] if r['map'] == 'vivec_city')
        self.assertEqual((row['kind'], row['legacy'], row['kept_because']), ('chim-area', [], None))
        self.assertFalse([r for r in manifest['rows'] if r['map'] in retired_flags.VIVEC_DISTRICTS])
