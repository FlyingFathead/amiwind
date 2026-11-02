# SPDX-License-Identifier: GPL-3.0-only
"""The player's body assembled from parts by equipment slot (PLAYER-GEAR-VISUAL-59, docs/THIRD_PERSON.md "The
assembled body"): the builder's recipe table (tools/prepare_player_parts.py) and the engine's reader of it
(engine/aga/src/aw_player_parts.c, natively), the engine wiring (aw_view.c: the assembled body the default, the baked
body kept selectable), the per-axis alias scale and the bone pose shared by the parts (r_alias.c)."""
import re
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
SRC = ROOT / 'engine/aga/src'


def field(tag, data):
    return (tag, data)


def z(s):
    return s.encode('ascii') + b'\0'


def item(kind, typ, slots):
    """A CLOT/ARMO record's fields: its type data, then per slot INDX, BNAM (male) and CNAM (female) when given."""
    fields = [field('NAME', b'x\0'), field('CTDT' if kind == 'CLOT' else 'AODT', struct.pack('<i', typ) + b'\0' * 8)]
    for slot, male, female in slots:
        fields.append(field('INDX', bytes([slot])))
        if male:
            fields.append(field('BNAM', z(male)))
        if female:
            fields.append(field('CNAM', z(female)))
    return fields


class RecipeBuilder(unittest.TestCase):
    def kinds(self):
        return {'CLOT': {'common_shirt_01': item('CLOT', 8, [(3, 'c_shirt', None), (13, 'c_shirt_ua', 'c_shirt_ua_f')]),
                         'robe': item('CLOT', 4, [(3, 'c_robe', None)]),
                         'skirt': item('CLOT', 7, [(4, 'c_skirt', None)])},
                'ARMO': {'iron_helmet': item('ARMO', 0, [(0, 'a_helm', None)]),
                         'iron_shield': item('ARMO', 8, [(10, 'a_shield', None)]),
                         'iron_cuirass': item('ARMO', 1, [(3, 'a_cuirass', None)])}}

    def test_item_rows_ranks_and_the_original_covers(self):
        import prepare_player_parts as ppp
        rows = {r['id']: r for r in ppp.item_rows(self.kinds())}
        self.assertNotIn('iron_shield', rows)                  # a shield is a held item on the shield bone
        self.assertEqual(rows['iron_cuirass']['rank'], 3)
        self.assertEqual(rows['common_shirt_01']['rank'], 2)
        self.assertEqual(rows['robe']['rank'], 24)
        self.assertEqual(rows['skirt']['rank'], 8)
        self.assertEqual(rows['iron_helmet']['slots'][1], [None, None])     # a helmet hides the hair
        self.assertEqual(set(rows['robe']['slots']), {3} | set(ppp.ROBE_COVERS))
        self.assertEqual(set(rows['skirt']['slots']), {4} | set(ppp.SKIRT_COVERS))
        self.assertEqual(rows['common_shirt_01']['slots'][13], ['c_shirt_ua', 'c_shirt_ua_f'])
        # beast races wear no boots or shoes: no beast part is built for them, their own feet show
        kinds = self.kinds()
        kinds['ARMO']['iron boots'] = item('ARMO', 5, [(15, 'a_boot', None)])
        kinds['CLOT']['common_shoes_01'] = item('CLOT', 3, [(15, 'c_shoe', None)])
        kinds['BODY'] = {'a_boot': [], 'c_shoe': [], 'c_shirt': []}
        rows = {r['id']: r for r in ppp.item_rows(kinds)}
        self.assertFalse(rows['iron boots']['beast'])
        self.assertFalse(rows['common_shoes_01']['beast'])
        self.assertTrue(rows['common_shirt_01']['beast'])
        need = ppp.needed_parts(kinds, [{'skeleton': 'meshes/base_anim.nif', 'skin': {}, 'heads': [], 'hairs': []},
                                        {'skeleton': 'meshes/base_animkna.nif', 'skin': {}, 'heads': [], 'hairs': []}],
                                [rows['iron boots'], rows['common_shirt_01']])
        self.assertIn(('meshes/base_anim.nif', 15, 'a_boot'), need)
        self.assertNotIn(('meshes/base_animkna.nif', 15, 'a_boot'), need)
        self.assertIn(('meshes/base_animkna.nif', 3, 'c_shirt'), need)

    def test_recipe_text_is_what_the_engine_reads(self):
        import prepare_player_parts as ppp
        races = [{'race': 'dark elf', 'female': False, 'skeleton': 'meshes/base_anim.nif', 'weight': 1.0,
                  'height': 1.0, 'skin': {3: 'b_chest'}, 'heads': ['b_head 1', 'b_head 2'], 'hairs': ['b_hair']}]
        items = ppp.item_rows(self.kinds())
        h = 'meshes/base_anim.nif'
        models = {(h, 3, 'b_chest'): 'progs/parts/aa/aaaaaaaaaa.mdl', (h, 0, 'b_head 1'): 'progs/parts/bb/bbbbbbbbb1.mdl',
                  (h, 0, 'b_head 2'): 'progs/parts/bb/bbbbbbbbb2.mdl', (h, 1, 'b_hair'): 'progs/parts/cc/cccccccccc.mdl',
                  (h, 3, 'c_shirt'): 'progs/parts/dd/dddddddddd.mdl',
                  ('meshes/base_animkna.nif', 3, 'c_shirt'): 'progs/parts/ee/eeeeeeeeee.mdl'}
        text = ppp.recipe_text(races, items, models, {('h', 0): 'progs/parts/hm.anm'}, {'h': 'progs/humanoid.awsk'},
                               {'h': (59, 60)})
        lines = text.splitlines()
        self.assertEqual(lines[0], 'AWPP1')
        self.assertIn('T h progs/humanoid.awsk 59 60', lines)
        self.assertIn('R dark|elf 0 h 1.0000 1.0000', lines)
        self.assertIn('S dark|elf 0 3 aaaaaaaaaaaa', lines)
        self.assertIn('H dark|elf 0 b_head|1 bbbbbbbbbbb1', lines)
        shirt = next(x for x in lines if x.startswith('I common_shirt_01 '))
        # a part the female column lacks is the male one; a part no skeleton has is '-'
        self.assertEqual(shirt, 'I common_shirt_01 2 3=dddddddddddd/eeeeeeeeeeee,dddddddddddd/eeeeeeeeeeee 13=-/-,-/-')
        self.assertIn('1=-,-', next(x for x in lines if x.startswith('I iron_helmet ')))
        self.assertTrue(text.isascii() and text.endswith('\n') and '\r' not in text)
        # 'ember hand' and 'ember_hand' are two items: a space is written '|', so an id holding '|' is refused
        self.assertIn('I ember|hand 2 ', ppp.recipe_text([], [{'id': 'ember hand', 'kind': 'CLOT', 'rank': 2,
                                                                 'slots': {}}], {}, {}, {}, {}))
        with self.assertRaises(ValueError):
            ppp.recipe_text(races, [{'id': 'a|b', 'kind': 'CLOT', 'rank': 2, 'slots': {}}], {}, {}, {}, {})
        with self.assertRaises(ValueError):
            ppp.recipe_text(races, [{'id': 'a=b', 'kind': 'CLOT', 'rank': 2, 'slots': {}}], {}, {}, {}, {})

    def test_part_paths_are_shared_short_and_spread(self):
        import prepare_player_parts as ppp
        a = ppp.part_dict(15, 'b_foot', 'b\\B_Foot.NIF')
        b = ppp.part_dict(15, 'b_other_foot_record', 'b/b_foot.nif')
        path = ppp.part_path('meshes/base_anim.nif', a)
        # one model per mesh: two records naming the same mesh in the same slot share it
        self.assertEqual(path, ppp.part_path('meshes/base_anim.nif', b))
        self.assertNotEqual(path, ppp.part_path('meshes/base_animkna.nif', a))
        self.assertNotEqual(path, ppp.part_path('meshes/base_anim.nif', ppp.part_dict(16, 'b_foot', 'b\\B_Foot.NIF')))
        self.assertRegex(path, r'^progs/parts/[0-9a-f]{2}/[0-9a-f]{10}\.mdl$')
        self.assertEqual(len(path), 29)
        self.assertEqual(ppp.part_hex(path), path[12:14] + path[15:25])

    def test_part_quotas_keep_the_cap(self):
        import numpy as np
        import prepare_player_parts as ppp
        shapes = [{'faces': np.zeros((n, 3))} for n in (300, 100, 5)]
        q = ppp.quotas_for(shapes, 60)
        self.assertLessEqual(int(q.sum()), 60)
        self.assertTrue(all(1 <= x <= n for x, n in zip(q, (300, 100, 5))))
        self.assertEqual(list(ppp.quotas_for(shapes[2:], 60)), [5])
        # every slot has a cap; the starting clothes stay near the baked body's triangles
        self.assertTrue(all(0 < c <= 96 for c in ppp.SLOT_CAP.values()))

    def test_layouts_are_not_model_layouts(self):
        # every <model>.anm in the image must have its model (tools/actor_frames.py, the payload preflight): the
        # player's part layouts belong to every part, so they are view/parts_<s><f>.txt
        source = (ROOT / 'tools/prepare_player_parts.py').read_text(encoding='utf-8')
        self.assertIn("path = 'view/parts_' + s + ('f' if female else 'm') + '.txt'", source)

    def test_tables_written_twice_must_be_the_same(self):
        import tempfile
        import prepare_player_parts as ppp
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'progs/humanoid.awsk'
            ppp.write_same(p, b'AWSK1')
            ppp.write_same(p, b'AWSK1')
            with self.assertRaises(ValueError):
                ppp.write_same(p, b'AWSK2')


class RecipeEngine(unittest.TestCase):
    def test_native_recipe_reader(self):
        import test_aga_native_source as native
        native.NativeSourceTests.compile_run(self, 'aga_player_parts_test.c', [SRC / 'aw_player_parts.c'],
                                             cflags=['-fsanitize=address,undefined', '-fno-sanitize-recover=all'])

    def test_reader_has_no_emulated_number_parsing(self):
        code = re.sub(r'/\*.*?\*/', '', (SRC / 'aw_player_parts.c').read_text(encoding='utf-8'), flags=re.S)
        self.assertNotRegex(code, r'\b(?:sscanf|atof|strtod|strtof|scanf)\s*\(')


class EngineWiring(unittest.TestCase):
    def test_assembled_body_is_the_default_and_the_baked_one_stays(self):
        view = (SRC / 'aw_view.c').read_text(encoding='utf-8')
        self.assertIn('{"aw_player_body_parts","1",true}', view)
        self.assertIn('Cvar_RegisterVariable(&parts_cvar)', view)
        self.assertIn('view/bodies.txt', view)             # the baked bodies: aw_player_body_parts 0, torch, water
        self.assertIn('view/parts.txt', view)
        self.assertIn('parts on/off', view)
        self.assertIn('aw_player_parts.c', (ROOT / 'engine/aga/Makefile').read_text(encoding='utf-8'))
        cl = (SRC / 'cl_main.c').read_text(encoding='utf-8')
        self.assertIn('held<32', cl)
        # asked every frame: the worn ids from the state, never a catalogue (disk) read per frame; the hands' rows
        # only when their id changes (in game: 15 instead of 60 frames a second, and the emulator's disk stall)
        ready = view[view.index('static int parts_ready('):view.index('static int body_find(')]
        self.assertIn('aw_state.inventory.equipped[s]', ready)
        self.assertNotIn('AW_InventoryEquippedItem', ready)
        draws = view[view.index('static void parts_draws('):view.index('static entity_t *view_held(')]
        self.assertNotIn('AW_InventoryEquippedItem', draws)
        # a weapon or shield is equipped under the assembled body too (it holds them on its table's bones)
        self.assertIn('if(body_parts)return parts_table && parts.weapon_bone>=0', view)
        # clothing with body parts is worn now that the assembled body shows it
        inventory = (ROOT / 'tools/prepare_inventory.py').read_text(encoding='utf-8')
        self.assertIn("elif item['parts'] and inert and (not item['enchantment'] or (enchant and enchant[0]==2)):flags|=4",
                      inventory)

    def test_per_axis_alias_scale_and_one_bone_pose_for_all_parts(self):
        alias = (SRC / 'r_alias.c').read_text(encoding='utf-8')
        for axis in range(3):
            self.assertIn('pmdl->scale[%d] * R_AliasAxisScale(currententity, %d)' % (axis, axis), alias)
        self.assertIn('posed_table = NULL', alias)
        self.assertRegex(alias, r'if \(table != posed_table \|\| key != posed_key')
        render = (SRC / 'render.h').read_text(encoding='utf-8')
        self.assertIn('float aw_alias_zscale;', render)


if __name__ == '__main__':
    unittest.main()
