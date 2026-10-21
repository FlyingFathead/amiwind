# SPDX-License-Identifier: GPL-3.0-only
"""Scrolling textures (GHOSTFENCE-NO-ANIMATION-46): the scenery stage keeps a shape's NiUVController keys
(prepare_scenery.uv_scroll), and the CHIM builder draws such a shape as a Quake turbulent texture when the
build asks for it (uv_scroll 'turbulent', a build's default since v0.0.47); 'off' keeps the still texture of
before. In game, dbg ghostfence off (aw_ghostfence 0) draws turbulent textures straight and still."""
import os
import re
import shutil
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
for part in ('tools', 'src'):
    if str(ROOT / part) not in sys.path:
        sys.path.insert(0, str(ROOT / part))

from chim.format import texture_class  # noqa: E402
from chim.models import (TURBULENT_SIZE, TURBULENT_SIZES, UV_SCROLL, engine_texture_name,  # noqa: E402
                         material_texture_key, scrolls_turbulent)


class NiUVController(SimpleNamespace):
    pass


class NiAlphaController(SimpleNamespace):
    pass


def keys(*pairs):
    return SimpleNamespace(keys=[SimpleNamespace(time=t, value=v) for t, v in pairs])


def fence_shape():
    """The Ghostfence curtain's first layer (meshes/x/ex_gg_fence_s_01.nif): V moves 2 heights in 8 s, U sways."""
    data = SimpleNamespace(uv_groups=[keys((0, 0), (2, .05), (4, 0), (6, -.05), (8, 0)), keys((0, 0), (8, 2)),
                                      keys(), keys()])
    return SimpleNamespace(controller=NiAlphaController(next_controller=NiUVController(data=data, next_controller=None)))


def model(texture='Tx_GG_fence_01.tga', scroll=True):
    material = {'texture_source': texture, 'texture_index': 3, 'diffuse': [1.0, 1.0, 1.0], 'alpha': 0.5,
                'emissive': 3}
    if scroll:
        material['uv_scroll'] = {'u': [[0, 0], [8, 0]], 'v': [[0, 0], [8, 2.0]]}
    return {'source': 'meshes/x/ex_gg_fence_s_01.nif', 'materials': [material]}


class ScenerySideTests(unittest.TestCase):
    def test_controller_keys_are_kept(self):
        from prepare_scenery import uv_scroll
        scroll = uv_scroll(fence_shape())
        self.assertEqual(scroll['v'], [[0.0, 0.0], [8.0, 2.0]])
        self.assertEqual(scroll['u'][1], [2.0, 0.05])

    def test_no_controller_or_no_movement_is_none(self):
        from prepare_scenery import uv_scroll
        self.assertIsNone(uv_scroll(SimpleNamespace(controller=None)))
        still = SimpleNamespace(uv_groups=[keys((0, 0), (8, 0)), keys((0, 1), (8, 1)), keys(), keys()])
        self.assertIsNone(uv_scroll(SimpleNamespace(controller=NiUVController(data=still, next_controller=None))))


class ChimSideTests(unittest.TestCase):
    def test_off_is_the_default_and_keeps_the_key_of_before(self):
        self.assertEqual(UV_SCROLL[0], 'off')
        self.assertEqual(TURBULENT_SIZES, (16, 32, TURBULENT_SIZE))
        m = model()
        before = material_texture_key(m, 0, 64, False)
        self.assertEqual(before, (3, 64, (1.0, 1.0, 1.0), 3))
        self.assertEqual(material_texture_key(m, 0, 64, False, None, 'off'), before)

    def test_turbulent_marks_only_scrolling_shapes(self):
        key = material_texture_key(model(), 0, TURBULENT_SIZE, False, None, 'turbulent')
        self.assertEqual(key, (3, 64, (1.0, 1.0, 1.0), 0, 'turbulent'))
        self.assertEqual(material_texture_key(model(scroll=False), 0, 64, False, None, 'turbulent'),
                         (3, 64, (1.0, 1.0, 1.0), 3))

    def test_lava_and_small_textures_stay_still(self):
        self.assertFalse(scrolls_turbulent(model('Tx_lava_molten.tga')['materials'][0], 64, 'turbulent'))
        # Turbulent8 (d_scan.c) reads a 64 x 64 texture: 16 and 32 are tiled to it by the engine, larger stays still
        self.assertTrue(scrolls_turbulent(model()['materials'][0], 32, 'turbulent'))
        self.assertFalse(scrolls_turbulent(model()['materials'][0], 128, 'turbulent'))
        with self.assertRaises(ValueError):
            scrolls_turbulent(model()['materials'][0], 64, 'warp')

    def test_engine_name_is_a_quake_turbulent_name(self):
        name = engine_texture_name('turbulent', 0, 1234)
        self.assertEqual(name, '*scroll1234')
        self.assertLess(len(engine_texture_name('turbulent', 0, 99999999)), 16)
        self.assertEqual(texture_class(name), '*')
        self.assertEqual(engine_texture_name('surface', 3, 5), 'emit3_5')

    def test_setting_reaches_the_conversion(self):
        from chim.build import uv_scroll_mode
        self.assertEqual(uv_scroll_mode(None), 'off')
        self.assertEqual(uv_scroll_mode({'uv_scroll': 'turbulent'}), 'turbulent')
        with self.assertRaises(ValueError):
            uv_scroll_mode({'uv_scroll': 'warp'})
        import build
        on = build.chim_stage_options(build.parser().parse_args(['--chim-uv-scroll', 'turbulent']))
        self.assertEqual(on[on.index('--uv-scroll') + 1], 'turbulent')
        # turbulent is the default of a build since v0.0.47; off asks for the still texture of before
        default = build.chim_stage_options(build.parser().parse_args([]))
        self.assertEqual(default[default.index('--uv-scroll') + 1], 'turbulent')
        self.assertNotIn('--uv-scroll', build.chim_stage_options(build.parser().parse_args(['--chim-uv-scroll', 'off'])))


SRC = ROOT / 'engine' / 'aga' / 'src'


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class EngineTileTests(unittest.TestCase):
    def test_small_turbulent_textures_are_tiled_to_64(self):
        import test_aga_native_source as native
        native.NativeSourceTests().compile_run('aga_chim_turbulent_test.c', [SRC / 'chim' / 'chim_format.c'],
                                               cflags=['-fsanitize=undefined', '-fno-sanitize-recover=all',
                                                       '-I' + str(SRC / 'chim')])


class EngineWiringTests(unittest.TestCase):
    def test_the_chim_texture_loader_tiles_before_turbulent_drawing(self):
        code = re.sub(r'/\*.*?\*/', '', (SRC / 'chim' / 'chim_models.c').read_text(encoding='utf-8'), flags=re.S)
        loader = code[code.index('static texture_t *LoadTexture'):code.index('static texture_t *ResolveTexture')]
        self.assertIn('ChimFormat_TurbulentTile (mt->name, mt->width, mt->height)', loader)
        self.assertIn('ChimFormat_TileTurbulent (small, mt->width, mt->height, (byte *)(tx+1));', loader)
        self.assertIn('tx->width = tx->height = CHIM_TURB_SIZE;', loader)
        # model.c's own rule makes a '*' texture turbulent; d_edge.c draws it 64 texels wide
        self.assertIn('if (!Q_strncmp(out->texinfo->texture->name,"*",1))', (SRC / 'model.c').read_text(encoding='utf-8'))
        self.assertIn('cachewidth = 64;', (SRC / 'd_edge.c').read_text(encoding='utf-8'))

    def test_dbg_ghostfence_switches_the_ripple_off(self):
        strip = lambda name: re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8'), flags=re.S)
        self.assertIn('cvar_t\taw_ghostfence = {"aw_ghostfence","1"};', strip('r_main.c'))
        self.assertIn('Cvar_RegisterVariable (&aw_ghostfence);', strip('r_main.c'))
        self.assertIn('stillturbtable[i] = AMP;', strip('r_main.c'))
        self.assertIn('r_turb_sintable = aw_ghostfence.value ? sintable + ((int)(cl.time*SPEED)&(CYCLE-1)) : '
                      'stillturbtable;', strip('r_misc.c'))
        self.assertIn('"aw_ghostfence"', strip('aw_boolean.h'))
        catalogue = (ROOT / 'config' / 'debug-commands.txt').read_text(encoding='utf-8')
        self.assertIn('VIDEO|ghostfence|aw_ghostfence|', catalogue)


if __name__ == '__main__':
    unittest.main()
