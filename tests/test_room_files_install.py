"""Every room installer copies the files a room needs besides its map (its plant sprites), so the image never
places a sprite it does not have (v0.0.44-dev1: the Balmora interiors installer copied only room.bsp and the
image step refused a Mages Guild plant sprite; NPC interior plants as sprites, INTERIOR-MORAG-TONG-FPS-43)."""
import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RoomFilesInstallTests(unittest.TestCase):
    def test_sprites_are_copied_and_shared_names_must_match(self):
        from interior_plants import install_room_files
        with tempfile.TemporaryDirectory() as tmp:
            scene = Path(tmp)
            for slug, data in (('room_a', b'sprite'), ('room_b', b'sprite')):
                path = scene / 'area-work' / slug / 'id1' / 'progs/aw_flora/f_x.spr'
                path.parent.mkdir(parents=True)
                path.write_bytes(data)
            report = {'plant_sprites': {'sprite_files': {'progs/aw_flora/f_x.spr': 'sha'}}}
            self.assertEqual(install_room_files(scene, 'room_a', report), ['progs/aw_flora/f_x.spr'])
            self.assertEqual(install_room_files(scene, 'room_b', report), ['progs/aw_flora/f_x.spr'])
            self.assertEqual((scene / 'id1/progs/aw_flora/f_x.spr').read_bytes(), b'sprite')
            (scene / 'area-work/room_b/id1/progs/aw_flora/f_x.spr').write_bytes(b'other')
            with self.assertRaisesRegex(ValueError, 'room_b: file progs/aw_flora/f_x.spr differs'):
                install_room_files(scene, 'room_b', report)
            self.assertEqual(install_room_files(scene, 'room_c', {}), [])

    def test_every_room_installer_installs_the_room_files(self):
        """Any tool that copies area-work/<room>/room.bsp into a scene also calls install_room_files."""
        found = []
        for path in sorted((ROOT / 'tools').glob('*.py')):
            text = path.read_text(encoding='utf-8')
            if re.search(r"area-work['\"]?\s*/[^\n]*room\.bsp['\"][^\n]*maps", text):
                found.append(path.name)
                self.assertIn('install_room_files', text, path.name)
        self.assertGreaterEqual(len(found), 4, found)


if __name__ == '__main__':
    unittest.main()
