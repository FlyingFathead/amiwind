# SPDX-License-Identifier: GPL-3.0-only
"""The seven expansion rooms the v0.0.66-dev2 room batches refused (tools/chim_room_batches.py, tools/lava.py):

- ROOM-EMPTY-CELL-66: a cell with no placement the room converter keeps (only an NPC, or no reference at all) is listed
  by name as empty in the game data and never refused; since v0.0.67 it is built as an empty room
  (ROOMS-SET-ASIDE-NOT-BUILT-67);
- LAVA-POOL-NOT-LAVA-NAMED-66: a molten pool whose layers are not named lava (Sotha Sil's hot oil) is a pool by its
  flowing layers (lava.room_pools_of), equal to pools_of for every lava-named pool, and its activator leaves the
  statics;
- ROOM-EFFECT-MODEL-NO-TRIANGLES-66: an effect model without drawn static triangles is left out of the room's statics,
  counted in its omitted list, instead of refusing the room; any other export error still refuses it."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

import chim_room_batches as B  # noqa: E402
import lava as L  # noqa: E402

SCROLL = {'u': [], 'v': [[0.0, 0.0], [48.0, 2.0]]}
NO_TRIANGLES = 'No supported visible static triangles'      # prepare_scenery.model_geometry's refusal


def stack(textures, scroll=(True, True, True)):
    """A 2 x 2 pool mesh of three layers at z -2, -1 and 0 (the lava pools' stack), one material per layer."""
    v, f = [], []
    for k, z in enumerate((-2.0, -1.0, 0.0)):
        base = len(v)
        v += [[-1, -1, z, 0, 0], [1, -1, z, 0, 0], [1, 1, z, 0, 0], [-1, 1, z, 0, 0]]
        f += [[base, base + 1, base + 2, k], [base, base + 2, base + 3, k]]
    materials = [{'texture_source': t, 'uv_scroll': SCROLL if s else None} for t, s in zip(textures, scroll)]
    return v, f, materials


OIL = ('Tx_hot_oil.dds', 'Tx_hot_oil.dds', 'Tx_oil_crust.dds')
LAVA = ('Tx_lava_molten.tga', 'Tx_lava_molten.tga', 'Tx_lava_crust.tga')
MOLTEN = {'act_hot_oil_512': {'script': 'SothaHotOil', 'dps': 20.0, 'sound': 'oil bubbly'},
          'in_lava_512': {'script': 'lava', 'dps': 20.0, 'sound': 'lava layer'}}


class Source:
    def read(self, model):
        return model.encode(), 'test'


def ref(number, ident, model, kind='ACTI', position=(0.0, 0.0, 0.0)):
    return {'number': number, 'id': ident, 'model': model, 'type': kind, 'position': list(position),
            'rotation_radians': [0.0, 0.0, 0.0], 'scale': 1.0}


class PoolShapes(unittest.TestCase):
    def setUp(self):
        meshes = {'meshes/i/act_hot_oil_512.nif': stack(OIL), 'meshes/i/in_lava_512.nif': stack(LAVA),
                  'meshes/i/still.nif': stack(('a.dds', 'b.dds', 'c.dds'), (False, False, False))}

        def geometry(raw, reader, repair_uv=False):
            v, f, m = meshes[raw.decode()]
            return (v, f), [dict(x) for x in m], None, None
        for target, value in (('prepare_scenery.model_geometry', geometry), ('prepare_scenery.nif_reader', object),
                              ('mwad.scene.unpack_geometry', lambda g: (g[0], g[1], None))):
            patcher = mock.patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_the_hot_oil_is_a_pool_by_its_flowing_layers(self):
        refs = [ref(1, 'act_hot_oil_512', 'i\\act_hot_oil_512.NIF', position=(100.0, 200.0, 50.0))]
        with self.assertRaises(ValueError):           # the strict rule refused both Sotha Sil oil rooms
            L.pools_of('data', refs, MOLTEN, Source())
        pools = L.room_pools_of('data', refs, MOLTEN, Source())
        self.assertEqual(len(pools), 1)
        pool = pools[0]
        self.assertEqual((pool['reference'], pool['dps'], pool['sound']), (1, 20.0, 'oil bubbly'))
        self.assertEqual(pool['layers'], list(OIL))            # bottom to top: the crust over the flowing oil
        self.assertEqual(pool['top'], 50.0)
        self.assertEqual(len(pool['hull']), 4)

    def test_a_lava_pool_is_what_pools_of_gives(self):
        refs = [ref(1, 'in_lava_512', 'i\\in_lava_512.nif'), ref(2, 'rock', 'x\\rock.nif', 'STAT'),
                ref(3, 'in_lava_512', 'i\\in_lava_512.nif', position=(512.0, 0.0, 8.0))]
        self.assertEqual(L.room_pools_of('data', refs, MOLTEN, Source()), L.pools_of('data', refs, MOLTEN, Source()))
        v, f, m = stack(LAVA)
        points, layers = L.pool_shape(v, f, m)
        self.assertEqual(len(points), len(L.pool_points(v, f, m)))
        self.assertEqual(layers, L.pool_layers(v, f, m))

    def test_a_pool_with_neither_lava_nor_flowing_layers_is_refused_named(self):
        molten = dict(MOLTEN, still={'script': 's', 'dps': 1.0, 'sound': ''})
        with self.assertRaisesRegex(ValueError, 'meshes/i/still.nif'):
            L.room_pools_of('data', [ref(1, 'still', 'i\\still.nif')], molten, Source())

    def test_no_molten_object_reads_no_mesh(self):
        self.assertEqual(L.room_pools_of('data', [ref(1, 'rock', 'x\\rock.nif', 'STAT')], MOLTEN), [])


class LiquidsLeaveTheStatics(unittest.TestCase):
    def test_a_pool_drawn_as_liquid_leaves_the_statics(self):
        refs = [ref(1, 'act_hot_oil_512', 'i\\act_hot_oil_512.NIF'), ref(2, 'wall', 'i\\wall.nif', 'STAT')]
        kept, omitted = B.leave_out_liquids(refs, [{'reference': 9, 'id': 'm', 'reason': 'editor marker'}],
                                            [{'reference': 1}])
        self.assertEqual([r['number'] for r in kept], [2])
        self.assertEqual(omitted[-1], {'reference': 1, 'id': 'act_hot_oil_512', 'reason': 'molten pool drawn as liquid'})

    def test_lava_pools_left_out_by_name_change_nothing(self):
        refs = [ref(2, 'wall', 'i\\wall.nif', 'STAT')]
        omitted = [{'reference': 1, 'id': 'in_lava_512', 'reason': 'liquid or effect activator'}]
        kept, again = B.leave_out_liquids(refs, omitted, [{'reference': 1}])
        self.assertIs(kept, refs)
        self.assertIs(again, omitted)


class EffectModels(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def errors(self, rows):
        (self.tmp / 'conversion-errors.json').write_text(json.dumps(rows), encoding='utf-8')

    def test_only_models_without_drawn_triangles(self):
        self.errors([{'source': 'meshes/amalexia_summon.nif', 'error': NO_TRIANGLES}])
        self.assertEqual(B.effect_models(self.tmp), {'meshes/amalexia_summon.nif'})

    def test_any_other_error_keeps_the_refusal(self):
        self.errors([{'source': 'meshes/a.nif', 'error': NO_TRIANGLES},
                     {'source': 'meshes/b.nif', 'error': 'Missing base BSA texture: textures/b.dds'}])
        self.assertEqual(B.effect_models(self.tmp), set())

    def test_no_error_list(self):
        self.assertEqual(B.effect_models(self.tmp), set())


class BuildShellEffects(unittest.TestCase):
    """build_shell with its collaborators stubbed: the scenery export refuses the room while an effect model is in it
    (as prepare_scenery.export_refs does: conversion-errors.json, then the incomplete assembly)."""

    def setUp(self):
        self.scene = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.scene, True)
        self.calls = []
        stubs = {'interior_lighting.cell_lighting': lambda cell: {'lights': []},
                 'prepare_area.interior_visual_profile': lambda model, area: None,
                 'interior_plants.room_wants_sprites': lambda entry: False,
                 'lava.lava_mode': lambda: 'quake', 'lava.room_pools_of': lambda data, refs, molten: [],
                 'lava.molten_objects_of': lambda path: {}, 'mwad.masters.master_path': lambda data: Path('master'),
                 'prepare_scenery.export_refs': self.export, 'chim_room_batches.shell_map': lambda *a: b'BSP'}
        for target, value in stubs.items():
            patcher = mock.patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def export(self, data, out, refs, groups, *args, **kwargs):
        self.calls.append([r['number'] for r in refs])
        out.mkdir(parents=True, exist_ok=False)
        bad = [r for r in refs if r['model'] in self.failing]
        if bad:
            rows = [{'source': 'meshes/' + r['model'].replace('\\', '/').lower(), 'error': self.failing[r['model']]}
                    for r in bad]
            (out / 'conversion-errors.json').write_text(json.dumps(rows), encoding='utf-8')
            raise ValueError('Converted assembly is incomplete: room; ' + str(rows))
        index = {'references': [dict(r, bounds=[[0, 0, 0], [256, 256, 256]]) for r in refs], 'errors': []}
        (out / 'scenery-index.json').write_text(json.dumps(index), encoding='utf-8')

    def task(self, refs):
        cell = {'name': 'Sotha Sil, Dome of Sotha Sil', 'refs': refs, 'entrances': [], 'water_height': None,
                'master_sha256': '0' * 64, 'flags': 1}
        return ('data', str(self.scene), {'map': 'room', 'cell': cell['name'], 'interior': True, 'area': 'balmora'},
                None, cell)

    def test_the_effect_model_is_left_out_and_counted(self):
        self.failing = {'Amalexia_summon.NIF': NO_TRIANGLES}
        refs = [ref(1, 'in_sotha_sil00', 'i\\in_sotha_sil00.NIF'),
                ref(2, 'Sotha Alma Appear Effect', 'Amalexia_summon.NIF'), ref(3, 'lab', 'i\\in_sotha_lab00.NIF', 'STAT')]
        with contextlib.redirect_stdout(io.StringIO()) as log:
            report, _ = B.build_shell(self.task(refs))
        self.assertEqual(self.calls, [[1, 2, 3], [1, 3]])
        self.assertEqual(report['placements'], 2)
        self.assertEqual(json.loads((self.scene / 'area-work/room/placements.json').read_text()), [1, 3])
        left = [o for o in report['omitted'] if o['reference'] == 2]
        self.assertEqual(len(left), 1)
        self.assertIn('effect model without drawn static triangles', left[0]['reason'])
        self.assertIn('1 effect placements without drawn static triangles left out', log.getvalue())

    def test_any_other_export_error_still_refuses_the_room(self):
        self.failing = {'Amalexia_summon.NIF': NO_TRIANGLES, 'i\\in_sotha_sil00.NIF': 'Malformed NIF'}
        refs = [ref(1, 'in_sotha_sil00', 'i\\in_sotha_sil00.NIF'),
                ref(2, 'Sotha Alma Appear Effect', 'Amalexia_summon.NIF')]
        with self.assertRaisesRegex(ValueError, 'Converted assembly is incomplete'):
            B.build_shell(self.task(refs))
        self.assertEqual(len(self.calls), 1)

    def test_a_door_without_triangles_still_refuses_the_room(self):
        self.failing = {'d\\door.nif': NO_TRIANGLES}
        refs = [ref(1, 'door', 'd\\door.nif', 'DOOR'), ref(2, 'lab', 'i\\in_sotha_lab00.NIF', 'STAT')]
        with self.assertRaises(ValueError):
            B.build_shell(self.task(refs))


class StoredRoomsKept(unittest.TestCase):
    def test_the_rooms_stored_before_the_fix_are_found(self):
        """The room code after the fix differs from 796d8043's only where that code refused the room: the 1,117 rooms
        the v0.0.66-dev2 run stored under the old reach digest are found under the new one (tools/unit_store.py)."""
        import unit_store
        self.assertEqual(unit_store.legacy_sources(
            'interior-room-chim', 'ba92267dd851229b02fac55fb0c394999fd48dc511f9920c463e07ba62750576'),
            ('b839f4c67012130a27a869342bfee3c5da56323876bbdd3d370618ca0341335e',))


class EmptyRooms(unittest.TestCase):
    def test_a_cell_without_scenery_is_listed_not_converted(self):
        cells = {'a': {'refs': [{'number': 1, 'id': 'a shady smuggler', 'type': 'NPC_', 'model': ''}],
                       'entrances': []},
                 'b': {'refs': [], 'entrances': []},
                 'c': {'refs': [ref(1, 'wall', 'i\\wall.nif', 'STAT')], 'entrances': [{'number': 5}]}}
        entries = [{'map': m, 'cell': name} for m, name in (('a', 'Mournhold, Royal Palace'), ('b', 'Sotha Sil,'),
                                                            ('c', 'A room'))]
        keep, empty = B.empty_rooms(entries, cells)
        self.assertEqual([e['map'] for e in keep], ['c'])
        self.assertEqual(sorted(empty), ['Mournhold, Royal Palace', 'Sotha Sil,'])
        self.assertIn('1 references: NPC_ a shady smuggler', empty['Mournhold, Royal Palace'])
        self.assertIn('(0 references)', empty['Sotha Sil,'])
        self.assertIn('0 doors lead in', empty['Sotha Sil,'])

    def test_an_empty_cell_is_built_as_an_empty_room(self):
        """ROOMS-SET-ASIDE-NOT-BUILT-67 (the maintainer's rule of 19 November 2026: if a place is in the original, it is in
        AmiWind): the four cells of the masters with no scenery ("Sotha Sil,", "Mournhold, Royal Palace" with its one
        NPC, the two Vor Lair cells) are built as empty rooms: a shell map with no scenery around their references,
        the start in its middle, no placements; the CHIM interiors stage makes an empty room record of each, and the
        image's room map of it carries no placement. Before, the room stage listed them as empty and built none."""
        import chim.interior as I
        from chim.frame_map import entities
        scene = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, scene, True)
        smuggler = {'number': 4219120, 'id': 'a shady smuggler', 'type': 'NPC_', 'model': '',
                    'position': [400.0, -800.0, 120.0]}
        cells = {'mournhold, royal palace': {'name': 'Mournhold, Royal Palace', 'refs': [smuggler], 'entrances': [],
                                             'flags': 1, 'master_sha256': 'a' * 64},
                 'sotha sil,': {'name': 'Sotha Sil,', 'refs': [], 'entrances': [], 'flags': 1, 'master_sha256': 'b' * 64}}
        for slug, cell in (('rmpalace', cells['mournhold, royal palace']), ('rsothasil', cells['sotha sil,'])):
            report, back = B.build_empty((None, scene, {'map': slug, 'cell': cell['name']}, None, cell))
            self.assertIs(back, cell)
            work = scene / 'area-work' / slug
            self.assertEqual((report['form'], report['placements']), ('empty room', 0))
            self.assertEqual(json.loads((work / 'placements.json').read_text()), [])
            (lo, hi) = report['bounds']
            # the box holds its references (quarter scale) and the start stands inside it
            for ref in cell['refs']:
                self.assertTrue(all(lo[i] < ref['position'][i] * 0.25 < hi[i] for i in range(3)))
            self.assertTrue(all(lo[i] < report['spawn'][i] < hi[i] for i in range(3)))
            world = entities((work / 'room.bsp').read_bytes())
            self.assertEqual(world[0].get('classname'), 'worldspawn')
            self.assertEqual(world[0].get(B.SHELL_KEY), '1')
            self.assertIn('info_player_start', [e.get('classname') for e in world])
            # the CHIM interiors stage: an empty room record, no models, no placements
            room = I.empty_room_input(work)
            self.assertEqual((room['room'], room['cell'], room['spec']['placements']), (slug, cell['name'], []))
            self.assertIsNone(I.unsupported(work))
            self.assertEqual(I.room_cost((str(work),)), 0)
            data, row = I.Store().add_room(room)
            self.assertEqual((row['placements'], row['models']), (0, 0))
        # every other room keeps room_input (a room with scenery has no empty form)
        self.assertIsNone(I.empty_room_input(scene / 'nowhere'))

    def test_what_points_to_the_empty_cells_matches_by_prefix(self):
        """What the masters point at these cells with (measured in all three masters, 19 November 2026): Tribunal's
        TribunalMain asks `GetPCCell "Sotha Sil," == 1`, and two Tribunal dialogue lines carry a Not Cell condition on
        "Mournhold, Royal Palace". Both match by prefix, as the original (OpenMW cellextensions.cpp OpGetPCCell and
        filter.cpp Function_NotCell, ciStartsWith): GetPCCell "Sotha Sil," is true in every "Sotha Sil, ..." room and in
        "Sotha Sil," itself, and the Not Cell lines are said nowhere in "Mournhold, Royal Palace..." (the engine's
        AW_GLUT_OP_CELL: starts_with). The GetPCCell row is made here from the names, so the engine compares numbers."""
        from types import SimpleNamespace
        from mwscript import codegen
        numbers = {'sotha sil,': 1217, 'sotha sil, outer flooded halls': 949, 'sotha sil, dome of sotha sil': 948,
                   'mournhold, royal palace': 1165, 'mournhold, royal palace throne room': 1166,
                   'mournhold, royal palace: jail': 1168, 'mournhold temple': 1170}
        data = SimpleNamespace(interior_numbers=numbers, exteriors={}, regions={}, default_cell_name='Wilderness')
        prog = SimpleNamespace(data=data, pccells=codegen.Table(), presented={})
        row = prog.pccells.rows[codegen.Program.pccell(prog, 'Sotha Sil,')]
        self.assertEqual((row['rooms'], row['outside'], row['wilderness']), ([948, 949, 1217], [], False))
        row = prog.pccells.rows[codegen.Program.pccell(prog, 'Mournhold, Royal Palace')]
        self.assertEqual(row['rooms'], [1165, 1166, 1168])
        # the dialogue's Not Cell condition (the reference the dialogue table is checked against): a prefix too
        import dialogue_pick_check as P
        st = {'cell': 'Mournhold, Royal Palace: Jail'}
        self.assertFalse(P._select('NotCell', 'mournhold, royal palace', 0, 0, {}, st, None))
        self.assertTrue(P._select('NotCell', 'mournhold, royal palace', 0, 0, {}, {'cell': 'Mournhold Temple'}, None))
        engine = (ROOT / 'engine/aga/src/aw_glut.c').read_text(encoding='utf-8', errors='replace')
        self.assertIn('case AW_GLUT_OP_CELL:', engine)
        self.assertIn('starts_with(cell,want)', engine)

    def test_the_counts_keep_empty_rooms_in_the_plan_and_out_of_the_classic_maps(self):
        import interior_counts as C
        run = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, run, True)
        (run / C.BATCH_RECORD).parent.mkdir(parents=True)
        (run / C.BATCH_RECORD).write_text(json.dumps({
            'selection': '1-50', 'rooms': [{'room': 'A'}], 'held': {}, 'refused': {},
            'empty': {'Sotha Sil,': 'empty in the game data'}}), encoding='utf-8')
        record = C.counts(run)
        self.assertEqual((record['plan']['rooms'], record['plan']['empty']), (2, 1))
        self.assertEqual(record['classic'], [])
        self.assertIn('1 empty in the game data', '\n'.join(C.summary_lines(record)))


if __name__ == '__main__':
    unittest.main()
