# SPDX-License-Identifier: GPL-3.0-only
"""Payload hashing on threads (tools/parallel_hash.py, BUILD-IMAGE-HASH-UNDERUSED-36): the digests are
exactly hashlib's over every byte, in input order, whatever the sizes, batches, thread counts or method."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))

import build_jobs  # noqa: E402
import build_parallel  # noqa: E402
import parallel_hash  # noqa: E402


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ParallelHashTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        sizes = [0, 1, 2047, 2048, 65536, parallel_hash.SMALL_BYTES, parallel_hash.SMALL_BYTES + 1,
                 parallel_hash.BUFFER_BYTES + 3, 3 * 1024 * 1024] + [1000 + 37 * i for i in range(60)]
        self.paths = []
        for index, size in enumerate(sizes):
            path = self.root / f'{index:03d}.bin'
            path.write_bytes(os.urandom(size))
            self.paths.append(path)

    def tearDown(self):
        self.temp.cleanup()

    def test_digests_equal_hashlib_in_input_order_for_every_job_count(self):
        expected = [digest(path) for path in self.paths]
        shuffled = list(reversed(self.paths))
        for jobs in (1, 2, 3, 8, 24, 64):
            with self.subTest(jobs=jobs):
                self.assertEqual(parallel_hash.hash_files(self.paths, jobs), expected)
                self.assertEqual(parallel_hash.hash_files(shuffled, jobs), list(reversed(expected)))

    def test_builder_entry_points_default_to_threads_and_keep_the_process_method(self):
        expected = [digest(path) for path in self.paths]
        os.environ.pop('AMIWIND_HASH_METHOD', None)
        with mock.patch.object(build_parallel, 'process_pool', side_effect=AssertionError('no processes')):
            self.assertEqual(build_parallel.hash_files(self.paths, 8), expected)
        with mock.patch.dict(os.environ, {'AMIWIND_HASH_METHOD': 'process'}):
            self.assertEqual(build_parallel.hash_files(self.paths, 2), expected)
            self.assertEqual(build_parallel.hash_existing(self.paths[:3] + [self.root / 'missing'], 2),
                             expected[:3] + [None])

    def test_hash_existing_gives_none_for_missing_and_directories(self):
        listed = self.paths[:2] + [self.root / 'missing.bin', self.root] + self.paths[2:]
        result = parallel_hash.hash_existing(listed, 6)
        self.assertEqual(result, [digest(self.paths[0]), digest(self.paths[1]), None, None]
                         + [digest(path) for path in self.paths[2:]])
        self.assertEqual(build_parallel.hash_existing(listed, 6), result)

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            parallel_hash.hash_files(self.paths + [self.root / 'missing.bin'], 4)
        with self.assertRaises(FileNotFoundError):
            parallel_hash.hash_files([self.root / 'missing.bin'], 1)

    def test_size_is_only_a_hint(self):
        # a file that grew after it was measured is still hashed to its end (no trust in stat)
        path = self.paths[3]
        grown = path.read_bytes() + os.urandom(parallel_hash.SMALL_BYTES * 2)
        path.write_bytes(grown)
        self.assertEqual(parallel_hash.sha256_file(path, 10), hashlib.sha256(grown).hexdigest())
        self.assertEqual(parallel_hash.sha256_file(path, None), hashlib.sha256(grown).hexdigest())
        self.assertEqual(parallel_hash.sha256_file(self.paths[0], 0), hashlib.sha256(b'').hexdigest())

    def test_batches_cover_every_file_once_small_lane_first_then_largest(self):
        sizes = [10, 5 << 20, 300 << 10, 7, 90 << 20, 1 << 20, 0, 600 << 10]
        groups = parallel_hash.batches(sizes, 4)
        self.assertEqual(sorted(index for group in groups for index in group), list(range(len(sizes))))
        small = [index for index, size in enumerate(sizes) if size <= parallel_hash.SMALL_BYTES]
        self.assertEqual(groups[0], small)
        big = [group for group in groups[1:]]
        self.assertEqual(big[0], [4])                      # the 90 MiB file first, alone
        totals = [sum(sizes[index] for index in group) for group in big]
        self.assertEqual(totals[:2], sorted(totals[:2], reverse=True))

    def test_explicit_jobs_reach_the_threads_uncapped(self):
        sizes = [400 << 10] * 200
        with mock.patch.object(build_jobs, 'usable_cpus', return_value=2):
            threads, groups = parallel_hash.plan(sizes, 32)
        self.assertEqual(threads, 32)
        self.assertGreaterEqual(len(groups), 32)
        self.assertEqual(parallel_hash.plan([10] * 3, 32), (1, None))       # tiny lists: in the caller
        self.assertEqual(parallel_hash.plan(sizes, 1), (1, None))

    def test_profile_section_counts_files(self):
        with tempfile.TemporaryDirectory() as temp:
            sections = Path(temp) / 'sections.jsonl'
            with mock.patch.dict(os.environ, {'AMIWIND_PROFILE_SECTIONS': str(sections)}):
                parallel_hash.hash_files(self.paths, 4)
            rows = [json.loads(line) for line in sections.read_text().splitlines()]
        named = [row for row in rows if row['name'] == 'parallel hash: sha256']
        self.assertEqual(len(named), 1)
        self.assertEqual(named[0]['items'], len(self.paths))
        self.assertEqual(named[0]['bytes'], sum(path.stat().st_size for path in self.paths))


if __name__ == '__main__':
    unittest.main()
