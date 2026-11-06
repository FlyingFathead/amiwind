# SPDX-License-Identifier: GPL-3.0-only
"""A held carried light as itself (HELD-LIGHT-OWN-MODEL-61): the builder's held light file (tools/held_lights.py),
the catalogue's light flags (tools/prepare_inventory.py byte 511) and the engine wiring that reads them (aw_torch.c,
aw_hand_models.c, aw_view.c, aw_guard_torch.c, aw_inventory.c)."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
SRC = ROOT / 'engine/aga/src'


def code(name):
    return (SRC / name).read_text(encoding='latin-1')


class HeldLightFile(unittest.TestCase):
    def test_text_reads_back_and_is_bounded(self):
        import held_lights as hl
        record = {'offset': [0.0, 0.7493, -0.1207, 0.0, 0.0, -90.0],
                  'flames': [[-4.6282, 2.0771, 5.2172, 0.8, 0.625, 0.875, 0.092]] * 3}
        text = hl.text(record)
        self.assertTrue(text.startswith('AWHL1\noffset 0.0000 0.7493 -0.1207'))
        back = hl.read(text.encode('ascii'))
        self.assertEqual(len(back['flames']), 3)
        self.assertAlmostEqual(back['offset'][5], -90.0)
        five = dict(record, flames=record['flames'] * 2)
        self.assertEqual(len(hl.read(hl.text(five).encode())['flames']), hl.FLAMES)   # cut to what the engine takes
        with self.assertRaises(ValueError):
            hl.read(b'AWHL2\noffset 0 0 0 0 0 0\n')
        self.assertEqual(hl.sidecar_path('progs/items/m0123456789abcdef.mdl'), 'progs/items/m0123456789abcdef.hld')
        with self.assertRaises(ValueError):
            hl.sidecar_path('progs/items/m01.awt')

    def test_the_engine_takes_as_many_flames(self):
        import held_lights as hl
        self.assertEqual(int(re.search(r'#define AW_HELD_FLAMES (\d+)', code('aw_torch.h')).group(1)), hl.FLAMES)

    def test_carried_place_is_the_rigid_attachment(self):
        """The item model (point + BoneOffset) turned by the place equals the mesh carried as a light
        (npc_geometry.rigid_attachment: p @ R + bo)."""
        import numpy as np
        import held_lights as hl
        from npc_items import angle_matrix
        bo = np.array([-11.47, 1.26, -1.74])
        place = hl.carried_place(bo)
        self.assertEqual([round(v, 4) for v in place[3:]], [0.0, 0.0, -90.0])
        # the builder's carried-light turn, read from npc_geometry.rigid_attachment (not imported: its package import
        # order differs between test runs)
        self.assertIn('matrix[:3,:3]=((1,0,0),(0,0,-1),(0,1,0))',
                      (ROOT / 'tools/npc_geometry.py').read_text(encoding='utf-8'))
        m = np.eye(4)
        m[:3, :3] = hl.CARRIED_TURN
        m[3, :3] = bo
        rot = angle_matrix(*place[3:])
        for p in ([0.0, 0.0, 22.2], [3.0, -4.0, 5.0]):
            p = np.array(p)
            q = (p + bo) * hl.SCALE                               # the item model's vertex
            held = q @ rot + np.array(place[:3])
            want = (np.append(p, 1.0) @ m)[:3] * hl.SCALE
            self.assertTrue(np.allclose(held, want, atol=1e-6), (held, want))

    def test_catalogue_flags(self):
        import held_lights as hl
        self.assertEqual(hl.catalogue_flags(0x1 | 0x2 | 0x10 | 0x40), 0x80 | 1 | 2)   # the candles: fire, slow flicker
        self.assertEqual(hl.catalogue_flags(0x1 | 0x2), 0x80)                          # the paper lantern: steady
        self.assertEqual(hl.catalogue_flags(0x80), 0x81)                               # pulse
        engine = code('aw_inventory.h')
        self.assertIn('#define AW_LIGHT_FLAGS_SET 0x80', engine)
        self.assertIn('#define AW_LIGHT_FLICKER 1', engine)
        self.assertIn('#define AW_LIGHT_FIRE 2', engine)


class Wiring(unittest.TestCase):
    def test_catalogue_writes_byte_511_and_the_files(self):
        source = (ROOT / 'tools/prepare_inventory.py').read_text(encoding='utf-8')
        self.assertIn("struct.pack('<i3BB',light['time'],*light['colour'],catalogue_flags(", source)
        self.assertIn('sidecar_path(model)', source)
        self.assertIn('torch_mesh', source)          # the torch's mesh keeps the torch's own path

    def test_the_torch_stays_the_torch(self):
        torch = code('aw_torch.c')
        self.assertIn('return torch_assets && light_lit() && !held_own();', torch)
        # the torch's own light, unchanged; the held light scaled from it
        self.assertIn('else light->radius=AW_TorchLightRadius()+(torch?radius[phase()]-144:0);', torch)
        self.assertIn('light->radius=own->radius*(own->flicker?radius[phase()]/144.f:1);', torch)

    def test_both_views_draw_the_light_itself(self):
        hands, view, r_main = code('aw_hand_models.c'), code('aw_view.c'), code('r_main.c')
        self.assertIn('aw_hand_parts_apply(race,female,AW_HAND_LIGHT_STANCE,cl.viewent.frame)', hands)
        self.assertIn('AW_BlockCompose(origin,angles,l->offset,light_pose,light_pose+3);', hands)
        self.assertIn('if(AW_HandLightItemApply()){', r_main)
        self.assertIn('#define HAND_PART_STANCES 8', view)
        self.assertIn('AW_BlockCompose(origin,angles,light->offset,out->origin,out->angles);', view)
        self.assertIn('aw_items_player_layer=player_light_layer;', view)
        self.assertIn('AW_HeldLightDraw ();', code('view.c'))
        self.assertIn('AW_HeldFlameDraw(at[i],shape,0);', code('aw_guard_torch.c'))


if __name__ == '__main__':
    unittest.main()
