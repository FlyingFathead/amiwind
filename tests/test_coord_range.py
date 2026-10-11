# SPDX-License-Identifier: GPL-3.0-only
"""The build's coordinate range (tools/coord_range.py, tools/build.py --coord-range; CHIM-FRAME-COORD-RANGE-33):
wide (24 bits of 1/256 units, +/-32,000) is the default since v0.0.36 so all of Vivec fits one CHIM frame; narrow
(Quake's 1/8-unit shorts, +/-4,000) stays selectable. The builder's numbers are the engine header's, a default
build's engine command has no coordinate option, narrow reaches the engine as -DAW_COORD_NARROW and the builder's
checks through AMIWIND_COORD_RANGE, and an area wider than +/-4,000 is refused with narrow."""
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import coord_range  # noqa: E402


def header_values(narrow):
    text = (ROOT / 'engine/aga/src/aw_coord.h').read_text(encoding='utf-8')
    wide, rest = text.split('#ifndef AW_COORD_NARROW', 1)[1].split('#else', 1)
    block = rest.split('#endif', 1)[0] if narrow else wide
    return {name: int(re.search(r'#define AW_COORD_%s (\d+)' % name, block).group(1))
            for name in ('BYTES', 'BOUND', 'PROTOCOL')}


class CoordRangeTests(unittest.TestCase):
    def setUp(self):
        self.saved = os.environ.pop(coord_range.ENV, None)

    def tearDown(self):
        os.environ.pop(coord_range.ENV, None)
        if self.saved is not None:
            os.environ[coord_range.ENV] = self.saved

    def test_numbers_are_the_engine_headers(self):
        for name, narrow in (('wide', False), ('narrow', True)):
            values = header_values(narrow)
            r = coord_range.RANGES[name]
            self.assertEqual((r['bytes'], r['bound'], r['protocol']),
                             (values['BYTES'], values['BOUND'], values['PROTOCOL']), name)
        self.assertEqual(coord_range.DEFAULT, 'wide')
        self.assertEqual(coord_range.RANGES['narrow']['define'], '-DAW_COORD_NARROW')

    def test_environment_and_core_checks(self):
        self.assertEqual(coord_range.current(), 'wide')
        self.assertEqual(coord_range.bound(), 32000)
        self.assertEqual(coord_range.extra_baseline_bytes(), 3)
        os.environ[coord_range.ENV] = 'narrow'
        self.assertEqual(coord_range.bound(), 4000)
        self.assertEqual(coord_range.extra_baseline_bytes(), 0)
        city = [[-4096, -4608], [4096, 4608]]
        self.assertIn('needs --coord-range wide', coord_range.core_problem(city))
        self.assertIsNone(coord_range.core_problem(city, 'wide'))
        os.environ[coord_range.ENV] = 'medium'
        with self.assertRaises(ValueError):
            coord_range.current()

    def test_narrow_refuses_the_whole_city_area(self):
        from chim.areas import area_problems
        self.assertEqual(area_problems(['balmora', 'seyda', 'vivec_city']), [])
        os.environ[coord_range.ENV] = 'narrow'
        problems = area_problems(['balmora', 'seyda', 'vivec_city'])
        self.assertTrue(any('vivec_city' in p and 'needs --coord-range wide' in p for p in problems), problems)
        self.assertEqual(area_problems(['balmora', 'seyda', 'vivec_arena']), [])

    def test_signon_counts_the_wide_bytes(self):
        from sprite_heap import inspect_sprites
        entities = b'{\n"classname" "worldspawn"\n}\n{\n"classname" "aw_static"\n}\n{\n"classname" "light"\n}\n'
        sizes = {'signon_capacity': 16380, 'reliable_capacity': 16380}
        wide = inspect_sprites(entities, Path(tempfile.gettempdir()), sizes)
        os.environ[coord_range.ENV] = 'narrow'
        narrow = inspect_sprites(entities, Path(tempfile.gettempdir()), sizes)
        self.assertEqual(wide['signon_upper_bound_bytes'] - narrow['signon_upper_bound_bytes'], 3 * 3)

    def test_build_option_reaches_the_engine_only_when_narrow(self):
        import build
        tools = {name: '/tools/' + name for name in ('qbsp', 'vis', 'light', 'qcc', 'ffmpeg', 'xdftool', 'rdbtool')}
        for extra, expect in (([], None), (['--coord-range', 'narrow'], 'narrow'), (['--coord-range', 'wide'], None)):
            # areas inside the narrow bound (the default areas hold vivec_city, which needs wide coordinates)
            args = build.parser().parse_args(['--hands', 'sprites', '--chim-area', 'balmora', '--chim-area', 'seyda',
                                              *extra])
            args.data_files, args.sdk, args.upstream_archive = Path('/d'), Path('/sdk'), Path('/u.tar.gz')
            record = build.resolve_coord_range(args)
            self.assertEqual(record['range'], expect or 'wide')
            self.assertEqual(os.environ.get(coord_range.ENV), expect)
            engine = [str(part) for part in dict(build.commands(args, tools, Path('/private/run')))['engine']]
            if expect:
                self.assertEqual(engine[engine.index('--coord-range') + 1], 'narrow')
            else:
                self.assertNotIn('--coord-range', engine)
        args = build.parser().parse_args(['--coord-range', 'narrow', '--engine-experiment', 'widecoord'])
        with self.assertRaises(ValueError):
            build.resolve_coord_range(args)
        # the default areas hold vivec_city: a narrow build of them is refused before any stage
        import build_font_options as options
        args = build.parser().parse_args(['--coord-range', 'narrow'])
        build.resolve_coord_range(args)
        with self.assertRaisesRegex(ValueError, 'vivec_city.*needs --coord-range wide'):
            options.resolve_builder(args)
        os.environ.pop(coord_range.ENV, None)
        args = build.parser().parse_args(['--coord-range', 'narrow', '--engine-experiment', 'widecoord'])
        with self.assertRaises(ValueError):
            build.resolve_coord_range(args)

    def test_engine_stage_defines_and_receipt(self):
        import build_aga
        calls = []

        def fake_run(command, cwd=None, env=None, capture=False):
            command = [str(c) for c in command]
            calls.append(command)
            tree = Path(cwd) if cwd else None
            if command[0] == 'make':
                (tree / 'build').mkdir(exist_ok=True)
                (tree / ('build/awbench' if 'bench' in command else 'build/AmiQuakeGCC')).write_bytes(b'x')
            elif '-o' in command:
                Path(command[command.index('-o') + 1]).write_bytes(b'hunk')
            return ''
        for asked, define, protocol in ((None, None, 1015), ('narrow', '-DAW_COORD_NARROW', 15), ('wide', None, 1015)):
            calls.clear()
            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / 'engine'
                argv = ['build_aga.py', 'engine', '--out', str(out), '--sdk', tmp, '--jobs', '1',
                        *(['--coord-range', asked] if asked else [])]
                with patch('sys.argv', argv), patch.object(build_aga, 'run', side_effect=fake_run), \
                        patch.object(build_aga, 'check_binary'), \
                        patch.object(build_aga, 'check_engine_fpu', return_value=None), \
                        patch.object(build_aga, 'executable_path', side_effect=lambda p: p), \
                        patch.object(build_aga, 'write_world_coverage'), patch('sys.stdout'):
                    build_aga.main()
                make = calls[0]
                record = json.loads((out / 'engine-build.json').read_text())
                extra = [part for part in make if part.startswith('EXTRA_DEFINES=')]
                self.assertEqual(extra, ['EXTRA_DEFINES=' + define] if define else [])
                self.assertEqual((record['coord_range'], record['protocol']), (asked or 'wide', protocol))


if __name__ == '__main__':
    unittest.main()
