# SPDX-License-Identifier: GPL-3.0-only
"""A closed bug that comes back is a regression, never a new bug (REGISTER-REGRESSION-HANDLER-52).

The maintainer, 25 October 2026: searches go through BOTH open and closed bugs, "so as to NOT open up old bugs as new
ones if it's something that has been closed but has been regressed", and "a regression handler so to speak": "oh
shit, this bug was marked as closed then, but now it's open again". tools/bug_register.py: `find` searches the whole
register (archives included), `add` refuses a title that nearly matches a fixed or closed bug, and `reopen` puts the
bug back to open with an entry in its regressions list, one severity step up."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import bug_register as R  # noqa: E402


def bug(identifier, title, state='fixed', **extra):
    b = {'id': identifier, 'title': title, 'state': state, 'fixed_in': 'v0.0.45' if state == 'fixed' else None,
         'owner_accepted': None, 'status': 'Fixed in v0.0.45.', 'severity': 'medium', 'severity_reason': 'Holes.',
         'persists_in': 'fixed in v0.0.45', 'reported_by': 'owner'}
    b.update(extra)
    return b


class RegressionTests(unittest.TestCase):
    def test_the_search_finds_fixed_and_closed_bugs(self):
        bugs = [bug('CHUNK-HOLES-33', 'Balmora chunks fail to load and leave holes'),
                bug('OPEN-40', 'Something else entirely', state='open')]
        self.assertEqual(R.closest(bugs, 'Balmora chunks leave holes'), [])  # open only, as before
        found = R.closest(bugs, 'Balmora chunks leave holes', states=R.STATES)
        self.assertEqual(found[0][1]['id'], 'CHUNK-HOLES-33')
        self.assertGreaterEqual(found[0][0], R.SAME_TITLE)

    def test_reopen_records_the_return_and_raises_the_severity(self):
        b = bug('CHUNK-HOLES-33', 'Balmora chunks fail to load and leave holes')
        entry = R.reopen(b, 'v0.0.52-dev1', '2026-10-26 10:00 +0200', by='abc1234', note='holes at Balmora again')
        self.assertEqual(entry, {'version': 'v0.0.52-dev1', 'at': '2026-10-26 10:00 +0200', 'was': 'fixed',
                                 'fixed_in': 'v0.0.45', 'by': 'abc1234', 'note': 'holes at Balmora again'})
        self.assertEqual((b['state'], b['fixed_in'], b['owner_accepted']), ('open', None, None))
        self.assertEqual(b['severity'], 'high')
        self.assertTrue(b['severity_reason'].startswith('Regressed in v0.0.52-dev1 (was medium)'))
        self.assertTrue(b['status'].startswith('REGRESSED in v0.0.52-dev1 (fixed in v0.0.45 before)'))
        self.assertEqual(b['persists_in'], ['v0.0.52-dev1'])
        self.assertEqual(R.came_back(b), 'in v0.0.52-dev1 (fixed in v0.0.45 before)')
        self.assertEqual(R.validate_regressions(b, b['id']), [])

    def test_only_a_fixed_or_closed_bug_can_come_back(self):
        with self.assertRaises(ValueError):
            R.reopen(bug('OPEN-40', 'x', state='open'), 'v0.0.52', '2026-10-26')

    def test_a_critical_bug_stays_critical_and_a_closed_one_says_so(self):
        b = bug('BAD-41', 'x', state='closed', severity='critical')
        R.reopen(b, 'v0.0.52', '2026-10-26')
        self.assertEqual(b['severity'], 'critical')
        self.assertEqual(R.came_back(b), 'in v0.0.52 (closed before)')

    def test_two_returns_are_both_kept_in_time_order(self):
        b = bug('BACK-AGAIN-36', 'x')
        R.reopen(b, 'v0.0.52', '2026-10-26')
        b.update(state='fixed', fixed_in='v0.0.53')
        R.reopen(b, 'v0.0.55', '2026-11-02')
        self.assertEqual([r['version'] for r in b['regressions']], ['v0.0.52', 'v0.0.55'])
        self.assertEqual(R.came_back(b), 'in v0.0.52 (fixed in v0.0.45 before); in v0.0.55 (fixed in v0.0.53 before)')

    def test_the_regressions_field_is_checked(self):
        self.assertEqual(R.validate_regressions({}, 'A-01'), [])
        self.assertTrue(R.validate_regressions({'regressions': []}, 'A-01'))
        self.assertTrue(R.validate_regressions({'regressions': [{'version': 'v0.0.52', 'at': '2026-10-26'}]}, 'A-01'))
        self.assertTrue(R.validate_regressions({'regressions': [
            {'version': 'v0.0.52', 'at': '2026-10-26', 'was': 'open', 'fixed_in': None}]}, 'A-01'))
        self.assertTrue(R.validate_regressions({'regressions': [
            {'version': 'v0.0.52', 'at': '2026-10-27', 'was': 'fixed', 'fixed_in': 'v0.0.45'},
            {'version': 'v0.0.53', 'at': '2026-10-26', 'was': 'fixed', 'fixed_in': 'v0.0.52'}]}, 'A-01'))

    def test_a_regression_needs_a_reason_of_record_at_once(self):
        # the release guard runs bug_register.py persisting --fail: an open regression without a reason stops a
        # release even when it was seen in fewer than LONG_PERSISTING releases
        back = bug('BACK-33', 'x')
        R.reopen(back, 'v0.0.52', '2026-10-26')
        fresh = bug('NEW-52', 'y', state='open', persists_in=['v0.0.52'])
        rows = dict((b['id'], reason) for b, reason in R.long_persisting([back, fresh]))
        self.assertEqual(rows, {'BACK-33': None})
        back['deferred'] = '2026-10-26: after the light audit'
        self.assertIn('deferred by the maintainer', dict((b['id'], r) for b, r in R.long_persisting([back]))['BACK-33'])
        self.assertIn('on the release TODO list',
                      dict((b['id'], r) for b, r in R.long_persisting([dict(back, deferred=None)],
                                                                        '- [ ] BACK-33 regression'))['BACK-33'])

    def test_the_page_shows_that_it_came_back(self):
        b = bug('CHUNK-HOLES-33', 'Balmora chunks fail to load and leave holes', family='chim-streamer',
                where='CHIM', reproduction='always', duplicate_of=None, found_in='v0.0.33', found_date='2026-10-09')
        R.reopen(b, 'v0.0.52', '2026-10-26')
        rows = R.parse_fact_table(R.facts_table(b, {b['id']: b}, {}))
        self.assertEqual(rows['Came back (regression)'], 'in v0.0.52 (fixed in v0.0.45 before)')


if __name__ == '__main__':
    unittest.main()
