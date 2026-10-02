"""Appearance reuse must preserve content and reject stale/partial cache entries."""
import contextlib
import copy
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

import gallery_cache as c
import build_gallery as g


class GalleryCacheTests(unittest.TestCase):
    key = 'm'+'1'*16
    spec = {'kind': 'NPC_', 'appearance': {'parts': [], 'skeleton': 'meshes/base_anim.nif', 'height': 1., 'weight': 1.}}

    def pair(self, key=None):
        raw=bytearray(128);raw[:8]=b'IDPO\x06\0\0\0';struct.pack_into('<ii',raw,60,3,1)
        raw=bytes(raw)
        return raw, {'key':key or self.key,'status':'ready','bytes':len(raw),'sha256':c.digest(raw),
                     'palette_sha256':c.digest(bytes(768)),'vertices':3,'triangles':1,
                     'quality_profile':'','quality_settings':None}

    def ident(self, **changes):
        args=dict(spec=self.spec,palette=bytes(768),dependencies={'meshes/head.nif':'a'},sources={'converter':'b'},env={'python':'p'})
        args.update(changes)
        return c.identity(**args)

    def test_completion_progress_counts_and_stable_export_order(self):
        keys = ['m'+str(i)*16 for i in (3, 1, 2)]
        tasks = [('data', 'out', key, self.spec, bytes(768), 'cache', {}) for key in keys]
        results = [dict(self.pair(key)[1], dimensions=[1., 2., 3.]) for key in keys]
        # Simulate a conversion, a failure and a hit finishing out of source order.
        failed = dict(results[1], status='failed', error='Alias vertex budget exceeded')
        finishes = [(results[2], 'converted', 2.), (failed, 'converted', 3.),
                    (results[0], 'hit', .1)]
        output = io.StringIO()
        with patch.object(g, 'completed_map', return_value=iter(finishes)), contextlib.redirect_stdout(output):
            actual, counts, seconds = g.collect_models(tasks, 2)
        self.assertEqual(list(actual), keys)
        self.assertEqual(counts, {'reused': 1, 'converted': 1, 'failed': 1})
        self.assertAlmostEqual(seconds, 5.1)
        self.assertIn('reused 1, converted 1, failed 1, remaining 0', output.getvalue())
        self.assertIn('Alias vertex budget exceeded', output.getvalue())
        self.assertEqual(actual[keys[1]]['status'], 'failed')

    def test_reordered_completion_preserves_catalogue_and_audit_bytes(self):
        keys = ['m'+str(i)*16 for i in (3, 1, 2)]
        results = {key: dict(self.pair(key)[1], dimensions=[1., 2., 3.]) for key in keys}
        tasks = [('data', 'out', key, self.spec, bytes(768), 'cache', {}) for key in keys]
        finishes = [(results[key], 'hit', 0.) for key in reversed(keys)]
        with patch.object(g, 'completed_map', return_value=iter(finishes)), contextlib.redirect_stdout(io.StringIO()):
            actual, _, _ = g.collect_models(tasks, 2)
        entries = [{'number': i+1, 'kind': 'NPC_', 'models': [key, key],
                    'id': 'actor'+str(i), 'name': 'Actor '+str(i)} for i, key in enumerate(keys)]
        with tempfile.TemporaryDirectory() as temp:
            outputs = [Path(temp)/name for name in ('ordered', 'completed')]
            for out, values in zip(outputs, (results, actual)):
                (out/'gallery').mkdir(parents=True)
                with patch('prepare_gallery.inspection_table'), patch('prepare_gallery.gallery_map'):
                    self.assertEqual(g.finish_catalogue(copy.deepcopy(entries), values, out, bytes(768)), 0)
            files = [p.relative_to(outputs[0]) for p in outputs[0].rglob('*') if p.is_file()]
            self.assertIn(Path('gallery/catalog.txt'), files)
            self.assertIn(Path('gallery-audit.json'), files)
            for name in files:
                self.assertEqual((outputs[0]/name).read_bytes(), (outputs[1]/name).read_bytes(), str(name))

    def test_duplicate_completion_cannot_hide_missing_model(self):
        _, result = self.pair()
        tasks = [('data', 'out', self.key, self.spec, bytes(768), 'cache', {})]
        with patch.object(g, 'completed_map', return_value=iter([(result, 'hit', 0.)]*2)), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ValueError, 'Duplicate completed'):
                g.collect_models(tasks, 2)

    def test_identity_changes_for_dependencies_palette_settings_and_environment(self):
        original=self.ident()
        for kwargs in ({'dependencies':{'meshes/head.nif':'changed'}}, {'palette':bytes([1])*768},
                       {'sources':{'converter':'new'}}, {'env':{'python':'other'}},
                       {'spec':dict(self.spec,appearance=dict(self.spec['appearance'],height=1.1))}):
            self.assertNotEqual(c.token(original),c.token(self.ident(**kwargs)))

    def test_complete_pair_roundtrip_and_corrupt_or_missing_files_miss(self):
        with tempfile.TemporaryDirectory() as temp:
            cache=Path(temp);ident=self.ident();raw,result=self.pair()
            c.publish(cache,ident,self.key,raw,result)
            self.assertEqual(c.load(cache,ident,self.key),(raw,result))
            directory=cache/c.token(ident)[:2]/c.token(ident)
            (directory/'model.mdl').write_bytes(b'partial')
            self.assertIsNone(c.load(cache,ident,self.key))
            c.publish(cache,ident,self.key,raw,result)
            (directory/'entry.json').unlink()
            self.assertIsNone(c.load(cache,ident,self.key))

    def test_different_identity_cannot_reuse_matching_filename(self):
        with tempfile.TemporaryDirectory() as temp:
            raw,result=self.pair();ident=self.ident();c.publish(temp,ident,self.key,raw,result)
            self.assertIsNone(c.load(temp,self.ident(palette=bytes([2])*768),self.key))

    def test_cache_hit_never_calls_converter_and_corrupt_entry_is_rebuilt(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);out=root/'out';out.mkdir();cache=root/'cache';ident=self.ident();raw,result=self.pair()
            c.publish(cache,ident,self.key,raw,result)
            task=('data',str(out),self.key,self.spec,bytes(768),str(cache),ident)
            with patch('prepare_gallery.convert_model',side_effect=AssertionError('unexpected conversion')):
                actual,action,_=c.convert_cached(task)
            self.assertEqual(action,'hit');self.assertEqual((out/(self.key+'.mdl')).read_bytes(),raw)
            (cache/c.token(ident)[:2]/c.token(ident)/'model.mdl').write_bytes(b'bad')
            def convert(task):
                c.materialize(task[1],task[2],raw,result);return result
            with patch('gallery_cache.verify_dependencies'), patch('prepare_gallery.convert_model',side_effect=convert) as conversion:
                actual,action,_=c.convert_cached(task)
            self.assertEqual(action,'converted');self.assertEqual(conversion.call_count,1)
            self.assertEqual(c.load(cache,ident,self.key),(raw,result))

    def test_changed_head_only_invalidates_its_appearance(self):
        with tempfile.TemporaryDirectory() as temp:
            raw,result=self.pair();a=self.ident();b=self.ident(dependencies={'meshes/other-head.nif':'b'})
            c.publish(temp,a,self.key,raw,result);c.publish(temp,b,self.key,raw,result)
            self.assertIsNone(c.load(temp,self.ident(dependencies={'meshes/head.nif':'new'}),self.key))
            self.assertEqual(c.load(temp,b,self.key),(raw,result))

    def test_texture_candidates_record_missing_preferred_dds(self):
        class FakeAssets:
            values={'textures/head.tga':b'old'}
            def read(self,name):return self.values[name]
        deps=object.__new__(c.Dependencies);deps.assets=FakeAssets();deps.hashes={};deps.meshes={'meshes/head.nif':['textures/head.dds','textures/head.tga']}
        spec={'kind':'CREA','mesh':'head.nif'}
        original=deps.for_spec(spec)
        self.assertIsNone(original['textures/head.dds'])
        deps.assets.values['textures/head.dds']=b'new preferred DDS'
        with self.assertRaisesRegex(ValueError,'changed'):deps.verify_unchanged()
        deps.hashes={};changed=deps.for_spec(spec)
        self.assertNotEqual(original,changed)

    def seed(self, root):
        data=root/'data';data.mkdir();(data/'Morrowind.esm').write_bytes(b'owned master fixture')
        run=root/'seed';source=run/'npc-gallery';(source/'gfx').mkdir(parents=True);(source/'gallery').mkdir()
        palette=bytes(768);(source/'gfx/palette.lmp').write_bytes(palette)
        env={'python':sys.version,'packages':{'numpy':'fixture'}}
        state={'schema':'amiwind-build-receipt-v1','runtime_version':'0.0.25-rc9','status':'cancelled','python':sys.version,
               'steps':[{'name':'npc-gallery','command':['python','build_gallery.py','--out',str(source)]}],
               'source_sha256':c.converter_sources(),'version_comparison':[{'name':'numpy','detected':'fixture'}],
               'input_sha256':{'Morrowind.esm':c.file_sha(data/'Morrowind.esm')}}
        (run/'build-state.json').write_text(json.dumps(state))
        raw,result=self.pair();c.materialize(source/'gallery',self.key,raw,result)
        return data,run,palette,env,state

    def test_stopped_rc9_seed_imports_complete_pairs_and_rejects_partial(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);data,run,palette,env,state=self.seed(root);cache=root/'cache';cache.mkdir()
            missing='m'+'2'*16
            specs={self.key:self.spec,missing:self.spec};ids={k:self.ident() for k in specs}
            report=c.import_rc9(run,data,palette,specs,ids,cache,env)
            self.assertEqual((report['imported'],report['missing_or_rejected']),(1,1))
            self.assertIsNotNone(c.load(cache,ids[self.key],self.key))
            self.assertIsNone(c.load(cache,ids[missing],missing))

    def test_seed_rejects_running_state_changed_inputs_and_converter(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);data,run,palette,env,state=self.seed(root);cache=root/'cache';cache.mkdir()
            args=(run,data,palette,{self.key:self.spec},{self.key:self.ident()},cache,env)
            for field,value,pattern in [('status','running','stopped'),('input_sha256',{},'inventory'),('source_sha256',{},'sources')]:
                changed=dict(state);changed[field]=value;(run/'build-state.json').write_text(json.dumps(changed))
                with self.assertRaisesRegex(ValueError,pattern):c.import_rc9(*args)
            self.assertEqual(list(cache.iterdir()),[])

    def test_low_space_fails_without_omitting_models(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch('gallery_cache.shutil.disk_usage',return_value=type('Space',(),{'free':0})()):
                with self.assertRaisesRegex(ValueError,'without omitting models'):c.require_space([(Path(temp),100)])

    def test_cache_cannot_overlap_input_or_run_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            with self.assertRaisesRegex(ValueError,'separate'):c.cache_location(root/'data/cache',root/'data',root/'out')
