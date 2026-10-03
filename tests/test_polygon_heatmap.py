# SPDX-License-Identifier: GPL-3.0-only
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import generate_polygon_heatmap as heat


def fixture():
    data=[b'' for _ in range(15)]
    data[0]=b'{"classname" "worldspawn"}\n{"model" "*1" "origin" "10 0 0" "angles" "0 90 0"}\n{"model" "*1" "origin" "20 0 0"}\0'
    data[3]=b''.join(struct.pack('<3f',*p) for p in [(0,0,0),(4,0,0),(4,4,0),(0,4,0)])
    data[7]=struct.pack('<Hhihh4Bi',0,0,0,4,0,0,0,0,0,-1)
    data[12]=b''.join(struct.pack('<HH',*p) for p in [(0,1),(1,2),(2,3),(3,0)])
    data[13]=struct.pack('<4i',0,1,2,3)
    data[14]=struct.pack('<9f7i',*([0]*14+[0,1]))*2
    header=bytearray(struct.pack('<i',29)+bytes(120));body=bytearray()
    for i,part in enumerate(data):
        struct.pack_into('<ii',header,4+i*8,124+len(body),len(part));body.extend(part)
    return bytes(header+body)


class PolygonHeatmapTest(unittest.TestCase):
    def test_shared_face_records_count_each_placed_rotated_instance(self):
        samples,disk=heat.polygon_samples(fixture())
        self.assertEqual(disk,1)
        self.assertEqual(list(samples),[([2.,2.],2),([8.,2.],2),([22.,2.],2)])

    def test_negative_world_bins_half_open_cores_overlap_not_sum(self):
        regions=[{'core':[[-8,-8],[0,0]],'coverage':[[-8,-8],[8,8]]},
                 {'core':[[0,0],[8,8]],'coverage':[[-8,-8],[8,8]]}]
        data=heat.aggregate([([0,0],2),([4,4],3)],[-4,-4],1,4,regions)
        self.assertEqual(data['bins'],[[-1,-1,1,2],[0,0,1,3]])
        self.assertEqual(data['region_centroid_counts'],[[1,2],[1,2]])
        self.assertEqual(data['placed_polygons'],2)
        self.assertEqual(sum(r[1] for r in data['region_centroid_counts']),4)

    def test_output_is_numeric_bins_and_allowlisted_metadata_no_assets(self):
        with tempfile.TemporaryDirectory() as temp:
            Path(temp,'synthetic.bsp').write_bytes(fixture())
            config={'title':'Synthetic </script>','texture':'SECRET_TEXTURE','vertices':['SECRET_VERTEX'],
                    'views':[{'name':'sample','bsp':'synthetic.bsp','centre':[0,0],'scale':1,'secret':'SECRET_ENTITY'}]}
            data=heat.generate(config,temp)
        text=heat.render(data)
        for forbidden in ('SECRET_TEXTURE','SECRET_VERTEX','SECRET_ENTITY','data:image','base64','synthetic.bsp'):
            self.assertNotIn(forbidden,text)
        self.assertIn('\\u003c/script>',text)
        self.assertEqual(data['views'][0]['placed_polygons'],3)
        self.assertNotIn('vertices',json.dumps(data))

    def test_malformed_indices_and_scales_rejected(self):
        raw=bytearray(fixture());offset=struct.unpack_from('<i',raw,4+12*8)[0]
        struct.pack_into('<H',raw,offset,65535)
        samples,_=heat.polygon_samples(raw)
        with self.assertRaises(ValueError):list(samples)
        with self.assertRaises(ValueError):heat.aggregate([], [0,0],0,4,[])
        with self.assertRaises(ValueError):heat.polygon_samples(b'not a BSP')

    def test_mosaic_owns_each_centroid_once_excludes_aprons_reports_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            Path(temp,'shared.bsp').write_bytes(fixture())
            sources=[{'name':name,'bsp':'shared.bsp','centre':[0,0],'scale':1,
                      'core':core,'coverage':[[-30,-30],[30,30]]}
                     for name,core in [('left',[[0,0],[4,4]]),('right',[[4,0],[24,4]])]]
            sources.append({'name':'missing','bsp':'absent.bsp','centre':[0,0],'scale':1,
                            'core':[[24,0],[30,4]],'coverage':[[24,0],[30,4]]})
            result=heat.mosaic({'name':'union','sources':sources},temp,4)
            self.assertEqual(result['placed_polygons'],3)
            self.assertEqual(result['triangle_equivalent'],6)
            self.assertEqual(result['region_centroid_counts'],[[1,None],[2,None],[None,None]])
            self.assertEqual(result['missing_regions'],['missing'])
            self.assertEqual(result['available_regions'],2)
            sources[1]['core']=[[2,0],[24,4]]
            with self.assertRaisesRegex(ValueError,'overlap'):heat.mosaic({'name':'bad','sources':sources},temp,4)

    def test_world_directory_origin_units_and_length(self):
        raw=b'AWR2'+struct.pack('<I',1)+bytes(56)+struct.pack('<8s11f',b'vf0000',2048,-2048,0,-1024,-1024,1024,1024,-1920,-1920,1920,1920)
        entry=heat.read_world_directory(raw)[0]
        self.assertEqual(entry['centre'],[8192,-8192])
        self.assertEqual(heat.world(entry['core'][0],entry['centre'],entry['scale']),[4096,-12288])
        with self.assertRaises(ValueError):heat.read_world_directory(raw[:-1])


if __name__=='__main__':unittest.main()
