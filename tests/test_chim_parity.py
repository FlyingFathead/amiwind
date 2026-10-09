# SPDX-License-Identifier: GPL-3.0-only
"""CHIM payload parity (CHIM-PAYLOAD-PARITY-33): the CHIM source applies the image's harvest removal
and town flora with the same shared functions. Synthetic data only."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import build  # noqa: E402
import build_font_options as options  # noqa: E402
import build_parallel  # noqa: E402
from chim import build as CB  # noqa: E402

TOOLS = {name: '/tools/' + name for name in ('qbsp', 'vis', 'light', 'qcc', 'ffmpeg', 'xdftool', 'rdbtool')}
RUN = Path('/private/run')


def flora_dir(root, policies):
    """A flora assets folder: references 100.. at x = 0, 300, 600 ...; policies by number."""
    refs, placements = [], []
    for k, (number, policy) in enumerate(sorted(policies.items())):
        x = k * 300.0
        refs.append({'number': number, 'model_index': 0, 'cell': [0, 0], 'scale': 1.0,
                     'position': [x, 0.0, 10.0], 'rotation_radians': [0.0, 0.0, 0.0],
                     'bounds': [[x - 10, -10, 0], [x + 10, 10, 20]]})
        placements.append({'number': number, 'renderer_policy': policy, 'requires_interaction': False,
                           'source_collision': {'mode': 'solid'}})
    index = {'chunk_size': 8192, 'chunks': {'0,0': list(range(len(refs)))}, 'references': refs,
             'models': [{'source': 'meshes/f/tree.nif', 'triangles': 240, 'materials': []}], 'textures': []}
    (root / 'source').mkdir(parents=True)
    (root / 'source/scenery-index.json').write_text(json.dumps(index))
    (root / 'tree-sprites.json').write_text(json.dumps({'placements': placements}))
    return root


ENTRIES = [{'name': 'bm000', 'origin': [0.0, 0.0, 0.0], 'coverage': [[-10, -10], [80, 10]]},
           {'name': 'bm001', 'origin': [0.0, 0.0, 0.0], 'coverage': [[60, -10], [160, 10]]}]


class TownFloraTests(unittest.TestCase):
    def test_selection_matches_the_image_rule(self):
        with tempfile.TemporaryDirectory() as tmp:
            flora = flora_dir(Path(tmp), {101: 'mesh', 102: 'mesh', 103: 'mesh', 104: 'mesh', 105: 'mesh'})
            with patch('install_town_flora.town_entries', return_value=ENTRIES):
                index, refs, modes = CB.town_flora('balmora', flora, town_numbers={102})
        # coverage x (quarter scale): 0..640 local units -> 101 (0), 102 (300, in the town already), 103 (600)
        self.assertEqual([r['number'] for r in refs], [101, 103])            # once each, town's own left out
        self.assertEqual(refs[0]['renderer_policy'], 'mesh')
        self.assertEqual(refs[0]['position'], [0.0, 0.0, 10.0])
        self.assertEqual(modes, {101: 'mesh', 103: 'mesh'})

    def test_sprites_place_their_solid_collision_only(self):
        # a sprite is a point entity of the region maps (the frame map carries it); its solid source
        # collision is a collision-only placement, as the image's overlay adds a collision func_wall
        with tempfile.TemporaryDirectory() as tmp:
            flora = flora_dir(Path(tmp), {101: 'sprite', 103: 'mesh'})
            receipt = json.loads((Path(tmp) / 'tree-sprites.json').read_text())
            receipt['placements'].append({'number': 105, 'renderer_policy': 'sprite', 'requires_interaction': False,
                                          'source_collision': {'mode': 'nonsolid'}})
            index = json.loads((Path(tmp) / 'source/scenery-index.json').read_text())
            index['references'].append(dict(index['references'][0], number=105, position=[90.0, 0.0, 10.0]))
            (Path(tmp) / 'tree-sprites.json').write_text(json.dumps(receipt))
            (Path(tmp) / 'source/scenery-index.json').write_text(json.dumps(index))
            with patch('install_town_flora.town_entries', return_value=ENTRIES):
                _, refs, modes = CB.town_flora('balmora', flora, set())
        self.assertEqual(modes, {101: 'collision_only', 103: 'mesh'})       # 105: no collision, no placement
        self.assertEqual([r['number'] for r in refs], [101, 103])

    def test_towns_without_town_flora(self):
        self.assertIsNone(CB.town_flora('vivec_arena', '/none', set()))

    def test_town_entries_are_the_images(self):
        from balmora_regions import config, regions
        from install_town_flora import town_entries
        settings = config()
        origin = [v * settings['scale'] for v in settings['centre']] + [0.]
        self.assertEqual(town_entries('balmora'), [{**e, 'origin': origin} for e in regions(settings)])
        self.assertIsNone(town_entries('seyda'))
        self.assertIsNone(town_entries('vivec_arena'))

    def test_mesh_profile(self):
        from prepare_world_flora import mesh_profile
        model = {'triangles': 480}
        solid = [{'source_collision': {'mode': 'solid'}, 'kind': 'tree'}]
        self.assertEqual(mesh_profile(model, solid), {'texture_size': 32, 'collision_only': False,
                                                      'collision_none': False, 'ratio': 0.25})
        soft = [{'source_collision': {'mode': 'nonsolid'}, 'kind': 'small_mushroom'}]
        p = mesh_profile({'triangles': 60}, soft)
        self.assertEqual((p['collision_none'], p['ratio'], p['preserve_shared_seams']), (True, 1.0, True))
        self.assertEqual(mesh_profile(model, solid, 'collision_only'),
                         {'texture_size': 32, 'collision_only': True, 'collision_none': False})


class TownReferenceTests(unittest.TestCase):
    def test_town_references_is_the_coverage_rule(self):
        # a frame centred off the cell grid audits whole cells: placements whose converted bounds stay
        # outside the town bounds are not the town's (the legacy region maps leave them out)
        from town_regions import audit_coverage, town_references
        settings = {'centre': [0.0, 0.0], 'scale': 0.25, 'bounds': [[-100, -100], [100, 100]],
                    'overlap': 1, 'hysteresis': 1, 'draw_distance': 1}

        def ref(number, x):
            return {'number': number, 'position': [x, 0.0, 0.0], 'bounds': [[x - 40, -40, 0], [x + 40, 40, 10]]}
        index = {'references': [ref(1, 0.0), ref(2, 420.0), ref(3, 600.0)]}
        self.assertEqual(town_references(index, settings), [1, 2])      # 2 reaches in (420 - 40 = 380 < 400)
        entries = [{'name': 'a', 'coverage': [[-100, -100], [100, 100]]}]
        self.assertEqual(audit_coverage(index, entries, settings)['covered_references'], 2)


class HarvestTests(unittest.TestCase):
    def test_harvest_numbers_are_the_removal_set(self):
        rows = [{'number': 5}, {'number': 9}]
        with patch('harvest_build.source_placements', return_value=({}, {}, rows)) as call:
            self.assertEqual(CB.harvest_numbers('/h', '/d'), {5, 9})
        call.assert_called_once_with('/h', '/d')


def plan(argv):
    args = build.parser().parse_args(argv)
    args.data_files, args.sdk, args.workspace = Path('/owned'), Path('/sdk'), Path('/private/ws')
    args.builder_options = options.resolve_builder(args)
    return build.commands(args, TOOLS, RUN)


class StageTests(unittest.TestCase):
    def test_chim_stage_gets_harvest_and_flora_by_default(self):
        steps = plan(['--jobs', '4', '--builder', 'chim'])
        command = [str(p) for p in dict(steps)['chim']]
        self.assertEqual(command[command.index('--harvest') + 1], str(RUN / 'harvest'))
        self.assertEqual(command[command.index('--flora') + 1], str(RUN / 'world-flora-assets'))
        deps = build_parallel.stage_dependencies(steps)
        self.assertEqual(set(deps['chim']), {'census', 'harvest', 'world-flora-assets', 'world-survey'})

    def test_debug_opt_outs_drop_them(self):
        command = [str(p) for p in dict(plan(['--jobs', '4', '--builder', 'chim', '--no-harvest',
                                              '--no-tree-sprites']))['chim']]
        self.assertNotIn('--harvest', command)
        self.assertNotIn('--flora', command)


if __name__ == '__main__':
    unittest.main()
