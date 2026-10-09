# SPDX-License-Identifier: GPL-3.0-only
"""chim-stats.json: stable schema and consistent figures on a synthetic world (no game assets)."""
import json
import re
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import stats as S  # noqa: E402
from chim.validate import measure, validate  # noqa: E402
from test_chim_format import CENTRE, fixture  # noqa: E402

TOP_LEVEL = {'schema', 'builder', 'chim_version', 'world_format', 'areas', 'counts', 'faces', 'models',
             'placements', 'chunks', 'views', 'disk', 'memory', 'streaming', 'build', 'pain_points', 'legacy'}
SECTIONS = {
    'counts': {'models', 'textures', 'chunks', 'placements', 'reach_copies', 'frames', 'paks'},
    'faces': {'models_stored', 'terrain', 'stored', 'placed', 'placed_over_stored', 'legacy_stored',
              'legacy_over_chim_placed'},
    'models': {'faces', 'top_by_faces', 'top_by_placed_faces', 'per_model'},
    'placements': {'faces', 'leaves', 'over_16_leaves', 'columns', 'rows'},
    'chunks': {'faces', 'faces_with_reach', 'terrain_faces', 'top_by_faces', 'per_chunk'},
    'views': {'cameras', 'camera_faces', 'all_chunks'},
    'disk': {'files', 'bytes', 'bytes_by_kind', 'paks', 'pak_bytes', 'largest_paks', 'stored_once', 'areas',
             'index_bytes'},
    'memory': {'ring_chunks', 'resident_ring_bytes', 'resident_ring_peak', 'model_zone_bytes',
               'model_zone_peak_bytes', 'walk_resident_max', 'basis'},
    'streaming': {'route_stops', 'chunks_visited', 'cache', 'legacy', 'cost_model'},
    'build': {'wall_seconds', 'cpu_seconds', 'jobs', 'sections', 'units'},
}
DISTRIBUTION = {'count', 'total', 'min', 'p50', 'p95', 'max', 'mean'}


def bsp29(path, faces):
    """A BSP29 header whose face lump holds `faces` records (only the directory is read)."""
    lumps = [(124, 0)] * 15
    lumps[S.FACES_LUMP] = (124, faces * S.FACE_BYTES)
    path.write_bytes(struct.pack('<i', 29) + b''.join(struct.pack('<ii', *x) for x in lumps)
                     + b'\0' * faces * S.FACE_BYTES)


class ChimStatsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        out = Path(cls.tmp.name) / 'w'
        cls.receipt, cls.source = fixture(out)
        fails, cls.world = validate(out, cls.source)
        assert not fails, fails
        cls.cameras = [('west', CENTRE[0] - 460 * 4, CENTRE[1] + 40 * 4), ('centre', CENTRE[0], CENTRE[1])]
        legacy = Path(cls.tmp.name) / 'legacy'
        legacy.mkdir()
        (legacy / 'regions.txt').write_text('ra -512 -512 0 0 -600 -600 100 100\nrb 0 0 512 512 -100 -100 600 600\n')
        bsp29(legacy / 'ra.bsp', 30)
        bsp29(legacy / 'rb.bsp', 50)
        cls.legacy = S.legacy_summary(legacy, legacy / 'regions.txt')
        cls.measured = measure(cls.world, cls.source, cameras=cls.cameras)
        cls.measured['walk'].pop('_replay', None)
        cls.stats = S.chim_stats(cls.world, cls.measured, cls.receipt, ['fixture'], cls.legacy, cls.cameras)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_schema_fields_are_stable(self):
        s = self.stats
        self.assertEqual(s['schema'], 'chim-stats 1')
        self.assertEqual(set(s), TOP_LEVEL)
        for section, keys in SECTIONS.items():
            with self.subTest(section=section):
                self.assertEqual(set(s[section]), keys)
        for dist in (s['models']['faces'], s['placements']['faces'], s['placements']['leaves'],
                     s['chunks']['faces'], s['disk']['pak_bytes'], s['memory']['resident_ring_bytes']):
            self.assertEqual(set(dist), DISTRIBUTION)
        self.assertEqual(s['placements']['columns'], ['pid', 'model', 'faces', 'leaves', 'chunk_x', 'chunk_y'])
        self.assertEqual((s['builder'], s['chim_version'], s['world_format']),
                         ('chim', self.receipt['chim_version'], self.receipt['world_format']))

    def test_face_totals_agree(self):
        s = self.stats
        models = s['models']['per_model']
        self.assertEqual(s['faces']['models_stored'], sum(m['faces'] for m in models))
        placed = sum(r[2] for r in s['placements']['rows'])
        self.assertEqual(placed, sum(m['placed_faces'] for m in models))
        self.assertEqual(s['faces']['placed'], placed + s['faces']['terrain'])
        self.assertEqual(s['chunks']['faces']['total'], s['faces']['placed'])
        self.assertEqual(sum(m['placements'] for m in models), s['counts']['placements'])
        self.assertEqual(s['counts']['placements'], len(self.source['placements']))
        self.assertEqual(s['faces']['legacy_stored'], 80)

    def test_top_lists_are_the_heaviest_in_order(self):
        s = self.stats
        faces = [m['faces'] for m in s['models']['top_by_faces']]
        self.assertEqual(faces, sorted(faces, reverse=True))
        self.assertEqual(faces[0], s['models']['faces']['max'])
        chunks = [c['faces'] for c in s['chunks']['top_by_faces']]
        self.assertEqual(chunks, sorted(chunks, reverse=True))
        self.assertEqual(chunks[0], s['chunks']['faces']['max'])
        paks = [p['bytes'] for p in s['disk']['largest_paks']]
        self.assertEqual(paks, sorted(paks, reverse=True))
        self.assertLessEqual(len(s['models']['top_by_faces']), S.TOP)

    def test_disk_and_duplication(self):
        s = self.stats
        on_disk = sum(p.stat().st_size for p in (Path(self.tmp.name) / 'w' / 'chim').rglob('*') if p.is_file())
        self.assertEqual(s['disk']['bytes'], on_disk)
        area = s['disk']['areas']['fixture']
        self.assertEqual(area['legacy_bytes'], self.legacy['bytes'])
        self.assertEqual(area['duplication_factor'], round(self.legacy['bytes'] / on_disk, 2))
        so = s['disk']['stored_once']
        self.assertGreaterEqual(so['model_bytes_if_each_placement_stored_its_own'], so['model_bytes'])

    def test_views_and_memory(self):
        s = self.stats
        self.assertEqual([c['camera'] for c in s['views']['cameras']], ['west', 'centre'])
        for c in s['views']['cameras']:
            self.assertEqual(c['faces'], c['terrain_faces'] + c['placement_list_faces'])
            self.assertLessEqual(c['placement_list'], c['ring_placements'])
        peak = s['memory']['resident_ring_peak']
        self.assertEqual(peak['total_bytes'], s['memory']['resident_ring_bytes']['max'])
        self.assertEqual(peak['total_bytes'], peak['chunk_bytes'] + peak['model_bytes'] + peak['texture_bytes'])
        self.assertIn('0', s['streaming']['cache'])

    def test_fields_stay_without_legacy_maps_or_cameras(self):
        bare = S.chim_stats(self.world, self.measured, self.receipt, ['fixture'])
        self.assertEqual(set(bare), TOP_LEVEL)
        for section, keys in SECTIONS.items():
            with self.subTest(section=section):
                self.assertEqual(set(bare[section]), keys)
        self.assertIsNone(bare['legacy'])
        self.assertIsNone(bare['faces']['legacy_stored'])
        self.assertIsNone(bare['disk']['areas']['fixture']['duplication_factor'])
        self.assertIsNone(bare['views']['camera_faces'])
        self.assertEqual(set(bare['disk']['areas']['fixture']), set(self.stats['disk']['areas']['fixture']))

    def test_output_is_deterministic(self):
        again = S.chim_stats(self.world, self.measured, self.receipt, ['fixture'], self.legacy, self.cameras)
        self.assertEqual(S.dumps(again), S.dumps(self.stats))
        json.loads(S.dumps(self.stats))

    def test_cli_refuses_an_invalid_world(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'w'
            fixture(out)
            sector = sorted((out / 'chim').rglob('*.ccs'))[0]
            data = bytearray(sector.read_bytes())
            data[-1] ^= 0xFF
            sector.write_bytes(bytes(data))
            import contextlib
            import io
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(S.main([str(out)]), 1)
            self.assertFalse((out / 'chim-stats.json').exists())

    def test_benchmark_cameras_match_the_documented_table(self):
        text = (ROOT / 'docs/HARDWARE-BENCHMARK.md').read_text(encoding='utf-8')
        doc = [(n, int(x), int(y)) for n, x, y in re.findall(r'\| (\w[\w ]*? \d) \| `dbg tp (-?\d+) (-?\d+)`', text)]
        mine = [row for rows in S.BENCHMARK_CAMERAS.values() for row in rows]
        self.assertEqual(sorted(mine), sorted(doc))


if __name__ == '__main__':
    unittest.main()
