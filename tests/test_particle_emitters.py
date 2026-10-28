# SPDX-License-Identifier: GPL-3.0-only
"""MESH-PARTICLE-EMITTERS and WEATHER-RAIN: the emitter sweep's kinds, the smoke table (world/smoke.aws) the engine
reads, the smoke puff sprite, and the engine's falling weather and smoke wiring (aw_atmos.c)."""
import re
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
SRC = ROOT / 'engine' / 'aga' / 'src'


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8'), flags=re.S)


class EmitterKindTests(unittest.TestCase):
    def test_the_particle_texture_decides_first(self):
        from particle_emitters import kind_of
        # a fire's spray emitter draws the fire texture, its ash emitter the fire's ash
        self.assertEqual(kind_of('SuperSpray01 Emitter', 'tx_firealpha10.tga', 'meshes/l/light_fire.nif'), 'fire')
        self.assertEqual(kind_of('ash Emitter', 'tx_fireash00.tga', 'meshes/l/light_fire.nif'), 'fire ash')
        self.assertEqual(kind_of('chimney_smoke02 Emitter', 'tx_smokealpha00a.tga', 'meshes/chimney_smoke02.nif'), 'smoke')
        self.assertEqual(kind_of('Ex_volcano_steam Emitter', 'tx_alpha_steam00.tga', 'x'), 'steam')
        self.assertEqual(kind_of('x Emitter', 'tx_waterfall_mist_01.tga', 'x'), 'spray')
        # no texture: the node, then the mesh
        self.assertEqual(kind_of('Smoke Emitter', '', 'meshes/l/light_torch_01.nif'), 'smoke')
        self.assertEqual(kind_of('Emitter', '', 'meshes/l/light_com_candle_06.nif'), 'fire')
        self.assertEqual(kind_of('Emitter', '', 'meshes/x/thing.nif'), 'other')


class SmokeTableTests(unittest.TestCase):
    def test_row_layout_matches_the_engine(self):
        from particle_emitters import SMOKE_ROW, SMOKE_MAGIC, read_smoke_table
        self.assertEqual(SMOKE_ROW.size, 26)
        self.assertIn('#define SMOKE_ROW %d' % SMOKE_ROW.size, (SRC / 'aw_atmos.c').read_text(encoding='utf-8'))
        rows = [(-3, -2, -20000.0, -14000.0, 900.0, 32, 134, 120, 40, 173, 172, 173, 1),
                (-3, -1, -20100.0, -9000.0, 800.0, 45, 209, 96, 40, 173, 172, 173, 1)]
        raw = SMOKE_MAGIC + struct.pack('<I', 2) + b''.join(SMOKE_ROW.pack(*r) for r in rows)
        got = read_smoke_table(raw)
        self.assertEqual(got[0]['cx'], -3); self.assertEqual(got[1]['cy'], -1); self.assertEqual(got[0]['rise'], 134)
        with self.assertRaisesRegex(ValueError, 'wrong shape'):
            read_smoke_table(raw[:-1])

    def test_no_game_data_gives_an_empty_table_and_no_sprite(self):
        from particle_emitters import smoke_table, smoke_sprite, read_smoke_table
        with tempfile.TemporaryDirectory() as scratch:
            raw, report = smoke_table(scratch)
            self.assertEqual(read_smoke_table(raw), []); self.assertEqual(report['rows'], 0)
            self.assertIsNone(smoke_sprite(scratch, bytes(768)))

    def test_the_puff_sprite_is_a_quake_sprite_with_thinning_frames(self):
        from PIL import Image
        import io
        import particle_emitters as P
        image = Image.new('RGBA', (64, 64), (200, 200, 200, 0))
        for x in range(64):
            for y in range(64):
                d = ((x - 32) ** 2 + (y - 32) ** 2) ** .5
                image.putpixel((x, y), (180, 180, 180, max(0, 255 - int(d * 8))))
        buf = io.BytesIO(); image.save(buf, 'TGA')
        palette = bytes(v for i in range(256) for v in (i, i, i))
        with tempfile.TemporaryDirectory() as scratch:
            (Path(scratch) / 'Textures').mkdir()
            (Path(scratch) / 'Textures' / (P.SMOKE_SPRITE_TEXTURE + '.tga')).write_bytes(buf.getvalue())
            raw = P.smoke_sprite(scratch, palette)
        self.assertEqual(raw[:8], b'IDSP\x01\x00\x00\x00')
        size, frames = P.SMOKE_SPRITE_SIZE, P.SMOKE_SPRITE_FRAMES
        self.assertEqual(struct.unpack_from('<i', raw, 24)[0], frames)
        self.assertEqual(len(raw), 36 + frames * (20 + size * size))
        shown = [sum(1 for b in raw[36 + k * (20 + size * size) + 20:36 + (k + 1) * (20 + size * size)] if b != 255)
                 for k in range(frames)]
        self.assertGreater(shown[0], 0)
        self.assertEqual(shown, sorted(shown, reverse=True))      # each frame keeps fewer texels: the puff thins


class AtmosWiringTests(unittest.TestCase):
    def test_engine_wiring(self):
        atmos = code('aw_atmos.c')
        self.assertIn('static cvar_t aw_atmos={"aw_atmos","2",true};', atmos)    # smoke on, falling weather off
        self.assertIn('kind=AW_WeatherFalling(&strength);', atmos)
        self.assertIn('AW_FxParticles(at,n,PRECIP_HALF_WIDTH,vel,rand_v,life,r,g,b,0);', atmos)
        self.assertIn('AW_FxSprite(smoke_model,at,s->size*0.25f*scale,frame)', atmos)
        self.assertIn('!R_SkyExterior()', atmos)
        self.assertIn('AW_AtmosUpdate ();', (SRC / 'cl_main.c').read_text(encoding='utf-8'))
        self.assertIn('AW_AtmosInit();', (SRC / 'r_sky.c').read_text(encoding='utf-8'))
        self.assertIn('aw_atmos.c', (ROOT / 'engine' / 'aga' / 'Makefile').read_text(encoding='utf-8'))
        weather = code('aw_weather.c')
        self.assertIn('falling=AW_WeatherPrecip(state.current,state.next,state.progress,&falling_strength);', weather)
        from prepare_world_ui import WORLD_UI_FILES, OPTIONAL_WORLD_UI_FILES
        self.assertIn('smoke.aws', WORLD_UI_FILES); self.assertIn('smoke.spr', OPTIONAL_WORLD_UI_FILES)
        self.assertIn('"world/smoke.aws"', (SRC / 'aw_atmos.c').read_text(encoding='utf-8'))
        self.assertIn('"world/smoke.spr"', (SRC / 'aw_atmos.c').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
