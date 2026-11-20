# SPDX-License-Identifier: GPL-3.0-only
"""The build module tribunal-mournhold (MOURNHOLD-EXTERIOR-CELLS-66): Mournhold's districts as a world of their own.

The module's rule, held here: its two stages are in the plan only with Tribunal selected and district cells to build;
the base stage list and every base command are the ones of a build without it; its stages are keyed by the base files
and Tribunal's files only; no base stage waits for it; the base world's cell list never holds a district cell."""
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import build  # noqa: E402
import build_cache  # noqa: E402
import build_parser  # noqa: E402
import build_preflight  # noqa: E402
import expansion_preflight  # noqa: E402
from chim import layer_stores, regions, sol_test  # noqa: E402

CELLS = '-12,-30:l -12,-29:l 0,-30:l'
BASE_CELLS = '1,1:l 2,1:l'
LEFT_OUT = {'intro', 'world-terrain', 'world-scenery', 'music', 'media', 'engine', 'dialogue-lookup', 'npc-gallery',
            'focus', 'books', 'chargen', 'item-models', 'harvest', 'hand-catalog', 'world-flora',
            'chim-interiors', 'chim-room-batches', 'seam-audit'}


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


def module_args(cells=CELLS):
    return SimpleNamespace(tribunal_mournhold_cells=cells, chim_regions_cells=BASE_CELLS, data_files='/data',
                           workspace=Path('/ws'), sdk='/sdk')


def module_steps(cells=CELLS):
    return build.tribunal_mournhold_commands(module_args(cells), base_steps(), tool, Path('/run'),
                                             {'qbsp': '/tools/qbsp'}, 8)


class TheBaseStagesAreUnchanged(unittest.TestCase):
    def test_without_the_module_the_plan_is_the_one_before(self):
        for cells in (None, ''):
            self.assertEqual(module_steps(cells), base_steps())

    def test_with_the_module_every_base_stage_keeps_its_place_and_its_command(self):
        steps = module_steps()
        names = [name for name, _ in steps]
        self.assertEqual(names, ['census', 'mwscript', 'tribunal-mournhold-data', 'tribunal-mournhold', 'chim',
                                 'cell-progress', 'image'])
        # the base stage list: the plan without the module's two stages, in the same order
        self.assertEqual([n for n in names if not n.startswith('tribunal-')], [n for n, _ in base_steps()])
        commands, before = dict(steps), dict(base_steps())
        for name in ('census', 'chim'):
            self.assertEqual(commands[name], before[name], name)
        # the tracker data counts the districts' world as the build's own (TRACKERS-MOURNHOLD-NOT-COUNTED-67): the
        # stage takes the presentation receipt and the module's world after its unchanged base command
        self.assertEqual(commands['cell-progress'][:len(before['cell-progress'])], before['cell-progress'])
        self.assertEqual([str(p) for p in commands['cell-progress'][len(before['cell-progress']):]],
                         ['--presented', str(Path('/run') / 'tribunal-mournhold-data' / 'presented-data.json'),
                          '--module-chim-world', str(Path('/run') / 'tribunal-mournhold')])
        # the image installs every stage's output and the scripts make the merged variant of a small table: they
        # take the module's receipt and its cells, after their unchanged base command
        receipt = str(Path('/run') / 'tribunal-mournhold-data' / 'presented-data.json')
        for name in ('image', 'mwscript'):
            self.assertEqual(commands[name][:len(before[name])], before[name], name)
            self.assertEqual([str(p) for p in commands[name][len(before[name]):]],
                             ['--presented-receipt', receipt, '--presented-cells', CELLS], name)

    def test_the_plan_with_the_module_can_be_recorded(self):
        # BUILD-NPCLOD-PATH-ARG-34, seen again: the receipt option went into the image's and the scripts' commands
        # as a Path, and the build stopped 171 s in when its plan was written to build-state.json. Every argument of
        # the plan is a string, the plan serializes, and a plan that does not is refused before the first stage
        import json
        import build_parallel
        steps = module_steps()
        self.assertEqual(build_parallel.plan_argument_problems(steps), [])
        for name, command in steps:
            self.assertTrue(all(isinstance(part, str) for part in command), name)
        json.dumps({'steps': [{'name': name, 'command': command} for name, command in steps]})
        build_parallel.require_plan_arguments(steps)
        bad = steps + [('late', ['python3', 'x.py', '--out', Path('/run/late')])]
        problems = build_parallel.plan_argument_problems(bad)
        self.assertEqual(len(problems), 1)
        self.assertIn('stage late: argument 3', problems[0])
        self.assertIn("after '--out'", problems[0])
        with self.assertRaisesRegex(ValueError, 'cannot be recorded'):
            build_parallel.require_plan_arguments(bad)
        # and the state file itself is always written: a path in a record is written as its text, so the save that
        # records a build's end cannot fail and leave the run reading "running"
        state = json.loads(build_parallel.state_text({'status': 'failed', 'steps': [{'command': bad[-1][1]}]}))
        self.assertEqual(state['status'], 'failed')
        self.assertEqual(state['steps'][0]['command'][-1], str(Path('/run/late')))
        self.assertEqual(build_parallel.state_text({'a': 1}), json.dumps({'a': 1}, indent=2) + '\n')

    def test_no_base_stage_waits_for_the_module_and_the_module_for_no_world_stage(self):
        from build_parallel import stage_dependencies
        with_module = stage_dependencies(module_steps(), LEFT_OUT)
        without = stage_dependencies(base_steps(), LEFT_OUT)
        for name in ('census', 'chim'):
            self.assertEqual(with_module[name], without[name], name)
        # only the tracker data waits for the module: it counts the districts' world (TRACKERS-MOURNHOLD-NOT-COUNTED-67)
        self.assertEqual(set(with_module['cell-progress']) - set(without['cell-progress']),
                         {'tribunal-mournhold-data', 'tribunal-mournhold'})
        self.assertEqual(with_module['tribunal-mournhold-data'], ())
        self.assertEqual(with_module['tribunal-mournhold'], ('census', 'tribunal-mournhold-data'))
        self.assertEqual(set(with_module['image']) - set(without['image']),
                         {'tribunal-mournhold-data', 'tribunal-mournhold'})
        self.assertEqual(set(with_module['mwscript']) - set(without['mwscript']), {'tribunal-mournhold-data'})


class TheModulesOwnStages(unittest.TestCase):
    def test_the_data_stage_presents_the_base_master_and_tribunal_only(self):
        command = dict(module_steps())['tribunal-mournhold-data']
        self.assertEqual(command, tool('presented_data.py', '--data-files', '/data', '--out',
                                       Path('/run') / 'tribunal-mournhold-data',
                                       '--masters', 'Morrowind.esm,Tribunal.esm'))

    def test_the_world_stage_builds_the_modules_cells_from_its_own_folder_into_its_own_world(self):
        command = [str(p) for p in dict(module_steps())['tribunal-mournhold']]
        self.assertEqual(command[1], 'tribunal_mournhold.py')

        def value(option):
            return command[command.index(option) + 1]
        self.assertEqual(value('--data-files'), str(Path('/run') / 'tribunal-mournhold-data'))
        self.assertEqual(value('--out'), str(Path('/run') / 'tribunal-mournhold'))
        self.assertEqual(value('--unit-cache'), str(Path('/ws') / 'cache/tribunal-mournhold-units'))
        self.assertEqual(value('--lighting-type'), 'hybrid')
        self.assertEqual(value('--chim-regions-cells'), CELLS)
        # the base world's cell list is not on the module's command line: a change to it re-keys no module stage
        self.assertEqual(command.count('--chim-regions-cells'), 1)
        self.assertNotIn(BASE_CELLS, command)
        self.assertNotIn(str(Path('/run') / 'chim-world'), command)

    def test_the_stages_are_keyed_by_the_base_files_and_tribunals_only(self):
        tribunal = build_cache.BASE_GAME_INPUTS + build_cache.LAYER_GAME_INPUTS['tribunal']
        for stage in ('tribunal-mournhold-data', 'tribunal-mournhold'):
            self.assertEqual(build_cache.STAGE_GAME_INPUTS[stage], tribunal)
            self.assertEqual(build_cache.MODULE_STAGE_LAYERS[stage], ('tribunal',))
            # Bloodmoon's rows of the measured mesh tables are left out of the module's key, Tribunal's are in it
            self.assertEqual(build_cache.stage_layers_left_out(stage), {'bloodmoon'})
            self.assertEqual(build_cache.master_list(build_cache.MODULE_STAGE_LAYERS[stage]),
                             ['Morrowind.esm', 'Tribunal.esm'])
        # and the base world stage reads neither layer's rows, so no expansion row re-keys it
        self.assertEqual(build_cache.stage_layers_left_out('chim'), {'tribunal', 'bloodmoon'})
        self.assertEqual(build_cache.LAYER_READING_STAGES, set())

    def test_the_stages_own_unit_cache_never_moves_its_key(self):
        # BUILD-MODULE-UNIT-CACHE-IN-KEY-67: the stage's key hashed its own unit cache folder, so the units a run
        # stored re-keyed the stage: a build resumed after its image step failed would have run the stage again.
        # The folder's row is the same before the folder exists, when it is empty and when it has grown
        import tempfile
        self.assertIn(('tribunal-mournhold', '--unit-cache'), build_cache.CONTENT_ADDRESSED)
        self.assertIn(('tribunal-mournhold', '--unit-cache'), build_cache.CONTENT_ADDRESSED_FROM_THE_START)
        self.assertIn('{WORKSPACE}/cache/tribunal-mournhold-units', build_cache.CONTENT_ADDRESSED_FOLDERS)
        with tempfile.TemporaryDirectory() as tmp:
            run, cache = Path(tmp) / 'build' / 'run', Path(tmp) / 'cache' / 'tribunal-mournhold-units'
            run.mkdir(parents=True)
            command = ['python3', 'tribunal_mournhold.py', '--out', str(run / 'tribunal-mournhold'),
                       '--unit-cache', str(cache), '--jobs', '8']
            metadata = {'workspace': str(Path(tmp)), 'tools': {}}

            def row():
                found, problems = build_cache.external_inputs('tribunal-mournhold', command, run, metadata)
                self.assertEqual(problems, [])
                return found
            before = row()
            self.assertEqual(list(before.values()), ['not hashed (content-addressed cache)'])
            cache.mkdir(parents=True)
            self.assertEqual(row(), before)
            (cache / 'mesh').mkdir()
            (cache / 'mesh' / 'unit.bin').write_bytes(b'a unit the run stored')
            self.assertEqual(row(), before)
            # another stage naming a folder outside the run is still keyed by what the folder holds
            plain = Path(tmp) / 'elsewhere'
            plain.mkdir()
            reader = ['python3', 'some_stage.py', '--input', str(plain)]
            first = build_cache.external_inputs('some-stage', reader, run, metadata)[0]
            (plain / 'new.bin').write_bytes(b'more')
            self.assertNotEqual(build_cache.external_inputs('some-stage', reader, run, metadata)[0], first)

    def test_the_wrapper_runs_the_converter_with_the_modules_own_masters(self):
        import tribunal_mournhold
        self.assertEqual(tribunal_mournhold.MASTERS, ('Morrowind.esm', 'Tribunal.esm'))
        self.assertEqual(','.join(tribunal_mournhold.MASTERS), build.TRIBUNAL_MOURNHOLD_MASTERS)
        seen = {}
        fake = SimpleNamespace(main=lambda: seen.update(masters=os.environ.get('AMIWIND_MASTERS'),
                                                        argv=list(sys.argv)) or 0)
        argv, env = list(sys.argv), os.environ.get('AMIWIND_MASTERS')
        try:
            os.environ['AMIWIND_MASTERS'] = 'Morrowind.esm,Tribunal.esm,Bloodmoon.esm'
            with mock.patch.dict(sys.modules, {'chim_build': fake}):
                self.assertEqual(tribunal_mournhold.main(['--out', '/w']), 0)
        finally:
            sys.argv = argv
            if env is None:
                os.environ.pop('AMIWIND_MASTERS', None)
            else:
                os.environ['AMIWIND_MASTERS'] = env
        self.assertEqual(seen['masters'], 'Morrowind.esm,Tribunal.esm')
        self.assertEqual(seen['argv'][1:], ['--out', '/w'])
        self.assertTrue(seen['argv'][0].endswith('chim_build.py'))


class TheCellLists(unittest.TestCase):
    """The base world's cell list never takes an expansion's named set; the module takes Tribunal's, read from the
    selection itself (BUILD-LAYER-SETS-NEVER-TAKEN-67: the masters were read from a value set only later)."""

    def args(self, **more):
        values = dict(chim_regions=[], chim_regions_status=None, miniwind=False, chim_region_rows=None, dlc=None,
                      dlc_off=False, no_dlc=False, presented_exteriors=None, data_files=None)
        values.update(more)
        return SimpleNamespace(**values)            # no expansion_layers: it does not exist yet when these run

    def plans(self, args):
        seen = []

        def plan(values, status, towns=(), one_map_only=False):
            seen.append(list(values))
            return regions.ownership({(-12, -30): 'land', (-12, -29): 'land'} if values == ['mournhold']
                                     else {(1, 1): 'land'}, {'values': values}), []
        builder = {'builder': 'chim', 'chim_areas': []}
        with mock.patch.object(regions, 'plan', side_effect=plan), \
                mock.patch.object(regions, 'owned_land_problems', return_value=[]), \
                mock.patch.object(regions, 'ocean_land_problems', return_value=[]), \
                mock.patch.object(regions, 'ocean_map_split', return_value=([], [], [])):
            build.resolve_chim_regions(args, builder)
            record = build.resolve_tribunal_mournhold(args, builder)
        return seen, record

    def test_the_base_list_is_the_default_list_alone_whatever_is_selected(self):
        for more in ({}, {'dlc': 'tribunal'}, {'dlc': 'bloodmoon'}, {'no_dlc': True}):
            args = self.args(**more)
            seen, _ = self.plans(args)
            self.assertEqual(len(seen[0]), 1, more)
            self.assertTrue(seen[0][0].startswith('@'), more)
            self.assertEqual(args.chim_regions_cells, '1,1:l', more)

    def test_the_module_takes_tribunals_set_when_tribunal_is_selected(self):
        for more in ({}, {'dlc': 'tribunal'}, {'presented_exteriors': 'on'}):
            args = self.args(**more)
            seen, record = self.plans(args)
            self.assertEqual(seen[1], ['mournhold'], more)
            self.assertEqual(args.tribunal_mournhold_cells, '-12,-30:l -12,-29:l', more)
            self.assertEqual(record['counts']['cells'], 2, more)

    def test_the_module_is_left_out_with_its_reason(self):
        for more in ({'no_dlc': True}, {'dlc_off': True}, {'dlc': 'bloodmoon'}, {'presented_exteriors': 'off'},
                     {'miniwind': True, 'chim_regions': ['none']}):
            args = self.args(**more)
            _, record = self.plans(args)
            self.assertIsNone(record, more)
            self.assertIsNone(args.tribunal_mournhold_cells, more)

    def test_a_cell_list_of_the_callers_own_builds_those_cells_and_no_module(self):
        args = self.args(chim_regions=['1,1'])
        _, record = self.plans(args)
        self.assertIsNone(record)
        self.assertIsNone(args.tribunal_mournhold_cells)


class TheFirstMinuteCheck(unittest.TestCase):
    """A selected expansion's finished cells are built by its module, or the log says why not; finished cells that
    nothing takes stop the build before any stage."""

    def problems(self, masters, finished, **more):
        values = dict(tribunal_mournhold_cells=None, presented_exteriors=None, chim_regions=None, miniwind=False)
        values.update(more)
        lines = []
        with mock.patch.object(expansion_preflight, 'finished_set_cells',
                               side_effect=lambda name, status: list(finished.get(name, ()))):
            found = expansion_preflight.module_set_problems(masters, SimpleNamespace(**values), 'status.json',
                                                            lines.append)
        return found, lines

    def test_finished_district_cells_that_no_module_takes_are_a_problem(self):
        both = ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm')
        finished = {'mournhold': [(-12, -30), (-12, -29)], 'solstheim': [(-22, 20)]}
        found, lines = self.problems(both, finished)
        self.assertEqual(len(found), 1)
        self.assertIn('Tribunal.esm is selected', found[0])
        self.assertIn('tribunal-mournhold takes none', found[0])
        # Solstheim's cells have no module yet: said, never failed
        self.assertTrue(any('Bloodmoon.esm, named set solstheim: 1 finished cell(s), NOT built' in line
                            for line in lines))

    def test_the_module_taking_them_passes_and_says_so(self):
        finished = {'mournhold': [(-12, -30), (-12, -29)]}
        found, lines = self.problems(('Morrowind.esm', 'Tribunal.esm'), finished,
                                     tribunal_mournhold_cells='-12,-30:l -12,-29:l')
        self.assertEqual(found, [])
        self.assertTrue(any('2 built by the module tribunal-mournhold' in line for line in lines))
        # fewer cells than the tracker calls finished: a problem
        found, _ = self.problems(('Morrowind.esm', 'Tribunal.esm'), finished, tribunal_mournhold_cells='-12,-30:l')
        self.assertEqual(len(found), 1)

    def test_a_stated_reason_or_no_finished_cell_passes(self):
        finished = {'mournhold': [(-12, -30)]}
        for more in ({'presented_exteriors': 'off'}, {'chim_regions': ['1,1']}, {'miniwind': True}):
            found, lines = self.problems(('Morrowind.esm', 'Tribunal.esm'), finished, **more)
            self.assertEqual(found, [], more)
            self.assertTrue(any('none built' in line for line in lines), more)
        self.assertEqual(self.problems(('Morrowind.esm', 'Tribunal.esm'), {})[0], [])
        self.assertEqual(self.problems(('Morrowind.esm',), finished)[0], [])

    def test_the_check_is_registered_for_the_first_minute(self):
        entry = [e for e in build_preflight.EARLY_CHECKS if e[0] == 'expansion-module-cells']
        self.assertEqual(entry, [('expansion-module-cells', 'inputs', 'expansion_preflight:module_sets')])
        # a build without CHIM region cells, or the base game alone, has nothing to check
        context = build_preflight.EarlyContext('inputs', SimpleNamespace(chim_regions_cells=None, data_files=None),
                                               masters=('Morrowind.esm', 'Tribunal.esm'), log=lambda line: None)
        self.assertEqual(expansion_preflight.module_sets(context), [])
        context = build_preflight.EarlyContext('inputs', SimpleNamespace(chim_regions_cells='1,1:l', data_files=None),
                                               masters=('Morrowind.esm',), log=lambda line: None)
        self.assertEqual(expansion_preflight.module_sets(context), [])


class TheImageTakesTheDistrictsAsAStoreOfTheirOwn(unittest.TestCase):
    def test_the_image_option_only_with_the_modules_stage_and_tribunal(self):
        names = {'chim', 'image', 'tribunal-mournhold'}
        self.assertEqual(layer_stores.image_options(['Tribunal', 'Bloodmoon'], names, '/run'),
                         ['--chim-layer-world', 'chimmh=' + str(Path('/run') / 'tribunal-mournhold')])
        self.assertEqual(layer_stores.image_options(['Bloodmoon'], names, '/run'), [])
        self.assertEqual(layer_stores.image_options(['Tribunal'], {'chim', 'image'}, '/run'), [])
        self.assertEqual(layer_stores.parse(['chimmh=/w']), [('chimmh', Path('/w'))])
        self.assertEqual(layer_stores.store_kinds()['chimmh'], 'frames')

    def test_the_districts_frames_hold_their_doors_like_base_region_frames(self):
        # the image's door tables (tools/build_aga.py layer_region_frames): each frame of the module's world under
        # the frame map name its install gives it, in the world table's order
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            world = Path(tmp) / 'tribunal-mournhold'
            world.mkdir()
            table = regions.ownership({(-12, -30): 'land', (-12, -29): 'land', (0, -30): 'land'}, {'values': ['x']})
            (world / regions.TABLE_FILE).write_text(regions.dumps(table), encoding='utf-8')
            holders = layer_stores.frame_holders(['chimmh=' + str(world)])
            names = {cell: name for cell, (name, _origin) in holders.items()}
            order = [tuple(f['cell']) for f in table['frames']]
            self.assertEqual(names, {cell: 'mh%04d' % i for i, cell in enumerate(order)})
            self.assertEqual(holders[order[0]][1], list(table['frames'][0]['origin']))
            # a rooms store holds no frames; no store, no holders
            self.assertEqual(layer_stores.frame_holders(['chimiti=' + str(world)]), {})
            self.assertEqual(layer_stores.frame_holders(None), {})

    def test_the_districts_frame_maps_and_rows_are_their_own(self):
        import struct
        land = sol_test.LANDS['chimmh']
        self.assertEqual((land['prefix'], land['limit'], land['directory'], land['title']),
                         ('mh', 256, 'world/regions-mh.awr', 'Mournhold'))
        self.assertEqual(land['data_stage'], build.TRIBUNAL_MOURNHOLD_DATA_STAGE)
        self.assertEqual(sol_test.map_name(3, 'mh', 256), 'mh0003')
        with self.assertRaises(ValueError):
            sol_test.map_name(256, 'mh', 256)
        frame = {'id': 'rcm12_m30', 'cell': [-12, -30], 'origin': [-23552.0, -60416.0, 0.0],
                 'core': [[-1024, -1024], [1024, 1024]]}
        raw = sol_test.directory_rows([frame, dict(frame, cell=[-12, -29])], 'mh', 256)
        self.assertEqual((raw[:4], struct.unpack_from('<I', raw, 4)[0], len(raw)), (b'AWS1', 2, 8 + 2 * 52))
        self.assertEqual((raw[8:16], raw[60:68]), (b'mh0000\0\0', b'mh0001\0\0'))
        # Solstheim's rows are as before
        self.assertEqual(sol_test.directory_rows([frame])[8:16], b'sl0000\0\0')
        # the engine's ID ranges (aw_maps.h): Solstheim 3840 maps, Mournhold the block's last 256
        self.assertEqual(sol_test.LANDS['chimsol']['limit'] + land['limit'], 4096)

    def test_the_cells_of_one_district_are_open_to_each_other_and_a_lone_cell_is_closed(self):
        frames = [{'cell': c} for c in ([-12, -30], [-12, -29], [-8, -30], [-7, -30], [0, -30])]
        self.assertEqual(sol_test.closed_frames(frames, 'alone'), {(0, -30)})
        self.assertEqual(len(sol_test.closed_frames(frames, 'closed')), 5)

    def test_the_layout_plan_moves_the_store_as_one_folder(self):
        import layout_plan
        self.assertEqual(layout_plan.movable_unit('id1/chimmh/world.cwi'), 'id1/chimmh/')

    def test_the_door_audit_knows_the_districts_map_ids(self):
        import door_audit
        self.assertEqual([door_audit.terrain_id(n) for n in ('vf0000', 'vf4095', 'sl0000', 'sl3839', 'mh0000', 'mh0255')],
                         [0, 4095, 4096, 7935, 7936, 8191])
        self.assertEqual([door_audit.terrain_id(n) for n in ('vf4096', 'sl3840', 'mh0256', 'xx0000')], [-1] * 4)


class TheImagesLastTablesKnowTheDistrictsMaps(unittest.TestCase):
    """DOOR-CHECK-MODULE-FRAME-MAPS-67: an image stopped in its last step, 1 h 34 min into a build, when the door
    check's job table met the first frame map of Mournhold's districts (KeyError: 'mh0001'): the table knew only the
    open-world directory's frames. The table now lists such a door with its reason, and a first-minute check runs
    the image's own table code on the module's frame map names."""

    def door_rows(self, names):
        return [{'reference': i + 1, 'holder': name, 'holder_kind': 'region',
                 'bank': {'box': [[0.0, 0.0, 0.0], [8.0, 8.0, 64.0]], 'target': '-', 'arrival': [0.0, 0.0, 0.0]}}
                for i, name in enumerate(names)]

    def test_the_door_check_lists_a_door_in_a_world_of_its_own_and_does_not_walk_it(self):
        import door_engine_check
        directory = [('vf0000', [0.0, 0.0, 0.0], [-1024.0, -1024.0, 1024.0, 1024.0]),
                     ('vf0001', [2048.0, 0.0, 0.0], [-1024.0, -1024.0, 1024.0, 1024.0])]
        planned = door_engine_check.job_lines(self.door_rows(['mh0001', 'vf0000']), lambda name: None, directory)
        (district, line, why), (island, island_line, island_why) = planned
        self.assertIsNone(line)
        self.assertIn('mh0001', why)
        self.assertIn('a world of its own', why)
        # a door of the island is walked as before, from its neighbouring frame
        self.assertIsNone(island_why)
        self.assertIn(' W vf0001 ', island_line)
        self.assertEqual(door_engine_check.neighbour_walks(directory, 'mh0001', [0.0, 0.0, 0.0]), [])

    def test_the_first_minute_check_runs_the_images_own_tables_on_the_modules_maps(self):
        names = expansion_preflight.module_map_names(CELLS, 'chimmh')
        self.assertEqual(names, ['mh0000', 'mh0001', 'mh0002'])
        self.assertEqual(expansion_preflight.finalize_table_problems(names, 'chimmh'), [])
        # the fault as the build met it: the job table raising on a module map is a problem that names it
        import door_engine_check

        def stops(rows, bank, directory):
            raise KeyError(rows[1]['holder'])
        with mock.patch.object(door_engine_check, 'job_lines', side_effect=stops):
            problems = expansion_preflight.finalize_table_problems(names, 'chimmh')
        self.assertEqual(len(problems), 1)
        self.assertIn('job_lines', problems[0])
        self.assertIn("KeyError: 'mh0001'", problems[0])
        # a name the engine does not know as a map, and a store the disk layout does not know
        self.assertTrue(any('engine does not know' in p and 'zz0000' in p
                            for p in expansion_preflight.finalize_table_problems(['zz0000'], 'chimmh')))
        self.assertTrue(any('disk layout' in p for p in expansion_preflight.finalize_table_problems(names, 'chimxx')))

    def test_the_check_is_registered_and_idle_without_a_module(self):
        entry = [e for e in build_preflight.EARLY_CHECKS if e[0] == 'module-frame-maps']
        self.assertEqual(entry, [('module-frame-maps', 'inputs', 'expansion_preflight:module_frame_maps')])
        said = []
        context = build_preflight.EarlyContext('inputs', SimpleNamespace(tribunal_mournhold_cells=None,
                                                                         data_files=None), log=said.append)
        self.assertEqual(expansion_preflight.module_frame_maps(context), [])
        self.assertEqual(said, [])
        context = build_preflight.EarlyContext('inputs', SimpleNamespace(tribunal_mournhold_cells=CELLS,
                                                                         data_files=None), log=said.append)
        self.assertEqual(expansion_preflight.module_frame_maps(context), [])
        self.assertIn('mh0000 .. mh0002', said[0])


class TheModulesMapsAreTriedRightAfterItsStage(unittest.TestCase):
    """The image's last per-map checks on a module's real frame maps, right after its world stage (the probes were
    run on a build's districts before the check was registered: eight passes in about five seconds)."""

    def test_the_check_is_registered_after_the_modules_world_stage(self):
        entry = [e for e in build_preflight.EARLY_CHECKS if e[0] == 'module-store-maps']
        self.assertEqual(entry, [('module-store-maps', 'after:tribunal-mournhold',
                                  'expansion_preflight:module_store_after')])
        self.assertEqual(expansion_preflight.MODULE_WORLD_STAGES, {'tribunal-mournhold': 'chimmh'})
        self.assertEqual(set(expansion_preflight.MODULE_WORLD_STAGES), set(layer_stores.MODULE_STAGES))

    def test_without_the_stages_output_there_is_nothing_to_check(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            context = build_preflight.EarlyContext('after:tribunal-mournhold', run=tmp, steps=['tribunal-mournhold'],
                                                   log=lambda line: None)
            self.assertEqual(expansion_preflight.module_store_after(context), [])

    def test_a_store_the_image_cannot_install_is_one_problem_that_names_it(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            world = Path(tmp) / 'tribunal-mournhold'
            (world / 'chim').mkdir(parents=True)
            (world / 'chim' / 'world.cwi').write_bytes(b'not a world')
            problems = expansion_preflight.store_map_problems(world, 'chimmh', Path(tmp) / 'scratch',
                                                              log=lambda line: None)
            self.assertEqual(len(problems), 1)
            self.assertIn('install of the store chimmh', problems[0])


class TheOption(unittest.TestCase):
    def test_unset_by_default(self):
        import inspect
        text = inspect.getsource(build_parser)
        self.assertIn('"--presented-exteriors"', text)
        at = text.index('"--presented-exteriors"')
        self.assertIn('default=None', text[at:at + 200])


class TheDistrictsPeople(unittest.TestCase):
    """DISTRICT-PEOPLE-NOT-PLACED-67: the people of Mournhold's districts were in no frame map. In the game data a
    district is an interior cell, so the open world's actor census (exterior cells of the merged master) never held
    them; the districts' frame maps were written with a worldspawn, a start and flames only. The image step now
    gives a store of frames the same actor inputs the open world's frames get, read from the store's OWN presented
    master, where the district's cells are exterior cells."""

    def master(self):
        sys.path.insert(0, str(ROOT / 'tests'))
        from test_entity_tracker import base, cell
        from test_chim_actor_table import ref
        from test_chim_levelled import crea
        return (base('NPC_', 'merchant') + crea('fabricant', 'r\\fab.nif', 'Fabricant')
                + cell('', False, -8, -30, ref(4202100, 'merchant', (-8 * 8192.0 + 50.0, -30 * 8192.0 + 60.0, 300.0))
                       + ref(4202101, 'fabricant', (-8 * 8192.0 + 90.0, -30 * 8192.0 + 60.0, 300.0)))
                + cell('', False, 0, 0, ref(11, 'merchant', (10.0, 10.0, 0.0))))

    def test_inputs_come_from_the_stores_own_presented_master(self):
        import tempfile
        import build_aga
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            (run / 'tribunal-mournhold-data').mkdir()
            (run / 'tribunal-mournhold-data' / 'Morrowind.esm').write_bytes(self.master())
            (run / 'actor-library').mkdir()
            args = SimpleNamespace(chim_region_actors='on', chim_world=str(run / 'chim-world'),
                                   actor_library=str(run / 'actor-library'), data_files=None)
            with mock.patch.dict(os.environ, {'AMIWIND_START_DISABLED': 'placed'}):
                make = build_aga.layer_actor_inputs(args, 16)
                got = make('chimmh', run / 'tribunal-mournhold')
            self.assertEqual(sorted(got['refs']), [(-8, -30), (0, 0)])
            self.assertEqual([r['number'] for r in got['refs'][(-8, -30)]], [4202100, 4202101])
            self.assertEqual(got['town_refs'], set())
            self.assertEqual(got['heap_mb'], 16)
            self.assertEqual(got['library_id1'], run / 'actor-library' / 'id1')
            # a store whose data stage wrote no master, and a store that is no land: nothing changes for them
            self.assertIsNone(make('chimmh', run / 'elsewhere' / 'tribunal-mournhold'))
            self.assertIsNone(make('chimxx', run / 'tribunal-mournhold'))

    def test_without_region_actors_or_the_library_nothing_is_asked(self):
        import build_aga
        off = SimpleNamespace(chim_region_actors='off', chim_world='/run/chim-world', actor_library='/run/actor-library')
        self.assertIsNone(build_aga.layer_actor_inputs(off, 16))
        bare = SimpleNamespace(chim_region_actors='on', chim_world='/run/chim-world', actor_library=None)
        self.assertIsNone(build_aga.layer_actor_inputs(bare, 16))

    def test_a_store_of_frames_is_installed_with_its_actor_inputs(self):
        seen = []

        def install_frames(world, id1, hand_fields, store=None, actors=None):
            seen.append((str(world), store, actors))
            return {'store': store, 'maps': []}
        with mock.patch.object(sol_test, 'install', install_frames):
            layer_stores.install(['chimmh=/run/tribunal-mournhold'], '/id1', {},
                                 actors=lambda store, world: {'store': store, 'world': str(world)})
            layer_stores.install(['chimmh=/run/tribunal-mournhold'], '/id1', {})
        self.assertEqual(seen[0][1], 'chimmh')
        self.assertEqual(seen[0][2]['store'], 'chimmh')
        self.assertTrue(seen[0][2]['world'].replace('\\', '/').endswith('/run/tribunal-mournhold'))
        self.assertIsNone(seen[1][2])

    def test_the_frame_maps_take_the_plan_of_the_open_worlds_frames(self):
        import inspect
        text = inspect.getsource(sol_test.install)
        self.assertIn('FM.region_actor_tasks([task], world, actors)', text)
        self.assertIn('FM.region_actor_map(planned, data, report)', text)
        import build_aga
        self.assertIn('actors=layer_actor_inputs(args, engine_record.get(\'heap_mb\'))',
                      inspect.getsource(build_aga))


if __name__ == '__main__':
    unittest.main()
