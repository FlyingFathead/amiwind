# SPDX-License-Identifier: GPL-3.0-only
"""Parallel drive readback (world_volumes.verify_combined) equals the serial receipt."""
import hashlib
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]
TOOLS = Path(sys.executable).parent
XDFTOOL = shutil.which('xdftool') or (TOOLS / 'xdftool' if (TOOLS / 'xdftool').is_file() else None)
RDBTOOL = shutil.which('rdbtool') or (TOOLS / 'rdbtool' if (TOOLS / 'rdbtool').is_file() else None)


@unittest.skipUnless(importlib.util.find_spec('amitools') and XDFTOOL and RDBTOOL, 'needs amitools (xdftool, rdbtool)')
class ReadbackTests(unittest.TestCase):
    def drive(self, root, count=9):
        files, command = [], [str(XDFTOOL), str(root / 'part.hdf'), 'create', 'size=4Mi', '+', 'format', 'TEST', 'ffs',
                              '+', 'makedir', 'id1']
        for index in range(count):
            raw = bytes([index]) * (3000 + 1500 * index)
            (root / f'f{index}.bin').write_bytes(raw)
            command += ['+', 'write', str(root / f'f{index}.bin'), f'id1/f{index}.bin']
            files.append(dict(path=f'id1/f{index}.bin', bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL)
        from amiga_fs import check_image
        check_image(root / 'part.hdf', normalize=True)  # as the image step does before packing
        subprocess.run([str(RDBTOOL), str(root / 'drive.hdf'), 'create', 'chs=129,1,64', '+', 'init',
                        '+', 'addimg', str(root / 'part.hdf'), 'name=DH0', 'bootable=1'], check=True, stdout=subprocess.DEVNULL)
        return root / 'drive.hdf', [dict(partition='DH0', volume='TEST', files=files)]

    def test_sliced_parallel_readback_equals_serial(self):
        import world_volumes
        with tempfile.TemporaryDirectory() as temp:
            hdf, partitions = self.drive(Path(temp))
            serial = world_volumes.verify_combined(hdf, partitions, jobs=1)
            with patch.object(world_volumes, 'READBACK_CHUNK', 2):
                sliced = world_volumes.verify_combined(hdf, partitions, jobs=1)
                parallel = world_volumes.verify_combined(hdf, partitions, jobs=3)
                partitions[0]['files'][5]['sha256'] = '0' * 64
                with self.assertRaisesRegex(ValueError, 'readback mismatch: id1/f5.bin'):
                    world_volumes.verify_combined(hdf, partitions, jobs=3)
        self.assertEqual(serial, sliced)
        self.assertEqual(serial, parallel)
        self.assertEqual(serial[0]['files'], 9)
        self.assertTrue(serial[0]['highest_file'].startswith('id1/f'))


if __name__ == '__main__':
    unittest.main()
