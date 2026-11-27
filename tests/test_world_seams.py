# SPDX-License-Identifier: GPL-3.0-only
"""The open world's seams and edges (tools/world_seams.py; SOL-SEA-INVISIBLE-BLOCKER-68,
ACTOR-CLIP-ABOVE-DRAWN-BODY-69): nothing stops or holds a player inside the map's box that the original does not
have. The checks on synthetic
worlds: the engine's bounds table (holes, open sides inside the box, the grid), every cell of the box in exactly one
exterior store (a town's frame covering several cells), the creatures in the water against the collision rule of
aw_actor_clip.c (the person box alone counted beside it), collision without a drawn face (flora cards apart), and that
the tool's numbers are the engine's."""
import json
import re
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tools', ROOT / 'src'):          # src first: tools/mwad.py is a command, src/mwad the package
    while str(_p) in sys.path:
        sys.path.remove(str(_p))
    sys.path.insert(0, str(_p))

import world_seams as W  # noqa: E402


def row(name, origin, core):
    return name.encode('ascii').ljust(8, b'\0') + struct.pack('<3f', *origin) + struct.pack('<4f', *core) + \
        struct.pack('<4f', core[0] - 896, core[1] - 896, core[2] + 896, core[3] + 896)


def directory(kind, rows):
    head = (b'AWR2' + struct.pack('<I', len(rows))).ljust(64, b'\0') if kind == 'AWR2' else \
        b'AWS1' + struct.pack('<I', len(rows))
    return head + b''.join(rows)


def cell_rows(prefix, cells):
    """one region map a cell, its core the cell (origin at the cell's corner)"""
    return [row('%s%04d' % (prefix, i), (x * 2048.0, y * 2048.0, 0), (0, 0, 2048, 2048))
            for i, (x, y) in enumerate(cells)]


BOX = (-2, -2, 2, 2)
ALL = [(x, y) for x in range(-2, 3) for y in range(-2, 3)]


class BoundsTable(unittest.TestCase):
    def test_both_directory_forms_read_as_the_engine_reads_them(self):
        base = W.directory_rows(directory('AWR2', cell_rows('vf', ALL[:20])))
        layer = W.directory_rows(directory('AWS1', cell_rows('sl', ALL[20:])))
        self.assertEqual(len(base) + len(layer), 25)
        self.assertEqual(base[0][0], 'vf0000')
        self.assertEqual(set(W.bounds_cells(base + layer)), set(ALL))
        with self.assertRaises(ValueError):
            W.directory_rows(b'XXXX' + bytes(60))
        with self.assertRaises(ValueError):
            W.directory_rows(directory('AWS1', cell_rows('sl', ALL[:2]))[:-1])

    def test_a_whole_box_has_walls_only_on_its_perimeter(self):
        b = W.bounds_check(set(ALL), BOX)
        self.assertEqual((b['holes'], b['inner_sides'], b['perimeter_sides'], b['fits_grid']), ([], [], 20, True))
        self.assertEqual(W.check({'bounds': b, 'stores': W.stores_check({'chim': {c: 'f' for c in ALL}}, BOX)}), [])

    def test_a_missing_sea_cell_is_a_hole_with_walls_round_it(self):
        b = W.bounds_check(set(ALL) - {(0, 0)}, BOX)
        self.assertEqual(b['holes'], [[0, 0]])
        self.assertEqual(len(b['inner_sides']), 4)          # the current would stand round it, in the middle of the sea
        findings = W.check({'bounds': b, 'stores': W.stores_check({'chim': {c: 'f' for c in ALL}}, BOX)})
        self.assertEqual(len(findings), 2)

    def test_the_engine_grid_bounds_the_table(self):
        far = set(ALL) | {(200, 0)}
        b = W.bounds_check(far, BOX)
        self.assertFalse(b['fits_grid'])
        self.assertEqual(b['outside'], [[200, 0]])
        self.assertEqual(b['groups'], [25, 1])


class Stores(unittest.TestCase):
    def test_a_town_frame_covers_the_cells_of_its_core(self):
        region = {'cell': (0, 0), 'centre': (4096.0, 4096.0), 'low': (-1920.0, -1920.0), 'nx': 15, 'ny': 15,
                  'grain': 256}
        self.assertEqual(W.frame_cells(region), [(0, 0)])
        # Seyda Neen's frame of the v0.0.69-dev5 build (42 x 39 chunks): cells x -4..1, y -11..-7
        town = {'cell': (-2, -9), 'centre': (-11264.0, -71680.0), 'low': (-4608.0, -5376.0), 'nx': 42, 'ny': 39,
                'grain': 256}
        cells = W.frame_cells(town)
        self.assertEqual((min(c[0] for c in cells), max(c[0] for c in cells)), (-4, 1))
        self.assertEqual((min(c[1] for c in cells), max(c[1] for c in cells)), (-11, -7))
        self.assertEqual(W.frame_cells({'cells': [(3, 4), (3, 5)]}), [(3, 4), (3, 5)])

    def test_every_cell_in_one_store_and_the_store_edges(self):
        sea = {c: 'f' for c in ALL if c[0] < 0}
        land = {c: 'f' for c in ALL if c[0] >= 0}
        s = W.stores_check({'chim': land, 'chimsea': sea}, BOX)
        self.assertEqual((s['gaps'], s['doubles'], s['edges']), ([], [], {'chim|chimsea': 5}))
        land[(-1, 0)] = 'f'
        del sea[(-2, -2)]
        s = W.stores_check({'chim': land, 'chimsea': sea}, BOX)
        self.assertEqual(s['gaps'], [[-2, -2]])
        self.assertEqual(s['doubles'], [[[-1, 0], ['chim', 'chimsea']]])


class Creatures(unittest.TestCase):
    def test_the_rule_is_the_engines(self):
        clip = (ROOT / 'engine/aga/src/aw_actor_clip.h').read_text(encoding='utf-8')
        self.assertIn('#define AW_ACTOR_CLIP_MIN %.1ff' % W.ACTOR_CLIP_MIN, clip)
        qc = (ROOT / 'engine/aga/qc/world.qc').read_text(encoding='utf-8')
        self.assertIn("setsize(self,'-7.32 -7.12 0','7.32 7.12 %.2f');" % W.PERSON_TOP, qc)
        bounds = (ROOT / 'engine/aga/src/aw_bounds.h').read_text(encoding='utf-8')
        self.assertIn('#define AW_BOUNDS_GRID %d ' % W.GRID, bounds)
        self.assertIn('#define AW_BOUNDS_CELL %.1ff' % W.CELL, bounds)
        self.assertEqual(W.clip_top(11.34), 11.34)
        self.assertEqual(W.clip_top(50), W.PERSON_TOP)
        self.assertEqual(W.clip_top(0), W.PERSON_TOP)
        self.assertEqual(W.clip_top(.2), W.ACTOR_CLIP_MIN)
        self.assertAlmostEqual(W.clip_top(11.34, 2), 22.68)

    def test_a_swimmer_under_the_surface_no_longer_stands_above_it(self):
        # the measured horker at cell -19,17 (key 8422013): its record 22.2 units under the surface, its drawn idle pose
        # 11.34 units tall; one on land and one whose back shows above the water are no finding
        horker = {'model': 'progs/c_9d8917efa100_k.mdl', 'aw_source_id': 'bm_horker_large'}
        rows = [({'key': 8422013, 'origin': (657.4, -739.4, -22.2)}, horker, (-19, 17), 1.0),
                ({'key': 2, 'origin': (0, 0, 10.0)}, horker, (0, 0), 1.0),
                ({'key': 3, 'origin': (0, 0, -5.0)}, horker, (0, 0), 1.0)]
        a = W.actors_check(rows, {'progs/c_9d8917efa100_k.mdl': 11.34})
        self.assertEqual((a['water'], a['water_blockers_person_box'], a['water_blockers'], a['lowered']), (2, 1, 0, 3))
        self.assertEqual(a['examples'][0]['key'], 8422013)
        self.assertAlmostEqual(a['examples'][0]['person_box_top'], 11.05)
        self.assertAlmostEqual(a['examples'][0]['collision_top'], -10.86)
        self.assertEqual(a['person_box_by_creature'], {'bm_horker_large': 1})
        # a model whose height cannot be read keeps the person box and is a finding
        a = W.actors_check(rows, {'progs/c_9d8917efa100_k.mdl': None})
        self.assertEqual(a['unreadable'], ['progs/c_9d8917efa100_k.mdl'])
        report = {'bounds': W.bounds_check(set(ALL), BOX), 'stores': W.stores_check({'chim': {c: 1 for c in ALL}}, BOX),
                  'actors': a}
        self.assertEqual(len(W.check(report)), 1)


class CollisionOnly(unittest.TestCase):
    def test_flora_cards_are_drawn_elsewhere_and_anything_else_is_a_finding(self):
        self.assertEqual(W.model_stem('x/flora_ashtree_04@s2#2'), 'x/flora_ashtree_04')
        self.assertEqual(W.model_stem('f/flora_tree_01.nif#collision_only@s1'), 'f/flora_tree_01')
        census = {'models': [
            {'name': 'f/flora_tree_01.nif#collision_only@s1', 'store': 'open world', 'faces': 0, 'clipnodes': 9},
            {'name': 'x/flora_ashtree_04@s2#2', 'store': 'open world', 'faces': 0, 'clipnodes': 9},
            {'name': 'x/ex_rock_01@s1', 'store': 'open world', 'faces': 0, 'clipnodes': 9, 'file': 'frames/x'},
            {'name': 'x/ex_rock_02@s1', 'store': 'open world', 'faces': 12, 'clipnodes': 9},
            {'name': 'i/in_wall@s1', 'store': 'rooms', 'faces': 0, 'clipnodes': 9}]}
        cards = W.card_models({'placements': [{'kind': 'tree', 'model': 'x/flora_ashtree_04.nif'},
                                              {'kind': 'grass', 'model': 'x/ex_rock_01.nif'}]})
        c = W.collision_only_check(census, cards)
        self.assertEqual((c['models'], c['cards'], c['others']), (3, 2, [['x/ex_rock_01@s1', 'frames/x']]))

    def test_the_originals_own_walls_are_listed_as_theirs(self):
        text = 'AWWB1\nopening 0\nship 0\nbox 12345 0 0 0 1 0 0 0 1 0 0 0 1 1 1 1\n'
        self.assertEqual(W.barriers_list(text), [12345])

    def test_a_closed_frame_edge_is_a_finding_only_where_a_player_reaches_its_walls(self):
        # the v0.0.69-dev5 image: the Vivec city map closes its edge (walls at its bounds -6912..6912, -6400..7424),
        # but its town row hands off to the open world at its core + 32 (-6144..6144, -5632..6656): 736 units inside
        # the walls on every side (VIVEC-CITY-FRAME-EDGE-WALLS-69). A town without a handoff is a finding; Mournhold's
        # districts are listed apart (bounded by the city in the original).
        towns = W.town_rows((ROOT / 'engine/aga/src/aw_town_table.h').read_text(encoding='utf-8'))
        self.assertEqual(towns['vivec_city'], {'world_slot': -1, 'handoff': 1, 'origin': [8192.0, -23040.0, 0.0],
                                               'core': [-6144.0, -5632.0, 6144.0, 6656.0]})
        self.assertEqual((towns['seyda']['world_slot'], towns['balmora']['world_slot']), (0, 1))
        towns['walled'] = {'world_slot': -1, 'handoff': 0, 'origin': [0, 0, 0], 'core': [-100, -100, 100, 100]}
        closed = lambda m: [{'classname': 'worldspawn', '_chim_edge': 'closed', 'message': m}]
        maps = {'vivec_city-chim': closed('Vivec'), 'walled-chim': closed('Walled'), 'mh0006': closed('Mournhold'),
                'vf0001': [{'classname': 'worldspawn'}], 'broken': []}
        bounds = {'vivec_city-chim': ([-6912, -6400, -790], [6912, 7424, 2048]),
                  'walled-chim': ([-500, -500, 0], [500, 500, 100])}
        e = W.closed_edges(maps, towns, bounds)
        self.assertEqual(e, {'closed': [['walled-chim', 'Walled']], 'handed_off': [['vivec_city-chim', 'Vivec', 736.0]],
                             'mournhold': [['mh0006', 'Mournhold']]})
        report = {'bounds': W.bounds_check(set(ALL), BOX), 'stores': W.stores_check({'chim': {c: 1 for c in ALL}}, BOX),
                  'frame_edges': e}
        self.assertEqual(len(W.check(report)), 1)
        # a handoff line at or past the walls does not count: the walls are reached first
        self.assertIsNone(W.handoff_before_walls(towns['vivec_city'], ([-6100, -6400, 0], [6912, 7424, 0])))
        # the world model's bounds, as a .chim frame map keeps them (BSP29 lump 14, model 0)
        raw = bytearray(4 + 15 * 8 + 64)
        struct.pack_into('<i', raw, 0, 29)
        struct.pack_into('<ii', raw, 4 + 14 * 8, 4 + 15 * 8, 64)
        struct.pack_into('<6f', raw, 4 + 15 * 8, -6912, -6400, -790, 6912, 7424, 2048)
        self.assertEqual(W.map_bounds(bytes(raw)), ([-6912.0, -6400.0, -790.0], [6912.0, 7424.0, 2048.0]))


class Audit(unittest.TestCase):
    def test_the_report_of_a_run_with_only_its_directories(self):
        with tempfile.TemporaryDirectory() as t:
            id1 = Path(t) / 'image' / 'boot' / 'id1'
            (id1 / 'world').mkdir(parents=True)
            (id1 / 'world' / 'regions.awr').write_bytes(directory('AWR2', cell_rows('vf', ALL)))
            report = W.audit(t, BOX)
            self.assertEqual(report['bounds']['cells'], 25)
            self.assertEqual(report['stores']['gaps'], [list(c) for c in sorted(ALL)])   # no store: every cell
            self.assertNotIn('actors', report)
            out = Path(t) / 'report.json'
            out.write_text(json.dumps(report))
            self.assertEqual(W.main(['check', '--report', str(out)]), 1)


if __name__ == '__main__':
    unittest.main()
