import hashlib,json,struct,unittest
from guard_torch_heap import alias_cost,map_cost,apply
from prepare_guard_torches import fingerprint_entries,registry

# Explicit synthetic32-bit layout fixture; production requires the target probe.
SIZES={'aliashdr':48,'maliasframedesc':32,'mdl':84,'stvert':12,'mtriangle':16,
       'maliasskindesc':12,'trivertx':4,'cache_system':40,'hunk':16}

def model():
    header=struct.pack('<4si3f3ff3f8if',b'IDPO',6,1,1,1,0,0,0,1,0,0,0,1,4,4,3,1,8,0,0,1)
    return header+bytes(4+16+36+16)+bytes(8*(28+12))

class GuardTorchHeapTests(unittest.TestCase):
    def test_alias_alignment_cache_and_malloc_are_separate(self):
        row=alias_cost(model(),SIZES)
        self.assertEqual(row['file_bytes'],476)
        self.assertEqual(row['decoded_hunk_bytes'],752)
        self.assertEqual(row['cache_bytes'],800)
        self.assertEqual(row['external_malloc_peak_bytes'],1228)
        self.assertEqual(row['source_file_hunk_fallback_bytes'],496)
        with self.assertRaisesRegex(ValueError,'Actual target'):
            alias_cost(model(),{})

    def test_shared_models_count_once_and_forced_registry_is_conservative(self):
        item=dict(source_id='guard',base_model='progs/base.mdl',body_model='progs/held.mdl',
                  torch_model='progs/held.mdl',auto_inventory_eligible=False)
        prepared={'records':[item],'models':{'progs/held.mdl':alias_cost(model(),SIZES)}}
        entity=b'{"classname" "aw_npc" "aw_source_id" "guard" "model" "progs/base.mdl"}'
        row=map_cost(entity*2,prepared)
        self.assertEqual(row['matching_guard_placements'],2)
        self.assertEqual(row['active_cache_bytes'],800)
        self.assertEqual(row['automatic_cache_bytes'],0)
        self.assertEqual(row['conservative_game_heap_peak_bytes'],2048)
        self.assertEqual(row['admission_probe_bytes'],1024*1024)
        self.assertEqual(row['external_malloc_peak_bytes'],1024*1024)
        self.assertEqual(map_cost(b'{}',prepared)['external_malloc_peak_bytes'],0)
        large={**prepared,'models':{'progs/held.mdl':{**prepared['models']['progs/held.mdl'],'external_malloc_peak_bytes':1200000}}}
        self.assertEqual(map_cost(entity,large)['external_malloc_peak_bytes'],1200000)
        report=dict(peak_loader_bytes=123,resident_loader_bytes=100,resident_bytes_at_peak=100,
                    classifier_allocation_failure_fallback_peak_bytes=123)
        apply(report,row)
        self.assertEqual(report['geometry_and_sprite_peak_before_guard_bytes'],123)
        self.assertEqual(report['peak_loader_bytes'],2171)
        self.assertEqual(report['resident_loader_bytes'],900)

    def test_source_ids_ignore_case_but_model_paths_remain_exact(self):
        item=dict(source_id='GuArD',base_model='progs/base.mdl',body_model='progs/held.mdl',
                  torch_model='progs/held.mdl',auto_inventory_eligible=True)
        prepared={'records':[item],'models':{'progs/held.mdl':alias_cost(model(),SIZES)}}
        entity=b'{"classname" "aw_npc" "aw_source_id" "gUaRd" "model" "progs/base.mdl"}'
        wrong_path=entity.replace(b'progs/base.mdl',b'progs/BASE.mdl')
        row=map_cost(entity*2+wrong_path,prepared)
        self.assertEqual(row['matching_guard_placements'],2)
        self.assertEqual(row['active_cache_bytes'],800)
        self.assertEqual(row['automatic_cache_bytes'],800)
        self.assertEqual(row['conservative_game_heap_peak_bytes'],2048)
        self.assertEqual(map_cost(wrong_path,prepared)['matching_guard_placements'],0)

    def test_absent_optional_assets_retain_legacy_namespace(self):
        self.assertEqual(fingerprint_entries(lambda name:None),[])
        night=b'owned atlas fixture';self.assertEqual(fingerprint_entries(lambda name:night if name=='gfx/aw_night_sky.lmp' else None),
            [('gfx/aw_night_sky.lmp',hashlib.sha256(night).hexdigest())])

    def test_fingerprint_validates_manifest_registry_models_and_base(self):
        digest=lambda raw:hashlib.sha256(raw).hexdigest()
        row=dict(source_id='guard',base_model='progs/base.mdl',body_model='progs/body.mdl',torch_model='progs/torch.mdl',
                 auto_inventory_eligible=True,frames=8,emitters=[[0,0,1]]*8,base_sha256=digest(b'base'))
        assets={'progs/base.mdl':b'base','progs/body.mdl':b'body','progs/torch.mdl':b'torch','gfx/guard-torches.awg':registry([row])}
        report={'format':'AmiWind original guard torch companions 1','records':[row],
                'files':{name:{'bytes':len(raw),'sha256':digest(raw)} for name,raw in assets.items() if name!='progs/base.mdl'}}
        assets['gfx/guard-torches.json']=json.dumps(report).encode()
        result=fingerprint_entries(assets.get)
        self.assertEqual([name for name,_ in result],['gfx/guard-torches.json','gfx/guard-torches.awg','progs/body.mdl','progs/torch.mdl'])
        for changed in ('progs/base.mdl','progs/body.mdl','gfx/guard-torches.awg'):
            corrupt={**assets,changed:b'broken'}
            with self.assertRaises(ValueError):fingerprint_entries(corrupt.get)
        with self.assertRaises(ValueError):fingerprint_entries(lambda name:None if name=='gfx/guard-torches.json' else assets.get(name))

if __name__=='__main__':unittest.main()
