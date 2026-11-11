# SPDX-License-Identifier: GPL-3.0-only
"""See-through textures (ROOM-DECAL-ALPHA-62, CHIM-MODEL-FENCE-FACES-64): tools/chim/fence.py and the engine pass.

A texture whose alpha channel leaves texels under half alpha is quantized without palette index 255, its transparent
texels become 255 and its engine name starts with '{'; every other texture keeps its unit kind, key and bytes. The
engine keeps such faces off the edge list and draws them after the opaque world (engine/aga/src/d_fence.c)."""
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]     # src first: the mwad package, not tools/mwad.py
from chim import fence, units  # noqa: E402

SRC = ROOT / 'engine/aga/src'


def palette():
    from PIL import Image
    pal = Image.new('P', (1, 1))
    pal.putpalette([v for i in range(256) for v in (i, i, i)])
    return pal


class FenceImageTests(unittest.TestCase):
    def image(self, alpha, colour=(255, 255, 255), diffuse=(1., 1., 1.)):
        rgba = np.zeros((32, 32, 4), np.uint8)
        rgba[:, :, :3] = colour
        rgba[:, :, 3] = alpha
        model = {'materials': [{'texture_index': 0, 'diffuse': list(diffuse)}]}
        with mock.patch.object(fence, 'texture_rgba', return_value=rgba):
            return np.array(fence.fence_image(None, {'textures': [{}]}, model, 0, 32, palette()))

    def test_transparent_texels_are_255_and_no_other_texel_is(self):
        alpha = np.full((32, 32), 255, np.uint8)
        alpha[:, :16] = 0
        pixels = self.image(alpha)
        self.assertTrue((pixels[:, :12] == 255).all())
        self.assertTrue((pixels[:, 20:] != 255).all())      # white quantizes to 254 here, never 255

    def test_engine_names(self):
        self.assertEqual(fence.engine_name('fence', 0, 7), '{surface7')
        self.assertEqual(fence.engine_name('surface', 0, 7), 'surface7')
        self.assertEqual(fence.engine_name('surface', 3, 7), 'emit3_7')
        self.assertLess(len(fence.engine_name('fence', 0, 99999)), 16)

    def test_share(self):
        alpha = np.full((8, 8, 4), 255, np.uint8)
        alpha[0, 0, 3] = 0
        with mock.patch.object(fence, 'texture_rgba', return_value=alpha):
            fence._SHARE.clear()
            self.assertAlmostEqual(fence.transparent_share(None, {'sha256': 'x'}), 1 / 64)


class ArchivePairTests(unittest.TestCase):
    """CHIM-FENCE-WRONG-ARCHIVE-64: a texture in both the scenery and the flora index; the model reads its own."""

    def test_the_material_record_pairs_with_the_models_archive(self):
        import hashlib
        import struct
        import tempfile
        rgba = np.full((16, 16, 4), 255, np.uint8)
        rgba[:, :8, 3] = 0
        payload = struct.pack('>4sHH', b'RGBA', 16, 16) + rgba.tobytes()
        sha = hashlib.sha256(payload).hexdigest()
        with tempfile.TemporaryDirectory() as temp:
            scenery, flora = Path(temp) / 'scenery.mwpak', Path(temp) / 'flora.mwpak'
            scenery.write_bytes(b'\0' * 512 + payload)          # at 512 in the scenery archive
            flora.write_bytes(payload)                          # at 0 in the flora archive
            records = [{'offset': 512, 'bytes': len(payload), 'sha256': sha, 'source': 'tx_web.dds'},
                       {'offset': 0, 'bytes': len(payload), 'sha256': sha, 'source': 'tx_web.dds'}]
            model = {'_archive': str(flora), 'materials': [{'texture_index': 1, 'diffuse': [1, 1, 1]}]}
            fence._SHARE.clear()
            record = fence.material_record(records, model, 0)
            self.assertIs(record, records[1])
            self.assertTrue(fence.is_fence(model['_archive'], record))
            # the record found by hash (the scenery one) does not fit the flora archive, and the refusal names it
            fence._SHARE.clear()
            with self.assertRaises(ValueError) as caught:
                fence.is_fence(model['_archive'], records[0])
            self.assertIn('tx_web.dds at offset 512', str(caught.exception))
            self.assertIn('flora.mwpak', str(caught.exception))

    def test_the_builder_asks_with_the_materials_record(self):
        build = (ROOT / 'tools/chim/build.py').read_text(encoding='utf-8')
        self.assertIn('fence.is_fence(str(source_archive), fence.material_record(texture_records, model, material))',
                      build)
        self.assertNotIn('fence.is_fence(str(source_archive), texture_records[ti])', build)


class UnitKindTests(unittest.TestCase):
    def test_own_kind_keeps_the_texture_key_off_this_module(self):
        self.assertEqual(units.CODE_ENTRIES['texture'], [('tools/chim/models.py', 'texture_unit')])
        self.assertIn('texture-fence', units.CODE_ENTRIES)
        self.assertNotIn('tools/chim/fence.py', units.TOOLS['texture'])


def model_lumps(faces):
    """A one-model image: FACES = [(texinfo, numedges)], texinfo i uses local texture i."""
    import struct
    lumps = [bytearray() for _ in range(15)]
    for t in range(4):
        lumps[6] += struct.pack('<8f2i', *([0.0] * 8), t, 0)
    for texinfo, n in faces:
        first = len(lumps[13]) // 4
        lumps[13] += struct.pack('<%di' % n, *range(1, n + 1))
        lumps[7] += fence.FACE.pack(5, 0, first, n, texinfo, 0, 255, 255, 255, 96)
    lumps[14] += fence.MODEL.pack(*([0.0] * 9), 0, 0, 0, 0, 0, 0, len(faces))
    return lumps


class TwoSidedConverterTests(unittest.TestCase):
    """The converter route (build option --chim-fence-twosided-faces mirror): only see-through faces get a copy."""

    def test_only_fence_faces_get_a_mirrored_copy(self):
        lumps, added = fence.mirror_faces(model_lumps([(0, 4), (1, 3), (0, 5)]), {1})
        self.assertEqual(added, 1)
        faces = [fence.FACE.unpack_from(lumps[7], o) for o in range(0, len(lumps[7]), fence.FACE.size)]
        self.assertEqual(len(faces), 4)
        plane, side, first, n, texinfo = faces[3][:5]
        self.assertEqual((plane, side, n, texinfo, faces[3][-1]), (5, 1, 3, 1, 96))   # same plane, texels, light
        import struct
        self.assertEqual(struct.unpack_from('<3i', lumps[13], first * 4), (-3, -2, -1))  # the loop reversed
        self.assertEqual(fence.MODEL.unpack(bytes(lumps[14]))[15], 4)

    def test_no_fence_texture_leaves_the_bytes(self):
        original = model_lumps([(0, 4), (2, 3)])
        lumps, added = fence.mirror_faces(original, {1})
        self.assertEqual((added, [bytes(x) for x in lumps]), (0, [bytes(x) for x in original]))

    def test_the_option_is_off_by_default(self):
        self.assertEqual(fence.twosided_mode({}), 'off')
        self.assertEqual(fence.twosided_mode({'fence_twosided_faces': 'mirror'}), 'mirror')
        with self.assertRaises(ValueError):
            fence.twosided_mode({'fence_twosided_faces': 'both'})


class TwoSidedEngineTests(unittest.TestCase):
    """The engine route (aw_fence_twosided): a fence face the back-face test dropped still reaches the fence list;
    an ordinary face stays culled."""

    def test_back_faces_reach_the_fence_list_only_for_fence_faces(self):
        bsp = (SRC / 'r_bsp.c').read_text(encoding='utf-8')
        back = bsp[bsp.index('static int R_FenceBack'):]
        back = back[:back.index('\n}\n')]
        self.assertIn('if (!r_fence_twosided)\n\t\treturn 0;', back)
        self.assertIn('(psurf->flags & SURF_FENCEKNOWN) && !(psurf->flags & SURF_DRAWFENCE)', back)
        # the two brush model paths and both world back-face branches
        self.assertEqual(bsp.count('&& R_FenceBack (psurf))\n\t\t\tcontinue;'), 2)
        self.assertEqual(bsp.count('(void) R_FenceBack (surf);'), 2)
        # R_FenceDivert still sets SURF_DRAWFENCE only for '{' textures (ordinary faces return 0 and stay culled)
        self.assertIn('texture->name[0] == AW_FENCE_TEXTURE_PREFIX', bsp)

    def test_the_switch(self):
        draw = (SRC / 'd_fence.c').read_text(encoding='utf-8')
        self.assertIn('cvar_t\taw_fence_twosided = {"aw_fence_twosided", "0"};', draw)
        self.assertIn('r_fence_twosided = r_fence_cache_on && (aw_seethrough_material.value >= 2 || '
                      'aw_fence_twosided.value != 0);', draw)


class EngineSourceTests(unittest.TestCase):
    def test_prefix_and_flag(self):
        model = (SRC / 'd_fence.h').read_text(encoding='utf-8')     # not model.h: tools/edge_cache_heap.py pins it
        self.assertIn("#define AW_FENCE_TEXTURE_PREFIX\t'{'", model)
        self.assertRegex(model, r'#define SURF_DRAWFENCE\s+0x80')

    def test_faces_leave_the_edge_list_and_255_is_skipped(self):
        bsp = (SRC / 'r_bsp.c').read_text(encoding='utf-8')
        # the four front-face call sites and R_FenceBack (the two-sided route)
        self.assertEqual(len(re.findall(r'R_FenceDivert \((?:psurf|surf)\)', bsp)), 5)
        draw = (SRC / 'd_fence.c').read_text(encoding='utf-8')
        self.assertIn('if (btemp != 255)', draw)
        # the setting is aw_seethrough_material, on (1) by default since v0.0.64-dev4
        self.assertIn('cvar_t\taw_seethrough_material = {"aw_seethrough_material", "1"};', draw)
        # 2 = also seen from behind (the engine two-sided route); aw_fence_twosided 1 stays its old name
        self.assertIn('(aw_seethrough_material.value >= 2 || aw_fence_twosided.value != 0)', draw)
        cvar = (SRC / 'cvar.c').read_text(encoding='utf-8')
        self.assertIn('if(!strcmp(v->name,"aw_seethrough_material"))', cvar)
        # the quiet aliases aw_seethrough and aw_fence reach the same setting
        self.assertIn('!Q_strcasecmp(Cmd_Argv(0),"aw_seethrough") || !Q_strcasecmp(Cmd_Argv(0),"aw_fence")', cvar)
        self.assertIn("s[0]>='0' && s[0]<='2' && !s[1]", cvar)
        self.assertIn('--chim-fence-twosided-faces mirror', cvar)
        surf = (SRC / 'r_surf.c').read_text(encoding='utf-8')
        self.assertIn('pix == 255 ? 255 : colormap', surf)
        main = (SRC / 'r_main.c').read_text(encoding='utf-8')
        self.assertLess(main.index('r_fence_draw ();'), main.index('R_DrawEntitiesOnList (); AW_EndMark(1);'))
        self.assertIn('\td_fence.c \\\n', (ROOT / 'engine/aga/Makefile').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
