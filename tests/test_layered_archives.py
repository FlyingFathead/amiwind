# SPDX-License-Identifier: GPL-3.0-only
"""The selected masters' archives as one directory (src/mwad/archives.py, ASSETS-ARCHIVE-ORDER-32): the base game alone
reads Morrowind.bsa exactly as before; a selected layer's archive is read over it in load order, later archive wins."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

from mwad.archives import archive_names, layered_bsa  # noqa: E402
from mwad.audit import BSA  # noqa: E402
from mwad.esm import read_bsa_asset  # noqa: E402


def write_bsa(path, files):
    """A TES3 BSA (version 0x100) of {name: bytes}; hashes zero (no reader here uses them)."""
    names = list(files)
    blob, offsets, name_table, name_offsets = b'', [], b'', []
    for n in names:
        offsets.append((len(files[n]), len(blob)))
        blob += files[n]
        name_offsets.append(len(name_table))
        name_table += n.encode('ascii') + b'\0'
    count = len(names)
    directory = b''.join(struct.pack('<II', *o) for o in offsets) + \
        b''.join(struct.pack('<I', o) for o in name_offsets) + name_table
    hashes = b'\0' * (8 * count)
    path.write_bytes(struct.pack('<III', 0x100, len(directory), count) + directory + hashes + blob)


class LayeredArchives(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)
        write_bsa(self.data / 'Morrowind.bsa', {'meshes\\a.nif': b'base-a', 'meshes\\b.nif': b'base-b'})
        write_bsa(self.data / 'Tribunal.bsa', {'meshes\\b.nif': b'trib-b', 'meshes\\t.nif': b'trib-t'})
        write_bsa(self.data / 'Bloodmoon.bsa', {'meshes\\b.nif': b'blood-b', 'meshes\\s.nif': b'blood-s'})

    def tearDown(self):
        self.tmp.cleanup()

    def test_the_base_game_alone_is_the_plain_archive(self):
        got = layered_bsa(self.data, ['Morrowind.esm'])
        plain = BSA(self.data / 'Morrowind.bsa')
        self.assertEqual(got.entries, plain.entries)              # no 'path' added: --no-dlc reads as before
        self.assertEqual(got.path, plain.path)
        self.assertEqual(read_bsa_asset(got, 'meshes/b.nif'), b'base-b')

    def test_later_archive_wins_in_load_order(self):
        both = layered_bsa(self.data, ['Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm'])
        self.assertEqual(read_bsa_asset(both, 'meshes/a.nif'), b'base-a')
        self.assertEqual(read_bsa_asset(both, 'meshes/b.nif'), b'blood-b')
        self.assertEqual(read_bsa_asset(both, 'meshes/t.nif'), b'trib-t')
        self.assertEqual(read_bsa_asset(both, 'meshes/s.nif'), b'blood-s')
        trib = layered_bsa(self.data, ['Morrowind.esm', 'Tribunal.esm'])
        self.assertEqual(read_bsa_asset(trib, 'meshes/b.nif'), b'trib-b')
        self.assertNotIn('meshes/s.nif', trib.entries)
        self.assertEqual(archive_names(['Morrowind.esm', 'Bloodmoon.esm']), ['Morrowind.bsa', 'Bloodmoon.bsa'])

    def test_the_room_readers_use_it(self):
        for rel in ('tools/chim_room_batches.py', 'tools/prepare_scenery.py'):
            text = (ROOT / rel).read_text(encoding='utf-8')
            self.assertIn('layered_bsa(', text, rel)
            self.assertNotIn("BSA(child_ci(data, 'Morrowind.bsa'))", text, rel)


if __name__ == '__main__':
    unittest.main()
