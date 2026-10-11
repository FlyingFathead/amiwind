# SPDX-License-Identifier: GPL-3.0-only
"""CHIM terrain references (world format 0.7, CHIM-REGION-MARGIN-STORAGE-36): chunk terrain stored once in
chunk-local units and placed at an offset (docs/chim/WORLD_FORMAT.md "Terrain references")."""
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src'), str(ROOT / 'tests')]

from chim import FORMAT_VERSION, REFS_FORMAT_VERSION  # noqa: E402
from chim import format as F  # noqa: E402
from chim.build import local_terrain_task, terrain_refs_on  # noqa: E402
from chim.terrain import terrain_unit  # noqa: E402
from chim_fixture import terrain_bsp  # noqa: E402


def lumps_of(image):
    return F.read_brush_image(image)


def grid_task(x0, y0, heights_of, step=128, grain=256):
    """A regular-grid chunk task at (x0, y0) with its full hull ring (as chim.build makes it)."""
    cx0, cy0 = x0 - step, y0 - step
    n = grain // step + 2
    hs = [[float(heights_of(cx0 + i * step, cy0 + j * step)) for i in range(n + 1)] for j in range(n + 1)]
    ms = [[1 + ((i + j) % 2) for i in range(grain // step)] for j in range(grain // step)]
    return {'box': (x0, y0, x0 + grain, y0 + grain), 'step': step, 'heights': hs, 'materials': ms,
            'floor': -1024, 'ceiling': 2048, 'water': 0.0, 'light': 12,
            'collision_box': (cx0, cy0, cx0 + n * step, cy0 + n * step)}


def ground(x, y):
    return 0.13 * x - 0.07 * y + 20.0 * ((x // 128 + y // 128) % 3) - 40.0


class TranslateTests(unittest.TestCase):
    def test_translated_fixture_terrain_equals_the_terrain_built_there(self):
        # every position field moves; texinfo, faces, edges and clipnodes stay
        at, local = terrain_bsp((-384, 640, -128, 896), 12.0, 20.0), terrain_bsp((0, 0, 256, 256), 12.0, 20.0)
        moved = lumps_of(F.translate_image(local, (-384, 640, 0)))
        want = lumps_of(at)
        for k in (1, 3, 5, 6, 7, 9, 11, 12, 13, 14):
            self.assertEqual(moved[k], want[k], F.LUMPS[k])
        self.assertEqual(moved[10][28:], want[10][28:])          # leaf 0 is the shared solid leaf

    def test_a_builder_unit_built_locally_and_moved_is_the_unit_built_in_place(self):
        # the builder's own terrain unit (routed standing hull with its ring): the chunk-local unit moved by
        # the graft's rule gives the same tree, faces, hull and bounds, planes within single precision
        task = grid_task(-640.0, 384.0, ground)
        direct = terrain_unit(task)['lumps']
        local = terrain_unit(local_terrain_task(task, -640.0, 384.0))['lumps']
        image = F.brush_image(local)[0]
        self.assertIsNone(F.refuse_shift(image, (-640, 384, 0)))
        moved = lumps_of(F.translate_image(image, (-640, 384, 0)))
        for k in (5, 6, 7, 9, 11, 12, 13, 14):
            self.assertEqual(moved[k], bytes(direct[k]), F.LUMPS[k])
        self.assertEqual(moved[10][28:], bytes(direct[10])[28:])
        for k, size in ((1, 20), (3, 12)):
            a = list(struct.iter_unpack('<%df' % (size // 4), moved[k]))
            b = list(struct.iter_unpack('<%df' % (size // 4), bytes(direct[k])))
            self.assertEqual(len(a), len(b))
            for ra, rb in zip(a, b):
                for va, vb in zip(ra, rb):
                    self.assertAlmostEqual(va, vb, delta=1e-3 * max(1.0, abs(vb)))

    def test_shift_rule(self):
        image = terrain_bsp((0, 0, 256, 256), 0.0)
        self.assertIsNone(F.refuse_shift(image, (256, -512, 0)))
        self.assertIn('moves 8 texels', F.refuse_shift(image, (8, 0, 0)))
        self.assertIn('whole units', F.refuse_shift(image, (0.5, 0, 0)))

    def test_a_model_origin_is_refused(self):
        lumps = list(lumps_of(terrain_bsp((0, 0, 256, 256), 0.0)))
        m = bytearray(lumps[14])
        struct.pack_into('<f', m, 24, 1.0)
        lumps[14] = bytes(m)
        with self.assertRaises(ValueError):
            F.translate_image(F.brush_image(lumps)[0], (256, 0, 0))

    def test_reference_block_round_trip(self):
        block = F.terrain_ref(7, 3, 1024, 900, 800, (-1920.0, 128.0, 0.0))
        self.assertEqual(len(block), 32)
        self.assertEqual(F.read_terrain_ref(block), {'id': 7, 'file': 3, 'offset': 1024, 'bytes': 900, 'render': 800,
                                                     'shift': (-1920.0, 128.0, 0.0)})

    def test_build_options_reach_the_chim_stage_only_when_given(self):
        import argparse
        from build import chim_stage_options
        self.assertEqual(chim_stage_options(argparse.Namespace()), [])
        self.assertEqual(chim_stage_options(argparse.Namespace(chim_terrain_hull='auto', chim_terrain_refs='off')), [])
        self.assertEqual(chim_stage_options(argparse.Namespace(chim_terrain_hull='compiled', chim_terrain_refs='on')),
                         ['--terrain-hull', 'compiled', '--terrain-refs', 'on'])

    def test_the_setting_is_off_by_default(self):
        self.assertFalse(terrain_refs_on({}))
        self.assertFalse(terrain_refs_on(None))
        self.assertTrue(terrain_refs_on({'terrain_refs': 'on'}))
        with self.assertRaises(ValueError):
            terrain_refs_on({'terrain_refs': 'yes'})


class WorldTests(unittest.TestCase):
    def build(self, out, refs):
        from test_chim_format import fixture
        return fixture(Path(out), settings={'grain': 256, 'sector_chunks': 2, **({'terrain_refs': 'on'} if refs else {})})

    def test_a_world_with_references_reads_as_the_world_with_copies(self):
        from chim.validate import Failures, load_world, validate
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            copies, source = self.build(a, False)
            refs, _ = self.build(b, True)
            self.assertEqual(copies['world_format'], '%d.%d' % FORMAT_VERSION)
            self.assertEqual(refs['world_format'], '%d.%d' % REFS_FORMAT_VERSION)
            self.assertNotIn('terrain_refs', copies)
            self.assertLessEqual(refs['terrain_refs']['records'], refs['chunks'])
            index = (Path(b) / 'chim/world.cwi').read_bytes()
            self.assertEqual(struct.unpack_from('>HH', index, 8), REFS_FORMAT_VERSION)
            fa, fb = Failures(), Failures()
            wa, wb = load_world(a, fa)[5], load_world(b, fb)[5]
            self.assertEqual((list(fa), list(fb)), ([], []))
            for (_, _, ca), (_, _, cb) in zip(wa, wb):
                for x, y in zip(ca, cb):
                    self.assertIn('ref', y)
                    self.assertEqual(x['owned'], y['owned'])
                    self.assertEqual(x['reach'], y['reach'])
                    self.assertEqual(x['pvs'], y['pvs'])
                    la, lb = lumps_of(x['image']), lumps_of(y['image'])
                    for k in (5, 6, 7, 9, 10, 11, 12, 13, 14):
                        self.assertEqual(la[k], lb[k], F.LUMPS[k])
            fails, _ = validate(b, source)
            self.assertEqual(list(fails), [])

    def test_a_reference_to_another_record_kind_is_refused(self):
        from chim.validate import Failures, load_world
        with tempfile.TemporaryDirectory() as b:
            self.build(b, True)
            root = Path(b) / 'chim'
            sector = sorted(root.rglob('s00.ccs'))[0]
            data = bytearray(sector.read_bytes())
            rec = next(r for r in F.read_sector(bytes(data)) if r['kind'] == b'CHNK')
            at = rec['offset'] + rec['bytes'] - F.TERRAIN_REF.size + 4      # the file row of the first chunk
            struct.pack_into('>H', data, at, 0)                             # the index is no sector file
            sector.write_bytes(bytes(data))
            fails = Failures()
            try:
                load_world(b, fails)
            except Exception:  # noqa: BLE001 - a structural refusal is fine too
                return
            self.assertTrue(any('terrain reference' in f or 'CRC' in f for f in fails), list(fails))


if __name__ == '__main__':
    unittest.main()
