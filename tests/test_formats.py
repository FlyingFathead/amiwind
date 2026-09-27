"""Synthetic format checks; no original game assets required."""
import struct
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mwad.audit import BSA, FormatError, decode_heights, decode_materials, records, subrecords, terrain_packet


class Formats(unittest.TestCase):
    def test_record_bounds(self):
        for raw in (b"TES", struct.pack("<4sIII", b"LAND", 42, 0, 0)):
            with self.assertRaises(FormatError):
                list(records(raw))
        with self.assertRaises(FormatError):
            list(subrecords(struct.pack("<4sI", b"VHGT", 42)))

    def test_height_rows_accumulate_separately_from_columns(self):
        d = [0] * 4225
        d[0], d[1], d[65], d[66] = 2, -1, 3, 4
        h = decode_heights(struct.pack("<f4225b3x", 10.0, *d))
        self.assertEqual(h[0][:3], [96, 88, 88])
        self.assertEqual(h[1][:3], [120, 152, 152])
        with self.assertRaises(FormatError):
            decode_heights(b"\0" * 4231)

    def test_material_tiles(self):
        m = decode_materials(struct.pack("<256H", *range(256)))
        self.assertEqual(m[0][:5], [0, 1, 2, 3, 16])
        self.assertEqual(m[4][:5], [64, 65, 66, 67, 80])
        self.assertEqual(m[15][15], 255)

    def test_big_endian_packet_and_negative_world_location(self):
        land = {"heights": [[(y-x)*8 for x in range(65)] for y in range(65)],
                "materials": [[7]*16 for _ in range(16)]}
        packet = terrain_packet(land, -2, -9, 0, 0, 2)
        self.assertEqual(len(packet), 256)
        self.assertEqual(struct.unpack_from(">4sHHiiHHI", packet), (b"MWT0", 1, 9, -8, -36, 256, 8, 226))
        self.assertEqual(struct.unpack_from(">9h", packet, 24), tuple(-x for x in range(0, 17, 2)))
        self.assertEqual(packet[186:250], bytes([7]*64))
        self.assertEqual(packet[250:], bytes(6))

    def test_bsa_offsets_and_overrun(self):
        name = b"meshes\\test.nif\0"
        directory = struct.pack("<III", 3, 0, 0) + name
        raw = struct.pack("<III", 0x100, len(directory), 1) + directory + bytes(8) + b"abc"
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/"test.bsa"
            p.write_bytes(raw)
            self.assertEqual(BSA(p).entries["meshes/test.nif"]["bytes"], 3)
            p.write_bytes(raw[:-1])
            with self.assertRaises(FormatError):
                BSA(p)


if __name__ == "__main__":
    unittest.main()
