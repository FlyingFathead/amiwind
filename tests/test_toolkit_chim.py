# SPDX-License-Identifier: GPL-3.0-only
"""The Toolkit's CHIM reader (amiwind-toolkit/chim-reader.js) against the builder's own reader and heap gate.

One reader: the 3D Map Inspector's CHIM code is a port of tools/chim/format.py and of the heap gate's ring
model (tools/chim/heap.py). On synthetic worlds built by tools/chim (terrain stored in the chunks, and terrain
references, format 0.7) the JavaScript reader must give the same records, byte counts, zone block sizes and
ring scan as Python, read a CHIM map (.chim) through its own reader, and the page must accept .chim files.
Synthetic data only; DOM and WebGL are stubbed (no GPU claim)."""
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import format as F  # noqa: E402
from chim import heap  # noqa: E402
from chim.frame_map import empty_world, entity_text  # noqa: E402
from chim.validate import validate  # noqa: E402

PAGE = ROOT / 'amiwind-toolkit' / 'map-inspector.html'
READER = ROOT / 'amiwind-toolkit' / 'chim-reader.js'
DRIVER = ROOT / 'tests' / 'test_toolkit_chim.js'
# The heap gate's test sizes (tests/test_chim_heap.py): illustrative 68k sizes; the build probes the real ones.
SIZES = {'pointer': 4, 'short': 2, 'int': 4, 'hunk': 16, 'dvertex': 12, 'dedge': 4, 'dplane': 20, 'dnode': 24,
         'dclipnode': 8, 'clipnode': 8, 'dleaf': 28, 'texinfo': 40, 'dface': 20, 'dmodel': 64, 'mvertex': 12,
         'medge': 8, 'mplane': 20, 'mtexinfo': 52, 'msurface': 68, 'mnode': 40, 'mleaf': 48, 'texture': 100,
         'entity': 400, 'scenery': 120, 'model': 300}


def node():
    return shutil.which('node')


def run(*args):
    r = subprocess.run([node(), str(DRIVER), *map(str, args)], capture_output=True, text=True, timeout=120)
    if r.returncode:
        raise AssertionError(r.stdout + r.stderr)
    return json.loads(r.stdout)


def faces(image):
    """Faces of a brush image's model 0 (the range the inspector draws)."""
    lumps = F.read_brush_image(image)
    return struct.unpack_from('<i', lumps[14], 60)[0] if len(lumps[14]) >= 64 else len(lumps[7]) // 20


def python_frames(out):
    """Per frame, what the Toolkit must report: counts and bytes (chim.validate.load_world) and the gate's ring."""
    fails, world = validate(str(out))
    assert not fails, fails
    ring = {f['frame']: f for f in heap.ring_peak(world, SIZES)['frames']}
    models, textures = world['models'], world['textures']
    result = {}
    for path, frame, chunks in world['frames']:
        used_m = sorted({r['model'] for c in chunks for r in c['owned'] + c['reach']})
        used_t = set()
        for c in chunks:
            used_t.update(F.read_texture_refs(F.read_brush_image(c['image'])[2]))
        for m in used_m:
            used_t.update(F.read_texture_refs(F.read_brush_image(models[m]['image'])[2]))
        r = ring[path]
        result[path] = {
            'chunks': len(chunks), 'owned': sum(len(c['owned']) for c in chunks),
            'reach': sum(len(c['reach']) for c in chunks),
            'chunk_record_bytes': sum(c['render'] + c['collision'] for c in chunks),
            'chunk_render_bytes': sum(c['render'] for c in chunks),
            'chunk_collision_bytes': sum(c['collision'] for c in chunks),
            'terrain_references': sum(1 for c in chunks if 'ref' in c),
            'models': len(used_m), 'model_bytes': sum(models[m]['bytes'] for m in used_m),
            'textures': len(used_t), 'texture_bytes': sum(textures[t]['bytes'] for t in used_t),
            'chunk_heap': [heap.image_bytes(F.read_brush_image(c['image']), SIZES) for c in chunks],
            'model_heap': [[m, heap.image_bytes(F.read_brush_image(models[m]['image']), SIZES, point_hull_only=True)] for m in used_m],
            'geometry': {'terrain_faces': sum(faces(c['image']) for c in chunks),
                         'placement_faces': sum(faces(models[r['model']]['image']) for c in chunks for r in c['owned'])},
            'scan': {'peak_bytes': r['peak_bytes'], 'peak_position': r['peak_position'], 'positions': r['positions'],
                     'positions_over_budget': r['positions_over_budget'], 'median_bytes': r['median_bytes'],
                     'budget_bytes': r['budget_bytes'], 'ring_chunks': r['ring_chunks'],
                     'ring_models': r['ring_models'], 'ring_textures': r['ring_textures']}}
    return result


def frame_map(path, cell=(0, 0), key=True):
    """A CHIM frame map as the image step writes it (chim.frame_map: empty world, entities, the frame key)."""
    world = {'classname': 'worldspawn', 'wad': 'gfx.wad'}
    if key:
        world['_chim_frame'] = '%d %d' % cell
    world['_chim_hunk_rest'] = '20256'
    rows = [world, {'classname': 'info_player_start', 'origin': '0 0 64'},
            {'classname': 'aw_npc', 'origin': '-120 40 8', 'aw_ref': '77'},
            {'classname': 'aw_static', 'origin': '64 -32 0', 'model': 'progs/x.mdl', '_chim_chunk': '3',
             '_chim_box': '40 -56 -24 88 -8 24'}]
    lumps = empty_world((-512.0, -512.0, -256.0), (512.0, 512.0, 2048.0))
    lumps[0] = entity_text(rows)
    Path(path).write_bytes(F.brush_image(lumps)[0])
    return rows


@unittest.skipUnless(node(), 'Node.js unavailable; the Toolkit CHIM checks need an existing interpreter')
class ToolkitChimReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from test_chim_format import fixture
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.worlds = {}
        for name, refs in (('copies', False), ('refs', True)):
            out = root / name
            fixture(out, settings={'grain': 256, 'sector_chunks': 2, **({'terrain_refs': 'on'} if refs else {})})
            heap.require_heap(out, sizes=SIZES)
            cls.worlds[name] = out
        cls.sizes = root / 'sizes.json'
        cls.sizes.write_text(json.dumps({'target_struct_sizes_bytes': SIZES}), encoding='utf-8')
        cls.map = root / 'town-chim.chim'
        cls.rows = frame_map(cls.map, cell=(-3, -2))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_world_reader_matches_the_python_reader_and_the_heap_gate(self):
        for name, out in self.worlds.items():
            want = python_frames(out)
            got = run('world', out, self.sizes)
            self.assertEqual(got['version'], [0, 7] if name == 'refs' else [0, 5], name)
            self.assertEqual(sorted(f['frame'] for f in got['loaded']), sorted(want), name)
            for f in got['loaded']:
                w = want[f['frame']]
                self.assertEqual(f['problems'], [], name)
                for k, v in w.items():
                    self.assertEqual(f[k], v, '%s %s %s' % (name, f['frame'], k))
                # the report the page reads (chim-heap.json) carries the same figures
                self.assertEqual(f['report']['peak_bytes'], w['scan']['peak_bytes'], name)
            if name == 'refs':
                self.assertTrue(all(f['terrain_references'] == f['chunks'] for f in got['loaded']))

    def test_a_zipped_world_reads_as_the_folder(self):
        import zipfile
        out = self.worlds['refs']
        archive = Path(self.tmp.name) / 'chim-world.zip'
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
            for f in sorted(out.rglob('*')):
                if f.is_file() and (f.name == 'chim-heap.json' or 'chim' in f.relative_to(out).parts[:1]):
                    z.write(f, 'chim-world/' + f.relative_to(out).as_posix())
        self.assertEqual(run('world', archive, self.sizes)['loaded'], run('world', out, self.sizes)['loaded'])

    def test_heap_report_parsing(self):
        out = self.worlds['copies']
        doc = json.loads((out / 'chim-heap.json').read_text(encoding='utf-8'))
        got = run('heap', out / 'chim-heap.json')
        self.assertEqual(got['active_radius'], doc['active_radius'])
        self.assertEqual(got['zone_kib'], doc['zone_kib'])
        self.assertEqual(got['frames'], [[f['frame'].replace('/frame.ccf', ''), f['peak_bytes'], f['budget_bytes'], f['ok']]
                                         for f in doc['frames']])
        self.assertEqual(got['over'], [f['frame'].replace('/frame.ccf', '') for f in doc['frames'] if not f['ok']])
        bad = Path(self.tmp.name) / 'not-run.json'
        bad.write_text(json.dumps({'ok': None, 'status': 'not run: no Amiga SDK given (--sdk)'}), encoding='utf-8')
        with self.assertRaisesRegex(AssertionError, 'did not run'):
            run('heap', bad)

    def test_chim_map_reader(self):
        got = run('map', self.map)
        self.assertEqual(got['format'], 'chim-map')
        self.assertEqual(got['version'], 29)
        self.assertEqual(got['faces'], 0)
        self.assertEqual(got['tail_bytes'], 0)
        self.assertEqual(got['frame_key'], '-3 -2')
        self.assertEqual(got['frame_path'], 'frames/x-03/y-02')
        self.assertEqual(got['classnames'], [r['classname'] for r in self.rows])
        self.assertTrue(got['is_frame_map'])
        plain = Path(self.tmp.name) / 'plain.bsp'
        frame_map(plain, key=False)
        self.assertFalse(run('map', plain)['is_frame_map'])        # a frame map is told by its key, never its name
        broken = Path(self.tmp.name) / 'broken.chim'
        broken.write_bytes(struct.pack('<i', 30) + bytes(200))
        with self.assertRaisesRegex(AssertionError, 'not known to this reader'):
            run('map', broken)

    def test_inspector_page_opens_chim_maps_and_worlds(self):
        out = self.worlds['refs']
        got = run('page', PAGE, out, self.sizes, 'frames/x+00/y+00', self.map)
        self.assertIn('names CHIM frame -3 -2', got['map']['hint'])
        self.assertIn('its geometry lives in the CHIM world', got['map']['hint'])
        self.assertEqual(len(got['map']['objects']), len(self.rows))      # frame bounds + every point entity
        self.assertIn('named .bsp', got['map_named_bsp']['hint'])
        want = python_frames(out)['frames/x+00/y+00/frame.ccf']
        w = got['world']
        self.assertEqual(w['chunks'], want['chunks'])
        self.assertEqual(w['placements'], want['owned'])
        self.assertEqual(w['markers'], 0)                                 # the map names another frame
        self.assertEqual(w['frames'], ['frames/x+00/y+00'])
        self.assertEqual(w['scan']['peak_bytes'], want['scan']['peak_bytes'])
        self.assertIn('matches the heap report', w['info'])
        self.assertIn('Ground colours', w['hint'])
        self.assertEqual(got['ring']['bytes'], want['scan']['peak_bytes'])
        self.assertEqual(got['ring']['chunks'], want['scan']['ring_chunks'])
        self.assertIn('Ring at', got['ring']['info'])
        self.assertIn('terrain reference to TERR', got['describe']['chunk'])
        self.assertIn('CHIM placement', got['describe']['placement'])
        self.assertGreater(got['overlay_draw_calls'], 0)

    def test_page_text_and_release_listing(self):
        html = PAGE.read_text(encoding='utf-8')
        self.assertIn('Open BSP / CHIM / JSON <input id="file" type="file" accept=".bsp,.chim,.json">', html)
        self.assertIn('Open a converted BSP, a CHIM map (.chim) or a CHIM world to navigate its actual polygons. '
                      'This viewer does not change the game.', html)
        self.assertIn('Open BSP / CHIM / JSON above', html)
        self.assertIn('<script src="chim-reader.js"></script>', html)
        self.assertIn(r'/\.(bsp|chim|json)$/i', html)
        self.assertIn('webkitdirectory', html)
        listed = set(json.loads((ROOT / 'tools' / 'release-files.json').read_text(encoding='utf-8')))
        for name in ('amiwind-toolkit/chim-reader.js', 'tests/test_toolkit_chim.py', 'tests/test_toolkit_chim.js',
                     'docs/CHIM_FILE_FORMAT.md'):
            self.assertIn(name, listed)
        self.assertIn('tools/chim/format.py', READER.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
