"""Lossless storage sharing preserves independently read lighting and PVS."""
import struct
import unittest
from player_hull import lumps, pack_lumps
from deduplicate_bsp import deduplicate, visibility_row


class DeduplicateBSPTests(unittest.TestCase):
    def fixture(self):
        data=[bytearray() for _ in range(15)]
        data[3]=b''.join(struct.pack('<3f',*p) for p in [(0,0,0),(16,0,0),(0,16,0)])
        data[12]=b''.join(struct.pack('<HH',*e) for e in [(0,1),(1,2),(2,0)])
        data[13]=struct.pack('<3i',0,1,2)
        data[6]=struct.pack('<8f2i',1,0,0,0,0,1,0,0,0,0)
        data[7]=b''.join(struct.pack('<Hhihh4Bi',0,0,0,3,0,0,255,255,255,o) for o in (0,4))
        data[8]=bytes([12,13,14,15])*2
        data[4]=b'\x03\x03'
        data[10]=b''.join(struct.pack('<ii6h2H4B',-1,o,*([0]*12)) for o in (-1,0,1))
        data[14]=bytearray(64);struct.pack_into('<i',data[14],52,2)
        return pack_lumps(data)

    def test_shared_offsets_preserve_each_consumers_bytes(self):
        raw=self.fixture();result,report=deduplicate(raw)
        before=lumps(raw);after=lumps(result)
        self.assertLess(len(result),len(raw))
        self.assertEqual(after[8],bytes([12,13,14,15]))
        for index in range(2):
            old=struct.unpack_from('<i',before[7],index*20+16)[0]
            new=struct.unpack_from('<i',after[7],index*20+16)[0]
            self.assertEqual(before[8][old:old+4],after[8][new:new+4])
        for index in (1,2):
            old=struct.unpack_from('<i',before[10],index*28+4)[0]
            new=struct.unpack_from('<i',after[10],index*28+4)[0]
            self.assertEqual(before[4][old],after[4][new])
        for i in set(range(15))-{4,7,8,10}:self.assertEqual(before[i],after[i])
        self.assertEqual(deduplicate(result)[0],result)

    def test_bad_visibility_and_lightmap_bounds_are_rejected(self):
        for raw in (b'\0',b'\0\0',b'\0\2'):
            with self.assertRaises(ValueError):visibility_row(raw,0,1)
        data=lumps(self.fixture());data[8]=data[8][:-1]
        with self.assertRaisesRegex(ValueError,'Lightmap sample bounds'):deduplicate(pack_lumps(data))


if __name__=='__main__':unittest.main()
