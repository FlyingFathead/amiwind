"""Default flag and final-staging behavior, with synthetic BSP29 data only."""
import contextlib
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from hidden_surface_build import bsp_counts, cull_staged_maps, enabled_value


def fixture(faces=2):
    chunks = [b''] * 15
    chunks[7] = bytes(20 * faces)
    header = bytearray(struct.pack('<i', 29) + bytes(120))
    body = bytearray()
    for i, data in enumerate(chunks):
        struct.pack_into('<ii', header, 4 + 8 * i, 124 + len(body), len(data))
        body += data
    return bytes(header + body)


def parallel_fixture_processor(raw, **kwargs):
    if bsp_counts(raw)['stored_faces'] == 3:
        raise ValueError('parallel unsupported fixture')
    return fixture(1), {'status': 'fixture proof'}


class HiddenBuildTests(unittest.TestCase):
    def test_default_on_and_explicit_off_reach_image_command(self):
        import build
        for override, expected in (([], 'true'), (['--hidden-surface-cull', 'false'], 'false')):
            args = build.parser().parse_args(override)
            args.data_files = Path('/owned'); args.sdk = Path('/sdk')
            tools = {k: '/tools/' + k for k in ('qbsp', 'vis', 'light', 'qcc', 'ffmpeg', 'xdftool', 'rdbtool')}
            steps = dict(build.commands(args, tools, Path('/private/run')))
            image = steps['image']
            self.assertEqual(image[image.index('--hidden-surface-cull') + 1], expected)
            self.assertNotIn('--hidden-surface-cull', steps['engine'])
        self.assertTrue(enabled_value())
        self.assertFalse(enabled_value('false'))
        with self.assertRaises(ValueError): enabled_value('perhaps')

    def test_external_manifest_cuts_exterior_preserves_interior_and_original(self):
        original = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); maps = base / 'maps'; maps.mkdir()
            for n in ('sn045', 'room'): (maps / (n + '.bsp')).write_bytes(original)
            calls = []
            def processor(raw, **kwargs):
                calls.append(kwargs)
                return fixture(1), {'status': 'fixture proof'}
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                report = cull_staged_maps(maps, base / 'proof', {'sn045'}, processor=processor)
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0]['scene_kind'], 'exterior')
            self.assertEqual(bsp_counts((maps / 'sn045.bsp').read_bytes())['stored_faces'], 1)
            self.assertEqual((maps / 'room.bsp').read_bytes(), original)
            self.assertEqual((base / 'proof/originals/sn045.bsp').read_bytes(), original)
            self.assertEqual(report['removed_stored_faces'], 1)
            self.assertIn('sn045: ON', stdout.getvalue())
            self.assertIn('room: ON; outside exterior pass', stdout.getvalue())

    def test_off_is_byte_identical_and_never_calls_processor(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); maps = base / 'maps'; maps.mkdir()
            raw = fixture(); (maps / 'sn045.bsp').write_bytes(raw)
            def forbidden(*a, **kw): self.fail('OFF ran the culler')
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                report = cull_staged_maps(maps, base / 'proof', {'sn045'}, enabled=False, processor=forbidden)
            self.assertEqual((maps / 'sn045.bsp').read_bytes(), raw)
            self.assertEqual(report['removed_stored_faces'], 0)
            self.assertIn('sn045: OFF', stdout.getvalue())

    def test_failure_keeps_all_input_maps_and_records_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); maps = base / 'maps'; maps.mkdir()
            for n in ('one', 'two'): (maps / (n + '.bsp')).write_bytes(fixture())
            calls = []
            def processor(raw, **kwargs):
                calls.append(1)
                if len(calls) == 2: raise ValueError('unsupported fixture')
                return fixture(1), {'status': 'fixture proof'}
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, 'unsupported'):
                cull_staged_maps(maps, base / 'proof', {'one', 'two'}, processor=processor)
            for p in maps.iterdir(): self.assertEqual(p.read_bytes(), fixture())
            report = json.loads((base / 'proof/hidden-surfaces.json').read_text())
            self.assertEqual(report['status'], 'failed')

    def test_invalid_manifest_and_missing_maps_fail_before_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); maps = base / 'maps'; maps.mkdir()
            (maps / 'one.bsp').write_bytes(fixture())
            for names in ({'../escape'}, {'missing'}):
                with self.assertRaises(ValueError): cull_staged_maps(maps, base / 'proof', names)
                self.assertFalse((base / 'proof').exists())

    def test_explicit_runtime_directories_not_sky_classify_exteriors(self):
        from build_aga import staged_exterior_map_names
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp); (id1 / 'maps').mkdir(); (id1 / 'world').mkdir()
            for n in ('seyda', 'room'): (id1 / 'maps' / (n + '.bsp')).write_bytes(fixture())
            directory = bytearray(64 + 2 * 52); directory[:4] = b'AWR2'
            struct.pack_into('<I', directory, 4, 2)
            (id1 / 'world/regions.awr').write_bytes(directory)
            self.assertEqual(staged_exterior_map_names(id1), {'seyda', 'vf0000', 'vf0001'})


    def test_parallel_matches_serial_survivors_and_evidence(self):
        results = []
        for jobs in (1, 2):
            with tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp); maps = base / 'maps'; maps.mkdir()
                for name in ('one', 'two', 'room'):
                    (maps / (name + '.bsp')).write_bytes(fixture())
                with contextlib.redirect_stdout(io.StringIO()):
                    report = cull_staged_maps(maps, base / 'proof', {'one', 'two'},
                        processor=parallel_fixture_processor, jobs=jobs)
                results.append(([p.read_bytes() for p in sorted(maps.iterdir())], report['maps']))
                self.assertEqual(report['removed_stored_faces'], 2)
                self.assertEqual(report['preparation_jobs'], jobs)
                self.assertEqual((base / 'proof/originals/one.bsp').read_bytes(), fixture())
        self.assertEqual(results[0], results[1])

    def test_progress_receipt_writes_are_throttled_and_final_receipt_complete(self):
        # The parent rewrote the whole growing receipt after every map (4 MB for the
        # world, 2,741 times): the workers waited for it. Progress saves are now at
        # most every 2 s; the final receipt is the same.
        import hidden_surface_build
        reports = []
        for throttle in (False, True):
            with tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp); maps = base / 'maps'; maps.mkdir()
                for index in range(40):
                    (maps / f'm{index:02d}.bsp').write_bytes(fixture())
                writes = []
                real = Path.write_text

                def counted(path, *args, **kwargs):
                    if path.name == 'hidden-surfaces.json':
                        writes.append(path)
                    return real(path, *args, **kwargs)
                clock = patch.object(hidden_surface_build.time, 'monotonic', return_value=100.0) if throttle else contextlib.nullcontext()
                with contextlib.redirect_stdout(io.StringIO()), patch.object(Path, 'write_text', counted), clock:
                    report = cull_staged_maps(maps, base / 'proof', {f'm{i:02d}' for i in range(20)},
                                              processor=parallel_fixture_processor)
                saved = json.loads((base / 'proof/hidden-surfaces.json').read_text())
                reports.append(({k: v for k, v in saved.items() if k not in ('started_at', 'finished_at')}, len(writes)))
        self.assertEqual(reports[0][0], reports[1][0])
        self.assertEqual(len(reports[1][0]['maps']), 40)
        self.assertLessEqual(reports[1][1], 3)

    def test_parallel_failure_never_installs_partial_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); maps = base / 'maps'; maps.mkdir()
            inputs = {'one': fixture(), 'two': fixture(3)}
            for name, raw in inputs.items(): (maps / (name + '.bsp')).write_bytes(raw)
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, 'parallel unsupported'):
                cull_staged_maps(maps, base / 'proof', set(inputs),
                    processor=parallel_fixture_processor, jobs=2)
            for name, raw in inputs.items():
                self.assertEqual((maps / (name + '.bsp')).read_bytes(), raw)
            self.assertEqual(json.loads((base / 'proof/hidden-surfaces.json').read_text())['status'], 'failed')
            with self.assertRaisesRegex(ValueError, 'positive integer'):
                cull_staged_maps(maps, base / 'invalid', set(inputs), jobs=0)
            self.assertFalse((base / 'invalid').exists())


if __name__ == '__main__': unittest.main()
