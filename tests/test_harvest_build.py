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


class HarvestBuild(unittest.TestCase):
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


class ImageHooks(unittest.TestCase):
    def test_image_step_hooks(self):
        text = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        image = text[text.index('def image(args):'):text.index('def staged_exterior_map_names')]
        final = text[text.index('def finalize_image(args):'):text.index('def main():')]
        # Baked mushrooms go before the final map passes; catalogues after the
        # last map change, before the entity tracker, heap audit and fingerprint.
        self.assertLess(image.index('clear_baked('), image.index("qc=out/'qc'"))
        for later in ('entity_gate(', 'audit_world_map_heap_with_receipt(', 'write_content_fingerprint('):
            self.assertLess(final.index('optimize_maps(boot'), final.index('harvest_image_step('))
            self.assertLess(final.index('harvest_image_step('), final.index(later))
        self.assertIn("build_record['harvest'] = harvest", final)

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
