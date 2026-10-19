"""Tools that read every map of a folder see the CHIM frame maps (x.chim) too (tools/map_files.py).

Since v0.0.36 the CHIM town and region frame maps are BSP29 files named maps/<name>.chim. A tool that lists
maps with its own *.bsp pattern silently misses them (GUARD-TORCH-CHIM-FRAMES-44: the guard torch tool found
only the interior guards). Each test puts a frame map in a temporary maps folder and checks the tool sees it;
on the *.bsp-only listing every one of them fails. tests/test_map_listing_guard.py keeps new *.bsp-only
listings out of tools/.
"""
import struct
import tempfile
import unittest
from pathlib import Path

from player_hull import pack_lumps
from test_actor_frames import bsp, header_only, npc

FRAME_KEY = '{\n"classname" "worldspawn"\n"_chim_frame" "0 0"\n}\n'


def frame_map(entities='', miptex=b''):
    """A BSP29 CHIM frame map: worldspawn with "_chim_frame", ENTITIES after it, MIPTEX as its texture lump."""
    chunks = [b'' for _ in range(15)]
    chunks[0] = (FRAME_KEY + entities).encode()
    chunks[2] = miptex
    return pack_lumps(chunks)


class FrameMapsAreListed(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.id1 = Path(tmp.name)
        (self.id1 / 'maps').mkdir()
        (self.id1 / 'progs').mkdir()

    def test_actor_frames_audits_the_residents_of_a_frame_map(self):
        from actor_frames import audit_payload
        (self.id1 / 'progs/town.mdl').write_bytes(header_only(8))
        (self.id1 / 'progs/odd.mdl').write_bytes(header_only(17))
        (self.id1 / 'maps/room.bsp').write_bytes(bsp(npc('progs/town.mdl')))
        self.assertEqual(audit_payload(self.id1)['actor_models'], 1)
        # a town frame's resident with an undeclared layout is found as in a legacy map
        (self.id1 / 'maps/balmora-chim.chim').write_bytes(frame_map(npc('progs/odd.mdl')))
        with self.assertRaisesRegex(ValueError, r'progs/odd\.mdl \(17 frames\): Undeclared'):
            audit_payload(self.id1)

    def test_sky_keys_of_frame_maps_are_read(self):
        from build_exclusions import worldspawn_sky_keys
        sky = '{\n"classname" "worldspawn"\n"_chim_frame" "1 2"\n"_aw_sky_mode" "exterior"\n' \
              '"_aw_sky_asset" "gfx/aw_shared_sky.lmp"\n}\n'
        head = bytearray(124)
        struct.pack_into('<iii', head, 0, 29, 124, len(sky))
        (self.id1 / 'maps/vf0001.chim').write_bytes(bytes(head) + sky.encode())
        self.assertEqual(worldspawn_sky_keys(self.id1 / 'maps'),
                         {'vf0001': {'_aw_sky_mode': 'exterior', '_aw_sky_asset': 'gfx/aw_shared_sky.lmp'}})

    def test_gallery_greetings_come_from_frame_maps_too(self):
        from stage_gallery import greetings
        (self.id1 / 'sound').mkdir()
        (self.id1 / 'sound/hello.wav').write_bytes(b'RIFF')
        voiced = ('{\n"classname" "aw_npc"\n"model" "progs/town.mdl"\n"aw_source_id" "Town_Guard"\n'
                  '"aw_voice" "hello.wav"\n"aw_line" "Halt."\n}\n')
        (self.id1 / 'maps/balmora-chim.chim').write_bytes(frame_map(voiced))
        self.assertEqual(greetings(self.id1), {'town_guard': ('hello.wav', '8', 'Halt.')})

    def test_ui_palette_audit_reads_frame_map_textures(self):
        from ui_palette import check_scene
        def miptex(pixel):
            # one 4x4 texture, only its full-size level stored
            body = b'door'.ljust(16, b'\0') + struct.pack('<6I', 4, 4, 40, 0, 0, 0) + bytes([pixel]) * 16
            return struct.pack('<ii', 1, 8) + body
        (self.id1 / 'maps/vf0002.chim').write_bytes(frame_map(miptex=miptex(10)))
        check_scene(self.id1)
        (self.id1 / 'maps/vf0002.chim').write_bytes(frame_map(miptex=miptex(225)))
        with self.assertRaisesRegex(ValueError, 'UI palette slots already used'):
            check_scene(self.id1)

    def test_hull_chain_audit_and_face_check_list_frame_maps_of_a_folder(self):
        from check_faces import bsp_paths
        from hull_chain_audit import maps_in
        maps = self.id1 / 'maps'
        for name in ('vf0000.bsp', 'vf0001.chim', 'notes.txt'):
            (maps / name).write_bytes(b'x')
        expected = [maps / 'vf0000.bsp', maps / 'vf0001.chim']
        self.assertEqual(maps_in([maps]), expected)
        self.assertEqual(list(bsp_paths([maps])), expected)
        # files named on the command line are taken as given
        self.assertEqual(maps_in([maps / 'notes.txt']), [maps / 'notes.txt'])


if __name__ == '__main__':
    unittest.main()
