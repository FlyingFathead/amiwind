# SPDX-License-Identifier: GPL-3.0-only
from pathlib import Path
import hashlib,json,struct,sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from install_world_terrain import install

def digest(raw): return hashlib.sha256(raw).hexdigest()
def entry(i,raw):
    return {'name':f'vf{i:04d}','origin':[i*1024,0,0],
            'core':[[-512,-512],[512,512]],'coverage':[[-1408,-1408],[1408,1408]],
            'converted':{'bytes':len(raw),'sha256':digest(raw)}}
def packet(rows):
    return b'AWR2'+struct.pack('<I',len(rows))+bytes(56)+b''.join(
        struct.pack('<8s11f',r['name'].encode(),*r['origin'],*r['core'][0],*r['core'][1],
                    *r['coverage'][0],*r['coverage'][1]) for r in rows)

class TerrainInstallTests(unittest.TestCase):
    def fixture(self,root):
        terrain=root/'terrain';id1=root/'id1'
        (id1/'maps').mkdir(parents=True);(id1/'world').mkdir()
        old=[entry(0,b'old')];old_packet=packet(old)
        (id1/'world/regions.awr').write_bytes(old_packet)
        (id1/'maps/vf0000.bsp').write_bytes(b'old')
        rows=[entry(0,b'child0'),entry(1,b'child1')];new_packet=packet(rows)
        terrain.mkdir()
        base=(json.dumps({'regions':old})+'\n').encode()
        (terrain/'base-world-regions.json').write_bytes(base)
        for i,row in enumerate(rows):
            (terrain/row['name']).mkdir();(terrain/row['name']/'scene.bsp').write_bytes(f'child{i}'.encode())
        (terrain/'regions.awr').write_bytes(new_packet)
        receipt={'format':'AmiWind playable terrain regions 1','diagnostic_subset':False,
            'regions':rows,'refinement':{'children':['vf0000','vf0001'],
            'base_directory_sha256':digest(old_packet),'directory_sha256':digest(new_packet),
            'base_regions_receipt_sha256':digest(base)}}
        (terrain/'world-regions.json').write_text(json.dumps(receipt))
        return terrain,id1,old_packet
    def test_complete_refinement_and_verified_reuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            terrain,id1,_=self.fixture(Path(tmp))
            self.assertEqual(install(terrain,id1)['replaced_maps'],2)
            self.assertEqual(install(terrain,id1)['replaced_maps'],0)
    def test_later_bad_payload_cannot_partially_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            terrain,id1,original=self.fixture(Path(tmp))
            (terrain/'vf0001/scene.bsp').write_bytes(b'changed')
            with self.assertRaises(ValueError):install(terrain,id1)
            self.assertEqual((id1/'maps/vf0000.bsp').read_bytes(),b'old')
            self.assertEqual((id1/'world/regions.awr').read_bytes(),original)
    def test_parent_changed_refused_before_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            terrain,id1,original=self.fixture(Path(tmp))
            (id1/'maps/vf0000.bsp').write_bytes(b'not the audited parent')
            with self.assertRaises(ValueError):install(terrain,id1)
            self.assertFalse((id1/'maps/vf0001.bsp').exists())
            self.assertEqual((id1/'world/regions.awr').read_bytes(),original)

if __name__=='__main__':unittest.main()
