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

    def test_frame_checks_on_the_pool_give_the_same_failures(self):
        # BUILD-CHIM-STAGE-SERIAL-TAIL-36: the model digests and each frame's checks on the worker pool, merged in
        # frame order: the same lines as one process, passing and failing
        import contextlib
        import io
        from build_parallel import stage_pool
        broken = copy.deepcopy(self.source)
        broken['frames'][0]['frame_ownership']['pieces'][0]['yaw'] = 111.
        broken['frames'][1]['frame_ownership']['pieces'].pop()
        for source in (self.source, broken):
            serial = list(validate(self.out, source, jobs=1, cross_checks='serial')[0])
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()), \
                    stage_pool(2, 'test'):
                pooled = list(validate(self.out, source, jobs=2, cross_checks='pool')[0])
            self.assertEqual(pooled, serial)
        self.assertGreaterEqual(sum('pieces differ' in f for f in serial), 2)

    def test_missing_piece_refused(self):
        s = copy.deepcopy(self.source);s['frames'][0]['frame_ownership']['pieces'].pop()
        self.assertTrue(any('pieces differ' in f for f in self.failures(s)))

    def test_compiled_apron_excludes_only_external_nonintersecting_pieces(self):
        from chim.ownership import select_compiled_apron
        spec = copy.deepcopy(self.specs[0]); refs = copy.deepcopy(self.refs)
        number = next(r['original']['number'] for r in self.source['frames'][0]['frame_ownership']['references'] if r['role']=='dependency')
        next(p for p in spec['placements'] if p['ref']==number)['origin'] = (100000., 100000., 0.)
        selected, excluded = select_compiled_apron(spec, refs)
        self.assertEqual([r['original']['number'] for r in excluded], [number])
        self.assertNotIn(number, [r['number'] for r in selected])
        self.assertNotIn(number, [p['ref'] for p in spec['placements']])
        self.assertEqual(excluded[0]['original'], next(r['_chim_original'] for r in refs if r['number']==number))
        self.assertEqual(len(manifest(spec, selected)['references']), len(refs)-1)

    def test_compiled_apron_keeps_owned_original_even_when_geometry_is_outside(self):
        from chim.ownership import select_compiled_apron
        spec = copy.deepcopy(self.specs[0]); refs = copy.deepcopy(self.refs)
        number = next(r['original']['number'] for r in self.source['frames'][0]['frame_ownership']['references'] if r['role']=='owner')
        next(p for p in spec['placements'] if p['ref']==number)['origin'] = (100000., 100000., 0.)
        selected, excluded = select_compiled_apron(spec, refs)
        self.assertEqual(excluded, []); self.assertEqual(selected, refs)
        self.assertIn(number, [p['ref'] for p in spec['placements']])

    def test_compiled_apron_keeps_reaching_dependencies_and_missing_piece_failure(self):
        from chim.ownership import select_compiled_apron
        spec = copy.deepcopy(self.specs[0]); refs = copy.deepcopy(self.refs)
        selected, excluded = select_compiled_apron(spec, refs)
        self.assertEqual(selected, refs); self.assertEqual(excluded, [])
        number = next(r['original']['number'] for r in self.source['frames'][0]['frame_ownership']['references'] if r['role']=='dependency')
        spec['placements'] = [p for p in spec['placements'] if p['ref'] != number]
        selected, excluded = select_compiled_apron(spec, refs)
        self.assertEqual(selected, refs); self.assertEqual(excluded, [])
        with self.assertRaisesRegex(ValueError, 'no compiled footprint'):
            manifest(spec, selected)

    def test_compiled_apron_rejects_nonfinite_footprints_and_duplicate_sources(self):
        from chim.ownership import select_compiled_apron
        spec = copy.deepcopy(self.specs[0]); refs = copy.deepcopy(self.refs)
        with self.assertRaisesRegex(ValueError, 'Repeated source'):
            select_compiled_apron(spec, refs + refs[:1])
        spec['placements'][0]['origin'] = (float('nan'), 0., 0.)
        with self.assertRaisesRegex(ValueError, 'Nonfinite'):
            select_compiled_apron(spec, refs)

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



class ApronDispositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        OwnershipTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        OwnershipTests.tearDownClass()

    def fixture(self, root, declared=True):
        import json
        specs = copy.deepcopy(OwnershipTests.specs)
        sections = copy.deepcopy(OwnershipTests.source['frames'])
        sections[0]['town'] = 'town'; sections[1]['town'] = 'regional'
        row = next(r for r in sections[0]['frame_ownership']['references'] if r['role'] == 'owner')
        ref = row['original']; number = ref['number']
        from chim.cut import source_ref
        specs[0]['placements'] = [p for p in specs[0]['placements'] if source_ref(p['ref']) != number]
        sections[0]['placements'] = [p for p in sections[0]['placements'] if p['ref'] != number]
        m = sections[0]['frame_ownership']
        m['references'] = [r for r in m['references'] if r['original']['number'] != number]
        m['pieces'] = [p for p in m['pieces'] if source_ref(p['ref']) != number]
        path = Path(root)/'work/town/source-catalogue.json'; path.parent.mkdir(parents=True)
        path.write_text(json.dumps({'references': [ref], 'deferred': [ref] if declared else []}))
        return specs, sections, ref, path

    def test_explicit_deferred_dependency_has_no_mesh_or_invented_owner(self):
        from chim.apron_policy import reconcile
        with tempfile.TemporaryDirectory() as root:
            specs, sections, ref, path = self.fixture(root)
            self.assertTrue(source_failures(sections))
            records = reconcile(specs, sections, root, {'regional'})
            self.assertEqual([r['original'] for r in records], [ref])
            self.assertEqual(records[0]['disposition'], 'deferred_by_owner')
            self.assertEqual(source_failures(sections), [])
            out = Path(root)/'compiled'
            build_frames(out, specs, {'grain': 256, 'sector_chunks': 2})
            source = {'frames': sections}; bind_index(out, source)
            self.assertEqual(validate(out, source)[0], [])

    def test_undeclared_or_changed_reference_still_fails(self):
        import json
        from chim.apron_policy import reconcile
        with tempfile.TemporaryDirectory() as root:
            specs, sections, ref, path = self.fixture(root, declared=False)
            self.assertEqual(reconcile(specs, sections, root, {'regional'}), [])
            self.assertTrue(any('0 logical owners' in x for x in source_failures(sections)))
            changed = dict(ref, scale=2.)
            path.write_text(json.dumps({'references': [changed], 'deferred': [changed]}))
            with self.assertRaisesRegex(ValueError, 'differs'):
                reconcile(specs, sections, root, {'regional'})

    def test_nonsolid_sprite_preserved_once_with_exact_asset_binding(self):
        import json, hashlib
        from chim.apron_policy import reconcile
        with tempfile.TemporaryDirectory() as root:
            specs, sections, ref, path = self.fixture(root)
            flora = Path(root)/'flora'; name = 'progs/aw_flora/f_'+'a'*16+'.spr'
            asset = flora/name; asset.parent.mkdir(parents=True); asset.write_bytes(b'fixture sprite bytes')
            entry = {'sprite_asset_name': name, 'bytes': asset.stat().st_size,
                     'sha256': hashlib.sha256(asset.read_bytes()).hexdigest(),
                     'source_xy_bake_center': [0., 0.]}
            row = dict(ref, renderer_policy='sprite', requires_interaction=False,
                       source_collision={'mode': 'nonsolid'}, sprite_asset_name=name)
            (flora/'tree-sprites.json').write_text(json.dumps({'placements': [row], 'assets': [entry]}))
            records = reconcile(specs, sections, root, {'regional'}, flora)
            self.assertEqual(records[0]['disposition'], 'existing_nonsolid_sprite')
            self.assertEqual(len(sections[1]['sprite_entities']), 1)
            self.assertEqual(sections[1]['sprite_entities'][0]['aw_ref'], str(ref['number']))
            bound = sections[1]['sprite_assets'][0]
            self.assertEqual((Path(root)/bound['file']).read_bytes(), asset.read_bytes())
            self.assertEqual(source_failures(sections), [])
            self.assertEqual(reconcile(specs, sections, root, {'regional'}, flora), [])
            self.assertEqual(len(sections[1]['sprite_entities']), 1)

    def test_corrupt_sprite_cannot_replace_a_missing_owner(self):
        import json
        from chim.apron_policy import reconcile
        with tempfile.TemporaryDirectory() as root:
            specs, sections, ref, path = self.fixture(root)
            flora = Path(root)/'flora'; name = 'progs/aw_flora/f_'+'a'*16+'.spr'
            asset = flora/name; asset.parent.mkdir(parents=True); asset.write_bytes(b'bad')
            row = dict(ref, renderer_policy='sprite', requires_interaction=False,
                       source_collision={'mode': 'nonsolid'}, sprite_asset_name=name)
            (flora/'tree-sprites.json').write_text(json.dumps({'placements': [row], 'assets': [
                {'sprite_asset_name': name, 'bytes': 3, 'sha256': '0'*64}]}))
            with self.assertRaisesRegex(ValueError, 'checksum'):
                reconcile(specs, sections, root, {'regional'}, flora)
            self.assertTrue(source_failures(sections))


class NamedTownApronDispositionTests(ApronDispositionTests):
    def fixture(self, root, declared=True):
        specs, sections, ref, path = super().fixture(root, declared)
        sections[1]['town'] = 'neighbor-town'
        return specs, sections, ref, path




class MissingApronTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        OwnershipTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        OwnershipTests.tearDownClass()

    def fixture(self):
        from chim.cut import source_ref
        specs = copy.deepcopy(OwnershipTests.specs)
        sections = copy.deepcopy(OwnershipTests.source['frames'])
        sections[0]['town'] = 'seyda'; sections[1]['town'] = 'neighbor'
        number = next(r['original']['number'] for r in sections[1]['frame_ownership']['references']
                      if r['role'] == 'owner')
        specs[0]['placements'] = [p for p in specs[0]['placements'] if source_ref(p['ref']) != number]
        sections[0]['placements'] = [p for p in sections[0]['placements'] if p['ref'] != number]
        refs = [r for r in OwnershipTests.refs if r['number'] != number]
        sections[0]['frame_ownership'] = manifest(specs[0], refs)
        return specs, sections, number

    def test_missing_apron_retains_exact_owner_models_and_serializes(self):
        from chim.apron_policy import supplement_seyda
        from chim.ownership import model_digest
        from chim.cut import source_ref
        specs, sections, number = self.fixture()
        donor = copy.deepcopy(specs[1])
        records = supplement_seyda(specs, sections)
        self.assertEqual([r['original']['number'] for r in records], [number])
        self.assertEqual(source_failures(sections), [])
        a = next(p for p in specs[0]['placements'] if source_ref(p['ref']) == number)
        b = next(p for p in specs[1]['placements'] if source_ref(p['ref']) == number)
        self.assertEqual(a['origin'], b['origin'])
        self.assertEqual(model_digest(specs[0]['variants'][a['variant']]['lumps']),
                         model_digest(specs[1]['variants'][b['variant']]['lumps']))
        self.assertEqual(specs[1]['placements'], donor['placements'])
        with tempfile.TemporaryDirectory() as tmp:
            build_frames(tmp, specs, {'grain': 256, 'sector_chunks': 2})
            source = {'frames': sections}; bind_index(tmp, source)
            self.assertEqual(list(validate(tmp, source)[0]), [])
        self.assertEqual(supplement_seyda(specs, sections), [])

    def test_supplement_parity_rejects_missing_or_rebound_model(self):
        from chim.apron_policy import supplement_seyda, checked_seyda_supplements
        from chim_town import seyda_static_check
        specs, sections, number = self.fixture()
        supplement_seyda(specs, sections)
        placed = {p['ref'] for p in sections[0]['placements']}
        added = checked_seyda_supplements(sections[0], placed)
        self.assertEqual(added, [number])
        self.assertEqual(seyda_static_check({}, [], placed, {'apron_owner_added': added})[1]['in_chunks'], 1)
        with self.assertRaisesRegex(ValueError, 'Unbound'):
            checked_seyda_supplements(sections[0], placed-{number})
        sections[0]['apron_owner_supplements'][0]['model_sha256'] = ['0'*64]
        with self.assertRaisesRegex(ValueError, 'Unbound'):
            checked_seyda_supplements(sections[0], placed)

    def test_translation_uses_both_frame_centres(self):
        from chim.apron_policy import supplement_seyda
        specs, sections, number = self.fixture()
        frame = specs[1]['frame']; before = frame['centre']
        frame['centre'] = (before[0]+512., before[1])
        frame['low'] = (frame['low'][0]-128., frame['low'][1])
        frame['owned'] = tuple((p[0]-128., p[1]) for p in frame['owned'])
        for p in specs[1]['placements']:
            p['origin'] = (p['origin'][0]-128., *p['origin'][1:])
        sections[1]['frame_ownership'] = manifest(specs[1], OwnershipTests.refs)
        supplement_seyda(specs, sections)
        a = next(p for p in specs[0]['placements'] if p['ref'] == number)
        b = next(p for p in specs[1]['placements'] if p['ref'] == number)
        self.assertAlmostEqual(a['origin'][0], b['origin'][0]+128.)
        self.assertEqual(source_failures(sections), [])

    def test_invalid_owner_is_not_repaired_or_relabelled(self):
        from chim.apron_policy import supplement_seyda
        specs, sections, number = self.fixture()
        next(r for r in sections[1]['frame_ownership']['references']
             if r['original']['number'] == number)['role'] = 'dependency'
        with self.assertRaisesRegex(ValueError, 'invalid ownership'):
            supplement_seyda(specs, sections)

    def test_other_frames_are_unchanged(self):
        from chim.apron_policy import supplement_seyda
        specs, sections, number = self.fixture()
        sections[0]['town'] = 'unrelated'
        before = copy.deepcopy(sections)
        self.assertEqual(supplement_seyda(specs, sections), [])
        self.assertEqual(sections, before)


if __name__ == '__main__':
    unittest.main()
