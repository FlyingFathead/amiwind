# SPDX-License-Identifier: GPL-3.0-only
"""MiniWind interior scope: one room, its start (MINIWIND-NO-INTERIOR-SCOPE-42)."""
import contextlib
import io
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools'), str(ROOT / 'tests')]

import build  # noqa: E402
import build_exclusions  # noqa: E402
import build_font_options as options  # noqa: E402
import build_recipe  # noqa: E402
import miniwind  # noqa: E402
import town_interiors  # noqa: E402
from test_build_builder import RUN, TOOLS  # noqa: E402


# MiniWind builds are -devN only: plan them as a development version of this line, whatever VERSION is
# (an rc or final VERSION skipped these tests before; v0.0.42-rc1 gate 2923).
DEV_VERSION = build.VERSION.split('-')[0] + '-dev1'


def plan(argv):
    with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(build, 'VERSION', DEV_VERSION):
        args = build.parser().parse_args(['--data-files', '/owned', '--jobs', '4', *argv])
        build_recipe.configure(build.parser, args, ['--data-files', '/owned', '--jobs', '4', *argv], DEV_VERSION,
                               out=io.StringIO())
        build.configure_miniwind(args)
        build.town_selection(args)
        build_exclusions.miniwind_defaults(args)
        build_exclusions.resolve(args, DEV_VERSION, area_build=True)
        build.configure_area_closure(args)
        build.configure_direct_start(args)
        build.configure_skip_census(args)
        args.sdk, args.workspace = Path('/sdk'), Path('/private/ws')
        args.builder_options = options.resolve_builder(args)
        return args, dict(build.commands(args, TOOLS, RUN))


class InteriorScopePlan(unittest.TestCase):
    def test_palace_preset_converts_its_room_only_and_leaves_out_island_checks(self):
        args, steps = plan(['--miniwind-preset', 'vivec-palace'])
        self.assertEqual(args.miniwind_scope, 'interior')
        rooms = [str(part) for part in steps['chim-rooms-vivec_city']]
        self.assertEqual(rooms[rooms.index('--only-cell') + 1], 'Vivec, Palace of Vivec')
        for name in ('seam-audit', 'cell-progress'):
            self.assertNotIn(name, steps)
            self.assertIn(name, args.miniwind_record['left_out'])
        image = [str(part) for part in steps['image']]
        self.assertEqual(image[image.index('--miniwind-scope') + 1], 'interior')
        self.assertEqual(args.closure_cells[-1], 'interior:Vivec, Palace of Vivec')

    def test_full_scope_keeps_every_room(self):
        _, steps = plan(['--miniwind-preset', 'vivec-palace', '--miniwind-scope', 'full'])
        self.assertNotIn('--only-cell', [str(p) for p in steps['chim-rooms-vivec_city']])
        self.assertIn('seam-audit', steps)

    def test_interior_scope_needs_an_interior_start(self):
        with self.assertRaisesRegex(ValueError, 'builds one room'):
            plan(['--miniwind', '--miniwind-town', 'vivec_city', '--miniwind-scope', 'interior'])


class Selection(unittest.TestCase):
    LISTED = [{'cell': 'A Room', 'map': 'a1', 'exclude': None}, {'cell': 'B Room', 'map': 'b1', 'exclude': None},
              {'cell': 'C Room', 'map': 'c1', 'exclude': 'over a limit'}]

    def test_only_rooms_excludes_the_others_with_the_scope_reason(self):
        rows = town_interiors.only_rooms(self.LISTED, ['a room'], 'Town')
        self.assertEqual([r['exclude'] for r in rows], [None, town_interiors.ONLY_CELLS_LEFT_OUT, 'over a limit'])
        self.assertIs(town_interiors.only_rooms(self.LISTED, None, 'Town'), self.LISTED)

    def test_unknown_or_excluded_room_refused(self):
        for cell in ('Nowhere', 'C Room'):
            with self.assertRaisesRegex(ValueError, 'not a converted room'):
                town_interiors.only_rooms(self.LISTED, [cell], 'Town')

    def test_kept_maps_and_start_maps_of_the_interior_scope(self):
        self.assertEqual(miniwind.start_maps('vpi015', 'interior'), ('vpi015',))
        self.assertEqual(miniwind.start_maps('vpi015', 'full'), ())
        kept, _ = miniwind.kept_maps(ROOT, 'interior', 'vivec_city', ('vpi015',))
        self.assertEqual(kept, {'vivec_city', 'vpi015'})


if __name__ == '__main__':
    unittest.main()
