# SPDX-License-Identifier: GPL-3.0-only
"""Adjacent frames retain boundary scenery without duplicate original ownership."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT/'tools', ROOT/'src', ROOT/'tests'):
    sys.path.insert(0, str(p))

from chim.ownership import bind_index, capture, manifest, source_failures
from chim.validate import validate
from chim.world import build_frames
from test_chim_frames import frame_specs


class OwnershipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        a, _, sections = frame_specs(cls.tmp.name)
        a = copy.deepcopy(a)
        b = copy.deepcopy(a)
        a['frame']['owned'] = ((-512., -512.), (0., 512.))
        b['frame']['owned'] = ((0., -512.), (512., 512.))
        b['frame']['cell'] = (1, 0)
        refs = [capture({'number': p['ref'], 'cell': p['cell'], 'id': 'box%s' % p['ref'],
                         'type': 'STAT', 'model': 'box.nif', 'scale': 1.,
                         'rotation_radians': [0., 0., 0.],
                         'position': [a['frame']['centre'][0]+4*p['origin'][0],
                                      a['frame']['centre'][1]+4*p['origin'][1], 4*p['origin'][2]]})
                for p in a['placements']]
        cls.specs = [a, b];cls.refs = refs
        cls.out = Path(cls.tmp.name)/'adjacent'
        build_frames(cls.out, [a, b], {'grain': 256, 'sector_chunks': 2})
        cls.source = {'frames': [dict(copy.deepcopy(sections[0]), cell=list(s['frame']['cell']),
                                    frame_ownership=manifest(s, refs)) for s in [a, b]]}
        bind_index(cls.out, cls.source)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def failures(self, source):
        return list(validate(self.out, source)[0])

    def test_boundary_copies_pass_real_serialized_validator(self):
        self.assertEqual(self.failures(self.source), [])
        self.assertEqual(source_failures(self.source['frames']), [])

    def test_no_metadata_keeps_old_duplicate_guard(self):
        self.assertTrue(any('two frames' in f for f in self.failures(None)))

    def test_partial_metadata_fails_closed(self):
        s = copy.deepcopy(self.source)
        del s['frames'][1]['frame_ownership']
        self.assertTrue(any('metadata missing' in f for f in self.failures(s)))

    def test_stale_world_binding_fails_closed(self):
        s = copy.deepcopy(self.source);s['ownership_index_sha256'] = '0'*64
        self.assertTrue(any('not bound' in f for f in self.failures(s)))

    def test_changed_original_fields_fail(self):
        for field, value in [('position', [1., 2., 3.]), ('rotation_radians', [0., 1., 0.]),
                             ('model', 'other.nif'), ('cell', [15, 15]), ('scale', 2.),
                             ('master', 'other.esm'), ('id', 'other'), ('type', 'ACTI')]:
            with self.subTest(field=field):
                s = copy.deepcopy(self.source)
                s['frames'][1]['frame_ownership']['references'][0]['original'][field] = value
                self.assertTrue(any('identity/transform differs' in f for f in source_failures(s['frames'])))

    def test_second_declared_owner_is_refused(self):
        s = copy.deepcopy(self.source)
        rows = s['frames'][1]['frame_ownership']['references']
        next(r for r in rows if r['role'] == 'dependency')['role'] = 'owner'
        self.assertTrue(any('role disagrees' in f for f in source_failures(s['frames'])))

    def test_overlapping_cores_are_refused(self):
        s = copy.deepcopy(self.source)
        s['frames'][1]['frame_ownership']['core'] = s['frames'][0]['frame_ownership']['core']
        self.assertTrue(any('cores overlap' in f for f in source_failures(s['frames'])))

    def test_missing_included_owner_is_refused(self):
        s = copy.deepcopy(self.source)
        m = s['frames'][0]['frame_ownership'];n = next(r['original']['number'] for r in m['references'] if r['role']=='owner')
        m['references'] = [r for r in m['references'] if r['original']['number'] != n]
        m['pieces'] = [p for p in m['pieces'] if p['ref'] != n]
        s['frames'][0]['placements'] = [p for p in s['frames'][0]['placements'] if p['ref'] != n]
        self.assertTrue(any('0 logical owners; expected 1' in f for f in source_failures(s['frames'])))

    def test_external_owner_permitted_for_isolated_frame(self):
        self.assertEqual(source_failures(self.source['frames'][:1]), [])

    def test_repeated_source_and_piece_ids_refused(self):
        for key in ['references', 'pieces']:
            s = copy.deepcopy(self.source);m = s['frames'][0]['frame_ownership']
            m[key].append(copy.deepcopy(m[key][0]))
            self.assertTrue(source_failures(s['frames']))

    def test_piece_pose_cell_geometry_and_collision_bindings(self):
        for field, value in [('origin', [2., 3., 4.]), ('yaw', 111.), ('cell', [33, 44]),
                             ('model_sha256', '0'*64), ('story_hidden', True)]:
            with self.subTest(field=field):
                s = copy.deepcopy(self.source)
                s['frames'][0]['frame_ownership']['pieces'][0][field] = value
                self.assertTrue(any('serialized render/collision/placement' in f for f in self.failures(s)))

    def test_missing_piece_refused(self):
        s = copy.deepcopy(self.source);s['frames'][0]['frame_ownership']['pieces'].pop()
        self.assertTrue(any('pieces differ' in f for f in self.failures(s)))

    def test_dependency_without_footprint_refused_before_pack(self):
        spec = copy.deepcopy(self.specs[0]);refs = copy.deepcopy(self.refs)
        n = next(r['original']['number'] for r in self.source['frames'][0]['frame_ownership']['references'] if r['role']=='dependency')
        next(p for p in spec['placements'] if p['ref']==n)['origin'] = (100000., 100000., 0.)
        with self.assertRaisesRegex(ValueError, 'no compiled footprint'):
            manifest(spec, refs)

    def test_asset_identity_uses_original_case_insensitive_paths(self):
        from chim.ownership import original
        a = copy.deepcopy(self.refs[0]);b = copy.deepcopy(a)
        a.update(model='F/BIG.NIF', id='Box', master='Morrowind.esm')
        b.update(model='f'+chr(92)+'big.nif', id='box', master='morrowind.esm')
        self.assertEqual(original(a), original(b))

    def test_geometry_digest_keeps_render_and_collision_changes(self):
        from chim.ownership import model_digest
        from chim import format as F
        from chim_fixture import box_bsp
        lumps = F.read_brush_image(box_bsp([((0,0,0),(64,64,64))]))
        base = model_digest(lumps)
        for part in [3, 9]:
            with self.subTest(lump=part):
                altered = list(lumps);data = bytearray(altered[part]);data[0] ^= 1;altered[part] = bytes(data)
                self.assertNotEqual(base, model_digest(altered))

    def test_original_snapshot_survives_visual_adjustments(self):
        r = copy.deepcopy(self.refs[0]);before = copy.deepcopy(r['_chim_original'])
        r['position'][2] += 3.;r['rotation_radians'][1] += .1
        self.assertEqual(r['_chim_original'], before)


if __name__ == '__main__':
    unittest.main()
