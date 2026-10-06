# SPDX-License-Identifier: GPL-3.0-only
import copy
import unittest
from pathlib import Path
import test_aga_native_source as native
from test_prepare_harvest import source, inputs
from prepare_harvest import prepare, placement_index
from world_flora import inventory


class GlobalHarvestIndexTests(unittest.TestCase):
    def test_global_index_is_independent_of_region_subset_and_input_order(self):
        full = inventory(source(), ('small_mushroom',))
        second = copy.deepcopy(full['references'][0]); second['number'] = 99
        full['references'].append(second)
        first, digest = placement_index(full)
        full['references'].reverse()
        self.assertEqual((first, digest), placement_index(full))
        full['references'].append(second)
        with self.assertRaises(ValueError): placement_index(full)

    def test_catalogue_emits_global_identity_and_slot(self):
        raw = source(); region, bsp = inputs(raw); payload, receipt = prepare(raw, region, bsp)
        self.assertTrue(payload.startswith(b'AWH3 2 2 1 1 '))
        self.assertEqual(receipt['global_slots'], 1)
        self.assertEqual(receipt['placements'][0]['slot'], 1)
        self.assertEqual(len(receipt['global_catalogue_sha256']), 64)

    def test_original_engine_global_capacity_and_corrupt_saves(self):
        native.NativeSourceTests().compile_run('aga_global_harvest_test.c',
            [Path(native.SOURCE)/'src'/n for n in ('aw_harvest.c','aw_state.c','aw_save_codec.c')],
            cflags=['-fsanitize=undefined', '-fno-sanitize-recover=all'])
