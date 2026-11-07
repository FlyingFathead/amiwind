"""The benchmark result file (BENCH-RESULT-FILE-62): tools/bench_result.py reads what aw bench halloween writes."""
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools')]
import bench_result as br  # noqa: E402

SRC = ROOT / 'engine' / 'aga' / 'src'


def fixed_frames():
    """The fixed list of tests/aga_halloween_test.c: 600 frames of 0.2 s, five slow drawn frames, three disk frames."""
    times = [.2] * 600
    disk = [0.0] * 600
    for i, t in ((100, .4), (200, .5), (300, .6), (400, .8), (500, 1.0)):
        times[i] = t
    for i, t, d in ((11, 2.5, 2.3), (50, .7, .5), (599, .25, .01)):
        times[i], disk[i] = t, d
    return times, disk


def result_text(times, disk):
    """The file as the engine writes it (aw_halloween.c bench_write), its figures from the reader's own rule."""
    every = br.figures(times)
    drawing = br.figures(times, lambda i: not disk[i] > 0)
    waited = [i for i, d in enumerate(disk) if d > 0]
    worst = max(waited, key=lambda i: disk[i]) if waited else -1
    slowest = sorted(range(len(times)), key=lambda i: -times[i])[:br.SLOWEST]
    lines = [br.MAGIC, 'scene dagoth', 'build 0.0.62-dev1', 'title AmiWind v0.0.62-dev1 test', 'cpu 68040',
             'fast_ram_mb 32', 'settings screen 320x256 viewsize 100 fov 90 fog 1', 'step_s 0.100',
             'summary HALLOWEEN BENCH dagoth: avg %.1f fps, min %.1f, 1%% low %.1f, %d frames, %.1f s, Fast RAM 32 MB, '
             'CPU 68040, AmiWind v0.0.62-dev1 test' % (every['avg'], every['min'], every['low1'], every['frames'],
                                                       every['seconds'])]
    for key, f in (('all', every), ('drawing', drawing)):
        lines.append('%s frames %d seconds %.3f avg %.2f min %.2f low1 %.2f' % (key, f['frames'], f['seconds'],
                                                                                 f['avg'], f['min'], f['low1']))
    lines.append('disk frames %d ms %.2f worst_ms %.2f worst_frame %d lookups 14 reads 30' % (
        len(waited), sum(disk) * 1000, disk[worst] * 1000 if waited else 0, worst + 1))
    lines += ['slowest %d %.2f %.2f' % (i + 1, times[i] * 1000, disk[i] * 1000) for i in slowest]
    lines.append('times frame ms disk_ms')
    lines += ['%d %.2f %.2f' % (i + 1, t * 1000, d * 1000) for i, (t, d) in enumerate(zip(times, disk))]
    lines.append('end')
    return '\n'.join(lines) + '\n'


class Figures(unittest.TestCase):
    def test_the_same_figures_as_the_engine_test(self):
        # the numbers asserted in tests/aga_halloween_test.c for the same list
        times, disk = fixed_frames()
        every = br.figures(times)
        self.assertEqual(every['frames'], 600)
        self.assertAlmostEqual(every['seconds'], 125.15, places=6)
        self.assertAlmostEqual(every['avg'], 600 / 125.15, places=6)
        self.assertAlmostEqual(every['min'], .4, places=6)
        self.assertAlmostEqual(every['low1'], 6 / 6.1, places=6)
        drawing = br.figures(times, lambda i: not disk[i] > 0)
        self.assertEqual(drawing['frames'], 597)
        self.assertAlmostEqual(drawing['avg'], 597 / 121.7, places=6)
        self.assertAlmostEqual(drawing['min'], 1.0, places=6)
        self.assertAlmostEqual(drawing['low1'], 5 / 3.3, places=6)
        self.assertEqual(br.figures([])['frames'], 0)


class Reader(unittest.TestCase):
    def test_a_file_becomes_one_row(self):
        times, disk = fixed_frames()
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'halloween-0.0.62-dev1-001.txt'
            path.write_text(result_text(times, disk), encoding='ascii', newline='\n')
            row = br.row_of(path, commit='abc1234', machine='Pi 4B, Amiberry')
            self.assertEqual((row['build'], row['commit'], row['scene'], row['cpu'], row['fast_ram_mb']),
                             ('0.0.62-dev1', 'abc1234', 'dagoth', '68040', 32))
            self.assertEqual(row['settings'], 'screen 320x256 viewsize 100 fov 90 fog 1')
            self.assertEqual(row['drawing']['frames'], 597)
            self.assertAlmostEqual(row['drawing']['avg'], 4.91, places=2)
            self.assertEqual(row['disk'], {'frames': 3, 'ms': 2810.0, 'worst_ms': 2300.0, 'worst_frame': 12,
                                           'lookups': 14, 'reads': 30})
            self.assertEqual([s['frame'] for s in row['slowest']], [12, 501, 401, 51, 301])
            self.assertNotIn('times_ms', row)
            self.assertEqual(len(br.row_of(path, frames=True)['times_ms']), 600)
            # added once: the same file again adds nothing
            target = Path(d) / 'rows.jsonl'
            self.assertEqual(len(br.append([row], target)), 1)
            self.assertEqual(br.append([row], target), [])
            self.assertEqual(json.loads(target.read_text().splitlines()[0])['sha256'], row['sha256'])
            self.assertEqual(br.main([str(path), '--commit', 'abc1234']), 0)

    def test_damaged_files_are_refused(self):
        times, disk = fixed_frames()
        good = result_text(times, disk)
        cases = {'not a benchmark result file': 'hello\n',
                 'cut short': good[:good.index('\n300 ')],
                 'expected frame 2': good.replace('\n2 200.00 0.00\n', '\n'),
                 'all avg': good.replace('all frames 600 seconds 125.150 avg 4.79', 'all frames 600 seconds 125.150 avg 9.79'),
                 'unknown line': good.replace('step_s 0.100', 'speed 0.100')}
        for said, text in cases.items():
            with self.subTest(said), self.assertRaisesRegex(ValueError, said):
                br.parse(text)

    def test_the_engine_writes_what_the_reader_reads(self):
        # every line the reader takes is one the engine writes, in the same words (aw_halloween.c bench_write)
        engine = (SRC / 'aw_halloween.c').read_text(encoding='utf-8')
        body = engine[engine.index('static int bench_write('):]
        body = body[:body.index('\n}\n')]
        written = re.findall(r'put_line\(f,"([a-z_0-9A-Z]+)', body)
        self.assertEqual(written, ['AWBENCH1', 'scene', 'build', 'title', 'cpu', 'fast_ram_mb', 'settings', 'step_s',
                                   'summary', 'all', 'drawing', 'disk', 'slowest', 'times', 'end'])
        self.assertIn('put_line(f,"' + br.MAGIC + '\\n")', body)
        for words in ('all frames %d seconds %.3f avg %.2f min %.2f low1 %.2f',
                      'drawing frames %d seconds %.3f avg %.2f min %.2f low1 %.2f',
                      'disk frames %d ms %.2f worst_ms %.2f worst_frame %d lookups %lu reads %lu',
                      'slowest %d %.2f %.2f', '%d %.2f %.2f'):
            self.assertIn('"' + words + '\\n"', body)
        header = (SRC / 'aw_halloween.h').read_text(encoding='utf-8')
        self.assertIn('#define AW_HW_BENCH_SLOWEST\t\t%d' % br.SLOWEST, header)
        self.assertIn('#define AW_HW_BENCH_FOLDER\t\t"bench"', header)


if __name__ == '__main__':
    unittest.main()
