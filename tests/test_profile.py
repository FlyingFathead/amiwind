import importlib.util
from pathlib import Path
import struct
import unittest

spec = importlib.util.spec_from_file_location('profile_demo', Path(__file__).resolve().parents[1] / 'tools/profile_demo.py')
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)


class ProfileTests(unittest.TestCase):
    def fixture(self):
        p = bytearray(832)
        struct.pack_into('>4sHHII', p, 0, b'MWP1', 1, 50, 1, 1500)
        struct.pack_into('>12I', p, 16, 10, 50, 0, 0, 3, 10, 30, 0, 0, 1, 5, 0)
        struct.pack_into('>I', p, 64 + 10 * 4, 3)
        struct.pack_into('>I', p, 320 + 5 * 4, 10)
        return p

    def test_native_big_endian_metrics(self):
        r = profile.decode(self.fixture())
        self.assertEqual(r['solid_fps'], 10)
        self.assertEqual(r['solid_p95_ms'], 100)
        self.assertEqual(r['read_p95_ms'], 200)
        self.assertEqual(r['stream_bytes'], 49152)
        self.assertIsNone(r['wire_fps'])

    def test_corrupt_profile_rejected(self):
        good = self.fixture()
        for p in [good[:-1], b'NOPE' + good[4:], good[:64] + bytes(768)]:
            with self.assertRaises(ValueError):
                profile.decode(p)
