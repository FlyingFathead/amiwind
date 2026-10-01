"""Survey partitions and source-aligned terrain boundaries, without game data."""
import json
from pathlib import Path
import tempfile
import unittest
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from prepare_world_regions import plan, Terrain, map_text
from world_volumes import balanced


class WorldRegionsTests(unittest.TestCase):
    def test_measured_splits_stable_names_and_matching_shared_vertices(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            def cell(x,split):
                return dict(cell=[x,0],screen=dict(candidate=split),unresolved_placements=0,
                            name='',region='Test')
            report=dict(format='AmiWind world survey 1',terrain=dict(height_seams=[]),
                        settings=dict(overlap_runtime=896),cells=[cell(0,2),cell(-1,1)])
            (root/'world-survey.json').write_text(json.dumps(report))
            _,entries=plan(root)
            self.assertEqual(len(entries),5)
            self.assertEqual([e['name'] for e in entries],[f'vf{i:04d}' for i in range(5)])
            self.assertEqual(entries[0]['cell'],[-1,0])
            terrain=Terrain.__new__(Terrain)
            terrain.cells={(-1,0):0,(0,0):1}
            terrain.heights=np.zeros((2,65,65),np.float32)
            terrain.materials=np.ones((2,16,16),np.uint16)
            for index in range(2):
                for x in range(65):terrain.heights[index,:,x]=(index*64+x)*4
            self.assertEqual(terrain.sample(-32,64)[0],63)
            self.assertEqual(terrain.sample(0,64)[0],64)
            self.assertEqual(terrain.sample(2048,64)[0],128)
            self.assertEqual(terrain.sample(-4096,64),(-512.,0))
            for entry in entries:
                text=map_text(entry,terrain)
                self.assertIn('"info_player_start"',text)
                ox,oy,oz=entry['origin']
                for x in range(entry['coverage'][0][0],entry['coverage'][1][0]+1,128):
                    self.assertEqual((x+ox)%128,0)

    def test_two_partition_balance_includes_boot_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);paths=[]
            for index in range(5):
                p=root/f'vf{index:04d}.bsp';p.write_bytes(bytes(4));paths.append(p)
            self.assertEqual(balanced(reversed(paths),4,12),(paths[:2],paths[2:]))
            self.assertEqual(balanced(paths,20,20),([],paths))
            with self.assertRaisesRegex(ValueError,'two-partition budget'):balanced(paths,4,11)


if __name__=='__main__':unittest.main()
