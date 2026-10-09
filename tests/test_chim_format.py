# SPDX-License-Identifier: GPL-3.0-only
"""CHIM world format 0.1: builder, writer and validator on synthetic data (no game assets)."""
import json
import math
import os
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import format as F  # noqa: E402
from chim import CHIM_VERSION, FORMAT_VERSION  # noqa: E402
from chim.build import build_frame  # noqa: E402
from chim.models import model_image_lumps  # noqa: E402
from chim.terrain import chunk_terrain, quake_texture_axes  # noqa: E402
from chim.units import UnitCache, fingerprint, tool_fingerprint  # noqa: E402
from chim.validate import measure, validate  # noqa: E402

STEP = 128
LOW = (-512.0, -512.0)
SPAN = (1024, 1024)
CENTRE = (4096.0, 4096.0)
TEXSIZE = 32
# A coarse grey ramp: neighbouring greys quantize to the same palette entry.
PALETTE = bytes(v for i in range(256) for v in (i // 4 * 4,) * 3)


def solid_miptex(name, size, value):
    from PIL import Image
    from prepare_quake import miptex
    im = Image.new('P', (size, size), value)
    im.putpalette(bytes(range(256)) * 3)
    return miptex(name, im)


def box_surfaces(s, h, sy=None):
    """Faces of a box [-s, s] x [-sy, sy] x [0, h] (sy defaults to s), counter-clockwise about outward normals."""
    sy = s if sy is None else sy
    c = np.array([[x, y, z] for z in (0, h) for y in (-sy, sy) for x in (-s, s)], dtype=float)
    quads = [((0, 2, 3, 1), (0, 0, -1)), ((4, 5, 7, 6), (0, 0, 1)), ((0, 1, 5, 4), (0, -1, 0)),
             ((2, 6, 7, 3), (0, 1, 0)), ((0, 4, 6, 2), (-1, 0, 0)), ((1, 3, 7, 5), (1, 0, 0))]
    out = []
    for ids, n in quads:
        n = np.array(n, dtype=float)
        out.append((c[list(ids)], n, quake_texture_axes(n), np.zeros(2), 0))
    return out, c


def box_prepared(s, h, sy=None):
    """A box as prepare_mesh_bsp._prepare_model returns a mesh (texture axes per texture size)."""
    surfaces, corners = box_surfaces(s, h, sy)
    from mesh_geometry import split_surface
    # split at 240 texels as _prepare_model does (large boxes)
    polys = [(patch, 0, ax / TEXSIZE, off, n) for q, n, ax, off, _ in surfaces
             for patch in split_surface(q, np.column_stack((ax.T, off)))]
    return (np.column_stack((corners * 4, np.zeros((len(corners), 2)))), np.array([[0, 1, 2, 0]]), polys,
            [(corners, None, [], 0.)], {})


def height(x, y):
    # not separable in x and y, so most tiles are two triangles, not one quad
    return 24.0 * np.sin(x / 300.0) + 0.05 * y + 0.0002 * x * y - 4.0


def material(x, y):
    # alternating tiles: every chunk holds both ground materials
    return 1 + int(x // STEP) % 2


MODEL_OF = {'small': 0, 'large': 1, 'small-again': 2}
ROWS = [
    {'ref': 11, 'cell': (0, 0), 'origin': (-400.0, -400.0, 10.0), 'yaw': 0.0, 'variant': 'small'},
    {'ref': 12, 'cell': (0, 0), 'origin': (130.0, 70.0, 0.0), 'yaw': 30.0, 'variant': 'large'},
    {'ref': 13, 'cell': (1, 0), 'origin': (500.0, 500.0, 0.0), 'yaw': 90.0, 'variant': 'small'},
    {'ref': 14, 'cell': (0, 0), 'origin': (-10.0, 300.0, 0.0), 'yaw': 0.0, 'variant': 'small-again'},
    {'ref': 16, 'cell': (0, 0), 'origin': (-200.0, 100.0, 0.0), 'yaw': 45.0, 'variant': 'small-again'},
    {'ref': 15, 'cell': (0, 0), 'origin': (255.9, -0.1, 0.0), 'yaw': 0.0, 'variant': 'small'}]


def fixture(out, placements=None, settings=None, duplicate_texture=False, jobs=1, cache=None, mesh_fps=None,
            heights_of=height, same_ground=False, hollow_large=False, mesh_occluders=True, large_size=(100, 64),
            prepared_of=None, ground=None, own_profiles=False, qbsp=None, collision_cache=None):
    """A 4 x 4 chunk frame through the real CHIM units (chim.build.build_frame)."""
    placements = ROWS if placements is None else placements
    models = [dict(source='meshes/x/small.nif', materials=[dict(texture_index=None, diffuse=[1, 1, 1])], flames=[]),
              dict(source='meshes/x/large.nif', materials=[dict(texture_index=None,
                                                                 diffuse=[1.006 if duplicate_texture else 0.5, 1, 1])],
                   flames=[]),
              dict(source='meshes/x/small-copy.nif', materials=[dict(texture_index=None, diffuse=[1, 1, 1])], flames=[])]
    if own_profiles:
        # models carrying their own (empty) converter profile, as the Seyda tutorial barrel does
        models = [dict(m, _profile={}) if 'small' in m['source'] else m for m in models]
    prepared = {0: box_prepared(20, 40), 1: box_prepared(*large_size), 2: box_prepared(20, 40)}
    prepared.update(prepared_of or {})
    refs = [{'number': p['ref'], 'model_index': MODEL_OF[p['variant']], 'scale': 1.0, 'cell': list(p['cell']),
             'position': [CENTRE[0] + p['origin'][0] * 4, CENTRE[1] + p['origin'][1] * 4, p['origin'][2] * 4],
             'rotation_radians': [0.0, 0.0, -math.radians(p['yaw'])]} for p in placements]
    xs = range(int(LOW[0]), int(LOW[0]) + SPAN[0] + 1, STEP)
    ys = range(int(LOW[1]), int(LOW[1]) + SPAN[1] + 1, STEP)
    heights = [[float(heights_of(x, y)) for x in xs] for y in ys]
    materials = [[material(x + STEP / 2, y + STEP / 2) for x in xs[:-1]] for y in ys[:-1]]
    settings = settings or {'grain': 256, 'sector_chunks': 2}
    receipt = build_frame(out, frame={'cell': (0, 0), 'centre': CENTRE, 'low': LOW, 'span': SPAN}, centre=CENTRE,
                          models=models, references=refs, prepared=prepared,
                          profiles={m['source']: dict({'texture_size': TEXSIZE},
                                                      **({'hollow_collision': True}
                                                         if hollow_large and 'large' in m['source'] else {}))
                                    for m in models if '_profile' not in m},
                          mesh_fps=mesh_fps or {0: 'small', 1: 'large', 2: 'small-copy'}, texture_records=[],
                          archive=None, palette=PALETTE, heights=heights, materials=materials, step=STEP,
                          floor=-1024, ceiling=2048,
                          ground_textures={'g1': solid_miptex('g1', 32, 10),
                                           'g2': solid_miptex('g2', 32, 10 if same_ground else 20),
                                           '*water': solid_miptex('*water', 64, 30)},
                          jobs=jobs, cache=cache, settings=settings, mesh_occluders=mesh_occluders,
                          ground=ground, qbsp=qbsp, collision_cache=collision_cache)
    source = {'placements': [{'ref': p['ref'], 'cell': list(p['cell'])} for p in placements],
              'doors': [[-400, -400], [400, 400], [-300, 300]], 'terrain_step': STEP,
              'terrain_low': list(LOW), 'terrain_tiles': (len(xs) - 1) * (len(ys) - 1), 'water_level': 0.0,
              'terrain_heights': heights}
    if ground is not None:
        source.update(terrain_triangles=ground.rows(), terrain_size=list(ground.size))
    return receipt, source


def chim_files(out):
    root = Path(out) / 'chim'
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob('*')) if p.is_file()}


class World:
    """A written CHIM world opened for tampering: every change is relinked (sector file, frame file,
    index directories, sizes and CRCs), so only the tampering itself is wrong."""

    def __init__(self, out):
        self.root = Path(out) / 'chim'
        self.settings, self.files, self.models, self.textures = F.read_index((self.root / 'world.cwi').read_bytes())
        self.frame_row = next(i for i, f in enumerate(self.files) if f['kind'] == b'FRAM')
        self.frame, self.chunks, self.sectors = F.read_frame(self.path(self.frame_row).read_bytes())

    def path(self, row):
        return self.root / self.files[row]['path']

    def sector_row(self, si):
        return next(i for i, f in enumerate(self.files) if f['kind'] == b'SECT' and f['sector'] == si)

    def records(self, si):
        return [(r['kind'], r['id'], r['data']) for r in F.read_sector(self.path(self.sector_row(si)).read_bytes())]

    def chunk(self, index):
        c = self.chunks[index]
        raw = next(d for k, i, d in self.records(c['sector']) if k == b'CHNK' and i == index)
        return dict(c, **F.read_chunk(raw))

    def write_sector(self, si, records):
        row = self.sector_row(si)
        blob = F.sector_file(records)
        self.path(row).write_bytes(blob)
        at = {(r['kind'], r['id']): r for r in F.read_sector(blob)}
        for c in self.chunks:
            if c['sector'] == si and (b'CHNK', c['index']) in at:
                r = at[(b'CHNK', c['index'])]
                c['offset'] = r['offset']
                c['render'] = F.read_chunk(r['data'])['render']
                c['collision'] = r['bytes'] - c['render']
        for kind, directory in ((b'MODL', self.models), (b'TEXR', self.textures)):
            for i, e in enumerate(directory):
                if (kind, i) in at:
                    e['file'], e['offset'], e['bytes'] = row, at[(kind, i)]['offset'], at[(kind, i)]['bytes']
        self.sectors[si] = dict(self.sectors[si], bytes=len(blob), crc=F.crc32(blob))
        self.files[row] = dict(self.files[row], bytes=len(blob), crc=F.crc32(blob), entries=len(records))
        self.save()

    def write_chunk(self, index, owned=None, reach=None, pvs=None, image=None, pvl=None):
        c = self.chunk(index)
        data, _, _ = F.chunk_record([F.placement(*F.record_args(p)) for p in (owned or c['owned'])],
                                    [F.placement(*F.record_args(p)) for p in (reach or c['reach'])],
                                    c['pvs'] if pvs is None else pvs,
                                    *(image or (c['image'], c['image_render'])), c['leaves'],
                                    c['pvl'] if pvl is None else pvl)
        records = [(k, i, data if (k, i) == (b'CHNK', index) else d) for k, i, d in self.records(c['sector'])]
        self.write_sector(c['sector'], records)

    def save(self):
        rows = [(c['cx'], c['cy'], c['sector'], c['offset'], c['render'], c['collision'], c['owned_count'],
                 c['reach_count'], c['zmin'], c['zmax']) for c in self.chunks]
        blob = F.frame_file(self.frame, rows, [(s['sx'], s['sy'], s['bytes'], s['crc']) for s in self.sectors])
        self.path(self.frame_row).write_bytes(blob)
        self.files[self.frame_row] = dict(self.files[self.frame_row], bytes=len(blob), crc=F.crc32(blob))
        index = F.index_file(self.settings, self.files,
                             [(m['name'], m['file'], m['offset'], m['bytes'], m['render']) for m in self.models],
                             [(t['name'], t['file'], t['offset'], t['bytes'], t['width'], t['height'])
                              for t in self.textures])
        (self.root / 'world.cwi').write_bytes(index)


class ChimWriterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_world_validates_and_stores_everything_once(self):
        receipt, source = fixture(self.tmp)
        fails, world = validate(self.tmp, source)
        self.assertEqual(list(fails), [])
        self.assertEqual(receipt['builder'], 'chim')
        self.assertEqual(receipt['chim_version'], CHIM_VERSION)
        self.assertEqual(receipt['world_format'], '%d.%d' % FORMAT_VERSION)
        self.assertEqual(receipt['placements'], 6)
        # the two 'small' variants are byte-identical: one model, recorded as an alias
        self.assertEqual(receipt['models'], 2)
        self.assertEqual(len(receipt['model_aliases']), 1)
        # the large box reaches beyond its owner chunk; reach copies are records only
        self.assertGreater(receipt['reach_copies'], 4)
        self.assertEqual(receipt['chunks'], 16)
        self.assertEqual(receipt['sectors'], 4)
        self.assertEqual(receipt['terrain']['tiles'], 64)
        self.assertGreater(receipt['terrain']['water_faces'], 0)
        m = measure(world, source)
        self.assertEqual(m['placements'], 6)
        self.assertEqual(m['reach_copies'], receipt['reach_copies'])
        walk = m['walk']['extra_0']
        self.assertGreater(walk['cold_bytes'], 0)
        self.assertLessEqual(walk['per_crossing_max'], m['bytes_total'])
        self.assertIn('estimated_ms_p50', walk)

    def test_identical_texture_content_is_stored_once(self):
        receipt, source = fixture(self.tmp, duplicate_texture=True)
        fails, _ = validate(self.tmp, source)
        self.assertEqual(list(fails), [])
        self.assertEqual(receipt['textures'], receipt['texture_keys'] - 1)

    def test_ground_materials_with_one_texture_reference_it_once(self):
        receipt, source = fixture(self.tmp, same_ground=True)
        fails, _ = validate(self.tmp, source)
        self.assertEqual(list(fails), [])
        self.assertEqual(receipt['textures'], receipt['texture_keys'] - 1)

    def test_files_obey_ffs_rules_and_order(self):
        fixture(self.tmp)
        root = self.tmp / 'chim'
        for p in root.rglob('*'):
            self.assertLessEqual(len(p.name), F.FFS_NAME_CHARS)
        settings, files, models, textures = F.read_index((root / 'world.cwi').read_bytes())
        self.assertEqual([f['kind'] for f in files], [b'FRAM'] + [b'SECT'] * 4)
        self.assertEqual(settings['sector_chunks'], 2)
        frame, chunks, sectors = F.read_frame((root / files[0]['path']).read_bytes())
        self.assertEqual([(c['cx'], c['cy']) for c in chunks], F.sector_order(4, 4, 2)[0])
        for f in files[1:]:
            records = F.read_sector((root / f['path']).read_bytes())
            kinds = [r['kind'] for r in records]
            self.assertEqual(kinds[:4], [b'CHNK'] * 4)          # its chunks first, then what is first needed there
            self.assertNotIn(b'CHNK', kinds[4:])
        # model 0 is first needed by the first chunk that places anything; it is stored in that chunk's sector
        first = next(c for c in chunks if c['owned_count'] or c['reach_count'])
        self.assertEqual(files[models[0]['file']]['sector'], first['sector'])
        for c in chunks:
            # render part (placements, terrain faces) before the collision part (terrain hull)
            self.assertGreater(c['render'], 0)
            self.assertGreater(c['collision'], 0)

    def test_sector_size_must_divide_the_frame(self):
        with self.assertRaisesRegex(ValueError, 'Sector size must divide'):
            fixture(self.tmp, settings={'grain': 256, 'sector_chunks': 3})

    def test_boxes_come_from_stored_precision(self):
        # An origin that single precision rounds across a whole unit: the stored box,
        # the reach chunks and the leaf count must follow the stored values.
        rows = [{'ref': 1, 'cell': (0, 0), 'origin': (255.99999999, 10.0, 0.0), 'yaw': 33.3333333, 'variant': 'small'},
                {'ref': 2, 'cell': (0, 0), 'origin': (-0.000000001, -255.9999999, 0.0), 'yaw': 0.1, 'variant': 'large'}]
        receipt, source = fixture(self.tmp, rows)
        fails, _ = validate(self.tmp, source)
        self.assertEqual(list(fails), [])

    def test_parallel_build_matches_serial_byte_for_byte(self):
        fixture(self.tmp / 'serial', jobs=1)
        receipt, _ = fixture(self.tmp / 'parallel', jobs=2)
        self.assertEqual(chim_files(self.tmp / 'parallel'), chim_files(self.tmp / 'serial'))
        self.assertTrue(chim_files(self.tmp / 'serial'))

    def test_unit_cache_reuses_and_rebuilds_only_changed_units(self):
        cache_dir = self.tmp / 'units'
        cache = UnitCache(cache_dir)
        fixture(self.tmp / 'a', cache=cache)
        self.assertTrue(all(v.get('reused', 0) == 0 for v in cache.stats.values()), cache.stats)
        cache = UnitCache(cache_dir)
        receipt, _ = fixture(self.tmp / 'b', cache=cache)
        self.assertTrue(all(v.get('built', 0) == 0 for v in cache.stats.values()), cache.stats)
        self.assertEqual(chim_files(self.tmp / 'b'), chim_files(self.tmp / 'a'))
        # one changed mesh: only its variant is built again
        cache = UnitCache(cache_dir)
        fixture(self.tmp / 'c', cache=cache, mesh_fps={0: 'small', 1: 'large, edited', 2: 'small-copy'})
        self.assertEqual(cache.stats['variant'], {'built': 1, 'reused': 2})
        self.assertEqual(cache.stats['terrain'], {'built': 0, 'reused': 16})
        self.assertEqual(chim_files(self.tmp / 'c'), chim_files(self.tmp / 'a'))
        # one changed ground height inside a chunk: that chunk's terrain, the three neighbours whose
        # standing hull ring holds its tiles (format 0.4), and the visibility rows
        cache = UnitCache(cache_dir)
        fixture(self.tmp / 'd', cache=cache, heights_of=lambda x, y: height(x, y) + (5.0 if (x, y) == (-384, -384) else 0))
        self.assertEqual(cache.stats['terrain'], {'built': 4, 'reused': 12})
        self.assertEqual(cache.stats['variant'], {'built': 0, 'reused': 3})
        self.assertNotEqual(chim_files(self.tmp / 'd'), chim_files(self.tmp / 'a'))

    def test_unchanged_files_are_not_rewritten(self):
        receipt, _ = fixture(self.tmp)
        self.assertEqual(len(receipt['files_rewritten']), 6)
        receipt, _ = fixture(self.tmp)
        self.assertEqual(receipt['files_rewritten'], [])

    def test_files_of_an_older_layout_are_removed(self):
        stale = self.tmp / 'chim' / 'models' / 'm00.cmp'
        stale.parent.mkdir(parents=True)
        stale.write_bytes(b'old')
        keep = self.tmp / 'chim' / 'notes.txt'
        keep.write_bytes(b'not a CHIM file')
        receipt, source = fixture(self.tmp)
        self.assertEqual(receipt['files_removed'], ['chim/models/m00.cmp'])
        self.assertFalse(stale.parent.exists())
        keep.unlink()
        fails, _ = validate(self.tmp, source)
        self.assertEqual(list(fails), [])

    def test_placement_lists_hide_placements_behind_a_house(self):
        # a long hollow house between the small boxes at the frame's west and east ends
        rows = [{'ref': 1, 'cell': (0, 0), 'origin': (0.0, 0.0, 0.0), 'yaw': 0.0, 'variant': 'large'},
                {'ref': 2, 'cell': (0, 0), 'origin': (-460.0, 40.0, 0.0), 'yaw': 0.0, 'variant': 'small'},
                {'ref': 3, 'cell': (0, 0), 'origin': (460.0, 40.0, 0.0), 'yaw': 0.0, 'variant': 'small'}]
        receipt, source = fixture(self.tmp, rows, hollow_large=True, heights_of=lambda x, y: 4.0 + 0 * x,
                                  large_size=(60, 300, 500))
        fails, world = validate(self.tmp, source)
        self.assertEqual(list(fails), [])
        self.assertGreater(receipt['visibility']['placements_blocked'], 0)
        report = measure(world, source, cameras=[('west', CENTRE[0] - 460 * 4, CENTRE[1] + 40 * 4)])
        cam = report['cameras'][0]
        self.assertLess(cam['placement_list'], cam['ring_placements'])
        self.assertLess(cam['placement_list_faces'], cam['ring_faces'])
        pl = report['visibility']['placement_list']
        self.assertLessEqual(pl['placements_share_of_chunk_rows'], 1.0)

    def test_hollow_building_occludes_through_its_render_mesh(self):
        receipt, source = fixture(self.tmp / 'a', hollow_large=True)
        self.assertEqual(receipt['visibility']['occluder_meshes'], 1)
        self.assertEqual(receipt['visibility']['occluder_pieces'], 5)     # the five small solid boxes; its hollow shell is none
        with_mesh = receipt['visibility']['occluder_cells']
        fails, _ = validate(self.tmp / 'a', source)
        self.assertEqual(list(fails), [])
        receipt, _ = fixture(self.tmp / 'b', hollow_large=True, mesh_occluders=False)
        self.assertEqual(receipt['visibility']['occluder_meshes'], 0)
        self.assertGreater(with_mesh, receipt['visibility']['occluder_cells'] + 50)   # the house's core cells

    def test_partition_gets_the_files_in_pack_order(self):
        from chim.disk import pack_order, partition_command, partition_mib
        fixture(self.tmp)
        root = self.tmp / 'chim'
        order = pack_order(root)
        self.assertEqual(order[0], 'world.cwi')
        self.assertTrue(order[1].endswith('frame.ccf'))
        self.assertEqual([p.rsplit('/', 1)[1] for p in order[2:]], ['s%02d.ccs' % i for i in range(4)])
        command = partition_command('xdftool', 'p.hdf', root, 'AW_CHIM', 128)
        writes = [command[i + 2] for i, c in enumerate(command) if c == 'write']
        self.assertEqual(writes, ['chim/' + p for p in order])
        dirs = [command[i + 1] for i, c in enumerate(command) if c == 'makedir']
        self.assertEqual(dirs[:2], ['chim', 'chim/frames'])
        self.assertLess(command.index('chim/frames/x+00/y+00'), command.index('write'))
        self.assertEqual(partition_mib(17 << 20), 128)
        with self.assertRaisesRegex(ValueError, '2 GiB'):
            partition_mib(1800 << 20)

    def test_walk_writes_replay_lists_for_awbench(self):
        from chim.validate import write_replays
        receipt, source = fixture(self.tmp)
        fails, world = validate(self.tmp, source)
        walk = measure(world, source)['walk']
        write_replays(self.tmp / 'replay', walk.pop('_replay'), 'AW_CHIM:')
        text = (self.tmp / 'replay' / 'replay-extra0.txt').read_text(encoding='ascii')
        rows = json.loads((self.tmp / 'replay' / 'replay-extra0.json').read_text(encoding='utf-8'))
        self.assertTrue(text.startswith('X 0\nR AW_CHIM:chim/frames/x+00/y+00/s'))
        self.assertEqual(text.count('X '), len(rows))
        self.assertEqual(sum(r['runs'] for r in rows), text.count('\nR '))
        for line in text.splitlines():
            if line.startswith('R '):
                _, path, offset, n = line.split()
                data = (self.tmp / path.replace('AW_CHIM:', '')).read_bytes()
                self.assertLessEqual(int(offset) + int(n), len(data))

    def test_ring_reads_do_not_depend_on_string_hashing(self):
        # the walk's cache evicts in the order a ring's needs are listed; that order must not
        # follow Python's per-process string hashing (sets of paths)
        import subprocess
        code = ('import sys, json; sys.path[:0] = [%r]; from chim.validate import ring_needs; '
                'chunks = [{"file": "frames/x+00/y+00/s%%02d.ccs" %% (k * 7 %% 23), "terrain_textures": [], '
                '"records": []} for k in range(23)]; '
                'print(json.dumps(list(ring_needs(chunks, [], [], [], {c["file"]: 1 for c in chunks}))))'
                % str(ROOT / 'tools'))
        outs = {subprocess.run([sys.executable, '-c', code], env=dict(os.environ, PYTHONHASHSEED=seed),
                               capture_output=True, text=True, check=True).stdout for seed in ('1', '2', '3', '4')}
        self.assertEqual(len(outs), 1)

    def test_placement_listed_twice_is_refused(self):
        rows = [{'ref': 1, 'cell': (0, 0), 'origin': (0.0, 0.0, 0.0), 'yaw': 0.0, 'variant': 'small'}] * 2
        with self.assertRaisesRegex(ValueError, 'listed twice'):
            fixture(self.tmp, rows)


class ChimValidatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.receipt, self.source = fixture(self.tmp)
        self.world = World(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def validate(self):
        fails, _ = validate(self.tmp, self.source)
        return list(fails)

    def first_reach_chunk(self):
        return next(i for i in range(len(self.world.chunks)) if self.world.chunk(i)['reach'])

    def test_relinking_alone_keeps_the_world_valid(self):
        w = self.world
        w.write_chunk(0)
        self.assertEqual(self.validate(), [])

    def test_changed_reach_copy_is_found(self):
        i = self.first_reach_chunk()
        reach = [dict(p) for p in self.world.chunk(i)['reach']]
        reach[0]['origin'] = (123.0,) + tuple(reach[0]['origin'][1:])
        self.world.write_chunk(i, reach=reach)
        self.assertTrue(any('reach copy differs' in f for f in self.validate()))

    def test_reach_copy_turned_owner_is_found(self):
        i = self.first_reach_chunk()
        reach = [dict(p) for p in self.world.chunk(i)['reach']]
        reach[0]['owner'] = i
        self.world.write_chunk(i, reach=reach)
        self.assertTrue(self.validate())

    def test_missing_source_placement_is_found(self):
        self.source = dict(self.source, placements=self.source['placements'] + [{'ref': 99, 'cell': [0, 0]}])
        self.assertTrue(any('1 missing' in f for f in self.validate()))

    def test_corrupted_file_fails_its_index_crc(self):
        path = self.world.path(self.world.sector_row(0))
        data = bytearray(path.read_bytes())
        data[-1] ^= 0xFF
        path.write_bytes(bytes(data))
        self.assertTrue(any('CRC' in f for f in self.validate()))

    def test_long_file_name_breaks_the_ffs_rule(self):
        (self.world.root / ('x' * 31)).write_bytes(b'')
        self.assertTrue(any('longer than 30' in f for f in self.validate()))

    def test_file_over_the_size_limit_breaks_the_ffs_rule(self):
        from unittest.mock import patch
        with patch.object(F, 'FFS_MAX_PACK', 4096):
            self.assertTrue(any('1 GiB' in f for f in self.validate()))

    def test_model_stored_twice_is_found(self):
        w = self.world
        model = next(i for i, m in enumerate(w.models))
        data = next(d for k, i, d in w.records(w.models[model]['file'] - 1) if (k, i) == (b'MODL', model))
        other = next(si for si in range(len(w.sectors)) if si != w.models[model]['file'] - 1)
        records = w.records(other)
        records.insert(sum(1 for k, _, _ in records if k == b'CHNK'), (b'MODL', model, data))
        w.write_sector(other, records)
        fails = self.validate()
        self.assertTrue(any('stored more than once' in f for f in fails), fails)

    def test_model_moved_out_of_its_home_sector_is_found(self):
        w = self.world
        model = 0
        home = w.models[model]['file'] - 1
        other = next(si for si in range(len(w.sectors)) if si != home)
        data = next(d for k, i, d in w.records(home) if (k, i) == (b'MODL', model))
        w.write_sector(home, [r for r in w.records(home) if (r[0], r[1]) != (b'MODL', model)])
        records = w.records(other)
        records.insert(sum(1 for k, _, _ in records if k == b'CHNK'), (b'MODL', model, data))
        w.write_sector(other, records)
        fails = self.validate()
        self.assertTrue(any('not stored in the sector that first needs them' in f for f in fails), fails)

    def test_bytes_between_records_are_found(self):
        w = self.world
        path = w.path(w.sector_row(1))
        data = bytearray(path.read_bytes() + bytes(8))
        struct.pack_into('>I', data, 28, len(data))      # a header that agrees, so only the tiling is wrong
        data = bytes(data)
        path.write_bytes(data)
        w.sectors[1] = dict(w.sectors[1], bytes=len(data), crc=F.crc32(data))
        row = w.sector_row(1)
        w.files[row] = dict(w.files[row], bytes=len(data), crc=F.crc32(data))
        w.save()
        self.assertTrue(any('bytes after its last record' in f for f in self.validate()))

    def test_terrain_face_stored_twice_is_found(self):
        c = self.world.chunk(0)
        lumps = [bytearray(x) for x in F.read_brush_image(c['image'])]
        lumps[7] += lumps[7][:20]                      # the first ground face again
        struct.pack_into('<i', lumps[14], 60, struct.unpack_from('<i', lumps[14], 60)[0] + 1)
        self.world.write_chunk(0, image=F.brush_image(lumps))
        fails = self.validate()
        self.assertTrue(any('covered 2 times' in f for f in fails), fails)
        self.assertTrue(any('not on exactly one node' in f for f in fails), fails)

    def test_wrong_leaf_count_is_found(self):
        i = next(i for i in range(len(self.world.chunks)) if self.world.chunk(i)['owned'])
        owned = [dict(p) for p in self.world.chunk(i)['owned']]
        owned[0]['leaves'] += 1
        self.world.write_chunk(i, owned=owned)
        self.assertTrue(any('leaves' in f for f in self.validate()))

    def test_placement_row_missing_a_neighbour_placement_is_found(self):
        from chim.visibility import bits_to_row, compress_row
        i = next(i for i in range(len(self.world.chunks)) if self.world.chunk(i)['owned'])
        self.world.write_chunk(i, pvl=compress_row(bits_to_row([False] * self.world.frame['owned_total'])))
        self.assertTrue(any('misses a placement next to the chunk' in f for f in self.validate()))

    def test_placement_row_beyond_the_ring_is_found(self):
        from chim.visibility import bits_to_row, compress_row
        # a short draw distance: far placements are outside the ring
        self.world = None
        shutil.rmtree(self.tmp)
        self.tmp = Path(tempfile.mkdtemp())
        self.receipt, self.source = fixture(self.tmp, settings={'grain': 256, 'sector_chunks': 2,
                                                                'draw_distance': 200.0, 'hysteresis': 0.0})
        w = World(self.tmp)
        self.assertEqual(self.validate(), [])
        w.write_chunk(0, pvl=compress_row(bits_to_row([True] * w.frame['owned_total'])))
        self.assertTrue(any('outside the ring' in f for f in self.validate()))

    def test_asymmetric_pvs_row_is_found(self):
        from chim.visibility import bits_to_row, compress_row
        chunks = self.world.chunks
        first = chunks[0]
        far = next(c for c in chunks if abs(c['cx'] - first['cx']) + abs(c['cy'] - first['cy']) == 3)
        self.world.write_chunk(far['index'], pvs=compress_row(bits_to_row([True] * len(chunks))))
        fails = self.validate()
        self.assertTrue(any('not symmetric' in f or 'beyond the ring' in f for f in fails), fails)


class ChimVisibilityTests(unittest.TestCase):
    def test_vis_rows_round_trip_quake_compression(self):
        from chim.visibility import compress_row, decompress_row
        for row in (bytes(40), b'\x01' * 9, bytes(300) + b'\x80' + bytes(3), b'\x00\x05\x00'):
            self.assertEqual(decompress_row(compress_row(row), len(row)), row)
        self.assertEqual(compress_row(bytes(3) + b'\x07'), b'\x00\x03\x07')
        with self.assertRaises(ValueError):
            decompress_row(b'\x00', 4)

    def test_wall_and_ridge_block_sight_lines(self):
        from scipy.spatial import ConvexHull
        from chim.visibility import Ground, Occluders, cluster_pvs
        offsets = [(dx, 0) for dx in range(-6, 7)]
        flat = Ground([[0.0] * 13, [0.0] * 13], 128, (0, 0))
        tops = {(i, 0): 8.0 for i in range(6)}
        seen, stats = cluster_pvs(6, 1, 256, (0, 0), flat, None, tops, offsets)
        self.assertEqual(seen[(0, 0)], {(i, 0) for i in range(6)})
        occ = Occluders((0, 0), (1536, 256))
        wall = np.array([[x, y, z] for x in (740, 790) for y in (-40, 300) for z in (-50, 500)], dtype=float)
        occ.add(ConvexHull(wall).equations, wall)
        self.assertGreater(occ.cells(), 0)
        seen, stats = cluster_pvs(6, 1, 256, (0, 0), flat, occ, tops, offsets)
        self.assertNotIn((5, 0), seen[(0, 0)])
        self.assertIn((1, 0), seen[(0, 0)])
        self.assertIn((3, 0), seen[(2, 0)])            # neighbours always see each other
        self.assertGreater(stats['pairs_blocked'], 0)
        ridge = Ground([[0, 0, 0, 0, 0, 0, 900, 0, 0, 0, 0, 0, 0]] * 2, 128, (0, 0))
        seen, _ = cluster_pvs(6, 1, 256, (0, 0), ridge, None, tops, offsets)
        self.assertNotIn((5, 0), seen[(0, 0)])
        tall = dict(tops)
        tall[(5, 0)] = 5000.0
        seen, _ = cluster_pvs(6, 1, 256, (0, 0), ridge, None, tall, offsets)
        self.assertIn((5, 0), seen[(0, 0)])           # a tower behind the ridge stays visible

    def test_world_records_carry_boxes_leaves_and_the_16_leaf_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            receipt, source = fixture(Path(directory))
            fails, world = validate(Path(directory), source)
            self.assertEqual(list(fails), [])
            report = measure(world, source)['visibility']
        self.assertGreater(receipt['placements_over_16_leaves'], 0)
        self.assertEqual(report['placements_over_16_leaves'], receipt['placements_over_16_leaves'])
        self.assertGreater(report['leaves_per_placement']['max'], 16)
        self.assertLessEqual(report['chunk_bsp_depth']['max'], 6)
        self.assertEqual(report['frame_grid_depth'], 4)
        self.assertGreater(report['world_faces_per_view']['p50'], 0)
        self.assertGreaterEqual(receipt['visibility']['occluder_pieces'], 1)


class ChimUnitTests(unittest.TestCase):
    def test_fingerprint_changes_exactly_when_inputs_change(self):
        task = {'box': (0, 0, 256, 256), 'heights': [[0.0, 1.0], [2.0, 3.0]], 'step': 128}
        same = {'step': 128, 'heights': [[0.0, 1.0], [2.0, 3.0]], 'box': (0, 0, 256, 256)}
        self.assertEqual(fingerprint('terrain', task), fingerprint('terrain', same))
        moved = dict(task, heights=[[0.0, 1.0], [2.0, 3.0000001]])
        self.assertNotEqual(fingerprint('terrain', task), fingerprint('terrain', moved))
        self.assertNotEqual(fingerprint('terrain', task), fingerprint('variant', task))
        self.assertEqual(fingerprint('pvs', np.arange(4.0)), fingerprint('pvs', np.arange(4.0)))
        self.assertNotEqual(fingerprint('pvs', np.arange(4.0)), fingerprint('pvs', np.arange(4.0) + 1e-9))

    def test_build_switches_change_the_tool_fingerprint(self):
        # the stair rule's switch too: toggling it rebuilds the mesh and variant units (COLLISION-STAIR-SLOPE-32);
        # and the standing-hull form (--model-hull): a chain build never reuses routed hulls (BUILD-CHIM-UNIT-HULL-KEY-33)
        for name, value in (('AMIWIND_NO_FLAMES', '1'), ('AMIWIND_STAIR_MITIGATION', 'off'),
                            ('AMIWIND_MODEL_HULL', 'chain'), ('AMIWIND_MODEL_HULL', 'routed')):
            for kind in ('mesh', 'variant'):
                with self.subTest(name=name, kind=kind):
                    # measure from the switch's unset state: an earlier in-process build test may have exported
                    # the same value (mesh_geometry_env.export_model_hull), which made before == after (TEST-ENV-LEAK-HULL-33)
                    old = os.environ.pop(name, None)
                    try:
                        before = tool_fingerprint(kind)
                        os.environ[name] = value
                        self.assertNotEqual(tool_fingerprint(kind), before)
                        os.environ.pop(name)
                        self.assertEqual(tool_fingerprint(kind), before)
                    finally:
                        os.environ.pop(name, None)
                        if old is not None:
                            os.environ[name] = old

    def test_routed_hull_source_is_part_of_the_mesh_and_variant_fingerprints(self):
        from chim.units import TOOLS
        for kind in ('mesh', 'variant'):
            self.assertIn('tools/routed_hull.py', TOOLS[kind])

    def test_tool_sources_are_part_of_the_fingerprint(self):
        with tempfile.TemporaryDirectory() as directory:
            probe = Path(directory) / 'tool.py'
            probe.write_bytes(b'one')
            rel = os.path.relpath(probe, ROOT).replace(os.sep, '/')
            first = tool_fingerprint('probe-a', [rel])
            probe.write_bytes(b'two')
            self.assertNotEqual(tool_fingerprint('probe-b', [rel]), first)

    def test_damaged_cache_entry_is_rebuilt_and_counted(self):
        from chim.units import run_units
        with tempfile.TemporaryDirectory() as directory:
            cache = UnitCache(directory)
            self.assertEqual(run_units('probe', [('f' * 64, 3)], abs, 1, cache), [3])
            path = Path(directory) / 'probe' / 'ff' / ('f' * 64 + '.pickle')
            path.write_bytes(b'not a pickle')
            cache = UnitCache(directory)
            self.assertEqual(run_units('probe', [('f' * 64, -3)], abs, 1, cache), [3])
            self.assertEqual(cache.stats['probe'], {'damaged': 1, 'built': 1, 'reused': 0})


class ChimTerrainTests(unittest.TestCase):
    def test_flat_tile_is_one_quad_and_sloped_tiles_two_triangles(self):
        lumps, info = chunk_terrain((0, 0, 256, 256), 128, lambda x, y: 10.0, lambda x, y: 1, -1024,
                                    lambda m: 0, 1)
        self.assertEqual(info['faces'], 4)
        self.assertEqual(info['water_faces'], 0)
        lumps, info = chunk_terrain((0, 0, 256, 256), 128, lambda x, y: 0.001 * x * y + 5, lambda x, y: 1,
                                    -1024, lambda m: 0, 1)
        self.assertEqual(info['faces'], 8)
        tree = info['tree']
        # a box above one tile reaches its air leaves only; a box over the chunk reaches every air leaf
        self.assertEqual(len(tree.leaves_touched((5, 40, 100), (15, 50, 120))), 1)
        self.assertEqual(len(tree.leaves_touched((-10, -10, -2000), (300, 300, 3000))), 8)
        self.assertEqual(info['depth'], 4)            # x split, y split, diagonal, ground plane

    def test_ground_below_water_gets_two_sided_water(self):
        lumps, info = chunk_terrain((0, 0, 128, 128), 128, lambda x, y: x / 8 - 8, lambda x, y: 1, -1024,
                                    lambda m: 0, 1)
        self.assertEqual(info['water_faces'], 2)
        texinfo = list(struct.iter_unpack('<8fii', lumps[6]))
        faces = list(struct.iter_unpack('<HhihH4Bi', lumps[7]))
        water = [f for f in faces if texinfo[f[4]][9] & 1]
        self.assertEqual(len(water), 2)
        self.assertTrue(all(f[9] == -1 for f in water))
        self.assertTrue(all(texinfo[f[4]][9] == 0 and f[9] == 0 for f in faces if f not in water))
        self.assertEqual(set(lumps[8]), {12})
        leafs = list(struct.iter_unpack('<2i6h2H4B', lumps[10]))
        self.assertEqual(sorted(lf[0] for lf in leafs), [-3, -2, -1])   # water, solid ground, air
        self.assertEqual(info['tree'].leaves, [-2, -1, -3])

    def test_chunk_edges_must_lie_on_the_tile_grid(self):
        with self.assertRaisesRegex(ValueError, 'tile grid'):
            chunk_terrain((0, 0, 200, 256), 128, lambda x, y: 0, lambda x, y: 1, -1024, lambda m: 0, 1)


class ChimLayoutTests(unittest.TestCase):
    def test_hilbert_order_steps_to_a_neighbour(self):
        order = F.spatial_order(8, 8)
        self.assertEqual(sorted(order), [(x, y) for x in range(8) for y in range(8)])
        for a, b in zip(order, order[1:]):
            self.assertEqual(abs(a[0] - b[0]) + abs(a[1] - b[1]), 1)
        self.assertEqual(len(F.spatial_order(24, 24)), 576)

    def test_record_sizes(self):
        self.assertEqual(F.HEADER.size, 32)
        self.assertEqual(F.PLACEMENT.size, 48)
        self.assertEqual(F.CHUNK_HEAD.size, 24)
        self.assertEqual(F.CHUNK_ENTRY.size, 28)
        self.assertEqual(F.MODEL_DIR.size, 24)
        self.assertEqual(F.TEXTURE_DIR.size, 24)
        self.assertEqual(F.FILE_ENTRY.size, 60)
        self.assertEqual(F.FRAME_BLOCK.size, 32)
        self.assertEqual(F.SETTINGS.size, 40)
        self.assertEqual(F.INDEX_TOC.size, 32)
        self.assertEqual(F.SECTOR_ENTRY.size, 12)
        self.assertEqual(F.RECORD_ENTRY.size, 16)

    def test_sector_order_keeps_each_sector_together(self):
        chunks, sectors = F.sector_order(24, 24, 3)
        self.assertEqual(len(sectors), 64)
        self.assertEqual(sorted(chunks), [(x, y) for x in range(24) for y in range(24)])
        for k, (sx, sy) in enumerate(sectors):
            block = chunks[9 * k:9 * k + 9]
            self.assertEqual({(x // 3, y // 3) for x, y in block}, {(sx, sy)})
        self.assertEqual(sectors, F.spatial_order(8, 8))
        with self.assertRaisesRegex(ValueError, 'divide'):
            F.sector_order(24, 24, 5)

    def test_sector_file_records_tile_the_file(self):
        blob = F.sector_file([(b'CHNK', 0, b'abcde'), (b'MODL', 7, b'xy')])
        recs = F.read_sector(blob)
        self.assertEqual([(r['kind'], r['id'], r['data']) for r in recs], [(b'CHNK', 0, b'abcde'), (b'MODL', 7, b'xy')])
        self.assertEqual(recs[1]['offset'], recs[0]['offset'] + 8)
        longer = bytearray(blob + bytes(4))
        struct.pack_into('>I', longer, 28, len(longer))
        with self.assertRaisesRegex(ValueError, 'after its last record'):
            F.read_sector(bytes(longer))

    def test_brush_image_puts_collision_last_and_loads_back(self):
        lumps = [bytearray() for _ in range(15)]
        lumps[9] = bytearray(struct.pack('<iHH', 0, 65535, 65534))
        lumps[1] = bytearray(struct.pack('<4fi', 0, 0, 1, 0, 3))
        image, render = F.brush_image(lumps)
        self.assertEqual(F.read_brush_image(image)[9], bytes(lumps[9]))
        self.assertEqual(F.render_extent(image), render)
        self.assertEqual(struct.unpack_from('<i', image, 4 + 8 * 9)[0], render)

    def test_big_endian_header(self):
        data = F.header(b'FRAM', 3, 32, 64, 64)
        self.assertEqual(data[:8], b'CHIMFRAM')
        self.assertEqual(struct.unpack_from('>HH', data, 8), FORMAT_VERSION)
        with self.assertRaisesRegex(ValueError, 'Expected a CHIM SECT'):
            F.read_header(data + bytes(32), b'SECT')


def legacy_model(root, surfaces, corners, texsize=64, parts=None):
    """One placement of a model through the legacy region assembly (prepare_mesh_bsp.append_meshes);
    parts: its collision pieces [(points, hull, ids, error)] (default: one piece, the corners)."""
    from player_hull import pack_lumps
    from prepare_mesh_bsp import append_meshes
    polys = [(q, 0, ax / texsize, off, n) for q, n, ax, off, _ in surfaces]
    data = (np.column_stack((corners * 4, np.zeros((len(corners), 2)))), np.array([[0, 1, 2, 0]]), polys,
            parts or [(corners, None, [], 0.)], {})
    ref = dict(number=1, model_index=0, scale=1, position=[0, 0, 0], rotation_radians=[0, 0, 0])
    model = dict(source='synthetic-box.nif', triangles=12, materials=[dict(texture_index=None, diffuse=[1, 1, 1])])
    (root / 'scenery-index.json').write_text(json.dumps(dict(models=[model], textures=[], references=[ref])))
    (root / 'scenery.mwpak').write_bytes(b'')
    (root / 'palette.lmp').write_bytes(bytes(range(256)) * 3)
    sections = [b''] * 15
    sections[0] = b'{\n"classname" "worldspawn"\n}\n\0'
    sections[2] = struct.pack('<i', 0)
    sections[3] = bytes(12)                       # as in a compiled map: vertex 0 and edge 0 exist
    sections[12] = struct.pack('<HH', 0, 0)
    sections[10] = (struct.pack('<2i6h2H4B', -2, -1, *[0] * 6, 0, 0, 0, 0, 0, 0)
                    + struct.pack('<2i6h2H4B', -1, -1, *[0] * 6, 0, 0, 0, 0, 0, 0))
    sections[14] = bytes(64)
    (root / 'base.bsp').write_bytes(pack_lumps(sections))
    append_meshes(root / 'base.bsp', root / 'out.bsp', root, root / 'palette.lmp', centre=(0, 0), jobs=1,
                  references=[1], prepared_models={0: data})
    raw = (root / 'out.bsp').read_bytes()
    lumps = [raw[o:o + n] for o, n in struct.iter_unpack('<ii', raw[4:124])]
    d = struct.unpack_from('<9f7i', lumps[14], 64)
    return {'lumps': lumps, 'first': d[14], 'num': d[15], 'lo': list(d[0:3]), 'hi': list(d[3:6]), 'clip0': d[10]}


def polygons(m):
    """Face points, plane and texture vectors of a model's faces, independent of record indices."""
    lumps = m['lumps']
    verts = list(struct.iter_unpack('<3f', lumps[3]))
    edges = list(struct.iter_unpack('<HH', lumps[12]))
    surfedges = [v[0] for v in struct.iter_unpack('<i', lumps[13])]
    out = []
    for f in list(struct.iter_unpack('<HhihH4Bi', lumps[7]))[m['first']:m['first'] + m['num']]:
        pts = [tuple(round(c, 4) for c in verts[edges[e][0] if e >= 0 else edges[-e][1]])
               for e in surfedges[f[2]:f[2] + f[3]]]
        plane = tuple(round(v, 4) for v in struct.unpack_from('<4f', lumps[1], 20 * f[0]))
        tex = tuple(round(v, 4) for v in struct.unpack_from('<8f', lumps[6], 40 * f[4]))
        out.append((pts, plane, f[1], tex, struct.unpack_from('<i', lumps[6], 40 * f[4] + 32)[0], f[5:10]))
    return out


def hull(m):
    lumps, base = m['lumps'], m['clip0']
    rel = lambda c: c - base if c < 0xFFF0 else c  # noqa: E731
    return [(tuple(round(v, 4) for v in struct.unpack_from('<4f', lumps[1], 20 * p)), rel(a), rel(b))
            for p, a, b in list(struct.iter_unpack('<iHH', lumps[9]))[base:]]


class ChimLegacyParityTests(unittest.TestCase):
    """The CHIM model writer and the legacy region assembly emit the same records."""

    def test_same_faces_texinfo_and_hull_as_append_meshes(self):
        surfaces, corners = box_surfaces(16, 32)
        with tempfile.TemporaryDirectory() as directory:
            legacy = legacy_model(Path(directory), surfaces, corners)
        chim, keys = model_image_lumps(surfaces, [(corners, None, [], 0.)], legacy['lo'], legacy['hi'], lambda m: 7)
        self.assertEqual(keys, [7])
        mine = {'lumps': [bytes(x) for x in chim], 'first': 0, 'num': 6, 'clip0': 0}
        self.assertEqual(polygons(mine), polygons(legacy))
        self.assertEqual(hull(mine), hull(legacy))
        self.assertEqual(F.read_texture_refs(chim[2]), [7])

    def test_same_texture_pixels_as_append_meshes(self):
        from PIL import Image
        from chim.models import material_texture_image
        from prepare_quake import miptex
        surfaces, corners = box_surfaces(16, 32)
        with tempfile.TemporaryDirectory() as directory:
            legacy = legacy_model(Path(directory), surfaces, corners)
        tex = legacy['lumps'][2]
        offset = struct.unpack_from('<i', tex, 4)[0]
        legacy_pixels = tex[offset + 40:]
        pal = Image.new('P', (1, 1))
        pal.putpalette(bytes(range(256)) * 3)
        model = dict(source='synthetic-box.nif', materials=[dict(texture_index=None, diffuse=[1, 1, 1])])
        im = material_texture_image(None, {}, model, 0, 64, pal)
        self.assertEqual(miptex('surface0', im)[40:], legacy_pixels)


if __name__ == '__main__':
    unittest.main()
