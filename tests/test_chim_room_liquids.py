# SPDX-License-Identifier: GPL-3.0-only
"""CHIM rooms with water and lava (tools/chim/interior.py room_liquids, liquid_world, room_map;
docs/chim/INTERIOR_STORE.md): the room map's world carries the room's liquids as the exterior chunks carry theirs, and
a room without liquids keeps the bytes it had before."""
import hashlib
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / 'tools', ROOT / 'src'):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
from chim import format as F  # noqa: E402
from chim import interior as I  # noqa: E402
from chim import placed as P  # noqa: E402
from chim.frame_map import add_clip_models, empty_world, entities, entity_text, model_bounds  # noqa: E402

REF = 4000001
BOUNDS = ((-200.0, -200.0, -50.0), (200.0, 200.0, 150.0))
POOL = [[-50.0, -50.0], [50.0, -50.0], [50.0, 50.0], [-50.0, 50.0]]
# room_map of the fixture room without liquids, made by the code before liquids came over (0cbd59d8)
NO_LIQUIDS_SHA256 = 'cc17fe17eb6d6b86e57736b2c56fedf92dd2e0c95f908e22d89ce15285c22449'


def miptex(name, size=16, colour=7):
    pixels = bytes([colour]) * (size * size + (size // 2) ** 2 + (size // 4) ** 2 + (size // 8) ** 2)
    o = 40
    offsets = (o, o + size * size, o + size * size + (size // 2) ** 2,
               o + size * size + (size // 2) ** 2 + (size // 4) ** 2)
    return name.encode('ascii').ljust(16, b'\0') + struct.pack('<II4I', size, size, *offsets) + pixels


def texture_lump(names):
    data, offsets = b'', []
    for n in names:
        offsets.append(4 + 4 * len(names) + len(data))
        data += miptex(n)
    return struct.pack('<i%di' % len(names), len(names), *offsets) + data


def fixture_room(textures=('voidwall', '*water', '*lava')):
    """A compiled room map as the image holds it: worldspawn, the player start, one placed mesh (*1, a box) at the
    origin the room record gives it, an aw_lava point entity; its texture lump holds the room's own textures."""
    lumps = empty_world([-300.0, -300.0, -100.0], [300.0, 300.0, 200.0])
    lumps, numbers = add_clip_models(lumps, [((-16.0, -16.0, 0.0), (16.0, 16.0, 32.0))])
    lumps[2] = texture_lump(textures)
    rows = [{'classname': 'worldspawn', 'wad': 'room.wad', 'message': 'Fixture'},
            {'classname': 'info_player_start', 'origin': '0 0 40', 'angle': '90'},
            {'classname': 'func_wall', 'model': '*%d' % numbers[0], 'aw_ref': str(REF), 'origin': '0 0 0'},
            {'classname': 'aw_lava', 'origin': '0.00 0.00 10.00', '_aw_lava_radius': '70.71'}]
    lumps[0] = entity_text(rows)
    bsp = F.brush_image(lumps)[0]
    rec = I.with_light(P.placement(0, REF, 3, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 0, 0, 0,
                                   ((-17, -17, -1), (17, 17, 33)), 1, False), 100)
    record = I.room_record(BOUNDS, [3], [rec])
    return bsp, record


def make_map(tmp, liquids):
    bsp, record = fixture_room()
    path = Path(tmp) / 'fixture.bsp'
    path.write_bytes(bsp)
    return I.room_map(path, 'fixture', record, BOUNDS, liquids)


def contents(lumps, p, head=None):
    """Point contents of hull 0 (Quake SV_PointContents: the world's node tree)."""
    node = struct.unpack_from('<9f7i', lumps[14], 0)[9] if head is None else head
    while node >= 0:
        pn, front, back = struct.unpack_from('<ihh', lumps[5], 24 * node)
        nx, ny, nz, d = struct.unpack_from('<4f', lumps[1], 20 * pn)
        node = front if nx * p[0] + ny * p[1] + nz * p[2] - d >= 0 else back
    return struct.unpack_from('<i', lumps[10], 28 * (-1 - node))[0]


def world_faces(lumps):
    """[(texture name, texinfo flags, z of every vertex)] of the world model's faces."""
    tex = lumps[2]
    n = struct.unpack_from('<i', tex)[0]
    names = [tex[o:o + 16].split(b'\0')[0].decode() for o in struct.unpack_from('<%di' % n, tex, 4)]
    m = struct.unpack_from('<9f7i', lumps[14], 0)
    edges = list(struct.iter_unpack('<HH', lumps[12]))
    surfedges = [v[0] for v in struct.iter_unpack('<i', lumps[13])]
    out = []
    for f in range(m[14], m[14] + m[15]):
        _, side, first, count, ti = struct.unpack_from('<HhihH', lumps[7], 20 * f)
        miptex_index, flags = struct.unpack_from('<ii', lumps[6], 40 * ti + 32)
        verts = [edges[e][0] if e >= 0 else edges[-e][1] for e in surfedges[first:first + count]]
        zs = [struct.unpack_from('<3f', lumps[3], 12 * v)[2] for v in verts]
        out.append((names[miptex_index], flags, side, zs))
    return out


class RoomLiquidWorldTests(unittest.TestCase):
    def test_a_room_without_liquids_is_byte_identical_to_before(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, report = make_map(tmp, None)
        self.assertEqual(hashlib.sha256(data).hexdigest(), NO_LIQUIDS_SHA256)
        self.assertNotIn('liquids', report)

    def test_water_contents_below_the_level_and_a_water_surface_at_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, report = make_map(tmp, {'water': 20.0, 'lava': []})
        lumps = F.read_brush_image(data)
        for x, y in ((0.0, 0.0), (-230.0, 190.0), (240.0, -240.0)):
            self.assertEqual(contents(lumps, (x, y, 19.0)), -3)      # CONTENTS_WATER: swimming
            self.assertEqual(contents(lumps, (x, y, -60.0)), -3)
            self.assertEqual(contents(lumps, (x, y, 21.0)), -1)      # open air above
        faces = world_faces(lumps)
        self.assertEqual(sorted(f[2] for f in faces), [0, 1])       # seen from above and from below
        for name, flags, _, zs in faces:
            self.assertEqual(name, '*water')
            self.assertEqual(flags & 1, 1)                           # TEX_SPECIAL: no lightmap
            self.assertTrue(all(abs(z - 20.0) < 1e-4 for z in zs))
        self.assertEqual(report['liquids']['water_faces'], 2)
        self.assertEqual(report['liquids']['water'], 20.0)
        # the room edge and the placed mesh are kept; the aw_lava point entity is carried
        rows = entities(data)
        self.assertEqual(sum(1 for r in rows if r.get('aw_clip') == 'fixture room edge'), 6)
        self.assertTrue(any(r.get('classname') == 'aw_lava' for r in rows))
        self.assertEqual(rows[0].get('_chim_room'), 'fixture')

    def test_a_lava_pool_keeps_its_brushes_and_lava_contents(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, report = make_map(tmp, {'water': None, 'lava': [{'hull': POOL, 'top': 10.0}]})
        lumps = F.read_brush_image(data)
        self.assertEqual(contents(lumps, (0.0, 0.0, 6.0)), -5)      # CONTENTS_LAVA: the liquid prism, 8 deep
        self.assertEqual(contents(lumps, (45.0, -45.0, 3.0)), -5)
        self.assertEqual(contents(lumps, (0.0, 0.0, 11.0)), -1)
        self.assertEqual(contents(lumps, (0.0, 0.0, 1.0)), -1)      # under the liquid: the bed (a clip model)
        self.assertEqual(contents(lumps, (60.0, 0.0, 6.0)), -1)     # beside the pool
        faces = world_faces(lumps)
        self.assertEqual(len(faces), 2)
        for name, flags, _, zs in faces:
            self.assertEqual(name, '*lava')
            self.assertEqual(flags & 1, 1)
            self.assertTrue(all(abs(z - 10.0) < 1e-4 for z in zs))
        rows = entities(data)
        beds = [r for r in rows if r.get('aw_clip') == 'fixture lava bed']
        self.assertEqual(len(beds), 1)
        lo, hi = model_bounds(data, int(beds[0]['model'][1:]))
        # tools/lava.pool_brushes: the bed BED_THICKNESS (16) under the liquid (LIQUID_DEPTH 8 under the top)
        self.assertEqual([round(v, 3) for v in lo], [-50.0, -50.0, -14.0])
        self.assertEqual([round(v, 3) for v in hi], [50.0, 50.0, 2.0])
        self.assertEqual(report['liquids']['lava_leaves'], 1)
        self.assertEqual(report['liquids']['beds'], 1)

    def test_water_and_lava_over_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, _ = make_map(tmp, {'water': -40.0, 'lava': [{'hull': POOL, 'top': 10.0}]})
        lumps = F.read_brush_image(data)
        self.assertEqual(contents(lumps, (0.0, 0.0, -45.0)), -3)
        self.assertEqual(contents(lumps, (0.0, 0.0, 6.0)), -5)
        self.assertEqual(contents(lumps, (100.0, 0.0, 6.0)), -1)
        self.assertEqual(sorted(f[0] for f in world_faces(lumps)), ['*lava', '*lava', '*water', '*water'])

    def test_lava_whose_bed_reaches_under_the_water(self):
        """CHIM-ROOM-LAVA-UNDER-WATER-48 (Indoranyon, Subdun, the Forge of Hilbongard): the water plane at 7 cuts the
        pool's prism (top 10, 8 deep): lava above and under the plane inside the prism, water under the plane beside
        it, air above; the lava surface drawn once, the water surface once."""
        with tempfile.TemporaryDirectory() as tmp:
            data, report = make_map(tmp, {'water': 7.0, 'lava': [{'hull': POOL, 'top': 10.0}]})
        lumps = F.read_brush_image(data)
        self.assertEqual(contents(lumps, (0.0, 0.0, 9.0)), -5)      # lava above the water plane
        self.assertEqual(contents(lumps, (0.0, 0.0, 4.0)), -5)      # lava under it: the lava wins in its prism
        self.assertEqual(contents(lumps, (0.0, 0.0, 1.0)), -3)      # under the prism (the bed is a clip model): water
        self.assertEqual(contents(lumps, (100.0, 0.0, 4.0)), -3)    # beside the pool under the plane: water
        self.assertEqual(contents(lumps, (100.0, 0.0, 9.0)), -1)    # beside it above the plane: air
        self.assertEqual(contents(lumps, (0.0, 0.0, 11.0)), -1)
        self.assertEqual(sorted(f[0] for f in world_faces(lumps)), ['*lava', '*lava', '*water', '*water'])
        self.assertEqual(report['liquids']['lava_leaves'], 2)       # the prism's part on each side of the plane

    def test_lava_wholly_under_the_water(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, _ = make_map(tmp, {'water': 60.0, 'lava': [{'hull': POOL, 'top': 10.0}]})
        lumps = F.read_brush_image(data)
        self.assertEqual(contents(lumps, (0.0, 0.0, 6.0)), -5)
        self.assertEqual(contents(lumps, (0.0, 0.0, 30.0)), -3)
        self.assertEqual(contents(lumps, (100.0, 0.0, 6.0)), -3)
        self.assertEqual(contents(lumps, (0.0, 0.0, 61.0)), -1)
        faces = world_faces(lumps)
        lava_faces = [f for f in faces if f[0] == '*lava']
        self.assertEqual(len(lava_faces), 2)
        self.assertTrue(all(abs(z - 10.0) < 1e-4 for f in lava_faces for z in f[3]))

    def test_a_texture_the_room_map_lacks_is_refused(self):
        bsp, record = fixture_room(textures=('voidwall',))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'fixture.bsp'
            path.write_bytes(bsp)
            with self.assertRaises(ValueError):
                I.room_map(path, 'fixture', record, BOUNDS, {'water': 20.0, 'lava': []})


def room_work(tmp, water=None, pools=(), water_brush=None):
    """A converted room's work folder as prepare_area.build_room leaves it: conversion.json and room.map."""
    import lava
    from prepare_quake import box
    work = Path(tmp) / 'room'
    work.mkdir()
    walls = [box([-232, -232, -82], [232, 232, -74], 'voidwall')]
    if water_brush is not None:
        walls.append(box([-224, -224, -74], [224, 224, water_brush], '*water'))
    records = []
    for hull, top in pools:
        walls += lava.pool_brushes(hull, top)
        records.append({'reference': 1, 'id': 'lava_pool', 'model': 'meshes/x.nif', 'top': round(top, 2),
                        'corners': len(hull), 'dps': 10, 'sound': None})
    text = '{\n"classname" "worldspawn"\n"wad" "room.wad"\n' + '\n'.join(walls) + '\n}\n' + \
           '{\n"classname" "info_player_start"\n"origin" "0 0 0"\n}\n'
    (work / 'room.map').write_text(text, encoding='cp1252')
    (work / 'conversion.json').write_text(json.dumps({'water_height': water,
                                                      'lava': {'mode': 'quake', 'pools': records}}))
    return work


class RoomLiquidSourceTests(unittest.TestCase):
    def test_no_liquids(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = room_work(tmp)
            self.assertEqual(I.room_liquids(work), (None, None))
            self.assertIsNone(I.unsupported(work))

    def test_water_comes_from_the_record_and_the_room_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            # water_height in game units, the room map at SCALE (0.25)
            liquids, why = I.room_liquids(room_work(tmp, water=-29, water_brush=-7.25))
        self.assertIsNone(why)
        self.assertEqual(liquids, {'water': -7.25, 'lava': []})

    def test_a_pool_comes_from_its_lava_prism(self):
        hull = [[10.0, 0.0], [40.0, 5.0], [30.0, 30.0], [5.0, 20.0]]
        with tempfile.TemporaryDirectory() as tmp:
            liquids, why = I.room_liquids(room_work(tmp, pools=[(hull, -12.5)]))
        self.assertIsNone(why)
        self.assertIsNone(liquids['water'])
        self.assertEqual(liquids['lava'][0]['top'], -12.5)
        self.assertEqual(sorted(map(tuple, liquids['lava'][0]['hull'])), sorted(map(tuple, hull)))

    def test_mismatches_keep_the_room_map_lava_under_water_comes_over(self):
        with tempfile.TemporaryDirectory() as tmp:
            liquids, why = I.room_liquids(room_work(tmp, water=-29, water_brush=0.0))
        self.assertIsNone(liquids)
        self.assertIn('water', why)
        # lava at or under the water level: carved into the water since v0.0.48 (CHIM-ROOM-LAVA-UNDER-WATER-48)
        with tempfile.TemporaryDirectory() as tmp:
            liquids, why = I.room_liquids(room_work(tmp, water=40, water_brush=10.0, pools=[(POOL, 5.0)]))
        self.assertIsNone(why)
        self.assertEqual((liquids['water'], [p['top'] for p in liquids['lava']]), (10.0, [5.0]))
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(I.unsupported(room_work(tmp, water=40, water_brush=10.0, pools=[(POOL, 5.0)])))


class FailedRoomTests(unittest.TestCase):
    """CHIM-ROOM-FAIL-STAGE-48: one room that cannot be made (a model over the clipnode budget, say) failed the whole
    CHIM interiors stage, so a default build with every room batch would fail at its end. Now the room is named and
    left out; a batch room's shell map leaves the image with it (its doors stay inert)."""

    def test_a_failed_room_is_named_and_the_stage_goes_on(self):
        from unittest.mock import patch

        def failing(task):
            return {'room': Path(task[0]).name, 'failed': 'ValueError: Clipnode budget exceeded (models.py:214 collider)'}
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / 'ribad'
            work.mkdir()
            (work / 'conversion.json').write_text(json.dumps({'water_height': None, 'lava': {'pools': []}}))
            with patch.object(I, '_room_task', failing):
                receipt = I.build([work], Path(tmp) / 'palette.lmp', Path(tmp) / 'out', jobs=1)
        self.assertEqual(receipt['rooms'], [])
        self.assertEqual(receipt['failed_rooms'], [{'room': 'ribad', 'reason':
                                                    'ValueError: Clipnode budget exceeded (models.py:214 collider)'}])

    def test_install_removes_the_shell_maps_of_rooms_not_made(self):
        import chim_room_batches as S
        with tempfile.TemporaryDirectory() as tmp:
            out, id1 = Path(tmp) / 'out', Path(tmp) / 'id1'
            (out / I.STORE / 'rooms').mkdir(parents=True)
            (id1 / 'maps').mkdir(parents=True)
            shell = S.shell_map((-64, -64, -64), (64, 64, 64), ['{\n"classname" "worldspawn"\n"%s" "1"\n}' % S.SHELL_KEY])
            self.assertTrue(I.is_shell_map(shell))
            (id1 / 'maps/ribad.bsp').write_bytes(shell)
            (id1 / 'maps/rikept.bsp').write_bytes(shell)
            bsp, _ = fixture_room()
            self.assertFalse(I.is_shell_map(bsp))
            (id1 / 'maps/bmtown.bsp').write_bytes(bsp)              # a town room kept as its room map stays
            (out / 'chim-rooms-receipt.json').write_text(json.dumps(
                {'rooms': [], 'failed_rooms': [{'room': 'ribad', 'reason': 'x'}],
                 'kept_room_maps': [{'room': 'rikept', 'reason': 'y'}, {'room': 'bmtown', 'reason': 'z'}]}))
            record = I.install(out, id1)
            self.assertFalse((id1 / 'maps/ribad.bsp').exists())
            self.assertFalse((id1 / 'maps/rikept.bsp').exists())
            self.assertTrue((id1 / 'maps/bmtown.bsp').exists())
            self.assertEqual(sorted(r['room'] for r in record['shell_maps_removed']), ['ribad', 'rikept'])


if __name__ == '__main__':
    unittest.main()
