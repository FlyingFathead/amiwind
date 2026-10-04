# SPDX-License-Identifier: GPL-3.0-only
import unittest
from scenery_admission import catalogue_count
from prepare_world_flora import reserve_violations

class CatalogueAdmissionTests(unittest.TestCase):
    def test_exact_runtime_names_and_occurrences(self):
        raw=b'{"classname" "func_wall"}\n'*654
        for name in ('balmora','bm000','bm019','bm063'):
            self.assertEqual(catalogue_count(name,raw),654)
        for name in ('bm064','bm01','bm000x','sn001','vf0001','BalMora'):
            self.assertEqual(catalogue_count(name,raw),0)
    def test_town_engine_clip_format_does_not_relax_world_reserve(self):
        m=dict(models_plus_sprites=170,entities=20,static_entities=0,nodes=18426,
               clipnodes=53119,bytes=4643376,catalogue_placements=634,visible_entity_floor=652)
        self.assertFalse(reserve_violations(m,'town'))
        self.assertEqual({v['metric'] for v in reserve_violations(m,'world')},{'clipnodes','bytes'})
        m['clipnodes']=65521
        self.assertIn('clipnodes',{v['metric'] for v in reserve_violations(m,'town')})
        m['catalogue_placements']=1001
        self.assertIn('catalogue_placements',{v['metric'] for v in reserve_violations(m,'town')})
