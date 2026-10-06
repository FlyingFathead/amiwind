# SPDX-License-Identifier: GPL-3.0-only
from pathlib import Path
import tempfile
import unittest
from alias_stream_heap import apply,eligible,runtime_policy
from guard_torch_heap import alias_cost,map_cost
from test_guard_torch_heap import SIZES,model

class AliasStreamHeapTests(unittest.TestCase):
    def test_only_verified_stream_formats_drop_duplicate_staging(self):
        raw=model();old=alias_cost(raw,SIZES);new=alias_cost(raw,dict(SIZES,alias_streaming=1))
        self.assertEqual(old['cache_bytes'],new['cache_bytes'])
        self.assertGreater(old['loader_fallback_bytes'],0)
        self.assertEqual(new['loader_fallback_bytes'],0)
        self.assertEqual(new['external_malloc_peak_bytes'],0)
        self.assertTrue(eligible(raw,new['decoded_hunk_bytes']))
        self.assertFalse(eligible(raw+b'\0',new['decoded_hunk_bytes']))
        self.assertFalse(eligible(raw,524289))
        malformed=bytearray(raw);malformed[84]=1
        self.assertFalse(eligible(malformed,new['decoded_hunk_bytes']))
        item=dict(source_id='guard',base_model='progs/base.mdl',body_model='progs/held.mdl',torch_model='progs/held.mdl',auto_inventory_eligible=False)
        cost=map_cost(b'{"classname" "aw_npc" "aw_source_id" "guard" "model" "progs/base.mdl"}',dict(records=[item],models={'progs/held.mdl':new}))
        self.assertEqual(cost['active_cache_bytes'],new['cache_bytes'])
        self.assertEqual(cost['conservative_game_heap_peak_bytes'],new['cache_bytes'])
        self.assertEqual(cost['admission_probe_bytes'],1024*1024)

    def test_changed_or_missing_stream_source_fails_closed(self):
        source=Path(__file__).resolve().parents[1]/'engine/aga/src'
        self.assertEqual(runtime_policy(source)['alias_streaming'],1)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'model.c').write_text((source/'model.c').read_text())
            with self.assertRaisesRegex(ValueError,'Unrecognized'):runtime_policy(root)
            (root/'model_alias_stream.inc').write_text((source/'model_alias_stream.inc').read_text()+'\n')
            with self.assertRaisesRegex(ValueError,'Unrecognized'):runtime_policy(root)
            (root/'model.c').write_text('void legacy(void){}')
            self.assertEqual(runtime_policy(root)['alias_streaming'],0)

if __name__=='__main__':unittest.main()
