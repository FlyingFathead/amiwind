# SPDX-License-Identifier: GPL-3.0-only
"""FLORA-FAUNA-COVERAGE-62: the bracket fungi on the Bitter Coast tree trunks are harvested like the small mushrooms.

Synthetic records only: one small mushroom and one trunk fungus in a master. The fungi join the global placement index
as a new generation after the mushrooms, so every earlier mushroom slot and the earlier index digest are kept, and the
catalogues name that earlier index as their base (aw_harvest.c compatible(): an earlier save is taken over in place)."""
import copy
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import numpy as np
from prepare_harvest import (HARVEST_KINDS, INDEX_GENERATIONS, identity_key, index_generations, placement_index,
                             placement_source_key, source_context)
from prepare_harvest_alias import catalogue
from world_flora import flora_kind, harvest_only_kind, inventory
from test_prepare_harvest import source
from test_world_flora_integration import record, sub

FUNGUS_MODELS = ('f/flora_bc_shelffungus_01.nif', 'f/flora_bc_shelffungus_02.nif',
                 'f/flora_bc_shelffungus_03.nif', 'f/flora_bc_shelffungus_04.nif')


def fungus(number=77, cell=(-3, -10), name=b'bracket', model=FUNGUS_MODELS[0]):
    """A trunk fungus record and one exterior placement of it, as the master has them (organic, respawning)."""
    raw = record('CONT', sub('NAME', name + b'\0') + sub('FNAM', b"Bungler's Bane\0") + sub('MODL', model.encode() + b'\0') +
                 sub('FLAG', struct.pack('<I', 11)) + sub('CNDT', struct.pack('<f', 0)) +
                 sub('NPCO', struct.pack('<i32s', 1, b'ingredient')))
    raw += record('CELL', sub('DATA', struct.pack('<Iii', 0, *cell)) + sub('FRMR', struct.pack('<I', number)) +
                  sub('NAME', name + b'\0') + sub('DATA', struct.pack('<6f', -24000, -81000, 600, 0, 0, 1.5)))
    return raw


class TreeFungusKindTests(unittest.TestCase):
    def test_the_four_trunk_fungus_meshes_are_a_harvest_kind_and_no_scenery_kind(self):
        for model in FUNGUS_MODELS:
            self.assertEqual(harvest_only_kind(model), 'tree_fungus')
            # the collision, sprite and tracker decisions made from flora_kind stay as they were
            self.assertIsNone(flora_kind(model))
        for model in ('f/flora_bc_shelffungus_x.nif', 'f/flora_bc_mushroom_01.nif', 'f/flora_bc_tree_01.nif',
                      'f/flora_bc_shelffungus_01.kf'):
            self.assertIsNone(harvest_only_kind(model))
        self.assertEqual(HARVEST_KINDS, ('small_mushroom', 'tree_fungus'))
        self.assertEqual(INDEX_GENERATIONS[0], ('small_mushroom',))
        import remove_harvest_geometry
        self.assertEqual(remove_harvest_geometry.HARVEST_KINDS, HARVEST_KINDS)

    def test_inventory_selects_the_fungi_only_when_asked(self):
        raw = source(extra=fungus())
        self.assertEqual([r['kind'] for r in inventory(raw, ('small_mushroom',))['references']], ['small_mushroom'])
        both = inventory(raw, HARVEST_KINDS)
        self.assertEqual(sorted(r['kind'] for r in both['references']), ['small_mushroom', 'tree_fungus'])
        self.assertEqual(inventory(raw, ('tree',))['references'], [])


class IndexGenerationTests(unittest.TestCase):
    def test_mushroom_slots_and_digest_are_those_of_the_earlier_index(self):
        raw = source(extra=fungus())
        earlier, earlier_digest = placement_index(inventory(raw, ('small_mushroom',)), (('small_mushroom',),))
        full = inventory(raw, HARVEST_KINDS)
        chain, indices = index_generations(full)
        self.assertEqual(chain[0], (len(earlier), earlier_digest))
        self.assertEqual(len(chain), 2)
        self.assertEqual(chain[1][0], len(indices))
        self.assertNotEqual(chain[1][1], earlier_digest)
        for key, slot in earlier.items():
            self.assertEqual(indices[key], slot)        # no earlier slot moves
        fungus_ref = next(r for r in full['references'] if r['kind'] == 'tree_fungus')
        key = identity_key(placement_source_key(fungus_ref, full['master_sha256']))
        self.assertEqual(indices[key], len(earlier) + 1)
        self.assertEqual(placement_index(full), (indices, chain[1][1]))

    def test_new_fungi_sort_among_themselves_after_every_mushroom(self):
        raw = source(extra=fungus(80, (-1, -9), b'bracket_a', FUNGUS_MODELS[1]) +
                     fungus(70, (-5, -9), b'bracket_b', FUNGUS_MODELS[3]))
        full = inventory(raw, HARVEST_KINDS)
        chain, indices = index_generations(full)
        mushrooms = {identity_key(placement_source_key(r, full['master_sha256']))
                     for r in full['references'] if r['kind'] == 'small_mushroom'}
        self.assertTrue(all(indices[k] <= len(mushrooms) for k in mushrooms))
        fungi = sorted(k for k in indices if k not in mushrooms)
        self.assertEqual([indices[k] for k in fungi], list(range(len(mushrooms) + 1, len(indices) + 1)))
        reordered = copy.deepcopy(full); reordered['references'].reverse()
        self.assertEqual(index_generations(reordered), (chain, indices))

    def test_a_master_without_fungi_keeps_the_earlier_index_unchanged(self):
        raw = source()
        chain, indices = index_generations(inventory(raw, HARVEST_KINDS))
        self.assertEqual(len(chain), 1)
        self.assertEqual((indices, chain[0][1]), placement_index(inventory(raw, ('small_mushroom',)), (('small_mushroom',),)))
        self.assertEqual(source_context(raw)['bases'], [])

    def test_an_empty_first_generation_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'empty'):
            index_generations(inventory(fungus(), HARVEST_KINDS))


class CatalogueTests(unittest.TestCase):
    def rows(self, context):
        refs = []
        for r in context['full']['references']:
            refs.append(dict(copy.deepcopy(r), model_index=0 if r['kind'] == 'small_mushroom' else 1,
                             source_key=placement_source_key(r, context['full']['master_sha256'])))
        return refs

    def test_a_fungus_row_is_a_plant_like_a_mushroom_and_the_header_names_the_earlier_index(self):
        raw = source(extra=fungus())
        context = source_context(raw, max_plants=256, intern_root_spans=True)
        self.assertEqual(context['kinds'], HARVEST_KINDS)
        self.assertEqual(len(context['bases']), 1)
        raw_catalogue, provenance = catalogue(context, self.rows(context), np.zeros(3), {0: 0, 1: 1},
                                              ['progs/harvest/a.mdl x', 'progs/harvest/b.mdl y'])
        lines = raw_catalogue.decode('ascii').splitlines()
        head = lines[0].split()
        slots, digest = context['bases'][0]
        self.assertEqual(head[0], 'AWH4')
        self.assertEqual(head[3:7], ['2', str(len(context['indices'])), context['catalogue'], '2'])
        self.assertEqual(head[7:], ['bases', '1', str(slots), digest])
        self.assertTrue(any(line.endswith(" Bungler's Bane") and ' @1 ' in line for line in lines))
        self.assertEqual(sorted(p['source_id'] for p in provenance), ['bracket', 'plant'])

    def test_without_an_earlier_generation_the_header_is_the_earlier_form(self):
        raw = source()
        context = source_context(raw, max_plants=256, intern_root_spans=True)
        raw_catalogue, _ = catalogue(context, self.rows(context), np.zeros(3), {0: 0}, ['progs/harvest/a.mdl x'])
        self.assertEqual(len(raw_catalogue.decode('ascii').splitlines()[0].split()), 7)

    def test_a_scripted_or_unorganic_fungus_is_not_admitted(self):
        raw = source(extra=fungus())
        context = source_context(raw, max_plants=256, intern_root_spans=True)
        refs = self.rows(context)
        bad = next(r for r in refs if r['kind'] == 'tree_fungus')
        bad['script'] = 'someScript'
        context['original'][identity_key(bad['source_key'])]['script'] = 'someScript'
        with self.assertRaisesRegex(ValueError, 'unscripted organic container plants'):
            catalogue(context, refs, np.zeros(3), {0: 0, 1: 1}, ['progs/harvest/a.mdl x', 'progs/harvest/b.mdl y'])


if __name__ == '__main__':
    unittest.main()
