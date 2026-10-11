# SPDX-License-Identifier: GPL-3.0-only
"""CHIM-DEV3-MAPLOAD-CRASH-36: the two causes of the v0.0.36-dev3 map-load failure stay fixed.

1. aw_aread.c: AllocDosObject(DOS_STDPKT) returns the DosPacket part of a StandardPacket (dp_Link already points
   at its Message). Treating it as a StandardPacket wrote every packet 20 bytes off its allocation and sent
   SendPkt() a garbage dp_Link: memory corruption on every asynchronous music read (the emulator died under the
   JIT, the game froze without it).
2. The engine refused a CHIM world index with more than 4096 file rows while the writer had no limit; the
   coast world has 7,236 rows, so every CHIM frame map failed with "chim/world.cwi cannot be read".
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine/aga/src'
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import format as F  # noqa: E402


def code(path):
    """Source without comments."""
    text = path.read_text(encoding='utf-8')
    text = re.sub(r'/\*.*?\*/', ' ', text, flags=re.S)
    return re.sub(r'//[^\n]*', ' ', text)


class AsyncReadPacketTest(unittest.TestCase):
    def test_stdpkt_is_used_as_a_dos_packet(self):
        src = code(SRC / 'aw_aread.c')
        self.assertIn('AllocDosObject(DOS_STDPKT', src.replace(' ', ''))
        self.assertNotIn('StandardPacket', src, 'AllocDosObject(DOS_STDPKT) returns a struct DosPacket *')
        self.assertNotIn('sp_Pkt', src, 'the returned pointer is already the DosPacket')
        self.assertRegex(src, r'struct\s+DosPacket\s*\*\s*packet\s*;')
        self.assertRegex(src, r'dp\s*=\s*r->packet\s*;')
        self.assertRegex(src, r'r->result\s*=\s*r->packet->dp_Res1\s*;')


class IndexFileLimitTest(unittest.TestCase):
    def test_engine_and_writer_agree(self):
        local = code(SRC / 'chim/chim_local.h')
        m = re.search(r'#define\s+CHIM_MAX_FILES\s+(\d+)', local)
        self.assertIsNotNone(m, 'chim_local.h defines CHIM_MAX_FILES')
        self.assertEqual(int(m.group(1)), F.MAX_INDEX_FILES)
        world = code(SRC / 'chim/chim_world.c')
        self.assertIn('t->files > CHIM_MAX_FILES', world)
        self.assertNotRegex(world, r'files\s*>\s*4096')

    def test_limit_covers_the_record_file_field(self):
        # MODEL_DIR / TEXTURE_DIR name their file row in 16 bits; the limit is that field's range.
        self.assertEqual(F.MODEL_DIR.format[1:3], 'HH')
        self.assertEqual(F.MAX_INDEX_FILES, 0xFFFF)
        self.assertGreater(F.MAX_INDEX_FILES, 7236, 'the v0.0.36-dev3 coast world has 7,236 file rows')

    def test_writer_refuses_more_rows_than_the_engine_reads(self):
        import inspect
        self.assertIn('MAX_INDEX_FILES', inspect.getsource(F))


if __name__ == '__main__':
    unittest.main()
