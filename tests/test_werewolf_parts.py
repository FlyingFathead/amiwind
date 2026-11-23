# SPDX-License-Identifier: GPL-3.0-only
"""The werewolf's look (WEREWOLF-BODY-63, tools/werewolf_parts.py; docs/THIRD_PERSON.md "The werewolf") and an NPC
appearance with an empty part (NPC-WEREWOLF-NO-MODEL-66, tools/npc_library.py without_empty_parts): the records, the
recipes' werewolf rows by the engine reader's rules, the parts coverage, the shared-vertex route on a synthetic actor
(a reduced part passes the outer-hull check, a torn one fails it), the unit inputs of the other parts. Synthetic
records and meshes, no game files."""
import importlib.util
import json
import re
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import werewolf_parts as WW  # noqa: E402

GEOMETRY = all(importlib.util.find_spec(n) for n in ('scipy', 'PIL'))
H_SKELETON = 'meshes/base_anim.nif'
K_SKELETON = 'meshes/base_animkna.nif'


def z(s):
    return s.encode('ascii') + b'\0'


def body(mesh, part=3, flags=0, kind=0, race='Argonian'):
    return [('NAME', b'x\0'), ('MODL', z(mesh)), ('FNAM', z(race)), ('BYDT', bytes([part, 0, flags, kind]))]


def clot(typ, slots):
    fields = [('NAME', b'x\0'), ('CTDT', struct.pack('<i', typ) + b'\0' * 8)]
    for slot, male in slots:
        fields += [('INDX', bytes([slot])), ('BNAM', z(male))]
    return fields


def kinds(werewolf=True):
    """The masters' records the stages read: one playable beast race (Argonian), its heads (one of them the
    werewolf's, flagged not playable), a shirt, a common robe and (with WEREWOLF) Bloodmoon's werewolf set."""
    radt = struct.pack('<4fI', 1.0, 1.0, 1.0, 1.0, 1 | 2)
    out = {'RACE': {'argonian': [('NAME', b'Argonian\0'), ('RADT', radt)]},
           'BODY': {'b_n_argonian_m_head_01': body('b\\B_N_Argonian_M_Head_01.nif', part=0),
                    'b_n_argonian_m_hair01': body('b\\B_N_Argonian_M_Hair01.nif', part=1),
                    'b_n_argonian_m_chest': body('b\\B_N_Argonian_M_Skins.nif', part=3),
                    'c_shirt': body('c\\C_M_Shirt.nif', part=3, kind=1),
                    'c_robe': body('c\\C_M_Robe.nif', part=3, kind=1)},
           'CLOT': {'common_shirt_01': clot(8, [(3, 'c_shirt')]), 'common_robe_01': clot(4, [(3, 'c_robe')])},
           'ARMO': {}}
    if werewolf:
        out['BODY'].update({'werewolfskin': body('wolf\\skin.NIF', kind=1),
                            'werewolfskin.1st': body('wolf\\skin.1st.NIF', kind=1),
                            'werewolfhead': body('wolf\\head.NIF', part=0, flags=2),
                            'werewolfhair': body('wolf\\hair.NIF', part=1, flags=2)})
        out['CLOT']['werewolfrobe'] = clot(4, [(3, 'WerewolfSkin')])
    return out


# ---------------------------------------------------------------- the engine reader's rules (aw_player_parts.c)

HEX12 = re.compile(r'^[0-9a-f]{12}$')


def reader_errors(text):
    """The recipe lines the engine reader (engine/aga/src/aw_player_parts.c AW_PartsAssemble) would refuse or skip
    wrongly: a one-letter line kind, R <race> <0|1> <one letter> <decimal 0.5..2> <decimal 0.5..2>, S <race> <0|1>
    <slot < 27> <12 hex>, H/K <race> <0|1> <id> <12 hex>, T <letter> <path < 32> <bone> <bone>, A <letter> <0|1>
    <anm < 48>; and every race's skeleton letter with its T line and an A line per sex."""
    errors, letters, tables, anms = [], {}, set(), set()

    def decimal(w):
        m = re.fullmatch(r'(\d{1,4})(\.\d{0,6})?', w)
        return m is not None and 0.5 <= float(w) <= 2

    lines = text.split('\n')
    if lines[0] != 'AWPP1':
        errors.append('no AWPP1 header')
    for line in lines[1:]:
        if not line:
            continue
        w = line.split(' ')
        if len(w[0]) != 1:
            errors.append('kind: ' + line)
        elif w[0] == 'R':
            if not (len(w) == 6 and w[2] in '01' and re.fullmatch('[a-z]', w[3]) and decimal(w[4]) and decimal(w[5])):
                errors.append('R: ' + line)
            else:
                letters[(w[1], w[2])] = w[3]
        elif w[0] == 'S':
            if not (len(w) == 5 and w[2] in '01' and w[3].isdigit() and int(w[3]) < 27 and HEX12.match(w[4])):
                errors.append('S: ' + line)
        elif w[0] in 'HK':
            if not (len(w) == 5 and w[2] in '01' and HEX12.match(w[4])):
                errors.append('H/K: ' + line)
        elif w[0] == 'T':
            if not (len(w) == 5 and len(w[1]) == 1 and len(w[2]) < 32):
                errors.append('T: ' + line)
            tables.add(w[1])
        elif w[0] == 'A':
            if not (len(w) == 4 and len(w[1]) == 1 and w[2] in '01' and len(w[3]) < 48):
                errors.append('A: ' + line)
            anms.add((w[1], w[2]))
    for (race, sex), letter in letters.items():
        if letter not in tables or (letter, sex) not in anms:
            errors.append('race %s %s on %s has no T or A line' % (race, sex, letter))
    return errors


class Records(unittest.TestCase):
    def test_the_werewolf_set_from_the_records(self):
        ww = WW.werewolf_set(kinds())
        self.assertEqual(ww['robe'], 'werewolfrobe')
        self.assertEqual(ww['skin'], ('werewolfskin', 'wolf\\skin.NIF'))
        self.assertEqual(ww['skin_1st'], ('werewolfskin.1st', 'wolf\\skin.1st.NIF'))
        self.assertEqual(ww['head'][0], 'werewolfhead')
        self.assertEqual(ww['hair'][0], 'werewolfhair')
        self.assertIsNone(WW.werewolf_set(kinds(werewolf=False)))       # the base game alone: no werewolf rows

    def test_a_not_playable_part_is_no_race_head_or_hair(self):
        # Bloodmoon's WerewolfHead and WerewolfHair name the Argonian race (flagged not playable): they were listed as an
        # Argonian man's head and hair, and the hair's empty mesh failed its bake in every build
        import prepare_player_parts as ppp
        with mock.patch('prepare_player_view.playable_races', return_value=['argonian']):
            rows = ppp.race_rows(kinds())
        man = next(r for r in rows if not r['female'])
        self.assertEqual(man['heads'], ['b_n_argonian_m_head_01'])
        self.assertEqual(man['hairs'], ['b_n_argonian_m_hair01'])

    def test_the_robe_is_worn_on_the_werewolf_only_and_counted_there(self):
        import prepare_player_parts as ppp
        k = kinds()
        races = [{'race': 'argonian', 'female': False, 'skeleton': K_SKELETON, 'skin': {}, 'heads': [], 'hairs': []},
                 {'race': 'nord', 'female': False, 'skeleton': H_SKELETON, 'skin': {}, 'heads': [], 'hairs': []}]
        items = ppp.item_rows(k)
        self.assertIs(WW.robe_row(items, WW.werewolf_set(k)), next(i for i in items if i['id'] == 'werewolfrobe'))
        need = ppp.needed_parts(k, races, items)
        self.assertFalse(any(b == 'werewolfskin' for _, _, b in need))   # not baked on the humanoid or beast skeleton
        self.assertIn((H_SKELETON, 3, 'c_robe'), need)                   # a common robe as before (ROBE-WORN)
        self.assertIn((K_SKELETON, 3, 'c_robe'), need)
        # the robe's skin counted on the werewolf's skeleton: missing without its model, built with it
        cover = ppp.part_coverage(items, {}, {H_SKELETON, K_SKELETON})
        self.assertIn({'item': 'werewolfrobe', 'skeleton': WW.SKELETON, 'slot': 3, 'body': 'werewolfskin'},
                      cover['missing'])
        models = {(s, slot, b): 'progs/parts/aa/aaaaaaaaaa.mdl' for s, slot, b in need}
        models[(WW.SKELETON, 3, 'werewolfskin')] = 'progs/parts/bb/bbbbbbbbbb.mdl'
        cover = ppp.part_coverage(items, models, {H_SKELETON, K_SKELETON})
        self.assertEqual(cover['missing'], [])
        self.assertEqual(cover['skeletons'][WW.LETTER], {'parts': 1, 'built': 1, 'missing': 0})

    def test_the_werewolf_skin_is_off_the_known_missing_list(self):
        import prepare_player_parts as ppp
        rows = json.loads((ROOT / ppp.KNOWN_MISSING).read_text(encoding='utf-8'))['parts']
        self.assertFalse([r for r in rows if r['body'] == 'werewolfskin'])
        self.assertNotIn(('meshes/base_anim.nif', 'werewolfskin'), ppp.known_missing())

    def test_the_other_parts_keep_their_needs_and_unit_inputs(self):
        # a werewolf-set bake does not change another part's unit inputs: the same parts are needed with the werewolf
        # set in the masters as without it, and a part's inputs are the form they always had
        import prepare_player_parts as ppp
        races = [{'race': 'nord', 'female': False, 'skeleton': H_SKELETON, 'skin': {}, 'heads': [], 'hairs': []}]
        with_ww, without = kinds(), kinds(werewolf=False)
        items = ppp.item_rows(with_ww)
        WW.robe_row(items, WW.werewolf_set(with_ww))
        self.assertEqual(ppp.needed_parts(with_ww, races, items),
                         ppp.needed_parts(without, races, ppp.item_rows(without)))
        palette = bytes(range(256)) * 3
        part = ppp.part_dict(3, 'c_shirt', 'c\\C_M_Shirt.nif')
        inputs = ppp.unit_inputs(('/data', palette, H_SKELETON, part, 72))
        self.assertEqual(set(inputs), {'entry', 'skeleton', 'part', 'cap', 'palette_sha256'})
        self.assertEqual(inputs['entry'], {'name': 'part h 3 c_shirt'})
        import prepare_player_fp_parts as fp
        fpin = fp.unit_inputs(('/data', palette, ppp.part_dict(6, 'b_hand', 'b\\B_Hand.nif'), 320))
        self.assertEqual(set(fpin), {'entry', 'skeleton', 'part', 'cap', 'palette_sha256', 'table_frames'})
        self.assertEqual(fpin['skeleton'], fp.FP_SKELETON)

    def test_the_werewolf_units_carry_their_code(self):
        import prepare_player_parts as ppp
        import prepare_player_fp_parts as fp
        ww = WW.werewolf_set(kinds())
        palette = bytes(range(256)) * 3
        with mock.patch.object(WW, 'unit_code', side_effect=lambda f: 'code of ' + f):
            body_in = ppp.unit_inputs(('/data', palette, WW.SKELETON, WW.body_part(ww), 72))
            arms_in = fp.unit_inputs(('/data', palette, WW.first_person_part(ww), WW.FP_CAP))
        self.assertEqual(body_in['entry'], {'name': 'part w 3 werewolfskin'})
        self.assertEqual((body_in['code'], body_in['head_from'], body_in['reducer']),
                         ('code of bake_body', 'skin', 'needed'))
        self.assertEqual((arms_in['skeleton'], arms_in['code']), (WW.SKELETON_1ST, 'code of bake_first_person'))
        self.assertNotEqual(ppp.part_path(WW.SKELETON, WW.body_part(ww)),
                            ppp.part_path(H_SKELETON, WW.body_part(ww)))
        self.assertEqual(fp.fp_part_path(WW.first_person_part(ww)),
                         ppp.part_path(WW.SKELETON_1ST, WW.first_person_part(ww)))


class Recipes(unittest.TestCase):
    def body_recipe(self, werewolf=True):
        import prepare_player_parts as ppp
        k = kinds(werewolf)
        ww = WW.werewolf_set(k)
        items = ppp.item_rows(k)
        WW.robe_row(items, ww)
        races = [{'race': 'argonian', 'female': f, 'skeleton': K_SKELETON, 'weight': 1.0, 'height': 1.0,
                  'skin': {3: 'b_n_argonian_m_chest'}, 'heads': [], 'hairs': []} for f in (False, True)]
        models = {(K_SKELETON, 3, 'b_n_argonian_m_chest'): 'progs/parts/aa/aaaaaaaaaa.mdl',
                  (WW.SKELETON, 3, 'werewolfskin'): 'progs/parts/bb/bbbbbbbbbb.mdl'}
        tables, anms, bones = {'k': 'progs/humanoid_kna.awsk'}, {('k', 0): 'view/parts_km.txt',
                                                                 ('k', 1): 'view/parts_km.txt'}, {'k': (18, 9)}
        if werewolf:
            tables['w'] = WW.TABLE
            anms[('w', 0)] = anms[('w', 1)] = WW.LAYOUT
            bones['w'] = (39, -1)
        return ppp.recipe_text(races + WW.race_rows(ww), items, models, anms, tables, bones)

    def test_the_body_recipe_carries_the_werewolf_rows(self):
        lines = self.body_recipe().splitlines()
        for line in ('T w progs/werewolf.awsk 39 -1', 'A w 0 view/parts_wm.txt', 'A w 1 view/parts_wm.txt',
                     'R werewolf 0 w 1.0000 1.0000', 'S werewolf 0 3 bbbbbbbbbbbb',
                     'R werewolf 1 w 1.0000 1.0000', 'S werewolf 1 3 bbbbbbbbbbbb'):
            self.assertIn(line, lines)
        self.assertFalse([x for x in lines if x.startswith(('H werewolf', 'K werewolf'))])
        robe = next(x for x in lines if x.startswith('I werewolfrobe '))
        self.assertTrue(robe.startswith('I werewolfrobe 24 3=-/-,-/- '))  # nothing on the humanoid or beast columns
        self.assertEqual(reader_errors(self.body_recipe()), [])

    def test_without_the_werewolf_the_recipe_has_no_werewolf_row(self):
        text = self.body_recipe(werewolf=False)
        self.assertNotIn('werewolf', text)
        self.assertNotIn('T w ', text)
        self.assertEqual(reader_errors(text), [])

    def test_the_first_person_recipe_carries_the_werewolf_rows(self):
        import prepare_player_fp_parts as fp
        races = [{'race': 'argonian', 'female': False, 'skin': {6: 'b_hand'}}]
        models = {(6, 'b_hand'): 'progs/parts/cc/cccccccccc.mdl'}
        plain = fp.recipe_text(races, [], models, (41, 21))
        were = fp.recipe_text(races, [], models, (41, 21), {'table': WW.TABLE_1ST, 'bones': (40, -1),
                                                             'slot': WW.FP_SLOT,
                                                             'model': 'progs/parts/dd/dddddddddd.mdl'})
        self.assertEqual(plain.splitlines()[:4], ['AWPP1', 'T h progs/humanoid_1st.awsk 41 21', 'A h 0 -', 'A h 1 -'])
        self.assertNotIn('werewolf', plain)
        lines = were.splitlines()
        for line in ('T w progs/werewolf_1st.awsk 40 -1', 'A w 0 -', 'A w 1 -', 'R werewolf 0 w 1.0000 1.0000',
                     'S werewolf 0 6 dddddddddddd', 'R werewolf 1 w 1.0000 1.0000', 'S werewolf 1 6 dddddddddddd'):
            self.assertIn(line, lines)
        self.assertEqual(set(lines) - set(plain.splitlines()), {x for x in lines if ' w ' in x or 'werewolf' in x})
        self.assertEqual(reader_errors(were), [])

    def test_a_first_person_table_takes_other_stances(self):
        import prepare_player_fp_parts as fp
        source = (ROOT / 'tools/prepare_player_fp_parts.py').read_text(encoding='utf-8')
        head = source[source.index('def fp_table('):source.index('"""', source.index('def fp_table(') + 40)]
        self.assertIn('stances=None, spells=None, light=None', head)
        names = [s for s, _ in [(s, None) for s in fp.STANCES]] + [fp.LIGHT_STANCE] + list(fp.SPELL_STANCES)
        self.assertEqual(len(names) * fp.FRAMES, 308)

    def test_the_werewolf_layout_is_the_player_profile(self):
        import prepare_player_parts as ppp
        source = (ROOT / 'tools/werewolf_parts.py').read_text(encoding='utf-8')
        layout = source[source.index('def body_layout('):source.index('def hand_times(')]
        self.assertIn('player_profile()', layout)
        player = (ROOT / 'tools/prepare_player_parts.py').read_text(encoding='utf-8')
        self.assertIn('npc_anim.plan(rig, player_profile(), over', player[player.index('def player_layout('):])
        names = [g[0] for g in ppp.player_profile()]
        for group in ('idle', 'walk', 'run', 'jump', 'land', 'block', 'ready', 'readywalk', 'swim', 'swimidle'):
            self.assertIn(group, names)


def tube(radius, z0, z1, around=12, rings=8, centre=(0.0, 0.0)):
    """A closed tube (both ends capped)."""
    pts = [(centre[0] + radius * np.cos(2 * np.pi * i / around), centre[1] + radius * np.sin(2 * np.pi * i / around),
            z0 + (z1 - z0) * k / rings) for k in range(rings + 1) for i in range(around)]
    faces = []
    for k in range(rings):
        for i in range(around):
            a, b = k * around + i, k * around + (i + 1) % around
            faces += [(a, b, b + around), (a, b + around, a + around)]
    pts += [(centre[0], centre[1], z0), (centre[0], centre[1], z1)]
    n = len(pts)
    faces += [(n - 2, (i + 1) % around, i) for i in range(around)]
    faces += [(n - 1, rings * around + i, rings * around + (i + 1) % around) for i in range(around)]
    return np.array(pts, float), np.array(faces, int)


def actor():
    """A body on the root and a thin limb on its own bone, as the skeletal bake takes them: (shapes, sources,
    materials, table bytes, bone names)."""
    import skeletal_actor as sa
    shapes, sources = [], []
    for k, (name, bone, (p, f)) in enumerate((('Tri Chest 0', 'bip01', tube(6.0, 0.0, 20.0, around=24, rings=12)),
                                              ('Tri Chest 1', 'bip01 r upperarm',
                                               tube(0.8, 2.0, 18.0, around=12, rings=16, centre=(9.0, 0.0))))):
        shapes.append({'name': name, 'part': -1, 'positions': np.stack([p, p]), 'faces': f,
                       'uv': np.zeros((len(p), 2)), 'colours': np.ones((len(p), 4)), 'material': 0})
        sources.append({'name': name, 'part': -1, 'bones': [bone], 'bone': np.zeros(len(p), int),
                        'second': np.full(len(p), -1), 'weight': np.zeros(len(p)), 'rest': p.copy(),
                        'rest2': np.zeros_like(p), 'faces': f, 'uv': np.zeros((len(p), 2)), 'texture': None})
    q = np.zeros((2, 2, 4), np.int16)
    q[..., 0] = 32767
    table = sa.write_table([-1, 0], {'idle': (0, 1)}, q, np.zeros((2, 2, 3), np.int16), 1.0)
    materials = [{'texture_index': None, 'diffuse': [1.0, 1.0, 1.0], 'alpha': 1.0}]
    return shapes, sources, materials, table, ['bip01', 'bip01 r upperarm']


@unittest.skipUnless(GEOMETRY, 'scipy and PIL are needed for the reduction and its check')
class Route(unittest.TestCase):
    def run_needed(self, today_error=None):
        import skeletal_actor as sa
        shapes, sources, materials, table, bones = actor()
        palette = bytes(range(256)) * 3
        rest = np.eye(4)
        today = mock.patch.object(sa, 'skeletal_from_shapes', side_effect=ValueError(today_error)) if today_error \
            else mock.patch.object(sa, 'skeletal_from_shapes', return_value=(b'today', {'faces': 480, 'budget': 480}))
        with today:
            return WW.needed_model(shapes, materials, {}, palette, sources, lambda name: rest, [1.0, 1.0, 1.0], table,
                                   bones, 'progs/test.awsk', None), shapes

    def test_a_part_reduced_by_the_route_passes_the_hull_check(self):
        import skeletal_actor as sa
        (raw, facts), shapes = self.run_needed()
        source = sum(len(s['faces']) for s in shapes)
        record = facts['reducer']
        self.assertTrue(record['passes'], record)
        self.assertEqual(record['row']['problems'], [])
        self.assertLessEqual(facts['faces'], source)
        self.assertGreaterEqual(record['least_girth'], 0.8)
        k = sa.read_skeletal(raw)                          # one shared-vertex skeletal model on the table it names
        self.assertEqual(k['table'], 'progs/test.awsk')
        self.assertLess(k['nv'], 3 * k['nt'])              # shared vertices, not three a face

    def test_a_refused_today_starts_the_search_and_never_draws_torn(self):
        (raw, facts), _ = self.run_needed('NPC body check: open joint part -1 Tri Chest 0 (gap 1.41)')
        self.assertTrue(facts['reducer']['passes'])
        self.assertIn('NPC body check', facts['reducer']['today_refused'])
        with mock.patch('outer_reduce.needed_bake', return_value=None):
            with self.assertRaises(ValueError) as caught:
                self.run_needed('NPC body check: open joint')
            self.assertIn('no count', str(caught.exception))
            with self.assertRaises(ValueError):          # today's model is never shipped unjudged either
                self.run_needed()

    def test_a_torn_part_fails_the_hull_check(self):
        import outer_hull as H
        shapes, sources, _, _, _ = actor()
        named = [dict(s, positions=s['positions'][:1]) for s in shapes]
        self.assertTrue(H.label_bones(named, sources))
        sp, sf = H.source_whole(named)
        groups = H.bone_faces(named)
        self.assertEqual(H.problems(H.measure(named, sp, sf, groups)), [])     # the source itself passes
        torn = sp.copy()
        limb = slice(len(named[0]['positions'][0]), None)
        torn[limb] += [0.0, 0.0, 6.0]                                         # the limb pulled off the body
        self.assertTrue(H.problems(H.measure(named, torn, sf, groups)))
        cut = sf[:len(named[0]['faces'])]                                     # the limb's faces lost
        self.assertTrue(H.problems(H.measure(named, sp, cut, groups)))


class EmptyPart(unittest.TestCase):
    """NPC-WEREWOLF-NO-MODEL-66: an appearance with a part that holds no shape gets a model without it."""

    def apps(self):
        part = {'slot': 3, 'attach': 'Chest', 'filter': 'Chest', 'id': 'b_chest', 'mesh': 'b\\Chest.nif'}
        hair = {'slot': 1, 'attach': 'Head', 'filter': 'Hair', 'id': 'werewolfhair', 'mesh': 'wolf\\hair.NIF'}
        return {'bm_werewolf_skaal1a3': {'id': 'bm_werewolf_skaal1a3', 'parts': [part, hair]},
                'skaal guard': {'id': 'skaal guard', 'parts': [part]}}

    def read(self, name):
        return {'meshes/b/Chest.nif': b'NetImmerse ... NiTriShape NiTriShapeData ...',
                'meshes/wolf/hair.NIF': b'NetImmerse ... NiNode ...'}[name]

    def test_the_empty_part_is_left_out_and_the_rest_kept_as_it_was(self):
        import npc_library as NL
        apps = self.apps()
        out, emptied = NL.without_empty_parts(apps, '/data', read=self.read)
        self.assertEqual(emptied, {'bm_werewolf_skaal1a3': ['werewolfhair']})
        self.assertEqual([p['id'] for p in out['bm_werewolf_skaal1a3']['parts']], ['b_chest'])
        self.assertIs(out['skaal guard'], apps['skaal guard'])      # no empty part: the same appearance, the same key
        self.assertEqual(len(apps['bm_werewolf_skaal1a3']['parts']), 2)    # the input is not changed

    def test_the_library_gives_it_a_model(self):
        # the bake refuses an appearance with a part that holds no shape (npc_geometry.assemble: "No attached
        # geometry"); before the empty part was left out, the library left the whole appearance out
        import actor_units
        import npc_library as NL
        import pass_cache

        def bake_all(tasks, names, jobs, cache, inputs, log=print):
            done, errors = {}, {}
            for key, _data, _palette, app, _profile in tasks:
                if any('hair' in p['mesh'] for p in app['parts']):
                    errors[key] = 'ValueError: No attached geometry: %r' % app['parts'][-1]
                else:
                    done[key] = ((b'IDPO model', '', {}, {'bytes': 10, 'frames': 1, 'triangles': 1, 'vertices': 3,
                                                          'step': 0.1, 'sha256': 'x'}), 0.1)
            return done, errors, 0
        k = {'NPC_': {i: [('FNAM', z('Werewolf'))] for i in self.apps()}}
        with tempfile.TemporaryDirectory() as data, tempfile.TemporaryDirectory() as out_id1:
            for name, raw in (('meshes/b/Chest.nif', self.read('meshes/b/Chest.nif')),
                              ('meshes/wolf/hair.NIF', self.read('meshes/wolf/hair.NIF'))):
                (Path(data) / name).parent.mkdir(parents=True, exist_ok=True)
                (Path(data) / name).write_bytes(raw)
            with mock.patch.object(NL, 'appearances', return_value=(self.apps(), {})), \
                    mock.patch.object(actor_units, 'bake_appearances', side_effect=bake_all), \
                    mock.patch.object(actor_units, 'open_cache', return_value=None), \
                    mock.patch.object(pass_cache, 'game_data_digest', return_value=None), \
                    mock.patch.object(pass_cache, 'source_digest', return_value='s'), \
                    mock.patch.object(pass_cache, 'previous_digests', return_value=()), \
                    mock.patch.object(pass_cache, 'covered_lines', return_value=[]), \
                    mock.patch('mwad.archives.layered_bsa', return_value=None):
                NL._assets.clear()
                manifest = NL.build(data, bytes(range(256)) * 3, list(self.apps()), out_id1, kinds=k,
                                    held_items=False)
            NL._assets.clear()
        self.assertEqual(manifest['left_out'], {})
        self.assertIn('bm_werewolf_skaal1a3', manifest['npcs'])
        self.assertEqual(manifest['empty_parts'], {'bm_werewolf_skaal1a3': ['werewolfhair']})


if __name__ == '__main__':
    unittest.main()
