"""Declared original-cell cores differ from terrain apron/render ownership."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import cell_progress_chim as CH
import cell_progress as CP

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value))

def world(root,with_stats=True):
    frame={'cell':[0,0],'centre':[0,0],'grain':256,'low':[-256,-256],
           'nx':18,'ny':10,'owned_total':2,'sector_chunks':3}
    write(root/'chim-receipt.json',{'areas':['synthetic'],'frames':[{'frame':frame}],
                                   'models':7,'placements':11,'source_placements':2})
    geometry={'source_cell':[0,0],'centre':[0,0],'scale':.25,
              'bounds':[[0,0],[4096,2048]],'owned_cells':[[0,0],[2,1]]}
    write(root/'work/synthetic/source-receipt.json',{'geometry':geometry})
    refs=[{'number':1,'type':'STAT'},{'number':2,'type':'CONT'},{'number':3,'type':'NPC_'}]
    def owner(n,cell,role):
        return {'master':'Morrowind.esm','reference':n,'physical_cell':cell,'role':role}
    catalogue={'references':refs,'deferred':[refs[2]],'ownership':{
        'owned_references':[owner(1,[0,0],'owned_origin'),owner(3,[1,0],'owned_origin')],
        'dependency_references':[owner(2,[-1,0],'footprint_or_assembly_dependency')]}}
    write(root/'work/synthetic/source-catalogue.json',catalogue)
    if with_stats:
        rows=[]
        for i in range(frame['nx']):
            for j in range(frame['ny']):
                cell=CH.cell_of(frame,-256+(i+.5)*256,-256+(j+.5)*256)
                owned=1 if (i,j) in [(0,1),(1,1)] else 0
                rows.append({'frame':CH.frame_path([0,0]),'cell':[i,j],'owned':owned,
                             'terrain_faces':2,'placed_faces':owned*5,'bytes':64})
        write(root/'chim-stats.json',{'chunks':{'per_chunk':rows},'build':{'cpu_seconds':12.5},
                                      'memory':{'model_zone_peak_bytes':4096},'disk':{'bytes':9999}})
    return frame

class DeclaredCoreTests(unittest.TestCase):
    def test_empty_owned_cell_converts_apron_dependency_does_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);world(root)
            digest=CH.digest('test',root)
            converted={k for k,e in digest['cells'].items() if e['converted']}
            self.assertEqual(converted,{'0,0','1,0'})
            self.assertFalse(digest['cells']['-1,0']['converted'])
            self.assertGreater(digest['cells']['-1,0']['owned'],0)
            self.assertEqual(digest['cells']['1,0']['owned'],0)
            self.assertEqual(digest['models'],7);self.assertEqual(digest['placements'],11)
            self.assertNotIn('models',digest['cells']['0,0'])

    def test_reference_types_and_deferred_counts_are_actual_not_render_totals(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);world(root);d=CH.digest('test',root)
            self.assertEqual(d['cells']['0,0']['source_references']['owned_by_type'],{'STAT':1})
            self.assertEqual(d['cells']['1,0']['source_references']['owned_by_type'],{'NPC_':1})
            self.assertEqual(d['cells']['1,0']['source_references']['deferred_by_type'],{'NPC_':1})
            self.assertEqual(d['cells']['-1,0']['source_references']['dependency_by_type'],{'CONT':1})
            self.assertEqual(d['frame_ownership'][0]['deferred_by_type'],{'NPC_':1})

    def test_no_stats_keeps_core_but_unknown_chunk_statistics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);world(root,False);d=CH.digest('test',root)
            self.assertEqual({k for k,e in d['cells'].items() if e['converted']},{'0,0','1,0'})
            self.assertIsNone(d['cells']['1,0']['chunks'])
            self.assertIsNone(d['cells']['1,0']['bytes'])

    def test_unknown_catalogue_does_not_become_zero_reference_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);world(root)
            (root/'work/synthetic/source-catalogue.json').unlink()
            d=CH.digest('test',root)
            self.assertNotIn('source_references',d['cells']['0,0'])
            self.assertNotIn('source_references_by_type',d['frame_ownership'][0])

    def test_wrong_transform_or_partial_grid_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);world(root);path=root/'work/synthetic/source-receipt.json'
            source=json.loads(path.read_text());source['geometry']['bounds'][1][0]-=1;write(path,source)
            with self.assertRaisesRegex(ValueError,'aligned'):CH.digest('test',root)
            world(root);path=root/'chim-receipt.json';doc=json.loads(path.read_text())
            doc['frames'][0]['frame']['nx']=8;write(path,doc)
            with self.assertRaisesRegex(ValueError,'cover'):CH.digest('test',root)

    def test_duplicate_and_incomplete_original_ownership_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);world(root);path=root/'work/synthetic/source-catalogue.json'
            cat=json.loads(path.read_text());cat['ownership']['owned_references'].append(cat['ownership']['owned_references'][0]);write(path,cat)
            with self.assertRaisesRegex(ValueError,'Duplicate'):CH.digest('test',root)
            world(root);cat=json.loads(path.read_text());cat['ownership']['dependency_references']=[];write(path,cat)
            with self.assertRaisesRegex(ValueError,'incomplete'):CH.digest('test',root)

    def test_historical_undeclared_build_keeps_existing_predicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);world(root)
            (root/'work/synthetic/source-receipt.json').unlink()
            d=CH.digest('test',root)
            self.assertTrue(d['cells']['-1,0']['converted'])
            self.assertFalse(d['cells']['1,0']['converted'])
            self.assertEqual(d['frame_ownership'],[])

    def test_frame_totals_not_repeated_in_cell_stats(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);world(root);d=CH.digest('test',root)
            cells={k:{'chim':{'converted':v['converted']},'contents':None,'provenance':None,'spiral_rank':None} for k,v in d['cells'].items()}
            digest_cell={k:(d,e) for k,e in d['cells'].items() if e['converted']}
            CP.assemble_stats(cells,{}, {},digest_cell,{})
            for cell in cells.values():
                self.assertNotIn('memory',cell['stats']);self.assertNotIn('time',cell['stats'])
                self.assertNotIn('models',cell['stats'])
            self.assertEqual(d['run_stats']['build_cpu_s'],12.5)
            self.assertEqual(d['run_stats']['model_zone_peak_bytes'],4096)
            self.assertEqual(d['run_stats']['world_bytes'],9999)
            self.assertEqual(cells['1,0']['stats']['source_references']['deferred_by_type'],{'NPC_':1})

    def test_adjacent_core_owners_and_dependency_copies_union_original_identities(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);frame=world(root)
            receipt=json.loads((root/'chim-receipt.json').read_text())
            other=dict(frame,cell=[2,0],centre=[16384,0])
            receipt['areas'].append('adjacent');receipt['frames'].append({'frame':other})
            write(root/'chim-receipt.json',receipt)
            source=json.loads((root/'work/synthetic/source-receipt.json').read_text())
            source['geometry'].update(source_cell=[2,0],centre=[16384,0],owned_cells=[[2,0],[4,1]])
            write(root/'work/adjacent/source-receipt.json',source)
            path=root/'work/synthetic/source-catalogue.json';cat=json.loads(path.read_text())
            cat['ownership']['owned_references'][0]['physical_cell']=[1,0]
            cat['ownership']['owned_references'][1]['physical_cell']=[0,0]
            cat['ownership']['dependency_references'][0]['physical_cell']=[2,0]
            write(path,cat)
            def own(n,cell):return {'master':'Morrowind.esm','reference':n,'physical_cell':cell}
            adjacent={'references':[{'number':1,'type':'STAT'},{'number':2,'type':'CONT'},{'number':4,'type':'STAT'}],
                      'deferred':[],'ownership':{'owned_references':[own(2,[2,0]),own(4,[3,0])],
                                                'dependency_references':[own(1,[1,0])]}}
            write(root/'work/adjacent/source-catalogue.json',adjacent)
            stats=json.loads((root/'chim-stats.json').read_text())
            for i in range(other['nx']):
                for j in range(other['ny']):
                    stats['chunks']['per_chunk'].append({'frame':CH.frame_path([2,0]),'cell':[i,j],
                                                         'owned':1 if (i,j)==(1,1) else 0,
                                                         'terrain_faces':2,'placed_faces':0,'bytes':64})
            write(root/'chim-stats.json',stats);d=CH.digest('adjacent',root)
            self.assertEqual({k for k,e in d['cells'].items() if e['converted']},{'0,0','1,0','2,0','3,0'})
            source=[e['source_references'] for e in d['cells'].values() if 'source_references' in e]
            self.assertEqual(sum(sum(c['owned_by_type'].values()) for c in source),4)
            self.assertEqual(sum(sum(c['dependency_by_type'].values()) for c in source),0)
            self.assertEqual(sum(sum(c['unique_by_type'].values()) for c in source),4)
            self.assertEqual(d['cells']['1,0']['source_references']['owned_by_type'],{'STAT':1})
            dep=d['cells']['1,0']['source_references']['dependency_by_frame'][CH.frame_path([2,0])]
            self.assertEqual(dep['by_type'],{'STAT':1});self.assertEqual(dep['unique_reference_count'],1)
            self.assertEqual(len(dep['identity_union_sha256']),64)
            self.assertEqual([f['dependency_references'] for f in d['frame_ownership']],[1,1])

if __name__=='__main__':
    unittest.main()
