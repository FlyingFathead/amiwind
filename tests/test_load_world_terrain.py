# SPDX-License-Identifier: GPL-3.0-only
"""BUILD-POOL-TINY-UNITS-48 (CHIM world read): load_world decodes each referenced terrain record once, on the workers.

The parent decoded a generated terrain record (world format 0.11) again for every chunk that references it: 305,568
decodes of 97,369 records on one core, most of the 7.8 minutes the v0.0.48-dev2 chim validation took on 2.1 of 13.8
cores, and the same in every whole-world read (the image step's frame maps). The worker task must give the bytes the
parent gave, and a world read on several workers the same frames as on one. Synthetic data only."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

try:
    import numpy as np  # noqa: F401
except ImportError:  # pragma: no cover - the gate image has it
    np = None


@unittest.skipIf(np is None, 'numpy is required')
class TerrainDecodedOnce(unittest.TestCase):

    def test_the_worker_task_gives_the_parent_s_bytes(self):
        from test_chim_format import fixture
        from test_chim_terc import ground, sector_records
        from chim.validate import _terrain_image, _terrain_records_task
        with tempfile.TemporaryDirectory() as tmp:
            made = Path(tmp) / 'made'
            fixture(made, heights_of=ground, settings={'grain': 256, 'sector_chunks': 2, 'terrain_refs': 'on',
                                                       'terrain_pack': 'generate'})
            datas = [data for key, data in sector_records(made).items() if key[0] == b'TERR']
        self.assertTrue(any(bytes(d[:4]) == b'THG1' for d in datas))
        self.assertEqual(_terrain_records_task(datas), [_terrain_image(d, 0)[0] for d in datas])

    def test_a_world_read_on_workers_equals_one_worker(self):
        from chim.validate import Failures, load_world
        from chim.world import build_frames
        from test_chim_frames import frame_specs
        with tempfile.TemporaryDirectory() as tmp:
            a, b, _ = frame_specs(tmp)
            out = Path(tmp) / 'two'
            build_frames(out, [a, b], {'grain': 256, 'sector_chunks': 2})
            with patch.dict(os.environ, {'AMIWIND_PASS_CACHE': 'off'}):
                one = load_world(out, Failures(), 1)
                three = load_world(out, Failures(), 3)
        self.assertEqual(len(one[5]), 2)
        self.assertEqual(one[5], three[5])
        self.assertEqual(one[4], three[4])
        refs = sum('terrain_record' in c for _, _, chunks in three[5] for c in chunks)
        self.assertEqual(refs, sum('terrain_record' in c for _, _, chunks in one[5] for c in chunks))


if __name__ == '__main__':
    unittest.main()
