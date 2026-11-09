"""The player view's flow (tools/player_view_schedule.py; BUILD-PLAYER-VIEW-UNDERUSED-48, NPC-BAKE-FALLBACK-62).

1. The fitting tries the flow runs are exactly the tries prepare_player_view._fit_body makes, in its order, and the
   first that fits is the body _fit_body returns (every pattern of fit / no fit / error over the six tries, with and
   without the dev1 body rules set): the flow's result is byte for byte the bake's.
2. The split follows the fitting code it was written against (FIT_SOURCES_SHA256): a change to _fit_body or
   _fit_body_rules fails here first, and the flow then runs every body whole.
3. The schedule on the unit times the v0.0.62 release build recorded (no bake): the flow ends the step well before
   the two maps did, and a body known not to fit starts at its fallback.
"""
import contextlib
import io
import itertools
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))

import player_view_schedule as flow  # noqa: E402

# Unit seconds the v0.0.62 release build 7011540 recorded (cache item-costs/player-view.json, 2026-11-08), and per
# body how many fitting tries it ran (its log: "no fit with the whole hair share", "no fit with the locked head
# reducer", "BAKE-FALLBACK ... v0.0.62-dev1 body rules" lines); the last try it ran fitted.
BODY = {'argonian female': (4537.144, 3), 'argonian male': (4838.566, 3), 'breton female': (1343.305, 1),
        'breton male': (3117.992, 2), 'dark elf female': (1923.22, 1), 'dark elf male': (4505.571, 4),
        'high elf female': (2158.223, 1), 'high elf male': (2538.818, 1), 'imperial female': (1857.046, 1),
        'imperial male': (2912.017, 2), 'khajiit female': (4853.959, 6), 'khajiit male': (4902.232, 3),
        'nord female': (1498.875, 1), 'nord male': (3419.501, 2), 'orc female': (1859.46, 1),
        'orc male': (4901.494, 3), 'redguard female': (1316.408, 1), 'redguard male': (3275.834, 2),
        'wood elf female': (1418.547, 1), 'wood elf male': (4717.602, 4)}
SWIM = {'argonian female': 118.357, 'argonian male': 157.082, 'breton female': 83.772, 'breton male': 148.804,
        'dark elf female': 85.789, 'dark elf male': 37.272, 'high elf female': 101.502, 'high elf male': 159.843,
        'imperial female': 95.573, 'imperial male': 107.836, 'khajiit female': 85.861, 'khajiit male': 91.743,
        'nord female': 72.132, 'nord male': 124.208, 'orc female': 83.118, 'orc male': 138.625,
        'redguard female': 55.358, 'redguard male': 181.574, 'wood elf female': 74.686, 'wood elf male': 130.511}
INVENTORY = {'argonian female': 135.814, 'argonian male': 115.193, 'breton female': 98.224, 'breton male': 162.355,
             'dark elf female': 113.778, 'dark elf male': 62.385, 'high elf female': 163.822,
             'high elf male': 150.882, 'imperial female': 97.158, 'imperial male': 161.78,
             'khajiit female': 96.838, 'khajiit male': 135.327, 'nord female': 116.619, 'nord male': 128.962,
             'orc female': 75.95, 'orc male': 148.805, 'redguard female': 81.021, 'redguard male': 113.206,
             'wood elf female': 145.891, 'wood elf male': 158.577}
TORCH = {'argonian female': 95.748, 'argonian male': 122.315, 'breton female': 74.683, 'breton male': 112.762,
         'dark elf female': 62.589, 'dark elf male': 800.084, 'high elf female': 103.655, 'high elf male': 121.197,
         'imperial female': 91.188, 'imperial male': 98.738, 'khajiit female': 80.991, 'khajiit male': 126.14,
         'nord female': 47.131, 'nord male': 78.3, 'orc female': 64.712, 'orc male': 120.42,
         'redguard female': 63.755, 'redguard male': 89.403, 'wood elf female': 60.103, 'wood elf male': 90.388}
TRIES = 6
WORKERS = 24
MEASURED_MAPS_SECONDS = 5716.5      # "Player view: 80 units (0 from the unit cache, 80 made) in 5716.5 s" (7011540)


def _units(known=False):
    """Planner units of the release build's player view; KNOWN: every body starts at the try that fitted."""
    rows, index = [], 0
    names = sorted(BODY)
    for n, race in enumerate(names):
        rows.append((n, 'body ' + race, TRIES, BODY[race][1] - 1 if known else 0, 3 * len(names) + n))
    for n, race in enumerate(names):
        rows.append((len(names) + n, 'swim ' + race, None, 0, None))
        rows.append((2 * len(names) + n, 'inventory ' + race, None, 0, None))
        rows.append((3 * len(names) + n, 'torch ' + race, None, 0, None))
    return rows


def _seconds(name, number):
    kind, race = name.split(' try')[0].split(' ', 1)
    if kind == 'body':
        total, ran = BODY[race]
        return total / ran            # each try of a body: its recorded time over the tries it ran
    return {'swim': SWIM, 'inventory': INVENTORY, 'torch': TORCH}[kind][race]


def _likely(name):
    """The cost history after one build with the flow: every try a body ran is in it."""
    if ' try' not in name:
        return False
    base, number = name.split(' try')
    return int(number) <= BODY[base.split(' ', 1)[1]][1]


def _fits(index, number):
    race = sorted(BODY)[index]
    return number == BODY[race][1] - 1 or number >= BODY[race][1]


class TriesFollowFitBody(unittest.TestCase):

    def test_split_follows_the_fitting_code(self):
        self.assertEqual(flow.fit_sources_digest(), flow.FIT_SOURCES_SHA256,
                         'prepare_player_view._fit_body or _fit_body_rules changed: bring fit_tries() and '
                         'FIT_SOURCES_SHA256 in tools/player_view_schedule.py up to date (until then every body '
                         'runs whole)')

    def test_first_fitting_try_is_what_fit_body_returns(self):
        import prepare_player_view as view
        from npc_geometry import DEV1_BODY_RULES
        names = sorted(set(DEV1_BODY_RULES) | {'AMIWIND_NPC_HAIR_SHARE', 'AMIWIND_NPC_HEAD_REDUCER'})
        saved_env = {k: os.environ.get(k) for k in names}
        saved_search = view._fit_body_search
        try:
            for dev1_set, hair, head in itertools.product((False, True), ('', 'plain'), ('', 'default')):
                for k in names:
                    os.environ.pop(k, None)
                if dev1_set:
                    os.environ.update(DEV1_BODY_RULES)
                if hair:
                    os.environ['AMIWIND_NPC_HAIR_SHARE'] = hair
                if head:
                    os.environ['AMIWIND_NPC_HEAD_REDUCER'] = head
                before = {k: os.environ.get(k) for k in names}
                tries = flow.fit_tries()
                signatures = [tuple(sorted(dict(before, **dict(env)).items(), key=str)) for env in tries]
                self.assertEqual(len(set(signatures)), len(signatures))
                for pattern in itertools.product(('fit', 'none', 'error'), repeat=len(tries)):
                    outcome = dict(zip(signatures, pattern))

                    def search(identifier, *args):
                        now = tuple(sorted({k: os.environ.get(k) for k in names}.items(), key=str))
                        what = outcome.get(now, 'none')
                        if what == 'fit':
                            return ('body', now)
                        if what == 'error':
                            raise ValueError(identifier + ': Player body bake omitted face-part labels')
                        raise ValueError(identifier + ': no body fits the existing budgets (x)')
                    view._fit_body_search = search
                    try:
                        with contextlib.redirect_stdout(io.StringIO()):
                            expected = ('ok', view._fit_body('b', 1, 2, 3, 4, 5))
                    except ValueError as error:
                        expected = ('error', str(error))
                    self.assertEqual({k: os.environ.get(k) for k in names}, before)
                    got = None
                    for env in tries:
                        try:
                            got = ('ok', flow.fit_once(env, 'b', 1, 2, 3, 4, 5))
                            break
                        except flow._NoFitSignal as error:
                            got = ('error', str(error))
                        except ValueError as error:
                            got = ('error', str(error))
                            break
                    self.assertEqual({k: os.environ.get(k) for k in names}, before)
                    self.assertEqual(got, expected, (dev1_set, hair, head, pattern))
        finally:
            view._fit_body_search = saved_search
            for k, v in saved_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


class PlannerOrder(unittest.TestCase):

    def test_later_try_waits_for_the_earlier_ones(self):
        planner = flow.Planner(lambda name: 1.0)
        planner.add(0, 'body x', 3)
        self.assertEqual(planner.take(), (0, 0))
        self.assertEqual(planner.take(), (0, 1))          # an idle worker: the next try
        self.assertEqual(planner.take(), (0, 2))
        self.assertIsNone(planner.done(0, 2, 'third'))    # fits, but tries 1 and 2 have not said
        self.assertEqual(planner.done(0, 0, flow.NoFit('no'))[0], 'try')
        self.assertEqual(planner.done(0, 1, flow.NoFit('no')), ('kept', 'third', 2))
        self.assertFalse(planner.open)

    def test_earlier_fit_drops_the_later_tries(self):
        planner = flow.Planner(lambda name: 1.0)
        planner.add(0, 'body x', 3)
        planner.take(), planner.take()
        self.assertEqual(planner.done(0, 0, 'first'), ('kept', 'first', 0))
        self.assertEqual(planner.orphans(), [(0, 1)])
        self.assertIsNone(planner.done(0, 1, 'second'))

    def test_error_in_order_fails_the_body(self):
        planner = flow.Planner(lambda name: 1.0)
        planner.add(0, 'body x', 2)
        planner.take()
        self.assertEqual(planner.done(0, 0, flow.Failed('ValueError: bad')), ('failed', 'ValueError: bad', 0))

    def test_every_try_no_fit_fails_with_the_last_message(self):
        planner = flow.Planner(lambda name: 1.0)
        planner.add(0, 'body x', 2)
        planner.take()
        planner.done(0, 0, flow.NoFit('a'))
        self.assertEqual(planner.take(), (0, 1))
        self.assertEqual(planner.done(0, 1, flow.NoFit('b')), ('failed', 'ValueError: b', 1))


class FlowRunsProcesses(unittest.TestCase):

    def test_every_failing_unit_is_named_and_no_process_is_left(self):
        import multiprocessing
        tasks = [('/nonexistent-game-data', b'\0' * 768, race, female) for race in ('Breton', 'Nord')
                 for female in (False, True)]
        swim = [t + ({'model': 'progs/body/x.mdl'},) for t in tasks]
        lines = []
        with self.assertRaises(ValueError) as caught:
            flow.run_view(tasks, swim, None, 3, log=lambda *a, **k: lines.append(a[0]))
        self.assertIn('12 units failed', str(caught.exception))
        self.assertIn('body Breton male', str(caught.exception))
        self.assertTrue(any('[12/16]' in line for line in lines), lines[-3:])
        for child in multiprocessing.active_children():
            child.join(10)
        self.assertEqual(multiprocessing.active_children(), [])


class ReleaseBuildSchedule(unittest.TestCase):
    """The schedule on the v0.0.62 release build's recorded unit times, 24 workers."""

    def setUp(self):
        names = sorted(BODY)
        self.first = [('body ' + r, BODY[r][0]) for r in names] + [('swim ' + r, SWIM[r]) for r in names] + \
            [('inventory ' + r, INVENTORY[r]) for r in names]
        self.torch = [('torch ' + r, TORCH[r]) for r in names]

    def test_the_two_maps_model_the_measured_step(self):
        maps, _ = flow.simulate_maps(self.first, self.torch, WORKERS)
        self.assertLess(abs(maps - MEASURED_MAPS_SECONDS) / MEASURED_MAPS_SECONDS, 0.05, maps)

    def test_the_flow_shortens_the_tail(self):
        maps, _ = flow.simulate_maps(self.first, self.torch, WORKERS)
        # the first build with the flow (no try timed yet), a build after a bake change (the tries of the last build
        # in the cost history), a build with the bake unchanged (the fit table)
        first, _, trace = flow.simulate(_units(), WORKERS, _seconds, _fits)
        again, _, _ = flow.simulate(_units(), WORKERS, _seconds, _fits, likely=_likely)
        known, _, _ = flow.simulate(_units(known=True), WORKERS, _seconds, _fits)
        print('\nplayer view on the v0.0.62 release unit times, %d workers: two maps %.0f s; flow %.0f s (first), '
              '%.0f s (tries timed), %.0f s (fit table)' % (WORKERS, maps, first, again, known))
        self.assertLess(first, 0.8 * maps)
        self.assertLess(again, 0.65 * maps)
        self.assertLess(known, 0.5 * maps)
        # no stretch of over 10 minutes with a single busy worker
        one = [t for t, n in trace if n <= 1]
        self.assertTrue(not one or first - min(one) < 600, (first, one[:3]))


if __name__ == '__main__':
    unittest.main()
