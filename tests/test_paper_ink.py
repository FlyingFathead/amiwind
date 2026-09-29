"""Synthetic coverage, option-precedence and paper-source regression tests."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import build
import build_font_options as options
import prepare_reading as reading
import prepare_ui as ui


def synthetic_fonts(root):
    data = root / 'Data Files'
    fonts = data / 'Fonts'
    fonts.mkdir(parents=True)
    (data / 'Morrowind.esm').write_bytes(b'fixture')
    (data / 'Morrowind.bsa').write_bytes(b'fixture')
    name = 'Magic_Cards_Regular_0_Lod_A'
    header = struct.pack('<fII', 12, 1, 1) + (name.encode() + b'\0').ljust(284, b'\0')
    glyph = [0.0] * 14
    glyph[3] = glyph[6] = 1.0
    glyph[9:14] = [4., 2., 0., 1., 12.]
    fnt = fonts / 'Magic_Cards_Regular.fnt'
    fnt.write_bytes(header + struct.pack('<14f', *glyph) * 256)
    rgba = b''.join(bytes([255, 255, 255, a]) for a in [0, 50, 100, 150, 200, 255, 85, 170])
    (fonts / (name + '.tex')).write_bytes(struct.pack('<II', 4, 2) + rgba)
    return data, fnt


class PaperInkTests(unittest.TestCase):
    def test_filled_changes_coverage_not_geometry_or_ui_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, fnt = synthetic_fonts(Path(tmp))
            ordinary = ui.pack_font(fnt, 12)
            original = ui.pack_font(fnt, 12, paper_ink='original')
            filled = ui.pack_font(fnt, 12, paper_ink='filled')
            self.assertEqual(ordinary, original)
            self.assertEqual(ordinary[:2056], filled[:2056])
            self.assertEqual(len(ordinary), len(filled))
            self.assertNotEqual(ordinary[2056:], filled[2056:])
            a = ui.OriginalFont(fnt).bake(12)[65]['mask']
            b = ui.OriginalFont(fnt).bake(12, paper_ink='filled')[65]['mask']
            self.assertTrue(all(y >= x for x, y in zip(a.tobytes(), b.tobytes())))
            self.assertEqual(b.getpixel((0, 0)), 0)
            for size in (12, 14, 16):
                self.assertEqual(ui.pack_font(fnt, size), ui.pack_font(fnt, size, paper_ink='original'))

    def test_preview_shades_preserve_transparent_pixels_at_every_alpha(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, fnt = synthetic_fonts(Path(tmp))
            raw = bytearray(fnt.read_bytes())
            glyph = [0.0] * 14
            glyph[3] = glyph[6] = 1.0
            glyph[9:14] = [16., 16., 0., 1., 12.]
            raw[296:] = struct.pack('<14f', *glyph) * 256
            fnt.write_bytes(raw)
            atlas = fnt.parent / 'Magic_Cards_Regular_0_Lod_A.tex'
            rgba = b''.join(bytes([255, 255, 255, alpha]) for alpha in range(256))
            atlas.write_bytes(struct.pack('<II', 16, 16) + rgba)
            font = ui.OriginalFont(fnt)
            original = font.bake(12)[65]['mask'].tobytes()
            filled = font.bake(12, paper_ink='filled')[65]['mask'].tobytes()
            expected = bytes(0 if a < 43 else 85 if a < 80 else 170 if a < 190 else 255
                             for a in range(256))
            self.assertEqual(filled, expected)
            self.assertEqual([x == 0 for x in original], [x == 0 for x in filled])
            self.assertTrue(all(y >= x for x, y in zip(original, filled)))

    def test_unknown_ink_mode_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, fnt = synthetic_fonts(Path(tmp))
            with self.assertRaisesRegex(ValueError, 'Bitmap paper ink'):
                ui.pack_font(fnt, 12, paper_ink='typo')

    def test_missing_ttfs_default_to_filled_paper_without_touching_ui(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()) as log:
            root = Path(tmp)
            data, fnt = synthetic_fonts(root)
            scene = root / 'scene'
            gfx = scene / 'id1/gfx'
            gfx.mkdir(parents=True)
            for size in (12, 14, 16):
                (gfx / f'magic{size}.awf').write_bytes(ui.pack_font(fnt, size))
            before = {p.name: p.read_bytes() for p in gfx.glob('magic*.awf')}
            report = reading.prepare_paper_font(data, scene)
            self.assertEqual(report['source_mode'], 'bitmap')
            self.assertEqual(report['effective_paper_ink'], 'filled')
            self.assertEqual((gfx / 'paper12.awf').read_bytes(), ui.pack_font(fnt, 12, paper_ink='filled'))
            self.assertFalse((gfx / 'book12.awf').exists())
            self.assertEqual(before, {p.name: p.read_bytes() for p in gfx.glob('magic*.awf')})
            self.assertEqual(report, json.loads((gfx / 'paper-font-conversion.json').read_text()))
            self.assertIn('reading uses gfx/paper12.awf', log.getvalue())

    def test_original_option_removes_stale_filled_and_ttf_assets(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            root = Path(tmp)
            data, _ = synthetic_fonts(root)
            scene = root / 'scene'
            reading.prepare_paper_font(data, scene)
            gfx = scene / 'id1/gfx'
            (gfx / 'book12.awf').write_bytes(b'old TTF')
            report = reading.prepare_paper_font(data, scene, 'original')
            self.assertFalse((gfx / 'book12.awf').exists())
            self.assertFalse((gfx / 'paper12.awf').exists())
            self.assertEqual(report['runtime_asset'], 'gfx/magic12.awf')
            self.assertEqual(report['expected_awf_sha256'], report['ordinary_awf_sha256'])

    def test_ttf_is_preferred_and_byte_identical_for_both_ink_options(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            root = Path(tmp)
            data, fnt = synthetic_fonts(root)
            (data / 'BookArt').mkdir()
            (data / 'BookArt/Magic Cards.ttf').write_bytes(b'ttf fixture')
            expected = ui.pack_font(fnt, 12)
            scene = root / 'scene'
            (scene / 'id1/gfx').mkdir(parents=True)
            (scene / 'id1/gfx/paper12.awf').write_bytes(b'stale')
            with patch.object(reading, 'pack_truetype', return_value=expected) as ttf, \
                 patch.object(reading, 'pack_font', side_effect=AssertionError('TTF must not use bitmap')):
                for choice in ('filled', 'original'):
                    report = reading.prepare_paper_font(data, scene, choice)
                    self.assertEqual(report['effective_paper_ink'], 'not applied (TTF)')
                    self.assertEqual((scene / 'id1/gfx/book12.awf').read_bytes(), expected)
                    self.assertFalse((scene / 'id1/gfx/paper12.awf').exists())
                self.assertEqual(ttf.call_count, 2)

    def test_invalid_ttf_uses_same_filled_fallback(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            root = Path(tmp)
            data, fnt = synthetic_fonts(root)
            (data / 'BookArt').mkdir()
            (data / 'BookArt/Magic Cards.ttf').write_bytes(b'invalid font')
            scene = root / 'scene'
            report = reading.prepare_paper_font(data, scene)
            self.assertEqual(report['source_mode'], 'bitmap-fallback')
            self.assertTrue(report['ttf_error'])
            self.assertEqual((scene / 'id1/gfx/paper12.awf').read_bytes(), ui.pack_font(fnt, 12, paper_ink='filled'))

    def test_no_usable_source_fails_before_overwriting_existing_assets(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            root = Path(tmp)
            data, fnt = synthetic_fonts(root)
            fnt.unlink()
            scene = root / 'scene'
            gfx = scene / 'id1/gfx'
            gfx.mkdir(parents=True)
            for name in ('book12.awf', 'paper12.awf'):
                (gfx / name).write_bytes(b'preserved failed-run evidence')
            with self.assertRaisesRegex(ValueError, 'No usable Magic Cards'):
                reading.prepare_paper_font(data, scene)
            for name in ('book12.awf', 'paper12.awf'):
                self.assertEqual((gfx / name).read_bytes(), b'preserved failed-run evidence')

    def test_write_failure_is_not_misreported_as_missing_ttf(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data, fnt = synthetic_fonts(root)
            (data / 'BookArt').mkdir()
            (data / 'BookArt/Magic Cards.ttf').write_bytes(b'ttf fixture')
            with patch.object(reading, 'pack_truetype', return_value=ui.pack_font(fnt, 12)), \
                 patch.object(reading, '_write_generated', side_effect=OSError('disk full')):
                with self.assertRaisesRegex(OSError, 'disk full'):
                    reading.prepare_paper_font(data, root / 'scene')


class PaperOptionTests(unittest.TestCase):
    def test_default_and_cli_override(self):
        p = build.parser()
        default = options.resolve_font_options(p.parse_args([]))
        self.assertEqual(default['bitmap_paper_ink'], 'filled')
        self.assertEqual(default['selected_by'], 'shipped default')
        cli = options.resolve_font_options(p.parse_args(['--bitmap-paper-ink', 'original']))
        self.assertEqual(cli['bitmap_paper_ink'], 'original')
        self.assertEqual(cli['selected_by'], 'CLI override')

    def test_config_then_cli_precedence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'build.json'
            path.write_text('{"bitmap_paper_ink":"original"}')
            args = ['--build-config', str(path)]
            record = options.resolve_font_options(build.parser().parse_args(args))
            self.assertEqual(record['bitmap_paper_ink'], 'original')
            self.assertEqual(record['selected_by'], 'build config')
            record = options.resolve_font_options(build.parser().parse_args(args + ['--bitmap-paper-ink', 'filled']))
            self.assertEqual(record['bitmap_paper_ink'], 'filled')
            self.assertEqual(record['selected_by'], 'CLI override')
            self.assertEqual(len(record['config_files']), 2)

    def test_bad_configs_fail_clearly(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'bad.json'
            for text in ('null', '[]', '{bad', '{"bitmap_paper_ink":"typo"}', '{"bitmap_paper_ink":false}', '{"bitmap_paper_in":"filled"}'):
                with self.subTest(text=text):
                    path.write_text(text)
                    with self.assertRaises(ValueError):
                        options.resolve_font_options(build.parser().parse_args(['--build-config', str(path)]))
            path.unlink()
            with self.assertRaisesRegex(ValueError, 'Cannot read build config'):
                options.resolve_font_options(build.parser().parse_args(['--build-config', str(path)]))

    def test_unknown_cli_mode_is_rejected(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            build.parser().parse_args(['--bitmap-paper-ink', 'typo'])

    def test_effective_mode_reaches_reading_command(self):
        args = build.parser().parse_args(['--bitmap-paper-ink', 'original'])
        args.sdk = Path('/sdk')
        args.data_files = Path('/owned/Data Files')
        tools = {n: '/tools/' + n for n in ('qbsp', 'vis', 'light', 'qcc', 'ffmpeg', 'xdftool', 'rdbtool')}
        commands = dict(build.commands(args, tools, Path('/external/run')))
        self.assertEqual(commands['reading'][-2:], ['--bitmap-paper-ink', 'original'])
        self.assertNotIn('--bitmap-paper-ink', commands['engine'])

    def test_bad_config_exits_before_setup(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'bad.json'
            p.write_text('{"bitmap_paper_ink":"broken"}')
            with patch.object(build, 'prerequisites') as setup, contextlib.redirect_stderr(io.StringIO()), \
                 self.assertRaises(SystemExit):
                build.main(['--build-config', str(p), '--check'])
            setup.assert_not_called()


if __name__ == '__main__':
    unittest.main()
