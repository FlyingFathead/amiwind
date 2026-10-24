# SPDX-License-Identifier: GPL-3.0-only
"""BUILD-SEYDA-BSP-CARRIER-48 (c): the town room stages (area, balmora-interiors, chim-rooms-TOWN) write shell rooms in
a build with CHIM rooms, as the batch rooms do: no qbsp, vis or light; the placements the compiled room map would have
placed (prepare_area.mesh_placements, append_meshes' rule), its entities and liquid textures in a shell map; a room with
an object the engine activates is compiled as before."""
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
import prepare_area as A  # noqa: E402

TOOLS = {name: '/tools/' + name for name in ('qbsp', 'vis', 'light', 'qcc', 'ffmpeg', 'xdftool', 'rdbtool')}


def index(refs, models):
    return {'references': [{'number': n, 'id': 'r%d' % n, 'model_index': m, 'position': list(p), 'scene_groups': ['g'],
                            'bounds': [[p[0] - 4, p[1] - 4, p[2]], [p[0] + 4, p[1] + 4, p[2] + 8]]}
                           for n, m, p in refs],
            'models': [{'source': s} for s in models],
            'groups': {'g': {'references': [n for n, _, _ in refs]}}}


class Placements(unittest.TestCase):
    def setUp(self):
        self.index = index([(1, 0, (0, 0, 0)), (2, 1, (10, 0, 0)), (3, 2, (20, 0, 0)), (4, 0, (30, 0, 0))],
                           ['meshes/f/furn_table.nif', 'meshes/m/marker_arrow.nif', 'meshes/f/flora_fern.nif'])

    def test_the_seyda_rooms_rule(self):
        # references=None: the runtime selection (whole groups), the interior dressing kept, editor markers out
        from prepare_mesh_bsp import INTERIOR_DRESSING
        kept, omitted, retained, selection = A.mesh_placements(self.index, None, INTERIOR_DRESSING)
        self.assertEqual(kept, [1, 3, 4])
        self.assertEqual([o['reference'] for o in omitted], [2])
        self.assertIn('marker_', omitted[0]['reason'])
        self.assertEqual([r['reference'] for r in retained], [3])
        self.assertEqual(selection['selected_groups'], ['g'])

    def test_the_retained_rooms_rule(self):
        # Balmora and the CHIM town rooms: the explicit list, every piece kept (retain_dressing True)
        kept, omitted, _, _ = A.mesh_placements(self.index, [1, 2, 4], True)
        self.assertEqual((kept, omitted), ([1, 2, 4], []))
        with self.assertRaisesRegex(ValueError, 'not all converted'):
            A.mesh_placements(self.index, [1, 99], True)


class Shell(unittest.TestCase):
    def shell(self, refs):
        import chim_room_batches as S
        from chim.interior import is_shell_map
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            idx = index([(n, 0, (n, 0, 0)) for n in refs], ['meshes/f/furn_table.nif'])
            from PIL import Image
            from prepare_quake import miptex
            tile = Image.new('P', (16, 16), 3)
            water, void = miptex('*water', tile), miptex('voidwall', tile)
            report = A.shell_room(root, idx, idx['references'], {'map': 'room1'}, 'Room One',
                                  '"aw_hand_idle" "2.5"', ['{\n"classname" "info_player_start"\n}'],
                                  [('voidwall', 0x43, void), ('*water', 0x43, water)], [-64, -64, -64], [64, 64, 64],
                                  True, True, [], [], [], [], {}, b'', root)
            if report is None:
                return None, None, None
            data = (root / 'room.bsp').read_bytes()
            from chim.frame_map import entities
            from chim.interior import miptex_named
            rows = entities(data)
            self.assertTrue(is_shell_map(data))
            # the liquid texture the CHIM room takes, never the compile-only void wall
            self.assertTrue(miptex_named(data, ('*water',)))
            self.assertFalse(miptex_named(data, ('voidwall',)))
            return report, rows, json.loads((root / 'placements.json').read_text())

    def test_a_shell_room(self):
        report, rows, placements = self.shell([5, 6])
        self.assertEqual(placements, [5, 6])
        self.assertEqual(report['form'], 'chim room shell')
        self.assertEqual(rows[0]['message'], 'Room One')
        self.assertEqual(rows[0]['aw_hand_idle'], '2.5')
        self.assertEqual(rows[1]['classname'], 'info_player_start')

    def test_an_activated_object_keeps_the_compile(self):
        from chim.frame_map import activated_refs
        ref = sorted(activated_refs())[0]
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(self.shell([5, ref])[0], None)
        self.assertIn('compiled, not a shell', out.getvalue())


class Builder(unittest.TestCase):
    def plan(self, *argv):
        import build
        args = build.parser().parse_args(list(argv))
        args.data_files, args.sdk, args.workspace = Path('/owned'), Path('/sdk'), Path('/private/ws')
        import build_font_options as options
        args.builder_options = options.resolve_builder(args)
        with patch('build_jobs.auto_jobs', return_value=4), contextlib.redirect_stdout(io.StringIO()):
            return dict(build.commands(args, TOOLS, Path('/private/run')))

    def test_a_build_with_chim_rooms_writes_shell_rooms(self):
        steps = self.plan()
        self.assertIn('chim-interiors', steps)
        for name in ('area', 'balmora-interiors', 'chim-rooms-vivec_city'):
            command = [str(part) for part in steps[name]]
            self.assertEqual(command[command.index('--room-form') + 1], 'shell', name)
        # the room batches and the census and prison rooms are no part of it
        self.assertNotIn('--room-form', [str(p) for p in steps['census']])

    def test_classic_interiors_compile(self):
        steps = self.plan('--interior-format', 'bsp')
        self.assertNotIn('chim-interiors', steps)
        self.assertNotIn('--room-form', [str(p) for p in steps['area']])

    def test_the_tools_take_the_option(self):
        import argparse
        p = argparse.ArgumentParser()
        A.add_room_form_option(p)
        self.assertEqual(p.parse_args([]).room_form, 'compiled')
        self.assertEqual(p.parse_args(['--room-form', 'shell']).room_form, 'shell')
        with self.assertRaises(ValueError):
            A.prepare('/nowhere', '/nowhere', 'q', 'v', 'l', room_form='flat')


if __name__ == '__main__':
    unittest.main()
