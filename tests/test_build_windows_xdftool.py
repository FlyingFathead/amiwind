"""Windows packing must preserve all operations despite the command-line limit."""
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import build_windows_xdftool
from build_windows_xdftool import batches, command_units, posix_bytes, run, run_any


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

    def test_posix_queue_stays_below_arg_max_in_order(self):
        # 15,747 boot files with absolute paths exceeded Linux ARG_MAX (2 MiB) in one command.
        command = ['/opt/tools/xdftool', '/vol/build/image/partition.hdf', 'create', 'size=1920Mi',
                   '+', 'format', 'AMIWIND', 'ffs', '+', 'boot', 'install']
        for number in range(18000):
            command += ['+', 'write', f'/vol/ws2/build/dev1-r2/image/boot/id1/progs/aw_flora/f_{number:016x}.spr',
                        f'id1/progs/aw_flora/f_{number:016x}.spr']
        self.assertGreater(posix_bytes(command), 2 * 1024 * 1024)
        result = list(batches(command, build_windows_xdftool.MAX_POSIX_BYTES, posix_bytes))
        self.assertGreater(len(result), 1)
        self.assertTrue(all(posix_bytes(c) <= build_windows_xdftool.MAX_POSIX_BYTES for c in result))
        self.assertEqual(result[0][:4], command[:4])
        self.assertTrue(all(c[:2] == command[:2] and 'create' not in c for c in result[1:]))
        reconstructed = result[0] + sum((['+'] + c[2:] for c in result[1:]), [])
        self.assertEqual(reconstructed, command)
        with patch.object(build_windows_xdftool.os, 'name', 'posix'), \
                patch('build_windows_xdftool.subprocess.run') as execute:
            run_any(command)
        self.assertEqual([call.args[0] for call in execute.call_args_list], result)

    def test_image_packing_uses_the_bounded_runner(self):
        root = Path(__file__).resolve().parents[1] / 'tools'
        for name in ('build_aga.py', 'world_volumes.py'):
            text = (root / name).read_text(encoding='utf-8')
            self.assertIn('run_any as run_xdftool', text, name)
            self.assertNotIn('import run as run_xdftool', text, name)


if __name__ == '__main__':
    unittest.main()
