"""Normal64-region integration; builder mocked, no compiler/native execution."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from prepare_seyda_regions import (regions, validate_layout, LAYOUT, default_region,
                                   directory_text, convert)
from test_share_bsp_geometry import repeated_geometry


class SeydaBoundedPipelineTests(unittest.TestCase):
    def test_exact64_partition_policy_and_native_directory(self):
        entries=regions()
        self.assertEqual(len(entries),64)
        self.assertEqual(default_region(entries)['name'],'sn029')
        lines=directory_text(entries).splitlines()
        self.assertEqual(lines[0],'AWBR1 64 96 540 0 0 64 90 0 0 64 90')
        self.assertEqual(len(lines),65)
        for index,line in enumerate(lines[1:]):
            self.assertEqual(line.split()[0],f'sn{index:03d}')
            self.assertEqual(len(line.split()),9)

    def test_holes_overlaps_and_reduced_apron_rejected(self):
        baseline=json.loads(LAYOUT.read_text())
        bad=copy.deepcopy(baseline);bad['regions'][0]['core'][1][0]-=1
        with self.assertRaises(ValueError):validate_layout(bad)
        bad=copy.deepcopy(baseline);bad['regions'][0]['core'][1][0]+=1
        with self.assertRaises(ValueError):validate_layout(bad)
        bad=copy.deepcopy(baseline);bad['regions'][0]['coverage'][1][0]-=1
        with self.assertRaisesRegex(ValueError,'apron'):validate_layout(bad)
        bad=copy.deepcopy(baseline);bad['hysteresis']=0
        with self.assertRaisesRegex(ValueError,'policy'):validate_layout(bad)

    def test_normal_converter_builds_all_worlds_before_aliasing_source(self):
        self.run_convert(1)

    def run_convert(self, jobs):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);maps=root/'id1/maps';maps.mkdir(parents=True)
            raw=repeated_geometry();source=maps/'seyda.bsp';source.write_bytes(raw)
            land=root/'seyda.map';land.write_text('fixture source map')
            palette=root/'id1/gfx/palette.lmp';palette.parent.mkdir();palette.write_bytes(bytes(768))
            calls=[]
            def builder(source_map,texture_bsp,source_bsp,palette_path,coverage,out_dir,
                        ericw_bin,target_sizes,*,core=None,threads=1):
                self.assertEqual(Path(source_bsp).read_bytes(),raw)
                self.assertEqual(source.read_bytes(),raw) # Never overwrite mid-generation.
                self.assertNotEqual(Path(source_bsp).parent,maps)
                out=Path(out_dir);out.mkdir();target=out/'candidate.bsp';target.write_bytes(raw)
                calls.append((out.name,coverage,core))
                return {'candidate_path':str(target),'candidate_sha256':hashlib.sha256(raw).hexdigest(),
                        'heap_estimate':None,'world_collision_samples':{'fixture':True}}
            with patch('prepare_bounded_world.build_candidate',side_effect=builder), \
                 patch('canonical_land_reference.CanonicalLand'), \
                 patch('cull_bsp_terrain.cull_bsp',side_effect=lambda raw,policy,**kw:(raw,{'policy':policy,'unchanged':True,'fixture':True})), \
                 patch('subprocess.run',side_effect=AssertionError('No compiler allowed in source test')):
                report=convert(source,maps,source_map=land,palette=palette,ericw_bin=root/'unused',jobs=jobs,
                               canonical_land_source=root/'synthetic-land.npz',terrain_cull_config={'default':True,'overlap':.5,
                                  'cells':{'Seyda Neen':{'overlap':1.}},
                                  'subcells':{'sn000':{'enabled':False}},
                                  'bsps':{'sn001.bsp':{'overlap':0.}}})
            self.assertEqual(len(calls),66)
            first,second=report['regions'][:2]
            self.assertFalse(first['bounded']['terrain_visual_cull']['policy']['enabled'])
            self.assertEqual(first['bounded']['terrain_visual_cull']['policy']['overlap'],1.)
            self.assertEqual(second['bounded']['terrain_visual_cull']['policy']['overlap'],0.)
            self.assertEqual(second['bounded']['terrain_visual_cull']['policy']['overlap_provenance'],'bsps')
            if jobs==1:  # serial call order; parallel order is free, results are not
                self.assertEqual([name for name,_,_ in calls[:64]],[f'sn{i:03d}' for i in range(64)])
                self.assertEqual([name for name,_,_ in calls[64:]],['intro_docks','sncourt'])
            self.assertEqual(len(list(maps.glob('*.bsp'))),67)
            self.assertEqual(source.read_bytes(),(maps/'sn029.bsp').read_bytes())
            self.assertEqual(Path(report['complete_source_preserved']).read_bytes(),raw)
            self.assertEqual(report['regular_regions'],64)
            self.assertEqual((maps.parent/'seyda-regions.txt').read_text(),directory_text(regions()))
            report=json.loads(json.dumps(report).replace(str(root),'<root>'))
            return report,{p.name:p.read_bytes() for p in sorted(maps.glob('*.bsp'))},sorted(calls)

    def test_regions_compile_in_the_pool_with_serial_results(self):
        # BUILD-IMAGE-SERIAL-32: regions run side by side in the shared pool
        # (thread pool stand-in here, so the mocked builder applies).
        from concurrent.futures import ThreadPoolExecutor
        import build_parallel
        sizes=[]
        def pool(count):
            sizes.append(count);return ThreadPoolExecutor(max_workers=count)
        serial=self.run_convert(1)
        with patch.object(build_parallel,'process_pool',side_effect=pool):
            parallel=self.run_convert(5)
        self.assertEqual(sizes,[5])
        self.assertEqual(serial,parallel)

    def test_generation_failure_leaves_existing_runtime_map_untouched(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);maps=root/'maps';maps.mkdir()
            source=maps/'seyda.bsp';raw=repeated_geometry();source.write_bytes(raw)
            with patch('prepare_bounded_world.build_candidate',side_effect=ValueError('terrain failure')):
                with self.assertRaisesRegex(ValueError,'terrain failure'):
                    convert(source,maps,source_map=root/'source.map',palette=root/'palette',ericw_bin=root/'unused',terrain_visual_cull=False,
                            jobs=1)
            self.assertEqual(source.read_bytes(),raw)
            self.assertEqual([p.name for p in maps.glob('*.bsp')],['seyda.bsp'])


if __name__=='__main__':unittest.main()
