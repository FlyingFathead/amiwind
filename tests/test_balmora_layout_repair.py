import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from balmora_regions import config, regions, owner
from repair_balmora_maps import repair


class LayoutTests(unittest.TestCase):
    def test_measured_split_reuses_slot_and_keeps_arrival(self):
        s=config();es=regions(s)
        self.assertEqual(len(es),64)
        self.assertEqual(es[1]['core'],[[-768,-640],[0,0]])
        self.assertEqual(es[27]['core'],[[-768,-768],[0,-640]])
        self.assertEqual(owner([-209,-1486],es),19)
        self.assertEqual(owner([-384,-700],es),27)
        self.assertEqual(owner([-384,-600],es),1)
        for y in range(-3072,3072,64):
            for x in range(-3072,3072,64):
                self.assertIsNotNone(owner([x+.5,y+.5],es))

    def test_holes_overlaps_and_unknown_names_rejected(self):
        for change in ('hole','overlap','unknown'):
            s=config()
            if change=='hole':s['region_core_overrides']['bm027'][1][1]=-768
            if change=='overlap':s['region_core_overrides']['bm027'][1][1]=-512
            if change=='unknown':s['region_core_overrides']['bm099']=[[0,0],[128,128]]
            with self.assertRaises(ValueError):regions(s)

    def fixture(self,root):
        maps=root/'id1/maps';maps.mkdir(parents=True)
        for e in regions(config()):(maps/(e['name']+'.bsp')).write_bytes(e['name'].encode())
        (maps/'balmora.bsp').write_bytes(b'bm019')
        lines=['AWBR1 64 96 540 -209 -1486 311 90 645 385 246 67']
        lines += [e['name']+' '+' '.join(map(str,[*e['core'][0],*e['core'][1],*e['coverage'][0],*e['coverage'][1]])) for e in regions(config())]
        (maps.parent/'balmora-regions.txt').write_text('\n'.join(lines)+'\n')
        cache=root/'cache';(cache/'scenery').mkdir(parents=True)
        (cache/'scenery/scenery-index.json').write_text('{"references":[]}')
        return maps,cache

    def test_prepare_failure_leaves_all_originals(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);maps,cache=self.fixture(root)
            before={p:p.read_bytes() for p in maps.parent.rglob('*') if p.is_file()}
            with patch('repair_balmora_maps.rebuild_cached_region',side_effect=ValueError('fixture failure')):
                with self.assertRaisesRegex(ValueError,'fixture failure'):
                    repair(maps,cache=cache,palette=root/'palette',ericw_bin=root,work_dir=root/'work',threads=1)
            self.assertEqual(before,{p:p.read_bytes() for p in before})
            self.assertEqual(json.loads((root/'work/balmora-repair.json').read_text())['status'],'failed')

    def test_success_writes_all_maps_and_metadata_together(self):
        def rebuilt(cache,source,palette,entry,settings,out,bin,threads=4):
            out.mkdir();p=out/(entry['name']+'.bsp');p.write_bytes(('new-'+entry['name']).encode())
            return {'candidate_path':str(p)}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);maps,cache=self.fixture(root)
            with patch('repair_balmora_maps.rebuild_cached_region',side_effect=rebuilt),patch('repair_balmora_maps.bound_visuals',side_effect=lambda raw,bounds:(raw+b'-bounded',{})):
                result=repair(maps,cache=cache,palette=root/'palette',ericw_bin=root,work_dir=root/'work',threads=1)
            self.assertEqual(result['status'],'complete')
            self.assertEqual((maps/'balmora.bsp').read_bytes(),(maps/'bm019.bsp').read_bytes())
            self.assertEqual(len(result['output_hashes']),66)
            self.assertIn('bm001 -768 -640 0 0 ',(maps.parent/'balmora-regions.txt').read_text())


    def test_regions_run_in_the_pool_with_serial_results(self):
        # dev3-r2 profile: the three Balmora rebuilds ran one after another (2.6 cores).
        from concurrent.futures import ThreadPoolExecutor
        import build_parallel
        calls=[];sizes=[]
        def rebuilt(cache,source,palette,entry,settings,out,bin,threads=None):
            calls.append((entry['name'],threads))
            out.mkdir();p=out/(entry['name']+'.bsp');p.write_bytes(('new-'+entry['name']).encode())
            return {'candidate_path':str(p)}
        def pool(count):
            sizes.append(count);return ThreadPoolExecutor(max_workers=count)
        results=[]
        for threads in (1,9):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);maps,cache=self.fixture(root)
                with patch('repair_balmora_maps.rebuild_cached_region',side_effect=rebuilt),\
                     patch('repair_balmora_maps.bound_visuals',side_effect=lambda raw,bounds:(raw+b'-bounded',{'b':len(raw)})),\
                     patch.object(build_parallel,'process_pool',side_effect=pool),\
                     contextlib.redirect_stdout(io.StringIO()) as log:
                    result=repair(maps,cache=cache,palette=root/'palette',ericw_bin=root,work_dir=root/'work',threads=threads)
                text=json.dumps(result).replace(str(root),'<root>')
                results.append((text,{p.name:p.read_bytes() for p in sorted(maps.iterdir())},log.getvalue()))
        self.assertEqual(results[0],results[1])
        self.assertEqual(sizes,[3,9])  # the three rebuilds side by side, then 61 bounded regions
        self.assertEqual(sorted(calls[3:]),[('bm000',3),('bm001',3),('bm027',3)])  # 9 // 3 vis/model threads each


if __name__=='__main__':unittest.main()
