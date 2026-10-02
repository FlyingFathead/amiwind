"""Docker context privacy boundaries and retained failure diagnostics."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import build_docker


class DockerBuilderTests(unittest.TestCase):
    def test_only_validated_source_is_copied(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'repo'
            root.mkdir()
            (root / 'private-game.bsa').write_bytes(b'private')
            target = Path(tmp) / 'context'
            with patch.object(build_docker, 'inspect_source', return_value={'README.md': b'public\n'}):
                manifest = build_docker.prepare_context(target, root)
            self.assertEqual(set(manifest), {'README.md'})
            self.assertFalse((target / 'source/private-game.bsa').exists())
            self.assertEqual((target / 'source/README.md').read_bytes(), b'public\n')
            self.assertIn('!source/**', (target / '.dockerignore').read_text())

    def test_invalid_source_leaves_no_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'context'
            with patch.object(build_docker, 'inspect_source', side_effect=ValueError('unexpected source')):
                with self.assertRaisesRegex(ValueError, 'unexpected source'):
                    build_docker.prepare_context(target)
            self.assertFalse(target.exists())

    def test_existing_context_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'context'
            target.mkdir()
            sentinel = target / 'private.txt'
            sentinel.write_text('keep')
            with self.assertRaisesRegex(ValueError, 'must be new'):
                build_docker.prepare_context(target)
            self.assertEqual(sentinel.read_text(), 'keep')

    def test_failure_receipt_retains_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'results'
            with patch.object(build_docker, 'prepare_context', side_effect=ValueError('source rejected')):
                status = build_docker.main(['build', '--context', str(Path(tmp)/'context'),
                                           '--output', str(output)])
            receipt = json.loads((output/'docker-result.json').read_text())
            self.assertEqual(status, 1)
            self.assertEqual(receipt['status'], 'failed')
            self.assertIn('source rejected', receipt['error'])
            self.assertIn('finished_at', receipt)

    def test_failed_command_output_is_saved(self):
        import sys
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / 'failure.log'
            with self.assertRaisesRegex(RuntimeError, 'exited 7'):
                build_docker.logged([sys.executable, '-c',
                    "import sys; print('exact diagnostic', file=sys.stderr); sys.exit(7)"], log)
            self.assertIn('exact diagnostic', log.read_text())
