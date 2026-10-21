# SPDX-License-Identifier: GPL-3.0-only
"""Generated terrain records (world format 0.11, EXPERIMENTAL, build setting terrain_pack generate; tools/chim/thgt.py
and engine chim/chim_thgt.c): a regular-path chunk terrain stored as its heights and the facts the builder decided,
from which the engine generates the render part, the same bytes as the TERR record it replaces; the planes and the
standing hull stay stored.

The builder's own world with terrain references (tests/test_chim_format.py's fixture) is written plain and with the
generate pack and compared like for like: every generated record gives back the plain record byte for byte (in Python
and in the engine's generator, natively), the validator reads both worlds into the same chunks, the bytes saved are
counted; a record the generator does not make stays as the compact pack writes it. Synthetic data only.
"""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
SRC = ROOT / 'engine/aga/src'

try:
    import numpy as np  # noqa: F401
except ImportError:  # pragma: no cover - the gate image has it
    np = None

from test_chim_terc import ground, sector_records, world_bytes  # noqa: E402


@unittest.skipIf(np is None, 'numpy is required')
class GeneratedTerrainWorldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from test_chim_format import fixture
        cls.tmp = tempfile.TemporaryDirectory(prefix='amiwind-thgt-')
        t = Path(cls.tmp.name)
        cls.plain, cls.made = t / 'plain', t / 'made'
        base = {'grain': 256, 'sector_chunks': 2, 'terrain_refs': 'on'}
        cls.receipt_plain, _ = fixture(cls.plain, heights_of=ground, settings=base)
        cls.receipt_made, _ = fixture(cls.made, heights_of=ground, settings=dict(base, terrain_pack='generate'))
        cls.r_plain, cls.r_made = sector_records(cls.plain), sector_records(cls.made)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_version_and_receipt(self):
        from chim import format as F
        from chim import reach  # noqa: F401
        index = (Path(self.made) / 'chim/world.cwi').read_bytes()
        self.assertEqual(F.read_header(index)['version'], (0, 11))
        self.assertGreater(self.receipt_made['terrain_pack']['generated_records'], 0)

    def test_every_generated_record_gives_back_the_plain_record(self):
        from chim import terc, thgt
        made = 0
        for key, data in self.r_made.items():
            if key[0] == b'TERR':
                if thgt.is_generated(data):
                    made += 1
                    self.assertEqual(thgt.decode(data), self.r_plain[key])
                    self.assertLess(len(data), len(self.r_plain[key]))
                else:
                    self.assertEqual(terc.decode(data), self.r_plain[key])
            elif key[0] != b'CHNK':
                self.assertEqual(data, self.r_plain[key], key)
        self.assertGreater(made, 0)

    def test_validator_reads_the_same_chunks(self):
        from chim.validate import validate
        fa, wa = validate(self.plain)
        fb, wb = validate(self.made)
        self.assertEqual(list(fa), [])
        self.assertEqual(list(fb), [])
        for (_, _, ca), (_, _, cb) in zip(wa['frames'], wb['frames']):
            for x, y in zip(ca, cb):
                for key in ('owned', 'reach', 'pvs', 'pvl', 'image', 'image_render', 'leaves', 'terrain_record'):
                    self.assertEqual(x.get(key), y.get(key), key)

    def test_bytes_saved(self):
        info = self.receipt_made['terrain_pack']
        saved = sum(len(self.r_plain[k]) - len(d) for k, d in self.r_made.items() if k[0] == b'TERR')
        self.assertEqual(saved, info['bytes_saved'] + info['generated_bytes_saved'])
        self.assertEqual(world_bytes(self.plain) - world_bytes(self.made), saved)

    @unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
    @unittest.skipUnless(shutil.which('cc'), 'a C compiler is required')
    def test_engine_generates_every_record_to_the_same_bytes(self):
        from chim import thgt
        from test_aga_native_source import NativeSourceTests
        from test_chim_engine_native import WARN
        records = [(d, self.r_plain[k]) for k, d in sorted(self.r_made.items())
                   if k[0] == b'TERR' and thgt.is_generated(d)]
        with tempfile.TemporaryDirectory(prefix='amiwind-thgt-c-') as tmp:
            for n, (rec, image) in enumerate(records):
                (Path(tmp) / ('%d.thg' % n)).write_bytes(rec)
                (Path(tmp) / ('%d.img' % n)).write_bytes(image)
            out = Path(tmp) / 'out.txt'
            NativeSourceTests.compile_run(self, 'aga_chim_thgt_test.c',
                                          [SRC / 'chim/chim_format.c', SRC / 'chim/chim_terc.c',
                                           SRC / 'chim/chim_thgt.c'],
                                          cflags=[*WARN, '-O1'], arguments=[tmp, str(len(records)), str(out)])
            lines = out.read_text(encoding='ascii').splitlines()
        self.assertEqual(lines[:len(records)], ['%d same' % n for n in range(len(records))])
        self.assertTrue(lines[len(records)].startswith('work records %d ' % len(records)))
        self.assertEqual(lines[-1], 'refusals ok')


def irregular_ground():
    """tests/test_chim_ground.py's three kinds of tiles (a fine 32-unit patch, fans next to it carrying its edge
    samples, two coarse triangles elsewhere and a fan on every third tile) with the samples a LAND record gives: every
    corner on the 32-unit samples (the fans turn about the tile centre) and every height a quarter unit."""
    import test_chim_ground as G
    from chim.ground import TriangleGround
    from test_chim_format import LOW, SPAN, STEP, material

    def p(x, y):
        return [float(x), float(y), round(float(G.z(x, y)) * 4) / 4]

    def tiles(tx, ty):
        i, j = int((tx - LOW[0]) // STEP), int((ty - LOW[1]) // STEP)
        m = material(tx + STEP / 2, ty + STEP / 2)
        if G.fine(i, j):
            out = []
            for yy in range(int(ty), int(ty) + STEP, 32):
                for xx in range(int(tx), int(tx) + STEP, 32):
                    c = [p(xx, yy), p(xx + 32, yy), p(xx + 32, yy + 32), p(xx, yy + 32)]
                    out += [([c[0], c[1], c[2]], m), ([c[0], c[2], c[3]], m)]
            return out
        need = [G.fine(i, j - 1), G.fine(i + 1, j), G.fine(i, j + 1), G.fine(i - 1, j)]
        if not any(need) and (i + 2 * j) % 3:
            c = [p(tx, ty), p(tx + STEP, ty), p(tx + STEP, ty + STEP), p(tx, ty + STEP)]
            return [([c[0], c[1], c[2]], m), ([c[0], c[2], c[3]], m)]
        corners = [(tx, ty), (tx + STEP, ty), (tx + STEP, ty + STEP), (tx, ty + STEP)]
        ring = []
        for e in range(4):
            (ax, ay), (bx, by) = corners[e], corners[(e + 1) % 4]
            ring.append(p(ax, ay))
            if need[e]:
                ring += [p(ax + (bx - ax) * k / 4, ay + (by - ay) * k / 4) for k in (1, 2, 3)]
        centre = p(tx + 64, ty + 64)
        return [([ring[k], ring[(k + 1) % len(ring)], centre], m) for k in range(len(ring))]
    nx, ny = SPAN[0] // STEP, SPAN[1] // STEP
    tris = [t for j in range(ny) for i in range(nx) for t in tiles(LOW[0] + i * STEP, LOW[1] + j * STEP)]
    return TriangleGround(tris, STEP, LOW, (nx, ny))


@unittest.skipIf(np is None, 'numpy is required')
class GeneratedIrregularTerrainWorldTests(GeneratedTerrainWorldTests):
    """Record version 2: the same checks on a frame of irregular ground (irregular_ground: fine 32-unit patches, coarse
    tiles, fans), whose chunks the generator makes from the converter's own triangles."""

    @classmethod
    def setUpClass(cls):
        from test_chim_format import fixture
        triangle_ground = irregular_ground
        cls.tmp = tempfile.TemporaryDirectory(prefix='amiwind-thgt-irr-')
        t = Path(cls.tmp.name)
        cls.plain, cls.made = t / 'plain', t / 'made'
        base = {'grain': 256, 'sector_chunks': 2, 'terrain_refs': 'on'}
        cls.receipt_plain, _ = fixture(cls.plain, ground=triangle_ground(), settings=base)
        cls.receipt_made, _ = fixture(cls.made, ground=triangle_ground(), settings=dict(base, terrain_pack='generate'))
        cls.r_plain, cls.r_made = sector_records(cls.plain), sector_records(cls.made)

    def test_triangle_records_are_version_2(self):
        import struct
        from chim import thgt
        versions = [struct.unpack_from('>H', d, 12)[0] for k, d in self.r_made.items()
                    if k[0] == b'TERR' and thgt.is_generated(d)]
        self.assertIn(2, versions)
        made = [d for k, d in self.r_made.items() if k[0] == b'TERR' and thgt.is_generated(d)]
        for d in made:
            if struct.unpack_from('>H', d, 12)[0] == 2:
                facts = thgt.decode_facts(d)
                self.assertTrue(all(len(tris) for row in facts['tile_facts'] for _, tris in row))


class GeneratedTerrainRecordTests(unittest.TestCase):
    def test_what_the_generator_does_not_make_stays(self):
        """A record that is not a regular-path chunk (here: not a chunk image at all) is not generated."""
        from chim import format as F
        from chim import thgt
        lumps = [b''] * 15
        lumps[3] = b'\0' * 12
        image, _ = F.brush_image(lumps)
        self.assertIsNone(thgt.encode(image))
        self.assertEqual(thgt.decode(image), image)

    def test_option_values(self):
        from chim.terc import terrain_pack
        self.assertEqual(terrain_pack({'terrain_pack': 'generate', 'terrain_refs': 'on'}), 'generate')
        with self.assertRaises(ValueError):
            terrain_pack({'terrain_pack': 'generate'})
        import build as B
        opts = B.chim_stage_options(B.parser().parse_args(['--chim-terrain-pack', 'generate']))
        self.assertEqual(opts[opts.index('--terrain-pack') + 1], 'generate')


class GeneratedTerrainKeyTests(unittest.TestCase):
    def test_no_unit_kind_or_stair_code_reaches_the_module(self):
        from chim import units
        from chim import collision
        for kind in units.CODE_ENTRIES:
            self.assertNotIn('tools/chim/thgt.py', units.TOOLS.get(kind, []), kind)
            key = units.unit_code_key(kind)
            self.assertFalse(any('chim/thgt.py' in str(u) for u in key.get('units', key.get('reach', []))), kind)
        self.assertFalse(any('thgt.py' in f for f in collision.stair_code_selection()[0]))


if __name__ == '__main__':
    unittest.main()
