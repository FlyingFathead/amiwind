# SPDX-License-Identifier: GPL-3.0-only
"""The image step's payload preflight reads only and reports the same errors as the checks it calls."""
import contextlib
import hashlib
import io
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import build_aga  # noqa: E402
import payload_preflight  # noqa: E402


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

    def test_catalogues_not_yet_installed_are_planned_from_the_harvest_source(self):
        """The image step installs the harvest catalogues late (after the BSP optimizer); at its start the
        preflight plans them from the harvest source, so the rc1c error is found in the first minute."""
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as temp:
            id1 = stage(temp)/'boot/id1'
            for path in id1.glob('harvest-*.txt'):
                path.unlink()
            removed = {'maps/intro_docks.bsp'}
            self.assertEqual(payload_preflight.check_harvest(id1, [], removed), 0)      # nothing staged, no source
            with patch.object(payload_preflight, 'planned_catalogues', return_value=['intro_docks', 'town']) as plan:
                with self.assertRaisesRegex(ValueError, 'Harvest catalogue has no matching map: harvest-intro_docks.txt'):
                    payload_preflight.check_harvest(id1, [], removed, 'harvest-source', 'data')
                plan.assert_called_once_with(id1, 'harvest-source', 'data')
                self.assertEqual(payload_preflight.check_harvest(id1, [], set(), 'harvest-source', 'data'), 2)
            self.assertEqual(sorted(p.name for p in id1.glob('harvest-*')), [])        # placeholders never staged

    def test_interior_sections_run_and_may_not_bind_removed_maps(self):
        from unittest.mock import patch
        import interior_sections
        with tempfile.TemporaryDirectory() as temp:
            id1 = stage(temp)/'boot/id1'
            self.assertEqual(payload_preflight.check_interior_sections(id1, set()), 0)   # no section table
            entries = [('interior-sections.txt', 'a'), ('maps/town.bsp', 'b')]
            with patch.object(interior_sections, 'fingerprint_entries', return_value=entries):
                self.assertEqual(payload_preflight.check_interior_sections(id1, {'maps/other.bsp'}), 2)
                with self.assertRaisesRegex(ValueError, 'bind files the image removes: maps/town.bsp'):
                    payload_preflight.check_interior_sections(id1, {'maps/town.bsp'})
            with patch.object(interior_sections, 'fingerprint_entries', side_effect=ValueError('Missing section content: x')):
                _, _, error = run_quiet(stage(Path(temp)/'second'))
            self.assertIn('interior-sections: Missing section content: x', str(error))

    def test_a_chim_town_from_the_game_data_needs_no_legacy_inputs(self):
        """CHIM-LEGACY-CHAIN-33: a town the chim-town stage made has no legacy region maps; its frame map takes
        the chim-town entities, so the preflight does not ask for them (the Temple sandbox stopped there)."""
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as temp:
            id1 = stage(temp)/'boot/id1'
            (id1/'vivec_temple-regions.txt').write_text('x', encoding='ascii')
            with patch('build_aga.chim_world_receipt', return_value=({}, ['vivec_temple'])),                     patch('chim.frame_map.region_table', return_value=((0, 0, 0), [('vp000', None), ('vp001', None)])):
                with self.assertRaisesRegex(ValueError, 'CHIM frame map inputs are not staged: maps/vp000.bsp'):
                    payload_preflight.check_chim_inputs(id1, Path(temp)/'w')
                payload_preflight.check_chim_inputs(id1, Path(temp)/'w', chim_towns={'vivec_temple'})


if __name__ == '__main__':
    unittest.main()


class FileFormatTests(unittest.TestCase):
    """ANIMKIT-IMAGE-FORMATS-35: the image step's palette overlay knows every staged format, checked first."""

    def test_kit_files_are_known_and_a_new_type_fails_in_the_preflight(self):
        from sky_palette_overlay import unknown_formats
        self.assertEqual(unknown_formats(['arena/f08c7f92da6db.anm', 'progs/m.tag', 'progs/m.mdl', 'maps/a.bsp',
                                          'gfx/palette.lmp', 'save-content.bin', 'sound/a.wav']), [])
        self.assertEqual(unknown_formats(['progs/new.xyz', 'README']), ['progs/new.xyz', 'README'])
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp)
            (id1 / 'arena').mkdir()
            (id1 / 'arena' / 'f08c7f92da6db.anm').write_text('idle:0:8:0.1500\n', encoding='ascii')
            payload_preflight.check_file_formats(id1)
            (id1 / 'arena' / 'x.newkind').write_bytes(b'1')
            with self.assertRaisesRegex(ValueError, 'x.newkind'):
                payload_preflight.check_file_formats(id1)
