# SPDX-License-Identifier: GPL-3.0-only
"""A plain build reuses the earlier builds of its workspace by default (BUILD-OFFER-EARLIER-RUNS-67).

A player who built once can update the source and build again in the same build folder: only what changed is made
again. The builder takes --reuse-all-available by itself when the workspace's stage index holds earlier builds, asks
once in a terminal (no terminal: yes), turns the first-minute stops into notices for that build only, and says at the
start and the end what came from earlier builds, with the from-scratch build recommended if something looks wrong.
--no-reuse, --clean and --release-from-scratch keep it off; an explicit --reuse-all-available keeps its strict stop."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

import build  # noqa: E402
import build_cache  # noqa: E402
import build_summary  # noqa: E402
import reuse_all as RA  # noqa: E402
import reuse_report  # noqa: E402


def write_run(workspace, name, started, stages, status='passed', version=None, profile=None):
    run = Path(workspace) / 'build' / name
    run.mkdir(parents=True, exist_ok=True)
    state = {'build_started_at': started, 'status': status,
             'steps': [{'name': stage, 'status': 'passed'} for stage in stages],
             'stage_cache': {'schema': 'amiwind-stage-cache-v2', 'fingerprints': dict(stages)}}
    if version:
        state['runtime_version'] = version
    (run / 'build-state.json').write_text(json.dumps(state), encoding='utf-8')
    if profile is not None:
        (run / 'build-profile.json').write_text(json.dumps(profile), encoding='utf-8')
    return run


def parsed(*argv):
    args = build.parser().parse_args(list(argv))
    build_cache.resolve_release_reuse(args)
    return args


class TheDefaultSwitchesOn(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_plain_build_with_earlier_builds_takes_them(self):
        write_run(self.ws, '2026_11_17_v0.0.66_full_ad5e9a0', '2026-11-17T10:00:00+00:00', {'a': 'A'})
        record = RA.default_choice(parsed('--workspace', str(self.ws)))
        self.assertTrue(record['on'])
        self.assertEqual(record['earlier_builds'], 1)
        self.assertIn('the default: 1 earlier build in this workspace', RA.default_line(record))
        self.assertIn('--no-reuse turns it off', RA.default_line(record))
        self.assertFalse(RA.index_path(self.ws).exists())      # read only: the decision writes no index

    def test_a_first_build_has_nothing_to_take(self):
        record = RA.default_choice(parsed('--workspace', str(self.ws)))
        self.assertEqual(record, {'on': False, 'selected_by': 'no earlier build in this workspace', 'earlier_builds': 0})
        # a run that passed no stage is no earlier build
        write_run(self.ws, 'stopped', '2026-11-17T10:00:00+00:00', {}, status='failed')
        self.assertFalse(RA.default_choice(parsed('--workspace', str(self.ws)))['on'])

    def test_switches_that_keep_it_off(self):
        write_run(self.ws, 'r', '2026-11-17T10:00:00+00:00', {'a': 'A'})
        for flag, why in (('--no-reuse', '--no-reuse'), ('--release-from-scratch', '--release-from-scratch'),
                          ('--no-profile', '--no-profile'), ('--dry-run', '--dry-run')):
            record = RA.default_choice(parsed('--workspace', str(self.ws), flag))
            self.assertEqual((record['on'], record['selected_by']), (False, why), flag)
        args = argparse.Namespace(clean=True, allow_release_reuse=None, workspace=self.ws)
        build_cache.resolve_release_reuse(args)
        self.assertEqual(RA.default_choice(args)['selected_by'], '--clean')
        args = parsed('--workspace', str(self.ws))
        args.recover_image_from = self.ws / 'build' / 'r'
        self.assertEqual(RA.default_choice(args)['selected_by'], '--recover-image-from')

    def test_an_explicit_reuse_option_is_the_callers_choice(self):
        write_run(self.ws, 'r', '2026-11-17T10:00:00+00:00', {'a': 'A'})
        self.assertIsNone(RA.default_choice(parsed('--workspace', str(self.ws), '--reuse-all-available')))
        self.assertIsNone(RA.default_choice(parsed('--workspace', str(self.ws), '--reuse-from', str(self.ws))))
        with self.assertRaisesRegex(ValueError, '--no-reuse contradicts --reuse-all-available'):
            RA.default_choice(parsed('--workspace', str(self.ws), '--reuse-all-available', '--no-reuse'))

    def test_modes_that_build_nothing(self):
        write_run(self.ws, 'r', '2026-11-17T10:00:00+00:00', {'a': 'A'})
        for flag in ('--plan', '--host-plan', '--versions', '--check-inputs', '--install-sdk', '--layout-selftest'):
            self.assertIsNone(RA.default_choice(parsed('--workspace', str(self.ws), flag)), flag)
        self.assertTrue(RA.default_choice(parsed('--workspace', str(self.ws), '--check'))['on'])   # plans as a build

    def test_a_final_version_takes_the_default_path(self):
        # the release kind never turns reuse off (build_cache.resolve_release_reuse): the default applies to a final
        write_run(self.ws, 'r', '2026-11-17T10:00:00+00:00', {'a': 'A'})
        args = parsed('--workspace', str(self.ws))
        self.assertTrue(args.allow_release_reuse)
        self.assertTrue(RA.default_choice(args)['on'])
        build_cache.require_reuse_allowed('0.0.67', args.allow_release_reuse)     # no refusal

    def test_the_request_is_strict_only_when_given(self):
        args = argparse.Namespace(reuse_all_available=True, workspace=self.ws, allow_rebuild_map={})
        self.assertTrue(build.reuse_all_request(args)['strict'])                      # explicit: the stop
        args.reuse_default_record = {'on': True}
        self.assertFalse(build.reuse_all_request(args)['strict'])                     # the default: notices
        args.reuse_all_available = False
        self.assertIsNone(build.reuse_all_request(args))

    def test_the_builder_decides_after_the_release_and_clean_rules_and_before_the_reuse_checks(self):
        text = (ROOT / 'tools/build.py').read_text(encoding='utf-8')
        decide = text.index('args.reuse_default_record = _reuse_default.default_choice(args)')
        self.assertLess(text.index('resolve_release_reuse(args)'), decide)
        self.assertLess(text.index('args.clean_record = clean_build.configure_clean('), decide)
        self.assertLess(decide, text.index("raise ValueError('--reuse-all-available needs a profiled AGA"))
        # the question comes after the stage plan, and the answer no plans again without the earlier builds
        prepare = text.index('steps = build_cache.prepare(steps, run, metadata, args.reuse_from, reuse_mode')
        settle = text.index('_reuse_default.settle_default(record, metadata.get', prepare)
        self.assertLess(settle, text.index('build_cache.PLANS.pop(str(run), None)', settle))


class TheQuestion(unittest.TestCase):
    QUESTION = RA.question_text(2, 3, 5)

    def test_text(self):
        self.assertEqual(self.QUESTION, 'Found 2 earlier builds in this build folder: 3 of 5 stages can be reused '
                                        'unchanged. Reuse them? [Y/n] ')
        self.assertIn('Found 1 earlier build in', RA.question_text(1, 1, 1))

    def test_no_terminal_is_yes(self):
        out = []
        self.assertEqual(RA.ask_reuse(self.QUESTION, False, read=None, write=out.append), (True, 'no terminal: yes'))
        self.assertEqual(out, [self.QUESTION + 'yes (no terminal to ask)'])

    def test_answers_and_the_default(self):
        for reply, yes in (('', True), ('y', True), ('YES', True), ('n', False), ('No', False), ('  nope ', False)):
            asked = []
            answer, how = RA.ask_reuse(self.QUESTION, True, read=lambda q: asked.append(q) or reply, write=print)
            self.assertEqual(answer, yes, reply)
            self.assertEqual(asked, [self.QUESTION])                       # asked once
        self.assertEqual(RA.ask_reuse(self.QUESTION, True, read=lambda q: '', write=print)[1],
                         'terminal: yes (the default)')

    def test_end_of_input_is_yes(self):
        def closed(question):
            raise EOFError
        out = []
        self.assertTrue(RA.ask_reuse(self.QUESTION, True, read=closed, write=out.append)[0])


class TheNotice(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self.tmp.name)
        self.old = write_run(self.ws, '2026_11_17_v0.0.66_full-release_ad5e9a0', '2026-11-17T08:00:00+00:00',
                             {'a': 'A', 'b': 'B'}, version='0.0.66')
        self.new = write_run(self.ws, '2026_11_18_v0.0.67-dev2_full_0d6f7ab', '2026-11-18T08:00:00+00:00',
                             {'c': 'C'})
        self.cache = {'reused': {'a': {'from': str(self.old)}, 'b': {'from': str(self.old)},
                                 'c': {'from': str(self.new)}, 'p': {'from': 'prerendered /store'}},
                      'minute_one': {'units': {'d': [['resident-bake', 1700, 1769]], 'e': [['resident-bake', 1700, 1769],
                                                                                            ['room-actor', 10, 12]]},
                                     'notices': [['d', 'would bake again 69 of the 1769 units']]}}

    def tearDown(self):
        self.tmp.cleanup()

    def settle(self, read=None, interactive=False, check=False, cache=None):
        out = []
        record = {'on': True, 'selected_by': 'the default: 2 earlier builds in this workspace', 'earlier_builds': 2}
        RA.settle_default(record, self.cache if cache is None else cache, 6, self.ws, interactive, read=read,
                          write=out.append, check=check)
        return record, out

    def test_what_came_from_where_and_the_from_scratch_line(self):
        record, out = self.settle()
        self.assertEqual(record['answer'], 'yes')
        self.assertEqual(record['answered_by'], 'no terminal: yes')
        self.assertEqual(record['stages_reused'], 3)                     # the prerendered entry is no earlier build
        self.assertEqual([(s['run'], s['stages']) for s in record['sources']],
                         [(self.old.name, 2), (self.new.name, 1)])
        self.assertEqual(record['units'], [1710, 1781])                   # one cache counted once
        self.assertEqual(record['notices'], 1)
        text = '\n'.join(out)
        self.assertIn(RA.question_text(2, 3, 6) + 'yes (no terminal to ask)', out)
        self.assertIn('Earlier builds reused: 3 of 6 stages come from earlier builds of this workspace', text)
        self.assertIn('2 stages from v0.0.66, built 2026-11-17 (%s)' % self.old.name, text)
        self.assertIn('from v0.0.67-dev2, built 2026-11-18', text)      # the version from the run name
        self.assertIn('1,710 of the 1,781 units', text)
        self.assertIn('If something in the game looks wrong or unstable, build once from scratch in a new build '
                      'folder', text)
        self.assertIn('./build.sh --clean --workspace ../amiwind-clean', text)
        self.assertIn(r'(Windows: .\build.cmd --clean --workspace ..\amiwind-clean)', text)
        self.assertIn('not known', text)
        self.assertEqual(record['notice'], out[1:])

    def test_the_last_build_that_ran_every_stage(self):
        write_run(self.ws, '2026_11_10_v0.0.65_full_1234567', '2026-11-10T08:00:00+00:00', {'a': 'A0'},
                  version='0.0.65', profile={'wall_seconds': 3900.0, 'stages': [{'name': 'a', 'wall': 3900.0}]})
        # newer, but it took a stage from another run: not a full build
        write_run(self.ws, '2026_11_11_v0.0.65_full_2345678', '2026-11-11T08:00:00+00:00', {'a': 'A0'},
                  profile={'wall_seconds': 60.0, 'stages': [{'name': 'a', 'wall': 1.0, 'reused': {'from': 'x'}}]})
        found = RA.last_full_build(self.ws)
        self.assertEqual(found['run'], '2026_11_10_v0.0.65_full_1234567')
        record, out = self.settle()
        self.assertIn('The last build of this workspace that ran every stage took 1 h 05 min (v0.0.65, built '
                      '2026-11-10, 2026_11_10_v0.0.65_full_1234567).', '\n'.join(out))

    def test_the_answer_no(self):
        record, out = self.settle(read=lambda q: 'n', interactive=True)
        self.assertEqual((record['on'], record['answer'], record['answered_by']), (False, 'no', 'terminal: no'))
        self.assertNotIn('notice', record)
        self.assertIn('off for this build (answered no)', out[-1])

    def test_nothing_to_reuse_asks_nothing(self):
        def never(question):
            raise AssertionError('asked although nothing can be reused')
        record, out = self.settle(read=never, interactive=True, cache={'reused': {}})
        self.assertEqual(record['answered_by'], 'nothing to reuse')
        self.assertTrue(record['on'])
        self.assertIn('every stage runs', out[0])

    def test_a_check_says_what_a_build_would_ask(self):
        def never(question):
            raise AssertionError('a check never asks')
        record, out = self.settle(read=never, interactive=True, check=True)
        self.assertEqual(out[0], 'A build would ask: ' + RA.question_text(2, 3, 6).rstrip())
        self.assertIn('notice', record)

    def test_the_end_summary_carries_it(self):
        record, _ = self.settle()
        run = write_run(self.ws, 'this', '2026-11-18T09:00:00+00:00', {})
        state = json.loads((run / 'build-state.json').read_text(encoding='utf-8'))
        state['reuse_default'] = record
        (run / 'build-state.json').write_text(json.dumps(state), encoding='utf-8')
        kept = {}
        self.assertEqual(build_summary.reuse_default_lines(run, kept), record['notice'])
        self.assertEqual(kept['reuse_default']['answer'], 'yes')            # build-summary.json carries it too
        state['reuse_default'] = {'on': False, 'selected_by': '--no-reuse', 'earlier_builds': None}
        (run / 'build-state.json').write_text(json.dumps(state), encoding='utf-8')
        self.assertEqual(build_summary.reuse_default_lines(run, {}), ['Reuse of earlier builds: off (--no-reuse)'])
        del state['reuse_default']
        (run / 'build-state.json').write_text(json.dumps(state), encoding='utf-8')
        self.assertEqual(build_summary.reuse_default_lines(run, {}), [])     # a build the default did not apply to

    def test_the_build_report_carries_it(self):
        import build_report
        record, _ = self.settle()
        ctx = types.SimpleNamespace(args=argparse.Namespace(reuse_from=None, reuse_all_available=True, reuse_mode='copy'),
                                    stage_cache={'reused': {}, 'minute_one': self.cache['minute_one']},
                                    metadata={'reuse_default': record}, path=lambda value: str(value),
                                    plan_names=lambda: ['a'])
        text = '\n'.join(build_report.reuse(ctx))
        self.assertIn('Reuse of earlier builds: on (the default: 2 earlier builds in this workspace); asked: no '
                      'terminal: yes', text)
        self.assertIn('--reuse-all-available, the default of this build', text)
        self.assertIn('Reuse notices (the default build made this stored work again and went on):', text)
        self.assertIn('./build.sh --clean --workspace ../amiwind-clean', text)


class TheStopsOfTheDefaultBuild(unittest.TestCase):
    STEPS = [('area', ['python3', 'tools/prepare_area.py'])]

    def minute_one(self, strict):
        run = Path('/nonexistent/build/run')
        build_cache.PLANS[str(run)] = {}
        build_cache.CLOSURES[str(run)] = {'stages': {'area': {'tools/prepare_area.py'}}, 'units': {}}
        request = {'workspace': '/nonexistent', 'allowed': {}, **({} if strict is None else {'strict': strict})}
        cache, metadata, out = {}, {}, io.StringIO()
        with mock.patch.object(RA, 'unit_report', return_value={'area': [('resident-bake', 0, 2147)]}), \
                mock.patch.object(RA, 'uncached_bakes', return_value=set()), contextlib.redirect_stdout(out):
            try:
                build_cache.minute_one(self.STEPS, run, metadata, cache, {'area': 'changed: sources'},
                                       mock.Mock(root=ROOT), request)
                error = None
            except ValueError as exc:
                error = exc
        return error, cache, out.getvalue()

    def test_explicit_reuse_all_available_still_stops(self):
        for strict in (None, True):                        # an older caller without the key stops as before
            error, cache, out = self.minute_one(strict)
            self.assertIn('Reuse stop (--reuse-all-available)', str(error))
            self.assertIn('STOP area: would bake again 2147 of the 2147 units', out)
            self.assertEqual(len(cache['minute_one']['stops']), 1)
            self.assertNotIn('notices', cache['minute_one'])

    def test_the_default_build_goes_on_with_a_notice(self):
        error, cache, out = self.minute_one(False)
        self.assertIsNone(error)
        self.assertIn('NOTICE area: would bake again 2147 of the 2147 units its unit cache resident-bake holds', out)
        self.assertIn('this build makes that again and goes on', out)
        self.assertIn('Stage plan (every earlier build of the workspace, the default)', out)
        self.assertFalse([line for line in out.splitlines() if line.startswith('STOP ')])
        self.assertEqual(cache['minute_one']['stops'], [])
        self.assertEqual(cache['minute_one']['notices'][0][0], 'area')
        # the build server reads STOP lines of a check as a stopped check: a notice is none
        import aw_service
        self.assertEqual(aw_service.parse_check(out)['stops'], [])

    def preflight(self, strict, accept=False):
        index = types.SimpleNamespace(scope='units', files={}, root=ROOT)
        check = {'stages': 1, 'reused': 0, 'rebuilt': 1, 'unexpected': 1, 'policy': 0, 'rows': [],
                 'source_diff': {'changed': [], 'added': [], 'removed': []}, 'too_broad': ['area']}
        run = Path('/nonexistent/build/run')
        summary = {'sources': {}, 'candidates': [], 'primary': None, 'passed_over': {}}
        out = io.StringIO()
        with mock.patch.object(build_cache, 'fingerprint_steps', return_value=({'area': 'F'}, {}, {}, {})), \
                mock.patch.object(build_cache, 'stage_units', return_value=({}, {})), \
                mock.patch.object(build_cache, 'stage_closures', return_value={}), \
                mock.patch.object(build_cache, 'plan_all', return_value=({}, {'area': 'changed: sources'}, {},
                                                                          Path('/nonexistent/build/old'), {}, summary)), \
                mock.patch.object(build_cache, 'run_preflight', return_value=check), \
                mock.patch.object(build_cache, 'minute_one'), contextlib.redirect_stdout(out):
            metadata = {}
            try:
                build_cache.prepare(self.STEPS, run, metadata, None, 'copy', index, accept_rebuild=accept,
                                    reuse_all={'workspace': '/nonexistent', 'allowed': {}, 'strict': strict})
                error = None
            except ValueError as exc:
                error = exc
        build_cache.PLANS.pop(str(run), None)
        return error, metadata, out.getvalue()

    def test_a_too_broad_key_stops_an_explicit_build_and_is_a_notice_in_the_default_build(self):
        error, _, out = self.preflight(True)
        self.assertIn('Reuse preflight: 1 stage(s) would be rebuilt', str(error))
        self.assertIn('stopping before any stage runs', out)
        error, metadata, out = self.preflight(False)
        self.assertIsNone(error)
        self.assertIn('accepted with the default build (a notice, no stop): they run again.', out)
        self.assertEqual(metadata['stage_cache']['preflight']['too_broad'], ['area'])
        self.assertIn('too_broad_noticed', metadata['stage_cache']['preflight'])
        error, _, out = self.preflight(True, accept=True)
        self.assertIsNone(error)
        self.assertIn('accepted with --accept-rebuild.', out)

    def test_the_preflight_wording_keeps_its_default(self):
        result = {'stages': 1, 'reused': 0, 'rebuilt': 1, 'unexpected': 1, 'policy': 0, 'rows': [],
                  'source_diff': {'changed': [], 'added': [], 'removed': []}, 'too_broad': ['area']}
        out = io.StringIO()
        reuse_report.print_preflight(result, out, accepted=True)
        self.assertIn('accepted with --accept-rebuild.', out.getvalue())


class TheOption(unittest.TestCase):
    def test_no_reuse_is_an_option(self):
        # a choice, not a debugging opt-out (tests/test_build_defaults.py reads every no_* dest as one)
        self.assertTrue(build.parser().parse_args(['--no-reuse']).reuse_declined)
        self.assertFalse(build.parser().parse_args([]).reuse_declined)

    def test_the_index_records_the_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_run(tmp, 'explicit-name', '2026-11-17T10:00:00+00:00', {'a': 'A'}, version='0.0.66')
            entry = RA.update_index(tmp, write=False)['runs']['explicit-name']
            self.assertEqual(entry['version'], '0.0.66')
            self.assertEqual(RA.run_label('explicit-name', entry), 'v0.0.66, built 2026-11-17')
            self.assertEqual(RA.run_label('no-version-here', {}), 'version not recorded, built on a date not recorded')


if __name__ == '__main__':
    unittest.main()
