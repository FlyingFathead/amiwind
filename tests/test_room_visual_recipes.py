# SPDX-License-Identifier: GPL-3.0-only
"""The universal conversion rule in the rooms (VISUAL-EVERYWHERE-ROOMS-67; tools/chim/interior.py room_visual_profiles):
one model's replacement in config/visual-recipes.json "everywhere" is used wherever that model is placed, the CHIM
rooms included, every row kind as the CHIM frames apply it (ratio, primitive), keyed by the mesh's source path and
packet SHA-256, so only that model type changes and only its units re-key. A synthetic room, no game data."""
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / 'tools', ROOT / 'src'):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from chim import interior as I  # noqa: E402

LANTERN = 'meshes/l/test_lantern_01.nif'
URN = 'meshes/o/test_urn_01.nif'
TABLE = 'meshes/f/test_table_01.nif'
SHELL = {'kind': 'lantern_shell', 'half_width': 10.0, 'top': 1.0, 'bottom': -49.0, 'body_bottom': -36.0,
         'neck_z': -40.0, 'neck_half_width': 1.35, 'roof_width_ratio': 1.15, 'paper_material': 2, 'frame_material': 0}


def box_geometry(lo, hi, materials=3, rings=4):
    """A closed box split into horizontal rings (more triangles than its shape needs, like a game lantern), each side
    quad two triangles, the material cycling through MATERIALS; returns (vertices N x 9, faces M x 4)."""
    zs = np.linspace(lo[2], hi[2], rings + 1)
    corners = [(lo[0], lo[1]), (hi[0], lo[1]), (hi[0], hi[1]), (lo[0], hi[1])]
    v, f = [], []
    for k in range(rings):
        for s in range(4):
            (x0, y0), (x1, y1) = corners[s], corners[(s + 1) % 4]
            a = len(v)
            v += [[x0, y0, zs[k], 0, 0, 255, 255, 255, 255], [x1, y1, zs[k], 1, 0, 255, 255, 255, 255],
                  [x1, y1, zs[k + 1], 1, 1, 255, 255, 255, 255], [x0, y0, zs[k + 1], 0, 1, 255, 255, 255, 255]]
            m = (k + s) % materials
            f += [[a, a + 1, a + 2, m], [a, a + 2, a + 3, m]]
    for z, flip in ((lo[2], True), (hi[2], False)):
        a = len(v)
        v += [[x, y, z, i % 2, i // 2, 255, 255, 255, 255] for i, (x, y) in enumerate(corners)]
        f += [[a, a + 2, a + 1, 0], [a, a + 3, a + 2, 0]] if flip else [[a, a + 1, a + 2, 0], [a, a + 2, a + 3, 0]]
    return v, f


def model_record(source, raw, materials=3):
    from mwad.scene import unpack_geometry
    return {'source': source, 'offset': 0, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'triangles': len(unpack_geometry(raw)[1]),
            'materials': [{'texture_index': None, 'diffuse': [1, 1, 1]} for _ in range(materials)]}


def synthetic_room():
    """(models, profiles, document): three meshes of a room (a lantern, an urn, a table) and a recipe document
    whose everywhere recipe replaces the lantern (primitive) and reduces the urn (ratio); the table has no row."""
    from mwad.scene import pack_geometry
    raws = {LANTERN: pack_geometry(*box_geometry((-10, -10, -49), (10, 10, 1), 3, 8), 3),
            URN: pack_geometry(*box_geometry((-8, -8, 0), (8, 8, 30), 1, 6), 1),
            TABLE: pack_geometry(*box_geometry((-30, -20, 0), (30, 20, 25), 1, 2), 1)}
    models = [model_record(LANTERN, raws[LANTERN]), model_record(URN, raws[URN], 1), model_record(TABLE, raws[TABLE], 1)]
    document = {'format': 1, 'everywhere': 'ev', 'recipes': {
        'ev': {'models': {LANTERN: {'sha256': models[0]['sha256'], 'primitive': dict(SHELL)},
                          URN: {'sha256': models[1]['sha256'], 'ratio': 0.1, 'error_share': 0.01}}},
        'room-only': {'models': {URN: {'sha256': models[1]['sha256'], 'ratio': 0.25, 'error_share': 0.0025},
                                 LANTERN: {'sha256': models[0]['sha256'], 'primitive': dict(SHELL)}}}}}
    profiles = {m['source']: {'texture_size': 64} for m in models}
    return models, profiles, document, raws


class EverywhereInRooms(unittest.TestCase):
    def setUp(self):
        os.environ.pop('AMIWIND_VISUAL_EVERYWHERE', None)
        self.models, self.profiles, self.document, self.raws = synthetic_room()

    def apply(self, recipe=None, everywhere=True):
        profiles = {k: dict(v) for k, v in self.profiles.items()}
        applied = I.room_visual_profiles(self.models, range(len(self.models)), profiles, recipe, everywhere,
                                         self.document)
        return profiles, applied

    def test_every_row_kind_reaches_the_room_by_model(self):
        profiles, applied = self.apply()
        self.assertEqual(profiles[LANTERN]['visual_primitive'], SHELL)
        self.assertEqual(profiles[LANTERN]['visual_recipe']['name'], 'ev')
        self.assertEqual((profiles[URN]['ratio'], profiles[URN]['meshopt_error_share']), (0.1, 0.01))
        self.assertTrue(profiles[URN]['lod_preserve_border'])
        # a mesh no row names keeps its profile exactly
        self.assertEqual(profiles[TABLE], {'texture_size': 64})
        self.assertEqual(applied, {LANTERN: 'ev', URN: 'ev'})

    def test_only_that_model_type_changes(self):
        # another mesh with the same file name but other content (another packet) is not that model
        self.models[0] = dict(self.models[0], sha256='b' * 64)
        profiles, applied = self.apply()
        self.assertNotIn('visual_primitive', profiles[LANTERN])
        self.assertEqual(profiles[LANTERN], {'texture_size': 64})
        self.assertEqual(applied, {URN: 'ev'})

    def test_the_rooms_own_recipe_keeps_its_ratio_rows_and_the_everywhere_rows_fill_in(self):
        # recipe_rooms (room-only extras): its ratio rows first, as before; a primitive row of the room's recipe is not
        # applied by the room's recipe (the method before), the everywhere recipe brings the lantern's
        profiles, applied = self.apply('room-only')
        self.assertEqual(profiles[URN]['ratio'], 0.25)
        self.assertEqual(profiles[URN]['visual_recipe']['name'], 'room-only')
        self.assertEqual(profiles[LANTERN]['visual_recipe']['name'], 'ev')
        self.assertEqual(applied, {LANTERN: 'ev', URN: 'room-only'})

    def test_the_method_before_stays_selectable(self):
        # everywhere_in_rooms false: only recipe_rooms' ratio rows (up to v0.0.67-dev1)
        profiles, applied = self.apply('room-only', everywhere=False)
        self.assertEqual(applied, {URN: 'room-only'})
        self.assertNotIn('visual_primitive', profiles[LANTERN])
        profiles, applied = self.apply(None, everywhere=False)
        self.assertEqual((applied, profiles), ({}, self.profiles))
        # AMIWIND_VISUAL_EVERYWHERE=off: the original meshes outdoors and in the rooms
        with mock.patch.dict(os.environ, {'AMIWIND_VISUAL_EVERYWHERE': 'off'}):
            profiles, applied = self.apply()
        self.assertEqual((applied, profiles), ({}, self.profiles))

    def test_only_the_named_meshes_re_key(self):
        from chim.build import mesh_fingerprint
        before = {m['source']: str(mesh_fingerprint(m, self.profiles[m['source']], [])) for m in self.models}
        profiles, _ = self.apply()
        after = {m['source']: str(mesh_fingerprint(m, profiles[m['source']], [])) for m in self.models}
        self.assertEqual(before[TABLE], after[TABLE])
        self.assertNotEqual(before[LANTERN], after[LANTERN])
        self.assertNotEqual(before[URN], after[URN])
        # the same everywhere row gives the same profile, so the same unit, in every room that places the model
        again, _ = self.apply()
        self.assertEqual(again, profiles)

    def test_the_room_draws_the_replacement_and_keeps_the_original_collision(self):
        from prepare_mesh_bsp import _prepare_model
        from chim.units import _canonical
        profiles, _ = self.apply()
        model = self.models[0]
        with tempfile.TemporaryDirectory() as d:
            pak = Path(d) / 'scenery.mwpak'
            pak.write_bytes(self.raws[LANTERN])
            _, original = _prepare_model((0, model, dict(self.profiles[LANTERN]), pak, []))
            _, replaced = _prepare_model((0, model, profiles[LANTERN], pak, []))
        # the primitive's 20 faces (four paper sides, the spike, the roof and its eaves) in place of the source's
        self.assertEqual(len(replaced[2]), 20)
        self.assertGreater(len(original[2]), len(replaced[2]))
        self.assertEqual(replaced[4]['visual_primitive'], 'lantern_shell')
        # the collision is the original mesh's
        self.assertEqual(_canonical(original[3]), _canonical(replaced[3]))

    def test_a_bad_switch_is_refused(self):
        with mock.patch.object(I, '_rooms_config', return_value={'everywhere_in_rooms': 'yes'}):
            with self.assertRaises(ValueError):
                I.everywhere_in_rooms()
        with mock.patch.object(I, '_rooms_config', return_value={}):
            self.assertTrue(I.everywhere_in_rooms())


class TheShippedDefault(unittest.TestCase):
    def test_every_room_takes_the_everywhere_recipe_by_default(self):
        data = json.loads((ROOT / 'config/chim-rooms.json').read_text(encoding='utf-8'))
        self.assertIs(data['everywhere_in_rooms'], True)
        self.assertTrue(I.everywhere_in_rooms())
        # the room build goes through the one rule (no second copy of the recipe logic in room_input)
        source = (ROOT / 'tools/chim/interior.py').read_text(encoding='utf-8')
        self.assertIn('room_visual_profiles(index[\'models\'], used, profiles, room_recipe(work.name),', source)

    def test_the_real_everywhere_rows_reach_a_room_that_places_them(self):
        # every row of the shipped everywhere recipe applies in a room for a model with its source and SHA-256
        from visual_recipes import load_recipes
        doc = load_recipes()
        rows = doc['recipes'][doc['everywhere']]['models']
        models = [{'source': src, 'sha256': row['sha256'], 'triangles': 1000} for src, row in sorted(rows.items())]
        profiles = {m['source']: {} for m in models}
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('AMIWIND_VISUAL_EVERYWHERE', None)
            applied = I.room_visual_profiles(models, range(len(models)), profiles, None, True, doc)
        self.assertEqual(sorted(applied), sorted(rows))
        self.assertEqual(profiles['meshes/l/light_de_streetlight_01.nif']['visual_primitive']['kind'], 'lantern_shell')


if __name__ == '__main__':
    unittest.main()
