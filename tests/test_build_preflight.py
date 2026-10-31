"""Build preflight (BUILD-CACHE-OWNER-FAILS-STAGE-34): seconds-long checks before any stage, each with its fix."""
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_preflight  # noqa: E402


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name) / 'workspace'
        (self.workspace / 'cache' / 'chim-units' / 'frame').mkdir(parents=True)
        (self.workspace / 'cache' / 'chim-units' / 'frame' / 'x.pickle').write_bytes(b'x')
        self.data = Path(self.temp.name) / 'Data Files'
        self.data.mkdir()
        (self.data / 'Morrowind.esm').write_bytes(b'TES3')

    @unittest.skipUnless(hasattr(os, 'geteuid') and os.geteuid() != 0, 'POSIX owners, not root')
    def test_clean_workspace_passes(self):
        self.assertEqual(build_preflight.run(self.workspace, self.data, minimum_gib=0), [])

    @unittest.skipUnless(hasattr(os, 'geteuid'), 'POSIX owners')
    def test_entries_of_another_user_fail_with_the_chown_fix(self):
        problems = build_preflight.cache_problems(self.workspace / 'cache', uid=os.geteuid() + 4242)
        self.assertEqual(len(problems), 1)
        self.assertIn('owned by another user', problems[0])
        self.assertIn(f'chown -R {os.geteuid() + 4242}:', problems[0])

    def test_free_space_minimum(self):
        problems = build_preflight.free_space_problems(self.workspace, minimum_gib=10 ** 9)
        self.assertEqual(len(problems), 1)
        self.assertIn('GiB needed', problems[0])
        self.assertEqual(build_preflight.free_space_problems(self.workspace / 'not-yet', minimum_gib=0), [])

    def test_a_filling_disk_warns_and_names_the_collector(self):
        # BUILD-CACHE-NO-RETENTION-55: old runs and cache entries piled up for weeks and nothing said so.
        warning = build_preflight.fill_warning(self.workspace, share=0.0)  # any disk is at least 0 % full
        self.assertIn('[disk] WARNING: the build disk is', warning)
        self.assertIn('python tools/build_gc.py plan ' + str(self.workspace), warning)
        self.assertIn('--delete', warning)
        self.assertIsNone(build_preflight.fill_warning(self.workspace, share=1.01))  # never over 100 % full
        self.assertIsNotNone(build_preflight.fill_warning(self.workspace / 'not-yet' / 'deeper', share=0.0))

    def test_too_little_room_stops_every_build(self):
        # BUILD-DISK-NEED-UNKNOWN-52: a tester's public build filled its disk halfway; every build, development
        # ones too, stops before its first stage, against at least 35 GiB by default
        # (v0.0.53: the need is the last known good build's figure plus the margin, checked right after the options are
        # read: tools/disk_need.py, tests/test_disk_need.py)
        self.assertGreaterEqual(build_preflight.DEFAULT_MIN_FREE_GIB, 35)
        text = (ROOT / 'tools' / 'build.py').read_text(encoding='utf-8')
        self.assertIn("__import__('disk_need').entry(args, p, storage_pool_dir)", text)
        self.assertNotIn('development builds only warn', text)

    def test_game_data_checked(self):
        self.assertEqual(build_preflight.data_problems(self.data), [])
        self.assertIn('does not exist', build_preflight.data_problems(self.data / 'missing')[0])
        (self.data / 'Morrowind.esm').unlink()
        self.assertIn('no Morrowind.esm', build_preflight.data_problems(self.data)[0])

    def test_image_builds_run_it_before_any_stage(self):
        text = (ROOT / 'tools' / 'build.py').read_text(encoding='utf-8')
        check = text.index('build_preflight.run(args.workspace')
        self.assertLess(text.index('require_previous_release(ROOT, VERSION)'), check)
        self.assertLess(check, text.index("        if getattr(args, 'accept_known_stair_findings', None):\n"))


class HarvestTownPlanTests(unittest.TestCase):
    """BUILD-HARVEST-TOWN-PLAN-54: a full build's CHIM town other than Seyda Neen and Balmora needs CHIM region frames
    around it (their catalogues carry its plants); refused in the plan, not 20 minutes into the image step."""
    TOWNS = ['balmora', 'seyda', 'vivec_city']

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(ROOT / 'src'))
        import build
        from chim import regions
        cls.regions = regions
        cls.default = regions.plan(['@' + str(build.CHIM_CELLS_DEFAULT)], build.CHIM_CELLS_STATUS_DEFAULT,
                                   towns=cls.TOWNS)

    def test_the_default_full_build_passes(self):
        table, problems = self.default
        self.assertEqual(problems, [])
        self.assertEqual(build_preflight.harvest_town_problems(self.TOWNS, (table, {})), [])

    def test_every_town_with_a_region_table_has_its_own_catalogues(self):
        # CHIM-NATIVE-HARVEST-MISSING-36 (v0.0.57): every town with a region table carries its plants in catalogues of
        # its own (harvest_build.plan_rows), so a town with no region frames around it is no longer refused
        self.assertEqual(build_preflight.harvest_town_problems(self.TOWNS, None), [])       # --chim-regions none
        far = {'cells': {self.regions.cell_key((-19, 14)): {}}}                   # region cells elsewhere only
        self.assertEqual(build_preflight.harvest_town_problems(['vivec_city'], (far, {})), [])

    def test_the_fixed_towns_and_miniwinds_are_not_refused(self):
        self.assertEqual(build_preflight.harvest_town_problems(['balmora', 'seyda'], None), [])
        self.assertEqual(build_preflight.harvest_town_problems(self.TOWNS, None, miniwind=True), [])

    def test_the_check_runs_in_the_build_preflight(self):
        text = (ROOT / 'tools' / 'build.py').read_text(encoding='utf-8')
        self.assertIn('build_preflight.harvest_town_problems(chim_native_towns(args, preflight_builder),', text)


if __name__ == '__main__':
    unittest.main()
