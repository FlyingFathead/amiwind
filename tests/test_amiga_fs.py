"""Legacy filesystem regression: preserve payload, bitmap state and checksums."""
import struct
import sys
import unittest
import tempfile
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from amiga_fs import legacy_root, check_payload_names


def root(marker=0, bitmap=0xffffffff):
    words=[0]*128
    words[0]=2; words[3]=72; words[-1]=1
    words[78]=bitmap; words[79]=123; words[-4]=marker
    words[5]=(-sum(words))&0xffffffff
    return struct.pack('>128I',*words)


class LegacyRootTests(unittest.TestCase):
    def test_payload_names_reject_long_names_and_case_collisions(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory/'doors-bmhlaalucouncil.txt').touch()
            check_payload_names(directory)
            bad = directory/'scene-doors-bmhlaalucouncil.txt'
            bad.touch()
            with self.assertRaisesRegex(ValueError, '30 bytes'):
                check_payload_names(directory)
            bad.unlink()
            # Model a foreign case-sensitive source inventory even when the
            # host filesystem merges names differing only in case.
            entries=[directory/'doors-bmhlaalucouncil.txt', directory/'DOORS-bmhlaalucouncil.txt']
            with patch.object(Path, 'rglob', return_value=entries), \
                 self.assertRaisesRegex(ValueError, 'collision'):
                check_payload_names(directory)

    def test_modern_marker_is_rejected_until_normalized(self):
        for dos in range(0x444f5300,0x444f5304):
            before=root(dos, bitmap=0)
            with self.assertRaisesRegex(ValueError, 'DOS marker'):
                legacy_root(before,dos)
            after=legacy_root(before,dos,True)
            self.assertEqual(after,root(0,bitmap=0))
            self.assertEqual(legacy_root(after,dos),after)
            self.assertEqual(sum(struct.unpack('>128I',after))&0xffffffff,0)

    def test_valid_legacy_root_is_unchanged(self):
        self.assertEqual(legacy_root(root(),0x444f5301,True),root())

    def test_unknown_corruption_and_modern_formats_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'Unknown root'):
            legacy_root(root(1234),0x444f5301,True)
        damaged=bytearray(root());damaged[40]=1
        with self.assertRaisesRegex(ValueError,'checksum'):
            legacy_root(damaged,0x444f5301,True)
        with self.assertRaisesRegex(ValueError,'DOS0..3'):
            legacy_root(root(),0x444f5306,True)
