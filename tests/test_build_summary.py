"""Final output identity and failure reporting through the real build entry point."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import build
import build_summary
from mwad import progress


class BuildSummaryTests(unittest.TestCase):
    def test_success_records_timezone_elapsed_bytes_hash_warnings_and_terminal_rules(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root/'logs').mkdir()
            (root/'logs/22-engine.log').write_text('source.c:1: warning: example\nsource.c:2: note: detail\nwarning 10: assembler example\n')
            output = root/'example.hdf'; output.write_bytes(b'abc')
            captured = io.StringIO()
            with patch.object(build_summary, 'timestamp', side_effect=['2026-10-01T20:00:00+03:00', '2026-10-01T21:01:01+03:00']), \
                 patch.object(build_summary.time, 'monotonic', side_effect=[100, 100, 100, 3761.25]), \
                 patch.object(progress.shutil, 'get_terminal_size', return_value=os.terminal_size((53, 24))), \
                 patch.object(progress.os, 'get_terminal_size', side_effect=OSError), \
                 contextlib.redirect_stdout(captured):
                summary = build_summary.BuildSummary(root, 'test', 'AGA conversion and image')
                result = summary.finish('passed', output)
            self.assertEqual(result['elapsed_seconds'], 3661.25)
            self.assertEqual(result['elapsed'], '1 hrs 01 mins 01 secs')
            self.assertEqual(result['output']['sha256'], 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
            self.assertEqual(result['output']['bytes'], 3)
            self.assertEqual(result['compiler_warnings']['count'], 2)
            self.assertEqual(json.loads((root/'build-summary.json').read_text()), result)
            text = captured.getvalue(); self.assertIn('Compilation finished without errors', text)
            self.assertIn('0.000000 GiB (3 bytes)', text)
            self.assertEqual(text.splitlines()[-1], '-'*53)
            self.assertEqual(text.count('-'*53), 2)

    def test_private_image_never_claims_compilation_without_errors(self):
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()) as captured:
            root = Path(temp); output = root/'test-private-test.hdf'; output.write_bytes(b'fixture')
            acceptance = {'status': 'owner-accepted-known-findings', 'production_gate_passed': False, 'unresolved': 23}
            result = build_summary.BuildSummary(root, 'test', 'AGA image recovery').finish('passed', output, actor_acceptance=acceptance)
            self.assertEqual(result['validation'], 'private-test-only')
            self.assertFalse(result['actor_ground_audit']['production_gate_passed'])
            self.assertIn('production actor gate DID NOT PASS', captured.getvalue())
            self.assertNotIn('Compilation finished without errors', captured.getvalue())
            self.assertEqual(result['output']['bytes'], 7)

    def test_duration_does_not_wrap_at_midnight(self):
        self.assertEqual(build_summary.duration(90061), '25 hrs 01 mins 01 secs')
        self.assertEqual(build_summary.duration(59.99), '0 hrs 00 mins 59 secs')

    def test_inventory_uses_detected_versions_and_only_selected_tools(self):
        metadata = {'compiler_jobs': 12, 'tools': {'qcc': '/tools/qcc', 'make': '/tools/make', 'console-font': '/font.ttf'},
                    'tool_sha256': {'qcc': 'a'*64, 'make': 'b'*64},
                    'version_comparison': [
                        {'name': 'Python', 'kind': 'interpreter', 'detected': '3.12.3'},
                        {'name': 'numpy', 'kind': 'package', 'detected': '2.5.3'},
                        {'name': 'qcc', 'kind': 'tool', 'detected': 'sha256:'+'a'*64, 'reference': 'DO NOT CLAIM THIS VERSION', 'status': 'unknown'},
                        {'name': 'make', 'kind': 'tool', 'detected': '4.3', 'status': 'matching'},
                        {'name': 'ffmpeg', 'kind': 'tool', 'detected': '8.0.1', 'path': '/tools/ffmpeg'}]}
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()) as captured:
            summary = build_summary.BuildSummary(Path(temp), 'test', 'asset-free test')
            summary.record_environment(metadata)
            with patch.object(subprocess, 'run', side_effect=AssertionError('must not reprobe tools')):
                result = summary.finish('failed')
            env = result['build_environment']
            self.assertEqual(env['python'], '3.12.3')
            self.assertEqual(env['packages'], [{'name': 'numpy', 'version': '2.5.3'}])
            self.assertEqual([row['name'] for row in env['tools']], ['qcc', 'make'])
            self.assertEqual(env['worker_budget'], 12)
            self.assertIn('make: 4.3', captured.getvalue())
            self.assertIn('qcc: no recorded version', captured.getvalue())
            self.assertIn('Binary SHA-256: '+'a'*64, captured.getvalue())
            self.assertNotIn('DO NOT CLAIM THIS VERSION', captured.getvalue())
            self.assertIsNone(result['output'])
            self.assertEqual(json.loads((Path(temp)/'build-summary.json').read_text())['build_environment'], env)

    def test_inventory_missing_probe_preserves_binary_identity(self):
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()) as captured:
            summary = build_summary.BuildSummary(Path(temp), 'test', 'test')
            summary.record_environment({'compiler_jobs': 1, 'tools': {'vasmm68k_mot': '/tools/vasm'},
                                        'tool_sha256': {'vasmm68k_mot': 'c'*64}})
            result = summary.finish('failed')
            self.assertEqual(result['build_environment']['stage_scheduling'], 'serial')
            self.assertIn('vasmm68k_mot: version not recorded', captured.getvalue())
            self.assertIn('Binary SHA-256: '+'c'*64, captured.getvalue())

    def test_large_file_is_hashed_in_chunks(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)/'large.hdf'; data = b'abc123' * 400000
            output.write_bytes(data)
            with patch.object(Path, 'read_bytes', side_effect=AssertionError('do not load whole HDF')):
                result = build_summary.output_identity(output)
            self.assertEqual(result['bytes'], len(data))
            self.assertEqual(result['sha256'], hashlib.sha256(data).hexdigest())

    def test_directory_is_not_given_a_fake_file_checksum(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root/'one').write_bytes(b'123'); (root/'sub').mkdir()
            (root/'sub/two').write_bytes(b'45')
            result = build_summary.output_identity(root)
            self.assertEqual((result['kind'], result['files'], result['bytes'], result['sha256']), ('directory', 2, 5, None))

    def test_failure_and_cancel_do_not_hash_or_claim_partial_output(self):
        for status in ('failed', 'cancelled'):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); output = root/'partial.hdf'; output.write_bytes(b'partial')
                captured = io.StringIO()
                with patch.object(build_summary, 'output_identity', side_effect=AssertionError('partial output')), contextlib.redirect_stdout(captured):
                    result = build_summary.BuildSummary(root, 'test', 'AGA conversion and image').finish(status, output)
                self.assertEqual(result['status'], status); self.assertIsNone(result['output'])
                self.assertNotIn('Compilation finished without errors', captured.getvalue())
                self.assertNotIn('SHA-256:', captured.getvalue())

    def test_unwritable_receipt_does_not_hide_failure(self):
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()) as captured:
            summary = build_summary.BuildSummary(Path(temp), 'test', 'AGA conversion and image')
            with patch.object(Path, 'write_text', side_effect=OSError(28, 'No space left on device')):
                result = summary.finish('failed')
            self.assertEqual(result['status'], 'failed')
            self.assertIn('Summary save warning:', captured.getvalue())

    def run_fixture(self, root, outcome):
        args = ['--dry-run', '--workspace', str(root), '--name', 'fixture', '--jobs', '1']
        def commands(options, run):
            output = run/'image'/f'AmiWind-v{build.VERSION}-dry-run.hdf'
            script = (f'from pathlib import Path; p=Path({str(output)!r}); '
                      'p.parent.mkdir(); p.write_bytes(b"synthetic final output"); '
                      'print("fixture.c:1: warning: fixture warning")')
            if outcome == 'failed': script += '; raise SystemExit(7)'
            if outcome == 'missing': script = 'print("no output")'
            return [('engine', [sys.executable, '-c', script])]
        captured = io.StringIO()
        with patch('setup_build.use_environment'), \
             patch.object(build, 'dry_run_prerequisites', return_value={}), \
             patch.object(build, 'provenance', return_value={'compiler_jobs': 1, 'tools': {'make': '/fixture/make'},
                 'version_comparison': [{'name': 'make', 'kind': 'tool', 'detected': '4.3', 'status': 'matching'}]}), \
             patch.object(build, 'dry_run_commands', side_effect=commands), \
             contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            if outcome == 'passed': self.assertEqual(build.main(args), 0)
            else:
                with self.assertRaises(SystemExit) as error: build.main(args)
                self.assertEqual(error.exception.code, 1)
        return captured.getvalue(), json.loads((root/'build/fixture/build-summary.json').read_text())

    def test_entry_point_summarizes_real_subprocess_output(self):
        with tempfile.TemporaryDirectory() as temp:
            text, result = self.run_fixture(Path(temp), 'passed')
            self.assertEqual(result['status'], 'passed')
            self.assertEqual(result['compiler_warnings']['count'], 1)
            self.assertEqual(result['output']['sha256'], hashlib.sha256(b'synthetic final output').hexdigest())
            self.assertEqual(text.count('Compilation finished without errors'), 1)
            self.assertIn('make: 4.3', text)
            self.assertEqual(result['build_environment']['tools'][0]['detected'], '4.3')

    def test_entry_point_rejects_missing_output_and_failed_stage(self):
        for outcome in ('failed', 'missing'):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as temp:
                text, result = self.run_fixture(Path(temp), outcome)
                self.assertEqual(result['status'], 'failed'); self.assertIsNone(result['output'])
                self.assertIn('Compilation failed', text)
                self.assertNotIn('Compilation finished without errors', text)


if __name__ == '__main__':
    unittest.main()
