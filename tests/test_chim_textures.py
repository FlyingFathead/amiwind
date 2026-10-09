# SPDX-License-Identifier: GPL-3.0-only
"""CHIM-TEXTURE-SPECKS-33: a CHIM texture equals the legacy texture for the same source.

The legacy chain quantizes a material (prepare_mesh_bsp.material_image), writes it into a region
map, and the image's sky overlay (sky_palette_overlay.convert) moves every pixel off the seven
banked palette entries before repainting them as sky colours. CHIM textures must take the same
path, or their texels on banked entries show as bright specks. Synthetic data only."""
import ast
import struct
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import sky_palette_overlay as overlay  # noqa: E402
from chim.build import sky_bank_textures  # noqa: E402


def banked_safe_palette():
    """Distinct colours; each banked entry one unit off its replacement (the overlay's guard holds)."""
    rng = np.random.default_rng(3)
    pal = rng.integers(0, 250, size=(256, 3)).astype(int)
    for i, (target, _) in overlay.BANK.items():
        pal[i] = pal[target] + [2, 0, 0]
    return bytes(pal.astype(np.uint8).flatten())


def bsp_with(mip):
    """A BSP29 holding one miptex in its texture lump (other lumps empty), as a region map does."""
    lump = struct.pack('<ii', 1, 8) + mip
    head = struct.pack('<i', 29)
    lumps = [(124, 0)] * 15
    lumps[2] = (124, len(lump))
    return head + b''.join(struct.pack('<ii', *x) for x in lumps) + lump


class TextureParityTests(unittest.TestCase):
    def setUp(self):
        from PIL import Image
        self.palette = banked_safe_palette()
        self.pal = Image.new('P', (1, 1))
        self.pal.putpalette(self.palette)
        self.assertTrue(overlay.bank_safe(self.palette))

    def legacy_texture(self, mip):
        """The legacy chain: the miptex in a map, through the image's sky overlay."""
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / 'id1'
            (src / 'gfx').mkdir(parents=True)
            (src / 'maps').mkdir()
            (src / 'gfx/palette.lmp').write_bytes(self.palette)
            (src / 'maps/t.bsp').write_bytes(bsp_with(mip))
            overlay.convert(src, Path(tmp) / 'out')
            raw = (Path(tmp) / 'out/maps/t.bsp').read_bytes()
        return raw[124 + 8:]

    def test_chim_texture_equals_legacy_texture(self):
        # The image comes from the shared quantizer (test_one_quantization_function); here a texture
        # whose texels sit on each banked entry and its neighbours, as quantization leaves them.
        from PIL import Image
        from prepare_quake import miptex
        for banked in overlay.BANK:
            with self.subTest(banked=banked):
                pixels = np.full((32, 32), banked, np.uint8)
                pixels[::3, ::5] = overlay.BANK[banked][0]
                pixels[1::7, ::2] = 7
                im = Image.fromarray(pixels, 'P')
                im.putpalette(self.palette)
                mip = miptex('surface0', im)
                legacy = self.legacy_texture(mip)
                chim = sky_bank_textures({'k': {'miptex': mip}}, self.palette)['k']['miptex']
                self.assertEqual(chim, legacy)
                self.assertNotIn(banked, set(chim[40:]))
                self.assertIn(7, set(chim[40:]))                      # other entries stay as they are

    def test_unsafe_palette_is_left_alone(self):
        grey = bytes(v for i in range(256) for v in (i // 4 * 4,) * 3)
        self.assertFalse(overlay.bank_safe(grey))
        mip = struct.pack('<16s6I', b'x', 16, 16, 40, 296, 360, 376) + bytes([83]) * (256 + 64 + 16 + 4)
        self.assertEqual(sky_bank_textures({'k': {'miptex': mip}}, grey)['k']['miptex'], mip)

    def test_remap_covers_every_mip_level(self):
        pixels = (bytes(sorted(overlay.BANK)) * 64)[:256 + 64 + 16 + 4]
        mip = struct.pack('<16s6I', b'x', 16, 16, 40, 296, 360, 376) + pixels
        out = overlay.remap_miptex(mip)
        self.assertEqual(out[:40], mip[:40])
        self.assertEqual(len(out), len(mip))
        self.assertFalse(set(out[40:]) & set(overlay.BANK))
        self.assertEqual(out[40:], pixels.translate(overlay.bank_mapping()))

    def test_one_quantization_function(self):
        # the legacy converter's texture() and CHIM's texture unit call prepare_mesh_bsp.material_image
        text = (ROOT / 'tools/prepare_mesh_bsp.py').read_text(encoding='utf-8')
        tree = ast.parse(text)
        append = next(f for f in ast.walk(tree) if isinstance(f, ast.FunctionDef) and f.name == '_append_meshes')
        inner = next(f for f in ast.walk(append) if isinstance(f, ast.FunctionDef) and f.name == 'texture')
        calls = [n.func.id for n in ast.walk(inner) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
        self.assertEqual(calls.count('material_image'), 2)
        self.assertNotIn('quantize', ast.unparse(inner))
        chim = (ROOT / 'tools/chim/models.py').read_text(encoding='utf-8')
        self.assertIn('from prepare_mesh_bsp import material_image', chim)
        self.assertNotIn('.quantize(', chim)


if __name__ == '__main__':
    unittest.main()
