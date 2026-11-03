# SPDX-License-Identifier: GPL-3.0-only
"""Residents drawn from parts at run time (NPC-PARTS-RUNTIME-59, docs/MODULAR_NPCS.md "Stage: residents from parts"):
the builder's recipe per resident (tools/npc_recipes.py) and the engine wiring (aw_npc_parts.c: off by default, the
fused model kept as the server model and the fallback). The engine's reader of the recipe line runs natively in
tests/aga_player_parts_test.c (test_player_parts.RecipeEngine)."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
SRC = ROOT / 'engine/aga/src'

import npc_recipes  # noqa: E402


def appearance(identifier='Fargoth', **over):
    a = {'id': identifier, 'race': 'wood elf', 'female': False, 'skeleton': 'meshes/base_anim.nif',
         'parts': [{'slot': 0, 'id': 'b_n_wood elf_m_head_06'}, {'slot': 1, 'id': 'b_n_wood elf_m_hair_02'},
                   {'slot': 3, 'id': 'c_shirt'}],
         'equipment': [{'list': 'l_shirts', 'chosen': 'common_shirt_01'},
                       {'item': 'common_shirt_01', 'kind': 'CLOT', 'priority': 2},
                       {'item': 'common_pants_01', 'kind': 'CLOT', 'priority': 2}]}
    a.update(over)
    return a


class Recipe(unittest.TestCase):
    def test_line_is_race_sex_head_hair_and_worn_items(self):
        self.assertEqual(npc_recipes.recipe_line(appearance()),
                         'N Fargoth wood|elf 0 b_n_wood|elf_m_head_06 b_n_wood|elf_m_hair_02 common_shirt_01 '
                         'common_pants_01')

    def test_covered_hair_is_a_dash(self):
        a = appearance(parts=[{'slot': 0, 'id': 'h'}])
        self.assertEqual(npc_recipes.recipe_line(a).split()[4:6], ['h', '-'])

    def test_who_keeps_the_fused_model(self):
        self.assertEqual(npc_recipes.eligible(appearance()), (True, ''))
        self.assertFalse(npc_recipes.eligible(appearance(female=True))[0])          # her own female table
        self.assertTrue(npc_recipes.eligible(appearance(female=True, skeleton='meshes/base_animkna.nif'))[0])
        self.assertFalse(npc_recipes.eligible(appearance(initially_dead=True))[0])
        self.assertFalse(npc_recipes.eligible(appearance(animation='meshes/x.nif'))[0])

    def test_ids_the_engine_cannot_read_are_left_out_not_written(self):
        self.assertRaises(ValueError, npc_recipes.word, 'a|b')
        self.assertRaises(ValueError, npc_recipes.word, 'x' * 64)
        many = appearance(equipment=[{'item': 'i%d' % n} for n in range(17)])
        text, report = npc_recipes.recipe_text([many, appearance('Arrille')])
        self.assertEqual(report['lines'], 1)
        self.assertIn('Fargoth', report['left'])
        self.assertTrue(text.startswith('AWNP1\nN Arrille '))

    def test_written_tables_are_ascii_lf(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = npc_recipes.write_tables(tmp, [appearance(), appearance('fargoth')], [('c-2_-9', 'FARGOTH')],
                                              log=lambda *a, **k: None)
            pack = (Path(tmp) / 'view/npc_parts/cells.awnp').read_bytes()
            raw = npc_recipes.pack_tables(pack)[(-2, -9)]
            self.assertFalse((Path(tmp) / 'view/npc_parts.txt').exists())     # no island-wide recipe file
            self.assertEqual(sorted(p.name for p in (Path(tmp) / 'view/npc_parts').iterdir()), ['cells.awnp', 'dir.awnd'])
            directory = npc_recipes.parse_dir((Path(tmp) / 'view/npc_parts/dir.awnd').read_bytes())
            self.assertEqual(directory, {npc_recipes.id_hash('Fargoth'): 'c-2_-9'})
            # the image install merges each stage's directory (a room stage's residents with the area's)
            other = Path(tmp) / 'room-dir.awnd'
            other.write_bytes(npc_recipes.dir_bytes({1: 'some_room', npc_recipes.id_hash('Fargoth'): 'some_room'}))
            merged = npc_recipes.parse_dir(npc_recipes.MERGEABLE[npc_recipes.DIR_PATH](
                Path(tmp) / 'view/npc_parts/dir.awnd', other, 'chim-room-batches'))
            self.assertEqual(merged, {1: 'some_room', npc_recipes.id_hash('Fargoth'): 'c-2_-9'})
        self.assertEqual(report['lines'], 1)                 # one line per id, case-insensitive
        self.assertEqual(raw[:6], b'AWNB\x02' + bytes([npc_recipes.RECORD]))
        self.assertEqual(npc_recipes.RECORD, 42)             # a few dozen bytes a resident


class PerPlace(unittest.TestCase):
    """BUILD-NPC-RECIPES-PER-CELL-59: one table per exterior cell and per room, each resident's line the very line
    of the one island-wide table it replaces."""
    CAST = [appearance('Fargoth'), appearance('Arrille', race='high elf'), appearance('Hrisskar', race='nord'),
            appearance('seyda guard', race='imperial'), appearance('Dead', initially_dead=True)]
    PLACED = [('c-2_-9', 'fargoth'), ('c-2_-9', 'Seyda Guard'), ('c-1_-9', 'seyda guard'),
              ('arrilles_tradehouse', 'arrille'), ('arrilles_tradehouse', 'hrisskar'), ('c-2_-9', 'dead'),
              ('c-3_-9', 'dead')]

    def test_cell_key_and_cell_of(self):
        self.assertEqual(npc_recipes.cell_key(-2, -9), 'c-2_-9')
        self.assertEqual(npc_recipes.cell_of((-8192 * 1.5, -8192 * 8.25, 0)), (-2, -9))
        self.assertEqual(npc_recipes.cell_of((0.0, 8191.9, 0)), (0, 0))
        self.assertRaises(ValueError, npc_recipes.table_path, 'a/b')
        self.assertRaises(ValueError, npc_recipes.table_path, 'x' * 41)

    def test_per_place_lookups_equal_the_island_wide_table(self):
        whole = npc_recipes.parse_lines(npc_recipes.recipe_text(self.CAST)[0], 'island')
        texts, report = npc_recipes.tables(self.CAST, self.PLACED)
        self.assertEqual(sorted(texts), ['arrilles_tradehouse', 'c-1_-9', 'c-2_-9'])   # no table without a resident
        def as_key(identifier):
            return npc_recipes.word(identifier).casefold()
        self.assertEqual(len(whole), 4)
        for key, identifier in self.PLACED:
            found = npc_recipes.parse_lines(texts[key], key) if key in texts else {}
            self.assertEqual(found.get(as_key(identifier)), whole.get(as_key(identifier)), (key, identifier))
            if as_key(identifier) in whole:
                self.assertIn(as_key(identifier), found)
        for key, text in texts.items():                        # only the place's own residents
            self.assertEqual(set(npc_recipes.parse_lines(text, key)),
                             {as_key(i) for k, i in self.PLACED if k == key and as_key(i) in whole})
        self.assertEqual(report['tables'], 3)
        self.assertEqual(report['bytes'], sum(map(len, texts.values())))
        self.assertEqual(report['largest'][0], 'c-2_-9')

    def test_engine_reads_the_binary_tables_as_the_text_table(self):
        """The engine's reader (aw_player_parts.c, natively under ASan) against the builder's own tables: every
        resident's recipe equals the one island-wide text table's, a table holds only its place's residents, and
        loading and letting go leaves nothing held."""
        import test_aga_native_source as native
        cast = self.CAST + [appearance('Elone', race='Redguard', female=True, skeleton='meshes/base_animkna.nif',
                                       equipment=[{'item': 'Extravagant_Robe_01'}, {'item': 'common_shoes_02'}])]
        placed = self.PLACED + [('c-2_-9', 'elone'), ('census_and_excise_office', 'ELONE')]
        with tempfile.TemporaryDirectory() as tmp:
            npc_recipes.write_tables(tmp, cast, placed, log=lambda *a, **k: None)
            folder = Path(tmp) / 'view/npc_parts'
            (folder / 'global.txt').write_text(npc_recipes.recipe_text(cast)[0], encoding='ascii', newline='\n')
            texts, _ = npc_recipes.tables(cast, placed)
            ids = {key: [line.split(' ')[1].replace('|', ' ') for line in text.splitlines()[1:]]
                   for key, text in texts.items()}
            (folder / 'places.txt').write_text(''.join('\t'.join([k] + v) + '\n' for k, v in sorted(ids.items())),
                                               encoding='ascii', newline='\n')
            native.NativeSourceTests.compile_run(self, 'aga_npc_tables_test.c', [SRC / 'aw_player_parts.c'],
                                                 arguments=[str(folder)],
                                                 cflags=['-fsanitize=address,undefined', '-fno-sanitize-recover=all'])

    def test_the_stage_writes_tables_not_the_island_wide_file(self):
        area = (ROOT / 'tools/prepare_area.py').read_text(encoding='utf-8')
        self.assertIn('npc_recipes.write_tables(', area)
        self.assertNotIn('npc_recipes.write(', area)
        engine = (SRC / 'aw_npc_parts.c').read_text(encoding='latin-1')
        self.assertNotIn('"view/npc_parts.txt"', engine)
        self.assertIn('view/npc_parts/%.40s.awnb', engine)
        actors = (SRC / 'aw_actors.c').read_text(encoding='latin-1')
        self.assertIn('AW_NpcPartsCell (cx, cy, 1);', actors)      # with the cell's join (prefetched frames too)
        self.assertIn('AW_NpcPartsCell (cx, cy, 0);', actors)      # and its leave
        self.assertIn('AW_NpcPartsRoom (sv.name);', actors)        # a room on entering it


class EngineWiring(unittest.TestCase):
    def test_off_by_default_fused_model_kept_and_wired(self):
        source = (SRC / 'aw_npc_parts.c').read_text(encoding='latin-1')
        self.assertIn('static int npc_parts_on=0;', source)
        self.assertNotIn('Cvar_RegisterVariable', source)                      # the resident registry budget
        self.assertIn('AW_NpcPartsSet(on)', (SRC / 'aw_view.c').read_text(encoding='latin-1'))
        self.assertIn('AW_NpcTablesFind(&tables,', source)                    # only the tables held now
        self.assertIn('h->aw_skel_table!=(const void *)e->table', source)       # only the parts' own table
        torch = (SRC / 'aw_torch.c').read_text(encoding='latin-1')
        self.assertIn('AW_NpcPartsUpdate();', torch)
        self.assertIn('AW_NpcPartsReset();', torch)
        self.assertIn('aw_npc_parts.c', (ROOT / 'engine/aga/Makefile').read_text())

    def test_recipe_formats_agree(self):
        self.assertEqual(npc_recipes.ITEMS_MAX, 16)
        header = (SRC / 'aw_player_parts.h').read_text(encoding='latin-1')
        self.assertIn('#define AW_PARTS_ITEMS 16', header)
        self.assertIn('#define AW_PARTS_ID 64', header)


if __name__ == '__main__':
    unittest.main()
