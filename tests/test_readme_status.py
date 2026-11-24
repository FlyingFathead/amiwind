"""The main page's status must not name a date or version older than the release line in VERSION.

A status heading with a date (or a version) goes stale the day the next snapshot is cut; the date of the page lives in the
italic "Last updated with AmiWind ..." line, which must name the current VERSION.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MONTHS = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october',
          'november', 'december']
HEADING = re.compile(r'^#{1,3}\s+Where AmiWind stands(.*)$', re.M)
LAST_UPDATED = re.compile(r'_Last updated with AmiWind v([0-9][^\s(]*) \((\d{1,2}) ([A-Za-z]+) (\d{4})\)\._')
VERSION_IN_TEXT = re.compile(r'v?(\d+)\.(\d+)\.(\d+)')
DATE_IN_TEXT = re.compile(r'(\d{1,2}) ([A-Za-z]+) (\d{4})')


def release_line(text):
    m = VERSION_IN_TEXT.search(text)
    return tuple(int(x) for x in m.groups()) if m else None


def date_key(day, month, year):
    return (int(year), MONTHS.index(month.lower()) + 1, int(day))


def problems(readme, version):
    """The reasons a README text's status heading is stale against the VERSION text, empty when it is not."""
    out = []
    found = HEADING.search(readme)
    if not found:
        return ['no "Where AmiWind stands" heading']
    tail = found.group(1)
    current = release_line(version)
    named = release_line(tail)
    if named and current and named < current:
        out.append('the status heading names version %s, older than the release line %s' % (
            '.'.join(map(str, named)), '.'.join(map(str, current))))
    stamp = LAST_UPDATED.search(readme)
    if not stamp:
        out.append('no "Last updated with AmiWind" line')
        return out
    if current and release_line(stamp.group(1)) != current:
        out.append('the "Last updated" line names v%s, VERSION is %s' % (stamp.group(1), version.strip()))
    day = DATE_IN_TEXT.search(tail)
    if day and day.group(2).lower() in MONTHS:
        if date_key(*day.groups()) < date_key(*stamp.group(2, 3, 4)):
            out.append('the status heading names the date %s, older than the page date %s %s %s' % (
                day.group(0), *stamp.group(2, 3, 4)))
    return out


class ReadmeStatusTest(unittest.TestCase):
    def test_readme_status_is_current(self):
        readme = (ROOT / 'README.md').read_text(encoding='utf-8')
        version = (ROOT / 'VERSION').read_text(encoding='utf-8')
        self.assertEqual(problems(readme, version), [])

    def test_refuses_todays_old_heading(self):
        old = ('_Last updated with AmiWind v0.0.68-dev11 (23 November 2026)._\n\n'
               '## Where AmiWind stands (19 November 2026)\n')
        self.assertTrue(problems(old, '0.0.68-dev11\n'))

    def test_refuses_an_older_version_in_the_heading(self):
        old = ('_Last updated with AmiWind v0.0.68-dev11 (23 November 2026)._\n\n'
               '## Where AmiWind stands (v0.0.67)\n')
        self.assertTrue(problems(old, '0.0.68-dev11\n'))

    def test_refuses_a_stale_last_updated_line(self):
        old = ('_Last updated with AmiWind v0.0.67 (19 November 2026)._\n\n## Where AmiWind stands\n')
        self.assertTrue(problems(old, '0.0.68-dev11\n'))

    def test_accepts_a_heading_without_a_date(self):
        ok = ('_Last updated with AmiWind v0.0.68-dev11 (23 November 2026)._\n\n## Where AmiWind stands\n')
        self.assertEqual(problems(ok, '0.0.68-dev11\n'), [])


if __name__ == '__main__':
    unittest.main()
