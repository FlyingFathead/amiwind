# SPDX-License-Identifier: GPL-3.0-only
"""The per-race hand catalogue is a builder step that matches the image (BUILD-HANDS-NOT-BUILT-32).

v0.0.31 ships 40 per-race hand models, gfx/hand-models.awh and
gfx/hand-torch.awt, converted against the image's final palette (scene palette,
reserved UI bank, sky colour bank) and never touched by the sky remap. These
tests cover the palette derivation, the verified install into an image stage,
its place after the sky step, and the sky overlay's handling of the catalogue.
"""
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]

import prepare_hand_catalog as catalog  # noqa: E402
import sky_palette_overlay as overlay  # noqa: E402


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def scene_palette():
    """A palette whose UI bank (225..253) still repeats colour 224."""
    raw = bytearray(bytes(range(256)) * 3)
    for i in range(225, 254):
        raw[i * 3:i * 3 + 3] = raw[224 * 3:224 * 3 + 3]
    return bytes(raw)


def make_catalog(root, palette, races=('nord', 'orc')):
    """A complete catalogue directory as prepare() writes it (synthetic models)."""
    out = root / 'catalog'
    (out / 'progs/hands').mkdir(parents=True)
    (out / 'gfx').mkdir()
    entries = []
    for race in races:
        for female in (False, True):
            hand, torch = catalog.model_paths(race, female)
            raw_hand, raw_torch = (race + hand).encode(), (race + torch).encode()
            (out / hand).write_bytes(raw_hand)
            (out / torch).write_bytes(raw_torch)
            entries.append({'race': race, 'female': female, 'hand_model': hand, 'torch_model': torch,
                            'hand_sha256': sha(raw_hand), 'torch_sha256': sha(raw_torch)})
    awh = catalog.pack_catalog(entries)
    (out / 'gfx/hand-models.awh').write_bytes(awh)
    (out / 'gfx/hand-torch.awt').write_bytes(b'emitter')
    report = {'format': 'AWH1', 'entries': entries, 'catalog_sha256': sha(awh),
              'torch_metadata_sha256': sha(b'emitter'), 'palette_sha256': sha(palette)}
    (out / 'hand-catalog-report.json').write_text(json.dumps(report), encoding='utf-8')
    return out


def stage(root, palette):
    id1 = root / 'id1'
    (id1 / 'gfx').mkdir(parents=True)
    (id1 / 'gfx/palette.lmp').write_bytes(palette)
    return id1


class RuntimePalette(unittest.TestCase):
    def test_reserves_ui_bank_then_applies_sky_bank(self):
        reserved = bytes(reversed(scene_palette()))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'palette.lmp'
            path.write_bytes(scene_palette())
            with patch('ui_palette.reserved_palette', return_value=(reserved, {})) as reserve, \
                 patch.object(overlay, 'EXPECTED_PALETTE', sha(reserved)):
                result = catalog.runtime_palette(Path(tmp), path)
            reserve.assert_called_once()
            self.assertEqual(result, overlay.banked_palette(reserved))
            self.assertNotEqual(result, reserved)

    def test_scene_with_ui_receipt_is_not_reserved_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'palette.lmp'
            raw = scene_palette()
            path.write_bytes(raw)
            (Path(tmp) / 'ui-palette.json').write_text(json.dumps({'palette_sha256': sha(raw)}), encoding='utf-8')
            with patch('ui_palette.reserved_palette') as reserve:
                # Not the approved sky input: no sky bank either (other sky paths keep their palette).
                self.assertEqual(catalog.runtime_palette(Path(tmp), path), raw)
            reserve.assert_not_called()

    def test_sky_bank_is_one_implementation(self):
        raw = scene_palette()
        banked = overlay.banked_palette(raw)
        for i, (_, rgb) in overlay.BANK.items():
            self.assertEqual(banked[i * 3:i * 3 + 3], bytes(rgb))
        changed = {i for i in range(256) if banked[i * 3:i * 3 + 3] != raw[i * 3:i * 3 + 3]}
        self.assertLessEqual(changed, set(overlay.BANK))

    def test_prepare_converts_with_and_records_the_runtime_palette(self):
        final = overlay.banked_palette(scene_palette())
        used = []

        def hands(assets, kinds, palette, *args):
            used.append(palette)
            return b'hand', {'sha256': sha(b'hand'), 'clips': {'idle': 8}}

        def torch(data, stage, **kwargs):
            used.append((stage / 'gfx/palette.lmp').read_bytes())
            (stage / 'progs').mkdir()
            (stage / 'progs/v_torch.mdl').write_bytes(b'torch')
            (stage / 'gfx/torch.awt').write_bytes(b'emitter')
            return {'files': {'progs/v_torch.mdl': sha(b'torch')}}

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'palette.lmp').write_bytes(scene_palette())
            with patch.object(catalog, 'TorchSource') as source, \
                 patch.object(catalog, 'first', return_value=struct.pack('<16xI', 1)), \
                 patch.object(catalog, 'bake_appearance', side_effect=hands), \
                 patch.object(catalog, 'prepare_torch', side_effect=torch), \
                 patch.object(catalog, 'runtime_palette', return_value=final):
                source.return_value.kinds = {'RACE': {'nord': object()}}
                result = catalog.prepare(root / 'owned', root / 'palette.lmp', root / 'out', runtime=True, jobs=1)
        self.assertEqual(used, [final] * 4)
        self.assertEqual(result['palette_sha256'], sha(final))
        self.assertEqual(result['scene_palette_sha256'], sha(scene_palette()))
        self.assertTrue(result['runtime_palette'])


class Install(unittest.TestCase):
    def test_installs_every_file_when_palette_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = make_catalog(root, scene_palette())
            id1 = stage(root, scene_palette())
            result = catalog.install(out, id1)
            self.assertEqual((result['files'], result['entries']), (10, 4))
            for path in ('progs/hands/nord_m.mdl', 'progs/hands/orc_f_t.mdl', 'gfx/hand-models.awh', 'gfx/hand-torch.awt'):
                self.assertEqual((id1 / path).read_bytes(), (out / path).read_bytes())

    def test_other_palette_installs_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = make_catalog(root, scene_palette())
            id1 = stage(root, overlay.banked_palette(scene_palette()))
            with self.assertRaisesRegex(ValueError, 'another palette'):
                catalog.install(out, id1)
            self.assertFalse((id1 / 'progs').exists())

    def test_changed_file_or_existing_target_installs_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = make_catalog(root, scene_palette())
            id1 = stage(root, scene_palette())
            (out / 'progs/hands/orc_m.mdl').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'differs from its report'):
                catalog.install(out, id1)
            self.assertFalse((id1 / 'progs').exists())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = make_catalog(root, scene_palette())
            id1 = stage(root, scene_palette())
            (id1 / 'gfx/hand-torch.awt').write_bytes(b'old')
            with self.assertRaisesRegex(ValueError, 'already has'):
                catalog.install(out, id1)
            self.assertFalse((id1 / 'progs').exists())

    def test_unsafe_model_path_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = make_catalog(root, scene_palette())
            report = json.loads((out / 'hand-catalog-report.json').read_text())
            report['entries'][0]['hand_model'] = '../progs/hands/nord_m.mdl'
            (out / 'hand-catalog-report.json').write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, 'model path'):
                catalog.install(out, stage(root, scene_palette()))


class ImageOrder(unittest.TestCase):
    def test_installed_after_the_sky_bank_and_before_the_final_gates(self):
        source = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        finalize = source[source.index('def finalize_image(args):'):]
        sky = finalize.index('prepare_staged_sky(boot')
        install = finalize.index('install_hand_catalog(args.hand_catalog')
        guard = finalize.index('prepare_guard_torches(args.data_files')
        self.assertLess(sky, install)
        self.assertLess(install, guard)
        image = source[source.index('def image(args):'):source.index('def finalize_image(args):')]
        self.assertNotIn('install_hand_catalog', image)


class SkyOverlayKnowsTheCatalogue(unittest.TestCase):
    def test_hand_catalogue_has_no_pixels_and_head_previews_still_do(self):
        entries = [{'race': 'nord', 'female': False, 'hand_model': 'progs/hands/nord_m.mdl',
                    'torch_model': 'progs/hands/nord_m_t.mdl'}]
        awh = catalog.pack_catalog(entries)
        self.assertEqual(overlay.spans(awh, 'gfx/hand-models.awh'), ([], 'hand model catalogue (paths only)'))
        with self.assertRaisesRegex(ValueError, 'Invalid hand catalogue'):
            overlay.spans(awh[:-1], 'gfx/hand-models.awh')
        head = b'AWH1' + struct.pack('<H', 1) + bytes(82)
        self.assertEqual(overlay.spans(head, 'character/h001.awh'), ([(24, 64)], 'indexed pixels'))


if __name__ == '__main__':
    unittest.main()
