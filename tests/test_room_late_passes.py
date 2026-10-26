# SPDX-License-Identifier: GPL-3.0-only
"""IMAGE-ROOM-MAPS-LATE-PASSES-48: the image checks after the CHIM rooms install see CHIM rooms.

In the Balmora A/B (22 October 2026) the CHIM rooms image (B) counted 47 converted cells against 52, 81 dressing pieces
in 18 maps against 99 in 19, and checked 0 actor placements against 93: the checks after the install selected maps as
x.bsp (or read only the room map's entities, while a CHIM room's placed meshes live in its room record). Each step
here is run on one room in both forms: today's room map (maps/fixture.bsp) and the CHIM room made from it
(maps/fixture.chim on a one-model interior store), and must give the same counts."""
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
from chim import format as F  # noqa: E402
from chim import interior as I  # noqa: E402
from chim import placed as P  # noqa: E402
from chim.frame_map import add_clip_models, empty_world, entity_text  # noqa: E402
from player_hull import PROFILE  # noqa: E402
from test_actor_ground import alias, actor  # noqa: E402

REF = 4000001                       # the floor slab, a placed mesh
SLAB = ((-64.0, -64.0, -16.0), (64.0, 64.0, 0.0))
BOUNDS = ((-64.0, -64.0, -16.0), (64.0, 64.0, 64.0))
SHELL = ([-128.0, -128.0, -64.0], [128.0, 128.0, 128.0])
SIZES = {'pointer': 4, 'short': 2, 'int': 4, 'hunk': 16, 'dvertex': 12, 'dedge': 4, 'dplane': 20, 'dnode': 24,
         'dclipnode': 8, 'clipnode': 8, 'dleaf': 28, 'texinfo': 40, 'dface': 20, 'dmodel': 64, 'mvertex': 12,
         'medge': 8, 'mplane': 20, 'mtexinfo': 52, 'msurface': 68, 'mnode': 40, 'mleaf': 48, 'texture': 100,
         'entity': 400, 'scenery': 120, 'model': 300}


def slab_image():
    """The store model: a solid slab, point hull and standing hull, as the placed models' writer makes it."""
    import numpy as np
    from chim.models import model_image_lumps
    lo, hi = SLAB
    corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])], float)
    return F.brush_image(model_image_lumps([], [(corners, None, [], 0.)], lo, hi, lambda m: 0)[0])[0]


def write_store(id1, image):
    from chim.world import DEFAULT_SETTINGS
    root = Path(id1) / I.STORE
    (root / 'rooms').mkdir(parents=True)
    blob = F.sector_file([(b'MODL', 0, image)], I.FORMAT_VERSION)
    (root / 'p00.ccs').write_bytes(blob)
    offset = F.read_sector(blob)[0]['offset']
    files = [{'kind': b'SECT', 'sector': 0, 'cell': (0, 0), 'bytes': len(blob), 'crc': F.crc32(blob), 'entries': 1,
              'path': 'p00.ccs'}]
    settings = dict(DEFAULT_SETTINGS, terrain_light=0, placements=0, models=1, textures=0, frames=0)
    (root / 'world.cwi').write_bytes(F.index_file(settings, files, [('slab', 0, offset, len(image), 0)], [],
                                                   I.FORMAT_VERSION))


def room_rows(actor_text, chim):
    world = {'classname': 'worldspawn', 'aw_hull': PROFILE, 'message': 'Fixture Room'}
    if chim:
        world.update({'_chim_world': I.STORE, '_chim_room': 'fixture'})
    rows = [world, {'classname': 'info_player_start', 'origin': '0 0 24', 'angle': '0'}]
    import re
    for body in re.findall(r'\{([^{}]*)\}', actor_text):
        rows.append(dict(re.findall(r'"([^"]*)"\s+"([^"]*)"', body)))
    return rows


def make_image(tmp, form, actor_text=None):
    """id1 of an image holding the fixture room in FORM 'bsp' (the slab a func_wall of the room map) or 'chim' (the
    slab a placement of the room record, on the store)."""
    actor_text = actor() if actor_text is None else actor_text
    id1 = Path(tmp) / form / 'id1'
    (id1 / 'maps').mkdir(parents=True)
    (id1 / 'progs').mkdir()
    (id1 / 'progs/test.mdl').write_bytes(alias())
    lumps = empty_world(*SHELL)
    rows = room_rows(actor_text, form == 'chim')
    if form == 'bsp':
        lumps, numbers = add_clip_models(lumps, [SLAB])
        rows.append({'classname': 'func_wall', 'model': '*%d' % numbers[0], 'aw_ref': str(REF), 'origin': '0 0 0'})
        lumps[0] = entity_text(rows)
        (id1 / 'maps/fixture.bsp').write_bytes(F.brush_image(lumps)[0])
    else:
        write_store(id1, slab_image())
        rec = P.placement(0, REF, 0, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 0, 0, 0, ((-65, -65, -17), (65, 65, 1)), 1,
                          False)
        (id1 / I.STORE / 'rooms/fixture.crm').write_bytes(I.room_record(BOUNDS, [0], [rec]))
        lumps[0] = entity_text(rows)
        from map_files import frame_map_path
        frame_map_path(id1, 'fixture', 'chim').write_bytes(F.brush_image(lumps)[0])
    return id1


class Forms(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def both(self, actor_text=None):
        return {form: make_image(self.tmp.name, form, actor_text) for form in ('bsp', 'chim')}


class MapSelectionTests(Forms):
    def test_scene_maps_hold_room_maps_and_chim_rooms_not_frame_maps(self):
        from map_files import room_record_path, scene_maps
        images = self.both()
        self.assertEqual([p.name for p in scene_maps(images['bsp'] / 'maps')], ['fixture.bsp'])
        chim = scene_maps(images['chim'] / 'maps')
        self.assertEqual([p.suffix for p in chim], ['.chim'])
        self.assertEqual(room_record_path(images['chim'], chim[0]), images['chim'] / I.STORE / 'rooms/fixture.crm')
        self.assertIsNone(room_record_path(images['bsp'], images['bsp'] / 'maps/fixture.bsp'))


class EntityTrackerTests(Forms):
    def test_the_room_record_placements_are_counted(self):
        """The tracker's and the dressing track's placements (refs_by_map): the same in both forms."""
        from entity_tracker import refs_by_map
        images = self.both()
        counts = {form: refs_by_map([id1 / 'maps']) for form, id1 in images.items()}
        self.assertEqual(counts['bsp'], {'fixture': {REF, 123}})
        self.assertEqual(counts['chim'], counts['bsp'])

    def test_dressing_track_sees_the_room_record(self):
        from entity_tracker import dressing_placements, refs_by_map

        def sub(tag, body):
            return tag + struct.pack('<I', len(body)) + body

        def record(tag, body, flags=0):
            return tag + struct.pack('<III', len(body), 0, flags) + body
        stat = record(b'STAT', sub(b'NAME', b'furn_slab\0') + sub(b'MODL', b'f\\furn_dressing_slab.nif\0'))
        ref = sub(b'FRMR', struct.pack('<I', REF)) + sub(b'NAME', b'furn_slab\0') + \
            sub(b'DATA', struct.pack('<6f', 0, 0, 0, 0, 0, 0))
        cell = record(b'CELL', sub(b'NAME', b'Fixture Room\0') + sub(b'DATA', struct.pack('<Iii', 1, 0, 0)) + ref)
        master = record(b'TES3', sub(b'HEDR', b'\0' * 300)) + stat + cell
        images = self.both()
        tracks = {form: dressing_placements(master, refs_by_map([id1 / 'maps']), ('furn_dressing',))
                  for form, id1 in images.items()}
        self.assertEqual(sum(len(v) for v in tracks['bsp'].values()), 1)
        self.assertEqual(tracks['chim'], tracks['bsp'])


class ActorContactTests(Forms):
    def test_room_actors_are_checked_on_the_store_collision(self):
        from check_actor_ground import audit
        images = self.both()
        reports = {form: audit(id1 / 'maps') for form, id1 in images.items()}
        for form, r in reports.items():
            self.assertEqual(r['status'], 'passed', (form, r['errors']))
            self.assertEqual(r['placement_copies'], 1, form)
            self.assertEqual(r['summary'], {'grounded': 1}, form)
        chim = reports['chim']
        self.assertEqual(chim['rows'][0]['collision'], chim['chim_rooms']['fixture']['collision'])
        self.assertEqual(chim['chim_rooms']['fixture']['summary'], {'grounded': 1})
        self.assertNotIn('chim_rooms', reports['bsp'])
        from chim.room_scene import RoomScene
        from check_actor_ground import ROOM_COLLISION
        self.assertEqual(ROOM_COLLISION, RoomScene.COLLISION)

    def test_a_shell_rooms_resident_is_deferred_before_the_image_and_refused_in_it(self):
        """CHIM-ROOM-SHELL-ACTORS-EARLY-48: the rc1 warm build's actor-contact stage refused 110 residents of rooms
        converted as shells (--room-form shell): no hull, no collision before the image makes them CHIM rooms."""
        from check_actor_ground import SHELL_DEFERRED, audit
        id1 = Path(self.tmp.name) / 'shell' / 'id1'
        (id1 / 'maps').mkdir(parents=True)
        (id1 / 'progs').mkdir()
        (id1 / 'progs/test.mdl').write_bytes(alias())
        rows = room_rows(actor(), False)
        rows[0] = {'classname': 'worldspawn', 'message': 'Fixture Room', I.SHELL_KEY: '1'}
        lumps = empty_world(*SHELL)
        lumps[0] = entity_text(rows)
        (id1 / 'maps/fixture.bsp').write_bytes(F.brush_image(lumps)[0])
        early = audit(id1 / 'maps', defer_shells=True)
        self.assertEqual((early['status'], early['summary']), ('passed', {SHELL_DEFERRED: 1}))
        late = audit(id1 / 'maps')
        self.assertEqual(late['status'], 'failed')
        self.assertEqual(late['summary'], {'invalid': 1})

    def test_a_floating_room_actor_fails_in_both_forms(self):
        from check_actor_ground import audit
        images = self.both(actor(z=20))
        for form, id1 in images.items():
            self.assertEqual(audit(id1 / 'maps')['summary'], {'failed-contact': 1}, form)

    def test_the_room_scene_has_the_store_floor(self):
        from chim.room_scene import RoomScene
        images = self.both()
        scene = RoomScene(images['chim'] / 'maps/fixture.chim', hull=0)
        hit = scene.floor((10.0, 10.0, 8.0), 32)
        self.assertEqual(hit['status'], 'supported')
        self.assertAlmostEqual(hit['height'], 0.0, places=3)
        self.assertEqual(scene.placements, 1)


class RoomActorBakeTests(Forms):
    """ROOM-ACTORS-FLOATING-48: the image step fits CHIM room residents on the room's store collision (dev2 try11:
    1,662 batch room residents kept their game-data height, 1 to 15 units above the store floor)."""

    def chim(self, actor_text):
        return make_image(self.tmp.name, 'chim', actor_text)

    def entity(self, id1):
        from check_actor_ground import entities
        return next(e for e in entities((id1 / 'maps/fixture.chim').read_bytes()) if e.get('classname') == 'aw_npc')

    def test_a_resident_above_the_store_floor_is_fitted_and_then_passes_the_check(self):
        from room_actor_bake import bake_room_ground
        from check_actor_ground import audit
        id1 = self.chim(actor(z=6))
        self.assertEqual(audit(id1 / 'maps')['summary'], {'failed-contact': 1})
        report = bake_room_ground(id1 / 'maps')
        self.assertEqual((report['mode'], report['rooms'], report['residents']), ('store', 1, 1))
        self.assertEqual((report['fitted'], report['unchanged'], report['refused']), (1, 0, 0))
        e = self.entity(id1)
        self.assertAlmostEqual(float(e['origin'].split()[2]), 0.25, places=4)
        self.assertEqual(e['aw_ground_valid'], '1')
        self.assertAlmostEqual(float(e['aw_authored_z']), 6.0, places=4)
        result = audit(id1 / 'maps')
        self.assertEqual(result['status'], 'passed', result['errors'])
        self.assertEqual(result['summary'], {'grounded': 1})

    def test_a_grounded_resident_is_unchanged_and_a_second_bake_keeps_the_authored_spot(self):
        from room_actor_bake import bake_room_ground
        id1 = self.chim(actor(z=.25))
        self.assertEqual(bake_room_ground(id1 / 'maps')['unchanged'], 1)
        again = bake_room_ground(id1 / 'maps')
        self.assertEqual((again['unchanged'], again['fitted']), (1, 0))
        self.assertAlmostEqual(float(self.entity(id1)['aw_authored_z']), 0.25, places=4)

    def test_an_upper_storey_resident_over_a_gap_is_never_dropped_to_the_floor_below(self):
        from room_actor_bake import ROOM_HEADROOM, bake_room_ground
        from check_actor_ground import audit
        import os
        from unittest import mock
        from room_actor_bake import ROOM_CELL_DROP_ENV
        # 60 units over the only floor (a storey up, nothing under its footprint in between): not moved, by either
        # probe; the footprint probe also reports the surface below
        id1 = self.chim(actor(z=60))
        report = bake_room_ground(id1 / 'maps')        # the default probe (near): refused, not moved
        self.assertEqual((report['fitted'], report['refused']), (0, 1))
        self.assertEqual(self.entity(id1)['origin'], '0 0 60')
        with mock.patch.dict(os.environ, {ROOM_CELL_DROP_ENV: 'footprint'}):
            report = bake_room_ground(id1 / 'maps')
        self.assertGreater(60, ROOM_HEADROOM)
        self.assertEqual((report['fitted'], report['unchanged'], report['refused'], report['storey_below']), (0, 0, 1, 1))
        row = report['rows'][0]
        self.assertAlmostEqual(row['storey_below'], 60.0, places=2)
        self.assertAlmostEqual(row['nearest_below'], 0.0, places=2)
        self.assertEqual(report['refused_by_status'], {'storey below': 1})
        self.assertEqual(self.entity(id1)['origin'], '0 0 60')
        self.assertEqual(audit(id1 / 'maps')['summary'], {'failed-contact': 1})

    def test_the_footprint_takes_the_first_surface_under_the_soles(self):
        from room_actor_bake import _RoomFitter, footprint_support
        id1 = self.chim(actor(z=20))
        fitter = _RoomFitter(id1 / 'maps')
        samples = [(1.0, 1.0, 0.0), (-1.0, 1.0, 0.1), (1.0, -1.0, 0.2)]
        near = fitter.neighbourhood('fixture', [0.0, 0.0, 20.0], samples)
        hit = footprint_support(near, [0.0, 0.0, 20.0], samples)
        # the first sole to touch the slab top (0) is the lowest one (local z 0): it rests on the surface
        self.assertEqual(hit['status'], 'supported')
        self.assertAlmostEqual(hit['height'], 0.0, places=3)
        self.assertAlmostEqual(hit['footprint_drop'], 20.0, places=3)
        self.assertAlmostEqual(hit['spread'], 0.2, places=3)
        # inside the slab (top 0, bottom -16): the first surface is the slab itself, blocked, never the floor below
        self.assertEqual(footprint_support(near, [0.0, 0.0, -8.0], samples)['status'], 'blocked')

    def master(self, tag, flags=0):
        def sub(t, body):
            return t + struct.pack('<I', len(body)) + body

        def record(t, body):
            return t + struct.pack('<III', len(body), 0, 0) + body
        body = sub(b'NAME', b'heddvild\0') + sub(b'MODL', b'r\\test.nif\0')
        if tag == b'CREA':
            body += sub(b'FLAG', struct.pack('<I', flags))
        path = Path(self.tmp.name) / ('master-%s-%d.esm' % (tag.decode(), flags))
        path.write_bytes(record(b'TES3', sub(b'HEDR', b'\0' * 300)) + record(tag, body))
        return path

    def test_only_actors_whose_record_needs_the_ground_are_fitted(self):
        from room_actor_bake import bake_room_ground
        id1 = self.chim(actor(z=6))
        report = bake_room_ground(id1 / 'maps', master=self.master(b'NPC_'))
        self.assertEqual((report['record_classes'], report['fitted']), ({'npc': 1}, 1))
        self.assertEqual(bake_room_ground(id1 / 'maps', master=self.master(b'CREA', 0x40))['record_classes'],
                         {'creature: walks': 1})
        before = (id1 / 'maps/fixture.chim').read_bytes()
        for flags, kind in ((0x20, 'flies'), (0x10, 'swims')):   # a creature that flies or swims and does not walk
            with self.assertRaisesRegex(ValueError, 'flies or swims and does not walk'):
                bake_room_ground(id1 / 'maps', master=self.master(b'CREA', flags))
        self.assertEqual((id1 / 'maps/fixture.chim').read_bytes(), before)

    def test_the_game_keeps_what_the_build_placed(self):
        """Build and runtime agree: the engine's spawn grounding (engine/aga/src/aw_scene.c AW_NPCFloor) keeps a baked
        resident exactly (aw_ground_valid 1, origin == aw_ground_baked), and its bounded fallback (a point trace from
        8 over the origin, 40 down, origin = hit + 0.25) lands where the bake put it: G(G(p)) == G(p)."""
        from room_actor_bake import bake_room_ground
        from chim.room_scene import RoomScene
        id1 = self.chim(actor(z=6))
        bake_room_ground(id1 / 'maps')
        e = self.entity(id1)
        origin = [float(v) for v in e['origin'].split()]
        self.assertEqual(e['aw_ground_valid'], '1')
        self.assertEqual([float(v) for v in e['aw_ground_baked'].split()], origin)
        hit = RoomScene(id1 / 'maps/fixture.chim', hull=0).floor([origin[0], origin[1], origin[2]+8], 40)
        self.assertEqual(hit['status'], 'supported')
        self.assertAlmostEqual(hit['height']+.25, origin[2], places=3)
        again = bake_room_ground(id1 / 'maps')
        self.assertEqual((again['unchanged'], again['fitted']), (1, 0))

    def test_a_resident_decided_case_by_case_stays_and_is_an_explicit_exception(self):
        from unittest import mock
        import room_actor_bake as actor_grounding
        from room_actor_bake import ROOM_PLACEMENTS_FORMAT, bake_room_ground
        from check_actor_ground import audit
        id1 = self.chim(actor(z=60))
        table = Path(self.tmp.name) / 'kept.json'
        table.write_text(json.dumps({'format': ROOM_PLACEMENTS_FORMAT, 'placements': {}, 'authored': {
            'fixture 123': {'id': 'Heddvild', 'reason': 'test: stands on a gallery no floor piece holds'}}}))
        with mock.patch.object(actor_grounding, 'ROOM_PLACEMENTS', table):
            report = bake_room_ground(id1 / 'maps')
            result = audit(id1 / 'maps')
        self.assertEqual((report['room_exceptions'], report['residents']), (1, 0))
        self.assertEqual(self.entity(id1)['origin'], '0 0 60')
        self.assertEqual(self.entity(id1)['aw_ground_mode'], '1')
        self.assertEqual(result['summary'], {'explicit-exception': 1})
        self.assertEqual(result['rows'][0]['exception_reason'], 'test: stands on a gallery no floor piece holds')
        # without the file's entry the same map is refused by the check (the entry is the decision, never a default)
        self.assertEqual(audit(id1 / 'maps')['summary'], {'invalid': 1})
        table.write_text(json.dumps({'format': ROOM_PLACEMENTS_FORMAT, 'authored': {
            'fixture 123': {'id': 'someone else', 'reason': 'test'}}}))
        other = make_image(Path(self.tmp.name) / 'other', 'chim', actor(z=60))
        with mock.patch.object(actor_grounding, 'ROOM_PLACEMENTS', table):
            with self.assertRaisesRegex(ValueError, 'the room exception names someone else'):
                bake_room_ground(other / 'maps')

    def test_the_collision_box_must_be_free(self):
        from room_actor_bake import _RoomFitter
        id1 = self.chim(actor(z=6))
        fitter = _RoomFitter(id1 / 'maps')
        self.assertTrue(fitter.fits('fixture', [0.0, 0.0, 0.25]))
        self.assertFalse(fitter.fits('fixture', [0.0, 0.0, -8.0]))     # in the slab

    def test_an_explicit_placement_is_written_as_given(self):
        from unittest import mock
        import room_actor_bake as actor_grounding
        from room_actor_bake import ROOM_PLACEMENTS_FORMAT, bake_room_ground
        id1 = self.chim(actor(z=60))
        table = Path(self.tmp.name) / 'placements.json'
        table.write_text(json.dumps({'format': ROOM_PLACEMENTS_FORMAT, 'placements': {
            'fixture 123': {'origin': [0, 0, 0.25], 'reason': 'test: decided case by case'}}}))
        with mock.patch.object(actor_grounding, 'ROOM_PLACEMENTS', table):
            report = bake_room_ground(id1 / 'maps')
        self.assertEqual((report['overrides'], report['fitted']), (1, 1))
        self.assertEqual(self.entity(id1)['origin'].split()[2], '0.25000')

    def test_near_is_the_map_bakes_probe(self):
        import os
        from unittest import mock
        from room_actor_bake import ROOM_CELL_DROP_ENV, bake_room_ground
        from check_actor_ground import audit
        id1 = self.chim(actor(z=60))
        with mock.patch.dict(os.environ, {ROOM_CELL_DROP_ENV: 'near'}):
            report = bake_room_ground(id1 / 'maps')
        self.assertEqual((report['fitted'], report['refused'], report['storey_below']), (0, 1, 0))
        self.assertEqual(self.entity(id1)['origin'], '0 0 60')
        self.assertEqual(audit(id1 / 'maps')['summary'], {'failed-contact': 1})

    def test_a_resident_over_no_placed_floor_is_refused_and_the_check_still_fails(self):
        from room_actor_bake import bake_room_ground
        from check_actor_ground import audit
        # over the room's closing clip floor only (outside the slab): no floor of the room, never dropped onto the clip
        id1 = self.chim(actor(z=6).replace('"origin" "0 0 6"', '"origin" "100 0 6"'))
        report = bake_room_ground(id1 / 'maps')
        self.assertEqual((report['fitted'], report['unchanged'], report['refused'], report['storey_below']), (0, 0, 1, 0))
        self.assertEqual(self.entity(id1)['origin'], '100 0 6')
        self.assertEqual(audit(id1 / 'maps')['summary'], {'failed-contact': 1})

    def test_off_is_the_method_before(self):
        import os
        from unittest import mock
        from room_actor_bake import ROOM_BAKE_ENV, bake_room_ground
        id1 = self.chim(actor(z=6))
        before = (id1 / 'maps/fixture.chim').read_bytes()
        with mock.patch.dict(os.environ, {ROOM_BAKE_ENV: 'off'}):
            self.assertEqual(bake_room_ground(id1 / 'maps')['residents'], 0)
        self.assertEqual((id1 / 'maps/fixture.chim').read_bytes(), before)
        with mock.patch.dict(os.environ, {ROOM_BAKE_ENV: 'maybe'}):
            with self.assertRaises(ValueError):
                bake_room_ground(id1 / 'maps')

    def test_the_map_bake_still_leaves_chim_rooms_to_the_room_bake(self):
        from actor_grounding import bake_ground
        id1 = self.chim(actor(z=6))
        before = (id1 / 'maps/fixture.chim').read_bytes()
        self.assertEqual(bake_ground(id1 / 'maps'), [])
        self.assertEqual((id1 / 'maps/fixture.chim').read_bytes(), before)

    def test_a_probe_that_raises_the_visit_guard_is_made_again_in_segments(self):
        from unittest import mock
        import audit_walkability
        from room_actor_bake import VISIT_GUARD, _RoomFitter
        id1 = self.chim(actor(z=6))
        near = _RoomFitter(id1 / 'maps').neighbourhood('fixture', [0.0, 0.0, 6.0], [(1.0, 1.0, 0.0)])
        real = audit_walkability.Scene.floor

        def guarded(scene, point, drop):
            if drop > 8:
                raise ValueError(VISIT_GUARD)
            return real(scene, point, drop)
        with mock.patch.object(audit_walkability.Scene, 'floor', guarded):
            hit = near.floor((10.0, 10.0, 14.0), 40)
            self.assertEqual((hit['status'], hit['segmented']), ('supported', 8.0))
            self.assertAlmostEqual(hit['height'], 0.0, places=3)
            self.assertEqual(hit['point'], [10.0, 10.0, 14.0])

    def test_the_fit_collision_is_the_check_collision(self):
        from room_actor_bake import _RoomFitter
        from chim.room_scene import RoomScene
        id1 = self.chim(actor(z=6))
        fitter = _RoomFitter(id1 / 'maps')
        scene = fitter.scene('fixture')
        self.assertIsInstance(scene, RoomScene)
        self.assertEqual(len(fitter.boxes('fixture')), len(scene.brushes))
        near = fitter.neighbourhood('fixture', [0.0, 0.0, 6.0], [(1.0, 1.0, 0.0)])
        self.assertEqual(near.floor((10.0, 10.0, 8.0), 32)['height'], scene.floor((10.0, 10.0, 8.0), 32)['height'])


class GroundFitCoverageTests(Forms):
    """ROOM-ACTORS-FLOATING-48 (a regression of ACTOR-GROUND-BAKE-CHIM-ROOMS-48): every ground resident of every scene
    kind the actor check reads as a map goes through a ground bake before the check, so a bake that skips a scene kind
    fails here and in the image step (require_fitted), not after an hour of build."""

    def image(self):
        """One id1 with a classic room map (classic.bsp) and a CHIM room (fixture.chim), both residents floating."""
        import shutil
        classic = make_image(self.tmp.name, 'bsp', actor(z=6))
        id1 = make_image(self.tmp.name, 'chim', actor(z=6))
        shutil.copyfile(classic / 'maps/fixture.bsp', id1 / 'maps/classic.bsp')
        return id1

    def test_the_image_order_of_bakes_fits_every_scene_kind(self):
        from actor_grounding import bake_ground
        from room_actor_bake import bake_room_ground, require_fitted, unfitted_ground_residents
        from check_actor_ground import audit
        id1 = self.image()
        maps = id1 / 'maps'
        self.assertEqual(sorted(unfitted_ground_residents(maps)), [('classic', '123'), ('fixture', '123')])
        bake_ground(maps)                      # the map bake: classic maps (CHIM rooms are not installed yet in a build)
        self.assertEqual(unfitted_ground_residents(maps), [('fixture', '123')])
        with self.assertRaisesRegex(ValueError, '1 ground residents in 1 maps were never fitted'):
            require_fitted(maps)
        self.assertEqual(require_fitted(maps, exclude=('fixture.chim',)), 0)
        bake_room_ground(maps)                 # after the CHIM rooms install
        self.assertEqual(unfitted_ground_residents(maps), [])
        self.assertEqual(require_fitted(maps), 0)
        report = audit(maps)
        self.assertEqual(report['status'], 'passed', report['errors'])
        self.assertEqual(report['summary'], {'grounded': 2})

    def test_the_image_step_runs_the_room_bake_and_the_guard_between_the_install_and_the_check(self):
        text = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        install = text.index('install_chim_interiors(args.chim_interiors')
        bake = text.index('bake_room_ground(boot/')
        guard = text.index('require_fitted(boot/')
        check = text.index('require_actor_ground(boot/')
        self.assertLess(install, bake)
        self.assertLess(bake, guard)
        self.assertLess(guard, check)
        self.assertLess(text.index('bake_ground(boot/'), install)


class HarvestTests(Forms):
    def test_a_harvestable_plant_in_a_chim_room_is_listed_not_skipped(self):
        from harvest_build import chim_room_plants
        images = self.both()
        refs = [{'number': REF, 'cell': 'Fixture Room'}, {'number': 7, 'cell': [0, 0]}]
        self.assertEqual(chim_room_plants(images['chim'], refs), {'fixture': [REF]})
        self.assertEqual(chim_room_plants(images['bsp'], refs), {})


class DirectStartTests(Forms):
    def test_a_start_in_a_chim_room_stands_on_its_store_floor(self):
        from direct_start import image_start_check
        images = self.both()
        records = {form: image_start_check(id1, {'map': 'fixture', 'arrival': [0.0, 0.0, 24.25], 'source': 'test'})
                   for form, id1 in images.items()}
        for form, r in records.items():
            self.assertTrue(r['ok'], form)
        self.assertEqual(records['chim']['standing_spot'], records['bsp']['standing_spot'])


class RoomHeapTests(Forms):
    def test_each_room_is_checked_against_its_zone(self):
        from chim.heap import require_room_map_heap, room_map_heap
        images = self.both()
        rooms = room_map_heap(images['chim'], SIZES, heap_mb=96)
        self.assertEqual(list(rooms), ['fixture'])
        row = rooms['fixture']
        self.assertEqual((row['models'], row['placements']), (1, 1))
        self.assertGreater(row['model_bytes'], 0)
        self.assertTrue(row['ok'])
        self.assertEqual(room_map_heap(images['bsp'], SIZES, heap_mb=96), {})
        report_path = Path(self.tmp.name) / 'room-heap.json'
        report = require_room_map_heap(images['chim'], sizes=SIZES, heap_mb=96, report_path=report_path)
        self.assertEqual(report['status'], 'passed')
        self.assertEqual(json.loads(report_path.read_text())['rooms']['fixture']['need_bytes'], row['need_bytes'])
        with self.assertRaisesRegex(ValueError, 'CHIM room heap gate failed: fixture'):
            require_room_map_heap(images['chim'], sizes=dict(SIZES, model=1 << 30), heap_mb=96)

    def test_the_early_check_reads_the_store_alone_and_agrees(self):
        """ROOM-AKULAKHAN-HEAP-52: the chim-interiors stage's check (room_store_heap) on the interior store alone, the
        room map at its smallest: what fails there fails in the image's gate."""
        from chim.heap import require_room_map_heap, require_room_store_heap, room_map_heap, room_store_heap
        images = self.both()
        early = room_store_heap(images['chim'], SIZES)
        late = room_map_heap(images['chim'], SIZES)
        self.assertEqual(list(early), ['fixture'])
        self.assertTrue(early['fixture']['ok'])
        self.assertEqual(early['fixture']['need_bytes'], late['fixture']['need_bytes'])
        self.assertGreaterEqual(early['fixture']['min_fast_room_bytes'], late['fixture']['min_fast_room_bytes'])
        report_path = Path(self.tmp.name) / 'early.json'
        big = dict(SIZES, model=1 << 30)
        with self.assertRaisesRegex(ValueError, r'CHIM room heap check \(early, before the image\) failed: fixture'):
            require_room_store_heap(images['chim'], sizes=big, report_path=report_path)
        self.assertEqual(json.loads(report_path.read_text())['failed'], ['fixture'])
        with self.assertRaises(ValueError):
            require_room_map_heap(images['chim'], sizes=big)


if __name__ == '__main__':
    unittest.main()
