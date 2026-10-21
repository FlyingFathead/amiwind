# SPDX-License-Identifier: GPL-3.0-only
"""Compact terrain records (world format 0.10, EXPERIMENTAL, build setting terrain_pack compact; tools/chim/terc.py and
engine chim/chim_terc.c): a lossless repack of a TERR record that expands back into the very same bytes.

The builder's own worlds with terrain references (tests/test_chim_format.py's fixture) are written plain and compact
and compared like for like: every compact record expands to the plain world's record byte for byte (Python and the
engine's expander, natively), the validator reads both worlds into the same chunks, every other record is untouched,
and the bytes saved are counted. Every method is checked on its own (planes with exact and negative-zero axial normals
and slanted ones, a uniform light lump, clipnodes and nodes with 16-bit plane numbers), and a record that a method
cannot hold exactly stays as it was. Synthetic data only.
"""
import os
import shutil
import struct
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


def sector_records(out):
    from chim import format as F
    from chim import reach  # noqa: F401 (formats 0.8 to 0.10)
    root = Path(out) / 'chim'
    _, files, _, _ = F.read_index((root / 'world.cwi').read_bytes())
    found = {}
    for f in files:
        if f['kind'] == b'SECT':
            for r in F.read_sector((root / f['path']).read_bytes()):
                found[(r['kind'], r['id'])] = r['data']
    return found


def world_bytes(out):
    return sum(p.stat().st_size for p in (Path(out) / 'chim').rglob('*') if p.is_file())


def ground(x, y):
    return 0.37 * x + 0.21 * y + 9.0 * ((int(x) // 128 + int(y) // 128) % 3)


@unittest.skipIf(np is None, 'numpy is required')
class CompactTerrainWorldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from test_chim_format import fixture
        cls.tmp = tempfile.TemporaryDirectory(prefix='amiwind-terc-')
        t = Path(cls.tmp.name)
        cls.plain, cls.packed = t / 'plain', t / 'packed'
        base = {'grain': 256, 'sector_chunks': 2, 'terrain_refs': 'on'}
        cls.receipt_plain, _ = fixture(cls.plain, heights_of=ground, settings=base)
        cls.receipt_packed, _ = fixture(cls.packed, heights_of=ground, settings=dict(base, terrain_pack='compact'))
        cls.r_plain, cls.r_packed = sector_records(cls.plain), sector_records(cls.packed)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_versions_and_receipt(self):
        from chim import format as F
        from chim import reach  # noqa: F401
        for out, want in ((self.plain, (0, 7)), (self.packed, (0, 10))):
            index = (Path(out) / 'chim/world.cwi').read_bytes()
            self.assertEqual(F.read_header(index)['version'], want)
        info = self.receipt_packed['terrain_pack']
        self.assertGreater(info['compact_records'], 0)
        self.assertNotIn('terrain_pack', self.receipt_plain)

    def test_every_compact_record_expands_to_the_plain_record(self):
        from chim import terc
        self.assertEqual(set(self.r_plain), set(self.r_packed))
        compact = 0
        for key, data in self.r_packed.items():
            if key[0] == b'TERR' and terc.is_compact(data):
                compact += 1
                self.assertEqual(terc.decode(data), self.r_plain[key])
                self.assertLess(len(data), len(self.r_plain[key]))
            elif key[0] != b'CHNK':
                self.assertEqual(data, self.r_plain[key], key)
        self.assertGreater(compact, 0)

    def test_validator_reads_the_same_chunks(self):
        from chim.validate import validate
        fa, wa = validate(self.plain)
        fb, wb = validate(self.packed)
        self.assertEqual(list(fa), [])
        self.assertEqual(list(fb), [])
        for (pa, frame_a, ca), (pb, frame_b, cb) in zip(wa['frames'], wb['frames']):
            for x, y in zip(ca, cb):
                for key in ('owned', 'reach', 'pvs', 'pvl', 'image', 'image_render', 'leaves', 'terrain_record'):
                    self.assertEqual(x.get(key), y.get(key), key)

    def test_bytes_saved(self):
        saved = sum(len(self.r_plain[k]) - len(d) for k, d in self.r_packed.items() if k[0] == b'TERR')
        self.assertEqual(saved, self.receipt_packed['terrain_pack']['bytes_saved'])
        self.assertEqual(world_bytes(self.plain) - world_bytes(self.packed), saved)

    @unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
    @unittest.skipUnless(shutil.which('cc'), 'a C compiler is required')
    def test_engine_expands_every_record_to_the_same_bytes(self):
        from chim import terc
        from test_aga_native_source import NativeSourceTests
        from test_chim_engine_native import WARN
        records = [(d, self.r_plain[k]) for k, d in sorted(self.r_packed.items())
                   if k[0] == b'TERR' and terc.is_compact(d)]
        records.append((synthetic_record(), terc.decode(synthetic_record())))
        with tempfile.TemporaryDirectory(prefix='amiwind-terc-c-') as tmp:
            for n, (packed, image) in enumerate(records):
                (Path(tmp) / ('%d.trc' % n)).write_bytes(packed)
                (Path(tmp) / ('%d.img' % n)).write_bytes(image)
            out = Path(tmp) / 'out.txt'
            NativeSourceTests.compile_run(self, 'aga_chim_terc_test.c',
                                          [SRC / 'chim/chim_format.c', SRC / 'chim/chim_terc.c'],
                                          cflags=[*WARN, '-O1'], arguments=[tmp, str(len(records)), str(out)])
            lines = out.read_text(encoding='ascii').splitlines()
        self.assertEqual(lines, ['%d same' % n for n in range(len(records))] + ['refusals ok'])


def synthetic_record():
    """A brush image whose every method is used, packed: planes with exact, negative-zero and negative axial normals
    and slanted ones, a uniform light lump, clipnodes and nodes with 16-bit plane numbers."""
    from chim import format as F
    from chim import terc
    lumps = [b''] * 15
    planes = [(1.0, 0.0, 0.0, 5.0, 3), (0.0, -1.0, 0.0, -7.5, 3), (-0.0, 0.0, 1.0, 2.0, 2), (0.0, -0.0, -1.0, 1.0, 5),
              (0.6, 0.8, 0.0, 3.0, 3), (0.0, 0.0, 1.0, 0.0, 0)]
    lumps[1] = b''.join(struct.pack('<ffffi', *p) for p in planes)
    lumps[8] = bytes([12]) * 40
    lumps[9] = b''.join(struct.pack('<ihh', k % 6, -1, k) for k in range(5))
    lumps[5] = b''.join(struct.pack('<ihh6hHH', k % 6, 1, -2, -1, -1, -1, 1, 1, 1, 0, 0) for k in range(3))
    lumps[14] = struct.pack('<9f7i', *([0.0] * 9), 0, 0, 0, 0, 0, 0, 0)
    image, _ = F.brush_image(lumps)
    packed = terc.encode(image)
    if packed is None:
        raise AssertionError('the synthetic record was not packed')
    return packed


class CompactTerrainMethodTests(unittest.TestCase):
    def test_methods_are_exact_and_used(self):
        from chim import format as F
        from chim import terc
        packed = synthetic_record()
        image = terc.decode(packed)
        lumps = F.read_brush_image(image)
        methods = {}
        for slot, k in enumerate(F.FILE_ORDER):
            methods[k] = terc.ENTRY.unpack_from(packed, terc.HEAD.size + slot * terc.ENTRY.size)[0]
        self.assertEqual((methods[1], methods[8], methods[9], methods[5]),
                         (terc.PLANES, terc.UNIFORM, terc.CLIPNODES, terc.NODES))
        # every plane comes back bit for bit, negative zeros included
        planes = [(1.0, 0.0, 0.0, 5.0, 3), (0.0, -1.0, 0.0, -7.5, 3), (-0.0, 0.0, 1.0, 2.0, 2), (0.0, -0.0, -1.0, 1.0, 5),
                  (0.6, 0.8, 0.0, 3.0, 3), (0.0, 0.0, 1.0, 0.0, 0)]
        self.assertEqual(lumps[1], b''.join(struct.pack('<ffffi', *p) for p in planes))
        self.assertEqual(lumps[1][40:44], struct.pack('<f', -0.0))
        self.assertEqual(lumps[1][64:68], struct.pack('<f', -0.0))

    def test_what_cannot_be_held_stays_plain(self):
        from chim import format as F
        from chim import terc
        lumps = [b''] * 15
        lumps[9] = struct.pack('<ihh', 70000, -1, -2)          # a plane number past 16 bits: RAW
        lumps[1] = struct.pack('<ffffi', 0.6, 0.8, 0.0, 1.0, 3) * 40
        image, _ = F.brush_image(lumps)
        packed = terc.encode(image)
        if packed is not None:
            self.assertEqual(terc.decode(packed), image)
            slot = F.FILE_ORDER.index(9)
            self.assertEqual(terc.ENTRY.unpack_from(packed, terc.HEAD.size + slot * terc.ENTRY.size)[0], terc.RAW)
        # a record too large for the engine's smallest loading buffer stays a BSP29 image
        lumps[3] = bytes(12 * (terc.EXPAND_ROOM // 12 + 1))
        big, _ = F.brush_image(lumps)
        self.assertIsNone(terc.encode(big))

    def test_option_refusals(self):
        from chim.terc import terrain_pack
        self.assertEqual(terrain_pack({}), 'bsp29')
        self.assertEqual(terrain_pack({'terrain_pack': 'compact', 'terrain_refs': 'on'}), 'compact')
        for bad in ({'terrain_pack': 'compact'}, {'terrain_pack': 'lz4', 'terrain_refs': 'on'}):
            with self.assertRaises(ValueError):
                terrain_pack(bad)

    def test_build_option_passes_through(self):
        import build as B
        args = B.parser().parse_args(['--chim-terrain-pack', 'compact'])
        opts = B.chim_stage_options(args)
        self.assertEqual(opts[opts.index('--terrain-pack') + 1], 'compact')
        # generate by default since v0.0.47; bsp29 passes nothing (the chim stage's own default, the method before);
        # without terrain references the builder keeps bsp29
        default = B.chim_stage_options(B.parser().parse_args([]))
        self.assertEqual(default[default.index('--terrain-pack') + 1], 'generate')
        bsp29 = B.parser().parse_args(['--chim-terrain-pack', 'bsp29'])
        self.assertNotIn('--terrain-pack', B.chim_stage_options(bsp29))
        no_refs = B.parser().parse_args(['--chim-terrain-refs', 'off'])
        self.assertNotIn('--terrain-pack', B.chim_stage_options(no_refs))


class CompactTerrainKeyTests(unittest.TestCase):
    def test_no_unit_kind_or_stair_code_reaches_the_module(self):
        from chim import units
        from chim import collision
        for kind in units.CODE_ENTRIES:
            self.assertNotIn('tools/chim/terc.py', units.TOOLS.get(kind, []), kind)
            key = units.unit_code_key(kind)
            self.assertFalse(any('chim/terc.py' in str(u) for u in key.get('units', key.get('reach', []))), kind)
        self.assertFalse(any('terc.py' in f for f in collision.stair_code_selection()[0]))


if __name__ == '__main__':
    unittest.main()
