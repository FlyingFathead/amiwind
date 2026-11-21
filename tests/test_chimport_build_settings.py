# SPDX-License-Identifier: GPL-3.0-only
"""tools/chimport.py converts a cell as a default build does (CHIMPORT-UNITS-NOT-SHARED-WITH-BUILD-68,
CHIMPORT-HEAP-NOT-BUILD-FRAMES-68): the frame settings a default build's CHIM stage hands chim.build.build_areas and
the converter switches a default build exports, so every unit a cell makes carries the key a build asks for
(chim.units.tool_fingerprint hashes the raw switch values) and its memory figures are measured on frames stored as a
build stores them. The earlier settings stay selectable (--frame-settings cell-v1)."""
import argparse
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src'):          # src ends up first: the package src/mwad, not tools/mwad.py
    while str(p) in sys.path:
        sys.path.remove(str(p))
    sys.path.insert(0, str(p))

import chimport as C  # noqa: E402
from chim import units  # noqa: E402

KINDS = ('mesh', 'mesh-stair', 'stair-flights', 'hull-surface', 'variant', 'texture', 'texture-fence', 'tiles',
         'tiles-budget')
COPY = 'tools/chimport.py FRAME_SETTING_SETS["build"]'
SOURCE = 'tools/build.py chim_stage_options (the defaults of tools/build_parser.py)'


def unset_switches():
    for name in units.SWITCHES:
        os.environ.pop(name, None)


def build_switches():
    """The switch values a default build exports (tools/build.py plan_stage_environment: the build's own parse,
    resolve and export of a command line with no options)."""
    import build as B
    unset_switches()
    B.plan_stage_environment([])
    return {name: os.environ.get(name, '') for name in units.SWITCHES}


def build_chim_settings():
    """{chim.build settings key: value} of the options a default build's CHIM stage passes to tools/chim_build.py
    (tools/build.py chim_stage_options), by chim_build's own naming (--terrain-refs -> terrain_refs)."""
    import build as B
    options = [str(part) for part in B.chim_stage_options(B.parser().parse_args([]))]
    pairs = dict(zip(options[0::2], options[1::2]))
    pairs.pop('--chim-regions-cells', None)
    return {flag[2:].replace('-', '_'): value for flag, value in pairs.items()}


class BuildSwitches(unittest.TestCase):
    def test_the_switches_are_the_ones_a_default_build_exports(self):
        with mock.patch.dict(os.environ):
            unset_switches()
            mine = C.export_build_switches()
            build = build_switches()
        self.assertEqual(mine['switches'], build,
                         'tools/chimport.py export_build_switches no longer exports what tools/build.py '
                         'export_converter_environment does: call the same exporters there')
        self.assertEqual(mine['explicit'], [])
        # the three values that made every unit key differ (a CHIMport run through aw had none of them set)
        self.assertEqual((build['AMIWIND_STAIR_MITIGATION'], build['AMIWIND_MODEL_HULL'], build['AMIWIND_LAVA']),
                         ('on', 'auto', 'quake'))

    def test_every_unit_kind_gets_the_key_a_build_asks_for(self):
        with mock.patch.dict(os.environ):
            unset_switches()
            before = {kind: units.tool_fingerprint(kind) for kind in KINDS}
            C.export_build_switches()
            mine = {kind: units.tool_fingerprint(kind) for kind in KINDS}
            build_switches()
            build = {kind: units.tool_fingerprint(kind) for kind in KINDS}
        self.assertEqual(mine, build)
        # the key itself is not normalised: unset and the default value stay two keys (the island's stored units
        # keep theirs; nothing in chim.units changed)
        self.assertTrue(all(before[kind] != build[kind] for kind in KINDS))

    def test_a_value_the_caller_set_stays_and_is_named(self):
        with mock.patch.dict(os.environ):
            unset_switches()
            os.environ['AMIWIND_MODEL_HULL'] = 'chain'
            got = C.export_build_switches()
            self.assertEqual(os.environ['AMIWIND_MODEL_HULL'], 'chain')
        self.assertEqual(got['explicit'], ['AMIWIND_MODEL_HULL'])
        self.assertEqual(got['switches']['AMIWIND_MODEL_HULL'], 'chain')
        self.assertEqual(got['switches']['AMIWIND_STAIR_MITIGATION'], 'on')

    def test_the_command_line_leaves_the_environment_as_it_found_it(self):
        with mock.patch.dict(os.environ):
            unset_switches()
            seen = {}

            def cli(argv):
                C.export_build_switches()
                seen.update(C.switch_values())
                return 0
            with mock.patch.object(C, '_cli', cli):
                self.assertEqual(C.main(['cell']), 0)
            self.assertEqual(seen['AMIWIND_MODEL_HULL'], 'auto')            # exported while the command ran
            self.assertEqual({n: os.environ.get(n) for n in units.SWITCHES}, {n: None for n in units.SWITCHES})


class FrameSettings(unittest.TestCase):
    def test_the_build_set_is_the_settings_of_a_default_build(self):
        mine = {k: v for k, v in C.FRAME_SETTING_SETS['build'].items() if k not in ('grain', 'sector_chunks')}
        self.assertEqual(mine, build_chim_settings(),
                         'the frame settings of a default build changed: %s must equal what %s passes, so a CHIMport '
                         'cell is stored and measured as a build stores it (CHIMPORT-HEAP-NOT-BUILD-FRAMES-68)'
                         % (COPY, SOURCE))
        self.assertIs(C.FRAME_SETTINGS, C.FRAME_SETTING_SETS[C.FRAME_SETTINGS_DEFAULT])
        self.assertEqual(C.FRAME_SETTINGS_DEFAULT, 'build')

    def test_the_names_are_the_keys_chim_build_hands_on(self):
        # the copy's keys are the settings keys tools/chim_build.py builds from its options, and the grain is its
        # default (a default build passes no --grain)
        text = (ROOT / 'tools/chim_build.py').read_text(encoding='utf-8')
        for key in build_chim_settings():
            self.assertIn("**({'%s': a.%s}" % (key, key), text,
                          'tools/chim_build.py no longer maps --%s to the setting %s: %s needs the new name'
                          % (key.replace('_', '-'), key, COPY))
        self.assertIn("ap.add_argument('--grain', type=int, default=256", text)
        self.assertEqual(C.FRAME_SETTINGS['grain'], 256)

    def test_the_settings_before_stay_selectable(self):
        self.assertEqual(C.frame_settings('cell-v1', 'qbsp'), {'grain': 256, 'sector_chunks': 4})
        self.assertEqual(C.frame_settings(None, 'qbsp'), C.FRAME_SETTINGS)
        self.assertEqual(C.frame_settings('build', 'qbsp')['terrain_pack'], 'generate')

    def test_without_qbsp_the_terrain_hull_is_auto(self):
        self.assertNotIn('terrain_hull', C.frame_settings('build', None))
        self.assertEqual(C.frame_settings('build', '/opt/qbsp')['terrain_hull'], 'compiled')
        self.assertEqual(C.FRAME_SETTING_SETS['build']['terrain_hull'], 'compiled')      # the table is unchanged

    def test_a_named_set_reaches_the_cell_and_world_processes_and_the_default_adds_nothing(self):
        a = SimpleNamespace(data_files=Path('/d'), palette=Path('/p'), out=Path('/r'), jobs=1, qbsp=None,
                            frame_settings='build')
        self.assertNotIn('--frame-settings', C.cell_command(a, {'x': 1, 'y': 2}))
        self.assertNotIn('--frame-settings', C.world_command(a, 3))
        a.frame_settings = 'cell-v1'
        cmd = C.cell_command(a, {'x': 1, 'y': 2})
        self.assertEqual(cmd[cmd.index('--frame-settings') + 1], 'cell-v1')
        cmd = C.world_command(a, 3)
        self.assertEqual(cmd[cmd.index('--frame-settings') + 1], 'cell-v1')

    def test_the_result_records_what_the_cell_converted_with(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ):
            unset_switches()
            palette = Path(d) / 'palette.lmp'
            palette.write_bytes(bytes(768))
            C.export_build_switches()
            got = C.settings_record(C.frame_settings('build', 'q'), palette)
        import hashlib
        self.assertEqual(got['frame_settings'], 'build')
        self.assertEqual(got['frame'], C.FRAME_SETTINGS)
        self.assertEqual(got['palette_sha256'], hashlib.sha256(bytes(768)).hexdigest())
        self.assertEqual(got['switches']['AMIWIND_LAVA'], 'quake')
        self.assertIsNone(C.settings_record({}, Path(d) / 'missing.lmp')['palette_sha256'])

    def test_the_cell_key_follows_the_frame_settings(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ):
            data = Path(d) / 'data'
            data.mkdir()
            palette = Path(d) / 'palette.lmp'
            palette.write_bytes(bytes(768))
            lock = Path(d) / 'inputs.lock'
            lock.write_text('{"files": {"%s": {"sha256": "%s", "bytes": 1, "mtime_ns": 1}}}'
                            % ((data / 'Morrowind.esm').as_posix(), 'a' * 64))
            from known_inputs import LOCK_ENV
            os.environ[LOCK_ENV] = str(lock)
            with mock.patch.object(C, 'layer_touch', lambda cell, data_files: None):
                default = C.cell_key((3, -2), data, palette)[0]
                build = C.cell_key((3, -2), data, palette, frame=C.frame_settings('build'))[0]
                before = C.cell_key((3, -2), data, palette, frame=C.frame_settings('cell-v1'))[0]
        self.assertIsNotNone(default)
        self.assertEqual(default, build)
        self.assertNotEqual(default, before)


OWNED = (0, 0)


def region_work(root, placements, flat=(), unread=()):
    """A region-shape cell's source stage output on small synthetic inputs: the audit of the 3 x 3 square around
    OWNED (cells UNREAD left out of it, cells FLAT read as flat default ground) and its placements
    {(x, y): [record numbers]}."""
    work = Path(root) / 'work'
    cells = [{'x': OWNED[0] + dx, 'y': OWNED[1] + dy, 'references': len(placements.get((OWNED[0] + dx, OWNED[1] + dy),
                                                                                       ()))}
             for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (OWNED[0] + dx, OWNED[1] + dy) not in unread]
    C.write_json(work / 'audit' / 'audit.json', {
        'input': {'esm_sha256': 'e' * 64},
        'area': {'center': list(OWNED), 'radius_cells': 1, 'cells': cells,
                 'references': sum(len(v) for v in placements.values()),
                 'default_land_cells': [list(c) for c in flat]}})
    C.write_json(work / 'audit' / 'placements.json',
                 [{'cell': list(c), 'number': n, 'type': 'STAT', 'id': 'rock_%d' % n}
                  for c, numbers in sorted(placements.items()) for n in numbers])
    return work


def region_world():
    """A region frame's 15 x 15 chunks of 256 units over the owned cell (-1024..1024) and the 896-unit margin."""
    chunks = [{'cx': cx, 'cy': cy} for cy in range(15) for cx in range(15)]
    return {'frames': [('zf/frame', {'grain': 256, 'low': [-1920, -1920]}, chunks)]}


class CellShape(unittest.TestCase):
    """--cell-shape region (CHIMPORT-HEAP-NOT-BUILD-FRAMES-68): each cell built as the frame a build installs for it,
    made by the build's own function, its records counting the owned cell and its apron named apart."""

    def test_the_region_frame_is_the_one_a_build_makes_for_the_cell(self):
        from chim import regions as R
        for kind in ('land', 'seabed'):
            # the build's own route (tools/chim_build.py: ownership, then frame_settings with the table's margin)
            table = R.ownership({(-21, 24): kind})
            want = R.frame_settings(table['frames'][0], table['terrain_margin'])
            self.assertEqual(C.cell_settings((-21, 24), shape='region'), want)
        got = C.cell_settings((0, -30), shape='region')
        self.assertEqual((got['source_radius'], got['region_source_apron'], got['terrain_margin']), (1, True, 896))
        self.assertEqual(got['town']['map_prefix'], 'zf')
        # the cell shape stays the default and stays as it was
        self.assertEqual(C.CELL_SHAPE_DEFAULT, 'cell')
        self.assertEqual(C.cell_settings((0, -30)), C.cell_settings((0, -30), shape='cell'))
        self.assertEqual(C.cell_settings((0, -30))['source_radius'], 0)

    def test_a_region_frame_takes_the_world_sectors_as_a_build_does(self):
        from chim.world import DEFAULT_SETTINGS
        region = C.frame_settings('build', 'q', 'region')
        self.assertNotIn('sector_chunks', region)
        self.assertEqual({k: v for k, v in region.items()},
                         {k: v for k, v in C.FRAME_SETTINGS.items() if k != 'sector_chunks'})
        side = (2 * C.HALF + 2 * 896) // region['grain']
        self.assertEqual(side, 15)
        self.assertEqual(side % DEFAULT_SETTINGS['sector_chunks'], 0)
        self.assertEqual(C.frame_settings('build', 'q', 'cell'), C.FRAME_SETTINGS)

    def test_a_cell_without_land_is_flat_ground_in_the_region_shape(self):
        with self.assertRaises(ValueError):
            C.cell_settings((0, -30), None, 'region')            # --missing-land refuse
        import contextlib
        import io
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            C._cli(['cell', '--data-files', '/d', '--palette', '/p', '--cell=0,-30', '--out', '/o',
                    '--cell-shape', 'region', '--missing-land', 'refuse'])

    def test_the_region_frame_is_a_generated_area_while_it_converts(self):
        import town_config
        settings = C.cell_settings((0, -30), shape='region')
        ident = settings['town']['id']
        self.assertNotIn(ident, town_config.generated_areas())
        others = set(town_config.generated_areas())
        with C.generated_frames([settings, C.cell_settings((1, -30))]):
            self.assertIs(town_config.generated_areas()[ident], settings)
            # the cell shape's frame is not registered (it is no generated area)
            self.assertEqual(set(town_config.generated_areas()) - others, {ident})
        self.assertNotIn(ident, town_config.generated_areas())
        before = dict(settings, title='registered before')
        town_config._GENERATED[ident] = before
        try:
            with C.generated_frames([settings]):
                self.assertIs(town_config.generated_areas()[ident], settings)
            self.assertIs(town_config.generated_areas()[ident], before)      # put back
        finally:
            town_config._GENERATED.pop(ident, None)

    def test_the_records_and_the_source_facts_count_the_owned_cell(self):
        with tempfile.TemporaryDirectory() as d:
            work = region_work(d, {OWNED: [1, 2, 3], (1, 0): [10, 11], (-1, -1): [20]}, flat=[(-1, 1)])
            chim_refs = {1, 2, 10, 20}
            mine = C.record_accounting(work, None, chim_refs, OWNED)
            whole = C.record_accounting(work, None, chim_refs)
            facts = C.source_facts(work, OWNED)
            alone = C.source_facts(work)
        self.assertEqual((mine['totals']['placed'], mine['totals']['converted']), (3, 2))
        self.assertEqual((whole['totals']['placed'], whole['totals']['converted']), (6, 4))
        self.assertEqual((facts['references'], facts['apron_references'], facts['default_land']), (3, 3, False))
        self.assertEqual(facts['apron_default_land_cells'], ['-1,1'])
        self.assertEqual(alone['references'], 6)        # the cell shape's facts as before (the audit's own count)
        # the plan check reads the owned cell's numbers: a plan of 3 placements is met
        res = {'converted': True, 'records': mine, 'source': facts}
        self.assertEqual(C.plan_mismatch({'x': 0, 'y': 0, 'land': True, 'refs': 3}, res), [])
        self.assertTrue(C.plan_mismatch({'x': 0, 'y': 0, 'land': True, 'refs': 4}, res))

    def test_the_apron_is_named_by_neighbour(self):
        with tempfile.TemporaryDirectory() as d:
            work = region_work(d, {OWNED: [1], (1, 0): [10, 11], (-1, -1): [20]}, flat=[(-1, 1), (0, 1)])
            got = C.apron_figures(work, region_world(), OWNED, {1, 10, 20})
            unmeasured = C.apron_figures(work, None, OWNED, {1, 10, 20})
        # a chunk across the owned cell's edge is the owned cell's on every side: 9 x 9 owned, the 144 around it
        self.assertEqual((got['owned_chunks'], got['chunks']), (81, 144))
        self.assertEqual(sorted(got['cells']), sorted(C.ckey((dx, dy)) for dx, dy in C.NEIGHBOURS))
        self.assertEqual(got['cells']['1,0'], {'read': True, 'ground': 'land', 'placements_read': 2,
                                               'placements_in_frame': 1, 'chunks': 27})
        self.assertEqual(got['cells']['-1,-1']['chunks'], 9)
        self.assertEqual(got['cells']['0,1']['ground'], 'flat default')
        self.assertEqual((got['placements_read'], got['placements_in_frame']), (3, 2))
        self.assertEqual(got['flat_default_ground'], ['-1,1', '0,1'])
        self.assertEqual(got['problems'], [])
        self.assertIsNone(unmeasured['chunks'])
        self.assertIsNone(unmeasured['cells']['1,0']['chunks'])

    def test_a_neighbour_not_read_is_a_problem_of_the_cell(self):
        with tempfile.TemporaryDirectory() as d:
            work = region_work(d, {OWNED: [1]}, unread=[(1, 1)])
            got = C.apron_figures(work, region_world(), OWNED, {1})
        self.assertEqual(len(got['problems']), 1)
        self.assertIn('1,1', got['problems'][0])
        self.assertFalse(got['cells']['1,1']['read'])

    def test_the_shape_is_in_the_key_the_records_and_the_command_lines(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ):
            data = Path(d) / 'data'
            data.mkdir()
            palette = Path(d) / 'palette.lmp'
            palette.write_bytes(bytes(768))
            lock = Path(d) / 'inputs.lock'
            lock.write_text('{"files": {"%s": {"sha256": "%s", "bytes": 1, "mtime_ns": 1}}}'
                            % ((data / 'Morrowind.esm').as_posix(), 'a' * 64))
            from known_inputs import LOCK_ENV
            os.environ[LOCK_ENV] = str(lock)
            with mock.patch.object(C, 'layer_touch', lambda cell, data_files: None):
                default = C.cell_key((3, -2), data, palette)[0]
                cell = C.cell_key((3, -2), data, palette, shape='cell')[0]
                region = C.cell_key((3, -2), data, palette, shape='region')[0]
            record = C.settings_record(C.frame_settings('build', 'q', 'region'), palette, 'build', 'region')
        self.assertEqual(default, cell)
        self.assertNotEqual(default, region)
        self.assertEqual(record['cell_shape'], 'region')
        self.assertNotIn('sector_chunks', record['frame'])
        a = SimpleNamespace(data_files=Path('/d'), palette=Path('/p'), out=Path('/r'), jobs=1, qbsp=None,
                            frame_settings='build', cell_shape='cell')
        self.assertNotIn('--cell-shape', C.cell_command(a, {'x': 1, 'y': 2}))
        self.assertNotIn('--cell-shape', C.world_command(a, 3))
        a.cell_shape = 'region'
        for cmd in (C.cell_command(a, {'x': 1, 'y': 2}), C.world_command(a, 3)):
            self.assertEqual(cmd[cmd.index('--cell-shape') + 1], 'region')

    def test_the_shape_reaches_the_cell_conversion(self):
        seen = []
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(C, 'convert_cell', lambda *args, **named: seen.append(named) or {}):
            C.convert_cell_pooled((0, -30), Path('/d'), Path('/p'), Path(d), shape='region')
            C.convert_cell_pooled((0, -30), Path('/d'), Path('/p'), Path(d))
        self.assertEqual(seen, [{'shape': 'region'}, {}])

    def test_the_summary_and_the_tracker_name_the_apron_apart(self):
        apron = {'placements_read': 5, 'placements_in_frame': 4, 'chunks': 144, 'owned_chunks': 81}

        def result(with_apron):
            res = {'converted': True, 'errors': [], 'audits': {}, 'wall_s': 1.0, 'cpu_s': 1.0,
                   'records': {'totals': {'placed': 2, 'converted': 2, 'deferred': 0, 'failed': 0, 'skipped': 0},
                               'by_type': {}},
                   'stats': {'meshes': {'new': 0, 'reused': 0}, 'disk': {'chim_bytes': 10}}}
            return dict(res, apron=apron) if with_apron else res
        with tempfile.TemporaryDirectory() as d:
            run = Path(d)
            plan = {'cells': [{'x': 0, 'y': 0, 'ring': 0, 'order': 0}, {'x': 1, 'y': 0, 'ring': 0, 'order': 1}]}
            C.write_json(run / 'cells' / C.cell_dir((0, 0)) / 'result.json', result(True))
            C.write_json(run / 'cells' / C.cell_dir((1, 0)) / 'result.json', result(True))
            summary = C.summarise(run, plan)
            C.write_json(run / 'cells' / C.cell_dir((1, 0)) / 'result.json', result(False))
            C.write_json(run / 'cells' / C.cell_dir((0, 0)) / 'result.json', result(False))
            plain = C.summarise(run, plan)
        self.assertEqual(summary['total']['records_placed'], 4)                   # the owned cells' records
        self.assertEqual((summary['total']['apron_placements_in_frame'], summary['total']['apron_chunks']), (8, 288))
        self.assertNotIn('apron_chunks', plain['total'])                        # the cell shape's summary as before
        self.assertNotIn('apron_chunks', plain['rings'][0])
        tracked = C.tracker_cell(result(True), {})
        self.assertEqual(tracked['stats']['records']['refs_total'], 2)
        self.assertEqual(tracked['stats']['apron'], apron)
        self.assertNotIn('apron', C.tracker_cell(result(False), {})['stats'])


class WorldCells(unittest.TestCase):
    """CHIM-FRAME-EDGE-CLAMPS-OUTSIDE-TILES-68: a region frame converted alone stands for one frame of the build's
    world: the run's cells and the reference's finished cells are that world's frames."""

    def test_the_world_is_the_runs_cells_and_the_references_finished_ones(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            ref = Path(tmp, 'reference.json')
            ref.write_text(json.dumps({'cells': {
                '-26,25': {'status': 'audits_passed', 'island': 2}, '-27,25': {'status': 'empty_sea', 'island': 2},
                '-26,27': {'status': 'converted_failing', 'island': 2}, '-25,25': {'status': 'not_started', 'island': 2}}}))
            got = C.world_frame_cells([(-26, 26), (-26, 27)], ref)
            self.assertEqual(got['cells'], [[-27, 25], [-26, 25], [-26, 26], [-26, 27]])
            self.assertEqual(got['run_cells'], 2)
            self.assertTrue(got['reference_sha256'])
            self.assertEqual(C.world_frame_cells([(1, 1)], Path(tmp, 'missing.json'))['cells'], [[1, 1]])

    def test_a_region_runs_cell_processes_are_told_the_world(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            args = argparse.Namespace(data_files=out, palette=out / 'p.lmp', out=out, jobs=1, qbsp=None,
                                      cell_shape='region', frame_settings=None)
            row = {'x': -26, 'y': 26}
            self.assertNotIn('--world-cells', C.cell_command(args, row))
            (out / C.WORLD_CELLS_FILE).write_text('{"cells": []}')
            cmd = C.cell_command(args, row)
            self.assertEqual(cmd[cmd.index('--world-cells') + 1], str(out / C.WORLD_CELLS_FILE))
            args.cell_shape = 'cell'
            self.assertNotIn('--world-cells', C.cell_command(args, row))

    def test_the_world_reaches_the_build_and_the_result(self):
        seen = {}

        def build_areas(*args, **kw):
            seen.update(kw)
            raise RuntimeError('stop after the build call')
        with tempfile.TemporaryDirectory() as tmp, mock.patch('chim.build.build_areas', build_areas):
            res = C.convert_cell((-27, 25), Path(tmp), Path(tmp, 'p.lmp'), Path(tmp, 'out'), shape='region',
                                 world_cells=[(-27, 25), (-26, 26), (-20, 20)])
        self.assertEqual(seen['frame_cells'], [(-27, 25), (-26, 26), (-20, 20)])
        self.assertEqual(res['world_frames']['neighbours_with_a_frame'], [[-26, 26]])
        self.assertEqual(res['world_frames']['cells'], 3)


if __name__ == '__main__':
    unittest.main()
