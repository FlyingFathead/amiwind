# SPDX-License-Identifier: GPL-3.0-only
"""BUILD-POOL-TINY-UNITS-48 (chim-town stages): frame_world without a loaded world reads only the asked frame.

The chim-town stages need one frame's collision; frame_world read and checked the whole CHIM world for it, about 110 s
on 2.5 of 8-12 cores per stage in the v0.0.48-dev2 build (most of it one core decoding every frame's terrain). The
frame read alone (chim.frame_map.frame_alone, through chim.validate.load_frame) must give the same frame row, the same
models and the same collision scene as the whole-world read. Synthetic data only."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim.collision import FrameScene  # noqa: E402
from chim.frame_map import frame_world, load  # noqa: E402
from chim.world import build_frames  # noqa: E402
from test_chim_frames import frame_specs  # noqa: E402


class FrameAlone(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        a, b, _ = frame_specs(cls.tmp.name)
        cls.out = Path(cls.tmp.name) / 'two'
        build_frames(cls.out, [a, b], {'grain': 256, 'sector_chunks': 2})
        cls.world = load(cls.out)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_the_frame_alone_equals_the_whole_world_read(self):
        self.assertEqual(len(self.world['frames']), 2)
        for path, frame, chunks in self.world['frames']:
            cell = tuple(frame['cell'])
            whole, wi = frame_world(self.out, cell, world=self.world)
            alone, ai = frame_world(self.out, cell)
            self.assertEqual(ai, wi)
            self.assertEqual(alone['frames'][ai], whole['frames'][wi])
            used = {r['model'] for c in chunks for r in c['owned'] + c['reach']}
            self.assertEqual(set(alone['models']), used)
            for i in used:
                self.assertEqual(alone['models'][i], whole['models'][i])
            for hull in (0, 1):
                a, b = FrameScene(alone, ai, hull=hull), FrameScene(whole, wi, hull=hull)
                self.assertEqual((a.planes, a.nodes, a.brushes, a.boxes, a.chunk_roots),
                                 (b.planes, b.nodes, b.brushes, b.boxes, b.chunk_roots))

    def test_a_generated_terrain_world_reads_alone(self):
        """World format 0.11 (generated terrain records, the builder's default pack): the frame alone reads it as the
        whole-world read does (the dev2 measurement first stopped here on the format check)."""
        from test_chim_format import fixture
        from test_chim_terc import ground
        with tempfile.TemporaryDirectory() as tmp:
            made = Path(tmp) / 'made'
            fixture(made, heights_of=ground, settings={'grain': 256, 'sector_chunks': 2, 'terrain_refs': 'on',
                                                       'terrain_pack': 'generate'})
            world = load(made)
            _, frame, _ = world['frames'][0]
            alone, ai = frame_world(made, tuple(frame['cell']))
            whole, wi = frame_world(made, tuple(frame['cell']), world=world)
            self.assertEqual(alone['frames'][ai], whole['frames'][wi])

    def test_a_damaged_frame_file_is_refused(self):
        path, frame, _ = self.world['frames'][0]
        target = self.out / 'chim' / path
        raw = target.read_bytes()
        try:
            target.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
            with self.assertRaises(ValueError) as caught:
                frame_world(self.out, tuple(frame['cell']))
            self.assertIn('CRC', str(caught.exception))
        finally:
            target.write_bytes(raw)

    def test_an_unknown_cell_is_refused(self):
        with self.assertRaises(StopIteration):
            frame_world(self.out, (999, 999))


if __name__ == '__main__':
    unittest.main()
