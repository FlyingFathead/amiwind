# SPDX-License-Identifier: GPL-3.0-only
"""CHIM texture effects (.chimfx, tools/chim/texfx.py) and the sky-bank gate (CHIM-TEXTURE-SPECKS-33).

Default: no effect, so no texture changes and the validator refuses texels left on the sky bank.
Opt-in: autumn_glitter_leaves.chimfx puts the specks back on purpose, reproducibly. Synthetic data only."""
import inspect
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
from chim import texfx  # noqa: E402

SHIPPED = ROOT / 'tools/chim/effects/autumn_glitter_leaves.chimfx'


def safe_palette():
    """Distinct colours; each banked entry one unit off its replacement (the sky-bank guard holds)."""
    rng = np.random.default_rng(5)
    pal = rng.integers(0, 120, size=(256, 3)).astype(int)
    for i, (target, _) in overlay.BANK.items():
        pal[i] = pal[target] + [1, 0, 0]
    return bytes(pal.astype(np.uint8).flatten())


def miptex(w, h, fill=7):
    """A miptex of one colour with its four mip levels."""
    sizes = [(w >> k) * (h >> k) for k in range(4)]
    offs = [40 + sum(sizes[:k]) for k in range(4)]
    return struct.pack('<16s6I', b'surface0', w, h, *offs) + bytes([fill]) * sum(sizes)


def level(mip, k):
    w, h, *offs = struct.unpack_from('<6I', mip, 16)
    lw, lh = w >> k, h >> k
    return np.frombuffer(mip, np.uint8, lw * lh, offs[k]).reshape(lh, lw)


EFFECT = """effect = speckle
name = test_fx
colour = 255 174 66 1
density = 0.01
seed = 4
targets = ground|* textures/tx_a*
"""


class EffectFileTests(unittest.TestCase):
    def test_shipped_effect_reads(self):
        e = texfx.load_effect(SHIPPED)
        self.assertEqual((e['effect'], e['name'], e['size'], e['targets']), ('speckle', 'autumn_glitter_leaves', 1, ['*']))
        self.assertEqual([c[:3] for c in e['colours']], [(255, 174, 66), (255, 232, 160), (153, 38, 79)])
        self.assertAlmostEqual(e['density'], 0.02)
        self.assertEqual(texfx.effect_path('autumn_glitter_leaves'), SHIPPED)
        raw = SHIPPED.read_bytes()
        self.assertNotIn(b'\r', raw)

    def test_effects_library_is_distributed(self):
        # every shipped effect is in the public file list, and the release check accepts .chimfx there
        import release
        listed = set(release.allowed_files(ROOT))
        for path in (ROOT / 'tools/chim/effects').iterdir():
            self.assertIn(path.relative_to(ROOT).as_posix(), listed)
        self.assertEqual(release.CHIM_EFFECTS_DIR.as_posix(), 'tools/chim/effects')

    def test_bug_page_links_and_frames_resolve(self):
        # the "From bug to effect" section: frames are public PNGs, links reach the effect and its docs
        import re
        import release
        page = ROOT / 'docs/bugs/CHIM-TEXTURE-SPECKS-33.md'
        links = re.findall(r'\]\(([^)#:]+)(?:#[^)]*)?\)', page.read_text(encoding='utf-8'))
        for link in links:
            self.assertTrue((page.parent / link).resolve().is_file(), link)
        targets = {(page.parent / link).resolve().relative_to(ROOT).as_posix() for link in links}
        for name in ('tools/chim/effects/autumn_glitter_leaves.chimfx', 'tools/chim/effects/README.md',
                     'docs/chim/TEXTURE_EFFECTS.md'):
            self.assertIn(name, targets)
        frames = sorted(t for t in targets if t.startswith('docs/images/'))
        self.assertEqual(len(frames), 3)
        listed = set(release.allowed_files(ROOT))
        for name in frames:
            self.assertIn(name, release.DOCUMENTATION_IMAGES)
            self.assertIn(name, listed)
            self.assertLess((ROOT / name).stat().st_size, 150 * 1024)

    def test_bad_files_name_the_problem(self):
        bad = {
            'unknown key': EFFECT + 'glow = 1\n',
            'colour': EFFECT.replace('255 174 66 1', '255 174'),
            'density': EFFECT.replace('0.01', '0.5'),
            'missing seed': EFFECT.replace('seed = 4\n', ''),
            'effect:': EFFECT.replace('speckle', 'sparkle'),
            'twice': EFFECT + 'seed = 5\n',
            'name:': EFFECT.replace('test_fx', 'a b'),
            'size:': EFFECT + 'size = 9\n',
        }
        for word, text in bad.items():
            with self.subTest(word=word):
                with self.assertRaises(ValueError) as err:
                    texfx.parse_effect(text, 'x.chimfx')
                self.assertIn('x.chimfx', str(err.exception))


class SpeckleTests(unittest.TestCase):
    def setUp(self):
        self.palette = safe_palette()
        self.effect = texfx.parse_effect(EFFECT)

    def test_colours_land_on_the_shown_palette_including_the_sky_bank(self):
        # (255, 174, 66) is sky-bank entry 140's colour in the image; the build palette has nothing near it
        self.assertEqual(texfx.nearest_indices([(255, 174, 66), (255, 232, 160)], texfx.shown_palette(self.palette)),
                         [140, 83])

    def test_deterministic_density_and_stable_across_mips(self):
        mip = miptex(256, 256)
        a = texfx.speckle_miptex(mip, self.effect, 'ground|g1', self.palette)
        self.assertEqual(a, texfx.speckle_miptex(mip, self.effect, 'ground|g1', self.palette))
        self.assertNotEqual(a, texfx.speckle_miptex(mip, self.effect, 'ground|g2', self.palette))
        self.assertEqual(a[:40], mip[:40])
        self.assertEqual(len(a), len(mip))
        full = level(a, 0) == 140
        share = full.mean()
        self.assertGreater(share, 0.007)
        self.assertLess(share, 0.013)
        for k in (1, 2, 3):
            spots = level(a, k) == 140
            self.assertGreater(spots.sum(), 0)
            self.assertLess(abs(spots.mean() - share), 0.01)
            # every speck of a smaller level sits over a speck of the full-size texture
            ys, xs = np.nonzero(spots)
            for y, x in zip(ys, xs):
                self.assertTrue(full[y << k:(y + 1) << k, x << k:(x + 1) << k].any())

    def test_transparent_texels_stay(self):
        mip = miptex(64, 64, fill=255)
        self.assertEqual(texfx.speckle_miptex(mip, self.effect, 'ground|g1', self.palette), mip)

    def test_targets_and_default_off(self):
        textures = {
            ('ground', 'g1'): {'identity': 'ground|g1', 'miptex': miptex(64, 64), 'source': None},
            ('model', 3): {'identity': 'model|3|64', 'miptex': miptex(64, 64), 'source': 'textures/tx_a_wall.dds'},
            ('model', 4): {'identity': 'model|4|64', 'miptex': miptex(64, 64), 'source': 'textures/tx_b_wall.dds'},
        }
        same, record = texfx.apply_effects(textures, [], self.palette)
        self.assertIs(same, textures)
        self.assertEqual(record, [])
        out, record = texfx.apply_effects(textures, [self.effect], self.palette)
        self.assertEqual(record[0]['textures'], ['ground|g1', 'model|3|64'])
        self.assertEqual(out[('model', 4)], textures[('model', 4)])
        self.assertNotEqual(out[('model', 3)]['miptex'], textures[('model', 3)]['miptex'])


class BuilderTests(unittest.TestCase):
    def test_build_areas_applies_no_effect_by_default(self):
        from chim.build import build_areas
        self.assertEqual(inspect.signature(build_areas).parameters['texture_effects'].default, ())

    def test_builder_option_is_off_by_default_and_selectable(self):
        import build
        import build_font_options as options
        record = options.resolve_builder(build.parser().parse_args(['--builder', 'chim']))
        self.assertEqual(record['chim_texture_effects'], [])
        record = options.resolve_builder(build.parser().parse_args(
            ['--builder', 'chim', '--chim-texture-effect', 'autumn_glitter_leaves']))
        self.assertEqual([e['name'] for e in record['chim_texture_effects']], ['autumn_glitter_leaves'])
        args = build.parser().parse_args(['--builder', 'chim', '--chim-texture-effect', 'autumn_glitter_leaves'])
        args.data_files, args.sdk, args.workspace = Path('/owned'), Path('/sdk'), Path('/private/ws')
        args.builder_options = options.resolve_builder(args)
        from test_build_builder import RUN, TOOLS
        command = [str(p) for p in dict(build.commands(args, TOOLS, RUN))['chim']]
        self.assertEqual(Path(command[command.index('--texture-effect') + 1]), SHIPPED)
        args.builder_options = options.resolve_builder(build.parser().parse_args(['--builder', 'chim']))
        self.assertNotIn('--texture-effect', [str(p) for p in dict(build.commands(args, TOOLS, RUN))['chim']])

    def test_build_config_key(self):
        import build
        import build_font_options as options
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'build.json'
            path.write_text('{"builder":"chim","chim_texture_effects":["autumn_glitter_leaves"]}')
            record = options.resolve_builder(build.parser().parse_args(['--build-config', str(path)]))
            self.assertEqual(record['chim_texture_effects'][0]['name'], 'autumn_glitter_leaves')
            path.write_text('{"chim_texture_effects":"autumn_glitter_leaves"}')
            with self.assertRaises(ValueError):
                options.resolve_builder(build.parser().parse_args(['--build-config', str(path)]))


class SkyBankGateTests(unittest.TestCase):
    """CHIM-TEXTURE-SPECKS-33 regression gate: the first CHIM Balmora world kept 858 texels on the
    sky bank and every one showed as a bright speck; the validator now refuses that."""

    def test_banked_texels_fail_unless_an_effect_put_them_there(self):
        from chim.validate import sky_bank_texels
        palette = safe_palette()
        clean = {'name': 'ground|g1', 'miptex': miptex(32, 32)}
        dirty = {'name': 'model|9|32', 'miptex': overlay.remap_miptex(miptex(32, 32))[:40] + bytes([140]) * 3
                 + miptex(32, 32)[43:]}
        self.assertEqual(sky_bank_texels([clean], palette), [])
        self.assertEqual(sky_bank_texels([clean, dirty], palette), [('model|9|32', 3)])
        self.assertEqual(sky_bank_texels([clean, dirty], palette, exempt={'model|9|32'}), [])
        self.assertEqual(sky_bank_texels([dirty], None), [])                 # no palette: not checked

    def test_chim_build_validates_with_the_palette(self):
        text = (ROOT / 'tools/chim_build.py').read_text(encoding='utf-8')
        self.assertIn("'--palette', str(a.palette)", text)

    def test_effects_run_after_the_sky_bank_translation(self):
        text = (ROOT / 'tools/chim/build.py').read_text(encoding='utf-8')
        self.assertLess(text.index('textures = sky_bank_textures(textures, palette)'),
                        text.index("spec['textures'], record = apply_effects("))


if __name__ == '__main__':
    unittest.main()
