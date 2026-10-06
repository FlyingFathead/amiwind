# SPDX-License-Identifier: GPL-3.0-only
"""Real catalogue/model closure must be charged despite unchanged BSP bytes."""
import copy
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import check_world_map_heap as heap
import harvest_heap
from build_aga import apply_map_budget_policy
from test_prepare_harvest_alias import sample
from prepare_harvest_alias import convert_plan
from test_check_world_map_heap import SIZES, make_bsp


TARGET = dict(SIZES, scenery=216, msprite=44, mspriteframe=44,
              mspritegroup=8, mspriteframedesc=8, entity=184, efrag=16, efrag_page=16388,
              aliashdr=124, mdl=84, stvert=12, mtriangle=16,
              maliasskindesc=8, trivertx=4, cache_system=48,
              harvest_proxy_static=4484, harvest_catalogue_extension=1064,
              harvest_plant_capacity=24, harvest_model_capacity=8)


def payload(root):
    args, _ = sample(root/'source')
    convert_plan(**args, output=root/'id1')
    maps=root/'id1/maps'; maps.mkdir()
    # Map geometry itself stays identical when the external catalogue appears.
    (maps/'town.bsp').write_bytes(make_bsp())
    return root/'id1'


class HarvestHeapTests(unittest.TestCase):
    def test_unchanged_bsp_adds_verified_model_heap_and_separate_static_allowance(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); id1=payload(root); maps=id1/'maps'
            catalogue=(id1/'harvest-town.txt').read_bytes(); (id1/'harvest-town.txt').unlink()
            before=heap.inspect_maps(maps,{k:v for k,v in TARGET.items() if not k.startswith('harvest_')})['maps'][0]
            (id1/'harvest-town.txt').write_bytes(catalogue)
            inspected=heap.inspect_maps(maps,TARGET); after=inspected['maps'][0]
            cost=inspected['harvest_external_profile']
            self.assertEqual(before['file_sha256'], after['file_sha256'])
            dynamic=cost['map_costs']['town']['conservative_game_heap_peak_bytes']
            self.assertGreater(dynamic,0)
            self.assertEqual(after['peak_loader_bytes']-before['peak_loader_bytes'],dynamic)
            self.assertEqual(after['additional_static_allowance_bytes'],5548)
            self.assertEqual(after['estimated_total_bytes']-before['estimated_total_bytes'],dynamic+5548)
            self.assertEqual(cost['native_acceptance'],'not_measured')
            self.assertEqual(len(cost['fingerprint_entries']),2)

    def test_shared_models_charged_once_and_only_static_applies_to_legacy_maps(self):
        with tempfile.TemporaryDirectory() as td:
            id1=payload(Path(td)); first=harvest_heap.profile(id1,TARGET)
            shutil.copyfile(id1/'maps/town.bsp',id1/'maps/other.bsp')
            shutil.copyfile(id1/'harvest-town.txt',id1/'harvest-other.txt')
            second=harvest_heap.profile(id1,TARGET)
            self.assertEqual(second['unique_models'],1)
            self.assertEqual(first['map_costs']['town'],second['map_costs']['town'])
            self.assertEqual(second['map_costs']['town'],second['map_costs']['other'])
            # Legacy indexed map shares global identity; no added model registry.
            original=(id1/'harvest-town.txt').read_text().splitlines(); header=original[0].split()
            (id1/'harvest-other.txt').write_text('AWH3 0 0 0 '+header[4]+' '+header[5]+'\n')
            (id1/'maps/no_catalogue.bsp').write_bytes(make_bsp())
            rows=heap.inspect_maps(id1/'maps',TARGET)['maps']
            self.assertEqual([r['harvest_external']['conservative_game_heap_peak_bytes'] for r in rows],
                             [0,0,first['map_costs']['town']['conservative_game_heap_peak_bytes']])
            self.assertEqual({r['additional_static_allowance_bytes'] for r in rows},{5548})

    def test_missing_or_changed_model_and_global_identity_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            id1=payload(Path(td)); model=next((id1/'progs/harvest').glob('*.mdl')); raw=model.read_bytes()
            model.write_bytes(raw+b'x')
            with self.assertRaises(ValueError): harvest_heap.profile(id1,TARGET)
            model.unlink()
            with self.assertRaises(ValueError): harvest_heap.profile(id1,TARGET)
            model.write_bytes(raw)
            (id1/'maps/other.bsp').write_bytes(make_bsp())
            text=(id1/'harvest-town.txt').read_text()
            fields=text.splitlines()[0].split(); text=text.replace(fields[5],'b'*64)
            (id1/'harvest-other.txt').write_text(text)
            with self.assertRaisesRegex(ValueError,'Mismatched harvest global'): harvest_heap.profile(id1,TARGET)

    def test_measured_static_alias_abi_required_only_when_external_models_exist(self):
        with tempfile.TemporaryDirectory() as td:
            id1=payload(Path(td)); raw=(id1/'harvest-town.txt').read_bytes()
            for key in ('harvest_proxy_static','harvest_catalogue_extension','aliashdr'):
                sizes=copy.deepcopy(TARGET); sizes.pop(key)
                with self.assertRaisesRegex(ValueError,'[Aa]ctual target'): harvest_heap.profile(id1,sizes)
            sizes=copy.deepcopy(TARGET); sizes['harvest_proxy_static']=True
            with self.assertRaises(ValueError): harvest_heap.profile(id1,sizes)
            (id1/'harvest-town.txt').unlink()
            self.assertIsNone(harvest_heap.profile(id1,SIZES))
            (id1/'harvest-town.txt').write_text('AWH3 0 0 0 1 '+'a'*64+'\n')
            self.assertIsNone(harvest_heap.profile(id1,SIZES))

    def test_candidate_static_storage_charged_even_without_any_catalogue(self):
        with tempfile.TemporaryDirectory() as td:
            maps=Path(td)/'maps';maps.mkdir();(maps/'town.bsp').write_bytes(make_bsp())
            old_sizes={k:v for k,v in TARGET.items() if not k.startswith('harvest_')}
            before=heap.inspect_maps(maps,old_sizes)['maps'][0]
            after=heap.inspect_maps(maps,TARGET)['maps'][0]
            self.assertEqual(after['peak_loader_bytes'],before['peak_loader_bytes'])
            self.assertEqual(after['estimated_total_bytes']-before['estimated_total_bytes'],5548)
            self.assertEqual(after['harvest_external']['conservative_game_heap_peak_bytes'],0)

    def test_warning_policy_never_waives_actual_allocation_ceiling(self):
        report=dict(heap_budget_bytes=11534336, baseline_reserve_bytes=3145728,
                    safety_headroom_bytes=2097152, failing_maps=['town.bsp'],
                    maps=[dict(map='town.bsp',peak_loader_bytes=9000000)])
        decision=apply_map_budget_policy(report,'warning')
        self.assertTrue(decision['private_assembly_allowed'])
        self.assertFalse(decision['production_memory_gate_passed'])
        report['maps'][0]['peak_loader_bytes']=report['heap_budget_bytes']
        with self.assertRaisesRegex(ValueError,'allocation_ceiling_failed'):
            apply_map_budget_policy(report,'warning')


if __name__=='__main__': unittest.main()
