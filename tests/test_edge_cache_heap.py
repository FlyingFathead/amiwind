# SPDX-License-Identifier: GPL-3.0-only
from pathlib import Path
import struct,tempfile,unittest
from edge_cache_heap import prefix,runtime_policy,SOURCE_HASHES

class EdgeCacheHeapTests(unittest.TestCase):
    def table(self):
        return dict(faces=b''.join(struct.pack('<Hhihh4Bi',0,0,i,1,0,255,255,255,255,-1) for i in range(3)),
            models=struct.pack('<9f7i',*[0]*9,0,0,0,0,0,0,1),nodes=b'',marksurfaces=b'',
            surfedges=struct.pack('<3i',2,-7,9),edges=bytes(10*4))

    def test_sparse_generic_edges_preserve_ids_and_include_all_consumers(self):
        table=self.table();self.assertEqual(prefix(table)['prefix_edges'],3)
        table['marksurfaces']=struct.pack('<H',1);self.assertEqual(prefix(table)['prefix_edges'],8)
        table['nodes']=struct.pack('<i2h6h2H',0,-1,-1,*[0]*6,2,1)
        self.assertEqual(prefix(table)['prefix_edges'],10)
        table['surfedges']=struct.pack('<3i',2,-7,-2147483648)
        with self.assertRaisesRegex(ValueError,'edge index'):prefix(table)
        table=self.table();table['marksurfaces']=struct.pack('<H',3)
        with self.assertRaisesRegex(ValueError,'face span'):prefix(table)

    def test_exact_policy_binding_rejects_renderer_or_loader_changes(self):
        source=Path(__file__).resolve().parents[1]/'engine/aga/src'
        self.assertEqual(runtime_policy(source)['edge_cache_split'],1)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for name in SOURCE_HASHES:(root/name).write_bytes((source/name).read_bytes())
            (root/'r_draw.c').write_text((root/'r_draw.c').read_text()+'\n')
            with self.assertRaisesRegex(ValueError,'Unrecognized'):runtime_policy(root)

    def test_unsorted_map_without_mushrooms_charges_generic_prefix_and_all_slots(self):
        import check_world_map_heap as heap
        from test_check_world_map_heap import make_bsp,SIZES
        table=heap.lump_table(make_bsp(),Path('control'))
        table.update(self.table());table['nodes']=b''
        table['entities']=b'{"classname" "worldspawn"}\n'
        table['marksurfaces']=struct.pack('<H',2)
        header=bytearray(struct.pack('<i',29));body=bytearray();offset=heap.HEADER_SIZE
        for name in heap.RECORDS:
            lump=table[name];header.extend(struct.pack('<ii',offset if lump else 0,len(lump)))
            body.extend(lump);offset+=len(lump)
        with tempfile.TemporaryDirectory() as temp:
            maps=Path(temp);(maps/'plain.bsp').write_bytes(header+body)
            before=heap.inspect_maps(maps,SIZES)['maps'][0]
            after=heap.inspect_maps(maps,dict(SIZES,medge=4,edge_cache_split=1,edge_cache_static=2048))['maps'][0]
        expected=heap.hunk_alloc_bytes(11*4,16)+heap.hunk_alloc_bytes(10*4,16)-heap.hunk_alloc_bytes(11*8,16)
        self.assertEqual(after['edge_cache_residency']['prefix_edges'],10)
        self.assertEqual(after['resident_loader_bytes']-before['resident_loader_bytes'],expected)
        self.assertEqual(after['additional_static_allowance_bytes']-before['additional_static_allowance_bytes'],2048)
        self.assertEqual(after['baseline_reserve_bytes'],before['baseline_reserve_bytes'])
        self.assertEqual(after['safety_headroom_bytes'],before['safety_headroom_bytes'])

if __name__=='__main__':unittest.main()
