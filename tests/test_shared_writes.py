"""Files two build stages write (BUILD-STAGE-WRITES-OTHERS-OUTPUT-63, BUILD-SHARED-WRITES-UNATTRIBUTED-52)."""
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

import build_cache  # noqa: E402

# The shared writes recorded in the v0.0.63-dev1 build. The list only shrinks: a file moved to one owner comes
# out of config/shared-writes.json and this number goes down with it; a new shared write is never added.
CATALOGUE_CEILING = 50


class CatalogueTests(unittest.TestCase):
    def test_the_catalogue_never_grows(self):
        known = build_cache.load_shared_writes_catalogue(ROOT)
        self.assertTrue(known, 'config/shared-writes.json is missing or unreadable')
        self.assertLessEqual(len(known), CATALOGUE_CEILING,
                             'a new file two stages write: give it one owner stage instead of listing it')
        for path, stages in known.items():
            self.assertGreaterEqual(len(stages), 2, path)
            self.assertEqual(stages, sorted(set(stages)), path)

    def test_shared_writes_and_new_ones(self):
        found = build_cache.shared_writes({'a': {'x', 'y'}, 'b': {'x'}, 'c': {'y', 'z'}, 'd': None})
        self.assertEqual(found, {'x': ['a', 'b'], 'y': ['a', 'c']})
        self.assertEqual(build_cache.new_shared_writes(found, {'x': ['a', 'b']}), {'y': ['a', 'c']})
        # a known file written by one more stage than listed is new too
        self.assertEqual(build_cache.new_shared_writes({'x': ['a', 'b', 'c']}, {'x': ['a', 'b']}),
                         {'x': ['a', 'b', 'c']})
        self.assertEqual(build_cache.new_shared_writes(found, {'x': ['a', 'b'], 'y': ['a', 'c']}), {})

    def test_a_run_is_read_from_its_traces(self):
        with tempfile.TemporaryDirectory() as temp:
            reads = Path(temp) / 'profile' / 'reads'
            reads.mkdir(parents=True)
            (reads / '01-area.txt').write_text('>scene/doors.txt\n>scene/own.txt\ntools/x.py\n')
            (reads / '02-census.txt').write_text('>scene/doors.txt\n')
            self.assertEqual(build_cache.run_shared_writes(temp), {'scene/doors.txt': ['area', 'census']})


class ThirdStageWriterTests(unittest.TestCase):
    """v0.0.63-dev1: chim-town-seyda and chim-town-vivec_city ran beside world-terrain and world-ui and saw their
    files change; the two towns were compared first (name order), neither had written the files, and both were
    refused. The pairs that can be attributed are now settled before any pair is refused."""

    def run_three(self, run, writer_writes):
        names = ('a-town', 'b-town', 'z-world')
        steps = [(name, [sys.executable, 'tools/x.py', '--scene', str(run / 'scene'), '--out', str(run / name)]) for name in names]
        (run / 'scene').mkdir(parents=True)
        recorder = build_cache.Recorder(run, steps, {})
        recorder.traced = True
        for name, command in steps:
            recorder.before(name, command)
        time.sleep(0.01)
        (run / 'scene' / 'lava.wav').write_bytes(b'loop')
        for name in names:
            (run / name).mkdir()
            (run / name / 'own.json').write_text('{}')
        traces = {}
        for name in names:
            traces[name] = run.parent / f'{name}.txt'
            writes = [f'{name}/own.json'] + (writer_writes if name == 'z-world' else [])
            traces[name].write_text(''.join('>' + path + '\n' for path in writes) + 'tools/x.py\n')
        for name in names:
            recorder.after(name, {}, traces[name])
        recorder.close({'status': 'passed'})
        return {name: build_cache.load_manifest(run, name) for name in names}

    def test_a_file_a_third_stage_wrote_refuses_neither_observer(self):
        with tempfile.TemporaryDirectory() as temp:
            manifests = self.run_three(Path(temp) / 'run', ['scene/lava.wav'])
            for name, manifest in manifests.items():
                self.assertTrue(manifest['reusable'], (name, manifest['reasons']))
            self.assertIn('scene/lava.wav', manifests['z-world']['files'])
            for town in ('a-town', 'b-town'):
                self.assertNotIn('scene/lava.wav', manifests[town]['files'])

    def test_a_file_nobody_wrote_still_refuses_the_stages_that_saw_it(self):
        with tempfile.TemporaryDirectory() as temp:
            manifests = self.run_three(Path(temp) / 'run', [])
            for town in ('a-town', 'b-town'):
                self.assertFalse(manifests[town]['reusable'])
                self.assertIn('outputs cannot be attributed', manifests[town]['reasons'][-1])


class ResettleTests(unittest.TestCase):
    """Records refused before the fix (v0.0.63-dev1 towns) are reusable when read, once the two records no longer
    share a path; anything else keeps them refused."""

    def write(self, folder, name, files, reasons):
        import json
        record = {'schema': build_cache.MANIFEST_SCHEMA, 'stage': name, 'status': 'complete', 'fingerprint': 'f',
                  'files': {path: {'size': 1, 'sha256': 'a' * 64, 'mode': 420} for path in files}, 'links': {},
                  'deleted': [], 'reusable': not reasons, 'reasons': reasons}
        (folder / f'{name}.json').write_text(json.dumps(record))

    def test_resettle(self):
        reason = 'changed scene/lava.wav (and 10 more) while {} ran; outputs cannot be attributed'
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            folder = run / 'profile' / 'manifests'
            folder.mkdir(parents=True)
            self.write(folder, 'seyda', ['seyda/a.json'], [reason.format('vivec')])
            self.write(folder, 'vivec', ['vivec/b.json'], [reason.format('seyda')])
            self.write(folder, 'balmora', ['vivec/b.json'], [reason.format('vivec')])      # still overlapping
            self.write(folder, 'lonely', ['x/c.json'], [reason.format('missing')])         # no other record
            self.write(folder, 'mixed', ['m/d.json'], [reason.format('vivec'), 'ran 1 Python files from outside'])
            for name, expected in (('seyda', True), ('vivec', True), ('balmora', False), ('lonely', False),
                                   ('mixed', False)):
                manifest = build_cache.load_manifest(run, name)
                self.assertIs(manifest['reusable'], expected, name)
            self.assertIn('resettled', build_cache.load_manifest(run, 'seyda'))


if __name__ == '__main__':
    unittest.main()
