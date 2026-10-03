import tempfile
import unittest
from pathlib import Path
from world_volumes import balanced, partition_batches, hardfile_groups

class WorldVolumeLayoutTests(unittest.TestCase):
    def maps(self, root, sizes):
        result = []
        for i, size in enumerate(sizes):
            p = root / f'vf{i:04d}.bsp'
            p.write_bytes(b'x' * size)
            result.append(p)
        return result

    def test_small_layout_preserves_existing_balance(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self.maps(Path(directory), [10] * 6)
            kept, additional = balanced(paths, 20, 100)
            self.assertEqual(partition_batches(paths, 20, 100), (kept, [additional]))

    def test_large_layout_retains_every_map_once_with_bounded_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self.maps(Path(directory), [30] * 10)
            kept, batches = partition_batches(paths, 40, 100)
            self.assertEqual(kept + [p for batch in batches for p in batch], paths)
            self.assertLessEqual(40 + sum(p.stat().st_size for p in kept), 100)
            self.assertTrue(all(sum(p.stat().st_size for p in batch) <= 100 for batch in batches))
            self.assertGreater(len(batches), 1)

    def test_drives_include_header_and_keep_all_partitions(self):
        worlds = [dict(bytes=40000, volume=f'AW_WORLD{i}') for i in range(3)]
        groups = hardfile_groups(40000, worlds, 130000)
        self.assertEqual([p for group in groups for p in group], worlds)
        self.assertEqual(len(groups), 2)
        for i, group in enumerate(groups):
            self.assertLess(32768 + (40000 if i == 0 else 0) + sum(p['bytes'] for p in group), 130000)
        with self.assertRaises(ValueError):
            hardfile_groups(97232, [], 130000)

if __name__ == '__main__':
    unittest.main()
