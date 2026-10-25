# SPDX-License-Identifier: GPL-3.0-only
"""PERSISTING MUST MEAN SCHEDULED, and why a bug is not fixed yet (the maintainer, 24 October 2026).

BUILD-ENGINE-SOURCE-KEY-BROAD-36 was seen again in five releases and never repaired; the same finding was then
registered a second time as new (BUILD-CHIM-KEY-ENGINE-SOURCES-49). tools/bug_register.py now lists the open bugs seen
in three releases or more with the reason each is not fixed (waiting_on "Lacks dependency: <system>", the maintainer's
deferral, or a place on the release TODO list), and `add` prints the closest open bugs and refuses a near-identical
title."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import bug_register as R  # noqa: E402


def bug(identifier, persists, state='open', **extra):
    return dict({'id': identifier, 'title': 'title of ' + identifier, 'state': state, 'persists_in': persists}, **extra)


class PersistingTests(unittest.TestCase):
    def test_releases_count_each_release_once(self):
        self.assertEqual(R.releases_of(bug('A-01', ['v0.0.36-dev3', 'v0.0.36', 'v0.0.45', 'v0.0.46-dev1'])),
                         ['0.0.36', '0.0.45', '0.0.46'])
        self.assertEqual(R.releases_of(bug('A-01', 'fixed in v0.0.51')), [])

    def test_a_bug_in_three_releases_needs_a_reason(self):
        bugs = [bug('KEY-BROAD-36', ['v0.0.36-dev3', 'v0.0.45', 'v0.0.46-dev1', 'v0.0.48-dev2', 'v0.0.50']),
                bug('MAGIC-29', ['v0.0.29', 'v0.0.30', 'v0.0.31'], waiting_on='Lacks dependency: magic'),
                bug('LATER-30', ['v0.0.30', 'v0.0.31', 'v0.0.32'], deferred='2026-10-24: after the interiors'),
                bug('TWO-40', ['v0.0.40', 'v0.0.41']),
                bug('DONE-33', ['v0.0.33', 'v0.0.34', 'v0.0.35'], state='fixed')]
        rows = {b['id']: reason for b, reason in R.long_persisting(bugs)}
        self.assertEqual(sorted(rows), ['KEY-BROAD-36', 'LATER-30', 'MAGIC-29'])
        self.assertIsNone(rows['KEY-BROAD-36'])
        self.assertEqual(rows['MAGIC-29'], 'Lacks dependency: magic')
        self.assertIn('deferred by the maintainer', rows['LATER-30'])
        scheduled = dict((b['id'], reason) for b, reason in R.long_persisting(bugs, '- [ ] 0.1 KEY-BROAD-36 (...)'))
        self.assertEqual(scheduled['KEY-BROAD-36'], 'on the release TODO list')
        # a longer ID that contains it is not it
        other = dict((b['id'], reason) for b, reason in R.long_persisting(bugs, 'XKEY-BROAD-36 KEY-BROAD-360'))
        self.assertIsNone(other['KEY-BROAD-36'])

    def test_the_reason_fields_are_checked(self):
        good = bug('A-01', ['v0.0.50'], waiting_on='Lacks dependency: MWScript function GetJournalIndex')
        self.assertEqual(R.validate_waiting(good, 'A-01'), [])
        self.assertTrue(R.validate_waiting(bug('A-01', [], waiting_on='DEPENDENCY MISSING'), 'A-01'))
        self.assertTrue(R.validate_waiting(bug('A-01', [], waiting_on='Lacks dependency: '), 'A-01'))
        self.assertTrue(R.validate_waiting(bug('A-01', [], deferred='later'), 'A-01'))
        self.assertEqual(R.validate_waiting(bug('A-01', [], deferred='2026-10-24: after Bloodmoon'), 'A-01'), [])
        self.assertTrue(R.validate_waiting(bug('A-01', [], state='fixed', waiting_on='Lacks dependency: x'), 'A-01'))

    def test_the_register_shows_what_a_bug_waits_on(self):
        rows = R.table([dict(bug('A-01', ['v0.0.50'], waiting_on='Lacks dependency: jail system'), severity='low',
                             found_in='v0.0.50', fixed_in=None, owner_accepted=None, status='Open.', report=None)])
        self.assertIn('| Waiting on |', rows)
        self.assertIn('| jail system |', rows)


class DuplicateTitleTests(unittest.TestCase):
    BUGS = [bug('BUILD-ENGINE-SOURCE-KEY-BROAD-36', [], title='Any engine source edit changes the keys of the chim '
                                                              'and world-flora stages'),
            bug('AUDIO-LOAD-29', [], title='Music crackles while a map loads'),
            bug('OLD-01', [], state='fixed', title='Any engine source edit changes the keys of the chim stage')]

    def test_the_closest_open_bug_comes_first(self):
        near = R.closest(self.BUGS, 'An engine source edit changes the keys of the chim stages')
        self.assertEqual(near[0][1]['id'], 'BUILD-ENGINE-SOURCE-KEY-BROAD-36')
        self.assertGreaterEqual(near[0][0], R.SAME_TITLE)
        self.assertNotIn('OLD-01', [b['id'] for _, b in near])     # fixed bugs are not candidates

    def test_a_different_finding_is_not_refused(self):
        near = R.closest(self.BUGS, 'The heart chamber does not load at 32 MB')
        self.assertTrue(all(score < R.SAME_TITLE for score, _ in near))


if __name__ == '__main__':
    unittest.main()
