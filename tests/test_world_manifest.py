# SPDX-License-Identifier: GPL-3.0-only
"""The world map manifest (docs/BUILD_MANIFEST.md, BUILD-LEGACY-TOWN-MAPS-SHIPPED-36): decided from the CHIM coverage
before the first stage; every legacy map of a CHIM cell the build still makes is named with the reason; the image
summary counts what was built and proves none ships. Synthetic data only."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import world_manifest as M  # noqa: E402


def table(cells):
    return {'frames': [{'id': 'r%d_%d' % c, 'cell': list(c)} for c in cells]}


class Plan(unittest.TestCase):
    def test_rows_and_reasons(self):
        statuses = {(-7, 2): {'legacy_maps': ['vf0225']}, (-6, 2): {'legacy_maps': ['vf0226']}}
        manifest = M.plan(['seyda', 'balmora'], ['seyda', 'balmora'], table([(-7, 2), (-6, 2)]), statuses,
                          region_rows='legacy')
        default = M.plan(['seyda', 'balmora'], ['seyda', 'balmora'], table([(-7, 2), (-6, 2)]), statuses)
        # v0.0.36-dev5: Seyda Neen CHIM-native too: a default build makes no legacy map of a CHIM cell at all
        self.assertEqual(default['summary']['legacy_maps_of_chim_cells_made'], 0)
        self.assertEqual(M.collisions(default, []), [])
        self.assertEqual(M.region_cells(default), [(-7, 2), (-6, 2)])
        rows = {row['map']: row for row in manifest['rows']}
        self.assertEqual(rows['balmora']['legacy'], [])                 # CHIM-native: no town chain
        self.assertEqual(rows['seyda']['legacy'], [])
        self.assertIsNone(rows['seyda']['kept_because'])
        self.assertEqual(rows['vf0225']['cells'], ['-7,2'])
        self.assertEqual(rows['vf0226']['kept_because'], M.KEPT_REGION_MAP)
        self.assertEqual(manifest['summary']['kinds'], {'chim-area': 2, 'chim-region-cell': 2})
        self.assertEqual(manifest['summary']['legacy_maps_of_chim_cells_made'], 2)
        self.assertEqual(M.legacy_region_maps(manifest), {'vf0225': '-7,2', 'vf0226': '-6,2'})

    def test_legacy_chain_of_a_chim_area_is_refused_without_a_retired_flag(self):
        # BUILD-LEGACY-TOWN-MAPS-SHIPPED-36: no "kept because" for a town chain any more; ANY legacy map of a CHIM
        # area is refused, unless a retired flag labels the build as an A/B regression test.
        bare = M.plan(['seyda', 'balmora'], ['balmora'])
        self.assertIsNone({r['map']: r for r in bare['rows']}['seyda']['kept_because'])
        refused = M.collisions(bare, [])
        self.assertEqual(len(refused), 1)
        self.assertIn('seyda', refused[0])
        self.assertIn('no recorded reason', refused[0])
        self.assertFalse(hasattr(M, 'KEPT_TOWN_CHAIN'))
        labelled = M.plan(['seyda', 'balmora'], ['balmora'], retired=[{'flag': '--legacy-area'}])
        row = {r['map']: r for r in labelled['rows']}['seyda']
        self.assertIn('--legacy-area', row['kept_because'])
        self.assertIn('A/B regression', row['kept_because'])
        self.assertEqual(M.collisions(labelled, []), [])

    def test_no_coverage_no_rows_and_stable_sha256(self):
        manifest = M.plan([], [], None, None)
        self.assertEqual(manifest['rows'], [])
        self.assertEqual(manifest['summary']['legacy_maps_of_chim_cells_made'], 0)
        self.assertEqual(M.sha256(manifest), M.sha256(json.loads(M.text(manifest))))

    def test_all_native_and_no_regions_makes_no_legacy_map(self):
        manifest = M.plan(['balmora', 'bcoast_x7y2'], ['balmora', 'bcoast_x7y2'])
        self.assertEqual(manifest['summary']['legacy_maps_of_chim_cells_made'], 0)
        self.assertEqual(manifest['summary']['kept_because'], {})


class Collisions(unittest.TestCase):
    """The preflight collision check (maintainer order 11 October 2026: never a CHIM map and a legacy map of the same cell):
    before any stage, every open-world stage must take exactly the manifest's CHIM region cells."""
    CELLS = '5,5:s 6,5:l'

    def manifest(self, rows='game-data'):
        statuses = {(5, 5): {'legacy_maps': ['vf0100']}, (6, 5): {'legacy_maps': ['vf0101']}}
        return M.plan(['balmora'], ['balmora'], table([(5, 5), (6, 5)]), statuses, region_rows=rows)

    def steps(self, scenery_cells=CELLS):
        def stage(cells):
            return ['python3', 'tool.py', '--jobs', '24'] + (['--chim-regions-cells', cells] if cells else [])
        return [('world-terrain', stage(self.CELLS)), ('world-scenery', stage(scenery_cells)),
                ('world-flora', stage(self.CELLS)), ('image', ['python3', 'build_aga.py', 'image'])]

    def test_a_consistent_plan_passes(self):
        manifest = self.manifest()
        self.assertEqual(M.region_cells(manifest), [(5, 5), (6, 5)])
        self.assertEqual(manifest['summary']['legacy_maps_of_chim_cells_made'], 0)
        self.assertEqual(M.collisions(manifest, self.steps()), [])

    def test_a_mixed_plan_is_refused_with_the_cells(self):
        problems = M.collisions(self.manifest(), self.steps(scenery_cells='5,5:s'))
        self.assertEqual(problems, ['stage world-scenery would build the legacy maps of CHIM cells 6,5'])
        problems = M.collisions(self.manifest(), self.steps(scenery_cells=None))
        self.assertEqual(problems, ['stage world-scenery would build the legacy maps of CHIM cells 5,5 6,5'])
        problems = M.collisions(self.manifest(), self.steps(scenery_cells='5,5:s 6,5:l 7,5:l'))
        self.assertEqual(problems, ['stage world-scenery leaves out cells that are not CHIM region cells: 7,5'])

    def test_a_cell_claimed_twice_is_refused(self):
        manifest = self.manifest()
        manifest['rows'].append(dict(manifest['rows'][-1], map='vf0999'))
        self.assertIn('cell 6,5 is claimed by vf0101 and by vf0999', M.collisions(manifest, self.steps()))

    def test_the_legacy_method_keeps_the_maps_with_its_reason(self):
        manifest = self.manifest('legacy')
        self.assertEqual(M.region_cells(manifest), [])
        self.assertEqual(manifest['summary']['kept_because'], {M.KEPT_REGION_MAP: 2})
        self.assertEqual(M.collisions(manifest, self.steps(scenery_cells=None)), [])
        manifest['rows'][-1]['kept_because'] = None
        self.assertEqual(M.collisions(manifest, self.steps(scenery_cells=None)),
                         ['vf0101: legacy maps vf0101 of a CHIM cell are made with no recorded reason'])

    def test_the_builder_gives_the_cells_to_every_open_world_stage(self):
        import inspect
        from types import SimpleNamespace
        import build
        args = SimpleNamespace(chim_regions_cells=self.CELLS, chim_region_rows=None)
        self.assertEqual(build.chim_region_skip(args), ['--chim-regions-cells', self.CELLS])
        self.assertEqual(build.chim_region_skip(SimpleNamespace(chim_regions_cells=self.CELLS,
                                                                chim_region_rows='legacy')), [])
        self.assertEqual(build.chim_region_skip(SimpleNamespace(chim_regions_cells=None, chim_region_rows=None)), [])
        source = inspect.getsource(build)
        for tool in ('prepare_world_regions.py', 'prepare_world_scenery.py', 'prepare_world_flora.py'):
            block = source[source.index(tool):]
            self.assertIn('*chim_region_skip(args)', block[:700], tool)
        self.assertIn('world_manifest.collisions(manifest, steps)', source)


class OpenWorldStages(unittest.TestCase):
    """The open-world stages make no legacy map of a CHIM region cell (docs/BUILD_MANIFEST.md step 2)."""

    def test_terrain_selects_exactly_the_region_cells(self):
        from prepare_world_regions import chim_region
        cells = {(5, 5)}
        self.assertTrue(chim_region({'cell': [5, 5], 'divisions': 1}, cells))
        # every map of a divided cell: the cell's one CHIM frame owns it all (CHIM-REGION-DIVIDED-CELLS-36)
        self.assertTrue(chim_region({'cell': [5, 5], 'divisions': 2}, cells))
        self.assertFalse(chim_region({'cell': [6, 5], 'divisions': 1}, cells))
        self.assertFalse(chim_region({'cell': [5, 5], 'divisions': 1}, set()))

    def stage_scenery(self, root, references):
        terrain, scenery = root / 'terrain', root / 'scenery'
        terrain.mkdir()
        scenery.mkdir()
        (terrain / 'world-regions.json').write_text(json.dumps({'master_sha256': 'm', 'regions': [
            {'name': 'vf0000', 'cell': [5, 5], 'divisions': 1, 'chim_region': True, 'converted': None}]}))
        (scenery / 'scenery-index.json').write_text(json.dumps({'errors': [], 'master_sha256': 'm',
                                                                'references': references, 'models': []}))
        (root / 'palette.lmp').write_bytes(bytes(768))
        return terrain, scenery

    def test_scenery_makes_no_map_for_a_region_cell(self):
        import prepare_world_scenery as S
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            terrain, scenery = self.stage_scenery(root, [{'cell': [5, 5], 'number': 7, 'kind': 'rock'}])
            receipt = S.prepare(terrain, scenery, root / 'palette.lmp', root / 'out', 1)
            self.assertEqual(receipt['regions'], [{'name': 'vf0000', 'chim_region': True, 'instances': 0,
                                                   'source_references': []}])
            self.assertEqual(receipt['chim_region_cells'], [[5, 5]])
            self.assertFalse((root / 'out' / 'vf0000').exists())
            S.check_chim_cells('5,5:s', terrain)
            with self.assertRaisesRegex(ValueError, 'differ from the terrain stage'):
                S.check_chim_cells(None, terrain)

    def test_a_placement_outside_the_region_cells_must_still_be_covered(self):
        import prepare_world_scenery as S
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            terrain, scenery = self.stage_scenery(root, [{'cell': [9, 9], 'number': 7, 'kind': 'rock'}])
            with self.assertRaisesRegex(ValueError, 'omitted source references'):
                S.prepare(terrain, scenery, root / 'palette.lmp', root / 'out', 1)

    def test_the_image_refuses_a_legacy_map_of_a_region_cell(self):
        import install_world_terrain as T
        import inspect
        source = inspect.getsource(T.install)
        self.assertIn("A legacy map of a CHIM region cell is staged", source)


class ImageSummary(unittest.TestCase):
    def test_built_shipped_and_payload_by_kind(self):
        import build_aga
        from chim import frame_map as FM
        from chim import format as F
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp) / 'id1'
            (id1 / 'maps').mkdir(parents=True)
            lumps = FM.empty_world((-64, -64, -64), (64, 64, 64))
            lumps[0] = FM.entity_text([{'classname': 'worldspawn', FM.FRAME_KEY: '-7 2'}])
            (id1 / 'maps/vf0225.chim').write_bytes(F.brush_image(lumps)[0])
            (id1 / 'maps/vf0225.far').write_bytes(b'far')
            (id1 / 'maps/bmtemple.bsp').write_bytes(b'interior')
            removed = [{'file': 'maps/vf0225.bsp', 'bytes': 4000}, {'file': 'maps/sn001.bsp', 'bytes': 3000},
                       {'file': 'harvest-vf0225.txt', 'bytes': 10}]
            summary = build_aga.legacy_maps_summary(id1, removed)
            self.assertEqual((summary['built'], summary['shipped'], summary['removed_bytes']), (2, [], 7000))
            self.assertEqual(summary['line'], 'legacy maps of CHIM cells: 2 built / 0 shipped (7000 bytes kept out '
                                              'of the image)')
            self.assertEqual(set(summary['payload_by_kind']), {'CHIM frame maps', 'far terrain',
                                                               'interiors and other maps'})
            (id1 / 'maps/sn001.bsp').write_bytes(b'legacy')            # a legacy map left in the payload
            self.assertEqual(build_aga.legacy_maps_summary(id1, removed)['shipped'], ['maps/sn001.bsp'])


if __name__ == '__main__':
    unittest.main()


class RunFolder(unittest.TestCase):
    def test_the_manifest_is_written_when_the_run_folder_is_made(self):
        # BUILD-RUN-FOLDER-PRECREATED-36: the plan wrote world-manifest.json into the run folder before the run made
        # it, and every real CHIM build was refused ('File exists'); the plan hands the file to create_run instead
        from build_parallel import create_run
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / 'run'
            metadata = {'_run_files': {'world-manifest.json': '{}\n'}, 'kept': 1}
            create_run(run, metadata)
            self.assertEqual((run / 'world-manifest.json').read_text(encoding='utf-8'), '{}\n')
            self.assertTrue((run / 'logs').is_dir())
            self.assertEqual(metadata, {'kept': 1})                    # never in a receipt
            with self.assertRaises(FileExistsError):
                create_run(run, {})
        source = (ROOT / 'tools/build.py').read_text(encoding='utf-8')
        self.assertNotIn('run.mkdir(', source)                          # only create_run makes a run folder


class ExteriorChecklist(unittest.TestCase):
    def test_scenery_and_flora_verify_serialized_chim_cell_selection(self):
        import exterior_plan as E
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plan = E.make([(0, 0), (1, 0)], [(1, 0)], [], 'master')
            path = root / 'exterior-plan.json'
            path.write_text(json.dumps(plan))
            rows = [dict(name='vf%04d' % i, cell=[i, 0], origin=[i*2048+1024, 1024, 0],
                         core=[[-1024]*2, [1024]*2], chim_region=bool(i)) for i in range(2)]
            receipt = root / 'world-regions.json'
            receipt.write_text(json.dumps({'regions': rows, 'master_sha256': 'master'}))
            # Exercise the disk round trip used by both real stage entry points.
            # JSON cells are lists, unlike the tuple set used by terrain conversion.
            E.verify_stage(path, root)
            rows[1]['chim_region'] = False
            receipt.write_text(json.dumps({'regions': rows, 'master_sha256': 'master'}))
            with self.assertRaisesRegex(ValueError, 'ownership changed'):
                E.verify_stage(path, root)
            with self.assertRaisesRegex(ValueError, 'selection differs'):
                E.classify_regions(plan, rows, 'master', [[0, 0]])

    def test_source_inventory_excludes_interiors_and_checks_duplicate_land(self):
        import struct
        import exterior_plan as E
        def record(tag, data):
            return struct.pack('<4sIII', tag, len(data), 0, 0) + data
        def land(x, y):
            return record(b'LAND', struct.pack('<4sIii', b'INTV', 8, x, y) + struct.pack('<4sI', b'VHGT', 0))
        with tempfile.TemporaryDirectory() as td:
            master = Path(td) / 'synthetic.esm'
            interior = record(b'CELL', struct.pack('<4sIIii', b'DATA', 12, 1, 99, 99))
            sea = record(b'CELL', struct.pack('<4sIIii', b'DATA', 12, 0, 2, 0))
            master.write_bytes(land(0, 0) + interior + land(1, 0) + sea)
            cells, digest = E.source_cells(master)
            self.assertEqual(cells, [(0, 0), (1, 0), (2, 0)])
            self.assertEqual(len(digest), 64)
            master.write_bytes(land(0, 0) * 2)
            with self.assertRaisesRegex(ValueError, 'Duplicate LAND'):
                E.source_cells(master)

    def test_all_cells_one_owner_and_partial_town_keeps_only_required_bsp_maps(self):
        import exterior_plan as E
        towns = [{'owner': 'test-town', 'core': [0, 0, 3072, 2048]}]
        plan = E.make([(0, 0), (1, 0), (2, 0)], [(2, 0)], towns, 'master')
        self.assertEqual(plan['summary'], {'bsp': 1, 'chim-region': 1, 'chim-town': 1})
        self.assertEqual(plan['cells'][1]['bsp_core'], [[3072, 0, 4096, 2048]])
        entries = [dict(name='vf0000', cell=[0, 0], origin=[1024, 1024, 0], core=[[-1024]*2, [1024]*2]),
                   dict(name='vf0001', cell=[1, 0], origin=[2560, 512, 0], core=[[-512]*2, [512]*2]),
                   dict(name='vf0002', cell=[1, 0], origin=[3584, 512, 0], core=[[-512]*2, [512]*2]),
                   dict(name='vf0003', cell=[2, 0], origin=[5120, 1024, 0], core=[[-1024]*2, [1024]*2])]
        kinds = E.classify_regions(plan, entries, 'master', {(2, 0)})
        self.assertEqual(kinds, {'vf0000': 'routing-only', 'vf0001': 'routing-only',
                                 'vf0002': 'bsp', 'vf0003': 'chim-region'})
        for cells, selected in [([(0, 0)], [(9, 9)]), ([(0, 0)], [(0, 0), (0, 0)])]:
            with self.assertRaises(ValueError):
                E.make(cells, selected)
        with self.assertRaisesRegex(ValueError, 'same exterior cell'):
            E.make([(0, 0)], [(0, 0)], towns)
        with self.assertRaisesRegex(ValueError, 'master differs'):
            E.classify_regions(plan, entries, 'changed', {(2, 0)})
        with self.assertRaisesRegex(ValueError, 'survey cells differ'):
            E.classify_regions(plan, entries[:-1], 'master', {(2, 0)})

    def test_town_owned_region_never_calls_scenery_converter_and_interior_survives(self):
        from unittest.mock import patch
        import exterior_plan as E
        import prepare_world_scenery as S
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            terrain, scenery = root / 'terrain', root / 'scenery'
            terrain.mkdir(); scenery.mkdir()
            interior = root / 'temple.bsp'
            interior.write_bytes(b'interior-control')
            plan = E.make([(0, 0)], [], [{'owner': 'town', 'core': [0, 0, 2048, 2048]}], 'm')
            (terrain / 'world-regions.json').write_text(json.dumps({'master_sha256': 'm',
                'exterior_checklist': plan, 'regions': [{'name': 'vf0000', 'cell': [0, 0],
                'origin': [1024, 1024, 0], 'core': [[-1024]*2, [1024]*2], 'routing_only': True}]}))
            refs = [{'cell': [0, 0], 'number': 7, 'position': [4096, 4096, 0]}]
            (scenery / 'scenery-index.json').write_text(json.dumps({'errors': [], 'master_sha256': 'm', 'references': refs}))
            (root / 'palette.lmp').write_bytes(bytes(768))
            with patch.object(S, 'convert_region_cached', side_effect=AssertionError('BSP converter called')):
                result = S.prepare(terrain, scenery, root / 'palette.lmp', root / 'out', 1)
            self.assertTrue(result['regions'][0]['routing_only'])
            self.assertFalse((root / 'out/vf0000').exists())
            self.assertEqual(interior.read_bytes(), b'interior-control')
            # A placement outside the town cannot be silently dropped merely
            # because its original reference belongs to the same exterior cell.
            refs[0]['position'] = [9000, 4096, 0]
            (scenery / 'scenery-index.json').write_text(json.dumps({'errors': [], 'master_sha256': 'm', 'references': refs}))
            with self.assertRaisesRegex(ValueError, 'omitted source references'):
                S.prepare(terrain, scenery, root / 'palette.lmp', root / 'bad', 1)

    def test_every_exterior_stage_receives_checklist_but_interiors_do_not(self):
        import exterior_plan as E
        names = ['world-terrain', 'world-scenery', 'world-flora', 'balmora-interiors', 'engine', 'image']
        result = dict(E.bind_steps([(n, ['tool']) for n in names], 'checklist.json'))
        for name in names[:3]:
            self.assertEqual(result[name][-2:], ['--exterior-plan', 'checklist.json'])
        for name in names[3:5]:
            self.assertEqual(result[name], ['tool'])
        self.assertEqual(result['image'][-2:], ['--exterior-terrain', 'world-terrain'])

    def test_terrain_schedules_only_bsp_not_chim_or_town_owned_cores(self):
        import hashlib
        from unittest.mock import patch
        import exterior_plan as E
        import prepare_world_regions as T
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for folder in ('survey', 'data', 'scene/id1/gfx', 'bin'):
                (root / folder).mkdir(parents=True)
            for name in ('Morrowind.esm', 'Morrowind.bsa'):
                (root / 'data' / name).write_bytes(b'synthetic')
            for name in ('world-survey.json', 'terrain-source.npz'):
                (root / 'survey' / name).write_bytes(b'synthetic')
            (root / 'scene/id1/gfx/palette.lmp').write_bytes(bytes(768))
            sha = hashlib.sha256(b'synthetic').hexdigest()
            checklist = E.make([(0, 0), (1, 0), (2, 0)], [(2, 0)],
                               [{'owner': 'town', 'core': [0, 0, 2048, 2048]}], sha)
            (root / 'plan.json').write_text(json.dumps(checklist))
            entries = [dict(name='vf%04d' % i, cell=[i, 0], divisions=1,
                origin=[i*2048+1024, 1024, 0], core=[[-1024]*2, [1024]*2],
                coverage=[[-1920]*2, [1920]*2]) for i in range(3)]
            report = {'master_sha256': sha, 'bsa_sha256': sha,
                      'cells': [{'cell': [i, 0]} for i in range(3)]}
            compiled = []
            def compile_one(task):
                compiled.append(task[2]['name'])
                return dict(task[2], converted={'bytes': 128, 'sha256': 'test'})
            def run_costed(label, worker, tasks, keys, jobs, **kw):
                return [worker(task) for task in tasks]
            def frame_row(task):
                return dict(task[2], converted=None, chim_region=True)
            with patch.object(T, 'plan', return_value=(report, entries)), \
                 patch.object(T, 'terrain_wad', return_value=b'wad'), \
                 patch.object(T, 'compile_region', side_effect=compile_one), \
                 patch.object(T, 'chim_region_row', side_effect=frame_row), \
                 patch('build_costs.costed_map', side_effect=run_costed), \
                 patch('lava.lava_mode', return_value='off'):
                result = T.prepare(root/'survey', root/'data', root/'scene', root/'out', root/'bin', 1,
                    only=['vf0000', 'vf0001', 'vf0002'], chim_cells={(2, 0)}, exterior_plan=root/'plan.json')
            self.assertEqual(compiled, ['vf0001'])
            self.assertEqual(result['routing_only_maps_not_made'], ['vf0000'])
            self.assertTrue(result['regions'][2]['chim_region'])
