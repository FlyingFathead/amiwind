# SPDX-License-Identifier: GPL-3.0-only
"""CHIM read cost model and the awbench seek mode it is fitted from (no game data)."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim.readcost import (DEFAULT, EXT_BYTES, compare_replay, crossing_ms, features, fit, fit_replay,  # noqa: E402
                           merge_runs, parse, parse_replay)


def line(pattern, gap, size, us_per_request, open_us=500, request=16384, requests=24):
    return ('AWBENCH seek pattern=%s gap=%d file_bytes=%d requests=%d request=%d us=%d us_per_request=%d '
            'useful_mb_per_s=1.000 open_us=%d cpu_free_pct=50.0' % (pattern, gap, size, requests, request,
                                                                     us_per_request * requests, us_per_request,
                                                                     open_us))


def report(size, seq_us, ext_us):
    """A synthetic seek report: skips up to 64 KiB cost a plain request, longer ones one step per 36 KiB."""
    rows = [line('skip', 0, size, seq_us)]
    for gap in (4096, 16384, 65536, 262144, 1048576):
        cost = seq_us if gap <= 65536 else seq_us + int(ext_us * gap / EXT_BYTES)
        rows.append(line('skip', gap, size, cost))
    for gap in (4096, 16384, 65536):
        rows.append(line('through', gap, size, seq_us * 2))
    rows.append(line('random', 0, size, seq_us + int(ext_us * size / 2 / EXT_BYTES)))
    return 'AWBENCH start version=2\n' + '\n'.join(rows) + '\nAWBENCH end\n'


class ReadCostTests(unittest.TestCase):
    def test_fit_recovers_the_constants(self):
        rows = parse(report(8 << 20, 720, 250)) + parse(report(128 << 20, 720, 250))
        cost = fit(rows)
        self.assertAlmostEqual(cost['seq_ms_per_kib'], 0.720 / 16, places=4)
        self.assertAlmostEqual(cost['ext_ms'], 0.250, delta=0.005)
        self.assertEqual(cost['skip_free_bytes'], 65536)
        self.assertEqual(cost['open_ms'], 0.5)

    def test_reports_without_far_seeks_are_refused(self):
        with self.assertRaisesRegex(ValueError, 'far-seek'):
            fit(parse(line('skip', 0, 8 << 20, 700)))
        with self.assertRaisesRegex(ValueError, 'No AWBENCH'):
            fit([])

    def test_runs_join_over_free_forward_gaps_only(self):
        ranges = [('a', 0, 100), ('a', 60000, 61000), ('a', 200000, 201000), ('b', 0, 10)]
        runs = merge_runs(ranges, 65536)
        self.assertEqual([(r[0], r[1], r[2], r[3]) for r in runs],
                         [('a', 0, 61000, 2), ('a', 200000, 201000, 1), ('b', 0, 10, 1)])
        self.assertEqual(len(merge_runs(ranges, 0)), 4)

    def test_crossing_cost_grows_with_the_offset_walked(self):
        near = crossing_ms([('a', 0, 16384, 1)], DEFAULT)
        far = crossing_ms([('a', 64 * EXT_BYTES, 64 * EXT_BYTES + 16384, 1)], DEFAULT)
        self.assertAlmostEqual(far - near, 64 * DEFAULT['ext_ms'], places=6)
        two_files = crossing_ms([('a', 0, 16384, 1), ('b', 0, 16384, 1)], DEFAULT)
        self.assertAlmostEqual(two_files - near, near, places=6)

    def test_replay_report_is_compared_and_fitted(self):
        cost = dict(seq_ms_per_kib=0.02, ext_ms=0.1, open_ms=1.0, request_ms=0.5, skip_free_bytes=65536)
        rows, lines = [], ['AWBENCH replay list=PROBE:x runs=9']
        for k in range(1, 40):
            runs = [['s%02d' % (k % 7), (k % 5) * EXT_BYTES, (k % 5) * EXT_BYTES + 1024 * (10 + 7 * k), 1]]
            if k % 3:
                runs.append(['s%02d' % (k % 4 + 10), 0, 2048 * k, 1])
            if k % 4 == 0:             # a second run in the first file: runs and files differ
                end = runs[0][2]
                runs.append([runs[0][0], end + 200000, end + 210000, 1])
            f = features(runs)
            ms = crossing_ms(runs, cost)
            self.assertAlmostEqual(ms, f['kib'] * 0.02 + f['ext_blocks'] * 0.1 + f['files'] + f['runs'] * 0.5, places=3)
            rows.append(dict(f, crossing=k, estimated_ms=round(ms * 2, 3)))     # an estimate twice too high
            lines.append('AWBENCH replay crossing=%d runs=%d files=%d bytes=%d us=%d' % (
                k, f['runs'], f['files'], f['bytes'], round(ms * 1000)))
        lines.append('AWBENCH replay crossing=40 runs=1 files=1 bytes=5 us=99 incomplete=1')
        measured = parse_replay('\n'.join(lines))
        self.assertNotIn(40, measured)
        result = compare_replay(measured, rows)
        self.assertAlmostEqual(result['scale'], 0.5, places=2)
        self.assertAlmostEqual(result['ratio_p50'], 0.5, places=2)
        fitted = fit_replay(measured, rows)
        for key in ('seq_ms_per_kib', 'ext_ms', 'open_ms', 'request_ms'):
            self.assertAlmostEqual(fitted[key], cost[key], places=2)
        self.assertGreater(fitted['r2'], 0.99)

    def test_awbench_has_the_seek_mode_and_the_guide_documents_it(self):
        source = (ROOT / 'engine/aga/bench/awbench.c').read_text(encoding='utf-8')
        self.assertIn('awbench seek FILE [N]', source)
        for pattern in ('"skip"', '"through"', '"random"'):
            self.assertIn(pattern, source)
        # the report line the cost model parses
        self.assertTrue(re.search(r'AWBENCH seek pattern=%s gap=%lu file_bytes=%lu requests=%lu request=%lu us=%lu '
                                  r'us_per_request=%lu', source))
        self.assertIn('awbench replay LIST', source)
        self.assertIn('awbench buffers DRIVE N', source)
        # the mount entry's buffer count does not follow AddBuffers; the file system's own count does
        self.assertIn('AddBuffers((STRPTR)drive, 0)', source)
        self.assertNotIn('DE_NUMBUFFERS', source[source.index('static void set_buffers'):])
        self.assertTrue(re.search(r'AWBENCH replay crossing=%ld runs=%lu files=%lu bytes=%lu us=%lu', source))
        guide = (ROOT / 'docs/HARDWARE-BENCHMARK.md').read_text(encoding='utf-8')
        for mode in ('awbench seek', 'awbench replay', 'awbench buffers'):
            self.assertIn(mode, guide)


if __name__ == '__main__':
    unittest.main()
