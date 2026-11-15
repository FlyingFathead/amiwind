# SPDX-License-Identifier: GPL-3.0-only
"""The build stages that first ran with Tribunal and Bloodmoon selected in v0.0.66-dev2, on small synthetic game data
(no game files): the exterior checklist hashes the same selected game data as the world survey
(EXTERIOR-PLAN-MASTER-LAYERS-66); the world scenery coverage leaves out the placements of exterior cells only an
expansion adds (EXTERIOR-EXPANSION-ONLY-CELLS-66); the world door table holds back the doors of places the build does
not hold (EXPANSION-DOORS-HELD-BACK-66); the creature readers read the expansions' archives
(ACTOR-LIBRARY-BASE-ARCHIVE-66). With the base game alone every result is the one before."""
import hashlib
import json
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools'), str(ROOT / 'tests')]

import exterior_plan as E  # noqa: E402
from mwad.masters import master_path  # noqa: E402
from test_layered_archives import write_bsa  # noqa: E402

BOTH = ['Morrowind.esm', 'Tribunal.esm']


def sub(tag, data):
    return struct.pack('<4sI', tag.encode(), len(data)) + data


def rec(tag, *subs):
    payload = b''.join(subs)
    return struct.pack('<4sIII', tag.encode(), len(payload), 0, 0) + payload


def tes3(*masters):
    out = [sub('HEDR', struct.pack('<fI', 1.3, 0) + b'\0' * 288 + struct.pack('<I', 0))]
    for m in masters:
        out += [sub('MAST', m.encode() + b'\0'), sub('DATA', struct.pack('<Q', 0))]
    return rec('TES3', *out)


def cell(x, y):
    return rec('CELL', sub('NAME', b'\0'), sub('DATA', struct.pack('<Iii', 2, x, y)))


def land(x, y, heights=True):
    return rec('LAND', sub('INTV', struct.pack('<ii', x, y)), *([sub('VHGT', b'\0' * 8)] if heights else []))


class GameData:
    """A data folder: the base game file (cells 0,0 and 1,0 and a LAND without heights at 2,0) and Tribunal.esm, which
    edits cell 1,0, gives 2,0 its heights and adds 9,9 (an exterior cell only it has)."""

    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name) / 'Data Files'
        self.data.mkdir()
        self.merged = Path(self.tmp.name) / 'merged'
        (self.data / 'Morrowind.esm').write_bytes(tes3() + cell(0, 0) + land(0, 0) + land(1, 0) +
                                                  land(2, 0, heights=False))
        (self.data / 'Tribunal.esm').write_bytes(tes3('Morrowind.esm') + land(1, 0) + land(2, 0) + cell(9, 9) +
                                                 land(9, 9))


class SelectedCellsTests(unittest.TestCase):
    def setUp(self):
        self.game = GameData()

    def tearDown(self):
        self.game.tmp.cleanup()

    def test_base_game_alone_is_the_base_files_checklist(self):
        got = E.selected_cells(self.game.data, ['Morrowind.esm'], self.game.merged)
        self.assertEqual(got, E.source_cells(self.game.data / 'Morrowind.esm'))
        self.assertEqual(got[1], hashlib.sha256((self.game.data / 'Morrowind.esm').read_bytes()).hexdigest())

    def test_expansions_hash_the_merged_master_over_the_base_grid(self):
        cells, digest = E.selected_cells(self.game.data, BOTH, self.game.merged)
        merged = master_path(self.game.data, BOTH, self.game.merged)
        self.assertEqual(digest, hashlib.sha256(merged.read_bytes()).hexdigest())     # the survey's master_sha256
        self.assertNotEqual(digest, E.source_cells(self.game.data / 'Morrowind.esm')[1])
        # 2,0 gets its heights from Tribunal and is in the base grid; 9,9 only Tribunal has: listed, not planned
        self.assertEqual(cells, [(0, 0), (1, 0), (2, 0)])
        self.assertEqual(E.base_grid(self.game.data / 'Morrowind.esm'), {(0, 0), (1, 0), (2, 0)})

    def test_base_grid_is_the_surveys_rule(self):
        try:
            import survey_vvardenfell
        except ImportError as exc:   # the survey's own libraries (numpy, Pillow, the NIF reader)
            self.skipTest('survey reader not importable here: %s' % exc)
        path = self.game.data / 'Morrowind.esm'
        self.assertEqual(E.base_grid(path), survey_vvardenfell.base_grid(path))

    def test_the_terrain_stage_takes_the_checklist_of_the_selected_masters(self):
        cells, digest = E.selected_cells(self.game.data, BOTH, self.game.merged)
        plan = E.make(cells, [], (), digest)
        entries = [dict(name='vf%04d' % i, cell=list(c), origin=[c[0] * 2048 + 1024, c[1] * 2048 + 1024, 0],
                        core=[[-1024] * 2, [1024] * 2]) for i, c in enumerate(cells)]
        survey = hashlib.sha256(master_path(self.game.data, BOTH, self.game.merged).read_bytes()).hexdigest()
        self.assertEqual(set(E.classify_regions(plan, entries, survey, []).values()), {'bsp'})
        # the v0.0.66-dev2 failure: a checklist of the base game file against the merged survey
        old = E.make(*E.source_cells(self.game.data / 'Morrowind.esm')[:1], [], (),
                     E.source_cells(self.game.data / 'Morrowind.esm')[1])
        with self.assertRaisesRegex(ValueError, 'master differs from the terrain survey'):
            E.classify_regions(old, entries[:2], survey, [])


class UnplannedTests(unittest.TestCase):
    PLAN = {'cells': [{'cell': [0, 0]}, {'cell': [1, 0]}], 'towns': []}

    def test_only_references_outside_the_planned_cells(self):
        refs = [{'cell': [0, 0], 'number': 1}, {'cell': [9, 9], 'number': 2}, {'number': 3}]
        self.assertEqual(E.unplanned(refs, self.PLAN), [refs[1]])
        self.assertEqual(E.unplanned(refs, None), [])           # no checklist: nothing left out

    def test_planned_cells_of_a_terrain_output(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertIsNone(E.planned_cells(td))
            Path(td, 'world-regions.json').write_text(json.dumps({'exterior_checklist': self.PLAN}))
            self.assertEqual(E.planned_cells(td), {(0, 0), (1, 0)})
            Path(td, 'world-regions.json').write_text(json.dumps({'regions': []}))
            self.assertIsNone(E.planned_cells(td))

    def test_world_scenery_leaves_out_the_expansion_only_cells(self):
        import prepare_world_scenery as S
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            terrain, scenery = root / 'terrain', root / 'scenery'
            terrain.mkdir()
            scenery.mkdir()
            palette = root / 'palette.lmp'
            palette.write_bytes(bytes(768))
            regions = [{'name': 'vf0000', 'cell': [0, 0], 'chim_region': True},
                       {'name': 'vf0001', 'cell': [1, 0], 'routing_only': True}]
            (terrain / 'world-regions.json').write_text(json.dumps(
                {'master_sha256': 'm', 'regions': regions, 'exterior_checklist': self.PLAN}))
            refs = [{'cell': [0, 0], 'number': 1}, {'cell': [9, 9], 'number': 2}]
            (scenery / 'scenery-index.json').write_text(json.dumps(
                {'errors': [], 'master_sha256': 'm', 'references': refs}))
            with patch.object(S, 'unit_cache', return_value=(None, None)):
                receipt = S.prepare(terrain, scenery, palette, root / 'out', 1)
                self.assertEqual(receipt['unplanned_source_references'], 1)
                # a placement of a planned cell no map holds is still refused
                refs.append({'cell': [1, 0], 'number': 3})
                (scenery / 'scenery-index.json').write_text(json.dumps(
                    {'errors': [], 'master_sha256': 'm', 'references': refs}))
                with self.assertRaisesRegex(ValueError, 'omitted source references'):
                    S.prepare(terrain, scenery, palette, root / 'out2', 1)


def door(number, source_cell, position, destination_cell, arrival):
    return {'number': number, 'id': 'door_%d' % number, 'source_interior': bool(source_cell),
            'source_cell': source_cell, 'position': list(position), 'destination_cell': destination_cell,
            'destination_interior': bool(destination_cell),
            'destination': {'position': list(arrival), 'rotation_radians': [0.0, 0.0, 0.0]}}


class HeldBackDoorTests(unittest.TestCase):
    def setUp(self):
        import world_doors
        self.W = world_doors
        here, far = (1000.0, 1000.0, 0.0), (9 * 8192 + 100.0, 9 * 8192 + 100.0, 0.0)
        self.doors = [door(1, '', here, 'Held Room', (0.0, 0.0, 0.0)),        # resolves
                      door(2, '', far, 'Held Room', (0.0, 0.0, 0.0)),         # in a cell the build does not plan
                      door(3, 'Held Room', (0.0, 0.0, 0.0), '', far),          # its way out there
                      door(4, '', here, 'Refused Room', (0.0, 0.0, 0.0)),     # a room the batch stage refused
                      door(5, '', here, 'Missing Room', (0.0, 0.0, 0.0))]     # a room nobody accounts for
        self.args = ({'held room': 'heldroom'}, [], {(0, 0): ('r0', [0.0, 0.0, 0.0])})

    def rows(self, **kw):
        rooms, towns, regions = self.args
        return {r['reference']: r for r in self.W.table(self.doors, rooms, towns, regions, {}, **kw)}

    def test_without_held_back_places_every_unresolved_door_is_a_problem(self):
        rows = self.rows()
        self.assertEqual(sorted(n for n, r in rows.items() if 'problem' in r), [2, 3, 4, 5])
        self.assertFalse(any('held_back' in r for r in rows.values()))
        self.assertNotIn('held_back', json.dumps(self.W.summary(list(rows.values()))))

    def test_places_the_build_does_not_hold_are_held_back_and_named(self):
        held = self.W.held_back_places({'exterior_like': [{'cell': 'Big Plaza', 'state': 'waiting'}],
                                        'refused': {'Refused Room': 'ValueError: no placement to convert'}})
        self.assertEqual(held, {'big plaza': 'waiting',
                                'refused room': 'refused by the room batch stage (ValueError: no placement to convert)'})
        rows = self.rows(planned={(0, 0)}, held_back=held)
        self.assertEqual(sorted(n for n, r in rows.items() if 'held_back' in r), [2, 3, 4])
        self.assertIn('9,9', rows[2]['held_back'])
        self.assertIn('Refused Room is held back', rows[4]['held_back'])
        self.assertEqual(self.W.unresolved_problems(list(rows.values())),
                         [self.W.unresolved_problems([rows[5]])[0]])
        self.assertEqual(rows[1]['target'], 'heldroom')
        self.assertEqual(rows[1], self.rows()[1])                  # a resolving door is the same row as before


class ExpansionArchiveTests(unittest.TestCase):
    def test_creature_assets_read_the_selected_archives(self):
        import creature_library
        import creature_tables
        with tempfile.TemporaryDirectory() as td:
            data = Path(td)
            write_bsa(data / 'Morrowind.bsa', {'meshes\\r\\base.nif': b'base'})
            write_bsa(data / 'Tribunal.bsa', {'meshes\\r\\goblin01.nif': b'goblin'})
            for masters, readable in (('Morrowind.esm,Tribunal.esm', True), ('Morrowind.esm', False)):
                creature_tables._assets.clear()
                with patch.dict(os.environ, {'AMIWIND_MASTERS': masters}):
                    assets = creature_library.layered_assets(data)
                    # the skeletal method's reader takes the same assets (its cache, filled first)
                    self.assertIs(creature_tables._open(data), assets)
                    self.assertEqual(assets.read('meshes/r/base.nif'), b'base')
                    if readable:
                        self.assertEqual(assets.read('meshes/r/goblin01.nif'), b'goblin')
                    else:
                        with self.assertRaises(KeyError):
                            assets.read('meshes/r/goblin01.nif')
            creature_tables._assets.clear()


if __name__ == '__main__':
    unittest.main()
