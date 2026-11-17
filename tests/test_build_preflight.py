"""Build preflight (BUILD-CACHE-OWNER-FAILS-STAGE-34): seconds-long checks before any stage, each with its fix."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
import unittest.mock

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


@unittest.skipUnless(hasattr(os, 'geteuid') and hasattr(os, 'fork'), 'POSIX owners, forked workers')
class CacheWalkPoolTests(unittest.TestCase):
    """BUILD-PREFLIGHT-SERIAL-REPEATED-66: the cache walk on a process pool names the same counts and the same first
    entries as the serial walk and as the earlier one-core method (cache_problems_walk), in os.walk's order."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cache = Path(self.temp.name) / 'cache'
        for a in range(3):
            for b in range(3):
                for c in range(2):
                    folder = self.cache / f'pool-{a}' / f'{b:02x}' / f'{c:02x}' / 'deep'
                    folder.mkdir(parents=True)
                    for n in range(3):
                        (folder / f'entry-{n}.json').write_text('{}')
                    (folder.parent / f'top-{c}.bin').write_bytes(b'x')
            (self.cache / f'pool-{a}' / 'flat.json').write_text('{}')
        (self.cache / 'index.json').write_text('{}')
        os.symlink(self.cache / 'pool-0', self.cache / 'pool-link')       # a link to a folder: never walked
        os.symlink(self.cache / 'missing', self.cache / 'pool-1' / 'dangling')

    def messages(self, uid):
        # no fallback to this process: a pool that stopped would only give the serial answer again
        with unittest.mock.patch.object(build_preflight, 'FALLBACK', False), \
                unittest.mock.patch.object(build_preflight, 'TASK_CHUNK', 2):
            return (build_preflight.cache_problems_walk(self.cache, uid=uid),
                    build_preflight.cache_problems(self.cache, uid=uid),
                    build_preflight.cache_problems(self.cache, uid=uid, workers=1),
                    build_preflight.cache_problems(self.cache, uid=uid, workers=3))

    def test_every_entry_foreign_gives_the_same_message_every_way(self):
        earlier, serial, one, pool = self.messages(os.geteuid() + 4242)
        self.assertEqual(len(earlier), 1)
        self.assertEqual(serial, earlier)
        self.assertEqual(one, earlier)
        self.assertEqual(pool, earlier)
        walked = sum(1 + len(files) for _, _, files in os.walk(self.cache))
        self.assertIn(f'{walked} cache entries owned by another user', pool[0])

    def test_a_clean_cache_passes_every_way(self):
        self.assertEqual(self.messages(os.geteuid()), ([], [], [], []))

    def test_the_tasks_cover_the_walk_in_its_order(self):
        tasks = list(build_preflight._walk_tasks(str(self.cache), depth=2))
        self.assertTrue(any(task[0] == 'tree' for task in tasks))
        flat = []
        for task in tasks:
            if task[0] == 'here':
                flat.append((task[1], task[2]))
            else:
                flat += [(folder, files) for folder, _, files in os.walk(task[1])]
        self.assertEqual(flat, [(folder, files) for folder, _, files in os.walk(str(self.cache))])
        self.assertFalse(any(task[-1].endswith('pool-link') for task in tasks if task[0] == 'tree'))


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


class EarlyCheckTests(unittest.TestCase):
    """The early checks (BUILD-IMAGE-CHECKS-EARLY-66): one list, every check of a phase runs, its problems are
    collected with its name, and nothing a check does stops the build by itself."""
    MODULE = 'aw_test_early_checks_module'

    def setUp(self):
        import types
        module = types.ModuleType(self.MODULE)
        module.seen = []

        def clean(context):
            module.seen.append(('clean', context.phase))
            return []

        def two(context):
            module.seen.append(('two', context.phase))
            return ['room A: no grounding class', 'room B: no grounding class']

        def broken(context):
            raise KeyError('census')

        def exits(context):
            sys.exit('stop')
        module.clean, module.two, module.broken, module.exits = clean, two, broken, exits
        sys.modules[self.MODULE] = module
        self.addCleanup(sys.modules.pop, self.MODULE, None)
        self.module = module

    def run_phase(self, phase, checks, **extra):
        lines = []
        context = build_preflight.EarlyContext(phase, log=lines.append, **extra)
        return build_preflight.early_problems(context, checks), lines

    def test_every_check_of_the_phase_runs_and_its_problems_carry_its_name(self):
        m = self.MODULE
        checks = [('two', 'inputs', m + ':two'), ('clean', 'inputs', m + ':clean'), ('later', 'stored', m + ':two')]
        problems, lines = self.run_phase('inputs', checks)
        self.assertEqual(problems, ['two: room A: no grounding class', 'two: room B: no grounding class'])
        self.assertEqual(self.module.seen, [('two', 'inputs'), ('clean', 'inputs')])   # the stored one waits
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].startswith('Early check two (inputs): 2 problems, '), lines)
        self.assertTrue(lines[1].startswith('Early check clean (inputs): ok, '), lines)
        problems, _ = self.run_phase('stored', checks, reused={'image': '/work/build/older'})
        self.assertEqual(len(problems), 2)
        self.assertEqual(self.module.seen[-1], ('two', 'stored'))

    def test_a_check_that_raises_or_exits_is_a_problem_never_a_stop(self):
        m = self.MODULE
        problems, _ = self.run_phase('inputs', [('broken', 'inputs', m + ':broken'), ('exits', 'inputs', m + ':exits'),
                                                ('missing', 'inputs', 'aw_no_such_module_here:problems'),
                                                ('clean', 'inputs', m + ':clean')])
        self.assertEqual(len(problems), 3)
        self.assertTrue(problems[0].startswith("broken: the check itself failed (KeyError: 'census')"), problems)
        self.assertTrue(problems[1].startswith('exits: the check itself failed (SystemExit: stop)'), problems)
        self.assertTrue(problems[2].startswith('missing: the check itself failed (ModuleNotFoundError'), problems)
        self.assertIn(('clean', 'inputs'), self.module.seen)                   # the checks after them still ran

    def test_phases_are_named(self):
        with self.assertRaises(ValueError):
            build_preflight.EarlyContext('later')
        problems, _ = self.run_phase('inputs', [('odd', 'later', self.MODULE + ':clean')])
        self.assertEqual(problems, ["odd: early check of an unknown phase 'later' (one of inputs, stored or "
                                    "after:STAGE)"])
        self.assertTrue(build_preflight.known_phase('after:chim-room-batches'))
        self.assertFalse(build_preflight.known_phase('after:'))
        context = build_preflight.EarlyContext('stored', reused={'image': '/work/build/older'}, steps=['image'])
        self.assertEqual((context.reused, context.steps), ({'image': Path('/work/build/older')}, ['image']))

    def test_every_registered_check_names_a_function_and_a_phase(self):
        import importlib
        for name, phase, target in build_preflight.EARLY_CHECKS:
            module, _, function = target.partition(':')
            self.assertTrue(build_preflight.known_phase(phase), (name, phase))
            self.assertTrue(callable(getattr(importlib.import_module(module), function)), name)

    def test_the_builder_runs_both_phases_before_its_first_stage_and_in_its_check(self):
        text = (ROOT / 'tools' / 'build.py').read_text(encoding='utf-8')
        start = text.index('def _main(')
        inputs = text.index("build_preflight.early_problems(build_preflight.EarlyContext(\n                'inputs'", start)
        preflight_stop = text.index("raise ValueError('Build preflight failed before any stage:", start)
        self.assertLess(inputs, preflight_stop)                                # one stop with the preflight's own
        helper = text[text.index('def stored_early_problems('):]
        self.assertIn("build_preflight.early_problems(build_preflight.EarlyContext(\n                'stored'",
                      helper[:helper.index('\ndef ')])
        stored = text.index('problems = stored_early_problems(args, metadata, steps, run)', start)
        self.assertLess(stored, text.index('execute(steps, run, metadata)', start))
        check = text[text.index('def unit_stop_check('):text.index('def early_masters(')]
        self.assertIn('stored_early_problems(args, metadata, steps, run)', check)   # the --check stops on them too


if __name__ == '__main__':
    unittest.main()
