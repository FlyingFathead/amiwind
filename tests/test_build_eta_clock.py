"""The builder's finish times show UTC and the host's local time (BUILD-ETA-CLOCK-UTC-ONLY-46)."""

from pathlib import Path
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))

import build_progress  # noqa: E402


RUNNING = {'status': 'running', 'percent': 77.3, 'eta_seconds': 1260, 'eta_at': '2026-10-20T12:53:09+00:00',
           'eta_basis': 'history', 'stages': [{'name': 'chim', 'status': 'running', 'remaining_seconds': 228}],
           'counts': {}, 'run': 'r'}


class EtaClockTests(unittest.TestCase):
    def test_utc_and_local_with_host_offset(self):
        with patch.dict(os.environ, {'AMIWIND_LOCAL_UTC_OFFSET': '+0300'}):
            self.assertEqual(build_progress.clock_text('2026-10-20T12:53:09+00:00'),
                             '12:53:09 UTC / 15:53:09 local (+0300)')
            self.assertIn('(at 12:53:09 UTC / 15:53:09 local (+0300))', build_progress.eta_line(RUNNING))
            head = build_progress.status_lines(RUNNING)[0]
            self.assertIn('at 12:53:09 UTC / 15:53:09 local (+0300), history', head)

    def test_negative_offset_and_colon_form(self):
        with patch.dict(os.environ, {'AMIWIND_LOCAL_UTC_OFFSET': '-05:30'}):
            self.assertEqual(build_progress.clock_text('2026-10-20T02:00:00+00:00'),
                             '02:00:00 UTC / 20:30:00 local (-0530)')

    def test_utc_host_shows_utc_only(self):
        with patch.dict(os.environ, {'AMIWIND_LOCAL_UTC_OFFSET': '+0000'}):
            self.assertEqual(build_progress.clock_text('2026-10-20T15:53:09+03:00'), '12:53:09 UTC')

    def test_bad_input_never_fails(self):
        with patch.dict(os.environ, {'AMIWIND_LOCAL_UTC_OFFSET': 'Europe/Helsinki'}):
            self.assertTrue(build_progress.clock_text('2026-10-20T12:53:09+00:00').startswith('12:53:09 UTC'))
        self.assertEqual(build_progress.clock_text(''), '')
        self.assertIsInstance(build_progress.clock_text('not a time at all'), str)


if __name__ == '__main__':
    unittest.main()
