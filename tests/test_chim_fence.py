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


class EngineSourceTests(unittest.TestCase):
    def test_prefix_and_flag(self):
        model = (SRC / 'd_fence.h').read_text(encoding='utf-8')     # not model.h: tools/edge_cache_heap.py pins it
        self.assertIn("#define AW_FENCE_TEXTURE_PREFIX\t'{'", model)
        self.assertRegex(model, r'#define SURF_DRAWFENCE\s+0x80')

    def test_faces_leave_the_edge_list_and_255_is_skipped(self):
        bsp = (SRC / 'r_bsp.c').read_text(encoding='utf-8')
        self.assertEqual(len(re.findall(r'R_FenceDivert \((?:psurf|surf)\)', bsp)), 4)
        draw = (SRC / 'd_fence.c').read_text(encoding='utf-8')
        self.assertIn('if (btemp != 255)', draw)
        self.assertIn('cvar_t\taw_fence = {"aw_fence", "0"};', draw)
        surf = (SRC / 'r_surf.c').read_text(encoding='utf-8')
        self.assertIn('pix == 255 ? 255 : colormap', surf)
        main = (SRC / 'r_main.c').read_text(encoding='utf-8')
        self.assertLess(main.index('r_fence_draw ();'), main.index('R_DrawEntitiesOnList (); AW_EndMark(1);'))
        self.assertIn('\td_fence.c \\\n', (ROOT / 'engine/aga/Makefile').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
