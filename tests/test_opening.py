"""Independent examples for the native display packing and memory gate."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("opening_builder", Path(__file__).resolve().parents[1] / "tools/build_opening.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class OpeningTests(unittest.TestCase):
    def test_plane_order_and_pixel_order(self):
        pixels = bytearray(64000)
        pixels[:8] = bytes([1, 2, 4, 8, 15, 0, 0, 0])
        pixels[-1] = 15
        packed = builder.planar_bytes(pixels)
        self.assertEqual(len(packed), 32000)
        self.assertEqual([packed[p * 8000] for p in range(4)], [0x88, 0x48, 0x28, 0x18])
        self.assertEqual([packed[(p + 1) * 8000 - 1] for p in range(4)], [1, 1, 1, 1])

    def test_rejects_non_ocs_indices(self):
        with self.assertRaises(ValueError):
            builder.planar_bytes(bytes([16]) * 64000)

    def test_chip_hunk_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "test"
            p.write_bytes(struct.pack(">7I", 1011, 0, 2, 0, 1, 100, 0x40000000 | 64000))
            result = builder.hunk_memory(p)
            self.assertEqual(result["chip_hunks_bytes"], 256000)
            self.assertEqual(result["all_hunks_bytes"], 256400)
            p.write_bytes(struct.pack(">6I", 1011, 0, 1, 0, 0, 0x40000000 | 100000))
            with self.assertRaises(ValueError):
                builder.hunk_memory(p)

    def test_single_colour_image_keeps_sixteen_palette_slots(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            Image.new("RGB", (640, 400), "black").save(p / "input.png")
            palette = builder.prepare_scene(p / "input.png", p, 0)
            self.assertEqual(len(palette), 16)
            self.assertTrue(all(0 <= c <= 4095 for c in palette))
            self.assertEqual((p / "scene-0.planes").stat().st_size, 32000)


if __name__ == "__main__":
    unittest.main()
