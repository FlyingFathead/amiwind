# SPDX-License-Identifier: GPL-3.0-only
"""The image step's payload preflight reads only and reports the same errors as the checks it calls."""
import contextlib
import hashlib
import io
from pathlib import Path
import tempfile
import unittest

import build_aga
import payload_preflight


def snapshot(root):
    return {p.relative_to(root).as_posix(): (hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else 'dir',
                                             p.stat().st_mtime_ns)
            for p in sorted(Path(root).rglob('*'))}


def stage(base):
    """A small staged payload: out/boot with an engine stand-in, two maps, a harvest catalogue each."""
    out = Path(base)/'image'
    id1 = out/'boot/id1'
    (id1/'maps').mkdir(parents=True)
    (out/'boot/AmiWind').write_bytes(b'\0engine')
    for name in ('town', 'intro_docks'):
        (id1/'maps'/(name+'.bsp')).write_bytes(b'\0bsp '+name.encode())
        (id1/('harvest-'+name+'.txt')).write_bytes(b'AWH1 0 0 0\n')
    (id1/'readme.txt').write_text('plain text\n', encoding='ascii', newline='\n')
    return out


def run_quiet(out, **options):
    text = io.StringIO()
    with contextlib.redirect_stdout(text):
        try:
            return payload_preflight.run(out, **options), text.getvalue(), None
        except ValueError as exc:
            return None, text.getvalue(), exc


class PayloadPreflightTests(unittest.TestCase):
    def test_reads_only_and_prints_one_summary_line(self):
        with tempfile.TemporaryDirectory() as temp:
            out = stage(temp)
            before = snapshot(Path(temp))
            report, text, error = run_quiet(out, jobs=4)
            self.assertIsNone(error)
            self.assertEqual(snapshot(Path(temp)), before)             # no file changed, added or removed
            self.assertRegex(text, r'^Payload preflight: \d+ checks, 0 errors, [0-9.]+ s\n$')
            self.assertEqual(report['errors'], [])
            self.assertEqual(report['results']['harvest-catalogues'], 2)
            self.assertEqual(report['results']['disk-layout']['drives'], 1)

    def test_bad_harvest_catalogue_fails_with_the_image_step_message(self):
        with tempfile.TemporaryDirectory() as temp:
            out = stage(temp)
            id1 = out/'boot/id1'
            (id1/'harvest-nowhere.txt').write_bytes(b'AWH1 0 0 0\n')
            with self.assertRaises(ValueError) as direct:
                build_aga.harvest_fingerprint_entries(id1)
            before = snapshot(Path(temp))
            _, text, error = run_quiet(out)
            self.assertIsNotNone(error)
            self.assertIn('harvest-catalogues: ' + str(direct.exception), str(error))
            self.assertIn('Harvest catalogue has no matching map: harvest-nowhere.txt', str(error))
            self.assertIn(', 1 errors, ', text)
            self.assertEqual(snapshot(Path(temp)), before)

    def test_every_error_is_listed_together(self):
        with tempfile.TemporaryDirectory() as temp:
            out = stage(temp)
            id1 = out/'boot/id1'
            (id1/'harvest-nowhere.txt').write_bytes(b'AWH1 0 0 0\n')
            (id1/('x'*31+'.txt')).write_bytes(b'long name\n')
            _, _, error = run_quiet(out)
            self.assertIn('harvest-catalogues:', str(error))
            self.assertIn('payload-names:', str(error))
            self.assertIn('found 2 error(s)', str(error))

    def test_harvest_runs_on_the_planned_chim_map_set(self):
        """The image removes a CHIM town's legacy special map and writes its frame map later: the preflight
        sees that final set (CHIM-HARVEST-SPECIALS-33 failed only at the end of the image step)."""
        with tempfile.TemporaryDirectory() as temp:
            id1 = stage(temp)/'boot/id1'
            removed = {'maps/intro_docks.bsp'}
            self.assertEqual(payload_preflight.check_harvest(id1, ['intro_docks-chim'], removed), 1)
            with self.assertRaisesRegex(ValueError, 'Harvest catalogue has no matching map: harvest-intro_docks.txt'):
                payload_preflight.check_harvest(id1, [], removed)
            self.assertTrue((id1/'maps/intro_docks.bsp').is_file())


if __name__ == '__main__':
    unittest.main()
