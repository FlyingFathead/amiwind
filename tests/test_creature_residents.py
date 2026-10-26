# SPDX-License-Identifier: GPL-3.0-only
"""Interior creatures in the resident stage (tools/creature_residents.py, INTERIOR-CREATURES-MISSING-41)."""
import ast
import os
import struct
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

import creature_residents as cr  # noqa: E402


def crea(health=100, model='r\\LordVivec.NIF'):
    npdt = struct.pack('<10i', 0, 50, 1, 1, 1, 1, 1, 1, 1, 1) + struct.pack('<i', health) + bytes(52)
    return [('NAME', b'x\0'), ('MODL', model.encode() + b'\0'), ('FNAM', b'Vivec\0'), ('NPDT', npdt)]


def ref(number, ident, kind='CREA', **extra):
    row = dict(number=number, id=ident, type=kind, scale=1.0, position=[0, 0, 0], rotation_radians=[0, 0, 0])
    row.update(extra)
    return row


KINDS = {'CREA': {'vivec_god': crea(), 'rat': crea(model='r\\Rat.nif'), 'dead_rat': crea(health=0)}}


class Selection(unittest.TestCase):
    def run_mode(self, mode, refs):
        with mock.patch.dict(os.environ, {cr.ENV: mode}):
            return cr.select(refs, KINDS, 'room')

    def test_listed_mode_places_vivec_and_names_every_other_reference(self):
        refs = [ref(1, 'vivec_god'), ref(2, 'rat'), ref(3, 'lev', 'LEVC'), ref(4, 'npc', 'NPC_'),
                ref(5, 'vivec_god', deleted=True)]
        placed, left = self.run_mode('listed', refs)
        self.assertEqual([r['number'] for r in placed], [1])
        reasons = {r['reference']: r['reason'] for r in left}
        self.assertEqual(sorted(reasons), [2, 3, 5])           # the NPC is not a creature row
        self.assertIn('not listed', reasons[2])
        self.assertIn('levelled', reasons[3])
        self.assertIn('deleted', reasons[5])
        self.assertTrue(all(r['map'] == 'room' and r['id'] for r in left))

    def test_off_mode_is_the_previous_method(self):
        placed, left = self.run_mode('off', [ref(1, 'vivec_god'), ref(2, 'rat')])
        self.assertEqual(placed, [])
        self.assertEqual({r['reason'] for r in left}, {'creatures off (--interior-creatures off)'})

    def test_all_mode_leaves_out_unclassified_dead_and_scaled(self):
        placed, left = self.run_mode('all', [ref(1, 'vivec_god'), ref(2, 'rat'), ref(3, 'dead_rat'),
                                             ref(4, 'vivec_god', scale=1.5), ref(5, 'missing')])
        self.assertEqual([r['number'] for r in placed], [1])
        reasons = {r['reference']: r['reason'] for r in left}
        self.assertIn('grounding classification', reasons[2])
        self.assertIn('dead', reasons[3])
        self.assertIn('instance scale', reasons[4])
        self.assertIn('no creature record', reasons[5])

    def test_unknown_mode_refused(self):
        with mock.patch.dict(os.environ, {cr.ENV: 'some'}):
            with self.assertRaises(ValueError):
                cr.mode()

    def test_default_mode_is_listed(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(cr.ENV, None)
            self.assertEqual(cr.mode(), 'listed')


class Config(unittest.TestCase):
    def test_every_listed_creature_has_a_reason_source_and_support_state(self):
        from actor_grounding import initial_state
        rows = cr.listed()
        self.assertIn('vivec_god', rows)
        for key in rows:
            self.assertIn(initial_state(key), ('ground', 'flying', 'levitating', 'swimming'))

    def test_dagoth_ur_and_the_heart_are_placed_dagoth_whole(self):
        # CREATURE-DAGOTH-UR-ABSENT-52: neither Dagoth Ur nor the Heart of Lorkhan was ever placed (creatures not on
        # the list); Dagoth Ur bakes with the gallery's whole-model profile (every original triangle)
        from prepare_gallery import quality_profiles
        rows = cr.listed()
        for key in ('dagoth_ur_1', 'dagoth_ur_2', 'heart_akulakhan'):
            self.assertIn(key, rows)
        self.assertEqual(quality_profiles()['r/dagothr.nif']['encoding'], 'shared-vertex')
        source = (Path(cr.__file__)).read_text(encoding='utf-8')
        self.assertIn("if profile and profile.get('encoding') == 'shared-vertex':", source)

    def test_vivec_is_levitating_so_ground_check_and_floor_snap_leave_him(self):
        from actor_grounding import fields
        self.assertEqual(fields('vivec_god')['aw_ground_mode'], 1)   # aw_scene.c AW_NPCFloor returns at once

    def test_vivec_profile_names_his_authored_idle(self):
        from prepare_gallery import quality_profiles
        profile = quality_profiles()['r/lordvivec.nif']
        self.assertEqual(profile['pose_event'].split(':')[0], 'idle2')
        self.assertTrue(profile['preserve_airborne'])


class IdleRange(unittest.TestCase):
    def skeleton(self, events):
        return type('S', (), {'events': events})()

    def test_profile_group_loop_range(self):
        s = self.skeleton({'idle2: start': 0., 'idle2: loop start': 4.33, 'idle2: loop stop': 7., 'idle2: stop': 10.})
        self.assertEqual(cr.idle_range(s, {'pose_event': 'idle2: loop start'}), ('idle2', 4.33, 7.))

    def test_default_idle_without_loop_keys(self):
        s = self.skeleton({'idle: start': 0., 'idle: stop': 2.})
        self.assertEqual(cr.idle_range(s, None), ('idle', 0., 2.))

    def test_missing_range_refused(self):
        with self.assertRaises(ValueError):
            cr.idle_range(self.skeleton({'walkforward: start': 0.}), None)


class Wiring(unittest.TestCase):
    def test_resident_stage_lists_left_out_references_and_places_creatures(self):
        text = (ROOT / 'tools/prepare_area.py').read_text()
        tree = ast.parse(text)
        populate = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'populate')
        source = ast.get_source_segment(text, populate)
        for needle in ('creature_residents.select', 'creature_residents.safe_bake', "'left_out':left_out",
                       "kinds['CREA']"):
            self.assertIn(needle, source)

    def test_build_sets_the_mode_for_the_stages(self):
        text = (ROOT / 'tools/build.py').read_text()
        self.assertIn("os.environ['AMIWIND_INTERIOR_CREATURES']", text)
        self.assertIn('creature_residents.add_option(p)', text)


if __name__ == '__main__':
    unittest.main()


class Populate(unittest.TestCase):
    """A listed creature reaches the room's cast and map; the others are listed as left out."""

    def test_listed_creature_is_placed_in_its_room(self):
        import contextlib
        import hashlib
        import re
        import tempfile
        import prepare_area as area
        from player_hull import pack_lumps, lumps
        from chim.frame_map import empty_world
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {cr.ENV: 'listed'}):
            root = Path(tmp); (root / 'Morrowind.esm').write_bytes(b'fictional master fixture')
            scene = root / 'scene'; (scene / 'id1/maps').mkdir(parents=True); (scene / 'id1/progs').mkdir()
            (scene / 'id1/gfx').mkdir(); (scene / 'id1/gfx/palette.lmp').write_bytes(bytes(768))
            chunks = empty_world([-32., -32., -32.], [32., 32., 32.]); chunks[0] = b'{"classname" "worldspawn"}' + bytes([0])
            (scene / 'id1/maps/room.bsp').write_bytes(pack_lumps(chunks))
            refs = [ref(405515, 'vivec_god', position=[4., 8., -390.], rotation_radians=[0., 0., 3.14159265]),
                    ref(7, 'rat'), ref(8, 'some list', 'LEVC')]
            rawmodel = b'fictional creature model'
            calls = []

            def producer(function, tasks, workers):
                calls.append(function.__name__)
                if function.__name__ != 'safe_bake':
                    self.assertEqual(tasks, []); return []
                self.assertEqual([t[2]['id'] for t in tasks], ['vivec_god'])
                return [('vivec_god', rawmodel, {'appearance': {'id': 'vivec_god', 'name': 'Vivec', 'kind': 'CREA'},
                         'greeting': {'text': '', 'voice': ''}, 'step': .33, 'frames': 8, 'triangles': 1,
                         'idle': {'group': 'idle2'}, 'lift': 13.9, 'sha256': hashlib.sha256(rawmodel).hexdigest()})]
            with contextlib.ExitStack() as stack:
                for name, value in {'load_master': ({'NPC_': {}, 'CREA': dict(KINDS['CREA'])}, [], {}),
                                    'behavior_record': {}}.items():
                    stack.enter_context(mock.patch.object(area, name, return_value=value))
                stack.enter_context(mock.patch.object(area, 'ordered_map', side_effect=producer))
                stack.enter_context(mock.patch.object(area.npc_lod, 'publish', return_value={'mode': 'off'}))
                report = area.populate(root, scene, rooms={'room': {'refs': refs}}, reports=[], jobs=1,
                                       include_exterior=False, doors=False)
            self.assertIn('safe_bake', calls)
            self.assertEqual([(c['map'], c['reference']) for c in report['cast']], [('room', 405515)])
            self.assertEqual(report['creatures'], {'mode': 'listed', 'placed': 1})
            self.assertEqual(sorted(r['reference'] for r in report['left_out']), [7, 8])
            stem = 'a_' + hashlib.sha256(b'vivec_god').hexdigest()[:12]
            self.assertEqual((scene / 'id1/progs' / (stem + '.mdl')).read_bytes(), rawmodel)
            text = lumps((scene / 'id1/maps/room.bsp').read_bytes())[0].decode('cp1252')
            block = next(b for b in re.findall(r'\{[^{}]*\}', text) if '"aw_npc"' in b)
            self.assertIn('"aw_ground_mode" "1"', block)       # levitating: no floor snap, no contact fit
            self.assertIn('"aw_source_id" "vivec_god"', block)
            self.assertIn('"aw_hello_distance" "0"', block)
            self.assertIn('"origin" "1.00000 2.00000 -97.50000"', block)
