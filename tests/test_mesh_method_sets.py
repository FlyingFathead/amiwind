# SPDX-License-Identifier: GPL-3.0-only
"""Mesh method sets for Solstheim's stages and the test route's own runner (SOL-GLACIER-METHODS-AB-COMPARE-68).

Held here: the sets file is checked (format, the baseline set names no mesh, a set names only meshes a layer lists
and only methods this tree builds, its default names a set); the set is the runners' own option and never reaches the
converter; the module's world stage always names its set, the shipped default E when the build names none; without
the option the test route's commands are the ones before; the test route's world stage goes through its runner
(the star trees' route keeps its own entry), and a release candidate or final refuses the route and its look-only
option; a test image leaves the Solstheim module out, says so and refuses a plan with both; the runner's look-only
gates report a budget failure instead of stopping, write the receipt's mark, and stop on any other failure; everything
the runner swaps is put back."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import bloodmoon_solstheim  # noqa: E402
import bloodmoon_solstheim_module as module  # noqa: E402
import build  # noqa: E402
import solstheim_test_world as runner  # noqa: E402
from chim import method_sets  # noqa: E402


def write(tmp, data):
    path = Path(tmp) / 'sets.json'
    path.write_text(json.dumps(data), encoding='utf-8', newline='\n')
    return path


def sets_file(**more):
    data = {'format': method_sets.FORMAT, 'layers': {'bloodmoon': ['x/bm_ex_iceberg_shard01']},
            'sets': {'baseline': {'meshes': {}}}}
    data['sets'].update(more)
    return data


class TheSetsFile(unittest.TestCase):
    def test_the_repositorys_file_reads_and_holds_the_baseline(self):
        data = method_sets.load()
        self.assertIn(method_sets.BASELINE, data['sets'])
        self.assertEqual(data['sets'][method_sets.BASELINE]['meshes'], {})
        listed = {m for meshes in data['layers'].values() for m in meshes}
        self.assertEqual(listed, {'x/bm_ex_iceberg_shard01', 'x/bm_ex_iceberg', 'x/bm_ex_iceberg_collapsed'})

    def test_a_bad_file_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'unknown format'):
                method_sets.load(write(tmp, dict(sets_file(), format='other')))
            with self.assertRaisesRegex(ValueError, "today's methods"):
                method_sets.load(write(tmp, sets_file(baseline={'meshes': {'x/bm_ex_iceberg_shard01': {}}})))
            with self.assertRaisesRegex(ValueError, 'no layer lists'):
                method_sets.load(write(tmp, sets_file(C={'meshes': {'x/ex_vivec_c_02': {}}})))
            with self.assertRaisesRegex(ValueError, 'not built by this tree'):
                method_sets.load(write(tmp, sets_file(C={'meshes': {'x/bm_ex_iceberg_shard01': {'collision': {}}}})))

    def test_the_option_is_taken_out_and_an_unknown_set_is_refused(self):
        self.assertEqual(method_sets.take(['--out', '/w']), (None, ['--out', '/w']))
        self.assertEqual(method_sets.take(['--out', '/w', '--mesh-method-set', 'baseline', '--jobs', '4']),
                         ('baseline', ['--out', '/w', '--jobs', '4']))
        for bad in (['--mesh-method-set'], ['--mesh-method-set', '--out', '/w']):
            with self.assertRaises(SystemExit):
                method_sets.take(bad)
        with self.assertRaises(SystemExit):
            method_sets.install('no-such-set')
        record, restore = method_sets.install('baseline')
        self.assertEqual(record['meshes'], [])
        self.assertIn("today's methods", method_sets.line(record))
        restore()


class TheModuleRunner(unittest.TestCase):
    def run_main(self, argv):
        seen = {}
        fake = SimpleNamespace(main=lambda: seen.update(argv=list(sys.argv)) or 0)
        saved = list(sys.argv)
        try:
            # the runner sets the module's master list for its process: kept inside this test
            with mock.patch.dict(sys.modules, {'chim_build': fake}), mock.patch.dict(os.environ):
                self.assertEqual(bloodmoon_solstheim.main(argv), 0)
        finally:
            sys.argv = saved
        return seen['argv'][1:]

    def test_the_set_is_the_runners_own_option_and_never_reaches_the_converter(self):
        self.assertEqual(self.run_main(['--out', '/w', '--mesh-method-set', 'baseline']), ['--out', '/w'])
        self.assertEqual(self.run_main(['--out', '/w']), ['--out', '/w'])

    def args(self, method_set=None):
        args = SimpleNamespace(bloodmoon_solstheim_cells='-22,16:l', tribunal_mournhold_cells=None,
                               chim_regions_cells='1,1:l', data_files='/data', workspace=Path('/ws'), sdk='/sdk')
        if method_set:
            args.chim_mesh_method_set = method_set
        return args

    def stage(self, args):
        steps = [('chim', ['python3', 'chim_build.py']), ('cell-progress', ['python3', 'cell_progress_build.py']),
                 ('image', ['python3', 'build_aga.py'])]
        tool = lambda name, *parts: ['python3', name, *[str(p) for p in parts]]  # noqa: E731
        made = module.commands(args, steps, tool, Path('/run'), {'qbsp': '/q'}, 8, build.module_chim_options)
        return dict(made)['bloodmoon-solstheim']

    def test_the_modules_command_names_the_shipped_default_set_unless_the_build_names_one(self):
        # method E is the shipped default of the Solstheim module (decided for the project on 22 November 2026,
        # config/mesh-method-sets.json "default"): a build that names no set builds the glacier's ice with E; until
        # v0.0.68-dev7 such a build named none and built today's methods (the nine glacier cells did not fit 32 MB)
        plain = self.stage(self.args())
        at = plain.index('--mesh-method-set')
        self.assertEqual(plain[at + 1], 'E')
        self.assertEqual(module.method_set(self.args()), 'E')
        for name in ('baseline', 'C'):
            with_set = self.stage(self.args(name))
            self.assertEqual(with_set[with_set.index('--mesh-method-set') + 1], name)
            self.assertEqual(with_set[:at] + with_set[at + 2:], plain[:at] + plain[at + 2:])
            self.assertEqual(with_set.count('--mesh-method-set'), 1)

    def test_the_shipped_default_is_read_from_the_sets_file_and_checked(self):
        self.assertEqual(method_sets.default_name(), 'E')
        self.assertEqual(method_sets.load()['default'], 'E')
        with tempfile.TemporaryDirectory() as tmp:
            # a file without a default builds today's methods; a default that names no set is refused
            self.assertEqual(method_sets.default_name(write(tmp, sets_file())), method_sets.BASELINE)
            self.assertEqual(module.method_set(self.args(), write(tmp, sets_file())), method_sets.BASELINE)
            with self.assertRaisesRegex(ValueError, 'default set'):
                method_sets.load(write(tmp, dict(sets_file(), default='F')))
        # E is method C on the shard and both icebergs and method D on the shard, as measured
        record = method_sets.rows('E')[0]
        self.assertEqual(record['methods'], {'x/bm_ex_iceberg_shard01': ['C', 'D'], 'x/bm_ex_iceberg': ['C'],
                                             'x/bm_ex_iceberg_collapsed': ['C']})


class TheTestRoute(unittest.TestCase):
    def setUp(self):
        # the test route is a -devN option (project_version.require_private_test_version refuses it on an rc or final
        # VERSION): its commands are checked under a dev version, so the tests hold on a release line too; a test of the
        # refusal sets its own VERSION inside
        patcher = mock.patch.object(build, 'VERSION', '0.0.0-dev1')
        patcher.start()
        self.addCleanup(patcher.stop)

    def commands(self, **options):
        values = dict(chim_sol_test='-26,26:l', chim_sol_tree_copies=None, workspace=Path('/ws'), data_files='/data',
                      sdk='/sdk')
        values.update(options)
        args = SimpleNamespace(**values)
        steps = [('chim', ['python3', 'chim_build.py']), ('image', ['python3', 'build_aga.py'])]
        tool = lambda name, *parts: ['python3', name, *[str(p) for p in parts]]  # noqa: E731
        return dict(build.chim_sol_test_commands(args, steps, tool, Path('/run'), {'qbsp': '/q'}, 8))

    def test_without_the_options_the_world_stage_goes_through_the_runner_as_well(self):
        # the runner reads the layered test folder with its own master alone; the converter called directly read the
        # build's selection and stopped on 'Missing Tribunal.esm' (21 November 2026)
        stage = self.commands()['chim-sol']
        self.assertEqual(stage[1], 'solstheim_test_world.py')
        self.assertIn('--unit-pool', stage)
        for option in ('--mesh-method-set', '--look-only'):
            self.assertNotIn(option, stage)
        at = stage.index('--data-files')
        self.assertTrue(str(stage[at + 1]).endswith('chim-sol-data'))

    def test_the_base_commands_are_the_same_with_and_without_the_test_route(self):
        values = dict(chim_sol_test=None, chim_sol_tree_copies=None, workspace=Path('/ws'), data_files='/data',
                      sdk='/sdk')
        steps = [('chim', ['python3', 'chim_build.py', '--x']), ('image', ['python3', 'build_aga.py'])]
        tool = lambda name, *parts: ['python3', name, *[str(p) for p in parts]]  # noqa: E731
        plain = dict(build.chim_sol_test_commands(SimpleNamespace(**values), list(steps), tool, Path('/run'),
                                                  {'qbsp': '/q'}, 8))
        routed = dict(build.chim_sol_test_commands(SimpleNamespace(**dict(values, chim_sol_test='-26,26:l')),
                                                   list(steps), tool, Path('/run'), {'qbsp': '/q'}, 8))
        self.assertEqual(plain, dict(steps))
        self.assertEqual(routed['chim'], plain['chim'])
        self.assertEqual(routed['image'][:len(plain['image'])], plain['image'])        # the store added after it

    def test_a_test_image_of_solstheim_cells_is_built_without_the_module(self):
        # both made the store chimsol, and the glacier comparison's image stopped in its image step (21 November 2026)
        lines = []

        def builder():
            raise AssertionError('the module must not be resolved further for a --chim-sol-test build')
        args = SimpleNamespace(chim_sol_test='-26,26:l', miniwind=False, chim_regions=None, data_files='/data')
        record = module.resolve(args, ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm'), builder, {},
                                log=lines.append)
        self.assertIsNone(getattr(args, module.CELLS_OPTION))
        # loud: one plan line, and the same fact as the record the build writes into build-state.json
        self.assertEqual(len(lines), 1)
        self.assertIn('bloodmoon-solstheim: NOT BUILT', lines[0])
        self.assertIn('--chim-sol-test', lines[0])
        self.assertEqual(record['built'], False)
        self.assertIn('--chim-sol-test', record['reason'])
        self.assertEqual(build.chim_sol_test_module_record(SimpleNamespace(bloodmoon_solstheim_record=record)), record)
        for other in (None, {'selection': [], 'counts': {}, 'dropped': []}):
            self.assertIsNone(build.chim_sol_test_module_record(SimpleNamespace(bloodmoon_solstheim_record=other)))
        # without the test route the module is resolved as before (the builder is asked)
        plain = SimpleNamespace(chim_sol_test=None, miniwind=False, chim_regions=None, data_files='/data')
        with self.assertRaisesRegex(AssertionError, 'must not be resolved further'):
            module.resolve(plain, ('Morrowind.esm', 'Bloodmoon.esm'), builder, {}, log=lines.append)

    def test_the_test_images_record_says_the_module_is_not_in_it(self):
        # chim-sol-image.json of a --chim-sol-test image: the Solstheim module is left out of such a build
        import build_aga
        for layer_worlds in (None, [], ['chimmh=/run/tribunal-mournhold']):
            record = build_aga.sol_test_module_record(layer_worlds)
            self.assertEqual(record['built'], False)
            self.assertIn('--chim-sol-test', record['text'])
        # a store chimsol from a layer too: no such record (the image step refuses that image)
        self.assertIsNone(build_aga.sol_test_module_record(['chimsol=/run/bloodmoon-solstheim']))

    def test_the_plan_refuses_the_module_and_the_test_route_together_before_any_command(self):
        # if the module's cells and the test route are ever both in a plan, it stops while the commands are made (the
        # plan, which `build.py --check` makes too), before the first command of the route and so before any stage;
        # on 8b5069bf5 the plan passed and the image step stopped on the second store chimsol
        made = []
        values = dict(chim_sol_test='-26,26:l', chim_sol_tree_copies=None, workspace=Path('/ws'), data_files='/data',
                      sdk='/sdk', bloodmoon_solstheim_cells='-22,16:l')
        steps = [('chim', ['python3', 'chim_build.py']), ('image', ['python3', 'build_aga.py'])]
        before = [list(command) for _, command in steps]

        def tool(name, *parts):
            made.append(name)
            return ['python3', name, *[str(p) for p in parts]]
        with mock.patch.object(build, 'VERSION', '0.0.68-dev3'):
            with self.assertRaises(SystemExit) as stop:
                build.chim_sol_test_commands(SimpleNamespace(**values), steps, tool, Path('/run'), {'qbsp': '/q'}, 8)
        text = str(stop.exception)
        for part in ('--chim-sol-test', 'bloodmoon-solstheim', 'store chimsol', 'drop --chim-sol-test'):
            self.assertIn(part, text)
        self.assertEqual(made, [])
        self.assertEqual([list(command) for _, command in steps], before)

    def test_the_star_route_keeps_its_own_entry(self):
        stage = self.commands(chim_sol_tree_copies='star')['chim-sol']
        self.assertEqual(stage[1], 'chim_tree_star.py')

    def test_with_a_set_or_look_only_the_world_stage_runs_through_its_runner(self):
        with mock.patch.object(build, 'VERSION', '0.0.68-dev3'):
            stage = self.commands(chim_mesh_method_set='baseline', chim_sol_test_look_only=True)['chim-sol']
        self.assertEqual(stage[1], 'solstheim_test_world.py')
        self.assertEqual(stage[stage.index('--mesh-method-set') + 1], 'baseline')
        self.assertIn('--look-only', stage)
        self.assertIn('--unit-pool', stage)
        stage = self.commands(chim_mesh_method_set='baseline')['chim-sol']
        self.assertNotIn('--look-only', stage)

    def test_a_release_candidate_or_final_refuses_the_look_only_option(self):
        for version in ('0.0.68-rc1', '0.0.68'):
            with mock.patch.object(build, 'VERSION', version):
                with self.assertRaisesRegex(ValueError, 'private-test waivers'):
                    self.commands(chim_sol_test_look_only=True)

    def test_a_release_candidate_or_final_refuses_the_test_route_itself(self):
        # a --chim-sol-test image leaves the Solstheim module out: Solstheim is only the named cells, never a release
        for version in ('0.0.68-rc1', '0.0.68'):
            for options in ({}, {'chim_mesh_method_set': 'baseline'}):
                with mock.patch.object(build, 'VERSION', version):
                    with self.assertRaisesRegex(ValueError, r'private-test waivers \(--chim-sol-test\)'):
                        self.commands(**options)
        with mock.patch.object(build, 'VERSION', '0.0.68-dev3'):
            self.assertEqual(self.commands()['chim-sol'][1], 'solstheim_test_world.py')
        # without the route nothing is refused or recorded (a release builds the module as before)
        with mock.patch.object(build, 'VERSION', '0.0.68-rc1'):
            self.assertEqual(self.commands(chim_sol_test=None), {'chim': ['python3', 'chim_build.py'],
                                                                 'image': ['python3', 'build_aga.py']})

    def test_star_trees_do_not_take_the_runners_options(self):
        with self.assertRaises(SystemExit):
            self.commands(chim_sol_tree_copies='star', chim_mesh_method_set='baseline')


class TheLookOnlyGates(unittest.TestCase):
    def test_a_budget_failure_reports_and_marks_the_receipt_and_everything_is_put_back(self):
        import chim.heap
        import chim.zone_sim
        heap, walk = chim.heap.require_heap, chim.zone_sim.require_zone_walk
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / 'chim-heap.json').write_text(json.dumps({'frames': [{'frame': 'f', 'ok': False}]}), encoding='utf-8')

            def over(path, *a, **kw):
                raise ValueError('CHIM heap gate failed: 1 frame(s) over the zone')
            with mock.patch.object(chim.heap, 'require_heap', over):
                failures, restore = runner.look_only_gates()
                report = chim.heap.require_heap(out)
                self.assertEqual(report['status'], 'failed (look only)')
                self.assertEqual(report['frames'][0]['frame'], 'f')
                self.assertEqual(len(failures), 1)
                restore()
                self.assertIs(chim.heap.require_heap, over)
            runner.mark_receipt(out, failures)
            receipt = json.loads((out / 'chim-receipt.json').read_text(encoding='utf-8'))
            self.assertEqual(receipt['look_only']['text'], runner.LOOK_ONLY_TEXT)
        self.assertIs(chim.heap.require_heap, heap)
        self.assertIs(chim.zone_sim.require_zone_walk, walk)

    def test_any_other_failure_still_stops_the_stage(self):
        import chim.heap

        def broken(path, *a, **kw):
            raise ValueError('CHIM heap gate: the world does not read back (truncated)')
        with mock.patch.object(chim.heap, 'require_heap', broken):
            failures, restore = runner.look_only_gates()
            try:
                with self.assertRaisesRegex(ValueError, 'does not read back'):
                    chim.heap.require_heap('/nowhere')
            finally:
                restore()
        self.assertEqual(failures, [])

    def test_the_layered_test_folder_is_read_with_its_own_master_alone(self):
        # the build exports its master selection (all three since the expansions are selected), and the test route's
        # folder (tools/chim_layer_data.py) holds one merged Morrowind.esm: the glacier's method E image stopped on
        # "Missing Tribunal.esm" (21 November 2026)
        from mwad.masters import MASTERS_ENV
        seen = {}
        fake = SimpleNamespace(main=lambda: seen.update(masters=os.environ.get(MASTERS_ENV)) or 0)
        saved = list(sys.argv)
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / 'chim-sol-data'
            data.mkdir()
            (data / 'layer-data.json').write_text(json.dumps({'format': 'aw-chim-layer-data-1'}), encoding='utf-8',
                                                  newline='\n')
            try:
                with mock.patch.dict(sys.modules, {'chim_build': fake}), \
                        mock.patch.dict(os.environ, {MASTERS_ENV: 'Morrowind.esm,Tribunal.esm,Bloodmoon.esm'}):
                    self.assertEqual(runner.main(['--data-files', str(data), '--out', tmp, '--mesh-method-set',
                                                  'baseline']), 0)
                    self.assertEqual(seen['masters'], 'Morrowind.esm')
                    self.assertEqual(os.environ[MASTERS_ENV], 'Morrowind.esm,Tribunal.esm,Bloodmoon.esm')  # put back
                    # another folder (no layered record): the build's selection stands
                    other = Path(tmp) / 'other'
                    other.mkdir()
                    self.assertEqual(runner.main(['--data-files=' + str(other), '--out', tmp, '--look-only']), 0)
                    self.assertEqual(seen['masters'], 'Morrowind.esm,Tribunal.esm,Bloodmoon.esm')
            finally:
                sys.argv = saved

    def test_the_runners_options_never_reach_the_converter(self):
        seen = {}
        fake = SimpleNamespace(main=lambda: seen.update(argv=list(sys.argv)) or 0)
        saved = list(sys.argv)
        with tempfile.TemporaryDirectory() as tmp:
            try:
                with mock.patch.dict(sys.modules, {'chim_build': fake}):
                    self.assertEqual(runner.main(['--out', tmp, '--mesh-method-set', 'baseline', '--look-only']), 0)
            finally:
                sys.argv = saved
            self.assertFalse((Path(tmp) / 'chim-receipt.json').exists())      # nothing failed: no mark
        self.assertEqual(seen['argv'][1:], ['--out', tmp])
        self.assertEqual(runner.take_flag(['--look-only', '--out', '/w'], '--look-only'), (True, ['--out', '/w']))
        self.assertEqual(runner.out_of(['--jobs', '4', '--out', '/w']), Path('/w'))
        self.assertEqual(runner.out_of(['--out=/x']), Path('/x'))


def book_mesh(strips=4):
    """A test mesh in mesh units: a walkable floor (two triangles) inside an open book of two steep pages (vertical,
    joined at the spine, STRIPS triangles pairs each, so they are one connected steep surface whose convex hull fills
    the space over the floor), and a lone steep plate far away. (vertices, faces with a material column)."""
    import numpy as np
    v, f = [], []

    def quad(a, b, c, d):
        base = len(v)
        v.extend([a, b, c, d])
        f.extend([(base, base + 1, base + 2, 0), (base, base + 2, base + 3, 0)])
    quad((8, 8, 0), (120, 8, 0), (120, 40, 0), (8, 40, 0))           # the floor, walkable (normal up)
    for s in range(strips):                                          # page A in y=0, page B in x=0 (steep)
        x0, x1 = 160 * s / strips, 160 * (s + 1) / strips
        quad((x0, 0, 0), (x1, 0, 0), (x1, 0, 160), (x0, 0, 160))
        quad((0, x1, 0), (0, x0, 0), (0, x0, 160), (0, x1, 160))
    quad((800, 800, 0), (800, 840, 0), (800, 840, 160), (800, 800, 160))   # a lone steep plate
    return np.asarray(v, float), np.asarray(f, int)


def today_pieces(v, f):
    """One thin convex piece per triangle, as the hull-surface rule gives these meshes (converter units)."""
    from mesh_geometry import _proxy_piece
    tris = v[f[:, :3], :3] * 0.25
    return [_proxy_piece(tris, [i]) for i in range(len(f))]


class MethodC(unittest.TestCase):
    """chim.collision_exact: the walkable pieces kept, the steep faces' proxies split where they rise over the
    walkable surface, the figures measured on the result."""

    def place(self):
        from chim import collision_exact as CE
        v, f = book_mesh()
        parts = today_pieces(v, f)
        data = (v, f, [], parts, {})
        ref = {'position': [1000.0, 2000.0, 0.0], 'rotation_radians': [0.0, 0.0, 0.0], 'scale': 1.0}
        return CE, v, f, data, ref, [1000.0, 2000.0], parts

    def test_the_converter_scale_is_the_one_the_method_assumes(self):
        from prepare_mesh_bsp import SCALE
        self.assertEqual(SCALE, 0.25)

    def test_the_walkable_surface_is_kept_and_nothing_rises_over_it(self):
        import numpy as np
        from mesh_geometry import collision_parts
        CE, v, f, data, ref, centre, parts = self.place()
        out, figures = CE.exact_footing(data, ref, centre, parts)
        tris = CE.placed_triangles(data, ref, centre)
        np.testing.assert_allclose(tris, v[f[:, :3], :3] * 0.25)
        walk = CE.walkable(tris)
        self.assertEqual(walk.tolist()[:2], [True, True])
        self.assertFalse(walk[2:].any())
        self.assertTrue(all(any(p is q for q in out) for p in parts[:2]))        # the floor's own pieces
        self.assertEqual(figures['lost_cells'], 0)
        self.assertEqual(figures['over_rise_cells'], 0)
        self.assertLessEqual(figures['largest_move'], 8.0)
        self.assertGreater(figures['walkable_cells'], 0)
        self.assertGreaterEqual(figures['splits'] + figures['parts_back'], 1)
        self.assertGreaterEqual(figures['proxies'], 1)                           # the lone plate stays a proxy
        # without the test, the pages' own proxy stands over the floor
        steep = tris[2:]
        naive = [(p, h, ids, e) for p, h, ids, e in collision_parts(steep.reshape(-1, 3) / 0.25, np.column_stack(
            [np.arange(len(steep) * 3).reshape(-1, 3), np.zeros(len(steep), int)]), 2.0)]
        grid = CE.Grid(tris, 2.0)
        today = grid.top(parts)
        surface = grid.walkable_tops(tris, walk) & np.isfinite(today)
        rise = (grid.top(parts[:2] + naive)[surface] - today[surface]) * CE.GAME
        self.assertGreater(float(np.nanmax(rise)), 100.0)

    def test_a_bad_setting_or_a_foreign_collision_is_refused(self):
        CE, v, f, data, ref, centre, parts = self.place()
        with self.assertRaisesRegex(ValueError, 'unknown setting'):
            CE.settings({'tolerance': 2.0, 'grain': 4})
        self.assertEqual(CE.settings(None), CE.DEFAULTS)
        for lod in ({'collision': 'authored RootCollisionNode, approximate convex conversion'},
                    {'collision_mesh': {'triangles': 3}}, {'stair_removed_triangles': [1]}):
            with self.assertRaisesRegex(ValueError, 'own mesh'):
                CE.placed_triangles((v, f, [], parts, lod), ref, centre)

    def test_the_placement_swap_gives_the_methods_pieces_for_its_mesh_only(self):
        import prepare_mesh_bsp
        CE, v, f, data, ref, centre, parts = self.place()
        original = prepare_mesh_bsp._prepare_placement
        calls = []
        fake = lambda task: calls.append(task) or ([], list(task[1][3]), [0, 0, 0], [1, 1, 1])  # noqa: E731
        with mock.patch.object(prepare_mesh_bsp, '_prepare_placement', fake):
            with CE.Placement(data, None) as placement:
                got = prepare_mesh_bsp._prepare_placement((ref, data, 64, centre, None, False))
                other = (v, f, [], parts[:1], {})
                plain = prepare_mesh_bsp._prepare_placement((ref, other, 64, centre, None, False))
            self.assertIs(prepare_mesh_bsp._prepare_placement, fake)
        self.assertIs(prepare_mesh_bsp._prepare_placement, original)
        self.assertEqual(len(placement.figures), 1)
        self.assertNotEqual(len(got[1]), len(parts))
        self.assertEqual(len(plain[1]), 1)
        result, figures = CE.take_figures(CE._with_figures({'lumps': []}, placement.figures))
        self.assertEqual(result, {'lumps': []})
        self.assertEqual(figures['form'], CE.FORM)
        tiles, figures = CE.take_figures(CE._with_figures((256.0, [{'tile': [0, 0]}, {'tile': [1, 0]}]),
                                                          placement.figures))
        self.assertEqual(tiles, (256.0, [{'tile': [0, 0]}, {'tile': [1, 0]}]))
        self.assertIsNotNone(figures)

    def test_the_methods_code_is_inside_its_unit_kinds_key(self):
        # a worker that runs code outside its kind's key stores nothing (chim.units KEY_GAPS): the method's own code,
        # traced while it runs, is all in the reach of 'variant-c'
        import code_key
        from chim import units as U
        CE, v, f, data, ref, centre, parts = self.place()
        record, restore = method_sets.install('E')
        try:
            tracer = code_key.Tracer()
            tracer.begin()
            try:
                CE.exact_footing(data, ref, centre, parts)
            finally:
                tracer.end()
            executed = tracer.take()
            tracer.close()
            if executed is None:
                self.skipTest('no sys.monitoring in this Python')
            mine = [e for e in executed if e[0] == 'tools/chim/collision_exact.py']
            self.assertTrue(mine)
            self.assertEqual(code_key.uncovered(executed, U.unit_code_key('variant-c')), [])
        finally:
            restore()


class TheSetsInstalled(unittest.TestCase):
    def test_the_repositorys_sets_name_the_methods_of_the_comparison(self):
        record, c_rows, d_rows = method_sets.rows('E')
        self.assertEqual(record['methods'], {'x/bm_ex_iceberg': ['C'], 'x/bm_ex_iceberg_collapsed': ['C'],
                                             'x/bm_ex_iceberg_shard01': ['C', 'D']})
        self.assertEqual(sorted(c_rows), ['x/bm_ex_iceberg', 'x/bm_ex_iceberg_collapsed', 'x/bm_ex_iceberg_shard01'])
        self.assertEqual(d_rows['x/bm_ex_iceberg_shard01']['recipe']['expected_triangles'], 1302)
        self.assertEqual(method_sets.rows('C')[0]['methods']['x/bm_ex_iceberg_shard01'], ['C'])
        self.assertEqual(method_sets.rows('D')[0]['methods'], {'x/bm_ex_iceberg_shard01': ['D']})

    def test_install_swaps_for_the_process_and_restore_puts_everything_back(self):
        import chim.build
        import model_method2
        from chim import units as U
        run, load = chim.build.run_units, model_method2.load_table
        kinds = set(U.CODE_ENTRIES)
        with tempfile.TemporaryDirectory() as tmp:
            record, restore = method_sets.install('E', report=tmp)
            try:
                self.assertIsNot(chim.build.run_units, run)
                self.assertEqual(set(U.CODE_ENTRIES) - kinds,
                                 {'variant-c', 'variant-bsp2-c', 'tiles-budget-c', 'tiles-budget-union-c'})
                table = model_method2.load_table()
                row = table['models']['meshes/x/bm_ex_iceberg_shard01.nif']
                self.assertEqual((row['kind'], row['method']), ('conservative', 2))
                profile = model_method2.apply_method2({'ratio': 0.5, 'faces': 'merge'}, {
                    'source': 'meshes\\x\\bm_ex_iceberg_shard01.nif', 'source_sha256': row['source_sha256']}, table)
                self.assertEqual(profile['visual_method2']['kind'], 'conservative')
                self.assertNotIn('ratio', profile)
            finally:
                restore()
            report = json.loads((Path(tmp) / method_sets.REPORT).read_text(encoding='utf-8'))
            self.assertEqual(report['set']['set'], 'E')
        self.assertIs(chim.build.run_units, run)
        self.assertIs(model_method2.load_table, load)
        self.assertEqual(set(U.CODE_ENTRIES), kinds)
        self.assertNotIn('meshes/x/bm_ex_iceberg_shard01.nif', model_method2.load_table()['models'])
        # the baseline installs nothing and writes no report
        with tempfile.TemporaryDirectory() as tmp:
            record, restore = method_sets.install('baseline', report=tmp)
            self.assertIs(chim.build.run_units, run)
            restore()
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_the_dispatcher_sends_only_the_listed_meshes_to_the_methods_kinds(self):
        from chim import collision_exact as CE
        calls = []

        def original(kind, items, worker, jobs, cache, soft=None):
            calls.append((kind, [fp for fp, _ in items], worker))
            if kind == 'variant-c':
                return [{'lumps': [], CE.FIGURES_KEY: {'pieces': 3, 'pieces_today': 5}} for _ in items]
            return [{'lumps': [], 'kind': kind} for _ in items]
        shard = {'source': 'meshes\\x\\bm_ex_iceberg_shard01.nif', 'materials': []}
        berg = {'source': 'meshes\\x\\bm_ex_iceberg.nif', 'materials': []}
        rock = {'source': 'meshes\\x\\ex_rock_01.nif', 'materials': []}
        ref = {'position': [0.0, 0.0, 0.0], 'rotation_radians': [0.1, 0.0, 0.0], 'scale': 1.0, 'number': 1}
        items = [('fp-rock', {'model': rock, 'ref': ref}), ('fp-shard', {'model': shard, 'ref': ref, 'qbsp': '/q'}),
                 ('fp-berg', {'model': berg, 'ref': ref, 'qbsp': '/q'})]
        record, c_rows, _ = method_sets.rows('E')
        from chim import units as U
        record, restore = method_sets.install('E')
        try:
            with tempfile.TemporaryDirectory() as tmp:
                (Path(tmp) / method_sets.REPORT_LINES).write_text('', encoding='utf-8')
                run = method_sets.dispatcher(original, c_rows, tmp)
                out = run('variant', items, 'plain-worker', 2, None, soft=('Clipnode',))
                lines = (Path(tmp) / method_sets.REPORT_LINES).read_text(encoding='utf-8').splitlines()
            self.assertEqual(out[0], {'lumps': [], 'kind': 'variant'})
            self.assertEqual(out[1], {'lumps': []})                       # the figures taken out
            self.assertIn('stored as tiles', out[2]['over_budget'])       # the iceberg: to its tiles at once
            self.assertEqual(calls[0], ('variant', ['fp-rock'], 'plain-worker'))
            self.assertEqual(calls[1][0], 'variant-c')
            self.assertNotEqual(calls[1][1], ['fp-shard'])                 # its own key
            self.assertIs(calls[1][2], CE.variant_unit_c)
            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0])['figures']['pieces'], 3)
            self.assertEqual(run('texture', items, 'w', 1, None), [{'lumps': [], 'kind': 'texture'}] * 3)
            with self.assertRaisesRegex(ValueError, 'does not make tiles units'):
                run('tiles', items, 'w', 1, None)
        finally:
            restore()
        self.assertNotIn('variant-c', U.CODE_ENTRIES)

    def test_the_runners_cache_pickles_as_before_without_a_set_and_installs_the_set_with_one(self):
        import pickle
        from chim.units import PooledUnitCache
        import chim.build
        saved = chim.build.UnitCache
        with tempfile.TemporaryDirectory() as tmp:
            made = bloodmoon_solstheim.pooled_units(Path(tmp) / 'pool')
            try:
                cache = chim.build.UnitCache(Path(tmp) / 'units')
                self.assertIs(type(pickle.loads(pickle.dumps(cache))), PooledUnitCache)
                record, restore = method_sets.install('E')
                try:
                    self.assertEqual(method_sets.cache_reduce(PooledUnitCache, ('a', 'b'), {})[0],
                                     method_sets.worker_cache)
                    again = pickle.loads(pickle.dumps(cache))
                    self.assertIs(type(again), method_sets.SetPooledUnitCache)
                    self.assertEqual(again.folder, cache.folder)
                    import copy
                    self.assertIs(type(copy.copy(cache)), method_sets.SetPooledUnitCache)
                finally:
                    restore()
                self.assertIs(type(pickle.loads(pickle.dumps(cache))), PooledUnitCache)
            finally:
                chim.build.UnitCache = saved
            self.assertEqual(len(made), 1)


class TheChimportOption(unittest.TestCase):
    def test_the_set_reaches_each_cell_and_enters_its_key_only_when_named(self):
        import chimport
        args = SimpleNamespace(data_files=Path('/d'), palette=Path('/p'), out=Path('/run'), jobs=2, qbsp=None,
                               frame_settings=None, cell_shape='region', mesh_method_set=None)
        row = {'x': -26, 'y': 26}
        plain = chimport.cell_command(args, row)
        self.assertNotIn('--mesh-method-set', plain)
        args.mesh_method_set = 'E'
        named = chimport.cell_command(args, row)
        self.assertEqual(named[named.index('--mesh-method-set') + 1], 'E')
        self.assertEqual([w for w in named if w not in ('--mesh-method-set', 'E')], plain)
        with mock.patch.object(chimport, 'inputs_identity', lambda d: [['Morrowind.esm', 'a' * 64]]), \
                mock.patch.object(chimport, 'layer_touch', lambda c, d: None), \
                tempfile.TemporaryDirectory() as tmp:
            palette = Path(tmp) / 'palette.lmp'
            palette.write_bytes(b'\0' * 768)
            base = chimport.cell_key((-26, 26), '/d', palette)[0]
            again = chimport.cell_key((-26, 26), '/d', palette, method_set=None)[0]
            other = chimport.cell_key((-26, 26), '/d', palette, method_set={'set': 'E', 'methods': {}})[0]
        self.assertEqual(base, again)
        self.assertNotEqual(base, other)
        with chimport.method_set_installed(None, Path('/run')) as nothing:
            self.assertIsNone(nothing)


if __name__ == '__main__':
    unittest.main()
