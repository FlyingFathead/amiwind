"""The master builder's stall fallback (tools/stall_guard.py, BUILD-NO-STALL-ALERT-66): a stalled step is stopped
with the reason within its limit; a step that prints progress is not; a step in a known wait reports the wait."""
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import stall_guard as S  # noqa: E402

PY = sys.executable


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class GuardTests(unittest.TestCase):
    def guard(self, **kw):
        clock = Clock()
        return S.Guard('test', limit_s=60, clock=clock, stream=io.StringIO(), **kw), clock

    def test_silent_idle_step_is_a_stall(self):
        g, c = self.guard()
        c.t = 59
        self.assertIsNone(g.check(0.0))
        c.t = 61
        self.assertIn('no progress', g.check(0.0))

    def test_progress_lines_reset_the_clock(self):
        g, c = self.guard()
        for t in range(0, 600, 30):
            c.t = t
            g.line('unit %d done' % t)
            self.assertIsNone(g.check(0.0))

    def test_heartbeat_is_not_progress(self):
        g, c = self.guard()
        c.t = 70
        g.line('[heartbeat] chim: (no phase recorded): still working, 1m 10s (no output for 1m 10s)')
        self.assertIsNotNone(g.check(0.0))

    def test_heartbeat_cores_count_as_cpu(self):
        g, c = self.guard()
        c.t = 500
        g.line('[heartbeat] chim: x: still working, 8m, 10.8 cores (no output for 8m 20s)')
        self.assertIsNone(g.check(None))
        g.line('[heartbeat] chim: x: still working, 8m, 0.0 cores (no output for 8m 50s)')
        self.assertIsNotNone(g.check(None))

    def test_busy_cpu_is_not_a_stall(self):
        g, c = self.guard()
        c.t = 1000
        self.assertIsNone(g.check(80.0))

    def test_unknown_cpu_waits_twice_the_limit(self):
        g, c = self.guard()
        c.t = 100
        self.assertIsNone(g.check(None))
        c.t = 121
        self.assertIsNotNone(g.check(None))

    def test_known_wait_reports_instead(self):
        g, c = self.guard()
        g.line('gate-queue: queued behind 3 gates (running 3 of max 3, waiting ahead 0), waited 30 s so far')
        for t in (10, 400, 900, 2000):
            c.t = t
            self.assertIsNone(g.check(0.0))
        self.assertIn('waiting, not stalled', g.stream.getvalue())

    def test_a_wait_has_an_upper_bound(self):
        g, c = self.guard()
        g.line('waiting for a lease (memory)')
        c.t = S.WAIT_MAX_S - 1
        self.assertIsNone(g.check(0.0))
        c.t = S.WAIT_MAX_S + 61
        self.assertIsNotNone(g.check(0.0))

    def test_a_heartbeat_ends_a_wait(self):
        g, c = self.guard()
        g.line('gate-queue: queued behind 1 gates')
        g.line('[heartbeat] chim: x: still working, 1m (no output for 1m)')
        c.t = 61
        self.assertIsNotNone(g.check(0.0))

    def test_own_containers_only(self):
        self.assertTrue(S.own_name('amiwind-gate-suite-10645', '-10645'))
        self.assertTrue(S.own_name('amiwind-gate-stage-10645-source', '-10645'))
        self.assertFalse(S.own_name('amiwind-gate-suite-106450', '-10645'))
        self.assertFalse(S.own_name('aw-other-10645x', '-10645'))
        self.assertTrue(S.own_name('aw-build-run_1', 'aw-build-run_1'))

    def test_history_lengthens_the_limit(self):
        g, c = self.guard(history={'chim': 100})
        g.line('[heartbeat] chim: x: still working, 5m (no output for 1m 40s)')
        c.t = 200
        self.assertIsNone(g.check(0.0))          # 3 x 100 s = 300 s
        c.t = 301
        self.assertIn('stage chim', g.check(0.0))
        self.assertEqual(g.passed_history()['chim'], 100)

    def test_log_growth_is_progress(self):
        g, c = self.guard()
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 'x.log')
            Path(p).write_text('a')
            g.logs([p])
            c.t = 50
            Path(p).write_text('ab')
            g.logs([p])
            c.t = 100
            self.assertIsNone(g.check(0.0))


class UnderusedTests(unittest.TestCase):
    def test_under_half_the_planned_cores_for_five_minutes_is_flagged(self):
        clock = Clock()
        g = S.Guard('build x', limit_s=3600, clock=clock, stream=io.StringIO(), planned_cores=22)
        g.line('Check: reuse preflight')
        for t in range(0, 301, 30):
            clock.t = t
            g.line('still checking %d' % t)      # progress, so not a stall
            self.assertIsNone(g.check(100.0))     # 1 of 22 cores
        self.assertEqual(len(g.underused), 1)
        self.assertIn('1.0 of 22 planned cores', g.underused[0])
        self.assertIn('UNDERUSED', g.stream.getvalue())

    def test_using_its_cores_is_not_flagged(self):
        clock = Clock()
        g = S.Guard('build x', limit_s=3600, clock=clock, stream=io.StringIO(), planned_cores=22)
        for t in range(0, 900, 30):
            clock.t = t
            g.line('unit %d' % t)
            g.check(1800.0)                       # 18 cores
        self.assertEqual(g.underused, [])


class RunTests(unittest.TestCase):
    def run_step(self, code, limit=2):
        out = io.StringIO()
        killed = []
        with tempfile.TemporaryDirectory() as d:
            rc = S.run_watched([PY, '-c', code], log_path=os.path.join(d, 'step.log'), echo=False, name='fake',
                               containers=['aw-test-own'], limit_s=limit, cpu_probe=lambda: 0.0,
                               kill=lambda p, own, s: (killed.append(own), p.kill()), shell='',
                               history_path=os.path.join(d, 'h.json'), resume='aw request again', stream=out,
                               check_s=0.2)
        return rc, out.getvalue(), killed

    def test_stalled_fake_step_is_stopped_with_the_reason(self):
        rc, out, killed = self.run_step('import time; print("start", flush=True); time.sleep(60)')
        self.assertEqual(rc, S.STALL_EXIT)
        self.assertIn('FAILED FAST', out)
        self.assertIn('resume: aw request again', out)
        self.assertEqual(killed, [['aw-test-own']])

    def test_progressing_step_is_not_stopped(self):
        rc, out, killed = self.run_step(
            'import time\nfor i in range(8):\n    print(i, flush=True); time.sleep(0.5)\n', limit=2)
        self.assertEqual(rc, 0)
        self.assertEqual(killed, [])

    def test_waiting_step_reports_its_wait(self):
        rc, out, killed = self.run_step(
            'import time; print("waiting for a lease (memory)", flush=True); time.sleep(4)', limit=1)
        self.assertEqual(rc, 0)
        self.assertIn('waiting, not stalled', out)
        self.assertEqual(killed, [])

    def test_off_switch(self):
        os.environ['AW_STALL'] = 'off'
        try:
            rc, out, killed = self.run_step('import time; time.sleep(2)', limit=0.5)
        finally:
            del os.environ['AW_STALL']
        self.assertEqual(rc, 0)
        self.assertIn('OFF for this run', out)


if __name__ == '__main__':
    unittest.main()
