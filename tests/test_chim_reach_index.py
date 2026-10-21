# SPDX-License-Identifier: GPL-3.0-only
"""CHIM world format 0.9 (EXPERIMENTAL, build setting reach_index refs; tools/chim/reach.py): a placement record is
stored once per frame, and a chunk that its drawn box reaches but does not own holds a 4-byte reference to it.

The synthetic placements of tests/test_chim_placed_format.py (box meshes, tilted, yawed, scaled; several of them
across chunk edges) are built through the real CHIM units into a 0.8 world and a 0.9 world, then compared like for
like: the records every chunk holds once the references are resolved, every other record byte for byte, the bytes
saved, the validator on both, the readers that take owned records only (chim.cuts, chim.far). The engine side (the
catalogue of every loaded chunk, the placed collision) is compared in tests/test_chim_engine_native.py. Synthetic data
only.
"""
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

try:
    import numpy as np
except ImportError:  # pragma: no cover - the gate image has it
    np = None

REFS_ON = {'reach_index': 'refs'}
COMPARED = ('owned', 'reach', 'pvs', 'pvl', 'image', 'image_render', 'leaves', 'cx', 'cy', 'index', 'sector')


def records_by_kind(out):
    """{(file path, kind, id): record bytes} of every sector record of a written world, and the index bytes."""
    from chim import format as F
    from chim import reach  # noqa: F401 (format 0.9 headers)
    root = Path(out) / 'chim'
    index = (root / 'world.cwi').read_bytes()
    _, files, _, _ = F.read_index(index)
    out_rows = {}
    for f in files:
        if f['kind'] != b'SECT':
            continue
        for r in F.read_sector((root / f['path']).read_bytes()):
            out_rows[(f['path'], r['kind'], r['id'])] = r['data']
    return out_rows, index


@unittest.skipIf(np is None, 'numpy is required')
class ReachIndexBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from test_chim_placed_format import build
        cls.tmp = tempfile.TemporaryDirectory(prefix='amiwind-reach-index-')
        t = Path(cls.tmp.name)
        cls.out08, cls.out09 = t / 'w08', t / 'w09'
        cls.receipt08 = build(cls.out08, '0.8')
        cls.receipt09 = build(cls.out09, '0.8', REFS_ON)
        # tiled large models (chim.cut by tiles) and terrain references (CHK3)
        cls.out08t, cls.out09t = t / 'w08t', t / 'w09t'
        build(cls.out08t, '0.8', {'cut_models_over': 128, 'terrain_refs': 'on'})
        build(cls.out09t, '0.8', {'cut_models_over': 128, 'terrain_refs': 'on', **REFS_ON})

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def frames(self, out):
        from chim.validate import Failures, load_world
        fails = Failures()
        frames = load_world(out, fails)[5]
        self.assertEqual(list(fails), [], out.name)
        return frames

    def test_world_versions_and_receipts(self):
        from chim import format as F
        for out, want in ((self.out08, (0, 8)), (self.out09, (0, 9)), (self.out09t, (0, 9))):
            self.assertEqual(F.read_header(records_by_kind(out)[1])['version'], want, out.name)
        self.assertNotIn('reach_index', self.receipt08)
        n = self.receipt09['reach_copies']
        self.assertGreater(n, 0)
        self.assertEqual(self.receipt09['reach_index'], {'references': n, 'reference_bytes': 4 * n,
                                                          'copy_bytes': 56 * n})
        self.assertEqual(self.receipt08['reach_copies'], n)

    def test_09_worlds_validate(self):
        from chim.validate import validate
        for out in (self.out08, self.out09, self.out08t, self.out09t):
            fails, _ = validate(out)
            self.assertEqual(list(fails), [], out.name)

    def test_09_chunks_hold_the_08_records(self):
        """Resolved, every 0.9 chunk holds exactly the 0.8 chunk's owned records and reach records (the same values,
        in the same order), the same PVS and placement rows and the same terrain."""
        for a, b in ((self.out08, self.out09), (self.out08t, self.out09t)):
            fa, fb = self.frames(a), self.frames(b)
            self.assertEqual(len(fa), len(fb))
            reach = 0
            for (pa, frame_a, ca), (pb, frame_b, cb) in zip(fa, fb):
                self.assertEqual(pa, pb)
                self.assertEqual(frame_a, frame_b)
                self.assertEqual(len(ca), len(cb))
                for x, y in zip(ca, cb):
                    for key in COMPARED:
                        self.assertEqual(x[key], y[key], (b.name, x['index'], key))
                    self.assertNotIn('reach_refs', x)
                    self.assertEqual(len(y['reach_refs']), len(y['reach']))
                    reach += len(y['reach'])
            self.assertGreater(reach, 0, b.name)

    def test_09_raw_references(self):
        """A 0.9 chunk record: magic CHK2 (CHK3 with a terrain reference), the head's reach count, 4-byte references
        in placement id order that name records their owner chunk owns."""
        from chim import reach as RI
        from chim import format as F
        for out in (self.out09, self.out09t):
            rows, _ = records_by_kind(out)
            chunks = {k[2]: v for k, v in rows.items() if k[1] == b'CHNK'}
            magics = {v[:4] for v in chunks.values()}
            self.assertEqual(magics, {b'CHK3'} if out is self.out09t else {b'CHK2'})
            parts = {i: RI.read_chunk(v) for i, v in chunks.items()}
            for i, p in parts.items():
                for owner, k in p['reach_refs']:
                    self.assertNotEqual(owner, i)
                    self.assertLess(k, len(parts[owner]['owned']))
                    self.assertEqual(parts[owner]['owned'][k]['owner'], owner)
                head = F.CHUNK_HEAD.unpack_from(chunks[i])
                self.assertEqual(head[2], len(p['reach_refs']))
                self.assertEqual(head[8], 56)

    def test_09_bytes(self):
        """Every model, texture and terrain record is byte-identical; each chunk record is shorter by 52 bytes per
        reach entry (a 56-byte copy against a 4-byte reference); nothing else changes."""
        for a, b in ((self.out08, self.out09), (self.out08t, self.out09t)):
            ra, ia = records_by_kind(a)
            rb, ib = records_by_kind(b)
            self.assertEqual(set(ra), set(rb))
            saved = 0
            for key, data in ra.items():
                if key[1] != b'CHNK':
                    self.assertEqual(data, rb[key], key)
                    continue
                n_reach = struct.unpack_from('>H', data, 6)[0]
                self.assertEqual(len(data) - len(rb[key]), 52 * n_reach, key)
                saved += 52 * n_reach
            self.assertGreater(saved, 0)
            size = lambda out: sum(p.stat().st_size for p in (Path(out) / 'chim').rglob('*') if p.is_file())  # noqa
            self.assertEqual(size(a) - size(b), saved)

    def test_owned_only_readers(self):
        """chim.cuts.frame_placements and chim.far.frame_boxes read the same owned records from a 0.9 world."""
        from chim.cuts import frame_placements
        from chim.far import frame_boxes
        for a, b in ((self.out08, self.out09), (self.out08t, self.out09t)):
            fa = sorted((Path(a) / 'chim').rglob('frame.ccf'))
            fb = sorted((Path(b) / 'chim').rglob('frame.ccf'))
            for x, y in zip(fa, fb):
                self.assertEqual(frame_placements(x)[1], frame_placements(y)[1])
                self.assertEqual(frame_boxes(x), frame_boxes(y))

    def test_load_frame_resolves(self):
        from chim.validate import load_frame
        for a, b in ((self.out08, self.out09), (self.out08t, self.out09t)):
            (pa, fa, ca), ma = load_frame(a, 0)
            (pb, fb, cb), mb = load_frame(b, 0)
            self.assertEqual(set(ma), set(mb))
            for x, y in zip(ca, cb):
                for key in COMPARED:
                    self.assertEqual(x[key], y[key], key)


class ReachIndexOptionTests(unittest.TestCase):
    def test_modes_and_refusals(self):
        from chim.reach import reach_mode
        self.assertEqual(reach_mode({}), 'copies')
        self.assertEqual(reach_mode({'reach_index': 'copies'}), 'copies')
        self.assertEqual(reach_mode({'reach_index': 'refs', 'placement_format': '0.8'}), 'refs')
        with self.assertRaises(ValueError):
            reach_mode({'reach_index': 'refs'})            # the records of 0.7 have no reference form
        with self.assertRaises(ValueError):
            reach_mode({'reach_index': 'pages', 'placement_format': '0.8'})

    @unittest.skipIf(np is None, 'numpy is required')
    def test_world_refuses_refs_without_08(self):
        from test_chim_placed_format import build
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                build(Path(tmp) / 'x', None, REFS_ON)

    def test_resolve_refuses_bad_references(self):
        from chim.reach import resolve_frame
        rec = {'pid': 5, 'owner': 0}
        good = [{'index': 0, 'owned': [rec]}, {'index': 1, 'owned': [], 'reach_refs': [(0, 0)]}]
        self.assertEqual(resolve_frame(good)[1]['reach'], [rec])
        for refs in ([(0, 1)], [(1, 0)], [(7, 0)]):
            with self.assertRaises(ValueError):
                resolve_frame([{'index': 0, 'owned': [rec]}, {'index': 1, 'owned': [], 'reach_refs': refs}])
        with self.assertRaises(ValueError):          # a record owned by another chunk than the one named
            resolve_frame([{'index': 0, 'owned': [{'pid': 5, 'owner': 3}]},
                           {'index': 1, 'owned': [], 'reach_refs': [(0, 0)]}])

    def test_build_options_pass_through(self):
        sys.path.insert(0, str(ROOT / 'tools'))
        import build as B
        args = B.parser().parse_args(['--chim-placement-format', '0.8', '--chim-reach-index', 'refs'])
        opts = B.chim_stage_options(args)
        self.assertIn('--reach-index', opts)
        self.assertEqual(opts[opts.index('--reach-index') + 1], 'refs')
        self.assertNotIn('--reach-index', B.chim_stage_options(B.parser().parse_args([])))


class ReachIndexKeyTests(unittest.TestCase):
    def test_default_kinds_never_reach_the_09_module(self):
        """No unit kind (default or 0.8) reaches chim.reach: the 0.9 references are written by the pack after every
        unit, so every unit key stays as it was."""
        from chim import units
        for kind in units.CODE_ENTRIES:
            self.assertNotIn('tools/chim/reach.py', units.TOOLS.get(kind, []), kind)
            key = units.unit_code_key(kind)
            self.assertFalse(any('chim/reach.py' in str(u) for u in key.get('units', key.get('reach', []))), kind)

    def test_stair_walk_code_never_reaches_the_09_module(self):
        from chim import collision
        sel, _ = collision.stair_code_selection()
        self.assertFalse(any('reach.py' in f for f in sel))


if __name__ == '__main__':
    unittest.main()
