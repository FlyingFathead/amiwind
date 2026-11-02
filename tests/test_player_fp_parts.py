# SPDX-License-Identifier: GPL-3.0-only
"""The first-person arms assembled from parts (PLAYER-GEAR-VISUAL-59, docs/THIRD_PERSON.md "First-person arms"): the
builder's first-person table, item rows and recipe (tools/prepare_player_fp_parts.py), the engine's reader of the
recipe (engine/aga/src/aw_player_parts.c, natively, the body's reader), and the engine wiring (aw_view.c, the baked
arms kept selectable; aw_hand_models.c; r_main.c; r_alias.c)."""
import re
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
SRC = ROOT / 'engine/aga/src'


def z(s):
    return s.encode('ascii') + b'\0'


def item(kind, typ, slots):
    """A CLOT/ARMO record's fields: its type data, then per slot INDX, BNAM (male) and CNAM (female) when given."""
    fields = [('NAME', b'x\0'), ('CTDT' if kind == 'CLOT' else 'AODT', struct.pack('<i', typ) + b'\0' * 8)]
    for slot, male, female in slots:
        fields.append(('INDX', bytes([slot])))
        if male:
            fields.append(('BNAM', z(male)))
        if female:
            fields.append(('CNAM', z(female)))
    return fields


class FakeSkeleton:
    """A small skeleton in npc_geometry.Skeleton's shape (parents, keys, pose(t) -> name -> 4 x 4 row-vector world):
    a root, a neck carrying the camera, and two arms whose joints turn with the time; the camera moves with the time
    too, so each stance's first frame gives another view."""

    def __init__(self):
        import numpy as np
        self.np = np
        self.parents = {'fileroot': None, 'bip01': 'fileroot', 'bip01 neck': 'bip01', 'camera': 'bip01 neck',
                        'left hand': 'bip01 l hand'}
        for side, item_bone in (('l', 'shield bone'), ('r', 'weapon bone')):
            chain = ['bip01 neck', 'bip01 %s clavicle' % side, 'bip01 %s upperarm' % side,
                     'bip01 %s forearm' % side, 'bip01 %s hand' % side]
            for parent, child in zip(chain, chain[1:]):
                self.parents[child] = parent
            self.parents['bip01 %s finger0' % side] = 'bip01 %s hand' % side
            self.parents[item_bone] = 'bip01 %s hand' % side
        self.keys = {}

    def local(self, name, t):
        np = self.np
        m = np.eye(4)
        a = 0.3 * t + len(name) * 0.1
        c, s = np.cos(a), np.sin(a)
        if name.startswith('bip01 ') and name != 'bip01 neck':
            m[:3, :3] = [[c, s, 0], [-s, c, 0], [0, 0, 1]]
            m[3, :3] = [3.0, 1.0 if ' l ' in name else -1.0, 0.5]
        elif name == 'camera':
            m[3, :3] = [2.0 + 4.0 * t, 0.0, 10.0]
        elif name == 'bip01':
            m[3, :3] = [0.0, 0.0, 100.0]
        elif name == 'bip01 neck':
            m[3, :3] = [0.0, 0.0, 20.0]
        return m

    def pose(self, t):
        def world(name):
            m = self.local(name, t)
            parent = self.parents[name]
            return m if parent is None else m @ world(parent)
        return lambda name: world(name.casefold())


class Table(unittest.TestCase):
    def test_bones_are_both_arms_whole(self):
        import prepare_player_fp_parts as fp
        bones = fp.fp_bones(FakeSkeleton())
        self.assertEqual(bones[:2], ('bip01', 'bip01 neck'))
        for b in ('bip01 l clavicle', 'bip01 r hand', 'bip01 l finger0', 'shield bone', 'weapon bone'):
            self.assertIn(b, bones)
        self.assertNotIn('camera', bones)          # the view is carried by the root
        self.assertNotIn('left hand', bones)       # an attachment node rides its bone

    def test_view_matrix_is_the_baked_hands_axes(self):
        import numpy as np
        import prepare_player_fp_parts as fp
        camera = np.array([1.0, -2.0, 120.0])
        p = np.array([[5.0, 7.0, 110.0], [0.0, 0.0, 0.0]])
        hom = np.column_stack((p, np.ones(len(p))))
        got = (hom @ fp.view_matrix(camera))[:, :3]
        want = (p - camera)[:, [1, 0, 2]] * np.array([1, -1, 1])      # prepare_hands.bake_appearance
        self.assertTrue(np.allclose(got, want))

    def test_table_frames_are_the_stances_in_the_view(self):
        import numpy as np
        import prepare_player_fp_parts as fp
        import skeletal_actor as sa
        sk = FakeSkeleton()
        stances = [(s, [i * 4.0 + k * 0.1 for k in range(fp.FRAMES)]) for i, s in enumerate(fp.STANCES)]
        saved = fp.stance_times
        fp.stance_times = lambda skeleton: stances
        try:
            data, bones, view0, times = fp.fp_table(sk)
        finally:
            fp.stance_times = saved
        table = sa.read_table(data)
        self.assertEqual(table['frames'], fp.FRAMES * len(fp.STANCES))
        self.assertEqual([table['groups'][s] for s in fp.STANCES],
                         [(i * fp.FRAMES, i * fp.FRAMES + fp.FRAMES - 1) for i in range(len(fp.STANCES))])
        self.assertTrue(np.allclose(view0, fp.view_matrix(sk.pose(stances[0][1][0])('camera')[3, :3])))
        for i, (_, ts) in enumerate(stances):
            view = fp.view_matrix(sk.pose(ts[0])('camera')[3, :3])
            for k in (0, 13, fp.FRAMES - 1):
                world = sa.table_world(table, i * fp.FRAMES + k)
                for name in ('bip01 r hand', 'weapon bone', 'bip01 l forearm'):
                    want = np.asarray(sk.pose(ts[k])(name)) @ view
                    got = world[bones.index(name)]
                    self.assertTrue(np.allclose(got, want, atol=2e-2), (name, i, k, got, want))


class Items(unittest.TestCase):
    def kinds(self):
        return {'CLOT': {'common_shirt_01': item('CLOT', 8, [(3, 'c_shirt', None), (13, 'c_shirt_ua', 'c_shirt_ua_f')]),
                         'common_robe_01': item('CLOT', 4, [(3, 'c_robe', None)]),
                         'plain_robe': item('CLOT', 4, [(3, 'c_robe_plain', None)]),
                         'common_glove_left_01': item('CLOT', 6, [(7, 'c_glove', None)])},
                'ARMO': {'iron_gauntlet_left': item('ARMO', 6, [(7, 'a_gauntlet', None)]),
                         'iron_cuirass': item('ARMO', 1, [(3, 'a_cuirass', None)]),
                         'iron_helmet': item('ARMO', 0, [(0, 'a_helm', None)])},
                'BODY': {n: [] for n in ('c_shirt', 'c_shirt_ua', 'c_shirt_ua_f', 'c_robe', 'c_robe.1st', 'c_robe_plain',
                                         'c_glove', 'c_glove.1st', 'a_gauntlet', 'a_gauntlet.1st', 'a_cuirass',
                                         'a_helm')}}

    def test_first_person_records_and_robe_sleeves(self):
        import prepare_player_fp_parts as fp
        rows = {r['id']: r for r in fp.fp_item_rows(self.kinds())}
        # the '.1st' record where the game has one (gloves and gauntlets), the arm slots only
        self.assertEqual(rows['iron_gauntlet_left']['slots'], {7: ['a_gauntlet.1st', None]})
        self.assertEqual(rows['common_glove_left_01']['slots'], {7: ['c_glove.1st', None]})
        self.assertEqual(rows['common_shirt_01']['slots'], {13: ['c_shirt_ua', 'c_shirt_ua_f']})
        self.assertEqual(rows['iron_gauntlet_left']['rank'], 3)
        # a robe: its first-person sleeves in the chest slot, the arms under them covered
        robe = rows['common_robe_01']['slots']
        self.assertEqual(robe[3], ['c_robe.1st', None])
        self.assertTrue(all(robe[s] is None for s in fp.SLEEVES))
        # nothing on the arms: left out (a robe without its own first-person sleeves, a cuirass, a helmet)
        for gone in ('plain_robe', 'iron_cuirass', 'iron_helmet'):
            self.assertNotIn(gone, rows)

    def test_recipe_is_the_bodys_format(self):
        import prepare_player_fp_parts as fp
        races = [{'race': 'dark elf', 'female': False, 'skin': {6: 'b_hand.1st', 7: 'b_hand.1st', 11: 'b_fore'}}]
        items = fp.fp_item_rows(self.kinds())
        models = {(6, 'b_hand.1st'): 'progs/parts/aa/aaaaaaaaa6.mdl', (7, 'b_hand.1st'): 'progs/parts/aa/aaaaaaaaa7.mdl',
                  (11, 'b_fore'): 'progs/parts/bb/bbbbbbbbbb.mdl', (7, 'a_gauntlet.1st'): 'progs/parts/cc/cccccccccc.mdl',
                  (3, 'c_robe.1st'): 'progs/parts/dd/dddddddddd.mdl'}
        text = fp.recipe_text(races, items, models, (41, 21))
        lines = text.splitlines()
        self.assertEqual(lines[:4], ['AWPP1', 'T h progs/humanoid_1st.awsk 41 21', 'A h 0 -', 'A h 1 -'])
        self.assertIn('R dark|elf 0 h 1.0000 1.0000', lines)
        self.assertIn('S dark|elf 0 7 aaaaaaaaaaa7', lines)
        self.assertIn('I iron_gauntlet_left 3 7=cccccccccccc/-,cccccccccccc/-', lines)
        # a part without a model leaves the one under it ('-/-'); a robe covers the arms ('-,-')
        self.assertIn('I common_glove_left_01 2 7=-/-,-/-', lines)
        self.assertIn('I common_robe_01 24 3=dddddddddddd/-,dddddddddddd/- 11=-,- 12=-,- 13=-,- 14=-,-', lines)
        self.assertTrue(text.isascii() and text.endswith('\n') and '\r' not in text)

    def test_caps_cover_every_slot_drawn(self):
        import prepare_player_fp_parts as fp
        self.assertEqual(set(fp.FP_CAP), set(fp.FP_SLOTS) | {fp.CHEST})
        # about the baked bare arms' own triangles (1,092 for a Nord man, authored topology)
        self.assertLessEqual(sum(fp.FP_CAP[s] for s in fp.FP_SLOTS), 1200)


class Engine(unittest.TestCase):
    def test_native_recipe_reader_reads_the_first_person_recipe(self):
        import test_aga_native_source as native
        native.NativeSourceTests.compile_run(self, 'aga_player_parts_test.c', [SRC / 'aw_player_parts.c'],
                                             cflags=['-fsanitize=address,undefined', '-fno-sanitize-recover=all'])
        test = (ROOT / 'tests/aga_player_parts_test.c').read_text(encoding='utf-8')
        self.assertIn('progs/humanoid_1st.awsk', test)

    def test_arms_from_parts_are_the_default_and_the_baked_arms_stay(self):
        view = (SRC / 'aw_view.c').read_text(encoding='utf-8')
        self.assertIn('{"aw_hand_parts","1",true}', view)
        self.assertIn('Cvar_RegisterVariable(&hand_parts_cvar)', view)
        self.assertIn('view/parts_1st.txt', view)
        self.assertIn('hands on/off', view)
        self.assertIn('aw_hand_parts_apply=hand_parts_apply;aw_view_hand_part=hand_part;', view)
        # read only on a change: the worn ids from the state, never a catalogue (disk) read per frame
        ready = view[view.index('static int hand_parts_ready('):view.index('static int hand_parts_apply(')]
        self.assertIn('aw_state.inventory.equipped[s]', ready)
        self.assertIn('!strcmp(sig,hparts_sig))return 1;', ready)
        self.assertNotIn('AW_InventoryEquippedItem', ready)
        hands = (SRC / 'aw_hand_models.c').read_text(encoding='utf-8')
        apply = hands[hands.index('int AW_HandModelsApply(void)'):]
        # the parts first, the baked stance arms and bare hands after them (the previous method)
        self.assertLess(apply.index('aw_hand_parts_apply(race,female,stance,frame)'), apply.index('hand_weapon(index,1)'))
        self.assertIn('path=equipped?appearances[index].torch:appearances[index].hand;', apply)
        self.assertIn('cl.viewent.model!=weapon_base', hands)
        main = (SRC / 'r_main.c').read_text(encoding='utf-8')
        self.assertIn('struct model_s *(*aw_view_hand_part)(int i);', main)
        self.assertLess(main.index('aw_view_hand_part(part)'), main.index('AW_HandWeaponItemApply()'))
        alias = (SRC / 'r_alias.c').read_text(encoding='utf-8')
        self.assertRegex(alias, r'\(paliashdr && paliashdr->aw_skel\)\)\)')
        build = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        self.assertIn("from prepare_player_fp_parts import image_step;image_step(args.data_files,boot/'id1',out,jobs)",
                      build)

    def test_builder_reads_no_emulated_numbers(self):
        code = re.sub(r'/\*.*?\*/', '', (SRC / 'aw_player_parts.c').read_text(encoding='utf-8'), flags=re.S)
        self.assertNotRegex(code, r'\b(?:sscanf|atof|strtod|strtof|scanf)\s*\(')


if __name__ == '__main__':
    unittest.main()
