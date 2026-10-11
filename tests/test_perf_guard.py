"""Perf guard (tools/perf_guard.py, docs/BUILD_PROFILE.md "Perf guard"): parallelization never regresses."""
import argparse
import contextlib
import datetime
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import perf_guard  # noqa: E402

TODAY = '2026-10-11'
POLICY = {'independent_units': {'Image: stair walk': 'maps'}, 'waivers': []}


def section(name, wall, cores, items=None, phase=False):
    row = {'name': name, 'wall': wall, 'cores_avg': cores, 'cpu': round(wall * cores, 1), 'min_depth': 0, 'calls': 1}
    if items is not None:
        row['items'] = items
    if phase:
        row['phase'] = True
    return row


def profile(run, sections, stage='image', jobs=24, busy=False, other=0.0, fingerprint='f1'):
    host = {'cpus': 24, 'busy_percent': 50.0, 'other_percent': other, 'host_busy': busy, 'samples': 9}
    return {'schema': 'amiwind-build-profile-v1', 'run': 'out/build/' + run, 'version': '0.0.36-dev5',
            'budget': jobs, 'started_at': '2026-10-11T10:00:00',
            'stages': [{'name': stage, 'status': 'passed', 'jobs': jobs, 'jobs_mean': jobs, 'fingerprint': fingerprint,
                        'host': host, 'sections': sections}]}


def records(prof):
    return perf_guard.baseline_records(prof, 'sha-' + perf_guard.run_name(prof), POLICY)


def judge(prof, baseline_profiles=(), policy=POLICY, today=TODAY, fixed=()):
    recs = [record for other in baseline_profiles for record in records(other)]
    return perf_guard.judge(prof, recs, policy, today, set(fixed))


def verdicts(result):
    return {row['section']: row['verdict'] for row in result['rows']}


class PerfGuardTests(unittest.TestCase):
    def test_a_serial_regression_of_a_parallel_section_fails(self):
        before = profile('old', [section('parallel map: walk', 900, 11.6, items=270)])
        now = profile('new', [section('parallel map: walk', 950, 1.1, items=132)])
        result = judge(now, [before])
        self.assertEqual(result['verdict'], 'failed')
        row = result['rows'][0]
        self.assertEqual(row['verdict'], perf_guard.FAIL)
        self.assertEqual(row['baseline']['tier'], 'saturating')
        self.assertTrue(any(text.startswith('parallel -> serial') for text in row['reasons']), row['reasons'])

    def test_the_same_work_staying_parallel_passes(self):
        before = profile('old', [section('parallel map: walk', 300, 11.6, items=270)])
        now = profile('new', [section('parallel map: walk', 310, 12.0, items=270)])
        self.assertEqual(verdicts(judge(now, [before])), {'parallel map: walk': perf_guard.OK})

    def test_different_work_is_not_compared(self):
        # fewer units than cores in the baseline: it could not fill the machine, so its cores say nothing here
        before = profile('old', [section('parallel map: walk', 40, 9.0, items=10)])
        now = profile('new', [section('parallel map: walk', 45, 1.2, items=500)])
        self.assertEqual(verdicts(judge(now, [before])), {'parallel map: walk': perf_guard.NO_BASELINE})
        # another stage or another section is other work too
        other = profile('old2', [section('parallel map: walk', 40, 12.0, items=500)], stage='chim')
        renamed = profile('old3', [section('parallel map: other', 40, 12.0, items=500)])
        self.assertEqual(verdicts(judge(now, [other, renamed])), {'parallel map: walk': perf_guard.NO_BASELINE})
        # time is compared only with the same units
        before = profile('old4', [section('parallel map: walk', 40, 12.0, items=400)])
        result = judge(profile('new2', [section('parallel map: walk', 400, 12.0, items=4000)]), [before])
        self.assertEqual(result['rows'][0]['verdict'], perf_guard.OK)
        self.assertIsNone(result['rows'][0]['baseline']['wall'])

    def test_slower_with_the_same_units_fails(self):
        before = profile('old', [section('parallel map: bake', 100, 10.0, items=40)])
        result = judge(profile('new', [section('parallel map: bake', 200, 10.0, items=40)]), [before])
        self.assertEqual(result['rows'][0]['verdict'], perf_guard.FAIL)
        self.assertIn('slower with the same 40 units', ' '.join(result['rows'][0]['reasons']))
        # within the tolerance: fine
        result = judge(profile('new2', [section('parallel map: bake', 110, 10.0, items=40)]), [before])
        self.assertEqual(result['rows'][0]['verdict'], perf_guard.OK)

    def test_a_busy_host_is_marked_never_silently_compared(self):
        before = profile('old', [section('parallel map: bake', 100, 10.0, items=40)])
        # busy, and other work left fewer cores than the baseline used: not compared
        busy = profile('new', [section('parallel map: bake', 200, 8.0, items=40)], busy=True, other=75.0)
        row = judge(busy, [before])['rows'][0]
        self.assertEqual(row['verdict'], perf_guard.BUSY)
        self.assertTrue(any('busy host' in text for text in row['reasons']))
        # busy, but the section left most of its free cores idle: compared anyway, and said so
        idle = profile('new2', [section('parallel map: bake', 200, 1.0, items=40)], busy=True, other=50.0)
        row = judge(idle, [before])['rows'][0]
        self.assertEqual(row['verdict'], perf_guard.FAIL)
        self.assertTrue(any('cores compared anyway' in text for text in row['reasons']))
        # a busy baseline is used only when no quiet one exists, and then marked
        busy_base = profile('old2', [section('parallel map: bake', 100, 10.0, items=40)], busy=True)
        row = judge(profile('new3', [section('parallel map: bake', 100, 10.0, items=40)]), [busy_base])['rows'][0]
        self.assertTrue(row['baseline']['busy'])
        self.assertTrue(any('time not compared' in text for text in row['reasons']))

    def test_fix_now_without_a_baseline(self):
        now = profile('new', [section('parallel map: walk', 900, 1.7, items=132),
                              section('Image: stair walk', 905, 1.7, phase=True),
                              section('Image: drives', 120, 1.0, phase=True),
                              section('parallel map: pack', 90, 1.4, items=2)])
        result = judge(now)
        self.assertEqual(verdicts(result), {'parallel map: walk': perf_guard.FIX_NOW,
                                            'Image: stair walk': perf_guard.FIX_NOW,   # declared per-unit
                                            'Image: drives': perf_guard.NO_BASELINE,   # no independent units known
                                            'parallel map: pack': perf_guard.NO_BASELINE})  # 2 units, 1.4 cores
        self.assertEqual(result['failed'], 2)
        # under a minute is not a fix-now finding
        self.assertEqual(judge(profile('n2', [section('parallel map: walk', 50, 1.0, items=132)]))['failed'], 0)

    def test_waivers_are_visible_and_expire(self):
        waiver = {'id': 'BUILD-X-36', 'owner': 'stairs-rc1', 'stage': 'image',
                  'sections': ['Image: stair walk', 'parallel map: walk'], 'expires': '2026-10-14'}
        policy = dict(POLICY, waivers=[waiver])
        now = profile('new', [section('parallel map: walk', 900, 1.7, items=132)])
        result = judge(now, policy=policy)
        self.assertEqual((result['verdict'], result['waived']), ('passed', 1))
        self.assertIn('waived by BUILD-X-36 until 2026-10-14 (stairs-rc1)', ' '.join(result['rows'][0]['reasons']))
        self.assertIn('WAIVED', '\n'.join(perf_guard.table_lines(result)))
        expired = judge(now, policy=policy, today='2026-10-15')
        self.assertEqual(expired['verdict'], 'failed')
        self.assertIn('expired 2026-10-14', ' '.join(expired['rows'][0]['reasons']))
        fixed = judge(now, policy=policy, fixed={'BUILD-X-36'})
        self.assertEqual(fixed['verdict'], 'failed')
        self.assertIn('marked fixed', ' '.join(fixed['rows'][0]['reasons']))

    def test_the_table_ends_with_totals(self):
        lines = perf_guard.table_lines(judge(profile('new', [section('parallel map: a', 60, 10.0, items=30),
                                                             section('parallel map: b', 40, 4.0, items=8)])))
        body = [line for line in lines if not line.startswith('  ')]
        self.assertTrue(body[-1].startswith('TOTALS'), lines)
        self.assertIn('2 sections', body[-1])
        self.assertIn('38', body[-1])        # units
        self.assertIn('1m40s', body[-1])     # time
        self.assertIn('7.6 avg', body[-1])   # (600 + 160) / 100 cores

    def test_reused_stages_and_short_sections_are_not_judged(self):
        prof = profile('new', [section('parallel map: a', 20, 1.0, items=30), section('exec qbsp', 90, 1.0)])
        prof['stages'].append(dict(prof['stages'][0], name='chim', reused={'from': 'x'},
                                   sections=[section('parallel map: c', 900, 1.0, items=300)]))
        self.assertEqual(judge(prof)['rows'], [])

    def test_check_writes_the_run_files_and_records_only_passed_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            run = base / 'ws' / 'build' / 'run1'
            run.mkdir(parents=True)
            good = profile('run1', [section('parallel map: a', 300, 12.0, items=300)])
            (run / 'build-profile.json').write_text(json.dumps(good), encoding='utf-8')
            policy = base / 'policy.json'
            policy.write_text(json.dumps(POLICY), encoding='utf-8')
            with contextlib.redirect_stdout(io.StringIO()):
                result = perf_guard.check(run, policy=policy, record=True, today=TODAY)
            ledger = base / 'ws' / 'cache' / 'perf-guard' / 'baselines.jsonl'   # the build pool's cache
            self.assertEqual((result['verdict'], result['recorded']), ('passed', 1))
            self.assertTrue((run / 'perf-guard.json').is_file() and (run / 'perf-guard.txt').is_file())
            self.assertEqual(len(perf_guard.read_baselines(ledger)), 1)
            with contextlib.redirect_stdout(io.StringIO()):
                again = perf_guard.check(run, policy=policy, record=True, today=TODAY)
            self.assertEqual(again['recorded'], 0)          # the same profile SHA-256 is never added twice
            run2 = base / 'ws' / 'build' / 'run2'
            run2.mkdir()
            bad = profile('run2', [section('parallel map: a', 900, 1.0, items=300)])
            (run2 / 'build-profile.json').write_text(json.dumps(bad), encoding='utf-8')
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = perf_guard.main(['check', str(run2), '--policy', str(policy), '--record', '--today', TODAY,
                                        '--json'])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(out.getvalue().splitlines()[-1])['verdict'], 'failed')
            self.assertEqual(len(perf_guard.read_baselines(ledger)), 1)   # a failed run is never a baseline
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(perf_guard.main(['show', str(run2), '--json']), 1)
                self.assertEqual(perf_guard.main(['show', str(run), '--json']), 0)

    def test_build_ends_with_exit_3_when_the_guard_fails(self):
        import build
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / 'ws' / 'build' / 'run'
            run.mkdir(parents=True)
            (run / 'build-profile.json').write_text(json.dumps(
                profile('run', [section('parallel map: a', 900, 1.0, items=300)])), encoding='utf-8')
            args = argparse.Namespace(perf_guard='fail', perf_guard_baselines=Path(tmp) / 'b.jsonl', dry_run=False,
                                      no_profile=False)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(build.perf_guard_step(args, run), build.PERF_GUARD_EXIT)
            self.assertIn('PERF GUARD FAILED', out.getvalue())
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(build.perf_guard_step(argparse.Namespace(**dict(vars(args), perf_guard='warn')),
                                                       run), 0)
                self.assertEqual(build.perf_guard_step(argparse.Namespace(**dict(vars(args), dry_run=True)), run), 0)

    def test_the_policy_names_registered_bugs_owners_and_dates(self):
        policy = perf_guard.load_policy()
        bugs = {row['id'] for row in json.loads((ROOT / 'docs/bugs/bugs.json').read_text(encoding='utf-8'))}
        for waiver in policy['waivers']:
            self.assertIn(waiver['id'], bugs, waiver)
            self.assertTrue(waiver.get('owner') and waiver.get('reason') and waiver.get('sections'), waiver)
            since = datetime.date.fromisoformat(waiver['since'])
            expires = datetime.date.fromisoformat(waiver['expires'])
            self.assertLessEqual((expires - since).days, 14, 'a waiver is short-lived: %s' % waiver['id'])
        for name, unit in policy['independent_units'].items():
            self.assertTrue(isinstance(name, str) and isinstance(unit, str) and unit)


if __name__ == '__main__':
    unittest.main()
