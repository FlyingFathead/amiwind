# SPDX-License-Identifier: GPL-3.0-only
"""tools/parallel_json.py: documents whose long lists are encoded on the worker pool are byte for byte what
json.dumps writes (BUILD-CHIM-SERIAL-SECTIONS-44: the CHIM source manifest, receipt and statistics)."""
import json
from pathlib import Path
import random
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import parallel_json  # noqa: E402


def item(rng, depth=0):
    kind = rng.randrange(7 if depth < 3 else 4)
    if kind == 0:
        return rng.randrange(-10 ** 6, 10 ** 6)
    if kind == 1:
        return rng.random() * 1000 - 500
    if kind == 2:
        return rng.choice(['a', 'line\nbreak', 'quote "x"', 'ümlaut', '', 'tab\t'])
    if kind == 3:
        return rng.choice([None, True, False])
    if kind == 4:
        return [item(rng, depth + 1) for _ in range(rng.randrange(4))]
    return {rng.choice(['k', 'z', 'a', 'mid', 'Ä']) + str(n): item(rng, depth + 1) for n in range(rng.randrange(4))}


class ParallelJson(unittest.TestCase):
    def document(self, seed):
        rng = random.Random(seed)
        return {'frames': [item(rng) for _ in range(rng.randrange(0, 700))],
                'files': [],
                'models': {'per_model': [{'id': n, 'name': 'm%d' % n, 'faces': [n, n * 2]} for n in range(300)],
                           'top': [1, 2, 3]},
                'placements': {'rows': [[n, n % 7, 1.5 * n] for n in range(1000)], 'columns': ['a', 'b']},
                'scalar': 3, 'nested': {'deep': {'list': [{'x': [1, {'y': 'z'}]}]}}}

    def test_same_bytes_as_json_dumps(self):
        paths = [('frames',), ('files',), ('models', 'per_model'), ('placements', 'rows'), ('nested', 'deep', 'list'),
                 ('missing',), ('scalar',)]
        for seed in range(6):
            doc = self.document(seed)
            want = json.dumps(doc, indent=1, sort_keys=True)
            with self.subTest(seed=seed):
                self.assertEqual(parallel_json.dumps(doc, paths, jobs=1), want)
                with mock.patch.object(parallel_json, 'BATCH_ITEMS', 7):
                    self.assertEqual(parallel_json.dumps(doc, paths, jobs=1), want)

    def test_on_the_worker_pool(self):
        doc = self.document(11)
        with mock.patch.object(parallel_json, 'BATCH_ITEMS', 50):
            got = parallel_json.dumps(doc, [('frames',), ('placements', 'rows')], jobs=2)
        self.assertEqual(got, json.dumps(doc, indent=1, sort_keys=True))

    def test_other_indents_and_unsorted_keys(self):
        doc = self.document(3)
        for indent in (0, 2, 4):
            for sort_keys in (True, False):
                with self.subTest(indent=indent, sort_keys=sort_keys):
                    self.assertEqual(parallel_json.dumps(doc, [('frames',)], indent=indent, sort_keys=sort_keys),
                                     json.dumps(doc, indent=indent, sort_keys=sort_keys))


if __name__ == '__main__':
    unittest.main()
