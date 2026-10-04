"""Asset-free contracts for the original-cloud conversion boundary."""
from pathlib import Path
import sys
import unittest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from build_shared_sky_clouds import build_cloud_sky, FORBIDDEN, SECONDARY_TONES


class SharedSkyCloudTests(unittest.TestCase):
    palette = bytes(c for i in range(256) for c in (i, i, i))

    def test_transparency_survives_zero_cutoff(self):
        raw, _ = build_cloud_sky(Image.new('RGBA', (8, 8), (255, 255, 255, 0)),
                                self.palette, alpha_cutoff=0)
        self.assertEqual(len(raw), 32768)
        self.assertTrue(all(raw[y * 256:y * 256 + 128] == bytes(128) for y in range(128)))
        self.assertTrue(all(raw[y * 256 + 128:(y + 1) * 256] == bytes([224]) * 128 for y in range(128)))

    def test_both_layers_use_disjoint_runtime_roles(self):
        first = Image.new('RGBA', (128, 128))
        second = Image.new('RGBA', (128, 128))
        for x in range(128):
            for y in range(128):
                first.putpixel((x, y), (250, 30, 70, x * 2))
                second.putpixel((x, y), (0, 200, 255, y * 2))
        raw, report = build_cloud_sky(first, self.palette, secondary=second)
        left = set(raw[y * 256 + x] for y in range(128) for x in range(128))
        right = set(raw[y * 256 + x + 128] for y in range(128) for x in range(128))
        self.assertFalse((left - {0}) & FORBIDDEN)
        self.assertEqual(right, {224, *SECONDARY_TONES})
        self.assertFalse(left & right)
        self.assertGreater(report['secondary_cloud_pixels'], 0)
        self.assertLess(report['secondary_cloud_pixels'], 16384)
        self.assertEqual(raw, build_cloud_sky(first, self.palette, secondary=second)[0])

    def test_invalid_inputs_fail(self):
        image = Image.new('RGBA', (1, 1), (255, 255, 255, 255))
        with self.assertRaises(ValueError):
            build_cloud_sky(image, bytes(767))
        for kwargs in ({'alpha_cutoff': 255}, {'contrast': 0}, {'secondary_cutoff': -1}):
            with self.assertRaises(ValueError):
                build_cloud_sky(image, self.palette, **kwargs)


if __name__ == '__main__':
    unittest.main()
