"""Recovery rejects incomplete or changed runs and schedules no terrain rebuild."""
import copy
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch

import build
from build_parallel import stage_dependencies
from recover_image import inspect_run, recovery_commands
from prepare_world_regions import plan, region_directory


class ImageRecoveryTests(unittest.TestCase):
    def fixture(self, root):
        old=root/'old';source=root/'source';data=root/'data'
        (source/'docs').mkdir(parents=True);data.mkdir()
        (old/'world-survey').mkdir(parents=True);(old/'world-terrain').mkdir()
        (old/'intro-scene/id1/maps').mkdir(parents=True)
        (old/'intro-scene/id1/world').mkdir()
        args=build.parser().parse_args(['--recover-image-from',str(old),'--data-files',str(data)])
        args.sdk=Path('/sdk');args.font_options={'bitmap_paper_ink':'filled'}
        tools={n:'/tools/'+n for n in ('qbsp','vis','light','qcc','ffmpeg','xdftool','rdbtool')}
        steps=build.commands(args,tools,root/'next')
        state={'schema':'amiwind-build-receipt-v1','runtime_version':'0.0.25-rc3',
               'recipe':'seyda-neen-prison-v1','status':'failed','hands':'3d',
               'data_files':str(data),'font_options':args.font_options,
               'source_sha256':{'tools/example.py':'a'*64},'input_sha256':{'Morrowind.esm':'b'*64},
               'steps':[{'name':name,'status':'failed' if name=='image' else 'passed','command':command}
                        for name,command in steps if name not in ('world-ui', 'actor-contact', 'npc-gallery')]}
        (old/'build-state.json').write_text(json.dumps(state))
        (source/'docs/PATCH-v0.0.25-rc6.json').write_text(json.dumps({'base_files':{'tools/example.py':{'sha256':'a'*64}}}))
        areas=[]
        for name,filename,extent in [('Seyda Neen','seyda_area.json',2079),('Balmora','balmora.json',3072)]:
            config=json.loads((build.ROOT/'config'/filename).read_text())
            core=[[config['centre'][k]+sign*extent*4 for k in range(2)] for sign in (-1,1)]
            areas.append(dict(name=name,centre=config['centre'],scale=.25,regions=[dict(core=core)]))
        survey={'format':'AmiWind world survey 1','terrain':{'height_seams':[]},
                'settings':{'overlap_runtime':896},'areas':areas,
                'cells':[dict(cell=[0,0],screen=dict(candidate=1),unresolved_placements=0,name='',region='Test')]}
        (old/'world-survey/world-survey.json').write_text(json.dumps(survey))
        (old/'world-survey/terrain-source.npz').write_bytes(b'synthetic survey packet')
        _,entries=plan(old/'world-survey')
        payload=b'synthetic retained BSP';digest=hashlib.sha256(payload).hexdigest()
        entries[0]['converted']={'bytes':len(payload),'sha256':digest}
        (old/'intro-scene/id1/maps/vf0000.bsp').write_bytes(payload)
        (old/'intro-scene/id1/world/regions.awr').write_bytes(region_directory(survey,entries))
        report={'format':'AmiWind playable terrain regions 1','diagnostic_subset':False,'regions':entries}
        for key,name in [('survey_sha256','world-survey.json'),('terrain_sha256','terrain-source.npz')]:
            report[key]=hashlib.sha256((old/'world-survey'/name).read_bytes()).hexdigest()
        (old/'world-terrain/world-regions.json').write_text(json.dumps(report))
        return args,source,state,steps

    def test_valid_retained_run_is_read_only_and_schedules_engine_gallery_image_without_terrain(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);args,source,state,steps=self.fixture(root)
            snapshot=lambda:{str(p):p.read_bytes() for p in args.recover_image_from.rglob('*') if p.is_file()}
            before=snapshot();report=inspect_run(args,source)
            self.assertEqual(report['verified_regions'],1)
            self.assertEqual(snapshot(),before)
            selected=recovery_commands(steps,args.recover_image_from,root/'next')
            self.assertEqual([n for n,_ in selected],['engine','npc-gallery','image'])
            gallery=selected[1][1]
            self.assertEqual(gallery[gallery.index('--palette')+1],str(root/'old/intro-scene/id1/gfx/palette.lmp'))
            self.assertEqual(gallery[gallery.index('--cache')+1],str(args.workspace/'cache/npc-gallery-v1'))
            self.assertNotIn('--seed-run',gallery)
            image=selected[2][1]
            self.assertEqual(image[image.index('--gallery')+1],str(root/'next/npc-gallery'))
            self.assertEqual(image[image.index('--scene')+1],str(root/'old/intro-scene'))
            self.assertEqual(image[image.index('--engine')+1],str(root/'next/engine/runtime/build/AmiQuakeGCC'))
            self.assertFalse((root/'next').exists())

    def test_recovery_preserves_explicit_cache_and_gallery_seed_options(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);args,source,state,steps=self.fixture(root)
            args.gallery_cache=root/'shared cache'
            args.gallery_seed_run=root/'stopped rc9 run'
            tools={n:'/tools/'+n for n in ('qbsp','vis','light','qcc','ffmpeg','xdftool','rdbtool')}
            selected=recovery_commands(build.commands(args,tools,root/'next'),root/'old',root/'next')
            self.assertEqual([n for n,_ in selected],['engine','npc-gallery','image'])
            gallery=dict(selected)['npc-gallery']
            self.assertEqual(gallery[gallery.index('--cache')+1],str(args.gallery_cache))
            self.assertEqual(gallery[gallery.index('--seed-run')+1],str(args.gallery_seed_run))

    def test_reject_incomplete_stages_and_modified_source(self):
        with tempfile.TemporaryDirectory() as temp:
            args,source,state,steps=self.fixture(Path(temp));path=args.recover_image_from/'build-state.json'
            bad=copy.deepcopy(state)
            next(s for s in bad['steps'] if s['name']=='world-terrain')['status']='failed'
            path.write_text(json.dumps(bad))
            with self.assertRaisesRegex(ValueError,'22 pre-image'):inspect_run(args,source)
            state['source_sha256']['tools/example.py']='c'*64;path.write_text(json.dumps(state))
            with self.assertRaisesRegex(ValueError,'published baseline'):inspect_run(args,source)

    def test_reject_corrupt_region_and_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            args,source,state,steps=self.fixture(Path(temp));old=args.recover_image_from
            region=old/'intro-scene/id1/maps/vf0000.bsp';original=region.read_bytes()
            region.write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError,'terrain output hash mismatch'):inspect_run(args,source)
            region.write_bytes(original);(old/'intro-scene/id1/world/regions.awr').write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError,'world directory differs'):inspect_run(args,source)

    def test_reject_different_inputs_or_render_choices(self):
        with tempfile.TemporaryDirectory() as temp:
            args,source,state,steps=self.fixture(Path(temp))
            args.hands='sprites'
            with self.assertRaisesRegex(ValueError,'hands mode'):inspect_run(args,source)
            args.hands='3d';args.font_options={'bitmap_paper_ink':'original'}
            with self.assertRaisesRegex(ValueError,'paper ink'):inspect_run(args,source)

    def test_recovery_never_writes_outputs_into_original_run(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);args,source,state,steps=self.fixture(root)
            command=dict(steps)['image'];command[command.index('--out')+1]=str(root/'old/image')
            with self.assertRaisesRegex(ValueError,'new run'):recovery_commands(steps,root/'old',root/'next')

    def test_world_ui_validation_is_a_dependency_before_expensive_terrain(self):
        with tempfile.TemporaryDirectory() as temp:
            args,source,state,steps=self.fixture(Path(temp));deps=stage_dependencies(steps)
            self.assertIn('actor-contact',deps['world-terrain'])
            self.assertIn('npc-gallery',deps['world-terrain'])
            self.assertIn('npc-gallery',deps['image'])
            self.assertEqual(deps['npc-gallery'],('census',))
            self.assertIn('world-ui',deps['actor-contact'])
            self.assertIn('world-survey',deps['world-ui'])
            self.assertIn('opening-references',deps['world-ui'])

    def test_gallery_opt_out_requires_explicit_current_flag(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);args,source,state,steps=self.fixture(root)
            self.assertFalse(args.no_npc_gallery)
            args.no_npc_gallery=True
            tools={n:'/tools/'+n for n in ('qbsp','vis','light','qcc','ffmpeg','xdftool','rdbtool')}
            steps=build.commands(args,tools,root/'next')
            self.assertNotIn('npc-gallery',dict(steps))
            self.assertIn('--no-npc-gallery',dict(steps)['image'])
            self.assertNotIn('npc-gallery',stage_dependencies(steps)['image'])
            selected=recovery_commands(steps,root/'old',root/'next')
            self.assertEqual([name for name,_ in selected],['engine','image'])
            missing_flag=[(name,[x for x in command if x!='--no-npc-gallery']) for name,command in steps]
            with self.assertRaisesRegex(ValueError,'required NPC gallery'):
                recovery_commands(missing_flag,root/'old',root/'next')

    def run_entry_point(self, root, changed_inputs=False):
        old=root/'old';old.mkdir();(old/'retained').write_bytes(b'unchanged')
        def prerequisites(args, **kwargs):
            args.sdk=root/'sdk';args.data_files=root/'data'
            return {}
        def commands(args, run):
            output=run/'image'/f'AmiWind-v{build.VERSION}.hdf'
            script=f'from pathlib import Path; p=Path({str(output)!r}); p.parent.mkdir(); p.write_bytes(b"test image")'
            return [('world-terrain',[sys.executable,'-c','raise AssertionError("must not recompile")']),
                    ('engine',[sys.executable,'-c','print("engine rebuilt")','--out',str(run/'engine')]),
                    ('npc-gallery',[sys.executable,'-c','pass','--palette',str(run/'intro-scene/id1/gfx/palette.lmp'),'--out',str(run/'npc-gallery')]),
                    ('image',[sys.executable,'-c',script,'--out',str(run/'image'),'--scene',str(run/'intro-scene'),'--music',str(run/'music')])]
        inputs={'Morrowind.esm':'original'}
        with patch('setup_build.use_environment'), patch.object(build,'prerequisites',side_effect=prerequisites), \
             patch('recover_image.inspect_run',return_value={'from_run':str(old),'verified_regions':1,'input_sha256':inputs}), \
             patch.object(build,'commands',side_effect=lambda args,tools,run: commands(args,run)), \
             patch.object(build,'provenance',return_value={'compiler_jobs':1,'serial_stages':True,
                 'input_sha256':{'Morrowind.esm':'changed'} if changed_inputs else inputs}), \
             contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            argv=['--recover-image-from',str(old),'--workspace',str(root/'work'),'--name','retry','--jobs','1']
            if changed_inputs:
                with self.assertRaises(SystemExit) as error:build.main(argv)
                self.assertEqual(error.exception.code,1)
            else:self.assertEqual(build.main(argv),0)
        self.assertEqual((old/'retained').read_bytes(),b'unchanged')
        return root/'work/build/retry'

    def test_entry_point_rebuilds_engine_gallery_image_and_records_recovery(self):
        with tempfile.TemporaryDirectory() as temp:
            run=self.run_entry_point(Path(temp))
            state=json.loads((run/'build-state.json').read_text())
            self.assertEqual([s['name'] for s in state['steps']],['engine','npc-gallery','image'])
            self.assertEqual(state['recovery']['verified_regions'],1)
            summary=json.loads((run/'build-summary.json').read_text())
            self.assertEqual(summary['status'],'passed')
            self.assertIn('recovery',summary['mode'])

    def test_entry_point_rejects_changed_inputs_before_building(self):
        with tempfile.TemporaryDirectory() as temp:
            run=self.run_entry_point(Path(temp),changed_inputs=True)
            self.assertFalse(run.exists())


if __name__=='__main__':unittest.main()
