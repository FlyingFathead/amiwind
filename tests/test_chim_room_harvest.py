# SPDX-License-Identifier: GPL-3.0-only
"""CHIM-ROOM-HARVEST-DOUBLE-48: a harvestable plant in a CHIM room exists exactly once, as its harvest entity.

v0.0.48-dev2 try 9 stopped in the image: the CHIM rooms stage put the harvestable mushrooms of addamasartus into its
room record, the image's baked-mushroom removal (harvest_build.clear_baked) took them out of the room map, and the room
map install found 8 record placements missing from the map. In the batch (shell) rooms the mushrooms stayed placed
meshes with no harvest entity (not pickable). As the CHIM world outdoors (chim.build.harvest_numbers), a room now
leaves the harvest placements out of its record and the image places them from the room's catalogue."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
from chim import format as F  # noqa: E402
from chim import interior as I  # noqa: E402
from chim import placed as P  # noqa: E402
from chim.frame_map import add_clip_models, empty_world, entity_text  # noqa: E402
from test_room_late_passes import BOUNDS, REF, SHELL, SLAB, make_image  # noqa: E402

PLANT = 4000002                     # a harvestable mushroom of the fixture room


def placement(ref):
    return P.placement(0, ref, 0, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 0, 0, 0, ((-65, -65, -17), (65, 65, 1)), 1, False)


def room_bsp(tmp, refs, shell=False):
    """A room map whose func_walls are the slab model bound to each of REFS (a batch room's shell map: none)."""
    lumps = empty_world(*SHELL)
    world = {'classname': 'worldspawn', 'message': 'Fixture Room'}
    if shell:
        world[I.SHELL_KEY] = '1'
    rows = [world]
    if not shell:
        for ref in refs:
            lumps, numbers = add_clip_models(lumps, [SLAB])
            rows.append({'classname': 'func_wall', 'model': '*%d' % numbers[0], 'aw_ref': str(ref),
                         'origin': '0 0 0'})
    lumps[0] = entity_text(rows)
    path = Path(tmp) / ('shell.bsp' if shell else 'room.bsp')
    path.write_bytes(F.brush_image(lumps)[0])
    return path


def receipt(folder, rows):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'chim-rooms-receipt.json').write_text(json.dumps({'format': 'aw-chim-rooms-1', 'rooms': rows}))
    return folder


class RoomSelectionTests(unittest.TestCase):
    REFS = [{'number': REF}, {'number': PLANT}, {'number': 9}]

    def test_harvest_plants_are_left_out_of_the_record_and_still_bound_the_room(self):
        every, selected, left = I.room_selection('fixture', self.REFS, {REF, PLANT}, harvest={PLANT, 77})
        self.assertEqual([r['number'] for r in every], [REF, PLANT])
        self.assertEqual([r['number'] for r in selected], [REF])
        self.assertEqual(left, [PLANT])

    def test_without_a_harvest_source_every_kept_placement_is_placed(self):
        every, selected, left = I.room_selection('fixture', self.REFS, {REF, PLANT}, harvest=None)
        self.assertEqual([r['number'] for r in selected], [REF, PLANT])
        self.assertIsNone(left)

    def test_a_room_of_plants_only_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'nothing to place'):
            I.room_selection('fixture', self.REFS, {PLANT}, harvest={PLANT})

    def test_a_kept_placement_missing_from_the_export_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'not in its scenery export'):
            I.room_selection('fixture', self.REFS, {REF, 5}, harvest=set())


class RoomMapTests(unittest.TestCase):
    """The room map install (chim.interior.room_map) against the record, with the plant's baked entity removed."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_try9_a_record_holding_a_removed_plant_stops_the_install(self):
        bsp = room_bsp(self.tmp.name, [REF])         # clear_baked took PLANT out of the map
        record = I.room_record(BOUNDS, [0], [placement(REF), placement(PLANT)])
        with self.assertRaisesRegex(ValueError, r'1 record placements are not in the room map \(first: \[%d\]\)' % PLANT):
            I.room_map(bsp, 'fixture', record, BOUNDS)

    def test_a_record_leaving_the_plant_out_installs(self):
        bsp = room_bsp(self.tmp.name, [REF])
        _, report = I.room_map(bsp, 'fixture', I.room_record(BOUNDS, [0], [placement(REF)]), BOUNDS)
        self.assertEqual(report['placements_checked'], 1)

    def test_a_shell_room_installs_its_record_without_the_plant(self):
        bsp = room_bsp(self.tmp.name, [], shell=True)
        _, report = I.room_map(bsp, 'fixture', I.room_record(BOUNDS, [0], [placement(REF)]), BOUNDS)
        self.assertEqual(report['placements_checked'], 1)


class ShellRoomHullTests(unittest.TestCase):
    """CHIM-ROOM-SHELL-NO-HULL-48: a batch room's shell map has no aw_hull, and the dev2 try 10 actor ground check
    refused all 1,910 batch room residents ('Scene must declare the converted humanoid standing hull')."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_a_shell_rooms_map_declares_the_standing_hull(self):
        from chim.frame_map import entities
        from player_hull import PROFILE
        bsp = room_bsp(self.tmp.name, [], shell=True)
        self.assertNotIn('aw_hull', entities(Path(bsp).read_bytes())[0])
        data, _ = I.room_map(bsp, 'fixture', I.room_record(BOUNDS, [0], [placement(REF)]), BOUNDS)
        self.assertEqual(entities(data)[0].get('aw_hull'), PROFILE)


class HarvestRowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.id1 = make_image(self.tmp.name, 'chim')       # maps/fixture.chim, its record places REF
        self.refs = [{'number': PLANT, 'cell': 'Fixture Room'}, {'number': 7, 'cell': [0, 0]}]

    def stage(self, left, room='fixture'):
        row = {'room': room, 'placements': 1}
        if left is not None:
            row.update(harvest_left_out=left, harvest_origin=[0.0, 0.0, 0.0])
        return receipt(Path(self.tmp.name) / 'chim-interiors', [row])

    def test_a_room_that_left_its_plant_out_gets_a_harvest_row(self):
        from harvest_build import chim_room_rows, select
        rows = chim_room_rows(self.id1, self.refs, self.stage([PLANT]))
        self.assertEqual(rows, [dict(name='fixture', origin=[0.0, 0.0, 0.0], coverage=None, interior=True, chim=True,
                                     room=True, numbers=[PLANT])])
        self.assertEqual([r['number'] for r in select(rows[0], self.refs)], [PLANT])

    def test_a_plant_both_in_the_record_and_left_out_is_refused(self):
        from harvest_build import chim_room_rows
        with self.assertRaisesRegex(ValueError, 'both in the room record and left out'):
            chim_room_rows(self.id1, self.refs + [{'number': REF, 'cell': 'Fixture Room'}], self.stage([REF]))

    def test_a_plant_the_source_does_not_place_is_refused(self):
        from harvest_build import chim_room_rows
        with self.assertRaisesRegex(ValueError, 'does not place'):
            chim_room_rows(self.id1, self.refs, self.stage([123]))

    def test_rooms_without_plants_or_not_installed_have_no_row(self):
        from harvest_build import chim_room_rows
        self.assertEqual(chim_room_rows(self.id1, self.refs, self.stage([])), [])
        self.assertEqual(chim_room_rows(self.id1, self.refs, self.stage([PLANT], room='elsewhere')), [])
        self.assertEqual(chim_room_rows(self.id1, self.refs, None), [])

    def test_rooms_made_without_the_harvest_source_keep_their_plants(self):
        from harvest_build import chim_rooms_keeping_plants
        self.assertEqual(chim_rooms_keeping_plants(self.stage(None)), {'fixture'})
        self.assertEqual(chim_rooms_keeping_plants(self.stage([PLANT])), set())
        self.assertEqual(chim_rooms_keeping_plants(None), set())


class ClearBakedTests(unittest.TestCase):
    """clear_baked leaves the room map of a CHIM room whose record keeps its plant (the earlier stage form)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.id1 = make_image(self.tmp.name, 'bsp')        # maps/fixture.bsp binds REF on a func_wall
        self.refs = [{'number': REF, 'cell': 'Fixture Room', 'position': [0.0, 0.0, 0.0],
                      'bounds': [[-1, -1, -1], [1, 1, 1]]}]

    def run_clear(self, rows):
        import harvest_build as H
        stage = receipt(Path(self.tmp.name) / 'chim-interiors', rows)
        cleared = []
        with mock.patch.object(H, 'held_placements', return_value=(None, None, self.refs)), \
                mock.patch.object(H, '_clear', side_effect=lambda task: cleared.append(Path(task[0]).stem) or
                                  (Path(task[0]).stem, 1, dict(removed=[str(REF)]))):
            report = H.clear_baked('/h', self.id1, Path(self.tmp.name) / 'work', data_files='/d', jobs=1,
                                   chim_interiors=stage)
        return report, cleared

    def test_a_room_keeping_its_plants_is_not_cleared(self):
        report, cleared = self.run_clear([{'room': 'fixture'}])
        self.assertEqual((report['maps_checked'], cleared, report['interior_rows']), (0, [], []))

    def test_a_room_that_left_its_plants_out_is_cleared(self):
        report, cleared = self.run_clear([{'room': 'fixture', 'harvest_left_out': [REF]}])
        self.assertEqual((report['maps_checked'], cleared), (1, ['fixture']))
        self.assertEqual([r['name'] for r in report['interior_rows']], ['fixture'])


class NoHarvestImageTests(unittest.TestCase):
    def test_an_image_without_harvest_refuses_rooms_that_left_plants_out(self):
        from types import SimpleNamespace
        from harvest_build import image_step
        with tempfile.TemporaryDirectory() as tmp:
            stage = receipt(Path(tmp) / 'chim-interiors', [{'room': 'fixture', 'harvest_left_out': [PLANT]}])
            with self.assertRaisesRegex(ValueError, 'would be lost'):
                image_step(SimpleNamespace(harvest=None, chim_interiors=stage), Path(tmp), Path(tmp) / 'work')
            receipt(stage, [{'room': 'fixture'}])
            self.assertEqual(image_step(SimpleNamespace(harvest=None, chim_interiors=stage), Path(tmp),
                                        Path(tmp) / 'work'), {'status': 'not_requested'})


class PlanTests(unittest.TestCase):
    def test_the_rooms_stage_waits_for_the_harvest_step(self):
        from build_parallel import stage_dependencies
        steps = [(n, ['python3', n + '.py']) for n in ('harvest', 'chim-interiors')]
        self.assertEqual(stage_dependencies(steps, skipped=('census',))['chim-interiors'], ('harvest',))
        self.assertEqual(stage_dependencies(steps[1:])['chim-interiors'], ())


if __name__ == '__main__':
    unittest.main()
