"""Builder type (legacy or chim): config precedence, validation and receipts."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import build
import build_font_options as options
import chim


def resolve(argv):
    return options.resolve_builder(build.parser().parse_args(argv))


class BuilderOptionTests(unittest.TestCase):
    def test_shipped_default_is_chim_with_balmora_and_seyda(self):
        # v0.0.33, owner decision: the first CHIM release ships Balmora and Seyda Neen on CHIM.
        shipped = json.loads((ROOT / 'config/build-defaults.json').read_text(encoding='utf-8'))
        self.assertEqual((shipped['builder'], shipped['chim_areas']), ('chim', ['balmora', 'seyda']))
        record = resolve([])
        self.assertEqual((record['builder'], record['selected_by']), ('chim', 'shipped default'))
        self.assertEqual((record['chim_version'], record['world_format'], record['chim_areas']),
                         (chim.CHIM_VERSION, '%d.%d' % chim.FORMAT_VERSION, ['balmora', 'seyda']))

    def test_legacy_stays_selectable_without_chim_fields(self):
        record = resolve(['--builder', 'legacy'])
        self.assertEqual((record['builder'], record['selected_by']), ('legacy', 'CLI override'))
        self.assertEqual((record['chim_version'], record['world_format'], record['chim_areas']), (None, None, []))

    def test_cli_chim_records_versions_and_default_area(self):
        record = resolve(['--builder', 'chim'])
        self.assertEqual((record['builder'], record['selected_by']), ('chim', 'CLI override'))
        self.assertEqual(record['chim_version'], chim.CHIM_VERSION)
        self.assertEqual(record['world_format'], '%d.%d' % chim.FORMAT_VERSION)
        self.assertEqual(record['chim_areas'], ['balmora', 'seyda'])

    def test_chim_version_is_semver_not_a_builder_number(self):
        parts = chim.CHIM_VERSION.split('.')
        self.assertEqual(len(parts), 3)
        self.assertTrue(all(p.isdigit() for p in parts))
        # Naming rule: builder types are words, never numbered builder versions.
        self.assertEqual(options.BUILDERS, ('legacy', 'chim'))

    def test_config_then_cli_precedence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'build.json'
            path.write_text('{"builder":"chim","chim_areas":["vivec_arena"]}')
            record = resolve(['--build-config', str(path)])
            self.assertEqual((record['builder'], record['selected_by']), ('chim', 'build config'))
            self.assertEqual(record['chim_areas'], ['vivec_arena'])
            self.assertEqual(len(record['config_files']), 2)
            record = resolve(['--build-config', str(path), '--chim-area', 'balmora', '--chim-area', 'balmora'])
            self.assertEqual(record['chim_areas'], ['balmora'])
            record = resolve(['--build-config', str(path), '--builder', 'legacy'])
            self.assertEqual((record['builder'], record['selected_by']), ('legacy', 'CLI override'))
            self.assertEqual(record['chim_areas'], [])

    def test_areas_come_from_the_town_table_including_legacy_blocked_rows(self):
        from town_config import load_registry
        towns = load_registry()['towns']
        blocked = [t['id'] for t in towns if t.get('blocked')]
        self.assertTrue(blocked, 'fixture expects a legacy-blocked town row')
        record = resolve(['--builder', 'chim', '--chim-area', blocked[0]])
        self.assertEqual(record['chim_areas'], [blocked[0]])
        with self.assertRaisesRegex(ValueError, 'Unknown CHIM area'):
            resolve(['--builder', 'chim', '--chim-area', 'atlantis'])

    def test_bad_configs_fail_clearly(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'bad.json'
            for text in ('{"builder":"v2"}', '{"builder":"2"}', '{"builder":true}', '{"chim_areas":"balmora"}',
                         '{"chim_areas":[]}', '{"chim_areas":[""]}', '{"builder_type":"chim"}'):
                with self.subTest(text=text):
                    path.write_text(text)
                    with self.assertRaises(ValueError):
                        resolve(['--build-config', str(path)])
                    # The same file must also stop the font resolver: one config reader.
                    with self.assertRaises(ValueError):
                        options.resolve_font_options(build.parser().parse_args(['--build-config', str(path)]))

    def test_unknown_cli_builder_is_rejected(self):
        for value in ('v2', '1', 'CHIM'):
            with self.subTest(value=value), contextlib.redirect_stderr(io.StringIO()), \
                 self.assertRaises(SystemExit):
                build.parser().parse_args(['--builder', value])

    def test_bad_builder_config_exits_before_setup(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'bad.json'
            p.write_text('{"builder":"v2"}')
            with patch.object(build, 'prerequisites') as setup, contextlib.redirect_stderr(io.StringIO()), \
                 self.assertRaises(SystemExit):
                build.main(['--build-config', str(p), '--check'])
            setup.assert_not_called()

    def test_receipt_records_builder_version_and_format(self):
        for argv, expected in ((['--dry-run', '--builder', 'legacy'], ('legacy', None, None)),
                               (['--dry-run'], ('chim', chim.CHIM_VERSION, '%d.%d' % chim.FORMAT_VERSION)),
                               (['--dry-run', '--builder', 'chim'],
                                ('chim', chim.CHIM_VERSION, '%d.%d' % chim.FORMAT_VERSION))):
            with self.subTest(argv=argv), tempfile.TemporaryDirectory() as tmp:
                args = build.parser().parse_args(argv)
                args.font_options = {'synthetic': True}
                with patch.object(build, 'ROOT', Path(tmp)):
                    receipt = build.provenance(args, {})
                self.assertEqual((receipt['builder'], receipt['chim_version'], receipt['world_format']), expected)
                self.assertEqual(receipt['builder_options']['builder'], expected[0])


TOOLS = {name: '/tools/' + name for name in ('qbsp', 'vis', 'light', 'qcc', 'ffmpeg', 'xdftool', 'rdbtool')}
RUN = Path('/private/run')


def plan(argv):
    args = build.parser().parse_args(argv)
    args.data_files, args.sdk, args.workspace = Path('/owned'), Path('/sdk'), Path('/private/ws')
    args.builder_options = options.resolve_builder(args)
    return build.commands(args, TOOLS, RUN)


class BuilderTextTests(unittest.TestCase):
    def test_no_double_encoded_text_in_the_build_tools(self):
        # BUILD-MOJIBAKE-32: UTF-8 read as cp1252 and written back as UTF-8 ("1Ã¢..." for an en dash)
        marks = ('Ã¢', 'â€')
        bad = [p.name for p in sorted((ROOT / 'tools').glob('*.py'))
               if any(m in p.read_text(encoding='utf-8') for m in marks)]
        self.assertEqual(bad, [])


class ModelHullOptionTests(unittest.TestCase):
    def test_model_hull_default_config_and_cli(self):
        from build_font_options import resolve_font_options
        from types import SimpleNamespace
        r = resolve_font_options(SimpleNamespace(build_config=None, model_hull=None))
        self.assertEqual((r['model_hull'], r['model_hull_selected_by']), ('chain', 'shipped default'))
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / 'b.json'
            cfg.write_text('{"model_hull": "chain"}')
            r = resolve_font_options(SimpleNamespace(build_config=cfg, model_hull=None))
            self.assertEqual((r['model_hull'], r['model_hull_selected_by']), ('chain', 'build config'))
            r = resolve_font_options(SimpleNamespace(build_config=cfg, model_hull='routed'))
            self.assertEqual((r['model_hull'], r['model_hull_selected_by']), ('routed', 'CLI override'))
            cfg.write_text('{"model_hull": "tree"}')
            with self.assertRaisesRegex(ValueError, 'model_hull'):
                resolve_font_options(SimpleNamespace(build_config=cfg, model_hull=None))

    def test_chim_stream_statics_default_off_config_and_cli(self):
        from build_font_options import resolve_font_options
        from types import SimpleNamespace
        r = resolve_font_options(SimpleNamespace(build_config=None, model_hull=None, chim_stream_statics=None))
        self.assertEqual((r['chim_stream_statics'], r['chim_stream_statics_selected_by']), (True, 'shipped default'))
        r = resolve_font_options(SimpleNamespace(build_config=None, model_hull=None, chim_stream_statics=True))
        self.assertEqual((r['chim_stream_statics'], r['chim_stream_statics_selected_by']), (True, 'CLI override'))
        import mesh_geometry_env as E
        with patch.dict('os.environ', {}, clear=False):
            E.export_chim_stream_statics(True)
            from chim.frame_map import stream_enabled
            self.assertTrue(stream_enabled())
            E.export_chim_stream_statics(False)
            self.assertFalse(stream_enabled())

    def test_exported_for_the_converters(self):
        import mesh_geometry_env as E
        with patch.dict('os.environ', {}, clear=False):
            self.assertEqual(E.export_model_hull('chain'), 'chain')
            self.assertEqual(E.model_hull_mode(), 'chain')
            with self.assertRaises(ValueError):
                E.export_model_hull('tree')


class ChimStageTests(unittest.TestCase):
    def test_legacy_plan_has_no_chim_stage_and_is_unchanged(self):
        legacy = plan(['--jobs', '4', '--builder', 'legacy'])
        self.assertNotIn('chim', [name for name, _ in legacy])
        self.assertEqual(plan(['--jobs', '4']), plan(['--jobs', '4', '--builder', 'chim']))  # chim is the default

    def test_chim_stage_command(self):
        steps = plan(['--jobs', '4', '--builder', 'chim'])
        names = [name for name, _ in steps]
        legacy = [name for name, _ in plan(['--jobs', '4', '--builder', 'legacy'])]
        self.assertEqual([n for n in names if n != 'chim'], legacy)
        self.assertLess(names.index('census'), names.index('chim'))
        self.assertLess(names.index('chim'), names.index('image'))
        command = [str(part) for part in dict(steps)['chim']]
        self.assertTrue(command[1].endswith('tools/chim_build.py'))

        def value(flag):
            return command[command.index(flag) + 1]
        self.assertEqual(value('--area'), 'balmora')
        self.assertEqual(value('--palette'), str(RUN / 'intro-scene/id1/gfx/palette.lmp'))
        self.assertEqual(value('--out'), str(RUN / 'chim-world'))
        self.assertEqual(value('--unit-cache'), str(Path('/private/ws/cache/chim-units')))
        self.assertEqual(value('--qbsp'), TOOLS['qbsp'])
        self.assertIn('--validate', command)
        self.assertIn('--stats', command)

    def test_image_gets_the_chim_world_only_with_chim(self):
        image = [str(p) for p in dict(plan(['--jobs', '4', '--builder', 'chim']))['image']]
        self.assertEqual(image[image.index('--chim-world') + 1], str(RUN / 'chim-world'))
        self.assertNotIn('--chim-world', [str(p) for p in dict(plan(['--jobs', '4', '--builder', 'legacy']))['image']])

    def test_jobs_reach_the_chim_stage_exactly(self):
        for jobs in (1, 3, 100):
            with self.subTest(jobs=jobs):
                command = [str(p) for p in dict(plan(['--jobs', str(jobs), '--builder', 'chim']))['chim']]
                self.assertEqual(command.count('--jobs'), 1)
                self.assertEqual(command[command.index('--jobs') + 1], str(jobs))

    def test_areas_from_config_and_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'build.json'
            path.write_text('{"builder":"chim","chim_areas":["vivec_arena"]}')
            command = [str(p) for p in dict(plan(['--build-config', str(path)]))['chim']]
            self.assertEqual(command[command.index('--area') + 1], 'vivec_arena')
            command = [str(p) for p in dict(plan(['--build-config', str(path), '--chim-area', 'balmora']))['chim']]
            self.assertEqual([command[i + 1] for i, p in enumerate(command) if p == '--area'], ['balmora'])

    def test_dependencies(self):
        import build_parallel
        deps = build_parallel.stage_dependencies(plan(['--jobs', '4', '--builder', 'chim']))
        # census rewrites the palette (BUILD-PALETTE-RACE-32); harvest and flora: payload parity
        self.assertEqual(deps['chim'], ('census', 'harvest', 'world-flora-assets', 'world-survey'))
        self.assertIn('chim', deps['image'])
        self.assertNotIn('chim', build_parallel.stage_dependencies(plan(['--jobs', '4', '--builder', 'legacy']))['image'])

    def test_areas_the_builder_cannot_write_fail_before_setup(self):
        # an unknown area; two Vivec districts' frames overlap
        for extra in (['--chim-area', 'nowhere'], ['--chim-area', 'vivec_arena', '--chim-area', 'vivec_foreign']):
            with self.subTest(extra=extra):
                with self.assertRaises(ValueError):
                    resolve(['--builder', 'chim', *extra])
                with patch.object(build, 'prerequisites') as setup, contextlib.redirect_stderr(io.StringIO()),                      self.assertRaises(SystemExit):
                    build.main(['--builder', 'chim', *extra, '--check'])
                setup.assert_not_called()
        # The legacy builder ignores the CHIM area list.
        self.assertEqual(resolve(['--builder', 'legacy', '--chim-area', 'nowhere'])['builder'], 'legacy')

    def test_seyda_neen_is_a_chim_area_beside_balmora(self):
        # format 0.5: Seyda Neen's frame comes from the legacy scene stage (chim.seyda); it does not overlap Balmora
        self.assertEqual(resolve(['--builder', 'chim', '--chim-area', 'seyda', '--chim-area', 'balmora'])['chim_areas'],
                         ['seyda', 'balmora'])
        command = dict(plan(['--jobs', '4', '--builder', 'chim', '--chim-area', 'seyda']))['chim']
        self.assertEqual(command[command.index('--area') + 1], 'seyda')
        self.assertIn('--legacy-run', command)

    def test_chim_build_cli_refuses_before_reading_data(self):
        import chim_build
        with patch('chim.build.build_town') as run, contextlib.redirect_stderr(io.StringIO()),              self.assertRaises(SystemExit) as stop:
            chim_build.main(['--area', 'nowhere', '--data-files', '/none', '--palette', '/none', '--out', '/none'])
        self.assertEqual(stop.exception.code, 1)
        run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
