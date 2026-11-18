# SPDX-License-Identifier: GPL-3.0-only
"""--served-build (tools/toolkit_serve.py): a delivered build's maps, CHIM world and rooms store are served by themselves, the
newest copy wins without a restart, and the Polycount inspector opens it by default (TOOLKIT-SERVES-LATEST-BUILD-64)."""
import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import toolkit_serve as ts  # noqa: E402


def make_copy(folder, label, rooms=('addamasartus', 'bmcouncil'), maps=('seyda', 'bmhlaalo')):
    folder.mkdir(parents=True)
    (folder / 'maps').mkdir()
    for name in maps:
        (folder / 'maps' / (name + '.bsp')).write_bytes(b'BSP:' + name.encode())
    (folder / 'chim').mkdir()
    (folder / 'chim' / 'world.cwi').write_bytes(b'WORLD')
    (folder / 'chimi' / 'rooms').mkdir(parents=True)
    (folder / 'chimi' / 'world.cwi').write_bytes(b'STORE')
    for name in rooms:
        (folder / 'chimi' / 'rooms' / (name + '.crm')).write_bytes(b'ROOM:' + name.encode())
    (folder / ts.SERVED_MARK).write_text(json.dumps({'label': label, 'version': '0.0.64-dev4', 'run': 'r', 'commit': 'abc'}))


class ServedBuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.saved = (ts.Handler.served_build, ts.Handler.served_cache, ts.Handler.maps_dir, ts.Handler.chim_worlds)
        self.addCleanup(lambda: (setattr(ts.Handler, 'served_build', self.saved[0]), setattr(ts.Handler, 'served_cache', self.saved[1]),
                                 setattr(ts.Handler, 'maps_dir', self.saved[2]), setattr(ts.Handler, 'chim_worlds', self.saved[3])))
        ts.Handler.maps_dir, ts.Handler.chim_worlds = None, {}
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), ts.Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def get(self, path):
        try:
            with urllib.request.urlopen('http://127.0.0.1:%d%s' % (self.server.server_address[1], path), timeout=10) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, b''

    def serve(self, folder):
        ts.Handler.served_build = Path(folder).resolve()
        ts.Handler.served_cache = (0.0, None)

    def test_a_copy_is_listed_and_served(self):
        make_copy(self.tmp / 'v0.0.64-dev4', 'v0.0.64-dev4 (abc)')
        self.serve(self.tmp / 'v0.0.64-dev4')
        status, body = self.get('/build/config.json')
        info = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual((info['label'], info['maps'], info['rooms'], info['world'], info['interiors'], info['base']),
                         ('v0.0.64-dev4 (abc)', ['bmhlaalo', 'seyda'], ['addamasartus', 'bmcouncil'], True, True, '/chim-world/build/'))
        self.assertEqual(json.loads(self.get('/maps/index.json')[1]), ['bmhlaalo', 'seyda'])
        self.assertEqual(self.get('/maps/seyda.bsp'), (200, b'BSP:seyda'))
        self.assertEqual(self.get('/chim-world/build/chimi/rooms/bmcouncil.crm'), (200, b'ROOM:bmcouncil'))
        self.assertEqual(self.get('/chim-world/build/chimi/world.cwi'), (200, b'STORE'))
        self.assertEqual(self.get('/chim-world/build/chim/world.cwi'), (200, b'WORLD'))
        self.assertIn('build', json.loads(self.get('/chim-world/index.json')[1]))

    def test_nothing_outside_the_copy_is_served(self):
        make_copy(self.tmp / 'a', 'a')
        (self.tmp / 'secret.txt').write_text('no')
        self.serve(self.tmp / 'a')
        self.assertEqual(self.get('/chim-world/build/%2e%2e/secret.txt')[0], 400)
        self.assertEqual(self.get('/chim-world/build/chimi/rooms/none.crm')[0], 404)

    def test_the_newest_copy_wins_without_a_restart(self):
        make_copy(self.tmp / 'copies' / 'v0.0.64-dev4', 'v0.0.64-dev4')
        self.serve(self.tmp / 'copies')
        self.assertEqual(json.loads(self.get('/build/config.json')[1])['label'], 'v0.0.64-dev4')
        time.sleep(0.05)
        make_copy(self.tmp / 'copies' / 'v0.0.64-dev5', 'v0.0.64-dev5', rooms=('bmnew',))
        os.utime(self.tmp / 'copies' / 'v0.0.64-dev5' / ts.SERVED_MARK, (time.time() + 5, time.time() + 5))
        ts.Handler.served_cache = (0.0, None)                      # the server looks again every two seconds
        info = json.loads(self.get('/build/config.json')[1])
        self.assertEqual((info['label'], info['rooms']), ('v0.0.64-dev5', ['bmnew']))

    def test_a_folder_without_a_marker_is_not_a_copy(self):
        (self.tmp / 'half' / 'maps').mkdir(parents=True)          # a copy still being written has no marker yet
        self.assertIsNone(ts.served_build_root(self.tmp))
        self.serve(self.tmp)
        self.assertEqual(self.get('/build/config.json')[0], 404)

    def test_the_inspector_opens_the_served_build_by_default(self):
        page = (ROOT / 'amiwind-toolkit' / 'map-inspector.html').read_text(encoding='utf-8')
        for needle in ("fetch('/build/config.json'", 'async function servedBuildOpen(sb,q)', "q.get('room')",
                       "if(!w&&!u&&!z&&!rs){const sb=await servedBuild();", 'id="servedmap"', 'chimOpenRooms(AmiWindChim.urlSource(sb.base)'):
            self.assertIn(needle, page)

    def test_the_world_map_reads_the_served_maps(self):
        self.assertIn("fetch('../maps/index.json')", (ROOT / 'amiwind-toolkit' / 'world-map.html').read_text(encoding='utf-8'))

    def test_the_frame_that_holds_each_cell(self):
        """/build/cell-maps.json (TOOLKIT-LOCAL-CHIM-CELL-NO-MAP-67): a cell's region frame from the ownership table, the
        cells of a town frame from its chunk area, and the town's frame map; nothing for a cell no frame holds."""
        copy = self.tmp / 'v0.0.67'
        make_copy(copy, 'v0.0.67 (abc)')
        cell_world(copy)
        self.serve(copy)
        status, body = self.get('/build/cell-maps.json')
        self.assertEqual(status, 200)
        doc = json.loads(body)
        self.assertEqual((doc['ok'], doc['format'], doc['label']), (True, 'aw-toolkit-cell-maps-1', 'v0.0.67 (abc)'))
        cells = doc['cells']
        self.assertEqual(cells['0,0'], {'frame': 'frames/x+00/y+00', 'frame_id': 'rcp0_p0', 'maps': []})
        town = {'frame': 'frames/x+05/y+05', 'frame_id': None, 'maps': ['town-chim']}
        for key in ('4,4', '4,5', '5,5', '5,6', '6,4'):
            self.assertEqual(cells[key], town, key)
        # a second town whose area overlaps the first: cell 6,5 lies deeper inside the second, 5,5 inside the first
        self.assertEqual(cells['6,5']['frame'], 'frames/x+07/y+05')
        self.assertEqual(cells['9,5']['frame'], 'frames/x+07/y+05')
        self.assertNotIn('1,0', cells)                        # the region frame's margin holds no other cell's centre
        self.assertNotIn('3,5', cells)
        self.assertEqual(ts.served_cell_maps(self.tmp / 'nothing'), {})
        self.assertIn("fetch('../build/cell-maps.json'", (ROOT / 'amiwind-toolkit' / 'world-map.html').read_text(encoding='utf-8'))
        # /build/rooms.json (TOOLKIT-TILE-TO-INSPECTOR-67): the built room of each interior cell, from the room maps' heads
        status, body = self.get('/build/rooms.json')
        rooms = json.loads(body)
        self.assertEqual((status, rooms['format'], rooms['base']), (200, 'aw-toolkit-rooms-1', '/chim-world/build/'))
        self.assertEqual(rooms['rooms'], {
            'Mournhold, Royal Palace: Reception Area': {'room': 'rid3587e40b7', 'map': 'rid3587e40b7', 'types': [], 'default_type': None},
            'Vivec, Arena Pit': {'room': 'vai000', 'map': 'vai000', 'types': ['vai000t0', 'vai000t1', 'vai000t2'], 'default_type': 'vai000t2'}})
        self.assertIn("fetch('../build/rooms.json'", (ROOT / 'amiwind-toolkit' / 'world-map.html').read_text(encoding='utf-8'))

    def test_the_drawn_faces_of_every_room(self):
        """/build/room-faces.json (the rooms heatmap, TOOLKIT-DLC-VIEWS-64): every placement counts its model's faces (the
        face lump of the model's brush image in its pack); the heaviest models first."""
        copy = self.tmp / 'v0.0.67'
        make_copy(copy, 'v0.0.67 (abc)')
        room_store(copy)
        self.serve(copy)
        status, body = self.get('/build/room-faces.json')
        doc = json.loads(body)
        self.assertEqual((status, doc['format']), (200, 'aw-toolkit-room-faces-1'))
        self.assertEqual(doc['rooms']['mh_hall'], {'faces': 3 * 40 + 1 * 7, 'placements': 4, 'models': 2,
                                                    'top': [['i/test_hall_wall', 40, 3, 120], ['l/test_lamp', 7, 1, 7]]})
        self.assertNotIn('addamasartus', doc['rooms'])                  # make_copy's placeholder records are not rooms
        self.assertEqual(ts.served_room_faces(self.tmp / 'nothing'), {})


def room_store(copy):
    """A served copy's rooms store: an index naming two models in one pack (brush images of 7 and 40 faces) and a room
    record placing the second three times and the first once (56-byte placed records)."""
    import struct
    from chim import format as F
    pack, models = bytearray(), []
    for name, faces in (('l/test_lamp', 7), ('i/test_hall_wall', 40)):
        lumps = [b''] * 15
        lumps[7] = bytes(20 * faces)
        image = F.brush_image(lumps)[0]
        models.append((name, 0, len(pack), len(image), len(image)))
        pack += image
    (copy / 'chimi' / 'packs').mkdir(parents=True)
    (copy / 'chimi' / 'packs' / 'p0.cpk').write_bytes(bytes(pack))
    rows = [{'kind': b'PACK', 'sector': 0, 'cell': (0, 0), 'bytes': len(pack), 'crc': F.crc32(bytes(pack)), 'entries': 2, 'path': 'packs/p0.cpk'}]
    settings = {'draw_distance': 2048.0, 'hysteresis': 256.0, 'collision_margin': 64.0, 'prefetch_margin': 256.0, 'grain': 256,
                'terrain_light': 128, 'placements': 0, 'models': 2, 'textures': 0, 'frames': 0, 'sector_chunks': 1}
    (copy / 'chimi' / 'world.cwi').write_bytes(F.index_file(settings, rows, models, []))
    placed = [1, 1, 1, 0]
    body = struct.pack('>6fII', -64, -64, 0, 64, 64, 128, 2, 0) + struct.pack('>2I', 0, 1)
    body += b''.join(struct.pack('>III', k, 100 + k, m) + bytes(44) for k, m in enumerate(placed))
    total = 32 + len(body)
    (copy / 'chimi' / 'rooms' / 'mh_hall.crm').write_bytes(b'CHIMROOM' + struct.pack('>HHIIIII', 0, 13, 32, len(placed), 64, 72, total) + body)


def cell_world(copy):
    """A served copy's world index with a region frame at cell 0,0 (named in the ownership table), a town frame at 5,5
    whose chunk area spans three cells each way (cells 4 to 6), a second town at 7,5 whose area (x 5.25 to 9.75, y 4 to
    8.5 cells) overlaps it, their frame files' blocks, and the first town's frame map."""
    from chim import format as F
    from chim.frame_map import empty_world, entity_text
    frames = [((0, 0), (0.5 * 8192, 0.5 * 8192), (-1920.0, -1920.0), 15, 15),
              ((5, 5), (5.5 * 8192, 5.5 * 8192), (-3072.0, -3072.0), 24, 24),
              ((7, 5), (7.5 * 8192, 5.5 * 8192), (-4608.0, -3072.0), 36, 36)]
    rows = []
    for cell, centre, low, nx, ny in frames:
        path = 'frames/x%+03d/y%+03d/frame.ccf' % cell
        data = F.frame_file({'cell': cell, 'centre': centre, 'low': low, 'grain': 256, 'nx': nx, 'ny': ny, 'sector_chunks': 1,
                             'owned_total': 0}, [], [])
        (copy / 'chim' / path).parent.mkdir(parents=True)
        (copy / 'chim' / path).write_bytes(data)
        rows.append({'kind': b'FRAM', 'sector': 0, 'cell': cell, 'bytes': len(data), 'crc': F.crc32(data), 'entries': 0, 'path': path})
    settings = {'draw_distance': 2048.0, 'hysteresis': 256.0, 'collision_margin': 64.0, 'prefetch_margin': 256.0, 'grain': 256,
                'terrain_light': 128, 'placements': 0, 'models': 0, 'textures': 0, 'frames': 3, 'sector_chunks': 1}
    (copy / 'chim' / 'world.cwi').write_bytes(F.index_file(settings, rows, [], []))
    (copy / 'chim-regions.json').write_text(json.dumps({'format': 'aw-chim-ownership-1', 'cells': {'0,0': {'frame': 'rcp0_p0', 'kind': 'land'}},
                                                        'frames': [{'id': 'rcp0_p0', 'cell': [0, 0], 'cells': [[0, 0]]}]}))
    for name, world in (('town-chim', {'_chim_frame': '5 5'}),
                        ('rid3587e40b7', {'message': 'Mournhold, Royal Palace: Reception Area', '_aw_cell_id': 'Mournhold, Royal Palace: Reception Area',
                                          '_chim_world': 'chimi', '_chim_room': 'rid3587e40b7'}),
                        ('vai000', {'message': 'Vivec, Arena Pit', '_aw_cell_id': 'Vivec, Arena Pit', '_chim_world': 'chimi', '_chim_room': 'vai000',
                                    '_chim_room_types': '0 1 2', '_chim_room_type_default': '2'})):
        lumps = empty_world((-512.0, -512.0, -256.0), (512.0, 512.0, 2048.0))
        lumps[0] = entity_text([dict({'classname': 'worldspawn'}, **world)])
        (copy / 'maps' / (name + '.chim')).write_bytes(F.brush_image(lumps)[0])


if __name__ == '__main__':
    unittest.main()
