"""Private runtime input staging boundaries."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import run_docker


class DockerRuntimeTests(unittest.TestCase):
    def test_existing_input_volume_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(run_docker.subprocess, 'check_output', return_value='private-input\n'), \
                 patch.object(run_docker.subprocess, 'run') as mutate:
                with self.assertRaisesRegex(ValueError, 'already exists'):
                    run_docker.stage_inputs(['docker'], Path(tmp), 'private-input', 'image', Path(tmp)/'log')
                mutate.assert_not_called()

    def test_missing_tar_does_not_create_volume(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(run_docker.subprocess, 'check_output', return_value=''), \
                 patch.object(run_docker.shutil, 'which', return_value=None), \
                 patch.object(run_docker.subprocess, 'run') as mutate:
                with self.assertRaisesRegex(ValueError, 'tar executable'):
                    run_docker.stage_inputs(['docker'], Path(tmp), 'new-input', 'image', Path(tmp)/'log')
                mutate.assert_not_called()

    def test_empty_input_volume_is_refused_and_receipt_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'results'
            with patch.object(run_docker.subprocess, 'check_output', side_effect=['[{}]', '']), \
                 patch.object(run_docker.subprocess, 'run') as mutate:
                status=run_docker.main(['--input-volume','missing-input','--output',str(output)])
                mutate.assert_not_called()
            import json
            receipt=json.loads((output/'full-result.json').read_text())
            self.assertEqual(status,1)
            self.assertEqual(receipt['status'],'failed')
            self.assertIn('does not exist',receipt['error'])
