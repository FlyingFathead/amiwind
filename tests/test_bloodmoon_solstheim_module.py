# SPDX-License-Identifier: GPL-3.0-only
"""The build module bloodmoon-solstheim: Solstheim's outdoor cells as a world of their own.

The module's rule, held here on a small stand-in plan (no game data): its two stages are in the plan only with
Bloodmoon selected and finished Solstheim cells to build; the base stage list and every base command are the ones of
a build without it, also beside Mournhold's module; its stages are keyed by the base files and Bloodmoon's files
only; no base stage waits for it and it waits for no world stage; the base world's cell list never holds a Solstheim
cell; the image takes its world as the store chimsol with the frame maps slNNNN; the first-minute checks know the
module."""
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
import build_cache  # noqa: E402
import build_preflight  # noqa: E402
import expansion_preflight  # noqa: E402
from chim import layer_stores, regions, sol_test  # noqa: E402

CELLS = '-22,16:l -22,17:l -20,25:l'
DISTRICTS = '-12,-30:l -12,-29:l'
BASE_CELLS = '1,1:l 2,1:l'
LEFT_OUT = {'intro', 'world-terrain', 'world-scenery', 'music', 'media', 'engine', 'dialogue-lookup', 'npc-gallery',
            'focus', 'books', 'chargen', 'item-models', 'harvest', 'hand-catalog', 'world-flora',
            'chim-interiors', 'chim-room-batches', 'seam-audit'}
MODULE_STAGES = ('bloodmoon-solstheim-data', 'bloodmoon-solstheim')


def tool(name, *parts):
    return ['python3', name, *[str(p) for p in parts]]


def base_steps():
    return [('census', tool('census.py', '--data-files', '/data')),
            ('mwscript', tool('prepare_mwscript.py', '--data-files', '/data', '--out', '/run/mwscript')),
            ('chim', tool('chim_build.py', '--area', 'seyda', '--data-files', '/data', '--out', '/run/chim-world',
                          '--lighting-type', 'hybrid', '--chim-regions-cells', BASE_CELLS)),
            ('cell-progress', tool('cell_progress_build.py', '--out', '/run/toolkit', '--chim-world', '/run/chim-world',
                                   '--data-files', '/data', '--never-fail')),
            ('image', tool('build_aga.py', 'image', '--data-files', '/data'))]


def module_args(cells=CELLS, districts=None):
    return SimpleNamespace(bloodmoon_solstheim_cells=cells, tribunal_mournhold_cells=districts,
                           chim_regions_cells=BASE_CELLS, data_files='/data', workspace=Path('/ws'), sdk='/sdk')


def module_steps(cells=CELLS, steps=None, districts=None):
    return module.commands(module_args(cells, districts), base_steps() if steps is None else steps, tool, Path('/run'),
                           {'qbsp': '/tools/qbsp'}, 8, build.module_chim_options)


class TheBaseStagesAreUnchanged(unittest.TestCase):
    def test_without_the_module_the_plan_is_the_one_before(self):
        for cells in (None, ''):
            self.assertEqual(module_steps(cells), base_steps())

    def test_with_the_module_every_base_stage_keeps_its_place_and_its_command(self):
        steps = module_steps()
        names = [name for name, _ in steps]
        self.assertEqual(names, ['census', 'mwscript', *MODULE_STAGES, 'chim', 'cell-progress', 'image'])
        self.assertEqual([n for n in names if n not in MODULE_STAGES], [n for n, _ in base_steps()])
        commands, before = dict(steps), dict(base_steps())
        # no base stage takes an option from the module: the image installs the world by the plan's stage names
        # (layer_stores.image_options), the scripts and every other stage keep their command
        for name in ('census', 'mwscript', 'chim', 'image'):
            self.assertEqual(commands[name], before[name], name)
        # the tracker data counts the module's world as the build's own cells
        self.assertEqual(commands['cell-progress'][:len(before['cell-progress'])], before['cell-progress'])
        self.assertEqual(commands['cell-progress'][len(before['cell-progress']):],
                         ['--module-chim-world', str(Path('/run') / 'bloodmoon-solstheim')])

    def test_beside_mournholds_module_each_keeps_its_own_stages_and_commands(self):
        args = module_args(CELLS, DISTRICTS)
        mournhold = build.tribunal_mournhold_commands(args, base_steps(), tool, Path('/run'), {'qbsp': '/tools/qbsp'}, 8)
        both = module_steps(steps=mournhold, districts=DISTRICTS)
        names = [name for name, _ in both]
        self.assertEqual(names, ['census', 'mwscript', 'tribunal-mournhold-data', 'tribunal-mournhold',
                                 *MODULE_STAGES, 'chim', 'cell-progress', 'image'])
        commands, alone, mh = dict(both), dict(module_steps()), dict(mournhold)
        for name in MODULE_STAGES:
            self.assertEqual(commands[name], alone[name], name)
        for name in ('tribunal-mournhold-data', 'tribunal-mournhold', 'image', 'mwscript', 'census', 'chim'):
            self.assertEqual(commands[name], mh[name], name)
        # both worlds are counted
        tail = [str(p) for p in commands['cell-progress']]
        self.assertEqual(tail.count('--module-chim-world'), 2)
        self.assertIn(str(Path('/run') / 'tribunal-mournhold'), tail)
        self.assertIn(str(Path('/run') / 'bloodmoon-solstheim'), tail)

    def test_the_plan_with_the_module_can_be_recorded(self):
        import json
        import build_parallel
        steps = module_steps()
        self.assertEqual(build_parallel.plan_argument_problems(steps), [])
        json.dumps({'steps': [{'name': name, 'command': command} for name, command in steps]})

    def test_no_base_stage_waits_for_the_module_and_the_module_for_no_world_stage(self):
        from build_parallel import stage_dependencies
        with_module = stage_dependencies(module_steps(), LEFT_OUT)
        without = stage_dependencies(base_steps(), LEFT_OUT)
        for name in ('census', 'chim', 'mwscript'):
            self.assertEqual(with_module[name], without[name], name)
        self.assertEqual(with_module['bloodmoon-solstheim-data'], ())
        self.assertEqual(with_module['bloodmoon-solstheim'], ('census', 'bloodmoon-solstheim-data'))
        for name in ('image', 'cell-progress'):
            self.assertEqual(set(with_module[name]) - set(without[name]), set(MODULE_STAGES), name)


class TheModulesOwnStages(unittest.TestCase):
    def test_the_data_stage_reads_the_base_master_and_bloodmoon_only(self):
        self.assertEqual(dict(module_steps())['bloodmoon-solstheim-data'],
                         tool('presented_data.py', '--data-files', '/data', '--out',
                              Path('/run') / 'bloodmoon-solstheim-data', '--masters', 'Morrowind.esm,Bloodmoon.esm'))

    def test_the_world_stage_builds_the_modules_cells_from_its_own_folder_into_its_own_world(self):
        command = [str(p) for p in dict(module_steps())['bloodmoon-solstheim']]
        self.assertEqual(command[1], 'bloodmoon_solstheim.py')

        def value(option):
            return command[command.index(option) + 1]
        self.assertEqual(value('--data-files'), str(Path('/run') / 'bloodmoon-solstheim-data'))
        self.assertEqual(value('--out'), str(Path('/run') / 'bloodmoon-solstheim'))
        self.assertEqual(value('--unit-cache'), str(Path('/ws') / 'cache/bloodmoon-solstheim-units'))
        # the build's shared storage pool: the units a CHIMport run of these cells stored are taken, never made again
        self.assertEqual(value('--unit-pool'), str(Path('/ws') / 'cache' / 'asset-pool-v1'))
        with mock.patch.dict(os.environ, {'AMIWIND_STORAGE_POOL': '/elsewhere/pool'}):
            named = [str(p) for p in dict(module_steps())['bloodmoon-solstheim']]
        self.assertEqual(named[named.index('--unit-pool') + 1], str(Path('/elsewhere/pool').absolute()))
        self.assertEqual(value('--lighting-type'), 'hybrid')
        self.assertEqual(value('--chim-regions-cells'), CELLS)
        self.assertEqual(command.count('--chim-regions-cells'), 1)
        self.assertNotIn(BASE_CELLS, command)
        self.assertNotIn(str(Path('/run') / 'chim-world'), command)

    def test_the_stages_are_keyed_by_the_base_files_and_bloodmoons_only(self):
        bloodmoon = build_cache.BASE_GAME_INPUTS + build_cache.LAYER_GAME_INPUTS['bloodmoon']
        for stage in MODULE_STAGES:
            self.assertEqual(build_cache.STAGE_GAME_INPUTS[stage], bloodmoon)
            self.assertEqual(build_cache.MODULE_STAGE_LAYERS[stage], ('bloodmoon',))
            self.assertEqual(build_cache.stage_layers_left_out(stage), {'tribunal'})
            self.assertEqual(build_cache.master_list(build_cache.MODULE_STAGE_LAYERS[stage]),
                             ['Morrowind.esm', 'Bloodmoon.esm'])
        # Mournhold's module and the base world keep theirs
        self.assertEqual(build_cache.MODULE_STAGE_LAYERS['tribunal-mournhold'], ('tribunal',))
        self.assertEqual(build_cache.stage_layers_left_out('chim'), {'tribunal', 'bloodmoon'})
        self.assertEqual(build_cache.LAYER_READING_STAGES, set())

    def test_the_stages_own_unit_cache_never_moves_its_key(self):
        self.assertIn(('bloodmoon-solstheim', '--unit-cache'), build_cache.CONTENT_ADDRESSED)
        self.assertIn(('bloodmoon-solstheim', '--unit-cache'), build_cache.CONTENT_ADDRESSED_FROM_THE_START)
        self.assertIn('{WORKSPACE}/' + module.UNIT_CACHE, build_cache.CONTENT_ADDRESSED_FOLDERS)
        with tempfile.TemporaryDirectory() as tmp:
            run, cache = Path(tmp) / 'build' / 'run', Path(tmp) / module.UNIT_CACHE
            run.mkdir(parents=True)
            command = ['python3', 'bloodmoon_solstheim.py', '--out', str(run / 'bloodmoon-solstheim'),
                       '--unit-cache', str(cache), '--jobs', '8']
            metadata = {'workspace': str(Path(tmp)), 'tools': {}}

            def row():
                found, problems = build_cache.external_inputs('bloodmoon-solstheim', command, run, metadata)
                self.assertEqual(problems, [])
                return found
            before = row()
            self.assertEqual(list(before.values()), ['not hashed (content-addressed cache)'])
            (cache / 'mesh').mkdir(parents=True)
            (cache / 'mesh' / 'unit.bin').write_bytes(b'a unit the run stored')
            self.assertEqual(row(), before)
            # and the shared storage pool the stage also names: what it holds never moves the key either
            pool = Path(tmp) / 'cache' / 'asset-pool-v1'
            command += ['--unit-pool', str(pool)]
            pool.mkdir(parents=True)      # a build's workspace holds its pool before any stage of the plan runs
            empty = row()
            self.assertEqual(empty['--unit-pool={WORKSPACE}/cache/asset-pool-v1'],
                             'not hashed (content-addressed storage pool)')
            (pool / 'objects').mkdir(parents=True)
            (pool / 'objects' / 'blob').write_bytes(b'a pooled unit')
            self.assertEqual(row(), empty)

    def test_the_wrapper_runs_the_converter_with_the_modules_own_masters(self):
        self.assertEqual(bloodmoon_solstheim.MASTERS, ('Morrowind.esm', 'Bloodmoon.esm'))
        self.assertEqual(','.join(bloodmoon_solstheim.MASTERS), module.MASTERS)
        seen = {}
        fake = SimpleNamespace(main=lambda: seen.update(masters=os.environ.get('AMIWIND_MASTERS'),
                                                        argv=list(sys.argv)) or 0)
        argv, env = list(sys.argv), os.environ.get('AMIWIND_MASTERS')
        try:
            os.environ['AMIWIND_MASTERS'] = 'Morrowind.esm,Tribunal.esm,Bloodmoon.esm'
            with mock.patch.dict(sys.modules, {'chim_build': fake}):
                self.assertEqual(bloodmoon_solstheim.main(['--out', '/w']), 0)
        finally:
            sys.argv = argv
            if env is None:
                os.environ.pop('AMIWIND_MASTERS', None)
            else:
                os.environ['AMIWIND_MASTERS'] = env
        self.assertEqual(seen['masters'], 'Morrowind.esm,Bloodmoon.esm')
        self.assertEqual(seen['argv'][1:], ['--out', '/w'])
        self.assertTrue(seen['argv'][0].endswith('chim_build.py'))

    def test_the_pool_option_is_the_runners_own_and_never_reaches_the_converter(self):
        self.assertEqual(bloodmoon_solstheim.take_pool(['--out', '/w']), (None, ['--out', '/w']))
        pool, rest = bloodmoon_solstheim.take_pool(['--out', '/w', '--unit-pool', '/pool', '--jobs', '4'])
        self.assertEqual((pool, rest), (Path('/pool'), ['--out', '/w', '--jobs', '4']))
        with self.assertRaises(SystemExit):
            bloodmoon_solstheim.take_pool(['--unit-pool'])

    def test_with_the_pool_the_converters_unit_cache_is_the_pooled_one_for_this_process_only(self):
        import chim.build
        from chim.units import PooledUnitCache, UnitCache
        plain = chim.build.UnitCache
        self.assertIs(plain, UnitCache)
        said = []
        try:
            with tempfile.TemporaryDirectory() as tmp:
                made = bloodmoon_solstheim.pooled_units(Path(tmp) / 'pool')
                cache = chim.build.UnitCache(Path(tmp) / 'units')
                # the converter's own test of a cache it is handed, and of the one it makes, both hold
                self.assertIsInstance(cache, UnitCache)
                self.assertIsInstance(cache, PooledUnitCache)
                self.assertEqual((cache.pool, cache.link, cache.store), (Path(tmp) / 'pool', True, True))
                self.assertIsNone(chim.build.UnitCache(None).folder)
                self.assertEqual(len(made), 2)
                # a unit one cache stores is found by another cache on another folder through the pool
                cache.put('mesh', 'f' * 64, {'value': 1})
                other = chim.build.UnitCache(Path(tmp) / 'units-of-another-run')
                found = other.get('mesh', 'f' * 64)
                if cache.pool_stats['stored_units']:         # the pool stores only as the build user (not as root)
                    self.assertEqual(found, {'value': 1})
                    self.assertEqual(other.pool_stats['reused_units'], 1)
                said.append(bloodmoon_solstheim.pool_line(made))
        finally:
            chim.build.UnitCache = plain
        self.assertIn('MODULE bloodmoon-solstheim: storage pool:', said[0])
        self.assertIn('taken from the pool', said[0])
        # without the option nothing is installed
        seen = {}
        fake = SimpleNamespace(main=lambda: seen.update(cache=chim.build.UnitCache) or 0)
        argv = list(sys.argv)
        try:
            with mock.patch.dict(sys.modules, {'chim_build': fake}), mock.patch.dict(os.environ, {}):
                self.assertEqual(bloodmoon_solstheim.main(['--out', '/w']), 0)
        finally:
            sys.argv = argv
        self.assertIs(seen['cache'], UnitCache)

    def test_the_pooled_cache_crosses_into_the_converters_worker_processes(self):
        # SOL-MODULE-CACHE-NOT-PICKLED-68: the converter pickles its cache for its workers; the class made inside
        # pooled_units could not be pickled by name, and the v0.0.68-dev3 build stopped in the module's world stage.
        import pickle
        import chim.build
        from chim.units import PooledUnitCache
        plain = chim.build.UnitCache
        try:
            with tempfile.TemporaryDirectory() as tmp:
                bloodmoon_solstheim.pooled_units(Path(tmp) / 'pool')
                cache = chim.build.UnitCache(Path(tmp) / 'units')
                back = pickle.loads(pickle.dumps(cache))
                self.assertIsInstance(back, PooledUnitCache)
                self.assertEqual((back.folder, back.pool, back.link, back.store),
                                 (cache.folder, cache.pool, cache.link, cache.store))
        finally:
            chim.build.UnitCache = plain


class TheCellLists(unittest.TestCase):
    """The module takes Bloodmoon's named set from the tracker file, only when Bloodmoon is among the masters."""
    THREE = ['Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm']
    BUILDER = {'builder': 'chim', 'chim_areas': []}

    def resolve(self, masters, finished=((-22, 16), (-22, 17)), builder=None, **more):
        values = dict(chim_regions=[], miniwind=False, data_files=None)
        values.update(more)
        args = SimpleNamespace(**values)
        seen, said = [], []

        def plan(names, status, towns=(), one_map_only=False):
            seen.append((list(names), status, tuple(towns)))
            return regions.ownership({cell: 'land' for cell in finished}, {'values': names}), []
        with mock.patch.object(regions, 'plan', side_effect=plan), \
                mock.patch.object(regions, 'owned_land_problems', return_value=[]):
            record = module.resolve(args, masters, builder or self.BUILDER, 'status.json', log=said.append)
        return args, record, seen, said

    def test_the_module_takes_bloodmoons_set_when_bloodmoon_is_selected(self):
        for masters in (self.THREE, ['Morrowind.esm', 'Bloodmoon.esm']):
            args, record, seen, said = self.resolve(masters)
            self.assertEqual(seen, [(['solstheim'], 'status.json', ())], masters)
            self.assertEqual(args.bloodmoon_solstheim_cells, '-22,16:l -22,17:l', masters)
            self.assertEqual(record['counts']['cells'], 2, masters)
            self.assertEqual(len(said), 1)
            self.assertIn('Module bloodmoon-solstheim: 2 Solstheim cells', said[0])

    def test_the_module_is_left_out_without_bloodmoon_a_chim_builder_or_finished_cells(self):
        cases = (dict(masters=['Morrowind.esm']), dict(masters=['Morrowind.esm', 'Tribunal.esm']),
                 dict(masters=self.THREE, miniwind=True), dict(masters=self.THREE, chim_regions=['1,1']),
                 dict(masters=self.THREE, builder={'builder': 'classic', 'chim_areas': []}),
                 dict(masters=self.THREE, finished=()))
        for case in cases:
            args, record, _seen, said = self.resolve(**case)
            self.assertIsNone(record, case)
            self.assertIsNone(args.bloodmoon_solstheim_cells, case)
            self.assertEqual(said, [], case)

    def test_the_builder_is_asked_only_when_bloodmoon_is_selected(self):
        asked = []

        def builder():
            asked.append(1)
            return self.BUILDER
        self.resolve(['Morrowind.esm', 'Tribunal.esm'], builder=builder)
        self.assertEqual(asked, [])
        self.resolve(self.THREE, builder=builder)
        self.assertEqual(asked, [1])

    def test_a_failed_cell_preflight_stops_before_any_stage_and_names_the_module(self):
        args = SimpleNamespace(chim_regions=[], miniwind=False, data_files=None)
        with mock.patch.object(regions, 'plan', return_value=(regions.ownership({(-22, 16): 'land'},
                                                                                {'values': ['solstheim']}), ['bad row'])), \
                mock.patch.object(regions, 'owned_land_problems', return_value=[]):
            with self.assertRaisesRegex(ValueError, 'bloodmoon-solstheim.*failed its cell preflight'):
                module.resolve(args, self.THREE, self.BUILDER, 'status.json')
        self.assertIsNone(args.bloodmoon_solstheim_cells)

    def test_no_finished_cell_is_no_module_and_never_a_stop(self):
        # the tracker reference of a line whose Solstheim cells are not finished yet: the plan calls the empty
        # selection a problem; a build with Bloodmoon selected must then be the build without the module, not stop
        args = SimpleNamespace(chim_regions=[], miniwind=False, data_files=None)
        said = []
        empty = regions.ownership({}, {'values': ['solstheim']})
        with mock.patch.object(regions, 'plan', return_value=(empty, ['the selection solstheim holds no cell'])), \
                mock.patch.object(regions, 'owned_land_problems', side_effect=AssertionError('asked')):
            self.assertIsNone(module.resolve(args, self.THREE, self.BUILDER, 'status.json', log=said.append))
        self.assertIsNone(args.bloodmoon_solstheim_cells)
        self.assertEqual(said, ['Module bloodmoon-solstheim: not built: the selection solstheim holds no cell'])
        # and on the source tree's own reference, whatever it holds today, the module resolves without an error
        module.resolve(SimpleNamespace(chim_regions=[], miniwind=False, data_files=None), self.THREE, self.BUILDER,
                       ROOT / 'docs' / 'chim' / 'cell-progress-reference.json', log=said.append)

    def test_the_named_set_is_the_one_the_tracker_sets_know(self):
        self.assertEqual(regions.layer_sets()[module.MASTER], 'solstheim')

    def test_build_calls_the_module_and_holds_none_of_it(self):
        import inspect
        text = inspect.getsource(build)
        self.assertEqual(text.count("__import__('bloodmoon_solstheim_module')"), 2)
        self.assertNotIn('bloodmoon-solstheim-data', text)


class TheImageTakesSolstheimAsAStoreOfItsOwn(unittest.TestCase):
    def test_the_image_option_only_with_the_modules_stage_and_bloodmoon(self):
        names = [name for name, _ in module_steps()]
        self.assertEqual(layer_stores.image_options(['Bloodmoon'], names, '/run'),
                         ['--chim-layer-world', 'chimsol=%s' % (Path('/run') / 'bloodmoon-solstheim')])
        self.assertEqual(layer_stores.image_options(['Tribunal'], names, '/run'), [])
        self.assertEqual(layer_stores.image_options(['Bloodmoon'], [n for n, _ in base_steps()], '/run'), [])
        both = [name for name, _ in module_steps(steps=build.tribunal_mournhold_commands(
            module_args(CELLS, DISTRICTS), base_steps(), tool, Path('/run'), {'qbsp': '/tools/qbsp'}, 8))]
        self.assertEqual(layer_stores.image_options(['Tribunal', 'Bloodmoon'], both, '/run'),
                         ['--chim-layer-world', 'chimmh=%s' % (Path('/run') / 'tribunal-mournhold'),
                          '--chim-layer-world', 'chimsol=%s' % (Path('/run') / 'bloodmoon-solstheim')])

    def test_two_stages_for_one_store_are_refused_before_any_stage(self):
        names = [name for name, _ in module_steps()] + [layer_stores.stage_name('Bloodmoon')]
        with self.assertRaisesRegex(ValueError, 'both make the store chimsol'):
            layer_stores.image_options(['Bloodmoon'], names, '/run')

    def test_the_store_is_solstheims_land_and_the_module_opens_its_cells_to_each_other(self):
        self.assertEqual(layer_stores.MODULE_STAGES['bloodmoon-solstheim'],
                         {'layer': 'Bloodmoon', 'store': 'chimsol', 'kind': 'frames'})
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            test_land = sol_test.land_of('chimsol', run / 'chim-sol')
            self.assertEqual((test_land['data_stage'], test_land['edges'], test_land['flames']),
                             ('chim-sol-data', 'closed', False))
            (run / 'bloodmoon-solstheim-data').mkdir()
            land = sol_test.land_of('chimsol', run / 'bloodmoon-solstheim')
            self.assertEqual((land['data_stage'], land['edges'], land['flames']),
                             ('bloodmoon-solstheim-data', 'alone', True))
            self.assertEqual((land['prefix'], land['limit'], land['directory']),
                             ('sl', 3840, 'world/regions-sl.awr'))
            self.assertNotIn('module', land)
            # Mournhold's land is the same with or without that folder; a store that is no land has none
            self.assertEqual(sol_test.land_of('chimmh', run / 'tribunal-mournhold')['edges'], 'alone')
            self.assertIsNone(sol_test.land_of('chimiti', run / 'x'))
        frames = [{'cell': [-22, 16]}, {'cell': [-22, 17]}, {'cell': [-20, 25]}]
        self.assertEqual(sol_test.closed_frames(frames, 'alone'), {(-20, 25)})
        self.assertEqual(sol_test.closed_frames(frames, 'closed'), {(-22, 16), (-22, 17), (-20, 25)})

    def test_the_frame_map_names_and_the_disk_layout(self):
        names = expansion_preflight.module_map_names(CELLS, 'chimsol')
        self.assertEqual(names, ['sl0000', 'sl0001', 'sl0002'])
        import layout_plan
        self.assertEqual(layout_plan.movable_unit('id1/chimsol/world.cwi'), 'id1/chimsol/')


class TheFirstMinuteChecks(unittest.TestCase):
    def test_the_module_is_known_to_every_module_check(self):
        self.assertEqual(expansion_preflight.SET_MODULES['Bloodmoon.esm'],
                         ('bloodmoon-solstheim', module.CELLS_OPTION))
        self.assertEqual(expansion_preflight.MODULE_STORES[module.CELLS_OPTION], 'chimsol')
        self.assertEqual(expansion_preflight.MODULE_WORLD_STAGES['bloodmoon-solstheim'], 'chimsol')
        self.assertEqual(set(expansion_preflight.MODULE_RESOLVERS),
                         {name for name, _ in expansion_preflight.SET_MODULES.values()})
        entry = [e for e in build_preflight.EARLY_CHECKS if e[1] == build_preflight.AFTER + 'bloodmoon-solstheim']
        self.assertEqual(entry, [('module-store-maps', build_preflight.AFTER + 'bloodmoon-solstheim',
                                  'expansion_preflight:module_store_after')])

    def problems(self, args, finished):
        said = []
        with mock.patch.object(expansion_preflight, 'finished_set_cells', return_value=sorted(finished)):
            found = expansion_preflight.module_set_problems(['Morrowind.esm', 'Bloodmoon.esm'], args, 'status.json',
                                                            said.append)
        return found, said

    def test_finished_solstheim_cells_that_the_module_does_not_take_are_a_problem(self):
        args = SimpleNamespace(bloodmoon_solstheim_cells=None, chim_regions=[], miniwind=False)
        found, _ = self.problems(args, {(-22, 16), (-22, 17)})
        self.assertEqual(len(found), 1)
        self.assertIn('the module bloodmoon-solstheim takes none', found[0])
        self.assertIn('tools/bloodmoon_solstheim_module.py resolve', found[0])
        # switching the presented districts off is Mournhold's reason, never Solstheim's
        args.presented_exteriors = 'off'
        self.assertEqual(len(self.problems(args, {(-22, 16)})[0]), 1)

    def test_the_module_taking_them_passes_and_says_so_and_no_finished_cell_passes(self):
        args = SimpleNamespace(bloodmoon_solstheim_cells='-22,16:l -22,17:l', chim_regions=[], miniwind=False)
        found, said = self.problems(args, {(-22, 16), (-22, 17)})
        self.assertEqual(found, [])
        self.assertTrue(any('2 built by the module bloodmoon-solstheim' in line for line in said))
        found, _ = self.problems(args, {(-22, 16), (-22, 17), (-20, 25)})
        self.assertEqual(len(found), 1)           # the module takes fewer cells than the tracker calls finished
        args = SimpleNamespace(bloodmoon_solstheim_cells=None, chim_regions=[], miniwind=False)
        found, said = self.problems(args, set())
        self.assertEqual(found, [])
        self.assertTrue(any('none built (none finished)' in line for line in said))

    def test_a_solstheim_test_image_is_the_only_build_that_may_leave_finished_cells_out(self):
        # a --chim-sol-test image leaves the module out (resolve's NOT BUILT record): the full-parity check accepts that
        # on a development version and says so; every other build that leaves them out is refused, a release
        # candidate or final with the test route too (on 8b46aae03 the test image's plan check was refused here)
        finished = {(-22, 16), (-22, 17)}
        record = {'built': False, 'reason': '--chim-sol-test names Solstheim\'s cells for this image'}
        test_image = SimpleNamespace(bloodmoon_solstheim_cells=None, chim_regions=[], miniwind=False,
                                     chim_sol_test='-26,26:l', bloodmoon_solstheim_record=record)
        with mock.patch.dict(os.environ, {'AMIWIND_RUN_VERSION': '0.0.68-dev3'}):
            found, said = self.problems(test_image, finished)
        self.assertEqual(found, [])
        line = [line for line in said if line.startswith('Expansion cells: Bloodmoon.esm')]
        self.assertEqual(len(line), 1)
        self.assertIn('2 finished cell(s), none built (--chim-sol-test: a test image of named Solstheim cells',
                      line[0])
        for version in ('0.0.68-rc1', '0.0.68'):
            with mock.patch.dict(os.environ, {'AMIWIND_RUN_VERSION': version}):
                found, _ = self.problems(test_image, finished)
            self.assertEqual(len(found), 1, version)
            self.assertIn('the module bloodmoon-solstheim takes none', found[0])
        # the option without the module's own record, or a plain build that takes none: refused as before
        no_record = SimpleNamespace(**dict(vars(test_image), bloodmoon_solstheim_record=None))
        plain = SimpleNamespace(bloodmoon_solstheim_cells=None, chim_regions=[], miniwind=False, chim_sol_test=None,
                                bloodmoon_solstheim_record=None)
        for args in (no_record, plain):
            with mock.patch.dict(os.environ, {'AMIWIND_RUN_VERSION': '0.0.68-dev3'}):
                found, _ = self.problems(args, finished)
            self.assertEqual(len(found), 1)
            self.assertIn('the module bloodmoon-solstheim takes none', found[0])
        # the reason is Solstheim's alone: Mournhold's module taking none is never excused by it
        self.assertEqual(expansion_preflight.SET_MODULES['Tribunal.esm'][0], 'tribunal-mournhold')
        mournhold = SimpleNamespace(**dict(vars(test_image), tribunal_mournhold_cells=None))
        with mock.patch.object(expansion_preflight, 'finished_set_cells', return_value=[(-12, -30)]), \
                mock.patch.dict(os.environ, {'AMIWIND_RUN_VERSION': '0.0.68-dev3'}):
            found = expansion_preflight.module_set_problems(['Morrowind.esm', 'Tribunal.esm'], mournhold,
                                                            'status.json', lambda line: None)
        self.assertEqual(len(found), 1)
        self.assertIn('tribunal-mournhold takes none', found[0])

    def test_a_store_too_large_for_one_partition_is_named_right_after_its_stage(self):
        # the disk layout moves a store as one unit and never splits it: the densest forest frame measured is
        # 6.5 MB, and 144 such frames (936 MB) fit; a store that does not fit is a problem minutes after the world
        # stage, not in the image step's last minutes
        self.assertIsNone(expansion_preflight.store_unit_problem('chimsol', [6_512_604] * 144))
        problem = expansion_preflight.store_unit_problem('chimsol', [6_512_604] * 320)
        self.assertIn('the store chimsol is 2084033280 bytes in 320 files', problem)
        self.assertIn('moves as one unit', problem)
        # counted as the planner counts: the headroom and the limit decide
        self.assertIsNone(expansion_preflight.store_unit_problem('chimsol', [1024 * 1024] * 10, headroom_mib=1,
                                                                 limit=16 * 1024 * 1024))
        self.assertIsNotNone(expansion_preflight.store_unit_problem('chimsol', [1024 * 1024] * 10, headroom_mib=8,
                                                                    limit=16 * 1024 * 1024))

    def test_the_images_last_tables_know_the_modules_frame_maps(self):
        names = expansion_preflight.module_map_names(CELLS, 'chimsol')
        self.assertEqual(expansion_preflight.finalize_table_problems(names, 'chimsol'), [])
        last = sol_test.map_name(3839, 'sl', 3840)
        self.assertEqual(expansion_preflight.finalize_table_problems([last], 'chimsol'), [])
        said = []
        context = build_preflight.EarlyContext('inputs', module_args(), log=said.append)
        self.assertEqual(expansion_preflight.module_frame_maps(context), [])
        self.assertTrue(any('store chimsol, 3 frame maps (sl0000 .. sl0002)' in line for line in said))


if __name__ == '__main__':
    unittest.main()
