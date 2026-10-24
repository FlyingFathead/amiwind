# SPDX-License-Identifier: GPL-3.0-only
"""Room residents by rule (ROOM-BATCH-NPC-GROUNDING-48) and their bakes through the unit cache
(ROOM-RESIDENTS-NOT-CACHED-48).

Checked on synthetic rooms: an actor standing on the floor, one sitting on a chair, one authored high with a script
(kept where the game data puts it, listed with its script), one with no support under it and an authored-dead one;
the generated file holds no positions or heights, is read by reference number only for an actor the policy does not
name, and never classifies an id everywhere; the batch preflight passes with the generated classes and still refuses
an actor neither file names; a second resident pass bakes nothing (every resident restored from the unit cache,
byte-identical files)."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

import actor_grounding as G  # noqa: E402
import actor_grounding_census as C  # noqa: E402


def plate(z, x0=-100.0, y0=-100.0, x1=100.0, y1=100.0):
    """Two triangles of a level plate at height z (Morrowind units), as world triangles N x 3 x 3."""
    a, b, c, d = (x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)
    return np.array([[a, b, c], [a, c, d]], dtype=float)


def actor(number, ident, z, kind='NPC_', x=0.0, y=0.0):
    return {'number': number, 'id': ident, 'type': kind, 'position': [x, y, z]}


FLOOR = ({'id': 'in_floor_01'}, plate(0.0))
CHAIR = ({'id': 'furn_chair_01'}, plate(40.0, -20, -20, 20, 20))


class Classification(unittest.TestCase):
    def test_floor_sitting_high_none_dead(self):
        floor = C.room_actor(actor(1, 'Standing Guy', 2.0), [FLOOR], {})
        self.assertEqual((floor['class'], floor['gap'], floor['support_kind']), ('floor', 2.0, 'in_floor_01'))
        sitting = C.room_actor(actor(2, 'sitter', 42.0), [FLOOR, CHAIR], {})
        self.assertEqual((sitting['class'], sitting['gap'], sitting['support_kind']), ('floor', 2.0, 'furn_chair_01'))
        high = C.room_actor(actor(3, 'floater', 300.0), [FLOOR], {'script': 'FloatScript'})
        self.assertEqual((high['class'], high['gap'], high['script']), ('off_floor', 300.0, 'FloatScript'))
        just = C.room_actor(actor(4, 'just', C.DROP), [FLOOR], {})
        self.assertEqual(just['class'], 'floor')                     # the fitter's and AW_NPCFloor's reach
        void = C.room_actor(actor(5, 'void', 10.0, x=5000.0), [FLOOR], {})
        self.assertEqual((void['class'], void['gap']), ('no_floor', None))
        dead = C.room_actor(actor(6, 'corpse', 300.0, kind='CREA'), [FLOOR], {'dead': True})
        self.assertEqual(dead['class'], 'authored_dead')
        inside = C.room_actor(actor(7, 'sunk', -20.0), [FLOOR], {})
        self.assertEqual((inside['class'], inside['gap']), ('floor', -20.0))   # a little inside the floor

    def rows(self):
        return [dict(C.room_actor(actor(1, 'Standing Guy', 2.0), [FLOOR], {}), room='Room A'),
                dict(C.room_actor(actor(3, 'floater', 300.0), [FLOOR], {'script': 'FloatScript'}), room='Room A'),
                dict(C.room_actor(actor(6, 'corpse', 0.0), [FLOOR], {'dead': True}), room='Room B')]

    def test_document_has_no_positions(self):
        doc = C.rooms_document(self.rows(), ['Room A', 'Room B'], 'f' * 64)
        self.assertEqual(doc['format'], G.ROOMS_FORMAT)
        self.assertEqual(doc['rooms'], {'Room A': {'floor': [[1, 'standing guy']],
                                                   'off_floor': [[3, 'floater', 'FloatScript']]},
                                        'Room B': {'authored_dead': [[6, 'corpse']]}})
        text = C.rooms_text(doc)
        self.assertEqual(json.loads(text), doc)
        self.assertNotIn('300', text)
        self.assertNotIn('"position"', text)
        self.assertNotIn('"gap"', text)

    def test_lookup_by_reference_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'rooms.json'
            path.write_text(C.rooms_text(C.rooms_document(self.rows(), ['Room A', 'Room B'], 'f' * 64)))
            with patch.object(G, 'ROOMS', path):
                self.assertEqual(G.initial_state('Standing Guy', 1), 'ground')
                self.assertEqual(G.initial_state('floater', '3'), 'authored')
                self.assertEqual(G.fields('floater', 3)['aw_ground_mode'], 1)
                self.assertEqual(G.fields('standing guy', 1)['aw_ground_mode'], 0)
                self.assertEqual(G.initial_state('corpse', 6), 'authored_dead')
                with self.assertRaises(ValueError):
                    G.initial_state('floater')                       # never by id alone
                with self.assertRaises(ValueError):
                    G.initial_state('someone else', 1)               # the reference names another actor
                # the policy wins where it names the id (a shipped town resident keeps its class)
                named = json.loads(G.POLICY.read_text())['ground_npcs'][0]
                self.assertEqual(G.initial_state(named, 3), 'ground')

    def test_the_ground_bake_leaves_room_maps_and_shells(self):
        # ACTOR-GROUND-BAKE-CHIM-ROOMS-48: the bake loaded the 935 batch-room shells as classic collision scenes
        source = (Path(G.__file__)).read_text(encoding='utf-8')
        bake = source[source.index('def bake_ground('):]
        bake = bake[:bake.index('\ndef ')] if '\ndef ' in bake else bake
        self.assertIn('not is_chim_room(p)', bake)
        self.assertIn('not is_shell_map(', bake)
        scene = source[source.index('    def _scene(self, name):'):]
        self.assertIn("name + '.bsp: '", scene[:scene.index('\n    def ', 10)])

    def test_the_image_annotation_passes_the_reference(self):
        # ACTOR-ANNOTATE-ROOM-REFERENCE-48: the image's actor annotation asked by id alone, so a room corpse
        # classified by reference ('dead de male_01', Ald Redaynia Tower) stopped the image step
        source = (Path(G.__file__)).read_text(encoding='utf-8')
        annotate = source[source.index('def _annotate_map('):]
        annotate = annotate[:annotate.index('\ndef ')]
        self.assertIn("fields(identifier, e.get('aw_ref'))", annotate)
        self.assertNotIn('fields(identifier)', annotate)
        rooms = json.loads(G.ROOMS.read_text(encoding='utf-8'))
        rooms = rooms.get('rooms', rooms)
        number = next(n for row in rooms.values() if isinstance(row, dict)
                      for n, name in row.get('authored_dead', ()) if name == 'dead de male_01')
        self.assertEqual(G.fields('dead de male_01', str(number))['aw_ground_mode'], 1)


class Preflight(unittest.TestCase):
    def test_batch_preflight_passes_with_the_generated_classes(self):
        import chim_room_batches as S
        cells = {'ria': {'refs': [{'type': 'NPC_', 'id': 'Standing Guy', 'number': 1},
                                  {'type': 'NPC_', 'id': 'floater', 'number': 3},
                                  {'type': 'STAT', 'id': 'wall', 'number': 9}]},
                 'rib': {'refs': [{'type': 'NPC_', 'id': 'nobody xyz', 'number': 77}]}}
        rows = Classification.rows(None)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'rooms.json'
            path.write_text(C.rooms_text(C.rooms_document(rows, ['Room A', 'Room B'], 'f' * 64)))
            with patch.object(G, 'ROOMS', path), patch.object(S, 'read_cells', lambda data, rooms: cells):
                problems, _ = S.unclassified_residents('data', [{'map': 'ria', 'cell': 'Room A'}])
                self.assertEqual(problems, {})
                problems, _ = S.unclassified_residents('data', [{'map': 'ria', 'cell': 'Room A'},
                                                                {'map': 'rib', 'cell': 'Room B'}])
                self.assertEqual(problems, {'Room B': ['nobody xyz']})

    def test_the_repo_file_covers_every_room_actor_it_lists(self):
        """The generated file is sound: its format, every class known, no reference twice, no positions."""
        if not G.ROOMS.is_file():
            self.skipTest('no generated room file')
        doc = json.loads(G.ROOMS.read_text(encoding='utf-8'))
        self.assertEqual(doc['format'], G.ROOMS_FORMAT)
        seen = set()
        for room, classes in doc['rooms'].items():
            self.assertTrue(set(classes) <= set(G.ROOM_STATES), room)
            for rows in classes.values():
                for row in rows:
                    self.assertNotIn(row[0], seen)
                    seen.add(row[0])
                    self.assertTrue(all(not isinstance(v, float) for v in row))
        self.assertEqual(len(G.room_classes()), len(seen))


class ResidentReuse(unittest.TestCase):
    """A second pass of the resident bakes bakes nothing: every resident comes from the unit cache."""

    def test_second_pass_bakes_nothing(self):
        import prepare_area as P
        baked = []

        def fake_bake(task):
            ident = task[2]['id']
            baked.append(ident)
            return ident, b'mdl ' + ident.encode(), b'wav ' + ident.encode(), {
                'appearance': task[2], 'greeting': task[3], 'step': 0.25, 'triangles': 3, 'frames': 8,
                # a tuple, as real records hold (the first measured run stored only the records without one)
                'bounds': ((0, 0, 0), (1, 1, 1)), 'sha256': 'x', 'voice_seconds': 1.0,
                'greeting_lines': {'hello': [('line', None)]}}
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            lock = tmp / 'inputs.json'
            lock.write_text(json.dumps({'schema': __import__('known_inputs').LOCK_SCHEMA,
                                        'files': {'Morrowind.esm': {'sha256': '0' * 64}}}))
            ffmpeg = tmp / 'ffmpeg'
            ffmpeg.write_bytes(b'not a real program')
            env = {'AMIWIND_PASS_CACHE': str(tmp / 'cache'), __import__('known_inputs').LOCK_ENV: str(lock)}
            apps = [{'id': i, 'parts': [], 'skeleton': 's'} for i in ('anna', 'bert')]
            tasks = [('data', b'p' * 768, a, {'text': 'Hi', 'voice': 'v.mp3'}, str(ffmpeg), {'mode': 'off', 'pool': None})
                     for a in apps]
            with patch.dict(os.environ, env), patch.object(P, 'build_resident', fake_bake):
                out = {}
                for run in ('one', 'two'):
                    id1 = tmp / run / 'id1'
                    id1.mkdir(parents=True)
                    for task in tasks:
                        folder = tmp / run / 'units' / task[2]['id']
                        ident, record, made = P.build_resident_cached((task, str(folder)))
                        P.install_resident(folder, id1, record)
                        self.assertFalse(folder.exists())
                        self.assertEqual(made, run == 'one')
                        out.setdefault(run, {})[ident] = record
                    files = {p.relative_to(id1).as_posix(): p.read_bytes() for p in id1.rglob('*') if p.is_file()}
                    out[run + '-files'] = files
                self.assertEqual(sorted(baked), ['anna', 'bert'])            # baked once each
                self.assertEqual(out['one'], out['two'])
                self.assertEqual(out['one-files'], out['two-files'])
                self.assertEqual(len(out['two-files']), 4)                  # two models, two voices
                # a changed input bakes that resident again
                changed = (tasks[0][0], tasks[0][1], dict(apps[0], parts=['x']), *tasks[0][3:])
                P.build_resident_cached((changed, str(tmp / 'three')))
                self.assertEqual(baked[-1], 'anna')
                self.assertEqual(len(baked), 3)

    def test_without_the_cache_it_bakes(self):
        import prepare_area as P
        with patch.dict(os.environ, {'AMIWIND_PASS_CACHE': 'off'}):
            self.assertEqual(P.resident_unit(('d', b'p', {'id': 'x'}, {}, 'ffmpeg')), (None, None))


if __name__ == '__main__':
    unittest.main()
