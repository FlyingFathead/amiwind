# SPDX-License-Identifier: GPL-3.0-only
import base64
import hashlib
from pathlib import Path
import shutil
import tempfile
import unittest

import build_aga
import check_world_map_heap as heap
import compact_harvest_heap as compact
import harvest_heap
from test_harvest_heap import TARGET,payload
from test_check_world_map_heap import make_bsp

COMPACT=dict(TARGET,harvest_storage_mode=1,harvest_runtime_static=140,harvest_proxy_static=64,
    harvest_catalogue_extension=0,harvest_model_record=58,harvest_node_record=24,
    harvest_edge_record=12,harvest_plant_record=54,harvest_node_capacity=64,
    harvest_edge_capacity=256,harvest_plant_capacity=256,harvest_model_capacity=8,
    harvest_text_capacity=65535,harvest_storage_policy_verified=1,harvest_allocator_mode=1)


def dense_catalogue(path,count):
    lines=path.read_text().splitlines();header=lines[0].split()
    original=int(header[3]);assert original==1
    start=1+int(header[6])+int(header[1])+int(header[2]);plant=lines[start].split(maxsplit=14)
    header[3]=str(count);header[4]='4096';output=[' '.join(header),*lines[1:start]]
    for i in range(count):
        values=plant[:];values[0]='aw:h:'+base64.b32encode(hashlib.sha256(str(i).encode()).digest()).decode().lower().rstrip('=')
        values[1]=str(i+1);values[2]=str(i+100);output.append(' '.join(values))
    path.write_text('\n'.join(output)+'\n')


class CompactHarvestHeapTests(unittest.TestCase):
    def test_empty_map_allocates_no_dynamic_harvest_storage(self):
        with tempfile.TemporaryDirectory() as td:
            maps=Path(td)/'maps';maps.mkdir();(maps/'town.bsp').write_bytes(make_bsp())
            row=heap.inspect_maps(maps,COMPACT)['maps'][0]
            self.assertEqual(row['additional_static_allowance_bytes'],204)
            self.assertEqual(row['additional_external_allocation_allowance_bytes'],0)
            self.assertEqual(row['harvest_external']['catalogue_requested_bytes'],0)
            self.assertEqual(row['harvest_external']['all_available_binding_bytes'],0)

    def test_dense_growth_and_shared_model_are_not_a_global_static_array(self):
        with tempfile.TemporaryDirectory() as td:
            root=payload(Path(td));path=root/'harvest-town.txt'
            one=harvest_heap.profile(root,COMPACT);dense_catalogue(path,77)
            dense=harvest_heap.profile(root,COMPACT);row=dense['catalogues'][0]
            self.assertEqual(row['plants'],77);self.assertEqual(row['all_available_binding_bytes'],77*187)
            self.assertEqual(dense['unique_models'],1)
            self.assertEqual(one['global_warm_cache_ceiling_bytes'],dense['global_warm_cache_ceiling_bytes'])
            self.assertEqual(one['additional_static_allowance_bytes'],dense['additional_static_allowance_bytes'])
            self.assertGreater(row['catalogue_requested_bytes'],one['catalogues'][0]['catalogue_requested_bytes'])
            self.assertGreater(row['catalogue_growth']['requested_bytes'],row['catalogue_requested_bytes'])
            with self.assertRaisesRegex(ValueError,'counts'):build_aga.harvest_fingerprint_entries(root,plant_capacity=24)
            self.assertEqual(len(build_aga.harvest_fingerprint_entries(root,plant_capacity=256)),2)
            # The exact node/edge count is input-dependent; use the header token.
            lines=path.read_text().splitlines();header=lines[0].split();header[3]='257';lines[0]=' '.join(header)
            path.write_text('\n'.join(lines)+'\n')
            with self.assertRaises(ValueError):harvest_heap.profile(root,COMPACT)

    def test_malloc_and_static_are_in_total_allowance_not_hunk_ceiling(self):
        with tempfile.TemporaryDirectory() as td:
            root=payload(Path(td));result=heap.inspect_maps(root/'maps',COMPACT);row=result['maps'][0]
            extra=row['additional_external_allocation_allowance_bytes']
            self.assertGreater(extra,row['harvest_external']['external_malloc_requested_peak_bytes'])
            expected=row['peak_loader_bytes']+result['baseline_reserve_bytes']+result['safety_headroom_bytes']+204+extra
            self.assertEqual(row['estimated_total_bytes'],expected)
            receipt=Path(td)/'heap.json';receipt.write_text('{}')
            summary=build_aga.heap_watcher_summary(result,receipt)
            self.assertEqual(summary['estimated_committed_with_reserves_bytes'],expected)
            self.assertEqual(summary['estimated_growth_margin_after_reserves_bytes'],result['heap_budget_bytes']-expected)

    def test_legacy_brush_bindings_and_shared_strings_are_counted(self):
        raw=('AWH3 1 1 2 2 '+'a'*64+'\n0 0 0 0 0 ingredient\tSame name\n0 0 2\n'+
             'aw:h:'+'a'*52+' 1 11 *1 1 0 1 0 0 0 0 0 0 Same name\n'+
             'aw:h:'+'b'*52+' 2 12 *2 1 0 1 1 0 0 0 0 0 Same name\n').encode()
        row=compact.catalogue_usage(raw,COMPACT)
        self.assertEqual(row['interned_strings'],6)
        self.assertEqual(row['dictionary_bytes'],1+11+10+58+58+3+3)
        self.assertEqual(row['array_bytes'],24+12+2*54)
        self.assertEqual(row['all_available_binding_bytes'],2*5)
        self.assertEqual(compact.catalogue_usage(b'AWH1 0 0 0\n',COMPACT)['resident']['requested_bytes'],0)

    def test_allocator_and_runtime_policy_are_required_and_source_bound(self):
        with tempfile.TemporaryDirectory() as td:
            root=payload(Path(td))
            for key in ('harvest_allocator_mode','harvest_storage_policy_verified'):
                sizes=dict(COMPACT);sizes[key]=0
                with self.assertRaisesRegex(ValueError,'policies'):harvest_heap.profile(root,sizes)
            engine=Path(td)/'engine';(engine/'src').mkdir(parents=True)
            for name in ('aw_harvest.h','aw_harvest.c','aw_harvest_proxy.c','aw_harvest_runtime.c'):
                shutil.copyfile(heap.ROOT/'engine/aga/src'/name,engine/'src'/name)
            self.assertEqual(compact.runtime_policy(engine)['mode'],'compact_offsets')
            path=engine/'src/aw_harvest_proxy.c';path.write_text(path.read_text().replace('allocated_bytes=visible*','allocated_bytes=1024+visible*'))
            with self.assertRaisesRegex(ValueError,'allocation policy'):compact.runtime_policy(engine)

    def test_allocator_granularity_and_direct_large_blocks(self):
        small=compact.allocation_cost([1,16,17])
        self.assertEqual(small['requested_bytes'],34)
        self.assertEqual(small['rounded_live_blocks_bytes'],32+32+48)
        self.assertEqual(small['conservative_new_os_reservation_bytes'],3*(32760+3080))
        large=compact.allocation_cost([40000]);self.assertEqual(large['rounded_live_blocks_bytes'],40016)
        self.assertEqual(large['conservative_new_os_reservation_bytes'],40020)

    def test_harvest_lifetime_sources_reject_stale_engine_receipts(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);hashes={}
            for relative in build_aga.HEAP_LOADER_SOURCE_PATHS:
                path=root/relative;path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text('original');hashes[relative]=hashlib.sha256(path.read_bytes()).hexdigest()
            for relative in ('src/aw_harvest.h','src/aw_harvest.c','src/aw_harvest_runtime.c','src/aw_harvest_proxy.c'):
                self.assertIn(relative,hashes)
                path=root/relative;path.write_text('changed')
                with self.assertRaisesRegex(ValueError,'stale'):
                    build_aga.verify_heap_loader_source_receipt({'source_sha256':hashes},root)
                path.write_text('original')


if __name__=='__main__':unittest.main()
