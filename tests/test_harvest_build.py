# SPDX-License-Identifier: GPL-3.0-only
"""BUILD-HARVEST-NOT-BUILT-32: harvestable mushrooms built by the builder.

Synthetic master, packet and maps (no game data): the plan comes from the
staged region directories, the geometry gate refuses baked mushrooms where a
harvestable one is placed, clear_baked removes exactly those, admission
follows the heap check, and the output is byte-identical for every --jobs.
"""
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools'), str(ROOT / 'tests')]

from mwad.scene import pack_geometry  # noqa: E402
from compact_bsp import entities, entity_bytes  # noqa: E402
from player_hull import lumps, pack_lumps  # noqa: E402
from prepare_scenery import world_bounds  # noqa: E402
from test_replace_bsp_world import fixture as bsp_fixture  # noqa: E402
from test_world_flora_integration import record, sub  # noqa: E402
import harvest_build  # noqa: E402

PALETTE = bytes(range(256)) * 3
# (reference number, cell, position): quarter-scale positions (10, 20), (100, 20), (2050, 20).
PLACEMENTS = ((101, (0, 0), (40., 80., 0.)), (102, (0, 0), (400., 80., 0.)), (103, (1, 0), (8200., 80., 0.)))


def master():
    raw = record('CONT', sub('NAME', b'plant\0') + sub('FNAM', b'Luminous Russula\0') +
                 sub('MODL', b'f/flora_bc_mushroom_01.nif\0') + sub('FLAG', struct.pack('<I', 11)) +
                 sub('CNDT', struct.pack('<f', 0)) + sub('NPCO', struct.pack('<i32s', 1, b'ingredient')))
    raw += record('INGR', sub('NAME', b'ingredient\0') + sub('FNAM', b'Original ingredient name\0'))
    for cell in ((0, 0), (1, 0)):
        body = sub('DATA', struct.pack('<Iii', 0, *cell))
        for number, where, position in PLACEMENTS:
            if where == cell:
                body += sub('FRMR', struct.pack('<I', number)) + sub('NAME', b'plant\0') + \
                    sub('DATA', struct.pack('<6f', *position, 0, 0, 0))
        raw += record('CELL', body)
    return raw


def fake_export_refs(data_files, out, refs, groups, centre, texture_size=64, jobs=None, **_):
    """The packet export_refs would write, from a synthetic triangle model."""
    out = Path(out)
    out.mkdir(parents=True)
    vertices = [[0, 0, 0, -.4, -.3, 255, 255, 255, 255], [7, 0, 1, 2.6, .2, 255, 255, 255, 255],
                [0, 5, 2, .2, 2.3, 255, 255, 255, 255]]
    geometry = pack_geometry(vertices, [[0, 1, 2, 0]], 1)
    texture = struct.pack('>4sHH', b'MWT1', 2, 2) + bytes([160, 90, 40, 255]) * 4
    offset = (len(geometry) + 511) & ~511
    (out / 'scenery.mwpak').write_bytes(geometry + bytes(offset - len(geometry)) + texture)
    model = dict(source='meshes/f/flora_bc_mushroom_01.nif', source_sha256='a' * 64,
                 sha256=hashlib.sha256(geometry).hexdigest(), bytes=len(geometry), offset=0,
                 bounds=[[0, 0, 0], [7, 5, 2]], materials=[dict(texture_index=0, alpha=1, diffuse=[1, 1, 1])])
    index = dict(models=[model], textures=[dict(sha256=hashlib.sha256(texture).hexdigest(), bytes=len(texture),
                                                offset=offset)],
                 references=[dict(r, model_index=0, bounds=world_bounds(model['bounds'], r)) for r in refs], errors=[])
    (out / 'scenery-index.json').write_text(json.dumps(index) + '\n')


def bsp(baked=None):
    """A small map; baked=(number, origin) adds a baked brush mushroom bound to that placement."""
    data = lumps(bsp_fixture(inline=True))
    records = entities(data[0])
    records[1].update(aw_ref='999', origin='123 456 0', angles='0 0 0')
    if baked:
        records[1].update(aw_ref=str(baked[0]), origin=' '.join(map(str, baked[1])))
    records = records[:2]
    data[0] = bytearray(entity_bytes(records))
    return pack_lumps(data)


def awr(rows):
    # Header: the two town slots (origin, core), then one row per world map.
    raw = bytearray(b'AWR2' + struct.pack('<I', len(rows)) + struct.pack('<7f', 0, 0, 0, 0, 0, 1, 1) * 2)
    for name, origin, coverage in rows:
        raw += struct.pack('<8s11f', name.encode(), *origin, *coverage[0], *coverage[1], *coverage[0], *coverage[1])
    return bytes(raw)


def stage(root, baked=False):
    """A staged id1 with three world maps; vf0000 may carry a baked mushroom."""
    id1 = Path(root) / 'id1'
    (id1 / 'maps').mkdir(parents=True)
    (id1 / 'world').mkdir()
    (id1 / 'gfx').mkdir()
    (id1 / 'gfx/palette.lmp').write_bytes(PALETTE)
    (id1 / 'world/regions.awr').write_bytes(awr([
        ('vf0000', (0, 0, 0), ((-50, -50), (60, 60))),
        ('vf0001', (0, 0, 0), ((-50, -50), (3000, 3000))),
        ('vf0002', (0, 0, 0), ((5000, 5000), (6000, 6000)))]))
    (id1 / 'maps/vf0000.bsp').write_bytes(bsp((101, (10, 20, 0)) if baked else None))
    (id1 / 'maps/vf0001.bsp').write_bytes(bsp())
    (id1 / 'maps/vf0002.bsp').write_bytes(bsp())
    return id1


def gates(failing=()):
    def admission(id1, names, sizes, jobs=None):
        return {n: dict(gate='fail' if n in failing else 'pass', estimated_total_bytes=1,
                        estimated_clearance_bytes=-1 if n in failing else 1, harvest=1, harvest_allocator=0)
                for n in sorted(names)}
    return admission


class HarvestCase(unittest.TestCase):
    """The synthetic source and stage helpers (no tests of its own)."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = self.root / 'Data Files'
        self.data.mkdir()
        (self.data / 'Morrowind.esm').write_bytes(master())
        (self.data / 'Morrowind.bsa').write_bytes(b'')  # read only by export_refs (replaced here)
        (self.root / 'palette.lmp').write_bytes(PALETTE)

    def tearDown(self):
        self.temp.cleanup()

    def prepare(self, name='harvest', jobs=1):
        with patch('prepare_scenery.export_refs', fake_export_refs), \
                patch('prepare_hand_catalog.runtime_palette', lambda data, palette: PALETTE):
            return harvest_build.prepare(self.data, self.root / 'palette.lmp', self.root / name, jobs=jobs)

    def install(self, id1, source='harvest', failing=(), jobs=1, clear=True):
        work = id1.parent / 'work'
        with patch('harvest_build.heap_admission', gates(failing)):
            if clear:
                harvest_build.clear_baked(self.root / source, id1, work, data_files=self.data, jobs=jobs)
            return harvest_build.install(self.root / source, id1, work, data_files=self.data, sizes={}, jobs=jobs)


class HarvestBuild(HarvestCase):
    def test_plan_generated_from_the_players_data(self):
        receipt = self.prepare()
        self.assertEqual(receipt['placements'], 3)
        self.assertEqual(len(receipt['models']), 1)
        self.assertTrue((self.root / 'harvest/payload' / receipt['models'][0]['path']).is_file())
        id1 = stage(self.root / 's')
        staging = self.install(id1)
        self.assertEqual((staging['maps_considered'], staging['candidates'], staging['admitted'], staging['plants']),
                         (3, 2, 2, 4))
        plan = json.loads((id1.parent / 'work/harvest-plan.json').read_text())
        self.assertEqual(plan['format'], 'AmiWind external harvest plan 1')
        self.assertEqual([(m['name'], len(m['keys'])) for m in plan['maps']], [('vf0000', 1), ('vf0001', 3)])
        catalogue = (id1 / 'harvest-vf0001.txt').read_text()
        header = catalogue.splitlines()[0].split()
        # One ingredient node, one interned contents span, three plants of three slots, one model.
        self.assertEqual(header[:5] + header[6:], ['AWH4', '1', '1', '3', '3', '1'])
        self.assertIn('Luminous Russula', catalogue)
        self.assertFalse((id1 / 'harvest-vf0002.txt').exists())
        self.assertTrue((id1 / receipt['models'][0]['path']).is_file())
        # The image fingerprint and the heap check accept what was installed.
        from build_aga import harvest_fingerprint_entries
        self.assertEqual(len(harvest_fingerprint_entries(id1)), 3)

    def test_plan_rows_follow_the_staged_region_tables(self):
        id1 = Path(self.root / 't/id1')
        (id1 / 'maps').mkdir(parents=True)
        for name in ('sn000', 'bm000', 'intro_docks'):
            (id1 / 'maps' / (name + '.bsp')).write_bytes(b'')
        header = 'AWBR1 2 96 540 0 0 64 90 0 0 64 90\n'
        (id1 / 'seyda-regions.txt').write_text(header + 'sn000 -2079 -2079 -1536 -1536 -2079 -2560 -836 -836\n'
                                               'sn001 -1536 -2079 -768 -1536 -2048 -2560 -68 -836\n')
        (id1 / 'balmora-regions.txt').write_text(header.replace('AWBR1 2', 'AWBR1 1') +
                                                 'bm000 -3072 -3072 -1536 -2304 -3072 -3072 -640 -1408\n')
        rows = {r['name']: r for r in harvest_build.plan_rows(id1)}
        self.assertEqual(sorted(rows), ['bm000', 'intro_docks', 'sn000'])  # sn001 has no map
        self.assertEqual(rows['sn000']['origin'], [-2816., -17920., 0.])
        self.assertEqual(rows['sn000']['coverage'], [[-2079., -2560.], [-836., -836.]])
        self.assertEqual(rows['bm000']['origin'], [-5120., -3072., 0.])
        from prepare_intro_docks import BOUNDS
        self.assertEqual(rows['intro_docks']['coverage'], [[BOUNDS[0], BOUNDS[1]], [BOUNDS[2], BOUNDS[3]]])
        self.assertEqual(rows['intro_docks']['origin'], rows['sn000']['origin'])

    def test_admission_follows_the_heap_check(self):
        self.prepare()
        id1 = stage(self.root / 's')
        staging = self.install(id1, failing={'vf0001'})
        self.assertEqual(staging['admitted'], 1)
        self.assertEqual(sorted(staging['not_admitted']), ['vf0001'])
        self.assertFalse((id1 / 'harvest-vf0001.txt').exists())
        self.assertTrue((id1 / 'harvest-vf0000.txt').exists())
        # Nothing admitted: no catalogue and no orphan model is left behind.
        id1 = stage(self.root / 't')
        staging = self.install(id1, failing={'vf0000', 'vf0001'})
        self.assertEqual((staging['admitted'], staging['models']), (0, 0))
        self.assertEqual(list(id1.glob('harvest-*.txt')), [])
        self.assertFalse((id1 / 'progs/harvest').exists())

    def test_chim_town_catalogues_are_written_after_the_heap_check(self):
        # BUILD-HARVEST-NATIVE-TOWN-ORDER-36: a CHIM town's frame map is written later in the image step, so its
        # catalogues must not be on disk while the per-map heap check reads every catalogue in the image.
        self.prepare()
        id1 = stage(self.root / 's')
        real = harvest_build.map_selections
        seen = {}

        def selections(id1_, refs, native=(), **kw):
            rows, found = real(id1_, refs, native, **kw)
            return [dict(r, chim=True) if r['name'] == 'vf0001' else r for r in rows], found

        def admission(id1_, names, sizes, jobs=None):
            seen['names'] = sorted(names)
            seen['files'] = sorted(p.name for p in id1_.glob('harvest-*.txt'))
            return gates()(id1_, names, sizes, jobs)

        work = id1.parent / 'work'
        with patch('harvest_build.map_selections', selections), patch('harvest_build.heap_admission', admission):
            harvest_build.clear_baked(self.root / 'harvest', id1, work, data_files=self.data, jobs=1)
            staging = harvest_build.install(self.root / 'harvest', id1, work, data_files=self.data, sizes={}, jobs=1)
        self.assertEqual(seen, {'names': ['vf0000'], 'files': ['harvest-vf0000.txt']})
        self.assertEqual(staging['admitted'], 2)
        self.assertTrue((id1 / 'harvest-vf0001.txt').is_file())

    def regions(self, id1, cells=((0, 0), (1, 0)), z=7.0):
        """vf0001 replaced by a CHIM region frame (no legacy map), vf0002 its divided cell's alias row."""
        (id1 / 'maps/vf0001.bsp').unlink()
        return {'vf0001': dict(frame='rc0_p0', cells=[list(c) for c in cells], origin=[0., 0., z], aliases=['vf0002'])}

    def test_plan_rows_take_chim_region_frames(self):
        # HARVEST-CHIM-REGION-LOSS-41: a CHIM region cell has no legacy map; its row stays, with the frame's origin
        id1 = stage(self.root / 's')
        rows = {r['name']: r for r in harvest_build.plan_rows(id1, regions=self.regions(id1))}
        self.assertEqual(sorted(rows), ['vf0000', 'vf0001'])                    # the alias row is never loaded
        self.assertEqual(rows['vf0001']['origin'], [0., 0., 7.])
        self.assertEqual((rows['vf0001']['chim'], rows['vf0001']['frame']), (True, 'rc0_p0'))
        self.assertNotIn('chim', rows['vf0000'])
        self.assertEqual([r['name'] for r in harvest_build.plan_rows(id1)], ['vf0000', 'vf0002'])  # the earlier plan

    def test_chim_region_frames_get_their_catalogue(self):
        self.prepare()
        id1 = stage(self.root / 's')
        regions = self.regions(id1)
        seen = {}

        def admission(id1_, names, sizes, jobs=None):
            seen['names'] = sorted(names)
            return gates()(id1_, names, sizes, jobs)

        work = id1.parent / 'work'
        with patch('harvest_build.chim_regions', lambda id1_, world: regions), \
                patch('harvest_build.heap_admission', admission):
            harvest_build.clear_baked(self.root / 'harvest', id1, work, data_files=self.data, chim_world='w')
            staging = harvest_build.install(self.root / 'harvest', id1, work, data_files=self.data, sizes={},
                                            chim_world='w')
        self.assertEqual(seen['names'], ['vf0000'])                              # no per-map heap check for a frame
        self.assertEqual((staging['admitted'], staging['plants']), (2, 4))
        raw = (id1 / 'harvest-vf0001.txt').read_bytes()
        self.assertEqual(staging['chim_region_catalogues'],
                         {'vf0001': dict(frame='rc0_p0', plants=3, sha256=hashlib.sha256(raw).hexdigest(),
                                         bytes=len(raw))})
        plan = {m['name']: m for m in json.loads((work / 'harvest-plan.json').read_text())['maps']}
        self.assertEqual((plan['vf0001']['path'], plan['vf0001']['chim'], plan['vf0001']['frame'],
                          plan['vf0001']['origin']), (None, True, 'rc0_p0', [0., 0., 7.]))
        from entity_tracker import harvest_refs
        self.assertEqual(harvest_refs(raw), {101, 102, 103})

    def test_a_chim_map_over_the_runtime_bounds_stops_the_build(self):
        self.prepare()
        id1 = stage(self.root / 's')
        regions = self.regions(id1)
        limits = dict(harvest_build.runtime_limits(), plants=2)
        with patch('harvest_build.chim_regions', lambda id1_, world: regions), \
                patch('harvest_build.runtime_limits', lambda: limits), \
                patch('harvest_build.heap_admission', gates()):
            with self.assertRaisesRegex(ValueError, 'CHIM map.*over the runtime catalogue bounds.*vf0001: 3 plants'):
                harvest_build.install(self.root / 'harvest', id1, id1.parent / 'work', data_files=self.data,
                                      sizes={}, chim_world='w')

    def test_chim_coverage_reads_a_one_area_world(self):
        # HARVEST-CHIM-COVERAGE-ONE-AREA-48: a world of one area (every MiniWind sandbox of one town) writes its own
        # parity record, not {area: record}; the check reads both forms and finds the same plants
        self.prepare()
        _, _, refs = harvest_build.source_placements(self.root / 'harvest', self.data)
        id1 = stage(self.root / 's')
        reports = []
        for name, receipt in (('keyed', {'areas': ['balmora'], 'parity': {'balmora': {'harvest_removed': [102, 103]}}}),
                              ('one', {'areas': ['balmora'], 'town': 'balmora',
                                       'parity': {'harvest_removed': [102, 103], 'town_flora_added': []}})):
            world = self.root / ('world-' + name)
            world.mkdir()
            (world / 'chim-receipt.json').write_text(json.dumps(receipt))
            reports.append(harvest_build.chim_coverage(id1, world, refs, harvest_build.plan_rows(id1)))
        def found(report):          # what the check found (the receipt's own hash differs between the two files)
            return {k: v for k, v in report.items() if 'sha' not in k and 'receipt' not in k}
        self.assertEqual(found(reports[1]), found(reports[0]))
        # and the plants were read (a world that removed none gives another result)
        empty = self.root / 'world-none'
        empty.mkdir()
        (empty / 'chim-receipt.json').write_text(json.dumps({'areas': ['balmora'], 'parity': {'harvest_removed': []}}))
        self.assertNotEqual(found(harvest_build.chim_coverage(id1, empty, refs, harvest_build.plan_rows(id1))),
                            found(reports[0]))

    def test_a_chim_town_made_from_the_game_data_gets_its_own_catalogue_rows(self):
        # CHIM-NATIVE-HARVEST-MISSING-36 (v0.0.57): every town whose region table the image ships gets catalogue rows
        # (before: Seyda Neen and Balmora only, so Vivec's plants were in no catalogue of its frame)
        from town_config import runtime_towns
        id1 = Path(self.root / 'v/id1')
        (id1 / 'maps').mkdir(parents=True)
        vivec = next(t for t in runtime_towns() if t['id'] == 'vivec_city')
        p = vivec['prefix']
        (id1 / vivec['regions']).write_text('AWBR1 2 96 540 0 0 64 90 0 0 64 90\n'
                                            '%s000 -2079 -2079 -1536 -1536 -2079 -2560 -836 -836\n'
                                            '%s001 -1536 -2079 -768 -1536 -2048 -2560 -68 -836\n' % (p, p))
        names = {r['name']: r for r in harvest_build.plan_rows(id1, ['vivec_city'])}
        self.assertEqual(sorted(names), [p + '000', p + '001'])     # no region maps: a CHIM-native town's rows
        self.assertTrue(all(r.get('chim') for r in names.values()))
        self.assertEqual(harvest_build.unsupported_towns(['vivec_city'], id1), [])

    def test_partial_area_build_of_a_town_without_harvest_catalogues(self):
        # HARVEST-CHIM-COVERAGE-ONE-AREA-48, persisting (v0.0.54-dev1 combat playground: an interior-scope MiniWind of
        # one Vivec room stopped at the image step after 20 minutes): a one-area CHIM world of a town that has no
        # harvest catalogue mechanism (only the fixed towns Seyda Neen and Balmora do) leaves its plants out with
        # nowhere to place them. A partial-area test build lists them as its limit; every other build still refuses,
        # and a fixed town's or a region frame's plants are refused in a partial-area build too.
        self.prepare()
        _, _, refs = harvest_build.source_placements(self.root / 'harvest', self.data)
        id1 = stage(self.root / 's')
        # CHIM-NATIVE-HARVEST-MISSING-36 (v0.0.57): a town is unsupported only when the image ships no region table of
        # it (here: no town's region table is staged)
        self.assertEqual(harvest_build.unsupported_towns(['vivec_city', 'seyda'], id1), ['seyda', 'vivec_city'])
        self.assertEqual(harvest_build.unsupported_towns(['vivec_city']), [])
        world = self.root / 'world-vivec'
        world.mkdir()
        (world / 'chim-receipt.json').write_text(json.dumps(
            {'areas': ['vivec_city'], 'town': 'vivec_city', 'parity': {'harvest_removed': [102, 103]}}))
        (id1 / 'world/regions.awr').unlink()          # an interior-scope MiniWind ships no open-world maps
        rows = harvest_build.plan_rows(id1, ['vivec_city'])
        self.assertEqual(rows, [])                     # and the town gets no catalogue rows
        refused = harvest_build.chim_coverage(id1, world, refs, rows)
        self.assertEqual(([m['ref'] for m in refused['missing']], refused['partial_area']), ([102, 103], []))
        listed = harvest_build.chim_coverage(id1, world, refs, rows,
                                             partial_towns=harvest_build.unsupported_towns(['vivec_city'], id1))
        self.assertEqual(([m['ref'] for m in listed['partial_area']], listed['missing']), ([102, 103], []))
        with self.assertRaisesRegex(ValueError, 'HARVEST-CHIM-REGION-LOSS-41.*102'):
            harvest_build.require_chim_coverage(self.root / 'harvest', id1, id1.parent / 'work', data_files=self.data,
                                                chim_world=world, native=['vivec_city'])
        report = harvest_build.require_chim_coverage(self.root / 'harvest', id1, id1.parent / 'work',
                                                     data_files=self.data, chim_world=world, native=['vivec_city'],
                                                     partial_area=True)
        self.assertEqual((len(report['partial_area']), report['missing'], report['partial_towns']),
                         (2, [], ['vivec_city']))
        # v0.0.57 (CHIM-NATIVE-HARVEST-MISSING-36): every town with a region table has catalogues, so any town whose
        # table this partial-area image lacks (Balmora here too) is listed as its limit, and the plan has no early word
        fixed = self.root / 'world-balmora'
        fixed.mkdir()
        (fixed / 'chim-receipt.json').write_text(json.dumps(
            {'areas': ['balmora'], 'town': 'balmora', 'parity': {'harvest_removed': [102, 103]}}))
        report = harvest_build.require_chim_coverage(self.root / 'harvest', id1, id1.parent / 'work',
                                                     data_files=self.data, chim_world=fixed, native=['balmora'],
                                                     partial_area=True)
        self.assertEqual(report['partial_towns'], ['balmora'])
        import miniwind
        self.assertIsNone(miniwind.harvest_note('vivec_city'))
        self.assertIsNone(miniwind.harvest_note('balmora'))
        # both of the image step's calls pass the build's partial-area state
        self.assertIn("partial_area=bool(getattr(args, 'miniwind', False))",
                      (ROOT / 'tools' / 'build_aga.py').read_text(encoding='utf-8'))
        self.assertIn("partial_area=bool(getattr(args, 'miniwind', False))",
                      (ROOT / 'tools' / 'harvest_build.py').read_text(encoding='utf-8'))

    def test_chim_coverage_finds_plants_the_chim_world_left_out(self):
        # The island-wide check: every plant the CHIM world leaves out (receipt parity harvest_removed) is in a
        # shipped catalogue, a CHIM region cell's in the catalogue of its own frame map; the dev4 loss fails it.
        self.prepare()
        world = self.root / 'world'
        world.mkdir()
        (world / 'chim-receipt.json').write_text(json.dumps(
            {'parity': {'rc0_p0': {'harvest_removed': [101, 102]}, 'rc1_p0': {'harvest_removed': [103]}}}))
        _, _, refs = harvest_build.source_placements(self.root / 'harvest', self.data)
        id1 = stage(self.root / 's')
        regions = self.regions(id1)
        # The earlier plan: no catalogue for the region frame; 101 lies in the coverage of vf0000 (legacy), the
        # rest nowhere.
        report = harvest_build.chim_coverage(id1, world, refs, harvest_build.plan_rows(id1))
        self.assertEqual(([m['ref'] for m in report['missing']], report['placed']['legacy_map']), ([102, 103], 1))
        # With the region frame in the plan but no catalogue: the plants of its own cells must be in its
        # catalogue, whatever legacy overlap there is (101 too).
        rows = harvest_build.plan_rows(id1, regions=regions)
        report = harvest_build.chim_coverage(id1, world, refs, rows)
        self.assertEqual([(m['ref'], m.get('map')) for m in report['missing']],
                         [(101, 'vf0001'), (102, 'vf0001'), (103, 'vf0001')])
        with patch('harvest_build.chim_regions', lambda id1_, world_: regions), \
                patch('harvest_build.heap_admission', gates()):
            harvest_build.install(self.root / 'harvest', id1, id1.parent / 'work', data_files=self.data, sizes={},
                                  chim_world=world)
            report = harvest_build.require_chim_coverage(self.root / 'harvest', id1, id1.parent / 'work',
                                                         data_files=self.data, chim_world=world)
            self.assertEqual((report['missing'], report['placed']), ([], dict(region_cell=3, catalogue=0,
                                                                                legacy_map=0)))
            # The final payload also needs the frame map of each catalogue.
            with self.assertRaisesRegex(ValueError, 'vf0001: catalogue without its CHIM region frame map'):
                harvest_build.require_chim_coverage(self.root / 'harvest', id1, id1.parent / 'work',
                                                    data_files=self.data, chim_world=world, frame_maps=True)
            (id1 / 'maps/vf0001.chim').write_bytes(b'')
            self.assertEqual(harvest_build.require_chim_coverage(
                self.root / 'harvest', id1, id1.parent / 'work', data_files=self.data, chim_world=world,
                frame_maps=True, report_name='final.json')['missing'], [])
        self.assertTrue((id1.parent / 'work/final.json').is_file())

    def test_heap_check_estimates_only_the_named_maps(self):
        from check_world_map_heap import inspect_maps
        id1 = stage(self.root / 's')
        with self.assertRaisesRegex(ValueError, 'No BSP maps found'):
            inspect_maps(id1 / 'maps', {}, only=set())

    def test_geometry_gate_refuses_baked_mushrooms(self):
        self.prepare()
        id1 = stage(self.root / 's', baked=True)
        before = (id1 / 'maps/vf0000.bsp').read_bytes()
        with self.assertRaisesRegex(ValueError, 'geometry gate failed.*vf0000: Retained BSP already binds'):
            self.install(id1, clear=False)
        self.assertEqual(list(id1.glob('harvest-*.txt')), [])
        # Same pose, no reference binding: still refused.
        records = entities(lumps(before)[0])
        del records[1]['aw_ref']
        data = lumps(before)
        data[0] = bytearray(entity_bytes(records))
        (id1 / 'maps/vf0000.bsp').write_bytes(pack_lumps(data))
        with self.assertRaisesRegex(ValueError, 'scenery at selected source pose'):
            self.install(id1, clear=False)

    def test_clear_baked_removes_exactly_the_bound_mushroom(self):
        self.prepare()
        id1 = stage(self.root / 's', baked=True)
        other = (id1 / 'maps/vf0001.bsp').read_bytes()
        staging = self.install(id1)
        self.assertEqual(staging['baked_removal'], dict(maps=1, placements=1))
        self.assertNotIn('101', [e.get('aw_ref') for e in entities(lumps((id1 / 'maps/vf0000.bsp').read_bytes())[0])])
        self.assertEqual((id1 / 'maps/vf0001.bsp').read_bytes(), other)
        self.assertTrue((id1 / 'harvest-vf0000.txt').exists())

    def test_removed_mushrooms_must_be_admitted(self):
        self.prepare()
        id1 = stage(self.root / 's', baked=True)
        with self.assertRaisesRegex(ValueError, 'baked mushrooms were removed.*vf0000'):
            self.install(id1, failing={'vf0000'})

    def test_other_palette_or_master_is_refused(self):
        self.prepare()
        id1 = stage(self.root / 's')
        (id1 / 'gfx/palette.lmp').write_bytes(bytes(768))
        with self.assertRaisesRegex(ValueError, 'another palette'):
            self.install(id1)
        (id1 / 'gfx/palette.lmp').write_bytes(PALETTE)
        (self.data / 'Morrowind.esm').write_bytes(master() + b'x')
        with self.assertRaisesRegex(ValueError, 'another master'):
            self.install(id1)

    def test_byte_identical_for_every_jobs_value(self):
        results = []
        for jobs in (1, 2):
            self.prepare('harvest-%d' % jobs, jobs=jobs)
            id1 = stage(self.root / ('s%d' % jobs), baked=True)
            self.install(id1, source='harvest-%d' % jobs, jobs=jobs)
            trees = []
            for base in (self.root / ('harvest-%d' % jobs), id1.parent):
                trees.append({p.relative_to(base).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in sorted(base.rglob('*')) if p.is_file()})
            results.append(trees)
        self.assertEqual(results[0], results[1])
        self.assertIn('id1/harvest-vf0000.txt', results[0][1])

    def test_runtime_bounds_match_the_builder(self):
        limits = harvest_build.runtime_limits()
        self.assertEqual(limits['plants'], harvest_build.MAX_PLANTS)
        self.assertEqual(limits['models'], 8)


# HARVEST-INTERIOR-PICK-47: one interior with a representable mushroom (201) and an owned one (202, left baked).
CAVE = 'Test Cave'
CAVE_PLANTS = ((201, (400., 800., -40.), b''), (202, (440., 800., -40.), b'someone\0'))


def interior_master():
    body = sub('NAME', CAVE.encode() + b'\0') + sub('DATA', struct.pack('<Iii', 1, 0, 0))
    for number, position, owner in CAVE_PLANTS:
        body += sub('FRMR', struct.pack('<I', number)) + sub('NAME', b'plant\0') + \
            sub('DATA', struct.pack('<6f', *position, 0, 0, 0)) + (sub('ANAM', owner) if owner else b'')
    return master() + record('CELL', body)


def stage_interior(root, origin=(0., 0., 0.)):
    """stage() plus one interior room map (mitestcave) that bakes plant 201 as a brush entity (aw_ref) at its
    quarter-scale original position shifted by `origin` (a recentred room)."""
    id1 = stage(root)
    position = [v * .25 + o for v, o in zip(CAVE_PLANTS[0][1], origin)]
    (id1 / 'maps/mitestcave.bsp').write_bytes(bsp((201, position)))
    return id1


class InteriorHarvest(HarvestCase):
    """HARVEST-INTERIOR-PICK-47: interior mushrooms share the world's pick state (one global index, one digest)."""

    def setUp(self):
        super().setUp()
        (self.data / 'Morrowind.esm').write_bytes(interior_master())

    def prepare(self, name='harvest', jobs=1, interiors=True):
        with patch('prepare_scenery.export_refs', fake_export_refs), \
                patch('prepare_hand_catalog.runtime_palette', lambda data, palette: PALETTE):
            return harvest_build.prepare(self.data, self.root / 'palette.lmp', self.root / name, jobs=jobs,
                                         interiors=interiors)

    def test_interior_placements_join_the_source_owned_ones_as_thefts(self):
        # HARVEST-INTERIOR-PICK-47 (decided for the project 2026-10-27): the owned one (202) joins too, as a theft
        receipt = self.prepare()
        self.assertEqual((receipt['placements'], receipt['interior_placements']), (5, 2))
        self.assertEqual(receipt['interior_refused'], [])
        self.assertTrue(receipt['settings']['interiors'])
        off = self.prepare('harvest-off', interiors=False)
        self.assertEqual((off['placements'], off['interior_placements'], off['interior_refused']), (3, 0, []))
        # Both sources share the one global index: the same digest and slot count (saves stay compatible).
        self.assertEqual((receipt['global_catalogue_sha256'], receipt['global_slots']),
                         (off['global_catalogue_sha256'], off['global_slots']))

    def test_interior_room_gets_its_catalogue_and_loses_the_baked_plant(self):
        receipt = self.prepare()
        id1 = stage_interior(self.root / 's')
        staging = self.install(id1)
        self.assertEqual(staging['baked_removal'], dict(maps=1, placements=1))
        self.assertNotIn('201', [e.get('aw_ref') for e in
                                 entities(lumps((id1 / 'maps/mitestcave.bsp').read_bytes())[0])])
        catalogue = (id1 / 'harvest-mitestcave.txt').read_text().splitlines()
        header = catalogue[0].split()
        self.assertEqual((header[0], header[3], header[5]), ('AWH4', '1', receipt['global_catalogue_sha256']))
        plant = catalogue[-1].split()
        self.assertEqual(plant[2], '201')
        # The plant's slot is its slot in the global index (the one the outdoor catalogues use).
        from prepare_harvest import identity_key, placement_index
        from world_flora import inventory
        indices, digest_ = placement_index(inventory(interior_master(), ('small_mushroom',)))
        self.assertEqual(digest_, receipt['global_catalogue_sha256'])
        self.assertEqual(int(plant[1]), indices[identity_key((hashlib.sha256(interior_master()).hexdigest(),
                                                              'interior', CAVE, 201))])
        # Room coordinates: the quarter-scale original position, origin 0 0 0.
        self.assertEqual([float(v) for v in plant[7:10]], [100., 200., -10.])
        self.assertEqual(staging['families']['interior'], dict(maps=1, with_plants=1, admitted=1, plants=1))
        plan = json.loads((id1.parent / 'work/harvest-plan.json').read_text())
        row = [m for m in plan['maps'] if m['name'] == 'mitestcave'][0]
        self.assertEqual((row['origin'], row['coverage'], len(row['keys'])), ([0., 0., 0.], None, 1))
        # Exterior coverage never takes the interior plant (vf0001 covers its position): still three outdoors.
        self.assertEqual(len([m for m in plan['maps'] if m['name'] == 'vf0001'][0]['keys']), 3)

    def test_a_recentred_room_keeps_its_origin(self):
        self.prepare()
        id1 = stage_interior(self.root / 's', origin=(-64., 32., 0.))
        self.install(id1)
        plant = (id1 / 'harvest-mitestcave.txt').read_text().splitlines()[-1].split()
        self.assertEqual([float(v) for v in plant[7:10]], [36., 232., -10.])
        plan = json.loads((id1.parent / 'work/harvest-plan.json').read_text())
        self.assertEqual([m for m in plan['maps'] if m['name'] == 'mitestcave'][0]['origin'], [64., -32., 0.])

    def test_disagreeing_room_origins_are_refused(self):
        refs = [dict(number=201, cell=CAVE, position=[400., 800., -40.]),
                dict(number=203, cell=CAVE, position=[0., 0., 0.])]
        id1 = Path(self.root / 'r/id1')
        (id1 / 'maps').mkdir(parents=True)
        (id1 / 'maps/mitestcave.bsp').write_bytes(b'')

        def bound(task):
            return 'mitestcave', [(201, [100., 200., -10.]), (203, [5., 0., 0.])]
        with patch('harvest_build._interior_bound', bound), \
                self.assertRaisesRegex(ValueError, 'mitestcave binds plants at disagreeing origins'):
            harvest_build.interior_rows(id1, refs, jobs=1)

    def test_interior_harvest_off_keeps_the_room_baked(self):
        self.prepare(interiors=False)
        id1 = stage_interior(self.root / 's')
        before = (id1 / 'maps/mitestcave.bsp').read_bytes()
        staging = self.install(id1)
        self.assertEqual((id1 / 'maps/mitestcave.bsp').read_bytes(), before)
        self.assertFalse((id1 / 'harvest-mitestcave.txt').exists())
        self.assertNotIn('interior', staging['families'])

    def test_builder_option_reaches_the_step(self):
        import argparse
        import build

        def tool(*a):
            return [str(v) for v in a]
        on = build.harvest_steps(argparse.Namespace(data_files='D', harvest_interiors='on'), tool, Path('r'), 4)[0]
        off = build.harvest_steps(argparse.Namespace(data_files='D', harvest_interiors='off'), tool, Path('r'), 4)[0]
        self.assertNotIn('--interiors', on[1])
        self.assertEqual(off[1][off[1].index('--interiors') + 1], 'off')


class ImageHooks(unittest.TestCase):
    def test_image_step_hooks(self):
        text = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        image = text[text.index('def image(args):'):text.index('def staged_exterior_map_names')]
        final = text[text.index('def finalize_image(args):'):text.index('def main():')]
        # Baked mushrooms go before the final map passes; catalogues after the
        # last map change, before the entity tracker, heap audit and fingerprint.
        self.assertLess(image.index('clear_baked('), image.index("qc=out/'qc'"))
        for later in ('entity_gate(', 'audit_world_map_heap_with_receipt(', 'image_content_fingerprint('):
            self.assertLess(final.index('optimize_maps(boot'), final.index('harvest_image_step('))
            self.assertLess(final.index('harvest_image_step('), final.index(later))
        self.assertIn("build_record['harvest'] = harvest", final)
        # HARVEST-CHIM-REGION-LOSS-41: the region frame maps keep the harvest step's catalogues, and the final
        # payload is checked for every plant the CHIM world leaves out, before the gates and the fingerprint.
        self.assertIn('keep_catalogues=keep_catalogues', final)
        self.assertLess(final.index('chim_frame_maps(args.chim_world'), final.index('require_chim_coverage('))
        self.assertLess(final.index('prune_world_payload(boot'), final.index('require_chim_coverage('))
        self.assertLess(final.index('require_chim_coverage('), final.index('image_content_fingerprint('))
        import inspect
        import build_aga
        self.assertIn('write_content_fingerprint(', inspect.getsource(build_aga.image_content_fingerprint))

    def test_image_step_without_source_warns(self):
        import argparse
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(harvest_build.image_step(argparse.Namespace(harvest=None), None, None),
                             dict(status='not_requested'))
        self.assertIn('no harvestable mushrooms', out.getvalue())

    def test_entity_tracker_counts_catalogue_plants(self):
        from entity_tracker import harvest_refs
        raw = ('AWH4 1 1 2 2 ' + 'a' * 64 + ' 1\nprogs/harvest/x.mdl ' + 'b' * 64 + ' 0 0 0 1 1 1\n'
               '0 0 0 0 0 ingredient\tName\n0 0 1\n'
               'k1 1 101 @0 11 0 1 0 0 0 0 0 0 1 Name\nk2 2 102 @0 11 0 1 0 0 0 0 0 0 1 Name\n').encode()
        self.assertEqual(harvest_refs(raw), {101, 102})
        self.assertEqual(harvest_refs(b'AWH1 0 0 0\n'), set())


if __name__ == '__main__':
    unittest.main()
