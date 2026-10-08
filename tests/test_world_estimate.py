# SPDX-License-Identifier: GPL-3.0-only
"""World estimate (tools/world_estimate*.py) on fictional fixtures generated at
test time: a synthetic master with invented cells and objects, a synthetic BSA
and box meshes written with the repository's NIF library. No game data."""
import contextlib
import csv
import io
import json
import re
import struct
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import numpy as np  # noqa: E402
import world_estimate as W  # noqa: E402
import world_estimate_data as D  # noqa: E402
import world_estimate_model as M  # noqa: E402
import world_estimate_sample as V  # noqa: E402


def sub(tag, value):
    return struct.pack('<4sI', tag.encode(), len(value)) + value


def record(tag, value, flags=0):
    return struct.pack('<4sIII', tag.encode(), len(value), 0, flags) + value


def zstr(text):
    return text.encode('cp1252') + b'\0'


def box_nif(size=64.0, height=64.0):
    """A closed box mesh (12 triangles) with UVs, written by the converter's NIF library."""
    from prepare_scenery import nif_reader
    N = nif_reader()
    d = N.Data(version=0x04000002)
    root = N.NiNode()
    root.name = b'Root'
    shape = N.NiTriShape()
    shape.name = b'Box'
    data = N.NiTriShapeData()
    V8 = [(0, 0, 0), (size, 0, 0), (size, size, 0), (0, size, 0),
          (0, 0, height), (size, 0, height), (size, size, height), (0, size, height)]
    T = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
         (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    data.num_vertices = len(V8)
    data.has_vertices = True
    data.vertices.update_size()
    for v, p in zip(data.vertices, V8):
        v.x, v.y, v.z = p
    data.num_uv_sets = 1
    data.has_uv = True
    data.uv_sets.update_size()
    for uv, p in zip(data.uv_sets[0], V8):
        uv.u, uv.v = p[0] / size, (p[1] + p[2]) / size
    data.num_triangles = len(T)
    data.num_triangle_points = 3 * len(T)
    data.has_triangles = True
    data.triangles.update_size()
    for t, p in zip(data.triangles, T):
        t.v_1, t.v_2, t.v_3 = p
    shape.data = data
    root.num_children = 1
    root.children.update_size()
    root.children[0] = shape
    d.roots = [root]
    stream = io.BytesIO()
    d.write(stream)
    return stream.getvalue()


def bsa(files):
    """Minimal TES3 BSA: {path: bytes}."""
    names = list(files)
    blob = b''.join(n.encode() + b'\0' for n in names)
    offsets, pos = [], 0
    for n in names:
        offsets.append(pos)
        pos += len(n) + 1
    table, data, at = b'', b'', 0
    for n in names:
        table += struct.pack('<II', len(files[n]), at)
        data += files[n]
        at += len(files[n])
    directory = table + b''.join(struct.pack('<I', o) for o in offsets) + blob
    return struct.pack('<III', 0x100, len(directory), len(names)) + directory + bytes(8 * len(names)) + data


def ref(number, ident, pos, scale=None, door_to=None):
    out = sub('FRMR', struct.pack('<I', number)) + sub('NAME', zstr(ident))
    if scale is not None:
        out += sub('XSCL', struct.pack('<f', scale))
    if door_to is not None:
        out += sub('DODT', struct.pack('<6f', 0, 0, 0, 0, 0, 0)) + sub('DNAM', zstr(door_to))
    return out + sub('DATA', struct.pack('<6f', *pos, 0.0, 0.0, 0.5))


def cell(name, flags, x, y, refs, region=b''):
    body = sub('NAME', zstr(name)) + sub('DATA', struct.pack('<Iii', flags, x, y))
    if region:
        body += sub('RGNN', region)
    return record('CELL', body + b''.join(refs))


def land(x, y, height=10.0):
    return record('LAND', sub('INTV', struct.pack('<ii', x, y)) + sub('DATA', struct.pack('<I', 1)) +
                  sub('VHGT', struct.pack('<f4225b3x', height, *([0] * 4225))))


def synthetic_install(path):
    """Invented master: two reachable rooms, one unreachable room, a two-cell town."""
    path.mkdir()
    objects = [record('STAT', sub('NAME', zstr('fx_box')) + sub('MODL', zstr('x\\fx_box.nif'))),
               record('STAT', sub('NAME', zstr('fx_wall')) + sub('MODL', zstr('i\\fx_wall.nif'))),
               record('STAT', sub('NAME', zstr('fx_post')) + sub('MODL', zstr('x\\fx_postmarker.nif'))),
               record('DOOR', sub('NAME', zstr('fx_door')) + sub('MODL', zstr('d\\fx_door.nif'))),
               record('MISC', sub('NAME', zstr('fx_item')) + sub('MODL', zstr('m\\fx_item.nif'))),
               record('LIGH', sub('NAME', zstr('fx_lantern')) + sub('MODL', zstr('l\\fx_lantern.nif')) +
                      sub('LHDT', struct.pack('<fiiI4BI', 1.0, 1, -1, 128, 255, 200, 100, 0, 0x8))),
               record('NPC_', sub('NAME', zstr('fx_person'))),
               record('CREA', sub('NAME', zstr('fx_beast')))]
    room_a = [ref(1, 'fx_wall', (0, 0, 0)), ref(2, 'fx_wall', (256, 0, 0)), ref(3, 'fx_wall', (512, 0, 0), 1.5),
              ref(4, 'fx_lantern', (64, 64, 64)), ref(5, 'fx_person', (32, 32, 0)), ref(6, 'fx_item', (16, 0, 0)),
              ref(7, 'fx_door', (600, 0, 0), door_to='Fixture Room B')]
    room_b = [ref(8, 'fx_box', (0, 0, 0)), ref(9, 'fx_door', (100, 0, 0), door_to='Fixture Room A'),
              ref(10, 'fx_beast', (20, 0, 0))]
    lonely = [ref(11, 'fx_box', (0, 0, 0))]
    town0 = [ref(12, 'fx_box', (1000, 1000, 0)), ref(13, 'fx_box', (2000, 1000, 0), 2.0),
             ref(14, 'fx_lantern', (3000, 3000, 50)), ref(18, 'fx_post', (1500, 1500, 0)),
             ref(15, 'fx_door', (4000, 4000, 0), door_to='Fixture Room A')]
    town1 = [ref(16, 'fx_box', (9000, 1000, 0)), ref(17, 'fx_person', (9100, 1100, 0))]
    cells = [cell('Fixture Room A', 1, 0, 0, room_a), cell('Fixture Room B', 1, 0, 0, room_b),
             cell('Fixture Lonely Room', 1, 0, 0, lonely),
             cell('Fixture Script Room', 1, 0, 0, [ref(19, 'fx_box', (0, 0, 0)),
                                                   ref(20, 'fx_door', (50, 0, 0), door_to='Fixture Inner Room')]),
             cell('Fixture Inner Room', 1, 0, 0, [ref(21, 'fx_box', (0, 0, 0))]),
             cell('Fixtown', 0, 0, 0, town0), cell('Fixtown', 0, 1, 0, town1)]
    # A script moves the player into the script room (seeds reachability); its door leads on.
    script = record('SCPT', sub('SCHD', bytes(52)) + sub('SCTX', b'Begin fx_travel\nPlayer->PositionCell 0 0 0 0 '
                                                         b'"Fixture Script Room"\nEnd\n'))
    body = objects + [script] + cells + [land(0, 0), land(1, 0, 1100.0)]   # cell 1,0 rises above the frame ceiling
    head = struct.pack('<fI32s256sI', 1.3, 1, b'Synthetic fixture', b'World estimate test', len(body))
    (path / 'Morrowind.esm').write_bytes(record('TES3', sub('HEDR', head)) + b''.join(body))
    files = {'meshes\\x\\fx_box.nif': box_nif(64, 64), 'meshes\\i\\fx_wall.nif': box_nif(256, 128),
             'meshes\\d\\fx_door.nif': box_nif(32, 96), 'meshes\\m\\fx_item.nif': box_nif(8, 8),
             'meshes\\l\\fx_lantern.nif': box_nif(16, 24), 'meshes\\x\\fx_postmarker.nif': box_nif(8, 64)}
    (path / 'Morrowind.bsa').write_bytes(bsa(files))
    return path


def quiet(fn, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()) as out:
        result = fn(*args, **kwargs)
    return result, out.getvalue()


class Fixture:
    tmp = None

    @classmethod
    def data(cls):
        if cls.tmp is None:
            cls.tmp = tempfile.TemporaryDirectory()
            synthetic_install(Path(cls.tmp.name) / 'Data Files')
        return Path(cls.tmp.name) / 'Data Files'


def tearDownModule():
    if Fixture.tmp is not None:
        Fixture.tmp.cleanup()


class CensusAndMeshTests(unittest.TestCase):
    def test_census_reads_cells_references_and_land(self):
        masters = D.census(Fixture.data())
        m = masters['Morrowind.esm']
        self.assertEqual(sum(c['interior'] for c in m['cells']), 5)
        self.assertEqual(sum(not c['interior'] for c in m['cells']), 2)
        self.assertEqual(len(m['lands']), 2)
        room = next(c for c in m['cells'] if c['name'] == 'Fixture Room A')
        self.assertEqual(len(room['refs']), 7)
        self.assertAlmostEqual(next(r for r in room['refs'] if r['n'] == 3)['s'], 1.5)
        self.assertEqual(m['objects']['fx_lantern']['lflags'], 0x8)
        self.assertEqual(D.reachable_interiors(masters), {'fixture room a', 'fixture room b', 'fixture script room',
                                                          'fixture inner room'})
        self.assertEqual(D.used_meshes(masters)['meshes/x/fx_box.nif'], 7)

    def test_box_costs_follow_the_converter(self):
        masters = D.census(Fixture.data())
        rows = D.scan_meshes(Fixture.data(), sorted(D.used_meshes(masters)), jobs=1)
        box = rows['meshes/x/fx_box.nif']
        self.assertEqual(box['status'], 'ok')
        self.assertEqual(box['tris'], 12)
        for space in ('interior', 'exterior'):
            c = box['costs'][space]
            self.assertEqual(c['faces'], 6)          # coplanar triangle pairs merge into one face each
            self.assertEqual(c['nodes'], 6)          # one convex collision piece, six point-hull planes
            self.assertEqual(c['clipnodes'], 6)      # standing-box planes of an axial box stay six
            self.assertGreater(c['luxels'], 0)
            self.assertLessEqual(c['max_extent'], 256)
        # A wide interior kit surface is split at the 240-texel converter bound.
        wall = rows['meshes/i/fx_wall.nif']['costs']['interior']
        self.assertGreaterEqual(wall['faces'], 6)

    def test_scan_cache_is_reused_and_invalidated_by_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / 'meshes.json'
            names = ['meshes/x/fx_box.nif']
            first = D.scan_meshes(Fixture.data(), names, cache, jobs=1)
            stored = json.loads(cache.read_text())
            stored['meshes/x/fx_box.nif']['tris'] = 999          # cached rows are trusted while the hash matches
            cache.write_text(json.dumps(stored))
            self.assertEqual(D.scan_meshes(Fixture.data(), names, cache, jobs=1)['meshes/x/fx_box.nif']['tris'], 999)
            stored['meshes/x/fx_box.nif']['sha256'] = '0' * 64   # a different file is scanned again
            cache.write_text(json.dumps(stored))
            self.assertEqual(D.scan_meshes(Fixture.data(), names, cache, jobs=1), first)

    def test_frame_grid_follows_the_anchor(self):
        masters = D.census(Fixture.data())
        world = D.World(masters, 'Morrowind.esm', {})
        frames = D.world_frames(world, 'w', (0, 2))
        self.assertTrue(frames)
        for fid, (fx, fy) in frames:
            self.assertEqual((fx % 3, fy % 3), (0, 2))
            self.assertEqual(fid, 'w%+03d%+03d' % (fx, fy))
        covered = {(fx + dx, fy + dy) for _, (fx, fy) in frames for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
        self.assertTrue({(0, 0), (1, 0)} <= covered)


class LimitAndModelTests(unittest.TestCase):
    def test_limits_come_from_the_engine_sources(self):
        limits = W.engine_limits()
        quakedef = (ROOT / 'engine/aga/src/quakedef.h').read_text()
        self.assertEqual(limits['max_edicts'], int(re.search(r'#define\s+MAX_EDICTS\s+(\d+)', quakedef).group(1)))
        self.assertEqual(limits['static_flames'], 128)
        self.assertEqual(limits['lamp_cache_3x3'], 256)
        self.assertEqual(limits['texinfo'], 32767)
        self.assertEqual(W.engine_limits(65535)['texinfo'], 65535)
        self.assertEqual(limits['heap_allowed_peak'], limits['heap_budget'] - limits['heap_fixed'])
        with self.assertRaises(ValueError):
            W.engine_limits(4096)

    def test_shipped_model_is_generic_and_complete(self):
        model = M.load_model()
        text = M.DEFAULT_MODEL.read_text()
        self.assertNotIn('.nif', text.lower())
        self.assertNotIn('meshes/', text.lower())
        for space in M.SPACES:
            for t in M.TARGETS:
                self.assertTrue(all(v >= 0 for v in model['coefficients'][space][t]))
        self.assertIn('finish_cpu_seconds', model['timing'])

    def test_fit_recovers_known_coefficients(self):
        rng = np.random.default_rng(7)
        meshes = {}
        for k in range(30):
            c = {key: float(rng.integers(5, 400)) for key in M.COST_KEYS}
            c['max_extent'] = 128.0
            meshes['m%d' % k] = {'status': 'ok', 'tris': 50, 'costs': {'interior': c, 'exterior': c}}
        ratios = M.fallback_ratios(meshes)
        true = {}
        for space in M.SPACES:
            true[space] = {t: [float(rng.uniform(1, 50))] + [float(rng.uniform(0, 3)) for _ in M.XCOLS[t]]
                           for t in M.TARGETS}
            true[space]['heap_raw'] = [5e6] + [float(rng.uniform(0, 40)) for _ in M.HEAP_LUMPS]
        pairs = []
        for i in range(60):
            space = M.SPACES[i % 2]
            names = rng.choice(list(meshes), size=int(rng.integers(3, 12)), replace=False)
            f = {'map': 'x%03d' % i, 'space': space, 'cur_variants': [[n, int(rng.integers(1, 5))] for n in names],
                 'cur_textures': int(rng.integers(1, 40)), 'cur_flames': int(rng.integers(0, 5)),
                 'cov_area': float(rng.uniform(1e6, 3e6)) if space == 'exterior' else 0,
                 'land_frac_cov': float(rng.uniform(0, 1))}
            s = M.map_sums(meshes, ratios, f, 'cur')
            bsp = {t: M.dot(M.xrow(s, M.XCOLS[t]), true[space][t]) for t in M.TARGETS}
            heap = M.dot([1.0] + [bsp[k] for k in M.HEAP_LUMPS], true[space]['heap_raw'])
            pairs.append((f, {'bsp': bsp, 'heap_raw': heap, 'heap_final': heap}))
        coeff = M.fit(pairs, meshes, ratios)
        model = {'coefficients': coeff}
        for f, m in pairs:
            p, _ = M.predict(model, meshes, ratios, f, 'cur')
            self.assertAlmostEqual(p['faces'] / m['bsp']['faces'], 1.0, places=3)
            self.assertAlmostEqual(p['heap_raw'] / m['heap_raw'], 1.0, places=3)
        cv, rows = M.cross_validate(pairs, meshes, ratios)
        self.assertLess(cv['interior']['heap']['median_abs_pct'], 0.5)
        self.assertEqual(len(rows), len(pairs))

    def test_bsp_lumps_counts_records(self):
        lumps = [b'{\n"classname" "worldspawn"\n}\n{\n"classname" "func_wall"\n}\n', bytes(20 * 3), b'\0' * 4,
                 bytes(12 * 5), b'', bytes(24 * 2), bytes(40 * 4), bytes(20 * 7), bytes(100), bytes(8 * 9),
                 bytes(28 * 2), bytes(2 * 3), bytes(4 * 6), bytes(4 * 10), bytes(64)]
        raw, off = bytearray(struct.pack('<i', 29) + bytes(120)), 124
        for k, lump in enumerate(lumps):
            struct.pack_into('<ii', raw, 4 + 8 * k, off, len(lump))
            raw += lump
            off += len(lump)
        row = V.bsp_lumps(bytes(raw))
        self.assertEqual((row['planes'], row['vertexes'], row['nodes'], row['texinfo'], row['faces']), (3, 5, 2, 4, 7))
        self.assertEqual((row['clipnodes'], row['leafs'], row['models'], row['lighting_bytes']), (9, 2, 1, 100))
        self.assertEqual(row['func_walls'], 1)
        with self.assertRaises(ValueError):
            V.bsp_lumps(b'IBSP' + bytes(200))
        self.assertEqual(len(V.generic_palette()), 768)


class EstimateCommandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / 'estimate'
        cls.code, cls.log = quiet(W.main, ['estimate', '--data-files', str(Fixture.data()), '--out', str(cls.out),
                                           '--jobs', '1', '--frame-anchor', '0', '2'])
        with (cls.out / 'metrics.csv').open(newline='') as fh:
            cls.rows = list(csv.DictReader(fh))
        cls.summary = json.loads((cls.out / 'summary.json').read_text())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_outputs_and_columns(self):
        self.assertEqual(self.code, 0)
        with (self.out / 'metrics.csv').open(newline='') as fh:
            header = next(csv.reader(fh))
        self.assertEqual(header, list(W.COLUMNS))
        doc = json.loads((self.out / 'metrics.json').read_text())
        self.assertEqual(doc['format'], W.OUTPUT_FORMAT)
        self.assertEqual(len(doc['rows']), len(self.rows))
        self.assertEqual(doc['limits']['texinfo'], 32767)
        raw = (self.out / 'metrics.csv').read_bytes()
        self.assertNotIn(b'\r', raw)

    def test_interiors_exclusion_and_scenarios(self):
        names = {r['name'] for r in self.rows if r['space'] == 'interior'}
        self.assertEqual(names, {'Fixture Room A', 'Fixture Room B', 'Fixture Script Room', 'Fixture Inner Room'})
        self.assertEqual(self.summary['excluded_interiors'],
                         [['fixture lonely room', 'unreachable: no door chain from the world or a script']])
        room = next(r for r in self.rows if r['name'] == 'Fixture Room A')
        self.assertEqual(int(room['npc']), 1)
        self.assertEqual(int(room['lights']), 1)
        self.assertEqual(int(room['cur_refs_geometry']), 5)    # walls, lantern, door; item and actor deferred
        self.assertEqual(int(room['evr_refs_geometry']), 6)    # the item becomes geometry too
        self.assertEqual(int(room['evr_edicts']), 2 + 6 + 1)
        self.assertEqual(int(room['cur_inline_models']) >= 1, True)
        self.assertIn(room['evr_pass'], ('yes', 'no'))

    def test_exterior_regions_and_core_counts(self):
        ext = [r for r in self.rows if r['space'] == 'exterior']
        self.assertTrue(ext)
        self.assertTrue(all(re.fullmatch(r'w[+-]\d\d[+-]\d\d\d{3}', r['map']) for r in ext))
        self.assertEqual(sum(int(r['core_refs_total']) for r in ext), 7)
        self.assertEqual(sum(int(r['core_npc']) for r in ext), 1)
        built = [r for r in ext if r['buildable'] == 'yes']
        self.assertTrue(built)
        self.assertTrue(all(float(r['evr_heap']) > 0 for r in built))
        self.assertEqual(self.summary['vvardenfell']['interiors'], 4)

    def test_everything_is_never_below_current(self):
        # ESTIMATE-EVR-BELOW-CUR-31: a mesh whose name contains 'marker' is kept by the
        # exterior converter; the 'evr' scenario must keep it too, so no metric drops.
        post = [r for r in self.rows if r['space'] == 'exterior' and int(r['cur_refs_geometry'])
                and r['buildable'] == 'yes']
        self.assertTrue(post)
        for r in self.rows:
            for key in [k[4:] for k in r if k.startswith('cur_') and not k.startswith('cur_ratio_')
                        and k not in ('cur_fails', 'cur_pass')]:
                self.assertGreaterEqual(float(r['evr_' + key]), float(r['cur_' + key]), (r['map'], key))

    def test_ground_above_the_frame_ceiling_fails(self):
        ext = [r for r in self.rows if r['space'] == 'exterior' and r['terrain_max_q']]
        high = [r for r in ext if float(r['terrain_max_q']) > W.engine_limits()['terrain_ceiling']]
        low = [r for r in ext if float(r['terrain_max_q']) < 100]
        self.assertTrue(high and low)
        for r in high:
            self.assertGreater(float(r['evr_ratio_terrain_ceiling']), 1)
            self.assertIn('terrain_ceiling', r['evr_fails'].split())
        for r in low:
            self.assertNotIn('terrain_ceiling', r['evr_fails'].split())

    def test_charts_are_valid_svg_with_town_label_from_data(self):
        for name in ('heap-vs-budget.svg', 'faces-vs-limits.svg', 'entities-vs-max-edicts.svg', 'limits-failing.svg',
                     'world-heat-map.svg'):
            ET.parse(self.out / 'charts' / name)
        heat = (self.out / 'charts/world-heat-map.svg').read_text()
        self.assertIn('Fixtown', heat)

    def test_exclusion_modes_and_scenario_choice(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'all'
            quiet(W.main, ['estimate', '--data-files', str(Fixture.data()), '--out', str(out), '--jobs', '1',
                           '--exclude', 'none', '--scenario', 'cur', '--no-charts'])
            with (out / 'metrics.csv').open(newline='') as fh:
                reader = csv.DictReader(fh)
                rows = list(reader)
                self.assertFalse(any(c.startswith('evr_') for c in reader.fieldnames))
            self.assertIn('Fixture Lonely Room', {r['name'] for r in rows})
            config = Path(tmp) / 'config.json'
            doc = W.load_config()
            doc['exclusion']['include_cells'] = ['FIXTURE LONELY ROOM']
            doc['exclusion']['exclude_cells'] = ['Fixture Room B']
            config.write_text(json.dumps(doc))
            masters = D.census(Fixture.data())
            self.assertEqual(W.exclusion(W.load_config(config), masters, 'default'),
                             {'fixture room b': 'listed in exclude_cells'})
            self.assertEqual(W.exclusion(W.load_config(config), masters, 'none'), {})

    def test_builder_exposes_the_command(self):
        import build_aga
        with tempfile.TemporaryDirectory() as tmp:
            from unittest import mock
            argv = ['build_aga.py', 'estimate', '--data-files', str(Fixture.data()), '--out', tmp,
                    '--jobs', '1', '--no-charts', '--scenario', 'evr']
            with mock.patch.object(sys, 'argv', argv):
                code, _ = quiet(build_aga.main)
            self.assertEqual(code, 0)
            self.assertTrue((Path(tmp) / 'metrics.csv').is_file())
        import build
        args = build.parser().parse_args(['--data-files', str(Fixture.data()), '--estimate-world', 'x',
                                          '--estimate-sample', '4'])
        self.assertEqual((args.estimate_world, args.estimate_sample), (Path('x'), 4))

    def test_calibrate_refits_from_measured_maps(self):
        rng = np.random.default_rng(3)
        measured = []
        built = [r for r in self.rows if r['buildable'] == 'yes']
        for r in [r for r in built if r['space'] == 'interior'] + [r for r in built if r['space'] == 'exterior'][:6]:
            bsp = {t: float(rng.integers(100, 5000)) for t in M.TARGETS}
            fid = r['frame'] or None
            measured.append({'map': r['map'], 'space': r['space'], 'cell': r['name'] if r['space'] == 'interior' else None,
                             'frame': fid, 'centre_cell': [int(fid[1:4]), int(fid[4:7])] if fid else None,
                             'bsp': bsp, 'heap_raw': 6e6 + sum(bsp.values()), 'heap_final': 5.9e6 + sum(bsp.values()),
                             'final_bsp_bytes': bsp['bsp_bytes'], 'seconds': 3.0})
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / 'run'
            (src / 'validation').mkdir(parents=True)
            (src / 'validation/results.json').write_text(json.dumps({'measured': measured}))
            target = Path(tmp) / 'model.json'
            code, log = quiet(W.main, ['calibrate', '--data-files', str(Fixture.data()), '--from', str(src),
                                       '--model-out', str(target), '--work', str(Path(tmp) / 'work'), '--jobs', '1'])
            self.assertEqual(code, 0)
            model = M.load_model(target)
            self.assertEqual(model['calibration']['maps'], {'interior': 4, 'exterior': 6})
            self.assertEqual(model['timing'], M.load_model()['timing'])

    def test_sample_selection_is_stratified_and_deterministic(self):
        masters = D.census(Fixture.data())
        preds = []
        for i in range(10):
            preds.append({'map': 'i%04d' % i, 'set': 'vvardenfell', 'space': 'interior', 'cell': 'c%d' % i,
                          'cur_refs': 1, 'cur': {'faces': 10, 'heap_final': 1000 * i}})
            preds.append({'map': 'w+00+00%03d' % i, 'set': 'vvardenfell', 'space': 'exterior', 'frame': 'w+00+00',
                          'centre_cell': [0, 0], 'cur_refs': 1, 'cur': {'faces': 10, 'heap_final': 500 * i}})
        # Exterior frames need LAND under all 3x3 cells; the fixture has two, so only interiors qualify.
        pick = V.select(preds, 4, masters)
        self.assertEqual([p['map'] for p in pick], [p['map'] for p in V.select(preds, 4, masters)])
        self.assertEqual(len(pick), 2)
        heaps = [p['cur']['heap_final'] for p in pick]
        self.assertEqual(heaps, sorted(heaps))


if __name__ == '__main__':
    unittest.main()
