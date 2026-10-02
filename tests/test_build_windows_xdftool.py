"""Windows packing must preserve all operations despite the command-line limit."""
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from build_windows_xdftool import batches, command_units, run


class WindowsXdfToolTests(unittest.TestCase):
    def test_queue_is_preserved_across_bounded_commands(self):
        command = ['C:/tools with spaces/xdftool.exe', 'C:/build/out.hdf',
                   'create', 'size=4Mi', '+', 'format', 'TEST', 'ffs']
        for number in range(1200):
            command += ['+', 'write', 'C:/input with spaces/asset.bin', f'data/f{number}']
        result = list(batches(command))
        self.assertGreater(len(result), 1)
        self.assertTrue(all(command_units(c) <= 24000 for c in result))
        reconstructed = result[0] + sum((['+'] + c[2:] for c in result[1:]), [])
        self.assertEqual(reconstructed, command)

    def test_long_operation_is_rejected_before_any_tool_runs(self):
        with patch('build_windows_xdftool.subprocess.run') as execute:
            with self.assertRaisesRegex(ValueError, 'One xdftool operation'):
                run(['xdftool.exe', 'out.hdf', 'create', 'size=4Mi', '+', 'write',
                     'x' * 25000, 'file'])
        execute.assert_not_called()

    def test_failure_stops_following_batches(self):
        command = ['xdftool.exe', 'out.hdf', 'create', 'size=4Mi']
        for number in range(2000):
            command += ['+', 'write', 'some source file.bin', f'f{number}']
        with patch('build_windows_xdftool.subprocess.run',
                   side_effect=subprocess.CalledProcessError(9, 'xdftool')) as execute:
            with self.assertRaises(subprocess.CalledProcessError):
                run(command)
        self.assertEqual(execute.call_count, 1)

    def test_short_command_and_unicode_units(self):
        command = ['xdftool.exe', 'out.hdf', 'info']
        self.assertEqual(list(batches(command)), [command])
        # Supplementary characters occupy two UTF-16 units, not one.
        self.assertEqual(command_units(['\U0001f600']), 3)


if __name__ == '__main__':
    unittest.main()
